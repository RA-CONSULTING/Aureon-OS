from aureon.autonomous import (
    aureon_capability_growth_loop,
    aureon_organism_runtime_observer,
    aureon_repo_self_repair,
    aureon_self_enhancement_lifecycle,
    aureon_system_readiness_audit,
    hnc_saas_security_architect,
    mind_wiring_audit,
)
from aureon.operator.connections_api import _real_data_policy_summary


def test_audit_environments_default_to_no_simulation():
    env_maps = [
        aureon_system_readiness_audit.SAFE_AUDIT_ENV,
        aureon_organism_runtime_observer.SAFE_OBSERVER_ENV,
        mind_wiring_audit.AUDIT_ENV_FLAGS,
        hnc_saas_security_architect.SAFE_ENV,
        aureon_capability_growth_loop.SAFE_ENV,
        aureon_repo_self_repair.SAFE_ENV,
        aureon_self_enhancement_lifecycle.SAFE_ENV,
    ]

    assert all(env["AUREON_ALLOW_SIM_FALLBACK"] == "0" for env in env_maps)


def test_connections_readiness_exposes_real_data_policy(monkeypatch):
    monkeypatch.setenv("AUREON_ALLOW_SIM_FALLBACK", "0")

    summary = _real_data_policy_summary()

    assert summary["simulation_fallback_allowed"] is False
    assert "live" in summary["truth_statuses"]
    assert summary["source_registry_count"] >= 1
    assert set(summary["probe_summary"]).issuperset({"live", "real_derived", "cached_real", "no_data"})
