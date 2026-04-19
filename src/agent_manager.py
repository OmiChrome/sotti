"""
agent_manager.py — Sotti (Architecture v2)

Three-phase pipeline:
  Phase A  — OCR_MODEL    : image pack → question.md
  Phase B  — ORCHESTRATOR : classifies image (new question vs debug), builds code plan
  Phase C  — CODE_MODEL   : generates Java, verifies locally (up to _MAX_RETRIES)

Debug loop:
  Single screenshot → ORCHESTRATOR decides it's debug → CODE_MODEL re-iterates.
"""

import logging
import re
import time
from pathlib import Path
from typing import Callable

from google import genai
from google.genai import types

from .config import settings
from . import verifier
from .state import APP_STATE, save_state

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PYQ knowledge base — loaded once at import time
# ---------------------------------------------------------------------------

def _load_pyq_context() -> str:
    """Read all .java files from oppe-pyq/ and return as a compact string."""
    pyq_dir: Path = settings.oppe_pyq_dir
    if not pyq_dir.is_dir():
        log.warning("oppe-pyq dir not found: %s", pyq_dir)
        return ""
    parts: list[str] = []
    for jf in sorted(pyq_dir.glob("*.java")):
        parts.append(f"=== {jf.name} ===\n{jf.read_text(encoding='utf-8', errors='replace')}")
    joined = "\n\n".join(parts)
    log.info("Loaded %d PYQ files (%d chars)", len(parts), len(joined))
    return joined

_PYQ_CONTEXT: str = _load_pyq_context()

# ---------------------------------------------------------------------------
# System prompts (concise, direct)
# ---------------------------------------------------------------------------

_OCR_PROMPT = """\
You are an OCR engine reading an OPPE Java exam portal screenshot.

Output ONLY a markdown file in this exact format — no extra text:

# <Question Title>

## Problem Statement
<full problem text>

## Test Cases
| # | Input | Expected Output |
|---|-------|-----------------|
| 1 | <input> | <expected output> |

## Stub Code
```java
<exact stub code, character-for-character — DO NOT fix or complete it>
```

Rules:
- Left pane = question. Right pane = stub code.
- Copy stub code EXACTLY as shown. Preserve placeholder comments like "// Write here".
- If multiple test cases exist, list all of them.
"""

_ORCHESTRATOR_NEW_PROMPT = """\
You are an orchestrator for a Java exam assistant.

You receive a question.md. Output a SHORT instruction for CODE_MODEL.

FIRST LINE must be exactly one of:
THINKING: MEDIUM
THINKING: LOW

Use MEDIUM for questions requiring full class design / inheritance / complex logic.
Use LOW for simple single-method or straightforward implementations.

Then write (max 150 words total):
1. What to implement (class names, method signatures, return types)
2. Most similar PYQ (if any)
3. Key edge cases from test cases

No code.

--- PREVIOUS YEAR QUESTIONS ---
{pyq_context}
"""

_ORCHESTRATOR_DEBUG_PROMPT = """\
You are analyzing a debug screenshot from a Java exam portal.

Extract and return ONLY the error text / debug output visible in the image.
Then add one sentence explaining the likely root cause.
Format:
ERROR: <extracted error text>
CAUSE: <one-sentence diagnosis>
"""

_ORCHESTRATOR_CLASSIFY_PROMPT = """\
You are given one screenshot. Decide in ONE WORD:
- "NEW" if it shows a full coding question (problem statement + stub code visible)
- "DEBUG" if it shows only a debug/error window, console output, or partial screen

Reply with exactly one word: NEW or DEBUG
"""

