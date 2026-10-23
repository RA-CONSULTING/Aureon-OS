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
    env["AUREON_LIVE_TRADING"] = "0"
    env["AUREON_SIMULATED_BOOT"] = "0"
    env["AUREON_DISABLE_REAL_ORDERS"] = "1"
    env["AUREON_DISABLE_EXCHANGE_MUTATIONS"] = "1"
    env["AUREON_ORDER_INTENT_PUBLISH"] = "0"
    env["AUREON_UNIFIED_ORDER_EXECUTOR"] = "0"
    env["AUREON_FUSION_API_TOKEN"] = env.get("AUREON_FUSION_API_TOKEN") or "local-selfhost-token"
    env["AUREON_FUSION_PORT"] = "8765"
    env["AUREON_OPERATOR_HOST"] = "127.0.0.1"
    env["AUREON_OPERATOR_PORT"] = "8790"
    env["VITE_OPERATOR_URL"] = "http://127.0.0.1:8790"
    env["AUREON_OPERATOR_URL"] = "http://127.0.0.1:8790"
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
    notes: list[tuple[str, str]] = []
    plan: list[tuple[str, int, list[str], Path, dict[str, str]]] = [
        ("circulation", 8799, [python, "-m", "aureon.core.organism_circulation"], REPO, {}),
        ("market-status", 8791, [python, "-m", "aureon.exchanges.unified_market_status_server", "--port", "8791"], REPO, {}),
        ("orca", 8888, [python, "-m", "aureon.launch.orca_seat", "--port", "8888"], REPO, {}),
        ("fusion", 8765, [python, "-m", "aureon_fusion.http_service"], REPO, {}),
        ("gateway", 8790, [python, "-m", "aureon.operator.operator_server"], REPO, {}),
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
        if _port_open(port):
            notes.append((name, f"already listening on {port}"))
            continue
        env = dict(base)
        env.update(overlay)
        _spawn(name, cmd, env, cwd)
        notes.append((name, f"started for {port}"))
    notes.append(("thought-hub", "not started; its goal loop can pursue trading"))
    notes.append(("system-hub", "not started; separate server stays down"))
    notes.append(("bot-hunter", "not started; separate server stays down"))
    notes.append(("dashboard-api", "not started; separate server stays down"))
    return notes


def wait_for_gateway(timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8790/healthz", timeout=1.0) as response:
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
    if not wait_for_gateway():
        print("gateway http://127.0.0.1:8790/healthz did not answer", flush=True)
        return 1
    print("gateway listening on http://127.0.0.1:8790/healthz", flush=True)
    print("tabs at http://127.0.0.1:5173/console/seats", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
