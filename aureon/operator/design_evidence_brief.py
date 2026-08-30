"""Source-bound evidence briefs for Aureon's governed website-design agents.

An investor/design brief is useful only when a worker can tell which claims,
research records, routes and visual constraints it is allowed to act on.  This
module turns that otherwise prose-only direction into a small, deterministic
local contract.  It performs no web request, candidate staging, canonical
website mutation, package construction, credential access or deployment.

A passing brief audit is *planning evidence only*.  A separate reconciled
candidate work order, staged candidate validation, browser QA, named human
review and the WebsiteOperator owner gate retain their existing authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from aureon.operator.design_research_refresh import (
    DEFAULT_SOURCE_DECLARATION_PATH as DEFAULT_RESEARCH_REFRESH_DECLARATION_PATH,
)
from aureon.operator.design_research_refresh import (
    REFRESH_RECEIPT_SCHEMA,
    DesignResearchRefreshError,
    audit_design_research_sources_file,
)
from aureon.operator.design_stakeholder_feedback import (
    DEFAULT_FEEDBACK_PATH as DEFAULT_STAKEHOLDER_FEEDBACK_PATH,
)
from aureon.operator.design_stakeholder_feedback import (
    FEEDBACK_AUDIT_SCHEMA as STAKEHOLDER_FEEDBACK_AUDIT_SCHEMA,
)
from aureon.operator.design_stakeholder_feedback import (
    DesignStakeholderFeedbackError,
    audit_design_stakeholder_feedback_file,
)
from aureon.operator.public_claim_evidence import (
    PublicClaimEvidenceError,
    audit_public_claim_evidence_file,
)

BRIEF_SCHEMA = "aureon.design-evidence-brief.v1"
AUDIT_SCHEMA = "aureon.design-evidence-brief-audit.v1"
DEFAULT_BRIEF_PATH = Path("data/website_operator/investor_site_design_brief.v1.json")
DEFAULT_CLAIM_REGISTER_PATH = Path("data/website_operator/public_claim_evidence_register.v1.json")
AUDIT_OUTPUT_ROOT = Path("docs/audits")

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local source-bound design direction for staged website candidates only",
    "canonical_website_mutation": "never by this brief or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "human_visual_acceptance": "required for material brand changes",
    "release_authority": "WebsiteOperator owner gate only",
}

_BRIEF_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
_SOURCE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "brief_id",
        "issued_at",
        "refresh_by",
        "objective",
        "authority",
        "source_document",
        "research_refresh",
        "feedback_control",
        "claim_control",
        "source_inputs",
        "route_plan",
        "visual_rules",
        "prohibited_public_inferences",
        "acceptance_criteria",
    }
)
_SOURCE_DOCUMENT_FIELDS = frozenset({"path", "sha256"})
_RESEARCH_REFRESH_FIELDS = frozenset(
    {
        "declaration_path",
        "declaration_sha256",
        "required_state",
        "required_passed",
        "artwork_state",
        "artwork_cleared_for_use",
    }
)
_FEEDBACK_CONTROL_FIELDS = frozenset(
    {
        "feedback_path",
        "feedback_sha256",
        "required_state",
        "required_passed",
        "signal_ids",
    }
)
_STAKEHOLDER_CAPSULE_FIELDS = frozenset({"signal", "signal_capsule_sha256"})
_STAKEHOLDER_SIGNAL_FIELDS = frozenset(
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
_CLAIM_CONTROL_FIELDS = frozenset({"register_path", "register_sha256", "claim_ids"})
_SOURCE_INPUT_FIELDS = frozenset({"id", "path", "sha256", "role"})
_ROUTE_PLAN_FIELDS = frozenset({"id", "route", "purpose", "allowed_paths", "claim_ids", "content_order"})
_VISUAL_RULE_FIELDS = frozenset(
    {"id", "purpose", "static_equivalent", "reduced_motion_required", "affects_paths"}
)
_ALLOWED_SOURCE_PREFIXES = (
    "website/",
    "docs/research/",
    "data/website_operator/",
)


class DesignEvidenceBriefError(ValueError):
    """A design-evidence brief is malformed, stale, or insufficiently bound."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DesignEvidenceBriefError(f"{label} must be a non-empty ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DesignEvidenceBriefError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise DesignEvidenceBriefError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignEvidenceBriefError("Could not locate an Aureon repository with pyproject.toml and aureon/.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignEvidenceBriefError(f"Path must remain inside the repository: {path}") from exc


def _safe_relative(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignEvidenceBriefError(f"{label} must be a non-empty repository-relative path.")
    normalised = value.replace("\\", "/")
    path = Path(normalised)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise DesignEvidenceBriefError(f"{label} is unsafe: {value}")
    return path.as_posix()


def _resolve_source_path(root: Path, value: object, *, label: str) -> tuple[Path, str]:
    relative = _safe_relative(value, label=label)
    if not relative.startswith(_ALLOWED_SOURCE_PREFIXES):
        raise DesignEvidenceBriefError(f"{label} must be a declared public/research source, not {relative}.")
    path = (root / relative).resolve()
    if not path.is_file() or path.is_symlink():
        raise DesignEvidenceBriefError(f"{label} must be a regular existing file: {relative}")
    return path, relative


def _resolve_brief_path(root: Path, value: Path | None) -> tuple[Path, str]:
    raw = value or DEFAULT_BRIEF_PATH
    path = raw if raw.is_absolute() else root / raw
    path = path.resolve()
    relative = _relative_to_repo(root, path)
    if relative != DEFAULT_BRIEF_PATH.as_posix():
        raise DesignEvidenceBriefError(
            "Design-evidence brief must use the canonical data/website_operator location."
        )
    if not path.is_file() or path.is_symlink():
        raise DesignEvidenceBriefError(f"Design-evidence brief must be a regular file: {relative}")
    return path, relative


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DesignEvidenceBriefError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(value, Mapping):
        raise DesignEvidenceBriefError(f"{label} must be a JSON object: {path}")
    return dict(value)


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _text(value: object, *, label: str, minimum: int = 1, maximum: int = 500) -> str:
    if not isinstance(value, str):
        raise DesignEvidenceBriefError(f"{label} must be text.")
    result = " ".join(value.split())
    if not minimum <= len(result) <= maximum:
        raise DesignEvidenceBriefError(f"{label} must be between {minimum} and {maximum} characters.")
    if any(token in result.casefold() for token in ("<script", "javascript:", "data:")):
        raise DesignEvidenceBriefError(f"{label} contains an unsafe executable expression.")
    return result


def _text_list(
    value: object,
    *,
    label: str,
    minimum: int = 1,
    maximum: int = 16,
) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise DesignEvidenceBriefError(f"{label} must contain {minimum} to {maximum} items.")
    items = [_text(item, label=f"{label} item") for item in value]
    if len(set(items)) != len(items):
        raise DesignEvidenceBriefError(f"{label} must not contain duplicate items.")
    return items


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "passed": bool(passed),
        "message": message,
        "evidence": evidence,
    }


def _local_route_path(root: Path, value: object) -> tuple[str, str]:
    route = _text(value, label="route", maximum=240)
    parsed = urlsplit(route)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise DesignEvidenceBriefError("Route plan entries must be origin-free local public routes.")
    if not route.startswith("/") or "//" in route or ".." in Path(route).parts:
        raise DesignEvidenceBriefError(f"Route plan entry is unsafe: {route}")
    if route == "/":
        return route, "index.html"
    if route.endswith("/"):
        local = f"{route.strip('/')}/index.html"
    elif route.endswith(".html"):
        local = route.lstrip("/")
    else:
        local = f"{route.strip('/')}/index.html"
    _safe_relative(local, label="route local path")
    if not (root / "website" / local).is_file():
        raise DesignEvidenceBriefError(f"Route plan refers to a missing local website page: {route}")
    return route, local


def _website_path(root: Path, value: object, *, label: str) -> str:
    relative = _safe_relative(value, label=label)
    candidate = (root / "website" / relative).resolve()
    try:
        candidate.relative_to((root / "website").resolve())
    except ValueError as exc:
        raise DesignEvidenceBriefError(f"{label} escapes website/: {relative}") from exc
    if not candidate.is_file() or candidate.is_symlink():
        raise DesignEvidenceBriefError(f"{label} must name an existing regular website file: {relative}")
    return relative


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DesignEvidenceBriefError(f"{label} must be an object.")
    return dict(value)


def _claim_capsule(claim: Mapping[str, Any], *, claim_id: str) -> dict[str, Any]:
    """Reduce one verified public claim to the worker's route-safe context."""

    source = _mapping(claim.get("source"), label=f"claim '{claim_id}' source")
    source_path = _safe_relative(source.get("path"), label=f"claim '{claim_id}' source path")
    source_sha256 = source.get("sha256")
    if (
        not source_path.startswith("website/")
        or not isinstance(source_sha256, str)
        or not _SHA256.fullmatch(source_sha256)
    ):
        raise DesignEvidenceBriefError(
            f"Claim '{claim_id}' must retain a public website source and SHA-256 binding."
        )
    public_routes = _text_list(
        claim.get("public_routes"),
        label=f"claim '{claim_id}' public_routes",
        minimum=1,
        maximum=32,
    )
    return {
        "id": claim_id,
        "claim": _text(claim.get("claim"), label=f"claim '{claim_id}' wording"),
        "state": _text(claim.get("state"), label=f"claim '{claim_id}' state", maximum=80),
        "boundary": _text(claim.get("boundary"), label=f"claim '{claim_id}' boundary", minimum=12),
        "permitted_wording": _text_list(
            claim.get("permitted_wording"),
            label=f"claim '{claim_id}' permitted wording",
            maximum=64,
        ),
        "prohibited_inferences": _text_list(
            claim.get("prohibited_inferences"),
            label=f"claim '{claim_id}' prohibited inferences",
            maximum=64,
        ),
        "public_routes": public_routes,
        "expires_on": _text(claim.get("expires_on"), label=f"claim '{claim_id}' expiry", maximum=20),
        "source": {"path": source_path, "sha256": source_sha256},
    }


def _exact_fields(value: Mapping[str, Any], fields: frozenset[str], *, label: str) -> None:
    actual = set(value)
    if actual != fields:
        missing = sorted(fields - actual)
        extra = sorted(actual - fields)
        raise DesignEvidenceBriefError(
            f"{label} fields do not match the contract (missing={missing}, extra={extra})."
        )


def _redacted_research_refresh_binding(
    raw_binding: object,
    *,
    root: Path,
    current: datetime,
) -> tuple[dict[str, Any], bool, str]:
    """Return only the refresh fields a design brief may carry forward.

    The brief never carries source URLs, source contents, connector metadata,
    artwork data, or any local receipt path.  It only proves that the
    canonical redacted declaration has not changed and remains current under
    the separate refresh contract.
    """

    binding = {
        "declaration_path": "",
        "declaration_sha256": "",
        "state": "",
        "passed": False,
        "artwork": {"state": "", "cleared_for_use": False},
    }
    try:
        declared = _mapping(raw_binding, label="research_refresh")
        _exact_fields(declared, _RESEARCH_REFRESH_FIELDS, label="research_refresh")
        declaration_path = _safe_relative(
            declared.get("declaration_path"), label="research_refresh declaration path"
        )
        if declaration_path != DEFAULT_RESEARCH_REFRESH_DECLARATION_PATH.as_posix():
            raise DesignEvidenceBriefError(
                "research_refresh must bind the canonical design research source declaration."
            )
        declaration_sha256 = declared.get("declaration_sha256")
        if not isinstance(declaration_sha256, str) or not _SHA256.fullmatch(declaration_sha256):
            raise DesignEvidenceBriefError("research_refresh declaration_sha256 must be uppercase SHA-256.")
        declaration_file = (root / declaration_path).resolve()
        if not declaration_file.is_file() or declaration_file.is_symlink():
            raise DesignEvidenceBriefError(
                "research_refresh canonical declaration must be an existing regular file."
            )
        if _sha256(declaration_file) != declaration_sha256:
            raise DesignEvidenceBriefError(
                "research_refresh declaration hash no longer matches the canonical declaration."
            )
        if declared.get("required_state") != "current" or declared.get("required_passed") is not True:
            raise DesignEvidenceBriefError(
                "research_refresh must require one currently passing local refresh review."
            )
        if (
            declared.get("artwork_state") != "not-cleared"
            or declared.get("artwork_cleared_for_use") is not False
        ):
            raise DesignEvidenceBriefError("research_refresh must retain the not-cleared artwork boundary.")

        refresh = audit_design_research_sources_file(repo_root=root, as_of=current)
        receipt_declaration = _mapping(
            refresh.get("declaration"), label="research_refresh receipt declaration"
        )
        receipt_artwork = _mapping(refresh.get("artwork"), label="research_refresh receipt artwork")
        binding = {
            "declaration_path": str(receipt_declaration.get("path") or ""),
            "declaration_sha256": str(receipt_declaration.get("sha256") or ""),
            "state": str(refresh.get("state") or ""),
            "passed": refresh.get("passed") is True,
            "artwork": {
                "state": str(receipt_artwork.get("state") or ""),
                "cleared_for_use": receipt_artwork.get("cleared_for_use") is True,
            },
        }
        current_refresh = (
            refresh.get("schema") == REFRESH_RECEIPT_SCHEMA
            and binding["declaration_path"] == declaration_path
            and binding["declaration_sha256"] == declaration_sha256
            and binding["state"] == "current"
            and binding["passed"] is True
            and binding["artwork"] == {"state": "not-cleared", "cleared_for_use": False}
            and refresh.get("release_eligible") is False
            and refresh.get("package_authority") == "none"
            and refresh.get("deployment_authority") == "none"
        )
        if not current_refresh:
            raise DesignEvidenceBriefError(
                "research_refresh is not a currently passing redacted local source review."
            )
        return binding, True, ""
    except (DesignEvidenceBriefError, DesignResearchRefreshError, OSError) as exc:
        return binding, False, str(exc)


def _redacted_stakeholder_feedback_binding(
    raw_binding: object,
    *,
    root: Path,
    current: datetime,
) -> tuple[dict[str, Any], list[dict[str, Any]], bool, str]:
    """Bind current code-only stakeholder signals without exposing their source.

    The canonical feedback validator may inspect one human-redacted local
    snapshot, but this brief receives only stable signal ids, controlled
    taxonomies, exact route/claim scope and deterministic hashes. It never
    carries correspondence, identity, quotations, provider metadata, URLs,
    finance or free-form rationale.
    """

    binding: dict[str, Any] = {
        "feedback_id": "",
        "path": "",
        "sha256": "",
        "state": "",
        "passed": False,
        "signal_ids": [],
        "signal_capsules_sha256": "",
    }
    try:
        declared = _mapping(raw_binding, label="feedback_control")
        _exact_fields(declared, _FEEDBACK_CONTROL_FIELDS, label="feedback_control")
        feedback_path = _safe_relative(declared.get("feedback_path"), label="feedback_control feedback path")
        if feedback_path != DEFAULT_STAKEHOLDER_FEEDBACK_PATH.as_posix():
            raise DesignEvidenceBriefError(
                "feedback_control must bind the canonical stakeholder-feedback declaration."
            )
        feedback_sha256 = declared.get("feedback_sha256")
        if not isinstance(feedback_sha256, str) or not _SHA256.fullmatch(feedback_sha256):
            raise DesignEvidenceBriefError("feedback_control feedback_sha256 must be uppercase SHA-256.")
        feedback_file = (root / feedback_path).resolve()
        if not feedback_file.is_file() or feedback_file.is_symlink():
            raise DesignEvidenceBriefError(
                "feedback_control canonical declaration must be an existing regular file."
            )
        if _sha256(feedback_file) != feedback_sha256:
            raise DesignEvidenceBriefError(
                "feedback_control hash no longer matches the canonical declaration."
            )
        if declared.get("required_state") != "current" or declared.get("required_passed") is not True:
            raise DesignEvidenceBriefError(
                "feedback_control must require one currently passing privacy-safe review."
            )
        signal_ids = _text_list(
            declared.get("signal_ids"),
            label="feedback_control signal_ids",
            minimum=1,
            maximum=32,
        )

        feedback_audit = audit_design_stakeholder_feedback_file(
            repo_root=root,
            as_of=current,
        )
        feedback_record = _mapping(feedback_audit.get("feedback"), label="stakeholder feedback audit binding")
        raw_capsules = feedback_audit.get("signal_capsules")
        if not isinstance(raw_capsules, list) or not all(isinstance(item, Mapping) for item in raw_capsules):
            raise DesignEvidenceBriefError(
                "Stakeholder feedback audit did not emit controlled signal capsules."
            )
        capsules = [dict(item) for item in raw_capsules]
        audited_signal_ids = [
            str(_mapping(item.get("signal"), label="stakeholder signal capsule").get("signal_id") or "")
            for item in capsules
        ]
        if len(set(audited_signal_ids)) != len(audited_signal_ids) or set(signal_ids) != set(
            audited_signal_ids
        ):
            raise DesignEvidenceBriefError(
                "feedback_control must bind every current controlled signal exactly once."
            )

        binding = {
            "feedback_id": str(feedback_record.get("feedback_id") or ""),
            "path": str(feedback_record.get("path") or ""),
            "sha256": str(feedback_record.get("sha256") or ""),
            "state": str(feedback_audit.get("state") or ""),
            "passed": feedback_audit.get("passed") is True,
            "signal_ids": signal_ids,
            "signal_capsules_sha256": str(feedback_audit.get("signal_capsules_sha256") or ""),
        }
        current_feedback = (
            feedback_audit.get("schema") == STAKEHOLDER_FEEDBACK_AUDIT_SCHEMA
            and binding["path"] == feedback_path
            and binding["sha256"] == feedback_sha256
            and binding["state"] == "current"
            and binding["passed"] is True
            and feedback_audit.get("receipt_authority") is False
            and feedback_audit.get("release_eligible") is False
            and feedback_audit.get("package_authority") == "none"
            and feedback_audit.get("deployment_authority") == "none"
            and bool(binding["feedback_id"])
            and bool(binding["signal_capsules_sha256"])
        )
        if not current_feedback:
            raise DesignEvidenceBriefError(
                "feedback_control is not a currently passing privacy-safe local signal review."
            )
        return binding, capsules, True, ""
    except (
        DesignEvidenceBriefError,
        DesignStakeholderFeedbackError,
        OSError,
    ) as exc:
        return binding, [], False, str(exc)


def audit_design_evidence_brief(
    brief: Mapping[str, Any],
    *,
    brief_path: Path,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Audit an in-memory design brief against its current local evidence.

    The caller may use this result to prepare a local candidate work order;
    it never turns the brief into a permission to alter ``website/`` or to
    promote, package, or deploy a candidate.
    """

    root = _find_repo_root(repo_root)
    current = (as_of or _utc_now()).astimezone(UTC)
    checks: list[dict[str, Any]] = []
    raw = dict(brief)
    checks.append(
        _check(
            "schema",
            raw.get("schema") == BRIEF_SCHEMA,
            "Brief schema must match the current source-bound contract.",
        )
    )
    checks.append(
        _check(
            "top-level-fields",
            set(raw) == _TOP_LEVEL_FIELDS,
            "Brief must retain exactly the declared evidence-contract fields.",
            missing=sorted(_TOP_LEVEL_FIELDS - set(raw)),
            extra=sorted(set(raw) - _TOP_LEVEL_FIELDS),
        )
    )

    try:
        canonical_brief_path, canonical_brief_relative = _resolve_brief_path(root, brief_path)
        persisted_brief = _read_json(canonical_brief_path, label="Canonical design-evidence brief")
        brief_file_binding_ok = persisted_brief == raw
        brief_file_binding_error = (
            ""
            if brief_file_binding_ok
            else ("In-memory brief content does not match the canonical persisted brief file.")
        )
        brief_file_sha256 = _sha256(canonical_brief_path)
    except DesignEvidenceBriefError as exc:
        canonical_brief_relative = ""
        brief_file_binding_ok = False
        brief_file_binding_error = str(exc)
        brief_file_sha256 = ""
    checks.append(
        _check(
            "brief-file-binding",
            brief_file_binding_ok,
            "The audited mapping must exactly match the canonical persisted brief before it can produce a receipt.",
            path=canonical_brief_relative,
            sha256=brief_file_sha256,
            error=brief_file_binding_error,
        )
    )

    checks.append(
        _check(
            "authority",
            raw.get("authority") == NON_AUTHORITATIVE_AUTHORITY,
            "Brief must retain no canonical mutation, package, credential, or deployment authority.",
        )
    )

    brief_id = ""
    try:
        candidate_id = raw.get("brief_id")
        if not isinstance(candidate_id, str) or not _BRIEF_ID.fullmatch(candidate_id):
            raise DesignEvidenceBriefError("brief_id must be a stable lowercase identifier.")
        brief_id = candidate_id
        objective = _text(raw.get("objective"), label="objective", minimum=12, maximum=600)
        issued_at = _parse_datetime(raw.get("issued_at"), label="issued_at")
        refresh_by = _parse_datetime(raw.get("refresh_by"), label="refresh_by")
        timing_ok = issued_at <= current <= refresh_by
        timing_error = "" if timing_ok else "Brief refresh deadline has elapsed or precedes issue time."
    except DesignEvidenceBriefError as exc:
        objective = ""
        issued_at = current
        refresh_by = current
        timing_ok = False
        timing_error = str(exc)
    checks.append(
        _check(
            "brief-identity-and-freshness",
            bool(brief_id) and timing_ok,
            "Brief needs a valid id, objective, issue time and unexpired refresh deadline.",
            brief_id=brief_id,
            issued_at=_iso(issued_at),
            refresh_by=_iso(refresh_by),
            error=timing_error,
        )
    )

    source_document: dict[str, Any] = {}
    try:
        source_document = _mapping(raw.get("source_document"), label="source_document")
        _exact_fields(source_document, _SOURCE_DOCUMENT_FIELDS, label="source_document")
        document_path, document_relative = _resolve_source_path(
            root, source_document.get("path"), label="source_document path"
        )
        document_ok = (
            document_relative.startswith("docs/research/")
            and document_path.suffix.lower() == ".md"
            and source_document.get("sha256") == _sha256(document_path)
        )
        document_error = ""
    except DesignEvidenceBriefError as exc:
        document_relative = ""
        document_ok = False
        document_error = str(exc)
    checks.append(
        _check(
            "source-document-binding",
            document_ok,
            "Brief must bind its human-readable design document by exact current hash.",
            path=document_relative,
            error=document_error,
        )
    )

    research_refresh, research_refresh_ok, research_refresh_error = _redacted_research_refresh_binding(
        raw.get("research_refresh"),
        root=root,
        current=current,
    )
    checks.append(
        _check(
            "research-refresh-binding",
            research_refresh_ok,
            "Brief requires a current hash-bound redacted research refresh; it never clears artwork or grants candidate, package, release, or deployment authority.",
            declaration_path=research_refresh["declaration_path"],
            declaration_sha256=research_refresh["declaration_sha256"],
            state=research_refresh["state"],
            refresh_passed=research_refresh["passed"],
            artwork=research_refresh["artwork"],
            error=research_refresh_error,
        )
    )

    (
        stakeholder_feedback,
        stakeholder_signal_capsules,
        stakeholder_feedback_ok,
        stakeholder_feedback_error,
    ) = _redacted_stakeholder_feedback_binding(
        raw.get("feedback_control"),
        root=root,
        current=current,
    )
    checks.append(
        _check(
            "stakeholder-feedback-binding",
            stakeholder_feedback_ok,
            "Brief requires a current hash-bound privacy-safe stakeholder signal review; raw correspondence and private identity never reach the brief or worker.",
            feedback_id=stakeholder_feedback["feedback_id"],
            path=stakeholder_feedback["path"],
            sha256=stakeholder_feedback["sha256"],
            state=stakeholder_feedback["state"],
            feedback_passed=stakeholder_feedback["passed"],
            signal_ids=stakeholder_feedback["signal_ids"],
            signal_capsules_sha256=stakeholder_feedback["signal_capsules_sha256"],
            error=stakeholder_feedback_error,
        )
    )

    claim_control: dict[str, Any] = {}
    selected_claim_ids: list[str] = []
    claim_index: dict[str, Mapping[str, Any]] = {}
    claim_audit: dict[str, Any] = {}
    try:
        claim_control = _mapping(raw.get("claim_control"), label="claim_control")
        _exact_fields(claim_control, _CLAIM_CONTROL_FIELDS, label="claim_control")
        register_relative = _safe_relative(claim_control.get("register_path"), label="claim register path")
        if register_relative != DEFAULT_CLAIM_REGISTER_PATH.as_posix():
            raise DesignEvidenceBriefError("Brief must bind the canonical public-claim register.")
        register_path = (root / register_relative).resolve()
        if not register_path.is_file() or register_path.is_symlink():
            raise DesignEvidenceBriefError("Claim register is unavailable.")
        register_sha = claim_control.get("register_sha256")
        if not isinstance(register_sha, str) or register_sha != _sha256(register_path):
            raise DesignEvidenceBriefError("Claim register hash no longer matches the brief.")
        raw_ids = claim_control.get("claim_ids")
        if (
            not isinstance(raw_ids, list)
            or not raw_ids
            or not all(isinstance(item, str) and item.strip() for item in raw_ids)
        ):
            raise DesignEvidenceBriefError("claim_ids must be a non-empty string list.")
        selected_claim_ids = [str(item) for item in raw_ids]
        if len(set(selected_claim_ids)) != len(selected_claim_ids):
            raise DesignEvidenceBriefError("claim_ids must not contain duplicates.")
        claim_audit = audit_public_claim_evidence_file(
            repo_root=root,
            as_of=current.date(),
        )
        register = _read_json(register_path, label="Claim register")
        raw_claims = register.get("claims")
        if not isinstance(raw_claims, list) or not all(isinstance(item, Mapping) for item in raw_claims):
            raise DesignEvidenceBriefError("Claim register claims are malformed.")
        claim_index = {
            str(item.get("id")): item
            for item in raw_claims
            if isinstance(item.get("id"), str) and item.get("id")
        }
        missing_claims = sorted(set(selected_claim_ids) - set(claim_index))
        claim_ok = claim_audit.get("passed") is True and not missing_claims
        claim_error = "" if claim_ok else f"Missing or invalid claim ids: {missing_claims}"
    except (DesignEvidenceBriefError, PublicClaimEvidenceError) as exc:
        register_relative = ""
        missing_claims = selected_claim_ids
        claim_ok = False
        claim_error = str(exc)
    checks.append(
        _check(
            "claim-register-binding",
            claim_ok,
            "Brief must bind currently passing public-claim evidence and selected claim ids.",
            register_path=register_relative,
            selected_claim_ids=selected_claim_ids,
            missing_claim_ids=missing_claims,
            claim_audit_state=claim_audit.get("state"),
            error=claim_error,
        )
    )

    source_inputs: list[dict[str, Any]] = []
    source_paths: set[str] = set()
    try:
        raw_inputs = raw.get("source_inputs")
        if not isinstance(raw_inputs, list) or not 2 <= len(raw_inputs) <= 24:
            raise DesignEvidenceBriefError("source_inputs must contain 2 to 24 entries.")
        seen_ids: set[str] = set()
        for raw_input in raw_inputs:
            item = _mapping(raw_input, label="source input")
            _exact_fields(item, _SOURCE_INPUT_FIELDS, label="source input")
            identifier = item.get("id")
            if not isinstance(identifier, str) or not _SOURCE_ID.fullmatch(identifier):
                raise DesignEvidenceBriefError("Source input id must be a stable lowercase identifier.")
            if identifier in seen_ids:
                raise DesignEvidenceBriefError("Source input ids must be unique.")
            seen_ids.add(identifier)
            source_path, source_relative = _resolve_source_path(
                root, item.get("path"), label=f"source input '{identifier}' path"
            )
            declared_sha = item.get("sha256")
            if not isinstance(declared_sha, str) or not _SHA256.fullmatch(declared_sha):
                raise DesignEvidenceBriefError(f"Source input '{identifier}' has an invalid SHA-256.")
            if declared_sha != _sha256(source_path):
                raise DesignEvidenceBriefError(f"Source input '{identifier}' hash no longer matches.")
            source_inputs.append(
                {
                    "id": identifier,
                    "path": source_relative,
                    "sha256": declared_sha,
                    "role": _text(item.get("role"), label=f"source input '{identifier}' role"),
                }
            )
            source_paths.add(source_relative)
        selected_claim_source_paths = {
            str(_mapping(claim_index[claim_id].get("source"), label="claim source").get("path"))
            for claim_id in selected_claim_ids
            if claim_id in claim_index
        }
        unbound_claim_sources = sorted(selected_claim_source_paths - source_paths)
        sources_ok = not unbound_claim_sources
        sources_error = "" if sources_ok else "Selected claim sources are missing from source_inputs."
    except DesignEvidenceBriefError as exc:
        selected_claim_source_paths = set()
        unbound_claim_sources = []
        sources_ok = False
        sources_error = str(exc)
    checks.append(
        _check(
            "source-input-bindings",
            sources_ok,
            "Every declared evidence input and every selected claim source must be current and hash-bound.",
            source_count=len(source_inputs),
            unbound_claim_source_paths=unbound_claim_sources,
            error=sources_error,
        )
    )

    route_plan: list[dict[str, Any]] = []
    all_allowed_paths: set[str] = set()
    try:
        raw_plan = raw.get("route_plan")
        if not isinstance(raw_plan, list) or not 1 <= len(raw_plan) <= 12:
            raise DesignEvidenceBriefError("route_plan must contain 1 to 12 route entries.")
        seen_route_ids: set[str] = set()
        seen_routes: set[str] = set()
        seen_local_paths: set[str] = set()
        for raw_route in raw_plan:
            item = _mapping(raw_route, label="route plan entry")
            _exact_fields(item, _ROUTE_PLAN_FIELDS, label="route plan entry")
            identifier = item.get("id")
            if not isinstance(identifier, str) or not _SOURCE_ID.fullmatch(identifier):
                raise DesignEvidenceBriefError("Route plan id must be a stable lowercase identifier.")
            if identifier in seen_route_ids:
                raise DesignEvidenceBriefError("Route plan ids must be unique.")
            seen_route_ids.add(identifier)
            route, local_path = _local_route_path(root, item.get("route"))
            if route in seen_routes:
                raise DesignEvidenceBriefError("Route plan routes must be unique.")
            seen_routes.add(route)
            if local_path in seen_local_paths:
                raise DesignEvidenceBriefError(
                    "Route plan may not include aliases for the same local website page."
                )
            seen_local_paths.add(local_path)
            raw_paths = item.get("allowed_paths")
            if not isinstance(raw_paths, list) or not 1 <= len(raw_paths) <= 12:
                raise DesignEvidenceBriefError("Route plan allowed_paths must contain 1 to 12 exact files.")
            allowed_paths = [_website_path(root, path, label="route plan allowed path") for path in raw_paths]
            if len(set(allowed_paths)) != len(allowed_paths) or local_path not in allowed_paths:
                raise DesignEvidenceBriefError(
                    "Route plan must include its own local HTML path and no duplicate allowed paths."
                )
            raw_claim_ids = item.get("claim_ids")
            if (
                not isinstance(raw_claim_ids, list)
                or not raw_claim_ids
                or not all(isinstance(claim_id, str) for claim_id in raw_claim_ids)
            ):
                raise DesignEvidenceBriefError("Route plan claim_ids must be a non-empty string list.")
            route_claim_ids = [str(claim_id) for claim_id in raw_claim_ids]
            if len(set(route_claim_ids)) != len(route_claim_ids) or not set(route_claim_ids).issubset(
                selected_claim_ids
            ):
                raise DesignEvidenceBriefError(
                    "Route plan claim_ids must be unique and selected by claim_control."
                )
            route_plan.append(
                {
                    "id": identifier,
                    "route": route,
                    "local_path": local_path,
                    "purpose": _text(item.get("purpose"), label="route plan purpose", minimum=12),
                    "allowed_paths": allowed_paths,
                    "claim_ids": route_claim_ids,
                    "content_order": _text_list(
                        item.get("content_order"),
                        label="route plan content_order",
                        minimum=3,
                        maximum=8,
                    ),
                }
            )
            all_allowed_paths.update(allowed_paths)
        routes_ok = True
        routes_error = ""
    except DesignEvidenceBriefError as exc:
        routes_ok = False
        routes_error = str(exc)
    checks.append(
        _check(
            "route-plan",
            routes_ok,
            "Each design route needs an exact local page, bounded path list, selected evidence and reading order.",
            route_count=len(route_plan),
            allowed_path_count=len(all_allowed_paths),
            error=routes_error,
        )
    )

    route_claim_mismatches: list[dict[str, str]] = []
    route_claim_permissions_ok = routes_ok and bool(claim_index)
    route_claim_permissions_error = ""
    if route_claim_permissions_ok:
        for planned_route in route_plan:
            route = planned_route["route"]
            for claim_id in planned_route["claim_ids"]:
                claim = claim_index.get(claim_id)
                public_routes = claim.get("public_routes") if isinstance(claim, Mapping) else None
                if not isinstance(public_routes, list) or route not in public_routes:
                    route_claim_mismatches.append({"route": route, "claim_id": claim_id})
        route_claim_permissions_ok = not route_claim_mismatches
        if route_claim_mismatches:
            route_claim_permissions_error = (
                "One or more planned claims are not permitted on their exact public route."
            )
    else:
        route_claim_permissions_error = (
            "A structurally valid route plan and current selected-claim index are required."
        )
    checks.append(
        _check(
            "route-claim-permissions",
            route_claim_permissions_ok,
            "Every planned route claim must be explicitly permitted on that exact public route by the current claim register.",
            mismatch_count=len(route_claim_mismatches),
            mismatches=route_claim_mismatches,
            error=route_claim_permissions_error,
        )
    )

    route_claim_capsules: list[dict[str, Any]] = []
    try:
        if not route_claim_permissions_ok:
            raise DesignEvidenceBriefError(
                "Route claim capsules require an exact-route permission check to pass."
            )
        planned_claim_ids = {
            claim_id for planned_route in route_plan for claim_id in planned_route["claim_ids"]
        }
        unplanned_claim_ids = sorted(set(selected_claim_ids) - planned_claim_ids)
        if unplanned_claim_ids:
            raise DesignEvidenceBriefError(
                "Every selected claim must be assigned to at least one permitted planned route."
            )
        for planned_route in route_plan:
            route_claim_capsules.append(
                {
                    "route_id": planned_route["id"],
                    "route": planned_route["route"],
                    "claims": [
                        _claim_capsule(claim_index[claim_id], claim_id=claim_id)
                        for claim_id in planned_route["claim_ids"]
                    ],
                }
            )
        capsules_ok = True
        capsules_error = ""
    except DesignEvidenceBriefError as exc:
        route_claim_capsules = []
        capsules_ok = False
        capsules_error = str(exc)
        unplanned_claim_ids = sorted(set(selected_claim_ids))
    checks.append(
        _check(
            "route-claim-capsules",
            capsules_ok,
            "Each selected claim must reach a permitted route with immutable wording, boundary, inference and source context.",
            capsule_count=sum(len(item["claims"]) for item in route_claim_capsules),
            unplanned_claim_ids=unplanned_claim_ids,
            error=capsules_error,
        )
    )

    route_feedback_capsules: list[dict[str, Any]] = []
    route_feedback_error = ""
    try:
        if not stakeholder_feedback_ok:
            raise DesignEvidenceBriefError(
                "Route feedback capsules require a current privacy-safe feedback review."
            )
        if not route_claim_permissions_ok or not capsules_ok:
            raise DesignEvidenceBriefError(
                "Route feedback capsules require exact route and claim permissions."
            )
        planned_routes_by_path = {item["route"]: item for item in route_plan}
        capsules_by_route: dict[str, list[dict[str, Any]]] = {item["route"]: [] for item in route_plan}
        seen_feedback_signal_ids: set[str] = set()
        for raw_capsule in stakeholder_signal_capsules:
            capsule = _mapping(raw_capsule, label="stakeholder signal capsule")
            _exact_fields(
                capsule,
                _STAKEHOLDER_CAPSULE_FIELDS,
                label="stakeholder signal capsule",
            )
            signal = _mapping(capsule.get("signal"), label="stakeholder signal capsule signal")
            _exact_fields(
                signal,
                _STAKEHOLDER_SIGNAL_FIELDS,
                label="stakeholder signal capsule signal",
            )
            signal_id = _text(
                signal.get("signal_id"),
                label="stakeholder signal id",
                maximum=128,
            )
            if signal_id in seen_feedback_signal_ids:
                raise DesignEvidenceBriefError("Stakeholder signal capsules must contain unique signal ids.")
            seen_feedback_signal_ids.add(signal_id)
            route_scope = _text(
                signal.get("route_scope"),
                label=f"stakeholder signal '{signal_id}' route scope",
                maximum=240,
            )
            feedback_route = planned_routes_by_path.get(route_scope)
            if feedback_route is None:
                raise DesignEvidenceBriefError(
                    f"Stakeholder signal '{signal_id}' is outside the planned design routes."
                )
            signal_claim_ids = _text_list(
                signal.get("claim_ids"),
                label=f"stakeholder signal '{signal_id}' claim_ids",
                minimum=1,
                maximum=16,
            )
            unsupported_claim_ids = sorted(set(signal_claim_ids) - set(feedback_route["claim_ids"]))
            if unsupported_claim_ids:
                raise DesignEvidenceBriefError(
                    f"Stakeholder signal '{signal_id}' exceeds the selected claims for "
                    f"{route_scope}: {unsupported_claim_ids}."
                )
            capsule_sha256 = capsule.get("signal_capsule_sha256")
            if (
                not isinstance(capsule_sha256, str)
                or not _SHA256.fullmatch(capsule_sha256)
                or capsule_sha256 != _json_sha256(signal)
            ):
                raise DesignEvidenceBriefError(
                    f"Stakeholder signal '{signal_id}' lacks an uppercase SHA-256 binding."
                )
            capsules_by_route[route_scope].append(
                {
                    "signal": dict(signal),
                    "signal_capsule_sha256": capsule_sha256,
                }
            )

        missing_feedback_signal_ids = sorted(
            set(stakeholder_feedback["signal_ids"]) - seen_feedback_signal_ids
        )
        unknown_feedback_signal_ids = sorted(
            seen_feedback_signal_ids - set(stakeholder_feedback["signal_ids"])
        )
        if missing_feedback_signal_ids or unknown_feedback_signal_ids:
            raise DesignEvidenceBriefError(
                "Route feedback capsules do not exactly cover the bound stakeholder signals."
            )
        route_feedback_capsules = [
            {
                "route_id": route_item["id"],
                "route": route_item["route"],
                "signals": sorted(
                    capsules_by_route[route_item["route"]],
                    key=lambda item: str(
                        _mapping(
                            item.get("signal"),
                            label="route feedback signal",
                        ).get("signal_id")
                        or ""
                    ),
                ),
            }
            for route_item in route_plan
        ]
        route_feedback_ok = True
    except DesignEvidenceBriefError as exc:
        route_feedback_capsules = []
        route_feedback_ok = False
        route_feedback_error = str(exc)
        missing_feedback_signal_ids = list(stakeholder_feedback["signal_ids"])
        unknown_feedback_signal_ids = []
    checks.append(
        _check(
            "route-feedback-capsules",
            route_feedback_ok,
            "Every current stakeholder signal must reach one exact planned route using only controlled codes, existing claim ids and deterministic hashes.",
            route_capsule_count=len(route_feedback_capsules),
            signal_count=sum(len(item["signals"]) for item in route_feedback_capsules),
            missing_signal_ids=missing_feedback_signal_ids,
            unknown_signal_ids=unknown_feedback_signal_ids,
            error=route_feedback_error,
        )
    )

    visual_rules: list[dict[str, Any]] = []
    try:
        raw_rules = raw.get("visual_rules")
        if not isinstance(raw_rules, list) or not 1 <= len(raw_rules) <= 12:
            raise DesignEvidenceBriefError("visual_rules must contain 1 to 12 entries.")
        seen_rule_ids: set[str] = set()
        for raw_rule in raw_rules:
            item = _mapping(raw_rule, label="visual rule")
            _exact_fields(item, _VISUAL_RULE_FIELDS, label="visual rule")
            identifier = item.get("id")
            if not isinstance(identifier, str) or not _SOURCE_ID.fullmatch(identifier):
                raise DesignEvidenceBriefError("Visual rule id must be a stable lowercase identifier.")
            if identifier in seen_rule_ids:
                raise DesignEvidenceBriefError("Visual rule ids must be unique.")
            seen_rule_ids.add(identifier)
            raw_paths = item.get("affects_paths")
            if not isinstance(raw_paths, list) or not raw_paths:
                raise DesignEvidenceBriefError("Visual rule affects_paths must be a non-empty list.")
            affects_paths = [
                _website_path(root, path, label="visual rule affects path") for path in raw_paths
            ]
            if len(set(affects_paths)) != len(affects_paths) or not set(affects_paths).issubset(
                all_allowed_paths
            ):
                raise DesignEvidenceBriefError(
                    "Visual rule may affect only exact paths declared by the route plan."
                )
            if item.get("reduced_motion_required") is not True:
                raise DesignEvidenceBriefError("Visual rule must require a reduced-motion equivalent.")
            visual_rules.append(
                {
                    "id": identifier,
                    "purpose": _text(item.get("purpose"), label="visual rule purpose", minimum=12),
                    "static_equivalent": _text(
                        item.get("static_equivalent"),
                        label="visual rule static_equivalent",
                        minimum=12,
                    ),
                    "reduced_motion_required": True,
                    "affects_paths": affects_paths,
                }
            )
        visual_ok = True
        visual_error = ""
    except DesignEvidenceBriefError as exc:
        visual_ok = False
        visual_error = str(exc)
    checks.append(
        _check(
            "visual-rules",
            visual_ok,
            "Visual direction must name a purpose, a static equivalent, reduced-motion parity and exact affected files.",
            rule_count=len(visual_rules),
            error=visual_error,
        )
    )

    uncovered_route_ids: list[str] = []
    if visual_ok and routes_ok:
        covered_paths = {path for rule in visual_rules for path in rule.get("affects_paths", [])}
        uncovered_route_ids = [
            route["id"] for route in route_plan if route["local_path"] not in covered_paths
        ]
        visual_coverage_ok = not uncovered_route_ids
        visual_coverage_error = (
            ""
            if visual_coverage_ok
            else "One or more planned routes lack a visual-rule coverage declaration."
        )
    else:
        visual_coverage_ok = False
        visual_coverage_error = "Visual-route coverage requires valid route and visual-rule declarations."
    checks.append(
        _check(
            "visual-route-coverage",
            visual_coverage_ok,
            "Every planned route must be covered by at least one source-bound visual rule.",
            uncovered_route_ids=uncovered_route_ids,
            error=visual_coverage_error,
        )
    )

    try:
        prohibited = _text_list(
            raw.get("prohibited_public_inferences"),
            label="prohibited_public_inferences",
            minimum=4,
            maximum=20,
        )
        acceptance = _text_list(
            raw.get("acceptance_criteria"),
            label="acceptance_criteria",
            minimum=5,
            maximum=20,
        )
        boundaries_ok = True
        boundaries_error = ""
    except DesignEvidenceBriefError as exc:
        prohibited = []
        acceptance = []
        boundaries_ok = False
        boundaries_error = str(exc)
    checks.append(
        _check(
            "boundaries-and-acceptance",
            boundaries_ok,
            "Brief must retain explicit prohibited inferences and objective candidate acceptance criteria.",
            prohibited_count=len(prohibited),
            acceptance_count=len(acceptance),
            error=boundaries_error,
        )
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema": AUDIT_SCHEMA,
        "audited_at": _iso(current),
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "brief": {
            "brief_id": brief_id,
            "path": canonical_brief_relative,
            "sha256": brief_file_sha256,
            "objective": objective,
            "issued_at": _iso(issued_at),
            "refresh_by": _iso(refresh_by),
            "source_document": {"path": document_relative, "sha256": source_document.get("sha256", "")},
        },
        "research_refresh": research_refresh,
        "stakeholder_feedback": stakeholder_feedback,
        "claim_control": {
            "register_path": register_relative,
            "register_sha256": claim_control.get("register_sha256", ""),
            "claim_ids": selected_claim_ids,
            "claim_audit_state": claim_audit.get("state", ""),
            "claim_audit_warning_count": int(
                _mapping(claim_audit.get("summary"), label="claim audit summary").get("warning_count", 0)
            )
            if isinstance(claim_audit.get("summary"), Mapping)
            else 0,
        },
        "source_inputs": source_inputs,
        "route_plan": route_plan,
        "route_claim_capsules": route_claim_capsules,
        "route_claim_capsules_sha256": _json_sha256(route_claim_capsules),
        "route_feedback_capsules": route_feedback_capsules,
        "route_feedback_capsules_sha256": _json_sha256(route_feedback_capsules),
        "visual_rules": visual_rules,
        "summary": {
            "check_count": len(checks),
            "passed_check_count": sum(1 for check in checks if check["passed"]),
            "source_input_count": len(source_inputs),
            "route_count": len(route_plan),
            "claim_capsule_count": sum(len(item["claims"]) for item in route_claim_capsules),
            "feedback_signal_count": sum(len(item["signals"]) for item in route_feedback_capsules),
            "visual_rule_count": len(visual_rules),
        },
        "checks": checks,
    }


def audit_design_evidence_brief_file(
    brief_path: Path | None = None,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Load and audit the canonical local design-evidence brief."""

    root = _find_repo_root(repo_root)
    path, _ = _resolve_brief_path(root, brief_path)
    brief = _read_json(path, label="Design-evidence brief")
    return audit_design_evidence_brief(brief, brief_path=path, repo_root=root, as_of=as_of)


def write_design_evidence_brief_audit(
    receipt: Mapping[str, Any], output_path: Path, *, repo_root: Path | None = None
) -> Path:
    """Write one local audit receipt under docs/audits without release authority."""

    root = _find_repo_root(repo_root)
    path = output_path if output_path.is_absolute() else root / output_path
    path = path.resolve()
    audit_root = (root / AUDIT_OUTPUT_ROOT).resolve()
    try:
        path.relative_to(audit_root)
    except ValueError as exc:
        raise DesignEvidenceBriefError(
            f"Design-evidence brief audits must remain below {AUDIT_OUTPUT_ROOT.as_posix()}/."
        ) from exc
    if path.suffix.lower() != ".json":
        raise DesignEvidenceBriefError("Design-evidence brief audit output must use a .json filename.")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(dict(receipt), indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as stream:
        stream.write(serialised)
        temporary = Path(stream.name)
    temporary.replace(path)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-design-evidence-brief",
        description="Audit the source-bound Aureon investor/design brief for local staged-candidate work.",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument(
        "--brief", type=Path, help="Canonical design brief; defaults to data/website_operator."
    )
    parser.add_argument("--as-of", help="ISO timestamp for deterministic brief freshness checks.")
    parser.add_argument("--output", type=Path, help="Optional audit receipt below docs/audits/.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        as_of = _parse_datetime(args.as_of, label="--as-of") if args.as_of else None
        root = _find_repo_root(args.repo_root)
        receipt = audit_design_evidence_brief_file(args.brief, repo_root=root, as_of=as_of)
        if args.output is not None:
            output = write_design_evidence_brief_audit(receipt, args.output, repo_root=root)
            receipt["output"] = _relative_to_repo(root, output)
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0 if receipt["passed"] else 2
    except (DesignEvidenceBriefError, PublicClaimEvidenceError, OSError) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
