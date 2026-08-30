"""Deterministic investor-copy controls for staged Aureon website candidates.

The control is intentionally read-only.  It audits a bounded set of local HTML
routes against a small, controlled policy vocabulary and emits findings without
rewriting copy, staging a candidate, packaging a site, or granting release or
deployment authority.

The policy does not accept arbitrary regular expressions.  Every rule identifier
maps to code-reviewed logic in this module, so a worker cannot expand the scan,
hide a finding, or turn free-form policy text into executable behaviour.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping, Sequence

POLICY_SCHEMA = "aureon.investor-copy-quality-policy.v1"
AUDIT_SCHEMA = "aureon.investor-copy-quality-audit.v1"
DEFAULT_POLICY_PATH = Path("data/website_operator/investor_copy_quality_policy.v1.json")
DEFAULT_WEBSITE_ROOT = Path("website")
DEFAULT_AUDIT_ROOT = Path("docs/audits")

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "read-only local investor-copy quality audit",
    "canonical_website_mutation": "never",
    "candidate_staging": "never",
    "claim_register_mutation": "never",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "human_review": "required before public copy changes",
}

SEVERITIES = frozenset({"blocker", "warning"})
RULE_IDS = frozenset(
    {
        "category-language",
        "claim-boundary",
        "financial-figure",
        "hype-language",
        "meta-description",
        "page-title",
        "single-h1",
        "snapshot-date",
        "static-operating-count",
        "static-research-count",
        "static-traction-count",
    }
)

_POLICY_FIELDS = frozenset(
    {
        "schema",
        "policy_id",
        "issued_at",
        "refresh_by",
        "authority",
        "snapshot_max_age_days",
        "routes",
    }
)
_ROUTE_FIELDS = frozenset(
    {
        "route",
        "path",
        "rule_ids",
        "required_concept_groups",
    }
)
_CONCEPT_GROUP_FIELDS = frozenset({"concept_id", "severity", "alternatives"})
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")

_STATIC_RESEARCH_COUNT = re.compile(
    r"\b\d{1,6}(?:,\d{3})*\s+"
    r"(?:ORCID\s+(?:work\s+groups?|works?)|Zenodo\s+records?|"
    r"selected\s+records?|research\s+records?|publications?)\b",
    re.IGNORECASE,
)
_STATIC_TRACTION_COUNT = re.compile(
    r"\b\d{1,9}(?:,\d{3})*\s+"
    r"(?:stars?|forks?|clones?|(?:unique\s+)?cloners?|views?|downloads?|"
    r"reads?|citations?|unique\s+visitors?|countries?)\b",
    re.IGNORECASE,
)
_STATIC_OPERATING_COUNT = re.compile(
    r"(?:\b(?:~\s*)?(?:(?!0\d)\d{1,9}(?:,\d{3})*|zero)\s+"
    r"(?:selected\s+routes?|public\s+routes?|direct[- ]submit[- ]ready\s+routes?|"
    r"applications?|awards?|committed\s+investments?|modules?|offline\s+tests?|"
    r"customers?)\b|"
    r"\bcommit\s+[0-9a-f]{7,40}\b)",
    re.IGNORECASE,
)
_FINANCIAL_FIGURE = re.compile(
    r"(?:[£$€]\s*\d[\d,.]*|"
    r"\b(?:GBP|USD|EUR)\s+\d[\d,.]*|"
    r"\b\d{1,3}\s+months?\s+(?:of\s+)?runway\b|"
    r"\b(?:ARR|MRR|revenue|valuation|burn|runway)\b"
    r"[^.!?\n]{0,48}\b\d[\d,.]*\b)",
    re.IGNORECASE,
)
_SNAPSHOT_DATE = re.compile(
    r"\b(?:checked|as\s+of|snapshot(?:\s+dated)?)\s*"
    r"(?P<snapshot_date>"
    r"20\d{2}-\d{2}-\d{2}|"
    r"\d{1,2}\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20\d{2}"
    r")\b",
    re.IGNORECASE,
)
_CATEGORY_LANGUAGE = re.compile(
    r"\b(?:swiss\s+army|one[- ]trick\s+pony|everything\s+company)\b",
    re.IGNORECASE,
)
_HYPE_LANGUAGE = re.compile(
    r"\b(?:revolutionary|game[- ]changing|world[- ]leading|"
    r"industry[- ]leading|unparalleled|guaranteed\s+breakthrough)\b",
    re.IGNORECASE,
)
_UNQUALIFIED_CLAIM = re.compile(
    r"\b(?:proven\s+across|validated\s+across|adopted\s+across|"
    r"trusted\s+by\s+leading|customers?\s+include)\b",
    re.IGNORECASE,
)


class InvestorCopyQualityError(ValueError):
    """A copy-quality policy or bounded audit input is unsafe."""


class _HTMLCopyParser(HTMLParser):
    """Extract visible copy and basic document metadata without executing HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._title_depth = 0
        self._h1_depth = 0
        self.visible_parts: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.h1_count = 0
        self.meta_description = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "template", "svg"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if lowered == "title":
            self._title_depth += 1
        elif lowered == "h1":
            self._h1_depth += 1
            self.h1_count += 1
        elif lowered == "meta":
            values = {str(key).casefold(): value or "" for key, value in attrs}
            if values.get("name", "").casefold() == "description":
                self.meta_description = values.get("content", "").strip()

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in {"script", "style", "template", "svg"}:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if lowered == "title" and self._title_depth:
            self._title_depth -= 1
        elif lowered == "h1" and self._h1_depth:
            self._h1_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        self.visible_parts.append(value)
        if self._title_depth:
            self.title_parts.append(value)
        if self._h1_depth:
            self.h1_parts.append(value)

    def result(self) -> dict[str, Any]:
        return {
            "text": " ".join(self.visible_parts),
            "title": " ".join(self.title_parts),
            "h1": " ".join(self.h1_parts),
            "h1_count": self.h1_count,
            "meta_description": self.meta_description,
        }


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "aureon").is_dir() and (root / "website").is_dir():
            return root
    raise InvestorCopyQualityError("Could not locate the Aureon repository root.")


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
        raise InvestorCopyQualityError("Audit input escapes the repository.") from exc


