"""Source-bound, non-authoritative controls for public website claims.

The public site is an investor-facing company record.  This module inventories
the small set of material positioning claims the site currently makes and
checks that each one still has a local source, an explicit evidence state, a
boundary, approved wording and a review expiry.  It deliberately has no
release, package, credential, hosting or deployment authority.

A passing result means only that the internal claim register is internally
complete and still bound to the website sources it names.  It cannot turn a
company-authored statement, public record, research proposition or attention
signal into independent validation, customer adoption or a deployment decision.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

CLAIM_REGISTER_SCHEMA = "aureon.public-claim-evidence-register.v1"
CLAIM_AUDIT_SCHEMA = "aureon.public-claim-evidence-audit.v1"
DEFAULT_REGISTER_RELATIVE_PATH = Path("data/website_operator/public_claim_evidence_register.v1.json")
AUDIT_OUTPUT_DIRECTORY = Path("docs/audits")
EXPIRY_WARNING_DAYS = 30
REGISTER_SCOPE = "material public website positioning claims"

ALLOWED_STATES = frozenset(
    {
        "attention-signal",
        "company-authored",
        "external-recognition",
        "prospective-application",
        "public-research-record",
        "public-source-available",
        "research-proposition",
    }
)

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "read-only public-claim evidence control",
    "release_eligible": False,
    "deployment_authority": "none",
    "package_authority": "none",
    "human_review": "required for material public wording changes",
}

UNSAFE_WORDING_PATTERNS = (
    re.compile(r"\bguarantee(?:d|s)?\b", re.IGNORECASE),
    re.compile(r"\bproven\b", re.IGNORECASE),
    re.compile(r"\bmarket[- ]leading\b", re.IGNORECASE),
    re.compile(r"\bworld[- ]class\b", re.IGNORECASE),
    re.compile(r"\bfirst[- ]of[- ]its[- ]kind\b", re.IGNORECASE),
    re.compile(r"\bfully autonomous\b", re.IGNORECASE),
    re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE),
    re.compile(r"\bcustomer(?:s| adoption| use)?\b", re.IGNORECASE),
    re.compile(r"\brevenue\b", re.IGNORECASE),
    re.compile(r"\bfunding secured\b", re.IGNORECASE),
    re.compile(r"\bawarded?\b", re.IGNORECASE),
    re.compile(r"\bpartnership\b", re.IGNORECASE),
    re.compile(r"\bendorsement\b", re.IGNORECASE),
    re.compile(r"\bindependently validated\b", re.IGNORECASE),
    re.compile(r"\bpeer[- ]reviewed\b", re.IGNORECASE),
)


class PublicClaimEvidenceError(ValueError):
    """A local public-claim evidence input is malformed or unsafe."""


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().upper()


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise PublicClaimEvidenceError("Could not locate an Aureon repository with pyproject.toml and aureon/.")


def _safe_website_source_path(
    repo_root: Path,
    value: object,
    *,
    website_root: Path | None = None,
) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PublicClaimEvidenceError("A public-claim source path must be a non-empty relative path.")
    normalised = value.replace("\\", "/")
    relative = Path(normalised)
    if (
        relative.is_absolute()
        or not relative.parts
        or relative.parts[0] != "website"
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise PublicClaimEvidenceError(f"Public-claim source must stay under website/: {value}")
    active_website_root = (website_root or (repo_root / "website")).resolve()
    candidate = (active_website_root / Path(*relative.parts[1:])).resolve()
    try:
        candidate.relative_to(active_website_root)
    except ValueError as exc:
        raise PublicClaimEvidenceError(f"Public-claim source path escapes website/: {value}") from exc
    return candidate


def _safe_audit_output_path(repo_root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else repo_root / value
    candidate = candidate.resolve()
    output_root = (repo_root / AUDIT_OUTPUT_DIRECTORY).resolve()
    try:
        candidate.relative_to(output_root)
    except ValueError as exc:
        raise PublicClaimEvidenceError(
            f"Claim-evidence audit output must stay under {AUDIT_OUTPUT_DIRECTORY.as_posix()}/."
        ) from exc
    if candidate.suffix.lower() != ".json":
        raise PublicClaimEvidenceError("Claim-evidence audit output must use a .json filename.")
    return candidate


def _finding(
    code: str,
    severity: str,
    message: str,
    *,
    claim_id: str = "",
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if claim_id:
        result["claim_id"] = claim_id
    if evidence:
        result["evidence"] = dict(evidence)
    return result


def _nonempty_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    return candidate or None


def _string_list(value: object) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    values: list[str] = []
    for item in value:
        text = _nonempty_text(item)
        if text is None:
            return None
        values.append(text)
    return values


def _parse_iso_date(value: object) -> date | None:
    text = _nonempty_text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_iso_datetime(value: object) -> datetime | None:
    text = _nonempty_text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _unsafe_matches(text: str) -> list[str]:
    return sorted({match.group(0) for pattern in UNSAFE_WORDING_PATTERNS if (match := pattern.search(text))})


def _read_register(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PublicClaimEvidenceError(f"Claim-evidence register does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PublicClaimEvidenceError(f"Claim-evidence register is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise PublicClaimEvidenceError("Claim-evidence register must contain one JSON object.")
    return value


def _relative_to_repo(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def audit_public_claim_evidence(
    register: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    website_root: Path | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Inspect one claim register without granting release or deployment authority.

    The function is intentionally read-only.  It does not decide whether a
    website release can be built or published; callers must use the separate
    WebsiteOperator owner-gated lifecycle for that purpose.
    """

    root = _find_repo_root(repo_root)
    raw_website_root = website_root or (root / "website")
    active_website_root = (
        raw_website_root if raw_website_root.is_absolute() else root / raw_website_root
    ).resolve()
    try:
        active_website_root.relative_to(root)
    except ValueError as exc:
        raise PublicClaimEvidenceError("Claim-evidence website root must stay inside the repository.") from exc
    if not active_website_root.is_dir():
        raise PublicClaimEvidenceError(
            f"Claim-evidence website root does not exist: {active_website_root}"
        )
    today = as_of or datetime.now(UTC).date()
    findings: list[dict[str, Any]] = []
    claim_results: list[dict[str, Any]] = []

    if register.get("schema") != CLAIM_REGISTER_SCHEMA:
        findings.append(
            _finding(
                "register-schema",
                "error",
                f"Register schema must be {CLAIM_REGISTER_SCHEMA}.",
            )
        )
    if _parse_iso_datetime(register.get("generated_at")) is None:
        findings.append(
            _finding(
                "register-generated-at",
                "error",
                "Register must declare a timezone-aware ISO-8601 generated_at timestamp.",
            )
        )
    if register.get("scope") != REGISTER_SCOPE:
        findings.append(
            _finding(
                "register-scope",
                "error",
                f"Register scope must be {REGISTER_SCOPE!r}.",
            )
        )
    if register.get("authority") != NON_AUTHORITATIVE_AUTHORITY:
        findings.append(
            _finding(
                "non-authoritative-boundary",
                "error",
                "The register must retain no package, release or deployment authority.",
            )
        )

    claims = register.get("claims")
    if not isinstance(claims, list) or not claims:
        findings.append(
            _finding("claims-missing", "error", "Register must contain a non-empty claims list."))
        claims = []

    seen_claim_ids: set[str] = set()
    for index, candidate in enumerate(claims):
        claim_findings: list[dict[str, Any]] = []
        claim_id = ""
        if not isinstance(candidate, Mapping):
            finding = _finding(
                "claim-shape",
                "error",
                "Every claim must be a JSON object.",
                evidence={"index": index},
            )
            findings.append(finding)
            claim_results.append({"id": f"index-{index}", "passed": False, "findings": [finding]})
            continue

        raw_id = _nonempty_text(candidate.get("id"))
        claim_id = raw_id or f"index-{index}"
        if raw_id is None or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,80}", raw_id):
            claim_findings.append(
                _finding("claim-id", "error", "Claim id must be a lowercase stable slug.", claim_id=claim_id)
            )
        elif raw_id in seen_claim_ids:
            claim_findings.append(
                _finding("claim-id-duplicate", "error", "Claim ids must be unique.", claim_id=claim_id)
            )
        else:
            seen_claim_ids.add(raw_id)

        claim_text = _nonempty_text(candidate.get("claim"))
        if claim_text is None:
            claim_findings.append(
                _finding("claim-missing", "error", "Every claim needs canonical public wording.", claim_id=claim_id)
            )
        else:
            unsafe = _unsafe_matches(claim_text)
            if unsafe:
                claim_findings.append(
                    _finding(
                        "claim-unsafe-wording",
                        "error",
                        "Canonical claim wording contains a prohibited inference term.",
                        claim_id=claim_id,
                        evidence={"matches": unsafe},
                    )
                )

        if _nonempty_text(candidate.get("title")) is None:
            claim_findings.append(
                _finding("claim-title", "error", "Every claim needs a short inventory title.", claim_id=claim_id)
            )

        state = _nonempty_text(candidate.get("state"))
        if state not in ALLOWED_STATES:
            claim_findings.append(
                _finding(
                    "claim-state",
                    "error",
                    "Claim state must use the bounded public-evidence state vocabulary.",
                    claim_id=claim_id,
                    evidence={"state": state or ""},
                )
            )

        boundary = _nonempty_text(candidate.get("boundary"))
        if boundary is None:
            claim_findings.append(
                _finding("claim-boundary", "error", "Every claim needs an explicit public boundary.", claim_id=claim_id)
            )
        elif not re.search(r"\b(?:not|does not|do not|without|must|requires?|subject to|gates?)\b", boundary, re.IGNORECASE):
            claim_findings.append(
                _finding(
                    "claim-boundary-weak",
                    "error",
                    "A public boundary must explicitly limit the claim or name its required proof gates.",
                    claim_id=claim_id,
                )
            )

        permitted_wording = _string_list(candidate.get("permitted_wording"))
        if permitted_wording is None:
            claim_findings.append(
                _finding(
                    "claim-permitted-wording",
                    "error",
                    "Every claim needs one or more approved public wording variants.",
                    claim_id=claim_id,
                )
            )
        else:
            for wording in permitted_wording:
                unsafe = _unsafe_matches(wording)
                if unsafe:
                    claim_findings.append(
                        _finding(
                            "claim-permitted-wording-unsafe",
                            "error",
                            "Approved wording contains a prohibited inference term.",
                            claim_id=claim_id,
                            evidence={"matches": unsafe, "wording": wording},
                        )
                    )

        prohibited_inferences = _string_list(candidate.get("prohibited_inferences"))
        if prohibited_inferences is None:
            claim_findings.append(
                _finding(
                    "claim-prohibited-inferences",
                    "error",
                    "Every claim must name the inferences it does not permit.",
                    claim_id=claim_id,
                )
            )

        expires_on = _parse_iso_date(candidate.get("expires_on"))
        if expires_on is None:
            claim_findings.append(
                _finding(
                    "claim-expiry",
                    "error",
                    "Every claim needs an ISO-8601 expiry date.",
                    claim_id=claim_id,
                )
            )
        elif expires_on < today:
            claim_findings.append(
                _finding(
                    "claim-expired",
                    "error",
                    "Claim evidence is stale and needs a fresh source review before public reuse.",
                    claim_id=claim_id,
                    evidence={"expires_on": expires_on.isoformat(), "as_of": today.isoformat()},
                )
            )
        elif (expires_on - today).days <= EXPIRY_WARNING_DAYS:
            claim_findings.append(
                _finding(
                    "claim-expiry-near",
                    "warning",
                    "Claim evidence is near expiry; refresh its source before the next public-content cycle.",
                    claim_id=claim_id,
                    evidence={"expires_on": expires_on.isoformat(), "as_of": today.isoformat()},
                )
            )

        source = candidate.get("source")
        if not isinstance(source, Mapping):
            claim_findings.append(
                _finding("claim-source", "error", "Every claim needs one source binding object.", claim_id=claim_id)
            )
        else:
            source_path_value = source.get("path")
            source_path: Path | None = None
            try:
                source_path = _safe_website_source_path(
                    root,
                    source_path_value,
                    website_root=active_website_root,
                )
            except PublicClaimEvidenceError as exc:
                claim_findings.append(_finding("claim-source-path", "error", str(exc), claim_id=claim_id))

            source_hash = _nonempty_text(source.get("sha256"))
            if source_hash is None or not re.fullmatch(r"[A-Fa-f0-9]{64}", source_hash):
                claim_findings.append(
                    _finding(
                        "claim-source-hash",
                        "error",
                        "Every source needs an exact SHA-256 binding.",
                        claim_id=claim_id,
                    )
                )

            evidence_texts = _string_list(source.get("evidence_texts"))
            if evidence_texts is None:
                claim_findings.append(
                    _finding(
                        "claim-source-evidence",
                        "error",
                        "Every source needs one or more exact evidence text anchors.",
                        claim_id=claim_id,
                    )
                )

            source_boundary = _nonempty_text(source.get("boundary_text"))
            if source_boundary is None:
                claim_findings.append(
                    _finding(
                        "claim-source-boundary",
                        "error",
                        "Every source needs an exact boundary text anchor.",
                        claim_id=claim_id,
                    )
                )

            if _nonempty_text(source.get("locator")) is None:
                claim_findings.append(
                    _finding(
                        "claim-source-locator",
                        "error",
                        "Every source needs a stable local locator for human review.",
                        claim_id=claim_id,
                    )
                )
            elif boundary is not None and source_boundary != boundary:
                claim_findings.append(
                    _finding(
                        "claim-boundary-source-mismatch",
                        "error",
                        "Claim boundary must exactly match its source-bound boundary anchor.",
                        claim_id=claim_id,
                    )
                )

            if source_path is not None:
                if not source_path.is_file():
                    claim_findings.append(
                        _finding(
                            "claim-source-missing",
                            "error",
                            "Claim source file is missing.",
                            claim_id=claim_id,
                            evidence={"path": str(source_path_value or "")},
                        )
                    )
                else:
                    current_hash = _sha256(source_path)
                    if source_hash is not None and current_hash != source_hash.upper():
                        claim_findings.append(
                            _finding(
                                "claim-source-drift",
                                "error",
                                "Claim source changed after the register was bound; refresh the claim deliberately.",
                                claim_id=claim_id,
                                evidence={
                                    "path": _relative_to_repo(root, source_path),
                                    "expected_sha256": source_hash.upper(),
                                    "actual_sha256": current_hash,
                                },
                            )
                        )
                    source_text = source_path.read_text(encoding="utf-8", errors="replace")
                    source_text_unescaped = html.unescape(source_text)
                    for evidence_text in evidence_texts or []:
                        if evidence_text not in source_text and evidence_text not in source_text_unescaped:
                            claim_findings.append(
                                _finding(
                                    "claim-source-anchor-missing",
                                    "error",
                                    "An exact evidence text anchor is absent from the bound source.",
                                    claim_id=claim_id,
                                    evidence={"path": _relative_to_repo(root, source_path), "anchor": evidence_text},
                                )
                            )
                    if (
                        source_boundary is not None
                        and source_boundary not in source_text
                        and source_boundary not in source_text_unescaped
                    ):
                        claim_findings.append(
                            _finding(
                                "claim-source-boundary-missing",
                                "error",
                                "The exact boundary anchor is absent from the bound source.",
                                claim_id=claim_id,
                                evidence={"path": _relative_to_repo(root, source_path)},
                            )
                        )

        public_routes = _string_list(candidate.get("public_routes"))
        if public_routes is None or any(not route.startswith("/") for route in public_routes or []):
            claim_findings.append(
                _finding(
                    "claim-public-routes",
                    "error",
                    "Every claim needs one or more site-rooted public route references.",
                    claim_id=claim_id,
                )
            )

        claim_errors = [item for item in claim_findings if item["severity"] == "error"]
        findings.extend(claim_findings)
        claim_results.append(
            {
                "id": claim_id,
                "state": state or "",
                "passed": not claim_errors,
                "expires_on": expires_on.isoformat() if expires_on is not None else "",
                "findings": claim_findings,
            }
        )

    error_count = sum(1 for item in findings if item["severity"] == "error")
    warning_count = sum(1 for item in findings if item["severity"] == "warning")
    passed = error_count == 0
    return {
        "schema": CLAIM_AUDIT_SCHEMA,
        "audited_at": _utc_iso(),
        "as_of": today.isoformat(),
        "authority": dict(NON_AUTHORITATIVE_AUTHORITY),
        "state": "pass" if passed else "fail",
        "passed": passed,
        "release_eligible": False,
        "deployment_authority": "none",
        "summary": {
            "claim_count": len(claim_results),
            "passed_claim_count": sum(1 for item in claim_results if item["passed"]),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "findings": findings,
        "claims": claim_results,
    }


def audit_public_claim_evidence_file(
    register_path: Path | None = None,
    *,
    repo_root: Path | None = None,
    website_root: Path | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Load and audit a claim register, retaining the register's own hash in the receipt."""

    root = _find_repo_root(repo_root)
    candidate = register_path or root / DEFAULT_REGISTER_RELATIVE_PATH
    path = candidate if candidate.is_absolute() else root / candidate
    path = path.resolve()
    register = _read_register(path)
    receipt = audit_public_claim_evidence(
        register,
        repo_root=root,
        website_root=website_root,
        as_of=as_of,
    )
    receipt["register"] = {
        "path": _relative_to_repo(root, path),
        "sha256": _sha256(path),
    }
    return receipt


def write_public_claim_evidence_audit(receipt: Mapping[str, Any], output_path: Path, *, repo_root: Path | None = None) -> Path:
    """Write one local audit receipt under docs/audits without affecting a website release."""

    root = _find_repo_root(repo_root)
    path = _safe_audit_output_path(root, output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialised = json.dumps(dict(receipt), indent=2, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as stream:
        stream.write(serialised)
        temporary_path = Path(stream.name)
    temporary_path.replace(path)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-public-claim-evidence",
        description="Read-only source-bound audit for public Aureon website positioning claims.",
    )
    parser.add_argument("--repo-root", type=Path, help="Aureon repository root.")
    parser.add_argument("--register", type=Path, help="Claim register path; defaults to data/website_operator.")
    parser.add_argument("--as-of", help="ISO date for deterministic expiry checks (YYYY-MM-DD).")
    parser.add_argument("--output", type=Path, help="Optional JSON receipt path beneath docs/audits/.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
    except ValueError:
        print(json.dumps({"state": "blocked", "error": "--as-of must use YYYY-MM-DD."}), flush=True)
        return 2
    try:
        root = _find_repo_root(args.repo_root)
        receipt = audit_public_claim_evidence_file(args.register, repo_root=root, as_of=as_of)
        if args.output is not None:
            output_path = write_public_claim_evidence_audit(receipt, args.output, repo_root=root)
            receipt["output"] = _relative_to_repo(root, output_path)
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0 if receipt["passed"] else 2
    except PublicClaimEvidenceError as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
