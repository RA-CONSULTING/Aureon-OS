"""Fail-closed public-claim surface control for staged website candidates.

The public site is an investor-facing company record.  A source-hash refresh
alone must not let a staged worker turn an unsupported assertion into a
``candidate-validated`` result.  This module compares the newly rendered
static text surfaces of a staged candidate with its unchanged, owner-selected
source baseline, then binds every new surface to a sealed route claim capsule.

It is deliberately local and non-authoritative: no network access, browser
automation, canonical-site mutation, package creation, credential access, or
deployment is performed here.  A passing result only proves a narrow text
surface contract for one already-staged candidate.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree

CLAIM_SURFACE_SCHEMA = "aureon.design-candidate-claim-surface.v1"

AUTHORITY = {
    "scope": "local staged-candidate public claim-surface evidence only",
    "canonical_website_mutation": "never by this control or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "human_visual_acceptance": "required for material brand changes",
    "release_authority": "WebsiteOperator owner gate only",
}

TEXT_SURFACE_EXTENSIONS = frozenset(
    {".css", ".html", ".htm", ".js", ".json", ".svg", ".txt", ".webmanifest", ".xml"}
)
MANIFEST_KINDS = frozenset({"permitted-wording", "boundary", "non-claim"})
MANIFEST_RATIONALES_BY_KIND = {
    "permitted-wording": frozenset({"route-permitted-wording"}),
    "boundary": frozenset({"route-claim-boundary"}),
    "non-claim": frozenset(
        {
            "accessibility-label",
            "citation-label",
            "decorative-copy",
            "interface-label",
            "metadata-label",
            "navigation-label",
            "source-label",
        }
    ),
}
MANIFEST_RATIONALES = frozenset().union(*MANIFEST_RATIONALES_BY_KIND.values())
_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_SPACE = re.compile(r"\s+")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_CSS_CONTENT = re.compile(
    r"\bcontent\s*:\s*(?P<quote>['\"])(?P<value>(?:\\.|(?!\1).)*)\1",
    re.IGNORECASE | re.DOTALL,
)

# These are deliberately conservative: a non-claim surface may not smuggle a
# public company/validation assertion past the capsule.  Exact permitted
# wording and exact boundaries remain available through their own manifest
# kinds, including negative boundary language such as "not customer adoption".
_CLAIM_BEARING_PHRASES = (
    "aureon",
    "aureon os",
    "harmonic nexus",
    "hnc",
    "mission blade",
    "customer adoption",
    "customer use",
    "production autonomy",
    "production readiness",
    "production deployment",
    "independent validation",
    "peer review",
    "commercial outcome",
    "commercial performance",
    "commercial wedge",
    "evidence infrastructure",
    "evidence os",
    "first wedge",
    "funding outcome",
    "investment outcome",
    "partnership",
    "endorsement",
    "market leadership",
    "research and systems company",
    "research-led systems company",
    "universal validity",
    "established scientific field",
)


class DesignCandidateClaimSurfaceError(ValueError):
    """A staged candidate text surface or its sealed claim context is unsafe."""


def _json_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def normalise_public_text(value: object) -> str:
    """Return the stable NFC/whitespace form used by the public-text contract."""

    if not isinstance(value, str):
        raise DesignCandidateClaimSurfaceError("Public text must be UTF-8 text.")
    return _SPACE.sub(" ", unicodedata.normalize("NFC", unescape(value))).strip()


def public_text_sha256(value: object) -> str:
    """Hash one normalised public text surface without retaining its wording."""

    return hashlib.sha256(normalise_public_text(value).encode("utf-8")).hexdigest().upper()


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignCandidateClaimSurfaceError(f"{label} must be a non-empty candidate-relative path.")
    candidate = Path(value.replace("\\", "/"))
    if (
        candidate.is_absolute()
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise DesignCandidateClaimSurfaceError(f"{label} is unsafe.")
    return candidate.as_posix()


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {"id": identifier, "passed": bool(passed), "message": message, "evidence": evidence}


def _split_surfaces(value: object) -> list[str]:
    text = normalise_public_text(value)
    if not text:
        return []
    return [segment for segment in _SENTENCE_BREAK.split(text) if segment]


class _PublicHtmlSurfaceParser(HTMLParser):
    """Extract rendered/static HTML text without treating scripts or CSS as HTML copy."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.surfaces: list[tuple[str, str]] = []
        self.errors: list[str] = []
        self._blocked_depth = 0
        self._json_script_depth = 0
        self._json_script_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        attributes = {str(key).casefold(): value for key, value in attrs}
        if lowered == "script":
            script_type = str(attributes.get("type") or "").casefold().split(";", 1)[0].strip()
            if script_type == "application/ld+json":
                self._json_script_depth += 1
                self._json_script_chunks = []
            else:
                self._blocked_depth += 1
            return
        if lowered == "style":
            self._blocked_depth += 1
            return
        for name in ("alt", "aria-label", "title", "placeholder"):
            value = attributes.get(name)
            if isinstance(value, str) and normalise_public_text(value):
                self.surfaces.extend((f"html-attr:{name}", item) for item in _split_surfaces(value))
        if lowered == "meta":
            name = str(attributes.get("name") or attributes.get("property") or "").casefold()
            value = attributes.get("content")
            if name in {
                "description",
                "og:description",
                "twitter:description",
                "og:title",
                "twitter:title",
            } and isinstance(value, str):
                self.surfaces.extend(("html-meta", item) for item in _split_surfaces(value))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered == "script":
            if self._json_script_depth:
                self._json_script_depth -= 1
                if not self._json_script_depth:
                    try:
                        self.surfaces.extend(
                            ("json", item) for item in _json_surfaces("".join(self._json_script_chunks))
                        )
                    except DesignCandidateClaimSurfaceError:
                        self.errors.append("html-json-ld-not-statically-auditable")
                    self._json_script_chunks = []
            elif self._blocked_depth:
                self._blocked_depth -= 1
        elif lowered == "style" and self._blocked_depth:
            self._blocked_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._json_script_depth:
            self._json_script_chunks.append(data)
        elif not self._blocked_depth:
            self.surfaces.extend(("html-text", item) for item in _split_surfaces(data))


