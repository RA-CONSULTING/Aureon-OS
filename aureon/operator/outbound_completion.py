"""Fail-closed completion control for every external Aureon payload.

This module gives autonomous work one rule that cannot be rounded down:
prepare and revise as often as necessary, but do not cross an external send,
submit, publish, post, upload, or filing boundary until the exact payload has a
fresh completion assessment whose every quality axis is exactly ``1.0``.

The score is route-specific.  It describes the coherence of this payload with
its instructions and evidence; it never overwrites or pretends to improve the
organism's live global HNC reading.  The normal GroundedActionGate and human,
identity, legal, finance, CAPTCHA/MFA, and provider controls remain in force.

The release seal closes the time-of-check/time-of-use gap.  It is bound to the
canonical payload and assessment hashes and authenticated with a process-local
HMAC.  Editing one character after assessment invalidates the release.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence, TypeVar

SCHEMA_VERSION = "aureon-outbound-completion-v1"
DEFAULT_AUDIT_LOG = Path("state/outbound_completion_audit.jsonl")
DEFAULT_RELEASE_TTL_SECONDS = 300
DEFAULT_ASSESSMENT_TTL_SECONDS = 3600

FULL_COHERENCE = Decimal("1")
QUALITY_AXES = (
    "route_coherence",
    "semantic_completeness",
    "factual_support",
    "internal_consistency",
    "language_quality",
    "format_quality",
    "instruction_satisfaction",
)

# An approval request must be able to ask for the authorization that all other
# external payloads need.  Its destination is owner-locked at its integration.
_NON_RECURSIVE_AUTHORIZATION_KINDS = frozenset({"approval_request", "owner_approval_request"})
_SUBJECT_REQUIRED_KINDS = frozenset({"email", "email_reply", "approval_request", "owner_approval_request"})
_OUTBOUND_VERBS = frozenset({
    "file", "lodge", "notify", "post", "publish", "reply", "send", "submit", "upload",
})
_EXTERNAL_EFFECTS = frozenset({
    "email", "external", "filing", "form", "message", "portal", "publication",
    "submission", "upload",
})
_PLACEHOLDER_PATTERNS = (
    re.compile(r"\b(?:TODO|TBD|FIXME)\b", re.IGNORECASE),
    re.compile(r"\{\{[^{}]+\}\}"),
    re.compile(r"\[(?:insert|add|complete|fill)[^\]]*\]", re.IGNORECASE),
    re.compile(r"<placeholder(?:\s+[^>]*)?>", re.IGNORECASE),
)
_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("assessed_at must be an ISO-8601 timestamp")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return parsed


def _tuple_of_text(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _is_full(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return Decimal(str(value)) == FULL_COHERENCE
    except (InvalidOperation, ValueError):
        return False


def _verb_candidates(word: str) -> set[str]:
    candidates = {word}
    if word.endswith("ing") and len(word) > 4:
        stem = word[:-3]
        candidates.update({stem, f"{stem}e"})
        if len(stem) > 1 and stem[-1] == stem[-2]:
            candidates.add(stem[:-1])
    if word.endswith("ed") and len(word) > 3:
        stem = word[:-2]
        candidates.update({stem, f"{stem}e"})
        if len(stem) > 1 and stem[-1] == stem[-2]:
            candidates.add(stem[:-1])
    if word.endswith("s") and len(word) > 2:
        candidates.add(word[:-1])
    return candidates


def is_outbound_action(
    action: str,
    params: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> bool:
    """Return whether an action declares an external payload mutation.

    Callers can state the effect explicitly with ``external_effect`` or
    ``outbound``.  The token matcher also catches names such as
    ``send_email``, ``submit-application`` and ``publishing_report`` without
    confusing internal Thought Bus ``publish`` calls, which never enter the
    LocalActionBridge.
    """

    merged: dict[str, Any] = {}
    merged.update(dict(context or {}))
    merged.update(dict(params or {}))
    if merged.get("outbound") is True:
        return True
    effect = str(merged.get("external_effect") or merged.get("effect") or "").strip().lower()
    if effect in _EXTERNAL_EFFECTS:
        return True

    words = _WORD_RE.findall(str(action or "").lower())
    if words and words[0] in {"email", "message"}:
        return True
    return any(_verb_candidates(word) & _OUTBOUND_VERBS for word in words)


@dataclass(frozen=True)
class OutboundArtifact:
    """The exact provider-bound payload assessed for release."""

    kind: str
    route: str
    destination: str
    body: str
    subject: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    required_fields: tuple[str, ...] = ()
    authorization_required: bool = True

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": str(self.kind),
            "route": str(self.route),
            "destination": str(self.destination),
            "subject": str(self.subject),
            "body": str(self.body),
            "metadata": dict(self.metadata),
            "required_fields": list(self.required_fields),
            "authorization_required": bool(self.authorization_required),
        }

    @property
    def payload_sha256(self) -> str:
        return _sha256(self.canonical_payload())

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> OutboundArtifact:
        if not isinstance(value, Mapping):
            raise ValueError("outbound_artifact must be a mapping")
        return cls(
            kind=str(value.get("kind") or "").strip(),
            route=str(value.get("route") or "").strip(),
            destination=str(value.get("destination") or "").strip(),
            subject=str(value.get("subject") or ""),
            body=str(value.get("body") or ""),
            metadata=dict(value.get("metadata") or {}),
            required_fields=_tuple_of_text(value.get("required_fields")),
            # Only literal False disables the requirement. Strings such as
            # "false" cannot accidentally weaken an authorization boundary.
            authorization_required=value.get("authorization_required", True) is not False,
        )


@dataclass(frozen=True)
class CompletionAudit:
    """Fresh evidence that the assessed payload is finished, not merely fluent."""

    audit_id: str
    auditor: str
    assessed_payload_sha256: str
    assessed_at: datetime
    route_coherence: float
    semantic_completeness: float
    factual_support: float
    internal_consistency: float
    language_quality: float
    format_quality: float
    instruction_satisfaction: float
    evidence_refs: tuple[str, ...]
    latest_sources_verified: bool
    exact_payload_verified: bool
    authorization_confirmed: bool = False
    authorization_evidence_refs: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    unsupported_claims: tuple[str, ...] = ()
    language_issues: tuple[str, ...] = ()
    formatting_issues: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    valid_for_seconds: int = DEFAULT_ASSESSMENT_TTL_SECONDS

    def canonical_assessment(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["assessed_at"] = self.assessed_at.isoformat()
        return payload

    @property
    def audit_sha256(self) -> str:
        return _sha256(self.canonical_assessment())

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> CompletionAudit:
        if not isinstance(value, Mapping):
            raise ValueError("completion_audit must be a mapping")
        return cls(
            audit_id=str(value.get("audit_id") or "").strip(),
            auditor=str(value.get("auditor") or "").strip(),
            assessed_payload_sha256=str(value.get("assessed_payload_sha256") or "").strip(),
            assessed_at=_parse_time(value.get("assessed_at")),
            route_coherence=float(value.get("route_coherence", 0.0)),
            semantic_completeness=float(value.get("semantic_completeness", 0.0)),
            factual_support=float(value.get("factual_support", 0.0)),
            internal_consistency=float(value.get("internal_consistency", 0.0)),
            language_quality=float(value.get("language_quality", 0.0)),
            format_quality=float(value.get("format_quality", 0.0)),
            instruction_satisfaction=float(value.get("instruction_satisfaction", 0.0)),
            evidence_refs=_tuple_of_text(value.get("evidence_refs")),
            latest_sources_verified=value.get("latest_sources_verified", False) is True,
            exact_payload_verified=value.get("exact_payload_verified", False) is True,
            authorization_confirmed=value.get("authorization_confirmed", False) is True,
            authorization_evidence_refs=_tuple_of_text(value.get("authorization_evidence_refs")),
            contradictions=_tuple_of_text(value.get("contradictions")),
            unsupported_claims=_tuple_of_text(value.get("unsupported_claims")),
            language_issues=_tuple_of_text(value.get("language_issues")),
            formatting_issues=_tuple_of_text(value.get("formatting_issues")),
            unresolved_questions=_tuple_of_text(value.get("unresolved_questions")),
            valid_for_seconds=int(value.get("valid_for_seconds", DEFAULT_ASSESSMENT_TTL_SECONDS)),
        )


@dataclass(frozen=True)
class GateVerdict:
    allowed: bool
    state: str
    reasons: tuple[str, ...]
    trace_id: str
    payload_sha256: str
    audit_sha256: str
    route_coherence: float
    evaluated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "allowed": self.allowed,
            "state": self.state,
            "reasons": list(self.reasons),
            "trace_id": self.trace_id,
            "payload_sha256": self.payload_sha256,
            "audit_sha256": self.audit_sha256,
            "route_coherence": self.route_coherence,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass(frozen=True)
class ReleaseSeal:
    trace_id: str
    payload_sha256: str
    audit_sha256: str
    issued_at: datetime
    expires_at: datetime
    signature: str

    def signed_fields(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "payload_sha256": self.payload_sha256,
            "audit_sha256": self.audit_sha256,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


class OutboundBlocked(RuntimeError):
    """Raised when a payload has not earned release."""

    def __init__(self, verdict: GateVerdict) -> None:
        self.verdict = verdict
        detail = "; ".join(verdict.reasons) or "outbound completion gate refused release"
        super().__init__(detail)


def _field_value(artifact: OutboundArtifact, field_name: str) -> Any:
    if field_name.startswith("metadata."):
        value: Any = artifact.metadata
        for part in field_name.split(".")[1:]:
            if not isinstance(value, Mapping) or part not in value:
                return None
            value = value[part]
        return value
    return getattr(artifact, field_name, None)


def _structural_reasons(artifact: OutboundArtifact) -> list[str]:
    reasons: list[str] = []
    kind = artifact.kind.strip().lower()
    if not kind:
        reasons.append("missing_kind")
    if not artifact.route.strip():
        reasons.append("missing_route")
    if not artifact.destination.strip():
        reasons.append("missing_destination")
    if "\n" in artifact.destination or "\r" in artifact.destination:
        reasons.append("invalid_destination_newline")
    if not artifact.body.strip():
        reasons.append("missing_body")
    if artifact.body != artifact.body.strip():
        reasons.append("body_has_unreviewed_outer_whitespace")
    if "\x00" in artifact.body:
        reasons.append("body_contains_null_byte")
    if kind in _SUBJECT_REQUIRED_KINDS and not artifact.subject.strip():
        reasons.append("missing_subject")
    if artifact.subject != artifact.subject.strip():
        reasons.append("subject_has_unreviewed_outer_whitespace")
    if "\n" in artifact.subject or "\r" in artifact.subject:
        reasons.append("invalid_subject_newline")
    combined = f"{artifact.subject}\n{artifact.body}"
    if any(pattern.search(combined) for pattern in _PLACEHOLDER_PATTERNS):
        reasons.append("unresolved_placeholder")
    for field_name in artifact.required_fields:
        value = _field_value(artifact, field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            reasons.append(f"required_field_missing:{field_name}")
    return reasons


class OutboundCompletionGate:
    """Assess, audit-log, seal, and re-check provider-bound payloads."""

    def __init__(
        self,
        *,
        audit_log_path: Path | str | None = None,
        release_ttl_seconds: int = DEFAULT_RELEASE_TTL_SECONDS,
        secret: bytes | None = None,
    ) -> None:
        configured = os.environ.get("AUREON_OUTBOUND_AUDIT_LOG", "").strip()
        self.audit_log_path = Path(audit_log_path or configured or DEFAULT_AUDIT_LOG)
        self.release_ttl_seconds = max(1, int(release_ttl_seconds))
        self._secret = secret or secrets.token_bytes(32)

    def evaluate(
        self,
        artifact: OutboundArtifact,
        audit: CompletionAudit,
        *,
        now: datetime | None = None,
    ) -> GateVerdict:
        moment = now or datetime.now(UTC)
        reasons = _structural_reasons(artifact)
        payload_hash = artifact.payload_sha256

        for axis in QUALITY_AXES:
            if not _is_full(getattr(audit, axis)):
                reasons.append(f"quality_axis_not_full:{axis}")
        if not audit.audit_id:
            reasons.append("missing_audit_id")
        if not audit.auditor:
            reasons.append("missing_auditor")
        if audit.assessed_payload_sha256 != payload_hash:
            reasons.append("assessed_payload_hash_mismatch")
        if not audit.exact_payload_verified:
            reasons.append("exact_payload_not_verified")
        if not audit.latest_sources_verified:
            reasons.append("latest_sources_not_verified")
        if not audit.evidence_refs:
            reasons.append("missing_evidence_references")
        if audit.contradictions:
            reasons.append("contradictions_present")
        if audit.unsupported_claims:
            reasons.append("unsupported_claims_present")
        if audit.language_issues:
            reasons.append("language_issues_present")
        if audit.formatting_issues:
            reasons.append("formatting_issues_present")
        if audit.unresolved_questions:
            reasons.append("unresolved_questions_present")

        if audit.assessed_at.tzinfo is None or audit.assessed_at.utcoffset() is None:
            reasons.append("assessment_timestamp_not_timezone_aware")
        else:
            age = (moment - audit.assessed_at.astimezone(UTC)).total_seconds()
            if age < -300:
                reasons.append("assessment_timestamp_in_future")
            if audit.valid_for_seconds <= 0 or age > audit.valid_for_seconds:
                reasons.append("assessment_stale")
            if audit.valid_for_seconds > DEFAULT_ASSESSMENT_TTL_SECONDS:
                reasons.append("assessment_validity_exceeds_policy")

        kind = artifact.kind.strip().lower()
        if kind in _NON_RECURSIVE_AUTHORIZATION_KINDS:
            if artifact.authorization_required:
                reasons.append("approval_request_must_not_require_itself")
        else:
            if not artifact.authorization_required:
                reasons.append("authorization_requirement_cannot_be_disabled")
            if not audit.authorization_confirmed:
                reasons.append("authorization_not_confirmed")
            if not audit.authorization_evidence_refs:
                reasons.append("missing_authorization_evidence")

        unique_reasons = tuple(dict.fromkeys(reasons))
        allowed = not unique_reasons
        return GateVerdict(
            allowed=allowed,
            state="RELEASED" if allowed else "REDO_REQUIRED",
            reasons=unique_reasons,
            trace_id=f"outbound-{secrets.token_hex(8)}",
            payload_sha256=payload_hash,
            audit_sha256=audit.audit_sha256,
            route_coherence=float(audit.route_coherence),
            evaluated_at=moment,
        )

    def _append_audit(self, event: str, verdict: GateVerdict, artifact: OutboundArtifact) -> None:
        row = {
            **verdict.to_dict(),
            "event": event,
            "kind": artifact.kind,
            "route": artifact.route,
            "destination_sha256": hashlib.sha256(artifact.destination.encode("utf-8")).hexdigest(),
        }
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(_canonical_json(row) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _signature(self, fields: Mapping[str, Any]) -> str:
        return hmac.new(self._secret, _canonical_json(dict(fields)).encode("utf-8"), hashlib.sha256).hexdigest()

    def record_revision_required(self, artifact: OutboundArtifact, audit: CompletionAudit,
                                 verdict: GateVerdict) -> None:
        """Persist one failed completion attempt before the next revision."""

        if verdict.allowed:
            raise ValueError("an allowed verdict is not a revision-required event")
        self._append_audit("revision_required", verdict, artifact)

    def require_release(
        self,
        artifact: OutboundArtifact,
        audit: CompletionAudit,
        *,
        now: datetime | None = None,
    ) -> ReleaseSeal:
        verdict = self.evaluate(artifact, audit, now=now)
        try:
            self._append_audit("release_allowed" if verdict.allowed else "release_blocked", verdict, artifact)
        except OSError:
            blocked = GateVerdict(
                allowed=False,
                state="REDO_REQUIRED",
                reasons=(*verdict.reasons, "audit_log_unavailable"),
                trace_id=verdict.trace_id,
                payload_sha256=verdict.payload_sha256,
                audit_sha256=verdict.audit_sha256,
                route_coherence=verdict.route_coherence,
                evaluated_at=verdict.evaluated_at,
            )
            raise OutboundBlocked(blocked) from None
        if not verdict.allowed:
            raise OutboundBlocked(verdict)

        issued = verdict.evaluated_at
        assessment_expiry = audit.assessed_at.astimezone(UTC) + timedelta(seconds=audit.valid_for_seconds)
        expires = min(issued + timedelta(seconds=self.release_ttl_seconds), assessment_expiry)
        unsigned = {
            "trace_id": verdict.trace_id,
            "payload_sha256": verdict.payload_sha256,
            "audit_sha256": verdict.audit_sha256,
            "issued_at": issued.isoformat(),
            "expires_at": expires.isoformat(),
        }
        return ReleaseSeal(
            trace_id=verdict.trace_id,
            payload_sha256=verdict.payload_sha256,
            audit_sha256=verdict.audit_sha256,
            issued_at=issued,
            expires_at=expires,
            signature=self._signature(unsigned),
        )

    def verify_release(
        self,
        artifact: OutboundArtifact,
        audit: CompletionAudit,
        seal: ReleaseSeal,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Re-check the sealed exact payload immediately before provider handoff."""

        moment = now or datetime.now(UTC)
        if moment < seal.issued_at - timedelta(seconds=1) or moment > seal.expires_at:
            return False
        if artifact.payload_sha256 != seal.payload_sha256 or audit.audit_sha256 != seal.audit_sha256:
            return False
        if not self.evaluate(artifact, audit, now=moment).allowed:
            return False
        return hmac.compare_digest(self._signature(seal.signed_fields()), seal.signature)

    def record_handoff(self, artifact: OutboundArtifact, audit: CompletionAudit, seal: ReleaseSeal) -> None:
        """Reserve and append the exact hash about to be handed to a provider."""

        verdict = GateVerdict(
            allowed=True,
            state="PROVIDER_HANDOFF_STARTED_UNVERIFIED",
            reasons=(),
            trace_id=seal.trace_id,
            payload_sha256=seal.payload_sha256,
            audit_sha256=seal.audit_sha256,
            route_coherence=float(audit.route_coherence),
            evaluated_at=datetime.now(UTC),
        )
        self._append_audit("provider_handoff_started_unverified", verdict, artifact)


