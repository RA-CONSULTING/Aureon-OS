from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_HOLD = """#!/usr/bin/env node

// Terminal HOLD: operational route is unavailable.
process.exit(2);
"""


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_browser_bundle_contains_no_direct_provider_secret_route():
    utils = _read("frontend/src/workers/sources/aurisUtils.ts")
    sandbox = _read("frontend/src/workers/sources/aurisSandbox.ts")
    assert "api.openai.com" not in utils
    assert "VITE_OPENAI_API_KEY" not in utils + sandbox
    assert "supabase.functions.invoke('auris-classify'" in utils


def test_active_worker_surfaces_have_ollama_fallback():
    surfaces = (
        "deploy/cloudflare/aureon_murge_worker/index.mjs",
        "flameborn/workers/index.mjs",
    )
    for relative in surfaces:
        source = _read(relative)
        assert "callOllamaCloud" in source
        assert "AUREON_EXTERNAL_LLM_FALLBACK" in source
        assert "OLLAMA_API_KEY" in source
        assert "reasoning_effort" in source


def test_node_servers_are_held_and_archives_retain_fallback_source():
    surfaces = (
        (
            "flameborn/server.mjs",
            "docs/archive/flameborn_operational_sources/flameborn_server.mjs.txt",
        ),
        (
            "integrations/aureon_murge/web_app/server.mjs",
            "docs/archive/flameborn_operational_sources/aureon_murge_web_server.mjs.txt",
        ),
    )
    for active_relative, archive_relative in surfaces:
        assert _read(active_relative).replace("\r\n", "\n") == SERVER_HOLD
        archived = _read(archive_relative)
        assert archive_relative.endswith(".mjs.txt")
        assert "callOllamaCloud" in archived
        assert "AUREON_EXTERNAL_LLM_FALLBACK" in archived
        assert "OLLAMA_API_KEY" in archived
        assert "reasoning_effort" in archived


def test_supabase_llm_functions_use_shared_server_side_fallback():
    functions = (
        "ai-commentary",
        "analyze-lighthouse-event",
        "analyze-stargate-patterns",
        "aureon-chat",
        "auris-classify",
        "forecast-coherence",
        "interpret-frequency",
        "primelines-protocol-gateway",
    )
    for name in functions:
        source = _read(f"supabase/functions/{name}/index.ts")
        assert "fetchExternalLlm" in source
        assert "ai.gateway.lovable.dev/v1/chat/completions" not in source

    helper = _read("supabase/functions/_shared/external_llm_fallback.ts")
    assert "https://ollama.com/v1/chat/completions" in helper
    assert "AUREON_EXTERNAL_LLM_FALLBACK" in helper
    assert "reasoning_effort" in helper


def test_auris_edge_function_requires_jwt():
    config = _read("supabase/config.toml")
    assert "[functions.auris-classify]\nverify_jwt = true" in config


def test_structured_supabase_llm_responses_accept_fenced_json():
    helper = _read("supabase/functions/_shared/external_llm_fallback.ts")
    assert "export function parseExternalLlmJson" in helper
    assert "```(?:json)?" in helper

    for name in (
        "analyze-stargate-patterns",
        "auris-classify",
        "forecast-coherence",
        "primelines-protocol-gateway",
    ):
        source = _read(f"supabase/functions/{name}/index.ts")
        assert "parseExternalLlmJson" in source