def _json_surfaces(text: str) -> list[str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DesignCandidateClaimSurfaceError("JSON public text is not statically auditable.") from exc
    values: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, str):
            values.extend(_split_surfaces(value))
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, Mapping):
            for child in value.values():
                visit(child)

    visit(parsed)
    return values


def _javascript_surfaces(text: str) -> tuple[list[str], list[str]]:
    """Read simple static literals; dynamic rendered copy is intentionally rejected."""

    if re.search(r"\b(?:innerHTML|outerHTML|insertAdjacentHTML|document\.write)\b", text):
        return [], ["javascript-dynamic-dom-copy"]
    values: list[str] = []
    errors: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character not in {"'", '"', "`"}:
            index += 1
            continue
        quote = character
        index += 1
        buffer: list[str] = []
        escaped = False
        closed = False
        while index < length:
            current = text[index]
            if escaped:
                if current in {"u", "x"}:
                    errors.append("javascript-escaped-public-copy")
                buffer.append(current)
                escaped = False
            elif current == "\\":
                escaped = True
            elif quote == "`" and current == "$" and index + 1 < length and text[index + 1] == "{":
                errors.append("javascript-interpolated-template")
                return [], errors
            elif current == quote:
                closed = True
                index += 1
                break
            else:
                buffer.append(current)
            index += 1
        if not closed:
            errors.append("javascript-unterminated-literal")
            break
        candidate = "".join(buffer)
        if normalise_public_text(candidate):
            values.extend(_split_surfaces(candidate))
    return values, sorted(set(errors))


def _xml_surfaces(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return [], ["xml-not-statically-auditable"]
    values: list[tuple[str, str]] = []
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1].casefold() if isinstance(element.tag, str) else ""
        if local == "script":
            return [], ["svg-script-not-permitted"]
        if local in {"title", "desc", "text", "tspan"} and isinstance(element.text, str):
            values.extend(("svg-text", item) for item in _split_surfaces(element.text))
        for name in ("aria-label", "title", "desc"):
            value = element.attrib.get(name)
            if isinstance(value, str):
                values.extend((f"svg-attr:{name}", item) for item in _split_surfaces(value))
    return values, []


