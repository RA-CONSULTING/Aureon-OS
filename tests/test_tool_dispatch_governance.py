from __future__ import annotations

import copy
import json
import threading
from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest

from aureon.inhouse_ai.agent_runner import (
    _MAX_TOOL_ARG_BYTES,
    _MAX_TOOL_CALLS_PER_RESPONSE,
    AgentRunner,
)
from aureon.inhouse_ai.llm_adapter import LLMResponse, StreamChunk, ToolCall
from aureon.inhouse_ai.tool_registry import (
    ToolDispatchAuthorization,
    ToolDispatchProposal,
    ToolEffect,
)
from aureon.operator.tools import GuardedToolRegistry, build_operator_tools

_SCHEMA = {
    "type": "object",
    "properties": {"value": {"type": "string"}},
    "required": ["value"],
    "additionalProperties": False,
}


class _ReceiptVerifier:
    verifier_id = "trusted.test.dual-key-composition.v1"

    def __init__(self, *, accept: bool = True) -> None:
        self.accept = accept
        self.calls = 0

    def validate_tool_dispatch_authorization(
        self,
        *,
        proposal: ToolDispatchProposal,
        authorization: ToolDispatchAuthorization,
    ) -> bool:
        self.calls += 1
        receipt = json.loads(authorization.authority_receipt_json)
        return bool(
            self.accept
            and authorization.authority_receipt_id == "dual-key:test"
            and receipt == {
                "allow": True,
                "proposal_digest": proposal.proposal_digest,
            }
        )


class _NoBoundaryRegistry(GuardedToolRegistry):
    """Exercise GuardedToolRegistry governance without unrelated phrase guards."""

    @staticmethod
    def _guard(name: str, args: dict[str, Any]) -> str | None:
        return None


class _ScriptedAdapter:
    def __init__(self, tool_calls: list[ToolCall]) -> None:
        self.tool_calls = tool_calls
        self.prompt_count = 0
        self.stream_count = 0
        self.message_snapshots: list[list[dict[str, Any]]] = []

    def prompt(self, **kwargs: Any) -> LLMResponse:
        self.prompt_count += 1
        self.message_snapshots.append(copy.deepcopy(kwargs["messages"]))
        if self.prompt_count == 1:
            return LLMResponse(tool_calls=self.tool_calls, stop_reason="tool_use")
        return LLMResponse(text="done", stop_reason="end_turn")

    def stream(self, **kwargs: Any):
        self.stream_count += 1
        self.message_snapshots.append(copy.deepcopy(kwargs["messages"]))
        if self.stream_count == 1:
            for tool_call in self.tool_calls:
                yield StreamChunk(tool_call=tool_call)
            yield StreamChunk(done=True, stop_reason="tool_use")
            return
        yield StreamChunk(text="done")
        yield StreamChunk(done=True, stop_reason="end_turn")


