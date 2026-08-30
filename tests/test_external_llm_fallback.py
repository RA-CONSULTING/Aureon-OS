"""Repo-wide external LLM fallback routing tests (offline and secret-safe)."""

from __future__ import annotations

from pathlib import Path

import aureon.ollama_config as ollama_config
from aureon.inhouse_ai import llm_adapter
from aureon.inhouse_ai.llm_adapter import AureonStubAdapter
from aureon.integrations.ollama import ollama_bridge
from aureon.operator import providers
from scripts.validation.audit_external_llm_fallback import (
    _is_trusted_same_origin_worker_proxy,
    static_inventory,
)

_OLLAMA_ENV = (
    "OLLAMA_API_KEY",
    "AUREON_OLLAMA_API_KEY",
    "AUREON_LLM_API_KEY",
    "AUREON_OLLAMA_BASE_URL",
    "AUREON_LLM_BASE_URL",
    "AUREON_LLM_MODEL",
    "AUREON_OLLAMA_MODEL",
    "AUREON_EXTERNAL_LLM_FALLBACK",
    "AUREON_OLLAMA_REASONING_EFFORT",
)


def _clear(monkeypatch) -> None:
    for name in _OLLAMA_ENV:
        monkeypatch.delenv(name, raising=False)


def test_external_fallback_policy_defaults_to_ollama(monkeypatch) -> None:
    _clear(monkeypatch)
    assert ollama_config.resolve_external_llm_fallback() == "ollama"

    monkeypatch.setenv("AUREON_EXTERNAL_LLM_FALLBACK", "ollama_cloud")
    assert ollama_config.resolve_external_llm_fallback() == "ollama"

    monkeypatch.setenv("AUREON_EXTERNAL_LLM_FALLBACK", "off")
    assert ollama_config.resolve_external_llm_fallback() == "none"


def test_cloud_reasoning_defaults_to_visible_output(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.delenv("AUREON_OLLAMA_REASONING_EFFORT", raising=False)
    assert ollama_config.resolve_ollama_reasoning_effort() == "none"

    adapter = llm_adapter.AureonLocalAdapter(
        base_url="https://ollama.com/v1",
        model="cloud-model",
        api_key="test-secret",
    )
    payload = adapter._build_payload(
        [{"role": "user", "content": "Return one label"}],
        "",
        None,
        8,
        0.0,
    )
    assert payload["reasoning_effort"] == "none"

    bridge = ollama_bridge.OllamaBridge(
        base_url="https://ollama.com",
        api_key="test-secret",
        chat_model="cloud-model",
    )
    captured: dict = {}

    def fake_post(path: str, body: dict, timeout=None):
        captured.update({"path": path, "body": body})
        return {"message": {"content": "OK"}, "done": True}

    monkeypatch.setattr(bridge, "_post", fake_post)
    result = bridge.chat([{"role": "user", "content": "Return OK"}])
    assert result["message"]["content"] == "OK"
    assert captured["body"]["think"] is False


def test_forced_runtime_bootstrap_loads_cloud_profile(monkeypatch, tmp_path: Path) -> None:
    _clear(monkeypatch)
    monkeypatch.setattr(ollama_config, "_RUNTIME_BOOTSTRAP_ATTEMPTED", False)
    calls: list[Path] = []

    def fake_bootstrap(root: Path):
        calls.append(Path(root))
        monkeypatch.setenv("AUREON_LLM_BASE_URL", "https://ollama.com/v1")
        monkeypatch.setenv("AUREON_LLM_MODEL", "cloud-model")
        monkeypatch.setenv("OLLAMA_API_KEY", "test-secret")
        return {"ok": True}

    monkeypatch.setattr("aureon.core.aureon_env.bootstrap_credentials", fake_bootstrap)

    snapshot = ollama_config.ensure_ollama_runtime_config(
        force=True,
        repo_root=tmp_path,
    )

    assert calls == [tmp_path]
    assert snapshot["external_fallback"] == "ollama"
    assert snapshot["cloud"] is True
    assert snapshot["api_key_configured"] is True
    assert snapshot["authorization_header_enabled"] is True
    assert "test-secret" not in repr(snapshot)


def test_shared_constructors_request_runtime_bootstrap(monkeypatch) -> None:
    _clear(monkeypatch)
    calls: list[str] = []

    monkeypatch.setattr(
        llm_adapter,
        "ensure_ollama_runtime_config",
        lambda **_kwargs: calls.append("adapter") or {},
    )
    monkeypatch.setattr(
        ollama_bridge,
        "ensure_ollama_runtime_config",
        lambda **_kwargs: calls.append("bridge") or {},
    )

    llm_adapter.AureonLocalAdapter()
    ollama_bridge.OllamaBridge()

    assert calls == ["adapter", "bridge"]


def test_operator_registry_bootstraps_before_default_specs(monkeypatch) -> None:
    _clear(monkeypatch)
    calls: list[str] = []

    def fake_ensure(**_kwargs):
        calls.append("bootstrap")
        monkeypatch.setenv("AUREON_LLM_BASE_URL", "https://ollama.com/v1")
        monkeypatch.setenv("AUREON_LLM_MODEL", "cloud-model")
        monkeypatch.setenv("OLLAMA_API_KEY", "test-secret")
        return {}

    monkeypatch.setattr(providers, "ensure_ollama_runtime_config", fake_ensure)
    monkeypatch.setattr(
        providers,
        "_build_from_spec",
        lambda spec: AureonStubAdapter("ok", model=spec.model) if spec.kind == "local" else None,
    )

    registry = providers.build_registry(force_offline=False)

    assert calls == ["bootstrap"]
    assert set(registry) == {"local"}
    assert registry["local"]._model == "cloud-model"


def test_explicit_anthropic_voice_route_uses_ollama_fallback(monkeypatch) -> None:
    _clear(monkeypatch)
    monkeypatch.setenv("AUREON_VOICE_BACKEND", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class _Healthy:
        def health_check(self) -> bool:
            return True

    class _Fallback:
        def __init__(self) -> None:
            self.local = _Healthy()
            self.model = "ollama-cloud-fallback"

    monkeypatch.setattr(llm_adapter, "AureonHybridAdapter", _Fallback)
    monkeypatch.setattr(llm_adapter, "_llm_http_disabled", lambda: False)

    adapter = llm_adapter.build_voice_adapter()

    assert isinstance(adapter, _Fallback)
    assert adapter.model == "ollama-cloud-fallback"


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
    assert "flameborn/dist-workers/app.js" in inventory["trusted_same_origin_worker_proxies"]
    assert inventory["unexpected_direct_llm_surfaces"] == []
    assert inventory["all_discovered_calls_centralized"] is True