_CODE_MODEL_PROMPT = """\
You are a Java expert solving OPPE exam questions. Produce a complete, compilable Java solution.

REQUIRED OUTPUT FORMAT (markdown — DO NOT deviate):

## BLOCK
<the code that fills the stub — keep original stub anchor comments, ultra-compact bodies>

## FULL SOLUTION
```java
<complete compilable Java file, public class named Solution, all helpers non-public>
```

Hard rules — violations cause immediate test failure:
- Output ONLY the two markdown sections above. No explanation, no extra text.
- Compile + run: `java Solution.java` (Java 11+ single-file launcher).
- public class MUST be `Solution`. ALL other classes must NOT be public.
- Read EXACTLY as many tokens as the stub does — no more, no fewer.
  sc.next() reads one whitespace-delimited token. Newlines in stdin are whitespace.
- toString() / print format must EXACTLY match expected output (spacing, colon, comma, order).
  Derive the format from the test cases — do NOT guess.
- Deep-clone mutable fields in clone() — never share object references between e1 and e2.
- After e1.updateEmp(...), e2 must still hold the ORIGINAL values.

BLOCK comment rules — SCREEN SPACE IS CRITICAL:
1. KEEP original stub anchor comments EXACTLY as written:
     //define class Address          ← keep verbatim
     // Define the method getFoo()   ← keep verbatim, NOT the lines after it
2. STRIP any multi-line or descriptive comment that explains what the code does:
     REMOVE: //that uses the method isEligible() to return the stream of eligible students.
     REMOVE: //that helps customizing output message
     Only the single anchor line survives. Nothing else.
3. Write method bodies as one-liners — NO unnecessary newlines:
     GOOD: public Stream<Student> getEligibleList(List<Student> l) { return l.stream().filter(Student::isEligible); }
     BAD: method open-brace on one line, return on next, close-brace on next
4. Simple getters/setters MUST be one-liners.

BLOCK layout example (stub had three anchor comments, one was multi-line — strip extras):
  //define class Address
  class Address implements Cloneable { private String a; Address(String a){this.a=a;} public String getA(){return a;} public void setA(String a){this.a=a;} public Object clone() throws CloneNotSupportedException{return super.clone();} }

  //define class StudentList
  class StudentList { public Stream<Student> getEligibleList(List<Student> l){return l.stream().filter(Student::isEligible);} public boolean isEmpty(Stream<Student> s){return s.findAny().isEmpty();} }
"""


_CODE_FIX_PROMPT = """\
Your solution failed verification. Fix ONLY the error below. Do NOT rewrite unrelated code.

Error:
{error}

Common causes:
- NoSuchElementException → you read more tokens than stdin provides. Count sc.next() calls.
- WRONG OUTPUT field order → re-read the toString() format from the expected output above.
- Clone not deep enough → addr and dept objects still shared after clone().

Output the SAME markdown format:
## BLOCK
<fixed stub code>

## FULL SOLUTION
```java
<fixed complete file>
```
"""


# ---------------------------------------------------------------------------
# Gemini client (lazy, with fallback)
# ---------------------------------------------------------------------------

_client: genai.Client | None = None
_fallback_client: genai.Client | None = None


def _get_client(use_fallback: bool = False) -> genai.Client:
    global _client, _fallback_client
    if use_fallback:
        if not settings.gemini_api_key_fallback:
            raise ValueError("Fallback requested but GEMINI_API_KEY_FALLBACK not set.")
        if _fallback_client is None:
            _fallback_client = genai.Client(api_key=settings.gemini_api_key_fallback)
        return _fallback_client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# ---------------------------------------------------------------------------
# Thinking level resolution
#
# Abstract intents (used throughout this file):
#   None          → no thinking at all (OCR — fastest path)
#   "FAST"        → quick computation  (gemma: MINIMAL | gemini: LOW)
#   "CAREFUL"     → thorough reasoning (gemma: HIGH    | gemini: MEDIUM)
#
# "HIGH" for gemini is never used — takes 135s+; cap is MEDIUM.
# ---------------------------------------------------------------------------

_THINKING_OFF     = None       # OCR only
_THINKING_FAST    = "FAST"     # debug re-runs, simple fixes
_THINKING_CAREFUL = "CAREFUL"  # orchestrator + code gen default

# Sentinel for "never use HIGH on gemini" — maps to CAREFUL at most
_THINKING_HIGH = "HIGH"  # kept for gemma compatibility only


def _resolve_thinking(model: str, intent: str | None) -> str | None:
    """
    Map abstract intent to the correct API string for the given model family.

    Gemma (gemma-*):  supports MINIMAL and HIGH only.
    Gemini (gemini-*): supports LOW, MEDIUM, HIGH — we cap at MEDIUM.
    """
    if intent is None:
        return None
    is_gemma = model.lower().startswith("gemma")
    if is_gemma:
        # Gemma API: MINIMAL (fast) or HIGH (thorough) — nothing else
        return "HIGH" if intent in ("CAREFUL", "HIGH") else "MINIMAL"
    else:
        # Gemini API: LOW (fast) or MEDIUM (thorough); avoid HIGH (too slow)
        return "LOW" if intent in ("FAST",) else "MEDIUM"


