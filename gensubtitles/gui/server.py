"""gensubtitles.gui.server
~~~~~~~~~~~~~~~~~~~~~~~~~~
Server lifecycle management for the GenSubtitles desktop UI.

Extracted from gui/main.py to give the server startup/teardown concern
its own module, keeping gui/main.py focused on widget management.

Public API
----------
start(on_progress, on_ready, on_failed, is_closing)
              — launch uvicorn in a daemon thread and poll until ready,
                firing callbacks on the polling thread (caller must
                marshal to Tkinter main thread via ``self.after(0, ...)``)
stop()        — request the running server to shut down
SERVER_PORT   — TCP port the server listens on (8000)
BASE_URL      — HTTP base URL for the local server
"""
from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server address constants
# ---------------------------------------------------------------------------

SERVER_PORT: int = 8000
BASE_URL: str = f"http://127.0.0.1:{SERVER_PORT}"

_SERVER_BIND_TIMEOUT: int = 30  # seconds to wait for Uvicorn to bind

# ---------------------------------------------------------------------------
# Module-level server state
# ---------------------------------------------------------------------------

_server = None  # uvicorn.Server instance — set inside start()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def start(
    on_progress: Callable[[str, int], None],
    on_ready: Callable[[], None],
    on_failed: Callable[[str], None],
    is_closing: Callable[[], bool],
) -> None:
    """Start the uvicorn server and poll until the model is ready.

    All three callbacks are called directly on the polling thread.
    Callers that need to update Tkinter widgets MUST wrap them, e.g.::

        server.start(
            on_progress=lambda m, p: self.after(0, lambda: self._apply_startup_progress(m, p)),
            on_ready=lambda: self.after(0, self._on_server_ready),
            on_failed=lambda d: self.after(0, lambda: self._on_server_failed(d)),
            is_closing=lambda: self._closing,
        )
    """
    import uvicorn  # noqa: PLC0415

    global _server  # noqa: PLW0603

    def _run() -> None:
        global _server  # noqa: PLW0603
        try:
            config = uvicorn.Config(
                "gensubtitles.api.main:app",
                host="127.0.0.1",
                port=SERVER_PORT,
                log_level="error",
            )
            _server = uvicorn.Server(config)
            _server.run()
        except OSError as exc:
            logger.error("GUI server failed to start: %s", exc)

    def _wait_for_server() -> None:
        import requests as req  # noqa: PLC0415

        # Phase 1: wait until the HTTP server binds and /status responds
        deadline = time.monotonic() + _SERVER_BIND_TIMEOUT
        while not is_closing():
            if not thread.is_alive():
                if not is_closing():
                    on_failed(
                        f"Server process exited unexpectedly. Check port {SERVER_PORT}.",
                    )
                return
            if time.monotonic() > deadline:
                if not is_closing():
                    on_failed(
                        "Server did not start within "
                        f"{_SERVER_BIND_TIMEOUT}s. Check port {SERVER_PORT}.",
                    )
                return
            time.sleep(1)
            try:
                req.get(f"{BASE_URL}/status", timeout=1)
                break  # server is up
            except Exception:  # noqa: BLE001
                continue

        # Phase 2: poll /status until model is ready, updating the GUI label
        while not is_closing():
            if not thread.is_alive():
                if not is_closing():
                    on_failed(
                        "Server process exited unexpectedly during model loading.",
                    )
                return
            time.sleep(1)
            try:
                resp = req.get(f"{BASE_URL}/status", timeout=2)
                data = resp.json()
                stage = data.get("stage", "")
                message = data.get("message", "")
                progress = data.get("progress", -1)
                if not is_closing():
                    on_progress(message, progress)
                if stage == "ready":
                    if not is_closing():
                        on_ready()
                    return
                if stage == "error":
                    if not is_closing():
                        on_failed(message)
                    return
            except Exception:  # noqa: BLE001
                continue

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    threading.Thread(target=_wait_for_server, daemon=True).start()


def stop() -> None:
    """Request the running server to shut down."""
    if _server is not None:
        _server.should_exit = True
