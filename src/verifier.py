"""
verifier.py — Sotti
Compiles and runs a Java source file locally, optionally validating against test cases.
Uses `java SourceFile.java` (Java 11+ single-file launch) — no separate javac step.
"""

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 12


def verify_java_code(
    full_code: str,
    work_dir: Path | None = None,
    test_cases: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Write full_code to <work_dir>/Solution.java, run it with `java Solution.java`.

    If test_cases is provided (list of {input, expected_output}), each case is run
    separately with its stdin and stdout compared to expected_output.

    Returns:
        (True,  summary)  — all test cases passed (or no cases, exit 0)
        (False, details)  — compilation/runtime error or test mismatch
    """
    if work_dir is None:
        # Fallback to project-root tmp/
        work_dir = Path(__file__).resolve().parent.parent / "tmp"

    work_dir.mkdir(parents=True, exist_ok=True)
    solution_file = work_dir / "Solution.java"
    solution_file.write_text(full_code, encoding="utf-8")
    log.info("Verifier: wrote %d chars to %s", len(full_code), solution_file)

    # ── First pass: basic compilation check (no stdin) ──────────────────────
    try:
        probe = subprocess.run(
            ["java", str(solution_file)],
            input="",
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            cwd=str(work_dir),
            shell=False,
        )
    except subprocess.TimeoutExpired:
        msg = f"Compilation/run timed out after {_TIMEOUT_SECONDS}s."
        log.warning("Verifier: %s", msg)
        return False, msg
    except FileNotFoundError:
        msg = (
            "'java' executable not found. "
            "Make sure JDK is installed and java.exe is on your PATH."
        )
        log.error("Verifier: %s", msg)
        return False, msg

    if probe.returncode != 0:
        err = probe.stderr or probe.stdout or "(no output)"
        log.warning("Verifier: compile/run FAIL (exit %d)\n%s", probe.returncode, err[:500])
        return False, err

    # ── Second pass: run against each test case if provided ──────────────────
    if not test_cases:
        log.info("Verifier: PASS (no test cases, exit 0).")
        return True, probe.stdout or "(no output)"

    failures: list[str] = []
    for idx, tc in enumerate(test_cases, 1):
        stdin_data: str = str(tc.get("input", ""))
        expected: str = str(tc.get("expected_output", "")).strip()
        try:
            result = subprocess.run(
                ["java", str(solution_file)],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
                cwd=str(work_dir),
                shell=False,
            )
        except subprocess.TimeoutExpired:
            failures.append(f"TC{idx}: TIMEOUT after {_TIMEOUT_SECONDS}s")
            continue

        actual = (result.stdout or "").strip()
        if result.returncode != 0:
            failures.append(f"TC{idx}: RUNTIME ERROR\n{result.stderr[:300]}")
        elif actual != expected:
            failures.append(
                f"TC{idx}: MISMATCH\n  Input:    {stdin_data!r}\n"
                f"  Expected: {expected!r}\n  Got:      {actual!r}"
            )

    if failures:
        report = "\n\n".join(failures)
        log.warning("Verifier: %d/%d test(s) FAILED:\n%s", len(failures), len(test_cases), report[:600])
        return False, report

    log.info("Verifier: ALL %d test cases PASSED.", len(test_cases))
    return True, f"All {len(test_cases)} test cases passed."
