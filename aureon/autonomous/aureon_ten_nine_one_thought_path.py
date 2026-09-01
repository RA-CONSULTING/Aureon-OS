"""Receipt-bound 10 -> 9 -> 1 thought path for every Aureon brain cell.

10 is the bounded, unformed prompt.  9 is the same prompt organized under one
fresh canonical HNC field.  1 is the exact answer released only while a fully
linked Auris cosmic state is open and coherent.  The coherent answer is then
delivered to both the Hive and Mycelia channels.

The path is evidence-only.  It never grants tool, route, accounting, learning,
or economic authority.  Missing, stale, drifting, or low-coherence evidence
raises :class:`TenNineOneHold` before a work receipt can be minted.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_hnc_evidence,
    validate_provider_moment,
)

SCHEMA_VERSION = "aureon.10-9-1.thought-path.v1"
VACUUM_SCHEMA = "aureon.10-9-1.vacuum.v1"
HNC_SCHEMA = "aureon.10-9-1.hnc-organization.v1"
AURIS_SCHEMA = "aureon.10-9-1.auris-answer.v1"
PROPAGATION_SCHEMA = "aureon.10-9-1.propagation.v1"
COMMITMENT_PROPAGATION_SCHEMA = "aureon.10-9-1.propagation-commitment.v1"
ACK_SCHEMA = "aureon.10-9-1.delivery-ack.v1"
SELF_CODER_CONFIDENTIAL_PREFLIGHT_SCHEMA = (
    "aureon-self-coder-thought-path-preflight-v2"
)

PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INVERSE = 1.0 / PHI
PHI_SQUARED = PHI * PHI
ACTIVE_COHERENCE_THRESHOLD = 0.80
LIGHTHOUSE_COHERENCE_THRESHOLD = 0.945

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_FALSE_FLAGS = {
    "operational_eligible": False,
    "provider_eligible": False,
    "action_eligible": False,
    "actionable": False,
    "economic_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "eligible_for_action": False,
    "eligible_for_accounting": False,
    "eligible_for_learning": False,
    "action_gate_passed": False,
}


class TenNineOneHold(RuntimeError):
    """The thought path could not prove a coherent 10 -> 9 -> 1 release."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    material = value if isinstance(value, str) else _canonical_json(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    result = value.strip()
    if len(result) > 65_536:
        raise ValueError(f"{label}_too_large")
    return result


def _digest(value: Any, label: str) -> str:
    result = _nonblank(value, label).lower()
    if not _HEX_64.fullmatch(result):
        raise ValueError(f"{label}_must_be_sha256")
    return result


