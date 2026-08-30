from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

import aureon.governance.cognition_gate as cognition_gate_module
import aureon.governance.crown_voice as crown_module
import aureon.governance.dual_key as dual_key_module
import aureon.governance.tool_route_authority as route_authority_module
import aureon.operator.cognition as cognition_module
import aureon.swarm.auris_node_receipts as node_module
from aureon.core.hnc_field import CanonicalField, build_hnc_live_field_receipt_id
from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    TrustedCouncilEvidence,
    authority_route_requires_governance,
    build_cognition_governance_request,
    evaluate_cognition_governance,
    explicit_disabled_governance,
)
from aureon.governance.crown_voice import (
    ResolvedCrownVoiceEvidence,
    issue_crown_voice_receipt,
)
from aureon.governance.dual_key import build_queen_receipt
from aureon.governance.tool_route_authority import issue_tool_route_authority_lease
from aureon.inhouse_ai.llm_adapter import LLMResponse, ToolCall
from aureon.inhouse_ai.tool_registry import ToolEffect
from aureon.operator.cognition import AureonCognition
from aureon.operator.schemas import CognitionResult
from aureon.operator.tools import GuardedToolRegistry
from aureon.swarm.auris_node_receipts import (
    COHERENCE_METHOD,
    ProviderMoment,
    ResolvedAurisNodeEvidence,
    issue_auris_node_receipt,
)
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    build_seat_receipt,
    convene_druidic_council,
)

NOW = 1_786_473_600.0
SOURCE_TIME = NOW - 2.0
AURIS = "auris:cosmic_state:cognition-gate-auris"
PROVIDERS = (
    "provider:noaa:cognition-gate",
    "provider:schumann:cognition-gate",
)
PROVIDER_DIGEST = "9" * 64
COUNCIL_SUPPLIER_ID = "resolver:trusted-council-runtime:v1"
CROWN_SUPPLIER_ID = "resolver:trusted-crown-runtime:v1"
HNC_MEMORY_HASH = "4" * 64
HNC_MEMORY_RECEIPT_ID = f"hnc:lambda_history:{HNC_MEMORY_HASH}"
HNC_INPUTS = tuple(sorted((*PROVIDERS, HNC_MEMORY_RECEIPT_ID)))
HNC = build_hnc_live_field_receipt_id(
    input_receipt_ids=HNC_INPUTS,
    source_timestamp=SOURCE_TIME,
    received_at=SOURCE_TIME + 0.1,
    step=17,
    lambda_t=0.6,
    coherence_gamma=0.95,
    consciousness_psi=0.7,
    symbolic_life_score=0.9,
)


def _provider_acquisition() -> dict[str, Any]:
    return {
        "triggered": False,
        "outcome": "not_needed",
        "provider_receipt_ids": list(PROVIDERS),
        "provider_moment_digest": PROVIDER_DIGEST,
        "source_timestamp": SOURCE_TIME,
    }


def _coherent_hnc_field() -> CanonicalField:
    return CanonicalField(
        available=True,
        symbolic_life_score=0.9,
        coherence_gamma=0.95,
        consciousness_psi=0.7,
        consciousness_level="aware",
        lambda_t=0.6,
        step=17,
        source="hnc_live_daemon",
        evidence_transport="thought_bus",
        source_id="aureon:hnc:live_daemon",
        source_timestamp=SOURCE_TIME,
        received_at=SOURCE_TIME + 0.1,
        receipt_id=HNC,
        receipt_type="hnc_live_field",
        provider_receipt_type="hnc_live_field",
        input_receipt_ids=HNC_INPUTS,
        memory_receipt_id=HNC_MEMORY_RECEIPT_ID,
        memory_canonical_hash=HNC_MEMORY_HASH,
        data_status="live",
        truth_status="real_derived",
        source_count=2.0,
        freshness_status="fresh",
        equation_inputs_complete=True,
        action_gate_reason="route_specific_market_link_required",
    )


