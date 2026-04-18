"""
agent_manager.py — Sotti Phase 6
Phase 2 & 3: Extracts question-pack and generates Java solution in one go.
Phase 6: Includes OCR fallback, smart question tracking by title to save compute,
         and proactive status broadcasting for the UI ticker.
"""

import json
import logging
from pathlib import Path
from typing import Callable, Coroutine, Any

from google import genai
from google.genai import types
from PIL import Image

from .config import settings
from . import verifier
from .state import APP_STATE

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

def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
        log.info("Gemini client initialised.")
    return _client

# ---------------------------------------------------------------------------
# Broadcast helper type
# ---------------------------------------------------------------------------

BroadcastFn = Callable[[dict], Coroutine[Any, Any, None]]


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
        """Fire-and-forget: schedule a broadcast on the asyncio loop."""
        if broadcast is None:
            return
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(broadcast(payload), loop)
        except Exception as exc:
            log.warning("Broadcast emit failed: %s", exc)

    _emit({"type": "status", "message": "Doing OCR..."})

    if not image_paths:
        raise ValueError("image_paths must not be empty")

    client = _get_client()

    parts: list = []
    for raw_path in image_paths:
        path = Path(raw_path)
        if not path.exists():
            log.warning("Image not found, skipping: %s", path)
            continue
        parts.append(Image.open(path))

    if not parts:
        raise RuntimeError("No valid images could be loaded from the batch.")

    parts.append(
        "Extract the question pack from the screenshot(s) above. "
        "Return ONLY the JSON object — no markdown fences, no extra text."
    )

    log.info("Sending %d image(s) for OCR...", len(image_paths))

    try:
        response = client.models.generate_content(
            model=settings.orchestrator_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=_ORCHESTRATOR_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
    except Exception as e:
        log.warning("OCR failed with %s: %s. Using fallback %s...", 
                    settings.orchestrator_model, e, settings.sub_agent_model)
        _emit({"type": "status", "message": f"OCR fallback, using {settings.sub_agent_model}..."})
        response = client.models.generate_content(
            model=settings.sub_agent_model,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=_ORCHESTRATOR_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

    raw_text: str = response.text or ""

    try:
        question_pack = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OCR Model returned invalid JSON: {exc}\n{raw_text[:200]}") from exc

    title = question_pack.get("title", "")
    stub_code = question_pack.get("stub_code", "")

    # Check solved_questions state
    if title and title in APP_STATE["solved_questions"]:
        solved_info = APP_STATE["solved_questions"][title]
        # if the stub code is the same, abort to save compute
        if solved_info.get("stub_code") == stub_code:
            _emit({"type": "status", "message": "Question already solved."})
            log.info("Question '%s' already solved and stub unchanged. Aborting.", title)
            return None

    _emit({"type": "status", "message": "Generating code..."})

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
        log.info("Attempt %d/%d: generating solution...", attempt, _MAX_RETRIES)

        current_contents: list = list(history) + [
            types.Content(
                role="user",
                parts=[types.Part(text=user_prompt if attempt == 1 else _fix_prompt(last_stderr=last_hint))],
            )
        ]

        response = client.models.generate_content(
            model=settings.sub_agent_model,
            contents=current_contents,
            config=types.GenerateContentConfig(
                system_instruction=_SUB_AGENT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        raw_text: str = response.text or ""

        try:
            solution = json.loads(raw_text)
            block: str = solution.get("block", "")
            full_file: str = solution.get("full_file", "")
        except json.JSONDecodeError as exc:
            log.warning("Sub-agent returned non-JSON on attempt %d: %s", attempt, exc)
            last_block = raw_text
            last_hint = f"JSON parse error: {exc}"
            _append_to_history(history, role="model", text=raw_text)
            _append_to_history(history, role="user", text=_fix_prompt(last_stderr=last_hint))
            continue

        last_block = block

        log.info("Attempt %d/%d: compiling...", attempt, _MAX_RETRIES)

        if full_file:
            ok, output = verifier.verify_java_code(full_file)
        else:
            ok, output = False, "full_file was empty; cannot verify."

        if ok:
            log.info("Verification PASSED on attempt %d.", attempt)
            last_hint = _build_hint(question_pack, ok=True)
            verified = True
            break
        else:
            err_snippet = output[:300]
            log.warning("Verification FAILED on attempt %d: %s", attempt, err_snippet)
            last_hint = output

            _append_to_history(history, role="model", text=raw_text)
            _append_to_history(history, role="user", text=_fix_prompt(last_stderr=output))

    if not verified:
        log.warning("All %d attempts failed. Returning best-effort solution.", _MAX_RETRIES)
        last_hint = "WARNING: Failed local verification — " + last_hint[:200]
    else:
        APP_STATE["current"] = last_block
        if title:
            APP_STATE["solved_questions"][title] = {
                "block": last_block,
                "stub_code": stub_code
            }

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
