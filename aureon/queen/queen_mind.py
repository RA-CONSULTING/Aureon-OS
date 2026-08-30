"""One process-owned, receipt-bound mind for every Queen faculty.

The repository contains many capable cognitive organs.  This module does not
replace them.  It seats them as evidence-only faculties, freezes their latest
signals into one observer context, and asks the existing cloud workforce to
run that context through Aureon's strict 10 -> 9 -> 1 thought path.  The one
coherent answer is then evaluated by the independent Council and Crown.

No faculty, model response, thought envelope, or ACCEPT receipt is an action
permit.  Approved action proposals are published for the existing guarded
tool/economic boundaries; this module never calls a tool or provider.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import threading
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from aureon.autonomous.aureon_internal_coding_workforce import (
    WorkReceipt,
    validate_work_receipt,
)
from aureon.governance.cognition_gate import evaluate_cognition_governance

SCHEMA_VERSION = "aureon.queen-mind.v1"
MANIFEST_SCHEMA = "aureon.queen-faculty-manifest.v1"
FACULTY_RECEIPT_SCHEMA = "aureon.queen-faculty-signal.v1"
THOUGHT_SCHEMA = "aureon.queen-thought-envelope.v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
PHI_SQUARED_SECONDS = 2.618033988749895
MAX_SIGNAL_BYTES = 64 * 1024
MAX_SOURCE_RECEIPTS = 64
REQUIRED_COGNITIVE_ROLES = frozenset(
    {"metacognition", "miner", "quantum", "knowledge"}
)
_FACTORY_TOKEN = object()
_HEX_64 = frozenset("0123456789abcdef")
_EXCLUDED_PARTS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        "archive",
        "archives",
        "build",
        "dist",
        "imports",
        "node_modules",
        "tests",
        "venv",
    }
)
_FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "economic_mutation": False,
}
_AUTHORITY_TOKENS = (
    "place_market_order",
    "place_order",
    "submit_order",
    "cancel_order",
    "close_position",
    "autonomous_execute",
    "execute_shell",
    "session.post",
    "requests.post",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    material = value if isinstance(value, str) else _canonical_json(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    return value.strip()


def _digest(value: Any, label: str) -> str:
    result = _nonblank(value, label).lower()
    if len(result) != 64 or any(char not in _HEX_64 for char in result):
        raise ValueError(f"{label}_must_be_sha256")
    return result


def _json_copy(value: Any, label: str) -> Any:
    try:
        encoded = _canonical_json(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}_must_be_canonical_json") from exc
    if len(encoded.encode("utf-8")) > MAX_SIGNAL_BYTES:
        raise ValueError(f"{label}_exceeds_limit")
    return json.loads(encoded)


def _receipt(prefix: str, causal: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(causal)
    payload["receipt_id"] = f"{prefix}{_sha256(causal)}"
    return payload


def _module_name(relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _is_faculty_source(relative: Path) -> bool:
    parts = {part.casefold() for part in relative.parts}
    if parts & _EXCLUDED_PARTS:
        return False
    folded = relative.as_posix().casefold()
    if any(part in parts for part in {"queen", "miner"}):
        return True
    if "aureon/vault/voice/" in folded:
        return True
    return any(
        token in relative.stem.casefold()
        for token in (
            "metacogn",
            "conscious",
            "knowledge",
            "meaning",
            "mycelium",
            "quantum",
            "research",
            "self_question",
            "self_introspect",
            "soul",
            "wisdom",
        )
    )


def _faculty_role(relative: Path) -> str:
    folded = relative.as_posix().casefold()
    stem = relative.stem.casefold()
    if "miner" in folded:
        return "miner"
    if "quantum" in folded or "probability" in folded:
        return "quantum"
    if any(
        token in folded
        for token in (
            "knowledge",
            "meaning",
            "research",
            "vault",
            "wisdom",
        )
    ):
        return "knowledge"
    if any(
        token in folded
        for token in (
            "metacogn",
            "conscious",
            "self_question",
            "self_introspect",
            "source_law",
        )
    ):
        return "metacognition"
    if any(token in stem for token in ("soul", "affect", "emotion", "heart")):
        return "affect"
    if "memory" in folded or "dream" in folded:
        return "memory"
    return "queen_faculty"


def _entrypoints(tree: ast.Module) -> tuple[str, ...]:
    names = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return tuple(sorted(names)) or ("module",)


@dataclass(frozen=True, slots=True)
class QueenFacultyDescriptor:
    faculty_id: str
    source_file: str
    module_name: str
    source_sha256: str
    role: str
    effect_class: str
    entrypoints: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.faculty_id.startswith("queen-faculty:"):
            raise ValueError("queen_faculty_id_required")
        _nonblank(self.source_file, "faculty_source_file")
        _nonblank(self.module_name, "faculty_module_name")
        _digest(self.source_sha256, "faculty_source_sha256")
        if self.role not in {
            "affect",
            "knowledge",
            "memory",
            "metacognition",
            "miner",
            "quantum",
            "queen_faculty",
        }:
            raise ValueError("recognized_queen_faculty_role_required")
        if self.effect_class not in {"advisory", "legacy_authority_capable"}:
            raise ValueError("recognized_queen_faculty_effect_required")
        if not self.entrypoints or self.entrypoints != tuple(
            sorted(set(self.entrypoints))
        ):
            raise ValueError("sorted_unique_faculty_entrypoints_required")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["entrypoints"] = list(self.entrypoints)
        return result


@dataclass(frozen=True, slots=True)
class QueenFacultyManifest:
    faculties: tuple[QueenFacultyDescriptor, ...]
    manifest_id: str
    schema: str = MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        ids = [item.faculty_id for item in self.faculties]
        modules = [item.module_name for item in self.faculties]
        if (
            self.schema != MANIFEST_SCHEMA
            or not self.faculties
            or ids != sorted(set(ids))
            or len(modules) != len(set(modules))
        ):
            raise ValueError("sorted_unique_queen_faculty_manifest_required")
        if not REQUIRED_COGNITIVE_ROLES.issubset(
            {item.role for item in self.faculties}
        ):
            raise ValueError("complete_queen_cognitive_roles_required")
        if self.manifest_id != f"queen-faculty-manifest:{_sha256(self.payload())}":
            raise ValueError("queen_faculty_manifest_id_mismatch")

    def payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "faculties": [item.to_dict() for item in self.faculties],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "manifest_id": self.manifest_id}

    def report(self) -> dict[str, Any]:
        roles: dict[str, int] = {}
        effects: dict[str, int] = {}
        for item in self.faculties:
            roles[item.role] = roles.get(item.role, 0) + 1
            effects[item.effect_class] = effects.get(item.effect_class, 0) + 1
        return {
            "schema": SCHEMA_VERSION,
            "status": "seated",
            "manifest_id": self.manifest_id,
            "faculty_count": len(self.faculties),
            "roles": dict(sorted(roles.items())),
            "effects": dict(sorted(effects.items())),
            "required_roles": sorted(REQUIRED_COGNITIVE_ROLES),
            "action_eligible": False,
            "economic_mutation": False,
        }


def discover_queen_faculty_manifest(
    root: Path = REPO_ROOT,
) -> QueenFacultyManifest:
    """Discover every cognitive source without importing or executing it."""

    root = Path(root).resolve()
    descriptors: list[QueenFacultyDescriptor] = []
    for path in sorted(root.rglob("*.py")):
        try:
            relative = path.resolve().relative_to(root)
        except ValueError:
            continue
        if not _is_faculty_source(relative):
            continue
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=relative.as_posix())
        except SyntaxError as exc:
            raise ValueError(
                f"queen_faculty_source_parse_failed:{relative.as_posix()}"
            ) from exc
        source_file = relative.as_posix()
        descriptors.append(
            QueenFacultyDescriptor(
                faculty_id="queen-faculty:"
                + hashlib.sha256(source_file.encode("utf-8")).hexdigest(),
                source_file=source_file,
                module_name=_module_name(relative),
                source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
                role=_faculty_role(relative),
                effect_class=(
                    "legacy_authority_capable"
                    if any(token in source.casefold() for token in _AUTHORITY_TOKENS)
                    else "advisory"
                ),
                entrypoints=_entrypoints(tree),
            )
        )
    faculties = tuple(sorted(descriptors, key=lambda item: item.faculty_id))
    payload = {
        "schema": MANIFEST_SCHEMA,
        "faculties": [item.to_dict() for item in faculties],
    }
    return QueenFacultyManifest(
        faculties=faculties,
        manifest_id=f"queen-faculty-manifest:{_sha256(payload)}",
    )


@runtime_checkable
class QueenMindWorkforce(Protocol):
    def process_id_for_role(self, role: str) -> str: ...

    def decide(self, **kwargs: Any) -> tuple[str, Any]: ...


@runtime_checkable
class QueenMindComposition(Protocol):
    governance: Any

    def status(self) -> Mapping[str, Any]: ...


@runtime_checkable
class QueenMindConscience(Protocol):
    def ask_why(
        self,
        action: str,
        context: Mapping[str, Any] | None = None,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class QueenThoughtResult:
    thought: str
    envelope: Mapping[str, Any]


def validate_faculty_signal_receipt(
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    expected = {
        "schema",
        "faculty_id",
        "faculty_manifest_id",
        "module_name",
        "role",
        "signal",
        "signal_digest",
        "source_receipt_ids",
        "truth_status",
        "generated_values",
        *_FALSE_FLAGS,
        "receipt_id",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != expected:
        raise ValueError("exact_queen_faculty_signal_receipt_required")
    if receipt.get("schema") != FACULTY_RECEIPT_SCHEMA:
        raise ValueError("queen_faculty_signal_schema_mismatch")
    if any(receipt.get(key) is not value for key, value in _FALSE_FLAGS.items()):
        raise ValueError("queen_faculty_signal_is_evidence_only")
    if receipt.get("generated_values") is not False:
        raise ValueError("queen_faculty_signal_generated_values_forbidden")
    signal = _json_copy(receipt.get("signal"), "faculty_signal")
    if receipt.get("signal_digest") != _sha256(signal):
        raise ValueError("queen_faculty_signal_digest_mismatch")
    ids = receipt.get("source_receipt_ids")
    if (
        not isinstance(ids, list)
        or len(ids) > MAX_SOURCE_RECEIPTS
        or ids != sorted(set(ids))
        or any(not isinstance(item, str) or not item.strip() for item in ids)
    ):
        raise ValueError("sorted_unique_faculty_source_receipts_required")
    truth = "source_bound_context" if ids else "no_data"
    if receipt.get("truth_status") != truth:
        raise ValueError("faculty_signal_truth_status_mismatch")
    causal = {key: receipt[key] for key in receipt if key != "receipt_id"}
    if receipt.get("receipt_id") != f"queen-faculty-signal:{_sha256(causal)}":
        raise ValueError("queen_faculty_signal_receipt_id_mismatch")
    return dict(receipt)


def validate_queen_thought_envelope(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    expected = {
        "schema",
        "stage",
        "decision",
        "reason",
        "cycle_id",
        "created_at",
        "trigger",
        "observer_context_digest",
        "faculty_manifest_id",
        "faculty_receipts",
        "missing_required_roles",
        "thought",
        "thought_digest",
        "work_receipt_id",
        "thought_path_receipt_id",
        "governance_receipt",
        "action_proposal",
        "action_dispatch_status",
        "truth_status",
        "generated_values",
        *_FALSE_FLAGS,
        "receipt_id",
    }
    if not isinstance(envelope, Mapping) or set(envelope) != expected:
        raise ValueError("exact_queen_thought_envelope_required")
    if envelope.get("schema") != THOUGHT_SCHEMA:
        raise ValueError("queen_thought_envelope_schema_mismatch")
    if any(envelope.get(key) is not value for key, value in _FALSE_FLAGS.items()):
        raise ValueError("queen_thought_is_evidence_only")
    if envelope.get("generated_values") is not False:
        raise ValueError("queen_thought_generated_values_forbidden")
    if envelope.get("stage") not in {"HELD", "ABORTED", "APPROVED"}:
        raise ValueError("recognized_queen_thought_stage_required")
    if envelope.get("decision") not in {"HOLD", "ABORT", "ACCEPT"}:
        raise ValueError("recognized_queen_thought_decision_required")
    created = envelope.get("created_at")
    if isinstance(created, bool) or not isinstance(created, (int, float)):
        raise ValueError("finite_queen_thought_time_required")
    if not math.isfinite(float(created)) or float(created) <= 0:
        raise ValueError("finite_queen_thought_time_required")
    thought = envelope.get("thought")
    if not isinstance(thought, str):
        raise ValueError("queen_thought_text_required")
    if envelope.get("thought_digest") != _sha256(thought):
        raise ValueError("queen_thought_digest_mismatch")
    receipts = envelope.get("faculty_receipts")
    if not isinstance(receipts, list):
        raise ValueError("queen_faculty_receipts_required")
    validated = [validate_faculty_signal_receipt(item) for item in receipts]
    if [item["faculty_id"] for item in validated] != sorted(
        item["faculty_id"] for item in validated
    ):
        raise ValueError("sorted_queen_faculty_receipts_required")
    governance = envelope.get("governance_receipt")
    if envelope["stage"] == "APPROVED":
        if (
            envelope["decision"] != "ACCEPT"
            or not isinstance(governance, Mapping)
            or governance.get("decision") != "ACCEPT"
            or not governance.get("receipt_id")
        ):
            raise ValueError("approved_queen_thought_requires_dual_key_accept")
    elif envelope.get("action_proposal") is not None:
        raise ValueError("held_queen_thought_cannot_release_action_proposal")
    causal = {key: envelope[key] for key in envelope if key != "receipt_id"}
    if envelope.get("receipt_id") != f"queen-thought:{_sha256(causal)}":
        raise ValueError("queen_thought_receipt_id_mismatch")
    return dict(envelope)


class QueenMind:
    """Canonical converger for advisory faculties and governed thought."""

    def __init__(
        self,
        *,
        _factory_token: object,
        composition: QueenMindComposition,
        workforce: QueenMindWorkforce,
        conscience: QueenMindConscience,
        manifest: QueenFacultyManifest,
        bus: Any = None,
        clock: Any = time.time,
        interval_s: float = PHI_SQUARED_SECONDS,
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_queen_mind")
        if not isinstance(composition, QueenMindComposition):
            raise TypeError("canonical_organism_composition_required")
        if not isinstance(workforce, QueenMindWorkforce):
            raise TypeError("canonical_queen_mind_workforce_required")
        if not isinstance(conscience, QueenMindConscience):
            raise TypeError("queen_conscience_required")
        if not isinstance(manifest, QueenFacultyManifest):
            raise TypeError("queen_faculty_manifest_required")
        if not callable(clock):
            raise TypeError("queen_mind_clock_required")
        if isinstance(interval_s, bool) or not isinstance(interval_s, (int, float)):
            raise ValueError("positive_queen_mind_interval_required")
        if not math.isfinite(float(interval_s)) or float(interval_s) <= 0:
            raise ValueError("positive_queen_mind_interval_required")
        self._composition = composition
        self._workforce = workforce
        self._conscience = conscience
        self._manifest = manifest
        self._by_module = {item.module_name: item for item in manifest.faculties}
        self._bus = bus
        self._clock = clock
        self._interval_s = float(interval_s)
        self._latest: dict[str, dict[str, Any]] = {}
        self._thoughts: deque[dict[str, Any]] = deque(maxlen=256)
        self._signal_version = 0
        self._cycled_version = 0
        self._running = False
        self._subscribed = False
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

    @property
    def manifest(self) -> QueenFacultyManifest:
        return self._manifest

    def status(self) -> dict[str, Any]:
        composition = dict(self._composition.status())
        with self._lock:
            observed_roles = {
                receipt["role"] for receipt in self._latest.values()
            }
            observed_count = len(self._latest)
            thought_count = len(self._thoughts)
            running = self._running
        missing = sorted(REQUIRED_COGNITIVE_ROLES - observed_roles)
        ready = composition.get("status") == "ready"
        return {
            "schema": SCHEMA_VERSION,
            "status": "ready" if ready else "hold",
            "reason": None if ready else "canonical_organism_composition_not_ready",
            "manifest_id": self._manifest.manifest_id,
            "faculty_count": len(self._manifest.faculties),
            "observed_faculty_count": observed_count,
            "missing_observed_roles": missing,
            "running": running,
            "thought_count": thought_count,
            "truth_status": "real_observed" if ready else "no_data",
            "generated_values": False,
            **_FALSE_FLAGS,
        }

    def submit_faculty_signal(
        self,
        *,
        module_name: str,
        signal: Mapping[str, Any],
        source_receipt_ids: tuple[str, ...] | list[str] = (),
    ) -> dict[str, Any]:
        descriptor = self._by_module.get(str(module_name or ""))
        if descriptor is None:
            raise ValueError("seated_queen_faculty_required")
        normalized_signal = _json_copy(dict(signal), "faculty_signal")
        ids = sorted({_nonblank(item, "source_receipt_id") for item in source_receipt_ids})
        if len(ids) > MAX_SOURCE_RECEIPTS:
            raise ValueError("too_many_faculty_source_receipts")
        causal = {
            "schema": FACULTY_RECEIPT_SCHEMA,
            "faculty_id": descriptor.faculty_id,
            "faculty_manifest_id": self._manifest.manifest_id,
            "module_name": descriptor.module_name,
            "role": descriptor.role,
            "signal": normalized_signal,
            "signal_digest": _sha256(normalized_signal),
            "source_receipt_ids": ids,
            "truth_status": "source_bound_context" if ids else "no_data",
            "generated_values": False,
            **_FALSE_FLAGS,
        }
        receipt = validate_faculty_signal_receipt(
            _receipt("queen-faculty-signal:", causal)
        )
        with self._lock:
            self._latest[descriptor.faculty_id] = receipt
            self._signal_version += 1
        return receipt

    def submit_action_proposal(
        self,
        *,
        module_name: str,
        proposal: Mapping[str, Any],
        source_receipt_ids: tuple[str, ...] | list[str] = (),
    ) -> dict[str, Any]:
        receipt = self.submit_faculty_signal(
            module_name=module_name,
            signal={"kind": "action_proposal", "proposal": dict(proposal)},
            source_receipt_ids=source_receipt_ids,
        )
        self._publish("queen.mind.action.proposed", receipt)
        return receipt

    def _hold(self, reason: str, trigger: str) -> QueenThoughtResult:
        now = float(self._clock())
        with self._lock:
            receipts = sorted(self._latest.values(), key=lambda item: item["faculty_id"])
        causal = {
            "schema": THOUGHT_SCHEMA,
            "stage": "HELD",
            "decision": "HOLD",
            "reason": reason,
            "cycle_id": f"queen-mind-cycle:{_sha256({'trigger': trigger, 'time': now})}",
            "created_at": now,
            "trigger": trigger,
            "observer_context_digest": _sha256(
                [item["receipt_id"] for item in receipts]
            ),
            "faculty_manifest_id": self._manifest.manifest_id,
            "faculty_receipts": receipts,
            "missing_required_roles": sorted(
                REQUIRED_COGNITIVE_ROLES
                - {item["role"] for item in receipts}
            ),
            "thought": "",
            "thought_digest": _sha256(""),
            "work_receipt_id": None,
            "thought_path_receipt_id": None,
            "governance_receipt": None,
            "action_proposal": None,
            "action_dispatch_status": "not_released",
            "truth_status": "no_data",
            "generated_values": False,
            **_FALSE_FLAGS,
        }
        envelope = validate_queen_thought_envelope(
            _receipt("queen-thought:", causal)
        )
        with self._lock:
            self._thoughts.append(envelope)
        self._publish("queen.mind.thought.held", envelope)
        return QueenThoughtResult(thought="", envelope=envelope)

    def think_once(self, trigger: str = "autonomous QueenMind cycle") -> QueenThoughtResult:
        trigger_text = _nonblank(trigger, "queen_mind_trigger")[:2000]
        if self.status()["status"] != "ready":
            return self._hold("canonical_organism_composition_not_ready", trigger_text)
        with self._lock:
            receipts = sorted(self._latest.values(), key=lambda item: item["faculty_id"])
        missing = REQUIRED_COGNITIVE_ROLES - {item["role"] for item in receipts}
        if missing:
            return self._hold("complete_cognitive_role_inputs_required", trigger_text)

        observer = {
            "schema": "aureon.queen-observer-context.v1",
            "trigger": trigger_text,
            "faculty_manifest_id": self._manifest.manifest_id,
            "faculty_receipts": [item["receipt_id"] for item in receipts],
            "signals": [
                {
                    "faculty_id": item["faculty_id"],
                    "role": item["role"],
                    "signal": item["signal"],
                    "truth_status": item["truth_status"],
                }
                for item in receipts
            ],
        }
        observer_digest = _sha256(observer)
        prompt = (
            "Form one concise, source-aware Queen thought from this frozen observer "
            "context. State uncertainty and contradictions. Do not claim authority, "
            "execute anything, or invent missing evidence.\n\n"
            + _canonical_json(observer)
        )
        try:
            process_id = self._workforce.process_id_for_role("CEO Goal Steward")
            thought, work = self._workforce.decide(
                subject_type="agent",
                subject_id="CEO Goal Steward",
                process_id=process_id,
                prompt=prompt,
                stage="queen_mind_thought",
                work_kind="queen_sentient_thought",
                max_tokens=600,
            )
            thought_text = _nonblank(thought, "queen_mind_thought")
            if (
                not isinstance(work, WorkReceipt)
                or not validate_work_receipt(work)
                or work.process_id != process_id
                or work.stage != "queen_mind_thought"
                or work.work_kind != "queen_sentient_thought"
                or work.input_digest
                != hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                or work.output_digest
                != hashlib.sha256(thought_text.encode("utf-8")).hexdigest()
            ):
                raise ValueError("exact_truth_gated_queen_work_receipt_required")
            work_dict = work.to_dict()
            work_receipt_id = _nonblank(work_dict.get("receipt_id"), "work_receipt_id")
            thought_path_receipt_id = _nonblank(
                work_dict.get("thought_path_receipt_id"),
                "thought_path_receipt_id",
            )
        except Exception:
            return self._hold("truth_gated_cloud_brain_unavailable", trigger_text)

        action_proposal = None
        for item in reversed(receipts):
            signal = item.get("signal", {})
            if signal.get("kind") == "action_proposal":
                action_proposal = _json_copy(
                    signal.get("proposal"), "queen_action_proposal"
                )
                break
        governance = getattr(self._composition, "governance", None)
        if governance is None:
            return self._hold("canonical_governance_bindings_required", trigger_text)
        try:
            whisper = self._conscience.ask_why(
                f"Evaluate QueenMind thought: {thought_text}",
                {
                    "observer_context_digest": observer_digest,
                    "faculty_receipt_ids": [item["receipt_id"] for item in receipts],
                    "action_proposal": action_proposal,
                },
            )
            queen_verdict = _nonblank(
                getattr(getattr(whisper, "verdict", None), "name", None),
                "queen_verdict",
            ).upper()
            acquisition = governance.acquisition_supplier.load_governance_acquisition()
            gate = evaluate_cognition_governance(
                prompt=prompt,
                answer=thought_text,
                queen_verdict=queen_verdict,
                queen_evaluated=True,
                council_receipt_supplier=governance.council_receipt_supplier,
                crown_receipt_supplier=governance.crown_receipt_supplier,
                capability={
                    "family": "queen_mind",
                    "effect": "proposal_only",
                    "observer_context_digest": observer_digest,
                },
                bake={
                    "faculty_manifest_id": self._manifest.manifest_id,
                    "faculty_receipt_ids": [item["receipt_id"] for item in receipts],
                    "work_receipt_id": work_receipt_id,
                    "thought_path_receipt_id": thought_path_receipt_id,
                },
                acquisition=acquisition,
                now=float(self._clock()),
            )
        except Exception:
            gate = {"decision": "HOLD", "receipt_id": None, "reason": "governance_unavailable"}

        decision = str(gate.get("decision") or "HOLD").upper()
        if decision not in {"ACCEPT", "ABORT", "HOLD"}:
            decision = "HOLD"
        stage = {"ACCEPT": "APPROVED", "ABORT": "ABORTED", "HOLD": "HELD"}[decision]
        released_action = action_proposal if decision == "ACCEPT" else None
        now = float(self._clock())
        causal = {
            "schema": THOUGHT_SCHEMA,
            "stage": stage,
            "decision": decision,
            "reason": gate.get("reason"),
            "cycle_id": f"queen-mind-cycle:{_sha256({'observer': observer_digest, 'work': work_receipt_id})}",
            "created_at": now,
            "trigger": trigger_text,
            "observer_context_digest": observer_digest,
            "faculty_manifest_id": self._manifest.manifest_id,
            "faculty_receipts": receipts,
            "missing_required_roles": [],
            "thought": thought_text,
            "thought_digest": _sha256(thought_text),
            "work_receipt_id": work_receipt_id,
            "thought_path_receipt_id": thought_path_receipt_id,
            "governance_receipt": _json_copy(gate, "governance_receipt"),
            "action_proposal": released_action,
            "action_dispatch_status": (
                "awaiting_guarded_route" if released_action is not None else "not_requested"
            ),
            "truth_status": "real_derived" if decision == "ACCEPT" else "no_data",
            "generated_values": False,
            **_FALSE_FLAGS,
        }
        envelope = validate_queen_thought_envelope(
            _receipt("queen-thought:", causal)
        )
        with self._lock:
            self._thoughts.append(envelope)
            self._cycled_version = self._signal_version
        self._publish(f"queen.mind.thought.{stage.casefold()}", envelope)
        if released_action is not None:
            self._publish("queen.mind.action.approved", envelope)
        return QueenThoughtResult(thought=thought_text, envelope=envelope)

    def start(self) -> dict[str, Any]:
        if self.status()["status"] != "ready":
            return self.status()
        with self._lock:
            if self._running:
                return self.status()
            self._running = True
        if self._bus is not None:
            try:
                self._bus.subscribe("*", self._on_bus_thought)
                self._subscribed = True
            except Exception:
                pass
        self._thread = threading.Thread(
            target=self._run_loop,
            name="QueenMind",
            daemon=True,
        )
        self._thread.start()
        return self.status()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(1.0, self._interval_s * 2))
        if self._bus is not None and self._subscribed:
            try:
                self._bus.unsubscribe("*", self._on_bus_thought)
            except Exception:
                pass
            self._subscribed = False

    def _run_loop(self) -> None:
        while self._running:
            time.sleep(self._interval_s)
            with self._lock:
                changed = self._signal_version > self._cycled_version
                roles = {item["role"] for item in self._latest.values()}
            if changed and REQUIRED_COGNITIVE_ROLES.issubset(roles):
                try:
                    self.think_once()
                except Exception:
                    continue

    @staticmethod
    def _topic_module(topic: str, source: str) -> str | None:
        folded = f"{source}.{topic}".casefold()
        routes = (
            (("miner.",), "aureon.miner.miner_inhouse_ai_bridge"),
            (("quantum",), "aureon.queen.queen_quantum_cognition"),
            (("knowledge.", "vault.", "research."), "aureon.queen.knowledge_interpreter"),
            (("queen.metacognition", "meta.reflection"), "aureon.queen.queen_metacognition"),
            (("queen.source_law",), "aureon.queen.queen_source_law"),
        )
        for markers, module in routes:
            if any(marker in folded for marker in markers):
                return module
        return None

    def _on_bus_thought(self, thought: Any) -> None:
        topic = str(getattr(thought, "topic", "") or "")
        source = str(getattr(thought, "source", "") or "")
        if topic.startswith("queen.mind."):
            return
        module = self._topic_module(topic, source)
        if module is None or module not in self._by_module:
            return
        payload = getattr(thought, "payload", {})
        if not isinstance(payload, Mapping):
            payload = {"value": str(payload)[:1000]}
        ids: list[str] = []
        for key in ("receipt_id", "source_receipt_id"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                ids.append(value.strip())
        raw_ids = payload.get("source_receipt_ids")
        if isinstance(raw_ids, list):
            ids.extend(item for item in raw_ids if isinstance(item, str) and item.strip())
        try:
            self.submit_faculty_signal(
                module_name=module,
                signal={"topic": topic, "source": source, "payload": dict(payload)},
                source_receipt_ids=sorted(set(ids)),
            )
        except (TypeError, ValueError):
            return

    def _publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        if self._bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought

            self._bus.publish(
                Thought(source="queen_mind", topic=topic, payload=dict(payload))
            )
        except Exception:
            return

    def recent_thoughts(self) -> tuple[Mapping[str, Any], ...]:
        with self._lock:
            return tuple(dict(item) for item in self._thoughts)


def bind_queen_mind(
    *,
    composition: QueenMindComposition,
    workforce: QueenMindWorkforce,
    conscience: QueenMindConscience,
    bus: Any = None,
    root: Path = REPO_ROOT,
    manifest: QueenFacultyManifest | None = None,
    clock: Any = time.time,
    interval_s: float = PHI_SQUARED_SECONDS,
) -> QueenMind:
    return QueenMind(
        _factory_token=_FACTORY_TOKEN,
        composition=composition,
        workforce=workforce,
        conscience=conscience,
        manifest=manifest or discover_queen_faculty_manifest(root),
        bus=bus,
        clock=clock,
        interval_s=interval_s,
    )


_MIND_LOCK = threading.RLock()
_MIND: QueenMind | None = None


def configure_canonical_queen_mind(mind: QueenMind) -> QueenMind:
    if not isinstance(mind, QueenMind):
        raise TypeError("canonical_queen_mind_required")
    global _MIND
    with _MIND_LOCK:
        _MIND = mind
    return mind


def get_canonical_queen_mind() -> QueenMind | None:
    with _MIND_LOCK:
        return _MIND


def reset_canonical_queen_mind_for_tests() -> None:
    global _MIND
    with _MIND_LOCK:
        if _MIND is not None:
            _MIND.stop()
        _MIND = None


__all__ = [
    "FACULTY_RECEIPT_SCHEMA",
    "MANIFEST_SCHEMA",
    "PHI_SQUARED_SECONDS",
    "QueenFacultyDescriptor",
    "QueenFacultyManifest",
    "QueenMind",
    "QueenThoughtResult",
    "REQUIRED_COGNITIVE_ROLES",
    "SCHEMA_VERSION",
    "THOUGHT_SCHEMA",
    "bind_queen_mind",
    "configure_canonical_queen_mind",
    "discover_queen_faculty_manifest",
    "get_canonical_queen_mind",
    "reset_canonical_queen_mind_for_tests",
    "validate_faculty_signal_receipt",
    "validate_queen_thought_envelope",
]
