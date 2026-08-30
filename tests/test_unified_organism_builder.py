"""Hermetic proof for Aureon's complete process-owned composition join."""

from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

import pytest

import aureon.core.unified_organism_builder as builder_module
from aureon.core.organism_composition import (
    REQUIRED_SUBSYSTEMS,
    get_canonical_organism_composition,
    reset_canonical_organism_composition_for_tests,
)
from aureon.core.unified_organism_builder import build_canonical_cloud_organism
from aureon.governance.economic_mutation_readiness import (
    build_economic_mutation_readiness_receipt,
)
from aureon.queen.queen_mind import (
    get_canonical_queen_mind,
    reset_canonical_queen_mind_for_tests,
)
from aureon.swarm.auris_node_receipts import issue_auris_node_receipt
from aureon.swarm.druidic_council import ACTIVE_THRESHOLD, REQUIRED_SEATS
from tests.test_live_workforce_calibration import (
    NOW,
    _canonical,
    _successful_calibration,
)
from tests.test_unified_exchange_unity_composition import _capability


class _Workforce:
    calls = 0

    def process_id_for_role(self, role: str) -> str:
        return f"agent_company_role_cycle:{role}"

    def decide(self, **_kwargs):
        self.calls += 1
        raise AssertionError("composition_must_not_call_cloud_brain")


class _Conscience:
    calls = 0

    def ask_why(self, _action, context=None):
        self.calls += 1
        return SimpleNamespace(
            verdict=SimpleNamespace(name="APPROVED"),
            message=f"approved:{bool(context)}",
        )


def _brain_report():
    return {
        "ready": True,
        "status": "brain_fabric_ready",
        "canonical_role_count": 41,
        "agent_brain_count": 41,
        "process_brain_count": 41,
        "brain_passport_count": 82,
        "hnc_routed_brain_count": 82,
        "distinct_hnc_routing_receipt_count": 82,
        "all_brains_hnc_routed": True,
        "truth_gate_enforced": True,
        "provider_mode": "ollama_cloud_primary",
        "decision_authority": "aureon_internal",
        "codex_role": "senior_review_and_veto_only",
        "codex_implementation_allowed": False,
        "tools_enabled": False,
        "action_eligible": False,
        "economic_eligible": False,
    }


def _economic_receipt(*, blockers: int = 0):
    counts = {
        "economic-boundary-last-mile": 1,
        "live-capable-unguarded-blocker": blockers,
    }
    count = sum(counts.values())
    census = {
        "schema": "aureon.economic-mutation-census.v1",
        "source_files_scanned": 1,
        "detected_count": count,
        "classified_count": count,
        "counts_by_classification": counts,
        "counts_by_provider": {"multi-provider": count},
        "inventory_aligned": True,
        "certified_no_bypass": blockers == 0,
        "blocker_count": blockers,
        "unallowlisted": [],
        "stale_allowlist_entries": [],
        "parse_errors": [],
        "findings": [
            {"fingerprint": f"econop:{index}"} for index in range(count)
        ],
    }
    return build_economic_mutation_readiness_receipt(
        census,
        allowlist_sha256="f" * 64,
        now=NOW,
    )


@pytest.fixture(autouse=True)
def _reset_root():
    reset_canonical_organism_composition_for_tests()
    reset_canonical_queen_mind_for_tests()
    yield
    reset_canonical_queen_mind_for_tests()
    reset_canonical_organism_composition_for_tests()


def _complete_operation(tmp_path):
    calibration, final_pair = _successful_calibration((0.81, 0.90, 0.85))
    nodes = [
        issue_auris_node_receipt(
            seat=seat,
            resolver=calibration.node_resolver,
            now=NOW,
        )
        for seat in REQUIRED_SEATS
    ]
    driver_count = sum(float(node["gamma"]) >= ACTIVE_THRESHOLD for node in nodes)
    payload = {
        "schema": "aureon.live-druidic-calibration-operation.v1",
        "status": "complete",
        "reason": None,
        "provider_mode": "ollama_cloud_primary",
        "calibration_receipt": calibration.report,
        "auris_nodes": nodes,
        "node_driver_count": driver_count,
        "action_eligible": False,
        "economic_mutation": False,
        "exchange_call_count": 0,
        "order_call_count": 0,
    }
    path = tmp_path / "druidic_live_calibration_latest.json"
    path.write_text(_canonical(payload), encoding="utf-8")
    return path, final_pair


