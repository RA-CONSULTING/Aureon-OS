from __future__ import annotations

from pathlib import Path

from aureon.autonomous.aureon_murge_runtime_activation_stress_audit import (
    build_runtime_activation_stress_audit,
    publish_activation_events,
)


def test_murge_runtime_activation_audit_reports_guards_and_launcher() -> None:
    report = build_runtime_activation_stress_audit(probe_services=False, env={})

    assert report["schema_version"] == "aureon-murge-runtime-activation-stress-v1"
    assert report["summary"]["service_count"] == 3
    assert report["summary"]["service_present_count"] == 3
    assert report["summary"]["windows_launcher_present"] is True
    assert report["summary"]["host_bash_assumption_removed"] is True
    assert report["summary"]["dependency_check_count"] == 3
    assert report["dependency_readiness_rows"]
    assert all("install_command" in row for row in report["dependency_readiness_rows"])
    assert len(report["npm_audit_rows"]) == 3
    assert report["summary"]["terminal_guard_passing_count"] == report["summary"]["terminal_guard_count"]
    assert report["summary"]["no_trading_gate_bypass"] is True
    assert "collision_review_required" in report["blockers"]


def test_murge_runtime_activation_audit_blocks_remote_and_cloud_env() -> None:
    report = build_runtime_activation_stress_audit(
        probe_services=False,
        env={
            "HOST": "0.0.0.0",
            "FLAMEBORN_RUNTIME_HOST": "0.0.0.0",
            "MURGE_CLOUDFLARE_ENABLED": "1",
        },
    )

    assert "web_host_not_localhost" in report["blockers"]
    assert "runtime_host_not_localhost" in report["blockers"]
    assert "cloudflare_activation_out_of_scope" in report["blockers"]
    assert report["status"] == "murge_runtime_activation_attention"


def test_murge_runtime_activation_health_probe_can_certify_local_services() -> None:
    def probe(url: str) -> dict:
        return {"url": url, "ok": True, "status_code": 200, "round_trip_ms": 1.0}

    report = build_runtime_activation_stress_audit(
        probe_services=True,
        http_probe=probe,
        port_probe=lambda host, port: host == "127.0.0.1" and port > 0,
        env={},
    )

    assert report["summary"]["web_health_passed"] is True
    assert report["summary"]["runtime_health_passed"] is True
    assert "local_service_health_pending" not in report["blockers"]


def test_murge_activation_events_publish_to_fabric_artifacts(tmp_path: Path) -> None:
    report = build_runtime_activation_stress_audit(probe_services=False, env={})

    events = publish_activation_events(report, root=tmp_path, emit_external=False)

    assert events
    assert any(event["phase"] == "murge_activation_preflight" for event in events)
    assert all(event["route_key"] == "murge/local/full-launch" for event in events)
    assert (tmp_path / "frontend" / "public" / "aureon_live_trade_signal_fabric.json").exists()