AuditFn = Callable[[OutboundArtifact], CompletionAudit]
ReviseFn = Callable[[OutboundArtifact, GateVerdict], OutboundArtifact]


@dataclass(frozen=True)
class CompletionCycleResult:
    state: str
    attempts: int
    artifact: OutboundArtifact
    audit: CompletionAudit
    verdict: GateVerdict
    seal: ReleaseSeal | None = None


def run_completion_cycle(
    artifact: OutboundArtifact,
    *,
    audit_fn: AuditFn,
    revise_fn: ReviseFn,
    gate: OutboundCompletionGate,
    max_attempts: int = 8,
) -> CompletionCycleResult:
    """Revise until 1.000 or return ``REDO_REQUIRED`` without releasing.

    A cycle is deliberately bounded so a broken auditor cannot spin forever.
    The caller may persist and resume another cycle; the threshold is never
    lowered and no last/least-bad draft is released.
    """

    current = artifact
    audit: CompletionAudit | None = None
    verdict: GateVerdict | None = None
    attempts = max(1, int(max_attempts))
    for number in range(1, attempts + 1):
        audit = audit_fn(current)
        verdict = gate.evaluate(current, audit)
        if verdict.allowed:
            seal = gate.require_release(current, audit)
            return CompletionCycleResult("RELEASED", number, current, audit, verdict, seal)
        gate.record_revision_required(current, audit, verdict)
        if number < attempts:
            current = revise_fn(current, verdict)
    assert audit is not None and verdict is not None
    return CompletionCycleResult("REDO_REQUIRED", attempts, current, audit, verdict, None)


