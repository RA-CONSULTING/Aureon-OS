"""MURGE runtime activation stress audit.

This audit promotes the staged AUREON MURGE bundle from a file inventory into a
local-runtime activation contract. It does not start services or execute
terminal/sandbox commands; it checks that the launch path is local-only,
Windows-safe, guarded, and visible to ThoughtBus/Mycelium through the live trade
signal fabric.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from aureon.autonomous.aureon_murge_unity_bridge import build_unity_bridge
from aureon.trading.live_trade_signal_fabric import publish_trade_flow_event


SCHEMA_VERSION = "aureon-murge-runtime-activation-stress-v1"

DEFAULT_STATE_PATH = Path("state/aureon_murge_runtime_activation_stress_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_murge_runtime_activation_stress_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_murge_runtime_activation_stress_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_murge_runtime_activation_stress_audit.json")

WEB_DIR = Path("integrations/aureon_murge/web_app")
RUNTIME_DIR = Path("integrations/aureon_murge/runtime")
DESKTOP_DIR = Path("integrations/aureon_murge/desktop")
SCRIPT_DIR = Path("scripts/aureon_murge")

ONLINE_REQUIREMENTS = [
    {
        "surface": "express_local_server",
        "source": "https://expressjs.com/en/advanced/best-practice-security.html",
        "requirement": "Local web surfaces stay input-validated, dependency-aware, and reduced-fingerprint before external exposure.",
        "activation_gate": "bind_localhost_only",
    },
    {
        "surface": "electron_desktop_shell",
        "source": "https://www.electronjs.org/docs/latest/tutorial/security",
        "requirement": "Desktop renderer keeps context isolation, disabled Node integration, sandboxing, IPC validation, and external URL allowlisting.",
        "activation_gate": "desktop_after_web_runtime_health",
    },
    {
        "surface": "cloudflare_worker",
        "source": "https://developers.cloudflare.com/workers/wrangler/configuration/",
        "requirement": "Worker configuration and secrets stay isolated from local activation unless an explicit cloud gate is enabled.",
        "activation_gate": "cloudflare_disabled_by_default",
    },
    {
        "surface": "docker_sandbox_runtime",
        "source": "https://docs.docker.com/engine/security/",
        "requirement": "Docker sandboxing uses least privilege and cannot bypass existing Aureon runtime safety gates.",
        "activation_gate": "sandbox_disabled_until_docker_guard_certified",
    },
    {
        "surface": "locked_node_dependencies",
        "source": "https://docs.npmjs.com/cli/v8/commands/npm-ci/",
        "requirement": "Local runtime dependencies should install from the committed lockfile with npm ci before service launch certification.",
        "activation_gate": "dependency_lockfile_install_ready",
    },
]

SERVICE_TARGETS = [
    {
        "id": "murge_web_app",
        "label": "MURGE Web App",
        "path": WEB_DIR,
        "port": 4173,
        "health_urls": ["http://127.0.0.1:4173/api/aureon/status"],
        "command": "node server.mjs",
        "required_files": ["server.mjs", "package.json", "index.html", "style.css"],
        "launch_gate": "MURGE_PROVIDER_API_ENABLED",
    },
    {
        "id": "murge_runtime_server",
        "label": "MURGE Runtime Server",
        "path": RUNTIME_DIR,
        "port": 7331,
        "health_urls": ["http://127.0.0.1:7331/health", "http://127.0.0.1:7331/api/runtime/info"],
        "command": "node server.mjs",
        "required_files": ["server.mjs", "Dockerfile"],
        "launch_gate": "MURGE_HOST_TERMINAL_ENABLED",
    },
    {
        "id": "murge_desktop_shell",
        "label": "MURGE Desktop Shell",
        "path": DESKTOP_DIR,
        "port": 0,
        "health_urls": [],
        "command": "npm start",
        "required_files": ["main.cjs", "preload.cjs", "runtime-manager.cjs", "package.json"],
        "launch_gate": "MURGE_DESKTOP_ENABLED",
    },
]

PACKAGE_REQUIREMENTS = [
    {
        "id": "runtime_server_dependencies",
        "path": RUNTIME_DIR,
        "lockfile": "package-lock.json",
        "install_command": "npm ci",
        "required_modules": ["express", "ws", "dockerode", "node-pty"],
        "official_baseline": "https://docs.npmjs.com/cli/v8/commands/npm-ci/",
    },
    {
        "id": "web_app_dependencies",
        "path": WEB_DIR,
        "lockfile": "package-lock.json",
        "install_command": "npm ci",
        "required_modules": ["express", "ws", "dockerode", "node-pty", "@xterm/xterm"],
        "official_baseline": "https://docs.npmjs.com/cli/v8/commands/npm-ci/",
    },
    {
        "id": "desktop_dependencies",
        "path": DESKTOP_DIR,
        "lockfile": "package-lock.json",
        "install_command": "npm ci",
        "required_modules": ["electron", "electron-builder"],
        "official_baseline": "https://docs.npmjs.com/cli/v8/commands/npm-ci/",
    },
]

ACTIVATION_GATES = [
    "MURGE_HOST_TERMINAL_ENABLED",
    "MURGE_SANDBOX_ENABLED",
    "MURGE_DESKTOP_ENABLED",
    "MURGE_PROVIDER_API_ENABLED",
    "MURGE_CLOUDFLARE_ENABLED",
]

MANUAL_BOUNDARIES = [
    "activation stress audit does not start services",
    "no terminal or sandbox command execution",
    "no credential migration or reveal",
    "no Cloudflare deployment",
    "no order intent creation",
    "no live trading gate changes",
    "AUREON_PRODUCTION_LIVE.cmd remains owner of the trading organism core",
]


HttpProbe = Callable[[str], Dict[str, Any]]
PortProbe = Callable[[str, int], bool]


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


def _truthy_env(env: Dict[str, str], key: str, default: bool = False) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _localhost_bound(host: str) -> bool:
    return str(host or "").strip().lower() in {"127.0.0.1", "localhost", "::1"}


def _port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    if port <= 0:
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _default_http_probe(url: str) -> Dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=0.75) as response:
            elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
            return {
                "url": url,
                "ok": 200 <= int(response.status) < 500,
                "status_code": int(response.status),
                "round_trip_ms": round(elapsed, 3),
            }
    except urllib.error.HTTPError as exc:
        elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
        return {"url": url, "ok": 200 <= int(exc.code) < 500, "status_code": int(exc.code), "round_trip_ms": round(elapsed, 3)}
    except Exception as exc:
        return {"url": url, "ok": False, "status_code": 0, "error": str(exc)}


def _service_rows(
    root: Path,
    *,
    probe_services: bool,
    http_probe: Optional[HttpProbe],
    port_probe: Optional[PortProbe],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    probe = http_probe or _default_http_probe
    probe_port = port_probe or _port_open
    for target in SERVICE_TARGETS:
        service_root = _rooted(root, target["path"])
        missing = [name for name in target["required_files"] if not (service_root / name).exists()]
        port = int(target.get("port") or 0)
        health_rows: List[Dict[str, Any]] = []
        if probe_services:
            health_rows = [probe(url) for url in target.get("health_urls", [])]
        port_open = probe_port("127.0.0.1", port) if probe_services and port else False
        health_ok = bool(health_rows) and all(row.get("ok") for row in health_rows)
        rows.append(
            {
                "id": target["id"],
                "label": target["label"],
                "path": str(service_root),
                "command": target["command"],
                "port": port,
                "health_urls": target["health_urls"],
                "required_files": target["required_files"],
                "missing_files": missing,
                "present": service_root.exists() and not missing,
                "port_open": port_open,
                "health_rows": health_rows,
                "health_ok": health_ok,
                "activation_gate": target["launch_gate"],
                "status": "health_passed" if health_ok else "ready_to_launch" if service_root.exists() and not missing else "missing_required_files",
            }
        )
    return rows


def _gate_rows(env: Dict[str, str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    defaults = {
        "MURGE_HOST_TERMINAL_ENABLED": False,
        "MURGE_SANDBOX_ENABLED": False,
        "MURGE_DESKTOP_ENABLED": False,
        "MURGE_PROVIDER_API_ENABLED": False,
        "MURGE_CLOUDFLARE_ENABLED": False,
    }
    for key in ACTIVATION_GATES:
        enabled = _truthy_env(env, key, defaults[key])
        rows.append(
            {
                "gate": key,
                "enabled": enabled,
                "default_enabled": defaults[key],
                "authority": "explicit_operator_env_required" if not defaults[key] else "default",
                "status": "enabled_by_env" if enabled else "guarded_off",
            }
        )
    return rows


def _package_rows(root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for label, rel in [
        ("runtime_package", RUNTIME_DIR / "package.json"),
        ("web_package", WEB_DIR / "package.json"),
        ("desktop_package", DESKTOP_DIR / "package.json"),
    ]:
        path = _rooted(root, rel)
        payload = _read_json(path, {})
        scripts = payload.get("scripts") if isinstance(payload.get("scripts"), dict) else {}
        rows.append(
            {
                "id": label,
                "path": rel.as_posix(),
                "present": path.exists(),
                "dependency_count": len(payload.get("dependencies") or {}),
                "dev_dependency_count": len(payload.get("devDependencies") or {}),
                "scripts": sorted(scripts.keys()),
                "node_modules_present": (path.parent / "node_modules").exists(),
                "status": "package_present" if path.exists() else "package_missing",
            }
        )
    return rows


def _dependency_rows(root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for requirement in PACKAGE_REQUIREMENTS:
        package_root = _rooted(root, requirement["path"])
        node_modules = package_root / "node_modules"
        missing_modules = [
            module
            for module in requirement["required_modules"]
            if not (node_modules / module).exists()
        ]
        lock_present = (package_root / str(requirement["lockfile"])).exists()
        package_present = (package_root / "package.json").exists()
        dependencies_ready = package_present and lock_present and not missing_modules
        rows.append(
            {
                "id": requirement["id"],
                "path": str(package_root),
                "package_json_present": package_present,
                "lockfile_present": lock_present,
                "node_modules_present": node_modules.exists(),
                "required_modules": requirement["required_modules"],
                "missing_modules": missing_modules,
                "install_command": requirement["install_command"],
                "official_baseline": requirement["official_baseline"],
                "status": "dependencies_ready" if dependencies_ready else "npm_ci_required" if lock_present else "lockfile_missing",
            }
        )
    return rows


def _log_tail(path: Path, max_lines: int = 8) -> List[str]:
    try:
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:]
    except Exception:
        return []


def _launch_log_rows(root: Path) -> List[Dict[str, Any]]:
    log_root = _rooted(root, Path("integrations/aureon_murge/logs/activation"))
    rows: List[Dict[str, Any]] = []
    for service in ("murge-web", "murge-runtime"):
        stdout = log_root / f"{service}.out.log"
        stderr = log_root / f"{service}.err.log"
        rows.append(
            {
                "service": service,
                "stdout_path": str(stdout),
                "stderr_path": str(stderr),
                "stdout_present": stdout.exists(),
                "stderr_present": stderr.exists(),
                "stdout_tail": _log_tail(stdout),
                "stderr_tail": _log_tail(stderr),
                "status": "logs_present" if stdout.exists() or stderr.exists() else "not_launched_by_guarded_launcher",
            }
        )
    return rows


def _npm_audit_rows(root: Path) -> List[Dict[str, Any]]:
    log_root = _rooted(root, Path("integrations/aureon_murge/logs/activation"))
    mapping = [
        ("runtime", RUNTIME_DIR, log_root / "npm-audit-runtime.json"),
        ("web_app", WEB_DIR, log_root / "npm-audit-web_app.json"),
        ("desktop", DESKTOP_DIR, log_root / "npm-audit-desktop.json"),
    ]
    rows: List[Dict[str, Any]] = []
    for label, package_path, audit_path in mapping:
        payload = _read_json(audit_path, {})
        vulnerabilities = payload.get("metadata", {}).get("vulnerabilities", {}) if isinstance(payload, dict) else {}
        total = int(vulnerabilities.get("total") or 0) if isinstance(vulnerabilities, dict) else 0
        high = int(vulnerabilities.get("high") or 0) if isinstance(vulnerabilities, dict) else 0
        critical = int(vulnerabilities.get("critical") or 0) if isinstance(vulnerabilities, dict) else 0
        rows.append(
            {
                "id": f"{label}_npm_audit",
                "package_path": str(_rooted(root, package_path)),
                "audit_path": str(audit_path),
                "audit_present": audit_path.exists(),
                "vulnerabilities": vulnerabilities,
                "total_vulnerabilities": total,
                "high_vulnerabilities": high,
                "critical_vulnerabilities": critical,
                "status": "npm_audit_pending" if not audit_path.exists() else "npm_audit_attention" if high or critical else "npm_audit_clean_or_moderate",
            }
        )
    return rows


def _windows_rows(root: Path) -> List[Dict[str, Any]]:
    web_server = _read_text(_rooted(root, WEB_DIR / "server.mjs"))
    runtime_server = _read_text(_rooted(root, RUNTIME_DIR / "server.mjs"))
    launch_script = _rooted(root, SCRIPT_DIR / "start_murge_local_runtime.ps1")
    linux_scripts = [
        SCRIPT_DIR / "start_aureon_brain_local.sh",
        SCRIPT_DIR / "setup_sandbox_runtime.sh",
        SCRIPT_DIR / "fix_docker_sandbox_access.sh",
        SCRIPT_DIR / "start_flameborn_runtime.sh",
    ]
    host_bash_assumptions = [
        {"path": (WEB_DIR / "server.mjs").as_posix(), "present": 'spawn("/bin/bash"' in web_server or "spawn('/bin/bash'" in web_server},
        {"path": (RUNTIME_DIR / "server.mjs").as_posix(), "present": 'spawn("/bin/bash"' in runtime_server or "spawn('/bin/bash'" in runtime_server},
    ]
    return [
        {
            "id": "powershell_launcher",
            "status": "present" if launch_script.exists() else "missing",
            "path": (SCRIPT_DIR / "start_murge_local_runtime.ps1").as_posix(),
            "required_for_windows": True,
        },
        {
            "id": "host_bash_assumption_removed",
            "status": "passing" if not any(row["present"] for row in host_bash_assumptions) else "blocked",
            "bash_available": bool(shutil.which("bash")),
            "host_bash_assumptions": host_bash_assumptions,
        },
        {
            "id": "linux_scripts_reference_only",
            "status": "reference_only",
            "paths": [path.as_posix() for path in linux_scripts if _rooted(root, path).exists()],
        },
        {
            "id": "platform",
            "platform": platform.system(),
            "is_windows": platform.system().lower() == "windows",
            "node_available": bool(shutil.which("node")),
            "docker_cli_available": bool(shutil.which("docker")),
        },
    ]


def _terminal_guard_rows(root: Path, env: Dict[str, str]) -> List[Dict[str, Any]]:
    runtime_server = _read_text(_rooted(root, RUNTIME_DIR / "server.mjs"))
    web_server = _read_text(_rooted(root, WEB_DIR / "server.mjs"))
    return [
        {
            "surface": "runtime_host_terminal",
            "guard_env": "MURGE_HOST_TERMINAL_ENABLED",
            "enabled": _truthy_env(env, "MURGE_HOST_TERMINAL_ENABLED"),
            "code_guard_present": "HOST_TERMINAL_ENABLED" in runtime_server and "MURGE_HOST_TERMINAL_ENABLED" in runtime_server,
            "status": "guarded_off" if not _truthy_env(env, "MURGE_HOST_TERMINAL_ENABLED") else "operator_enabled_requires_localhost_origin_guard",
        },
        {
            "surface": "web_host_terminal",
            "guard_env": "MURGE_HOST_TERMINAL_ENABLED",
            "enabled": _truthy_env(env, "MURGE_HOST_TERMINAL_ENABLED"),
            "code_guard_present": "MURGE_HOST_TERMINAL_ENABLED" in web_server,
            "status": "guarded_off" if not _truthy_env(env, "MURGE_HOST_TERMINAL_ENABLED") else "operator_enabled_requires_localhost_origin_guard",
        },
        {
            "surface": "docker_sandbox",
            "guard_env": "MURGE_SANDBOX_ENABLED",
            "enabled": _truthy_env(env, "MURGE_SANDBOX_ENABLED"),
            "code_guard_present": "MURGE_SANDBOX_ENABLED" in runtime_server and "MURGE_SANDBOX_ENABLED" in web_server,
            "status": "guarded_off" if not _truthy_env(env, "MURGE_SANDBOX_ENABLED") else "operator_enabled_requires_docker_guard",
        },
    ]


def _electron_rows(root: Path) -> List[Dict[str, Any]]:
    main = _read_text(_rooted(root, DESKTOP_DIR / "main.cjs"))
    preload = _read_text(_rooted(root, DESKTOP_DIR / "preload.cjs"))
    manager = _read_text(_rooted(root, DESKTOP_DIR / "runtime-manager.cjs"))
    return [
        {"check": "context_isolation", "passing": "contextIsolation: true" in main},
        {"check": "node_integration_disabled", "passing": "nodeIntegration: false" in main},
        {"check": "renderer_sandbox_enabled", "passing": "sandbox: true" in main},
        {"check": "ipc_allowlist_present", "passing": "flameborn:get-status" in preload and "flameborn:restart-service" in preload},
        {"check": "open_external_allowlist", "passing": "isAllowedExternalUrl" in main},
        {"check": "desktop_auto_aureon_can_be_disabled", "passing": "FLAMEBORN_DESKTOP_AUTO_AUREON" in manager},
        {"check": "desktop_skip_auto_servers_supported", "passing": "FLAMEBORN_SKIP_AUTO_SERVERS" in manager and "skipAutoServers" in manager},
    ]


def _source_path_rows(root: Path) -> Dict[str, str]:
    return {
        "unity_bridge": "frontend/public/aureon_murge_unity_bridge.json",
        "web_app": str(_rooted(root, WEB_DIR)),
        "runtime": str(_rooted(root, RUNTIME_DIR)),
        "desktop": str(_rooted(root, DESKTOP_DIR)),
        "launcher": str(_rooted(root, SCRIPT_DIR / "start_murge_local_runtime.ps1")),
        "public": DEFAULT_PUBLIC_JSON.as_posix(),
    }


def _fabric_snapshot(root: Path) -> Dict[str, Any]:
    public_path = _rooted(root, Path("frontend/public/aureon_live_trade_signal_fabric.json"))
    payload = _read_json(public_path, {})
    if isinstance(payload, dict):
        return {
            "status": payload.get("status", ""),
            "generated_at": payload.get("generated_at", ""),
            "summary": payload.get("summary", {}),
        }
    return {}


def _summary(
    *,
    service_rows: List[Dict[str, Any]],
    gate_rows: List[Dict[str, Any]],
    dependency_rows: List[Dict[str, Any]],
    npm_audit_rows: List[Dict[str, Any]],
    terminal_rows: List[Dict[str, Any]],
    electron_rows: List[Dict[str, Any]],
    windows_rows: List[Dict[str, Any]],
    unity_bridge: Dict[str, Any],
    blockers: List[str],
) -> Dict[str, Any]:
    return {
        "service_count": len(service_rows),
        "service_present_count": sum(1 for row in service_rows if row.get("present")),
        "service_health_pass_count": sum(1 for row in service_rows if row.get("health_ok")),
        "local_launch_ready": not blockers,
        "web_health_passed": any(row["id"] == "murge_web_app" and row.get("health_ok") for row in service_rows),
        "runtime_health_passed": any(row["id"] == "murge_runtime_server" and row.get("health_ok") for row in service_rows),
        "desktop_gate_enabled": any(row["gate"] == "MURGE_DESKTOP_ENABLED" and row.get("enabled") for row in gate_rows),
        "activation_gate_enabled_count": sum(1 for row in gate_rows if row.get("enabled")),
        "dependency_ready_count": sum(1 for row in dependency_rows if row.get("status") == "dependencies_ready"),
        "dependency_check_count": len(dependency_rows),
        "npm_audit_present_count": sum(1 for row in npm_audit_rows if row.get("audit_present")),
        "npm_high_vulnerability_count": sum(int(row.get("high_vulnerabilities") or 0) for row in npm_audit_rows),
        "npm_critical_vulnerability_count": sum(int(row.get("critical_vulnerabilities") or 0) for row in npm_audit_rows),
        "terminal_guard_count": len(terminal_rows),
        "terminal_guard_passing_count": sum(1 for row in terminal_rows if row.get("code_guard_present")),
        "electron_security_pass_count": sum(1 for row in electron_rows if row.get("passing")),
        "electron_security_check_count": len(electron_rows),
        "windows_launcher_present": any(row.get("id") == "powershell_launcher" and row.get("status") == "present" for row in windows_rows),
        "host_bash_assumption_removed": any(row.get("id") == "host_bash_assumption_removed" and row.get("status") == "passing" for row in windows_rows),
        "collision_count": int((unity_bridge.get("summary") or {}).get("collision_count") or 0),
        "unity_ready": bool((unity_bridge.get("summary") or {}).get("unity_ready")),
        "thoughtbus_mycelium_required": True,
        "blocker_count": len(blockers),
        "no_trading_gate_bypass": True,
        "no_cloud_deploy": True,
        "no_credential_migration": True,
    }


def build_runtime_activation_stress_audit(
    *,
    root: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    probe_services: bool = True,
    http_probe: Optional[HttpProbe] = None,
    port_probe: Optional[PortProbe] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    env_map = dict(os.environ if env is None else env)
    unity_bridge = build_unity_bridge()
    service_rows = _service_rows(
        root_path,
        probe_services=probe_services,
        http_probe=http_probe,
        port_probe=port_probe,
    )
    gate_rows = _gate_rows(env_map)
    package_rows = _package_rows(root_path)
    dependency_rows = _dependency_rows(root_path)
    launch_log_rows = _launch_log_rows(root_path)
    npm_audit_rows = _npm_audit_rows(root_path)
    windows_rows = _windows_rows(root_path)
    terminal_rows = _terminal_guard_rows(root_path, env_map)
    electron_rows = _electron_rows(root_path)

    blockers: List[str] = []
    if int((unity_bridge.get("summary") or {}).get("collision_count") or 0) > 0:
        blockers.append("collision_review_required")
    if any(not row.get("present") for row in service_rows):
        blockers.append("murge_service_required_files_missing")
    if any(row.get("status") != "dependencies_ready" for row in dependency_rows):
        blockers.append("murge_dependency_install_required")
    if any((int(row.get("high_vulnerabilities") or 0) + int(row.get("critical_vulnerabilities") or 0)) > 0 for row in npm_audit_rows):
        blockers.append("murge_dependency_vulnerability_review_required")
    if any(row.get("id") == "host_bash_assumption_removed" and row.get("status") != "passing" for row in windows_rows):
        blockers.append("windows_host_bash_assumption_present")
    if not any(row.get("id") == "powershell_launcher" and row.get("status") == "present" for row in windows_rows):
        blockers.append("windows_powershell_launcher_missing")
    if not all(row.get("code_guard_present") for row in terminal_rows):
        blockers.append("terminal_or_sandbox_code_guard_missing")
    if not all(row.get("passing") for row in electron_rows):
        blockers.append("electron_security_review_required")
    if not _localhost_bound(env_map.get("HOST", "127.0.0.1")):
        blockers.append("web_host_not_localhost")
    if not _localhost_bound(env_map.get("FLAMEBORN_RUNTIME_HOST", "127.0.0.1")):
        blockers.append("runtime_host_not_localhost")
    if _truthy_env(env_map, "MURGE_CLOUDFLARE_ENABLED"):
        blockers.append("cloudflare_activation_out_of_scope")
    if _truthy_env(env_map, "MURGE_PROVIDER_API_ENABLED") and any(
        key for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY", "HF_TOKEN")
        if env_map.get(key)
    ):
        blockers.append("provider_api_credentials_present_activation_review_required")

    if probe_services:
        web = next(row for row in service_rows if row["id"] == "murge_web_app")
        runtime = next(row for row in service_rows if row["id"] == "murge_runtime_server")
        if not web.get("health_ok") or not runtime.get("health_ok"):
            blockers.append("local_service_health_pending")

    status = "murge_runtime_activation_ready" if not blockers else "murge_runtime_activation_attention"
    summary = _summary(
        service_rows=service_rows,
        gate_rows=gate_rows,
        dependency_rows=dependency_rows,
        npm_audit_rows=npm_audit_rows,
        terminal_rows=terminal_rows,
        electron_rows=electron_rows,
        windows_rows=windows_rows,
        unity_bridge=unity_bridge,
        blockers=blockers,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "generated_at": _utc_now(),
        "mode": "full_local_launch_activation_stress",
        "summary": summary,
        "activation_service_rows": service_rows,
        "activation_gate_rows": gate_rows,
        "package_readiness_rows": package_rows,
        "dependency_readiness_rows": dependency_rows,
        "launch_log_rows": launch_log_rows,
        "npm_audit_rows": npm_audit_rows,
        "windows_compatibility_rows": windows_rows,
        "terminal_sandbox_guard_rows": terminal_rows,
        "electron_security_rows": electron_rows,
        "online_requirement_baseline": ONLINE_REQUIREMENTS,
        "unity_collision_rows": unity_bridge.get("collision_rows", []),
        "fabric_visibility_proof": _fabric_snapshot(root_path),
        "next_activation_actions": [
            {
                "id": "murge-runtime-001",
                "priority": "P0",
                "producer": "murge_runtime_activation_stress_audit",
                "action": "Resolve staged collisions by distilling README, .gitignore, and docs/SECURITY.md instead of overwriting.",
                "blocked_before_execution": "collision_review_required" in blockers,
            },
            {
                "id": "murge-runtime-002",
                "priority": "P0",
                "producer": "scripts/aureon_murge/start_murge_local_runtime.ps1",
                "action": "Launch web/runtime on localhost with host terminal, sandbox, provider API, cloud, and desktop gates guarded off by default.",
                "blocked_before_execution": False,
            },
            {
                "id": "murge-runtime-003",
                "priority": "P1",
                "producer": "integrations/aureon_murge/desktop/runtime-manager.cjs",
                "action": "Start desktop only after web and runtime health pass, with imported Aureon bridge disabled on Windows.",
                "blocked_before_execution": not summary["web_health_passed"] or not summary["runtime_health_passed"],
            },
            {
                "id": "murge-runtime-004",
                "priority": "P1",
                "producer": "live_trade_signal_fabric",
                "action": "Publish activation phases into ThoughtBus/Mycelium whenever the launcher or audit observes service state.",
                "blocked_before_execution": False,
            },
        ],
        "blockers": blockers,
        "manual_boundaries": MANUAL_BOUNDARIES,
        "source_paths": _source_path_rows(root_path),
    }


def publish_activation_events(report: Dict[str, Any], *, root: Optional[Path] = None, emit_external: bool = True) -> List[Dict[str, Any]]:
    trace_id = f"murge-activation-{str(report.get('generated_at') or _utc_now())[:19].replace(':', '').replace('-', '')}"
    events: List[Dict[str, Any]] = []
    service_rows = report.get("activation_service_rows") if isinstance(report.get("activation_service_rows"), list) else []
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    base = {
        "trace_id": trace_id,
        "lifecycle_id": trace_id,
        "route_key": "murge/local/full-launch",
        "venue": "local",
        "symbol": "MURGE",
        "authority_mode": "activation_stress_no_trading_gate_bypass",
        "blockers": blockers,
        "verification_source": "aureon_murge_runtime_activation_stress_audit",
        "proof_mode": "local_runtime_activation",
        "no_trading_gate_bypass": True,
    }
    phase_map = [
        ("murge_activation_preflight", "murge_runtime_activation_stress_audit"),
        ("murge_terminal_guard_blocked" if blockers else "murge_terminal_guard_passed", "murge_runtime_activation_stress_audit"),
    ]
    for service in service_rows:
        if service.get("id") == "murge_web_app":
            phase_map.append(("murge_web_started" if service.get("health_ok") else "murge_activation_failed", "murge_web_app"))
        if service.get("id") == "murge_runtime_server":
            phase_map.append(("murge_runtime_started" if service.get("health_ok") else "murge_activation_failed", "murge_runtime_server"))
    if report.get("summary", {}).get("web_health_passed") and report.get("summary", {}).get("runtime_health_passed"):
        phase_map.append(("murge_health_passed", "murge_runtime_activation_stress_audit"))
    if report.get("summary", {}).get("desktop_gate_enabled"):
        phase_map.append(("murge_desktop_started", "murge_desktop_shell"))

    for phase, source in phase_map:
        payload = dict(base)
        payload["phase"] = phase
        payload["source_system"] = source
        payload["trace_health"] = "attention" if blockers or phase == "murge_activation_failed" else "complete"
        event = publish_trade_flow_event(
            phase,
            payload,
            source_system=source,
            root=root,
            emit_external=emit_external,
            write_artifacts=True,
        )
        events.append(event)
    return events


def _render_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    blockers = report.get("blockers") or []
    lines = [
        "# Aureon MURGE Runtime Activation Stress Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Services present: `{summary.get('service_present_count')}/{summary.get('service_count')}`",
        f"- Health passed: `{summary.get('service_health_pass_count')}/{summary.get('service_count')}`",
        f"- Terminal guards: `{summary.get('terminal_guard_passing_count')}/{summary.get('terminal_guard_count')}`",
        f"- Electron checks: `{summary.get('electron_security_pass_count')}/{summary.get('electron_security_check_count')}`",
        f"- No trading gate bypass: `{summary.get('no_trading_gate_bypass')}`",
        "",
        "## Blockers",
    ]
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Boundaries"])
    lines.extend(f"- {item}" for item in report.get("manual_boundaries", []))
    return "\n".join(lines) + "\n"


def write_report(report: Dict[str, Any], *, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    root_path = Path(root or _default_root()).resolve()
    writes = [
        _write_json(_rooted(root_path, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root_path, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _render_markdown(report)),
        _write_json(_rooted(root_path, DEFAULT_PUBLIC_JSON), report),
    ]
    return writes


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the MURGE runtime activation stress audit.")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    parser.add_argument("--no-probe", action="store_true", help="Skip localhost health probes.")
    parser.add_argument("--no-fabric", action="store_true", help="Do not publish activation events to the live signal fabric.")
    parser.add_argument("--no-external-fabric", action="store_true", help="Write fabric artifacts without ThoughtBus/Mycelium external emission.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = _default_root()
    report = build_runtime_activation_stress_audit(root=root, probe_services=not args.no_probe)
    writes = write_report(report, root=root)
    if not args.no_fabric:
        events = publish_activation_events(report, root=root, emit_external=not args.no_external_fabric)
        report["fabric_event_write_count"] = len(events)
        report["fabric_visibility_proof"] = _fabric_snapshot(root)
        report["write_info"] = {"evidence_writes": writes}
        write_report(report, root=root)
    else:
        report["write_info"] = {"evidence_writes": writes}

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(f"{report['status']} blockers={len(report.get('blockers') or [])} public={DEFAULT_PUBLIC_JSON.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