def _assert_numeric_free(value: Any) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            _assert_numeric_free(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            _assert_numeric_free(nested)
        return
    assert not isinstance(value, (int, float)), value


@pytest.fixture(autouse=True)
def _trusted_provider_moment(monkeypatch):
    moment = ProviderMoment(
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        source_timestamp=SOURCE_TIME,
        provider_receipt_ids=PROVIDERS,
        provider_moment_digest=PROVIDER_DIGEST,
    )
    monkeypatch.setattr(
        node_module,
        "validate_provider_moment",
        lambda *args, **kwargs: moment,
    )
    monkeypatch.setattr(
        crown_module,
        "validate_provider_moment",
        lambda *args, **kwargs: moment,
    )

    def _coherence(
        raw: Any,
        *,
        seat: str,
        agent_id: str,
        source_id: str,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], float]:
        assert raw == {"measured": True}
        assert agent_id == f"agent-{seat}"
        assert source_id == f"coherence:{seat}"
        return {
            "receipt_id": f"auris:coherence_measurement:{seat}:receipt",
            "measurement_method": COHERENCE_METHOD,
        }, 0.90

    monkeypatch.setattr(
        node_module,
        "validate_coherence_measurement",
        _coherence,
    )


class _NodeResolver:
    def resolve_auris_node_evidence(
        self,
        seat: str,
    ) -> ResolvedAurisNodeEvidence:
        return ResolvedAurisNodeEvidence(
            resolver_id=COUNCIL_SUPPLIER_ID,
            coherence_source_id=f"coherence:{seat}",
            seat=seat,
            agent_id=f"agent-{seat}",
            hnc_evidence={"raw": "hnc"},
            auris_evidence={"raw": "auris"},
            coherence_evidence={"measured": True},
        )


class _CouncilSupplier:
    supplier_id = COUNCIL_SUPPLIER_ID

    def __init__(
        self,
        *,
        decisions: Mapping[str, str] | None = None,
        return_raw_council: bool = False,
        omit_node: bool = False,
        tamper_node: bool = False,
    ) -> None:
        self.decisions = dict(decisions or {})
        self.return_raw_council = return_raw_council
        self.omit_node = omit_node
        self.tamper_node = tamper_node
        self.calls = 0

    def supply_council_evidence(
        self,
        request: CognitionGovernanceRequest,
    ) -> Any:
        self.calls += 1
        resolver = _NodeResolver()
        nodes = [
            issue_auris_node_receipt(
                seat=seat,
                resolver=resolver,
                now=NOW,
            )
            for seat in REQUIRED_SEATS
        ]
        seats = [
            build_seat_receipt(
                seat=node["seat"],
                agent_id=node["agent_id"],
                decision=self.decisions.get(node["seat"], "ACCEPT"),
                reason=f"{node['seat']} verified the exact proposal",
                gamma=node["gamma"],
                proposal_digest=request.proposal_digest,
                prompt_digest=request.prompt_digest,
                hnc_receipt_id=node["hnc_receipt_id"],
                auris_receipt_id=node["auris_receipt_id"],
                auris_node_receipt_id=node["receipt_id"],
                source_timestamp=node["source_timestamp"],
                derived_at=NOW,
            )
            for node in nodes
        ]
        council = convene_druidic_council(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            seat_receipts=seats,
            now=NOW,
        )
        if self.return_raw_council:
            return council
        if self.tamper_node:
            nodes[0] = copy.deepcopy(nodes[0])
            nodes[0]["gamma"] = 0.99
        if self.omit_node:
            nodes.pop()
        return TrustedCouncilEvidence(
            council_receipt=council,
            auris_node_receipts=tuple(nodes),
        )


class _CrownSupplier:
    supplier_id = CROWN_SUPPLIER_ID

    def __init__(
        self,
        *,
        verdict: str | None = None,
        issuer_id: str = "issuer:queen-runtime",
        mutate: str | None = None,
    ) -> None:
        self.verdict = verdict
        self.issuer_id = issuer_id
        self.mutate = mutate
        self.calls = 0
        self._request: CognitionGovernanceRequest | None = None

    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence:
        assert self._request is not None
        assert proposal_digest == self._request.proposal_digest
        assert prompt_digest == self._request.prompt_digest
        return ResolvedCrownVoiceEvidence(
            resolver_id=self.supplier_id,
            issuer_id=self.issuer_id,
            crown_identity="queen:conscience",
            verdict_source_id="queen:conscience:evaluation",
            queen_verdict=self.verdict or self._request.queen_verdict,
            queen_evaluated=True,
            reason="Crown evaluated the exact immutable proposal",
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            hnc_evidence={"raw": "hnc"},
            auris_evidence={"raw": "auris"},
        )

    def supply_crown_receipt(
        self,
        request: CognitionGovernanceRequest,
    ) -> Mapping[str, Any]:
        self.calls += 1
        self._request = request
        receipt = issue_crown_voice_receipt(
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            resolver=self,
            now=NOW,
        )
        if self.mutate:
            receipt = copy.deepcopy(receipt)
            receipt[self.mutate] = "tampered"
        return receipt


