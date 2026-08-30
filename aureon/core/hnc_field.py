"""
The canonical HNC field — one shared reading, not thirteen private ones.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The organism had ~13 independent ``LambdaEngine`` instances, each computing its own
``symbolic_life_score`` / ``coherence_gamma`` with nothing reconciling them. The HNC
live daemon (driven by real world data) now publishes the authoritative field on the
thought bus as ``symbolic.life.pulse``. This module is the single place to READ that
field, so a system that only wants "the current shared coherence" reads the one
canonical value instead of spinning a private engine — the field becomes shared
logic, not a per-module opinion.

Read path uses ``recall(topic_prefix)`` (filters by topic) so a high-volume bus
(baton.link heartbeats, etc.) can never evict the pulse from a recency window. Fully
guarded and offline-safe: with no bus / no pulse, ``read_canonical_field()`` returns
an ``available=False`` field rather than raising.

**Freshness is part of being real.** These readers cross process boundaries through
persisted trace files, and a file on disk has no idea how old it is. Without a bound,
``available=True`` meant only "a row exists somewhere", so a coherence figure written
days ago was served to a dashboard as the organism's current state — a stale number
presented as live is a false reading, not a cautious one. Every row is therefore
stamped when published and ignored once older than :data:`FIELD_MAX_AGE_S`; a row with
no timestamp has unknowable age and is refused. When nothing fresh is flowing the
readers report ``available=False``, which is the honest answer.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

#: How old a field row may be and still count as "the current field", in seconds.
#: ``AUREON_HNC_FIELD_MAX_AGE_S`` may tighten this ceiling but may never widen it.
#: The HNC daemon pulses continuously, so anything older than a few minutes means
#: the producer has stopped and the honest report is "unavailable", not a stale number.
FIELD_MAX_AGE_S = 300.0
FIELD_FUTURE_SKEW_S = 5.0


def _max_age_s() -> float:
    try:
        v = float(os.environ.get("AUREON_HNC_FIELD_MAX_AGE_S", "") or 300.0)
        return min(v, FIELD_MAX_AGE_S) if math.isfinite(v) and v > 0 else FIELD_MAX_AGE_S
    except (TypeError, ValueError):
        return FIELD_MAX_AGE_S

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_CANONICAL_CONTROL_FIELDS = (
    "operational_eligible",
    "provider_eligible",
    "action_eligible",
    "actionable",
    "accounting_eligible",
    "learning_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "action_gate_passed",
)


def _finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    return candidate or None


def build_hnc_live_field_receipt_id(
    *,
    input_receipt_ids: tuple[str, ...] | list[str],
    source_timestamp: float,
    received_at: float,
    step: int,
    lambda_t: float,
    coherence_gamma: float,
    consciousness_psi: float,
    symbolic_life_score: float,
) -> str:
    """Derive the daemon's content-bound live-field receipt identifier.

    This deliberately mirrors :meth:`HNCLiveDaemon._build_live_envelope`.  The
    identifier is not a signature, but re-deriving it prevents a bus or trace
    row from retaining a trusted receipt label after any coherence input or
    freshness timestamp has been changed.
    """

    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("non_negative_hnc_step_required")
    normalized_ids = tuple(str(value).strip() for value in input_receipt_ids)
    if (
        not normalized_ids
        or any(not value for value in normalized_ids)
        or normalized_ids != tuple(sorted(set(normalized_ids)))
    ):
        raise ValueError("sorted_distinct_hnc_input_receipt_ids_required")
    metrics = {
        "lambda_t": _finite_number(lambda_t),
        "coherence_gamma": _finite_number(coherence_gamma),
        "consciousness_psi": _finite_number(consciousness_psi),
        "symbolic_life_score": _finite_number(symbolic_life_score),
    }
    if any(value is None for value in metrics.values()):
        raise ValueError("finite_hnc_receipt_metrics_required")
    timestamps = {
        "source_timestamp": _finite_number(source_timestamp),
        "received_at": _finite_number(received_at),
    }
    if any(value is None for value in timestamps.values()):
        raise ValueError("finite_hnc_receipt_timestamps_required")
    fingerprint = {
        "input_receipt_ids": list(normalized_ids),
        **timestamps,
        "step": step,
        **metrics,
    }
    digest = hashlib.sha256(
        json.dumps(
            fingerprint,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()[:24]
    return f"hnc:live_field:{digest}"


def _validated_canonical_envelope(
    row: Any,
    *,
    now: float | None = None,
) -> dict[str, Any] | None:
    """Validate the daemon's complete evidence-only global field envelope."""
    if not isinstance(row, dict):
        return None
    checked_at = _finite_number(time.time() if now is None else now)
    source_timestamp = _finite_number(row.get("source_timestamp"))
    received_at = _finite_number(row.get("received_at"))
    legacy_timestamp = _finite_number(row.get("ts"))
    metrics = {
        name: _finite_number(row.get(name))
        for name in (
            "symbolic_life_score",
            "coherence_gamma",
            "consciousness_psi",
            "lambda_t",
            "source_count",
        )
    }
    source_id = _identifier(row.get("source_id"))
    receipt_id = _identifier(row.get("receipt_id"))
    receipt_type = _identifier(row.get("receipt_type"))
    provider_receipt_type = _identifier(row.get("provider_receipt_type"))
    source = _identifier(row.get("source"))
    consciousness_level = _identifier(row.get("consciousness_level"))
    step = row.get("step")
    memory_receipt_id = _identifier(row.get("memory_receipt_id"))
    memory_canonical_hash = _identifier(row.get("memory_canonical_hash"))
    memory_previous_receipt_id = _identifier(row.get("memory_previous_receipt_id"))
    raw_input_ids = row.get("input_receipt_ids")
    input_receipt_ids = (
        [_identifier(value) for value in raw_input_ids]
        if isinstance(raw_input_ids, list)
        else []
    )
    if (
        row.get("data_status") != "live"
        or checked_at is None
        or row.get("truth_status") != "real_derived"
        or row.get("generated_values") is not False
        or source != "hnc_live_daemon"
        or source_id != "aureon:hnc:live_daemon"
        or receipt_id is None
        or isinstance(step, bool)
        or not isinstance(step, int)
        or step < 0
        or memory_receipt_id is None
        or memory_canonical_hash is None
        or _SHA256_RE.fullmatch(memory_canonical_hash) is None
        or memory_receipt_id != f"hnc:lambda_history:{memory_canonical_hash}"
        or memory_receipt_id not in input_receipt_ids
        or (
            memory_previous_receipt_id is not None
            and not memory_previous_receipt_id.startswith("hnc:lambda_history:")
        )
        or (
            receipt_type != "hnc_live_field"
            and provider_receipt_type != "hnc_live_field"
        )
        or (
            receipt_type is not None
            and provider_receipt_type is not None
            and receipt_type != provider_receipt_type
        )
        or not input_receipt_ids
        or any(value is None for value in input_receipt_ids)
        or len(input_receipt_ids) != len(set(input_receipt_ids))
        or input_receipt_ids != sorted(input_receipt_ids)
        or source_timestamp is None
        or received_at is None
        or legacy_timestamp is None
        or not math.isclose(
            legacy_timestamp,
            source_timestamp,
            rel_tol=0.0,
            abs_tol=1e-6,
        )
        or source_timestamp > received_at + FIELD_FUTURE_SKEW_S
        or source_timestamp > checked_at + FIELD_FUTURE_SKEW_S
        or received_at > checked_at + FIELD_FUTURE_SKEW_S
        or checked_at - source_timestamp > _max_age_s()
        or checked_at - received_at > _max_age_s()
        or any(value is None for value in metrics.values())
        or metrics["source_count"] <= 0.0
        or consciousness_level is None
        or row.get("freshness_status") != "fresh"
        or row.get("equation_inputs_complete") is not True
        or row.get("action_gate_reason") != "route_specific_market_link_required"
        or any(row.get(name) is not False for name in _CANONICAL_CONTROL_FIELDS)
    ):
        return None
    try:
        expected_receipt_id = build_hnc_live_field_receipt_id(
            input_receipt_ids=tuple(str(value) for value in input_receipt_ids),
            source_timestamp=source_timestamp,
            received_at=received_at,
            step=step,
            lambda_t=metrics["lambda_t"],
            coherence_gamma=metrics["coherence_gamma"],
            consciousness_psi=metrics["consciousness_psi"],
            symbolic_life_score=metrics["symbolic_life_score"],
        )
    except (TypeError, ValueError):
        return None
    if receipt_id != expected_receipt_id:
        return None
    return {
        **row,
        **metrics,
        "source": source,
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "receipt_id": receipt_id,
        "receipt_type": receipt_type,
        "provider_receipt_type": provider_receipt_type,
        "input_receipt_ids": tuple(str(value) for value in input_receipt_ids),
        "consciousness_level": consciousness_level,
        "step": step,
        "memory_receipt_id": memory_receipt_id,
        "memory_canonical_hash": memory_canonical_hash,
        "memory_previous_receipt_id": memory_previous_receipt_id,
    }


