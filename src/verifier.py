"""
verifier.py — Sotti Phase 3
Compiles and runs a Java source file locally to verify correctness
before the solution is broadcast to the frontend.
"""

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Resolve tmp/ relative to the project root (two levels up from src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TMP_DIR = _PROJECT_ROOT / "tmp"
_SOLUTION_FILE = _TMP_DIR / "Solution.java"

_TIMEOUT_SECONDS = 10


def verify_java_code(full_code: str) -> tuple[bool, str]:
    """
    Write *full_code* to tmp/Solution.java, execute it with `java`, and
    return (success, output).

    Returns:
        (True,  stdout)   if compilation+execution succeed (exit code 0).
        (False, stderr)   if the JVM reports an error or times out.
    """
    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    _SOLUTION_FILE.write_text(full_code, encoding="utf-8")
    log.info("Verifier: wrote %d chars to %s", len(full_code), _SOLUTION_FILE)

    try:
        result = subprocess.run(
            ["java", str(_SOLUTION_FILE)],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            # Ensure we run in a plain CMD-compatible environment on Windows.
            shell=False,
        )
    except subprocess.TimeoutExpired:
        msg = f"Verification timed out after {_TIMEOUT_SECONDS}s."
        log.warning("Verifier: %s", msg)
        return False, msg
    except FileNotFoundError:
        msg = (
            "'java' executable not found. "
            "Make sure JDK is installed and java.exe is on your PATH."
        )
        log.error("Verifier: %s", msg)
        return False, msg

    if result.returncode == 0:
        log.info("Verifier: PASS (exit 0).")
        return True, result.stdout
    else:
        log.warning("Verifier: FAIL (exit %d).\n%s", result.returncode, result.stderr[:500])
        return False, result.stderr