class _RouteSupplier:
    supplier_id = "resolver:trusted-tool-route-authority:v1"

    def __init__(self) -> None:
        self.calls = 0

    def supply_tool_route_authority(self, request):
        self.calls += 1
        return issue_tool_route_authority_lease(
            request,
            supplier_id=self.supplier_id,
            mandate_receipt_id="mandate:director:bounded-test-fixture",
            mandate_receipt_digest="6" * 64,
            nonce=f"route-nonce-{self.calls:016d}",
            issued_at=NOW,
            not_before=NOW,
            expires_at=NOW + 1.0,
        )


class _LegacyCrownSupplier:
    supplier_id = CROWN_SUPPLIER_ID

    def __init__(self) -> None:
        self.calls = 0

    def supply_crown_receipt(
        self,
        request: CognitionGovernanceRequest,
    ) -> Mapping[str, Any]:
        self.calls += 1
        return build_queen_receipt(
            decision="APPROVE",
            reason="legacy self-assembled receipt",
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            source_timestamp=SOURCE_TIME,
            derived_at=NOW,
        )


def _evaluate(
    council: Any,
    crown: Any,
    *,
    verdict: str = "APPROVED",
    queen_evaluated: bool = True,
    answer: str = "A complete answer.",
    tool_calls: Sequence[Any] = (),
    max_age_s: float = 300.0,
) -> dict[str, Any]:
    return evaluate_cognition_governance(
        prompt="Explain the bounded system.",
        answer=answer,
        tool_calls=tool_calls,
        capability={"status": "ok", "families": [], "routes": []},
        bake={"complete": True, "passes": 1},
        acquisition=_provider_acquisition(),
        queen_verdict=verdict,
        queen_evaluated=queen_evaluated,
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        now=NOW,
        max_age_s=max_age_s,
    )


def test_proposal_digest_binds_answer_and_exact_tool_ledger() -> None:
    base = build_cognition_governance_request(
        prompt="p",
        answer="a",
        tool_calls=[{"tool": "read_state", "arguments": {"asset": "BTC"}, "blocked": False}],
        acquisition=_provider_acquisition(),
        queen_verdict="APPROVED",
    )
    same = build_cognition_governance_request(
        prompt="p",
        answer="a",
        tool_calls=[{"blocked": False, "arguments": {"asset": "BTC"}, "tool": "read_state"}],
        acquisition=_provider_acquisition(),
        queen_verdict="APPROVED",
    )
    changed = build_cognition_governance_request(
        prompt="p",
        answer="a changed",
        tool_calls=[{"tool": "read_state", "arguments": {"asset": "BTC"}, "blocked": False}],
        acquisition=_provider_acquisition(),
        queen_verdict="APPROVED",
    )

    assert base.proposal_digest == same.proposal_digest
    assert base.proposal_digest != changed.proposal_digest
    assert json.loads(base.proposal_json)["tool_calls"][0]["arguments"] == {
        "asset": "BTC",
    }


def test_exact_full_node_council_and_strict_crown_accept_once() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()
    receipt = _evaluate(council, crown)

    assert receipt["decision"] == "ACCEPT"
    assert receipt["harmonic_outcome"] == "CONSTRUCTIVE"
    assert receipt["route_authorization_required"] is True
    assert receipt["action_eligible"] is False
    assert receipt["economic_mutation"] is False
    assert receipt["provider_receipt_ids"] == list(PROVIDERS)
    assert receipt["provider_moment_digest"] == PROVIDER_DIGEST
    assert receipt["provider_source_timestamp"] == str(int(SOURCE_TIME))
    assert receipt["source_timestamp"] == SOURCE_TIME
    assert council.calls == crown.calls == 1


def test_dual_key_freshness_window_cannot_be_widened_by_caller() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()

    receipt = _evaluate(council, crown, max_age_s=3600.0)

    assert receipt["decision"] == "HOLD"
    assert receipt["data_status"] == "no_data"
    assert council.calls == crown.calls == 0
    _assert_numeric_free(receipt)


