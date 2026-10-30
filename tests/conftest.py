"""Pytest hooks for the tests/ tree (MCP guard isolation lives here, not in repo-root conftest)."""

from __future__ import annotations

import os

import pytest

from tests.support import mcp_isolation


def _mcp_module(request: pytest.FixtureRequest) -> bool:
    return mcp_isolation.is_mcp_test_module(request.module.__name__)


@pytest.fixture(scope="module", autouse=True)
def _mcp_public_imports(request: pytest.FixtureRequest) -> None:
    if not _mcp_module(request):
        yield
        return
    env_before = dict(os.environ)
    mcp_isolation.load_public_test_bindings(request.module)
    try:
        yield
    finally:
        mcp_isolation.teardown_guard_leaks()
        os.environ.clear()
        os.environ.update(env_before)


@pytest.fixture(scope="session", autouse=True)
def _mcp_guard_session_teardown() -> None:
    yield
    mcp_isolation.teardown_guard_leaks()