def _row_is_fresh(row: Any, now: float | None = None) -> bool:
    """True when ``row`` carries a timestamp within the freshness window.

    Fails CLOSED: a row with no timestamp, or an unparseable one, has unknowable age
    and is refused. Being unable to prove a reading is current is not a reason to
    present it as current.
    """
    if not isinstance(row, dict):
        return False
    ts = row.get("ts", row.get("timestamp", row.get("time")))
    if not isinstance(ts, (int, float)):
        return False
    now = time.time() if now is None else now
    age = now - float(ts)
    return -60.0 <= age <= _max_age_s()      # small negative tolerance for clock skew


@dataclass(frozen=True)
class CanonicalField:
    """A snapshot of the organism's shared HNC field."""

    available: bool = False
    symbolic_life_score: float | None = None
    coherence_gamma: float | None = None
    consciousness_psi: float | None = None
    consciousness_level: str | None = None
    lambda_t: float | None = None
    step: int | None = None
    source: str | None = None
    evidence_transport: str | None = None
    source_id: str | None = None
    source_timestamp: float | None = None
    received_at: float | None = None
    receipt_id: str | None = None
    receipt_type: str | None = None
    provider_receipt_type: str | None = None
    input_receipt_ids: tuple[str, ...] = ()
    memory_receipt_id: str | None = None
    memory_canonical_hash: str | None = None
    memory_previous_receipt_id: str | None = None
    data_status: str = "no_data"
    truth_status: str | None = None
    generated_values: bool = False
    source_count: float | None = None
    freshness_status: str | None = None
    operational_eligible: bool = False
    provider_eligible: bool = False
    action_eligible: bool = False
    actionable: bool = False
    accounting_eligible: bool = False
    learning_eligible: bool = False
    eligible_for_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False
    equation_inputs_complete: bool = False
    action_gate_passed: bool = False
    action_gate_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "symbolic_life_score": self.symbolic_life_score,
            "coherence_gamma": self.coherence_gamma,
            "consciousness_psi": self.consciousness_psi,
            "consciousness_level": self.consciousness_level,
            "lambda_t": self.lambda_t,
            "step": self.step,
            "source": self.source,
            "evidence_transport": self.evidence_transport,
            "source_id": self.source_id,
            "source_timestamp": self.source_timestamp,
            "received_at": self.received_at,
            "receipt_id": self.receipt_id,
            "receipt_type": self.receipt_type,
            "provider_receipt_type": self.provider_receipt_type,
            "input_receipt_ids": list(self.input_receipt_ids),
            "memory_receipt_id": self.memory_receipt_id,
            "memory_canonical_hash": self.memory_canonical_hash,
            "memory_previous_receipt_id": self.memory_previous_receipt_id,
            "data_status": self.data_status,
            "truth_status": self.truth_status,
            "generated_values": self.generated_values,
            "source_count": self.source_count,
            "freshness_status": self.freshness_status,
            "operational_eligible": self.operational_eligible,
            "provider_eligible": self.provider_eligible,
            "action_eligible": self.action_eligible,
            "actionable": self.actionable,
            "accounting_eligible": self.accounting_eligible,
            "learning_eligible": self.learning_eligible,
            "eligible_for_action": self.eligible_for_action,
            "eligible_for_accounting": self.eligible_for_accounting,
            "eligible_for_learning": self.eligible_for_learning,
            "equation_inputs_complete": self.equation_inputs_complete,
            "action_gate_passed": self.action_gate_passed,
            "action_gate_reason": self.action_gate_reason,
        }


