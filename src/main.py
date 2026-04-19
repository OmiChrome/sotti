"""
main.py — Sotti Phase 5
FastAPI server: serves the static frontend, hosts the WebSocket push
channel, and wires the watcher daemon into the asyncio event loop.
"""

import asyncio
import logging
import socket
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .watcher import start_watcher
from .state import APP_STATE, load_state
from .config import settings
from .startup_checks import run_startup_checks

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5s] %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet down uvicorn's own access logging a tiny bit so our logs stand out
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App + static files
# ---------------------------------------------------------------------------

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # --- Restore persisted state ---
    load_state()

    # --- Sanity checks (parallel, ≤5 s) ---
    await run_startup_checks(settings)

    loop = asyncio.get_running_loop()
    observer = start_watcher(loop)
    app.state.observer = observer

    local_ip = get_local_ip()
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │  Sotti is running                               │")
    print(f"  │  Localhost → http://127.0.0.1:{settings.server_port:<13} │")
    print(f"  │  Network   → http://{local_ip}:{settings.server_port:<13} │")
    print("  │  Vercel    → https://sotti.vercel.app           │")
    print("  │                                                 │")
    print("  │  (To access from phone over Network, ensure     │")
    print("  │  port is allowed in Windows Firewall)           │")
    print("  └─────────────────────────────────────────────────┘")
    print()
    yield
    obs = getattr(app.state, "observer", None)
    if obs:
        obs.stop()
        obs.join()
        log.info("Watcher stopped.")

app = FastAPI(title="Sotti", version="0.1.0", lifespan=app_lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


# ---------------------------------------------------------------------------
# REST root — serves index.html
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import FileResponse
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/solution")
async def get_solution():
    """Return current solution.md content if available for the active question."""
    from fastapi.responses import JSONResponse
    q_dir_str = APP_STATE.get("current_question_dir")
    if not q_dir_str:
        return JSONResponse({"available": False, "block": ""})
    q_dir = Path(q_dir_str)
    solution_path = q_dir / "solution.md"
    if not solution_path.exists():
        return JSONResponse({"available": False, "block": ""})
    import re as _re
    content = solution_path.read_text(encoding="utf-8")
    # Extract java block from solution.md
    m = _re.search(r"```java\n(.*?)```", content, _re.DOTALL)
    block = m.group(1).strip() if m else content
    title = APP_STATE.get("current_question_title", "")
    return JSONResponse({"available": True, "block": block, "title": title})


# ---------------------------------------------------------------------------
# WebSocket — code push channel
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts typed dicts to all."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        log.info("Frontend connected  (total: %d)", len(self._connections))

        # Immediately hydrate the new client with current global state.
        try:
            await ws.send_json({"type": "init", "state": {
                "current": APP_STATE.get("current", ""),
                "current_question_title": APP_STATE.get("current_question_title"),
                "current_question_dir": APP_STATE.get("current_question_dir"),
            }})
        except Exception as exc:
            log.warning("Could not send init state to new client: %s", exc)

    def disconnect(self, ws: WebSocket) -> None:
        try:
            self._connections.remove(ws)
        except ValueError:
            pass
        log.info("Frontend disconnected (total: %d)", len(self._connections))

    async def broadcast(self, payload: dict) -> None:
        """Broadcast a typed dict to every connected client."""
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self._connections.remove(ws)
            except ValueError:
                pass


manager = ConnectionManager()


_WS_PING_INTERVAL = 20  # seconds — keeps connection alive through proxies & mobile networks


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)

    async def _ping_loop() -> None:
        """Send a ping frame every N seconds to prevent idle timeout drops."""
        while True:
            await asyncio.sleep(_WS_PING_INTERVAL)
            try:
                await ws.send_json({"type": "ping"})
            except Exception:
                break  # connection gone; let the main loop handle cleanup

    ping_task = asyncio.create_task(_ping_loop())
    try:
        while True:
            # Server is push-only; drain any client frames (pong, etc.)
            await ws.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        ping_task.cancel()
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", 
        host=settings.server_host, 
        port=settings.server_port, 
        reload=True
    )