def test_builder_joins_full_organism_without_model_or_exchange_call(
    monkeypatch,
    tmp_path,
):
    calibration_path, pair = _complete_operation(tmp_path)
    workforce = _Workforce()
    conscience = _Conscience()
    client_calls = []
    monkeypatch.setattr(
        builder_module,
        "provision_agent_company_brain_fabric",
        lambda *_args, **_kwargs: workforce,
    )
    monkeypatch.setattr(
        builder_module,
        "company_brain_fabric_report",
        lambda _workforce: _brain_report(),
    )

    composition, bound_workforce, exchange = build_canonical_cloud_organism(
        brain_resolver=object(),
        thought_path=object(),
        conscience=conscience,
        capabilities=(_capability(),),
        present_subsystems={
            name: f"canonical role for {name}" for name in REQUIRED_SUBSYSTEMS
        },
        economic_readiness_receipt=_economic_receipt(),
        calibration_path=calibration_path,
        pair_loader=lambda: pair,
        client_factory=lambda **kwargs: client_calls.append(kwargs)
        or {"kind": "canonical-unified-exchange"},
        max_age_s=30.0,
        clock=lambda: NOW,
        civil_date_provider=lambda: date(2026, 8, 13),
    )

    assert bound_workforce is workforce
    assert exchange.client == {"kind": "canonical-unified-exchange"}
    assert len(client_calls) == 1
    assert workforce.calls == conscience.calls == 0
    assert composition.status()["status"] == "ready"
    assert composition.status()["economic_mutation"] is False
    assert composition.governance.council_receipt_supplier is (
        exchange.council_receipt_supplier
    )
    assert composition.governance.crown_receipt_supplier is (
        exchange.crown_receipt_supplier
    )
    assert get_canonical_organism_composition() is composition
    assert get_canonical_queen_mind() is not None
    assert get_canonical_queen_mind().status()["status"] == "ready"


def test_builder_holds_before_brain_provision_when_calibration_is_not_complete(
    monkeypatch,
    tmp_path,
):
    calibration_path = tmp_path / "druidic_live_calibration_latest.json"
    calibration_path.write_text(
        json.dumps({"schema": "wrong", "status": "complete"}),
        encoding="utf-8",
    )
    provision_calls = [0]
    monkeypatch.setattr(
        builder_module,
        "provision_agent_company_brain_fabric",
        lambda *_args, **_kwargs: provision_calls.__setitem__(
            0, provision_calls[0] + 1
        ),
    )

    with pytest.raises(
        ValueError,
        match="valid_fresh_complete_druidic_calibration_required",
    ):
        build_canonical_cloud_organism(
            brain_resolver=object(),
            thought_path=object(),
            conscience=_Conscience(),
            capabilities=(_capability(),),
            present_subsystems={
                name: f"canonical role for {name}" for name in REQUIRED_SUBSYSTEMS
            },
            economic_readiness_receipt=_economic_receipt(),
            calibration_path=calibration_path,
            pair_loader=lambda: (_successful_calibration()[1]),
            client_factory=lambda **_kwargs: object(),
            clock=lambda: NOW,
        )

    assert provision_calls == [0]
    assert get_canonical_organism_composition() is None


def test_builder_holds_before_brain_or_provider_when_census_has_blockers(
    monkeypatch,
    tmp_path,
):
    calibration_path, pair = _complete_operation(tmp_path)
    provision_calls = [0]
    client_calls = [0]
    monkeypatch.setattr(
        builder_module,
        "provision_agent_company_brain_fabric",
        lambda *_args, **_kwargs: provision_calls.__setitem__(
            0, provision_calls[0] + 1
        ),
    )

    with pytest.raises(
        ValueError,
        match="zero_aligned_economic_mutation_blockers_required",
    ):
        build_canonical_cloud_organism(
            brain_resolver=object(),
            thought_path=object(),
            conscience=_Conscience(),
            capabilities=(_capability(),),
            present_subsystems={
                name: f"canonical role for {name}" for name in REQUIRED_SUBSYSTEMS
            },
            economic_readiness_receipt=_economic_receipt(blockers=1_445),
            calibration_path=calibration_path,
            pair_loader=lambda: pair,
            client_factory=lambda **_kwargs: client_calls.__setitem__(
                0, client_calls[0] + 1
            ),
            max_age_s=30.0,
            clock=lambda: NOW,
        )

    assert provision_calls == [0]
    assert client_calls == [0]
    assert get_canonical_organism_composition() is None