def _call(
    model: str,
    contents: list,
    system: str,
    json_out: bool = False,
    temperature: float = 0.1,
    thinking_intent: str | None = _THINKING_OFF,
) -> str:
    """Call Gemini/Gemma. AFC disabled. thinking_intent resolved per model family."""
    resolved = _resolve_thinking(model, thinking_intent)
    thinking_cfg = (
        types.ThinkingConfig(thinking_level=resolved)
        if resolved is not None
        else None
    )
    if resolved:
        log.debug("[CALL] %s | thinking=%s (intent=%s)", model, resolved, thinking_intent)
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if json_out else "text/plain",
        temperature=temperature,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        thinking_config=thinking_cfg,
    )
    for use_fb in (False, True):
        try:
            resp = _get_client(use_fb).models.generate_content(
                model=model, contents=contents, config=cfg
            )
            return resp.text or ""
        except Exception as e:
            err = str(e)
            if use_fb or ("429" not in err and "503" not in err) or not settings.gemini_api_key_fallback:
                raise
            log.warning("Rate limit on primary key, switching to fallback...")
    return ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BroadcastFn = Callable[[dict], None]

_MAX_RETRIES = 2


def _emit(broadcast: BroadcastFn | None, payload: dict) -> None:
    if broadcast is None:
        return
    try:
        broadcast(payload)
    except Exception as exc:
        log.debug("Broadcast failed: %s", exc)


def _slug(text: str, max_len: int = 48) -> str:
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    return text[:max_len] or "unknown"


_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def _load_image_parts(image_paths: list[str]) -> list[types.Part]:
    """
    Load images as types.Part.from_bytes() with correct MIME types.
    This is the recommended approach per Gemini image understanding docs
    (inline data, <20MB per request).
    """
    parts: list[types.Part] = []
    for p in image_paths:
        path = Path(p)
        if not path.exists():
            log.warning("Image not found, skipping: %s", p)
            continue
        mime = _MIME_MAP.get(path.suffix.lower(), "image/jpeg")
        parts.append(types.Part.from_bytes(
            data=path.read_bytes(),
            mime_type=mime,
        ))
    if not parts:
        raise RuntimeError("No valid images in batch.")
    return parts


def _question_dir(title: str) -> Path:
    slug = _slug(title)
    d = settings.data_dir / slug
    d.mkdir(parents=True, exist_ok=True)
    return d

# ---------------------------------------------------------------------------
# Phase A — OCR
# ---------------------------------------------------------------------------

