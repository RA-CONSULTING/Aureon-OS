from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace
from typing import Any

import pytest

import aureon.governance.cognition_gate as cognition_gate_module
from aureon.core.hnc_field import CanonicalField, build_hnc_live_field_receipt_id
from aureon.inhouse_ai.agent_runner import AgentRunner
from aureon.inhouse_ai.llm_adapter import LLMResponse, ToolCall
from aureon.inhouse_ai.tool_registry import ToolEffect, ToolRegistry
from aureon.operator.cognition import AureonCognition
from aureon.operator.local_action_bridge import LocalActionBridge
from aureon.operator.tools import GuardedToolRegistry, build_operator_tools
from aureon.swarm.druidic_council import ACTIVE_THRESHOLD, LIGHTHOUSE_THRESHOLD


def _field(gamma: float) -> CanonicalField:
    now = time.time()
    source_timestamp = now - 0.5
    received_at = now - 0.25
    step = 13
    memory_hash = "3" * 64
    memory_receipt_id = f"hnc:lambda_history:{memory_hash}"
    input_receipt_ids = tuple(sorted((
        memory_receipt_id,
        "provider:test:a",
        "provider:test:b",
    )))
    receipt_id = build_hnc_live_field_receipt_id(
        input_receipt_ids=input_receipt_ids,
        source_timestamp=source_timestamp,
        received_at=received_at,
        step=step,
        lambda_t=0.6,
        coherence_gamma=gamma,
        consciousness_psi=0.7,
        symbolic_life_score=0.9,
    )
    return CanonicalField(
        available=True,
        symbolic_life_score=0.9,
        coherence_gamma=gamma,
        consciousness_psi=0.7,
        consciousness_level="aware",
        lambda_t=0.6,
        step=step,
        source="hnc_live_daemon",
        evidence_transport="thought_bus",
        source_id="aureon:hnc:live_daemon",
        source_timestamp=source_timestamp,
        received_at=received_at,
        receipt_id=receipt_id,
        receipt_type="hnc_live_field",
        provider_receipt_type="hnc_live_field",
        input_receipt_ids=input_receipt_ids,
        memory_receipt_id=memory_receipt_id,
        memory_canonical_hash=memory_hash,
        data_status="live",
        truth_status="real_derived",
        generated_values=False,
        source_count=2.0,
        freshness_status="fresh",
        equation_inputs_complete=True,
        action_gate_reason="route_specific_market_link_required",
    )


def _registry(
    effect: ToolEffect,
    calls: list[dict[str, Any]],
    *,
    repair_safe: bool = False,
) -> GuardedToolRegistry:
    registry = GuardedToolRegistry(
        include_builtins=False,
        governance_required=True,
    )
    registry.define_tool(
        "probe",
        "bounded HNC probe",
        {"type": "object", "properties": {}, "additionalProperties": False},
        lambda args: calls.append(dict(args)) or '{"ok":true}',
        effect=effect,
        operation_id="aureon.test.hnc-probe.v1",
        hnc_repair_safe=repair_safe,
    )
    return registry


def _proposal(registry: GuardedToolRegistry):
    return registry.build_dispatch_proposal(
        tool_call_id="call-1",
        runner_turn_index=1,
        response_call_index=0,
        name="probe",
        arguments={},
        context={"trace_id": "trace-1"},
    )


def test_hnc_runs_before_read_only_bypass() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.READ_ONLY, calls)
    registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD))
    proposal = _proposal(registry)

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert result == {"ok": True}
    assert calls == [{}]
    assert registry.dispatch_records[-1].decision == "READ_ONLY_BYPASS"
    assert registry.dispatch_records[-1].hnc_outcome == "PROCEED"
    assert registry.dispatch_records[-1].hnc_decision_receipt_id.startswith(
        "hnc:coherence_decision:"
    )
    assert registry.hnc_decisions[-1]["outcome"] == "PROCEED"
    assert registry.hnc_decisions[-1]["proposal_digest"] == proposal.proposal_digest