def _canonical_field_from_envelope(
    row: Any,
    *,
    evidence_transport: str,
) -> CanonicalField:
    try:
        return validate_canonical_field_snapshot(
            {
                **dict(row),
                "evidence_transport": evidence_transport,
                "available": True,
            },
        )
    except (TypeError, ValueError):
        return _EMPTY


def validate_canonical_field_snapshot(
    snapshot: CanonicalField | Mapping[str, Any],
    *,
    now: float | None = None,
) -> CanonicalField:
    """Revalidate one complete canonical HNC snapshot.

    ``read_canonical_field`` is the trusted capture path, but downstream gates
    must re-check freshness immediately before dispatch.  This public adapter
    deliberately reuses the daemon-envelope validator instead of teaching each
    consumer a slightly different definition of "live".  It accepts the
    immutable :class:`CanonicalField` returned by this module or its serialized
    mapping and returns a freshly validated immutable value.
    """

    captured_snapshot = isinstance(snapshot, CanonicalField)
    if captured_snapshot:
        raw = snapshot.to_dict()
    elif isinstance(snapshot, Mapping):
        raw = dict(snapshot)
    else:
        raise TypeError("canonical_field_snapshot_required")
    evidence_transport = raw.get("evidence_transport")
    if evidence_transport not in {"thought_bus", "persisted_trace"}:
        raise ValueError("trusted_canonical_field_transport_required")
    # ``ts`` is retained in the daemon envelope for legacy readers.  The
    # immutable snapshot stores the same fact once as ``source_timestamp``.
    if captured_snapshot:
        raw["ts"] = raw.get("source_timestamp")
    envelope = _validated_canonical_envelope(raw, now=now)
    if envelope is None or raw.get("available") is not True:
        raise ValueError("complete_fresh_canonical_hnc_field_required")
    return CanonicalField(
        available=True,
        symbolic_life_score=envelope["symbolic_life_score"],
        coherence_gamma=envelope["coherence_gamma"],
        consciousness_psi=envelope["consciousness_psi"],
        consciousness_level=envelope["consciousness_level"],
        lambda_t=envelope["lambda_t"],
        step=envelope["step"],
        source=envelope["source"],
        evidence_transport=str(evidence_transport),
        source_id=envelope["source_id"],
        source_timestamp=envelope["source_timestamp"],
        received_at=envelope["received_at"],
        receipt_id=envelope["receipt_id"],
        receipt_type=envelope["receipt_type"],
        provider_receipt_type=envelope["provider_receipt_type"],
        input_receipt_ids=envelope["input_receipt_ids"],
        memory_receipt_id=envelope["memory_receipt_id"],
        memory_canonical_hash=envelope["memory_canonical_hash"],
        memory_previous_receipt_id=envelope["memory_previous_receipt_id"],
        data_status=envelope["data_status"],
        truth_status=envelope["truth_status"],
        generated_values=envelope["generated_values"],
        source_count=envelope["source_count"],
        freshness_status=envelope["freshness_status"],
        operational_eligible=envelope["operational_eligible"],
        provider_eligible=envelope["provider_eligible"],
        action_eligible=envelope["action_eligible"],
        actionable=envelope["actionable"],
        accounting_eligible=envelope["accounting_eligible"],
        learning_eligible=envelope["learning_eligible"],
        eligible_for_action=envelope["eligible_for_action"],
        eligible_for_accounting=envelope["eligible_for_accounting"],
        eligible_for_learning=envelope["eligible_for_learning"],
        equation_inputs_complete=envelope["equation_inputs_complete"],
        action_gate_passed=envelope["action_gate_passed"],
        action_gate_reason=envelope["action_gate_reason"],
    )