def _exact_fields(value: Mapping[str, Any], expected: frozenset[str], *, label: str) -> None:
    actual = frozenset(str(key) for key in value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise InvestorCopyQualityError(
            f"{label} fields do not match the contract; missing={missing}, unknown={unknown}."
        )


def _mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise InvestorCopyQualityError(f"{label} must be one object.")
    return dict(value)


def _text(value: object, *, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvestorCopyQualityError(f"{label} must be non-empty text.")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise InvestorCopyQualityError(f"{label} exceeds {maximum} characters.")
    return cleaned


def _parse_datetime(value: object, *, label: str) -> datetime:
    text = _text(value, label=label, maximum=64)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestorCopyQualityError(f"{label} is not an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise InvestorCopyQualityError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _safe_relative_html(value: object, *, label: str) -> str:
    text = _text(value, label=label, maximum=240).replace("\\", "/")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or text.startswith("/") or path.suffix.casefold() != ".html":
        raise InvestorCopyQualityError(f"{label} must be a safe relative HTML path.")
    return path.as_posix()


def _safe_route(value: object) -> str:
    route = _text(value, label="route", maximum=160)
    if not route.startswith("/") or "://" in route or "?" in route or "#" in route or ".." in route:
        raise InvestorCopyQualityError(f"Unsafe local route: {route}")
    return route


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvestorCopyQualityError(f"{label} is not valid JSON: {path}") from exc
    return _mapping(parsed, label=label)


def _regular_file_under(root: Path, relative: str, *, label: str) -> Path:
    raw = root / relative
    if raw.is_symlink():
        raise InvestorCopyQualityError(f"{label} must not be a symbolic link.")
    target = raw.resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise InvestorCopyQualityError(f"{label} escapes its allowed root.") from exc
    if not target.is_file():
        raise InvestorCopyQualityError(f"{label} does not exist: {relative}")
    if target.stat().st_nlink != 1:
        raise InvestorCopyQualityError(f"{label} must not be a hard-linked file.")
    return target


def _snippet(text: str, start: int, end: int, *, radius: int = 74) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return " ".join(text[left:right].split())


def _finding(
    *,
    rule_id: str,
    severity: str,
    route: str,
    path: str,
    message: str,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "route": route,
        "path": path,
        "message": message,
        "evidence": dict(evidence),
    }


def _regex_findings(
    *,
    rule_id: str,
    pattern: re.Pattern[str],
    text: str,
    route: str,
    path: str,
    severity: str,
    message: str,
) -> list[dict[str, Any]]:
    return [
        _finding(
            rule_id=rule_id,
            severity=severity,
            route=route,
            path=path,
            message=message,
            evidence={
                "match": match.group(0),
                "snippet": _snippet(text, match.start(), match.end()),
            },
        )
        for match in pattern.finditer(text)
    ]


def _route_findings(
    route_policy: Mapping[str, Any],
    document: Mapping[str, Any],
    *,
    snapshot_max_age_days: int,
    as_of: datetime,
) -> list[dict[str, Any]]:
    route = str(route_policy["route"])
    path = str(route_policy["path"])
    text = str(document["text"])
    findings: list[dict[str, Any]] = []
    rule_ids = {str(item) for item in route_policy["rule_ids"]}

    regex_rules = {
        "category-language": (
            _CATEGORY_LANGUAGE,
            "blocker",
            "Replace catch-all positioning with one precise company category and a shared-core explanation.",
        ),
        "financial-figure": (
            _FINANCIAL_FIGURE,
            "blocker",
            "Do not expose internal or fundraising figures on the public investor surface.",
        ),
        "hype-language": (
            _HYPE_LANGUAGE,
            "warning",
            "Replace generic superlatives with a specific proposition and checkable evidence boundary.",
        ),
        "claim-boundary": (
            _UNQUALIFIED_CLAIM,
            "blocker",
            "Public adoption or validation language needs a source-bound, qualified claim.",
        ),
        "static-research-count": (
            _STATIC_RESEARCH_COUNT,
            "blocker",
            "Replace drift-prone research totals with durable evidence categories or a live verified source.",
        ),
        "static-operating-count": (
            _STATIC_OPERATING_COUNT,
            "blocker",
            "Do not publish internal route, application, implementation, test, customer, award, or commit counters.",
        ),
        "static-traction-count": (
            _STATIC_TRACTION_COUNT,
            "blocker",
            "Do not hard-code traction totals into investor copy; bind them to a current verified evidence surface or use non-numeric proof language.",
        ),
    }
    for rule_id, (pattern, severity, message) in regex_rules.items():
        if rule_id in rule_ids:
            findings.extend(
                _regex_findings(
                    rule_id=rule_id,
                    pattern=pattern,
                    text=text,
                    route=route,
                    path=path,
                    severity=severity,
                    message=message,
                )
            )

    if "snapshot-date" in rule_ids:
        for match in _SNAPSHOT_DATE.finditer(text):
            raw_observed = match.group("snapshot_date")
            observed = date.min
            for date_format in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y"):
                try:
                    observed = datetime.strptime(raw_observed, date_format).date()
                    break
                except ValueError:
                    continue
            age_days = (as_of.date() - observed).days
            findings.append(
                _finding(
                    rule_id="snapshot-date",
                    severity="blocker",
                    route=route,
                    path=path,
                    message=(
                        "A hard-coded public snapshot date must be removed or generated "
                        "from a current passing source-refresh receipt."
                    ),
                    evidence={
                        "observed_on": raw_observed,
                        "age_days": age_days,
                        "maximum_age_days": snapshot_max_age_days,
                        "outside_freshness_window": (age_days > snapshot_max_age_days or age_days < 0),
                        "snippet": _snippet(text, match.start(), match.end()),
                    },
                )
            )

    title = str(document["title"])
    if "page-title" in rule_ids and not 24 <= len(title) <= 72:
        findings.append(
            _finding(
                rule_id="page-title",
                severity="warning",
                route=route,
                path=path,
                message="Keep the page title between 24 and 72 characters.",
                evidence={"length": len(title), "title": title},
            )
        )

    description = str(document["meta_description"])
    if "meta-description" in rule_ids and not 80 <= len(description) <= 180:
        findings.append(
            _finding(
                rule_id="meta-description",
                severity="warning",
                route=route,
                path=path,
                message="Keep the meta description between 80 and 180 characters.",
                evidence={"length": len(description)},
            )
        )

    h1_count = int(document["h1_count"])
    if "single-h1" in rule_ids and h1_count != 1:
        findings.append(
            _finding(
                rule_id="single-h1",
                severity="blocker",
                route=route,
                path=path,
                message="Each investor-facing route needs exactly one H1.",
                evidence={"h1_count": h1_count},
            )
        )

    folded = text.casefold()
    for raw_group in route_policy["required_concept_groups"]:
        group = _mapping(raw_group, label="required concept group")
        alternatives = [str(item) for item in group["alternatives"]]
        if not any(alternative.casefold() in folded for alternative in alternatives):
            findings.append(
                _finding(
                    rule_id="required-concept",
                    severity=str(group["severity"]),
                    route=route,
                    path=path,
                    message=f"Route is missing the controlled concept '{group['concept_id']}'.",
                    evidence={"accepted_alternatives": alternatives},
                )
            )
    return findings


def _validate_policy(
    policy: Mapping[str, Any], *, as_of: datetime
) -> tuple[list[dict[str, Any]], datetime, datetime, int]:
    _exact_fields(policy, _POLICY_FIELDS, label="Investor-copy policy")
    if policy.get("schema") != POLICY_SCHEMA:
        raise InvestorCopyQualityError("Investor-copy policy schema is unsupported.")
    policy_id = _text(policy.get("policy_id"), label="policy_id", maximum=128)
    if not _IDENTIFIER.fullmatch(policy_id):
        raise InvestorCopyQualityError("policy_id must be a stable lowercase identifier.")
    if policy.get("authority") != NON_AUTHORITATIVE_AUTHORITY:
        raise InvestorCopyQualityError("Investor-copy policy authority changed.")

    issued_at = _parse_datetime(policy.get("issued_at"), label="issued_at")
    refresh_by = _parse_datetime(policy.get("refresh_by"), label="refresh_by")
    if refresh_by <= issued_at:
        raise InvestorCopyQualityError("refresh_by must follow issued_at.")
    if issued_at > as_of:
        raise InvestorCopyQualityError("Investor-copy policy is future-dated.")

    snapshot_max_age_days = policy.get("snapshot_max_age_days")
    if (
        isinstance(snapshot_max_age_days, bool)
        or not isinstance(snapshot_max_age_days, int)
        or not 1 <= snapshot_max_age_days <= 31
    ):
        raise InvestorCopyQualityError("snapshot_max_age_days must be an integer from 1 to 31.")

    raw_routes = policy.get("routes")
    if not isinstance(raw_routes, list) or not raw_routes:
        raise InvestorCopyQualityError("Investor-copy policy needs bounded routes.")
    routes: list[dict[str, Any]] = []
    seen_routes: set[str] = set()
    seen_paths: set[str] = set()
    for index, raw_route in enumerate(raw_routes):
        route_policy = _mapping(raw_route, label=f"route[{index}]")
        _exact_fields(route_policy, _ROUTE_FIELDS, label=f"route[{index}]")
        route = _safe_route(route_policy.get("route"))
        path = _safe_relative_html(route_policy.get("path"), label=f"{route} path")
        if route in seen_routes or path in seen_paths:
            raise InvestorCopyQualityError("Policy routes and paths must be unique.")
        seen_routes.add(route)
        seen_paths.add(path)

        raw_rules = route_policy.get("rule_ids")
        if not isinstance(raw_rules, list) or not raw_rules:
            raise InvestorCopyQualityError(f"{route} needs at least one controlled rule.")
        rule_ids = [_text(item, label=f"{route} rule id", maximum=80) for item in raw_rules]
        if len(rule_ids) != len(set(rule_ids)) or not set(rule_ids).issubset(RULE_IDS):
            raise InvestorCopyQualityError(f"{route} contains duplicate or unknown rule ids.")

        raw_groups = route_policy.get("required_concept_groups")
        if not isinstance(raw_groups, list):
            raise InvestorCopyQualityError(f"{route} required_concept_groups must be a list.")
        groups: list[dict[str, Any]] = []
        seen_concepts: set[str] = set()
        for group_index, raw_group in enumerate(raw_groups):
            group = _mapping(raw_group, label=f"{route} concept group[{group_index}]")
            _exact_fields(
                group,
                _CONCEPT_GROUP_FIELDS,
                label=f"{route} concept group[{group_index}]",
            )
            concept_id = _text(group.get("concept_id"), label="concept_id", maximum=80)
            if not _IDENTIFIER.fullmatch(concept_id) or concept_id in seen_concepts:
                raise InvestorCopyQualityError(f"{route} concept identifiers must be safe and unique.")
            seen_concepts.add(concept_id)
            severity = _text(group.get("severity"), label="severity", maximum=16)
            if severity not in SEVERITIES:
                raise InvestorCopyQualityError("Unknown concept severity.")
            alternatives = group.get("alternatives")
            if not isinstance(alternatives, list) or not alternatives:
                raise InvestorCopyQualityError(f"{route} concept group {concept_id} needs alternatives.")
            cleaned_alternatives = [
                _text(
                    item,
                    label=f"{route} concept alternative",
                    maximum=120,
                )
                for item in alternatives
            ]
            if len(cleaned_alternatives) != len(set(cleaned_alternatives)):
                raise InvestorCopyQualityError(f"{route} concept alternatives must be unique.")
            groups.append(
                {
                    "concept_id": concept_id,
                    "severity": severity,
                    "alternatives": cleaned_alternatives,
                }
            )
        routes.append(
            {
                "route": route,
                "path": path,
                "rule_ids": rule_ids,
                "required_concept_groups": groups,
            }
        )
    return routes, issued_at, refresh_by, snapshot_max_age_days


def audit_investor_copy_quality(
    policy: Mapping[str, Any],
    *,
    policy_path: Path,
    website_root: Path,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Audit bounded local routes and return a deterministic non-authoritative receipt."""

    root = _find_repo_root(repo_root)
    observed_at = (as_of or _utc_now()).astimezone(UTC)
    resolved_policy = policy_path.resolve()
    _relative_to_repo(root, resolved_policy)
    resolved_website = website_root.resolve()
    _relative_to_repo(root, resolved_website)
    if not resolved_website.is_dir() or resolved_website.is_symlink():
        raise InvestorCopyQualityError("website_root must be one regular directory.")

    routes, issued_at, refresh_by, max_age_days = _validate_policy(policy, as_of=observed_at)
    policy_current = issued_at <= observed_at <= refresh_by
    findings: list[dict[str, Any]] = []
    route_results: list[dict[str, Any]] = []
    for route_policy in routes:
        path = _regular_file_under(
            resolved_website,
            str(route_policy["path"]),
            label=f"{route_policy['route']} document",
        )
        parser = _HTMLCopyParser()
        try:
            parser.feed(path.read_text(encoding="utf-8-sig"))
            parser.close()
        except (OSError, UnicodeError) as exc:
            raise InvestorCopyQualityError(f"Could not read bounded HTML route: {path}") from exc
        document = parser.result()
        route_findings = _route_findings(
            route_policy,
            document,
            snapshot_max_age_days=max_age_days,
            as_of=observed_at,
        )
        findings.extend(route_findings)
        route_results.append(
            {
                "route": route_policy["route"],
                "path": route_policy["path"],
                "sha256": _sha256(path),
                "title": document["title"],
                "h1": document["h1"],
                "finding_count": len(route_findings),
                "blocker_count": sum(item["severity"] == "blocker" for item in route_findings),
                "warning_count": sum(item["severity"] == "warning" for item in route_findings),
            }
        )

    if not policy_current:
        findings.insert(
            0,
            _finding(
                rule_id="policy-freshness",
                severity="blocker",
                route="*",
                path=_relative_to_repo(root, resolved_policy),
                message="Investor-copy policy is stale and must be human-refreshed.",
                evidence={
                    "issued_at": _iso(issued_at),
                    "refresh_by": _iso(refresh_by),
                    "observed_at": _iso(observed_at),
                },
            ),
        )

    blocker_count = sum(item["severity"] == "blocker" for item in findings)
    warning_count = sum(item["severity"] == "warning" for item in findings)
    passed = blocker_count == 0 and policy_current
    return {
        "schema": AUDIT_SCHEMA,
        "audited_at": _iso(observed_at),
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": NON_AUTHORITATIVE_AUTHORITY,
        "policy": {
            "policy_id": policy["policy_id"],
            "path": _relative_to_repo(root, resolved_policy),
            "sha256": _sha256(resolved_policy),
            "issued_at": _iso(issued_at),
            "refresh_by": _iso(refresh_by),
            "current": policy_current,
        },
        "website_root": _relative_to_repo(root, resolved_website),
        "routes": route_results,
        "findings": findings,
        "summary": {
            "route_count": len(route_results),
            "finding_count": len(findings),
            "blocker_count": blocker_count,
            "warning_count": warning_count,
        },
        "next_gate": (
            "Named human copy review may use this receipt to prepare a bounded staged "
            "candidate; this audit cannot rewrite, promote, package, or deploy the site."
        ),
    }


def audit_investor_copy_quality_file(
    policy_path: Path | None = None,
    *,
    website_root: Path | None = None,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    root = _find_repo_root(repo_root)
    relative_policy = policy_path or DEFAULT_POLICY_PATH
    resolved_policy = (
        relative_policy if relative_policy.is_absolute() else (root / relative_policy)
    ).resolve()
    _relative_to_repo(root, resolved_policy)
    if resolved_policy.is_symlink() or not resolved_policy.is_file():
        raise InvestorCopyQualityError("Investor-copy policy must be one regular repository file.")
    relative_website = website_root or DEFAULT_WEBSITE_ROOT
    resolved_website = (
        relative_website if relative_website.is_absolute() else (root / relative_website)
    ).resolve()
    return audit_investor_copy_quality(
        _read_json(resolved_policy, label="Investor-copy policy"),
        policy_path=resolved_policy,
        website_root=resolved_website,
        repo_root=root,
        as_of=as_of,
    )


def write_investor_copy_quality_audit(
    receipt: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    root = _find_repo_root(repo_root)
    target = output_path if output_path.is_absolute() else root / output_path
    target = target.resolve()
    allowed = (root / DEFAULT_AUDIT_ROOT).resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise InvestorCopyQualityError("Copy-quality audits must stay below docs/audits/.") from exc
    if target.exists():
        raise InvestorCopyQualityError("Copy-quality audit output already exists.")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    target.write_text(encoded, encoding="utf-8", newline="\n")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit bounded Aureon investor-facing HTML copy without mutation."
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--website-root", type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    receipt = audit_investor_copy_quality_file(
        args.policy,
        website_root=args.website_root,
        repo_root=args.repo_root,
    )
    if args.output:
        write_investor_copy_quality_audit(receipt, args.output, repo_root=args.repo_root)
    else:
        # Keep stdout valid on the Windows operator host even when its console
        # still uses a legacy code page. Persisted receipts remain UTF-8.
        print(json.dumps(receipt, ensure_ascii=True, indent=2))
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
