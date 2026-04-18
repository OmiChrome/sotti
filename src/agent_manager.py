"""
agent_manager.py — Sotti Phase 2
Extracts a structured JSON question-pack from a batch of screenshot images
using the Gemini API (google-genai SDK).
"""

import json
import logging
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from .config import settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
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

# ---------------------------------------------------------------------------
# Lazy-initialised client
# ---------------------------------------------------------------------------

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
        log.info("Gemini client initialised (model: %s)", settings.orchestrator_model)
    return _client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_question_pack(image_paths: list[str]) -> str:
    """
    Send *image_paths* to the Gemini orchestrator model and return the
    extracted question-pack as a JSON string.

    Raises:
        RuntimeError: if the API call fails or returns non-JSON.
    """
    if not image_paths:
        raise ValueError("image_paths must not be empty")

    client = _get_client()

    # Build the content parts: one PIL Image per screenshot.
    parts: list = []
    for raw_path in image_paths:
        path = Path(raw_path)
        if not path.exists():
            log.warning("Image not found, skipping: %s", path)
            continue
        img = Image.open(path)
        parts.append(img)
        log.info("Loaded image: %s (%s, %s)", path.name, img.size, img.mode)

    if not parts:
        raise RuntimeError("No valid images could be loaded from the batch.")

    parts.append(
        "Extract the question pack from the screenshot(s) above. "
        "Return ONLY the JSON object — no markdown fences, no extra text."
    )

    log.info("Sending %d image(s) to %s …", len(image_paths), settings.orchestrator_model)

    response = client.models.generate_content(
        model=settings.orchestrator_model,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.1,   # Low temp for deterministic OCR-style extraction
        ),
    )

    raw_text: str = response.text or ""

    # Validate: make sure it's parseable JSON before returning.
    try:
        json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error("Model returned non-JSON: %s", raw_text[:300])
        raise RuntimeError(f"Model returned invalid JSON: {exc}") from exc

    log.info("Extraction complete (%d chars).", len(raw_text))
    return raw_text
