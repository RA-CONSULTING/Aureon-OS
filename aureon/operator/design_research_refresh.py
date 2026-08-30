"""Local source-control checks for Aureon's research-led website design.

The validator is deliberately local and read-only with respect to every
canonical input.  It validates a redacted declaration that points only to
existing public/research snapshots in this repository.  It does not fetch a
URL, use a browser or connector, read credentials, alter a website, amend the
claim register, construct a package, or deploy anything.

At most, a caller may write a new immutable review receipt beneath the narrow
``artifacts/website-operator/design-research-refreshes/`` evidence area.  A
passing receipt remains a research-refresh signal only; it is never a release
or artwork-use permission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

SOURCE_DECLARATION_SCHEMA = "aureon.design-research-sources.v1"
REFRESH_RECEIPT_SCHEMA = "aureon.design-research-refresh.v1"
DEFAULT_SOURCE_DECLARATION_PATH = Path("data/website_operator/design_research_sources.v1.json")
DEFAULT_CLAIM_REGISTER_PATH = Path("data/website_operator/public_claim_evidence_register.v1.json")
REFRESH_OUTPUT_ROOT = Path("artifacts/website-operator/design-research-refreshes")

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local redacted research and design source freshness review only",
    "declaration_mutation": "never by this validator",
    "canonical_website_mutation": "never",
    "claim_register_mutation": "never",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "connector_access": "none",
    "research_refresh_authority": "human review of local public-source evidence only",
}

_DECLARATION_FIELDS = frozenset(
    {
        "schema",
        "declaration_id",
        "issued_at",
        "refresh_due_within_days",
        "authority",
        "sources",
        "artwork_policy",
    }
)
_SOURCE_FIELDS = frozenset(
    {
        "id",
        "kind",
        "public_reference",
        "observed_at",
        "expires_at",
        "snapshot",
        "claim_ids",
        "purpose",
        "boundary",
    }
)
_REFERENCE_FIELDS = frozenset({"kind", "value"})
_SNAPSHOT_FIELDS = frozenset({"path", "sha256"})
_ARTWORK_POLICY_FIELDS = frozenset(
    {
        "state",
        "confirmed_local_provenance",
        "source_artwork_included",
        "boundary",
        "evidence_snapshot",
    }
)
_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "reviewed_at",
        "state",
        "passed",
        "release_eligible",
        "package_authority",
        "deployment_authority",
        "authority",
        "declaration",
        "claim_register",
        "sources",
        "artwork",
        "summary",
        "checks",
        "next_gate",
    }
)
_ALLOWED_SNAPSHOT_PREFIXES = ("docs/research/", "website/data/")
_SOURCE_KINDS = frozenset({"public-research-record", "public-website-data", "public-design-pattern"})
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
_CLAIM_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_RECORD_ID = re.compile(r"^[a-z][a-z0-9-]{1,31}:[A-Za-z0-9][A-Za-z0-9._:/-]{1,159}$")
_FORBIDDEN_PUBLIC_TEXT = (
    "<script",
    "javascript:",
    "data:",
    "gmail",
    "google drive",
    "drive.google",
    "mail.google",
    "api_key",
    "access_token",
    "authorization:",
)


class DesignResearchRefreshError(ValueError):
    """A source declaration or a requested review receipt is unsafe."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DesignResearchRefreshError(f"{label} must be a non-empty ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DesignResearchRefreshError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise DesignResearchRefreshError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignResearchRefreshError("Could not locate an Aureon repository with pyproject.toml and aureon/.")


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
        raise DesignResearchRefreshError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(parsed, Mapping):
        raise DesignResearchRefreshError(f"{label} must be a JSON object: {path}")
    return dict(parsed)


