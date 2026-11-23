"""Adversarial source/config checks for the maintained public GPU Space.

These are local contract tests, not substitutes for `docker build`, `nginx -t`,
or the real CUDA acceptance probe.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from aureon_fusion import unity_supervisor
from deploy.huggingface import demo_api, smoke

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "huggingface"
ENTRYPOINT = (DEPLOY / "entrypoint.sh").read_text(encoding="utf-8")
NGINX = (DEPLOY / "nginx.conf").read_text(encoding="utf-8")
SUPERVISOR = (DEPLOY / "supervisord.conf").read_text(encoding="utf-8")
DOCKERFILE = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
DOCKERIGNORE = (DEPLOY / "Dockerfile.dockerignore").read_text(encoding="utf-8")
MODEL_SERVICE = (DEPLOY / "model_service.sh").read_text(encoding="utf-8")


def _export(name: str) -> str | None:
    match = re.search(rf"^export {re.escape(name)}=(.*)$", ENTRYPOINT, re.MULTILINE)
    return match.group(1) if match else None


@pytest.mark.parametrize("name,value", {
    "AUREON_PUBLIC_READ_ONLY": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_FUSION_ARM_LIVE": '""',
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_ORDER_INTENT_PUBLISH": "0",
    "AUREON_AUTONOMY_MODE": "guarded",
    "AUREON_DEPLOYMENT_HOLD": "1",
    "AUREON_OPERATOR_ALLOW_LIVE": '""',
    "AUREON_LOCAL_ACTIONS_ARMED": "0",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
    "AUREON_DRY_RUN": "1",
    "DRY_RUN": "1",
    "AUREON_CODE_AUTO_APPROVE": "0",
    "AUREON_SOUL_ACT": "0",
    "AUREON_BILLING_CHARGE_ENABLED": "0",
    "AUREON_SOVEREIGN_MODE": "0",
    "AUREON_ACCEPT_LIVE_RISK": "0",
    "AUREON_ENABLE_AUTONOMOUS_CONTROL": "0",
    "AUREON_EXTERNAL_LLM_FALLBACK": "none",
    "AUREON_OWN_LLM_BASE_URL": "http://127.0.0.1:11435/v1",
    "AUREON_LLM_BASE_URL": "$AUREON_OWN_LLM_BASE_URL",
    "AUREON_OPERATOR_WAIT_OWN_MODEL": "1",
    "SERO_STATE_ROOT": "$RT/state",
    "SERO_FUSION_STATE": "$RT/fusion-state",
    "AUREON_FUSION_ORGAN_ALLOWLIST": "hnc_core",
}.items())
def test_entrypoint_unconditionally_sets_public_invariants(name: str, value: str) -> None:
    assert _export(name) == value
    assert ENTRYPOINT.index(f"export {name}=") < ENTRYPOINT.index("exec /usr/bin/supervisord")


def test_entrypoint_removes_inherited_credentials_and_never_enables_shell_trace() -> None:
    unset_block = ENTRYPOINT.split("unset \\\n", 1)[1].split("\n\n# Own-model", 1)[0]
    for name in (
        "KRAKEN_API_KEY", "KRAKEN_API_SECRET", "BINANCE_API_KEY",
        "ALPACA_SECRET_KEY", "CAPITAL_PASSWORD", "COINBASE_API_SECRET",
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN", "AUREON_LLM_API_KEY",
    ):
        assert name in unset_block
    for name in demo_api.SENSITIVE_ENV:
        if name not in {"AUREON_OPERATOR_API_KEY", "AUREON_FUSION_API_TOKEN"}:
            assert name in unset_block, f"public entrypoint must clear {name}"
    assert "set -euo pipefail" in ENTRYPOINT
    assert "set -x" not in ENTRYPOINT
    assert "printenv" not in ENTRYPOINT
    assert not re.search(r"echo[^\n]*(?:API_KEY|API_SECRET|PASSWORD|TOKEN)[^\n]*\$", ENTRYPOINT)


def test_every_declared_sensitive_value_fails_public_posture() -> None:
    for name in demo_api.SENSITIVE_ENV:
        env = dict(demo_api.PUBLIC_ENV)
        env[name] = "inherited-sensitive-value"
        posture = demo_api.public_posture(env)
        assert posture["ok"] is False
        assert posture["checks"]["credentials_absent"] is False
        assert "inherited-sensitive-value" not in json.dumps(posture)


def test_restart_removes_only_isolated_authority_flags() -> None:
    assert '"$SERO_FUSION_STATE/capital_release.flag"' in ENTRYPOINT
    assert '"$SERO_FUSION_STATE/queen_mind_restart_approved.json"' in ENTRYPOINT
    rm_block = ENTRYPOINT.split("rm -f -- \\", 1)[1].split("\n\n# Postgres", 1)[0]
    assert "capital_release.flag" in rm_block
    assert "queen_mind_restart_approved.json" in rm_block
    assert "touch" not in rm_block
    assert "approved" not in ENTRYPOINT.split("python3 - <<'PY'", 1)[1]


def test_random_internal_bearers_are_not_fixed_or_logged() -> None:
    assert ENTRYPOINT.count("secrets.token_urlsafe(32)") == 2
    assert "aureon-public-fusion-token" not in ENTRYPOINT + NGINX + SUPERVISOR
    assert "__AUREON_OPERATOR_KEY__" in NGINX
    assert "__AUREON_FUSION_TOKEN__" in NGINX
    assert "token_urlsafe" not in NGINX


def test_model_bootstrap_and_server_are_pinned_and_loopback_only() -> None:
    assert "--require-cuda" in MODEL_SERVICE
    assert "--strict-startup" in MODEL_SERVICE
    assert "--host 127.0.0.1" in MODEL_SERVICE
    assert "--port 11435" in MODEL_SERVICE
    assert smoke.EXPECTED_HASH in MODEL_SERVICE
    assert "--expected-weight-size 13990806664" in MODEL_SERVICE
    assert 'exec "$PYTHON" -u "$ROOT/training/aureon_chat_server.py"' in MODEL_SERVICE
    assert "HF_HUB_OFFLINE=1" in MODEL_SERVICE
    assert MODEL_SERVICE.index("model_bootstrap.py") < MODEL_SERVICE.index("HF_HUB_OFFLINE=1")
    assert "0.0.0.0:11435" not in NGINX
    assert "11435" not in NGINX


def test_nginx_generic_operator_fusion_and_mcp_routes_never_proxy() -> None:
    for prefix in ("/api/", "/fusion/", "/mcp/"):
        block = NGINX.split(f"location {prefix} {{", 1)[1].split("\n    }", 1)[0]
        assert 'if ($http_authorization = "") { return 401; }' in block
        assert "return 403;" in block
        assert "proxy_pass" not in block
        assert "proxy_set_header Authorization" not in block


def test_nginx_public_write_surface_is_exactly_one_bounded_route() -> None:
    exact_post = re.findall(r"location = ([^ ]+) \{\n\s+limit_req[^\n]+\n\s+limit_except POST", NGINX)
    assert exact_post == ["/api/demo/generate"]
    generate = NGINX.split("location = /api/demo/generate {", 1)[1].split("\n    }", 1)[0]
    assert "zone=aureon_generate" in generate
    assert 'proxy_set_header Authorization "";' in generate
    assert "proxy_pass http://demo_api;" in generate
    for location in ("location /hnc/ {", "location /app/ {", "location /assets/ {", "location / {"):
        block = NGINX.split(location, 1)[1].split("\n    }", 1)[0]
        assert "limit_except GET HEAD { deny all; }" in block


def test_nginx_injects_operator_bearer_only_into_reviewed_exact_reads() -> None:
    assert NGINX.count('proxy_set_header Authorization "Bearer __AUREON_OPERATOR_KEY__";') == 2
    assert NGINX.count('proxy_set_header Authorization "Bearer __AUREON_FUSION_TOKEN__";') == 1
    assert "location = /fusion/api/status" in NGINX
    assert "proxy_pass http://aureon_api/api/status;" in NGINX
    for method in ("PUT", "PATCH", "DELETE"):
        assert f"limit_except GET {method}" not in NGINX


def test_supervisor_retains_required_services_and_fails_model_or_smoke_cleanly() -> None:
    for process in smoke.REQUIRED_PROCESSES:
        assert f"[program:{process}]" in SUPERVISOR
    assert "[program:smoke]" in SUPERVISOR
    demo = SUPERVISOR.split("[program:demo_api]", 1)[1].split("\n[program:", 1)[0]
    assert 'AUREON_OPERATOR_API_KEY=""' in demo
    assert 'AUREON_FUSION_API_TOKEN=""' in demo
    model = SUPERVISOR.split("[program:aureon_model]", 1)[1].split("\n[program:", 1)[0]
    smoke_block = SUPERVISOR.split("[program:smoke]", 1)[1]
    for block in (model, smoke_block):
        assert "autorestart=false" in block
        assert "startretries=0" in block


def test_frontend_is_rebuilt_with_pinned_node_and_no_stale_dist() -> None:
    assert "FROM node:22-bookworm-slim AS frontend-build" in DOCKERFILE
    assert "npm ci --ignore-scripts --no-audit --no-fund" in DOCKERFILE
    assert "npm run typecheck && npm run lint:shell && npm run build" in DOCKERFILE
    assert "COPY --from=frontend-build" in DOCKERFILE
    assert "/build/frontend/dist" in DOCKERFILE
    assert "FROM nvcr.io/nvidia/pytorch:25.05-py3" in DOCKERFILE
    assert "USER aureon" in DOCKERFILE
    assert "VITE_OPERATOR_TOKEN" not in DOCKERFILE
    assert "frontend/dist" in DOCKERIGNORE
    assert "!frontend/dist" not in DOCKERIGNORE


def test_ngc_existing_uid_does_not_block_the_nonroot_runtime() -> None:
    match = re.search(r"^RUN useradd --create-home --uid ([0-9]+) aureon$", DOCKERFILE, re.MULTILINE)
    assert match is not None
    assert int(match.group(1)) > 1000


def test_build_context_excludes_credentials_and_does_not_reinclude_json_wholesale() -> None:
    for pattern in ("**/.env", "**/.env.*", "**/*.pem", "**/*.key", ".git", "runtime", "state"):
        assert pattern in DOCKERIGNORE
    assert "!**/*.json" not in DOCKERIGNORE
    assert "!huggingface/hnc-field/replay/brain.json" in DOCKERIGNORE
    assert "!huggingface/organism-replay/replay/organism.json" in DOCKERIGNORE
    assert "!training/aureon_chat_server.py" in DOCKERIGNORE
    assert "!training/**" not in DOCKERIGNORE


def test_fusion_state_override_isolated_from_checkout(tmp_path: Path) -> None:
    runtime = tmp_path / "fresh-public-state"
    script = """
