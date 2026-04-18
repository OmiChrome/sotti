"""
startup_checks.py — Sotti
Runs fast parallel sanity checks at app startup to catch misconfiguration early.

Strategy (minimal API usage):
  • watch_dir  — pure local stat, instant.
  • API key    — validated implicitly by calling client.models.list() once.
  • Both models — checked against the list returned by that same single call.
All three run concurrently; hard timeout of 5 seconds so startup is never blocked.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_G = "\033[92m"   # green
_R = "\033[91m"   # red
_Y = "\033[93m"   # yellow
_B = "\033[1m"    # bold
_D = "\033[0m"    # reset


def _ok(msg: str) -> str:
    return f"  {_G}✓{_D}  {msg}"


def _fail(msg: str) -> str:
    return f"  {_R}✗{_D}  {msg}"


def _warn(msg: str) -> str:
    return f"  {_Y}⚠{_D}  {msg}"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

async def _check_watch_dir(watch_dir: Path) -> tuple[bool, str]:
    """Local filesystem check — no I/O wait needed."""
    if not watch_dir.exists():
        return False, f"WATCH_DIR not found       → {watch_dir}"
    if not watch_dir.is_dir():
        return False, f"WATCH_DIR is not a dir    → {watch_dir}"
    return True, f"WATCH_DIR                 → {watch_dir}"


async def _check_api_and_models(
    api_key: str,
    model_a: str,
    model_b: str,
) -> list[tuple[bool, str]]:
    """
    One models.list() call validates the API key AND both model names.
    Runs in a thread executor so it doesn't block the event loop.
    Returns a flat list of (ok, message) tuples:
      [0] API key result
      [1] orchestrator_model result
      [2] sub_agent_model result  (may be merged with [1] if same model)
    """
    from google import genai

    def _sync() -> tuple[bool, set[str], str]:
        """Blocking work: create client and fetch model list."""
        client = genai.Client(api_key=api_key)
        # models.list() raises immediately if the key is bad (401/403).
        raw = list(client.models.list())
        # Names come back as "models/gemma-4-31b-it" — normalise to bare ID.
        available = set()
        for m in raw:
            name: str = m.name  # e.g. "models/gemma-4-31b-it"
            available.add(name)
            available.add(name.split("/")[-1])   # bare ID
        return True, available, "API key is valid"

    loop = asyncio.get_running_loop()
    try:
        key_ok, available, key_msg = await asyncio.wait_for(
            loop.run_in_executor(None, _sync),
            timeout=4.5,
        )
    except asyncio.TimeoutError:
        return [
            (False, "API key check timed out (>4.5 s)"),
            (False, f"Model '{model_a}': skipped (timeout)"),
            (False, f"Model '{model_b}': skipped (timeout)"),
        ]
    except Exception as exc:
        err = str(exc)
        if any(code in err for code in ("401", "403", "API_KEY_INVALID", "INVALID_ARGUMENT")):
            reason = "invalid or unauthorised key"
        else:
            reason = err[:100]
        return [
            (False, f"API key is INVALID         → {reason}"),
            (False, f"Model '{model_a}': skipped (API error)"),
            (False, f"Model '{model_b}': skipped (API error)"),
        ]

    results: list[tuple[bool, str]] = [(True, f"API key                   → {key_msg}")]

    def _model_result(model: str) -> tuple[bool, str]:
        if model in available:
            return True, f"Model '{model}' is available"
        return False, f"Model '{model}' NOT found in available models"

    # Deduplicate if both models are the same
    if model_a == model_b:
        ok, msg = _model_result(model_a)
        results.append((ok, f"{msg} (orchestrator + sub-agent)"))
    else:
        results.append(_model_result(model_a))
        results.append(_model_result(model_b))

    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_startup_checks(settings: "Settings") -> bool:
    """
    Runs all checks concurrently with a 5-second hard timeout.
    Prints a coloured checklist to stdout.
    Returns True if all critical checks passed (caller can decide whether to abort).
    """
    print(f"\n  {_B}── Startup Checks {'─' * 31}{_D}")

    try:
        dir_result, api_results = await asyncio.wait_for(
            asyncio.gather(
                _check_watch_dir(settings.watch_dir),
                _check_api_and_models(
                    settings.gemini_api_key,
                    settings.orchestrator_model,
                    settings.sub_agent_model,
                ),
                return_exceptions=True,
            ),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        print(_warn("Startup checks exceeded 5 s — proceeding anyway."))
        print()
        return True  # never block startup on a slow network

    all_ok = True

    # --- watch_dir ---
    if isinstance(dir_result, Exception):
        print(_fail(f"WATCH_DIR check error: {dir_result}"))
        all_ok = False
    else:
        ok, msg = dir_result
        print(_ok(msg) if ok else _fail(msg))
        all_ok &= ok

    # --- API key + models ---
    if isinstance(api_results, Exception):
        print(_fail(f"API/model check error: {api_results}"))
        all_ok = False
    else:
        for ok, msg in api_results:
            print(_ok(msg) if ok else _fail(msg))
            all_ok &= ok

    print(f"  {'─' * 49}")
    if all_ok:
        print(f"  {_G}{_B}All checks passed.{_D}")
    else:
        print(f"  {_R}{_B}One or more checks failed — review .env before use.{_D}")
    print()

    return all_ok
