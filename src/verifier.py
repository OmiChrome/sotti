"""
verifier.py — Sotti
Runs Java code locally using `java SourceFile.java` (Java 11+ single-file launcher).
NO javac. Validates against test cases extracted from question.md.
"""

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


def verify_java_code(
    full_code: str,
    work_dir: Path | None = None,
    test_cases: list[dict] | None = None,
) -> tuple[bool, str]:
    """
    Write full_code to <work_dir>/full_solution.java, run with `java full_solution.java`.

    If test_cases provided: each case is fed as stdin, stdout compared to expected_output.

    Returns:
        (True,  summary)  — all test cases passed (or exit 0 with no cases)
        (False, details)  — error details for the code model to fix
    """
    if work_dir is None:
        work_dir = Path(__file__).resolve().parent.parent / "tmp"

    work_dir.mkdir(parents=True, exist_ok=True)
    solution_file = work_dir / "full_solution.java"
    solution_file.write_text(full_code, encoding="utf-8")
    log.info("Verifier: wrote %d chars → %s", len(full_code), solution_file)

    # ── Probe run: syntax/compile check (empty stdin) ────────────────────────
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
        return False, f"Timed out after {_TIMEOUT_SECONDS}s on probe run."
    except FileNotFoundError:
        return False, (
            "'java' not found on PATH. Install JDK 11+ and ensure java.exe is on PATH."
        )

    if probe.returncode != 0:
        err = (probe.stderr or probe.stdout or "(no output)").strip()
        log.warning("Verifier probe FAIL (exit %d): %s", probe.returncode, err[:300])
        return False, err

    # ── Test case runs ────────────────────────────────────────────────────────
    if not test_cases:
        log.info("Verifier: PASS (no test cases).")
        return True, probe.stdout.strip() or "(no output)"

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
            failures.append(f"TC{idx}: RUNTIME ERROR\n{(result.stderr or result.stdout or '').strip()[:300]}")
        elif actual != expected:
            failures.append(
                f"TC{idx}: WRONG OUTPUT\n"
                f"  stdin:    {stdin_data!r}\n"
                f"  expected: {expected!r}\n"
                f"  got:      {actual!r}"
            )

    if failures:
        report = "\n\n".join(failures)
        log.warning("Verifier: %d/%d FAILED", len(failures), len(test_cases))
        return False, report

    log.info("Verifier: ALL %d test cases PASSED.", len(test_cases))
    return True, f"All {len(test_cases)} test case(s) passed."