def _make_registry(
    *,
    effect: ToolEffect = ToolEffect.LOCAL_MUTATION,
    verifier: _ReceiptVerifier | None = None,
    governance_required: bool = True,
) -> tuple[_NoBoundaryRegistry, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []
    registry = _NoBoundaryRegistry(
        include_builtins=False,
        governance_required=governance_required,
        authorization_verifier=verifier,
        hnc_coherence_required=False,
    )

    def handler(arguments: dict[str, Any]) -> str:
        calls.append(dict(arguments))
        return json.dumps({"ok": True, "arguments": arguments}, sort_keys=True)

    registry.define_tool(
        "act",
        "Test action",
        _SCHEMA,
        handler,
        effect=effect,
        operation_id="aureon.test.act.v1",
    )
    return registry, calls


def _authorization(
    proposal: ToolDispatchProposal,
    *,
    decision: str = "ACCEPT",
    issuer_id: str = _ReceiptVerifier.verifier_id,
    bound_proposal: ToolDispatchProposal | None = None,
) -> ToolDispatchAuthorization:
    bound = bound_proposal or proposal
    return ToolDispatchAuthorization.issue(
        proposal=bound,
        decision=decision,
        issuer_id=issuer_id,
        authority_receipt_id="dual-key:test",
        authority_receipt={
            "allow": True,
            "proposal_digest": bound.proposal_digest,
        },
    )


def _run_flow(flow: str, runner: AgentRunner) -> list[dict[str, Any]]:
    if flow == "turn":
        assert runner.turn("test") == "done"
    else:
        chunks = list(runner.stream_turn("test"))
        assert chunks[-1].done is True
        assert any(chunk.text == "done" for chunk in chunks)
    tool_results = runner._messages[2]["content"]
    return [json.loads(item["content"]) for item in tool_results]


def test_proposal_and_authorization_are_immutable_and_canonical() -> None:
    verifier = _ReceiptVerifier()
    registry, _calls = _make_registry(verifier=verifier)
    left = registry.build_dispatch_proposal(
        tool_call_id="call-1",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"value": "x", "nested": {"b": 2, "a": 1}},
        context={"z": 2, "a": 1},
    )
    right = registry.build_dispatch_proposal(
        tool_call_id="call-1",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"nested": {"a": 1, "b": 2}, "value": "x"},
        context={"a": 1, "z": 2},
    )
    assert left == right
    assert left.integrity_error() is None
    authorization = _authorization(left)
    assert authorization.integrity_error() is None

    with pytest.raises(FrozenInstanceError):
        left.tool_name = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        authorization.decision = "ABORT"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("case", "expected_reason"),
    [
        ("name", "tool name"),
        ("arguments", "tool arguments"),
        ("effect", "tool effect"),
        ("operation", "tool operation"),
        ("definition", "tool definition"),
        ("proposal_digest", "proposal digest"),
    ],
)
def test_guarded_registry_independently_rebinds_every_exact_field(
    case: str,
    expected_reason: str,
) -> None:
    verifier = _ReceiptVerifier()
    registry, calls = _make_registry(verifier=verifier)
    proposal = registry.build_dispatch_proposal(
        tool_call_id="call-1",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"value": "x"},
    )
    authorization = _authorization(proposal)
    name = "act"
    arguments = {"value": "x"}

    if case == "name":
        registry.define_tool(
            "other",
            "Other action",
            _SCHEMA,
            lambda _args: calls.append({"other": True}) or "other",
            effect=ToolEffect.LOCAL_MUTATION,
            operation_id="aureon.test.other.v1",
        )
        name = "other"
    elif case == "arguments":
        arguments = {"value": "changed"}
    elif case == "effect":
        current = registry.get("act")
        assert current is not None and current.handler is not None
        registry.define_tool(
            "act", current.description, current.input_schema, current.handler,
            effect=ToolEffect.EXTERNAL_MUTATION,
            operation_id=current.operation_id,
        )
    elif case == "operation":
        current = registry.get("act")
        assert current is not None and current.handler is not None
        registry.define_tool(
            "act", current.description, current.input_schema, current.handler,
            effect=current.effect,
            operation_id="aureon.test.changed.v1",
        )
    elif case == "definition":
        current = registry.get("act")
        assert current is not None and current.handler is not None
        registry.define_tool(
            "act", "Changed definition", current.input_schema, current.handler,
            effect=current.effect,
            operation_id=current.operation_id,
        )
    else:
        proposal = replace(proposal, proposal_digest="tool:proposal:" + ("0" * 64))
        authorization = _authorization(proposal)

    result = json.loads(registry.execute(
        name,
        arguments,
        proposal=proposal,
        authorization=authorization,
        governance_required=True,
    ))
    assert result["blocked"] is True
    assert expected_reason in result["reason"]
    assert calls == []
    assert verifier.calls == 0
    assert registry.dispatch_records[-1].handler_called is False


@pytest.mark.parametrize("decision", ["HOLD", "ABORT"])
def test_non_accept_decision_never_calls_handler_or_verifier(decision: str) -> None:
    verifier = _ReceiptVerifier()
    registry, calls = _make_registry(verifier=verifier)
    proposal = registry.build_dispatch_proposal(
        tool_call_id="call-1",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"value": "x"},
    )
    result = json.loads(registry.execute(
        "act",
        {"value": "x"},
        proposal=proposal,
        authorization=_authorization(proposal, decision=decision),
    ))
    assert result["blocked"] is True
    assert calls == []
    assert verifier.calls == 0
    assert registry.dispatch_records[-1].decision == decision


@pytest.mark.parametrize(
    "failure",
    ["missing_verifier", "wrong_issuer", "rejected", "corrupt_digest"],
)
def test_untrusted_authorization_never_calls_handler(failure: str) -> None:
    verifier = _ReceiptVerifier(accept=failure != "rejected")
    registry, calls = _make_registry(
        verifier=None if failure == "missing_verifier" else verifier,
    )
    proposal = registry.build_dispatch_proposal(
        tool_call_id="call-1",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"value": "x"},
    )
    authorization = _authorization(
        proposal,
        issuer_id="untrusted" if failure == "wrong_issuer" else verifier.verifier_id,
    )
    if failure == "corrupt_digest":
        authorization = replace(
            authorization,
            authorization_digest="tool:authorization:" + ("0" * 64),
        )
    result = json.loads(registry.execute(
        "act",
        {"value": "x"},
        proposal=proposal,
        authorization=authorization,
    ))
    assert result["blocked"] is True
    assert calls == []
    assert registry.dispatch_records[-1].handler_called is False


