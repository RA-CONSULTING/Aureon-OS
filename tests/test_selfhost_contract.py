"""Static contract for the self-host stack. The live proof is scripts/selfhost_smoke.py."""

from __future__ import annotations

from pathlib import Path

from aureon.operator.local_http_profile import service_environment

ROOT = Path(__file__).resolve().parents[1]


def test_local_http_profile_sets_no_secrets():
    env = service_environment("frontend_vite", {"PATH": "/usr/bin"}, required=True)
    assert env["AUREON_HTTP_PROFILE"] == "local"
    assert env["AUREON_LIVE_TRADING"] == "0"
    assert env["AUREON_DISABLE_REAL_ORDERS"] == "1"
    blob = " ".join(f"{key}={value}" for key, value in env.items())
    assert "API_KEY" not in blob
    assert "SECRET" not in blob
    assert "BEGIN PRIVATE" not in blob


def test_compose_stack_covers_every_layer():
    compose = (ROOT / "deploy" / "selfhost" / "docker-compose.yml").read_text(encoding="utf-8")
    nginx = (ROOT / "deploy" / "selfhost" / "nginx.conf").read_text(encoding="utf-8")
    for service in ("postgres:", "redis:", "error_sink:", "api_a:", "api_b:", "frontend:", "nginx:"):
        assert service in compose
    assert compose.count("restart: unless-stopped") >= 7
    assert "condition: service_healthy" in compose
    assert "03_lock_down.sql" in compose
    assert "server api_a:8765;" in nginx
    assert "server api_b:8765;" in nginx
    assert "limit_req_zone" in nginx
    assert "limit_req_status 429" in nginx
    assert "location /app/" in nginx
    workflow = (ROOT / ".github" / "workflows" / "selfhost-ci.yml").read_text(encoding="utf-8")
    assert "selfhost_smoke.py" in workflow
    assert 'AUREON_LIVE_TRADING: "0"' in workflow
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "selfhost_up.py" in makefile
    assert "docker-compose.yml" in makefile
