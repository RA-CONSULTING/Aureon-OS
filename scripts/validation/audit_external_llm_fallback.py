#!/usr/bin/env python3
"""Audit Aureon's external LLM routing without exposing credential material.

The static pass proves that repo consumers converge on the shared adapter,
operator-provider, Ollama bridge, or legacy Sero surface. ``--live`` additionally
checks the configured cloud route and performs small native and OpenAI-compatible
completions. It never executes tools, trading, payments, filings, or local actions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


ROUTE_MARKERS = (
    "AureonLocalAdapter(",
    "AureonHybridAdapter(",
    "OllamaBridge(",
    "OllamaLLMAdapter(",
    "OllamaModelSwitchboard(",
    "HNCPhiOllamaSwarm(",
    "build_voice_adapter(",
    "build_provider_set(",
    "SeroClient(",
    "fetchExternalLlm(",
    "callOllamaCloud(",
)

DIRECT_LLM_PATTERN = re.compile(
    r"/v1/chat/completions|/chat/completions|:generateContent|/api/chat|/api/generate"
)

DIRECT_HTTP_MARKERS = (
    "requests.post",
    "_requests.post",
    "_req.post",
    "self._session.post",
    "session.post",
    "self._post(",
    "self._post_stream(",
    "fetch(",
    "axios.post",
)

APPROVED_DIRECT_SURFACES = {
    "aureon/inhouse_ai/llm_adapter.py",
    "aureon/integrations/ollama/ollama_bridge.py",
    "aureon/operator/providers.py",
    "aureon/queen/self_enhancement_engine.py",
    "aureon/utils/aureon_sero_client.py",
    "aureon/vault/ui/server.py",
    "deploy/cloudflare/aureon_murge_worker/index.mjs",
    "flameborn/server.mjs",
    "flameborn/workers/index.mjs",
    "integrations/aureon_murge/web_app/server.mjs",
    "supabase/functions/_shared/external_llm_fallback.ts",
}

ARCHIVAL_PREFIXES = ("archive/", "imports/", "queen_backups/")

LOCAL_ONLY_DIRECT_SURFACES = {
    "aureon/command_centers/aureon_warzone_dashboard.py",
    "aureon/integrations/wiring.py",
    "flameborn/script.js",
    "flameborn/scripts/aureon_cli.mjs",
    "integrations/aureon_murge/web_app/script.js",
    "scripts/aureon_murge/aureon_cli.mjs",
    "scripts/validation/audit_external_llm_fallback.py",
}

TRUSTED_SAME_ORIGIN_WORKER_PROXIES = {
    "flameborn/cloudflare-ui/app.js",
    "flameborn/dist-workers/app.js",
}

_FORBIDDEN_BROWSER_PROVIDER_HOSTS = (
    "ollama.com",
    "api.openai.com",
    "openrouter.ai",
    "generativelanguage.googleapis.com",
    "api.x.ai",
    "api-inference.huggingface.co",
)


def _is_trusted_same_origin_worker_proxy(relative: str, source: str) -> bool:
    """Recognize only the exact authenticated Worker console proxy contract."""

    if relative not in TRUSTED_SAME_ORIGIN_WORKER_PROXIES:
        return False
    required = (
        'const ALLOWED_API_ROUTES = new Set(["/api/chat", "/api/aureon/status"]);',
        "if (!ALLOWED_API_ROUTES.has(path))",
        "if (!token)",
        "new URL(path, window.location.href)",
        "target.origin !== window.location.origin",
        'headers.set("Authorization", `Bearer ${token}`)',
        "fetch(target.href, { ...options, headers })",
    )
    lowered = source.lower()
    return all(marker in source for marker in required) and not any(
        host in lowered for host in _FORBIDDEN_BROWSER_PROVIDER_HOSTS
    )


def _source_files() -> list[Path]:
    extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
    files: list[Path] = []
    files.extend(path for path in REPO_ROOT.rglob("*") if path.suffix.lower() in extensions)
    return sorted(
        path
        for path in files
        if not any(
            part in {".git", ".venv", "node_modules", "__pycache__", "tests", "dist", "build"}
            for part in path.parts
        )
    )


def static_inventory() -> dict[str, Any]:
    consumers: dict[str, list[str]] = {}
    direct: list[str] = []
    source_files = _source_files()
    for path in source_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        markers = sorted(marker for marker in ROUTE_MARKERS if marker in text)
        if markers:
            consumers[rel] = markers
        if DIRECT_LLM_PATTERN.search(text) and any(marker in text for marker in DIRECT_HTTP_MARKERS):
            direct.append(rel)
    archived = sorted(path for path in set(direct) if path.startswith(ARCHIVAL_PREFIXES))
    local_only = sorted(set(direct) & LOCAL_ONLY_DIRECT_SURFACES)
    worker_proxies = sorted(
        rel
        for rel in set(direct) & TRUSTED_SAME_ORIGIN_WORKER_PROXIES
        if _is_trusted_same_origin_worker_proxy(
            rel,
            (REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace"),
        )
    )
    unexpected = sorted(
        set(direct)
        - APPROVED_DIRECT_SURFACES
        - set(archived)
        - set(local_only)
        - set(worker_proxies)
    )
    return {
        "source_file_count": len(source_files),
        "consumer_file_count": len(consumers),
        "consumers": consumers,
        "approved_direct_surfaces": sorted(set(direct) & APPROVED_DIRECT_SURFACES),
        "archival_direct_surfaces": archived,
        "local_only_direct_surfaces": local_only,
        "trusted_same_origin_worker_proxies": worker_proxies,
        "unexpected_direct_llm_surfaces": unexpected,
        "all_discovered_calls_centralized": not unexpected,
    }


def _adapter_view(adapter: Any) -> dict[str, Any]:
    local = getattr(adapter, "local", adapter)
    bridge = getattr(local, "bridge", None)
    return {
        "adapter": type(adapter).__name__,
        "model": str(
            getattr(local, "model", "")
            or getattr(local, "_model", "")
            or getattr(local, "chat_model", "")
            or getattr(bridge, "chat_model", "")
            or ""
        ),
        "base_url": str(
            getattr(local, "base_url", "")
            or getattr(bridge, "base_url", "")
            or ""
        ),
    }


def runtime_inventory(*, live: bool) -> dict[str, Any]:
    from aureon.accounting.throne_agent import ThroneCategorizer
    from aureon.core.aureon_env import bootstrap_credentials
    from aureon.inhouse_ai.llm_adapter import (
        build_voice_adapter,
    )
    from aureon.integrations.ollama import OllamaBridge, OllamaModelSwitchboard, ollama_config_snapshot
    from aureon.operator.providers import build_provider_set, describe_provider_set
    from aureon.utils.aureon_sero_client import SeroClient

    bootstrap_credentials(REPO_ROOT)
    config = ollama_config_snapshot()
    bridge = OllamaBridge()
    switchboard = OllamaModelSwitchboard(bridge=bridge)
    nerve_bridge, general_selection = switchboard.bridge_for("general")
    local, compatible_selection = switchboard.compatible_adapter_for("general")
    hybrid, hybrid_selection = switchboard.hybrid_adapter_for("general")
    voice = build_voice_adapter(lane="general")
    provider_set = build_provider_set(force_offline=not live)
    sero = SeroClient()
    throne = ThroneCategorizer()
    switchboard_snapshot = switchboard.snapshot()

    result: dict[str, Any] = {
        "config": config,
        "routes": {
            "local_adapter": _adapter_view(local),
            "hybrid_adapter": _adapter_view(hybrid),
            "voice_adapter": _adapter_view(voice),
            "native_bridge": _adapter_view(bridge),
            "model_switchboard": switchboard_snapshot,
            "active_general_nerve": general_selection.to_dict(),
            "compatible_general_nerve": compatible_selection.to_dict(),
            "hybrid_general_nerve": hybrid_selection.to_dict(),
            "operator_providers": describe_provider_set(provider_set),
            "sero": {
                "enabled": bool(sero.enabled),
                "route": str(sero.route),
                "provider_enabled": bool(sero.provider_enabled),
                "fallback_enabled": bool(sero.fallback_enabled),
            },
            "accounting_throne": _adapter_view(throne.adapter),
        },
        "live": bool(live),
        "checks": {},
    }
    if not live:
        return result

    model = general_selection.model
    native = nerve_bridge.chat(
        [{"role": "user", "content": "Reply with AUREON_NATIVE_OK only."}],
        model=model or None,
        options={"num_predict": 48, "temperature": 0},
    )
    native_text = str((native.get("message") or {}).get("content") or "").strip()
    compatible = local.prompt(
        [{"role": "user", "content": "Reply with AUREON_COMPAT_OK only."}],
        max_tokens=48,
        temperature=0,
    )
    # This is an advisory classification only; it does not post accounting data.
    throne_code = throne.decide("Interest received", 125)
    result["checks"] = {
        "native_health": nerve_bridge.health_check(max_age_s=0),
        "switchboard_catalog_live": bool(
            switchboard_snapshot.get("reachable") and switchboard_snapshot.get("catalog_size")
        ),
        "native_completion_visible": bool(native_text),
        "compatible_health": local.health_check(),
        "compatible_completion_visible": bool(
            str(compatible.text or "").strip() and compatible.stop_reason != "error"
        ),
        "compatible_stop_reason": compatible.stop_reason,
        "hybrid_health": hybrid.health_check(),
        "voice_health": voice.health_check(),
        "operator_provider_count": len(provider_set),
        "operator_has_ollama_fallback": "local" in provider_set,
        "sero_fallback_ready": bool(sero.enabled and sero.route in {"digitalocean_agent", "ollama_cloud"}),
        "accounting_short_task_returned": throne_code == "4200",
    }
    result["all_live_checks_passed"] = all(
        value is True
        for key, value in result["checks"].items()
        if key not in {"operator_provider_count", "compatible_stop_reason"}
    ) and int(result["checks"]["operator_provider_count"]) > 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="perform small authenticated cloud completions")
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    args = parser.parse_args()

    report = {
        "schema_version": "aureon-external-llm-fallback-audit-v1",
        "repo_root": str(REPO_ROOT),
        "static": static_inventory(),
        "runtime": runtime_inventory(live=args.live),
    }
    report["ok"] = bool(
        report["static"]["all_discovered_calls_centralized"]
        and (
            report["runtime"].get("all_live_checks_passed")
            if args.live
            else report["runtime"]["config"].get("api_key_configured")
        )
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        target = args.output.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
