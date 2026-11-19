"""Aureon's language-model routes use its own model or fail closed."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.autonomous.aureon_internal_coding_workforce import (
    _issue_brain_passport,
    provision_brain_bound_workforce,
    validate_brain_passport,
)
from aureon.autonomous.aureon_own_model_resolver import AureonOwnModelBrainResolver
from aureon.inhouse_ai import llm_adapter
from aureon.inhouse_ai.llm_adapter import (
    AUREON_OWN_DEFAULT_BASE_URL,
    AUREON_OWN_DEFAULT_MODEL,
    AureonAnthropicAdapter,
    AureonLocalAdapter,
    AureonStubAdapter,
    LLMResponse,
    build_voice_adapter,
)
from aureon.operator import providers
from aureon.operator.grounded_action import GroundedActionGate


def _clear_http_guards(monkeypatch):
    for name in (
        "AUREON_AUDIT_MODE",
        "AUREON_LLM_OFFLINE",
        "AUREON_DISABLE_LLM_HTTP",
    ):
        monkeypatch.delenv(name, raising=False)


def test_local_adapter_defaults_to_own_model_not_ollama(monkeypatch):
    _clear_http_guards(monkeypatch)
    monkeypatch.delenv("AUREON_OWN_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("AUREON_OWN_LLM_MODEL", raising=False)
    monkeypatch.setenv("AUREON_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("AUREON_LLM_MODEL", "llama3")

    adapter = AureonLocalAdapter()

    assert adapter.base_url == "http://127.0.0.1:11435/v1"
    assert adapter.model == "aureon-7b-v65k"
    assert adapter._model_pinned is True


def test_non_own_openai_compatible_route_cannot_make_http_calls(monkeypatch):
    _clear_http_guards(monkeypatch)
    adapter = AureonLocalAdapter(
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key="not-a-real-secret",
    )
    calls = []
    monkeypatch.setattr(adapter, "_http_post", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(adapter, "_http_get", lambda *a, **k: calls.append((a, k)))

    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert response.stop_reason == "error"
    assert response.raw["error"] == "aureon_own_model_required"
    assert adapter.health_check() is False
    assert calls == []


@pytest.mark.parametrize(
    ("base_url", "model"),
    [
        ("https://api.openai.com/v1", "aureon-7b-v65k"),
        ("http://localhost:11435/v1", "aureon-7b-v65k"),
        ("http://127.0.0.1:11435/v1", "gpt-4o-mini"),
        ("http://127.0.0.1:11434/v1", "aureon-7b-v65k"),
        ("http://127.0.0.1:11435/v1?redirect=https://api.openai.com", "aureon-7b-v65k"),
    ],
)
def test_own_route_environment_cannot_authorize_external_or_substitute_models(
    monkeypatch,
    base_url,
    model,
):
    _clear_http_guards(monkeypatch)
    monkeypatch.setenv("AUREON_OWN_LLM_BASE_URL", base_url)
    monkeypatch.setenv("AUREON_OWN_LLM_MODEL", model)
    adapter = llm_adapter._aureon_own_adapter()
    calls = []
    monkeypatch.setattr(adapter, "_http_post", lambda *a, **k: calls.append((a, k)))
    monkeypatch.setattr(adapter, "_http_get", lambda *a, **k: calls.append((a, k)))

    response = adapter.prompt([{"role": "user", "content": "ping"}])
    chunks = list(adapter.stream([{"role": "user", "content": "ping"}]))

    assert response.stop_reason == "error"
    assert response.raw["error"] == "aureon_own_model_required"
    assert adapter.health_check() is False
    assert chunks[-1].stop_reason == "error"
    assert calls == []


def test_own_adapter_ignores_legacy_ollama_native_protocol_flag(monkeypatch):
    _clear_http_guards(monkeypatch)
    monkeypatch.delenv("AUREON_OWN_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("AUREON_OWN_LLM_MODEL", raising=False)
    monkeypatch.setenv("AUREON_LLM_PREFER_NATIVE", "1")

    adapter = llm_adapter._aureon_own_adapter()

    assert adapter._prefer_native is False
    assert adapter.strict_loopback_no_redirects is True


@pytest.mark.parametrize("backend", ["ollama", "ollama_hybrid", "anthropic", "brain"])
def test_external_or_non_model_voice_routes_fail_closed(monkeypatch, backend):
    _clear_http_guards(monkeypatch)
    monkeypatch.setenv("AUREON_VOICE_BACKEND", backend)

    adapter = build_voice_adapter()
    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert isinstance(adapter, AureonStubAdapter)
    assert adapter.model == "aureon_own_model_required"
    assert adapter.health_check() is False
    assert response.stop_reason == "error"
    assert "own model" in response.text


def test_provider_registry_contains_only_the_own_model(monkeypatch):
    _clear_http_guards(monkeypatch)

    class OwnAdapter:
        model = "aureon-7b-v65k"

        def health_check(self):
            return True

    own = OwnAdapter()
    monkeypatch.setattr(providers, "_aureon_own_adapter", lambda: own)
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-secret")

    registry = providers.build_registry(force_offline=False)

    assert registry == {"aureon-own": own}


def test_explicit_external_provider_construction_is_disabled():
    adapter = providers.build_adapter(
        "openai",
        api_key="not-a-real-secret",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
    )

    assert isinstance(adapter, AureonStubAdapter)
    assert adapter.model == "aureon_own_model_required"
    assert adapter.health_check() is False


def test_explicit_provider_entries_fail_closed_without_external_transport():
    registry = providers.build_provider_set_from_entries({
        "openai": {
            "enabled": True,
            "api_key": "not-a-real-secret",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
        },
        "ollama": {
            "enabled": True,
            "api_key": "not-a-real-secret",
            "base_url": "https://ollama.com/v1",
            "model": "cloud-model",
        },
    })

    assert set(registry) == {"openai", "local"}
    for adapter in registry.values():
        assert isinstance(adapter, AureonStubAdapter)
        assert adapter.model == "aureon_own_model_required"
        assert adapter.health_check() is False


def test_action_rationale_calls_own_adapter_not_provider_fanout(monkeypatch):
    _clear_http_guards(monkeypatch)

    class OwnAdapter:
        model = "aureon-7b-v65k"

        def __init__(self):
            self.calls = []

        def prompt(self, messages, **kwargs):
            self.calls.append((messages, kwargs))
            return LLMResponse(text="Hold for review.", model=self.model)

    own = OwnAdapter()
    monkeypatch.setattr(llm_adapter, "_aureon_own_adapter", lambda: own)
    monkeypatch.setattr(
        providers,
        "build_provider_set",
        lambda *a, **k: pytest.fail("external provider fan-out must not be called"),
    )

    text = GroundedActionGate(enable_llm=True)._llm_reason("list_repo", {"path": "."})

    assert text == "Hold for review."
    assert len(own.calls) == 1


def test_own_adapter_strict_transport_and_response_identity(monkeypatch):
    _clear_http_guards(monkeypatch)
    adapter = llm_adapter._aureon_own_adapter()
    assert adapter.strict_loopback_no_redirects is True
    assert adapter._session.trust_env is False

    class Response:
        status_code = 200
        url = AUREON_OWN_DEFAULT_BASE_URL + "/chat/completions"
        is_redirect = False
        is_permanent_redirect = False
        history = ()

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "gpt-4o-mini",
                "choices": [{"message": {"content": "borrowed answer"}}],
            }

    monkeypatch.setattr(adapter, "_http_post", lambda *a, **k: Response())
    response = adapter.prompt([{"role": "user", "content": "ping"}])
    assert response.stop_reason == "error"
    assert response.raw["error"] == "aureon_own_model_response_invalid"
    assert adapter.health_check() is False


def test_own_adapter_accepts_exact_model_and_nonempty_stream(monkeypatch):
    _clear_http_guards(monkeypatch)
    adapter = llm_adapter._aureon_own_adapter()

    class Response:
        status_code = 200
        url = AUREON_OWN_DEFAULT_BASE_URL + "/chat/completions"
        is_redirect = False
        is_permanent_redirect = False
        history = ()

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": AUREON_OWN_DEFAULT_MODEL,
                "choices": [{"message": {"content": "OK"}}],
            }

        def iter_lines(self):
            yield ("data: " + __import__("json").dumps({
                "model": AUREON_OWN_DEFAULT_MODEL,
                "choices": [{"delta": {"content": "OK"}, "finish_reason": "stop"}],
            })).encode("utf-8")

    monkeypatch.setattr(adapter, "_http_post", lambda *a, **k: Response())
    monkeypatch.setattr(adapter, "_http_get", lambda *a, **k: type("Models", (), {
        "status_code": 200,
        "url": AUREON_OWN_DEFAULT_BASE_URL + "/models",
        "is_redirect": False,
        "is_permanent_redirect": False,
        "history": (),
        "json": lambda self: {"data": [{"id": AUREON_OWN_DEFAULT_MODEL}]},
    })())
    response = adapter.prompt([{"role": "user", "content": "ping"}])
    assert response.stop_reason == "end_turn"
    assert response.text == "OK"
    chunks = list(adapter.stream([{"role": "user", "content": "ping"}]))
    assert "".join(chunk.text for chunk in chunks) == "OK"
    assert chunks[-1].done is True
    assert chunks[-1].stop_reason == "stop"
    assert adapter.health_check() is True


def test_own_adapter_rejects_streaming_identity_mismatch(monkeypatch):
    _clear_http_guards(monkeypatch)
    adapter = llm_adapter._aureon_own_adapter()

    class Response:
        url = AUREON_OWN_DEFAULT_BASE_URL + "/chat/completions"
        is_redirect = False
        is_permanent_redirect = False
        history = ()

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield b'data: {"model":"gpt-4o-mini","choices":[{"delta":{"content":"bad"}}]}'

    monkeypatch.setattr(adapter, "_http_post", lambda *a, **k: Response())
    chunks = list(adapter.stream([{"role": "user", "content": "ping"}]))
    assert chunks == [chunk for chunk in chunks if chunk.done]
    assert len(chunks) == 1
    assert chunks[0].stop_reason == "error"
    assert "identity mismatch" in chunks[0].text


    class FakeAdapter:
        model = AUREON_OWN_DEFAULT_MODEL
        calls = 0

        def health_check(self):
            self.calls += 1
            return True

    field = SimpleNamespace(
        available=True,
        receipt_id="hnc:live_field:test",
        coherence_gamma=0.9,
        consciousness_psi=0.8,
        lambda_t=1.2,
        source_timestamp=1000.0,
    )
    adapter = FakeAdapter()
    resolver = AureonOwnModelBrainResolver(
        adapter=adapter, field_reader=lambda: field, clock=lambda: 1001.0
    )
    brain = resolver.resolve("coding")
    passport = _issue_brain_passport("agent", "Implementation Worker", "coding", brain)

    assert adapter.calls == 1
    assert brain.provider_mode == "aureon_own_model"
    assert brain.model == AUREON_OWN_DEFAULT_MODEL
    assert brain.routing_receipt_id.startswith("aureon-own:hnc-route:")
    assert passport.brain_ready is True
    assert validate_brain_passport(passport) is True
    assert passport.action_eligible is False
    assert passport.economic_eligible is False

    field.available = False
    unresolved = AureonOwnModelBrainResolver(
        adapter=adapter, field_reader=lambda: field, clock=lambda: 1002.0
    ).resolve("coding")
    held = _issue_brain_passport("agent", "Implementation Worker", "coding", unresolved)
    assert held.status == "no_data"
    assert held.brain_ready is False
    assert validate_brain_passport(held) is True


def test_workforce_default_own_model_absence_is_explicit_hold(monkeypatch):
    _clear_http_guards(monkeypatch)
    monkeypatch.setenv("AUREON_OWN_LLM_BASE_URL", AUREON_OWN_DEFAULT_BASE_URL)
    monkeypatch.setenv("AUREON_OWN_LLM_MODEL", AUREON_OWN_DEFAULT_MODEL)
    monkeypatch.setenv("AUREON_LLM_PROBE_TIMEOUT_S", "1")
    workforce = provision_brain_bound_workforce(
        role_brain_lanes={"Worker": "coding"},
        process_brain_bindings={"process:worker": ("coding", "Worker")},
    )
    report = workforce.report()

    assert report["status"] == "no_data"
    assert report["ready"] is False
    assert report["provider_mode"] == "hold"
    assert report["agent_brain_count"] == 1
    assert report["process_brain_count"] == 1
    assert report["brain_fabric_ready"] is False
    assert report["unready_agents"] == ["Worker"]
    assert report["unready_processes"] == ["process:worker"]
    assert report["action_eligible"] is False
    assert report["economic_eligible"] is False


def test_anthropic_adapter_is_retained_only_as_a_disabled_boundary(monkeypatch):
    _clear_http_guards(monkeypatch)
    adapter = AureonAnthropicAdapter(api_key="not-a-real-secret")

    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert response.stop_reason == "error"
    assert response.raw["error"] == "aureon_own_model_required"
    assert adapter.health_check() is False
    assert adapter._client is None
