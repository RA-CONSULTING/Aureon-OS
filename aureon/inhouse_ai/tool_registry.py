"""
Tool Registry — Sovereign Tool System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Central registry for all tools available to in-house agents.
Provides defineTool() for custom tools and ships 5 built-in tools:

  1. read_state       — read dashboard snapshot / system state
  2. read_positions   — read current trading positions + equity
  3. read_prices      — get live prices across all exchanges
  4. publish_thought  — publish a Thought to the ThoughtBus
  5. execute_shell    — run a shell command (sandboxed)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import subprocess
import threading
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Dict, List, Mapping, Protocol

logger = logging.getLogger("aureon.inhouse_ai.tools")


_TOOL_PROPOSAL_SCHEMA = "aureon.tool-dispatch-proposal.v1"
_TOOL_AUTHORIZATION_SCHEMA = "aureon.tool-dispatch-authorization.v1"
_READ_ONLY_BYPASS_ISSUER = "aureon.dispatch.read-only-bypass.v1"


class ToolEffect(StrEnum):
    """Trusted effect classification attached to a registered tool."""

    READ_ONLY = "read_only"
    LOCAL_MUTATION = "local_mutation"
    EXTERNAL_MUTATION = "external_mutation"
    ECONOMIC_MUTATION = "economic_mutation"
    PRIVILEGED = "privileged"
    UNKNOWN = "unknown"


def _validate_json_value(value: Any, *, path: str = "$") -> None:
    """Reject values that do not have one unambiguous JSON representation."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"non-string object key at {path}")
            _validate_json_value(item, path=f"{path}.{key}")
        return
    raise ValueError(f"non-JSON value at {path}: {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    _validate_json_value(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _digest(prefix: str, value: str) -> str:
    return f"{prefix}:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True)
class ToolDispatchProposal:
    """Immutable, exact description of one proposed tool invocation."""

    schema: str
    tool_call_id: str
    runner_turn_index: int
    response_call_index: int
    tool_name: str
    arguments_json: str
    arguments_digest: str
    effect: str
    operation_id: str
    tool_definition_digest: str
    context_json: str
    context_digest: str
    proposal_digest: str

    @classmethod
    def create(
        cls,
        *,
        tool_call_id: str,
        runner_turn_index: int,
        response_call_index: int,
        tool_name: str,
        arguments: Mapping[str, Any],
        effect: ToolEffect,
        operation_id: str,
        tool_definition_digest: str,
        context: Mapping[str, Any] | None = None,
    ) -> ToolDispatchProposal:
        call_id = str(tool_call_id).strip()
        name = str(tool_name).strip()
        operation = str(operation_id).strip()
        if not call_id:
            raise ValueError("tool_call_id is required")
        if not name:
            raise ValueError("tool_name is required")
        if not operation:
            raise ValueError("operation_id is required")
        if runner_turn_index < 0 or response_call_index < 0:
            raise ValueError("dispatch indexes must be non-negative")
        args_json = _canonical_json(dict(arguments))
        ctx_json = _canonical_json(dict(context or {}))
        payload = {
            "schema": _TOOL_PROPOSAL_SCHEMA,
            "tool_call_id": call_id,
            "runner_turn_index": int(runner_turn_index),
            "response_call_index": int(response_call_index),
            "tool_name": name,
            "arguments_json": args_json,
            "arguments_digest": _digest("sha256", args_json),
            "effect": effect.value,
            "operation_id": operation,
            "tool_definition_digest": str(tool_definition_digest),
            "context_json": ctx_json,
            "context_digest": _digest("sha256", ctx_json),
        }
        proposal_json = _canonical_json(payload)
        return cls(
            **payload,
            proposal_digest=_digest("tool:proposal", proposal_json),
        )

    def integrity_error(self) -> str | None:
        if self.schema != _TOOL_PROPOSAL_SCHEMA:
            return "unsupported proposal schema"
        try:
            arguments = json.loads(self.arguments_json)
            context = json.loads(self.context_json)
            if not isinstance(arguments, dict) or not isinstance(context, dict):
                return "proposal arguments and context must be JSON objects"
            if _canonical_json(arguments) != self.arguments_json:
                return "arguments_json is not canonical"
            if _canonical_json(context) != self.context_json:
                return "context_json is not canonical"
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return f"invalid proposal JSON: {exc}"
        if self.arguments_digest != _digest("sha256", self.arguments_json):
            return "arguments digest mismatch"
        if self.context_digest != _digest("sha256", self.context_json):
            return "context digest mismatch"
        payload = {
            "schema": self.schema,
            "tool_call_id": self.tool_call_id,
            "runner_turn_index": self.runner_turn_index,
            "response_call_index": self.response_call_index,
            "tool_name": self.tool_name,
            "arguments_json": self.arguments_json,
            "arguments_digest": self.arguments_digest,
            "effect": self.effect,
            "operation_id": self.operation_id,
            "tool_definition_digest": self.tool_definition_digest,
            "context_json": self.context_json,
            "context_digest": self.context_digest,
        }
        expected = _digest("tool:proposal", _canonical_json(payload))
        if self.proposal_digest != expected:
            return "proposal digest mismatch"
        return None


@dataclass(frozen=True)
class ToolDispatchAuthorization:
    """Immutable authorization envelope; authenticity is checked by a trusted verifier."""

    schema: str
    proposal_digest: str
    decision: str
    issuer_id: str
    authority_receipt_id: str
    authority_receipt_json: str
    authority_receipt_digest: str
    authorization_digest: str

    @classmethod
    def issue(
        cls,
        *,
        proposal: ToolDispatchProposal,
        decision: str,
        issuer_id: str,
        authority_receipt_id: str,
        authority_receipt: Mapping[str, Any],
    ) -> ToolDispatchAuthorization:
        receipt_json = _canonical_json(dict(authority_receipt))
        payload = {
            "schema": _TOOL_AUTHORIZATION_SCHEMA,
            "proposal_digest": proposal.proposal_digest,
            "decision": str(decision).strip().upper(),
            "issuer_id": str(issuer_id).strip(),
            "authority_receipt_id": str(authority_receipt_id).strip(),
            "authority_receipt_json": receipt_json,
            "authority_receipt_digest": _digest("sha256", receipt_json),
        }
        return cls(
            **payload,
            authorization_digest=_digest("tool:authorization", _canonical_json(payload)),
        )

    @classmethod
    def read_only_bypass(cls, proposal: ToolDispatchProposal) -> ToolDispatchAuthorization:
        return cls.issue(
            proposal=proposal,
            decision="READ_ONLY_BYPASS",
            issuer_id=_READ_ONLY_BYPASS_ISSUER,
            authority_receipt_id="",
            authority_receipt={},
        )

    def integrity_error(self) -> str | None:
        if self.schema != _TOOL_AUTHORIZATION_SCHEMA:
            return "unsupported authorization schema"
        try:
            receipt = json.loads(self.authority_receipt_json)
            if not isinstance(receipt, dict):
                return "authority receipt must be a JSON object"
            if _canonical_json(receipt) != self.authority_receipt_json:
                return "authority_receipt_json is not canonical"
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return f"invalid authority receipt JSON: {exc}"
        if self.authority_receipt_digest != _digest("sha256", self.authority_receipt_json):
            return "authority receipt digest mismatch"
        payload = {
            "schema": self.schema,
            "proposal_digest": self.proposal_digest,
            "decision": self.decision,
            "issuer_id": self.issuer_id,
            "authority_receipt_id": self.authority_receipt_id,
            "authority_receipt_json": self.authority_receipt_json,
            "authority_receipt_digest": self.authority_receipt_digest,
        }
        expected = _digest("tool:authorization", _canonical_json(payload))
        if self.authorization_digest != expected:
            return "authorization digest mismatch"
        return None


class ToolAuthorizationVerifier(Protocol):
    """Process-injected trust root for non-read-only dispatch receipts."""

    verifier_id: str

    def validate_tool_dispatch_authorization(
        self,
        *,
        proposal: ToolDispatchProposal,
        authorization: ToolDispatchAuthorization,
    ) -> bool:
        """Return True only for an authentic receipt bound to ``proposal``."""


@dataclass(frozen=True)
class ToolDispatchRecord:
    """Immutable audit fact recorded for every governed dispatch decision."""

    proposal_digest: str
    tool_name: str
    effect: str
    operation_id: str
    decision: str
    authorization_digest: str
    hnc_outcome: str
    hnc_decision_receipt_id: str
    hnc_repair_safe: bool
    handler_called: bool
    reason: str
    result_digest: str


@dataclass
class _HNCContextLease:
    """Revocable request context shared by inherited execution contexts."""

    canonical_field: Any
    active: bool = True

# ─────────────────────────────────────────────────────────────────────────────
# Tool definition
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolDefinition:
    """Schema + handler for a single tool."""

    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=lambda: {
        "type": "object", "properties": {}, "required": []
    })
    handler: Callable[..., str] | None = None
    effect: ToolEffect = ToolEffect.UNKNOWN
    operation_id: str = ""
    hnc_repair_safe: bool = False
    registration_generation: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Export as the wire format agents expect."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @property
    def definition_digest(self) -> str:
        payload = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "effect": self.effect.value,
            "operation_id": self.operation_id,
            "hnc_repair_safe": self.hnc_repair_safe,
            "registration_generation": self.registration_generation,
        }
        return _digest("tool:definition", _canonical_json(payload))


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────


