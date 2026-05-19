"""Full capability stress audit for the Flameborn/MURGE/Aureon unity shell.

The audit certifies launch visibility and guard state for local Flameborn web,
MURGE runtime, desktop shell readiness, Aureon supervisor, Phi bridge,
ThoughtBus/Mycelium artifacts, terminal/sandbox guards, provider/cloud
boundaries, and live-trading gate visibility. It does not start services,
execute shell commands, read credentials, or mutate broker/trading state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from aureon.trading.live_trade_signal_fabric import publish_trade_flow_event


SCHEMA_VERSION = "aureon-flameborn-full-capability-stress-v1"

DEFAULT_STATE_PATH = Path("state/aureon_flameborn_full_capability_stress_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_flameborn_full_capability_stress_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_flameborn_full_capability_stress_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_flameborn_full_capability_stress_audit.json")

WEB_DIR = Path("integrations/aureon_murge/web_app")
RUNTIME_DIR = Path("integrations/aureon_murge/runtime")
DESKTOP_DIR = Path("integrations/aureon_murge/desktop")
ACTIVATION_LOG_DIR = Path("integrations/aureon_murge/logs/activation")

WEB_STATUS_URL = "http://127.0.0.1:4173/api/aureon/status"
WEB_SUPERVISOR_URL = "http://127.0.0.1:4173/api/aureon/supervisor"
WEB_SYSTEMS_URL = "http://127.0.0.1:4173/api/aureon/systems"
WEB_CHAT_URL = "http://127.0.0.1:4173/api/aureon/chat"
WEB_TERMINAL_STATUS_URL = "http://127.0.0.1:4173/api/terminal/status"
WEB_SANDBOX_STATUS_URL = "http://127.0.0.1:4173/api/sandbox/status"
RUNTIME_HEALTH_URL = "http://127.0.0.1:7331/health"
RUNTIME_INFO_URL = "http://127.0.0.1:7331/api/runtime/info"
RUNTIME_TERMINAL_STATUS_URL = "http://127.0.0.1:7331/api/terminal/status"
RUNTIME_SANDBOX_STATUS_URL = "http://127.0.0.1:7331/api/sandbox/status"
PHI_STATUS_URL = "http://127.0.0.1:13002/api/phi-bridge/status"

REQUIRED_STATUS_IDS = [
    "web_health",
    "runtime_health",
    "desktop_ready",
    "supervisor_connected",
    "phi_status",
    "phi_chat_response",
    "terminal_guard",
    "sandbox_guard",
    "websocket_origin_guard",
    "provider_api_boundary",
    "cloudflare_boundary",
    "npm_audit_state",
    "live_trade_gate_visibility",
    "no_trading_gate_bypass",
]

ONLINE_REQUIREMENTS = [
    {
        "surface": "express_or_node_http_web",
        "source": "https://expressjs.com/en/advanced/best-practice-security.html",
        "requirement": "Reduce fingerprinting, validate inputs, and keep dependency vulnerability evidence visible.",
    },
    {
        "surface": "electron_desktop_shell",
        "source": "https://www.electronjs.org/docs/latest/tutorial/security",
        "requirement": "Renderer uses context isolation, disabled Node integration, sandboxing, IPC allowlists, and external URL controls.",
    },
    {
        "surface": "docker_sandbox_guard",
        "source": "https://docs.docker.com/engine/security/",
        "requirement": "Docker sandbox use remains guarded and least-privilege before command execution is trusted.",
    },
    {
        "surface": "cloudflare_boundary",
        "source": "https://developers.cloudflare.com/workers/wrangler/configuration/",
        "requirement": "Cloudflare config and secrets remain disabled/local-only unless a reviewed deployment gate is enabled.",
    },
    {
        "surface": "websocket_origin_guard",
        "source": "https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html",
        "requirement": "WebSocket upgrades enforce localhost/origin checks before terminal or sandbox sessions attach.",
    },
    {
        "surface": "node_runtime_boundary",
        "source": "https://nodejs.org/en/learn/getting-started/security-best-practices",
        "requirement": "Runtime command surfaces stay explicitly guarded, local-only, and dependency-aware.",
    },
    {
        "surface": "npm_audit_state",
        "source": "https://docs.npmjs.com/cli/v8/commands/npm-audit/",
        "requirement": "npm audit JSON is classified; high/critical rows block full capability certification.",
    },
]

MANUAL_BOUNDARIES = [
    "full capability stress audit observes local services only",
    "no service start or restart is performed by the audit",
    "no terminal or sandbox command execution",
    "no credential read, migration, or reveal",
    "no Cloudflare deploy",
    "no order, close, cancel, credential, or broker mutation",
    "live trading gates are reported, not changed",
]


HttpProbe = Callable[[str], Dict[str, Any]]
PostProbe = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def _default_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "aureon").exists() and (cwd / "frontend").exists():
        return cwd
    return Path(__file__).resolve().parents[2]


def _rooted(root: Path, path: Path | str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    except Exception:
        return ""


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        raw = path.read_bytes()
        for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
            try:
                return json.loads(raw.decode(encoding))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return default
    except Exception:
        return default


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": len(content.encode("utf-8"))}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _localhost(value: Any) -> bool:
    return str(value or "").strip().lower() in {"127.0.0.1", "localhost", "::1"}


def _default_http_probe(url: str) -> Dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=4.0) as response:
            body = response.read(250_000)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
            data: Any = None
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                data = {"raw": body[:2000].decode("utf-8", errors="replace")}
            return {
                "url": url,
                "ok": 200 <= int(response.status) < 500,
                "status_code": int(response.status),
                "round_trip_ms": round(elapsed, 3),
                "data": data,
            }
    except urllib.error.HTTPError as exc:
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
        return {"url": url, "ok": 200 <= int(exc.code) < 500, "status_code": int(exc.code), "round_trip_ms": round(elapsed, 3)}
    except Exception as exc:
        return {"url": url, "ok": False, "status_code": 0, "error": str(exc)}


def _default_post_probe(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=22.0) as response:
            raw = response.read(250_000)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
            data: Any = None
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                data = {"raw": raw[:2000].decode("utf-8", errors="replace")}
            return {
                "url": url,
                "ok": 200 <= int(response.status) < 500,
                "status_code": int(response.status),
                "round_trip_ms": round(elapsed, 3),
                "data": data,
            }
    except urllib.error.HTTPError as exc:
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
        return {"url": url, "ok": 200 <= int(exc.code) < 500, "status_code": int(exc.code), "round_trip_ms": round(elapsed, 3)}
    except Exception as exc:
        return {"url": url, "ok": False, "status_code": 0, "error": str(exc)}


def _row(
    row_id: str,
    label: str,
    *,
    status: str,
    passed: bool,
    evidence: Optional[Dict[str, Any]] = None,
    blocker_id: str = "",
    next_action: str = "",
    severity: str = "blocker",
) -> Dict[str, Any]:
    return {
        "id": row_id,
        "label": label,
        "status": status,
        "passed": bool(passed),
        "severity": "" if passed else severity,
        "blocker_id": "" if passed else blocker_id,
        "next_action": "" if passed else next_action,
        "evidence": evidence or {},
    }


def _npm_audit_rows(root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for label, filename in [
        ("runtime", "npm-audit-runtime.json"),
        ("web_app", "npm-audit-web_app.json"),
        ("desktop", "npm-audit-desktop.json"),
    ]:
        path = _rooted(root, ACTIVATION_LOG_DIR / filename)
        payload = _read_json(path, {})
        vulnerabilities = payload.get("metadata", {}).get("vulnerabilities", {}) if isinstance(payload, dict) else {}
        high = int(vulnerabilities.get("high") or 0) if isinstance(vulnerabilities, dict) else 0
        critical = int(vulnerabilities.get("critical") or 0) if isinstance(vulnerabilities, dict) else 0
        total = int(vulnerabilities.get("total") or 0) if isinstance(vulnerabilities, dict) else 0
        rows.append(
            {
                "id": f"{label}_npm_audit",
                "path": str(path),
                "audit_present": path.exists(),
                "vulnerabilities": vulnerabilities,
                "total_vulnerabilities": total,
                "high_vulnerabilities": high,
                "critical_vulnerabilities": critical,
                "status": "npm_audit_pending" if not path.exists() else "npm_audit_high_or_critical" if high or critical else "npm_audit_classified",
            }
        )
    return rows


def _electron_status(root: Path) -> Dict[str, Any]:
    main = _read_text(_rooted(root, DESKTOP_DIR / "main.cjs"))
    preload = _read_text(_rooted(root, DESKTOP_DIR / "preload.cjs"))
    manager = _read_text(_rooted(root, DESKTOP_DIR / "runtime-manager.cjs"))
    checks = [
        {"check": "context_isolation", "passed": "contextIsolation: true" in main},
        {"check": "node_integration_disabled", "passed": "nodeIntegration: false" in main},
        {"check": "renderer_sandbox_enabled", "passed": "sandbox: true" in main},
        {"check": "ipc_allowlist_present", "passed": "flameborn:get-status" in preload and "flameborn:restart-service" in preload},
        {"check": "external_url_allowlist", "passed": "isAllowedExternalUrl" in main and "shell.openExternal" in main},
        {"check": "window_open_handler", "passed": "setWindowOpenHandler" in main},
        {"check": "desktop_after_health", "passed": "ensureServices" in main and "webReachable" in main and "runtimeReachable" in main},
        {"check": "desktop_auto_aureon_can_be_disabled", "passed": "FLAMEBORN_DESKTOP_AUTO_AUREON" in manager},
    ]
    missing_files = [
        rel.as_posix()
        for rel in [DESKTOP_DIR / "main.cjs", DESKTOP_DIR / "preload.cjs", DESKTOP_DIR / "runtime-manager.cjs", DESKTOP_DIR / "package.json"]
        if not _rooted(root, rel).exists()
    ]
    return {
        "missing_files": missing_files,
        "checks": checks,
        "passed_count": sum(1 for item in checks if item["passed"]),
        "check_count": len(checks),
        "passed": not missing_files and all(item["passed"] for item in checks),
    }


def _websocket_guard_status(root: Path) -> Dict[str, Any]:
    web = _read_text(_rooted(root, WEB_DIR / "server.mjs"))
    runtime = _read_text(_rooted(root, RUNTIME_DIR / "server.mjs"))
    web_pre_upgrade_guard = "server.on(\"upgrade\"" in web and "allowTerminalRequest(req) || !isTrustedTerminalOrigin(req)" in web
    web_attach_guard = "attachSandboxTerminal" in web and "isTrustedTerminalOrigin(req)" in web and "allowTerminalRequest(req)" in web
    runtime_guard = "server.on('upgrade'" in runtime and "!allowRequest(req) || !isTrustedOrigin(req)" in runtime
    return {
        "web_pre_upgrade_guard": web_pre_upgrade_guard,
        "web_attach_guard": web_attach_guard,
        "runtime_upgrade_guard": runtime_guard,
        "passed": (web_pre_upgrade_guard or web_attach_guard) and runtime_guard,
    }


def _terminal_guard_status(root: Path, env: Dict[str, str], probes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    web = _read_text(_rooted(root, WEB_DIR / "server.mjs"))
    runtime = _read_text(_rooted(root, RUNTIME_DIR / "server.mjs"))
    enabled = _truthy(env.get("MURGE_HOST_TERMINAL_ENABLED"))
    code_guard = "MURGE_HOST_TERMINAL_ENABLED" in web and "HOST_TERMINAL_ENABLED" in runtime
    local_guard = "allowTerminalRequest" in web and "allowRequest" in runtime
    remote_off = not _truthy(env.get("TERMINAL_ALLOW_REMOTE")) and not _truthy(env.get("FLAMEBORN_RUNTIME_ALLOW_REMOTE"))
    status_payloads = [probes.get(WEB_TERMINAL_STATUS_URL, {}), probes.get(RUNTIME_TERMINAL_STATUS_URL, {})]
    return {
        "enabled": enabled,
        "code_guard_present": code_guard,
        "local_guard_present": local_guard,
        "remote_access_disabled": remote_off,
        "status_probes": status_payloads,
        "passed": code_guard and local_guard and remote_off,
    }


def _sandbox_guard_status(root: Path, env: Dict[str, str], probes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    web = _read_text(_rooted(root, WEB_DIR / "server.mjs"))
    runtime = _read_text(_rooted(root, RUNTIME_DIR / "server.mjs"))
    enabled = _truthy(env.get("MURGE_SANDBOX_ENABLED"))
    code_guard = "MURGE_SANDBOX_ENABLED" in web and "SANDBOX_ENABLED" in runtime
    local_guard = "allowTerminalRequest" in web and "allowRequest" in runtime
    status_payloads = [probes.get(WEB_SANDBOX_STATUS_URL, {}), probes.get(RUNTIME_SANDBOX_STATUS_URL, {})]
    return {
        "enabled": enabled,
        "code_guard_present": code_guard,
        "local_guard_present": local_guard,
        "status_probes": status_payloads,
        "passed": code_guard and local_guard,
    }


def _trading_mutation_controls(root: Path) -> List[Dict[str, str]]:
    index = _read_text(_rooted(root, WEB_DIR / "index.html"))
    script = _read_text(_rooted(root, WEB_DIR / "script.js"))
    controls: List[Dict[str, str]] = []
    risky_patterns = [
        re.compile(r"\b(buy|sell)\b", re.I),
        re.compile(r"\b(place|submit|send)\s+(live\s+)?order\b", re.I),
        re.compile(r"\b(close|cancel)\s+(position|order|trade)\b", re.I),
        re.compile(r"\b(live\s+)?hedge\s+(order|submit|execute)\b", re.I),
    ]
    for source_name, text in [("index.html", index), ("script.js", script)]:
        for match in re.finditer(r"<button\b[^>]*>(.*?)</button>", text, flags=re.I | re.S):
            label = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if any(pattern.search(label) for pattern in risky_patterns):
                controls.append({"source": source_name, "label": label[:120]})
        for line in text.splitlines():
            if any(pattern.search(line) for pattern in risky_patterns) and "Do not create manual trading controls" not in line:
                if "button" in line.lower() or "addEventListener" in line:
                    controls.append({"source": source_name, "label": line.strip()[:160]})
    return controls[:20]


def _artifact_snapshot(root: Path) -> Dict[str, Any]:
    fabric = _read_json(_rooted(root, "frontend/public/aureon_live_trade_signal_fabric.json"), {})
    fabric_stress = _read_json(_rooted(root, "frontend/public/aureon_live_trade_signal_fabric_stress_audit.json"), {})
    activation = _read_json(_rooted(root, "frontend/public/aureon_murge_runtime_activation_stress_audit.json"), {})
    return {
        "live_signal_fabric": {
            "status": fabric.get("status", "") if isinstance(fabric, dict) else "",
            "thoughtbus_receiving": bool((fabric.get("summary") or {}).get("thoughtbus_receiving")) if isinstance(fabric, dict) else False,
            "mycelium_receiving": bool((fabric.get("summary") or {}).get("mycelium_receiving")) if isinstance(fabric, dict) else False,
        },
        "live_signal_fabric_stress": {
            "status": fabric_stress.get("status", "") if isinstance(fabric_stress, dict) else "",
            "summary": fabric_stress.get("summary", {}) if isinstance(fabric_stress, dict) else {},
        },
        "murge_runtime_activation": {
            "status": activation.get("status", "") if isinstance(activation, dict) else "",
            "summary": activation.get("summary", {}) if isinstance(activation, dict) else {},
        },
    }


def _build_status_rows(
    *,
    root: Path,
    env: Dict[str, str],
    probes: Dict[str, Dict[str, Any]],
    chat_probe: Dict[str, Any],
    artifacts: Dict[str, Any],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    web_status = probes.get(WEB_STATUS_URL, {})
    web_data = web_status.get("data") if isinstance(web_status.get("data"), dict) else {}
    web_ok = bool(web_status.get("ok")) and _localhost(env.get("HOST", "127.0.0.1"))
    rows.append(_row("web_health", "Flameborn web health", status="health_passed" if web_ok else "web_unavailable", passed=web_ok, evidence=web_status, blocker_id="web_health_unavailable", next_action="Start or repair Flameborn web on http://127.0.0.1:4173."))

    runtime_health = probes.get(RUNTIME_HEALTH_URL, {})
    runtime_info = probes.get(RUNTIME_INFO_URL, {})
    runtime_data = runtime_info.get("data") if isinstance(runtime_info.get("data"), dict) else {}
    runtime_ok = bool(runtime_health.get("ok")) and bool(runtime_info.get("ok")) and _localhost(env.get("FLAMEBORN_RUNTIME_HOST", "127.0.0.1"))
    rows.append(_row("runtime_health", "MURGE runtime health", status="health_passed" if runtime_ok else "runtime_unavailable", passed=runtime_ok, evidence={"health": runtime_health, "info": runtime_info}, blocker_id="runtime_health_unavailable", next_action="Start or repair MURGE runtime on http://127.0.0.1:7331."))

    electron = _electron_status(root)
    rows.append(_row("desktop_ready", "Desktop shell security readiness", status="desktop_ready" if electron["passed"] else "desktop_security_attention", passed=electron["passed"], evidence=electron, blocker_id="desktop_security_review_required", next_action="Keep Electron contextIsolation, nodeIntegration=false, sandbox, IPC allowlist, external URL allowlist, and window-open guard passing."))

    supervisor = probes.get(WEB_SUPERVISOR_URL, {})
    supervisor_data = supervisor.get("data") if isinstance(supervisor.get("data"), dict) else {}
    supervisor_ok = bool(supervisor.get("ok")) and bool(supervisor_data.get("supervisorConnected"))
    rows.append(_row("supervisor_connected", "Aureon supervisor connected", status="supervisor_connected" if supervisor_ok else "supervisor_unavailable", passed=supervisor_ok, evidence=supervisor, blocker_id="supervisor_unavailable", next_action="Repair or start Aureon supervisor on port 8791 before trusting full launch."))

    chat_data = chat_probe.get("data") if isinstance(chat_probe.get("data"), dict) else {}
    chat_ok = bool(chat_probe.get("ok")) and bool(chat_data.get("reply") or chat_data.get("text"))
    phi = probes.get(PHI_STATUS_URL, {})
    phi_ok = bool(phi.get("ok")) or bool(supervisor_data.get("phiBridgeConnected")) or chat_ok
    rows.append(_row("phi_status", "Phi bridge status", status="phi_connected" if phi_ok else "phi_unavailable", passed=phi_ok, evidence={"direct": phi, "supervisor_phi_connected": supervisor_data.get("phiBridgeConnected")}, blocker_id="phi_bridge_unavailable", next_action="Start or repair the Phi bridge on port 13002."))

    chat_bridge_live = chat_ok and chat_data.get("bridgeConnected") is not False
    rows.append(_row("phi_chat_response", "Phi chat bridge response", status="chat_live" if chat_bridge_live else "chat_vault_fallback" if chat_ok else "chat_unavailable", passed=chat_ok, evidence=chat_probe, blocker_id="phi_chat_unavailable", next_action="Confirm /api/aureon/chat returns a live or vault-fallback response.", severity="attention"))

    terminal = _terminal_guard_status(root, env, probes)
    rows.append(_row("terminal_guard", "Guarded host terminal", status="terminal_guard_passed" if terminal["passed"] else "terminal_guard_blocked", passed=terminal["passed"], evidence=terminal, blocker_id="terminal_guard_missing", next_action="Keep host terminal local-only, env-gated, and origin-guarded before enabling."))

    sandbox = _sandbox_guard_status(root, env, probes)
    rows.append(_row("sandbox_guard", "Docker sandbox guard", status="sandbox_guard_passed" if sandbox["passed"] else "sandbox_guard_blocked", passed=sandbox["passed"], evidence=sandbox, blocker_id="sandbox_guard_missing", next_action="Keep sandbox local-only, Docker-aware, and env-gated before enabling."))

    websocket = _websocket_guard_status(root)
    rows.append(_row("websocket_origin_guard", "WebSocket origin guard", status="websocket_origin_guard_passed" if websocket["passed"] else "websocket_origin_guard_missing", passed=websocket["passed"], evidence=websocket, blocker_id="websocket_origin_guard_missing", next_action="Enforce localhost/origin checks before WebSocket terminal or sandbox sessions attach."))

    provider_enabled = _truthy(env.get("MURGE_PROVIDER_API_ENABLED"))
    provider_keys_present = [key for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY", "HF_TOKEN") if env.get(key)]
    provider_ok = not provider_enabled or not provider_keys_present
    rows.append(_row("provider_api_boundary", "Provider/API boundary", status="provider_api_guarded_off" if not provider_enabled else "provider_api_enabled_reviewed" if provider_ok else "provider_api_credential_review_required", passed=provider_ok, evidence={"enabled": provider_enabled, "credential_key_names_present": provider_keys_present, "web_configured": web_data.get("configured")}, blocker_id="provider_api_credentials_present", next_action="Keep provider APIs off by default or review credential scope before enabling."))

    cloud_enabled = _truthy(env.get("MURGE_CLOUDFLARE_ENABLED"))
    rows.append(_row("cloudflare_boundary", "Cloudflare boundary", status="cloudflare_guarded_off" if not cloud_enabled else "cloudflare_enabled_requires_review", passed=not cloud_enabled, evidence={"enabled": cloud_enabled}, blocker_id="cloudflare_enabled_requires_review", next_action="Leave Cloudflare disabled for local certification unless a deploy plan reviews config and secrets."))

    npm_rows = _npm_audit_rows(root)
    high = sum(int(row.get("high_vulnerabilities") or 0) for row in npm_rows)
    critical = sum(int(row.get("critical_vulnerabilities") or 0) for row in npm_rows)
    pending = [row["id"] for row in npm_rows if not row.get("audit_present")]
    npm_ok = high == 0 and critical == 0 and not pending
    rows.append(_row("npm_audit_state", "npm audit state", status="npm_audit_classified" if npm_ok else "npm_audit_attention", passed=npm_ok, evidence={"rows": npm_rows, "high": high, "critical": critical, "pending": pending}, blocker_id="npm_audit_high_critical_or_missing", next_action="Run npm audit --json for web/runtime/desktop and review any high or critical vulnerabilities."))

    gates = supervisor_data.get("liveGates") if isinstance(supervisor_data.get("liveGates"), dict) else {}
    required_gates = ["orderIntentPublishEnabled", "executorEnabled", "liveEnabled", "realOrdersDisabled", "exchangeMutationsDisabled", "tradePathState"]
    gates_visible = all(key in gates for key in required_gates)
    rows.append(_row("live_trade_gate_visibility", "Live trade gate visibility", status="live_trade_gates_visible" if gates_visible else "live_trade_gate_visibility_missing", passed=gates_visible, evidence={"liveGates": gates}, blocker_id="live_trade_gate_visibility_missing", next_action="Expose runtime gate truth through /api/aureon/supervisor before trusting the shell."))

    mutation_controls = _trading_mutation_controls(root)
    runtime_bypass_false = runtime_data.get("noTradingGateBypass") is True or runtime_data.get("guardedActivation") is True
    web_bypass_false = web_data.get("activation", {}).get("noTradingGateBypass") is True if isinstance(web_data.get("activation"), dict) else False
    no_bypass = not mutation_controls and (runtime_bypass_false or web_bypass_false or supervisor_data.get("noTradingGateBypass") is True)
    rows.append(_row("no_trading_gate_bypass", "No trading gate bypass", status="no_trading_gate_bypass" if no_bypass else "trading_gate_bypass_risk", passed=no_bypass, evidence={"manual_trading_controls": mutation_controls, "runtime_no_trading_gate_bypass": runtime_bypass_false, "web_no_trading_gate_bypass": web_bypass_false, "supervisor_no_trading_gate_bypass": supervisor_data.get("noTradingGateBypass")}, blocker_id="trading_gate_bypass_risk", next_action="Remove manual trading controls and keep broker mutation owned by Aureon runtime/executor gates."))

    fabric = artifacts.get("live_signal_fabric", {})
    if not fabric.get("thoughtbus_receiving") or not fabric.get("mycelium_receiving"):
        rows.append(_row("thoughtbus_mycelium_visibility", "ThoughtBus/Mycelium visibility", status="organism_receipt_attention", passed=False, evidence=fabric, blocker_id="organism_receipt_attention", next_action="Refresh live signal fabric so ThoughtBus and Mycelium receipt is visible.", severity="attention"))

    return rows


def _next_actions(status_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    for row in status_rows:
        if row.get("passed"):
            continue
        actions.append(
            {
                "id": row.get("blocker_id") or row.get("id"),
                "status_row": row.get("id"),
                "severity": row.get("severity") or "blocker",
                "action": row.get("next_action") or "Repair the failing full-capability check.",
            }
        )
    return actions


def _summary(status_rows: List[Dict[str, Any]], artifacts: Dict[str, Any]) -> Dict[str, Any]:
    by_id = {row["id"]: row for row in status_rows}
    blockers = [row for row in status_rows if not row.get("passed") and row.get("severity") == "blocker"]
    attention = [row for row in status_rows if not row.get("passed") and row.get("severity") != "blocker"]
    return {
        "required_status_count": len(REQUIRED_STATUS_IDS),
        "required_status_pass_count": sum(1 for row_id in REQUIRED_STATUS_IDS if by_id.get(row_id, {}).get("passed")),
        "status_row_count": len(status_rows),
        "passed_row_count": sum(1 for row in status_rows if row.get("passed")),
        "blocker_count": len(blockers),
        "attention_count": len(attention),
        "web_health": bool(by_id.get("web_health", {}).get("passed")),
        "runtime_health": bool(by_id.get("runtime_health", {}).get("passed")),
        "desktop_ready": bool(by_id.get("desktop_ready", {}).get("passed")),
        "supervisor_connected": bool(by_id.get("supervisor_connected", {}).get("passed")),
        "phi_status": bool(by_id.get("phi_status", {}).get("passed")),
        "phi_chat_response": bool(by_id.get("phi_chat_response", {}).get("passed")),
        "terminal_guard": bool(by_id.get("terminal_guard", {}).get("passed")),
        "sandbox_guard": bool(by_id.get("sandbox_guard", {}).get("passed")),
        "websocket_origin_guard": bool(by_id.get("websocket_origin_guard", {}).get("passed")),
        "provider_api_boundary": bool(by_id.get("provider_api_boundary", {}).get("passed")),
        "cloudflare_boundary": bool(by_id.get("cloudflare_boundary", {}).get("passed")),
        "npm_audit_state": bool(by_id.get("npm_audit_state", {}).get("passed")),
        "live_trade_gate_visibility": bool(by_id.get("live_trade_gate_visibility", {}).get("passed")),
        "no_trading_gate_bypass": bool(by_id.get("no_trading_gate_bypass", {}).get("passed")),
        "thoughtbus_receiving": bool((artifacts.get("live_signal_fabric") or {}).get("thoughtbus_receiving")),
        "mycelium_receiving": bool((artifacts.get("live_signal_fabric") or {}).get("mycelium_receiving")),
        "full_launch_local_only": True,
        "no_cloud_deploy": True,
        "no_credential_migration": True,
        "no_broker_mutation": True,
    }


def build_flameborn_full_capability_stress_audit(
    *,
    root: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    probe_services: bool = True,
    probe_chat: bool = True,
    http_probe: Optional[HttpProbe] = None,
    post_probe: Optional[PostProbe] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    env_map = dict(os.environ if env is None else env)
    get_probe = http_probe or _default_http_probe
    do_post = post_probe or _default_post_probe

    probe_urls = [
        WEB_STATUS_URL,
        WEB_SUPERVISOR_URL,
        WEB_SYSTEMS_URL,
        WEB_TERMINAL_STATUS_URL,
        WEB_SANDBOX_STATUS_URL,
        RUNTIME_HEALTH_URL,
        RUNTIME_INFO_URL,
        RUNTIME_TERMINAL_STATUS_URL,
        RUNTIME_SANDBOX_STATUS_URL,
        PHI_STATUS_URL,
    ]
    probes = {url: get_probe(url) for url in probe_urls} if probe_services else {}
    chat_probe = (
        do_post(
            WEB_CHAT_URL,
            {
                "provider": "aureon",
                "model": "aureon-brain",
                "message": "Full launch proof ping. Return a short health acknowledgement.",
                "responseStyle": "safe",
                "swarmRoute": "direct",
            },
        )
        if probe_services and probe_chat
        else {"url": WEB_CHAT_URL, "ok": False, "status_code": 0, "skipped": True}
    )
    artifacts = _artifact_snapshot(root_path)
    status_rows = _build_status_rows(root=root_path, env=env_map, probes=probes, chat_probe=chat_probe, artifacts=artifacts)
    blockers = [row.get("blocker_id") for row in status_rows if not row.get("passed") and row.get("severity") == "blocker"]
    blockers = [str(item) for item in blockers if item]
    attention = [row.get("blocker_id") for row in status_rows if not row.get("passed") and row.get("severity") != "blocker"]
    attention = [str(item) for item in attention if item]
    summary = _summary(status_rows, artifacts)

    if blockers:
        status = "flameborn_full_capability_attention"
    elif attention:
        status = "flameborn_full_capability_attention"
    else:
        status = "flameborn_full_capability_certified"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "generated_at": _utc_now(),
        "mode": "full_local_launch_capability_stress",
        "summary": summary,
        "status_rows": status_rows,
        "service_health_proof": {
            "web": probes.get(WEB_STATUS_URL, {}),
            "runtime_health": probes.get(RUNTIME_HEALTH_URL, {}),
            "runtime_info": probes.get(RUNTIME_INFO_URL, {}),
            "supervisor": probes.get(WEB_SUPERVISOR_URL, {}),
            "phi": probes.get(PHI_STATUS_URL, {}),
            "phi_chat": chat_probe,
        },
        "guard_proof": {
            "terminal": next((row for row in status_rows if row["id"] == "terminal_guard"), {}),
            "sandbox": next((row for row in status_rows if row["id"] == "sandbox_guard"), {}),
            "websocket": next((row for row in status_rows if row["id"] == "websocket_origin_guard"), {}),
            "provider_api": next((row for row in status_rows if row["id"] == "provider_api_boundary"), {}),
            "cloudflare": next((row for row in status_rows if row["id"] == "cloudflare_boundary"), {}),
        },
        "desktop_security_proof": next((row for row in status_rows if row["id"] == "desktop_ready"), {}),
        "npm_audit_rows": _npm_audit_rows(root_path),
        "artifact_receipt_proof": artifacts,
        "online_requirement_baseline": ONLINE_REQUIREMENTS,
        "next_repair_actions": _next_actions(status_rows),
        "blockers": blockers,
        "attention": attention,
        "manual_boundaries": MANUAL_BOUNDARIES,
        "source_paths": {
            "public_json": DEFAULT_PUBLIC_JSON.as_posix(),
            "state_json": DEFAULT_STATE_PATH.as_posix(),
            "audit_json": DEFAULT_AUDIT_JSON.as_posix(),
            "web_app": str(_rooted(root_path, WEB_DIR)),
            "runtime": str(_rooted(root_path, RUNTIME_DIR)),
            "desktop": str(_rooted(root_path, DESKTOP_DIR)),
            "murge_activation": "frontend/public/aureon_murge_runtime_activation_stress_audit.json",
            "live_signal_fabric": "frontend/public/aureon_live_trade_signal_fabric.json",
        },
    }


def publish_full_capability_event(report: Dict[str, Any], *, root: Optional[Path] = None, emit_external: bool = True) -> Dict[str, Any]:
    trace_id = f"flameborn-full-launch-{str(report.get('generated_at') or _utc_now())[:19].replace(':', '').replace('-', '')}"
    payload = {
        "trace_id": trace_id,
        "lifecycle_id": trace_id,
        "route_key": "flameborn/local/full-capability",
        "venue": "local",
        "symbol": "FLAMEBORN",
        "phase": "flameborn_full_capability_checked",
        "authority_mode": "local_capability_stress_no_trading_gate_bypass",
        "blockers": report.get("blockers") or [],
        "verification_source": "aureon_flameborn_full_capability_stress_audit",
        "proof_mode": "full_launch_capability_stress",
        "no_trading_gate_bypass": True,
        "summary": report.get("summary") or {},
    }
    return publish_trade_flow_event(
        "flameborn_full_capability_checked",
        payload,
        source_system="flameborn_full_capability_stress_audit",
        root=root,
        emit_external=emit_external,
        write_artifacts=True,
    )


def _render_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# Flameborn Full Capability Stress Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Required rows passed: `{summary.get('required_status_pass_count')}/{summary.get('required_status_count')}`",
        f"- Blockers: `{summary.get('blocker_count')}`",
        f"- Attention: `{summary.get('attention_count')}`",
        f"- No trading gate bypass: `{summary.get('no_trading_gate_bypass')}`",
        "",
        "## Status Rows",
    ]
    for row in report.get("status_rows") or []:
        mark = "pass" if row.get("passed") else row.get("severity") or "attention"
        lines.append(f"- `{row.get('id')}`: {mark} - {row.get('status')}")
    lines.extend(["", "## Blockers"])
    blockers = report.get("blockers") or []
    lines.extend([f"- `{item}`" for item in blockers] if blockers else ["- none"])
    lines.extend(["", "## Boundaries"])
    lines.extend(f"- {item}" for item in report.get("manual_boundaries") or [])
    return "\n".join(lines) + "\n"


def write_report(report: Dict[str, Any], *, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    root_path = Path(root or _default_root()).resolve()
    return [
        _write_json(_rooted(root_path, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root_path, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _render_markdown(report)),
        _write_json(_rooted(root_path, DEFAULT_PUBLIC_JSON), report),
    ]


def build_and_write_flameborn_full_capability_stress_audit(
    *,
    root: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    probe_services: bool = True,
    probe_chat: bool = True,
    emit_fabric: bool = True,
    emit_external_fabric: bool = True,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    report = build_flameborn_full_capability_stress_audit(
        root=root_path,
        env=env,
        probe_services=probe_services,
        probe_chat=probe_chat,
    )
    writes = write_report(report, root=root_path)
    report["write_info"] = {"evidence_writes": writes}
    if emit_fabric:
        event = publish_full_capability_event(report, root=root_path, emit_external=emit_external_fabric)
        report["fabric_event"] = {
            "event_id": event.get("event_id"),
            "phase": event.get("phase"),
            "thoughtbus_publish_ok": event.get("thoughtbus_publish_ok"),
            "mycelium_ingest_ok": event.get("mycelium_ingest_ok"),
        }
    write_report(report, root=root_path)
    return report


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Flameborn full capability stress audit.")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    parser.add_argument("--no-probe", action="store_true", help="Skip localhost service probes.")
    parser.add_argument("--no-chat-probe", action="store_true", help="Skip /api/aureon/chat proof.")
    parser.add_argument("--no-fabric", action="store_true", help="Do not publish the audit proof into the live signal fabric.")
    parser.add_argument("--no-external-fabric", action="store_true", help="Write fabric artifacts without ThoughtBus/Mycelium external emission.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = build_and_write_flameborn_full_capability_stress_audit(
        root=_default_root(),
        probe_services=not args.no_probe,
        probe_chat=not args.no_chat_probe,
        emit_fabric=not args.no_fabric,
        emit_external_fabric=not args.no_external_fabric,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(f"{report['status']} blockers={len(report.get('blockers') or [])} public={DEFAULT_PUBLIC_JSON.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
