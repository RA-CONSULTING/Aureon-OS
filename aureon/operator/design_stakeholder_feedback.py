"""Privacy-preserving stakeholder design signals for staged website work.

This module turns one human-created, redacted local evidence snapshot into
small controlled-code capsules.  It never emits the snapshot's free-form
content and has no message-provider, connector, network, credential, website
mutation, package, release, or deployment authority.

A passing audit establishes only that the local signal declaration is fresh,
source-bound, route-bounded, and tied to existing public claim identifiers.
A separately hash-bound response manifest records scope and disposition; it
does not establish design quality or authorise public wording.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

FEEDBACK_SCHEMA = "aureon.design-stakeholder-feedback.v1"
FEEDBACK_AUDIT_SCHEMA = "aureon.design-stakeholder-feedback-audit.v1"
RESPONSE_MANIFEST_SCHEMA = "aureon.design-stakeholder-response-manifest.v1"
RESPONSE_AUDIT_SCHEMA = "aureon.design-stakeholder-response-audit.v1"

DEFAULT_FEEDBACK_PATH = Path("data/website_operator/design_stakeholder_feedback.v1.json")
DEFAULT_CLAIM_REGISTER_PATH = Path("data/website_operator/public_claim_evidence_register.v1.json")

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local privacy-preserving stakeholder design signals only",
    "raw_correspondence_access": "none",
    "canonical_website_mutation": "never",
    "claim_register_mutation": "never",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "connector_access": "none",
    "human_review": "required before any staged design response",
}

SIGNAL_KINDS = frozenset(
    {
        "boundary-confirmation",
        "clarity-gap",
        "diligence-question",
        "evidence-request",
        "positioning-guidance",
    }
)
DISPOSITIONS = frozenset({"action-requested", "consider", "deferred", "no-action"})
PRIORITIES = frozenset({"critical", "high", "medium", "low"})
REQUESTED_RESPONSE_DIMENSIONS = frozenset(
    {
        "audience-specificity",
        "business-model-clarity",
        "claim-boundary",
        "differentiation-clarity",
        "evidence-hierarchy",
        "first-visit-clarity",
        "narrative-sequencing",
        "product-clarity",
    }
)
ROUTE_SCOPES = frozenset(
    {
        "/",
        "/funding/investor-deck/",
        "/projects/",
        "/research/",
    }
)
RESPONSE_CODES = frozenset({"addressed", "declined", "deferred", "unchanged"})

_ALLOWED_CHANGED_PATHS: dict[str, frozenset[str]] = {
    "/": frozenset({"index.html", "script.js", "styles.css"}),
    "/funding/investor-deck/": frozenset({"funding/investor-deck/index.html", "script.js", "styles.css"}),
    "/projects/": frozenset({"data/blades.json", "projects/index.html", "script.js", "styles.css"}),
    "/research/": frozenset(
        {"data/research-catalogue.json", "research/index.html", "script.js", "styles.css"}
    ),
}

_FEEDBACK_FIELDS = frozenset(
    {
        "schema",
        "feedback_id",
        "issued_at",
        "refresh_by",
        "authority",
        "claim_register",
        "evidence_snapshot",
        "signals",
    }
)
_FILE_BINDING_FIELDS = frozenset({"path", "sha256"})
_SNAPSHOT_FIELDS = frozenset({"kind", "path", "sha256"})
_SIGNAL_FIELDS = frozenset(
    {
        "signal_id",
        "signal_kind",
        "disposition",
        "priority",
        "requested_response_dimension",
        "route_scope",
        "claim_ids",
    }
)
_RESPONSE_MANIFEST_FIELDS = frozenset({"schema", "feedback", "authority", "responses", "manifest_sha256"})
_RESPONSE_FEEDBACK_FIELDS = frozenset({"feedback_id", "path", "sha256"})
_RESPONSE_FIELDS = frozenset(
    {
        "disposition",
        "response_code",
        "route_scope",
        "changed_paths",
        "claim_ids",
        "signal_capsule_sha256",
    }
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_URL = re.compile(r"(?i)(?:https?://|www\.|mailto:)")
_TOKEN = re.compile(
    r"(?i)(?:\bBearer\s+[A-Za-z0-9._~+/-]{8,}|"
    r"\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}|"
    r"\bgh[opsu]_[A-Za-z0-9]{8,}|"
    r"\bAIza[A-Za-z0-9_-]{8,}|"
    r"\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret)\s*[:=]\s*\S+)"
)
_RAW_MESSAGE = re.compile(r"(?im)^\s*(?:from|to|cc|bcc|subject|message-id|thread-id|in-reply-to)\s*:")
_PROVIDER_ID = re.compile(r"(?i)\b(?:message|thread|provider|attachment)[-_ ]?id\s*[:=]\s*[A-Za-z0-9_-]{8,}")
_MARKDOWN_QUOTE = re.compile(r"(?m)^\s*>\s+\S")
_NAMED_PERSON = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|Professor|Prof)\.?\s+[A-Z][A-Za-z'-]{1,}\b")
_PRIVATE_FINANCE = re.compile(
    r"(?i)(?:"
    r"(?:£|\$|€)\s*\d|"
    r"\b(?:GBP|USD|EUR)\s*\d|"
    r"\b\d+(?:[.,]\d+)?\s*(?:million|billion|mn|bn)\b|"
    r"\b(?:pre-money|post-money|valuation|revenue|arr|mrr|burn|runway|"
    r"cap\s+table|equity|share\s+price)\b[^\r\n]{0,48}\d"
    r")"
)
_PRIVATE_KEY_NAMES = frozenset(
    {
        "attachment_id",
        "email",
        "finance",
        "financials",
        "message",
        "message_id",
        "name",
        "provider_id",
        "quote",
        "raw_message",
        "sender",
        "stakeholder_name",
        "thread_id",
        "url",
    }
)

_SNAPSHOT_KIND = "human-created-redacted-evidence-snapshot"
_SNAPSHOT_PREFIX = "docs/research/"
_REFRESH_DUE_WINDOW = timedelta(days=3)
_MAX_SNAPSHOT_BYTES = 512 * 1024


class DesignStakeholderFeedbackError(ValueError):
    """A stakeholder signal declaration or response manifest is unsafe."""


def _json_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DesignStakeholderFeedbackError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(parsed, Mapping):
        raise DesignStakeholderFeedbackError(f"{label} must contain one JSON object.")
    return dict(parsed)


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignStakeholderFeedbackError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _exact_fields(
    value: object,
    fields: frozenset[str],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DesignStakeholderFeedbackError(f"{label} must be an object.")
    copied = dict(value)
    private_fields = sorted(str(key) for key in copied if str(key).casefold() in _PRIVATE_KEY_NAMES)
    if private_fields:
        raise DesignStakeholderFeedbackError(
            f"{label} contains prohibited private-content fields: {private_fields}."
        )
    if set(copied) != fields:
        missing = sorted(fields - set(copied))
        extra = sorted(set(copied) - fields)
        raise DesignStakeholderFeedbackError(
            f"{label} fields do not match the contract (missing={missing}, extra={extra})."
        )
    return copied


def _parse_datetime(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DesignStakeholderFeedbackError(f"{label} must be a non-empty ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DesignStakeholderFeedbackError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise DesignStakeholderFeedbackError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignStakeholderFeedbackError(f"{label} must be a non-empty repository-relative path.")
    normalised = value.replace("\\", "/")
    candidate = Path(normalised)
    if (
        candidate.is_absolute()
        or candidate.drive
        or candidate.root
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise DesignStakeholderFeedbackError(f"{label} is unsafe.")
    return candidate.as_posix()


def _relative_inside(root: Path, path: Path, *, label: str) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignStakeholderFeedbackError(f"{label} must remain inside the repository.") from exc


def _has_symlink_component(root: Path, relative: str) -> bool:
    candidate = root
    for part in Path(relative).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            return True
    return False


def _canonical_feedback_path(root: Path, value: Path | None) -> tuple[Path, str]:
    raw = value or DEFAULT_FEEDBACK_PATH
    candidate = raw if raw.is_absolute() else root / raw
    relative = _relative_inside(root, candidate, label="Stakeholder feedback declaration")
    if relative != DEFAULT_FEEDBACK_PATH.as_posix():
        raise DesignStakeholderFeedbackError(
            "Stakeholder feedback must use the canonical "
            "data/website_operator/design_stakeholder_feedback.v1.json location."
        )
    unresolved = root / relative
    if not unresolved.is_file() or unresolved.is_symlink() or _has_symlink_component(root, relative):
        raise DesignStakeholderFeedbackError("Stakeholder feedback must be a regular canonical JSON file.")
    return unresolved.resolve(), relative


def _identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise DesignStakeholderFeedbackError(f"{label} must be a controlled identifier.")
    if _TOKEN.search(value) or _EMAIL.search(value) or _URL.search(value):
        raise DesignStakeholderFeedbackError(f"{label} contains prohibited private material.")
    return value


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise DesignStakeholderFeedbackError(f"{label} must be an uppercase SHA-256.")
    return value


def _string_list(value: object, *, label: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "a list" if allow_empty else "a non-empty list"
        raise DesignStakeholderFeedbackError(f"{label} must be {qualifier}.")
    if not all(isinstance(item, str) and item for item in value):
        raise DesignStakeholderFeedbackError(f"{label} must contain non-empty strings.")
    if len(value) != len(set(value)):
        raise DesignStakeholderFeedbackError(f"{label} cannot contain duplicates.")
    return list(value)


def _private_content_codes(text: str) -> list[str]:
    patterns = (
        ("email", _EMAIL),
        ("url", _URL),
        ("credential-token", _TOKEN),
        ("raw-message", _RAW_MESSAGE),
        ("provider-id", _PROVIDER_ID),
        ("raw-quotation", _MARKDOWN_QUOTE),
        ("named-person", _NAMED_PERSON),
        ("private-finance", _PRIVATE_FINANCE),
    )
    return [code for code, pattern in patterns if pattern.search(text)]


def _resolve_snapshot(
    root: Path,
    binding: Mapping[str, Any],
) -> tuple[dict[str, Any], bool, list[str]]:
    path = _safe_relative_path(binding.get("path"), label="Evidence snapshot path")
    if not path.startswith(_SNAPSHOT_PREFIX) or Path(path).suffix.casefold() not in {
        ".json",
        ".md",
    }:
        raise DesignStakeholderFeedbackError(
            "Evidence snapshot must be a local Markdown or JSON record under docs/research/."
        )
    expected_sha256 = _sha256(binding.get("sha256"), label="Evidence snapshot SHA-256")
    unresolved = root / path
    exists = unresolved.is_file()
    symlinked = _has_symlink_component(root, path)
    resolved_inside = False
    if exists and not symlinked:
        try:
            unresolved.resolve().relative_to(root.resolve())
            resolved_inside = True
        except ValueError:
            resolved_inside = False
    actual_sha256 = ""
    privacy_codes: list[str] = []
    readable = False
    if exists and not symlinked and resolved_inside:
        try:
            if unresolved.stat().st_size <= _MAX_SNAPSHOT_BYTES:
                text = unresolved.read_text(encoding="utf-8-sig")
                actual_sha256 = _sha256_file(unresolved)
                privacy_codes = _private_content_codes(text)
                readable = True
            else:
                privacy_codes = ["snapshot-too-large"]
        except (OSError, UnicodeError):
            privacy_codes = ["snapshot-not-readable"]
    safe = (
        exists
        and not symlinked
        and resolved_inside
        and readable
        and actual_sha256 == expected_sha256
        and not privacy_codes
    )
    summary = {
        "kind": _SNAPSHOT_KIND,
        "path": path,
        "sha256": expected_sha256,
        "available": exists,
        "regular_file": exists and not symlinked and resolved_inside,
        "hash_matches": bool(actual_sha256 and actual_sha256 == expected_sha256),
        "privacy_checked": readable,
        "privacy_safe": readable and not privacy_codes,
    }
    return summary, safe, privacy_codes


def _claim_index(
    root: Path,
    binding: Mapping[str, Any],
) -> tuple[dict[str, set[str]], dict[str, Any], bool]:
    path = _safe_relative_path(binding.get("path"), label="Claim register path")
    if path != DEFAULT_CLAIM_REGISTER_PATH.as_posix():
        raise DesignStakeholderFeedbackError(
            "Stakeholder signals must bind the canonical public claim register."
        )
    expected_sha256 = _sha256(binding.get("sha256"), label="Claim register SHA-256")
    unresolved = root / path
    exists = unresolved.is_file()
    symlinked = _has_symlink_component(root, path)
    routes_by_claim: dict[str, set[str]] = {}
    actual_sha256 = ""
    parsed_ok = False
    if exists and not symlinked:
        try:
            unresolved.resolve().relative_to(root.resolve())
            content = _read_json(unresolved, label="Canonical public claim register")
            actual_sha256 = _sha256_file(unresolved)
            raw_claims = content.get("claims")
            if isinstance(raw_claims, list):
                for raw in raw_claims:
                    if not isinstance(raw, Mapping):
                        routes_by_claim = {}
                        break
                    claim_id = raw.get("id")
                    routes = raw.get("public_routes")
                    if (
                        not isinstance(claim_id, str)
                        or not isinstance(routes, list)
                        or not all(isinstance(route, str) for route in routes)
                        or claim_id in routes_by_claim
                    ):
                        routes_by_claim = {}
                        break
                    routes_by_claim[claim_id] = set(routes)
                parsed_ok = bool(routes_by_claim)
        except (OSError, ValueError, DesignStakeholderFeedbackError):
            routes_by_claim = {}
    safe = exists and not symlinked and parsed_ok and bool(actual_sha256) and actual_sha256 == expected_sha256
    summary = {
        "path": path,
        "sha256": expected_sha256,
        "available": exists,
        "regular_file": exists and not symlinked,
        "hash_matches": bool(actual_sha256 and actual_sha256 == expected_sha256),
        "claim_count": len(routes_by_claim),
    }
    return routes_by_claim, summary, safe


def _normalise_signal(
    value: Mapping[str, Any],
    *,
    routes_by_claim: Mapping[str, set[str]],
) -> dict[str, Any]:
    signal = _exact_fields(value, _SIGNAL_FIELDS, label="Stakeholder signal")
    signal_id = _identifier(signal.get("signal_id"), label="Signal id")
    signal_kind = signal.get("signal_kind")
    disposition = signal.get("disposition")
    priority = signal.get("priority")
    dimension = signal.get("requested_response_dimension")
    route_scope = signal.get("route_scope")
    if signal_kind not in SIGNAL_KINDS:
        raise DesignStakeholderFeedbackError("Signal kind is outside the controlled taxonomy.")
    if disposition not in DISPOSITIONS:
        raise DesignStakeholderFeedbackError("Signal disposition is outside the controlled taxonomy.")
    if priority not in PRIORITIES:
        raise DesignStakeholderFeedbackError("Signal priority is outside the controlled taxonomy.")
    if dimension not in REQUESTED_RESPONSE_DIMENSIONS:
        raise DesignStakeholderFeedbackError(
            "Requested response dimension is outside the controlled taxonomy."
        )
    if route_scope not in ROUTE_SCOPES:
        raise DesignStakeholderFeedbackError("Signal route scope is not an allowed public route.")
    claim_ids = _string_list(signal.get("claim_ids"), label="Signal claim ids")
    unknown = sorted(set(claim_ids) - set(routes_by_claim))
    if unknown:
        raise DesignStakeholderFeedbackError(f"Signal references unknown public claim ids: {unknown}.")
    incompatible = sorted(claim_id for claim_id in claim_ids if route_scope not in routes_by_claim[claim_id])
    if incompatible:
        raise DesignStakeholderFeedbackError(
            f"Signal claim ids are not permitted on route {route_scope}: {incompatible}."
        )
    return {
        "signal_id": signal_id,
        "signal_kind": signal_kind,
        "disposition": disposition,
        "priority": priority,
        "requested_response_dimension": dimension,
        "route_scope": route_scope,
        "claim_ids": sorted(claim_ids),
    }


def signal_capsule_sha256(capsule: Mapping[str, Any]) -> str:
    """Return the deterministic hash of one controlled-code signal capsule."""

    exact = _exact_fields(capsule, _SIGNAL_FIELDS, label="Signal capsule")
    return _json_sha256(exact)


def _check(
    identifier: str,
    passed: bool,
    message: str,
    **evidence: Any,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "passed": bool(passed),
        "message": message,
        "evidence": evidence,
    }


def audit_design_stakeholder_feedback(
    feedback: Mapping[str, Any],
    *,
    feedback_path: Path | None = None,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Audit one canonical local feedback declaration and emit code-only capsules."""

    root = _find_repo_root(repo_root)
    canonical_path, canonical_relative = _canonical_feedback_path(root, feedback_path)
    declaration = _exact_fields(
        feedback,
        _FEEDBACK_FIELDS,
        label="Stakeholder feedback declaration",
    )
    if declaration.get("schema") != FEEDBACK_SCHEMA:
        raise DesignStakeholderFeedbackError(f"Stakeholder feedback schema must be {FEEDBACK_SCHEMA}.")
    feedback_id = _identifier(declaration.get("feedback_id"), label="Feedback id")
    issued_at = _parse_datetime(declaration.get("issued_at"), label="Feedback issued_at")
    refresh_by = _parse_datetime(declaration.get("refresh_by"), label="Feedback refresh_by")
    if refresh_by <= issued_at:
        raise DesignStakeholderFeedbackError("Feedback refresh_by must be after issued_at.")
    if declaration.get("authority") != NON_AUTHORITATIVE_AUTHORITY:
        raise DesignStakeholderFeedbackError(
            "Stakeholder feedback must retain the non-authoritative local boundary."
        )

    claim_binding = _exact_fields(
        declaration.get("claim_register"),
        _FILE_BINDING_FIELDS,
        label="Claim register binding",
    )
    snapshot_binding = _exact_fields(
        declaration.get("evidence_snapshot"),
        _SNAPSHOT_FIELDS,
        label="Evidence snapshot binding",
    )
    if snapshot_binding.get("kind") != _SNAPSHOT_KIND:
        raise DesignStakeholderFeedbackError(
            "Evidence snapshot must be explicitly human-created and redacted."
        )

    routes_by_claim, claim_summary, claim_safe = _claim_index(root, claim_binding)
    snapshot_summary, snapshot_safe, privacy_codes = _resolve_snapshot(
        root,
        snapshot_binding,
    )

    raw_signals = declaration.get("signals")
    if not isinstance(raw_signals, Sequence) or isinstance(raw_signals, (str, bytes)):
        raise DesignStakeholderFeedbackError("Stakeholder signals must be a non-empty list.")
    if not raw_signals:
        raise DesignStakeholderFeedbackError("Stakeholder signals must be a non-empty list.")
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_signals:
        if not isinstance(raw, Mapping):
            raise DesignStakeholderFeedbackError("Each stakeholder signal must be an object.")
        signal = _normalise_signal(raw, routes_by_claim=routes_by_claim)
        if signal["signal_id"] in seen:
            raise DesignStakeholderFeedbackError("Stakeholder signal ids must be unique.")
        seen.add(signal["signal_id"])
        signals.append(signal)
    signals.sort(key=lambda item: item["signal_id"])

    persisted = _read_json(canonical_path, label="Canonical stakeholder feedback")
    file_bound = _json_sha256(persisted) == _json_sha256(declaration)
    reviewed_at = (as_of or datetime.now(UTC)).astimezone(UTC)
    if reviewed_at < issued_at:
        freshness_state = "future-issued"
    elif reviewed_at > refresh_by:
        freshness_state = "stale"
    elif refresh_by - reviewed_at <= _REFRESH_DUE_WINDOW:
        freshness_state = "refresh-due"
    else:
        freshness_state = "current"

    privacy_safe = snapshot_summary["privacy_safe"]
    source_safe = snapshot_safe and claim_safe
    passed = file_bound and source_safe and privacy_safe and freshness_state in {"current", "refresh-due"}
    state = freshness_state if passed else "stale" if freshness_state == "stale" else "blocked"

    capsules: list[dict[str, Any]] = []
    if passed:
        capsules = [
            {
                "signal": signal,
                "signal_capsule_sha256": signal_capsule_sha256(signal),
            }
            for signal in signals
        ]

    checks = [
        _check(
            "feedback-file-binding",
            file_bound,
            "The audited declaration matches the canonical local JSON file.",
            path=canonical_relative,
        ),
        _check(
            "non-authoritative-boundary",
            declaration.get("authority") == NON_AUTHORITATIVE_AUTHORITY,
            "The declaration grants no website, release, package, credential, connector, or deployment authority.",
        ),
        _check(
            "evidence-snapshot-integrity",
            snapshot_safe,
            "The human-created redacted evidence snapshot is regular, local, hash-bound, and privacy-safe.",
            path=snapshot_summary["path"],
            privacy_violation_codes=privacy_codes,
        ),
        _check(
            "claim-register-integrity",
            claim_safe,
            "Signals bind the canonical current public claim register.",
            path=claim_summary["path"],
        ),
        _check(
            "signal-route-claim-closure",
            bool(signals),
            "Every controlled signal is bound to an allowed route and existing route-compatible claim ids.",
            signal_ids=[signal["signal_id"] for signal in signals],
        ),
        _check(
            "feedback-freshness",
            freshness_state in {"current", "refresh-due"},
            "The stakeholder signal declaration remains inside its bounded review window.",
            state=freshness_state,
            refresh_by=_iso(refresh_by),
        ),
    ]

    return {
        "schema": FEEDBACK_AUDIT_SCHEMA,
        "reviewed_at": _iso(reviewed_at),
        "state": state,
        "passed": passed,
        "receipt_authority": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": NON_AUTHORITATIVE_AUTHORITY,
        "feedback": {
            "feedback_id": feedback_id,
            "path": canonical_relative,
            "sha256": _sha256_file(canonical_path),
        },
        "claim_register": claim_summary,
        "evidence_snapshot": snapshot_summary,
        "freshness": {
            "state": freshness_state,
            "issued_at": _iso(issued_at),
            "refresh_by": _iso(refresh_by),
        },
        "signal_capsules": capsules,
        "signal_capsules_sha256": _json_sha256(capsules),
        "summary": {
            "signal_count": len(signals),
            "emitted_capsule_count": len(capsules),
            "action_requested_count": sum(signal["disposition"] == "action-requested" for signal in signals),
            "no_action_count": sum(signal["disposition"] == "no-action" for signal in signals),
        },
        "checks": checks,
        "next_gate": "human-reviewed staged design response manifest",
    }


