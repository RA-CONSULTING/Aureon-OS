"""Aureon-owned coding workforce with one proven Ollama brain per seat/process.

This module turns the repo's replicator metaphor into an auditable runtime
contract.  Aureon agents make the coding decisions through the Ollama model
switchboard.  Codex is represented only as a senior review/veto actor and can
never receive implementation credit.

The contract is deliberately evidence-only: it grants no filesystem, network,
economic, or deployment authority.  Existing tool, dual-key, and route gates
remain mandatory at their own boundaries.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Protocol, Sequence
from urllib.parse import urlsplit

from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    SELF_CODER_CONFIDENTIAL_PREFLIGHT_SCHEMA,
    TenNineOneHold,
    ThoughtPathRequest,
    build_local_ten_nine_one_thought_path,
)
from aureon.inhouse_ai.agent import Agent, AgentConfig
from aureon.inhouse_ai.llm_adapter import LLMAdapter
from aureon.inhouse_ai.tool_registry import ToolRegistry

SCHEMA_VERSION = "aureon-internal-coding-workforce-v1"
BRAIN_SCHEMA_VERSION = "aureon-coding-brain-passport-v1"
WORK_SCHEMA_VERSION = "aureon-coding-work-receipt-v3"
INTERMEDIATE_WORK_SCHEMA_VERSION = "aureon-coding-work-receipt-v2"
LEGACY_WORK_SCHEMA_VERSION = "aureon-coding-work-receipt-v1"
TRUTH_GATED_THOUGHT_RECEIPT_PREFIX = "thought:10-9-1:truth-gated:"
MIN_INTERNAL_SHARE_PERCENT = 99
INTERNAL_BRAIN_MAX_TOKENS = 512
INTERNAL_AUTHOR_MAX_TOKENS = 4_096
LOCAL_SELF_CODER_PROVIDER_MODE = "ollama_local_hnc_protected"
SUPPORTED_HNC_PROVIDER_MODES = frozenset(
    {"ollama_cloud_primary", LOCAL_SELF_CODER_PROVIDER_MODE}
)
SELF_CODER_TRANSPORT_PREFLIGHT_SCHEMA = "aureon-self-coder-transport-preflight-v1"

INTERNAL_ACTOR = "aureon_internal"
SENIOR_OVERSIGHT_ACTOR = "codex_senior_oversight"
SENIOR_OVERSIGHT_ID = "codex:senior-development-overseer"
SENIOR_OVERSIGHT_STAGES = frozenset(
    {
        "architecture_review",
        "contract_review",
        "security_review",
        "release_acceptance",
    }
)

ROLE_BRAIN_LANES: Dict[str, str] = {
    "Estimator": "fast",
    "Project Manager": "architecture",
    "Foreman": "architecture",
    "Implementation Worker": "coding",
    "Test Pilot": "coding",
    "Security Auditor": "architecture",
    "Snagging Inspector": "self_evolution",
    "Release Manager": "general",
    "Archive Librarian": "fast",
}

PROCESS_BRAIN_BINDINGS: Dict[str, tuple[str, str]] = {
    "client_intake": ("fast", "Estimator"),
    "scope_of_works": ("architecture", "Project Manager"),
    "team_assignment": ("architecture", "Foreman"),
    "build_execution": ("coding", "Implementation Worker"),
    "internal_review": ("coding", "Test Pilot"),
    "security_review": ("architecture", "Security Auditor"),
    "snagging": ("self_evolution", "Snagging Inspector"),
    "client_handover": ("general", "Release Manager"),
    "memory_assimilation": ("fast", "Archive Librarian"),
}

ROLE_PROCESS_BINDINGS: Dict[str, str] = {
    owner: process_id for process_id, (_lane, owner) in PROCESS_BRAIN_BINDINGS.items()
}

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class WorkforceHold(RuntimeError):
    """Raised when a coding brain or its evidence is not ready."""


class CodingThoughtPath(Protocol):
    """Execution surface required by Aureon's internal cloud brains."""

    truth_gate_enforced: bool

    @property
    def receipts(self) -> tuple[Mapping[str, Any], ...]: ...

    def execute(
        self,
        *,
        request: ThoughtPathRequest,
        prompt: str,
        infer: Callable[[str], str],
        correction_attempt: int = 0,
    ) -> Any: ...


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _canonical_id(value: str, *, label: str) -> str:
    result = str(value or "").strip()
    if not result or len(result) > 160:
        raise ValueError(f"{label} must be 1..160 characters")
    return result


def _bounded_prompt(value: str) -> str:
    result = str(value or "").strip()
    if not result or len(result) > 65_536:
        raise ValueError("prompt must be 1..65536 characters")
    return result


def _accept_hold_verdict(value: str) -> str:
    first = str(value or "").strip().split(maxsplit=1)
    token = first[0].rstrip(":") if first else ""
    for wrapper in ("**", "__", "*", "_"):
        if token.startswith(wrapper) and token.endswith(wrapper) and len(token) > len(wrapper) * 2:
            token = token[len(wrapper) : -len(wrapper)]
            break
    token = token.upper()
    return token if token in {"ACCEPT", "HOLD"} else "HOLD"


def _canonical_digest(value: str, *, label: str) -> str:
    result = str(value or "").strip().lower()
    if not _HEX_64.fullmatch(result):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return result


def _valid_hnc_gamma(value: Any) -> bool:
    if type(value) not in {int, float}:
        return False
    assert isinstance(value, (int, float))
    gamma = float(value)
    return math.isfinite(gamma) and 0.0 <= gamma <= 1.0


@dataclass(frozen=True)
class ResolvedBrain:
    """A runtime adapter plus non-secret evidence from the Ollama switchboard."""

    adapter: LLMAdapter | None
    lane: str
    model: str
    source: str
    endpoint_reachable: bool
    working: bool
    catalog_size: int
    catalog_refreshed_at: float
    endpoint_authority_digest: str
    routing_receipt_id: str = ""
    hnc_receipt_id: str = ""
    hnc_gamma: float | None = None
    hnc_coherence_band: str = ""
    provider_mode: str = ""


