from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from typing import Any

import pytest

import aureon.governance.workforce_druid_resolver as workforce_module
from aureon.autonomous.aureon_internal_coding_workforce import (
    INTERNAL_ACTOR,
    WORK_SCHEMA_VERSION,
    WorkReceipt,
)
from aureon.governance.cognition_gate import CognitionGovernanceRequest
from aureon.governance.workforce_druid_resolver import (
    DEFAULT_WORKFORCE_DRUID_ROLES,
    WORKFORCE_DRUID_SCHEMA,
    bind_workforce_druid_resolver_factory,
)
from aureon.swarm.druidic_council import REQUIRED_SEATS

NOW = 1_786_480_000.0
FACTORY_ID = "aureon:workforce-druid-factory:v1"
RESOLVER_ID = "aureon:workforce-druid-resolver:v1"


def _sha(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _request() -> CognitionGovernanceRequest:
    evidence = {
        "action_influence_allowed": True,
        "blockers": [],
        "capital_market_evidence_receipt_id": "capital:evidence:one",
        "context_ready": True,
        "context_source_kinds": ["cftc_cot", "treasury_yield"],
        "probability": {"calibration_status": "validated"},
        "recommended_side": "BUY",
        "target_provider_moment_digest": "e" * 64,
        "target_provider_source_timestamp": NOW - 2.0,
        "target_ready": True,
        "volatility": {"spread_pct": 0.01},
    }
    proposal_json = json.dumps(
        {
            "tool_calls": [
                {
                    "arguments": {
                        "economic_mutation": {
                            "account_id_hash": "sensitive-account-hash",
                            "decision_evidence_json": json.dumps(
                                evidence, sort_keys=True, separators=(",", ":")
                            ),
                        }
                    },
                    "blocked": False,
                    "tool": "economic_boundary.prepare_mutation",
                }
            ]
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return CognitionGovernanceRequest(
        schema="aureon.cognition-governance-request.v1",
        prompt_digest="b" * 64,
        proposal_digest="a" * 64,
        proposal_json=proposal_json,
        provider_receipt_ids=("provider:one", "provider:two"),
        provider_moment_digest="c" * 64,
        provider_source_timestamp=str(NOW - 2.0),
        target_provider_receipt_ids=("provider:one", "provider:two"),
        target_provider_moment_digest="c" * 64,
        target_provider_source_timestamp=str(NOW - 2.0),
        queen_verdict="APPROVED",
    )


def _nodes() -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "seat": seat,
            "agent_id": f"agent-{seat}",
            "receipt_id": f"auris:node:{seat}",
            "hnc_receipt_id": "hnc:live_field:workforce",
            "auris_receipt_id": "auris:cosmic_state:workforce",
            "provider_receipt_ids": ["provider:one", "provider:two"],
            "provider_moment_digest": "c" * 64,
            "source_timestamp": NOW - 2.0,
            "data_status": "live",
        }
        for seat in REQUIRED_SEATS
    )


def _receipt(
    *,
    sequence: int,
    role: str,
    process_id: str,
    prompt: str,
    output: str,
    completed_at: float = NOW - 1.0,
) -> WorkReceipt:
    receipt = WorkReceipt(
        schema_version=WORK_SCHEMA_VERSION,
        sequence=sequence,
        actor_class=INTERNAL_ACTOR,
        actor_id=f"aureon:agent:{role}",
        process_id=process_id,
        stage="druidic_council_deliberation",
        work_kind="druid_seat_governance",
        input_digest=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        output_digest=hashlib.sha256(output.encode("utf-8")).hexdigest(),
        brain_passport_id=f"brain:{'d' * 64}",
        completed_at=completed_at,
        action_eligible=False,
        economic_eligible=False,
        receipt_id="",
        thought_path_receipt_id=f"thought:10-9-1:truth-gated:{sequence}",
    )
    causal = asdict(receipt)
    causal.pop("receipt_id")
    return replace(receipt, receipt_id=f"work:{_sha(causal)}")


class _Workforce:
    def __init__(
        self,
        *,
        decisions: dict[str, str] | None = None,
        stale: bool = False,
        tamper: bool = False,
    ) -> None:
        self.decisions = dict(decisions or {})
        self.stale = stale
        self.tamper = tamper
        self.calls: list[dict[str, Any]] = []

    def process_id_for_role(self, role: str) -> str:
        return f"agent_company_role_cycle:{role.lower().replace(' ', '_')}"

    def decide(self, **kwargs: Any) -> tuple[str, WorkReceipt]:
        prompt_body = json.loads(kwargs["prompt"].split("\n", 1)[0])
        seat = prompt_body["seat"]
        output = self.decisions.get(
            seat,
            f"ACCEPT {seat} verified the exact provider-bound proposal",
        )
        self.calls.append(dict(kwargs))
        receipt = _receipt(
            sequence=len(self.calls),
            role=kwargs["subject_id"],
            process_id=kwargs["process_id"],
            prompt=kwargs["prompt"],
            output=output,
            completed_at=(NOW - 60.0 if self.stale else NOW - 1.0),
        )
        if self.tamper:
            receipt = replace(receipt, input_digest="f" * 64)
        return output, receipt


def _factory(workforce: Any, **kwargs: Any):
    return bind_workforce_druid_resolver_factory(
        factory_id=FACTORY_ID,
        resolver_id=RESOLVER_ID,
        issuer_id_prefix="aureon:workforce-druid-issuer",
        trusted_factory_ids=frozenset({FACTORY_ID}),
        workforce=workforce,
        max_age_s=30.0,
        clock=lambda: NOW,
        **kwargs,
    )


@pytest.fixture(autouse=True)
def _validated_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        workforce_module,
        "validate_auris_node_receipt",
        lambda node, **_kwargs: dict(node),
    )