T = TypeVar("T")


def dispatch_released(
    artifact: OutboundArtifact,
    audit: CompletionAudit,
    *,
    gate: OutboundCompletionGate,
    sender: Callable[[], T],
    now: datetime | None = None,
) -> T:
    """The preferred exact-boundary adapter for SMTP, portal, and API senders."""

    seal = gate.require_release(artifact, audit, now=now)
    if not gate.verify_release(artifact, audit, seal, now=now):
        verdict = gate.evaluate(artifact, audit, now=now)
        invalid = GateVerdict(
            allowed=False,
            state="REDO_REQUIRED",
            reasons=(*verdict.reasons, "release_seal_invalid_or_payload_changed"),
            trace_id=seal.trace_id,
            payload_sha256=artifact.payload_sha256,
            audit_sha256=audit.audit_sha256,
            route_coherence=float(audit.route_coherence),
            evaluated_at=datetime.now(UTC),
        )
        raise OutboundBlocked(invalid)
    # Persist the reservation before the irreversible boundary. If the provider
    # call then fails, the log truthfully records an uncertain/failed attempt and
    # callers must reconcile provider state before retrying.
    gate.record_handoff(artifact, audit, seal)
    return sender()


__all__ = [
    "CompletionAudit",
    "CompletionCycleResult",
    "GateVerdict",
    "OutboundArtifact",
    "OutboundBlocked",
    "OutboundCompletionGate",
    "ReleaseSeal",
    "dispatch_released",
    "is_outbound_action",
    "run_completion_cycle",
]
