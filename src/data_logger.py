"""
data_logger.py — Sotti
Persists every model request/response to disk under data/sessions/<timestamp>_<title>/
so you can review exactly what was sent and received for each question pack.

Structure per session:
  data/sessions/20260419_023449_My-Question-Title/
    00_ocr_images.txt            — list of image paths fed to OCR
    01_ocr_response.json         — raw text + parsed question_pack
    02_gen_attempt1_request.json — prompt + history sent to code-gen model
    02_gen_attempt1_response.json — raw text + parsed solution
    02_gen_attempt1_verify.txt   — compiler stdout/stderr
    ...
    final_solution.java          — the block returned to the browser
    session_summary.json         — one-stop overview
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# Project-root-relative: src/../data/sessions/
_SESSIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"


def _slug(text: str, max_len: int = 40) -> str:
    """Turn arbitrary text into a safe directory-name fragment."""
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    return text[:max_len]


class DataLogger:
    """
    Create one DataLogger per pipeline run (one sealed image batch).
    All write operations are synchronous and intentionally simple —
    they run inside the executor thread alongside the AI calls.
    """

    def __init__(self, title: str = "unknown") -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slug(title) or "session"
        self.session_dir: Path = _SESSIONS_DIR / f"{ts}_{slug}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._summary: dict = {
            "session": self.session_dir.name,
            "started_at": datetime.now().isoformat(),
            "title": title,
            "ocr_model": None,
            "gen_model": None,
            "attempts": [],
            "verified": False,
            "final_block_chars": 0,
        }
        log.debug("DataLogger session: %s", self.session_dir)

    # ------------------------------------------------------------------
    # OCR stage
    # ------------------------------------------------------------------

    def log_ocr_images(self, image_paths: list[str]) -> None:
        out = "\n".join(image_paths)
        self._write("00_ocr_images.txt", out)

    def log_ocr_response(self, model: str, raw_text: str, question_pack: dict) -> None:
        self._summary["ocr_model"] = model
        self._write_json("01_ocr_response.json", {
            "model": model,
            "raw_text": raw_text,
            "question_pack": question_pack,
        })

    # ------------------------------------------------------------------
    # Code-gen stage
    # ------------------------------------------------------------------

    def log_gen_request(self, attempt: int, model: str, contents_snapshot: list[str]) -> None:
        """contents_snapshot: human-readable text representations of each Content."""
        self._summary["gen_model"] = model
        self._write_json(f"0{attempt + 1}_gen_attempt{attempt}_request.json", {
            "attempt": attempt,
            "model": model,
            "contents": contents_snapshot,
        })

    def log_gen_response(self, attempt: int, raw_text: str, parsed: dict | None) -> None:
        self._write_json(f"0{attempt + 1}_gen_attempt{attempt}_response.json", {
            "attempt": attempt,
            "raw_text": raw_text,
            "parsed": parsed,
        })

    def log_verify_result(self, attempt: int, ok: bool, output: str) -> None:
        status = "PASS" if ok else "FAIL"
        self._write(
            f"0{attempt + 1}_gen_attempt{attempt}_verify.txt",
            f"STATUS: {status}\n\n{output}",
        )
        self._summary["attempts"].append({
            "attempt": attempt,
            "verified": ok,
            "compiler_output_chars": len(output),
        })

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------

    def log_final(self, block: str, hint: str, verified: bool) -> None:
        self._summary["verified"] = verified
        self._summary["final_block_chars"] = len(block)
        self._summary["hint"] = hint
        self._summary["finished_at"] = datetime.now().isoformat()
        # Save the actual Java block as a .java file for easy reading
        self._write("final_solution.java", block)
        self._write_json("session_summary.json", self._summary)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write(self, filename: str, content: str) -> None:
        path = self.session_dir / filename
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as exc:
            log.warning("DataLogger write failed (%s): %s", filename, exc)

    def _write_json(self, filename: str, obj: dict) -> None:
        self._write(filename, json.dumps(obj, indent=2, ensure_ascii=False))