def audit_design_stakeholder_feedback_file(
    path: Path | None = None,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Read and audit the canonical local feedback declaration."""

    root = _find_repo_root(repo_root)
    canonical_path, _ = _canonical_feedback_path(root, path)
    return audit_design_stakeholder_feedback(
        _read_json(canonical_path, label="Canonical stakeholder feedback"),
        feedback_path=canonical_path,
        repo_root=root,
        as_of=as_of,
    )


def _normalised_manifest_payload(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = {key: item for key, item in value.items() if key != "manifest_sha256"}
    raw_responses = payload.get("responses")
    if isinstance(raw_responses, Mapping):
        responses: dict[str, Any] = {}
        for signal_id, raw in sorted(raw_responses.items(), key=lambda item: str(item[0])):
            if isinstance(raw, Mapping):
                response = dict(raw)
                if isinstance(response.get("changed_paths"), list):
                    response["changed_paths"] = sorted(response["changed_paths"])
                if isinstance(response.get("claim_ids"), list):
                    response["claim_ids"] = sorted(response["claim_ids"])
                responses[str(signal_id)] = response
            else:
                responses[str(signal_id)] = raw
        payload["responses"] = responses
    return payload


def response_manifest_sha256(manifest: Mapping[str, Any]) -> str:
    """Hash all response-manifest fields except the hash field itself."""

    return _json_sha256(_normalised_manifest_payload(manifest))


def audit_design_stakeholder_response_manifest(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Validate complete hash-bound responses to the current signal capsules."""

    root = _find_repo_root(repo_root)
    value = _exact_fields(
        manifest,
        _RESPONSE_MANIFEST_FIELDS,
        label="Stakeholder response manifest",
    )
    if value.get("schema") != RESPONSE_MANIFEST_SCHEMA:
        raise DesignStakeholderFeedbackError(f"Response manifest schema must be {RESPONSE_MANIFEST_SCHEMA}.")
    if value.get("authority") != NON_AUTHORITATIVE_AUTHORITY:
        raise DesignStakeholderFeedbackError(
            "Response manifest must retain the non-authoritative local boundary."
        )
    declared_manifest_sha256 = _sha256(
        value.get("manifest_sha256"),
        label="Response manifest SHA-256",
    )
    if response_manifest_sha256(value) != declared_manifest_sha256:
        raise DesignStakeholderFeedbackError("Response manifest has drifted from its deterministic hash.")

    feedback_binding = _exact_fields(
        value.get("feedback"),
        _RESPONSE_FEEDBACK_FIELDS,
        label="Response feedback binding",
    )
    feedback_id = _identifier(feedback_binding.get("feedback_id"), label="Response feedback id")
    feedback_path = _safe_relative_path(
        feedback_binding.get("path"),
        label="Response feedback path",
    )
    if feedback_path != DEFAULT_FEEDBACK_PATH.as_posix():
        raise DesignStakeholderFeedbackError(
            "Response manifest must bind the canonical stakeholder feedback declaration."
        )
    expected_feedback_sha256 = _sha256(
        feedback_binding.get("sha256"),
        label="Response feedback SHA-256",
    )
    canonical_feedback_path, _ = _canonical_feedback_path(root, root / feedback_path)
    if _sha256_file(canonical_feedback_path) != expected_feedback_sha256:
        raise DesignStakeholderFeedbackError("Response manifest stakeholder feedback binding has drifted.")

    feedback_audit = audit_design_stakeholder_feedback_file(
        canonical_feedback_path,
        repo_root=root,
        as_of=as_of,
    )
    if not feedback_audit["passed"]:
        raise DesignStakeholderFeedbackError(
            "Response manifest cannot use stale or blocked stakeholder signals."
        )
    if feedback_audit["feedback"]["feedback_id"] != feedback_id:
        raise DesignStakeholderFeedbackError(
            "Response manifest feedback id does not match the bound declaration."
        )
    capsules = {item["signal"]["signal_id"]: item for item in feedback_audit["signal_capsules"]}

    raw_responses = value.get("responses")
    if not isinstance(raw_responses, Mapping):
        raise DesignStakeholderFeedbackError("Response manifest responses must be keyed by signal id.")
    response_keys = {str(key) for key in raw_responses}
    if response_keys != set(capsules):
        missing = sorted(set(capsules) - response_keys)
        unknown = sorted(response_keys - set(capsules))
        raise DesignStakeholderFeedbackError(
            f"Response manifest must close every signal exactly once (missing={missing}, unknown={unknown})."
        )

    safe_responses: dict[str, dict[str, Any]] = {}
    changed_path_count = 0
    for signal_id in sorted(capsules):
        raw_response = raw_responses.get(signal_id)
        response = _exact_fields(
            raw_response,
            _RESPONSE_FIELDS,
            label=f"Response for {signal_id}",
        )
        capsule = capsules[signal_id]
        signal = capsule["signal"]
        disposition = response.get("disposition")
        response_code = response.get("response_code")
        route_scope = response.get("route_scope")
        if disposition != signal["disposition"] or disposition not in DISPOSITIONS:
            raise DesignStakeholderFeedbackError(f"Response {signal_id} must retain its audited disposition.")
        if response_code not in RESPONSE_CODES:
            raise DesignStakeholderFeedbackError(f"Response {signal_id} uses an unsupported response code.")
        if route_scope != signal["route_scope"] or route_scope not in ROUTE_SCOPES:
            raise DesignStakeholderFeedbackError(f"Response {signal_id} must retain its audited route scope.")
        capsule_sha256 = _sha256(
            response.get("signal_capsule_sha256"),
            label=f"Response {signal_id} capsule SHA-256",
        )
        if capsule_sha256 != capsule["signal_capsule_sha256"]:
            raise DesignStakeholderFeedbackError(f"Response {signal_id} capsule binding has drifted.")
        changed_paths = [
            _safe_relative_path(path, label=f"Response {signal_id} changed path")
            for path in _string_list(
                response.get("changed_paths"),
                label=f"Response {signal_id} changed paths",
                allow_empty=True,
            )
        ]
        claim_ids = _string_list(
            response.get("claim_ids"),
            label=f"Response {signal_id} claim ids",
            allow_empty=True,
        )
        unsupported_paths = sorted(set(changed_paths) - _ALLOWED_CHANGED_PATHS[str(route_scope)])
        if unsupported_paths:
            raise DesignStakeholderFeedbackError(
                f"Response {signal_id} changed paths exceed its route allow-list: {unsupported_paths}."
            )
        unknown_claims = sorted(set(claim_ids) - set(signal["claim_ids"]))
        if unknown_claims:
            raise DesignStakeholderFeedbackError(
                f"Response {signal_id} claim ids exceed its signal capsule: {unknown_claims}."
            )

        no_change = response_code in {"declined", "deferred", "unchanged"}
        if signal["disposition"] == "no-action" and response_code != "unchanged":
            raise DesignStakeholderFeedbackError(f"No-action signal {signal_id} must remain unchanged.")
        if no_change and (changed_paths or claim_ids):
            raise DesignStakeholderFeedbackError(
                f"Response {signal_id} cannot declare changes for {response_code}."
            )
        if response_code == "addressed" and (not changed_paths or not claim_ids):
            raise DesignStakeholderFeedbackError(
                f"Addressed response {signal_id} requires changed paths and bound claim ids."
            )

        safe_responses[signal_id] = {
            "disposition": disposition,
            "response_code": response_code,
            "route_scope": route_scope,
            "changed_paths": sorted(changed_paths),
            "claim_ids": sorted(claim_ids),
            "signal_capsule_sha256": capsule_sha256,
        }
        changed_path_count += len(changed_paths)

    return {
        "schema": RESPONSE_AUDIT_SCHEMA,
        "reviewed_at": _iso((as_of or datetime.now(UTC)).astimezone(UTC)),
        "state": "pass",
        "passed": True,
        "receipt_authority": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": NON_AUTHORITATIVE_AUTHORITY,
        "feedback": dict(feedback_binding),
        "manifest_sha256": declared_manifest_sha256,
        "responses": safe_responses,
        "summary": {
            "signal_count": len(capsules),
            "response_count": len(safe_responses),
            "changed_path_count": changed_path_count,
            "unchanged_count": sum(
                response["response_code"] == "unchanged" for response in safe_responses.values()
            ),
        },
        "next_gate": "existing candidate, claim, accessibility, visual, performance, and owner review",
    }
