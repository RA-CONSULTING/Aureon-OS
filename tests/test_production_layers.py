"""Local proofs for the production layers that can be shown without a paid host."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aureon_fusion import http_service

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "PRODUCTION_READINESS.md"
MIGRATIONS = ROOT / "supabase" / "migrations"
FUSION_CI = ROOT / ".github" / "workflows" / "fusion-ci.yml"
WINDOWS_CI = ROOT / ".github" / "workflows" / "windows-contract.yml"
FRONTEND_CI = ROOT / ".github" / "workflows" / "frontend-ci.yml"


def test_readiness_marks_every_layer_without_claiming_ci() -> None:
    text = READINESS.read_text(encoding="utf-8")
    for layer in (
        "Frontend",
        "APIs",
        "DB/storage",
        "Auth",
        "Hosting/deploy",
        "Cloud",
        "CI/CD",
        "Security/RLS",
        "Rate limiting",
        "Caching/CDN",
        "Load balancing/scaling",
        "Error tracking/logs",
    ):
        assert f"| {layer} |" in text
    assert "| PROVEN |" not in text
    assert "aureon-os-upstream/" not in text
    assert "supabase/migrations/20260811210525_lock_down_legacy_public_tables.sql" in text


def test_rate_limit_and_cache_are_local_and_disarmed(monkeypatch: pytest.MonkeyPatch) -> None:
    http_service.reset_limits()
    monkeypatch.setenv("AUREON_FUSION_RATE_LIMIT", "2")
    monkeypatch.setenv("AUREON_FUSION_RATE_WINDOW_S", "60")
    assert http_service.allow("client-a", now=1.0) is True
    assert http_service.allow("client-a", now=1.0) is True
    assert http_service.allow("client-a", now=1.0) is False
    assert http_service.live_trading_armed() is False

    monkeypatch.setattr(http_service, "status_report", lambda: {"may_act": False, "live_trading": False})
    monkeypatch.setenv("AUREON_FUSION_CACHE_TTL_S", "30")
    http_service.reset_limits()
    first = http_service.cached_status()
    second = http_service.cached_status()
    assert first["cache"] == "miss"
    assert second["cache"] == "hit"
    assert second["may_act"] is False


def test_rls_is_enabled_in_the_migrations() -> None:
    sql = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in MIGRATIONS.glob("*.sql"))
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY" in sql


def test_ci_keeps_live_trading_off_and_has_a_windows_job() -> None:
    fusion = FUSION_CI.read_text(encoding="utf-8")
    windows = WINDOWS_CI.read_text(encoding="utf-8")
    assert 'AUREON_LIVE_TRADING: "0"' in fusion
    assert "windows-latest" in windows
    assert "test_voice_runner_paths.py" in windows
    assert "test_release_update.py" in windows
    assert FRONTEND_CI.is_file()


def test_hosted_layers_are_not_proven_until_ci_is_green() -> None:
    text = READINESS.read_text(encoding="utf-8")
    assert "end user's choice" in text
    assert "nothing is PROVEN" in text or "Nothing is PROVEN" in text
    expected = {
        "Frontend": "local-only",
        "APIs": "local-only",
        "DB/storage": "local-only",
        "Auth": "local-only",
        "Hosting/deploy": "local-only",
        "Cloud": "local-only",
        "CI/CD": "missing",
        "Security/RLS": "policy text only",
        "Rate limiting": "local-only",
        "Caching/CDN": "local-only",
        "Load balancing/scaling": "local-only",
        "Error tracking/logs": "local-only",
    }
    for layer, status in expected.items():
        row = next(line for line in text.splitlines() if line.startswith(f"| {layer} |"))
        assert f"| {status} |" in row