_EMPTY = CanonicalField()


def read_canonical_field(bus: Any = None) -> CanonicalField:
    """Read the latest ``symbolic.life.pulse`` — the one shared field.

    Pass ``bus`` to read from a specific ThoughtBus; otherwise the global
    singleton is used. Never raises; returns an unavailable field when there is
    no bus, no pulse, no score, and no cross-process trace.

    Cross-process bridge: the HNC live daemon, the operator, and the organism
    daemon each run as SEPARATE processes with their own in-memory bus, so a
    pulse published in one is invisible to the others. The daemon also persists
    the field to ``state/hnc_live_trace.jsonl`` every step; when the local bus
    has no pulse, we fall back to the last line of that trace so the live field
    reaches every process. Path overridable via ``AUREON_HNC_TRACE_PATH``.
    """
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus, payload_of

        b = bus if bus is not None else get_thought_bus()
        if b is not None and hasattr(b, "recall"):
            pulses = b.recall("symbolic.life.pulse", limit=1) or []
            if pulses:
                p = payload_of(pulses[-1])
                captured = _canonical_field_from_envelope(
                    p,
                    evidence_transport="thought_bus",
                )
                if captured.available:
                    return captured
    except Exception:  # noqa: BLE001 — a missing field is a value, never a crash
        pass
    # Cross-process fallback: the HNC daemon's persisted trace.
    return _read_field_from_trace()


