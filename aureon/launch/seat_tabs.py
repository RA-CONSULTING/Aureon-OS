"""One-command local boot for the live seat tabs.

Starts the gateway, the buses it proxies, and the 5173 UI. Live trading stays
off. No order is placed. A seat that does not answer is reported with the
reason.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _env() -> dict[str, str]:
    env = dict(os.environ)
    gateway = str(env.get("AUREON_SEAT_GATEWAY_PORT") or "8790")
    market = str(env.get("AUREON_SEAT_MARKET_PORT") or "8791")
    bridge = str(env.get("AUREON_FRONTEND_BRIDGE_PORT") or "8787")
    env["AUREON_LIVE_TRADING"] = "0"
    env["AUREON_SIMULATED_BOOT"] = "0"
    env["AUREON_DISABLE_REAL_ORDERS"] = "1"
    env["AUREON_DISABLE_EXCHANGE_MUTATIONS"] = "1"
    env["AUREON_ORDER_INTENT_PUBLISH"] = "0"
    env["AUREON_UNIFIED_ORDER_EXECUTOR"] = "0"
    env["AUREON_FUSION_API_TOKEN"] = env.get("AUREON_FUSION_API_TOKEN") or "local-selfhost-token"
    env["AUREON_FUSION_PORT"] = "8765"
    env["AUREON_OPERATOR_HOST"] = "127.0.0.1"
    env["AUREON_OPERATOR_PORT"] = gateway
    env["AUREON_SEAT_GATEWAY_PORT"] = gateway
    env["AUREON_SEAT_MARKET_PORT"] = market
    env["VITE_OPERATOR_PORT"] = gateway
    env["VITE_MARKET_STATUS_PORT"] = market
    env["VITE_BRIDGE_PORT"] = bridge
    env["VITE_OPERATOR_URL"] = f"http://127.0.0.1:{gateway}"
    env["AUREON_OPERATOR_URL"] = f"http://127.0.0.1:{gateway}"
    env["VITE_MARKET_STATUS_URL"] = f"http://127.0.0.1:{market}"
    env["AUREON_MARKET_STATUS_URL"] = env.get("AUREON_MARKET_STATUS_URL") or f"http://127.0.0.1:{market}/health"
    env["NEXUS_WS_HOST"] = "127.0.0.1"
    env["AUREON_FRONTEND_BRIDGE_PORT"] = bridge
    env["NEXUS_COMMAND_PORT"] = bridge
    env["VITE_BRIDGE_WS_URL"] = f"ws://127.0.0.1:{bridge}"
    env["VITE_BRIDGE_HTTP_URL"] = f"http://127.0.0.1:{bridge}"
    env["AUREON_FRONTEND_BRIDGE_URL"] = f"http://127.0.0.1:{bridge}/health"
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _spawn(name: str, cmd: list[str], env: dict[str, str], cwd: Path) -> subprocess.Popen[bytes] | None:
    log_dir = REPO / "state" / "seat_tabs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handle = (log_dir / f"{name}.log").open("ab")
    return subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=handle, stderr=subprocess.STDOUT)


def start_processes() -> list[tuple[str, str]]:
    """Start any seat that is not already listening. Returns notes."""

    base = _env()
    python = sys.executable
    gateway_port = int(base["AUREON_SEAT_GATEWAY_PORT"])
    market_port = int(base["AUREON_SEAT_MARKET_PORT"])
    bridge_port = int(base["AUREON_FRONTEND_BRIDGE_PORT"])
    notes: list[tuple[str, str]] = []
    plan: list[tuple[str, int, list[str], Path, dict[str, str]]] = [
        ("circulation", 8799, [python, "-m", "aureon.core.organism_circulation"], REPO, {}),
        (
            "market-status",
            market_port,
            [python, "-m", "aureon.exchanges.unified_market_status_server", "--port", str(market_port)],
            REPO,
            {},
        ),
        ("orca", 8888, [python, "-m", "aureon.launch.orca_seat", "--port", "8888"], REPO, {}),
        ("fusion", 8765, [python, "-m", "aureon_fusion.http_service"], REPO, {}),
        ("gateway", gateway_port, [python, "-m", "aureon.operator.operator_server"], REPO, {}),
        (
            "live-bridge",
            bridge_port,
            [python, "-m", "aureon.bridges.aureon_frontend_bridge"],
            REPO,
            {
                "NEXUS_WS_HOST": "127.0.0.1",
                "NEXUS_COMMAND_PORT": str(bridge_port),
                "AUREON_FRONTEND_BRIDGE_PORT": str(bridge_port),
            },
        ),
        (
            "error-sink",
            8088,
            [python, "-u", str(REPO / "deploy" / "selfhost" / "error_sink.py")],
            REPO,
            {
                "AUREON_ERROR_SINK_BIND": "127.0.0.1",
                "AUREON_ERROR_SINK_PORT": "8088",
                "AUREON_ERROR_SINK_PATH": str(REPO / "state" / "errors.jsonl"),
            },
        ),
        (
            "api-b",
            8766,
            [python, "-u", "-m", "aureon_fusion.http_service"],
            REPO,
            {
                "AUREON_FUSION_BIND": "127.0.0.1",
                "AUREON_FUSION_PORT": "8766",
                "AUREON_FUSION_API_TOKEN": "local-selfhost-token",
                "AUREON_REPLICA_ID": "api_b",
            },
        ),
        (
            "neural-canvas",
            13012,
            [python, "-m", "aureon_fusion.neural_canvas", "serve", "--port", "13012"],
            REPO,
            {},
        ),
        (
            "thought-hub",
            13002,
            [python, "-m", "aureon.launch.thought_hub_status", "--port", "13002"],
            REPO,
            {},
        ),
    ]
    vite = REPO / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    node = os.environ.get("AUREON_NODE") or "node"
    if vite.is_file():
        plan.append(
            (
                "frontend",
                5173,
                [node, str(vite), "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
                REPO / "frontend",
                {},
            )
        )
    else:
        notes.append(("frontend", "vite.js is absent"))
    for name, port, cmd, cwd, overlay in plan:
        if name == "error-sink" and not (REPO / "deploy" / "selfhost" / "error_sink.py").is_file():
            notes.append((name, "error_sink.py is absent"))
            continue
        if name == "gateway" and _port_open(port):
            notes.append((name, f"operator gateway already owns {port}; this boot does not bind it again"))
            continue
        if _port_open(port):
            notes.append((name, f"already listening on {port}"))
            continue
        env = dict(base)
        env.update(overlay)
        _spawn(name, cmd, env, cwd)
        notes.append((name, f"started for {port}"))
    notes.append(("system-hub", "retired; held so the tab does not show a refused connection"))
    notes.append(("bot-hunter", "retired; held so the tab does not show a refused connection"))
    notes.append(("dashboard-api", "retired; command routes stay down and no order is placed"))
    return notes


def wait_for_gateway(timeout_s: float = 20.0) -> bool:
    gateway = os.environ.get("AUREON_SEAT_GATEWAY_PORT") or _env().get("AUREON_SEAT_GATEWAY_PORT") or "8790"
    url = f"http://127.0.0.1:{gateway}/healthz"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> int:
    from aureon.launch.faculty_files import record_missing_faculties

    written = record_missing_faculties()
    print(f"faculty absence records written={len(written)}", flush=True)
    for note in start_processes():
        print(f"seat {note[0]}: {note[1]}", flush=True)
    gateway = os.environ.get("AUREON_SEAT_GATEWAY_PORT") or "8790"
    if not wait_for_gateway():
        log = REPO / "state" / "seat_tabs" / "gateway.log"
        tail = ""
        if log.is_file():
            tail = log.read_text(encoding="utf-8", errors="replace")[-500:]
        print(
            f"operator gateway failed to bind http://127.0.0.1:{gateway}/healthz\n{tail}",
            flush=True,
        )
        return 1
    print(f"operator gateway owns http://127.0.0.1:{gateway}/healthz", flush=True)
    print("tabs at http://127.0.0.1:5173/console/seats", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
