"""
watcher.py — Sotti
Monitors the screenshots folder, seals image batches after the settle period,
then routes to the AI pipeline:
  - Multiple images OR single image classified as NEW  → full OCR pipeline
  - Single image classified as DEBUG (and active question exists) → debug loop
"""

import asyncio
import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import settings

log = logging.getLogger(__name__)

WATCHED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


# ---------------------------------------------------------------------------
# Settle-period handler
# ---------------------------------------------------------------------------

class ScreenshotHandler(FileSystemEventHandler):
    """Collects new image files and seals a batch after settings.settle_seconds of quiet."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._loop = loop
        self._batch: list[str] = []
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def on_created(self, event) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in WATCHED_EXTENSIONS:
            return
        with self._lock:
            if str(path) not in self._batch:
                self._batch.append(str(path))
                log.info("Detected: %s  (batch size: %d)", path.name, len(self._batch))
        self._reset_timer()

    def _reset_timer(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(settings.settle_seconds, self._seal_batch)
            self._timer.daemon = True
            self._timer.start()

    def _seal_batch(self) -> None:
        with self._lock:
            if not self._batch:
                return
            image_paths = list(self._batch)
            self._batch.clear()
            self._timer = None

        count = len(image_paths)
        names = [Path(p).name for p in image_paths]
        log.info("Batch sealed: %d image(s): %s", count, names)

        asyncio.run_coroutine_threadsafe(
            self._process(image_paths), self._loop
        )

    async def _process(self, image_paths: list[str]) -> None:
        from .main import manager
        count = len(image_paths)
        await manager.broadcast({
            "type": "status",
            "message": f"Batch of {count} image{'s' if count != 1 else ''} received…",
        })
        await _process_pack(image_paths, self._loop)


# ---------------------------------------------------------------------------
# Async AI pipeline
# ---------------------------------------------------------------------------

async def _process_pack(image_paths: list[str], loop: asyncio.AbstractEventLoop) -> None:
    from .agent_manager import generate_and_verify_solution, classify_and_route
    from .main import manager

    count = len(image_paths)
    names = [Path(p).name for p in image_paths]
    log.info("▶ Pipeline START | images=%s", names)
    t_start = time.monotonic()

    def _sync_broadcast(payload: dict) -> None:
        if not loop.is_running():
            log.debug("_sync_broadcast: loop not running, skipping %s", payload.get("type"))
            return
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)

    try:
        current_loop = asyncio.get_running_loop()

        if count == 1:
            # Single image: orchestrator classifies (NEW vs DEBUG)
            runner = classify_and_route
        else:
            # Multiple images: always treat as a new question pack
            runner = generate_and_verify_solution

        solution = await current_loop.run_in_executor(
            None, runner, image_paths, _sync_broadcast
        )

        elapsed = time.monotonic() - t_start
        if solution:
            log.info("▶ Pipeline DONE | elapsed=%.1fs | verified=%s",
                     elapsed, solution.get("hint", "")[:40])
            await manager.broadcast({
                "type": "solution",
                "block": solution["block"],
                "hint": solution["hint"],
            })
        else:
            log.info("▶ Pipeline SKIP | elapsed=%.1fs (already solved)", elapsed)

        await manager.broadcast({"type": "status", "message": "Waiting for images…"})

    except Exception as exc:
        elapsed = time.monotonic() - t_start
        log.error("▶ Pipeline ERROR | elapsed=%.1fs | %s", elapsed, exc, exc_info=True)
        await manager.broadcast({"type": "error", "message": str(exc)})
        await manager.broadcast({"type": "status", "message": "Waiting for images…"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def start_watcher(loop: asyncio.AbstractEventLoop) -> Observer:
    watch_dir = settings.watch_dir
    if not watch_dir.exists():
        log.warning("Watch directory does not exist, creating: %s", watch_dir)
        watch_dir.mkdir(parents=True, exist_ok=True)

    handler = ScreenshotHandler(loop=loop)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()
    log.info(
        "Watching '%s' (settle: %ds | ocr=%s | orch=%s | code=%s)",
        watch_dir,
        settings.settle_seconds,
        settings.ocr_model,
        settings.orchestrator_model,
        settings.code_model,
    )
    return observer


if __name__ == "__main__":
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    observer = start_watcher(_loop)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
