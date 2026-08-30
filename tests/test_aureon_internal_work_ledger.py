from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Generator

import pytest

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    canonical_agent_company_brain_topology,
)
from aureon.autonomous.aureon_internal_coding_workforce import ResolvedBrain, WorkforceHold
from aureon.autonomous.aureon_internal_work_ledger import (
    DurableInternalWorkLedger,
    WorkLedgerBusy,
    WorkLedgerError,
    _writer_lease,
)
from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk
from tests.aureon_ten_nine_one_fixtures import build_test_thought_path


class LedgerAdapter(LLMAdapter):
    def __init__(self, lane: str) -> None:
        self.lane = lane

    def prompt(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        del system, tools, max_tokens, temperature, kwargs
        return LLMResponse(text=f"{self.lane}:{messages[-1]['content']}", model=f"{self.lane}-model")

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        del messages, system, tools, max_tokens, temperature, kwargs
        yield StreamChunk(text="done", done=True)


class LedgerResolver:
    def __init__(self) -> None:
        self.adapters: dict[str, LedgerAdapter] = {}

    def resolve(self, lane: str) -> ResolvedBrain:
        return self.resolve_for(lane, nerve_id=f"lane:{lane}")

    def resolve_for(self, lane: str, *, nerve_id: str) -> ResolvedBrain:
        return ResolvedBrain(
            adapter=self.adapters.setdefault(lane, LedgerAdapter(lane)),
            lane=lane,
            model=f"ollama-{lane}",
            source="live_probe_passed:hnc_active:ledger-test",
            endpoint_reachable=True,
            working=True,
            catalog_size=5,
            catalog_refreshed_at=1_787_000_000.0,
            endpoint_authority_digest="9" * 64,
            routing_receipt_id="ollama:hnc-route:" + hashlib.sha256(nerve_id.encode()).hexdigest(),
            hnc_receipt_id="hnc:live_field:test",
            hnc_gamma=0.9,
            hnc_coherence_band="active",
            provider_mode="ollama_cloud_primary",
        )


def _decide(workforce, index: int = 1) -> None:
    workforce.decide(
        subject_type="agent",
        subject_id="Implementation Worker",
        process_id="build_execution",
        prompt=f"Implement bounded change {index}",
        stage="implementation",
    )


def test_work_receipts_resume_across_a_fresh_workforce(tmp_path: Path) -> None:
    ledger = DurableInternalWorkLedger(tmp_path / "state" / "coding-work.json")
    first = ledger.bind_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    _decide(first, 1)

    second = ledger.bind_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    assert second.report()["internal_work_units"] == 1
    _decide(second, 2)

    receipts = ledger.receipts()
    assert [item.sequence for item in receipts] == [1, 2]
    assert len({item.receipt_id for item in receipts}) == 2
    assert ledger.status()["generation"] == 2
    assert ledger.status()["receipt_count"] == 2
    assert ledger.status()["action_eligible"] is False


def test_99_percent_contract_survives_restart_and_final_review(tmp_path: Path) -> None:
    ledger = DurableInternalWorkLedger(tmp_path / "private" / "coding-work.json")
    workforce = ledger.bind_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    for index in range(99):
        _decide(workforce, index)
    workforce.record_senior_oversight(
        process_id="client_handover",
        stage="release_acceptance",
        reviewed_input_digest="a" * 64,
        review_output_digest="b" * 64,
    )
    assert workforce.report()["ready"] is True

    resumed = ledger.bind_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    report = resumed.report()
    assert report["ready"] is True
    assert report["internal_work_units"] == 99
    assert report["senior_oversight_units"] == 1
    assert report["internal_share_ppm"] == 990_000
    assert report["senior_oversight_is_final"] is True


def test_full_agent_company_binding_persists_41_plus_41_brain_work(tmp_path: Path) -> None:
    ledger = DurableInternalWorkLedger(tmp_path / "private" / "company-work.json")
    workforce = ledger.bind_agent_company_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    _role_lanes, process_bindings = canonical_agent_company_brain_topology()
    process_id = next(
        process for process, (_lane, owner) in process_bindings.items() if owner == "Implementation Worker"
    )

    workforce.decide(
        subject_type="agent",
        subject_id="Implementation Worker",
        process_id=process_id,
        prompt="Implement one bounded internal change.",
        stage="implementation",
    )
    report = workforce.report()
    assert report["agent_brain_count"] == 41
    assert report["process_brain_count"] == 41
    assert len(report["passports"]) == 82
    assert ledger.status()["receipt_count"] == 1

    resumed = ledger.bind_agent_company_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    assert resumed.report()["internal_work_units"] == 1


def test_full_company_binding_rejects_receipts_from_smaller_foreign_fabric(tmp_path: Path) -> None:
    ledger = DurableInternalWorkLedger(tmp_path / "private" / "foreign-work.json")
    small = ledger.bind_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    small.decide(
        subject_type="agent",
        subject_id="Estimator",
        process_id="client_intake",
        prompt="Foreign small-fabric scope decision.",
        stage="scope",
    )

    with pytest.raises(WorkforceHold, match="brain_binding_invalid"):
        ledger.bind_agent_company_workforce(LedgerResolver(), thought_path=build_test_thought_path())


def test_tamper_is_detected_before_receipts_are_rehydrated(tmp_path: Path) -> None:
    ledger = DurableInternalWorkLedger(tmp_path / "private" / "coding-work.json")
    workforce = ledger.bind_workforce(LedgerResolver(), thought_path=build_test_thought_path())
    _decide(workforce)
    payload = json.loads(ledger.path.read_text(encoding="utf-8"))
    payload["entries"][0]["work_receipt"]["actor_id"] = "forged"
    ledger.path.write_bytes(
        (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    )

    with pytest.raises(WorkLedgerError, match="state_hash_mismatch"):
        ledger.receipts()


def test_writer_contention_fails_immediately_without_local_divergence(tmp_path: Path) -> None:
    ledger = DurableInternalWorkLedger(tmp_path / "private" / "coding-work.json")
    workforce = ledger.bind_workforce(LedgerResolver(), thought_path=build_test_thought_path())

    with _writer_lease(ledger.lock_path), pytest.raises(WorkLedgerBusy, match="writer_busy"):
        _decide(workforce)

    assert workforce.report()["total_work_units"] == 0
    assert ledger.receipts() == ()


@pytest.mark.parametrize(
    "path",
    [Path("frontend/public/work.json"), Path("state/work.txt")],
)
def test_ledger_requires_a_private_json_path(path: Path) -> None:
    with pytest.raises(ValueError, match="private_json"):
        DurableInternalWorkLedger(path)
