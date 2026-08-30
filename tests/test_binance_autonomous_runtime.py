from __future__ import annotations

from typing import Any

import pytest

from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    TrustedCouncilEvidence,
)
from aureon.trading.binance_autonomous_runtime import (
    BINANCE_RECOVERY_ADAPTER_ID,
    BinanceAutonomousRuntime,
    bind_binance_autonomous_runtime,
)


class CouncilSupplier:
    supplier_id = "runtime-binance-council"

    def supply_council_evidence(
        self,
        request: CognitionGovernanceRequest,
    ) -> TrustedCouncilEvidence:
        raise AssertionError("construction_must_not_resolve_council")


class CrownSupplier:
    supplier_id = "runtime-binance-crown"

    def supply_crown_receipt(
        self,
        request: CognitionGovernanceRequest,
    ) -> dict[str, Any]:
        raise AssertionError("construction_must_not_resolve_crown")


class InertClient:
    dry_run = False
    use_testnet = False


def _bind(tmp_path):
    state_path = (
        tmp_path
        / "bounded_binance_roundtrip"
        / ("a" * 64 + ".json")
    )
    return bind_binance_autonomous_runtime(
        client=InertClient(),
        hnc_receipt_supplier=lambda: (_ for _ in ()).throw(
            AssertionError("construction_must_not_read_hnc")
        ),
        auris_receipt_supplier=lambda: (_ for _ in ()).throw(
            AssertionError("construction_must_not_read_auris")
        ),
        council_receipt_supplier=CouncilSupplier(),
        crown_receipt_supplier=CrownSupplier(),
        trusted_council_supplier_ids=frozenset({"runtime-binance-council"}),
        trusted_crown_supplier_ids=frozenset({"runtime-binance-crown"}),
        recovery_store_path=tmp_path / "binance-recovery.json",
        cycle_state_path=state_path,
        clock=lambda: 1_786_638_400.0,
    )


def test_binding_is_inert_and_wires_one_route(tmp_path):
    runtime = _bind(tmp_path)

    assert isinstance(runtime, BinanceAutonomousRuntime)
    assert runtime.route.client is runtime.client
    assert runtime.route.economic_boundary is runtime.boundary
    assert runtime.route.contingency_recovery is runtime.recovery
    assert runtime.recovery.adapter_id == BINANCE_RECOVERY_ADAPTER_ID
    assert not runtime.route.state_path.exists()
    assert not (tmp_path / "binance-recovery.json").exists()


def test_advance_delegates_once_without_looping(tmp_path, monkeypatch):
    runtime = _bind(tmp_path)
    calls: list[dict[str, Any]] = []

    def advance(**kwargs):
        calls.append(kwargs)
        return {"status": "pending", "economic_mutation": False}

    monkeypatch.setattr(runtime.route, "advance", advance)
    result = runtime.advance(
        authorization_receipt={"receipt": "owner"},
        confirmation_token="exact-token",
    )

    assert result == {"status": "pending", "economic_mutation": False}
    assert calls == [{
        "authorization_receipt": {"receipt": "owner"},
        "confirmation_token": "exact-token",
    }]


def test_read_only_preflight_delegates_without_mutation(tmp_path, monkeypatch):
    runtime = _bind(tmp_path)
    calls: list[dict[str, Any]] = []

    def preflight(**kwargs):
        calls.append(kwargs)
        return {"status": "no_action", "reason": "hnc_hold"}

    monkeypatch.setattr(runtime.route, "read_only_preflight", preflight)
    result = runtime.read_only_preflight(
        authorization_receipt={"receipt": "owner"},
        confirmation_token="exact-token",
        max_quote="10",
    )

    assert result == {"status": "no_action", "reason": "hnc_hold"}
    assert calls == [{
        "authorization_receipt": {"receipt": "owner"},
        "confirmation_token": "exact-token",
        "max_quote": "10",
    }]


@pytest.mark.parametrize(
    "relative_path",
    [
        "wrong-parent/" + "a" * 64 + ".json",
        "bounded_binance_roundtrip/not-a-digest.json",
        "bounded_binance_roundtrip/" + "A" * 64 + ".json",
    ],
)
def test_binding_rejects_nonprivate_cycle_paths(tmp_path, relative_path):
    with pytest.raises(ValueError, match="private_hashed_cycle_state_path_required"):
        bind_binance_autonomous_runtime(
            client=InertClient(),
            hnc_receipt_supplier=lambda: {},
            auris_receipt_supplier=lambda: {},
            council_receipt_supplier=CouncilSupplier(),
            crown_receipt_supplier=CrownSupplier(),
            trusted_council_supplier_ids=frozenset({"runtime-binance-council"}),
            trusted_crown_supplier_ids=frozenset({"runtime-binance-crown"}),
            recovery_store_path=tmp_path / "recovery.json",
            cycle_state_path=tmp_path / relative_path,
        )
