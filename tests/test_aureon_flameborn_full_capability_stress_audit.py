from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_flameborn_full_capability_stress_audit import (
    REQUIRED_STATUS_IDS,
    build_and_write_flameborn_full_capability_stress_audit,
    build_flameborn_full_capability_stress_audit,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _json(path: Path, payload: dict) -> None:
    _write(path, json.dumps(payload))


def _seed_root(root: Path, *, unsafe_electron: bool = False, missing_guards: bool = False) -> None:
    web_server = """
const MURGE_HOST_TERMINAL_ENABLED = process.env.MURGE_HOST_TERMINAL_ENABLED;
const MURGE_SANDBOX_ENABLED = process.env.MURGE_SANDBOX_ENABLED;
function allowTerminalRequest(req) { return true; }
function isTrustedTerminalOrigin(req) { return true; }
async function attachSandboxTerminal(ws, req) { if (!allowTerminalRequest(req) || !isTrustedTerminalOrigin(req)) return; }
server.on("upgrade", (req, socket, head) => { if (!allowTerminalRequest(req) || !isTrustedTerminalOrigin(req)) return; });
"""
    runtime_server = """
const HOST_TERMINAL_ENABLED = true;
const SANDBOX_ENABLED = true;
function allowRequest(req) { return true; }
function isTrustedOrigin(req) { return true; }
server.on('upgrade', async (req, socket, head) => { if (!allowRequest(req) || !isTrustedOrigin(req)) return; });
"""
    if missing_guards:
        web_server = "const server = {};"
        runtime_server = "const app = {};"
    _write(root / "integrations/aureon_murge/web_app/server.mjs", web_server)
    _write(root / "integrations/aureon_murge/web_app/index.html", "<html><button id='sendBtn'>Send</button></html>")
    _write(root / "integrations/aureon_murge/web_app/script.js", "console.log('safe ui');")
    _write(root / "integrations/aureon_murge/runtime/server.mjs", runtime_server)
    main = (
        "contextIsolation: true\nnodeIntegration: false\nsandbox: true\n"
        "function isAllowedExternalUrl(){}\nshell.openExternal(url)\n"
        "mainWindow.webContents.setWindowOpenHandler(()=>({action:'deny'}));\n"
        "ensureServices(); const webReachable = true; const runtimeReachable = true;\n"
    )
    if unsafe_electron:
        main = "nodeIntegration: true\n"
    _write(root / "integrations/aureon_murge/desktop/main.cjs", main)
    _write(root / "integrations/aureon_murge/desktop/preload.cjs", "flameborn:get-status\nflameborn:restart-service\n")
    _write(root / "integrations/aureon_murge/desktop/runtime-manager.cjs", "FLAMEBORN_DESKTOP_AUTO_AUREON\n")
    _write(root / "integrations/aureon_murge/desktop/package.json", "{}")
    for name in ("runtime", "web_app", "desktop"):
        _json(
            root / f"integrations/aureon_murge/logs/activation/npm-audit-{name}.json",
            {"metadata": {"vulnerabilities": {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0, "total": 0}}},
        )
    _json(
        root / "frontend/public/aureon_live_trade_signal_fabric.json",
        {"status": "trade_flow_active", "summary": {"thoughtbus_receiving": True, "mycelium_receiving": True}},
    )
    _json(root / "frontend/public/aureon_live_trade_signal_fabric_stress_audit.json", {"status": "trade_flow_active", "summary": {}})
    _json(root / "frontend/public/aureon_murge_runtime_activation_stress_audit.json", {"status": "murge_runtime_activation_ready", "summary": {}})


def _probe(url: str) -> dict:
    data = {}
    if url.endswith("/api/aureon/status"):
        data = {"activation": {"noTradingGateBypass": True}, "configured": True}
    elif url.endswith("/api/aureon/supervisor"):
        data = {
            "supervisorConnected": True,
            "phiBridgeConnected": True,
            "noTradingGateBypass": True,
            "liveGates": {
                "orderIntentPublishEnabled": True,
                "executorEnabled": True,
                "liveEnabled": True,
                "realOrdersDisabled": False,
                "exchangeMutationsDisabled": False,
                "tradePathState": "available",
            },
        }
    elif url.endswith("/api/runtime/info"):
        data = {"noTradingGateBypass": True, "guardedActivation": True}
    elif url.endswith("/api/terminal/status") or url.endswith("/api/sandbox/status"):
        data = {"enabled": False, "guardedActivation": True, "remoteAccess": False}
    elif url.endswith("/api/aureon/systems"):
        data = {"capabilities": {"detected": 13, "total": 13}}
    elif url.endswith("/health") or url.endswith("/api/phi-bridge/status"):
        data = {"status": "ok"}
    return {"url": url, "ok": True, "status_code": 200, "round_trip_ms": 1.0, "data": data}


def _post_probe(url: str, payload: dict) -> dict:
    return {"url": url, "ok": True, "status_code": 200, "round_trip_ms": 1.0, "data": {"reply": "health ok", "bridgeConnected": True}}


def test_full_capability_audit_certifies_all_required_rows(tmp_path: Path) -> None:
    _seed_root(tmp_path)

    report = build_flameborn_full_capability_stress_audit(
        root=tmp_path,
        env={},
        http_probe=_probe,
        post_probe=_post_probe,
    )

    assert report["schema_version"] == "aureon-flameborn-full-capability-stress-v1"
    assert report["status"] == "flameborn_full_capability_certified"
    row_ids = {row["id"] for row in report["status_rows"]}
    assert set(REQUIRED_STATUS_IDS).issubset(row_ids)
    assert report["summary"]["required_status_pass_count"] == report["summary"]["required_status_count"]
    assert report["summary"]["thoughtbus_receiving"] is True
    assert report["summary"]["mycelium_receiving"] is True
    assert report["summary"]["no_trading_gate_bypass"] is True


def test_full_capability_audit_blocks_unavailable_services(tmp_path: Path) -> None:
    _seed_root(tmp_path)

    def down(url: str) -> dict:
        return {"url": url, "ok": False, "status_code": 0, "error": "down"}

    report = build_flameborn_full_capability_stress_audit(root=tmp_path, env={}, http_probe=down, post_probe=_post_probe)

    assert "web_health_unavailable" in report["blockers"]
    assert "runtime_health_unavailable" in report["blockers"]
    assert "supervisor_unavailable" in report["blockers"]
    assert report["status"] == "flameborn_full_capability_attention"


def test_full_capability_audit_blocks_cloud_provider_and_unsafe_electron(tmp_path: Path) -> None:
    _seed_root(tmp_path, unsafe_electron=True)

    report = build_flameborn_full_capability_stress_audit(
        root=tmp_path,
        env={
            "HOST": "0.0.0.0",
            "FLAMEBORN_RUNTIME_HOST": "0.0.0.0",
            "MURGE_CLOUDFLARE_ENABLED": "1",
            "MURGE_PROVIDER_API_ENABLED": "1",
            "OPENAI_API_KEY": "present-but-not-read",
        },
        http_probe=_probe,
        post_probe=_post_probe,
    )

    assert "web_health_unavailable" in report["blockers"]
    assert "runtime_health_unavailable" in report["blockers"]
    assert "desktop_security_review_required" in report["blockers"]
    assert "cloudflare_enabled_requires_review" in report["blockers"]
    assert "provider_api_credentials_present" in report["blockers"]


def test_full_capability_audit_blocks_missing_guards_and_high_npm(tmp_path: Path) -> None:
    _seed_root(tmp_path, missing_guards=True)
    _json(
        tmp_path / "integrations/aureon_murge/logs/activation/npm-audit-web_app.json",
        {"metadata": {"vulnerabilities": {"high": 1, "critical": 0, "total": 1}}},
    )

    report = build_flameborn_full_capability_stress_audit(root=tmp_path, env={}, http_probe=_probe, post_probe=_post_probe)

    assert "terminal_guard_missing" in report["blockers"]
    assert "sandbox_guard_missing" in report["blockers"]
    assert "websocket_origin_guard_missing" in report["blockers"]
    assert "npm_audit_high_critical_or_missing" in report["blockers"]


def test_full_capability_audit_writes_public_artifact(tmp_path: Path) -> None:
    _seed_root(tmp_path)

    report = build_and_write_flameborn_full_capability_stress_audit(
        root=tmp_path,
        env={},
        probe_services=False,
        probe_chat=False,
        emit_fabric=False,
    )

    assert report["schema_version"] == "aureon-flameborn-full-capability-stress-v1"
    assert (tmp_path / "frontend/public/aureon_flameborn_full_capability_stress_audit.json").exists()
    assert (tmp_path / "docs/audits/aureon_flameborn_full_capability_stress_audit.md").exists()
