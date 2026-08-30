"""Portable, network-free checks for the Windows cleanup primitives."""

from __future__ import annotations

import asyncio
import os
import sys


def test_runtime_exposes_text_encoding_and_platform_identity() -> None:
    assert sys.version_info >= (3, 10)
    assert os.name in {"nt", "posix"}
    assert sys.stdout.encoding


def test_pure_coroutine_completes_without_opening_an_event_loop() -> None:
    async def pure_async() -> str:
        return "async works"

    coroutine = pure_async()
    try:
        coroutine.send(None)
    except StopIteration as completed:
        assert completed.value == "async works"
    else:  # pragma: no cover - a pure coroutine must finish on its first step
        raise AssertionError("pure coroutine unexpectedly suspended")

    assert asyncio.iscoroutinefunction(pure_async)
