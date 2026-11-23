"""External LLM routes are disabled; same-origin proxy security stays audited."""

from __future__ import annotations

from pathlib import Path

import pytest

import aureon.ollama_config as ollama_config
from aureon.inhouse_ai import llm_adapter
from aureon.inhouse_ai.llm_adapter import AureonUnavailableAdapter
from aureon.integrations.ollama import ollama_bridge
from aureon.operator import providers
from scripts.validation.audit_external_llm_fallback import (
    _is_trusted_same_origin_worker_proxy,
    static_inventory,
)


@pytest.mark.parametrize("value", [None, "ollama", "ollama_cloud", "off", "none"])
def test_external_fallback_policy_is_always_disabled(monkeypatch, value) -> None:
    if value is None:
        monkeypatch.delenv("AUREON_EXTERNAL_LLM_FALLBACK", raising=False)
    else:
        monkeypatch.setenv("AUREON_EXTERNAL_LLM_FALLBACK", value)

    assert ollama_config.resolve_external_llm_fallback() == "none"


def test_retired_runtime_bootstrap_never_loads_external_credentials(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "aureon.core.aureon_env.bootstrap_credentials",
        lambda *_args: pytest.fail("external credential bootstrap must not run"),
    )

    snapshot = ollama_config.ensure_ollama_runtime_config(force=True, repo_root=tmp_path)

    assert snapshot["external_fallback"] == "none"


def test_ollama_bridge_fails_closed_without_http(monkeypatch) -> None:
    bridge = ollama_bridge.OllamaBridge(
        base_url="https://ollama.com",
        api_key="not-a-real-secret",
        chat_model="cloud-model",
    )
    monkeypatch.setattr(
        bridge._session,
        "post",
        lambda *_args, **_kwargs: pytest.fail("Ollama HTTP must not run"),
    )
    monkeypatch.setattr(
        bridge._session,
        "get",
        lambda *_args, **_kwargs: pytest.fail("Ollama HTTP must not run"),
    )

    result = bridge.chat([{"role": "user", "content": "ping"}])

    assert result["done_reason"] == "error"
    assert "aureon_own_model_required" in result["error"]
    assert bridge.health_check() is False
    assert bridge.api_key == ""
    assert bridge._authorization_headers == {}


def test_operator_registry_ignores_keyed_cloud_profiles(monkeypatch) -> None:
    monkeypatch.setenv("AUREON_LLM_BASE_URL", "https://ollama.com/v1")
    monkeypatch.setenv("AUREON_LLM_MODEL", "cloud-model")
    monkeypatch.setenv("OLLAMA_API_KEY", "not-a-real-secret")
    monkeypatch.setattr(
        providers,
        "_aureon_own_adapter",
        lambda: AureonUnavailableAdapter("own model unavailable", model="aureon-own-unavailable"),
    )
    monkeypatch.setattr(
        providers,
        "_build_from_spec",
        lambda _spec: pytest.fail("external model specs must not be constructed"),
    )

    registry = providers.build_registry(force_offline=False)

    assert set(registry) == {"aureon-own"}
    assert registry["aureon-own"].health_check() is False


def test_explicit_anthropic_voice_route_has_no_ollama_fallback(monkeypatch) -> None:
    monkeypatch.setenv("AUREON_VOICE_BACKEND", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-secret")
    monkeypatch.setattr(
        llm_adapter,
        "AureonHybridAdapter",
        lambda: pytest.fail("hybrid fallback must not be constructed"),
    )

    adapter = llm_adapter.build_voice_adapter()

    assert isinstance(adapter, AureonUnavailableAdapter)
    assert adapter.model == "aureon_own_model_required"
    assert adapter.health_check() is False


def test_cloudflare_console_is_an_exact_authenticated_same_origin_worker_proxy() -> None:
    relative = "flameborn/cloudflare-ui/app.js"
    source = (Path(__file__).resolve().parents[1] / relative).read_text(encoding="utf-8")

    assert _is_trusted_same_origin_worker_proxy(relative, source) is True
    assert _is_trusted_same_origin_worker_proxy(
        relative,
        source.replace("target.origin !== window.location.origin", "false"),
    ) is False
    assert _is_trusted_same_origin_worker_proxy(
        relative,
        source + "\nfetch('https://api.openai.com/v1/chat/completions');\n",
    ) is False

    inventory = static_inventory()
    assert relative in inventory["trusted_same_origin_worker_proxies"]
    assert "flameborn/dist-workers/app.js" not in inventory["trusted_same_origin_worker_proxies"]
    assert inventory["unexpected_direct_llm_surfaces"] == []
    assert inventory["all_discovered_calls_centralized"] is True
