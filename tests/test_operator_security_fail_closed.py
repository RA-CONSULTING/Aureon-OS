"""Offline acceptance tests for the operator auth and rate-limit boundary."""

from __future__ import annotations

import ipaddress
from pathlib import Path

import pytest

pytest.importorskip("flask", reason="operator security tests require Flask")

from aureon.operator.security import SecurityConfig, TokenBucket, resolve_client_ip

ROOT = Path(__file__).resolve().parents[1]
SECURITY_ENV = (
    "AUREON_OPERATOR_ENV",
    "AUREON_OPERATOR_API_KEY",
    "AUREON_OPERATOR_RATE_RPS",
    "AUREON_OPERATOR_RATE_BURST",
    "AUREON_OPERATOR_MAX_BODY",
    "AUREON_OPERATOR_TRUSTED_PROXY_CIDRS",
    "AUREON_OPERATOR_HTTP_PROCESSES",
    "AUREON_OPERATOR_REPLICAS",
)


def _clear_security_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SECURITY_ENV:
        monkeypatch.delenv(name, raising=False)


def test_production_refuses_an_empty_secret_and_disabled_or_split_limiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("AUREON_OPERATOR_ENV", "production")

    with pytest.raises(ValueError, match="AUREON_OPERATOR_API_KEY"):
        SecurityConfig.from_env()

    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "   ")
    with pytest.raises(ValueError, match="AUREON_OPERATOR_API_KEY"):
        SecurityConfig.from_env()

    monkeypatch.setenv("AUREON_OPERATOR_API_KEY", "offline-test-secret")
    config = SecurityConfig.from_env()
    assert config.production is True
    assert config.auth_enabled is True
    assert config.rate_rps == 10.0
    assert config.rate_enabled is True

    monkeypatch.setenv("AUREON_OPERATOR_RATE_RPS", "0")
    with pytest.raises(ValueError, match="AUREON_OPERATOR_RATE_RPS"):
        SecurityConfig.from_env()
    monkeypatch.setenv("AUREON_OPERATOR_RATE_RPS", "10")

    monkeypatch.setenv("AUREON_OPERATOR_HTTP_PROCESSES", "2")
    with pytest.raises(ValueError, match="AUREON_OPERATOR_HTTP_PROCESSES"):
        SecurityConfig.from_env()
    monkeypatch.setenv("AUREON_OPERATOR_HTTP_PROCESSES", "1")

    monkeypatch.setenv("AUREON_OPERATOR_REPLICAS", "2")
    with pytest.raises(ValueError, match="AUREON_OPERATOR_REPLICAS"):
        SecurityConfig.from_env()


def test_explicit_development_mode_preserves_offline_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("AUREON_OPERATOR_ENV", "development")
    config = SecurityConfig.from_env()
    assert config.production is False
    assert config.auth_enabled is False
    assert config.rate_enabled is False


def test_forwarded_ip_requires_a_matching_trusted_direct_proxy() -> None:
    trusted = (ipaddress.ip_network("10.20.0.0/24"),)

    assert resolve_client_ip("203.0.113.9", "198.51.100.7", trusted) == "203.0.113.9"
    assert resolve_client_ip("10.20.0.5", "198.51.100.7, 10.20.0.4", trusted) == "198.51.100.7"
    assert resolve_client_ip("10.20.0.5", "not-an-ip", trusted) == "10.20.0.5"
    assert resolve_client_ip("10.20.0.5", "198.51.100.7") == "10.20.0.5"


def test_token_bucket_isolated_clients_exhaust_and_refill() -> None:
    now = [100.0]
    bucket = TokenBucket(rate_rps=2.0, burst=2, clock=lambda: now[0])

    assert bucket.check("client-a") == (True, 0.0)
    assert bucket.check("client-a") == (True, 0.0)
    allowed, retry = bucket.check("client-a")
    assert allowed is False
    assert retry == 0.5
    assert bucket.check("client-b") == (True, 0.0)

    now[0] += 0.5
    assert bucket.check("client-a") == (True, 0.0)


def test_open_operator_plane_is_restricted_to_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_security_env(monkeypatch)
    monkeypatch.setenv("AUREON_OPERATOR_ENV", "development")
    monkeypatch.delenv("AUREON_SUPABASE_JWT_SECRET", raising=False)

    from aureon.operator.operator_server import _is_loopback_host, create_app

    assert _is_loopback_host("127.0.0.1") is True
    assert _is_loopback_host("::1") is True
    assert _is_loopback_host("0.0.0.0") is False
    assert _is_loopback_host("203.0.113.9") is False

    app = create_app(operator=object())
    app.testing = True
    client = app.test_client()
    remote = client.get("/api/not-a-real-route", environ_base={"REMOTE_ADDR": "203.0.113.9"})
    local = client.get("/api/not-a-real-route", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert remote.status_code == 401
    assert remote.get_json() == {
        "error": {"code": 401, "message": "authenticated loopback operator required"}
    }
    assert local.status_code == 404


def test_operator_main_defaults_to_loopback() -> None:
    source = (ROOT / "aureon" / "operator" / "operator_server.py").read_text(encoding="utf-8")
    main_source = source[source.index("def main() -> None:") :]
    assert 'AUREON_OPERATOR_HOST", "127.0.0.1"' in main_source
    assert "non_loopback_operator_requires_AUREON_OPERATOR_API_KEY" in main_source


def test_compose_and_docs_use_the_exact_operator_environment_contract() -> None:
    compose_paths = (
        ROOT / "deploy" / "docker-compose.operator.yml",
        ROOT / "deploy" / "docker-compose.saas.yml",
    )
    required = (
        "AUREON_OPERATOR_ENV",
        "AUREON_OPERATOR_API_KEY",
        "AUREON_OPERATOR_RATE_RPS",
        "AUREON_OPERATOR_RATE_BURST",
        "AUREON_OPERATOR_MAX_BODY",
        "AUREON_OPERATOR_TRUSTED_PROXY_CIDRS",
        "AUREON_OPERATOR_HTTP_PROCESSES",
        "AUREON_OPERATOR_REPLICAS",
    )
    for path in compose_paths:
        text = path.read_text(encoding="utf-8")
        assert all(name in text for name in required)
        assert "AUREON_OPERATOR_API_KEY: \"${AUREON_OPERATOR_API_KEY:?" in text
        assert "replicas: 1" in text

    docs = (
        ROOT / "docs" / "deployment" / "OPERATOR_DEPLOY.md",
        ROOT / "docs" / "runbooks" / "PRODUCTION_GRADE.md",
        ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in docs)
    assert all(name in combined for name in required)
    assert "AUREON_RATE_ENABLED" not in combined
    assert "AUREON_MAX_BODY_BYTES" not in combined


def test_preexisting_tenant_conscience_tail_is_preserved() -> None:
    raw = (ROOT / "aureon" / "operator" / "operator_server.py").read_bytes()
    marker = b"    _tenant_conscience:"
    tail_bytes = raw[raw.index(marker) :]
    tail = tail_bytes.decode("utf-8")

    assert tail.startswith("    _tenant_conscience: Dict[str, Any] = {}")
    assert "class _UnavailableTenantConscience:" in tail
    assert 'return _UnavailableTenantConscience()' in tail
    assert "allow_repo_grounding=False" in tail
    assert "allow_organism_context=False" in tail