import json
from aureon_fusion import paths, organ_registry
print(json.dumps({
  'state': str(paths.FUSION_STATE),
  'capital': str(organ_registry.CAPITAL_RELEASE_FLAG),
  'queen': str(organ_registry.QUEEN_MIND_RESTART_APPROVAL),
}))
"""
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "SERO_WORKSPACE": str(ROOT),
        "SERO_FUSION_STATE": str(runtime),
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "AUREON_AUDIT_MODE": "1",
    })
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env, check=True)
    payload = json.loads(result.stdout)
    assert payload["state"] == str(runtime)
    assert payload["capital"] == str(runtime / "capital_release.flag")
    assert payload["queen"] == str(runtime / "queen_mind_restart_approved.json")


def test_public_state_root_separates_all_fusion_writes_from_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    runtime = tmp_path / "runtime"
    state = runtime / "state"
    mutable_names = (
        "SERO_MIND", "SERO_CONSCIENCE", "SERO_FEEL", "SERO_MEMORY_WEB",
        "SERO_THOUGHTBUS", "SERO_MYCELIUM", "SERO_CHIRP", "SERO_AUTONOMOUS",
        "TEMPORAL_STATE", "SHARED_STATE", "PIDS", "LOGS", "UNIFIED_LOGS",
        "PLANETARY_MONITOR", "HNC_LOGS",
    )
    script = f"""
