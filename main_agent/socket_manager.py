import asyncio
from typing import Any, Optional

import socketio

# Single Socket.IO server instance shared across the application.
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# Event loop that drives the Socket.IO server; populated on first connection.
_socket_loop: Optional[asyncio.AbstractEventLoop] = None


def create_socket_app(asgi_app: Any) -> socketio.ASGIApp:
    """Wrap the FastAPI app with Socket.IO support."""
    return socketio.ASGIApp(sio, other_asgi_app=asgi_app)


def emit_event(event: str, data: Any, *, room: Optional[str] = None) -> None:
    """Schedule an event emission if the Socket.IO server is ready."""
    if not _socket_loop or not _socket_loop.is_running():
        print("Socket.IO loop is not ready; skipping emit")
        return

    async def _emit() -> None:
        await sio.emit(event, data, room=room)

    future = asyncio.run_coroutine_threadsafe(_emit(), _socket_loop)
    future.add_done_callback(_log_emit_result)


def _log_emit_result(future: asyncio.Future) -> None:
    if future.cancelled():
        return
    exc = future.exception()
    if exc:
        print(f"Socket.IO emit failed: {exc}")


@sio.event
async def connect(sid: str, environ: Any) -> None:
    global _socket_loop
    _socket_loop = asyncio.get_running_loop()
    print(f"Socket.IO connected: {sid}")


@sio.event
async def join(sid: str, data: Any) -> None:
    session_id: Optional[str] = None
    if isinstance(data, dict):
        session_id = data.get("sessionId") or data.get("session_id")
    if not session_id:
        print(f"Socket.IO join missing sessionId for sid={sid}")
        return

    await sio.enter_room(sid, session_id)
    print(f"Socket.IO sid={sid} joined session {session_id}")


@sio.event
async def disconnect(sid: str) -> None:
    print(f"Socket.IO disconnected: {sid}")