class ToolRegistry:
    """
    Central tool registry.  Agents discover and call tools through this.

    Usage:
        registry = ToolRegistry()
        registry.define_tool("my_tool", "Does something", schema, handler_fn)
        result = registry.execute("my_tool", {"arg": "value"})
    """

    def __init__(
        self,
        include_builtins: bool = True,
        *,
        governance_required: bool = False,
        authorization_verifier: ToolAuthorizationVerifier | None = None,
        hnc_coherence_required: bool = True,
    ):
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_generations: Dict[str, int] = {}
        self._definition_lock = threading.Lock()
        self.governance_required = bool(governance_required)
        self.authorization_verifier = authorization_verifier
        self.dispatch_records: List[ToolDispatchRecord] = []
        self._consumed_authorizations: set[str] = set()
        self._authorization_lock = threading.Lock()
        self._hnc_context: ContextVar[tuple[_HNCContextLease, ...]] = ContextVar(
            f"aureon_hnc_dispatch_context_{id(self)}",
            default=(),
        )
        self._hnc_coherence_required = bool(hnc_coherence_required)
        self.hnc_decisions: List[Dict[str, Any]] = []
        if include_builtins:
            self._register_builtins()

    def define_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable[..., str],
        *,
        effect: ToolEffect | str = ToolEffect.UNKNOWN,
        operation_id: str | None = None,
        hnc_repair_safe: bool = False,
    ) -> ToolDefinition:
        """Register a new tool.  Returns the definition."""
        try:
            normalized_effect = effect if isinstance(effect, ToolEffect) else ToolEffect(str(effect))
        except ValueError as exc:
            raise ValueError(f"invalid effect for tool '{name}': {effect}") from exc
        normalized_operation = str(operation_id or f"aureon.tool.{name}.v1").strip()
        if not normalized_operation:
            raise ValueError(f"operation_id is required for tool '{name}'")
        if not isinstance(hnc_repair_safe, bool):
            raise TypeError(f"hnc_repair_safe must be bool for tool '{name}'")
        with self._definition_lock:
            generation = self._tool_generations.get(name, 0) + 1
            td = ToolDefinition(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=handler,
                effect=normalized_effect,
                operation_id=normalized_operation,
                hnc_repair_safe=hnc_repair_safe,
                registration_generation=generation,
            )
            self._tool_generations[name] = generation
            self._tools[name] = td
        logger.debug("Tool registered: %s", name)
        return td

    def set_hnc_coherence_context(
        self,
        canonical_field: Any,
    ) -> _HNCContextLease:
        """Install one request-scoped canonical HNC moment for dispatch.

        The context is local to the current execution context, so concurrent
        cognition turns sharing a registry cannot overwrite one another's HNC
        moment.  There is intentionally no per-call flag that can downgrade a
        required context.
        """

        from aureon.core.hnc_field import CanonicalField

        if canonical_field is None:
            canonical_field = CanonicalField()
        if not isinstance(canonical_field, CanonicalField):
            raise TypeError("captured_canonical_field_required")
        self.require_hnc_coherence()
        lease = _HNCContextLease(canonical_field=canonical_field)
        self._hnc_context.set((*self._hnc_context.get(), lease))
        return lease

    def require_hnc_coherence(self) -> None:
        """Permanently enable HNC enforcement for this registry instance."""

        self._hnc_coherence_required = True

    @property
    def hnc_coherence_required(self) -> bool:
        return self._hnc_coherence_required

    @property
    def hnc_context_active(self) -> bool:
        stack = self._hnc_context.get()
        return bool(stack and stack[-1].active)

    def clear_hnc_coherence_context(self) -> None:
        stack = self._hnc_context.get()
        if not stack:
            return
        # Revocation is shared with asyncio tasks that inherited this exact
        # lease object.  A child cannot continue using a high-HNC snapshot
        # after the parent request has ended.
        stack[-1].active = False
        self._hnc_context.set(stack[:-1])

    def _evaluate_hnc_dispatch(
        self,
        proposal: ToolDispatchProposal,
    ) -> Dict[str, Any] | None:
        stack = self._hnc_context.get()
        lease = stack[-1] if stack else None
        if self._hnc_coherence_required is not True:
            return None
        from aureon.core.hnc_field import CanonicalField
        from aureon.governance.cognition_gate import (
            build_hnc_coherence_request,
            evaluate_hnc_coherence,
        )

        request = build_hnc_coherence_request(
            proposal_digest=proposal.proposal_digest,
            effect=proposal.effect,
            operation_id=proposal.operation_id,
        )
        decision = evaluate_hnc_coherence(
            request,
            canonical_field=(
                lease.canonical_field
                if isinstance(lease, _HNCContextLease) and lease.active is True
                else CanonicalField()
            ),
        )
        self.hnc_decisions.append(dict(decision))
        if len(self.hnc_decisions) > 2048:
            del self.hnc_decisions[:-2048]
        return decision

    def preauthorize_tool_dispatch(self, proposal: ToolDispatchProposal) -> bool:
        """Evaluate HNC before any mutation-authority supplier is called.

        This preflight prevents low-coherence proposals from acquiring route
        authority.  :meth:`execute` deliberately re-evaluates the captured field
        at the handler boundary so a slow authority supplier cannot launder a
        stale decision.  A missing/revoked context fails closed.
        """

        if self._hnc_coherence_required is not True:
            return True
        if not isinstance(proposal, ToolDispatchProposal):
            return False
        try:
            arguments = json.loads(proposal.arguments_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
        if not isinstance(arguments, dict):
            return False
        definition = self._tools.get(proposal.tool_name)
        if self._dispatch_binding_error(
            proposal.tool_name,
            arguments,
            proposal,
            definition=definition,
        ):
            return False
        decision = self._evaluate_hnc_dispatch(proposal)
        if decision is None:
            return False
        outcome = str(decision.get("outcome") or "HOLD").upper()
        return bool(
            outcome == "PROCEED"
            or (
                outcome == "REPAIR"
                and definition is not None
                and definition.effect == ToolEffect.READ_ONLY
                and definition.hnc_repair_safe is True
            )
        )

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def build_dispatch_proposal(
        self,
        *,
        tool_call_id: str,
        runner_turn_index: int,
        response_call_index: int,
        name: str,
        arguments: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> ToolDispatchProposal:
        """Freeze the registered definition and exact arguments into one proposal."""
        td = self._tools.get(name)
        if td is None:
            td = ToolDefinition(
                name=name,
                description="",
                input_schema={},
                effect=ToolEffect.UNKNOWN,
                operation_id=f"aureon.tool.{name or 'unknown'}.unregistered.v1",
            )
        return ToolDispatchProposal.create(
            tool_call_id=tool_call_id,
            runner_turn_index=runner_turn_index,
            response_call_index=response_call_index,
            tool_name=name,
            arguments=arguments,
            effect=td.effect,
            operation_id=td.operation_id,
            tool_definition_digest=td.definition_digest,
            context=context,
        )

    def _dispatch_binding_error(
        self,
        name: str,
        arguments: Mapping[str, Any],
        proposal: ToolDispatchProposal | None,
        *,
        definition: ToolDefinition | None = None,
    ) -> str | None:
        if not isinstance(proposal, ToolDispatchProposal):
            return "missing or invalid dispatch proposal"
        integrity_error = proposal.integrity_error()
        if integrity_error:
            return integrity_error
        if proposal.tool_name != name:
            return "tool name does not match proposal"
        try:
            arguments_json = _canonical_json(dict(arguments))
        except (TypeError, ValueError) as exc:
            return f"arguments are not canonical JSON: {exc}"
        if arguments_json != proposal.arguments_json:
            return "tool arguments do not match proposal"
        td = definition if definition is not None else self._tools.get(name)
        if td is None:
            return f"unknown tool: {name}"
        if proposal.effect != td.effect.value:
            return "tool effect does not match proposal"
        if proposal.operation_id != td.operation_id:
            return "tool operation does not match proposal"
        try:
            definition_digest = td.definition_digest
        except (TypeError, ValueError) as exc:
            return f"tool definition is not canonical JSON: {exc}"
        if proposal.tool_definition_digest != definition_digest:
            return "tool definition does not match proposal"
        return None

    def _record_dispatch(
        self,
        *,
        proposal: ToolDispatchProposal | None,
        name: str,
        decision: str,
        authorization: ToolDispatchAuthorization | None,
        handler_called: bool,
        reason: str,
        result: str,
        hnc_decision: Mapping[str, Any] | None = None,
        hnc_repair_safe: bool = False,
    ) -> None:
        self.dispatch_records.append(ToolDispatchRecord(
            proposal_digest=proposal.proposal_digest if proposal else "",
            tool_name=name,
            effect=proposal.effect if proposal else ToolEffect.UNKNOWN.value,
            operation_id=proposal.operation_id if proposal else "",
            decision=decision,
            authorization_digest=(
                authorization.authorization_digest
                if isinstance(authorization, ToolDispatchAuthorization)
                else ""
            ),
            hnc_outcome=str((hnc_decision or {}).get("outcome") or ""),
            hnc_decision_receipt_id=str(
                (hnc_decision or {}).get("receipt_id") or ""
            ),
            hnc_repair_safe=hnc_repair_safe is True,
            handler_called=handler_called,
            reason=reason,
            result_digest=_digest("sha256", result),
        ))

    def _blocked_governed_dispatch(
        self,
        *,
        name: str,
        proposal: ToolDispatchProposal | None,
        authorization: ToolDispatchAuthorization | None,
        reason: str,
        decision: str = "HOLD",
        hnc_decision: Mapping[str, Any] | None = None,
        hnc_repair_safe: bool = False,
    ) -> str:
        result = json.dumps({
            "blocked": True,
            "reason": f"governance: {reason}",
            "tool": name,
            "proposal_digest": proposal.proposal_digest if proposal else "",
        })
        self._record_dispatch(
            proposal=proposal,
            name=name,
            decision=decision,
            authorization=authorization,
            handler_called=False,
            reason=reason,
            result=result,
            hnc_decision=hnc_decision,
            hnc_repair_safe=hnc_repair_safe,
        )
        return result

    def _invoke_handler(
        self,
        name: str,
        arguments: Dict[str, Any],
        *,
        definition: ToolDefinition | None = None,
    ) -> str:
        td = definition if definition is not None else self._tools.get(name)
        if not td:
            return json.dumps({"error": f"Unknown tool: {name}"})
        if not td.handler:
            return json.dumps({"error": f"Tool '{name}' has no handler"})
        try:
            return td.handler(arguments)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return json.dumps({"error": f"Tool execution failed: {e}"})

    def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        *,
        proposal: ToolDispatchProposal | None = None,
        authorization: ToolDispatchAuthorization | None = None,
        governance_required: bool | None = None,
    ) -> str:
        """Execute a tool, failing closed when this call or registry is governed."""
        governed = (
            self.governance_required
            or bool(governance_required)
            or self._hnc_coherence_required
        )
        if not governed:
            return self._invoke_handler(name, arguments)

        # Freeze the exact registered handler before any gate or verifier is
        # called.  A same-name re-registration during authorization cannot swap
        # the code that will run for this proposal.
        bound_definition = self._tools.get(name)
        binding_error = self._dispatch_binding_error(
            name,
            arguments,
            proposal,
            definition=bound_definition,
        )
        if binding_error:
            return self._blocked_governed_dispatch(
                name=name,
                proposal=proposal,
                authorization=authorization,
                reason=binding_error,
            )
        assert proposal is not None
        try:
            bound_arguments = json.loads(proposal.arguments_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            return self._blocked_governed_dispatch(
                name=name,
                proposal=proposal,
                authorization=authorization,
                reason="proposal arguments are not valid canonical JSON",
            )
        if not isinstance(bound_arguments, dict):
            return self._blocked_governed_dispatch(
                name=name,
                proposal=proposal,
                authorization=authorization,
                reason="proposal arguments must be an object",
            )

        if proposal.effect == ToolEffect.UNKNOWN.value:
            return self._blocked_governed_dispatch(
                name=name,
                proposal=proposal,
                authorization=authorization,
                reason="tool effect metadata is unknown",
            )

        hnc_decision: Dict[str, Any] | None = None
        repair_safe = False
        try:
            hnc_decision = self._evaluate_hnc_dispatch(proposal)
        except Exception as exc:  # noqa: BLE001 - a gate failure must hold
            logger.warning("HNC coherence dispatch evaluation failed: %s", exc)
            return self._blocked_governed_dispatch(
                name=name,
                proposal=proposal,
                authorization=authorization,
                reason="HNC coherence decision unavailable",
                decision="HOLD",
                hnc_decision=hnc_decision,
            )
        if hnc_decision is not None:
            outcome = str(hnc_decision.get("outcome") or "HOLD").upper()
            definition = bound_definition
            repair_safe = bool(
                outcome == "REPAIR"
                and definition is not None
                and definition.effect == ToolEffect.READ_ONLY
                and definition.hnc_repair_safe
            )
            if outcome != "PROCEED" and not repair_safe:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason=(
                        f"HNC coherence {outcome}: "
                        f"{hnc_decision.get('reason') or 'coherent route required'}"
                    ),
                    decision=outcome,
                    hnc_decision=hnc_decision,
                )

        if proposal.effect == ToolEffect.READ_ONLY.value:
            if authorization is None:
                authorization = ToolDispatchAuthorization.read_only_bypass(proposal)
            auth_error = (
                authorization.integrity_error()
                if isinstance(authorization, ToolDispatchAuthorization)
                else "invalid read-only bypass authorization"
            )
            if auth_error:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=(
                        authorization
                        if isinstance(authorization, ToolDispatchAuthorization)
                        else None
                    ),
                    reason=auth_error,
                    hnc_decision=hnc_decision,
                    hnc_repair_safe=repair_safe,
                )
            if (
                authorization.decision != "READ_ONLY_BYPASS"
                or authorization.issuer_id != _READ_ONLY_BYPASS_ISSUER
                or authorization.proposal_digest != proposal.proposal_digest
                or authorization.authority_receipt_id
                or authorization.authority_receipt_json != "{}"
            ):
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason="invalid read-only bypass binding",
                    hnc_decision=hnc_decision,
                    hnc_repair_safe=repair_safe,
                )
        else:
            if not isinstance(authorization, ToolDispatchAuthorization):
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=None,
                    reason="missing dispatch authorization",
                    hnc_decision=hnc_decision,
                )
            auth_error = authorization.integrity_error()
            if auth_error:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason=auth_error,
                    hnc_decision=hnc_decision,
                )
            if authorization.proposal_digest != proposal.proposal_digest:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason="authorization does not match proposal",
                    hnc_decision=hnc_decision,
                )
            if authorization.decision != "ACCEPT":
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason=f"authorization decision is {authorization.decision or 'missing'}",
                    decision=authorization.decision or "HOLD",
                    hnc_decision=hnc_decision,
                )
            verifier = self.authorization_verifier
            if verifier is None:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason="trusted authorization verifier is unavailable",
                    hnc_decision=hnc_decision,
                )
            verifier_id = str(getattr(verifier, "verifier_id", "")).strip()
            if not verifier_id or authorization.issuer_id != verifier_id:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason="authorization issuer does not match trusted verifier",
                    hnc_decision=hnc_decision,
                )
            try:
                verified = verifier.validate_tool_dispatch_authorization(
                    proposal=proposal,
                    authorization=authorization,
                )
            except Exception as exc:  # noqa: BLE001 - verifier failure must hold
                logger.warning("tool authorization verifier failed: %s", exc)
                verified = False
            if verified is not True:
                return self._blocked_governed_dispatch(
                    name=name,
                    proposal=proposal,
                    authorization=authorization,
                    reason="trusted authorization verifier rejected receipt",
                    hnc_decision=hnc_decision,
                )
            # Check and burn atomically. Concurrent calls sharing one receipt can
            # never both cross the handler boundary.
            with self._authorization_lock:
                if authorization.authorization_digest in self._consumed_authorizations:
                    return self._blocked_governed_dispatch(
                        name=name,
                        proposal=proposal,
                        authorization=authorization,
                        reason="dispatch authorization was already consumed",
                        hnc_decision=hnc_decision,
                    )
                # Consume immediately before the handler. A failed handler never
                # makes an authority-bearing receipt reusable.
                self._consumed_authorizations.add(authorization.authorization_digest)

        result = self._invoke_handler(
            name,
            bound_arguments,
            definition=bound_definition,
        )
        self._record_dispatch(
            proposal=proposal,
            name=name,
            decision=authorization.decision,
            authorization=authorization,
            handler_called=True,
            reason="",
            result=result,
            hnc_decision=hnc_decision,
            hnc_repair_safe=repair_safe,
        )
        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """Return all tool definitions in wire format."""
        return [td.to_dict() for td in self._tools.values()]

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    # ─────────────────────────────────────────────────────────────────────────
    # Built-in tools
    # ─────────────────────────────────────────────────────────────────────────

    def _register_builtins(self):
        """Register the 5 built-in tools."""

        # 1. read_state
        self.define_tool(
            name="read_state",
            description="Read the current system state from the dashboard snapshot. Returns exchange status, session stats, flight check results, and systems registry.",
            input_schema={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "string",
                        "description": "Comma-separated keys to read (e.g. 'session_stats,exchange_status') or 'all'",
                    },
                },
                "required": ["keys"],
                "additionalProperties": False,
            },
            handler=_builtin_read_state,
            effect=ToolEffect.READ_ONLY,
            operation_id="aureon.inhouse.read_state.v1",
            hnc_repair_safe=True,
        )

        # 2. read_positions
        self.define_tool(
            name="read_positions",
            description="Read current open trading positions and equity across all exchanges.",
            input_schema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "description": "Filter by exchange: binance|alpaca|kraken|all",
                    },
                },
                "required": ["exchange"],
                "additionalProperties": False,
            },
            handler=_builtin_read_positions,
            effect=ToolEffect.READ_ONLY,
            operation_id="aureon.inhouse.read_positions.v1",
        )

        # 3. read_prices
        self.define_tool(
            name="read_prices",
            description="Get live prices for tracked symbols across all exchanges.",
            input_schema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "string",
                        "description": "Comma-separated symbols (e.g. 'BTCUSDT,ETHUSDT') or 'all'",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Return top N symbols by activity (default 20)",
                    },
                },
                "required": ["symbols"],
                "additionalProperties": False,
            },
            handler=_builtin_read_prices,
            effect=ToolEffect.READ_ONLY,
            operation_id="aureon.inhouse.read_prices.v1",
        )

        # 4. publish_thought
        self.define_tool(
            name="publish_thought",
            description="Publish a Thought to the ThoughtBus for other system components to consume.",
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "ThoughtBus topic (e.g. 'agent.signal', 'agent.analysis')",
                    },
                    "payload": {
                        "type": "string",
                        "description": "JSON-encoded payload to publish",
                    },
                    "source": {
                        "type": "string",
                        "description": "Source identifier (agent name)",
                    },
                },
                "required": ["topic", "payload", "source"],
                "additionalProperties": False,
            },
            handler=_builtin_publish_thought,
            effect=ToolEffect.LOCAL_MUTATION,
            operation_id="aureon.inhouse.publish_thought.v1",
        )

        # 5. execute_shell
        self.define_tool(
            name="execute_shell",
            description="Execute a shell command and return its output. Sandboxed to safe read-only commands.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute (read-only commands only)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 30, max 60)",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            handler=_builtin_execute_shell,
            effect=ToolEffect.PRIVILEGED,
            operation_id="aureon.inhouse.execute_shell.v1",
        )

        self.define_tool(
            name="web_search",
            description="Search the web through AureonAgentCore and return bounded results for learning (privileged outbound network I/O).",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query."},
                    "num_results": {"type": "integer", "description": "Maximum result count, default 5, max 10."},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=_builtin_web_search,
            effect=ToolEffect.PRIVILEGED,
            operation_id="aureon.inhouse.web_search.v1",
        )

        self.define_tool(
            name="web_fetch",
            description="Fetch a public web page through AureonAgentCore and return bounded text for learning (privileged outbound network I/O).",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch."},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
            handler=_builtin_web_fetch,
            effect=ToolEffect.PRIVILEGED,
            operation_id="aureon.inhouse.web_fetch.v1",
        )

        self.define_tool(
            name="repo_search",
            description="Search local repository text without modifying files.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Case-insensitive regex/text pattern."},
                    "directory": {"type": "string", "description": "Relative directory, default repo root."},
                    "limit": {"type": "integer", "description": "Maximum hits, default 25, max 100."},
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
            handler=_builtin_repo_search,
            effect=ToolEffect.READ_ONLY,
            operation_id="aureon.inhouse.repo_search.v1",
        )

        self.define_tool(
            name="skill_base_status",
            description="Read Aureon's latest coding-agent skill-base manifest.",
            input_schema={
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "description": "summary|full, default summary."},
                },
                "required": [],
                "additionalProperties": False,
            },
            handler=_builtin_skill_base_status,
            effect=ToolEffect.READ_ONLY,
            operation_id="aureon.inhouse.skill_base_status.v1",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Built-in tool handlers