class BrainResolver(Protocol):
    def resolve(self, lane: str) -> ResolvedBrain:
        """Resolve and live-probe one Aureon Ollama reasoning lane."""


class OllamaSwitchboardBrainResolver:
    """Production resolver backed by the existing live Ollama switchboard."""

    def __init__(self, switchboard: Any = None) -> None:
        if switchboard is None:
            from aureon.integrations.ollama.model_switchboard import OllamaModelSwitchboard

            switchboard = OllamaModelSwitchboard()
        self.switchboard = switchboard
        self._cache: Dict[tuple[str, str], ResolvedBrain] = {}
        capture_field = getattr(self.switchboard, "capture_hnc_field", None)
        self._generation_hnc_field = capture_field() if callable(capture_field) else None

    def resolve(self, lane: str) -> ResolvedBrain:
        return self.resolve_for(lane, nerve_id=f"lane:{lane}")

    def self_coder_transport_preflight(self) -> dict[str, Any]:
        """Reject hosted or ambiguous endpoints before self-coder plaintext exists."""

        base_url = str(
            getattr(getattr(self.switchboard, "bridge", None), "base_url", "") or ""
        )
        canonical_endpoint = _canonical_self_coder_loopback_endpoint(base_url)
        ready = bool(canonical_endpoint)
        return {
            "schema_version": SELF_CODER_TRANSPORT_PREFLIGHT_SCHEMA,
            "ready": ready,
            "provider_mode": LOCAL_SELF_CODER_PROVIDER_MODE if ready else "hold",
            "endpoint_authority_digest": _text_digest(
                canonical_endpoint if ready else base_url
            ),
            "endpoint_loopback": ready,
            "external_source_egress_authorized": False,
            "action_eligible": False,
            "economic_eligible": False,
        }

    def resolve_for(self, lane: str, *, nerve_id: str) -> ResolvedBrain:
        lane_name = _canonical_id(lane, label="lane").lower()
        nerve = _canonical_id(nerve_id, label="nerve_id")
        cache_key = (lane_name, nerve)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        route_adapter = getattr(self.switchboard, "compatible_adapter_for_nerve", None)
        if callable(route_adapter):
            adapter, selection, route = route_adapter(
                lane_name,
                nerve_id=nerve,
                hnc_field=self._generation_hnc_field,
            )
        else:
            adapter, selection = self.switchboard.compatible_adapter_for(lane_name)
            route = None
        base_url = str(getattr(getattr(self.switchboard, "bridge", None), "base_url", "") or "")
        canonical_endpoint = _canonical_self_coder_loopback_endpoint(base_url)
        if canonical_endpoint:
            enable_strict = getattr(adapter, "enable_strict_loopback_transport", None)
            if callable(enable_strict):
                enable_strict()
        source = str(getattr(selection, "source", "") or "")
        resolved = ResolvedBrain(
            adapter=adapter,
            lane=str(getattr(selection, "lane", lane_name) or lane_name),
            model=str(getattr(selection, "model", "") or ""),
            source=source,
            endpoint_reachable=bool(getattr(selection, "endpoint_reachable", False)),
            working=source.startswith("live_probe_passed:"),
            catalog_size=int(getattr(selection, "catalog_size", 0) or 0),
            catalog_refreshed_at=float(getattr(selection, "catalog_refreshed_at", 0.0) or 0.0),
            endpoint_authority_digest=_text_digest(canonical_endpoint or base_url),
            routing_receipt_id=str(getattr(route, "receipt_id", "") or ""),
            hnc_receipt_id=str(getattr(route, "hnc_receipt_id", "") or ""),
            hnc_gamma=getattr(route, "coherence_gamma", None),
            hnc_coherence_band=str(getattr(route, "coherence_band", "") or ""),
            provider_mode=str(getattr(route, "provider_mode", "") or ""),
        )
        self._cache[cache_key] = resolved
        return resolved


@dataclass(frozen=True)
class BrainPassport:
    schema_version: str
    subject_type: str
    subject_id: str
    lane: str
    model: str
    selection_source: str
    endpoint_reachable: bool
    catalog_size: int | None
    catalog_refreshed_at: float | None
    endpoint_authority_digest: str
    status: str
    brain_ready: bool
    cloud_fallback_used: bool
    action_eligible: bool
    economic_eligible: bool
    receipt_id: str
    routing_receipt_id: str = ""
    hnc_receipt_id: str = ""
    hnc_gamma: float | None = None
    hnc_coherence_band: str = ""
    provider_mode: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkReceipt:
    schema_version: str
    sequence: int
    actor_class: str
    actor_id: str
    process_id: str
    stage: str
    work_kind: str
    input_digest: str
    output_digest: str
    brain_passport_id: str
    completed_at: float
    action_eligible: bool
    economic_eligible: bool
    receipt_id: str
    thought_path_receipt_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _brain_causal_payload(passport: BrainPassport) -> Dict[str, Any]:
    payload = passport.to_dict()
    payload.pop("receipt_id", None)
    return payload


def _canonical_self_coder_loopback_endpoint(base_url: str) -> str:
    """Return one canonical literal local Ollama endpoint or an empty HOLD."""

    try:
        parsed = urlsplit(str(base_url or "").strip())
        if not (
            parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "::1"}
            and parsed.port == 11434
            and parsed.username is None
            and parsed.password is None
            and parsed.query == ""
            and parsed.fragment == ""
            and parsed.path.rstrip("/") in {"", "/v1"}
        ):
            return ""
    except (TypeError, ValueError):
        return ""
    host = f"[{parsed.hostname}]" if parsed.hostname == "::1" else parsed.hostname
    return f"http://{host}:11434/v1"


def _is_exact_self_coder_loopback_endpoint(base_url: str) -> bool:
    """Accept only a literal unauthenticated local Ollama endpoint shape."""

    return bool(_canonical_self_coder_loopback_endpoint(base_url))


