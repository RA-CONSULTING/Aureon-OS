from __future__ import annotations

import inspect
from typing import Any

import pytest

from aureon.inhouse_ai.llm_adapter import AureonLocalAdapter


LOCAL_BASE_URL = "http://127.0.0.1:11434/v1"


class FakeResponse:
    def __init__(
        self,
        *,
        url: str,
        status_code: int,
        payload: dict[str, Any] | None = None,
        location: str = "",
    ) -> None:
        self.url = url
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = {"Location": location} if location else {}
        self.history: list[Any] = []
        self.is_redirect = 300 <= status_code < 400
        self.is_permanent_redirect = status_code in {308}
        self.text = ""

    def json(self) -> dict[str, Any]:
        return dict(self._payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status={self.status_code}")


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.trust_env = False
        self.proxies: dict[str, str] = {}
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("POST", url, dict(kwargs)))
        return self.response

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("GET", url, dict(kwargs)))
        return self.response


def _adapter() -> AureonLocalAdapter:
    return AureonLocalAdapter(
        base_url=LOCAL_BASE_URL,
        model="strict-loopback-test",
        api_key="",
        strict_loopback_no_redirects=True,
    )


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:11434/v1",
        "https://127.0.0.1:11434/v1",
        "http://192.168.1.20:11434/v1",
        "https://ollama.com/v1",
    ],
)
def test_strict_transport_accepts_only_literal_http_loopback(base_url: str) -> None:
    with pytest.raises(ValueError, match="strict_loopback_url_invalid"):
        AureonLocalAdapter(
            base_url=base_url,
            model="strict-loopback-test",
            api_key="",
            strict_loopback_no_redirects=True,
        )


def test_strict_transport_accepts_literal_ipv6_loopback() -> None:
    adapter = AureonLocalAdapter(
        base_url="http://[::1]:11434/v1",
        model="strict-loopback-test",
        api_key="",
        strict_loopback_no_redirects=True,
    )

    assert adapter.strict_loopback_no_redirects is True
    assert adapter._session is not None
    assert adapter._session.trust_env is False
    assert adapter._session.proxies == {}


def test_strict_prompt_rejects_redirect_without_following_external_location() -> None:
    adapter = _adapter()
    redirect = FakeResponse(
        url="http://127.0.0.1:11434/api/chat",
        status_code=307,
        location="https://example.invalid/capture",
    )
    session = FakeSession(redirect)
    adapter._session = session

    result = adapter.prompt([{"role": "user", "content": "private-source-canary"}])

    assert result.stop_reason == "error"
    assert "strict_loopback_redirect_rejected" in result.text
    assert len(session.calls) == 1
    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url == "http://127.0.0.1:11434/api/chat"
    assert kwargs["allow_redirects"] is False
    assert kwargs["proxies"] == {}
    assert "example.invalid" not in url


@pytest.mark.parametrize(
    ("call_path", "method", "local_url"),
    [
        ("native_prompt", "POST", "http://127.0.0.1:11434/api/chat"),
        (
            "compatible_prompt",
            "POST",
            "http://127.0.0.1:11434/v1/chat/completions",
        ),
        ("stream", "POST", "http://127.0.0.1:11434/v1/chat/completions"),
        ("health", "GET", "http://127.0.0.1:11434/v1/models"),
        ("probe", "POST", "http://127.0.0.1:11434/v1/chat/completions"),
    ],
)
@pytest.mark.parametrize("status_code", [301, 302, 303, 307, 308])
def test_every_adapter_http_path_rejects_redirects(
    call_path: str,
    method: str,
    local_url: str,
    status_code: int,
) -> None:
    adapter = _adapter()
    session = FakeSession(
        FakeResponse(
            url=local_url,
            status_code=status_code,
            location="https://example.invalid/capture",
        )
    )
    adapter._session = session

    if call_path == "native_prompt":
        result = adapter.prompt([{"role": "user", "content": "private-source-canary"}])
        assert result.stop_reason == "error"
    elif call_path == "compatible_prompt":
        adapter._prefer_native = False
        result = adapter.prompt([{"role": "user", "content": "private-source-canary"}])
        assert result.stop_reason == "error"
    elif call_path == "stream":
        chunks = list(
            adapter.stream([{"role": "user", "content": "private-source-canary"}])
        )
        assert len(chunks) == 1
        assert chunks[0].done is True
    elif call_path == "health":
        assert adapter.health_check() is False
    else:
        assert call_path == "probe"
        assert adapter._probe_model("strict-loopback-test") is False

    assert len(session.calls) == 1
    assert session.calls[0][0] == method
    assert session.calls[0][2]["allow_redirects"] is False
    assert session.calls[0][2]["proxies"] == {}