def _file_surfaces(path: Path, relative: str) -> tuple[list[dict[str, str]], list[str]]:
    suffix = Path(relative).suffix.casefold()
    if suffix not in TEXT_SURFACE_EXTENSIONS:
        return [], []
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return [], ["non-utf8-public-text"]
    try:
        if suffix in {".html", ".htm"}:
            parser = _PublicHtmlSurfaceParser()
            parser.feed(text)
            parser.close()
            pairs = parser.surfaces
            errors = parser.errors
        elif suffix in {".json", ".webmanifest"}:
            pairs = [("json", item) for item in _json_surfaces(text)]
            errors = []
        elif suffix == ".js":
            values, errors = _javascript_surfaces(text)
            pairs = [("javascript", item) for item in values]
        elif suffix == ".css":
            pairs = [
                ("css-content", item)
                for match in _CSS_CONTENT.finditer(text)
                for item in _split_surfaces(match.group("value"))
            ]
            errors = []
        elif suffix in {".svg", ".xml"}:
            pairs, errors = _xml_surfaces(text)
        else:
            pairs = [("text", item) for item in _split_surfaces(text)]
            errors = []
    except DesignCandidateClaimSurfaceError:
        return [], ["public-text-not-statically-auditable"]
    rows: list[dict[str, str]] = []
    ordinal: defaultdict[tuple[str, str], int] = defaultdict(int)
    for source, value in pairs:
        normalised = normalise_public_text(value)
        if not normalised:
            continue
        text_sha256 = public_text_sha256(normalised)
        key = (source, text_sha256)
        ordinal[key] += 1
        rows.append(
            {
                "path": relative,
                "source": source,
                "text": normalised,
                "text_sha256": text_sha256,
                "ordinal": str(ordinal[key]),
            }
        )
    return rows, sorted(set(errors))


def _surface_sha256(row: Mapping[str, str]) -> str:
    return _json_sha256(
        {
            "path": row["path"],
            "source": row["source"],
            "text_sha256": row["text_sha256"],
            "ordinal": int(row["ordinal"]),
        }
    )


def _new_surfaces(
    baseline: Sequence[Mapping[str, str]], candidate: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    previous = Counter((row["source"], row["text_sha256"]) for row in baseline)
    emitted: Counter[tuple[str, str]] = Counter()
    result: list[dict[str, str]] = []
    for raw in candidate:
        key = (raw["source"], raw["text_sha256"])
        emitted[key] += 1
        if emitted[key] <= previous[key]:
            continue
        row = dict(raw)
        row["surface_sha256"] = _surface_sha256(row)
        result.append(row)
    return result


def _removed_surfaces(
    baseline: Sequence[Mapping[str, str]], candidate: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    """Return baseline surfaces no longer present with the same rendered source.

    Boundary preservation is deliberately source-sensitive.  Moving a visible
    disclaimer into metadata is not equivalent to retaining it in the public
    rendering surface where it previously appeared.
    """

    retained = Counter((row["source"], row["text_sha256"]) for row in candidate)
    emitted: Counter[tuple[str, str]] = Counter()
    result: list[dict[str, str]] = []
    for raw in baseline:
        key = (raw["source"], raw["text_sha256"])
        emitted[key] += 1
        if emitted[key] <= retained[key]:
            continue
        row = dict(raw)
        row["surface_sha256"] = _surface_sha256(row)
        result.append(row)
    return result


def _claim_context(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], set[str], set[str]]:
    required = {"id", "route", "allowed_paths", "claim_capsule", "claim_capsule_sha256"}
    if set(value) != required:
        raise DesignCandidateClaimSurfaceError(
            "Claim-surface context must retain only the sealed route binding fields."
        )
    route_id = value.get("id")
    route = value.get("route")
    allowed = value.get("allowed_paths")
    capsule = value.get("claim_capsule")
    capsule_sha256 = value.get("claim_capsule_sha256")
    if (
        not isinstance(route_id, str)
        or not route_id
        or not isinstance(route, str)
        or not route.startswith("/")
        or not isinstance(allowed, list)
        or not allowed
        or not all(isinstance(item, str) and item for item in allowed)
        or not isinstance(capsule, Mapping)
        or not isinstance(capsule_sha256, str)
        or not _SHA256.fullmatch(capsule_sha256)
        or _json_sha256(capsule) != capsule_sha256
    ):
        raise DesignCandidateClaimSurfaceError("Claim-surface context is malformed or no longer hash-bound.")
    if capsule.get("route_id") != route_id or capsule.get("route") != route:
        raise DesignCandidateClaimSurfaceError("Claim capsule route does not match the sealed route binding.")
    raw_claims = capsule.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise DesignCandidateClaimSurfaceError(
            "Claim capsule must contain at least one route-permitted claim."
        )
    claims: dict[str, dict[str, Any]] = {}
    permitted_hashes: set[str] = set()
    boundary_hashes: set[str] = set()
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, Mapping):
            raise DesignCandidateClaimSurfaceError("Claim capsule entries must be objects.")
        identifier = raw_claim.get("id")
        wording = raw_claim.get("permitted_wording")
        boundary = raw_claim.get("boundary")
        prohibited = raw_claim.get("prohibited_inferences")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in claims
            or not isinstance(wording, list)
            or not wording
            or not all(isinstance(item, str) and normalise_public_text(item) for item in wording)
            or not isinstance(boundary, str)
            or not normalise_public_text(boundary)
            or not isinstance(prohibited, list)
            or not prohibited
            or not all(isinstance(item, str) and normalise_public_text(item) for item in prohibited)
        ):
            raise DesignCandidateClaimSurfaceError(
                "Claim capsule lacks a bounded wording, boundary, or inference contract."
            )
        claims[identifier] = {
            "permitted": {public_text_sha256(item) for item in wording},
            "boundary": public_text_sha256(boundary),
            "prohibited": {normalise_public_text(item).casefold() for item in prohibited},
        }
        permitted_hashes.update(claims[identifier]["permitted"])
        boundary_hashes.add(claims[identifier]["boundary"])
    context = {
        "id": route_id,
        "route": route,
        "allowed_paths": sorted(set(allowed)),
        "claim_capsule": dict(capsule),
        "claim_capsule_sha256": capsule_sha256,
    }
    return context, claims, permitted_hashes, boundary_hashes