def test_authorization_is_consumed_before_handler_and_cannot_replay() -> None:
    verifier = _ReceiptVerifier()
    registry, calls = _make_registry(verifier=verifier)
    proposal = registry.build_dispatch_proposal(
        tool_call_id="call-1",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"value": "x"},
    )
    authorization = _authorization(proposal)
    first = json.loads(registry.execute(
        "act", {"value": "x"}, proposal=proposal, authorization=authorization,
    ))
    second = json.loads(registry.execute(
        "act", {"value": "x"}, proposal=proposal, authorization=authorization,
    ))
    assert first["ok"] is True
    assert second["blocked"] is True
    assert "already consumed" in second["reason"]
    assert calls == [{"value": "x"}]


def test_verifier_cannot_swap_the_bound_handler_after_authorization() -> None:
    registry, original_calls = _make_registry(verifier=None)
    replacement_calls: list[dict[str, Any]] = []

    class _SwappingVerifier(_ReceiptVerifier):
        def validate_tool_dispatch_authorization(self, **kwargs: Any) -> bool:
            current = registry.get("act")
            assert current is not None
            registry.define_tool(
                "act",
                current.description,
                current.input_schema,
                lambda args: replacement_calls.append(dict(args)) or "replacement",
                effect=current.effect,
                operation_id=current.operation_id,
            )
            return super().validate_tool_dispatch_authorization(**kwargs)

    registry.authorization_verifier = _SwappingVerifier()
    proposal = registry.build_dispatch_proposal(
        tool_call_id="handler-swap",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"value": "original"},
    )

    result = json.loads(registry.execute(
        "act",
        {"value": "original"},
        proposal=proposal,
        authorization=_authorization(proposal),
    ))

    assert result["ok"] is True
    assert original_calls == [{"value": "original"}]
    assert replacement_calls == []


def test_verifier_cannot_mutate_arguments_that_reach_handler() -> None:
    registry, calls = _make_registry(verifier=None)
    caller_arguments = {"value": "original"}

    class _ArgumentMutatingVerifier(_ReceiptVerifier):
        def validate_tool_dispatch_authorization(self, **kwargs: Any) -> bool:
            caller_arguments["value"] = "mutated-after-binding"
            return super().validate_tool_dispatch_authorization(**kwargs)

    registry.authorization_verifier = _ArgumentMutatingVerifier()
    proposal = registry.build_dispatch_proposal(
        tool_call_id="argument-swap",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments=caller_arguments,
    )

    result = json.loads(registry.execute(
        "act",
        caller_arguments,
        proposal=proposal,
        authorization=_authorization(proposal),
    ))

    assert caller_arguments == {"value": "mutated-after-binding"}
    assert result["arguments"] == {"value": "original"}
    assert calls == [{"value": "original"}]