def _work_causal_payload(receipt: WorkReceipt) -> Dict[str, Any]:
    payload = receipt.to_dict()
    payload.pop("receipt_id", None)
    if receipt.schema_version == LEGACY_WORK_SCHEMA_VERSION:
        payload.pop("thought_path_receipt_id", None)
    return payload


def validate_brain_passport(passport: BrainPassport) -> bool:
    if not isinstance(passport, BrainPassport) or passport.schema_version != BRAIN_SCHEMA_VERSION:
        return False
    if passport.subject_type not in {"agent", "process"}:
        return False
    if not passport.subject_id or not passport.lane:
        return False
    if type(passport.endpoint_reachable) is not bool or type(passport.brain_ready) is not bool:
        return False
    if type(passport.cloud_fallback_used) is not bool or passport.cloud_fallback_used:
        return False
    if type(passport.action_eligible) is not bool or passport.action_eligible:
        return False
    if type(passport.economic_eligible) is not bool or passport.economic_eligible:
        return False
    if passport.catalog_size is not None and (
        type(passport.catalog_size) is not int or passport.catalog_size < 0
    ):
        return False
    if passport.catalog_refreshed_at is not None and (
        type(passport.catalog_refreshed_at) not in {int, float}
        or isinstance(passport.catalog_refreshed_at, bool)
        or not math.isfinite(float(passport.catalog_refreshed_at))
        or float(passport.catalog_refreshed_at) < 0
    ):
        return False
    if not _HEX_64.fullmatch(passport.endpoint_authority_digest):
        return False
    if passport.brain_ready:
        if (
            passport.status != "ready"
            or not passport.model
            or not passport.endpoint_reachable
            or not passport.routing_receipt_id.startswith("ollama:hnc-route:")
            or not passport.hnc_receipt_id.startswith("hnc:live_field:")
            or passport.hnc_coherence_band not in {"lighthouse", "active", "organizing", "low"}
            or passport.provider_mode not in SUPPORTED_HNC_PROVIDER_MODES
            or not _valid_hnc_gamma(passport.hnc_gamma)
        ):
            return False
        if not passport.selection_source.startswith("live_probe_passed:hnc_"):
            return False
    elif passport.status != "no_data" or any(
        value is not None for value in (passport.catalog_size, passport.catalog_refreshed_at)
    ) or any(
        (
            passport.routing_receipt_id,
            passport.hnc_receipt_id,
            passport.hnc_coherence_band,
            passport.provider_mode,
        )
    ) or passport.hnc_gamma is not None:
        return False
    return passport.receipt_id == f"brain:{_digest(_brain_causal_payload(passport))}"


def validate_work_receipt(receipt: WorkReceipt) -> bool:
    if not isinstance(receipt, WorkReceipt) or receipt.schema_version not in {
        WORK_SCHEMA_VERSION,
        INTERMEDIATE_WORK_SCHEMA_VERSION,
        LEGACY_WORK_SCHEMA_VERSION,
    }:
        return False
    if type(receipt.sequence) is not int or receipt.sequence < 1:
        return False
    if receipt.actor_class not in {INTERNAL_ACTOR, SENIOR_OVERSIGHT_ACTOR}:
        return False
    if not receipt.actor_id or not receipt.process_id or not receipt.stage or not receipt.work_kind:
        return False
    if not _HEX_64.fullmatch(receipt.input_digest) or not _HEX_64.fullmatch(receipt.output_digest):
        return False
    if type(receipt.completed_at) not in {int, float} or isinstance(receipt.completed_at, bool):
        return False
    if not math.isfinite(float(receipt.completed_at)) or float(receipt.completed_at) <= 0:
        return False
    if type(receipt.action_eligible) is not bool or receipt.action_eligible:
        return False
    if type(receipt.economic_eligible) is not bool or receipt.economic_eligible:
        return False
    if receipt.actor_class == INTERNAL_ACTOR:
        if not receipt.brain_passport_id.startswith("brain:"):
            return False
        if receipt.schema_version == WORK_SCHEMA_VERSION:
            if not receipt.thought_path_receipt_id.startswith(
                TRUTH_GATED_THOUGHT_RECEIPT_PREFIX
            ):
                return False
        elif receipt.schema_version == INTERMEDIATE_WORK_SCHEMA_VERSION:
            if not receipt.thought_path_receipt_id.startswith("thought:10-9-1:"):
                return False
        elif receipt.thought_path_receipt_id:
            return False
    else:
        if receipt.actor_id != SENIOR_OVERSIGHT_ID or receipt.stage not in SENIOR_OVERSIGHT_STAGES:
            return False
        if receipt.brain_passport_id:
            return False
        if receipt.thought_path_receipt_id:
            return False
    return receipt.receipt_id == f"work:{_digest(_work_causal_payload(receipt))}"


def _issue_brain_passport(
    subject_type: str, subject_id: str, lane: str, resolved: ResolvedBrain | None
) -> BrainPassport:
    ready = bool(
        resolved
        and resolved.adapter is not None
        and resolved.working
        and resolved.endpoint_reachable
        and resolved.model
        and resolved.lane == lane
        and resolved.source.startswith("live_probe_passed:")
        and resolved.routing_receipt_id.startswith("ollama:hnc-route:")
        and resolved.hnc_receipt_id.startswith("hnc:live_field:")
        and resolved.hnc_coherence_band in {"lighthouse", "active", "organizing", "low"}
        and resolved.provider_mode in SUPPORTED_HNC_PROVIDER_MODES
        and _valid_hnc_gamma(resolved.hnc_gamma)
    )
    if ready:
        assert resolved is not None
        assert resolved.hnc_gamma is not None
        passport = BrainPassport(
            schema_version=BRAIN_SCHEMA_VERSION,
            subject_type=subject_type,
            subject_id=subject_id,
            lane=lane,
            model=resolved.model,
            selection_source=resolved.source,
            endpoint_reachable=True,
            catalog_size=resolved.catalog_size,
            catalog_refreshed_at=resolved.catalog_refreshed_at,
            endpoint_authority_digest=resolved.endpoint_authority_digest,
            status="ready",
            brain_ready=True,
            cloud_fallback_used=False,
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
            routing_receipt_id=resolved.routing_receipt_id,
            hnc_receipt_id=resolved.hnc_receipt_id,
            hnc_gamma=float(resolved.hnc_gamma),
            hnc_coherence_band=resolved.hnc_coherence_band,
            provider_mode=resolved.provider_mode,
        )
    else:
        endpoint_digest = resolved.endpoint_authority_digest if resolved else _text_digest("")
        passport = BrainPassport(
            schema_version=BRAIN_SCHEMA_VERSION,
            subject_type=subject_type,
            subject_id=subject_id,
            lane=lane,
            model="",
            selection_source="no_data",
            endpoint_reachable=False,
            catalog_size=None,
            catalog_refreshed_at=None,
            endpoint_authority_digest=endpoint_digest,
            status="no_data",
            brain_ready=False,
            cloud_fallback_used=False,
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
            routing_receipt_id="",
            hnc_receipt_id="",
            hnc_gamma=None,
            hnc_coherence_band="",
            provider_mode="",
        )
    return BrainPassport(
        **{**passport.to_dict(), "receipt_id": f"brain:{_digest(_brain_causal_payload(passport))}"}
    )


