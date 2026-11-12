"""Local plug-and-play supervisor.

Starts the operator API, the public MCP server, the Vite dashboard, and a
stack health server. The health server's ``/api/cognition`` runs
``aureon.evaluation.brain_proof.evaluate_brain`` in this process.

No ``.env`` is read. Exchange keys and model keys are removed from the child
environment. ``AUREON_AUTONOMY_MODE=guarded`` keeps live trading off.
``AUREON_LLM_OFFLINE=1`` keeps the operator off external model HTTP.

POSIX children use a new session and ``os.killpg``. Windows children use a
new process group and ``taskkill``. ``install.cmd`` is the Windows entry.
Supported go-live stays HOLD.
"""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "deploy" / "plug" / "runtime"
PIDFILE = RUNTIME / "supervisor.pid"
PIDS = RUNTIME / "pids.json"



def _port(name: str, default: int) -> int:
    """Port from AUREON_PLUG_*_PORT, else the default. Bad values stop the run."""

    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise SystemExit(f"{name} must be a port number, got {raw!r}") from None
    if not 1 <= value <= 65535:
        raise SystemExit(f"{name} must be between 1 and 65535, got {value}")
    return value


# Defaults are unchanged. A machine that already uses one of these ports can
# move the stack with AUREON_PLUG_OPERATOR_PORT, AUREON_PLUG_MCP_PORT,
# AUREON_PLUG_FRONTEND_PORT and AUREON_PLUG_STACK_PORT.
OPERATOR_PORT = _port("AUREON_PLUG_OPERATOR_PORT", 8790)
MCP_PORT = _port("AUREON_PLUG_MCP_PORT", 8077)
FRONTEND_PORT = _port("AUREON_PLUG_FRONTEND_PORT", 5173)
STACK_PORT = _port("AUREON_PLUG_STACK_PORT", 8787)

OPERATOR_URL = f"http://127.0.0.1:{OPERATOR_PORT}"
MCP_URL = f"http://127.0.0.1:{MCP_PORT}/mcp"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}/"
STACK_URL = f"http://127.0.0.1:{STACK_PORT}"

_SENSITIVE_PARTS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "PASSWD")
_CHILDREN: dict[str, subprocess.Popen[bytes]] = {}
_STOPPING = False
# 0x00000200. Linux CPython does not export this Windows creation flag.
_CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)


def _sensitive(name: str) -> bool:
    """True for credential-shaped variables. Git's own GIT_CONFIG_KEY_* stays."""

    upper = name.upper()
    if upper.startswith("GIT_") or upper.startswith("NPM_"):
        return False
    return any(part in upper for part in _SENSITIVE_PARTS)


def _strip_secrets(env: dict[str, str]) -> dict[str, str]:
    cleaned = dict(env)
    for name in list(cleaned):
        if _sensitive(name):
            cleaned.pop(name, None)
    cleaned.pop("AUREON_LLM_BASE_URL", None)
    cleaned.pop("AUREON_LLM_MODEL", None)
    return cleaned