def _normalise_manifest(value: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise DesignCandidateClaimSurfaceError("Claim-surface manifest must be a list.")
    rows: list[dict[str, str]] = []
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {
            "path",
            "kind",
            "claim_id",
            "text_sha256",
            "surface_sha256",
            "rationale",
        }:
            raise DesignCandidateClaimSurfaceError(
                "Each claim-surface manifest entry needs exactly six bounded fields."
            )
        path = _safe_relative_path(raw.get("path"), label="Claim-surface path")
        kind = raw.get("kind")
        claim_id = raw.get("claim_id")
        text_sha256 = raw.get("text_sha256")
        surface_sha256 = raw.get("surface_sha256")
        rationale = raw.get("rationale")
        if (
            kind not in MANIFEST_KINDS
            or not isinstance(claim_id, str)
            or not isinstance(text_sha256, str)
            or not _SHA256.fullmatch(text_sha256)
            or not isinstance(surface_sha256, str)
            or not _SHA256.fullmatch(surface_sha256)
            or not isinstance(rationale, str)
            or rationale not in MANIFEST_RATIONALES_BY_KIND.get(str(kind), frozenset())
        ):
            raise DesignCandidateClaimSurfaceError("Claim-surface manifest entry is malformed.")
        if kind == "non-claim" and claim_id:
            raise DesignCandidateClaimSurfaceError("A non-claim surface must not name a claim id.")
        if kind != "non-claim" and not claim_id:
            raise DesignCandidateClaimSurfaceError(
                "A claim wording or boundary surface must name its claim id."
            )
        rows.append(
            {
                "path": path,
                "kind": str(kind),
                "claim_id": claim_id,
                "text_sha256": text_sha256,
                "surface_sha256": surface_sha256,
                # This is a controlled abstract taxonomy, never free-form
                # public wording.  It therefore cannot become a secondary
                # route for leaking or self-certifying staged copy.
                "rationale": rationale,
            }
        )
    keys = [(row["path"], row["surface_sha256"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise DesignCandidateClaimSurfaceError(
            "Claim-surface manifest cannot duplicate a public text surface."
        )
    return rows


def _contains_prohibited(text: str, claims: Mapping[str, Mapping[str, Any]]) -> bool:
    lowered = normalise_public_text(text).casefold()
    prohibited = set(_CLAIM_BEARING_PHRASES)
    for claim in claims.values():
        prohibited.update(claim["prohibited"])
    return any(phrase in lowered for phrase in prohibited)


def evaluate_candidate_claim_surface(
    *,
    baseline_site: Path,
    candidate_site: Path,
    changed_paths: Sequence[str],
    context: Mapping[str, Any],
    manifest: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Check every newly rendered public text surface against one sealed route capsule.

    ``changed_paths`` must come from the candidate diff; callers cannot direct
    this control at arbitrary files.  The receipt never retains raw new public
    wording—only its deterministic hashes and bounded classification.
    """

    checks: list[dict[str, Any]] = []
    try:
        sealed_context, claims, permitted_hashes, boundary_hashes = _claim_context(context)
        context_ok = True
        context_error = ""
    except DesignCandidateClaimSurfaceError as exc:
        sealed_context = {}
        claims = {}
        permitted_hashes = set()
        boundary_hashes = set()
        context_ok = False
        context_error = str(exc)
    checks.append(
        _check(
            "sealed-route-claim-capsule",
            context_ok,
            "A candidate claim surface needs an exact hash-bound runner route claim capsule.",
            error=context_error,
        )
    )

    try:
        safe_changed = sorted(
            {_safe_relative_path(item, label="Changed candidate path") for item in changed_paths}
        )
        changed_ok = all(path in set(sealed_context.get("allowed_paths") or []) for path in safe_changed)
    except DesignCandidateClaimSurfaceError:
        safe_changed = []
        changed_ok = False
    checks.append(
        _check(
            "changed-path-scope",
            changed_ok,
            "Claim-surface inspection may only consider exact staged paths allowed for the sealed route.",
            changed_paths=safe_changed,
        )
    )

    parse_errors: list[dict[str, str]] = []
    baseline_rows: list[dict[str, str]] = []
    candidate_rows: list[dict[str, str]] = []
    roots_ok = (
        baseline_site.is_dir()
        and candidate_site.is_dir()
        and not baseline_site.is_symlink()
        and not candidate_site.is_symlink()
    )
    if roots_ok:
        for relative in safe_changed:
            if Path(relative).suffix.casefold() not in TEXT_SURFACE_EXTENSIONS:
                continue
            baseline_path = baseline_site / relative
            candidate_path = candidate_site / relative
            if not candidate_path.is_file() or candidate_path.is_symlink():
                parse_errors.append({"path": relative, "code": "candidate-public-text-missing"})
                continue
            candidate_surfaces, candidate_errors = _file_surfaces(candidate_path, relative)
            candidate_rows.extend(candidate_surfaces)
            parse_errors.extend({"path": relative, "code": code} for code in candidate_errors)
            if baseline_path.is_file() and not baseline_path.is_symlink():
                baseline_surfaces, baseline_errors = _file_surfaces(baseline_path, relative)
                baseline_rows.extend(baseline_surfaces)
                parse_errors.extend({"path": relative, "code": code} for code in baseline_errors)
    else:
        parse_errors.append({"path": "", "code": "candidate-or-baseline-root-invalid"})
    checks.append(
        _check(
            "static-public-text-audit",
            roots_ok and not parse_errors,
            "Changed public rendering files must be regular UTF-8 sources with statically auditable public text surfaces.",
            errors=parse_errors,
        )
    )

    new_rows = _new_surfaces(baseline_rows, candidate_rows) if not parse_errors else []
    removed_rows = _removed_surfaces(baseline_rows, candidate_rows) if not parse_errors else []
    removed_boundaries = [row for row in removed_rows if row["text_sha256"] in boundary_hashes]
    removed_boundary_claims = sorted(
        claim_id
        for claim_id, claim in claims.items()
        if any(row["text_sha256"] == claim["boundary"] for row in removed_boundaries)
    )
    boundaries_preserved = context_ok and not removed_boundaries
    checks.append(
        _check(
            "existing-route-boundary-preservation",
            boundaries_preserved,
            "An exact route-claim boundary already rendered by a changed source must remain on the same public surface type.",
            removed_boundary_count=len(removed_boundaries),
            affected_claim_count=len(removed_boundary_claims),
            removed_boundary_surfaces=[
                {
                    "path": row["path"],
                    "source": row["source"],
                    "text_sha256": row["text_sha256"],
                    "surface_sha256": row["surface_sha256"],
                }
                for row in removed_boundaries
            ],
        )
    )
    try:
        manifest_rows = _normalise_manifest(manifest)
        manifest_ok = True
        manifest_error = ""
    except DesignCandidateClaimSurfaceError as exc:
        manifest_rows = []
        manifest_ok = False
        manifest_error = str(exc)
    expected_by_key = {(row["path"], row["surface_sha256"]): row for row in new_rows}
    observed_by_key = {(row["path"], row["surface_sha256"]): row for row in manifest_rows}
    coverage_ok = manifest_ok and set(expected_by_key) == set(observed_by_key)
    checks.append(
        _check(
            "new-public-surface-manifest",
            coverage_ok,
            "Every newly rendered public text surface needs exactly one hash-only claim-surface manifest entry.",
            expected_count=len(expected_by_key),
            declared_count=len(observed_by_key),
            missing_count=len(set(expected_by_key).difference(observed_by_key)),
            extra_count=len(set(observed_by_key).difference(expected_by_key)),
            error=manifest_error,
        )
    )

    classifications_ok = coverage_ok and context_ok
    unsafe_surface_count = 0
    classification_errors: list[dict[str, str]] = []
    if coverage_ok and context_ok:
        for key, observed in observed_by_key.items():
            actual = expected_by_key[key]
            text_hash = actual["text_sha256"]
            kind = observed["kind"]
            claim_id = observed["claim_id"]
            valid = observed["text_sha256"] == text_hash
            if kind == "permitted-wording":
                valid = valid and claim_id in claims and text_hash in claims[claim_id]["permitted"]
            elif kind == "boundary":
                valid = valid and claim_id in claims and text_hash == claims[claim_id]["boundary"]
            else:
                has_unsafe_inference = _contains_prohibited(actual["text"], claims)
                is_known_claim = text_hash in permitted_hashes or text_hash in boundary_hashes
                valid = valid and not has_unsafe_inference and not is_known_claim
                if has_unsafe_inference:
                    unsafe_surface_count += 1
            if not valid:
                classifications_ok = False
                classification_errors.append(
                    {
                        "path": actual["path"],
                        "surface_sha256": actual["surface_sha256"],
                        "code": "surface-not-permitted-by-route-capsule",
                    }
                )
    checks.append(
        _check(
            "route-permitted-wording-and-boundaries",
            classifications_ok,
            "New public copy must be exact permitted wording, an exact boundary, or a non-claim surface without prohibited inference.",
            invalid_surface_count=len(classification_errors),
            unsafe_non_claim_surface_count=unsafe_surface_count,
            errors=classification_errors,
        )
    )

    passed = all(item["passed"] for item in checks)
    safe_manifest = [
        {
            "path": row["path"],
            "kind": row["kind"],
            "claim_id": row["claim_id"],
            "text_sha256": row["text_sha256"],
            "surface_sha256": row["surface_sha256"],
            "rationale": row["rationale"],
        }
        for row in manifest_rows
    ]
    return {
        "schema": CLAIM_SURFACE_SCHEMA,
        "state": "pass" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(AUTHORITY),
        "context": {
            "id": sealed_context.get("id", ""),
            "route": sealed_context.get("route", ""),
            "allowed_paths": list(sealed_context.get("allowed_paths") or []),
            "claim_capsule_sha256": sealed_context.get("claim_capsule_sha256", ""),
        },
        "manifest": safe_manifest,
        "new_surfaces": [
            {
                "path": row["path"],
                "source": row["source"],
                "text_sha256": row["text_sha256"],
                "surface_sha256": row["surface_sha256"],
            }
            for row in new_rows
        ],
        "surface_fingerprint_sha256": _json_sha256(
            [
                {
                    "path": row["path"],
                    "source": row["source"],
                    "text_sha256": row["text_sha256"],
                    "surface_sha256": row["surface_sha256"],
                }
                for row in new_rows
            ]
        ),
        "summary": {
            "changed_path_count": len(safe_changed),
            "text_surface_path_count": len({row["path"] for row in candidate_rows}),
            "new_public_surface_count": len(new_rows),
            "manifest_entry_count": len(safe_manifest),
        },
        "checks": checks,
    }
