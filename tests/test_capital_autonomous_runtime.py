from __future__ import annotations

from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    TrustedCouncilEvidence,
)
from aureon.trading.capital_autonomous_runtime import bind_capital_autonomous_runtime


class _Council:
    supplier_id = "trusted-capital-council"

    def supply_council_evidence(
        self,
        request: CognitionGovernanceRequest,
    ) -> TrustedCouncilEvidence:
        raise AssertionError("composition must not call voices")


class _Crown:
    supplier_id = "trusted-capital-crown"

    def supply_crown_receipt(self, request: CognitionGovernanceRequest):
        raise AssertionError("composition must not call voices")


class _Client:
    enabled = True
    dry_run = False
    demo_mode = False


def test_composition_binds_one_client_and_independent_allowlisted_voices(tmp_path) -> None:
    client = _Client()

    runtime = bind_capital_autonomous_runtime(
        client=client,
        council_receipt_supplier=_Council(),
        crown_receipt_supplier=_Crown(),
        trusted_council_supplier_ids=frozenset({"trusted-capital-council"}),
        trusted_crown_supplier_ids=frozenset({"trusted-capital-crown"}),
        recovery_store_path=tmp_path / "capital-recovery.json",
        cycle_state_path=tmp_path / "capital-cycle.json",
        clock=lambda: 1_786_632_900.0,
        sleeper=lambda _: None,
    )

    assert runtime.client is client
    assert runtime.route.client is client
    assert runtime.cycle.client is client
    assert runtime.cycle.route is runtime.route
    assert not (tmp_path / "capital-recovery.json").exists()
    assert not (tmp_path / "capital-cycle.json").exists()