def _read_field_from_trace() -> CanonicalField:
    """Read the latest field from the HNC daemon's persisted trace file, so the
    live field crosses process boundaries (separate daemons, separate buses).
    Guarded; returns an unavailable field when the trace is absent/empty."""
    import json
    import os
    from pathlib import Path

    try:
        path = os.environ.get("AUREON_HNC_TRACE_PATH") or str(
            Path(__file__).resolve().parents[2] / "state" / "hnc_live_trace.jsonl")
        p = Path(path)
        if not p.exists():
            return _EMPTY
        last = ""
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = line
        if not last:
            return _EMPTY
        row = json.loads(last)
        # A trace file cannot say how old it is. Without this the last line written —
        # possibly days ago, by a daemon that has since stopped — was reported as the
        # organism's live field.
        return _canonical_field_from_envelope(
            row,
            evidence_transport="persisted_trace",
        )
    except Exception:  # noqa: BLE001
        return _EMPTY


def publish_subfield(source: str, state: Any, bus: Any = None) -> None:
    """Publish a producer's LOCAL field as a namespaced sub-field.

    The organism has many legitimate ``LambdaEngine`` producers (the Queen's
    cortex, source-law, metacognition, sentient loop, mycelium mind, the human
    loop). Each computes a real local field; reconciling them into one would
    destroy that. Instead each publishes its field here as
    ``symbolic.life.subfield`` so the organism can SENSE every sub-field — the
    fields become connected (visible on the shared bus) without losing their
    local computation. Guarded / no-op on any error.
    """
    payload = {
        "source": source,
        # Stamped at publish so a reader can tell a live sub-field from a dead
        # producer's last one. Rows without this are refused as unknowable-age, so
        # omitting it would silently drop the producer out of the blend.
        "ts": time.time(),
        "symbolic_life_score": getattr(state, "symbolic_life_score", None),
        "coherence_gamma": getattr(state, "coherence_gamma", None),
        "consciousness_level": getattr(state, "consciousness_level", None),
    }
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        b = bus if bus is not None else get_thought_bus()
        if b is not None:
            b.publish(Thought(source=source, topic="symbolic.life.subfield", payload=dict(payload)))
    except Exception:  # noqa: BLE001 — visibility is best-effort, never fatal
        pass
    # Cross-process bridge: sub-field producers (Queen engines, consciousness,
    # auris) live in other processes than the blend readers (organism daemon,
    # operator SaaS). Mirror to a dedicated trace so every sub-field reaches the
    # whole-body consensus, not just same-process ones.
    try:
        from aureon.core.bus_trace import append_trace

        append_trace("symbolic_subfield", dict(payload))
    except Exception:  # noqa: BLE001
        pass