def test_dark_hnc_holds_non_repair_read_before_handler() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.READ_ONLY, calls)
    registry.set_hnc_coherence_context(CanonicalField())
    proposal = _proposal(registry)

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert result["blocked"] is True
    assert "HNC coherence REPAIR" in result["reason"]
    assert calls == []
    assert registry.dispatch_records[-1].decision == "REPAIR"


def test_required_hnc_with_missing_context_cannot_fall_through_to_read_only_bypass() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.READ_ONLY, calls)
    registry.require_hnc_coherence()
    proposal = _proposal(registry)

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert result["blocked"] is True
    assert registry.hnc_decisions[-1]["outcome"] == "REPAIR"
    assert calls == []


def test_hnc_requirement_cannot_be_downgraded_on_default_registry() -> None:
    calls: list[dict[str, Any]] = []
    registry = GuardedToolRegistry(
        include_builtins=False,
        governance_required=False,
    )
    registry.define_tool(
        "probe",
        "default registry probe",
        {"type": "object", "properties": {}},
        lambda args: calls.append(dict(args)) or '{"ok":true}',
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.test.default-hnc-probe.v1",
    )
    registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD))

    missing = json.loads(
        registry.execute("probe", {}, governance_required=False)
    )
    proposal = _proposal(registry)
    accepted = json.loads(
        registry.execute(
            "probe",
            {},
            proposal=proposal,
            governance_required=False,
        )
    )

    assert missing["blocked"] is True
    assert accepted == {"ok": True}
    assert calls == [{}]
    assert registry.hnc_coherence_required is True


def test_hnc_latch_also_governs_base_tool_registry() -> None:
    calls: list[dict[str, Any]] = []
    registry = ToolRegistry(include_builtins=False, governance_required=False)
    registry.define_tool(
        "probe",
        "base registry probe",
        {"type": "object", "properties": {}},
        lambda args: calls.append(dict(args)) or '{"ok":true}',
        effect=ToolEffect.READ_ONLY,
        operation_id="aureon.test.base-hnc-probe.v1",
    )
    registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD))
    proposal = registry.build_dispatch_proposal(
        tool_call_id="base-call",
        runner_turn_index=0,
        response_call_index=0,
        name="probe",
        arguments={},
    )

    result = json.loads(
        registry.execute(
            "probe",
            {},
            proposal=proposal,
            governance_required=False,
        )
    )

    assert result == {"ok": True}
    assert calls == [{}]
    assert registry.dispatch_records[-1].hnc_outcome == "PROCEED"


def test_dark_hnc_allows_only_explicit_repair_safe_introspection() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.READ_ONLY, calls, repair_safe=True)
    registry.set_hnc_coherence_context(CanonicalField())
    proposal = _proposal(registry)

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert result == {"ok": True}
    assert calls == [{}]
    assert registry.hnc_decisions[-1]["outcome"] == "REPAIR"
    assert registry.dispatch_records[-1].hnc_outcome == "REPAIR"
    assert registry.dispatch_records[-1].hnc_repair_safe is True


@pytest.mark.parametrize(
    "effect",
    (
        ToolEffect.LOCAL_MUTATION,
        ToolEffect.EXTERNAL_MUTATION,
        ToolEffect.ECONOMIC_MUTATION,
        ToolEffect.PRIVILEGED,
    ),
)
def test_repair_safe_metadata_never_opens_a_mutation_effect(
    effect: ToolEffect,
) -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(effect, calls, repair_safe=True)
    registry.set_hnc_coherence_context(CanonicalField())
    proposal = _proposal(registry)

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert result["blocked"] is True
    assert calls == []
    assert registry.dispatch_records[-1].hnc_repair_safe is False


@pytest.mark.parametrize("bad_value", ("false", 1, None))
def test_repair_safe_metadata_requires_an_exact_boolean(bad_value: Any) -> None:
    registry = ToolRegistry(include_builtins=False)

    with pytest.raises(TypeError, match="hnc_repair_safe must be bool"):
        registry.define_tool(
            "probe",
            "invalid repair metadata",
            {"type": "object", "properties": {}},
            lambda args: '{"ok":true}',
            effect=ToolEffect.READ_ONLY,
            hnc_repair_safe=bad_value,
        )


