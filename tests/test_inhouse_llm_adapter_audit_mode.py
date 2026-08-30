import logging

from aureon.inhouse_ai.llm_adapter import (
    AureonBrainAdapter,
    AureonHybridAdapter,
    LLMResponse,
    AureonLocalAdapter,
    build_voice_adapter,
)


def test_audit_mode_disables_local_llm_http(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.delenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", raising=False)

    adapter = AureonLocalAdapter()
    response = adapter.prompt([{"role": "user", "content": "ping"}])

    assert response.stop_reason == "error"
    assert "LLM HTTP disabled" in response.text
    assert adapter.health_check() is False


def test_hybrid_adapter_uses_brain_in_audit_mode(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.delenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", raising=False)

    adapter = AureonHybridAdapter()
    response = adapter.prompt([{"role": "user", "content": "analyse BTCUSDT exposure"}])

    assert response.model == "aureon-brain-v1"
    assert "AureonBrain" in response.text


def test_voice_adapter_can_select_ollama_cognitive_hybrid(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.delenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", raising=False)
    monkeypatch.setenv("AUREON_VOICE_BACKEND", "ollama_hybrid")

    adapter = build_voice_adapter()
    response = adapter.prompt([{"role": "user", "content": "connect Ollama and Aureon cognition"}])

    assert isinstance(adapter, AureonHybridAdapter)
    assert adapter.model.startswith("aureon-ollama-hybrid")
    assert response.model == "aureon-brain-v1"


def test_default_voice_adapter_prefers_hybrid_when_local_llm_is_allowed(monkeypatch):
    monkeypatch.delenv("AUREON_VOICE_BACKEND", raising=False)
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", "1")
    # the suite exports AUREON_LLM_OFFLINE=1, which (correctly) trumps the
    # audit-allow flag; these tests patch every HTTP seam, so clear it here
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)

    adapter = build_voice_adapter()

    assert isinstance(adapter, AureonHybridAdapter)
    assert adapter.model.startswith("aureon-ollama-hybrid")


def test_hybrid_adapter_weaves_small_ollama_shards(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", "1")
    # the suite exports AUREON_LLM_OFFLINE=1, which (correctly) trumps the
    # audit-allow flag; these tests patch every HTTP seam, so clear it here
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.setenv("AUREON_OLLAMA_CONTEXT_WEAVER", "1")
    monkeypatch.setenv("AUREON_OLLAMA_WEAVER_SHARD_TOKENS", "64")
    monkeypatch.setenv("AUREON_OLLAMA_WEAVER_SHARD_LIMIT", "3")
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)
    monkeypatch.setattr(AureonBrainAdapter, "health_check", lambda self: False)

    calls = []

    def fake_prompt(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **kwargs):
        calls.append({"messages": messages, "system": system, "max_tokens": max_tokens})
        name = ["intent", "evidence", "draft"][len(calls) - 1]
        return LLMResponse(
            text=f"{name} shard answer",
            stop_reason="end_turn",
            usage={"total_tokens": 5},
            model="llama3:latest",
        )

    monkeypatch.setattr(AureonLocalAdapter, "prompt", fake_prompt)

    adapter = AureonHybridAdapter(model="llama3:latest")
    response = adapter.prompt(
        [{"role": "user", "content": "Use Aureon cognition and Ollama together without overflowing context."}],
        system="Aureon cockpit evidence is live.",
        max_tokens=120,
    )

    assert len(calls) == 3
    assert response.model == "aureon-ollama-weaver:llama3:latest"
    assert response.raw["weaver"] is True
    assert response.usage["weaver_shards"] == 3
    assert "draft shard answer" in response.text


def test_hybrid_adapter_compiles_weaver_shards_without_leaking_packet_scaffold(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", "1")
    # the suite exports AUREON_LLM_OFFLINE=1, which (correctly) trumps the
    # audit-allow flag; these tests patch every HTTP seam, so clear it here
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.setenv("AUREON_OLLAMA_CONTEXT_WEAVER", "1")
    monkeypatch.setenv("AUREON_OLLAMA_WEAVER_SHARD_LIMIT", "3")
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)
    monkeypatch.setattr(AureonBrainAdapter, "health_check", lambda self: False)

    shard_text = [
        "The operator is asking what Aureon can do.",
        "Phi Bridge ready. Hub ready. Adapter model AureonHybrid.",
        "I can scope jobs, recruit workers, build code and UI, run proof, and hold unsafe actions",
    ]

    def fake_prompt(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **kwargs):
        index = fake_prompt.calls
        fake_prompt.calls += 1
        return LLMResponse(
            text=shard_text[index],
            stop_reason="max_tokens" if index == 2 else "end_turn",
            usage={"total_tokens": 5},
            model="llama3:latest",
        )

    fake_prompt.calls = 0
    monkeypatch.setattr(AureonLocalAdapter, "prompt", fake_prompt)

    adapter = AureonHybridAdapter(model="llama3:latest")
    response = adapter.prompt(
        [{"role": "user", "content": "what can you do"}],
        system="Aureon cockpit evidence is live.",
        max_tokens=120,
    )

    assert response.raw["weaver"] is True
    assert "I can run Aureon" in response.text
    assert "Intent packet" not in response.text
    assert "Evidence packet" not in response.text
    assert "Draft packet" not in response.text
    assert "context-weaver path" not in response.text


def test_hybrid_adapter_rejects_boilerplate_weaver_draft_for_cockpit_status(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", "1")
    # the suite exports AUREON_LLM_OFFLINE=1, which (correctly) trumps the
    # audit-allow flag; these tests patch every HTTP seam, so clear it here
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.setenv("AUREON_OLLAMA_CONTEXT_WEAVER", "1")
    monkeypatch.setenv("AUREON_OLLAMA_WEAVER_SHARD_LIMIT", "3")
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)
    monkeypatch.setattr(AureonBrainAdapter, "health_check", lambda self: False)

    shard_text = [
        "The operator is asking for the current coding cockpit status.",
        "Status ready for client. Scope ready for client. Route clean true.",
        "Aureon will verify and compose.",
    ]

    def fake_prompt(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **kwargs):
        index = fake_prompt.calls
        fake_prompt.calls += 1
        return LLMResponse(
            text=shard_text[index],
            stop_reason="end_turn",
            usage={"total_tokens": 5},
            model="llama3:latest",
        )

    fake_prompt.calls = 0
    monkeypatch.setattr(AureonLocalAdapter, "prompt", fake_prompt)

    adapter = AureonHybridAdapter(model="llama3:latest")
    response = adapter.prompt(
        [{"role": "user", "content": "What can you see in the coding cockpit right now?"}],
        system="Aureon cockpit evidence is live.",
        max_tokens=120,
    )

    assert response.raw["weaver"] is True
    assert "I can see the coding cockpit" in response.text
    assert "Status ready for client" in response.text
    assert "Aureon will verify and compose" not in response.text
    assert "Intent packet" not in response.text


def test_hybrid_adapter_can_disable_context_weaver(monkeypatch):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    monkeypatch.setenv("AUREON_LLM_ALLOW_HTTP_IN_AUDIT", "1")
    # the suite exports AUREON_LLM_OFFLINE=1, which (correctly) trumps the
    # audit-allow flag; these tests patch every HTTP seam, so clear it here
    monkeypatch.delenv("AUREON_LLM_OFFLINE", raising=False)
    monkeypatch.delenv("AUREON_DISABLE_LLM_HTTP", raising=False)
    monkeypatch.setenv("AUREON_OLLAMA_CONTEXT_WEAVER", "0")
    monkeypatch.setattr(AureonLocalAdapter, "health_check", lambda self: True)
    monkeypatch.setattr(AureonBrainAdapter, "health_check", lambda self: False)

    calls = []

    def fake_prompt(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **kwargs):
        calls.append(messages)
        return LLMResponse(text="single local answer", model="llama3:latest")

    monkeypatch.setattr(AureonLocalAdapter, "prompt", fake_prompt)

    adapter = AureonHybridAdapter(model="llama3:latest")
    response = adapter.prompt(
        [{"role": "user", "content": "Use the normal local model path."}],
        max_tokens=120,
    )

    assert len(calls) == 1
    assert response.model == "llama3:latest"
    assert response.text == "single local answer"


def test_brain_adapter_matches_current_decide_signature(monkeypatch, caplog):
    monkeypatch.setenv("AUREON_AUDIT_MODE", "1")
    adapter = AureonBrainAdapter()

    with caplog.at_level(logging.WARNING, logger="aureon.inhouse_ai.llm"):
        response = adapter.prompt([{"role": "user", "content": "analyse BTCUSDT exposure"}])

    assert response.model == "aureon-brain-v1"
    assert '"source": "AureonBrain"' in response.text
    assert not any("AureonBrain reasoning failed" in r.message for r in caplog.records)