def canonical_field_reading(confidence: float = 0.9, bus: Any = None) -> Any:
    """The canonical field as a ``SubsystemReading`` — the Pattern-A merge, shared.

    Every local ``LambdaEngine`` producer (Queen cortex, source-law,
    metacognition, sentient loop, mycelium mind, human loop, Auris throne,
    pursuit, the ICS) closes its β·Λ(t−τ) loop by appending this reading to its
    own inputs before ``step()`` — the shared field informs the local one
    without replacing it. Returns ``None`` when the field is dark or stale
    (freshness fails closed upstream) — never a placeholder, because Γ consumes
    reading VALUES regardless of confidence.
    """
    try:
        from aureon.core.aureon_lambda_engine import SubsystemReading

        cf = read_canonical_field(bus)
        if cf.available and cf.symbolic_life_score is not None:
            return SubsystemReading(
                name="hnc_canonical_field",
                value=max(0.0, min(1.0, float(cf.symbolic_life_score))),
                confidence=max(0.0, min(1.0, float(confidence))),
                state=str(cf.consciousness_level or "live"),
            )
    except Exception:  # noqa: BLE001 — a missing field is a value, never a crash
        pass
    return None


def read_subfields(bus: Any = None) -> dict[str, dict[str, Any]]:
    """All recently-published local sub-fields, keyed by source — the organism's
    view of every field its producers are computing."""
    out: dict[str, dict[str, Any]] = {}

    def _absorb(src: Any, p: dict[str, Any], *, require_ts: bool) -> None:
        """Absorb one sub-field row.

        Freshness is checked per row, not per file: one live producer must not make a
        long-dead producer's last reading look current just by sharing the trace.

        ``require_ts`` differs by TRANSPORT, because what is knowable differs:

        * a **persisted trace row** carries no evidence of its own age, so an unstamped
          one is refused — that was the observed defect (75 rows, none stamped, served as
          the live field in a process with no producer running);
        * a **bus payload** arrives through ``recall(limit=…)`` on an in-memory ring
          buffer, so the bus itself bounds recency. Demanding a stamp there was stricter
          than the defect warranted and silently dropped live in-process producers out of
          the blend. A stamp is still honoured when present: a bus payload that says it
          is stale is refused.
        """
        if not src:
            return
        if require_ts:
            if not _row_is_fresh(p):
                return
        else:
            ts = p.get("ts", p.get("timestamp", p.get("time")))
            if isinstance(ts, (int, float)) and not _row_is_fresh(p):
                return
        out[str(src)] = {
            "symbolic_life_score": p.get("symbolic_life_score"),
            "coherence_gamma": p.get("coherence_gamma"),
            "consciousness_level": p.get("consciousness_level"),
        }

    # Cross-process sub-fields first (oldest), so same-process (freshest) wins on
    # collision — a producer in another process still reaches the blend.
    try:
        from aureon.core.bus_trace import read_trace

        for row in read_trace("symbolic_subfield", limit=200):
            _absorb(row.get("source"), row, require_ts=True)
    except Exception:  # noqa: BLE001
        pass
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus, payload_of

        b = bus if bus is not None else get_thought_bus()
        if b is not None and hasattr(b, "recall"):
            for t in b.recall("symbolic.life.subfield", limit=200) or []:
                p = payload_of(t)
                _absorb(p.get("source"), p, require_ts=False)
    except Exception:  # noqa: BLE001
        pass
    return out


