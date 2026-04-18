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
from typing import Callable, Any

from google import genai
from google.genai import types
from PIL import Image

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

You will receive a question.md file. Your job: write a SHORT, direct instruction for the CODE_MODEL.

Tell it:
1. What to implement (be specific — method signatures, class names, return types)
2. Which previous year question it most resembles (if any) from the PYQ list below
3. Any tricky edge cases from the test cases

Be concise. No code. Max 150 words.

--- PREVIOUS YEAR QUESTIONS (for reference) ---
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
You are a Java expert solving OPPE exam questions.

Given the question.md and orchestrator instructions, produce a compilable Java solution.

Output STRICT JSON with exactly two keys:
  "block"     — ONLY the code to type into the stub placeholder (no class shell unless stub is empty)
  "full_file" — Complete compilable Java file. Class must be named Solution. Use `java Solution.java` format (Java 11+).

Rules:
- Return ONLY the JSON. No markdown. No explanation.
- full_file MUST compile with `java Solution.java`.
- Keep it minimal: inline lambdas, compact loops, one-liners where readable.
- Match exact output format from test cases (spacing, punctuation).
"""

_CODE_FIX_PROMPT = """\
Your previous solution failed. Fix it.

Error:
{error}

Return ONLY the JSON with "block" and "full_file". No explanation.
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


def _call(model: str, contents: list, system: str, json_out: bool = False, temperature: float = 0.1) -> str:
    """Call Gemini with automatic fallback on rate-limit errors."""
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if json_out else "text/plain",
        temperature=temperature,
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

_MAX_RETRIES = 3


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