def test_nested_hnc_context_restores_outer_field() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.READ_ONLY, calls)
    registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD))
    registry.set_hnc_coherence_context(CanonicalField())
    inner = _proposal(registry)

    assert json.loads(registry.execute("probe", {}, proposal=inner))["blocked"] is True
    registry.clear_hnc_coherence_context()
    outer = registry.build_dispatch_proposal(
        tool_call_id="outer-call",
        runner_turn_index=1,
        response_call_index=1,
        name="probe",
        arguments={},
    )
    assert json.loads(registry.execute("probe", {}, proposal=outer)) == {"ok": True}
    registry.clear_hnc_coherence_context()
    assert registry.hnc_context_active is False


def test_inherited_async_context_is_revoked_when_parent_turn_ends() -> None:
    async def _scenario() -> tuple[dict[str, Any], list[dict[str, Any]]]:
        calls: list[dict[str, Any]] = []
        registry = _registry(ToolEffect.READ_ONLY, calls)
        registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD))
        release = asyncio.Event()

        async def _child() -> dict[str, Any]:
            await release.wait()
            proposal = _proposal(registry)
            return json.loads(registry.execute("probe", {}, proposal=proposal))

        child = asyncio.create_task(_child())
        await asyncio.sleep(0)
        registry.clear_hnc_coherence_context()
        release.set()
        return await child, calls

    result, calls = asyncio.run(_scenario())

    assert result["blocked"] is True
    assert "HNC coherence REPAIR" in result["reason"]
    assert calls == []


def test_high_hnc_does_not_fabricate_mutation_authority() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.ECONOMIC_MUTATION, calls)
    registry.set_hnc_coherence_context(_field(LIGHTHOUSE_THRESHOLD))
    proposal = _proposal(registry)

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert registry.hnc_decisions[-1]["outcome"] == "PROCEED"
    assert result["blocked"] is True
    assert "missing dispatch authorization" in result["reason"]
    assert calls == []


def test_low_hnc_holds_mutation_before_authorization_or_handler() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.LOCAL_MUTATION, calls)
    registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD - 0.01))
    proposal = _proposal(registry)

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert result["blocked"] is True
    assert registry.dispatch_records[-1].decision == "REPAIR"
    assert calls == []


def test_low_hnc_stops_before_authority_supplier_is_called() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.LOCAL_MUTATION, calls)
    registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD - 0.01))
    supplier_calls: list[str] = []
    runner = AgentRunner(
        object(),
        tools=registry,
        governance_required=True,
        authorize_tool_dispatch=lambda proposal: supplier_calls.append(
            proposal.proposal_digest
        ),
    )

    results = runner._dispatch_tool_calls(
        [ToolCall(id="low-hnc-call", name="probe", arguments={})],
        runner_turn_index=0,
        dispatch_mode="turn",
    )

    assert json.loads(results[0]["content"])["blocked"] is True
    assert supplier_calls == []
    assert calls == []


def test_cached_hnc_proceed_is_revalidated_at_handler_boundary(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.LOCAL_MUTATION, calls)
    field = _field(ACTIVE_THRESHOLD)
    registry.set_hnc_coherence_context(field)
    proposal = _proposal(registry)
    assert registry.preauthorize_tool_dispatch(proposal) is True
    monkeypatch.setattr(
        cognition_gate_module.time,
        "time",
        lambda: float(field.source_timestamp) + 301.0,
    )

    result = json.loads(registry.execute("probe", {}, proposal=proposal))

    assert result["blocked"] is True
    assert "HNC coherence REPAIR" in result["reason"]
    assert calls == []


