import asyncio
import socket

import pytest
from pytest_socket import SocketBlockedError, disable_socket, enable_socket


async def _socket_blocked_scenario():
    await asyncio.sleep(0)
    with pytest.raises(SocketBlockedError):
        socket.socket()
    return "complete"


def _run_with_sockets_blocked() -> str:
    """Create the asyncio self-pipe before applying the network guard."""

    enable_socket()
    loop = asyncio.new_event_loop()
    try:
        disable_socket()
        return loop.run_until_complete(_socket_blocked_scenario())
    finally:
        enable_socket()
        loop.close()


def test_coroutine_runs_after_the_event_loop_is_precreated():
    assert _run_with_sockets_blocked() == "complete"


def test_precreated_loop_keeps_new_socket_creation_blocked():
    assert _run_with_sockets_blocked() == "complete"