def _finite(value: Any, label: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"finite_{label}_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"finite_{label}_required")
    return result


def _receipt(prefix: str, causal: Mapping[str, Any]) -> dict[str, Any]:
    return {**dict(causal), "receipt_id": f"{prefix}{_sha256(causal)}"}


def _require_false_flags(payload: Mapping[str, Any]) -> None:
    if any(payload.get(key) is not value for key, value in _FALSE_FLAGS.items()):
        raise ValueError("thought_path_is_evidence_only")


@dataclass(frozen=True)
class ThoughtPathRequest:
    subject_type: str
    subject_id: str
    process_id: str
    stage: str
    work_kind: str
    prompt_digest: str
    brain_passport_id: str


@dataclass(frozen=True)
class ThoughtPathResult:
    answer: str
    receipt: Mapping[str, Any]


@runtime_checkable
class TenNineOneEvidenceResolver(Protocol):
    """Composition-root trust boundary for raw HNC and Auris evidence."""

    resolver_id: str

    def resolve_hnc_evidence(self, request: ThoughtPathRequest) -> Mapping[str, Any] | None:
        """Return the complete raw HNC envelope for stage nine."""

    def resolve_auris_evidence(
        self,
        request: ThoughtPathRequest,
        *,
        answer_digest: str,
        hnc_receipt_id: str,
    ) -> Mapping[str, Any] | None:
        """Return a complete Auris state linked to the exact stage-nine HNC."""


@runtime_checkable
class TenNineOnePropagator(Protocol):
    """Evidence-only delivery boundary for the Hive and Mycelia."""

    propagator_id: str

    def propagate(
        self,
        *,
        answer: str,
        answer_receipt: Mapping[str, Any],
    ) -> Mapping[str, Mapping[str, Any]]:
        """Deliver the coherent answer and return exact Hive/Mycelia acknowledgements."""


class LocalHncAurisEvidenceResolver:
    """Read full local HNC/Auris envelopes without constructing their producers."""

    resolver_id = "aureon:local-hnc-auris-traces"

    def __init__(
        self,
        *,
        bus: Any = None,
        root: Path | None = None,
        require_active_pair: bool = False,
        active_wait_s: float = 0.0,
        pair_max_age_s: float = DEFAULT_MAX_AGE_S,
        pair_min_remaining_s: float = 0.0,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._bus = bus
        self._root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        if type(require_active_pair) is not bool:
            raise ValueError("require_active_pair_must_be_boolean")
        self._require_active_pair = require_active_pair
        self._active_wait_s = max(0.0, _finite(active_wait_s, "active_wait_s"))
        self._pair_max_age_s = _finite(pair_max_age_s, "pair_max_age_s")
        if self._pair_max_age_s <= 0:
            raise ValueError("positive_pair_max_age_required")
        self._pair_min_remaining_s = max(
            0.0,
            _finite(pair_min_remaining_s, "pair_min_remaining_s"),
        )
        if self._pair_min_remaining_s >= self._pair_max_age_s:
            raise ValueError("pair_freshness_headroom_must_be_below_max_age")
        self._clock = clock
        self._sleep = sleep

    @staticmethod
    def _latest_json_line(path: Path) -> dict[str, Any] | None:
        try:
            last = ""
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        last = line
            value = json.loads(last) if last else None
            return dict(value) if isinstance(value, Mapping) else None
        except (OSError, TypeError, ValueError):
            return None

    @staticmethod
    def _recent_json_lines(path: Path, *, limit: int = 200) -> list[dict[str, Any]]:
        """Read a bounded trace tail, preserving chronological row order."""
        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                if size > 2 * 1024 * 1024:
                    handle.seek(size - 2 * 1024 * 1024)
                    handle.readline()
                raw = handle.read().decode("utf-8", errors="replace")
        except OSError:
            return []
        rows: list[dict[str, Any]] = []
        for line in raw.splitlines():
            try:
                payload = json.loads(line)
            except (TypeError, ValueError):
                continue
            if isinstance(payload, Mapping):
                rows.append(dict(payload))
        return rows[-limit:]

    def _recent_bus_payloads(
        self,
        topic: str,
        *,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        try:
            bus = self._bus
            if bus is None:
                from aureon.core.aureon_thought_bus import get_thought_bus

                bus = get_thought_bus()
            rows = bus.recall(topic, limit=limit) if bus is not None else []
            from aureon.core.aureon_thought_bus import payload_of

            payloads = []
            for row in rows:
                payload = payload_of(row)
                if isinstance(payload, Mapping):
                    payloads.append(dict(payload))
            return payloads
        except Exception:  # noqa: BLE001 - absence is a fail-closed value
            return []

    def _latest_bus_payload(self, topic: str) -> dict[str, Any] | None:
        rows = self._recent_bus_payloads(topic, limit=1)
        return rows[-1] if rows else None

    def _hnc_trace_path(self) -> Path:
        configured = os.environ.get("AUREON_HNC_TRACE_PATH")
        return Path(configured) if configured else self._root / "state" / "hnc_live_trace.jsonl"

    def _auris_trace_path(self) -> Path:
        configured_dir = os.environ.get("AUREON_BUS_TRACE_DIR")
        trace_root = Path(configured_dir) if configured_dir else self._root / "state"
        return trace_root / "auris_cosmic_state.jsonl"

    def resolve_hnc_evidence(self, request: ThoughtPathRequest) -> Mapping[str, Any] | None:
        del request
        deadline = self._clock() + self._active_wait_s
        while True:
            hnc_rows = self._recent_bus_payloads("symbolic.life.pulse")
            hnc_rows.extend(self._recent_json_lines(self._hnc_trace_path()))
            auris_rows = self._recent_bus_payloads("auris.throne.cosmic_state")
            auris_rows.extend(self._recent_json_lines(self._auris_trace_path()))

            # Choose the newest pair already observed together. This keeps one
            # immutable HNC moment stable while a slower Ollama inference runs,
            # even though the independent producers continue refreshing.
            by_receipt = {
                row.get("receipt_id"): row
                for row in hnc_rows
                if isinstance(row.get("receipt_id"), str)
            }
            pair: tuple[dict[str, Any], dict[str, Any]] | None = None
            for auris in reversed(auris_rows):
                linked = auris.get("hnc_receipt_id")
                if isinstance(linked, str) and linked in by_receipt:
                    pair = (dict(by_receipt[linked]), dict(auris))
                    break
            if pair is not None:
                if not self._require_active_pair:
                    return pair[0]
                try:
                    validate_provider_moment(
                        pair[0],
                        pair[1],
                        now=self._clock() + self._pair_min_remaining_s,
                        max_age_s=self._pair_max_age_s,
                    )
                    gamma = _finite(pair[1].get("coherence_gamma"), "auris_gamma")
                    if (
                        pair[1].get("gate_open") is True
                        and gamma >= ACTIVE_COHERENCE_THRESHOLD
                    ):
                        return pair[0]
                except (TypeError, ValueError):
                    pass
            if not self._require_active_pair or self._clock() >= deadline:
                return None if self._require_active_pair else (
                    dict(hnc_rows[-1]) if hnc_rows else None
                )
            self._sleep(min(2.0, max(0.0, deadline - self._clock())))

    def resolve_auris_evidence(
        self,
        request: ThoughtPathRequest,
        *,
        answer_digest: str,
        hnc_receipt_id: str,
    ) -> Mapping[str, Any] | None:
        del request, answer_digest
        rows = self._recent_bus_payloads("auris.throne.cosmic_state")
        rows.extend(self._recent_json_lines(self._auris_trace_path()))
        for live in reversed(rows):
            if live.get("hnc_receipt_id") == hnc_receipt_id:
                return dict(live)
        return None


def build_delivery_ack(
    *,
    channel: str,
    destination_id: str,
    answer_receipt_id: str,
    delivery_digest: str,
) -> dict[str, Any]:
    """Build a deterministic, evidence-only acknowledgement after actual delivery."""

    channel_name = _nonblank(channel, "channel").lower()
    if channel_name not in {"hive", "mycelia"}:
        raise ValueError("unknown_10_9_1_delivery_channel")
    causal = {
        "schema_version": ACK_SCHEMA,
        "channel": channel_name,
        "destination_id": _nonblank(destination_id, "destination_id"),
        "answer_receipt_id": _nonblank(answer_receipt_id, "answer_receipt_id"),
        "delivery_digest": _digest(delivery_digest, "delivery_digest"),
        **_FALSE_FLAGS,
    }
    return _receipt("thought:10-9-1:ack:", causal)


def validate_delivery_ack(
    ack: Mapping[str, Any],
    *,
    channel: str,
    answer_receipt_id: str,
) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "channel",
        "destination_id",
        "answer_receipt_id",
        "delivery_digest",
        *_FALSE_FLAGS,
        "receipt_id",
    }
    if not isinstance(ack, Mapping) or set(ack) != expected_keys:
        raise ValueError("exact_10_9_1_delivery_ack_required")
    _require_false_flags(ack)
    if (
        ack.get("schema_version") != ACK_SCHEMA
        or ack.get("channel") != channel
        or ack.get("answer_receipt_id") != answer_receipt_id
    ):
        raise ValueError("10_9_1_delivery_binding_mismatch")
    _nonblank(ack.get("destination_id"), "destination_id")
    _digest(ack.get("delivery_digest"), "delivery_digest")
    causal = {key: ack[key] for key in expected_keys - {"receipt_id"}}
    if ack.get("receipt_id") != f"thought:10-9-1:ack:{_sha256(causal)}":
        raise ValueError("10_9_1_delivery_ack_hash_mismatch")
    return dict(ack)


class ThoughtBusHiveMyceliaPropagator:
    """Deliver to exact Hive/Mycelia topics and verify local plus trace read-back."""

    propagator_id = "aureon:thought-bus-hive-mycelia"
    _CHANNELS = {
        "hive": ("hive.10_9_1.coherent_answer", "braincell_10_9_1_hive"),
        "mycelia": ("mycelia.10_9_1.coherent_answer", "braincell_10_9_1_mycelia"),
    }

    def __init__(self, *, bus: Any = None) -> None:
        self._bus = bus

    def propagate(
        self,
        *,
        answer: str,
        answer_receipt: Mapping[str, Any],
    ) -> Mapping[str, Mapping[str, Any]]:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus, payload_of
        from aureon.core.bus_trace import append_trace, read_trace_latest

        bus = self._bus if self._bus is not None else get_thought_bus()
        if bus is None or not hasattr(bus, "publish") or not hasattr(bus, "recall"):
            raise TenNineOneHold("hive_mycelia_bus_unavailable")
        answer_text = _nonblank(answer, "answer")
        answer_id = _nonblank(answer_receipt.get("receipt_id"), "answer_receipt_id")
        payload = {
            "schema_version": PROPAGATION_SCHEMA,
            "answer": answer_text,
            "answer_digest": _sha256(answer_text),
            "answer_receipt_id": answer_id,
            **_FALSE_FLAGS,
        }
        acknowledgements: dict[str, Mapping[str, Any]] = {}
        for channel, (topic, trace_name) in self._CHANNELS.items():
            bus.publish(Thought(source="aureon_10_9_1", topic=topic, payload=dict(payload)))
            rows = bus.recall(topic, limit=1) or []
            recalled = payload_of(rows[-1]) if rows else None
            if not isinstance(recalled, Mapping) or dict(recalled) != payload:
                raise TenNineOneHold(f"{channel}_delivery_readback_failed")
            append_trace(trace_name, dict(payload))
            traced = read_trace_latest(trace_name)
            if not isinstance(traced, Mapping):
                raise TenNineOneHold(f"{channel}_trace_readback_failed")
            traced_payload = {key: traced.get(key) for key in payload}
            if traced_payload != payload:
                raise TenNineOneHold(f"{channel}_trace_binding_mismatch")
            acknowledgements[channel] = build_delivery_ack(
                channel=channel,
                destination_id=f"aureon:{channel}:thought-bus-and-trace",
                answer_receipt_id=answer_id,
                delivery_digest=_sha256(payload),
            )
        return acknowledgements


class CommitmentOnlyHiveMyceliaPropagator:
    """Propagate only an answer commitment for confidential coding material.

    The raw answer is accepted only long enough to calculate its SHA-256
    commitment.  Neither the ThoughtBus payload nor either durable trace row
    contains the answer.  Dedicated topics prevent consumers of the historical
    plaintext channel from mistaking a commitment for disclosed content.
    """

    propagator_id = "aureon:thought-bus-hive-mycelia-commitment-only"
    confidential_output_propagation = True
    _CHANNELS = {
        "hive": (
            "hive.10_9_1.coherent_answer_commitment",
            "braincell_10_9_1_hive_commitment",
        ),
        "mycelia": (
            "mycelia.10_9_1.coherent_answer_commitment",
            "braincell_10_9_1_mycelia_commitment",
        ),
    }

    def __init__(
        self,
        *,
        bus: Any = None,
        append_trace_fn: Callable[[str, dict[str, Any]], None] | None = None,
        read_trace_latest_fn: Callable[[str], Mapping[str, Any] | None] | None = None,
    ) -> None:
        self._bus = bus
        self._append_trace = append_trace_fn
        self._read_trace_latest = read_trace_latest_fn

    def propagate(
        self,
        *,
        answer: str,
        answer_receipt: Mapping[str, Any],
    ) -> Mapping[str, Mapping[str, Any]]:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus, payload_of
        from aureon.core.bus_trace import append_trace, read_trace_latest

        bus = self._bus if self._bus is not None else get_thought_bus()
        if bus is None or not hasattr(bus, "publish") or not hasattr(bus, "recall"):
            raise TenNineOneHold("hive_mycelia_bus_unavailable")
        answer_text = _nonblank(answer, "answer")
        answer_id = _nonblank(answer_receipt.get("receipt_id"), "answer_receipt_id")
        answer_digest = _sha256(answer_text)
        if answer_receipt.get("answer_digest") != answer_digest:
            raise TenNineOneHold("answer_commitment_receipt_mismatch")
        payload = {
            "schema_version": COMMITMENT_PROPAGATION_SCHEMA,
            "answer_digest": answer_digest,
            "answer_receipt_id": answer_id,
            "content_disclosure": "commitment_only",
            "raw_answer_retained": False,
            **_FALSE_FLAGS,
        }
        acknowledgements: dict[str, Mapping[str, Any]] = {}
        trace_append = self._append_trace or append_trace
        trace_read_latest = self._read_trace_latest or read_trace_latest
        for channel, (topic, trace_name) in self._CHANNELS.items():
            bus.publish(
                Thought(
                    source="aureon_10_9_1_confidential",
                    topic=topic,
                    payload=dict(payload),
                )
            )
            rows = bus.recall(topic, limit=1) or []
            recalled = payload_of(rows[-1]) if rows else None
            if not isinstance(recalled, Mapping) or dict(recalled) != payload:
                raise TenNineOneHold(f"{channel}_commitment_delivery_readback_failed")
            trace_append(trace_name, dict(payload))
            traced = trace_read_latest(trace_name)
            if not isinstance(traced, Mapping):
                raise TenNineOneHold(f"{channel}_commitment_trace_readback_failed")
            traced_payload = {key: traced.get(key) for key in payload}
            if traced_payload != payload:
                raise TenNineOneHold(f"{channel}_commitment_trace_binding_mismatch")
            acknowledgements[channel] = build_delivery_ack(
                channel=channel,
                destination_id=f"aureon:{channel}:commitment-bus-and-trace",
                answer_receipt_id=answer_id,
                delivery_digest=_sha256(payload),
            )
        return acknowledgements


class TenNineOneThoughtPath:
    """Run one inference through vacuum, HNC, Auris, Hive, and Mycelia."""

    def __init__(
        self,
        *,
        resolver: TenNineOneEvidenceResolver,
        propagator: TenNineOnePropagator,
        max_age_s: float = DEFAULT_MAX_AGE_S,
        now: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(resolver, TenNineOneEvidenceResolver):
            raise ValueError("trusted_10_9_1_evidence_resolver_required")
        if not isinstance(propagator, TenNineOnePropagator):
            raise ValueError("10_9_1_hive_mycelia_propagator_required")
        self._resolver = resolver
        self._propagator = propagator
        self._max_age_s = _finite(max_age_s, "max_age_s")
        if self._max_age_s <= 0:
            raise ValueError("positive_max_age_required")
        self._now = now
        self._receipts: list[Mapping[str, Any]] = []

    @property
    def receipts(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(dict(item) for item in self._receipts)

    def execute(
        self,
        *,
        request: ThoughtPathRequest,
        prompt: str,
        infer: Callable[[str], str],
        correction_attempt: int = 0,
    ) -> ThoughtPathResult:
        if correction_attempt != 0:
            raise TenNineOneHold("correction_attempt_requires_truth_gated_path")
        if not isinstance(request, ThoughtPathRequest):
            raise TenNineOneHold("10_9_1_request_required")
        prompt_text = _nonblank(prompt, "prompt")
        prompt_digest = _digest(request.prompt_digest, "prompt_digest")
        if _sha256(prompt_text) != prompt_digest:
            raise TenNineOneHold("10_9_1_prompt_digest_mismatch")
        vacuum = _receipt(
            "thought:10-9-1:vacuum:",
            {
                "schema_version": VACUUM_SCHEMA,
                "stage": 10,
                "state": "bounded_unformed_thought",
                "subject_type": _nonblank(request.subject_type, "subject_type"),
                "subject_id": _nonblank(request.subject_id, "subject_id"),
                "process_id": _nonblank(request.process_id, "process_id"),
                "prompt_digest": prompt_digest,
                "brain_passport_id": _nonblank(request.brain_passport_id, "brain_passport_id"),
                **_FALSE_FLAGS,
            },
        )
        raw_hnc = self._resolver.resolve_hnc_evidence(request)
        # A production resolver may deliberately wait for the next fresh,
        # gate-open active pair. Validate against the clock *after* that wait;
        # the timestamp captured before resolver pacing would falsely classify
        # newly issued evidence as future-dated.
        hnc_now = _finite(self._now(), "now")
        try:
            hnc = validate_hnc_evidence(
                raw_hnc or {},
                now=hnc_now,
                max_age_s=self._max_age_s,
            )
        except (TypeError, ValueError) as exc:
            raise TenNineOneHold("stage_9_fresh_canonical_hnc_required") from exc
        hnc_gamma = _finite(hnc.get("coherence_gamma"), "hnc_gamma")
        hnc_stage = _receipt(
            "thought:10-9-1:hnc:",
            {
                "schema_version": HNC_SCHEMA,
                "stage": 9,
                "state": "hnc_organized",
                "vacuum_receipt_id": vacuum["receipt_id"],
                "prompt_digest": prompt_digest,
                "hnc_receipt_id": hnc["receipt_id"],
                "hnc_input_receipt_ids": list(hnc["input_receipt_ids"]),
                "hnc_source_timestamp": hnc["source_timestamp"],
                "hnc_gamma": hnc_gamma,
                "phi": PHI,
                "phi_inverse": PHI_INVERSE,
                "phi_squared": PHI_SQUARED,
                **_FALSE_FLAGS,
            },
        )
        organized_prompt = (
            "Follow Aureon's 10-9-1 path. The bounded thought is now organized by "
            f"canonical HNC receipt {hnc['receipt_id']}. Give one logically coherent answer.\n\n"
            f"Original prompt digest: {prompt_digest}\nOriginal prompt:\n{prompt_text}"
        )
        response = _nonblank(infer(organized_prompt), "answer")
        answer_digest = _sha256(response)
        raw_auris = self._resolver.resolve_auris_evidence(
            request,
            answer_digest=answer_digest,
            hnc_receipt_id=hnc["receipt_id"],
        )
        try:
            moment = validate_provider_moment(
                hnc,
                raw_auris or {},
                now=_finite(self._now(), "now"),
                max_age_s=self._max_age_s,
            )
        except (TypeError, ValueError) as exc:
            raise TenNineOneHold("stage_1_linked_auris_evidence_required") from exc
        if moment.hnc_receipt_id != hnc["receipt_id"]:
            raise TenNineOneHold("hnc_changed_during_inference")
        auris_gamma = _finite((raw_auris or {}).get("coherence_gamma"), "auris_gamma")
        if (raw_auris or {}).get("gate_open") is not True:
            raise TenNineOneHold("auris_gate_closed")
        if auris_gamma < ACTIVE_COHERENCE_THRESHOLD:
            raise TenNineOneHold("auris_answer_coherence_below_active_band")
        coherence_band = "LIGHTHOUSE" if auris_gamma >= LIGHTHOUSE_COHERENCE_THRESHOLD else "ACTIVE"
        answer_receipt = _receipt(
            "thought:10-9-1:answer:",
            {
                "schema_version": AURIS_SCHEMA,
                "stage": 1,
                "state": "one_coherent_answer",
                "hnc_stage_receipt_id": hnc_stage["receipt_id"],
                "answer_digest": answer_digest,
                "hnc_receipt_id": moment.hnc_receipt_id,
                "auris_receipt_id": moment.auris_receipt_id,
                "provider_receipt_ids": list(moment.provider_receipt_ids),
                "provider_moment_digest": moment.provider_moment_digest,
                "provider_source_timestamp": moment.source_timestamp,
                "auris_gamma": auris_gamma,
                "coherence_band": coherence_band,
                "coherence_threshold": ACTIVE_COHERENCE_THRESHOLD,
                "auris_gate_open": True,
                **_FALSE_FLAGS,
            },
        )
        delivered = self._propagator.propagate(answer=response, answer_receipt=answer_receipt)
        if not isinstance(delivered, Mapping) or set(delivered) != {"hive", "mycelia"}:
            raise TenNineOneHold("hive_and_mycelia_acknowledgements_required")
        hive_ack = validate_delivery_ack(
            delivered["hive"], channel="hive", answer_receipt_id=answer_receipt["receipt_id"]
        )
        mycelia_ack = validate_delivery_ack(
            delivered["mycelia"],
            channel="mycelia",
            answer_receipt_id=answer_receipt["receipt_id"],
        )
        propagation = _receipt(
            "thought:10-9-1:propagation:",
            {
                "schema_version": PROPAGATION_SCHEMA,
                "answer_receipt_id": answer_receipt["receipt_id"],
                "hive_ack_id": hive_ack["receipt_id"],
                "mycelia_ack_id": mycelia_ack["receipt_id"],
                "propagator_id": _nonblank(self._propagator.propagator_id, "propagator_id"),
                "propagated": True,
                **_FALSE_FLAGS,
            },
        )
        causal = {
            "schema_version": SCHEMA_VERSION,
            "stage_order": [10, 9, 1],
            "subject_type": request.subject_type,
            "subject_id": request.subject_id,
            "process_id": request.process_id,
            "stage": request.stage,
            "work_kind": request.work_kind,
            "brain_passport_id": request.brain_passport_id,
            "prompt_digest": prompt_digest,
            "answer_digest": answer_digest,
            "resolver_id": _nonblank(self._resolver.resolver_id, "resolver_id"),
            "vacuum_receipt": vacuum,
            "hnc_receipt": hnc_stage,
            "answer_receipt": answer_receipt,
            "propagation_receipt": propagation,
            "hive_ack": hive_ack,
            "mycelia_ack": mycelia_ack,
            "status": "coherent_and_propagated",
            "derived_at": _finite(self._now(), "derived_at"),
            **_FALSE_FLAGS,
        }
        final = _receipt("thought:10-9-1:", causal)
        validate_ten_nine_one_receipt(final)
        self._receipts.append(final)
        return ThoughtPathResult(answer=response, receipt=final)


def validate_ten_nine_one_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact stage order, cross-links, Phi policy, and delivery evidence."""

    expected_top_keys = {
        "schema_version",
        "stage_order",
        "subject_type",
        "subject_id",
        "process_id",
        "stage",
        "work_kind",
        "brain_passport_id",
        "prompt_digest",
        "answer_digest",
        "resolver_id",
        "vacuum_receipt",
        "hnc_receipt",
        "answer_receipt",
        "propagation_receipt",
        "hive_ack",
        "mycelia_ack",
        "status",
        "derived_at",
        *_FALSE_FLAGS,
        "receipt_id",
    }
    if (
        not isinstance(receipt, Mapping)
        or set(receipt) != expected_top_keys
        or receipt.get("schema_version") != SCHEMA_VERSION
    ):
        raise ValueError("10_9_1_receipt_required")
    _require_false_flags(receipt)
    if receipt.get("stage_order") != [10, 9, 1] or receipt.get("status") != "coherent_and_propagated":
        raise ValueError("exact_10_9_1_stage_order_required")
    for key in (
        "subject_type",
        "subject_id",
        "process_id",
        "stage",
        "work_kind",
        "brain_passport_id",
        "resolver_id",
    ):
        _nonblank(receipt.get(key), key)
    prompt_digest = _digest(receipt.get("prompt_digest"), "prompt_digest")
    answer_digest = _digest(receipt.get("answer_digest"), "answer_digest")
    vacuum = receipt.get("vacuum_receipt")
    hnc = receipt.get("hnc_receipt")
    answer = receipt.get("answer_receipt")
    propagation = receipt.get("propagation_receipt")
    if (
        not isinstance(vacuum, Mapping)
        or not isinstance(hnc, Mapping)
        or not isinstance(answer, Mapping)
        or not isinstance(propagation, Mapping)
    ):
        raise ValueError("complete_10_9_1_stage_receipts_required")
    expected_stage_keys = {
        VACUUM_SCHEMA: {
            "schema_version",
            "stage",
            "state",
            "subject_type",
            "subject_id",
            "process_id",
            "prompt_digest",
            "brain_passport_id",
            *_FALSE_FLAGS,
            "receipt_id",
        },
        HNC_SCHEMA: {
            "schema_version",
            "stage",
            "state",
            "vacuum_receipt_id",
            "prompt_digest",
            "hnc_receipt_id",
            "hnc_input_receipt_ids",
            "hnc_source_timestamp",
            "hnc_gamma",
            "phi",
            "phi_inverse",
            "phi_squared",
            *_FALSE_FLAGS,
            "receipt_id",
        },
        AURIS_SCHEMA: {
            "schema_version",
            "stage",
            "state",
            "hnc_stage_receipt_id",
            "answer_digest",
            "hnc_receipt_id",
            "auris_receipt_id",
            "provider_receipt_ids",
            "provider_moment_digest",
            "provider_source_timestamp",
            "auris_gamma",
            "coherence_band",
            "coherence_threshold",
            "auris_gate_open",
            *_FALSE_FLAGS,
            "receipt_id",
        },
        PROPAGATION_SCHEMA: {
            "schema_version",
            "answer_receipt_id",
            "hive_ack_id",
            "mycelia_ack_id",
            "propagator_id",
            "propagated",
            *_FALSE_FLAGS,
            "receipt_id",
        },
    }
    for item in (vacuum, hnc, answer, propagation):
        _require_false_flags(item)
        stage_schema = item.get("schema_version")
        if not isinstance(stage_schema, str) or set(item) != expected_stage_keys.get(
            stage_schema,
            set(),
        ):
            raise ValueError("exact_10_9_1_stage_receipt_schema_required")
        causal = {key: item[key] for key in item if key != "receipt_id"}
        expected_prefix = {
            VACUUM_SCHEMA: "thought:10-9-1:vacuum:",
            HNC_SCHEMA: "thought:10-9-1:hnc:",
            AURIS_SCHEMA: "thought:10-9-1:answer:",
            PROPAGATION_SCHEMA: "thought:10-9-1:propagation:",
        }.get(stage_schema)
        if not expected_prefix or item.get("receipt_id") != f"{expected_prefix}{_sha256(causal)}":
            raise ValueError("10_9_1_stage_receipt_hash_mismatch")
    if vacuum.get("stage") != 10 or vacuum.get("prompt_digest") != prompt_digest:
        raise ValueError("vacuum_stage_binding_mismatch")
    if (
        hnc.get("stage") != 9
        or hnc.get("vacuum_receipt_id") != vacuum.get("receipt_id")
        or hnc.get("prompt_digest") != prompt_digest
    ):
        raise ValueError("hnc_stage_binding_mismatch")
    hnc_inputs = hnc.get("hnc_input_receipt_ids")
    if (
        not isinstance(hnc_inputs, list)
        or not hnc_inputs
        or hnc_inputs != sorted(set(hnc_inputs))
        or not 0.0 <= _finite(hnc.get("hnc_gamma"), "hnc_gamma") <= 1.0
    ):
        raise ValueError("hnc_stage_evidence_invalid")
    _finite(hnc.get("hnc_source_timestamp"), "hnc_source_timestamp")
    for name, expected in (
        ("phi", PHI),
        ("phi_inverse", PHI_INVERSE),
        ("phi_squared", PHI_SQUARED),
    ):
        if type(hnc.get(name)) is not float or hnc[name].hex() != expected.hex():
            raise ValueError("phi_policy_mismatch")
    if (
        answer.get("stage") != 1
        or answer.get("hnc_stage_receipt_id") != hnc.get("receipt_id")
        or answer.get("answer_digest") != answer_digest
        or answer.get("hnc_receipt_id") != hnc.get("hnc_receipt_id")
        or answer.get("auris_gate_open") is not True
        or _finite(answer.get("auris_gamma"), "auris_gamma") < ACTIVE_COHERENCE_THRESHOLD
    ):
        raise ValueError("auris_answer_binding_mismatch")
    auris_gamma = float(answer["auris_gamma"])
    expected_band = "LIGHTHOUSE" if auris_gamma >= LIGHTHOUSE_COHERENCE_THRESHOLD else "ACTIVE"
    provider_ids = answer.get("provider_receipt_ids")
    if (
        answer.get("coherence_band") != expected_band
        or type(answer.get("coherence_threshold")) is not float
        or answer["coherence_threshold"].hex() != ACTIVE_COHERENCE_THRESHOLD.hex()
        or not isinstance(provider_ids, list)
        or not provider_ids
        or provider_ids != sorted(set(provider_ids))
    ):
        raise ValueError("auris_answer_policy_mismatch")
    _digest(answer.get("provider_moment_digest"), "provider_moment_digest")
    _finite(answer.get("provider_source_timestamp"), "provider_source_timestamp")
    _nonblank(answer.get("auris_receipt_id"), "auris_receipt_id")
    answer_id = _nonblank(answer.get("receipt_id"), "answer_receipt_id")
    hive_ack = validate_delivery_ack(receipt.get("hive_ack", {}), channel="hive", answer_receipt_id=answer_id)
    mycelia_ack = validate_delivery_ack(
        receipt.get("mycelia_ack", {}), channel="mycelia", answer_receipt_id=answer_id
    )
    if (
        propagation.get("answer_receipt_id") != answer_id
        or propagation.get("hive_ack_id") != hive_ack["receipt_id"]
        or propagation.get("mycelia_ack_id") != mycelia_ack["receipt_id"]
        or propagation.get("propagated") is not True
    ):
        raise ValueError("10_9_1_propagation_binding_mismatch")
    _nonblank(propagation.get("propagator_id"), "propagator_id")
    _finite(receipt.get("derived_at"), "derived_at")
    causal = {key: receipt[key] for key in receipt if key != "receipt_id"}
    if receipt.get("receipt_id") != f"thought:10-9-1:{_sha256(causal)}":
        raise ValueError("10_9_1_receipt_hash_mismatch")
    return dict(receipt)


def build_local_ten_nine_one_thought_path(
    *,
    bus: Any = None,
    root: Path | None = None,
) -> TenNineOneThoughtPath:
    """Build the production path from local authenticated HNC/Auris evidence."""

    return TenNineOneThoughtPath(
        resolver=LocalHncAurisEvidenceResolver(bus=bus, root=root),
        propagator=ThoughtBusHiveMyceliaPropagator(bus=bus),
    )


__all__ = [
    "ACTIVE_COHERENCE_THRESHOLD",
    "AURIS_SCHEMA",
    "COMMITMENT_PROPAGATION_SCHEMA",
    "CommitmentOnlyHiveMyceliaPropagator",
    "HNC_SCHEMA",
    "LIGHTHOUSE_COHERENCE_THRESHOLD",
    "LocalHncAurisEvidenceResolver",
    "PHI",
    "PHI_INVERSE",
    "PHI_SQUARED",
    "SCHEMA_VERSION",
    "SELF_CODER_CONFIDENTIAL_PREFLIGHT_SCHEMA",
    "TenNineOneEvidenceResolver",
    "TenNineOneHold",
    "TenNineOnePropagator",
    "TenNineOneThoughtPath",
    "ThoughtBusHiveMyceliaPropagator",
    "ThoughtPathRequest",
    "ThoughtPathResult",
    "build_delivery_ack",
    "build_local_ten_nine_one_thought_path",
    "validate_delivery_ack",
    "validate_ten_nine_one_receipt",
]