# ─────────────────────────────────────────────────────────────────────────────


def _load_snapshot() -> Dict[str, Any]:
    """Load the latest dashboard snapshot."""
    state_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "wisdom", "state")
    path = os.path.join(state_dir, "dashboard_snapshot.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        # Try repo root state dir
        alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "state", "dashboard_snapshot.json")
        try:
            with open(alt) as f:
                return json.load(f)
        except Exception:
            return {}


def _builtin_read_state(args: Dict[str, Any]) -> str:
    snap = _load_snapshot()
    keys_str = args.get("keys", "all")

    if keys_str == "all":
        return json.dumps({
            "timestamp": snap.get("timestamp"),
            "session_stats": snap.get("session_stats", {}),
            "exchange_status": snap.get("exchange_status", {}),
            "systems_registry": snap.get("systems_registry", {}),
            "flight_check": snap.get("flight_check", {}),
        }, indent=2)

    keys = [k.strip() for k in keys_str.split(",")]
    result = {}
    for k in keys:
        result[k] = snap.get(k, None)
    return json.dumps(result, indent=2)


def _builtin_read_positions(args: Dict[str, Any]) -> str:
    snap = _load_snapshot()
    exchange = args.get("exchange", "all")
    positions = snap.get("positions", [])
    equity = snap.get("queen_equity")

    if exchange != "all" and isinstance(positions, list):
        positions = [p for p in positions if isinstance(p, dict) and p.get("exchange", "").lower() == exchange.lower()]

    return json.dumps({
        "positions": positions,
        "active_count": len(positions) if isinstance(positions, list) else 0,
        "queen_equity": equity,
        "exchange_filter": exchange,
    }, indent=2)


