"""
state.py — Sotti Phase 6
Global in-memory application state. All modules import APP_STATE directly;
the dict is mutated in-place so references stay valid across imports.
"""

from typing import Any

APP_STATE: dict[str, Any] = {
    "current": None,           # Latest verified solution block (str | None)
    "solved_questions": {},    # Map of title -> {"block": str, "stub_code": str}
}
