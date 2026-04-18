"""
agent_manager.py — Sotti Phase 6
Phase 2 & 3: Extracts question-pack and generates Java solution in one go.
Phase 6: Includes OCR fallback, smart question tracking by title to save compute,
         and proactive status broadcasting for the UI ticker.
"""

import json
import logging
import time
from pathlib import Path
from typing import Callable, Any

from google import genai
from google.genai import types
from PIL import Image

from .config import settings
from . import verifier
from .state import APP_STATE, save_state
from .data_logger import DataLogger

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_ORCHESTRATOR_SYSTEM_PROMPT = """\
You are an advanced data extraction agent operating in a two-part workflow. \
You will be provided with screenshots of a coding examination portal. \
The screen is split into two panes: the Question (Left) and the Stub Code (Right).
Your task is to extract information from both panes and output a STRICT, valid JSON object.

### Part 1: Question Extraction (Intelligent Mode)
Read the left pane. Extract the title, the core problem statement, and all visible \
test cases (Inputs and Expected Outputs).

### Part 2: Stub Code Extraction (Strict OCR Mode)
Read the right pane. You are now functioning as a dumb, literal OCR engine.
CRITICAL RULES FOR STUB CODE:
- Transcribe the code EXACTLY character-for-character as it appears in the image.
- DO NOT fix missing semicolons, syntax errors, or typos.
- DO NOT format or indent the code differently than the image.
- DO NOT remove or answer the placeholder comments \
(e.g., "// Write your solution here" or "// Define constructor here").
- DO NOT complete the code. Only output what is visible on the screen.

### EXAMPLE JSON OUTPUT FORMAT:
{
  "title": "Inheritance - Doctor and Surgeon",
  "question": "A hospital management system maintains records of doctors...",
  "test_cases": [{"input": "...", "expected_output": "..."}],
  "stub_code": "class Doctor {\\n    private String name;\\n// Define constructor here\\n}\\n\\nclass Surgeon extends Doctor {\\n// Define constructor here\\n}"
}\
"""

_SUB_AGENT_SYSTEM_PROMPT = """\
You are a Java expert. You will be given a coding question pack (JSON) that contains \
the problem title, problem statement, test cases, and stub code from an exam portal.

Your task is to produce a complete, correct Java solution.

Output STRICT JSON with EXACTLY two keys:
  "block"     — ONLY the minimal code required to be typed into the portal's \
placeholder (no surrounding class/method shell unless the placeholder is a whole class).
  "full_file" — The complete, compilable Java file including all necessary imports \
and the block injected into the stub code, so it can be compiled and run locally \
with `java Solution.java`. The class must be named Solution.

Rules:
- Return ONLY the JSON object. No markdown fences. No extra text.
- The full_file MUST compile cleanly with standard javac / java (Java 11+).
- Use a public class named Solution as the top-level class.
\
"""

# ---------------------------------------------------------------------------
# Lazy-initialised Gemini client
# ---------------------------------------------------------------------------

_client: genai.Client | None = None
_fallback_client: genai.Client | None = None

def _get_client(use_fallback: bool = False) -> genai.Client:
    global _client, _fallback_client
    if use_fallback:
        if not settings.gemini_api_key_fallback:
            raise ValueError("Fallback requested but gemini_api_key_fallback is not configured.")
        if _fallback_client is None:
            _fallback_client = genai.Client(api_key=settings.gemini_api_key_fallback)
            log.info("Gemini fallback client initialised.")
        return _fallback_client

    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
        log.info("Gemini primary client initialised.")
    return _client

def _generate_with_fallback(model: str, contents: list, config: types.GenerateContentConfig) -> Any:
    client = _get_client()
    try:
        return client.models.generate_content(model=model, contents=contents, config=config)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "503" in error_msg:
            if settings.gemini_api_key_fallback:
                log.warning("API key hit rate limit/error: %s. Switching to fallback key...", error_msg[:50])
                fallback_client = _get_client(use_fallback=True)
                return fallback_client.models.generate_content(model=model, contents=contents, config=config)
            else:
                log.warning("API key hit rate limit/error (%s), but no fallback key configured.", error_msg[:50])
        raise

# ---------------------------------------------------------------------------
# Broadcast helper type
# ---------------------------------------------------------------------------

