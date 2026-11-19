import logging

import pytest

from aureon.inhouse_ai.llm_adapter import (
    AureonBrainAdapter,
    AureonHybridAdapter,
    AureonLocalAdapter,
    AureonUnavailableAdapter,
    LLMResponse,
    build_voice_adapter,
)


def test_audit_mode_disables_own_model_http(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.delenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", raising=False)

    adapter = AureonLocalAdapter()
    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert response.stop_reason == "error"
    assert "LLM HTTP disabled" in response.text
    assert adapter.health_check() is False


def test_hybrid_compatibility_adapter_fails_closed_in_audit_mode(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.delenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", raising=False)

    adapter = AureonHybridAdapter()
    monkeypatch.setattr(adapter, "_build_dynamic_filter", lambda *a, **k: {})
    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert response.stop_reason == "error"
    assert response.raw["error"] == "aureon-own-unavailable"
    assert adapter.health_check() is False


def test_voice_adapter_rejects_retired_ollama_hybrid(monkeypatch):
    monkeypatch.setenv("AUREON_VOICE_BACKEND", "ollama_hybrid")

    adapter = build_voice_adapter()

    assert isinstance(adapter, AureonUnavailableAdapter)
    assert adapter.model == "aureon_own_model_required"
    assert adapter.health_check() is False


def test_default_voice_adapter_selects_own_model_when_available(monkeypatch):
    monkeypatch.delenv("AUREON_VOICE_BACKEND", raising=False)
    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)

    adapter = build_voice_adapter()

    assert isinstance(adapter, AureonLocalAdapter)
    assert adapter.base_url == "http://127.0.0.1:11435/v1"
    assert adapter.model == "aureon-7b-v65k"


class _OwnAdapter:
    model = "aureon-7b-v65k"

    def __init__(self, *, available=True):
        self.available = available
        self.calls = []

    def health_check(self):
        return self.available

    def prompt(
        self,
        messages,
        system="",
        tools=None,
        max_tokens=4096,
        temperature=0.7,
        **kwargs,
    ):
        self.calls.append({"messages": messages, "system": system, **kwargs})
        return LLMResponse(text="own answer", model=self.model)


def _quiet_dynamic_filter(monkeypatch, adapter):
    monkeypatch.setattr(adapter, "_build_dynamic_filter", lambda *a, **k: {})
    monkeypatch.setattr(adapter, "_system_with_dynamic_filter", lambda system, _report: system)
    monkeypatch.setattr(adapter, "_enrich_system", lambda system, _messages: system)
    monkeypatch.setattr(
        adapter,
        "_finalize_dynamic_response",
        lambda response, _report, **_kwargs: response,
    )


def test_hybrid_compatibility_adapter_delegates_once_to_own_model(monkeypatch):
    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    own = _OwnAdapter()
    monkeypatch.setattr("aureon.inhouse_ai.llm_adapter._aureon_own_adapter", lambda: own)
    adapter = AureonHybridAdapter(model="llama3:latest")
    _quiet_dynamic_filter(monkeypatch, adapter)

    response = adapter.prompt([{"role": "user", "content": "Use Aureon's own model."}])

    assert response.text == "own answer"
    assert response.model == "aureon-7b-v65k"
    assert len(own.calls) == 1


def test_hybrid_compatibility_adapter_has_no_brain_fallback(monkeypatch):
    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    own = _OwnAdapter(available=False)
    monkeypatch.setattr("aureon.inhouse_ai.llm_adapter._aureon_own_adapter", lambda: own)
    adapter = AureonHybridAdapter()
    _quiet_dynamic_filter(monkeypatch, adapter)
    monkeypatch.setattr(
        adapter.brain,
        "prompt",
        lambda *a, **k: pytest.fail("AureonBrain must not replace the own model"),
    )

    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert response.stop_reason == "error"
    assert response.raw["error"] == "aureon-own-unavailable"
    assert own.calls == []


def test_brain_adapter_matches_current_decide_signature(monkeypatch, caplog):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    adapter = AureonBrainAdapter()

    with caplog.at_level(logging.WARNING, logger="aureon.inhouse_ai.llm"):
        response = adapter.prompt([{"role": "user", "content": "analyse BTCUSDT exposure"}])

    assert response.model == "aureon-brain-v1"
    assert '"source": "AureonBrain"' in response.text
    assert not any("AureonBrain reasoning failed" in r.message for r in caplog.records)