def _phase_ocr(image_paths: list[str], broadcast: BroadcastFn | None) -> tuple[str, Path]:
    """Returns (question_md_text, question_dir_path)."""
    _emit(broadcast, {"type": "status", "message": "OCR in progress…"})
    t0 = time.monotonic()

    img_parts = _load_image_parts(image_paths)
    contents: list = img_parts + [
        "Extract the question pack from these exam screenshots. "
        "Output ONLY the markdown as instructed — no extra text."
    ]

    raw = _call(settings.ocr_model, contents, _OCR_PROMPT, json_out=False, temperature=0.05)
    log.info("[OCR] done in %.1fs (%d chars)", time.monotonic() - t0, len(raw))

    # Extract title from first # heading
    title_match = re.search(r"^#\s+(.+)", raw, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "question"

    # Write question.md (single source of truth — no duplicate ocr_raw.txt)
    q_dir = _question_dir(title)
    (q_dir / "question.md").write_text(raw, encoding="utf-8")
    log.info("[OCR] Wrote question.md → %s", q_dir)

    # Update global state
    APP_STATE["current_question_dir"] = str(q_dir)
    APP_STATE["current_question_title"] = title
    save_state()

    # Parse stub preview for frontend
    stub_match = re.search(r"```java\n(.*?)```", raw, re.DOTALL)
    stub_preview = stub_match.group(1)[:300] if stub_match else raw[:300]

    _emit(broadcast, {
        "type": "ocr",
        "title": title,
        "block": f"// ✓ OCR Complete — {title}\n// Generating solution…\n\n{stub_preview}",
    })

    return raw, q_dir

# ---------------------------------------------------------------------------
# Phase B — Orchestrator (new question path)
# ---------------------------------------------------------------------------

def _phase_orchestrate_new(question_md: str, broadcast: BroadcastFn | None = None) -> str:
    """Returns orchestrator instructions for CODE_MODEL."""
    t0 = time.monotonic()
    _emit(broadcast, {"type": "status", "message": "Orchestrator thinking… (MEDIUM)"})
    log.info("[ORCH] calling model with MEDIUM thinking")
    system = _ORCHESTRATOR_NEW_PROMPT.format(pyq_context=_PYQ_CONTEXT)
    result = _call(
        settings.orchestrator_model,
        [question_md],
        system,
        thinking_intent=_THINKING_CAREFUL,
        temperature=0.1,
    )
    log.info("[ORCH] instructions ready in %.1fs", time.monotonic() - t0)
    return result

# ---------------------------------------------------------------------------
# Phase B — Orchestrator (debug path)
# ---------------------------------------------------------------------------

def _phase_orchestrate_debug(image_paths: list[str]) -> str:
    """Returns extracted error text + cause from a debug screenshot."""
    t0 = time.monotonic()
    img_parts = _load_image_parts(image_paths)
    contents: list = img_parts + ["Analyze the debug output in this screenshot."]
    result = _call(settings.orchestrator_model, contents, _ORCHESTRATOR_DEBUG_PROMPT, json_out=False, temperature=0.05)
    log.info("[ORCH-DEBUG] error extracted in %.1fs", time.monotonic() - t0)
    return result

# ---------------------------------------------------------------------------
# Image classification (single image: new question or debug?)
# ---------------------------------------------------------------------------

def _classify_image(image_paths: list[str]) -> str:
    """Returns 'NEW' or 'DEBUG'. Passes first image as Part.from_bytes."""
    t0 = time.monotonic()
    img_parts = _load_image_parts(image_paths[:1])  # only need first image to classify
    result = _call(
        settings.orchestrator_model,
        img_parts + ["Is this a full coding question or a debug window?"],
        _ORCHESTRATOR_CLASSIFY_PROMPT,
        json_out=False,
        temperature=0.0,
    )
    decision = result.strip().upper()
    decision = "DEBUG" if "DEBUG" in decision else "NEW"
    log.info("[CLASSIFY] %.1fs → %s", time.monotonic() - t0, decision)
    return decision

# ---------------------------------------------------------------------------
# Phase C — Code generation + verification loop
# ---------------------------------------------------------------------------

def _parse_code_response(raw: str) -> tuple[str, str]:
    """
    Parse the markdown response from CODE_MODEL.
    Returns (block, full_file). Both may be empty string on failure.
    """
    block = ""
    full_file = ""

    # Extract FULL SOLUTION java block — handles newline(s) between heading and fence
    full_match = re.search(
        r"##\s*FULL\s+SOLUTION\s*\n\s*```java\s*\n(.*?)```",
        raw, re.DOTALL | re.IGNORECASE
    )
    if full_match:
        full_file = full_match.group(1).strip()

    # Extract BLOCK section — everything between ## BLOCK and the next ## heading or fence
    block_match = re.search(
        r"##\s*BLOCK\s*\n(.*?)(?=\n\s*##|\n\s*```|\Z)",
        raw, re.DOTALL | re.IGNORECASE
    )
    if block_match:
        block = block_match.group(1).strip()

    return block, full_file


def _normalise_cell(cell: str) -> str:
    """
    Clean a markdown table cell value:
    - <br>, <br/>, <BR> → newline (exam portal uses these for multiline input)
    - literal \n escape → newline
    - strip surrounding whitespace
    """
    cell = re.sub(r"<br\s*/?>", "\n", cell, flags=re.IGNORECASE)
    cell = cell.replace("\\n", "\n")
    return cell.strip()


def _parse_test_cases(question_md: str) -> list[dict]:
    """Extract test cases from question.md markdown table.
    Handles <br> separators in both input and expected_output columns.
    """
    cases: list[dict] = []
    in_table = False
    for line in question_md.splitlines():
        if "| # |" in line or "| Input |" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 3:
                cases.append({
                    "input": _normalise_cell(cols[1]),
                    "expected_output": _normalise_cell(cols[2]),
                })
        elif in_table:
            break
    return cases


def _phase_code_gen(
    question_md: str,
    orch_instructions: str,
    q_dir: Path,
    broadcast: BroadcastFn | None,
    extra_context: str = "",
) -> dict:
    """
    Code-gen + verify loop. Returns {"block", "hint", "verified"}.
    Output format: markdown with ## BLOCK and ## FULL SOLUTION sections.
    """
    test_cases = _parse_test_cases(question_md)
    log.info("[CODE] %d test case(s) extracted", len(test_cases))

    # Determine thinking intent from orchestrator's first-line hint
    # Orchestrator emits THINKING: MEDIUM (→ CAREFUL) or THINKING: LOW (→ FAST)
    # Debug re-runs always use FAST
    thinking_intent = _THINKING_FAST if extra_context else _THINKING_CAREFUL
    first_line = orch_instructions.splitlines()[0].strip().upper() if orch_instructions else ""
    if "THINKING: MEDIUM" in first_line or "THINKING: CAREFUL" in first_line:
        thinking_intent = _THINKING_CAREFUL
    elif "THINKING: LOW" in first_line or "THINKING: FAST" in first_line:
        thinking_intent = _THINKING_FAST
    # Never escalate to HIGH on gemini; resolver handles gemma HIGH automatically
    log.info("[CODE] thinking_intent=%s", thinking_intent)

    user_msg = (
        f"## Question\n{question_md}\n\n"
        f"## Orchestrator Instructions\n{orch_instructions}\n"
    )
    if extra_context:
        user_msg += f"\n## Context\n{extra_context}\n"
    user_msg += "\nSolve it. Output the required markdown."

    history: list[types.Content] = []
    last_block = ""
    last_hint = ""
    verified = False

    for attempt in range(1, _MAX_RETRIES + 1):
        msg = f"Code gen attempt {attempt}/{_MAX_RETRIES} ({thinking_intent} thinking)…"
        _emit(broadcast, {"type": "status", "message": msg})
        log.info("[CODE] attempt %d/%d | thinking=%s", attempt, _MAX_RETRIES, thinking_intent)
        t_a = time.monotonic()

        prompt = user_msg if attempt == 1 else _CODE_FIX_PROMPT.format(error=last_hint[:600])
        current = list(history) + [
            types.Content(role="user", parts=[types.Part(text=prompt)])
        ]

        try:
            raw = _call(
                settings.code_model,
                current,
                _CODE_MODEL_PROMPT,
                temperature=0.1,
                thinking_intent=thinking_intent,
            )
        except Exception as e:
            log.warning("[CODE] API error attempt %d: %s", attempt, e)
            last_hint = str(e)
            continue

        log.info("[CODE] responded in %.1fs", time.monotonic() - t_a)
        (q_dir / f"attempt_{attempt}_raw.md").write_text(raw, encoding="utf-8")

        block, full_file = _parse_code_response(raw)

        if not full_file:
            last_hint = f"Could not parse FULL SOLUTION section. Raw output was:\n{raw[:400]}"
            log.warning("[CODE] parse failed attempt %d", attempt)
            _append_history(history, "model", raw)
            _append_history(history, "user", _CODE_FIX_PROMPT.format(error=last_hint))
            (q_dir / f"attempt_{attempt}_verify.txt").write_text(f"FAIL\n{last_hint}", encoding="utf-8")
            continue

        last_block = block

        # Write Solution.java (verifier will run: java Solution.java)
        (q_dir / "Solution.java").write_text(full_file, encoding="utf-8")

        # Verify with java command
        t_v = time.monotonic()
        ok, output = verifier.verify_java_code(full_file, work_dir=q_dir, test_cases=test_cases)
        log.info("[VERIFY] %s (%.1fs)", "PASS" if ok else "FAIL", time.monotonic() - t_v)
        (q_dir / f"attempt_{attempt}_verify.txt").write_text(
            f"{'PASS' if ok else 'FAIL'}\n{output}", encoding="utf-8"
        )

        if ok:
            verified = True
            last_hint = f"\u2713 Verified | {APP_STATE.get('current_question_title', '')} | {len(test_cases)} TC"
            # Block already contains original stub comments from prompt rule — write as-is
            (q_dir / "solution.md").write_text(
                f"# Solution Block\n\n```java\n{block}\n```\n",
                encoding="utf-8",
            )

            break
        else:
            last_hint = output
            _append_history(history, "model", raw)
            _append_history(history, "user", _CODE_FIX_PROMPT.format(error=output[:600]))

    if not verified:
        last_hint = "\u26a0 Unverified \u2014 " + last_hint[:200]

    # Persist state
    APP_STATE["current"] = last_block
    title = APP_STATE.get("current_question_title") or ""
    if title and verified:
        stub_match = re.search(r"```java\n(.*?)```", question_md, re.DOTALL)
        stub_code = stub_match.group(1) if stub_match else ""
        APP_STATE["solved_questions"][title] = {"block": last_block, "stub_code": stub_code}
    save_state()

    import json as _json
    (q_dir / "session_summary.json").write_text(_json.dumps({
        "title": title, "verified": verified,
        "attempts": _MAX_RETRIES, "hint": last_hint,
    }, indent=2), encoding="utf-8")

    return {"block": last_block, "hint": last_hint, "verified": verified}


def _append_history(history: list, role: str, text: str) -> None:
    history.append(types.Content(role=role, parts=[types.Part(text=text)]))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_and_verify_solution(
    image_paths: list[str],
    broadcast: BroadcastFn | None = None,
) -> dict | None:
    """
    Full pipeline for a new image pack (multiple images or single classified as NEW).

    1. OCR → question.md
    2. Orchestrate → instructions
    3. Code gen + verify loop
    4. Broadcast solution to frontend

    Returns {"block", "hint"} or None if question already solved unchanged.
    """
    log.info("▶ NEW QUESTION pipeline | images=%s", [Path(p).name for p in image_paths])
    t_total = time.monotonic()

    # Phase A
    question_md, q_dir = _phase_ocr(image_paths, broadcast)

    # Dedup check
    title = APP_STATE.get("current_question_title", "")
    stub_match = re.search(r"```java\n(.*?)```", question_md, re.DOTALL)
    stub_code = stub_match.group(1) if stub_match else ""
    if title and title in APP_STATE["solved_questions"]:
        prev = APP_STATE["solved_questions"][title]
        if prev.get("stub_code") == stub_code:
            _emit(broadcast, {"type": "status", "message": "Question already solved."})
            log.info("Question '%s' already solved — skipping.", title)
            return None

    # Phase B
    _emit(broadcast, {"type": "status", "message": "Orchestrator analysing question…"})
    orch_instructions = _phase_orchestrate_new(question_md, broadcast)
    (q_dir / "orchestrator_plan.txt").write_text(orch_instructions, encoding="utf-8")

    # Phase C
    result = _phase_code_gen(question_md, orch_instructions, q_dir, broadcast)

    log.info("▶ DONE | verified=%s | elapsed=%.1fs", result["verified"], time.monotonic() - t_total)
    return {"block": result["block"], "hint": result["hint"]}


def process_debug_screenshot(
    image_paths: list[str],
    broadcast: BroadcastFn | None = None,
) -> dict | None:
    """
    Debug loop: single screenshot with error/debug output.

    1. ORCHESTRATOR extracts error text from image
    2. CODE_MODEL re-iterates with error as context
    3. Broadcast updated solution

    Returns {"block", "hint"} or None on failure.
    """
    log.info("▶ DEBUG pipeline | images=%s", [Path(p).name for p in image_paths])
    t_total = time.monotonic()

    _emit(broadcast, {"type": "status", "message": "Analyzing debug screenshot…"})

    q_dir_str = APP_STATE.get("current_question_dir")
    if not q_dir_str:
        log.warning("[DEBUG] No active question dir — cannot debug.")
        _emit(broadcast, {"type": "error", "message": "No active question to debug."})
        return None

    q_dir = Path(q_dir_str)
    question_md_path = q_dir / "question.md"
    if not question_md_path.exists():
        log.warning("[DEBUG] question.md not found in %s", q_dir)
        _emit(broadcast, {"type": "error", "message": "question.md not found for active question."})
        return None

    question_md = question_md_path.read_text(encoding="utf-8")

    # Extract error from debug screenshot (passes image_paths directly)
    error_analysis = _phase_orchestrate_debug(image_paths)
    log.info("[DEBUG] Error analysis:\n%s", error_analysis[:300])

    # Reload orchestrator plan if available
    orch_plan_path = q_dir / "orchestrator_plan.txt"
    orch_instructions = orch_plan_path.read_text(encoding="utf-8") if orch_plan_path.exists() else ""

    # Re-run code gen with debug context
    result = _phase_code_gen(
        question_md,
        orch_instructions,
        q_dir,
        broadcast,
        extra_context=f"Previous attempt produced this error:\n{error_analysis}",
    )

    log.info("▶ DEBUG DONE | verified=%s | elapsed=%.1fs", result["verified"], time.monotonic() - t_total)
    return {"block": result["block"], "hint": result["hint"]}


def classify_and_route(
    image_paths: list[str],
    broadcast: BroadcastFn | None = None,
) -> dict | None:
    """
    Entry point for SINGLE image batches.
    Orchestrator decides NEW vs DEBUG, then routes appropriately.
    """
    _emit(broadcast, {"type": "status", "message": "Classifying image…"})

    decision = _classify_image(image_paths)

    if decision == "DEBUG" and APP_STATE.get("current_question_dir"):
        return process_debug_screenshot(image_paths, broadcast)
    else:
        # Either NEW or no active question for debug
        return generate_and_verify_solution(image_paths, broadcast)