# A sync callable that schedules a broadcast on the asyncio loop.
# Provided by watcher._sync_broadcast so it's safe to call from a thread.
BroadcastFn = Callable[[dict], None]


# ---------------------------------------------------------------------------
# Phase 3 / 6 — Full AI Pipeline (OCR + Code Generation)
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3

def generate_and_verify_solution(
    image_paths: list[str],
    broadcast: BroadcastFn | None = None,
) -> dict | None:
    """
    1) Extracts the question pack using the orchestrator (or sub_agent fallback).
    2) Checks APP_STATE["solved_questions"] to avoid redundant generation.
    3) Generates a Java solution, verifying locally up to _MAX_RETRIES times.
    """
    import asyncio

    def _emit(payload: dict) -> None:
        """Fire-and-forget sync shim. Guards against closed/stopped event loop."""
        if broadcast is None:
            return
        try:
            broadcast(payload)
        except Exception as exc:
            log.warning("Broadcast emit failed: %s", exc)

    log.info("  [OCR] Starting OCR stage...")
    _emit({"type": "status", "message": "Doing OCR..."})
    t0 = time.monotonic()

    if not image_paths:
        raise ValueError("image_paths must not be empty")

    parts: list = []
    for raw_path in image_paths:
        path = Path(raw_path)
        if not path.exists():
            log.warning("Image not found, skipping: %s", path)
            continue
        parts.append(Image.open(path))

    if not parts:
        raise RuntimeError("No valid images could be loaded from the batch.")

    # Initialise DataLogger with a temporary title; renamed after OCR extracts the real one.
    dl = DataLogger(title="ocr-pending")
    dl.log_ocr_images(image_paths)

    parts.append(
        "Extract the question pack from the screenshot(s) above. "
        "Return ONLY the JSON object — no markdown fences, no extra text."
    )

    log.info("  [OCR] Sending %d image(s) to model=%s ...", len(image_paths), settings.orchestrator_model)

    try:
        t_api = time.monotonic()
        ocr_model_used = settings.orchestrator_model
        response = _generate_with_fallback(
            model=ocr_model_used,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=_ORCHESTRATOR_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        log.info("  [OCR] Model responded in %.1fs", time.monotonic() - t_api)
    except Exception as e:
        log.warning("  [OCR] Failed with %s in %.1fs: %s. Trying fallback model=%s ...",
                    settings.orchestrator_model, time.monotonic() - t_api, e, settings.sub_agent_model)
        _emit({"type": "status", "message": f"OCR fallback, using {settings.sub_agent_model}..."})
        t_api = time.monotonic()
        ocr_model_used = settings.sub_agent_model
        response = _generate_with_fallback(
            model=ocr_model_used,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=_ORCHESTRATOR_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        log.info("  [OCR] Fallback responded in %.1fs", time.monotonic() - t_api)

    raw_text: str = response.text or ""

    try:
        question_pack = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OCR Model returned invalid JSON: {exc}\n{raw_text[:200]}") from exc

    title = question_pack.get("title", "")
    stub_code = question_pack.get("stub_code", "")
    log.info("  [OCR] Extracted title=%r  stub_code_len=%d  elapsed=%.1fs",
             title, len(stub_code), time.monotonic() - t0)

    # Re-create DataLogger now that we have the real title for a readable folder name.
    dl = DataLogger(title=title or "unknown")
    dl.log_ocr_images(image_paths)
    dl.log_ocr_response(ocr_model_used, raw_text, question_pack)

    # Check solved_questions state
    if title and title in APP_STATE["solved_questions"]:
        solved_info = APP_STATE["solved_questions"][title]
        # if the stub code is the same, abort to save compute
        if solved_info.get("stub_code") == stub_code:
            _emit({"type": "status", "message": "Question already solved."})
            log.info("Question '%s' already solved and stub unchanged. Aborting.", title)
            return None

    _emit({"type": "status", "message": "Generating code..."})
    log.info("  [GEN] Starting code generation (model=%s, max_retries=%d)...",
             settings.sub_agent_model, _MAX_RETRIES)
    t1 = time.monotonic()

    user_prompt = (
        "Here is the question pack (JSON):\n"
        + json.dumps(question_pack, indent=2)
        + "\n\nSolve it. Return ONLY the strict JSON with 'block' and 'full_file' keys."
    )

    history: list[types.Content] = []
    last_block: str = ""
    last_hint: str = ""
    verified = False

    for attempt in range(1, _MAX_RETRIES + 1):
        log.info("  [GEN] Attempt %d/%d — calling model...", attempt, _MAX_RETRIES)
        _emit({"type": "status", "message": f"Code gen attempt {attempt}/{_MAX_RETRIES}..."})
        t_attempt = time.monotonic()

        current_contents: list = list(history) + [
            types.Content(
                role="user",
                parts=[types.Part(text=user_prompt if attempt == 1 else _fix_prompt(last_stderr=last_hint))],
            )
        ]

        # Log the request (snapshot the text parts only — images are already logged)
        dl.log_gen_request(
            attempt,
            settings.sub_agent_model,
            [p.text for c in current_contents for p in c.parts if hasattr(p, "text") and p.text],
        )

        response = _generate_with_fallback(
            model=settings.sub_agent_model,
            contents=current_contents,
            config=types.GenerateContentConfig(
                system_instruction=_SUB_AGENT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        raw_text: str = response.text or ""
        log.info("  [GEN] Attempt %d/%d responded in %.1fs", attempt, _MAX_RETRIES, time.monotonic() - t_attempt)

        try:
            solution = json.loads(raw_text)
            block: str = solution.get("block", "")
            full_file: str = solution.get("full_file", "")
        except json.JSONDecodeError as exc:
            log.warning("Sub-agent returned non-JSON on attempt %d: %s", attempt, exc)
            last_block = raw_text
            last_hint = f"JSON parse error: {exc}"
            dl.log_gen_response(attempt, raw_text, None)
            dl.log_verify_result(attempt, False, f"JSON parse error: {exc}")
            _append_to_history(history, role="model", text=raw_text)
            _append_to_history(history, role="user", text=_fix_prompt(last_stderr=last_hint))
            continue

        last_block = block
        dl.log_gen_response(attempt, raw_text, {"block": block, "full_file": full_file})

        log.info("  [VERIFY] Attempt %d/%d — compiling full_file (%d chars)...",
                 attempt, _MAX_RETRIES, len(full_file))
        t_verify = time.monotonic()

        if full_file:
            ok, output = verifier.verify_java_code(full_file)
        else:
            ok, output = False, "full_file was empty; cannot verify."

        dl.log_verify_result(attempt, ok, output)

        if ok:
            log.info("  [VERIFY] PASSED on attempt %d in %.1fs", attempt, time.monotonic() - t_verify)
            last_hint = _build_hint(question_pack, ok=True)
            verified = True
            break
        else:
            err_snippet = output[:300]
            log.warning("  [VERIFY] FAILED on attempt %d in %.1fs: %s",
                        attempt, time.monotonic() - t_verify, err_snippet)
            last_hint = output

            _append_to_history(history, role="model", text=raw_text)
            _append_to_history(history, role="user", text=_fix_prompt(last_stderr=output))

    if not verified:
        log.warning("  [GEN] All %d attempts failed in %.1fs. Returning best-effort.",
                    _MAX_RETRIES, time.monotonic() - t1)
        last_hint = "WARNING: Failed local verification — " + last_hint[:200]
    else:
        log.info("  [GEN] Solution verified in %.1fs total.", time.monotonic() - t1)
        APP_STATE["current"] = last_block
        if title:
            APP_STATE["solved_questions"][title] = {
                "block": last_block,
                "stub_code": stub_code
            }
        save_state()

    dl.log_final(last_block, last_hint, verified)
    log.info("  [DATA] Session saved → %s", dl.session_dir)
    return {"block": last_block, "hint": last_hint}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fix_prompt(last_stderr: str) -> str:
    return (
        "Your previous solution failed to compile/run. "
        "Here is the compiler error:\n\n"
        f"{last_stderr}\n\n"
        "Fix ONLY the error. Return ONLY the strict JSON with 'block' and 'full_file' keys."
    )

def _append_to_history(
    history: list[types.Content], role: str, text: str
) -> None:
    history.append(
        types.Content(role=role, parts=[types.Part(text=text)])
    )

def _build_hint(question_pack: dict, *, ok: bool) -> str:
    title = question_pack.get("title", "Unknown")
    cases = question_pack.get("test_cases", [])
    n = len(cases)
    status = "✓ Verified locally" if ok else "⚠ Unverified"
    return f"{status} | {title} | {n} test case{'s' if n != 1 else ''}"
