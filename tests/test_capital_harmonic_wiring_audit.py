from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader


def test_harmonic_wiring_audit_has_required_sections():
    trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
    audit = CapitalCFDTrader._build_harmonic_wiring_audit(trader)
    assert isinstance(audit, dict)
    assert "checks" in audit
    names = {item.get("name") for item in audit["checks"]}
    assert "harmonic_fusion" in names
    assert "probability_validation_report" in names
    assert audit.get("total", 0) >= len(names)
    # Import checks prove the CODE wiring and must always pass. File checks
    # probe live runtime state (state/*.json written by the running daemons) —
    # on a cold checkout they are honestly "missing", and the audit is REQUIRED
    # to report that rather than call the instance fully wired.
    import_checks = [c for c in audit["checks"] if c.get("kind") == "import"]
    file_checks = [c for c in audit["checks"] if c.get("kind") == "file"]
    assert import_checks and all(c.get("ok") for c in import_checks)
    runtime_state_present = all(c.get("ok") for c in file_checks)
    assert audit.get("passed") == len(import_checks) + sum(1 for c in file_checks if c.get("ok"))
    assert audit.get("ok") is runtime_state_present
