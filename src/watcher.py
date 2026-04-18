"""
watcher.py — Sotti Phase 6
Monitors the configured screenshots folder, batches images after the settle
period, then hands the sealed pack to the AI agent manager.
Broadly emits status updates for the UI ticker.
"""

import asyncio
import logging
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger(__name__)

WATCHED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


# ---------------------------------------------------------------------------
# Settle-period handler
# ---------------------------------------------------------------------------

class ScreenshotHandler(FileSystemEventHandler):
    """Collects new image files and seals a batch after settings.settle_seconds of quiet."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._loop = loop          # The event loop owned by uvicorn/asyncio
        self._batch: list[str] = []  # Full file paths
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    # ------------------------------------------------------------------
    # watchdog callback (runs in watchdog's background thread)
    # ------------------------------------------------------------------

    def on_created(self, event) -> None:  # type: ignore[override]
        if event.is_directory:
            return

        path = Path(event.src_path)
        if path.suffix.lower() not in WATCHED_EXTENSIONS:
            return

        with self._lock:
            if str(path) not in self._batch:
                self._batch.append(str(path))
                log.info(
                    "Detected: %s  (batch size: %d)",
                    path.name,
                    len(self._batch),
                )

        self._reset_timer()

    # ------------------------------------------------------------------
    # Timer management (thread-safe)
    # ------------------------------------------------------------------

    def _reset_timer(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                settings.settle_seconds, self._seal_batch
            )
            self._timer.daemon = True
            self._timer.start()

    def _seal_batch(self) -> None:
        with self._lock:
            if not self._batch:
                return
            count = len(self._batch)
            image_paths = list(self._batch)
            self._batch.clear()
            self._timer = None

        names = [Path(p).name for p in image_paths]
        log.info(
            "Question Pack sealed with %d image%s: %s",
            count,
            "s" if count != 1 else "",
            names,
        )

        msg = f"Sending batch of {count} image{'s' if count != 1 else ''}..."

        # Schedule the async pipeline on the uvicorn event loop.
        asyncio.run_coroutine_threadsafe(
            self._broadcast_and_process(msg, image_paths), self._loop
        )

    async def _broadcast_and_process(self, msg: str, image_paths: list[str]) -> None:
        from .main import manager
        await manager.broadcast({"type": "status", "message": msg})
        await _process_pack(image_paths)


# ---------------------------------------------------------------------------
# Async AI pipeline (runs on the asyncio event loop)
# ---------------------------------------------------------------------------

async def _process_pack(image_paths: list[str]) -> None:
    """
    Passes paths to generate_and_verify_solution directly, avoiding split phases.
    """
    from .agent_manager import generate_and_verify_solution
    from .main import manager

    log.info("Processing pack: %s", [Path(p).name for p in image_paths])

    try:
        loop = asyncio.get_running_loop()

        solution = await loop.run_in_executor(
            None,
            generate_and_verify_solution,
            image_paths,
            manager.broadcast,   # Pass the async broadcast fn for live status updates
        )

        if solution:
            await manager.broadcast({
                "type": "solution",
                "block": solution["block"],
                "hint": solution["hint"],
            })

        await manager.broadcast({"type": "status", "message": "Waiting for images..."})

    except Exception as exc:
        log.error("Pipeline error: %s", exc, exc_info=True)
        await manager.broadcast({"type": "error", "message": str(exc)})
        await manager.broadcast({"type": "status", "message": "Waiting for images..."})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def start_watcher(loop: asyncio.AbstractEventLoop) -> Observer:
    """Start the watchdog observer and return it (non-blocking)."""
    watch_dir = settings.watch_dir
    if not watch_dir.exists():
        log.warning("Watch directory does not exist, creating: %s", watch_dir)
        watch_dir.mkdir(parents=True, exist_ok=True)

    handler = ScreenshotHandler(loop=loop)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()
    log.info(
        "Watching '%s' (settle: %ds, model: %s)",
        watch_dir,
        settings.settle_seconds,
        settings.orchestrator_model,
    )
    return observer


if __name__ == "__main__":
    # Standalone test mode — runs without FastAPI
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    observer = start_watcher(_loop)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