def _builtin_read_prices(args: Dict[str, Any]) -> str:
    snap = _load_snapshot()
    prices: Dict[str, float] = {}
    for key in ("binance_prices", "alpaca_prices", "kraken_prices"):
        raw = snap.get(key, {})
        if isinstance(raw, dict):
            for sym, val in raw.items():
                if sym not in prices and val:
                    try:
                        prices[sym] = float(val)
                    except (TypeError, ValueError):
                        pass

    symbols_str = args.get("symbols", "all")
    top_n = int(args.get("top_n", 20))

    if symbols_str != "all":
        wanted = {s.strip().upper() for s in symbols_str.split(",")}
        prices = {k: v for k, v in prices.items() if k.upper() in wanted}

    # Limit to top_n
    items = list(prices.items())[:top_n]
    return json.dumps({
        "total_tracked": len(prices),
        "prices": dict(items),
        "returned": len(items),
    }, indent=2)


def _builtin_publish_thought(args: Dict[str, Any]) -> str:
    topic = args.get("topic", "agent.signal")
    payload_str = args.get("payload", "{}")
    source = args.get("source", "inhouse_agent")

    try:
        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
    except json.JSONDecodeError:
        payload = {"raw": payload_str}

    try:
        from aureon.core.aureon_thought_bus import Thought, ThoughtBus
        bus = ThoughtBus()
        bus.publish(Thought(source=source, topic=topic, payload=payload))
        return json.dumps({"status": "published", "topic": topic, "source": source})
    except Exception as e:
        return json.dumps({"status": "failed", "error": str(e), "topic": topic})


