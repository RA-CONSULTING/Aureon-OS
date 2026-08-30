"""Secret-safe Ollama local/cloud configuration regression tests."""

from __future__ import annotations

from typing import Any

from aureon.core.aureon_env import apply_env_aliases
from aureon.inhouse_ai.llm_adapter import AureonLocalAdapter
from aureon.integrations.ollama import OllamaBridge
from aureon.ollama_config import (
    ollama_authorization_headers,
    ollama_config_snapshot,
    resolve_ollama_api_key,
    resolve_ollama_native_base_url,
    resolve_ollama_openai_base_url,
)
from aureon.operator.provider_catalog import get_provider


OLLAMA_ENV_NAMES = (
    "OLLAMA_API_KEY",
    "AUREON_OLLAMA_API_KEY",
    "AUREON_LLM_API_KEY",
    "AUREON_OLLAMA_BASE_URL",
    "AUREON_LLM_BASE_URL",
    "AUREON_OLLAMA_SEND_AUTH_TO_LOCAL",
)


def _clear(monkeypatch) -> None:
    for name in OLLAMA_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_official_key_precedes_compatibility_aliases(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("AUREON_LLM_API_KEY", "legacy")
    monkeypatch.setenv("AUREON_OLLAMA_API_KEY", "aureon")
    monkeypatch.setenv("OLLAMA_API_KEY", "official")

    assert resolve_ollama_api_key() == "official"


def test_environment_aliases_populate_all_ollama_key_names() -> None:
    env = {"OLLAMA_API_KEY": "secret"}

    applied = apply_env_aliases(env)

    assert env["AUREON_OLLAMA_API_KEY"] == "secret"
    assert env["AUREON_LLM_API_KEY"] == "secret"
    assert {item["target"] for item in applied} >= {
        "AUREON_OLLAMA_API_KEY",
        "AUREON_LLM_API_KEY",
    }


def test_cloud_url_aliases_normalize_native_and_openai_endpoints(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("AUREON_LLM_BASE_URL", "https://ollama.com/v1/")

    assert resolve_ollama_native_base_url() == "https://ollama.com"
    assert resolve_ollama_openai_base_url() == "https://ollama.com/v1"


def test_cloud_key_is_not_sent_to_loopback_by_default(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("OLLAMA_API_KEY", "cloud-secret")

    assert ollama_authorization_headers("https://ollama.com") == {
        "Authorization": "Bearer cloud-secret"
    }
    assert ollama_authorization_headers("http://localhost:11434") == {}
    assert ollama_authorization_headers(
        "http://localhost:11434",
        api_key="explicit-local-secret",
    ) == {"Authorization": "Bearer explicit-local-secret"}


class _Response:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"version": "cloud"}


class _Session:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, _url: str, **kwargs: Any) -> _Response:
        self.headers = dict(kwargs.get("headers") or {})
        return _Response()


def test_native_bridge_sends_bearer_and_never_snapshots_secret(monkeypatch) -> None:
    _clear(monkeypatch)
    bridge = OllamaBridge(
        base_url="https://ollama.com/api",
        api_key="cloud-secret",
    )
    session = _Session()
    bridge._session = session
    bridge._requests_available = True

    assert bridge.health_check(max_age_s=0)
    assert session.headers == {"Authorization": "Bearer cloud-secret"}
    snapshot = bridge.snapshot()
    assert snapshot["cloud"] is True
    assert snapshot["api_key_configured"] is True
    assert snapshot["authorization_header_enabled"] is True
    assert "cloud-secret" not in repr(snapshot)


def test_openai_compatible_adapter_uses_official_cloud_key(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("OLLAMA_API_KEY", "cloud-secret")

    cloud = AureonLocalAdapter(base_url="https://ollama.com/v1", model="m")
    local = AureonLocalAdapter(base_url="http://localhost:11434/v1", model="m")

    assert cloud._headers()["Authorization"] == "Bearer cloud-secret"
    assert "Authorization" not in local._headers()


def test_operator_catalog_uses_official_key_name() -> None:
    provider = get_provider("ollama")

    assert provider is not None
    assert provider.key_env == "OLLAMA_API_KEY"


def test_config_snapshot_is_secret_safe(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("OLLAMA_API_KEY", "never-print-me")

    snapshot = ollama_config_snapshot(base_url="https://ollama.com")

    assert snapshot["api_key_configured"] is True
    assert snapshot["authorization_header_enabled"] is True
    assert "never-print-me" not in repr(snapshot)
