import logging

import pytest

from aureon.core.hnc_llm_gears import unavailable_organism
from aureon.inhouse_ai.llm_adapter import (
    AureonBrainAdapter,
    AureonHybridAdapter,
    AureonLocalAdapter,
    AureonStubAdapter,
    AureonUnavailableAdapter,
    LLMResponse,
    build_voice_adapter,
)


def test_own_model_prompt_binds_organism_snapshot_to_request_and_response(monkeypatch):
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    adapter = AureonLocalAdapter()
    observed = {}

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "aureon-7b-v65k",
                "choices": [{"message": {"content": "private coding answer"}}],
            }

    def post(_url, **kwargs):
        observed.update(kwargs)
        return _Response()

    monkeypatch.setattr(adapter, "_http_post", post)
    organism = unavailable_organism("test_no_field")
    response = adapter.prompt(
        [{"role": "user", "content": "Write a safe function."}],
        system="test system",
        organism=organism,
    )

    assert observed["json"]["model"] == "aureon-7b-v65k"
    context = observed["json"]["messages"][0]["content"]
    assert "[AUREON_ORGANISM_STATE]" in context
    assert '"receipt_id"' not in context  # this fixture is explicitly unavailable
    assert response.text == "private coding answer"
    assert response.raw["hnc_gears"]["parsed"] is False
    assert response.raw["hnc_gears"]["gears"][1]["blocker"] == "test_no_field"
    assert response.raw["hnc_gears"]["authority"] == "evidence_only"


def test_own_model_stream_sends_snapshot_and_rejects_invalid_json(monkeypatch):
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    adapter = AureonLocalAdapter()
    observed = {}

    class _Response:
        def raise_for_status(self):
            return None

        def iter_lines(self):
            return [b'data: {"model":"aureon-7b-v65k","choices":[{"delta":{}}]}', b"data: broken"]

    def post(_url, **kwargs):
        observed.update(kwargs)
        return _Response()

    monkeypatch.setattr(adapter, "_http_post", post)
    chunks = list(adapter.stream(
        [{"role": "user", "content": "test"}],
        system="test system",
        organism=unavailable_organism("test_no_field"),
    ))
    assert "[AUREON_ORGANISM_STATE]" in observed["json"]["messages"][0]["content"]
    assert observed["json"]["stream"] is True
    assert chunks[-1].stop_reason == "error"
    assert "invalid JSON" in chunks[-1].text


def test_own_model_stream_rejects_invalid_organism_before_transport(monkeypatch):
    adapter = AureonLocalAdapter()
    monkeypatch.setattr(
        adapter, "_http_post",
        lambda *_args, **_kwargs: pytest.fail("invalid evidence reached transport"),
    )
    chunks = list(adapter.stream(
        [{"role": "user", "content": "test"}], organism={"all_turned": True},
    ))
    assert chunks[-1].stop_reason == "error"
    assert "organism_snapshot_schema_invalid" in chunks[-1].text


def test_own_model_invalid_organism_never_calls_transport(monkeypatch):
    adapter = AureonLocalAdapter()
    monkeypatch.setattr(
        adapter, "_http_post",
        lambda *_args, **_kwargs: pytest.fail("invalid evidence reached transport"),
    )
    response = adapter.prompt(
        [{"role": "user", "content": "test"}], organism={"all_turned": True},
    )
    assert response.stop_reason == "error"
    assert "organism_snapshot_schema_invalid" in response.text


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


def _auto_lane_env(monkeypatch):
    monkeypatch.delenv("AUREON_VOICE_BACKEND", raising=False)
    monkeypatch.delenv("AUREON_OWN_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("AUREON_OWN_LLM_MODEL", raising=False)
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", "1")
    # The suite exports AUREON_LLM_OFFLINE=1, which correctly trumps the
    # audit-allow flag. These tests patch every HTTP seam, so clear it here.
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)

    # The auto lane never consults the Ollama switchboard, so a borrowed model
    # cannot be picked even when one would be reachable.
    from aureon.integrations.ollama import model_switchboard

    def _no_borrowed_model(*_args, **_kwargs):
        raise AssertionError("auto voice lane consulted the Ollama switchboard")

    monkeypatch.setattr(model_switchboard.OllamaModelSwitchboard, "__init__", _no_borrowed_model)


def test_default_voice_adapter_uses_own_model_when_reachable(monkeypatch):
    _auto_lane_env(monkeypatch)
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)

    adapter = build_voice_adapter()

    assert type(adapter) is AureonLocalAdapter
    assert not isinstance(adapter, AureonHybridAdapter)
    assert adapter.base_url == "http://127.0.0.1:11435/v1"
    assert adapter.model == "aureon-7b-v65k"
    assert not adapter.model.startswith("aureon-ollama-hybrid")


def test_default_voice_adapter_is_unavailable_when_own_model_unreachable(monkeypatch):
    _auto_lane_env(monkeypatch)
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: False)

    adapter = build_voice_adapter()
    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert isinstance(adapter, AureonStubAdapter)
    assert isinstance(adapter, AureonUnavailableAdapter)
    assert not isinstance(adapter, (AureonHybridAdapter, AureonLocalAdapter))
    assert adapter.health_check() is False
    assert response.model == "aureon-own-unavailable"
    assert response.stop_reason == "error"
    assert "no borrowed or cloud fallback" in response.text


@pytest.mark.parametrize("backend", ["plain_local", "local_only", "no-such-backend"])
def test_unserved_voice_backend_is_unavailable_not_none(monkeypatch, backend):
    _auto_lane_env(monkeypatch)
    monkeypatch.setenv("AUREON_VOICE_BACKEND", backend)
    # Even with every local endpoint reachable, these names must not pick one.
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)

    adapter = build_voice_adapter()

    assert adapter is not None
    assert isinstance(adapter, AureonUnavailableAdapter)
    assert not isinstance(adapter, (AureonHybridAdapter, AureonLocalAdapter))
    assert adapter.health_check() is False
    response = adapter.prompt([{"role": "user", "content": "ping"}])
    assert response.model == "aureon_own_model_required"
    assert response.stop_reason == "error"
    assert backend in response.text


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
