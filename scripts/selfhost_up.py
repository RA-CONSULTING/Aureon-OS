"""Non-Docker self-host supervisor.

Starts Postgres RLS, Redis, two API replicas, the frontend HTTP profile,
nginx, and the local error sink. Live trading stays off.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "deploy" / "selfhost" / "runtime"
NGINX_CONF = RUNTIME / "nginx.conf"
PIDFILE = RUNTIME / "supervisor.pid"
PIDS = RUNTIME / "pids.json"
TOKEN = "local-selfhost-token"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def _postgres() -> None:
    probe = _run(["pg_isready"], check=False)
    if probe.returncode != 0:
        _run(["sudo", "pg_ctlcluster", "16", "main", "start"])
    exists = _run(["sudo", "-u", "postgres", "psql", "-tAc", "SELECT 1 FROM pg_database WHERE datname='aureon'"])
    if exists.stdout.strip() != "1":
        _run(["sudo", "-u", "postgres", "createdb", "aureon"])
    sql_files = [
        ROOT / "deploy" / "selfhost" / "postgres" / "01_roles.sql",
        ROOT / "deploy" / "selfhost" / "postgres" / "02_tables.sql",
        ROOT / "supabase" / "migrations" / "20260811210525_lock_down_legacy_public_tables.sql",
    ]
    for path in sql_files:
        _run(["sudo", "-u", "postgres", "psql", "-d", "aureon", "-v", "ON_ERROR_STOP=1", "-f", str(path)])


def _redis() -> None:
    probe = _run(["redis-cli", "ping"], check=False)
    if probe.stdout.strip() != "PONG":
        subprocess.Popen(["redis-server", "--daemonize", "yes", "--bind", "127.0.0.1", "--port", "6379"])
        for _ in range(20):
            if _run(["redis-cli", "ping"], check=False).stdout.strip() == "PONG":
                return
            time.sleep(0.2)
        raise SystemExit("redis did not answer")


def _write_nginx() -> None:
    temp = RUNTIME / "nginx-temp"
    for name in ("client", "proxy", "fastcgi", "uwsgi", "scgi"):
        (temp / name).mkdir(parents=True, exist_ok=True)
    NGINX_CONF.write_text(
        f"""
