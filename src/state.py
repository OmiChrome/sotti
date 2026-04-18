"""
state.py — Sotti
Shared in-memory state + simple JSON persistence.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "state.json"

APP_STATE: dict = {
    "current": "",                 # Last code block shown in frontend
    "current_question_dir": None,  # Absolute path to active question directory
    "current_question_title": None,# Human-readable title of active question
    "solved_questions": {},        # title → {block, stub_code}
}


def save_state() -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps(APP_STATE, indent=2, default=str), encoding="utf-8"
        )
    except Exception as exc:
        log.warning("Failed to persist state: %s", exc)


def load_state() -> None:
    if not _STATE_FILE.exists():
        return
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        APP_STATE.update(data)
        log.info("State restored from %s", _STATE_FILE)
    except Exception as exc:
        log.warning("Failed to load state: %s", exc)
