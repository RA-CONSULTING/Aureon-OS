from __future__ import annotations

import pytest

from aureon.core.aureon_thought_bus import ThoughtBus
from aureon.core.organism_contracts import (
    CONTRACT_SCHEMA_VERSION,
    OrganismContractStack,
    build_contract_stack_snapshot,
    work_order_contract,
)


def test_contract_stack_creates_goal_task_job_and_work_order(tmp_path):
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    stack = OrganismContractStack(
        thought_bus=bus,
        state_path=tmp_path / "contracts.json",
        source="test",
    )

    workflow = stack.create_goal_workflow(
        "Use the organism contracts to route an accounting review",
        skills=["accounting_context", "thought_bus"],
        route_surfaces=["memory", "contracts", "accounting"],
        source="test",
    )

    assert workflow["goal"]["schema_version"] == CONTRACT_SCHEMA_VERSION
    assert workflow["goal"]["contract_type"] == "goal"
    assert workflow["tasks"][0]["contract_type"] == "task"
    assert workflow["jobs"][0]["contract_type"] == "job"
    assert workflow["work_orders"][0]["contract_type"] == "work_order"
    assert workflow["work_orders"][0]["status"] == "queued"

    status = stack.status()
    assert status["contract_count"] == 4
    assert status["queue_count"] == 1
    assert status["type_counts"]["goal"] == 1
    assert status["type_counts"]["work_order"] == 1

    thoughts = bus.recall(topic_prefix="organism.contract", limit=20)
    topics = {item["topic"] for item in thoughts}
    assert "organism.contract.goal.created" in topics
    assert "organism.contract.work_order.queued" in topics


def test_contract_queue_claims_and_completes_work_order(tmp_path):
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    stack = OrganismContractStack(thought_bus=bus, state_path=tmp_path / "contracts.json")
    workflow = stack.create_goal_workflow("Run a safe local inspection")
    work_order_id = workflow["work_orders"][0]["contract_id"]

    claimed = stack.claim_next(worker="tester")
    assert claimed is not None
    assert claimed.contract_id == work_order_id
    assert claimed.status == "active"
    assert stack.status()["queue_count"] == 0

    completed = stack.complete_work_order(work_order_id, result={"ok": True}, worker="tester")
    assert completed is not None
    assert completed.status == "completed"

    status = stack.status()
    assert status["status_counts"]["completed"] >= 1
    assert status["type_counts"]["result"] == 1
    topics = {item["topic"] for item in bus.recall(topic_prefix="organism.contract", limit=30)}
    assert "organism.contract.work_order.claimed" in topics
    assert "organism.contract.work_order.completed" in topics
    assert "organism.contract.result" in topics


def test_unsafe_contracts_are_blocked_and_not_queued(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_LIVE_TRADING", "0")
    monkeypatch.setenv("AUREON_DISABLE_REAL_ORDERS", "1")
    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    stack = OrganismContractStack(thought_bus=bus, state_path=tmp_path / "contracts.json")

    blocked = stack.store(
        work_order_contract(
            "Submit HMRC return",
            "submit_hmrc",
            payload={"details": "file the CT600 with HMRC"},
            queue="organism.default",
        )
    )

    assert blocked.blocked is True
    assert blocked.status == "blocked"
    assert blocked.requires_human is True
    assert stack.status()["queue_count"] == 0
    topics = {item["topic"] for item in bus.recall(topic_prefix="organism.contract", limit=10)}
    assert "organism.contract.blocked" in topics


def test_contract_stack_snapshot_reads_persisted_state(tmp_path):
    stack = OrganismContractStack(state_path=tmp_path / "state" / "organism_contract_stack.json")
    stack.create_goal_workflow("Queue a contract snapshot test")

    snapshot = build_contract_stack_snapshot(tmp_path)

    assert snapshot["contract_schema_version"] == CONTRACT_SCHEMA_VERSION
    assert "goal" in snapshot["contract_types"]
    assert "work_order" in snapshot["contract_types"]
    assert snapshot["contract_count"] == 4
    assert snapshot["queue_count"] == 1


def test_import_state_preserves_legacy_source_and_does_not_requeue_completed_work(tmp_path):
    legacy_path = tmp_path / "state" / "legacy_contracts.json"
    legacy = OrganismContractStack(state_path=legacy_path, source="legacy")
    queued = legacy.enqueue_work_order("Queued legacy task", "execute_internal_task")
    completed = legacy.enqueue_work_order("Completed legacy task", "execute_internal_task")
    legacy.complete_work_order(completed.contract_id, result={"ok": True})

    canonical_path = tmp_path / "state" / "organism_contract_stack.json"
    canonical = OrganismContractStack(state_path=canonical_path, source="canonical")
    result = canonical.import_state(legacy_path)

    assert result["source_preserved"] is True
    assert legacy_path.exists()
    assert result["imported_contract_count"] >= 2
    assert queued.contract_id in canonical.queue
    assert completed.contract_id not in canonical.queue
    second = canonical.import_state(legacy_path)
    assert second["imported_contract_count"] == 0


def test_claim_next_available_services_deepest_specialist_queue(tmp_path):
    stack = OrganismContractStack(state_path=tmp_path / "contracts.json")
    stack.enqueue_work_order("default", "execute_internal_task", queue="organism.default")
    first_growth = stack.enqueue_work_order("growth one", "execute_internal_task", queue="organism.capability_growth")
    stack.enqueue_work_order("growth two", "execute_internal_task", queue="organism.capability_growth")

    claimed = stack.claim_next_available(
        ("organism.capability_growth", "organism.default"),
        worker="test",
    )

    assert claimed is not None
    assert claimed.contract_id == first_growth.contract_id
    assert claimed.queue == "organism.capability_growth"


def test_deduplicate_queue_preserves_contracts_and_cancels_only_duplicates(tmp_path):
    stack = OrganismContractStack(state_path=tmp_path / "contracts.json")
    first = stack.enqueue_work_order(
        "first",
        "execute_internal_task",
        queue="organism.capability_growth",
        payload={"gap": {"domain": "repo_wiring"}},
    )
    duplicate = stack.enqueue_work_order(
        "duplicate",
        "execute_internal_task",
        queue="organism.capability_growth",
        payload={"gap": {"domain": "repo_wiring"}},
    )

    result = stack.deduplicate_queued_work_orders(
        "organism.capability_growth",
        payload_path=("gap", "domain"),
        worker="test",
    )

    assert result["superseded_count"] == 1
    assert result["contracts_preserved"] is True
    assert first.contract_id in stack.contracts
    assert stack.contracts[duplicate.contract_id]["status"] == "cancelled"
    assert stack.contracts[duplicate.contract_id]["payload"]["superseded_by"] == first.contract_id


def test_integrated_cognitive_system_contract_commands(tmp_path):
    from aureon.core.integrated_cognitive_system import IntegratedCognitiveSystem

    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    stack = OrganismContractStack(thought_bus=bus, state_path=tmp_path / "contracts.json")
    ics = IntegratedCognitiveSystem()
    ics.thought_bus = bus
    ics.contract_stack = stack

    with pytest.raises(RuntimeError, match="integrated_cognitive_input_hold"):
        ics.process_user_input("/contracts goal reconcile internal task queues")
    assert stack.status()["queue_count"] == 0