def _load_images(image_paths: list[str]) -> list[Image.Image]:
    images: list[Image.Image] = []
    for p in image_paths:
        path = Path(p)
        if path.exists():
            images.append(Image.open(path))
        else:
            log.warning("Image not found, skipping: %s", p)
    if not images:
        raise RuntimeError("No valid images in batch.")
    return images


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

    images = _load_images(image_paths)
    contents: list = images + [
        "Extract the question pack from these exam screenshots. "
        "Output ONLY the markdown as instructed — no extra text."
    ]

    raw = _call(settings.ocr_model, contents, _OCR_PROMPT, json_out=False, temperature=0.05)
    log.info("[OCR] done in %.1fs (%d chars)", time.monotonic() - t0, len(raw))

    # Extract title from first # heading
    title_match = re.search(r"^#\s+(.+)", raw, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "question"

    # Write question.md
    q_dir = _question_dir(title)
    (q_dir / "question.md").write_text(raw, encoding="utf-8")
    (q_dir / "ocr_raw.txt").write_text(raw, encoding="utf-8")
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

def _phase_orchestrate_new(question_md: str) -> str:
    """Returns orchestrator instructions for CODE_MODEL."""
    t0 = time.monotonic()
    system = _ORCHESTRATOR_NEW_PROMPT.format(pyq_context=_PYQ_CONTEXT)
    result = _call(settings.orchestrator_model, [question_md], system, json_out=False, temperature=0.1)
    log.info("[ORCH] instructions ready in %.1fs", time.monotonic() - t0)
    return result

# ---------------------------------------------------------------------------
# Phase B — Orchestrator (debug path)
# ---------------------------------------------------------------------------

def _phase_orchestrate_debug(images: list[Image.Image]) -> str:
    """Returns extracted error text + cause from a debug screenshot."""
    t0 = time.monotonic()
    contents: list = images + ["Analyze the debug output in this screenshot."]
    result = _call(settings.orchestrator_model, contents, _ORCHESTRATOR_DEBUG_PROMPT, json_out=False, temperature=0.05)
    log.info("[ORCH-DEBUG] error extracted in %.1fs", time.monotonic() - t0)
    return result

# ---------------------------------------------------------------------------
# Image classification (single image: new question or debug?)
# ---------------------------------------------------------------------------

def _classify_image(image: Image.Image) -> str:
    """Returns 'NEW' or 'DEBUG'."""
    t0 = time.monotonic()
    result = _call(
        settings.orchestrator_model,
        [image, "Is this a full coding question or a debug window?"],
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

def _parse_test_cases(question_md: str) -> list[dict]:
    """Extract test cases from question.md table."""
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
                    "input": cols[1].replace("\\n", "\n"),
                    "expected_output": cols[2].replace("\\n", "\n"),
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
    Runs the code-gen + verify loop.
    Returns {"block": str, "hint": str, "verified": bool}.
    """
    import json

    test_cases = _parse_test_cases(question_md)
    log.info("[CODE] %d test case(s) extracted", len(test_cases))

    user_msg = (
        f"## Question\n{question_md}\n\n"
        f"## Orchestrator Instructions\n{orch_instructions}\n"
    )
    if extra_context:
        user_msg += f"\n## Additional Context\n{extra_context}\n"
    user_msg += "\nSolve it. Return ONLY the strict JSON."

    history: list[types.Content] = []
    last_block = ""
    last_hint = ""
    verified = False

    for attempt in range(1, _MAX_RETRIES + 1):
        _emit(broadcast, {"type": "status", "message": f"Code gen attempt {attempt}/{_MAX_RETRIES}…"})
        log.info("[CODE] attempt %d/%d", attempt, _MAX_RETRIES)
        t_a = time.monotonic()

        prompt = user_msg if attempt == 1 else _CODE_FIX_PROMPT.format(error=last_hint)
        current = list(history) + [
            types.Content(role="user", parts=[types.Part(text=prompt)])
        ]

        try:
            raw = _call(settings.code_model, current, _CODE_MODEL_PROMPT, json_out=True, temperature=0.15)
        except Exception as e:
            log.warning("[CODE] API error attempt %d: %s", attempt, e)
            last_hint = str(e)
            continue

        log.info("[CODE] model responded in %.1fs", time.monotonic() - t_a)

        # Save attempt response
        (q_dir / f"attempt_{attempt}_response.json").write_text(raw, encoding="utf-8")

        try:
            solution = json.loads(raw)
            block: str = solution.get("block", "")
            full_file: str = solution.get("full_file", "")
        except Exception as exc:
            log.warning("[CODE] JSON parse error: %s", exc)
            last_block = raw
            last_hint = f"JSON parse error: {exc}\nRaw: {raw[:200]}"
            _append_history(history, "model", raw)
            _append_history(history, "user", _CODE_FIX_PROMPT.format(error=last_hint))
            (q_dir / f"attempt_{attempt}_verify.txt").write_text(f"FAIL\n{last_hint}", encoding="utf-8")
            continue

        last_block = block

        if not full_file:
            last_hint = "full_file was empty."
            (q_dir / f"attempt_{attempt}_verify.txt").write_text(f"FAIL\n{last_hint}", encoding="utf-8")
            _append_history(history, "model", raw)
            _append_history(history, "user", _CODE_FIX_PROMPT.format(error=last_hint))
            continue

        # Write Solution.java to question directory
        (q_dir / "Solution.java").write_text(full_file, encoding="utf-8")

        # Verify
        t_v = time.monotonic()
        ok, output = verifier.verify_java_code(full_file, work_dir=q_dir, test_cases=test_cases)
        log.info("[VERIFY] attempt %d: %s (%.1fs)", attempt, "PASS" if ok else "FAIL", time.monotonic() - t_v)
        (q_dir / f"attempt_{attempt}_verify.txt").write_text(
            f"{'PASS' if ok else 'FAIL'}\n{output}", encoding="utf-8"
        )

        if ok:
            verified = True
            last_hint = f"✓ Verified | {APP_STATE.get('current_question_title', '')} | {len(test_cases)} test case(s)"
            break
        else:
            last_hint = output
            _append_history(history, "model", raw)
            _append_history(history, "user", _CODE_FIX_PROMPT.format(error=output[:800]))

    if not verified:
        last_hint = "⚠ Unverified — " + last_hint[:200]

    # Persist state
    APP_STATE["current"] = last_block
    title = APP_STATE.get("current_question_title") or ""
    if title and verified:
        stub_match = re.search(r"```java\n(.*?)```", question_md, re.DOTALL)
        stub_code = stub_match.group(1) if stub_match else ""
        APP_STATE["solved_questions"][title] = {"block": last_block, "stub_code": stub_code}
    save_state()

    # Write summary
    summary = {
        "title": title,
        "verified": verified,
        "attempts": _MAX_RETRIES,
        "hint": last_hint,
        "block_chars": len(last_block),
    }
    import json as _json
    (q_dir / "session_summary.json").write_text(_json.dumps(summary, indent=2), encoding="utf-8")

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
    _emit(broadcast, {"type": "status", "message": "Orchestrating…"})
    orch_instructions = _phase_orchestrate_new(question_md)
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

    # Extract error from debug screenshot
    images = _load_images(image_paths)
    error_analysis = _phase_orchestrate_debug(images)
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
    images = _load_images(image_paths)
    _emit(broadcast, {"type": "status", "message": "Classifying image…"})

    decision = _classify_image(images[0])

    if decision == "DEBUG" and APP_STATE.get("current_question_dir"):
        return process_debug_screenshot(image_paths, broadcast)
    else:
        # Either NEW or no active question for debug
        return generate_and_verify_solution(image_paths, broadcast)
