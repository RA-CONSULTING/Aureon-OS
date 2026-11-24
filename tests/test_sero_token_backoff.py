"""A missing Sero issuance endpoint backs off and never invents a token."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
import pytest

from aureon.utils import aureon_sero_client as sero_module


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


class _Response:
    def __init__(self, status: int, text: str = "", payload: dict | None = None):
        self.status = status
        self._text = text
        self._payload = {} if payload is None else payload

    async def text(self) -> str:
        return self._text

    async def json(self) -> dict:
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class _Session:
    def __init__(self, status: int = 404, text: str = "Not Found", payload: dict | None = None):
        self.posts = 0
        self.status = status
        self.text = text
        self.payload = payload

    def post(self, *_args, **_kwargs):
        self.posts += 1
        return _Response(self.status, self.text, self.payload)


class _FailingSession:
    def __init__(self) -> None:
        self.posts = 0

    def post(self, *_args, **_kwargs):
        self.posts += 1
        raise aiohttp.ClientError("endpoint down")


def _client(monkeypatch: pytest.MonkeyPatch) -> tuple[sero_module.SeroClient, _Clock]:
    clock = _Clock()
    monkeypatch.setattr(sero_module.time, "monotonic", clock.monotonic)
    client = sero_module.SeroClient()
    client.agent_id = "missing-agent"
    client.chatbot_id = "issuance-key"
    client.api_key = "issuance-key"
    client._cached_token = None
    client._token_expiry = 0
    return client, clock


def _issuance_logs(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if "Token issuance" in record.message]


def test_missing_endpoint_warns_once_then_backs_off(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert sero_module.TOKEN_BACKOFF_INITIAL_S == 30.0
    assert sero_module.TOKEN_BACKOFF_CAP_S == 15 * 60
    client, clock = _client(monkeypatch)
    session = _Session()

    with caplog.at_level(logging.WARNING, logger="aureon.utils.aureon_sero_client"):
        first = client._get_access_token(session)
        assert asyncio.run(first) is None
        second = asyncio.run(client._get_access_token(session))

    assert second is None
    assert session.posts == 1
    assert client._cached_token is None
    assert client._token_backoff_s == 30.0
    logs = _issuance_logs(caplog)
    assert len(logs) == 1
    assert logs[0].levelno == logging.WARNING
    assert "404 | Not Found" in logs[0].message
    assert not any(record.levelno >= logging.ERROR for record in logs)

    clock.now = 30.0
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="aureon.utils.aureon_sero_client"):
        third = asyncio.run(client._get_access_token(session))
    assert third is None
    assert session.posts == 2
    assert client._token_backoff_s == 60.0
    assert client._cached_token is None
    summary = _issuance_logs(caplog)
    assert len(summary) == 1
    assert "repeats not logged" in summary[0].message
    assert summary[0].levelno == logging.WARNING

    clock.now = 30.0 + 59.0
    before = session.posts
    assert asyncio.run(client._get_access_token(session)) is None
    assert session.posts == before


def test_backoff_caps_at_fifteen_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, clock = _client(monkeypatch)
    client._token_backoff_s = sero_module.TOKEN_BACKOFF_CAP_S
    client._token_failure_count = 4
    client._token_backoff_until = 0.0
    clock.now = 1_000.0
    session = _Session()

    assert asyncio.run(client._get_access_token(session)) is None

    assert client._token_backoff_s == 15 * 60
    assert client._token_backoff_until == 1_000.0 + 15 * 60
    assert client._cached_token is None
    assert session.posts == 1


def test_client_error_backs_off_without_a_token(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, _clock = _client(monkeypatch)
    session = _FailingSession()
    with caplog.at_level(logging.DEBUG, logger="aureon.utils.aureon_sero_client"):
        result = asyncio.run(client._get_access_token(session))
    assert result is None
    assert client._cached_token is None
    assert session.posts == 1
    assert client._token_backoff_s == 30.0
    logs = _issuance_logs(caplog)
    assert len(logs) == 1
    assert logs[0].levelno == logging.WARNING
    assert "endpoint down" not in logs[0].message


def test_real_token_is_cached_and_clears_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, clock = _client(monkeypatch)
    client._token_backoff_s = 120.0
    client._token_failure_count = 3
    client._token_backoff_until = 500.0
    clock.now = 500.0
    session = _Session(status=200, payload={"access_token": "issued-token"})

    token = asyncio.run(client._get_access_token(session))

    assert token == "issued-token"
    assert client._cached_token == "issued-token"
    assert client._token_failure_count == 0
    assert client._token_backoff_s == 0.0
    posts = session.posts
    again = asyncio.run(client._get_access_token(session))
    assert again == "issued-token"
    assert session.posts == posts


def test_success_without_a_token_does_not_invent_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _clock = _client(monkeypatch)
    session = _Session(status=200, payload={"access_token": ""})

    assert asyncio.run(client._get_access_token(session)) is None
    assert client._cached_token is None
    assert client._token_backoff_s == 30.0
