"""End-to-end smoke for the self-hosted stack. No orders. No long loops."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "selfhost" / "docker-compose.yml"
TOKEN = os.environ.get("AUREON_FUSION_API_TOKEN", "local-selfhost-token")
BASE = os.environ.get("AUREON_SELFHOST_BASE", "http://127.0.0.1:8080").rstrip("/")
MODE = os.environ.get("AUREON_SELFHOST_MODE", "compose")


def _get(path: str, token: str | None = None) -> tuple[int, bytes, str]:
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("Content-Type", "")


def _docker() -> list[str]:
    probe = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode == 0:
        return ["docker"]
    return ["sudo", "docker"]


def _compose(*args: str) -> str:
    completed = subprocess.run(
        [*_docker(), "compose", "-f", str(COMPOSE), *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _psql(sql: str) -> subprocess.CompletedProcess[str]:
    if MODE == "compose":
        return subprocess.run(
            [*_docker(), "compose", "-f", str(COMPOSE), "exec", "-T", "postgres", "psql", "-U", "aureon", "-d", "aureon", "-v", "ON_ERROR_STOP=1", "-c", sql],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    return subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", "aureon", "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True,
        text=True,
    )


def _redis_get() -> str:
    if MODE == "compose":
        completed = subprocess.run(
            [*_docker(), "compose", "-f", str(COMPOSE), "exec", "-T", "redis", "redis-cli", "GET", "aureon:fusion:status"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout
    completed = subprocess.run(["redis-cli", "GET", "aureon:fusion:status"], check=True, capture_output=True, text=True)
    return completed.stdout


def _organ_pids() -> dict[str, int]:
    if MODE != "compose":
        path = ROOT / "deploy" / "selfhost" / "runtime" / "pids.json"
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {name: int(pid) for name, pid in data.items()}
    pids = {}
    for name in ("api_a", "api_b", "frontend", "nginx", "error_sink"):
        raw = _compose("ps", "-q", name).strip()
        if not raw:
            continue
        inspected = subprocess.run(
            [*_docker(), "inspect", "-f", "{{.State.Pid}}", raw.splitlines()[0]],
            check=True,
            capture_output=True,
            text=True,
        )
        pid = int(inspected.stdout.strip() or "0")
        if pid:
            pids[name] = pid
    return pids


def _wait_health() -> None:
    deadline = time.time() + 90
    last = ""
    while time.time() < deadline:
        try:
            status, body, _ctype = _get("/healthz")
            if status == 200 and b'"live_trading": false' in body:
                return
            last = body.decode("utf-8", "replace")[:200]
        except Exception as exc:
            last = str(exc)
        time.sleep(1)
    raise SystemExit(f"healthz did not become ready: {last}")


def main() -> int:
    os.environ.setdefault("AUREON_LIVE_TRADING", "0")
    _wait_health()
    failures: list[str] = []

    status, body, _ctype = _get("/")
    page = body.decode("utf-8", "replace")
    if status != 200 or "Aureon OS" not in page or "LIVE TRADING OFF" not in page:
        failures.append(f"frontend console status={status}")
    status, body, _ctype = _get("/app/")
    if status != 200 or b"Aureon OS" not in body:
        failures.append(f"frontend app status={status}")

    status, body, _ctype = _get("/healthz")
    health = json.loads(body)
    if health.get("live_trading") is not False or health.get("may_act") is not False or health.get("hosting") != "self-hosted":
        failures.append(f"health contract {health}")

    status, _body, _ctype = _get("/api/status")
    if status != 401:
        failures.append(f"auth open status={status}")
    status, body, _ctype = _get("/api/status", token=TOKEN)
    first = json.loads(body)
    if status != 200 or first.get("may_act") is not False or first.get("live_trading") is not False:
        failures.append("authenticated status is not disarmed")
    status, body, _ctype = _get("/api/status", token=TOKEN)
    second = json.loads(body)
    if second.get("cache") != "hit" or second.get("cache_layer") != "redis":
        failures.append(f"redis cache was {second.get('cache')} layer={second.get('cache_layer')}")
    cached = _redis_get()
    if cached.strip() in {"", "(nil)"}:
        failures.append("redis key missing")

    replicas = set()
    for _ in range(8):
        status, body, _ctype = _get("/healthz")
        if status == 200:
            replicas.add(json.loads(body).get("replica"))
    if replicas != {"api_a", "api_b"}:
        failures.append(f"load balancer replicas={sorted(replicas)}")

    status, body, _ctype = _get("/error-test", token=TOKEN)
    if status != 500:
        failures.append(f"error-test status={status}")

    limited = False
    for _ in range(12):
        status, _body, _ctype = _get("/api/status", token=TOKEN)
        if status == 429:
            limited = True
            break
    if not limited:
        failures.append("nginx rate limit did not return 429")
    time.sleep(0.5)
    sink = ROOT / "deploy" / "selfhost" / "runtime" / "errors.jsonl"
    if not sink.is_file() or "fusion_error_sink_test" not in sink.read_text(encoding="utf-8"):
        failures.append("error sink did not record the test exception")
    logs = list((ROOT / "deploy" / "selfhost" / "runtime").glob("api_*.jsonl"))
    if not logs or not any('"event": "request"' in path.read_text(encoding="utf-8") or '"event":"request"' in path.read_text(encoding="utf-8") for path in logs):
        failures.append("structured api log missing")

    rls = _psql(
        "SELECT c.relrowsecurity FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relname = 'schumann_resonance_data';"
    )
    if rls.returncode != 0 or "t" not in rls.stdout:
        failures.append(f"rls not enabled: {rls.stderr}")
    policy = _psql("SELECT polname FROM pg_policy WHERE polrelid = 'public.schumann_resonance_data'::regclass;")
    if "deny_direct_client_access" not in policy.stdout:
        failures.append("rls policy missing")
    inserted = _psql(
        "INSERT INTO public.schumann_resonance_data (owner_id, frequency_hz, source) "
        "VALUES ('smoke', NULL, 'smoke-no-frequency');"
    )
    if inserted.returncode != 0:
        failures.append(f"rls table insert failed: {inserted.stderr}")
    denied = _psql("SET ROLE anon; SELECT count(*) FROM public.schumann_resonance_data;")
    if denied.returncode == 0:
        failures.append("anon role was able to read a locked table")
    allowed = _psql("SET ROLE service_role; SELECT count(*) FROM public.schumann_resonance_data;")
    visible = [int(part) for part in allowed.stdout.split() if part.isdigit()]
    if allowed.returncode != 0 or not visible or visible[0] < 1:
        failures.append(f"service_role could not read under rls: {allowed.stderr or allowed.stdout}")

    sys.path.insert(0, str(ROOT))
    from aureon_fusion.faculty_refresh import refresh

    report = refresh(organ_pids=_organ_pids())
    print(json.dumps(report["rows"], indent=2))
    for row in report["rows"]:
        if row["status"] not in {"fresh", "blocked"}:
            failures.append(f"{row['faculty']} is {row['status']}")
        if row["status"] == "blocked" and not row["blocked_reason"]:
            failures.append(f"{row['faculty']} blocked without a reason")
        if row["truth_status"] in {"simulated", "test_fixture"}:
            failures.append(f"{row['faculty']} is synthetic")
    if report["health"].get("simulated_detected"):
        failures.append(f"simulated faculties: {report['health']['simulated_detected']}")

    if failures:
        print("SMOKE FAILED")
        for item in failures:
            print(" -", item)
        return 1
    print("SMOKE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
