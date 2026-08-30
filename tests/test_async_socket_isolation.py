import asyncio
import socket

import pytest
from pytest_socket import SocketBlockedError


async def _socket_blocked_scenario():
    await asyncio.sleep(0)
    with pytest.raises(SocketBlockedError):
        socket.socket()
    return "complete"


async def test_native_coroutine_runs_without_unblocking_test_sockets():
    assert await _socket_blocked_scenario() == "complete"


def test_sync_asyncio_run_uses_precreated_loop_with_sockets_blocked():
    assert asyncio.run(_socket_blocked_scenario()) == "complete"
