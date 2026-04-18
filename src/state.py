"""
state.py — Sotti Phase 6
Global in-memory application state. All modules import APP_STATE directly;
the dict is mutated in-place so references stay valid across imports.
"""

from typing import Any
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / "state.json"

def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current": None,
        "solved_questions": {},
    }

APP_STATE: dict[str, Any] = load_state()

def save_state() -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(APP_STATE, f, indent=2)