def test_proposal_tamper_is_rejected_before_hnc_evaluation() -> None:
    calls: list[dict[str, Any]] = []
    registry = _registry(ToolEffect.READ_ONLY, calls)
    registry.set_hnc_coherence_context(_field(ACTIVE_THRESHOLD))
    proposal = _proposal(registry)

    result = json.loads(
        registry.execute("probe", {"changed": True}, proposal=proposal)
    )

    assert result["blocked"] is True
    assert "arguments" in result["reason"]
    assert registry.hnc_decisions == []
    assert calls == []


def test_only_pure_local_introspection_is_repair_safe_in_production_toolbelt() -> None:
    registry = build_operator_tools(allow_writes=True, allow_shell=True)

    assert {
        name
        for name in registry.names()
        if registry.get(name) is not None and registry.get(name).hnc_repair_safe
    } == {"read_state", "code_validate"}


def test_isolated_tenant_can_use_pure_code_validate_in_dark_repair_mode(
    monkeypatch,
) -> None:
    class _Adapter:
        model = "tenant-fixture"

        def __init__(self) -> None:
            self.calls = 0

        def prompt(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return LLMResponse(
                    tool_calls=[ToolCall(
                        id="tenant-code-validate",
                        name="code_validate",
                        arguments={"code": "def valid():\n    return True\n"},
                    )],
                    stop_reason="tool_use",
                    model=self.model,
                )
            return LLMResponse(
                text="Validation completed.",
                stop_reason="end_turn",
                model=self.model,
            )

    class _Bus:
        def subscribe(self, *_args, **_kwargs):
            return None

        def publish(self, *_args, **_kwargs):
            return None

    class _Conscience:
        def ask_why(self, _action, _context):
            return SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED"),
                message="approved pure tenant computation",
            )

    monkeypatch.setattr(
        AureonCognition,
        "_route",
        lambda _self, _prompt, result: setattr(
            result, "capability", {"status": "ok", "families": [], "routes": []}
        ),
    )
    monkeypatch.setattr(
        AureonCognition,
        "_ground",
        lambda _self, _prompt, _result: "isolated tenant system",
    )
    monkeypatch.setattr(
        AureonCognition,
        "_acquire",
        lambda _self, _prompt, _system, result: setattr(
            result, "acquisition", {"triggered": False, "outcome": "not_needed"}
        ),
    )
    monkeypatch.setattr(
        AureonCognition,
        "_bake",
        lambda _self, _prompt, _system, result: setattr(
            result, "bake", {"complete": True, "passes": 1, "reasons": []}
        ),
    )
    monkeypatch.setattr(AureonCognition, "_heart", lambda *_args: None)
    monkeypatch.setattr(
        AureonCognition,
        "_read_organism_state",
        lambda _self: {},
    )
    tools = build_operator_tools(
        allow_writes=False,
        allow_shell=False,
        allowlist={"code_validate"},
    )
    result = AureonCognition(
        adapter=_Adapter(),
        tools=tools,
        bus=_Bus(),
        conscience=_Conscience(),
        join_mesh=False,
        mesh_broadcast=False,
        allow_repo_grounding=False,
        allow_organism_context=False,
        governance_enabled=False,
    ).reason("validate this isolated code")

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool == "code_validate"
    assert result.tool_calls[0].handler_called is True
    assert result.tool_calls[0].blocked is False
    assert result.tool_calls[0].hnc_outcome == "REPAIR"
    assert result.tool_calls[0].hnc_repair_safe is True


def test_consequential_subject_is_readable_but_generic_mutation_bypass_is_not() -> None:
    subject = {"query": "explain the live trade route and payment filing path"}
    command = {"command": "place a live trade and disable the safety gate"}

    assert GuardedToolRegistry._guard("repo_search", subject) is None
    assert "bypass boundary" in str(
        GuardedToolRegistry._guard("execute_shell", command)
    )


def test_local_action_default_executor_cannot_bypass_exact_hnc_dispatch() -> None:
    bridge = object.__new__(LocalActionBridge)

    result = bridge._default_executor(
        "execute_shell",
        {"command": "echo this-command-must-not-run"},
    )

    assert result["ok"] is False
    assert isinstance(result["result"], dict)
    assert result["result"]["blocked"] is True
    assert "proposal" in result["error"]
