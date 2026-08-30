"""
🧠 AUREON COGNITION — the agentic mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Ground it in the repo, reach for tools, answer anything — then let the
conscience have the last word."

Where :class:`AureonOperator` fans one question across many models and collapses
them, :class:`AureonCognition` is the single-mind agentic mode: it grounds the
prompt in the whole repo, runs a tool-using loop (write code, search online,
read the repo, check trading state), and answers any domain — particle physics,
cosmology, the meaning of life, dealing with depression, baking a cake.

It is composition of parts that already exist:
  ground   →  repo-wide index (aureon/operator/repo_index) + relaxed persona
  loop     →  AgentRunner + a guarded ToolRegistry (aureon/operator/tools)
  veto     →  hard authority boundary + QueenConscience (aureon_operator)
  fabric   →  thought bus (operator.cognition.*) + mycelium broadcast, one trace_id

Every consequential tool call is vetted BEFORE it runs (GuardedToolRegistry), and
the whole turn is bounded by the same offline/audit guards as the rest of Aureon.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any, Dict, Generator, List

try:
    from aureon.core.aureon_baton_link import link_system as _baton_link

    _baton_link(__name__)
except Exception:  # noqa: BLE001
    pass

from aureon.governance.cognition_gate import (
    TrustedCouncilReceiptSupplier,
    TrustedCrownReceiptSupplier,
    build_cognition_governance_request,
    build_hnc_coherence_request,
    evaluate_cognition_governance,
    evaluate_hnc_coherence,
    explicit_disabled_governance,
)
from aureon.governance.dual_key import DUAL_KEY_SCHEMA
from aureon.governance.tool_route_authority import (
    LEASE_PREFIX,
    ToolRouteAuthorityRequest,
    TrustedToolRouteAuthoritySupplier,
    build_tool_route_authority_request,
    validate_tool_route_authority_lease,
)
from aureon.inhouse_ai.agent_runner import AgentRunner
from aureon.inhouse_ai.llm_adapter import LLMAdapter
from aureon.inhouse_ai.tool_registry import (
    ToolDispatchAuthorization,
    ToolDispatchProposal,
)
from aureon.operator.aureon_operator import (
    _OPERATOR_PERSONA,
    _hard_boundary_violation,
    broadcast_to_mesh,
    join_organism,
)
from aureon.operator.config import OperatorConfig
from aureon.operator.providers import build_provider_set
from aureon.operator.repo_index import REPO_ROOT, repo_search
from aureon.operator.schemas import CognitionResult, GroundingContext, ToolInvocation
from aureon.operator.tools import build_operator_tools

logger = logging.getLogger("aureon.operator.cognition")

try:
    from aureon.core.aureon_thought_bus import (
        Thought,
        get_thought_bus,
        payload_of,
        topic_of,
    )

    _HAS_BUS = True
except Exception:  # noqa: BLE001
    get_thought_bus = None  # type: ignore
    Thought = None  # type: ignore
    payload_of = None  # type: ignore
    topic_of = None  # type: ignore
    _HAS_BUS = False

# Grounding gate. A keyword index over 2000+ files gives even off-repo prompts a
# non-trivial TF-IDF sum (common English vocabulary is everywhere), so a single
# absolute floor can't separate "Aureon operator correlation" (155) from "healthy
# ways to deal with stress" (87). We use a hybrid gate instead:
#   ground  IF  top_score >= _MID_FLOOR AND the prompt names an Aureon-domain term
# Otherwise the prompt is treated as general-domain: answer from general knowledge,
# no repo citation. (A semantic/embedding index would sharpen this; documented as
# a keyword-index heuristic.)
_HIGH_FLOOR = 90.0
_MID_FLOOR = 30.0
_SNIPPET_FLOOR = 30.0
_DOMAIN_TERMS = frozenset((
    "aureon", "hnc", "harmonic", "queen", "operator", "mycelium", "nexus", "phi",
    "schumann", "lambda", "auris", "seer", "lighthouse", "stargate", "ghost",
    "coherence", "sero", "leckey", "ziggurat", "kelly", "veto", "conscience",
    "trade", "trading", "market", "bot", "exchange", "kraken", "binance", "alpaca",
    "repo", "repository", "correlation", "node", "master formula", "falsification",
))


def _has_domain_term(prompt: str) -> bool:
    low = prompt.lower()
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", low)
        for term in _DOMAIN_TERMS
    )


_QA_PATH = REPO_ROOT / "data" / "datasets" / "aureon_qa_dataset.json"
_TOOL_HINT = (
    "\n\nYou can call tools when they help: repo_search (search the whole Aureon "
    "repo), read_repo_file, list_repo, web_search, web_fetch, code_validate, "
    "write_repo_file, patch_repo_file, read_state/read_positions/read_prices. "
    "Prefer repo_search to ground Aureon-specific claims."
)
_BAKE_CHARTER = (
    "\n\nDeliver the FULLY BAKED result: a complete, self-contained answer/plan/"
    "code/report — never a stub or partial trace. Use ALL knowledge available "
    "to you: the grounded repo packets when relevant (cite them), tools when "
    "they help, and your general model knowledge otherwise — and state plainly "
    "which of those the answer rests on."
)

_GOVERNANCE_FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "action_gate_passed",
    "actionable",
    "operational_eligible",
    "provider_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)


def _governance_hold(reason: str) -> Dict[str, Any]:
    """Numeric-free HOLD evidence; never a fabricated governance receipt."""

    return {
        "schema": DUAL_KEY_SCHEMA,
        "receipt_type": "druid_queen_dual_key",
        "receipt_id": None,
        "decision": "HOLD",
        "reason": reason,
        "data_status": "no_data",
        "truth_status": "no_data",
        "freshness_status": "no_data",
        "equation_inputs_complete": False,
        "generated_values": False,
        "input_receipt_ids": [],
        "rune_voices": [],
        "lineage_alignment": "unavailable",
        "harmonic_outcome": "HOLD",
        "route_authorization_required": True,
        **dict.fromkeys(_GOVERNANCE_FALSE_FLAGS, False),
    }


def _sha256_json(value: Any) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _CognitionDispatchVerifier:
    """Registry trust root for one exact, mandate-backed route lease."""

    verifier_id = "aureon.cognition.dual-key-dispatch-verifier.v1"

    def __init__(self) -> None:
        self._expected: Dict[str, Dict[str, Any]] = {}
        self._consumed_route_leases: set[str] = set()
        self._lock = threading.RLock()

    def register(
        self,
        proposal: ToolDispatchProposal,
        request: ToolRouteAuthorityRequest,
        route_lease: Mapping[str, Any],
        supplier_id: str,
    ) -> None:
        with self._lock:
            self._expected[proposal.proposal_digest] = {
                "request": request,
                "supplier_id": supplier_id,
                "route_lease_id": str(route_lease.get("receipt_id") or ""),
            }

    def discard(self, proposal_digest: str) -> None:
        with self._lock:
            self._expected.pop(proposal_digest, None)

    def validate_tool_dispatch_authorization(
        self,
        *,
        proposal: ToolDispatchProposal,
        authorization: ToolDispatchAuthorization,
    ) -> bool:
        with self._lock:
            expected = self._expected.pop(proposal.proposal_digest, None)
        if expected is None:
            return False
        try:
            receipt = json.loads(authorization.authority_receipt_json)
            validated = validate_tool_route_authority_lease(
                receipt,
                request=expected["request"],
                expected_supplier_id=expected["supplier_id"],
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
        route_lease_id = str(validated.get("receipt_id") or "")
        valid = bool(
            authorization.issuer_id == self.verifier_id
            and authorization.proposal_digest == proposal.proposal_digest
            and authorization.authority_receipt_id == route_lease_id
            and route_lease_id == expected["route_lease_id"]
            and validated.get("decision") == "AUTHORIZE"
        )
        if not valid:
            return False
        with self._lock:
            if route_lease_id in self._consumed_route_leases:
                return False
            self._consumed_route_leases.add(route_lease_id)
        return True


class AureonCognition:
    """Single-mind agentic cognition: ground → tool-loop → veto, fully traced."""

    def __init__(
        self,
        adapter: LLMAdapter | None = None,
        *,
        tools=None,
        bus: Any = None,
        conscience: Any = None,
        config: OperatorConfig | None = None,
        allow_writes: bool = True,
        allow_shell: bool = True,
        max_turns: int = 6,
        join_mesh: bool = True,
        mesh_broadcast: bool = True,
        source: str = "aureon.cognition",
        prefer_local: bool | None = None,
        allow_repo_grounding: bool = True,
        allow_organism_context: bool = True,
        council_receipt_supplier: TrustedCouncilReceiptSupplier | None = None,
        crown_receipt_supplier: TrustedCrownReceiptSupplier | None = None,
        governance_acquisition: Mapping[str, Any] | None = None,
        governance_acquisition_supplier: Callable[[], Mapping[str, Any]] | None = None,
        governance_enabled: bool = True,
        route_authority_supplier: TrustedToolRouteAuthoritySupplier | None = None,
        trusted_route_authority_supplier_ids: frozenset[str] | None = None,
    ) -> None:
        # ``join_mesh`` governs INBOUND mesh membership only. Outbound broadcasts are separate and
        # default on, so nothing changes for the instance engine; a per-tenant engine passes
        # ``mesh_broadcast=False`` so a user's turn never radiates onto the shared mycelium (the
        # verdict quotes the action, i.e. their prompt).
        self._mesh_broadcast = bool(mesh_broadcast)
        self.config = config or OperatorConfig.from_env()
        if prefer_local is None:
            prefer_local = str(os.environ.get("AUREON_COGNITION_PREFER_LOCAL", "") or "").strip().lower() in {"1", "true", "yes", "on"}
        self.adapter = adapter or self._default_adapter(prefer_local=prefer_local)
        self._governance_enabled = bool(governance_enabled)
        if (
            self._governance_enabled
            and council_receipt_supplier is None
            and crown_receipt_supplier is None
            and governance_acquisition is None
            and governance_acquisition_supplier is None
        ):
            try:
                from aureon.core.organism_composition import (
                    get_canonical_organism_composition,
                )

                composition = get_canonical_organism_composition()
                if composition is not None:
                    composition_kwargs = composition.cognition_kwargs()
                    council_receipt_supplier = composition_kwargs.get(
                        "council_receipt_supplier"
                    )
                    crown_receipt_supplier = composition_kwargs.get(
                        "crown_receipt_supplier"
                    )
                    governance_acquisition_supplier = composition_kwargs.get(
                        "governance_acquisition_supplier"
                    )
            except Exception as exc:  # noqa: BLE001 - incomplete root stays fail-closed
                logger.debug("canonical organism composition unavailable: %s", exc)
        self._council_receipt_supplier = council_receipt_supplier
        self._crown_receipt_supplier = crown_receipt_supplier
        if (route_authority_supplier is None) is not (
            trusted_route_authority_supplier_ids is None
        ):
            raise ValueError(
                "route_authority_supplier_and_frozen_allowlist_required_together"
            )
        self._route_authority_supplier = None
        self._route_authority_supplier_id: str | None = None
        self._trusted_route_authority_supplier_ids: frozenset[str] = frozenset()
        if route_authority_supplier is not None:
            if not isinstance(
                route_authority_supplier,
                TrustedToolRouteAuthoritySupplier,
            ):
                raise TypeError("trusted_tool_route_authority_supplier_required")
            if not isinstance(trusted_route_authority_supplier_ids, frozenset):
                raise TypeError("frozen_route_authority_supplier_allowlist_required")
            allowed_ids = frozenset(
                str(value).strip()
                for value in trusted_route_authority_supplier_ids
                if isinstance(value, str) and value.strip()
            )
            supplier_id = str(route_authority_supplier.supplier_id).strip()
            if not supplier_id or supplier_id not in allowed_ids:
                raise ValueError("allowlisted_route_authority_supplier_required")
            independent_objects = {
                id(value)
                for value in (council_receipt_supplier, crown_receipt_supplier)
                if value is not None
            }
            authority_ids = {
                str(getattr(value, "supplier_id", "")).strip().casefold()
                for value in (council_receipt_supplier, crown_receipt_supplier)
                if value is not None
            }
            if (
                id(route_authority_supplier) in independent_objects
                or supplier_id.casefold() in authority_ids
            ):
                raise ValueError("independent_route_authority_supplier_required")
            self._route_authority_supplier = route_authority_supplier
            self._route_authority_supplier_id = supplier_id
            self._trusted_route_authority_supplier_ids = allowed_ids
        if governance_acquisition is not None and governance_acquisition_supplier is not None:
            raise ValueError(
                "static_and_request_scoped_governance_acquisition_are_mutually_exclusive"
            )
        if governance_acquisition is not None and not isinstance(
            governance_acquisition, Mapping
        ):
            raise TypeError("governance_acquisition must be a mapping")
        if governance_acquisition_supplier is not None and not callable(
            governance_acquisition_supplier
        ):
            raise TypeError("governance_acquisition_supplier must be callable")
        self._governance_acquisition = (
            dict(governance_acquisition) if governance_acquisition is not None else None
        )
        self._governance_acquisition_supplier = governance_acquisition_supplier
        self._dispatch_verifier = _CognitionDispatchVerifier()
        # `is not None`, NOT `or`: ToolRegistry defines __len__, so a registry deliberately pruned to
        # zero tools is FALSY, and `tools or build_operator_tools(...)` would silently hand back the
        # FULL instance toolbelt — the exact opposite of what an empty allowlist asks for. That fails
        # open on the tenant plane, inverting the allowlist guarantee.
        self.tools = tools if tools is not None else build_operator_tools(
            allow_writes=allow_writes,
            allow_shell=allow_shell,
            governance_required=True,
            authorization_verifier=self._dispatch_verifier,
        )
        try:
            self.tools.governance_required = True
            self.tools.authorization_verifier = self._dispatch_verifier
            if not callable(getattr(self.tools, "set_hnc_coherence_context", None)):
                raise TypeError("missing HNC coherence context support")
            if not callable(getattr(self.tools, "clear_hnc_coherence_context", None)):
                raise TypeError("missing HNC coherence context cleanup support")
            if not callable(getattr(self.tools, "require_hnc_coherence", None)):
                raise TypeError("missing mandatory HNC coherence support")
            if not callable(getattr(self.tools, "preauthorize_tool_dispatch", None)):
                raise TypeError("missing HNC dispatch pre-authorization support")
            self.tools.require_hnc_coherence()
        except Exception as exc:  # noqa: BLE001 - a non-governable toolbelt must not run
            raise TypeError(
                "an HNC- and governance-capable tool registry is required"
            ) from exc
        self.max_turns = max_turns
        self.source = source
        self._allow_repo_grounding = bool(allow_repo_grounding)
        self._allow_organism_context = bool(allow_organism_context)
        self._conscience = conscience
        self._conscience_loaded = conscience is not None
        self.last_mesh_message: Dict[str, Any] = {}
        # Live cache of the organism's shared state — the field, the cosmic gate,
        # lighthouse clearance, body coverage — so cognition reasons organism-aware
        # (mirrors what GroundedActionGate does for actions).
        self._organism: Dict[str, Any] = {}
        if bus is not None:
            self.bus = bus
        elif _HAS_BUS and get_thought_bus is not None:
            self.bus = get_thought_bus()
        else:
            self.bus = None
        if self.bus is not None:
            for _topic in ("symbolic.life.pulse", "auris.throne.cosmic_state",
                           "lighthouse.event", "organism.connectome.pulse"):
                try:
                    self.bus.subscribe(_topic, self._on_organism)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("organism subscribe skipped (%s): %s", _topic, exc)
        if join_mesh:
            join_organism(self, "aureon_cognition")

    @staticmethod
    def _default_adapter(prefer_local: bool = False) -> LLMAdapter:
        providers = build_provider_set()
        # Ollama-first: when prefer_local is set (the local-machine reasoning
        # path), the local/ollama line reasons even if cloud keys are present.
        if prefer_local:
            for key, val in providers.items():
                if "local" in key.lower() or "ollama" in key.lower():
                    return val
        # Otherwise a single primary line for the agentic loop (first available).
        return next(iter(providers.values()))

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def reason(self, prompt: str, session_id: str | None = None) -> CognitionResult:
        """Run one turn and always clear its request-scoped HNC moment."""

        try:
            return self._reason(prompt, session_id=session_id)
        finally:
            self.tools.clear_hnc_coherence_context()

    def _reason(self, prompt: str, session_id: str | None = None) -> CognitionResult:
        started = time.time()
        res = CognitionResult(trace_id=uuid.uuid4().hex, prompt=prompt,
                              submitted_at=started, session_id=session_id)
        self._publish(res, "boot", {"prompt": prompt, "tools": self.tools.names()})

        self._route(prompt, res)
        self._gate_aperture(res)
        system_prompt = self._ground(prompt, res)
        system_prompt += self._coherence_system_instruction(prompt, res)
        self._run_loop(
            prompt,
            system_prompt,
            res,
            phase="draft",
            observer_prompt=prompt,
        )
        self._acquire(prompt, system_prompt, res)
        self._bake(prompt, system_prompt, res)
        self._veto(prompt, res)
        self._govern_final_answer(prompt, res)
        self._actualize(res)
        self._assimilate(res)
        self._heart(res)

        res.elapsed_ms = (time.time() - started) * 1000.0
        self._publish(res, "complete", res.to_dict())
        if self._mesh_broadcast:
            broadcast_to_mesh("cognition.answer", {"trace_id": res.trace_id, "grounded": res.grounded,
                                                   "verdict": res.conscience_verdict, "blocked": res.blocked})
        return res

    def stream_events(self, prompt: str, session_id: str | None = None) -> Generator[Dict[str, Any], None, None]:
        res = self.reason(prompt, session_id=session_id)
        yield {"type": "grounding", "detail": res.grounding.to_dict() if res.grounding else {}}
        for t in res.tool_calls:
            yield {"type": "tool", "detail": t.to_dict()}
        yield {"type": "veto", "detail": {"verdict": res.conscience_verdict, "blocked": res.blocked}}
        for word in (res.text or "").split(" "):
            yield {"type": "token", "text": word + " "}
        yield {"type": "complete", "response": res.to_dict()}

    # ------------------------------------------------------------------
    # Route (the universal prompt router: classify, council the complex)
    # ------------------------------------------------------------------

    def _route(self, prompt: str, res: CognitionResult) -> None:
        """Classify the prompt against the goal-capability map; a prompt
        spanning ≥2 capability families convenes a deterministic swarm
        routing council. Advisory only — a routing failure is a recorded
        error, never a broken answer."""
        try:
            from aureon.operator.prompt_router import classify_prompt, swarm_council

            res.capability = classify_prompt(prompt)
            if res.capability.get("complex"):
                res.swarm = swarm_council(prompt, res.capability["families"])
            self._publish(res, "route", {"capability": res.capability,
                                         "council_convened": res.swarm is not None})
        except Exception as exc:  # noqa: BLE001 — routing must never break answering
            logger.debug("prompt routing failed: %s", exc)
            res.errors.append({"phase": "route", "error": str(exc)})

    # ------------------------------------------------------------------
    # Ground
    # ------------------------------------------------------------------

    def _ground(self, prompt: str, res: CognitionResult) -> str:
        sources: List[Dict[str, str]] = []
        blocks: List[str] = []
        if self._allow_repo_grounding:
            try:
                # the pattern buffer runs deep: more candidate packets, each carrying
                # its own measured relevance score into the envelope (never invented)
                hits = repo_search(prompt, top_k=8)
                top = hits[0].score if hits else 0.0
                is_grounded = top >= _MID_FLOOR and _has_domain_term(prompt)
                if is_grounded:
                    for s in hits:
                        if s.score < _SNIPPET_FLOOR:
                            continue
                        sources.append({"title": s.doc_id, "path": s.doc_id,
                                        "score": f"{s.score:.1f}"})
                        blocks.append(f"[{s.doc_id}] {s.text[:400]}")
            except Exception as exc:  # noqa: BLE001
                logger.debug("repo grounding failed: %s", exc)
                res.errors.append({"phase": "ground", "error": str(exc)})

            qa = self._life_questions_snippet(prompt)
            if qa:
                blocks.append(f"[aureon_qa_dataset] {qa}")

        system = _OPERATOR_PERSONA
        if not self._allow_repo_grounding:
            system += (
                "\n\nThis is an isolated tenant model plane. No instance repository, "
                "research corpus, operator memory, or organism state is available to it. "
                "Do not claim or infer access to those sources."
            )
        if blocks:
            system += "\n\nGrounded Aureon context (cite when relevant):\n" + "\n\n".join(blocks)[:4000]

        # Organism awareness — the shared field the whole body senses. Let the
        # model reason with the current coherence / cosmic gate / lighthouse.
        org = self._read_organism_state()
        if org:
            bits = []
            if org.get("symbolic_life_score") is not None:
                bits.append(f"symbolic_life_score={float(org['symbolic_life_score']):.3f}")
            if org.get("coherence_gamma") is not None:
                bits.append(f"coherence_gamma={float(org['coherence_gamma']):.3f}")
            if org.get("advisory"):
                bits.append(f"cosmic_advisory={org['advisory']}")
            if org.get("gate_open") is not None:
                bits.append(f"cosmic_gate={'open' if org['gate_open'] else 'closed'}")
            if org.get("lighthouse_event"):
                bits.append(f"lighthouse={org['lighthouse_event']}")
            # Whole-body consensus: the blend of every producer's field, plus how
            # much they disagree (high divergence → the organism is of two minds).
            try:
                from aureon.core.hnc_field import blend_field

                blended = blend_field(self.bus)
                if (blended.available and blended.contributors > 1
                        and blended.symbolic_life_score is not None):
                    bits.append(f"blended_sls={blended.symbolic_life_score:.3f}"
                                f"(n={blended.contributors})")
                    if blended.divergence is not None:
                        bits.append(f"field_divergence={blended.divergence:.3f}")
            except Exception as exc:  # noqa: BLE001
                logger.debug("blend read skipped: %s", exc)
            if bits:
                system += ("\n\nOrganism state (the shared HNC field you are part of): "
                           + ", ".join(bits))

        # Council specialist notes: a complex ask spans capability families —
        # the map's OWN reasons/instruments ride into grounding so the final
        # answer covers every family's aspect, not only the lead's.
        cap = res.capability or {}
        if cap.get("complex") and res.swarm is not None:
            by_route = {r.get("route"): r for r in cap.get("routes", [])}
            lines = []
            for fam in res.swarm.get("families", []):  # type: ignore[union-attr]
                r = by_route.get(fam, {})
                note = f"- {fam}: {r.get('reason', 'named by the capability map')}"
                systems = list(r.get("systems", []))[:4]
                if systems:
                    note += f" (instruments: {', '.join(systems)})"
                lines.append(note)
            if lines:
                system += (
                    "\n\nRouting council (measured, deterministic): lead family "
                    f"{res.swarm.get('lead')}. This ask spans several capability "  # type: ignore[union-attr]
                    "families — address EVERY family's aspect in the final "
                    "answer:\n" + "\n".join(lines))

        system += _TOOL_HINT
        system += _BAKE_CHARTER

        res.grounded = bool(sources)
        res.grounding = GroundingContext(sources=sources, lane="cognition",
                                         task_family="general", system_prompt_chars=len(system))
        self._publish(res, "ground", res.grounding.to_dict())
        return system

    @staticmethod
    def _life_questions_snippet(prompt: str) -> str:
        """Best-effort match against the 106 universal-life-questions dataset."""
        try:
            data = json.loads(_QA_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return ""
        answers = data.get("answers") or []
        toks = {w for w in prompt.lower().split() if len(w) > 3}
        best, best_score = None, 0
        for item in answers:
            q = str(item.get("question", "")).lower()
            score = sum(1 for t in toks if t in q)
            if score > best_score:
                best, best_score = item, score
        if best and best_score >= 2:
            return f"Q: {best.get('question','')}\nAureon: {str(best.get('answer',''))[:500]}"
        return ""

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------

    def _governance_acquisition_for(self, res: CognitionResult) -> Dict[str, Any]:
        if self._governance_acquisition_supplier is not None:
            try:
                supplied = self._governance_acquisition_supplier()
                if not isinstance(supplied, Mapping):
                    raise TypeError(
                        "governance_acquisition_supplier_must_return_mapping"
                    )
                acquisition = dict(supplied)
            except Exception as exc:  # noqa: BLE001 - bad evidence must HOLD, not crash
                logger.debug("governance acquisition unavailable: %s", exc)
                acquisition = {}
        else:
            acquisition = dict(self._governance_acquisition or {})
        acquisition["knowledge_acquisition"] = dict(res.acquisition or {})
        return acquisition

    @staticmethod
    def _proposal_material(proposal: ToolDispatchProposal) -> Dict[str, Any]:
        return {
            "schema": proposal.schema,
            "tool_call_id": proposal.tool_call_id,
            "runner_turn_index": proposal.runner_turn_index,
            "response_call_index": proposal.response_call_index,
            "tool_name": proposal.tool_name,
            "arguments_json": proposal.arguments_json,
            "arguments_digest": proposal.arguments_digest,
            "effect": proposal.effect,
            "operation_id": proposal.operation_id,
            "tool_definition_digest": proposal.tool_definition_digest,
            "context_json": proposal.context_json,
            "context_digest": proposal.context_digest,
            "proposal_digest": proposal.proposal_digest,
        }

    def _queen_voice(
        self,
        action: str,
        context: Mapping[str, Any],
    ) -> tuple[str, str, bool, Dict[str, Any]]:
        conscience = self._get_conscience()
        if conscience is None:
            return (
                "UNAVAILABLE",
                "QueenConscience is unavailable",
                False,
                {"available": False, "evaluated": False},
            )
        try:
            whisper = conscience.ask_why(action, dict(context))
            verdict = str(
                getattr(
                    getattr(whisper, "verdict", ""),
                    "name",
                    getattr(whisper, "verdict", ""),
                )
            ).strip().upper()
            message = str(getattr(whisper, "message", "") or "")
            if verdict not in {"APPROVED", "CONCERNED", "TEACHING_MOMENT", "VETO"}:
                return (
                    "UNAVAILABLE",
                    "QueenConscience returned an unrecognized verdict",
                    False,
                    {"available": True, "evaluated": False},
                )
            source = (
                f"{conscience.__class__.__module__}."
                f"{conscience.__class__.__qualname__}"
            )
            return (
                verdict,
                message,
                True,
                {
                    "available": True,
                    "evaluated": True,
                    "verdict_source_id": source,
                    "action_digest": hashlib.sha256(
                        action.encode("utf-8")
                    ).hexdigest(),
                    "context_digest": _sha256_json(dict(context)),
                    "message_digest": hashlib.sha256(
                        message.encode("utf-8")
                    ).hexdigest(),
                },
            )
        except Exception as exc:  # noqa: BLE001 - an unavailable Queen must hold
            logger.debug("conscience unavailable: %s", exc)
            return (
                "UNAVAILABLE",
                "QueenConscience evaluation failed",
                False,
                {
                    "available": True,
                    "evaluated": False,
                    "error_type": type(exc).__name__,
                },
            )

    def _authorize_tool_dispatch(
        self,
        proposal: ToolDispatchProposal,
        *,
        observer_prompt: str,
        phase: str,
        res: CognitionResult,
    ) -> tuple[ToolDispatchAuthorization | None, Dict[str, Any]]:
        if not self._governance_enabled:
            return None, _governance_hold(
                "mutation_dispatch_requires_enabled_governance"
            )
        proposal_material = self._proposal_material(proposal)
        tool_ledger = [item.to_dict() for item in res.tool_calls]
        dispatch_bake = {
            "phase": phase,
            "dispatch_proposal": proposal_material,
            "tool_ledger": tool_ledger,
            "tool_ledger_digest": _sha256_json(tool_ledger),
        }
        queen_context = {
            "trace_id": res.trace_id,
            "phase": phase,
            "tool_name": proposal.tool_name,
            "effect": proposal.effect,
            "operation_id": proposal.operation_id,
            "tool_proposal_digest": proposal.proposal_digest,
            "tool_ledger_digest": dispatch_bake["tool_ledger_digest"],
        }
        verdict, _message, evaluated, _evidence = self._queen_voice(
            f"authorize exact tool dispatch: {proposal.operation_id}",
            queen_context,
        )
        if not evaluated:
            return None, _governance_hold("evaluated_queen_voice_required")
        answer = json.dumps(
            proposal_material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        acquisition = self._governance_acquisition_for(res)
        governance_request = build_cognition_governance_request(
            prompt=observer_prompt,
            answer=answer,
            tool_calls=res.tool_calls,
            capability=res.capability,
            bake=dispatch_bake,
            acquisition=acquisition,
            queen_verdict=verdict,
        )
        gate = evaluate_cognition_governance(
            prompt=observer_prompt,
            answer=answer,
            tool_calls=res.tool_calls,
            capability=res.capability,
            bake=dispatch_bake,
            acquisition=acquisition,
            queen_verdict=verdict,
            queen_evaluated=evaluated,
            council_receipt_supplier=self._council_receipt_supplier,
            crown_receipt_supplier=self._crown_receipt_supplier,
        )
        gate_decision = str(gate.get("decision") or "HOLD").upper()
        if gate_decision != "ACCEPT" or not gate.get("receipt_id"):
            if gate_decision in {"HOLD", "ABORT"}:
                return (
                    ToolDispatchAuthorization.issue(
                        proposal=proposal,
                        decision=gate_decision,
                        issuer_id=self._dispatch_verifier.verifier_id,
                        authority_receipt_id=str(gate.get("receipt_id") or ""),
                        authority_receipt=gate,
                    ),
                    gate,
                )
            return None, gate
        supplier = self._route_authority_supplier
        supplier_id = str(getattr(supplier, "supplier_id", "")).strip()
        if (
            supplier is None
            or supplier_id != self._route_authority_supplier_id
            or supplier_id not in self._trusted_route_authority_supplier_ids
        ):
            return None, gate
        try:
            route_request = build_tool_route_authority_request(
                proposal,
                gate,
                expected_governance_proposal_digest=(
                    governance_request.proposal_digest
                ),
            )
            raw_route_lease = supplier.supply_tool_route_authority(route_request)
            route_lease = validate_tool_route_authority_lease(
                raw_route_lease,
                request=route_request,
                expected_supplier_id=supplier_id,
            )
        except Exception as exc:  # noqa: BLE001 - route authority failure holds
            logger.warning("exact tool route authority unavailable: %s", exc)
            return None, gate
        self._dispatch_verifier.register(
            proposal,
            route_request,
            route_lease,
            supplier_id,
        )
        try:
            authorization = ToolDispatchAuthorization.issue(
                proposal=proposal,
                decision="ACCEPT",
                issuer_id=self._dispatch_verifier.verifier_id,
                authority_receipt_id=str(route_lease["receipt_id"]),
                authority_receipt=route_lease,
            )
        except Exception:
            self._dispatch_verifier.discard(proposal.proposal_digest)
            raise
        return authorization, gate

    def _run_loop(
        self,
        prompt: str,
        system_prompt: str,
        res: CognitionResult,
        *,
        phase: str,
        observer_prompt: str,
    ) -> None:
        pending: List[ToolInvocation] = []
        dispatch_gates: Dict[str, Dict[str, Any]] = {}

        def _dispatch_context() -> Dict[str, Any]:
            ledger = [item.to_dict() for item in res.tool_calls]
            return {
                "trace_id": res.trace_id,
                "phase": phase,
                "observer_prompt_digest": hashlib.sha256(
                    observer_prompt.encode("utf-8")
                ).hexdigest(),
                "active_prompt_digest": hashlib.sha256(
                    prompt.encode("utf-8")
                ).hexdigest(),
                "tool_ledger_digest": _sha256_json(ledger),
            }

        def _authorize(
            proposal: ToolDispatchProposal,
        ) -> ToolDispatchAuthorization | None:
            try:
                authorization, gate = self._authorize_tool_dispatch(
                    proposal,
                    observer_prompt=observer_prompt,
                    phase=phase,
                    res=res,
                )
            except Exception as exc:  # noqa: BLE001 - authorizer failure holds
                logger.warning("cognition tool governance failed: %s", exc)
                authorization = None
                gate = _governance_hold("tool_governance_unavailable")
            dispatch_gates[proposal.proposal_digest] = gate
            return authorization

        runner = AgentRunner(
            self.adapter,
            tools=self.tools,
            system_prompt=system_prompt,
            max_turns=self.max_turns,
            governance_required=True,
            authorize_tool_dispatch=_authorize,
            dispatch_context_provider=_dispatch_context,
        )

        def _on_tool_call(name: str, args: Dict[str, Any]) -> None:
            definition = self.tools.get(name)
            invocation = ToolInvocation(
                tool=name,
                arguments=dict(args or {}),
                phase=phase,
                effect=(definition.effect.value if definition is not None else "unknown"),
                operation_id=(definition.operation_id if definition is not None else ""),
            )
            res.tool_calls.append(invocation)
            pending.append(invocation)
            self._publish(res, "tool", {"tool": name, "arguments": args})
            if self._mesh_broadcast:
                broadcast_to_mesh("cognition.tool", {"trace_id": res.trace_id, "tool": name})

        runner.on_tool_call = _on_tool_call

        def _on_tool_result(
            proposal: ToolDispatchProposal | None,
            authorization: ToolDispatchAuthorization | None,
            result: str,
        ) -> None:
            invocation = pending.pop(0) if pending else None
            if invocation is None:
                return
            if proposal is not None:
                invocation.proposal_digest = proposal.proposal_digest
                invocation.effect = proposal.effect
                invocation.operation_id = proposal.operation_id
            if authorization is not None:
                invocation.authorization_digest = authorization.authorization_digest
                if (
                    authorization.decision == "ACCEPT"
                    and authorization.authority_receipt_id.startswith(LEASE_PREFIX)
                ):
                    invocation.route_authority_receipt_id = (
                        authorization.authority_receipt_id
                    )
                    try:
                        route_receipt = json.loads(
                            authorization.authority_receipt_json
                        )
                    except (TypeError, json.JSONDecodeError):
                        route_receipt = None
                    if isinstance(route_receipt, dict):
                        invocation.route_authority_receipt = route_receipt
                        invocation.route_authority_request_digest = str(
                            route_receipt.get("request_digest") or ""
                        ) or None
            record = next(
                (
                    item
                    for item in reversed(getattr(self.tools, "dispatch_records", []))
                    if proposal is not None
                    and item.proposal_digest == proposal.proposal_digest
                ),
                None,
            )
            if record is not None:
                invocation.governance_decision = record.decision
                invocation.governance_reason = record.reason
                invocation.hnc_outcome = record.hnc_outcome
                invocation.hnc_decision_receipt_id = (
                    record.hnc_decision_receipt_id or None
                )
                invocation.hnc_repair_safe = record.hnc_repair_safe
                invocation.handler_called = record.handler_called
                invocation.result_digest = record.result_digest
                invocation.blocked = not record.handler_called
                if not record.handler_called and proposal is not None:
                    self._dispatch_verifier.discard(proposal.proposal_digest)
            else:
                invocation.blocked = True
                invocation.result_digest = hashlib.sha256(
                    result.encode("utf-8")
                ).hexdigest()
            if proposal is not None:
                gate = dispatch_gates.pop(proposal.proposal_digest, None)
                if gate is not None:
                    invocation.dual_key_receipt_id = gate.get("receipt_id") or None
                    invocation.dual_key_receipt = dict(gate)
                    invocation.governance_receipt_id = invocation.dual_key_receipt_id
                if gate is not None and not invocation.governance_decision:
                    invocation.governance_decision = str(gate.get("decision") or "HOLD")
                if gate is not None and not invocation.governance_reason:
                    invocation.governance_reason = str(gate.get("reason") or "")
            try:
                payload = json.loads(result)
            except (TypeError, json.JSONDecodeError):
                payload = {}
            if isinstance(payload, Mapping) and payload.get("blocked") is True:
                invocation.blocked = True

        runner.on_tool_result = _on_tool_result
        try:
            text = runner.turn(prompt)
        except Exception as exc:  # noqa: BLE001 — a loop failure must not crash cognition
            logger.warning("agentic loop failed: %s", exc)
            res.errors.append({"phase": "loop", "error": str(exc)})
            text = f"[cognition error] {exc}"

        res.text = (text or "").strip()
        res.turns += getattr(runner, "_turn_count", 0)   # accumulates across bake passes
        self._publish(res, "loop", {"turns": res.turns, "n_tools": len(res.tool_calls)})

    # ------------------------------------------------------------------
    # Gate (one canonical HNC decision; legacy aperture is telemetry only)
    # ------------------------------------------------------------------

    def _gate_aperture(self, res: CognitionResult) -> None:
        """Capture one HNC moment and bind it to every tool in this turn.

        The historical aperture remains visible for diagnostics, but it no
        longer authorizes or refuses work.  The hash-bound HNC decision in
        ``cognition_gate`` is the single dispatch policy.
        """
        try:
            from aureon.core.hnc_field import CanonicalField, read_canonical_field
            from aureon.operator.coherence_gate import compute_aperture

            org = self._read_organism_state()
            gamma = org.get("coherence_gamma")
            gate = compute_aperture(
                float(gamma) if isinstance(gamma, (int, float)) else None,
                org.get("gate_open"),
                org.get("lighthouse_severity"),
            )
            if not self._allow_organism_context:
                # Per-tenant cognition is intentionally isolated from the host
                # organism.  Never let ``read_canonical_field`` fall back to the
                # host's persisted trace for an isolated request.
                field = CanonicalField()
            else:
                try:
                    field = read_canonical_field(self.bus)
                except Exception as exc:  # noqa: BLE001 - missing evidence enters repair
                    logger.debug("canonical HNC capture unavailable: %s", exc)
                    field = CanonicalField()
            request = build_hnc_coherence_request(
                proposal_digest=(
                    "sha256:" + hashlib.sha256(res.prompt.encode("utf-8")).hexdigest()
                ),
                effect="read_only",
                operation_id="aureon.operator.cognition.reason.v1",
            )
            decision = evaluate_hnc_coherence(
                request,
                canonical_field=field,
            )
            self.tools.set_hnc_coherence_context(field)
            if hasattr(self.tools, "aperture_allowed"):
                self.tools.aperture_allowed = None
                self.tools.aperture_note = "legacy aperture is telemetry-only"
            res.coherence_gate = {
                **gate,
                "authority": "hnc_coherence_decision",
                "legacy_aperture_authoritative": False,
                "hnc_decision": decision,
            }
            self._publish(res, "gate", res.coherence_gate)
        except Exception as exc:  # noqa: BLE001 - gate failure still allows repair reasoning
            logger.warning("HNC coherence gate unavailable: %s", exc)
            self.tools.set_hnc_coherence_context(None)
            res.coherence_gate = {
                "authority": "hnc_coherence_decision",
                "legacy_aperture_authoritative": False,
                "hnc_decision": {
                    "outcome": "REPAIR",
                    "reason": "hnc_coherence_gate_unavailable",
                    "receipt_id": None,
                    "route_authorization_required": True,
                },
            }
            self._publish(res, "gate", res.coherence_gate)

    @staticmethod
    def _coherence_system_instruction(prompt: str, res: CognitionResult) -> str:
        decision = (res.coherence_gate or {}).get("hnc_decision") or {}
        outcome = str(decision.get("outcome") or "REPAIR").upper()
        reason = str(decision.get("reason") or "fresh HNC evidence unavailable")
        if outcome == "PROCEED":
            mode = (
                "HNC outcome PROCEED: continue the reasoning flow. This is "
                "evidence-only and does not replace exact route authorization."
            )
        else:
            mode = (
                f"HNC outcome {outcome}: work in repair/observation mode ({reason}). "
                "Diagnose, explain, and prepare exact next steps; do not claim an "
                "effect occurred. Only explicitly repair-safe introspection tools "
                "may be available."
            )
        if _hard_boundary_violation(prompt):
            mode += (
                " The prompt names a consequential effect. You may reason about and "
                "prepare its typed intent, but generic shell/write/publish tools are "
                "not an execution route. Execution requires a current, authenticated, "
                "scope-bound authority envelope and its one-use provider receipt."
            )
        return "\n\nUnified HNC coherence instruction: " + mode

    # ------------------------------------------------------------------
    # Acquire (the Borg loop: find what is missing, never invent it)
    # ------------------------------------------------------------------

    def _acquire(self, prompt: str, system_prompt: str, res: CognitionResult) -> None:
        """When the draft names a knowledge gap, run exactly ONE acquisition
        pass directing the agent at its tools — repo, skills, web, live
        state. The outcome is measured from the tool ledger (acquired /
        unavailable / declined), never self-reported. An honest offline
        reply is not an acquisition case — its status already says it all."""
        try:
            from aureon.operator.acquisition import (
                acquisition_outcome,
                acquisition_prompt,
                find_gaps,
            )
        except Exception as exc:  # noqa: BLE001 — a dark module never breaks answering
            logger.debug("acquisition module unavailable: %s", exc)
            return
        if res.blocked or res.status() != "ok":
            return
        gaps = find_gaps(prompt, res)
        if not gaps:
            res.acquisition = {"triggered": False, "gaps": [],
                               "outcome": "not_needed"}
            return
        self._publish(res, "acquire", {"gaps": gaps})
        tools_before = len(res.tool_calls)
        self._run_loop(acquisition_prompt(prompt, res.text, gaps),
                       system_prompt, res, phase="acquisition",
                       observer_prompt=prompt)
        verdict = acquisition_outcome(tools_before, res)
        res.acquisition = {"triggered": True, "gaps": gaps, **verdict}

    # ------------------------------------------------------------------
    # Bake (the completeness signal: one refinement pass, never a churn)
    # ------------------------------------------------------------------

    def _bake(self, prompt: str, system_prompt: str, res: CognitionResult) -> None:
        """Assess the draft with measured surface heuristics; run exactly ONE
        refinement pass when it looks unfinished. An honest ``[ERROR]``/offline
        reply is never refined (that would churn an honest status into risk of
        invention), and a blocked answer is never touched."""
        try:
            from aureon.operator.bake import assess_completeness, refinement_prompt
        except Exception as exc:  # noqa: BLE001 — a dark bake module never breaks answering
            logger.debug("bake module unavailable: %s", exc)
            return
        first = assess_completeness(prompt, res.text)
        res.bake = {"passes": 1, "complete": first["complete"],
                    "reasons": list(first["reasons"]), "refined": False}
        if first["complete"] or res.blocked or res.status() != "ok":
            if not first["complete"] and res.status() != "ok":
                res.bake["reasons"].append(
                    "not refined: the adapter is honestly unavailable — a "
                    "second pass would add no knowledge")
            return
        self._publish(res, "bake", {"reasons": first["reasons"]})
        self._run_loop(refinement_prompt(prompt, res.text, first["reasons"]),
                       system_prompt, res, phase="bake",
                       observer_prompt=prompt)
        second = assess_completeness(prompt, res.text)
        res.bake = {"passes": 2, "complete": second["complete"],
                    "reasons": list(second["reasons"]),
                    "first_pass_reasons": list(first["reasons"]),
                    "refined": True}

    # ------------------------------------------------------------------
    # Veto
    # ------------------------------------------------------------------

    def _veto(self, prompt: str, res: CognitionResult) -> None:
        org = self._read_organism_state()
        ctx = {
            "answer_preview": res.text[:400],
            "answer_digest": hashlib.sha256(res.text.encode("utf-8")).hexdigest(),
            "grounded": res.grounded,
            "tools_used": [t.tool for t in res.tool_calls],
            "tool_ledger_digest": _sha256_json(
                [item.to_dict() for item in res.tool_calls]
            ),
        }
        # Fold the shared field into the veto so the conscience's substrate-
        # coherence check sees the organism's real coherence, not "unknown".
        if org.get("symbolic_life_score") is not None:
            ctx["symbolic_life_score"] = org["symbolic_life_score"]
        if org.get("cosmic_score") is not None:
            ctx["cosmic_score"] = org["cosmic_score"]
        verdict, message, evaluated, evidence = self._queen_voice(
            f"answer cognition prompt: {prompt[:160]}",
            ctx,
        )
        res.conscience_verdict = verdict
        res.conscience_message = message
        res.queen_evaluated = evaluated
        res.queen_evidence = evidence
        if verdict == "VETO":
            res.blocked = True
            res.text = (
                "The Queen's conscience vetoed this answer.\n"
                f"Reason: {res.conscience_message}"
            )
        self._publish(res, "veto", {"verdict": res.conscience_verdict, "blocked": res.blocked})

    def _govern_final_answer(self, prompt: str, res: CognitionResult) -> None:
        """Require a second exact two-rune join before answer actualization."""

        pre_governance_status = res.status()
        if pre_governance_status != "ok":
            res.governance = _governance_hold(
                "healthy_cognition_result_required_before_governance"
            )
        elif not self._governance_enabled:
            res.governance = explicit_disabled_governance(res.capability)
        else:
            tool_ledger = [item.to_dict() for item in res.tool_calls]
            final_bake = dict(res.bake or {})
            final_bake.update({
                "phase": "final_answer",
                "tool_ledger": tool_ledger,
                "tool_ledger_digest": _sha256_json(tool_ledger),
            })
            res.governance = evaluate_cognition_governance(
                prompt=prompt,
                answer=res.text,
                tool_calls=res.tool_calls,
                capability=res.capability,
                bake=final_bake,
                acquisition=self._governance_acquisition_for(res),
                queen_verdict=res.conscience_verdict,
                queen_evaluated=res.queen_evaluated,
                council_receipt_supplier=self._council_receipt_supplier,
                crown_receipt_supplier=self._crown_receipt_supplier,
            )
        gate = res.governance or _governance_hold("governance_result_required")
        decision = str(gate.get("decision") or "HOLD").upper()
        self._publish(
            res,
            "governance",
            {
                "decision": decision,
                "receipt_id": gate.get("receipt_id"),
                "reason": gate.get("reason"),
            },
        )
        if decision not in {"ACCEPT", "DISABLED"}:
            res.blocked = True
            # Preserve an honest adapter/fault status verbatim. Governance may
            # park it, but must not relabel an unavailable result as a healthy
            # generic HOLD merely because that replacement text starts cleanly.
            if pre_governance_status == "ok":
                label = "ABORT" if decision == "ABORT" else "HOLD"
                res.text = (
                    f"{label}: Druid Council and Crown governance did not authorize "
                    "this cognition output.\n"
                    f"Reason: {gate.get('reason') or 'complete governance evidence required'}"
                )

    # ------------------------------------------------------------------
    # Actualize (the Film-Reel ledger: only the realized increment is written)
    # ------------------------------------------------------------------

    @staticmethod
    def _actualize(res: CognitionResult) -> None:
        """The replicator's last step, recorded honestly: executed tool calls
        and an un-vetoed answer are REALIZED increments; blocked tool calls and
        a vetoed/boundary-refused answer are PARKED possibilities. The parked
        ensemble is named, never deleted by fiat — and nothing parked is ever
        presented as materialized."""
        realized = [t.tool for t in res.tool_calls if not t.blocked]
        parked = [t.tool for t in res.tool_calls if t.blocked]
        res.actualization = {
            "realized_increments": realized,
            "parked_possibilities": parked,
            "answer": "parked" if res.blocked else "realized",
            "realized_count": len(realized) + (0 if res.blocked else 1),
            "parked_count": len(parked) + (1 if res.blocked else 0),
        }

    # ------------------------------------------------------------------
    # Assimilate (controlled write-back: only realized + validated joins)
    # ------------------------------------------------------------------

    def _assimilate(self, res: CognitionResult) -> None:
        """Gate this turn's knowledge record into the collective ledger —
        realized, approved, complete, ok — or refuse with the checks named."""
        governance = res.governance or {}
        if governance.get("learning_eligible") is not True:
            res.assimilation = {
                "assimilated": False,
                "checks": {"governance_learning_eligible": False},
                "reason": (
                    "write-back refused: governance evidence is evidence-only "
                    "and does not grant learning eligibility"
                ),
            }
            return
        try:
            from aureon.operator.assimilation import assimilate

            res.assimilation = assimilate(res)
        except Exception as exc:  # noqa: BLE001 — a dark ledger never breaks answering
            logger.debug("assimilation unavailable: %s", exc)

    def _heart(self, res: CognitionResult) -> None:
        """The Heart Charter on every answer, refusals included: the organism
        lives (measured or honestly dark), feels (the affect channel, silent
        when silent), and states the consequences of the power it just
        exercised or withheld — the power ledger can never be dark."""
        try:
            from aureon.operator.heart import heart_reading

            res.heart = heart_reading(self._read_organism_state(), res)
        except Exception as exc:  # noqa: BLE001 — a dark heart never breaks answering
            logger.debug("heart reading unavailable: %s", exc)

    def _get_conscience(self):
        if self._conscience_loaded:
            return self._conscience
        self._conscience_loaded = True
        try:
            from aureon.queen.queen_conscience import QueenConscience

            self._conscience = QueenConscience()
        except Exception as exc:  # noqa: BLE001
            logger.debug("QueenConscience unavailable: %s", exc)
            self._conscience = None
        return self._conscience

    # ------------------------------------------------------------------
    # Mesh + transport
    # ------------------------------------------------------------------

    def receive_mycelium_message(self, message_type: str, payload: Dict[str, Any]) -> None:
        self.last_mesh_message = {"type": message_type, "payload": payload}
        # A mesh push is also organism sensing — fold it into the shared state so
        # cognition acts on what the mesh tells it, not just stores it.
        if isinstance(payload, dict):
            self._organism.update({k: v for k, v in payload.items() if v is not None})

    # ------------------------------------------------------------------
    # Organism sensing
    # ------------------------------------------------------------------

    def _on_organism(self, thought: Any) -> None:
        """Cache the latest organism signal (subscribed to the shared bus)."""
        if topic_of is None:
            return
        try:
            topic = topic_of(thought)
            payload = payload_of(thought)
            if topic == "symbolic.life.pulse":
                for k in ("symbolic_life_score", "coherence_gamma",
                          "consciousness_level", "love_amplitude"):
                    if payload.get(k) is not None:
                        self._organism[k] = payload[k]
            elif topic == "auris.throne.cosmic_state":
                for k in ("cosmic_score", "gate_open", "advisory"):
                    if payload.get(k) is not None:
                        self._organism[k] = payload[k]
            elif topic == "lighthouse.event":
                self._organism["lighthouse_event"] = payload.get("type")
                self._organism["lighthouse_severity"] = payload.get("severity")
            elif topic == "organism.connectome.pulse":
                self._organism["connectome_coverage_pct"] = payload.get("coverage_pct")
        except Exception as exc:  # noqa: BLE001
            logger.debug("organism sense skipped: %s", exc)

    def _read_organism_state(self) -> Dict[str, Any]:
        """The live cache, backfilled from the bus ring buffer so a fresh
        cognition (no subscription history yet) still senses the current field."""
        if not self._allow_organism_context:
            return {}
        state = dict(self._organism)
        # Backfill the field from the one canonical accessor (shared source of
        # truth, flood-proof) so a fresh cognition still senses it before any
        # subscription has fired.
        if "symbolic_life_score" not in state:
            try:
                from aureon.core.hnc_field import read_canonical_field

                field = read_canonical_field(self.bus)
                if field.available:
                    state["symbolic_life_score"] = field.symbolic_life_score
                    state.setdefault("coherence_gamma", field.coherence_gamma)
            except Exception as exc:  # noqa: BLE001
                logger.debug("organism backfill skipped: %s", exc)
        return state

    def _publish(self, res: CognitionResult, phase: str, payload: Dict[str, Any]) -> None:
        topic = "cognition.complete" if phase == "complete" else f"operator.cognition.{phase}"
        if self.bus is None or Thought is None:
            return
        try:
            self.bus.publish(Thought(source=self.source, topic=topic, trace_id=res.trace_id,
                                     payload=dict(payload), meta={"phase": phase}))
        except Exception as exc:  # noqa: BLE001
            logger.debug("cognition publish failed (%s): %s", topic, exc)


def run_cognition(prompt: str, **kwargs) -> CognitionResult:
    """Convenience one-shot."""
    return AureonCognition(**kwargs).reason(prompt)


__all__ = ["AureonCognition", "run_cognition"]