def _builtin_execute_shell(args: Dict[str, Any]) -> str:
    command = args.get("command", "")
    timeout = min(int(args.get("timeout", 30)), 60)

    # Sandbox: block destructive commands
    blocked = ["rm ", "del ", "format ", "mkfs", "dd ", "shutdown", "reboot", "> /dev/", ":(){ ", "fork"]
    cmd_lower = command.lower()
    for b in blocked:
        if b in cmd_lower:
            return json.dumps({"error": f"Blocked: command contains '{b.strip()}'"})

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return json.dumps({
            "stdout": result.stdout[:4096],
            "stderr": result.stderr[:1024],
            "returncode": result.returncode,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Command timed out after {timeout}s"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _builtin_web_search(args: Dict[str, Any]) -> str:
    query = str(args.get("query", "")).strip()
    num_results = max(1, min(int(args.get("num_results", 5) or 5), 10))
    if not query:
        return json.dumps({"error": "query is required"})
    try:
        from aureon.autonomous.aureon_agent_core import AureonAgentCore

        agent = AureonAgentCore()
        return json.dumps({"query": query, "results": agent.web_search(query, num_results=num_results)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "query": query})


def _builtin_web_fetch(args: Dict[str, Any]) -> str:
    url = str(args.get("url", "")).strip()
    if not url:
        return json.dumps({"error": "url is required"})
    if not (url.startswith("https://") or url.startswith("http://")):
        return json.dumps({"error": "Only http(s) URLs are allowed", "url": url})
    try:
        from aureon.autonomous.aureon_agent_core import AureonAgentCore

        agent = AureonAgentCore()
        fetched = agent.web_fetch(url)
        text = str(fetched.get("text") or "")
        if text:
            fetched["text"] = text[:6000]
        return json.dumps(fetched, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "url": url})


def _repo_root() -> str:
    current = os.path.abspath(os.getcwd())
    candidates = [current]
    parent = current
    while True:
        next_parent = os.path.dirname(parent)
        if next_parent == parent:
            break
        candidates.append(next_parent)
        parent = next_parent
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    candidates.append(here)
    for candidate in candidates:
        if os.path.isdir(os.path.join(candidate, "aureon")) and os.path.isdir(os.path.join(candidate, "scripts")):
            return candidate
    return here


# Files whose PATH marks them as secret material. repo_search returns matching source lines
# verbatim, so without this filter a pattern like "API_KEY=" hands back live credentials in
# plaintext — the instance's .env is exactly where set_exchange_credential writes exchange keys.
# Directory pruning alone never covered it: dotfiles at the repo root are walked like any other.
_SECRET_FILE_RE = re.compile(
    r"(^|/)\.env|(^|/)id_rsa|\.pem$|\.key$|(^|/)provider_keys|"
    r"(^|/)secrets?\.(json|ya?ml|toml|ini|txt)$|(^|/)credentials?(\.|$)",
    re.IGNORECASE,
)


def _builtin_repo_search(args: Dict[str, Any]) -> str:
    pattern = str(args.get("pattern", "")).strip()
    directory = str(args.get("directory", ".") or ".").strip()
    limit = max(1, min(int(args.get("limit", 25) or 25), 100))
    if not pattern:
        return json.dumps({"error": "pattern is required"})
    root = os.path.abspath(_repo_root())
    base = os.path.abspath(os.path.join(root, directory))
    if not (base == root or base.startswith(root + os.sep)):
        return json.dumps({"error": "directory must stay inside repo", "directory": directory})
    ignored = {".git", ".venv", "__pycache__", "node_modules", "dist", "build", "queen_backups"}
    hits = []
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)
    for walk_root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ignored]
        for filename in files:
            if len(hits) >= limit:
                break
            path = os.path.join(walk_root, filename)
            rel = os.path.relpath(path, root).replace("\\", "/")
            if _SECRET_FILE_RE.search(rel):
                continue          # never echo secret material back as a search hit
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for line_no, line in enumerate(fh, start=1):
                        if regex.search(line):
                            hits.append(
                                {
                                    "path": os.path.relpath(path, root).replace("\\", "/"),
                                    "line": line_no,
                                    "text": line.strip()[:240],
                                }
                            )
                            break
            except Exception:
                continue
        if len(hits) >= limit:
            break
    return json.dumps({"pattern": pattern, "directory": directory, "hit_count": len(hits), "hits": hits}, indent=2)


def _builtin_skill_base_status(args: Dict[str, Any]) -> str:
    detail = str(args.get("detail", "summary") or "summary").lower()
    root = _repo_root()
    path = os.path.join(root, "state", "aureon_coding_agent_skill_base_last_run.json")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except Exception as e:
        return json.dumps({"status": "missing", "error": str(e), "path": path})
    if detail == "full":
        return json.dumps(data, indent=2)[:12000]
    return json.dumps(
        {
            "status": data.get("status"),
            "generated_at": data.get("generated_at"),
            "summary": data.get("summary"),
            "coding_work_orders": data.get("coding_work_orders", [])[:8],
        },
        indent=2,
    )
