"""Skip a test only when it must connect to a local server and loopback is down.

Binding ``127.0.0.1`` succeeds while the loopback interface is down.
Connecting does not: the errno is ``ENETUNREACH``. ``unshare -rn`` leaves
``lo`` down. A refused connection means the interface is up and the test runs.
"""

from __future__ import annotations

import errno
import socket

import pytest

_DOWN = {errno.ENETUNREACH, errno.ENETDOWN, errno.EHOSTUNREACH, errno.EADDRNOTAVAIL}

_REASON = (
    "loopback interface is down (connect to 127.0.0.1 returns ENETUNREACH); "
    "this test connects to a local server"
)


def loopback_up() -> bool:
    """True when a connect to 127.0.0.1 can leave the host, even if nothing listens."""

    sock = socket.socket()
    sock.settimeout(0.2)
    try:
        try:
            sock.connect(("127.0.0.1", 9))
        except ConnectionRefusedError:
            return True
        except OSError as exc:
            code = getattr(exc, "errno", None)
            if code in _DOWN:
                return False
            return code == errno.ECONNREFUSED
        return True
    finally:
        sock.close()


def require_loopback() -> None:
    """Skip the current test when it cannot connect to a server it binds."""

    if not loopback_up():
        pytest.skip(_REASON)