def test_four_internal_brains_issue_exact_receipt_bound_peer_voices() -> None:
    workforce = _Workforce(decisions={"sentinel": "HOLD risk envelope incomplete"})
    resolver = _factory(workforce).build_druid_seat_resolver(_request(), _nodes())

    bindings = resolver.trusted_druid_seat_bindings()
    voices = {
        seat: resolver.resolve_druid_seat_voice(seat, "a" * 64, "b" * 64)
        for seat in REQUIRED_SEATS
    }

    assert list(bindings) == list(REQUIRED_SEATS)
    assert len({binding.decision_source_id for binding in bindings.values()}) == 4
    assert all(
        binding.decision_source_id.startswith("work:")
        for binding in bindings.values()
    )
    assert voices["sentinel"] is not None
    assert voices["sentinel"].decision == "HOLD"
    assert all(
        voices[seat].auris_node_receipt_id == f"auris:node:{seat}"
        for seat in REQUIRED_SEATS
    )
    assert all(
        "thought:10-9-1:truth-gated:" in voices[seat].reason
        for seat in REQUIRED_SEATS
    )
    assert len(workforce.calls) == 4
    for seat, call in zip(REQUIRED_SEATS, workforce.calls, strict=True):
        prompt = json.loads(call["prompt"].split("\n", 1)[0])
        assert prompt["schema"] == WORKFORCE_DRUID_SCHEMA
        assert prompt["seat"] == seat
        assert prompt["agent_role"] == DEFAULT_WORKFORCE_DRUID_ROLES[seat]
        assert prompt["proposal_digest"] == "a" * 64
        assert prompt["decision_evidence"]["recommended_side"] == "BUY"
        assert "account_id_hash" not in prompt
        assert "sensitive-account-hash" not in call["prompt"]
        assert prompt["auris_node_receipt_id"] == f"auris:node:{seat}"
        assert call["stage"] == "druidic_council_deliberation"
        assert call["work_kind"] == "druid_seat_governance"
        assert call["max_tokens"] == 512
        assert "ALLOWED EXACT RESPONSES:" in call["prompt"]


def test_resolver_returns_none_for_wrong_proposal_or_unknown_seat() -> None:
    resolver = _factory(_Workforce()).build_druid_seat_resolver(
        _request(),
        _nodes(),
    )

    assert resolver.resolve_druid_seat_voice("unknown", "a" * 64, "b" * 64) is None
    assert resolver.resolve_druid_seat_voice("seer", "0" * 64, "b" * 64) is None


@pytest.mark.parametrize(
    ("output", "reason"),
    [
        ("MAYBE insufficient evidence", "exact_workforce_accept_hold_abort_token_required"),
        ("ACCEPT", "workforce_decision_reason_required"),
    ],
)
def test_unstructured_model_decisions_fail_closed(output: str, reason: str) -> None:
    workforce = _Workforce(decisions={"seer": output})

    with pytest.raises(ValueError, match=reason):
        _factory(workforce).build_druid_seat_resolver(_request(), _nodes())


def test_tampered_or_stale_work_receipts_fail_closed() -> None:
    with pytest.raises(ValueError, match="valid_truth_gated_work_receipt_required"):
        _factory(_Workforce(tamper=True)).build_druid_seat_resolver(
            _request(),
            _nodes(),
        )

    with pytest.raises(ValueError, match="fresh_workforce_druid_receipt_required"):
        _factory(_Workforce(stale=True)).build_druid_seat_resolver(
            _request(),
            _nodes(),
        )


def test_factory_requires_explicit_allowlist_and_exact_distinct_seat_roles() -> None:
    with pytest.raises(ValueError, match="workforce_druid_factory_not_allowlisted"):
        bind_workforce_druid_resolver_factory(
            factory_id=FACTORY_ID,
            resolver_id=RESOLVER_ID,
            issuer_id_prefix="issuer",
            trusted_factory_ids=frozenset({"other"}),
            workforce=_Workforce(),
        )

    with pytest.raises(
        ValueError,
        match="exact_distinct_four_seat_workforce_roles_required",
    ):
        _factory(
            _Workforce(),
            seat_roles=dict.fromkeys(REQUIRED_SEATS, "one-role"),
        )