import json
from aureon_fusion import paths
paths.ensure_dirs()
print(json.dumps({{
  'workspace': str(paths.WORKSPACE),
  'upstream': str(paths.AUREON_UPSTREAM),
  'state_root': str(paths.STATE_ROOT),
  'mutable': {{name: str(getattr(paths, name)) for name in {mutable_names!r}}},
  'source_entries': [path.name for path in paths.WORKSPACE.iterdir()],
  'runtime_home': str(paths.RUNTIME_HOME),
  'fusion_state': str(paths.FUSION_STATE),
}}))
"""
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT),
        "SERO_WORKSPACE": str(source),
        "SERO_STATE_ROOT": str(state),
        "SERO_RUNTIME_HOME": str(runtime / "home"),
        "SERO_FUSION_STATE": str(runtime / "fusion-state"),
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "AUREON_AUDIT_MODE": "1",
    })
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env, check=True)
    payload = json.loads(result.stdout)
    assert payload["workspace"] == str(source)
    assert payload["upstream"] == str(source)
    assert payload["state_root"] == str(state)
    assert payload["source_entries"] == []
    assert payload["runtime_home"] == str(runtime / "home")
    assert payload["fusion_state"] == str(runtime / "fusion-state")
    for value in payload["mutable"].values():
        path = Path(value)
        path.relative_to(state)
        assert path.is_dir()
    assert '"$ROOT/$d"' not in ENTRYPOINT


def test_supervisor_allowlist_precedes_full_autonomy_and_release(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUREON_FUSION_ORGAN_ALLOWLIST", "hnc_core")
    monkeypatch.setattr(unity_supervisor.importlib, "reload", lambda module: module)
    monkeypatch.setattr(unity_supervisor.organ_registry, "ORGANS", {
        "unity_supervisor": {}, "hnc_core": {}, "queen_mind": {}, "exchange_executor": {},
    })
    monkeypatch.setattr(unity_supervisor.organ_registry, "status_data", lambda: {
        "unity_supervisor": {"state": "running", "pid": 1},
        "hnc_core": {"state": "running", "pid": 2},
        "queen_mind": {"state": "stopped", "pid": None},
        "exchange_executor": {"state": "stopped", "pid": None},
    })
    monkeypatch.setattr(unity_supervisor.organ_registry, "_release_granted", lambda: True)
    monkeypatch.setattr(unity_supervisor.organ_registry, "_autonomy_releases_capital_pin", lambda: True)
    start = mock.Mock()
    monkeypatch.setattr(unity_supervisor.organ_registry, "start", start)
    monkeypatch.setattr(unity_supervisor.organ_registry, "write_observed_process_identity", lambda: None)
    monkeypatch.setattr(unity_supervisor.events, "publish_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(unity_supervisor, "FUSION_STATE", tmp_path)
    monkeypatch.setattr(unity_supervisor, "SUPERVISOR_STATE_FILE", tmp_path / "supervisor.json")

    result = unity_supervisor._supervise_cycle()

    start.assert_not_called()
    decisions = {item["organ"]: item["action"] for item in result["decisions"]}
    assert decisions["queen_mind"] == "skip_not_allowlisted"
    assert decisions["exchange_executor"] == "skip_not_allowlisted"
    assert result["restarts_this_cycle"] == []


def _ready_body() -> dict:
    names = (
        "ready", "provider_mode", "model", "immutable_revision", "weight_sha256",
        "weight_size_bytes", "parameters", "vocabulary", "eos", "cuda",
        "startup_generation_verified", "startup_generation_tokens",
    )
    return {
        "ok": True,
        "ready": True,
        "provider_mode": smoke.EXPECTED_PROVIDER,
        "model": smoke.EXPECTED_MODEL,
        "live_trading": False,
        "orders_placed": 0,
        "checks": {
            "public_posture": {"ok": True},
            "operator": {"ok": True},
            "model": {"ok": True, "checks": dict.fromkeys(names, True)},
        },
    }


def test_smoke_requires_every_aggregate_identity_and_safety_check() -> None:
    revision = "a" * 40
    assert smoke.validate_readiness(_ready_body(), revision) == []
    body = _ready_body()
    body["checks"]["model"]["checks"]["cuda"] = False
    assert "model_evidence" in smoke.validate_readiness(body, revision)
    assert "configured_revision" in smoke.validate_readiness(_ready_body(), "main")
    body = _ready_body()
    body["live_trading"] = True
    assert "paper_only" in smoke.validate_readiness(body, revision)
