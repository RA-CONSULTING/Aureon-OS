"""Dr Auris/Sero routing keeps its provider and gains Ollama Cloud fallback."""

from __future__ import annotations

from aureon.inhouse_ai import llm_adapter
from aureon.inhouse_ai.llm_adapter import LLMResponse
from aureon.integrations.ollama import OllamaModelSwitchboard
from aureon.utils import aureon_sero_client as sero_module


def _clear_provider(monkeypatch) -> None:
    for name in (
        "AUREON_AGENT_ENDPOINT",
        "AUREON_AGENT_ID",
        "AUREON_CHATBOT_ID",
        "AUREON_AGENT_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_sero_uses_ollama_cloud_when_legacy_agent_is_absent(monkeypatch) -> None:
    _clear_provider(monkeypatch)
    monkeypatch.setattr(sero_module, "ensure_ollama_runtime_config", lambda: {})
    monkeypatch.setattr(sero_module, "resolve_external_llm_fallback", lambda: "ollama")
    monkeypatch.setattr(
        sero_module,
        "ollama_config_snapshot",
        lambda: {"cloud": True, "authorization_header_enabled": True},
    )

    class _Adapter:
        def prompt(self, *_args, **_kwargs) -> LLMResponse:
            return LLMResponse(
                text="CAUTION 0.8 spread evidence is incomplete",
                stop_reason="end_turn",
                model="cloud-model",
            )

    monkeypatch.setattr(
        OllamaModelSwitchboard,
        "compatible_adapter_for",
        lambda self, lane: (_Adapter(), {"lane": lane, "model": "cloud-model"}),
    )
    monkeypatch.setattr(llm_adapter, "_llm_http_disabled", lambda: False)

    client = sero_module.SeroClient()
    response = client._query_ollama_fallback("review")
    advice = client._parse_trading_response(response)

    assert client.enabled is True
    assert client.provider_enabled is False
    assert client.fallback_enabled is True
    assert client.route == "ollama_cloud"
    assert advice is not None
    assert advice.recommendation == "CAUTION"
    assert advice.confidence == 0.8


def test_sero_explicit_agent_keeps_precedence(monkeypatch) -> None:
    monkeypatch.setattr(sero_module, "ensure_ollama_runtime_config", lambda: {})
    monkeypatch.setattr(sero_module, "resolve_external_llm_fallback", lambda: "ollama")
    monkeypatch.setattr(
        sero_module,
        "ollama_config_snapshot",
        lambda: {"cloud": True, "authorization_header_enabled": True},
    )
    monkeypatch.setenv("AUREON_AGENT_ENDPOINT", "https://agent.example")
    monkeypatch.setenv("AUREON_AGENT_ID", "agent")
    monkeypatch.setenv("AUREON_CHATBOT_ID", "chatbot")
    monkeypatch.setenv("AUREON_AGENT_KEY", "agent-key")

    client = sero_module.SeroClient()

    assert client.enabled is True
    assert client.provider_enabled is True
    assert client.route == "digitalocean_agent"