daemon off;
worker_processes 1;
error_log {RUNTIME / "nginx-error.log"};
pid {RUNTIME / "nginx.pid"};
events {{ worker_connections 128; }}
http {{
  access_log {RUNTIME / "nginx-access.log"};
  client_body_temp_path {temp / "client"};
  proxy_temp_path {temp / "proxy"};
  fastcgi_temp_path {temp / "fastcgi"};
  uwsgi_temp_path {temp / "uwsgi"};
  scgi_temp_path {temp / "scgi"};
  limit_req_zone $binary_remote_addr zone=aureon_api:10m rate=2r/s;
  limit_req_status 429;
  upstream aureon_api {{
    server 127.0.0.1:8765;
    server 127.0.0.1:8766;
  }}
  server {{
    listen 127.0.0.1:8080;
    location = /healthz {{ proxy_pass http://aureon_api; }}
    location = /readyz {{ proxy_pass http://aureon_api; }}
    location /api/ {{
      limit_req zone=aureon_api burst=3 nodelay;
      proxy_pass http://aureon_api;
    }}
    location = /error-test {{
      limit_req zone=aureon_api burst=3 nodelay;
      proxy_pass http://aureon_api;
    }}
    location /app/ {{ proxy_pass http://127.0.0.1:5173/; }}
    location / {{
      root {ROOT / "deploy" / "selfhost" / "www"};
      try_files $uri $uri/ /index.html;
    }}
  }}
}}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _spawn(name: str, cmd: list[str], env: dict[str, str], log_name: str) -> int:
    log_path = RUNTIME / log_name
    handle = log_path.open("a", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    return proc.pid


def _api_env(replica: str, port: str) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": str(ROOT),
            "AUREON_FUSION_BIND": "127.0.0.1",
            "AUREON_FUSION_PORT": port,
            "AUREON_FUSION_API_TOKEN": TOKEN,
            "AUREON_LIVE_TRADING": "0",
            "AUREON_FUSION_ARM_LIVE": "",
            "AUREON_FUSION_RATE_LIMIT": "100000",
            "AUREON_REDIS_URL": "redis://127.0.0.1:6379/0",
            "AUREON_ERROR_WEBHOOK_URL": "http://127.0.0.1:8088/envelope",
            "AUREON_FUSION_CACHE_TTL_S": "30",
            "AUREON_REPLICA_ID": replica,
            "AUREON_LOG_PATH": str(RUNTIME / f"{replica}.jsonl"),
            "AUREON_ERROR_SINK_PATH": str(RUNTIME / "errors.jsonl"),
        }
    )
    return env


def start() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    os.chmod(RUNTIME, 0o777)
    _postgres()
    _redis()
    _write_nginx()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["AUREON_LIVE_TRADING"] = "0"
    env["AUREON_ERROR_SINK_BIND"] = "127.0.0.1"
    env["AUREON_ERROR_SINK_PORT"] = "8088"
    env["AUREON_ERROR_SINK_PATH"] = str(RUNTIME / "errors.jsonl")
    pids = {
        "error_sink": _spawn("error_sink", [sys.executable, str(ROOT / "deploy" / "selfhost" / "error_sink.py")], env, "error_sink.out"),
        "api_a": _spawn("api_a", [sys.executable, "-m", "aureon_fusion.http_service"], _api_env("api_a", "8765"), "api_a.out"),
        "api_b": _spawn("api_b", [sys.executable, "-m", "aureon_fusion.http_service"], _api_env("api_b", "8766"), "api_b.out"),
        "frontend": _spawn(
            "frontend",
            [sys.executable, "-m", "aureon.operator.local_http_profile", "--serve", "--host", "127.0.0.1", "--port", "5173"],
            env,
            "frontend.out",
        ),
        "hnc_core": _spawn(
            "hnc_core",
            [sys.executable, "-m", "aureon_fusion.hnc_core", "--supervise"],
            env,
            "hnc_core.out",
        ),
    }
    nginx = subprocess.Popen(["nginx", "-c", str(NGINX_CONF)], start_new_session=True)
    pids["nginx"] = nginx.pid
    PIDS.write_text(json.dumps(pids), encoding="utf-8")
    PIDFILE.write_text(str(os.getpid()), encoding="utf-8")
    print(json.dumps({"ok": True, "base": "http://127.0.0.1:8080", "live_trading": False, "pids": pids}))

    def _stop(_signum, _frame) -> None:
        stop()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while True:
        time.sleep(2)
        current = json.loads(PIDS.read_text(encoding="utf-8"))
        for name, pid in list(current.items()):
            try:
                os.kill(int(pid), 0)
            except OSError:
                if name == "nginx":
                    nginx = subprocess.Popen(["nginx", "-c", str(NGINX_CONF)], start_new_session=True)
                    current[name] = nginx.pid
                elif name == "frontend":
                    current[name] = _spawn(
                        name,
                        [sys.executable, "-m", "aureon.operator.local_http_profile", "--serve", "--host", "127.0.0.1", "--port", "5173"],
                        env,
                        "frontend.out",
                    )
                elif name == "error_sink":
                    current[name] = _spawn(name, [sys.executable, str(ROOT / "deploy" / "selfhost" / "error_sink.py")], env, "error_sink.out")
                elif name == "hnc_core":
                    current[name] = _spawn(
                        name,
                        [sys.executable, "-m", "aureon_fusion.hnc_core", "--supervise"],
                        env,
                        "hnc_core.out",
                    )
                elif name.startswith("api_"):
                    port = "8765" if name == "api_a" else "8766"
                    current[name] = _spawn(name, [sys.executable, "-m", "aureon_fusion.http_service"], _api_env(name, port), f"{name}.out")
        PIDS.write_text(json.dumps(current), encoding="utf-8")


def stop() -> None:
    if PIDS.is_file():
        pids = json.loads(PIDS.read_text(encoding="utf-8"))
        for pid in pids.values():
            try:
                os.kill(int(pid), signal.SIGTERM)
            except OSError:
                pass
    if NGINX_CONF.is_file():
        subprocess.run(["nginx", "-c", str(NGINX_CONF), "-s", "stop"], check=False)
    if PIDFILE.is_file():
        PIDFILE.unlink()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--stop" in args:
        stop()
        print(json.dumps({"ok": True, "stopped": True}))
        return 0
    start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