def test_council_and_crown_agreeing_on_wrong_request_provider_moment_hold(
    monkeypatch,
) -> None:
    wrong = ProviderMoment(
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        source_timestamp=SOURCE_TIME - 1.0,
        provider_receipt_ids=("provider:wrong:mutually-agreed",),
        provider_moment_digest="8" * 64,
    )
    monkeypatch.setattr(node_module, "validate_provider_moment", lambda *a, **k: wrong)
    monkeypatch.setattr(crown_module, "validate_provider_moment", lambda *a, **k: wrong)
    council = _CouncilSupplier()
    crown = _CrownSupplier()

    receipt = _evaluate(council, crown)

    assert receipt["decision"] == "HOLD"
    assert receipt["data_status"] == "no_data"
    assert council.calls == 1
    assert crown.calls == 0
    _assert_numeric_free(receipt)


@pytest.mark.parametrize(
    ("queen_verdict", "crown_verdict", "expected"),
    [
        ("CONCERNED", "CONCERNED", "HOLD"),
        ("TEACHING_MOMENT", "TEACHING_MOMENT", "HOLD"),
        ("VETO", "VETO", "ABORT"),
    ],
)
def test_evaluated_queen_voice_controls_crown_key(
    queen_verdict: str,
    crown_verdict: str,
    expected: str,
) -> None:
    receipt = _evaluate(
        _CouncilSupplier(),
        _CrownSupplier(verdict=crown_verdict),
        verdict=queen_verdict,
    )
    assert receipt["decision"] == expected


def test_crown_cannot_claim_approve_over_concerned_queen() -> None:
    receipt = _evaluate(
        _CouncilSupplier(),
        _CrownSupplier(verdict="APPROVED"),
        verdict="CONCERNED",
    )
    assert receipt["data_status"] == "no_data"
    assert receipt["decision"] == "HOLD"
    _assert_numeric_free(receipt)


@pytest.mark.parametrize(
    "council",
    [
        _CouncilSupplier(return_raw_council=True),
        _CouncilSupplier(omit_node=True),
        _CouncilSupplier(tamper_node=True),
    ],
)
def test_caller_supplied_node_ids_or_incomplete_node_bodies_fail_closed(
    council: _CouncilSupplier,
) -> None:
    crown = _CrownSupplier()
    receipt = _evaluate(council, crown)
    assert receipt["data_status"] == "no_data"
    assert receipt["receipt_id"] is None
    assert crown.calls == 0
    _assert_numeric_free(receipt)


def test_legacy_self_assembled_queen_receipt_cannot_be_the_crown_voice() -> None:
    receipt = _evaluate(_CouncilSupplier(), _LegacyCrownSupplier())
    assert receipt["data_status"] == "no_data"
    assert receipt["decision"] == "HOLD"
    _assert_numeric_free(receipt)


def test_council_and_crown_composition_identities_must_be_independent() -> None:
    crown = _CrownSupplier()
    crown.supplier_id = COUNCIL_SUPPLIER_ID
    receipt = _evaluate(_CouncilSupplier(), crown)
    assert receipt["data_status"] == "no_data"
    _assert_numeric_free(receipt)


def test_crown_identity_cannot_overlap_a_council_agent() -> None:
    receipt = _evaluate(
        _CouncilSupplier(),
        _CrownSupplier(issuer_id="agent-seer"),
    )
    assert receipt["data_status"] == "no_data"
    _assert_numeric_free(receipt)


def test_missing_or_unevaluated_voice_never_calls_a_supplier() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()
    receipt = _evaluate(
        council,
        crown,
        queen_evaluated=False,
    )
    assert receipt["data_status"] == "no_data"
    assert council.calls == crown.calls == 0
    _assert_numeric_free(receipt)


def test_invalid_proposal_material_fails_before_supplier_calls() -> None:
    council = _CouncilSupplier()
    crown = _CrownSupplier()
    receipt = _evaluate(
        council,
        crown,
        tool_calls=[
            {
                "tool": "read_state",
                "arguments": {"value": float("nan")},
                "blocked": False,
            }
        ],
    )
    assert receipt["data_status"] == "no_data"
    assert council.calls == crown.calls == 0
    _assert_numeric_free(receipt)


def test_tampered_strict_crown_receipt_is_numeric_free_no_data() -> None:
    receipt = _evaluate(
        _CouncilSupplier(),
        _CrownSupplier(mutate="provider_moment_digest"),
    )
    assert receipt["data_status"] == "no_data"
    assert receipt["receipt_id"] is None
    _assert_numeric_free(receipt)