def _safe_relative(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignResearchRefreshError(f"{label} must be a non-empty repository-relative path.")
    normalised = value.replace("\\", "/")
    path = Path(normalised)
    if (
        path.is_absolute()
        or path.drive
        or path.root
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise DesignResearchRefreshError(f"{label} is unsafe.")
    return path.as_posix()


def _relative_inside(root: Path, candidate: Path, *, label: str) -> str:
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignResearchRefreshError(f"{label} must remain inside the repository.") from exc


def _resolve_canonical_declaration(root: Path, value: Path | None) -> tuple[Path, str]:
    raw = value or DEFAULT_SOURCE_DECLARATION_PATH
    candidate = raw if raw.is_absolute() else root / raw
    relative = _relative_inside(root, candidate, label="Source declaration")
    if relative != DEFAULT_SOURCE_DECLARATION_PATH.as_posix():
        raise DesignResearchRefreshError(
            "Source declaration must use the canonical "
            "data/website_operator/design_research_sources.v1.json location."
        )
    unresolved = root / relative
    if not unresolved.is_file() or unresolved.is_symlink():
        raise DesignResearchRefreshError("Source declaration must be a regular canonical JSON file.")
    return unresolved.resolve(), relative


def _safe_text(value: object, *, label: str, minimum: int, maximum: int) -> str:
    if not isinstance(value, str):
        raise DesignResearchRefreshError(f"{label} must be text.")
    result = " ".join(value.split())
    if not minimum <= len(result) <= maximum:
        raise DesignResearchRefreshError(f"{label} must be between {minimum} and {maximum} characters.")
    lowered = result.casefold()
    if any(token in lowered for token in _FORBIDDEN_PUBLIC_TEXT):
        raise DesignResearchRefreshError(f"{label} contains unsupported private or executable material.")
    return result


def _exact_fields(value: object, fields: frozenset[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DesignResearchRefreshError(f"{label} must be an object.")
    copied = dict(value)
    if set(copied) != fields:
        missing = sorted(fields - set(copied))
        extra = sorted(set(copied) - fields)
        raise DesignResearchRefreshError(
            f"{label} fields do not match the contract (missing={missing}, extra={extra})."
        )
    return copied


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "passed": bool(passed),
        "message": message,
        "evidence": evidence,
    }


def _claim_index(root: Path) -> tuple[set[str], dict[str, Any], str]:
    path = (root / DEFAULT_CLAIM_REGISTER_PATH).resolve()
    relative = DEFAULT_CLAIM_REGISTER_PATH.as_posix()
    result = {"path": relative, "sha256": "", "available": False}
    original = root / DEFAULT_CLAIM_REGISTER_PATH
    if not original.is_file() or original.is_symlink():
        return set(), result, "Canonical public-claim register is unavailable."
    try:
        content = _read_json(original, label="Canonical public-claim register")
    except DesignResearchRefreshError as exc:
        return set(), result, str(exc)
    claims = content.get("claims")
    if not isinstance(claims, list) or not all(isinstance(item, Mapping) for item in claims):
        return set(), result, "Canonical public-claim register has no valid claims array."
    identifiers = {
        item.get("id")
        for item in claims
        if isinstance(item.get("id"), str) and _CLAIM_ID.fullmatch(item.get("id", ""))
    }
    if not identifiers:
        return set(), result, "Canonical public-claim register has no usable claim identifiers."
    result.update({"sha256": _sha256_file(path), "available": True})
    return identifiers, result, ""


def _snapshot_result(root: Path, value: object, *, label: str) -> tuple[dict[str, str], list[str]]:
    output = {"path": "", "declared_sha256": "", "observed_sha256": "", "state": "invalid"}
    errors: list[str] = []
    try:
        snapshot = _exact_fields(value, _SNAPSHOT_FIELDS, label=label)
        relative = _safe_relative(snapshot.get("path"), label=f"{label} path")
        if not relative.startswith(_ALLOWED_SNAPSHOT_PREFIXES):
            raise DesignResearchRefreshError(f"{label} path must be a redacted public/research snapshot.")
        output["path"] = relative
        declared = snapshot.get("sha256")
        if not isinstance(declared, str) or not _SHA256.fullmatch(declared):
            raise DesignResearchRefreshError(f"{label} SHA-256 must be uppercase hexadecimal.")
        output["declared_sha256"] = declared
        original = root / relative
        resolved = original.resolve()
        _relative_inside(root, resolved, label=label)
        if not original.exists():
            output["state"] = "missing"
            errors.append(f"{label} snapshot is missing.")
            return output, errors
        if original.is_symlink() or not original.is_file():
            raise DesignResearchRefreshError(f"{label} snapshot must be a regular file.")
        observed = _sha256_file(resolved)
        output["observed_sha256"] = observed
        if observed != declared:
            output["state"] = "hash-mismatch"
            errors.append(f"{label} snapshot hash does not match its declaration.")
        else:
            output["state"] = "verified"
    except DesignResearchRefreshError as exc:
        errors.append(str(exc))
    return output, errors


def _public_reference(value: object) -> tuple[dict[str, str], list[str]]:
    output = {"kind": "", "value": ""}
    errors: list[str] = []
    try:
        reference = _exact_fields(value, _REFERENCE_FIELDS, label="Source public_reference")
        kind = reference.get("kind")
        raw_value = reference.get("value")
        if kind not in {"https-url", "record-id"}:
            raise DesignResearchRefreshError("Source public_reference kind must be https-url or record-id.")
        if not isinstance(raw_value, str) or not raw_value.strip():
            raise DesignResearchRefreshError("Source public_reference value must be non-empty text.")
        text = raw_value.strip()
        if any(token in text.casefold() for token in _FORBIDDEN_PUBLIC_TEXT):
            raise DesignResearchRefreshError(
                "Source public_reference contains unsupported private or executable material."
            )
        if kind == "https-url":
            parsed = urlsplit(text)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
            ):
                raise DesignResearchRefreshError(
                    "Source public_reference URL must be direct, credential-free HTTPS without query data."
                )
        elif not _RECORD_ID.fullmatch(text):
            raise DesignResearchRefreshError("Source public_reference record id has an unsafe form.")
        output = {"kind": str(kind), "value": text}
    except DesignResearchRefreshError as exc:
        errors.append(str(exc))
    return output, errors


def _claim_ids(value: object, known_ids: set[str]) -> tuple[list[str], list[str]]:
    if not isinstance(value, list) or len(value) > 32:
        return [], ["Source claim_ids must be a list with at most 32 items."]
    ids: list[str] = []
    errors: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _CLAIM_ID.fullmatch(item):
            errors.append("Source claim_ids contains an invalid identifier.")
            continue
        ids.append(item)
    if len(set(ids)) != len(ids):
        errors.append("Source claim_ids must not contain duplicates.")
    missing = sorted(set(ids) - known_ids)
    if missing:
        errors.append("Source claim_ids contains identifiers absent from the canonical register.")
    return ids, errors


def _audit_source(
    raw_source: object,
    *,
    root: Path,
    now: datetime,
    due_window: timedelta,
    known_claim_ids: set[str],
) -> dict[str, Any]:
    source = raw_source if isinstance(raw_source, Mapping) else {}
    errors: list[str] = []
    try:
        copied = _exact_fields(source, _SOURCE_FIELDS, label="Source")
    except DesignResearchRefreshError as exc:
        copied = dict(source)
        errors.append(str(exc))

    identifier = ""
    raw_identifier = copied.get("id")
    if isinstance(raw_identifier, str) and _IDENTIFIER.fullmatch(raw_identifier):
        identifier = raw_identifier
    else:
        errors.append("Source id must be a stable lowercase identifier.")

    kind = ""
    raw_kind = copied.get("kind")
    if raw_kind in _SOURCE_KINDS:
        kind = str(raw_kind)
    else:
        errors.append("Source kind is unsupported; artwork and private-source kinds are not accepted.")

    public_reference, reference_errors = _public_reference(copied.get("public_reference"))
    errors.extend(reference_errors)

    observed_at = ""
    expires_at = ""
    timing_valid = False
    try:
        observed = _parse_datetime(copied.get("observed_at"), label="Source observed_at")
        expires = _parse_datetime(copied.get("expires_at"), label="Source expires_at")
        if observed > now:
            raise DesignResearchRefreshError("Source observed_at cannot be in the future.")
        if expires <= observed:
            raise DesignResearchRefreshError("Source expires_at must follow observed_at.")
        if expires - observed > timedelta(days=366):
            raise DesignResearchRefreshError("Source validity window must not exceed 366 days.")
        observed_at = _iso(observed)
        expires_at = _iso(expires)
        timing_valid = True
    except DesignResearchRefreshError as exc:
        errors.append(str(exc))
        observed = now
        expires = now

    snapshot, snapshot_errors = _snapshot_result(root, copied.get("snapshot"), label="Source snapshot")
    errors.extend(snapshot_errors)

    claim_ids, claim_errors = _claim_ids(copied.get("claim_ids"), known_claim_ids)
    errors.extend(claim_errors)

    purpose = ""
    boundary = ""
    try:
        purpose = _safe_text(copied.get("purpose"), label="Source purpose", minimum=12, maximum=500)
    except DesignResearchRefreshError as exc:
        errors.append(str(exc))
    try:
        boundary = _safe_text(copied.get("boundary"), label="Source boundary", minimum=20, maximum=700)
    except DesignResearchRefreshError as exc:
        errors.append(str(exc))

    if snapshot["state"] == "missing":
        freshness = "missing"
    elif snapshot["state"] != "verified" or not timing_valid or errors:
        freshness = "invalid"
    elif expires <= now:
        freshness = "stale"
    elif expires <= now + due_window:
        freshness = "due"
    else:
        freshness = "fresh"
    integrity = "verified" if not errors and snapshot["state"] == "verified" else snapshot["state"]

    return {
        "id": identifier,
        "kind": kind,
        "public_reference": public_reference,
        "observed_at": observed_at,
        "expires_at": expires_at,
        "snapshot": snapshot,
        "claim_ids": claim_ids,
        "purpose": purpose,
        "boundary": boundary,
        "integrity": integrity,
        "freshness": freshness,
        "errors": errors,
    }


def _audit_artwork_policy(root: Path, raw_policy: object) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    policy: dict[str, Any]
    try:
        policy = _exact_fields(raw_policy, _ARTWORK_POLICY_FIELDS, label="artwork_policy")
    except DesignResearchRefreshError as exc:
        policy = dict(raw_policy) if isinstance(raw_policy, Mapping) else {}
        errors.append(str(exc))

    state = ""
    if policy.get("state") == "not-cleared":
        state = "not-cleared"
    else:
        errors.append("Artwork policy must remain not-cleared in this source-control contract.")
    if policy.get("confirmed_local_provenance") is not False:
        errors.append("Artwork policy cannot assert confirmed local provenance in this contract.")
    if policy.get("source_artwork_included") is not False:
        errors.append("Artwork policy must not include source artwork or artwork data.")
    boundary = ""
    try:
        boundary = _safe_text(
            policy.get("boundary"), label="Artwork policy boundary", minimum=20, maximum=700
        )
    except DesignResearchRefreshError as exc:
        errors.append(str(exc))
    snapshot, snapshot_errors = _snapshot_result(
        root, policy.get("evidence_snapshot"), label="Artwork policy evidence snapshot"
    )
    errors.extend(snapshot_errors)
    return (
        {
            "state": state,
            "confirmed_local_provenance": False,
            "source_artwork_included": False,
            "boundary": boundary,
            "evidence_snapshot": snapshot,
            "cleared_for_use": False,
            "errors": errors,
        },
        errors,
    )


def audit_design_research_sources(
    declaration: Mapping[str, Any],
    *,
    declaration_path: Path,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Audit one in-memory source declaration against its canonical local file.

    The in-memory mapping is required to match the canonical persisted
    declaration exactly.  This prevents an arbitrary temporary mapping from
    issuing a passing evidence receipt.  No input is modified.
    """

    root = _find_repo_root(repo_root)
    current = (as_of or _utc_now()).astimezone(UTC)
    raw = dict(declaration) if isinstance(declaration, Mapping) else {}
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "schema",
            raw.get("schema") == SOURCE_DECLARATION_SCHEMA,
            "Source declaration schema must match the local refresh contract.",
        )
    )
    checks.append(
        _check(
            "strict-declaration-shape",
            set(raw) == _DECLARATION_FIELDS,
            "Source declaration must retain exactly the redacted source-control fields.",
            missing=sorted(_DECLARATION_FIELDS - set(raw)),
            extra=sorted(set(raw) - _DECLARATION_FIELDS),
        )
    )

    declaration_relative = ""
    declaration_sha256 = ""
    declaration_binding_error = ""
    declaration_binding_ok = False
    try:
        canonical_path, declaration_relative = _resolve_canonical_declaration(root, declaration_path)
        persisted = _read_json(canonical_path, label="Canonical design research source declaration")
        declaration_sha256 = _sha256_file(canonical_path)
        declaration_binding_ok = persisted == raw
        if not declaration_binding_ok:
            declaration_binding_error = (
                "In-memory declaration content does not match the canonical persisted source declaration."
            )
    except DesignResearchRefreshError as exc:
        declaration_binding_error = str(exc)
    checks.append(
        _check(
            "declaration-file-binding",
            declaration_binding_ok,
            "The audited mapping must exactly match the canonical immutable local declaration.",
            path=declaration_relative,
            sha256=declaration_sha256,
            error=declaration_binding_error,
        )
    )

    authority_ok = raw.get("authority") == NON_AUTHORITATIVE_AUTHORITY
    checks.append(
        _check(
            "non-authoritative-boundary",
            authority_ok,
            "Refresh evidence grants no canonical mutation, claim-register mutation, release, package, deployment, credential, network or connector authority.",
        )
    )

    declaration_id = ""
    issued_at = ""
    due_days = 0
    declaration_timing_error = ""
    declaration_timing_ok = False
    try:
        candidate_id = raw.get("declaration_id")
        if not isinstance(candidate_id, str) or not _IDENTIFIER.fullmatch(candidate_id):
            raise DesignResearchRefreshError("declaration_id must be a stable lowercase identifier.")
        declaration_id = candidate_id
        issued = _parse_datetime(raw.get("issued_at"), label="issued_at")
        if issued > current:
            raise DesignResearchRefreshError("issued_at cannot be in the future.")
        due_value = raw.get("refresh_due_within_days")
        if not isinstance(due_value, int) or isinstance(due_value, bool) or not 1 <= due_value <= 90:
            raise DesignResearchRefreshError("refresh_due_within_days must be an integer from 1 to 90.")
        issued_at = _iso(issued)
        due_days = due_value
        declaration_timing_ok = True
    except DesignResearchRefreshError as exc:
        declaration_timing_error = str(exc)
    checks.append(
        _check(
            "declaration-timing",
            declaration_timing_ok,
            "Declaration id, issue timestamp and bounded due window must be current and explicit.",
            declaration_id=declaration_id,
            issued_at=issued_at,
            refresh_due_within_days=due_days,
            error=declaration_timing_error,
        )
    )

    known_claim_ids, claim_register, claim_register_error = _claim_index(root)
    checks.append(
        _check(
            "claim-register-read-only-binding",
            not claim_register_error,
            "Source claim ids may only be checked against the canonical local public-claim register; this validator never changes it.",
            **claim_register,
            error=claim_register_error,
        )
    )

    raw_sources = raw.get("sources")
    source_list = raw_sources if isinstance(raw_sources, list) else []
    source_list_ok = isinstance(raw_sources, list) and 1 <= len(source_list) <= 32
    checks.append(
        _check(
            "source-list",
            source_list_ok,
            "Declaration must include one to 32 redacted public/research source records.",
            source_count=len(source_list),
        )
    )
    due_window = timedelta(days=due_days) if due_days else timedelta(0)
    audited_sources = [
        _audit_source(
            item,
            root=root,
            now=current,
            due_window=due_window,
            known_claim_ids=known_claim_ids,
        )
        for item in source_list
    ]
    source_ids = [source["id"] for source in audited_sources]
    source_ids_ok = all(source_ids) and len(set(source_ids)) == len(source_ids)
    checks.append(
        _check(
            "source-identifiers",
            source_ids_ok,
            "Each source must retain one unique stable identifier.",
            source_ids=source_ids,
        )
    )
    source_integrity_ok = all(source["integrity"] == "verified" for source in audited_sources)
    checks.append(
        _check(
            "source-integrity",
            source_integrity_ok,
            "Each public/research snapshot must be a regular local file with an exact declared SHA-256.",
            invalid_source_ids=[
                source["id"] for source in audited_sources if source["integrity"] != "verified"
            ],
        )
    )
    source_claims_ok = all(
        not any("claim_ids" in error for error in source["errors"]) for source in audited_sources
    )
    checks.append(
        _check(
            "source-claim-ids",
            source_claims_ok,
            "Claim ids are optional per source but, when declared, must be unique current public-claim ids.",
            invalid_source_ids=[
                source["id"]
                for source in audited_sources
                if any("claim_ids" in error for error in source["errors"])
            ],
        )
    )
    stale_states = {"stale", "missing", "invalid"}
    source_freshness_ok = all(source["freshness"] not in stale_states for source in audited_sources)
    checks.append(
        _check(
            "source-freshness",
            source_freshness_ok,
            "Every source must be present, intact and unexpired; due sources remain valid but require a human refresh review.",
            due_source_ids=[source["id"] for source in audited_sources if source["freshness"] == "due"],
            stale_source_ids=[source["id"] for source in audited_sources if source["freshness"] == "stale"],
            missing_source_ids=[
                source["id"] for source in audited_sources if source["freshness"] == "missing"
            ],
            invalid_source_ids=[
                source["id"] for source in audited_sources if source["freshness"] == "invalid"
            ],
        )
    )

    artwork, artwork_errors = _audit_artwork_policy(root, raw.get("artwork_policy"))
    artwork_ok = not artwork_errors and artwork["state"] == "not-cleared"
    checks.append(
        _check(
            "artwork-not-cleared",
            artwork_ok,
            "No artwork is cleared by this source-control contract absent a separately governed local provenance process.",
            state=artwork["state"],
            cleared_for_use=False,
            errors=artwork_errors,
        )
    )

    summary = {
        "source_count": len(audited_sources),
        "fresh_count": sum(source["freshness"] == "fresh" for source in audited_sources),
        "due_count": sum(source["freshness"] == "due" for source in audited_sources),
        "stale_count": sum(source["freshness"] == "stale" for source in audited_sources),
        "missing_count": sum(source["freshness"] == "missing" for source in audited_sources),
        "invalid_count": sum(source["freshness"] == "invalid" for source in audited_sources),
    }
    passed = all(check["passed"] for check in checks)
    state = "blocked" if not passed else "refresh-due" if summary["due_count"] else "current"
    next_gate = (
        "A human may refresh due public-source observations using a separately controlled process; "
        "this receipt does not clear artwork or authorise a candidate, website change, package, release or deployment."
        if state == "refresh-due"
        else "Correct missing, stale or invalid local source evidence before any separate staged-candidate review; "
        "this receipt does not clear artwork or authorise a candidate, website change, package, release or deployment."
        if state == "blocked"
        else "Keep the declaration under periodic human review. Any website candidate remains subject to its own source, visual, owner and deployment gates."
    )
    return {
        "schema": REFRESH_RECEIPT_SCHEMA,
        "reviewed_at": _iso(current),
        "state": state,
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "declaration": {
            "id": declaration_id,
            "path": declaration_relative,
            "sha256": declaration_sha256,
            "issued_at": issued_at,
            "refresh_due_within_days": due_days,
        },
        "claim_register": claim_register,
        "sources": audited_sources,
        "artwork": artwork,
        "summary": summary,
        "checks": checks,
        "next_gate": next_gate,
    }


def audit_design_research_sources_file(
    declaration_path: Path | None = None,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Read and audit only the canonical persisted source declaration."""

    root = _find_repo_root(repo_root)
    path, _ = _resolve_canonical_declaration(root, declaration_path)
    declaration = _read_json(path, label="Canonical design research source declaration")
    return audit_design_research_sources(
        declaration,
        declaration_path=path,
        repo_root=root,
        as_of=as_of,
    )


def _safe_output_path(root: Path, value: Path) -> Path:
    if not isinstance(value, Path):
        raise DesignResearchRefreshError("Refresh receipt output must be a filesystem path.")
    if value.is_absolute():
        target = value.resolve()
    else:
        relative = _safe_relative(str(value), label="Refresh receipt output")
        target = (root / relative).resolve()
    output_root = (root / REFRESH_OUTPUT_ROOT).resolve()
    try:
        target.relative_to(output_root)
    except ValueError as exc:
        raise DesignResearchRefreshError(
            "Refresh receipt output must be inside artifacts/website-operator/design-research-refreshes/."
        ) from exc
    if target.suffix.lower() != ".json" or not target.name.startswith("design-research-refresh-"):
        raise DesignResearchRefreshError(
            "Refresh receipt output must be a new design-research-refresh-*.json file."
        )
    if target.exists() or target.is_symlink():
        raise DesignResearchRefreshError(f"Refusing to overwrite refresh evidence: {target}")
    return target


def _receipt_is_non_authoritative(receipt: Mapping[str, Any]) -> bool:
    return (
        set(receipt) == _RECEIPT_FIELDS
        and receipt.get("schema") == REFRESH_RECEIPT_SCHEMA
        and receipt.get("authority") == NON_AUTHORITATIVE_AUTHORITY
        and receipt.get("release_eligible") is False
        and receipt.get("package_authority") == "none"
        and receipt.get("deployment_authority") == "none"
        and isinstance(receipt.get("sources"), list)
        and isinstance(receipt.get("checks"), list)
        and isinstance(receipt.get("artwork"), Mapping)
        and receipt["artwork"].get("state") == "not-cleared"
        and receipt["artwork"].get("cleared_for_use") is False
    )


def write_design_research_refresh_receipt(
    receipt: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Append one immutable local refresh review receipt in its narrow evidence root."""

    root = _find_repo_root(repo_root)
    if not isinstance(receipt, Mapping) or not _receipt_is_non_authoritative(receipt):
        raise DesignResearchRefreshError(
            "Only a non-authoritative design research refresh receipt may be written."
        )
    target = _safe_output_path(root, output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    output_root = (root / REFRESH_OUTPUT_ROOT).resolve()
    try:
        target.parent.resolve().relative_to(output_root)
    except ValueError as exc:
        raise DesignResearchRefreshError("Refresh receipt output parent is unsafe.") from exc
    try:
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(dict(receipt), indent=2, ensure_ascii=False) + "\n")
    except FileExistsError as exc:
        raise DesignResearchRefreshError(f"Refusing to overwrite refresh evidence: {target}") from exc
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-design-research-refresh",
        description="Audit only local redacted research/design source freshness evidence.",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCE_DECLARATION_PATH)
    parser.add_argument("--as-of", help="Optional ISO-8601 UTC review timestamp.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional new immutable receipt below artifacts/website-operator/design-research-refreshes/.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        as_of = _parse_datetime(args.as_of, label="--as-of") if args.as_of else None
        receipt = audit_design_research_sources_file(
            args.sources,
            repo_root=args.repo_root,
            as_of=as_of,
        )
        output = None
        if args.output is not None:
            output = write_design_research_refresh_receipt(
                receipt,
                args.output,
                repo_root=args.repo_root,
            )
        summary = {
            "state": receipt["state"],
            "passed": receipt["passed"],
            "summary": receipt["summary"],
            "release_eligible": False,
            "deployment_authority": "none",
        }
        if output is not None:
            root = _find_repo_root(args.repo_root)
            summary["output"] = output.relative_to(root).as_posix()
        print(json.dumps(summary, indent=2))
        return 0 if receipt["passed"] else 2
    except DesignResearchRefreshError as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