def test_same_authorization_cannot_cross_handler_boundary_concurrently() -> None:
    barrier = threading.Barrier(2)

    class _ConcurrentVerifier(_ReceiptVerifier):
        def validate_tool_dispatch_authorization(self, **kwargs: Any) -> bool:
            accepted = super().validate_tool_dispatch_authorization(**kwargs)
            barrier.wait(timeout=5)
            return accepted

    verifier = _ConcurrentVerifier()
    registry, calls = _make_registry(verifier=verifier)
    proposal = registry.build_dispatch_proposal(
        tool_call_id="concurrent-replay",
        runner_turn_index=1,
        response_call_index=0,
        name="act",
        arguments={"value": "once"},
    )
    authorization = _authorization(proposal)
    results: list[dict[str, Any]] = []

    def _run() -> None:
        results.append(json.loads(registry.execute(
            "act",
            {"value": "once"},
            proposal=proposal,
            authorization=authorization,
        )))

    threads = [threading.Thread(target=_run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert all(not thread.is_alive() for thread in threads)
    assert sum(result.get("ok") is True for result in results) == 1
    assert sum(result.get("blocked") is True for result in results) == 1
    assert calls == [{"value": "once"}]


@pytest.mark.parametrize("flow", ["turn", "stream"])
@pytest.mark.parametrize(
    "failure",
    ["no_supplier", "missing", "hold", "abort", "mismatch", "rejected"],
)
def test_turn_and_stream_fail_closed_with_zero_handler_calls(
    flow: str,
    failure: str,
) -> None:
    verifier = _ReceiptVerifier(accept=failure != "rejected")
    registry, calls = _make_registry(verifier=verifier)
    supplier_calls: list[str] = []

    def authorizer(proposal: ToolDispatchProposal) -> ToolDispatchAuthorization | None:
        supplier_calls.append(proposal.proposal_digest)
        if failure == "missing":
            return None
        if failure in {"hold", "abort"}:
            return _authorization(proposal, decision=failure.upper())
        if failure == "mismatch":
            wrong = replace(proposal, proposal_digest="tool:proposal:" + ("f" * 64))
            return _authorization(proposal, bound_proposal=wrong)
        return _authorization(proposal)

    adapter = _ScriptedAdapter([
        ToolCall(id="call-1", name="act", arguments={"value": "x"}),
    ])
    runner = AgentRunner(
        adapter,
        tools=registry,
        max_turns=2,
        governance_required=True,
        authorize_tool_dispatch=None if failure == "no_supplier" else authorizer,
        dispatch_context_provider=lambda: {"trace_id": "trace-1", "phase": "tool"},
    )
    results = _run_flow(flow, runner)

    assert results[0]["blocked"] is True
    assert calls == []
    assert len(supplier_calls) == (0 if failure == "no_supplier" else 1)
    assert registry.dispatch_records[-1].handler_called is False
    assert runner.get_status()["turn_count"] == 2


@pytest.mark.parametrize("flow", ["turn", "stream"])
def test_turn_and_stream_accept_one_exact_authorized_mutation(flow: str) -> None:
    verifier = _ReceiptVerifier()
    registry, calls = _make_registry(verifier=verifier)
    proposals: list[ToolDispatchProposal] = []

    def authorizer(proposal: ToolDispatchProposal) -> ToolDispatchAuthorization:
        proposals.append(proposal)
        return _authorization(proposal)

    runner = AgentRunner(
        _ScriptedAdapter([
            ToolCall(id="call-1", name="act", arguments={"value": "x"}),
        ]),
        tools=registry,
        max_turns=2,
        governance_required=True,
        authorize_tool_dispatch=authorizer,
        dispatch_context_provider=lambda: {"trace_id": "trace-1", "phase": "tool"},
    )
    results = _run_flow(flow, runner)

    assert results == [{"arguments": {"value": "x"}, "ok": True}]
    assert calls == [{"value": "x"}]
    assert len(proposals) == 1
    assert proposals[0].effect == ToolEffect.LOCAL_MUTATION.value
    assert proposals[0].operation_id == "aureon.test.act.v1"
    assert verifier.calls == 1
    assert registry.dispatch_records[-1].decision == "ACCEPT"
    assert registry.dispatch_records[-1].handler_called is True


@pytest.mark.parametrize("flow", ["turn", "stream"])
def test_read_only_bypass_is_explicitly_recorded_and_skips_supplier(flow: str) -> None:
    registry, calls = _make_registry(effect=ToolEffect.READ_ONLY, verifier=None)
    supplier_calls = 0

    def authorizer(_proposal: ToolDispatchProposal) -> None:
        nonlocal supplier_calls
        supplier_calls += 1

    runner = AgentRunner(
        _ScriptedAdapter([
            ToolCall(id="call-1", name="act", arguments={"value": "x"}),
        ]),
        tools=registry,
        max_turns=2,
        governance_required=True,
        authorize_tool_dispatch=authorizer,
    )
    results = _run_flow(flow, runner)

    assert results[0]["ok"] is True
    assert calls == [{"value": "x"}]
    assert supplier_calls == 0
    record = registry.dispatch_records[-1]
    assert record.decision == "READ_ONLY_BYPASS"
    assert record.authorization_digest.startswith("tool:authorization:")
    assert record.handler_called is True


@pytest.mark.parametrize("flow", ["turn", "stream"])
def test_unknown_effect_fails_closed_without_calling_supplier(flow: str) -> None:
    registry, calls = _make_registry(effect=ToolEffect.UNKNOWN, verifier=_ReceiptVerifier())
    supplier_calls = 0

    def authorizer(_proposal: ToolDispatchProposal) -> None:
        nonlocal supplier_calls
        supplier_calls += 1

    runner = AgentRunner(
        _ScriptedAdapter([
            ToolCall(id="call-1", name="act", arguments={"value": "x"}),
        ]),
        tools=registry,
        max_turns=2,
        governance_required=True,
        authorize_tool_dispatch=authorizer,
    )
    results = _run_flow(flow, runner)

    assert results[0]["blocked"] is True
    assert "effect metadata is unknown" in results[0]["reason"]
    assert calls == []
    assert supplier_calls == 0


@pytest.mark.parametrize("flow", ["turn", "stream"])
def test_bounds_are_identical_for_turn_and_stream(flow: str) -> None:
    registry, calls = _make_registry(effect=ToolEffect.READ_ONLY, verifier=None)
    tool_calls = [
        ToolCall(id=f"call-{index}", name="act", arguments={"value": str(index)})
        for index in range(_MAX_TOOL_CALLS_PER_RESPONSE + 1)
    ]
    runner = AgentRunner(
        _ScriptedAdapter(tool_calls),
        tools=registry,
        max_turns=2,
        governance_required=True,
    )
    results = _run_flow(flow, runner)

    assert len(calls) == _MAX_TOOL_CALLS_PER_RESPONSE
    assert len(results) == _MAX_TOOL_CALLS_PER_RESPONSE + 1
    assert results[-1]["blocked"] is True
    assert "too many tool calls" in results[-1]["reason"]


@pytest.mark.parametrize("flow", ["turn", "stream"])
def test_oversized_argument_is_blocked_before_proposal_or_handler(flow: str) -> None:
    registry, calls = _make_registry(effect=ToolEffect.READ_ONLY, verifier=None)
    runner = AgentRunner(
        _ScriptedAdapter([
            ToolCall(
                id="call-1",
                name="act",
                arguments={"value": "x" * (_MAX_TOOL_ARG_BYTES + 1)},
            ),
        ]),
        tools=registry,
        max_turns=2,
        governance_required=True,
    )
    results = _run_flow(flow, runner)

    assert results[0]["blocked"] is True
    assert "exceeds" in results[0]["reason"]
    assert calls == []
    assert registry.dispatch_records == []


def test_legacy_ungoverned_dispatch_remains_compatible() -> None:
    registry, calls = _make_registry(
        effect=ToolEffect.LOCAL_MUTATION,
        verifier=None,
        governance_required=False,
    )
    runner = AgentRunner(
        _ScriptedAdapter([
            ToolCall(id="call-1", name="act", arguments={"value": "legacy"}),
        ]),
        tools=registry,
        max_turns=2,
        governance_required=False,
    )
    results = _run_flow("turn", runner)
    assert results[0]["ok"] is True
    assert calls == [{"value": "legacy"}]
    assert registry.dispatch_records == []


def test_registry_level_governance_cannot_be_downgraded_by_call() -> None:
    registry, calls = _make_registry(verifier=_ReceiptVerifier(), governance_required=True)
    result = json.loads(registry.execute(
        "act",
        {"value": "x"},
        governance_required=False,
    ))
    assert result["blocked"] is True
    assert "missing or invalid dispatch proposal" in result["reason"]
    assert calls == []


def test_operator_toolbelt_has_no_unknown_effects_and_stable_operations() -> None:
    registry = build_operator_tools(allow_writes=True, allow_shell=True)
    expected_effects = {
        "read_state": ToolEffect.READ_ONLY,
        "read_positions": ToolEffect.READ_ONLY,
        "read_prices": ToolEffect.READ_ONLY,
        "publish_thought": ToolEffect.LOCAL_MUTATION,
        "execute_shell": ToolEffect.PRIVILEGED,
        "web_search": ToolEffect.PRIVILEGED,
        "web_fetch": ToolEffect.PRIVILEGED,
        "repo_search": ToolEffect.READ_ONLY,
        "skill_base_status": ToolEffect.READ_ONLY,
        "read_repo_file": ToolEffect.READ_ONLY,
        "list_repo": ToolEffect.READ_ONLY,
        "sense_organism": ToolEffect.READ_ONLY,
        "list_organism": ToolEffect.READ_ONLY,
        "touch_module": ToolEffect.PRIVILEGED,
        "list_skills": ToolEffect.READ_ONLY,
        "code_validate": ToolEffect.READ_ONLY,
        "write_repo_file": ToolEffect.LOCAL_MUTATION,
        "patch_repo_file": ToolEffect.LOCAL_MUTATION,
    }
    assert set(registry.names()) == set(expected_effects)
    assert {
        name: registry.get(name).effect  # type: ignore[union-attr]
        for name in registry.names()
    } == expected_effects
    operation_ids = [registry.get(name).operation_id for name in registry.names()]  # type: ignore[union-attr]
    assert all(operation_ids)
    assert len(operation_ids) == len(set(operation_ids))