def test_explicit_compatibility_mode_never_bypasses_authority_routes() -> None:
    safe = {
        "status": "ok",
        "families": ["safe_code_repair"],
        "routes": [{"route": "safe_code_repair", "risk": "medium"}],
    }
    trading = {
        "status": "ok",
        "families": ["safe_trading_cognition"],
        "routes": [
            {
                "route": "safe_trading_cognition",
                "risk": "high",
                "requires_human": True,
            }
        ],
    }
    office_admin = {
        "status": "ok",
        "families": ["office_admin_workweek"],
        "routes": [
            {
                "route": "office_admin_workweek",
                "risk": "medium",
                "requires_human": False,
            }
        ],
    }

    assert authority_route_requires_governance(safe) is False
    assert explicit_disabled_governance(safe)["decision"] == "DISABLED"
    assert authority_route_requires_governance(trading) is True
    assert authority_route_requires_governance(office_admin) is True
    blocked = explicit_disabled_governance(trading)
    assert blocked["decision"] == "HOLD"
    assert blocked["data_status"] == "no_data"
    assert authority_route_requires_governance(None) is True
    _assert_numeric_free(blocked)


@pytest.mark.parametrize(
    "effect",
    (
        ToolEffect.LOCAL_MUTATION,
        ToolEffect.EXTERNAL_MUTATION,
        ToolEffect.ECONOMIC_MUTATION,
        ToolEffect.PRIVILEGED,
    ),
)
def test_dual_key_accept_without_exact_route_authority_never_calls_handler(
    monkeypatch,
    effect: ToolEffect,
) -> None:
    monkeypatch.setattr(cognition_gate_module.time, "time", lambda: NOW)
    monkeypatch.setattr(dual_key_module.time, "time", lambda: NOW)

    calls: list[str] = []
    registry = GuardedToolRegistry(include_builtins=False)
    registry.define_tool(
        "mutate_fixture",
        "mutate the isolated fixture",
        {"type": "object", "properties": {}},
        lambda arguments: calls.append("handler") or '{"ok":true}',
        effect=effect,
        operation_id="aureon.test.mutate-fixture.v1",
    )

    class _Adapter:
        model = "dual-key-runtime"

        def __init__(self) -> None:
            self.calls = 0

        def prompt(self, *, tools=None, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return LLMResponse(
                    text="",
                    tool_calls=[ToolCall(name="mutate_fixture", arguments={})],
                    stop_reason="tool_use",
                    model=self.model,
                )
            return LLMResponse(
                text="complete governed answer.",
                stop_reason="end_turn",
                model=self.model,
            )

    class _Conscience:
        def __init__(self) -> None:
            self.calls = 0

        def ask_why(self, action, context):
            self.calls += 1
            return type(
                "Whisper",
                (),
                {
                    "verdict": type("Verdict", (), {"name": "APPROVED"})(),
                    "message": "approved exact proposal",
                },
            )()

    def _route(self, prompt: str, result: CognitionResult) -> None:
        result.capability = {"status": "ok", "families": [], "routes": []}

    def _ground(self, prompt: str, result: CognitionResult) -> str:
        return "test system"

    def _acquire(self, prompt: str, system: str, result: CognitionResult) -> None:
        result.acquisition = {"triggered": False, "outcome": "not_needed"}

    def _bake(self, prompt: str, system: str, result: CognitionResult) -> None:
        result.bake = {"complete": True, "passes": 1, "reasons": []}

    monkeypatch.setattr(AureonCognition, "_route", _route)
    def _gate(self, result: CognitionResult) -> None:
        self.tools.set_hnc_coherence_context(_coherent_hnc_field())
        result.coherence_gate = {"hnc_decision": {"outcome": "PROCEED"}}

    monkeypatch.setattr(AureonCognition, "_gate_aperture", _gate)
    monkeypatch.setattr(AureonCognition, "_ground", _ground)
    monkeypatch.setattr(AureonCognition, "_acquire", _acquire)
    monkeypatch.setattr(AureonCognition, "_bake", _bake)
    monkeypatch.setattr(AureonCognition, "_heart", lambda *args: None)
    monkeypatch.setattr(AureonCognition, "_publish", lambda *args: None)
    council, crown, conscience = _CouncilSupplier(), _CrownSupplier(), _Conscience()
    result = AureonCognition(
        adapter=_Adapter(),
        tools=registry,
        conscience=conscience,
        council_receipt_supplier=council,
        crown_receipt_supplier=crown,
        governance_acquisition={
            "provider_receipt_ids": list(PROVIDERS),
            "provider_moment_digest": PROVIDER_DIGEST,
            "provider_source_timestamp": str(int(SOURCE_TIME)),
        },
        join_mesh=False,
        mesh_broadcast=False,
    ).reason("govern the isolated fixture")

    assert calls == []
    assert result.blocked is False
    assert result.governance is not None
    assert result.governance["decision"] == "ACCEPT"
    assert result.tool_calls[0].handler_called is False
    assert result.tool_calls[0].blocked is True
    assert result.tool_calls[0].governance_decision == "HOLD"
    assert result.tool_calls[0].governance_receipt_id is not None
    assert result.tool_calls[0].dual_key_receipt_id is not None
    assert result.tool_calls[0].route_authority_receipt_id is None
    assert result.tool_calls[0].hnc_outcome == "PROCEED"
    assert result.tool_calls[0].hnc_decision_receipt_id is not None
    assert council.calls == crown.calls == 2
    assert conscience.calls == 2
    assert result.assimilation is not None
    assert result.assimilation["assimilated"] is False


def test_exact_allowlisted_route_lease_admits_one_local_handler(
    monkeypatch,
) -> None:
    monkeypatch.setattr(cognition_gate_module.time, "time", lambda: NOW)
    monkeypatch.setattr(dual_key_module.time, "time", lambda: NOW)
    monkeypatch.setattr(route_authority_module.time, "time", lambda: NOW)
    calls: list[str] = []
    registry = GuardedToolRegistry(include_builtins=False)
    registry.define_tool(
        "mutate_fixture",
        "mutate the isolated fixture",
        {"type": "object", "properties": {}},
        lambda arguments: calls.append("handler") or '{"ok":true}',
        effect=ToolEffect.LOCAL_MUTATION,
        operation_id="aureon.test.mutate-fixture.v1",
    )

    class _Conscience:
        def ask_why(self, action, context):
            return type(
                "Whisper",
                (),
                {
                    "verdict": type("Verdict", (), {"name": "APPROVED"})(),
                    "message": "approved exact proposal",
                },
            )()

    route = _RouteSupplier()
    engine = AureonCognition(
        adapter=object(),
        tools=registry,
        conscience=_Conscience(),
        council_receipt_supplier=_CouncilSupplier(),
        crown_receipt_supplier=_CrownSupplier(),
        governance_acquisition={
            "provider_receipt_ids": list(PROVIDERS),
            "provider_moment_digest": PROVIDER_DIGEST,
            "provider_source_timestamp": str(int(SOURCE_TIME)),
        },
        route_authority_supplier=route,
        trusted_route_authority_supplier_ids=frozenset({route.supplier_id}),
        join_mesh=False,
        mesh_broadcast=False,
    )
    proposal = registry.build_dispatch_proposal(
        tool_call_id="route-call-1",
        runner_turn_index=0,
        response_call_index=0,
        name="mutate_fixture",
        arguments={},
        context={"trace_id": "route-trace-1", "phase": "draft"},
    )
    registry.set_hnc_coherence_context(_coherent_hnc_field())
    assert registry.preauthorize_tool_dispatch(proposal) is True
    result_context = CognitionResult(
        prompt="govern the isolated fixture",
        capability={"status": "ok", "families": [], "routes": []},
    )

    authorization, gate = engine._authorize_tool_dispatch(
        proposal,
        observer_prompt=result_context.prompt,
        phase="draft",
        res=result_context,
    )
    result = json.loads(
        registry.execute(
            "mutate_fixture",
            {},
            proposal=proposal,
            authorization=authorization,
        )
    )

    assert gate["decision"] == "ACCEPT"
    assert authorization is not None
    assert authorization.authority_receipt_id.startswith("tool:route-authority:")
    assert result == {"ok": True}
    assert calls == ["handler"]
    assert route.calls == 1
    assert registry.dispatch_records[-1].hnc_outcome == "PROCEED"
    replay = json.loads(
        registry.execute(
            "mutate_fixture",
            {},
            proposal=proposal,
            authorization=authorization,
        )
    )
    assert replay["blocked"] is True
    assert calls == ["handler"]
