"""Focused contracts for Aureon's canonical process composition root."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from aureon.core.organism_composition import (
    REQUIRED_SUBSYSTEMS,
    CallableGovernanceAcquisitionSupplier,
    GovernanceBindings,
    bind_canonical_organism_composition,
    configure_canonical_organism_composition,
    reset_canonical_organism_composition_for_tests,
)
from aureon.core.soul import SoulDeliberation
from aureon.governance.celtic_voice_bank import read_canonical_celtic_voice_bank
from aureon.governance.economic_mutation_readiness import (
    build_economic_mutation_readiness_receipt,
)
from aureon.inhouse_ai.tool_registry import ToolRegistry


class _CouncilSupplier:
    supplier_id = "test:council-supplier"

    def supply_council_evidence(self, request):  # pragma: no cover - shape only
        raise AssertionError("composition status must not invoke Council")


class _CrownSupplier:
    supplier_id = "test:crown-supplier"

    def supply_crown_receipt(self, request):  # pragma: no cover - shape only
        raise AssertionError("composition status must not invoke Crown")


class _Adapter:
    """Constructor-only adapter; focused tests do not invoke a model."""


@pytest.fixture(autouse=True)
def _reset_composition():
    reset_canonical_organism_composition_for_tests()
    yield
    reset_canonical_organism_composition_for_tests()


def _acquisition_payload(timestamp: str = "1.25") -> dict[str, Any]:
    return {
        "provider_receipt_ids": ["provider:test:one", "provider:test:two"],
        "provider_moment_digest": "a" * 64,
        "provider_source_timestamp": timestamp,
    }


def _governance(loader) -> GovernanceBindings:
    return GovernanceBindings(
        council_receipt_supplier=_CouncilSupplier(),
        crown_receipt_supplier=_CrownSupplier(),
        acquisition_supplier=CallableGovernanceAcquisitionSupplier(
            supplier_id="test:acquisition-supplier",
            loader=loader,
        ),
        voice_bank_receipt=read_canonical_celtic_voice_bank(),
    )


def _ready_economic_receipt() -> dict[str, Any]:
    census = {
        "schema": "aureon.economic-mutation-census.v1",
        "source_files_scanned": 1,
        "detected_count": 1,
        "classified_count": 1,
        "counts_by_classification": {"economic-boundary-last-mile": 1},
        "counts_by_provider": {"multi-provider": 1},
        "inventory_aligned": True,
        "certified_no_bypass": True,
        "blocker_count": 0,
        "unallowlisted": [],
        "stale_allowlist_entries": [],
        "parse_errors": [],
        "findings": [{"fingerprint": "econop:test"}],
    }
    return build_economic_mutation_readiness_receipt(
        census,
        allowlist_sha256="e" * 64,
        now=1.0,
    )


def _seated_queen_mind_report() -> dict[str, Any]:
    roles = {"knowledge": 1, "metacognition": 1, "miner": 1, "quantum": 1}
    return {
        "schema": "aureon.queen-mind.v1",
        "status": "seated",
        "manifest_id": "queen-faculty-manifest:" + ("f" * 64),
        "faculty_count": len(roles),
        "roles": roles,
        "effects": {"advisory": len(roles)},
        "required_roles": sorted(roles),
        "action_eligible": False,
        "economic_mutation": False,
    }


def _no_data_voice(name: str, voices: dict[str, dict[str, Any]]):
    voices[name] = {"stance": "wait", "truth_status": "no_data"}
    return "wait", 0.3, 0.3


def test_soul_seats_hash_bound_celtic_context_without_authority():
    voices: dict[str, dict[str, Any]] = {}

    SoulDeliberation()._voice_celtic_wisdom(voices)

    context = voices["celtic_wisdom"]
    assert context["truth_status"] == "source_bound_context"
    assert context["stance"] == "context"
    assert context["triad_required_confirming_voices"] == 3
    assert tuple(context["seat_context_digests"]) == (
        "seer",
        "sentinel",
        "weaver",
        "keeper",
    )
    assert all(len(value) == 64 for value in context["seat_context_digests"].values())
    assert context["generated_values"] is False
    assert context["action_eligible"] is False
    assert context["economic_mutation"] is False


def test_source_bound_celtic_context_does_not_make_blind_soul_live(monkeypatch):
    soul = SoulDeliberation()
    monkeypatch.setattr(
        soul,
        "_voice_feeling",
        lambda voices: _no_data_voice("feeling", voices),
    )
    monkeypatch.setattr(
        soul,
        "_voice_thought",
        lambda voices: _no_data_voice("thought", voices),
    )
    monkeypatch.setattr(
        soul,
        "_voice_elders",
        lambda voices: _no_data_voice("elders", voices),
    )
    monkeypatch.setattr(
        soul,
        "_voice_goals",
        lambda intent, voices: _no_data_voice("goals", voices),
    )
    monkeypatch.setattr(
        soul,
        "_voice_inner",
        lambda voices: _no_data_voice("inner", voices),
    )

    def no_conscience(intent, context, voices):
        lean, weight, intensity = _no_data_voice("conscience", voices)
        return lean, weight, intensity, None

    monkeypatch.setattr(soul, "_voice_conscience", no_conscience)

    determination, voices = soul._gather_and_determine("observe", {})

    assert voices["celtic_wisdom"]["truth_status"] == "source_bound_context"
    assert determination.available is False
    assert determination.resolved is False
    assert determination.truth_status == "no_data"


def test_incomplete_composition_reports_exact_hold_without_invoking_suppliers():
    composition = bind_canonical_organism_composition(
        present_subsystems={
            "thought_bus": "nervous system",
            "soul": "deliberation",
        },
        calibration_status={
            "status": "hold",
            "reason": "negative_measured_coherence_cannot_drive_council",
        },
    )

    status = composition.status()

    assert status["status"] == "hold"
    assert status["calibration_reason"] == (
        "negative_measured_coherence_cannot_drive_council"
    )
    assert "council" in status["missing_subsystem_ids"]
    assert status["governance_ready"] is False
    assert status["action_eligible"] is False
    assert status["economic_mutation"] is False


def test_complete_composition_reports_ready_but_remains_evidence_only():
    composition = bind_canonical_organism_composition(
        present_subsystems={name: f"test role for {name}" for name in REQUIRED_SUBSYSTEMS},
        governance=_governance(_acquisition_payload),
        brain_fabric_report={
            "ready": True,
            "status": "brain_fabric_ready",
            "truth_gate_enforced": True,
            "provider_mode": "ollama_cloud_primary",
        },
        calibration_status={"status": "complete", "receipt_id": "calibration:test"},
        economic_readiness=_ready_economic_receipt(),
        queen_mind_report=_seated_queen_mind_report(),
    )

    status = composition.status()

    assert status["status"] == "ready"
    assert status["missing_subsystem_ids"] == []
    assert status["brain_fabric_ready"] is True
    assert status["governance_ready"] is True
    assert status["queen_mind_ready"] is True
    assert status["action_eligible"] is False
    assert status["economic_mutation"] is False


def test_daemon_boot_publishes_honest_composition_hold_without_cold_mesh(
    monkeypatch,
    tmp_path,
):
    import aureon.core.aureon_connectome as connectome_module
    import aureon.core.aureon_consciousness_module as consciousness_module
    import aureon.core.aureon_thought_bus as thought_bus_module
    from aureon.core import organism_daemon
    from aureon.core.aureon_thought_bus import ThoughtBus

    monkeypatch.setenv("AUREON_CONNECTOME_SWEEP", "0")
    monkeypatch.setenv("AUREON_AURIS_AUTOSTART", "0")
    monkeypatch.setenv("AUREON_THOUGHT_BUS_PATH", str(tmp_path / "thoughts.jsonl"))
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "traces"))
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    connectome = object()
    monkeypatch.setattr(thought_bus_module, "get_thought_bus", lambda: bus)
    monkeypatch.setattr(connectome_module, "get_connectome", lambda: connectome)
    monkeypatch.setattr(
        consciousness_module,
        "ConsciousnessModule",
        lambda bus: SimpleNamespace(bus=bus),
    )
    mycelium_module = sys.modules.get("aureon.core.aureon_mycelium")
    if mycelium_module is not None:
        monkeypatch.setattr(mycelium_module, "_mycelium_instance", None)

    organs = organism_daemon.boot()
    status = organs["organism_composition_status"]

    assert organs["bus"] is bus
    assert organs["connectome"] is connectome
    assert "mycelium" not in organs
    assert status["status"] == "hold"
    assert status["governance_ready"] is False
    assert status["economic_mutation"] is False
    assert {"council", "crown", "brain_switchboard", "mycelium"} <= set(
        status["missing_subsystem_ids"]
    )


def test_daemon_boot_preserves_process_owned_canonical_composition(
    monkeypatch,
    tmp_path,
):
    import aureon.core.aureon_connectome as connectome_module
    import aureon.core.aureon_consciousness_module as consciousness_module
    import aureon.core.aureon_thought_bus as thought_bus_module
    from aureon.core import organism_daemon
    from aureon.core.aureon_thought_bus import ThoughtBus

    configured = configure_canonical_organism_composition(
        bind_canonical_organism_composition(
            present_subsystems={
                name: f"process-owned role for {name}" for name in REQUIRED_SUBSYSTEMS
            },
            governance=_governance(_acquisition_payload),
            brain_fabric_report={
                "ready": True,
                "status": "brain_fabric_ready",
                "truth_gate_enforced": True,
                "provider_mode": "ollama_cloud_primary",
            },
            calibration_status={"status": "complete"},
            economic_readiness=_ready_economic_receipt(),
            queen_mind_report=_seated_queen_mind_report(),
        )
    )
    monkeypatch.setenv("AUREON_CONNECTOME_SWEEP", "0")
    monkeypatch.setenv("AUREON_AURIS_AUTOSTART", "0")
    monkeypatch.setenv("AUREON_THOUGHT_BUS_PATH", str(tmp_path / "thoughts.jsonl"))
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "traces"))
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    monkeypatch.setattr(thought_bus_module, "get_thought_bus", lambda: bus)
    monkeypatch.setattr(connectome_module, "get_connectome", object)
    monkeypatch.setattr(
        consciousness_module,
        "ConsciousnessModule",
        lambda bus: SimpleNamespace(bus=bus),
    )

    organs = organism_daemon.boot()

    assert organs["organism_composition"] is configured
    assert organs["organism_composition_status"]["status"] == "ready"
    assert organs["organism_composition_status"]["governance_ready"] is True


def test_cognition_adopts_global_composition_and_loads_each_provider_moment(monkeypatch):
    import aureon.operator.cognition as cognition_module

    calls = 0

    def load():
        nonlocal calls
        calls += 1
        return _acquisition_payload(str(calls))

    composition = bind_canonical_organism_composition(
        present_subsystems={name: f"test role for {name}" for name in REQUIRED_SUBSYSTEMS},
        governance=_governance(load),
        brain_fabric_report={
            "ready": True,
            "status": "brain_fabric_ready",
            "truth_gate_enforced": True,
            "provider_mode": "ollama_cloud_primary",
        },
        calibration_status={"status": "complete"},
    )
    configure_canonical_organism_composition(composition)
    monkeypatch.setattr(cognition_module, "_HAS_BUS", False)
    cognition = cognition_module.AureonCognition(
        adapter=_Adapter(),
        tools=ToolRegistry(include_builtins=False),
        join_mesh=False,
    )
    result = SimpleNamespace(acquisition={"status": "not_needed"})

    first = cognition._governance_acquisition_for(result)
    second = cognition._governance_acquisition_for(result)

    assert calls == 2
    assert first["provider_source_timestamp"] == "1"
    assert second["provider_source_timestamp"] == "2"
    assert first["knowledge_acquisition"] == {"status": "not_needed"}
    assert cognition._council_receipt_supplier is composition.governance.council_receipt_supplier
    assert cognition._crown_receipt_supplier is composition.governance.crown_receipt_supplier


def test_explicit_cognition_inputs_are_not_completed_from_global_root(monkeypatch):
    import aureon.operator.cognition as cognition_module

    composition = bind_canonical_organism_composition(
        present_subsystems={name: f"test role for {name}" for name in REQUIRED_SUBSYSTEMS},
        governance=_governance(_acquisition_payload),
        brain_fabric_report={
            "ready": True,
            "status": "brain_fabric_ready",
            "truth_gate_enforced": True,
            "provider_mode": "ollama_cloud_primary",
        },
        calibration_status={"status": "complete"},
    )
    configure_canonical_organism_composition(composition)
    monkeypatch.setattr(cognition_module, "_HAS_BUS", False)
    explicit = _CouncilSupplier()

    cognition = cognition_module.AureonCognition(
        adapter=_Adapter(),
        tools=ToolRegistry(include_builtins=False),
        join_mesh=False,
        council_receipt_supplier=explicit,
    )

    assert cognition._council_receipt_supplier is explicit
    assert cognition._crown_receipt_supplier is None
    assert cognition._governance_acquisition_supplier is None


def test_bad_request_scoped_acquisition_degrades_to_numeric_free_hold_input(monkeypatch):
    import aureon.operator.cognition as cognition_module

    monkeypatch.setattr(cognition_module, "_HAS_BUS", False)

    def broken():
        raise RuntimeError("provider moment unavailable")

    cognition = cognition_module.AureonCognition(
        adapter=_Adapter(),
        tools=ToolRegistry(include_builtins=False),
        join_mesh=False,
        governance_acquisition_supplier=broken,
    )

    acquisition = cognition._governance_acquisition_for(
        SimpleNamespace(acquisition={})
    )

    assert acquisition == {"knowledge_acquisition": {}}
    assert not any(isinstance(value, (int, float)) for value in acquisition.values())