def test_strict_prompt_rejects_ambient_proxy_state_before_send() -> None:
    adapter = _adapter()
    session = FakeSession(
        FakeResponse(
            url="http://127.0.0.1:11434/api/chat",
            status_code=200,
        )
    )
    session.trust_env = True
    adapter._session = session

    result = adapter.prompt([{"role": "user", "content": "private-source-canary"}])

    assert result.stop_reason == "error"
    assert "strict_loopback_proxy_state_invalid" in result.text
    assert session.calls == []


def test_strict_prompt_accepts_one_direct_loopback_response() -> None:
    adapter = _adapter()
    session = FakeSession(
        FakeResponse(
            url="http://127.0.0.1:11434/api/chat",
            status_code=200,
            payload={
                "message": {"content": "local-only-answer"},
                "done_reason": "stop",
                "model": "strict-loopback-test",
            },
        )
    )
    adapter._session = session

    result = adapter.prompt([{"role": "user", "content": "private-source-canary"}])

    assert result.text == "local-only-answer"
    assert result.stop_reason == "end_turn"
    assert len(session.calls) == 1
    assert session.calls[0][2]["allow_redirects"] is False
    assert session.calls[0][2]["proxies"] == {}


def test_strict_wrapper_rejects_per_request_proxy_before_send() -> None:
    adapter = _adapter()
    session = FakeSession(
        FakeResponse(
            url="http://127.0.0.1:11434/api/chat",
            status_code=200,
        )
    )
    adapter._session = session

    with pytest.raises(
        RuntimeError,
        match="strict_loopback_request_proxy_forbidden",
    ):
        adapter._http_post(
            "http://127.0.0.1:11434/api/chat",
            proxies={"http": "http://127.0.0.1:8999"},
        )

    assert session.calls == []


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_strict_wrapper_rejects_external_request_url_before_send(method: str) -> None:
    adapter = _adapter()
    session = FakeSession(
        FakeResponse(
            url="http://127.0.0.1:11434/v1/models",
            status_code=200,
        )
    )
    adapter._session = session

    with pytest.raises(ValueError, match="strict_loopback_url_invalid"):
        if method == "POST":
            adapter._http_post("http://192.0.2.10:11434/v1/chat/completions")
        else:
            adapter._http_get("http://192.0.2.10:11434/v1/models")

    assert session.calls == []


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_strict_wrapper_rejects_external_200_response_url(method: str) -> None:
    adapter = _adapter()
    session = FakeSession(
        FakeResponse(
            url="http://192.0.2.10:11434/v1/models",
            status_code=200,
        )
    )
    adapter._session = session

    with pytest.raises(ValueError, match="strict_loopback_url_invalid"):
        if method == "POST":
            adapter._http_post("http://127.0.0.1:11434/v1/chat/completions")
        else:
            adapter._http_get("http://127.0.0.1:11434/v1/models")

    assert len(session.calls) == 1
    assert session.calls[0][0] == method


def test_mutated_external_base_url_holds_before_send() -> None:
    adapter = _adapter()
    session = FakeSession(
        FakeResponse(
            url="http://127.0.0.1:11434/api/chat",
            status_code=200,
        )
    )
    adapter._session = session
    adapter.base_url = "http://192.0.2.10:11434/v1"

    result = adapter.prompt([{"role": "user", "content": "private-source-canary"}])

    assert result.stop_reason == "error"
    assert "strict_loopback_url_invalid" in result.text
    assert session.calls == []


def test_current_session_http_calls_are_centralized_through_strict_wrappers() -> None:
    source = inspect.getsource(AureonLocalAdapter)

    assert source.count("self._session.post(") == 1
    assert source.count("self._session.get(") == 1
    assert "self._session.request(" not in source
    assert "def _http_post(" in source
    assert "def _http_get(" in source
