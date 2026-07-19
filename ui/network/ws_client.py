"""Runs a `websockets` connection on its own background thread and bridges
it to a plain, synchronous send()/recv_all() interface.

ui/main.py's render loop is synchronous (Img/Window's blocking-callback
model) and isn't going to become asyncio - so every bit of asyncio for a
networked game lives inside this one module. The render thread only ever
touches thread-safe primitives: a queue.Queue for inbound messages, and
asyncio.run_coroutine_threadsafe for outbound sends.
"""

import asyncio
import queue
import threading

import websockets

from net import protocol


class WsClient:
    """One WebSocket connection to a Kung Fu Chess server, decoded messages
    delivered through a thread-safe queue.

    The constructor blocks the calling thread until the connection is
    established (or raises on failure/timeout) - callers do their one-time
    "connect, then run the game loop" handshake the same way a local socket
    library would, without needing to know anything about asyncio.
    """

    def __init__(self, uri: str, connect_timeout: float = 5.0, on_event=None):
        """on_event(kind, payload), if given, is called for every bit of
        network activity this connection sees - "connect"/"send"/"recv"/
        "close" - so a caller can log it (see ui/main.py's wiring of
        persistence.event_log.EventLogWriter) without this module needing
        to know anything about logging itself. Called from whichever thread
        the activity happens on (the background asyncio thread for
        connect/recv/close, the caller's own thread for send)."""
        self._uri = uri
        self._on_event = on_event or (lambda kind, payload: None)
        self._inbound: queue.Queue = queue.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connection = None
        self._connect_error: Exception | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        if not self._ready.wait(timeout=connect_timeout):
            raise TimeoutError(f"Timed out connecting to {uri}")
        if self._connect_error is not None:
            raise self._connect_error

    def send(self, message: dict) -> None:
        """Fire-and-forget: hand message to the connection's own event loop
        thread for delivery. Safe to call from the render thread."""
        self._on_event("send", {"message": message})
        asyncio.run_coroutine_threadsafe(self._connection.send(protocol.encode(message)), self._loop)

    def recv_all(self) -> list:
        """Drain every message received since the last call, in arrival order."""
        messages = []
        while True:
            try:
                messages.append(self._inbound.get_nowait())
            except queue.Empty:
                break
        return messages

    def recv_one_blocking(self, timeout: float = 5.0) -> dict:
        """Block the calling thread for at most timeout seconds waiting for
        the next message - used once, right after connecting, to receive
        game_start before the render loop (which never blocks) can start."""
        return self._inbound.get(timeout=timeout)

    def close(self) -> None:
        if self._loop is not None and self._connection is not None:
            asyncio.run_coroutine_threadsafe(self._connection.close(), self._loop)
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            asyncio.run(self._main())
        except Exception as exc:  # surfaced to the connecting thread via _connect_error
            self._connect_error = exc
            self._ready.set()

    async def _main(self) -> None:
        self._loop = asyncio.get_running_loop()
        async with websockets.connect(self._uri) as connection:
            self._connection = connection
            self._ready.set()
            self._on_event("connect", {"uri": self._uri})
            try:
                async for text in connection:
                    message = protocol.decode(text)
                    self._on_event("recv", {"message": message})
                    self._inbound.put(message)
            finally:
                self._on_event("close", {})