@dataclass(frozen=True)
class BlendedField:
    """A consensus across the canonical field and every local sub-field —
    the organism's whole-body view of its own coherence."""

    available: bool = False
    symbolic_life_score: float | None = None   # mean across all contributors
    coherence_gamma: float | None = None
    contributors: int = 0                       # how many fields agreed to blend
    divergence: float | None = None             # max-min spread of sub-scores
    sources: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "symbolic_life_score": self.symbolic_life_score,
            "coherence_gamma": self.coherence_gamma,
            "contributors": self.contributors,
            "divergence": self.divergence,
            "sources": list(self.sources),
        }


def blend_field(bus: Any = None) -> BlendedField:
    """Blend the canonical field with every published sub-field into one
    consensus. The mean is the whole-body coherence; ``divergence`` (max-min
    spread) says how much the body's fields disagree — a high spread means the
    organism is of two minds and consumers should be cautious. Degrades to the
    canonical value alone when no sub-fields are present; unavailable when
    nothing is flowing. Never raises.
    """
    canonical = read_canonical_field(bus)
    subs = read_subfields(bus)

    scores: list[float] = []
    gammas: list[float] = []
    sources: list[str] = []
    if canonical.available and canonical.symbolic_life_score is not None:
        scores.append(canonical.symbolic_life_score)
        sources.append("canonical")
        if canonical.coherence_gamma is not None:
            gammas.append(canonical.coherence_gamma)
    for name, sub in sorted(subs.items()):
        sls = sub.get("symbolic_life_score")
        if sls is not None:
            try:
                scores.append(float(sls))
                sources.append(name)
                g = sub.get("coherence_gamma")
                if g is not None:
                    gammas.append(float(g))
            except (TypeError, ValueError):
                continue

    if not scores:
        return BlendedField()
    return BlendedField(
        available=True,
        symbolic_life_score=sum(scores) / len(scores),
        coherence_gamma=(sum(gammas) / len(gammas)) if gammas else None,
        contributors=len(scores),
        divergence=(max(scores) - min(scores)) if len(scores) > 1 else 0.0,
        sources=tuple(sources),
    )


def reconcile_gamma(local_coherence: float, bus: Any = None) -> float:
    """Conservatively reconcile a locally computed coherence with the canonical Γ.

    The LOWER of the two wins, so the organism's shared field can only TIGHTEN
    a live trading gate, never loosen it. Offline-safe: when the canonical
    field is unavailable (or carries no Γ) the local figure passes through
    unchanged — never a substituted or invented value. This is the one seam
    every live-order-path module uses to stay on the same field as the rest
    of the organism (b46 logic-train burn-down).
    """
    try:
        local = float(local_coherence)
    except (TypeError, ValueError):
        return local_coherence
    try:
        field = read_canonical_field(bus)
        if getattr(field, "available", False) and field.coherence_gamma is not None:
            gamma = max(0.0, min(1.0, float(field.coherence_gamma)))
            return min(local, gamma)
    except Exception:  # noqa: BLE001 — the shared field must never break a live order path
        pass
    return local


__all__ = [
    "CanonicalField", "read_canonical_field", "publish_subfield",
    "read_subfields", "BlendedField", "blend_field", "reconcile_gamma",
    "validate_canonical_field_snapshot", "build_hnc_live_field_receipt_id",
]