class InternalCodingWorkforce:
    """Runtime collection of brain-bound Aureon agents and process brains."""

    def __init__(
        self,
        *,
        agents: Mapping[str, Agent],
        process_brains: Mapping[str, Agent],
        passports: Sequence[BrainPassport],
        role_brain_lanes: Mapping[str, str] | None = None,
        role_process_bindings: Mapping[str, str] | None = None,
        prior_work_receipts: Sequence[WorkReceipt] = (),
        receipt_sink: Callable[[WorkReceipt], None] | None = None,
        thought_path: CodingThoughtPath | None = None,
        decision_observer: Callable[[Mapping[str, Any]], None] | None = None,
        response_stop_sequences: Sequence[str] = (),
    ) -> None:
        self._agents = dict(agents)
        self._process_brains = dict(process_brains)
        self._passports = tuple(passports)
        self._passport_by_subject = {(p.subject_type, p.subject_id): p for p in passports}
        self._role_brain_lanes = dict(role_brain_lanes or ROLE_BRAIN_LANES)
        self._role_process_bindings = dict(role_process_bindings or ROLE_PROCESS_BINDINGS)
        self._work_receipts = list(prior_work_receipts)
        self._receipt_sink = receipt_sink
        if decision_observer is not None and not callable(decision_observer):
            raise WorkforceHold("decision_observer_must_be_callable")
        self._decision_observer = decision_observer
        stops = tuple(str(item) for item in response_stop_sequences)
        if (
            len(stops) != len(set(stops))
            or any(not item or len(item) > 64 for item in stops)
        ):
            raise WorkforceHold("bounded_unique_response_stop_sequences_required")
        self._response_stop_sequences = stops
        self._thought_path = thought_path or build_local_ten_nine_one_thought_path()
        if any(
            not validate_work_receipt(receipt) or receipt.sequence != index
            for index, receipt in enumerate(self._work_receipts, start=1)
        ):
            raise WorkforceHold("prior_work_receipts_invalid")
        if len({receipt.receipt_id for receipt in self._work_receipts}) != len(self._work_receipts):
            raise WorkforceHold("prior_work_receipts_duplicate")
        passport_ids = {passport.receipt_id for passport in self._passports}
        if any(
            receipt.actor_class == INTERNAL_ACTOR and receipt.brain_passport_id not in passport_ids
            for receipt in self._work_receipts
        ):
            raise WorkforceHold("prior_work_receipt_brain_binding_invalid")

    @property
    def agents(self) -> Mapping[str, Agent]:
        return dict(self._agents)

    @property
    def process_brains(self) -> Mapping[str, Agent]:
        return dict(self._process_brains)

    @property
    def work_receipts(self) -> tuple[WorkReceipt, ...]:
        return tuple(self._work_receipts)

    @property
    def thought_path_receipts(self) -> tuple[Mapping[str, Any], ...]:
        return self._thought_path.receipts

    def process_id_for_role(self, role: str) -> str:
        """Return the exact paired process brain for one active role."""

        role_id = _canonical_id(role, label="role")
        process_id = self._role_process_bindings.get(role_id)
        if not process_id:
            raise WorkforceHold("role_process_binding_missing")
        return process_id

    def assert_sensitive_local_only(self, *, endpoint_authority_digest: str) -> None:
        """Fail closed unless every brain and the thought path are local/confidential.

        The check runs before any self-coder decision.  It deliberately refuses
        cloud brains even though they remain supported for non-sensitive workforce
        use elsewhere in Aureon.
        """

        endpoint_digest = _canonical_digest(
            endpoint_authority_digest,
            label="endpoint_authority_digest",
        )
        preflight = getattr(self._thought_path, "self_coder_confidential_preflight", None)
        thought = preflight() if callable(preflight) else None
        if (
            not isinstance(thought, Mapping)
            or set(thought)
            != {
                "schema_version",
                "ready",
                "truth_gate_enforced",
                "trusted_local_evidence_resolver",
                "trusted_receipt_backed_truth_gate",
                "commitment_only_propagation",
                "raw_answer_bus_persistence_authorized",
                "raw_answer_trace_persistence_authorized",
                "action_eligible",
                "economic_eligible",
            }
            or thought.get("schema_version")
            != SELF_CODER_CONFIDENTIAL_PREFLIGHT_SCHEMA
            or thought.get("ready") is not True
            or thought.get("truth_gate_enforced") is not True
            or thought.get("trusted_local_evidence_resolver") is not True
            or thought.get("trusted_receipt_backed_truth_gate") is not True
            or thought.get("commitment_only_propagation") is not True
            or thought.get("raw_answer_bus_persistence_authorized") is not False
            or thought.get("raw_answer_trace_persistence_authorized") is not False
            or thought.get("action_eligible") is not False
            or thought.get("economic_eligible") is not False
        ):
            raise WorkforceHold("self_coder_commitment_only_thought_path_required")
        if self._decision_observer is not None:
            raise WorkforceHold("self_coder_plaintext_decision_observer_forbidden")
        if not self._passports or any(
            not passport.brain_ready
            or passport.provider_mode != LOCAL_SELF_CODER_PROVIDER_MODE
            or passport.endpoint_authority_digest != endpoint_digest
            for passport in self._passports
        ):
            raise WorkforceHold("self_coder_local_brain_passports_required")
        runtimes = [*self._agents.values(), *self._process_brains.values()]
        if len(runtimes) != len(self._passports):
            raise WorkforceHold("self_coder_local_brain_runtime_count_mismatch")
        for runtime in runtimes:
            adapter = getattr(runtime, "adapter", None)
            base_url = str(getattr(adapter, "base_url", "") or "")
            canonical_endpoint = _canonical_self_coder_loopback_endpoint(base_url)
            if (
                not canonical_endpoint
                or _text_digest(canonical_endpoint) != endpoint_digest
                or getattr(adapter, "strict_loopback_no_redirects", None) is not True
            ):
                raise WorkforceHold("self_coder_strict_loopback_adapter_required")

    def _append_work(
        self,
        *,
        actor_class: str,
        actor_id: str,
        process_id: str,
        stage: str,
        work_kind: str,
        input_digest: str,
        output_digest: str,
        brain_passport_id: str,
        thought_path_receipt_id: str = "",
    ) -> WorkReceipt:
        receipt = WorkReceipt(
            schema_version=WORK_SCHEMA_VERSION,
            sequence=len(self._work_receipts) + 1,
            actor_class=actor_class,
            actor_id=_canonical_id(actor_id, label="actor_id"),
            process_id=_canonical_id(process_id, label="process_id"),
            stage=_canonical_id(stage, label="stage"),
            work_kind=_canonical_id(work_kind, label="work_kind"),
            input_digest=_canonical_digest(input_digest, label="input_digest"),
            output_digest=_canonical_digest(output_digest, label="output_digest"),
            brain_passport_id=brain_passport_id,
            completed_at=time.time(),
            action_eligible=False,
            economic_eligible=False,
            receipt_id="",
            thought_path_receipt_id=thought_path_receipt_id,
        )
        receipt = WorkReceipt(
            **{**receipt.to_dict(), "receipt_id": f"work:{_digest(_work_causal_payload(receipt))}"}
        )
        if not validate_work_receipt(receipt):
            raise WorkforceHold("work_receipt_validation_failed")
        if self._receipt_sink is not None:
            self._receipt_sink(receipt)
        self._work_receipts.append(receipt)
        return receipt

    def decide(
        self,
        *,
        subject_type: str,
        subject_id: str,
        process_id: str,
        prompt: str,
        stage: str,
        work_kind: str = "coding_decision",
        max_tokens: int | None = None,
    ) -> tuple[str, WorkReceipt]:
        if getattr(self._thought_path, "truth_gate_enforced", False) is not True:
            raise WorkforceHold("truth_gated_10_9_1_path_required")
        subject_key = (
            _canonical_id(subject_type, label="subject_type"),
            _canonical_id(subject_id, label="subject_id"),
        )
        passport = self._passport_by_subject.get(subject_key)
        process_passport = self._passport_by_subject.get(("process", process_id))
        runtime = (
            self._agents.get(subject_id) if subject_type == "agent" else self._process_brains.get(subject_id)
        )
        if not passport or not process_passport or not runtime:
            raise WorkforceHold("brain_binding_missing")
        if not validate_brain_passport(passport) or not passport.brain_ready:
            raise WorkforceHold("subject_brain_not_ready")
        if not validate_brain_passport(process_passport) or not process_passport.brain_ready:
            raise WorkforceHold("process_brain_not_ready")
        prompt_text = _bounded_prompt(prompt)
        request = ThoughtPathRequest(
            subject_type=subject_key[0],
            subject_id=subject_key[1],
            process_id=_canonical_id(process_id, label="process_id"),
            stage=_canonical_id(stage, label="stage"),
            work_kind=_canonical_id(work_kind, label="work_kind"),
            prompt_digest=_text_digest(prompt_text),
            brain_passport_id=passport.receipt_id,
        )

        token_budget = INTERNAL_BRAIN_MAX_TOKENS if max_tokens is None else max_tokens
        if type(token_budget) is not int or not 1 <= token_budget <= INTERNAL_AUTHOR_MAX_TOKENS:
            raise WorkforceHold("brain_output_token_budget_invalid")

        correction_attempt = 0

        def infer(organized_prompt: str) -> str:
            prompt_kwargs: Dict[str, Any] = {}
            if self._response_stop_sequences:
                prompt_kwargs["stop"] = list(self._response_stop_sequences)
            model_prompt = organized_prompt
            if correction_attempt:
                model_prompt += (
                    "\n\nKUNDALINI CORRECTION ATTEMPT "
                    f"{correction_attempt}: The prior answer failed the material truth "
                    "gate. Return exactly one complete line from ALLOWED EXACT RESPONSES. "
                    "Do not emit reasoning tags, analysis, Markdown, quotes, prefixes, "
                    "suffixes, or a second answer."
                )
            response = runtime.adapter.prompt(
                messages=[{"role": "user", "content": model_prompt}],
                system=runtime.config.system_prompt,
                tools=None,
                max_tokens=token_budget,
                temperature=runtime.config.temperature,
                **prompt_kwargs,
            )
            output = str(response.text or "").strip()
            if str(response.stop_reason or "").strip().lower() == "error" or output.startswith("[ERROR]"):
                raise TenNineOneHold("brain_decision_failed")
            if not output:
                raise TenNineOneHold("brain_returned_empty_decision")
            if self._decision_observer is not None:
                try:
                    self._decision_observer(
                        {
                            "subject_type": request.subject_type,
                            "subject_id": request.subject_id,
                            "process_id": request.process_id,
                            "stage": request.stage,
                            "work_kind": request.work_kind,
                            "prompt_digest": request.prompt_digest,
                            "correction_attempt": correction_attempt,
                            "output": output,
                        }
                    )
                except Exception as exc:
                    raise TenNineOneHold("decision_observer_failed") from exc
            return output

        thought = None
        for correction_attempt in range(3):
            try:
                thought = self._thought_path.execute(
                    request=request,
                    prompt=prompt_text,
                    infer=infer,
                    correction_attempt=correction_attempt,
                )
                break
            except TenNineOneHold as exc:
                correction_required = str(exc).startswith(
                    "truth_gate_correction_required:"
                )
                if correction_required and correction_attempt < 2:
                    continue
                raise WorkforceHold(str(exc)) from exc
        if thought is None:
            raise WorkforceHold("bounded_kundalini_correction_exhausted")
        output = thought.answer
        receipt = self._append_work(
            actor_class=INTERNAL_ACTOR,
            actor_id=f"aureon:{subject_type}:{subject_id}",
            process_id=process_id,
            stage=stage,
            work_kind=work_kind,
            input_digest=_text_digest(prompt_text),
            output_digest=_text_digest(output),
            brain_passport_id=passport.receipt_id,
            thought_path_receipt_id=str(thought.receipt["receipt_id"]),
        )
        return output, receipt

    def record_senior_oversight(
        self,
        *,
        process_id: str,
        stage: str,
        reviewed_input_digest: str,
        review_output_digest: str,
    ) -> WorkReceipt:
        if stage not in SENIOR_OVERSIGHT_STAGES:
            raise WorkforceHold("codex_is_restricted_to_senior_oversight")
        return self._append_work(
            actor_class=SENIOR_OVERSIGHT_ACTOR,
            actor_id=SENIOR_OVERSIGHT_ID,
            process_id=process_id,
            stage=stage,
            work_kind="senior_review",
            input_digest=reviewed_input_digest,
            output_digest=review_output_digest,
            brain_passport_id="",
            thought_path_receipt_id="",
        )

    def deliberate_coding_goal(
        self,
        prompt: str,
        *,
        scope_locked: bool = True,
        selected_roles: Sequence[str] | None = None,
        require_accept: bool = False,
    ) -> Dict[str, Any]:
        """Let every active Aureon seat and its process brain decide in sequence."""

        prompt_text = _bounded_prompt(prompt)
        active_roles: list[str] = list(self._role_brain_lanes)
        if selected_roles is not None:
            chosen = tuple(str(role or "").strip() for role in selected_roles)
            if (
                not chosen
                or any(not role for role in chosen)
                or len(set(chosen)) != len(chosen)
                or any(role not in self._role_brain_lanes for role in chosen)
            ):
                raise WorkforceHold("selected_deliberation_roles_invalid")
            active_roles = list(chosen)
        elif not scope_locked:
            preferred: list[str] = [
                role for role in ("Estimator", "Project Manager") if role in active_roles
            ]
            active_roles = preferred or active_roles[:2]
        decisions: list[Dict[str, Any]] = []
        prior_digest = _text_digest(prompt_text)
        stage = "pre_apply_council" if require_accept else "autonomous_deliberation"
        for role in active_roles:
            process_id = self._role_process_bindings[role]
            verdict_instruction = (
                "Reply ACCEPT or HOLD as the first token, then give a bounded reason."
                if require_accept
                else "Make your own bounded decision for this coding stage."
            )
            agent_prompt = (
                f"Goal: {prompt_text}\nProcess: {process_id}\n"
                f"Prior deliberation digest: {prior_digest}\n"
                f"{verdict_instruction}"
            )
            agent_decision, agent_receipt = self.decide(
                subject_type="agent",
                subject_id=role,
                process_id=process_id,
                prompt=agent_prompt,
                stage=stage,
                work_kind=("pre_apply_agent_review" if require_accept else "agent_stage_decision"),
            )
            agent_verdict = _accept_hold_verdict(agent_decision) if require_accept else ""
            process_prompt = (
                f"Goal: {prompt_text}\nAccountable seat: {role}\n"
                f"Seat decision: {agent_decision}\n"
                "Independently verify and refine the decision for this process.\n"
                f"{verdict_instruction}"
            )
            process_decision, process_receipt = self.decide(
                subject_type="process",
                subject_id=process_id,
                process_id=process_id,
                prompt=process_prompt,
                stage=stage,
                work_kind=("pre_apply_process_review" if require_accept else "process_stage_decision"),
            )
            process_verdict = _accept_hold_verdict(process_decision) if require_accept else ""
            prior_digest = _text_digest(process_decision)
            decisions.append(
                {
                    "role": role,
                    "process_id": process_id,
                    "lane": self._role_brain_lanes[role],
                    "agent_decision": agent_decision,
                    "process_decision": process_decision,
                    "agent_verdict": agent_verdict,
                    "process_verdict": process_verdict,
                    "agent_work_receipt_id": agent_receipt.receipt_id,
                    "process_work_receipt_id": process_receipt.receipt_id,
                }
            )
        hold_count = (
            sum(
                item["agent_verdict"] != "ACCEPT" or item["process_verdict"] != "ACCEPT" for item in decisions
            )
            if require_accept
            else 0
        )
        return {
            "schema_version": "aureon-internal-coding-deliberation-v1",
            "status": "complete",
            "scope_locked": scope_locked,
            "decision_count": len(decisions) * 2,
            "active_agent_count": len(active_roles),
            "decision_mode": "accept_hold" if require_accept else "advisory",
            "accepted": not require_accept or hold_count == 0,
            "hold_count": hold_count,
            "decisions": decisions,
            "action_eligible": False,
            "economic_eligible": False,
        }

    def report(self) -> Dict[str, Any]:
        passports_valid = all(validate_brain_passport(item) for item in self._passports)
        unready_agents = sorted(
            item.subject_id
            for item in self._passports
            if item.subject_type == "agent" and not item.brain_ready
        )
        unready_processes = sorted(
            item.subject_id
            for item in self._passports
            if item.subject_type == "process" and not item.brain_ready
        )
        receipts_valid = all(validate_work_receipt(item) for item in self._work_receipts)
        internal_units = sum(item.actor_class == INTERNAL_ACTOR for item in self._work_receipts)
        thought_path_units = sum(
            item.actor_class == INTERNAL_ACTOR
            and item.schema_version == WORK_SCHEMA_VERSION
            and item.thought_path_receipt_id.startswith(TRUTH_GATED_THOUGHT_RECEIPT_PREFIX)
            for item in self._work_receipts
        )
        thought_path_complete = internal_units == thought_path_units
        truth_gate_enforced = getattr(self._thought_path, "truth_gate_enforced", False) is True
        oversight_units = sum(item.actor_class == SENIOR_OVERSIGHT_ACTOR for item in self._work_receipts)
        total_units = len(self._work_receipts)
        internal_share_ppm = (internal_units * 1_000_000 // total_units) if total_units else None
        ratio_passed = bool(total_units and internal_units * 100 >= total_units * MIN_INTERNAL_SHARE_PERCENT)
        senior_oversight_present = oversight_units > 0
        senior_oversight_is_final = bool(
            self._work_receipts and self._work_receipts[-1].actor_class == SENIOR_OVERSIGHT_ACTOR
        )
        hnc_routed_brain_count = sum(
            item.brain_ready
            and item.provider_mode in SUPPORTED_HNC_PROVIDER_MODES
            and item.routing_receipt_id.startswith("ollama:hnc-route:")
            and item.hnc_receipt_id.startswith("hnc:live_field:")
            for item in self._passports
        )
        all_brains_hnc_routed = bool(self._passports) and hnc_routed_brain_count == len(self._passports)
        brain_fabric_ready = (
            passports_valid
            and not unready_agents
            and not unready_processes
            and all_brains_hnc_routed
            and truth_gate_enforced
        )
        ready = (
            brain_fabric_ready
            and receipts_valid
            and thought_path_complete
            and ratio_passed
            and senior_oversight_present
            and senior_oversight_is_final
        )
        if ready:
            status = "ready"
        elif not total_units:
            status = "no_data"
        else:
            status = "hold"
        return {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "ready": ready,
            "brain_fabric_ready": brain_fabric_ready,
            "decision_authority": INTERNAL_ACTOR,
            "codex_role": "senior_review_and_veto_only",
            "codex_implementation_allowed": False,
            "cloud_fallback_used": False,
            "provider_mode": (
                next(iter({item.provider_mode for item in self._passports}))
                if all_brains_hnc_routed
                and len({item.provider_mode for item in self._passports}) == 1
                else "hold"
            ),
            "hnc_routed_brain_count": hnc_routed_brain_count,
            "all_brains_hnc_routed": all_brains_hnc_routed,
            "truth_gate_enforced": truth_gate_enforced,
            "thought_path_mode": "truth_gated_10_9_1" if truth_gate_enforced else "hold",
            "distinct_hnc_routing_receipt_count": len(
                {item.routing_receipt_id for item in self._passports if item.routing_receipt_id}
            ),
            "distinct_cloud_model_count": len(
                {item.model for item in self._passports if item.brain_ready and item.model}
            ),
            "agent_brain_count": sum(item.subject_type == "agent" for item in self._passports),
            "process_brain_count": sum(item.subject_type == "process" for item in self._passports),
            "unready_agents": unready_agents,
            "unready_processes": unready_processes,
            "work_unit_definition": "one completed, receipt-bound decision or senior review event",
            "internal_work_units": internal_units,
            "ten_nine_one_work_units": thought_path_units,
            "ten_nine_one_complete": thought_path_complete,
            "senior_oversight_units": oversight_units,
            "total_work_units": total_units,
            "internal_share_ppm": internal_share_ppm,
            "minimum_internal_share_ppm": MIN_INTERNAL_SHARE_PERCENT * 10_000,
            "internal_share_passed": ratio_passed,
            "senior_oversight_present": senior_oversight_present,
            "senior_oversight_is_final": senior_oversight_is_final,
            "passports": [item.to_dict() for item in self._passports],
            "work_receipts": [item.to_dict() for item in self._work_receipts],
            "action_eligible": False,
            "economic_eligible": False,
        }


def provision_brain_bound_workforce(
    *,
    role_brain_lanes: Mapping[str, str],
    process_brain_bindings: Mapping[str, tuple[str, str]],
    resolver: BrainResolver | None = None,
    prior_work_receipts: Sequence[WorkReceipt] = (),
    receipt_sink: Callable[[WorkReceipt], None] | None = None,
    thought_path: CodingThoughtPath | None = None,
    agent_temperature: float = 0.2,
    process_temperature: float = 0.1,
    decision_observer: Callable[[Mapping[str, Any]], None] | None = None,
    response_stop_sequences: Sequence[str] = (),
    agent_system_prompt_suffix: str = "",
    process_system_prompt_suffix: str = "",
) -> InternalCodingWorkforce:
    """Provision an exact role/process topology with proven, non-authoritative brains."""

    role_lanes = dict(role_brain_lanes)
    process_bindings = dict(process_brain_bindings)
    if not role_lanes or not process_bindings:
        raise WorkforceHold("brain_topology_empty")
    role_process_bindings: Dict[str, str] = {}
    for process_id, binding in process_bindings.items():
        if not isinstance(binding, tuple) or len(binding) != 2:
            raise WorkforceHold("process_brain_binding_invalid")
        lane, owner = binding
        if owner not in role_lanes or lane != role_lanes[owner] or owner in role_process_bindings:
            raise WorkforceHold("process_brain_binding_mismatch")
        role_process_bindings[owner] = process_id
    if set(role_process_bindings) != set(role_lanes):
        raise WorkforceHold("each_role_requires_one_process_brain")
    for value, label in (
        (agent_temperature, "agent_temperature"),
        (process_temperature, "process_temperature"),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 2.0
        ):
            raise WorkforceHold(f"{label}_must_be_between_zero_and_two")
    agent_suffix = str(agent_system_prompt_suffix or "").strip()
    process_suffix = str(process_system_prompt_suffix or "").strip()
    if len(agent_suffix) > 2_048 or len(process_suffix) > 2_048:
        raise WorkforceHold("bounded_system_prompt_suffix_required")

    resolver = resolver or OllamaSwitchboardBrainResolver()
    resolved_by_nerve: Dict[tuple[str, str], ResolvedBrain | None] = {}

    def resolved(lane: str, nerve_id: str) -> ResolvedBrain | None:
        key = (lane, nerve_id)
        if key not in resolved_by_nerve:
            try:
                resolve_for = getattr(resolver, "resolve_for", None)
                resolved_by_nerve[key] = (
                    resolve_for(lane, nerve_id=nerve_id)
                    if callable(resolve_for)
                    else resolver.resolve(lane)
                )
            except Exception:
                resolved_by_nerve[key] = None
        return resolved_by_nerve[key]

    agents: Dict[str, Agent] = {}
    process_brains: Dict[str, Agent] = {}
    passports: list[BrainPassport] = []
    for role, lane in role_lanes.items():
        brain = resolved(lane, f"agent:{role}")
        passport = _issue_brain_passport("agent", role, lane, brain)
        passports.append(passport)
        if passport.brain_ready and brain and brain.adapter:
            agents[role] = Agent(
                brain.adapter,
                config=AgentConfig(
                    name=role,
                    system_prompt=(
                        f"You are Aureon's {role}. Make bounded coding decisions for Aureon itself. "
                        "Do not claim external actions and do not bypass governance or safety gates."
                        + (f"\n{agent_suffix}" if agent_suffix else "")
                    ),
                    max_turns=1,
                    max_tokens=INTERNAL_BRAIN_MAX_TOKENS,
                    temperature=float(agent_temperature),
                    tools_enabled=False,
                    metadata={
                        "brain_passport_id": passport.receipt_id,
                        "hnc_model_routing_receipt_id": passport.routing_receipt_id,
                        "hnc_receipt_id": passport.hnc_receipt_id,
                        "lane": lane,
                        "provider_mode": passport.provider_mode,
                    },
                ),
                tools=ToolRegistry(include_builtins=False),
            )
    for process_id, (lane, owner) in process_bindings.items():
        brain = resolved(lane, f"process:{process_id}")
        passport = _issue_brain_passport("process", process_id, lane, brain)
        passports.append(passport)
        if passport.brain_ready and brain and brain.adapter:
            process_brains[process_id] = Agent(
                brain.adapter,
                config=AgentConfig(
                    name=f"process:{process_id}",
                    system_prompt=(
                        f"You are the brain alongside Aureon's {process_id} process, accountable to {owner}. "
                        "Decide only within this process and return evidence for the governed coding route."
                        + (f"\n{process_suffix}" if process_suffix else "")
                    ),
                    max_turns=1,
                    max_tokens=INTERNAL_BRAIN_MAX_TOKENS,
                    temperature=float(process_temperature),
                    tools_enabled=False,
                    metadata={
                        "brain_passport_id": passport.receipt_id,
                        "hnc_model_routing_receipt_id": passport.routing_receipt_id,
                        "hnc_receipt_id": passport.hnc_receipt_id,
                        "lane": lane,
                        "owner": owner,
                        "provider_mode": passport.provider_mode,
                    },
                ),
                tools=ToolRegistry(include_builtins=False),
            )
    return InternalCodingWorkforce(
        agents=agents,
        process_brains=process_brains,
        passports=passports,
        role_brain_lanes=role_lanes,
        role_process_bindings=role_process_bindings,
        prior_work_receipts=prior_work_receipts,
        receipt_sink=receipt_sink,
        thought_path=thought_path,
        decision_observer=decision_observer,
        response_stop_sequences=response_stop_sequences,
    )


def provision_internal_coding_workforce(
    resolver: BrainResolver | None = None,
    *,
    prior_work_receipts: Sequence[WorkReceipt] = (),
    receipt_sink: Callable[[WorkReceipt], None] | None = None,
    thought_path: CodingThoughtPath | None = None,
) -> InternalCodingWorkforce:
    """Provision every declared coding seat and process with a proven brain."""

    return provision_brain_bound_workforce(
        role_brain_lanes=ROLE_BRAIN_LANES,
        process_brain_bindings=PROCESS_BRAIN_BINDINGS,
        resolver=resolver,
        prior_work_receipts=prior_work_receipts,
        receipt_sink=receipt_sink,
        thought_path=thought_path,
    )


__all__ = [
    "BRAIN_SCHEMA_VERSION",
    "CodingThoughtPath",
    "INTERNAL_ACTOR",
    "INTERNAL_BRAIN_MAX_TOKENS",
    "INTERNAL_AUTHOR_MAX_TOKENS",
    "LOCAL_SELF_CODER_PROVIDER_MODE",
    "MIN_INTERNAL_SHARE_PERCENT",
    "PROCESS_BRAIN_BINDINGS",
    "ROLE_PROCESS_BINDINGS",
    "ROLE_BRAIN_LANES",
    "SCHEMA_VERSION",
    "SENIOR_OVERSIGHT_ACTOR",
    "SENIOR_OVERSIGHT_STAGES",
    "SELF_CODER_TRANSPORT_PREFLIGHT_SCHEMA",
    "SUPPORTED_HNC_PROVIDER_MODES",
    "TRUTH_GATED_THOUGHT_RECEIPT_PREFIX",
    "WORK_SCHEMA_VERSION",
    "BrainPassport",
    "BrainResolver",
    "InternalCodingWorkforce",
    "OllamaSwitchboardBrainResolver",
    "ResolvedBrain",
    "WorkReceipt",
    "WorkforceHold",
    "provision_brain_bound_workforce",
    "provision_internal_coding_workforce",
    "validate_brain_passport",
    "validate_work_receipt",
]