def process_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for this stack. Secrets from the parent shell are dropped."""

    env = _strip_secrets(dict(os.environ))
    env.update(
        {
            "AUREON_PLUG_AND_PLAY": "1",
            "AUREON_LLM_OFFLINE": "1",
            "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
            "AUREON_LIVE_TRADING": "0",
            "AUREON_DISABLE_REAL_ORDERS": "1",
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
            "AUREON_FUSION_ARM_LIVE": "",
            "AUREON_ORDER_INTENT_PUBLISH": "0",
            "AUREON_AUTONOMY_MODE": "guarded",
            "AUREON_OPERATOR_ENV": "development",
            "AUREON_OPERATOR_HOST": "127.0.0.1",
            "AUREON_OPERATOR_PORT": str(OPERATOR_PORT),
            "AUREON_OPERATOR_URL": OPERATOR_URL,
            "VITE_OPERATOR_URL": OPERATOR_URL,
            "VITE_OPERATOR_PORT": str(OPERATOR_PORT),
            "AUREON_PUBLIC_OPEN": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": os.pathsep.join(
                [str(ROOT), str(ROOT / "mcp"), env.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep),
        }
    )
    if extra:
        env.update(extra)
    return env


def ensure_checkout_importable() -> None:
    """Put this checkout on sys.path for the in-process cognition import.

    ``./install.sh`` executes ``python scripts/plug_and_play.py``. That sets
    ``sys.path[0]`` to ``scripts/`` and does not add the checkout. Child
    processes receive the checkout through ``PYTHONPATH``. Writing
    ``os.environ["PYTHONPATH"]`` does not rebuild this process's ``sys.path``,
    so ``/api/cognition`` would raise ``ModuleNotFoundError`` for ``aureon``.
    """

    entries = (str(ROOT / "mcp"), str(ROOT))
    for entry in entries:
        while entry in sys.path:
            sys.path.remove(entry)
    for entry in entries:
        sys.path.insert(0, entry)


def arm_this_process() -> None:
    """Drop secrets in this process and keep PATH so Node can start."""

    env = process_env()
    for name in list(os.environ):
        if name not in env:
            os.environ.pop(name, None)
    os.environ.update(env)
    ensure_checkout_importable()


def _http_get(url: str, timeout: float = 3.0) -> tuple[int, bytes]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _http_post(url: str, payload: dict[str, Any], timeout: float = 60.0) -> tuple[int, bytes]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def probe_services() -> dict[str, Any]:
    services: dict[str, Any] = {}
    try:
        status, body = _http_get(OPERATOR_URL + "/healthz")
        payload = json.loads(body.decode("utf-8"))
        names = [item.get("name") for item in payload.get("providers") or []]
        ready_status, ready_body = _http_get(OPERATOR_URL + "/readyz", timeout=10)
        ready_payload = json.loads(ready_body.decode("utf-8"))
        services["operator"] = {
            "ok": (
                status == 200
                and payload.get("ok") is True
                and payload.get("service") == "aureon-operator"
                and ready_status == 200
                and ready_payload.get("ready") is True
                and names == ["offline"]
            ),
            "status": status,
            "ready": ready_payload.get("ready"),
            "url": OPERATOR_URL + "/healthz",
            "providers": names,
        }
    except Exception as exc:  # noqa: BLE001 — probe records the failure
        services["operator"] = {"ok": False, "url": OPERATOR_URL + "/healthz", "error": type(exc).__name__}
    try:
        status, _body = _http_get(MCP_URL)
        services["mcp"] = {
            "ok": status == 405,
            "status": status,
            "url": MCP_URL,
        }
    except Exception as exc:  # noqa: BLE001
        services["mcp"] = {"ok": False, "url": MCP_URL, "error": type(exc).__name__}
    try:
        status, body = _http_get(FRONTEND_URL)
        text = body.decode("utf-8", "replace")
        services["frontend"] = {
            "ok": status == 200 and "Aureon OS" in text,
            "status": status,
            "url": FRONTEND_URL,
        }
    except Exception as exc:  # noqa: BLE001
        services["frontend"] = {"ok": False, "url": FRONTEND_URL, "error": type(exc).__name__}
    services["cognition"] = {
        "ok": True,
        "url": STACK_URL + "/api/cognition",
        "runner": "aureon.evaluation.brain_proof.evaluate_brain",
    }
    ok = all(item.get("ok") is True for item in services.values())
    return {
        "ok": ok,
        "service": "aureon-plug",
        "live_trading": False,
        "external_llm": False,
        "autonomy_mode": "guarded",
        "exchange_keys": "unset",
        "services": services,
    }


def _trade_view(trade: object) -> dict[str, Any]:
    """Smoke line. Label rows stay on the cognition body."""

    body = trade if isinstance(trade, dict) else {}
    return {
        "entries": body.get("entries"),
        "evidence_tag": body.get("evidence_tag"),
        "filled_outcomes": body.get("filled_outcomes"),
        "orders_placed": body.get("orders_placed"),
        "outcome_labels": body.get("outcome_labels"),
        "paper_labels": body.get("paper_labels"),
        "reason": body.get("reason"),
        "release_boundary": body.get("release_boundary"),
        "verdict": body.get("verdict"),
    }


def _cognition_trade_failure(readiness: object) -> str | None:
    """Smoke gate for the printed trade view. A missing orders_placed is a failure."""

    body = readiness if isinstance(readiness, dict) else {}
    verdict = body.get("verdict")
    reason = str(body.get("reason") or "")
    if body.get("release_boundary") != "HOLD" or body.get("orders_placed") is not False:
        return "cognition auris trade_readiness"
    if verdict in {"pass", "fail"}:
        if body.get("outcome_labels") not in {"paper", "filled"}:
            return "cognition auris trade_readiness"
        if "no market series and no trade-outcome labels" in reason:
            return "cognition auris trade_readiness"
        return None
    if verdict != "HOLD" or (
        "no market series" not in reason and "no trade-outcome labels" not in reason
    ):
        return "cognition auris trade_readiness"
    return None


def cognition_view(report: dict[str, Any]) -> dict[str, Any]:
    """Short view of the brain-proof report. Series arrays stay on the HTTP body."""

    hnc = report["hnc"]
    auris = report["auris"]
    derived = report["qgita"]["derived_series"]
    on_lambda = report["qgita"]["on_hnc_series"]
    extension = hnc.get("multiverse_extension") or {}
    return {
        "schema": report.get("schema"),
        "live_trading": report.get("live_trading"),
        "orders_placed": report.get("orders_placed"),
        "external_llm": report.get("external_llm"),
        "cognition": report.get("cognition"),
        "hnc": {
            "state": hnc.get("state"),
            "coherence": hnc.get("coherence"),
            "lambda_last": hnc.get("lambda_last"),
            "steps": hnc.get("steps"),
            "enable_multiverse": hnc.get("enable_multiverse"),
            "multiverse_extension_verdict": extension.get("verdict"),
        },
        "auris": {
            "status": auris.get("status"),
            "coherence": auris.get("coherence"),
            "trade_readiness": _trade_view(auris.get("trade_readiness")),
            "hold_nodes": auris.get("hold_nodes"),
        },
        "qgita": {
            "derived_status": derived.get("status"),
            "derived_verdict": derived.get("verdict"),
            "derived_ftcp_count": derived.get("ftcp_count"),
            "derived_rates_verdict": derived.get("rates_verdict"),
            "on_hnc_status": on_lambda.get("status"),
            "on_hnc_ftcp_count": on_lambda.get("ftcp_count"),
            "on_hnc_rates_verdict": on_lambda.get("rates_verdict"),
        },
        "together": report.get("together"),
    }


def run_cognition() -> dict[str, Any]:
    ensure_checkout_importable()
    from aureon.evaluation.brain_proof import evaluate_brain

    report = evaluate_brain()
    if not isinstance(report, dict):
        raise RuntimeError("evaluate_brain did not return an object")
    return report


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")


def make_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: object) -> None:
            return

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in {"/healthz", "/readyz"}:
                report = probe_services()
                self._send(200 if report["ok"] else 503, report)
                return
            if path == "/api/cognition":
                try:
                    report = run_cognition()
                except Exception as exc:  # noqa: BLE001 — the caller sees the failure class
                    self._send(500, {"ok": False, "error": type(exc).__name__})
                    return
                self._send(200, report)
                return
            self._send(404, {"ok": False, "error": "not_found"})

    return Handler


def _platform(platform: str | None) -> str:
    return os.name if platform is None else platform


def _popen_session_kwargs(platform: str | None = None) -> dict[str, Any]:
    """Process-group flags. POSIX stays on ``start_new_session``."""

    if _platform(platform) == "nt":
        return {"creationflags": _CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _stop_command(platform: str | None = None) -> str:
    if _platform(platform) == "nt":
        return "install.cmd --stop"
    return "./install.sh --stop"


def _frontend_argv(platform: str | None = None) -> list[str]:
    """Dashboard command. POSIX keeps the npm shim. Windows runs vite.js."""

    if _platform(platform) == "nt":
        vite_js = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
        if not vite_js.is_file():
            raise SystemExit(f"dashboard binary missing: {vite_js}")
        return [
            "node",
            str(vite_js),
            "--host",
            "127.0.0.1",
            "--port",
            str(FRONTEND_PORT),
        ]
    vite = ROOT / "frontend" / "node_modules" / ".bin" / "vite"
    if not vite.is_file():
        raise SystemExit(f"dashboard binary missing: {vite}")
    return [str(vite), "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)]


def _tasklist_lists_pid(stdout: str, number: int) -> bool:
    """True when ``tasklist /FO CSV`` names this pid in the second column."""

    for line in stdout.splitlines():
        fields = line.split('","')
        if len(fields) >= 2 and fields[1] == str(number):
            return True
    return False


def _taskkill(number: int, *, force: bool) -> None:
    command = ["taskkill", "/T", "/PID", str(number)]
    if force:
        command.insert(1, "/F")
    try:
        subprocess.run(command, capture_output=True, check=False)
    except OSError:
        return


def _windows_pid_alive(number: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {number}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return True
    return _tasklist_lists_pid(result.stdout or "", number)


def _stop_windows_pids(seen: set[int]) -> None:
    for number in seen:
        _taskkill(number, force=False)
    time.sleep(0.4)
    for number in seen:
        if _windows_pid_alive(number) is False:
            continue
        _taskkill(number, force=True)


def _stop_posix_pids(seen: set[int]) -> None:
    for number in seen:
        try:
            os.killpg(number, signal.SIGTERM)
        except OSError:
            try:
                os.kill(number, signal.SIGTERM)
            except OSError:
                pass
    time.sleep(0.4)
    for number in seen:
        try:
            os.kill(number, 0)
        except OSError:
            continue
        try:
            os.killpg(number, signal.SIGKILL)
        except OSError:
            try:
                os.kill(number, signal.SIGKILL)
            except OSError:
                pass


def _spawn(name: str, cmd: list[str], env: dict[str, str], cwd: Path) -> subprocess.Popen[bytes]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    log_path = RUNTIME / f"{name}.log"
    handle = log_path.open("ab")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        **_popen_session_kwargs(),
    )
    return proc


def start_children() -> dict[str, int]:
    frontend_cmd = _frontend_argv()
    env = process_env()
    _CHILDREN["operator"] = _spawn(
        "operator",
        [sys.executable, "-m", "aureon.operator.operator_server"],
        env,
        ROOT,
    )
    _CHILDREN["mcp"] = _spawn(
        "mcp",
        [
            sys.executable,
            "-m",
            "aureon_public",
            "--transport",
            "streamable-http",
            "--host",
            "127.0.0.1",
            "--port",
            str(MCP_PORT),
        ],
        env,
        ROOT,
    )
    _CHILDREN["frontend"] = _spawn(
        "frontend",
        frontend_cmd,
        env,
        ROOT / "frontend",
    )
    pids = {name: int(proc.pid) for name, proc in _CHILDREN.items()}
    PIDS.write_text(json.dumps(pids), encoding="utf-8")
    return pids


def stop_children() -> None:
    global _STOPPING
    _STOPPING = True
    if PIDS.is_file():
        try:
            recorded = json.loads(PIDS.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            recorded = {}
    else:
        recorded = {}
    for proc in _CHILDREN.values():
        recorded.setdefault(str(proc.pid), proc.pid)
    seen: set[int] = set()
    for pid in list(recorded.values()) + [proc.pid for proc in _CHILDREN.values()]:
        try:
            number = int(pid)
        except (TypeError, ValueError):
            continue
        if number in seen or number <= 0:
            continue
        seen.add(number)
    if os.name == "nt":
        _stop_windows_pids(seen)
    else:
        _stop_posix_pids(seen)
    if PIDS.is_file():
        PIDS.unlink()
    if PIDFILE.is_file():
        PIDFILE.unlink()


def wait_until_ready(timeout_s: float = 90.0) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last: dict[str, Any] = {}
    while time.time() < deadline:
        for proc in _CHILDREN.values():
            if proc.poll() is not None:
                raise SystemExit(f"a child exited early: code {proc.returncode}. see {RUNTIME}")
        last = probe_services()
        if last.get("ok") is True:
            return last
        time.sleep(0.5)
    raise SystemExit("stack health did not become ready: " + json.dumps(last, sort_keys=True))


def _finite(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _mcp(method: str, params: dict[str, Any]) -> dict[str, Any]:
    status, body = _http_post(
        MCP_URL,
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    if status != 200:
        raise RuntimeError(f"{method} status {status}: {body[:300]!r}")
    payload = json.loads(body.decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(f"{method} error {payload['error']}")
    return payload


def smoke() -> int:
    failures: list[str] = []
    health_status, health_body = _http_get(STACK_URL + "/healthz", timeout=10)
    print("SMOKE healthz", health_status, health_body.decode("utf-8", "replace").rstrip())
    try:
        health = json.loads(health_body.decode("utf-8"))
    except json.JSONDecodeError:
        health = {}
    if health_status != 200 or health.get("ok") is not True or health.get("live_trading") is not False:
        failures.append("stack healthz")
    if health.get("external_llm") is not False:
        failures.append("stack healthz external_llm")

    op_status, op_body = _http_get(OPERATOR_URL + "/healthz")
    print("SMOKE operator", op_status, op_body.decode("utf-8", "replace").rstrip())
    try:
        operator = json.loads(op_body.decode("utf-8"))
    except json.JSONDecodeError:
        operator = {}
    providers = operator.get("providers") or []
    if op_status != 200 or operator.get("service") != "aureon-operator":
        failures.append("operator healthz")
    if not providers or any(item.get("name") != "offline" for item in providers):
        failures.append(f"operator providers {providers}")

    ready_status, ready_body = _http_get(OPERATOR_URL + "/readyz", timeout=20)
    print("SMOKE readyz", ready_status, ready_body.decode("utf-8", "replace").rstrip())
    try:
        ready = json.loads(ready_body.decode("utf-8"))
    except json.JSONDecodeError:
        ready = {}
    if ready_status != 200 or ready.get("ready") is not True:
        failures.append("operator readyz")

    front_status, front_body = _http_get(FRONTEND_URL, timeout=10)
    front_text = front_body.decode("utf-8", "replace")
    print(f"SMOKE frontend {front_status} aureon_os={'Aureon OS' in front_text}")
    if front_status != 200 or "Aureon OS" not in front_text:
        failures.append("frontend")

    try:
        initialized = _mcp(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "aureon-plug-smoke", "version": "0"},
            },
        )
        info = initialized.get("result", {}).get("serverInfo", {})
        print("SMOKE mcp_initialize", json.dumps(info, sort_keys=True))
        if info.get("name") != "aureon-public":
            failures.append(f"mcp serverInfo {info}")
        listed = _mcp("tools/list", {})
        names = sorted(item.get("name") for item in listed.get("result", {}).get("tools") or [])
        needed = {"hnc_reality_step", "auris_coherence", "qgita_analyze"}
        print("SMOKE mcp_tools", " ".join(name for name in names if name in needed))
        if not needed.issubset(set(names)):
            failures.append(f"mcp tools missing {sorted(needed - set(names))}")
        hnc_call = _mcp(
            "tools/call",
            {"name": "hnc_reality_step", "arguments": {"enable_multiverse": False}},
        )
        hnc_text = hnc_call["result"]["content"][0]["text"]
        if hnc_call["result"].get("isError") is True:
            failures.append(f"hnc tool error {hnc_text[:240]}")
        else:
            hnc = json.loads(hnc_text)
            print(
                "SMOKE hnc",
                json.dumps(
                    {
                        "enable_multiverse": hnc.get("enable_multiverse"),
                        "coherence": hnc.get("coherence"),
                        "status": hnc.get("status"),
                    },
                    sort_keys=True,
                ),
            )
            if hnc.get("enable_multiverse") is not False or not _finite(hnc.get("coherence")):
                failures.append("hnc tool payload")
        qgita_call = _mcp("tools/call", {"name": "qgita_analyze", "arguments": {}})
        qgita_text = qgita_call["result"]["content"][0]["text"]
        if qgita_call["result"].get("isError") is True:
            failures.append(f"qgita tool error {qgita_text[:240]}")
        else:
            qgita = json.loads(qgita_text)
            print(
                "SMOKE qgita",
                json.dumps(
                    {
                        "detection_rate": qgita.get("detection_rate"),
                        "false_alarm_rate": qgita.get("false_alarm_rate"),
                        "ftcp_count": qgita.get("ftcp_count"),
                        "status": qgita.get("status"),
                    },
                    sort_keys=True,
                ),
            )
            if qgita.get("detection_rate") != "HOLD" or qgita.get("false_alarm_rate") != "HOLD":
                failures.append("qgita rates are not HOLD")
        auris_call = _mcp("tools/call", {"name": "auris_coherence", "arguments": {}})
        auris_text = auris_call["result"]["content"][0]["text"]
        print("SMOKE auris_mcp", auris_text[:400])
        if auris_call["result"].get("isError") is True:
            if "differs from pin" not in auris_text:
                failures.append("auris mcp error is not the pin refusal")
        else:
            auris_body = json.loads(auris_text)
            if auris_body.get("trade_readiness") != "HOLD":
                failures.append("auris mcp trade_readiness")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"mcp protocol {type(exc).__name__}: {exc}")

    cog_status, cog_body = _http_get(STACK_URL + "/api/cognition", timeout=60)
    try:
        cognition = json.loads(cog_body.decode("utf-8"))
    except json.JSONDecodeError:
        cognition = {}
    if cog_status == 200 and "hnc" in cognition:
        view = cognition_view(cognition)
        print("SMOKE cognition", json.dumps(view, sort_keys=True))
        if cognition.get("external_llm") is not False or cognition.get("live_trading") is not False:
            failures.append("cognition flags")
        if cognition.get("orders_placed") is not False:
            failures.append("cognition orders_placed")
        hnc = cognition.get("hnc") or {}
        if hnc.get("enable_multiverse") is not False or not _finite(hnc.get("coherence")):
            failures.append("cognition hnc")
        auris = cognition.get("auris") or {}
        readiness = _trade_view(auris.get("trade_readiness") or {})
        trade_failure = _cognition_trade_failure(readiness)
        if trade_failure:
            failures.append(trade_failure)
        derived = (cognition.get("qgita") or {}).get("derived_series") or {}
        on_lambda = (cognition.get("qgita") or {}).get("on_hnc_series") or {}
        if derived.get("rates_verdict") != "HOLD" or on_lambda.get("rates_verdict") != "HOLD":
            failures.append("cognition qgita rates")
        together = (cognition.get("together") or {}).get("auris_joined_to_lambda") or {}
        if together.get("verdict") != "HOLD":
            failures.append("auris joined to lambda")
    else:
        print("SMOKE cognition", cog_status, cog_body[:300])
        failures.append("cognition endpoint")

    if failures:
        print("SMOKE FAILED")
        for item in failures:
            print(" -", item)
        return 1
    print("SMOKE PASSED")
    return 0


def start(smoke_mode: bool) -> int:
    import threading

    arm_this_process()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if PIDFILE.is_file():
        raise SystemExit(f"stack already recorded in {PIDFILE}. Run {_stop_command()} first.")
    try:
        server = ThreadingHTTPServer(("127.0.0.1", STACK_PORT), make_handler())
    except OSError as exc:
        raise SystemExit(f"health port {STACK_PORT} is in use: {exc}") from exc
    thread = threading.Thread(target=server.serve_forever, name="aureon-plug-health", daemon=True)
    thread.start()
    PIDFILE.write_text(str(os.getpid()), encoding="utf-8")
    try:
        pids = start_children()
        health = wait_until_ready()
    except (SystemExit, OSError):
        stop_children()
        server.shutdown()
        raise
    print(json.dumps({"banner": "aureon-plug", "pids": pids, **health}, sort_keys=True))
    print(f"operator   {OPERATOR_URL}/healthz")
    print(f"ready      {OPERATOR_URL}/readyz")
    print(f"mcp        {MCP_URL}")
    print(f"frontend   {FRONTEND_URL}")
    print(f"cognition  {STACK_URL}/api/cognition")
    print(f"health     {STACK_URL}/healthz")
    if smoke_mode:
        try:
            code = smoke()
        finally:
            stop_children()
            server.shutdown()
        return code

    def _handle_stop(_signum: int, _frame: object) -> None:
        stop_children()
        server.shutdown()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)
    thread.join()
    return 0


def stop_recorded() -> int:
    if PIDFILE.is_file():
        try:
            pid = int(PIDFILE.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = 0
        if pid and pid != os.getpid():
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    stop_children()
    print(json.dumps({"ok": True, "stopped": True}))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--stop" in args:
        return stop_recorded()
    if "--smoke" in args:
        return start(smoke_mode=True)
    return start(smoke_mode=False)


if __name__ == "__main__":
    sys.exit(main())
