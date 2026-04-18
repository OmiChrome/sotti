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

from .watcher import start_watcher
from .state import APP_STATE

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

app = FastAPI(title="Sotti", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


# ---------------------------------------------------------------------------
# REST root — serves index.html
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import FileResponse
    return FileResponse(str(STATIC_DIR / "index.html"))


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

        # Immediately hydrate the new client with the current global state.
        try:
            await ws.send_json({"type": "init", "state": APP_STATE})
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


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            # Server is push-only; keep the connection alive.
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Startup / shutdown lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    loop = asyncio.get_running_loop()
    observer = start_watcher(loop)
    app.state.observer = observer

    local_ip = get_local_ip()
    print()
    print("  ┌─────────────────────────────────────────────────┐")
    print(f"  │  Sotti is running                               │")
    print(f"  │  Local  → http://{local_ip}:8000{' ' * (28 - len(local_ip))}│")
    print(f"  │  Vercel → https://sotti.vercel.app              │")
    print("  │  (Vercel requires WebSocket override)           │")
    print("  └─────────────────────────────────────────────────┘")
    print()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    obs = getattr(app.state, "observer", None)
    if obs:
        obs.stop()
        obs.join()
        log.info("Watcher stopped.")


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
