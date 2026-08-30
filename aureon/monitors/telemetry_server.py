#!/usr/bin/env python3
"""Explicit lifecycle for the Aureon Prometheus metrics exporter.

Importing this module is intentionally inert. Runtime owners must call
start_telemetry_server and release their ownership with
stop_telemetry_server during shutdown.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)

import logging
import threading
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

_DEFAULT_OWNER = "telemetry-server"
_server_started = False
_server_handle: Optional[Any] = None
_server_thread: Optional[threading.Thread] = None
_server_port: Optional[int] = None
_server_address: Optional[str] = None
_server_owners: Set[str] = set()
_server_lock = threading.RLock()
_last_error = ""


def _normalise_port(port: int) -> int:
    value = int(port)
    if not 1 <= value <= 65535:
        raise ValueError("telemetry port must be between 1 and 65535")
    return value


def _owner_token(owner: Optional[str]) -> str:
    token = str(owner or _DEFAULT_OWNER).strip()
    return token or _DEFAULT_OWNER


def telemetry_server_status() -> Dict[str, Any]:
    """Return local lifecycle state without probing or binding any socket."""
    with _server_lock:
        thread_alive = bool(_server_thread is not None and _server_thread.is_alive())
        running = bool(_server_started and (_server_thread is None or thread_alive))
        return {
            "running": running,
            "port": _server_port,
            "address": _server_address,
            "owner_count": len(_server_owners),
            "stoppable": _server_handle is not None,
            "thread_alive": thread_alive,
            "last_error": _last_error or None,
        }


def start_telemetry_server(
    port: int = 8000,
    *,
    address: str = "0.0.0.0",
    owner: Optional[str] = None,
) -> bool:
    """Start the Prometheus HTTP server for an explicit runtime owner.

    Repeated calls for the same address and port share the process-wide server.
    The concrete WSGI server and thread returned by prometheus_client are
    retained so supported versions can be shut down and joined cleanly.
    """
    global _server_started, _server_handle, _server_thread
    global _server_port, _server_address, _last_error

    requested_port = _normalise_port(port)
    requested_address = str(address or "0.0.0.0")
    token = _owner_token(owner)

    with _server_lock:
        if _server_started:
            alive = _server_thread is None or _server_thread.is_alive()
            same_endpoint = (
                _server_port == requested_port
                and _server_address == requested_address
            )
            if alive and same_endpoint:
                _server_owners.add(token)
                return True
            if alive:
                _last_error = (
                    "telemetry_already_running_on_"
                    f"{_server_address}:{_server_port}"
                )
                logger.warning(
                    "Telemetry server already runs on %s:%s; refusing %s:%s",
                    _server_address,
                    _server_port,
                    requested_address,
                    requested_port,
                )
                return False

            # A previously owned thread exited unexpectedly. Close its socket
            # before permitting a clean, explicit restart.
            try:
                if _server_handle is not None:
                    _server_handle.server_close()
            except Exception:
                pass
            _server_started = False
            _server_handle = None
            _server_thread = None
            _server_port = None
            _server_address = None
            _server_owners.clear()

        try:
            from prometheus_client import start_http_server

            result = start_http_server(requested_port, addr=requested_address)
            if isinstance(result, tuple) and len(result) >= 2:
                _server_handle = result[0]
                _server_thread = result[1]
            else:
                # Older prometheus_client versions did not return lifecycle
                # handles. Metrics still work, but deterministic stop cannot be
                # promised and status reports that limitation truthfully.
                _server_handle = None
                _server_thread = None
            _server_started = True
            _server_port = requested_port
            _server_address = requested_address
            _server_owners.add(token)
            _last_error = ""
            logger.info(
                "Telemetry: Prometheus metrics server started on %s:%s",
                requested_address,
                requested_port,
            )
            return True
        except Exception as exc:
            _last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Telemetry: could not start metrics server: %s", exc)
            return False


def stop_telemetry_server(
    timeout: float = 2.0,
    *,
    owner: Optional[str] = None,
    force: bool = False,
) -> bool:
    """Release an owner and stop/join the exporter when no owners remain.

    force=True is reserved for process shutdown and tests. If the installed
    Prometheus client does not expose a WSGI handle, the function returns
    False rather than claiming that an unobservable server was stopped.
    """
    global _server_started, _server_handle, _server_thread
    global _server_port, _server_address, _last_error

    token = _owner_token(owner)
    with _server_lock:
        if not _server_started:
            _server_owners.discard(token)
            return True

        if force:
            _server_owners.clear()
        else:
            _server_owners.discard(token)
            if _server_owners:
                return True

        server = _server_handle
        thread = _server_thread
        if server is None:
            _last_error = "telemetry_server_stop_unsupported"
            logger.warning(
                "Telemetry: installed prometheus_client exposes no shutdown handle"
            )
            return False

        stopped = True
        try:
            server.shutdown()
        except Exception as exc:
            stopped = False
            _last_error = f"shutdown_failed: {type(exc).__name__}: {exc}"
            logger.warning("Telemetry: shutdown failed: %s", exc)
        try:
            server.server_close()
        except Exception as exc:
            stopped = False
            _last_error = f"close_failed: {type(exc).__name__}: {exc}"
            logger.warning("Telemetry: socket close failed: %s", exc)

        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(0.0, float(timeout)))
            if thread.is_alive():
                stopped = False
                _last_error = "telemetry_server_thread_join_timeout"

        if stopped:
            _last_error = ""
        _server_started = False
        _server_handle = None
        _server_thread = None
        _server_port = None
        _server_address = None
        _server_owners.clear()
        return stopped


def main() -> int:
    """Run the standalone exporter until the process receives an interrupt."""
    logging.basicConfig(level=logging.INFO)
    if not start_telemetry_server():
        return 1
    stopped = threading.Event()
    try:
        while not stopped.wait(1.0):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        stop_telemetry_server(force=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
