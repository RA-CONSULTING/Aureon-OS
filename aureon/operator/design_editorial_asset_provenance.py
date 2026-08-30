"""Fail-closed provenance and rights checks for external editorial artwork.

This module audits exact local files and exact proposed website placements.  A
provider delivery signal is provenance evidence only: it has no rights effect.
Only a separate, hash-bound decision made by a named human whose normalised
identity is on the controlled owner-reviewer allowlist can make one exact asset
record candidate-use-ready.  Even then, this module cannot mutate the
website, import assets, package a release, deploy, use credentials, or change
the global ``not-cleared`` artwork policy.

The worker capsule intentionally excludes source registers, correspondence,
mailbox/provider identifiers, the human decision-maker's name, and decision
evidence paths.  It is a bounded design input, not a publication authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import stat
import tempfile
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

MANIFEST_SCHEMA = "aureon.design-editorial-asset-provenance.v1"
AUDIT_SCHEMA = "aureon.design-editorial-asset-provenance-audit.v1"
WORKER_CAPSULE_SCHEMA = "aureon.design-editorial-asset-worker-capsule.v1"
RIGHTS_DECISION_SCHEMA = "aureon.editorial-asset-human-rights-decision.v1"
DELIVERY_SNAPSHOT_SCHEMA = "aureon.redacted-editorial-asset-delivery-evidence.v1"
INVENTORY_SNAPSHOT_SCHEMA = "aureon.redacted-editorial-asset-local-inventory.v1"
SURFACE_BINDING_SCHEMA = "aureon.design-editorial-asset-surface-binding.v1"
RIGHTS_PREPARATION_REQUEST_SCHEMA = "aureon.editorial-asset-rights-decision-preparation-request.v1"
RIGHTS_BINDING_PROPOSAL_SCHEMA = "aureon.editorial-asset-rights-manifest-binding-proposal.v1"
RUNTIME_VISIBILITY_REQUIRED_STATE = "runtime-computed-visibility-required"

DEFAULT_MANIFEST_PATH = Path("data/website_operator/editorial_asset_provenance.v1.json")
DEFAULT_AUDIT_ROOT = Path("docs/audits")
DEFAULT_RIGHTS_REQUEST_ROOT = Path("artifacts/website-operator/editorial-rights-requests")
DEFAULT_RIGHTS_PROPOSAL_ROOT = Path("artifacts/website-operator/editorial-rights-decisions")

NON_AUTHORITATIVE_AUTHORITY = {
    "scope": "local per-asset editorial provenance and rights preflight only",
    "global_artwork_policy_mutation": "never",
    "canonical_website_mutation": "never",
    "source_asset_import": "never",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "connector_access": "none",
    "human_rights_decision": "required for each exact candidate-use-ready asset",
}

GLOBAL_NOT_CLEARED_POLICY = {
    "state": "not-cleared",
    "cleared_for_use": False,
    "per_asset_effect": "candidate-use-ready only; never global clearance",
    "boundary": (
        "File integrity and delivery evidence do not grant rights. Each exact "
        "asset, variant, route, destination and copy binding requires a separate "
        "named human rights decision before staged use."
    ),
}

RIGHTS_PREPARATION_AUTHORITY = {
    "scope": "immutable per-asset decision evidence and manifest-binding proposal only",
    "rights_inference": "never",
    "canonical_manifest_mutation": "never",
    "global_artwork_policy_mutation": "never",
    "canonical_website_mutation": "never",
    "source_asset_mutation": "never",
    "candidate_mutation": "never",
    "package_authority": "none",
    "release_eligible": False,
    "deployment_authority": "none",
    "credential_access": "none",
    "network_access": "none",
    "connector_access": "none",
}

SAFE_ROOTS = {
    "source_assets": "docs/design-assets/substack-public-art",
    "website_assets": "website/assets/images/research/substack",
    "redacted_evidence": "docs/research/editorial-assets",
    "rights_decisions": "docs/research/editorial-assets/rights-decisions",
}

PRIVACY_BOUNDARY = {
    "raw_correspondence": "excluded",
    "mailbox_identifiers": "excluded",
    "provider_identifiers": "excluded",
    "credential_material": "excluded",
    "private_source_registers": "excluded",
}

RIGHTS_BOUNDARY_ACKNOWLEDGEMENT = (
    "editorial-only; not evidence, validation, facilities, measured data or tested hardware"
)
RIGHTS_USAGE_SCOPE = "bound-routes-destinations-copy-and-variants-only"

REPRESENTATION_PROFILES: dict[str, tuple[str, str]] = {
    "abstract-editorial": ("low", "editorial-only-not-evidence"),
    "concept-system-not-data": (
        "elevated",
        "conceptual-system-not-measured-data-or-validated-evidence",
    ),
    "concept-lab-not-facility": (
        "high",
        "conceptual-lab-not-company-facility-measured-data-or-tested-hardware",
    ),
}

ROUTE_DESTINATIONS: dict[str, frozenset[str]] = {
    "/": frozenset({"website/index.html"}),
    "/research/": frozenset({"website/research/index.html"}),
    "/research/journal/": frozenset(
        {
            "website/research/journal/index.html",
            "website/data/substack-research-index.json",
        }
    ),
}

FILE_ROLES = frozenset({"source", "small", "large"})
RIGHTS_STATES = frozenset({"pending", "approved", "rejected"})
RIGHTS_BASES = frozenset(
    {
        "copyright-owner-authorisation",
        "documented-provider-use-rights",
        "licensed-for-bound-public-use",
    }
)
EVIDENCE_KINDS = frozenset(
    {
        "redacted-delivery-evidence",
        "redacted-local-asset-inventory",
    }
)

_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "manifest_id",
        "issued_at",
        "authority",
        "global_artwork_policy",
        "safe_roots",
        "evidence_snapshots",
        "assets",
        "unmapped_assets",
    }
)
_EVIDENCE_BINDING_FIELDS = frozenset({"kind", "path", "sha256"})
_ASSET_FIELDS = frozenset(
    {
        "asset_id",
        "public_post_url",
        "delivery_evidence",
        "source_asset",
        "variants",
        "representation",
        "placements",
        "rights_decision",
    }
)
_DELIVERY_BINDING_FIELDS = frozenset({"snapshot_id", "evidence_code", "rights_effect"})
_FILE_FIELDS = frozenset(
    {
        "path",
        "sha256",
        "media_type",
        "bytes",
        "width",
        "height",
        "frame_count",
        "animation",
        "metadata_profile",
        "metadata_sha256",
    }
)
_VARIANT_FIELDS = frozenset({"role", *_FILE_FIELDS})
_REPRESENTATION_FIELDS = frozenset({"classification", "risk", "boundary"})
_PLACEMENT_FIELDS = frozenset(
    {
        "route_scope",
        "destination_path",
        "surface_id",
        "variant_roles",
        "alt",
        "caption",
        "credit",
    }
)
_RIGHTS_FIELDS = frozenset({"state", "named_human_decision", "decision_evidence"})
_RIGHTS_BINDING_FIELDS = frozenset({"path", "sha256"})
_UNMAPPED_FIELDS = frozenset({"asset_id", "source_asset", "mapping_state", "rights_state", "reason_code"})

_DELIVERY_SNAPSHOT_FIELDS = frozenset(
    {
        "schema",
        "snapshot_id",
        "observed_at",
        "source_channel",
        "privacy",
        "rights_effect",
        "items",
    }
)
_DELIVERY_ITEM_FIELDS = frozenset(
    {
        "asset_id",
        "public_post_url",
        "source_asset_path",
        "evidence_code",
        "rights_effect",
    }
)
_INVENTORY_SNAPSHOT_FIELDS = frozenset(
    {"schema", "snapshot_id", "captured_at", "privacy", "boundary", "files"}
)
_INVENTORY_FILE_FIELDS = frozenset({"asset_id", "role", *_FILE_FIELDS})
_RIGHTS_DECISION_FIELDS = frozenset(
    {
        "schema",
        "decision_id",
        "asset_id",
        "decision",
        "decided_by",
        "decided_at",
        "rights_basis",
        "usage_scope",
        "asset_scope_sha256",
        "boundary_acknowledgement",
    }
)
_RIGHTS_PREPARATION_REQUEST_FIELDS = frozenset(
    {
        "schema",
        "asset_ids",
        "asset_scopes",
        "boundary_acknowledgement",
        "decision",
        "decided_by",
        "decided_at",
        "manifest_sha256",
        "rights_basis",
        "usage_scope",
    }
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{2,127}$")
_CANDIDATE_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,80}$")
_SHA256 = re.compile(r"^[A-F0-9]{64}$")
_SURFACE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,95}$")
_PUBLIC_POST_PATH = re.compile(r"^/p/[a-z0-9][a-z0-9-]{2,160}$")
_NAMED_HUMAN = re.compile(
    r"^[A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’-]{1,}"
    r"(?: [A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’-]{1,}){1,5}$"
)
_TRUSTED_RIGHTS_DECISION_MAKER_SHA256 = frozenset(
    {
        # SHA-256 of the normalised, case-folded owner-reviewer identity. Keep
        # the public worker capsule copy-free while preventing an arbitrary
        # syntactically human-looking name from granting candidate readiness.
        "1EBEC44F0BED2BACE30E6D599ECBF2339CA8043AA181C129F331BF927873FAD0",
    }
)
_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_TOKEN = re.compile(
    r"(?i)(?:\bBearer\s+[A-Za-z0-9._~+/-]{8,}|"
    r"\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}|"
    r"\bgh[opsu]_[A-Za-z0-9]{8,}|"
    r"\bAIza[A-Za-z0-9_-]{8,}|"
    r"\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret)"
    r"\s*[:=]\s*\S+)"
)
_PRIVATE_FIELD_NAMES = frozenset(
    {
        "attachment_id",
        "bcc",
        "cc",
        "email",
        "from",
        "mailbox_id",
        "message",
        "message_id",
        "provider_id",
        "quote",
        "raw_correspondence",
        "raw_message",
        "sender",
        "subject",
        "thread_id",
        "to",
    }
)
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_MAX_EVIDENCE_BYTES = 512 * 1024
_MAX_DESTINATION_BYTES = 4 * 1024 * 1024
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()
_HTML_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_HTML_HIDDEN_TAGS = frozenset({"script", "style", "template", "noscript"})
_MEDIA_TAGS = frozenset(
    {
        "audio",
        "embed",
        "iframe",
        "image",
        "img",
        "input",
        "link",
        "object",
        "source",
        "video",
    }
)
_MEDIA_SOURCE_ATTRIBUTES = frozenset(
    {
        "data",
        "data-src",
        "data-srcset",
        "href",
        "imagesrcset",
        "poster",
        "src",
        "srcset",
        "xlink:href",
    }
)
_JSON_MEDIA_FIELDS = frozenset(
    {
        "artwork",
        "artwork_large",
        "artwork_small",
        "image",
        "image_large",
        "image_small",
        "image_url",
        "poster",
        "src",
        "srcset",
        "thumbnail",
    }
)


class DesignEditorialAssetProvenanceError(ValueError):
    """An editorial asset declaration is unsafe, ambiguous, or out of scope."""


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
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DesignEditorialAssetProvenanceError(f"{label} is not valid UTF-8 JSON: {path}.") from exc
    if not isinstance(parsed, Mapping):
        raise DesignEditorialAssetProvenanceError(f"{label} must be one JSON object.")
    return dict(parsed)


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignEditorialAssetProvenanceError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _exact_fields(
    value: object,
    fields: frozenset[str],
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DesignEditorialAssetProvenanceError(f"{label} must be an object.")
    copied = dict(value)
    private = sorted(
        str(key) for key in copied if str(key).casefold().replace("-", "_") in _PRIVATE_FIELD_NAMES
    )
    if private:
        raise DesignEditorialAssetProvenanceError(f"{label} contains prohibited private fields: {private}.")
    if set(copied) != fields:
        missing = sorted(fields - set(copied))
        extra = sorted(set(copied) - fields)
        raise DesignEditorialAssetProvenanceError(
            f"{label} fields do not match the exact contract (missing={missing}, extra={extra})."
        )
    return copied


def _identifier(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise DesignEditorialAssetProvenanceError(f"{label} must be a controlled lower-case identifier.")
    return value


def _sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise DesignEditorialAssetProvenanceError(f"{label} must be an uppercase SHA-256.")
    return value


def _positive_int(value: object, *, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= maximum:
        raise DesignEditorialAssetProvenanceError(f"{label} must be an integer between 1 and {maximum}.")
    return value


def _parse_datetime(value: object, *, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise DesignEditorialAssetProvenanceError(f"{label} must be a non-empty ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DesignEditorialAssetProvenanceError(f"{label} must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise DesignEditorialAssetProvenanceError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _safe_text(
    value: object,
    *,
    label: str,
    minimum: int = 3,
    maximum: int = 320,
) -> str:
    if not isinstance(value, str):
        raise DesignEditorialAssetProvenanceError(f"{label} must be text.")
    text = " ".join(value.split())
    if not minimum <= len(text) <= maximum:
        raise DesignEditorialAssetProvenanceError(
            f"{label} must contain {minimum}-{maximum} normalised characters."
        )
    if _EMAIL.search(text) or _TOKEN.search(text):
        raise DesignEditorialAssetProvenanceError(
            f"{label} contains prohibited private or credential material."
        )
    if "<" in text or ">" in text:
        raise DesignEditorialAssetProvenanceError(f"{label} must be plain text without markup.")
    return text


def _controlled_named_rights_reviewer(value: object, *, label: str) -> str:
    reviewer = _safe_text(
        value,
        label=label,
        minimum=5,
        maximum=120,
    )
    if not _NAMED_HUMAN.fullmatch(reviewer):
        raise DesignEditorialAssetProvenanceError(f"{label} must name one identifiable human reviewer.")
    reviewer_sha256 = hashlib.sha256(reviewer.casefold().encode("utf-8")).hexdigest().upper()
    if reviewer_sha256 not in _TRUSTED_RIGHTS_DECISION_MAKER_SHA256:
        raise DesignEditorialAssetProvenanceError(
            f"{label} is not in the controlled owner-reviewer allowlist."
        )
    return reviewer


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DesignEditorialAssetProvenanceError(f"{label} must be a repository-relative path.")
    normalised = value.replace("\\", "/")
    candidate = Path(normalised)
    if (
        candidate.is_absolute()
        or candidate.drive
        or candidate.root
        or not candidate.parts
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise DesignEditorialAssetProvenanceError(f"{label} is unsafe.")
    return candidate.as_posix()


def _under_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _public_post_url(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise DesignEditorialAssetProvenanceError(f"{label} must be a direct public URL.")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "garyleckey.substack.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query
        or parsed.fragment
        or not _PUBLIC_POST_PATH.fullmatch(parsed.path)
        or "%" in parsed.path
    ):
        raise DesignEditorialAssetProvenanceError(
            f"{label} must be a direct credential-free public Substack post URL "
            "without query, fragment, redirect, token, or user information."
        )
    return value


def _component_has_reparse_point(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _file_safety(
    root: Path,
    relative: str,
    *,
    max_bytes: int,
) -> tuple[Path, dict[str, Any]]:
    candidate = root
    reparse = False
    for part in Path(relative).parts:
        candidate = candidate / part
        if candidate.exists() or candidate.is_symlink():
            reparse = reparse or _component_has_reparse_point(candidate)
    exists = candidate.is_file()
    inside = False
    if exists and not reparse:
        try:
            candidate.resolve().relative_to(root.resolve())
            inside = True
        except ValueError:
            inside = False
    hardlink_count = 0
    byte_count = 0
    if exists and not reparse and inside:
        try:
            file_stat = candidate.stat()
            hardlink_count = int(file_stat.st_nlink)
            byte_count = int(file_stat.st_size)
        except OSError:
            hardlink_count = 0
            byte_count = 0
    regular = exists and inside and not reparse and hardlink_count == 1 and 0 < byte_count <= max_bytes
    return candidate, {
        "available": exists,
        "inside_repository": inside,
        "reparse_free": not reparse,
        "single_link": hardlink_count == 1,
        "hardlink_count": hardlink_count,
        "bytes_within_limit": 0 < byte_count <= max_bytes,
        "regular_file": regular,
    }


def _controlled_website_projection(
    root: Path,
    website_root: Path | None,
) -> tuple[str, str]:
    """Resolve only the canonical site or one deterministic candidate site."""

    requested = website_root or (root / "website")
    if any(part in {".", ".."} for part in requested.parts):
        raise DesignEditorialAssetProvenanceError("Website projection must not contain dot-path aliases.")
    candidate = requested if requested.is_absolute() else root / requested
    lexical = Path(os.path.abspath(candidate))
    try:
        relative = lexical.relative_to(root)
    except ValueError as exc:
        raise DesignEditorialAssetProvenanceError(
            "Website projection must stay inside the Aureon repository."
        ) from exc
    parts = relative.parts
    if parts == ("website",):
        projection = "canonical"
    elif (
        len(parts) == 4
        and parts[0:2] == ("artifacts", "website-candidates")
        and _CANDIDATE_RUN_ID.fullmatch(parts[2])
        and parts[3] == "website"
    ):
        projection = "candidate"
    else:
        raise DesignEditorialAssetProvenanceError(
            "Website projection must be canonical website/ or a deterministic "
            "artifacts/website-candidates/<run-id>/website directory."
        )
    cursor = root
    for part in parts:
        cursor /= part
        if (cursor.exists() or cursor.is_symlink()) and _component_has_reparse_point(cursor):
            raise DesignEditorialAssetProvenanceError("Website projection must be reparse-free.")
    if not lexical.is_dir():
        raise DesignEditorialAssetProvenanceError("Website projection must be an existing directory.")
    return relative.as_posix(), projection


def _canonical_manifest_path(root: Path, value: Path | None) -> tuple[Path, str]:
    raw = value or DEFAULT_MANIFEST_PATH
    candidate = raw if raw.is_absolute() else root / raw
    try:
        relative = candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset manifest must remain inside the repository."
        ) from exc
    if relative != DEFAULT_MANIFEST_PATH.as_posix():
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset provenance must use the canonical "
            "data/website_operator/editorial_asset_provenance.v1.json path."
        )
    unresolved, safety = _file_safety(
        root,
        relative,
        max_bytes=_MAX_EVIDENCE_BYTES,
    )
    if not safety["regular_file"]:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset manifest must be a regular, single-link, reparse-free canonical JSON file."
        )
    return unresolved, relative


def _metadata_digest(chunks: Sequence[tuple[bytes, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in chunks:
        digest.update(name)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest().upper()


def _jpeg_probe(data: bytes) -> dict[str, Any]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise DesignEditorialAssetProvenanceError("Declared JPEG does not have JPEG magic bytes.")
    offset = 2
    width = 0
    height = 0
    metadata: list[tuple[bytes, bytes]] = []
    metadata_markers: list[str] = []
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    metadata_marker_names = {
        0xE0: "APP0",
        0xE1: "APP1",
        0xE2: "APP2",
        0xED: "APP13",
        0xEE: "APP14",
        0xFE: "COM",
    }
    while offset < len(data):
        if data[offset] != 0xFF:
            raise DesignEditorialAssetProvenanceError("JPEG segment framing is invalid.")
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0xD9}:
            continue
        if marker == 0xDA:
            break
        if marker in {0x01, *range(0xD0, 0xD8)}:
            continue
        if offset + 2 > len(data):
            raise DesignEditorialAssetProvenanceError("JPEG segment is truncated.")
        segment_length = int.from_bytes(data[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(data):
            raise DesignEditorialAssetProvenanceError("JPEG segment length is invalid.")
        payload = data[offset + 2 : offset + segment_length]
        if marker in sof_markers:
            if len(payload) < 5:
                raise DesignEditorialAssetProvenanceError("JPEG frame header is truncated.")
            height = int.from_bytes(payload[1:3], "big")
            width = int.from_bytes(payload[3:5], "big")
        if marker in metadata_marker_names:
            name = metadata_marker_names[marker].encode("ascii")
            metadata.append((name, payload))
            metadata_markers.append(metadata_marker_names[marker])
        offset += segment_length
    if not width or not height:
        raise DesignEditorialAssetProvenanceError("JPEG dimensions could not be read from its frame header.")
    disallowed_metadata = sorted(set(metadata_markers) - {"APP0", "APP1"})
    app1_payloads = [payload for name, payload in metadata if name == b"APP1"]
    technical_exif_only = (
        not disallowed_metadata
        and all(payload.startswith(b"Exif\x00\x00") for payload in app1_payloads)
        and not any(
            marker in data
            for marker in (
                b"http://",
                b"https://",
                b"mailto:",
                b"@gmail.",
                b"@outlook.",
                b"GPSLatitude",
                b"GPSLongitude",
                b"UserComment",
                b"Artist\x00",
                b"Copyright\x00",
            )
        )
    )
    return {
        "media_type": "image/jpeg",
        "width": width,
        "height": height,
        "frame_count": 1,
        "animation": "static",
        "metadata_profile": ("technical-exif-only" if technical_exif_only else "unsafe-or-unknown"),
        "metadata_sha256": _metadata_digest(metadata),
        "metadata_markers": metadata_markers,
    }


def _webp_probe(data: bytes) -> dict[str, Any]:
    if (
        len(data) < 20
        or data[:4] != b"RIFF"
        or data[8:12] != b"WEBP"
        or int.from_bytes(data[4:8], "little") + 8 != len(data)
    ):
        raise DesignEditorialAssetProvenanceError(
            "Declared WebP does not have one complete RIFF/WEBP container."
        )
    offset = 12
    chunks: list[tuple[bytes, bytes]] = []
    while offset + 8 <= len(data):
        name = data[offset : offset + 4]
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        start = offset + 8
        end = start + size
        if end > len(data):
            raise DesignEditorialAssetProvenanceError("WebP chunk is truncated.")
        chunks.append((name, data[start:end]))
        offset = end + (size % 2)
    if offset != len(data):
        raise DesignEditorialAssetProvenanceError("WebP chunk alignment is invalid.")
    names = [name for name, _ in chunks]
    width = 0
    height = 0
    animation = b"ANIM" in names or b"ANMF" in names
    for name, payload in chunks:
        if name == b"VP8X":
            if len(payload) < 10:
                raise DesignEditorialAssetProvenanceError("WebP extended header is truncated.")
            animation = animation or bool(payload[0] & 0x02)
            width = int.from_bytes(payload[4:7], "little") + 1
            height = int.from_bytes(payload[7:10], "little") + 1
            break
        if name == b"VP8 ":
            if len(payload) < 10 or payload[3:6] != b"\x9d\x01\x2a":
                raise DesignEditorialAssetProvenanceError("WebP lossy frame header is invalid.")
            width = int.from_bytes(payload[6:8], "little") & 0x3FFF
            height = int.from_bytes(payload[8:10], "little") & 0x3FFF
            break
        if name == b"VP8L":
            if len(payload) < 5 or payload[0] != 0x2F:
                raise DesignEditorialAssetProvenanceError("WebP lossless frame header is invalid.")
            bits = int.from_bytes(payload[1:5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            break
    if not width or not height:
        raise DesignEditorialAssetProvenanceError("WebP dimensions could not be read.")
    metadata = [(name, payload) for name, payload in chunks if name in {b"EXIF", b"XMP ", b"ICCP"}]
    frame_count = sum(name == b"ANMF" for name in names)
    if not frame_count:
        frame_count = 1
    return {
        "media_type": "image/webp",
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "animation": "animated" if animation else "static",
        "metadata_profile": "none" if not metadata else "embedded",
        "metadata_sha256": _metadata_digest(metadata),
        "metadata_markers": [name.decode("ascii") for name, _ in metadata],
    }


def _probe_image(path: Path, declared_media_type: str) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise DesignEditorialAssetProvenanceError(f"Could not read declared image: {path}.") from exc
    if declared_media_type == "image/jpeg":
        return _jpeg_probe(data)
    if declared_media_type == "image/webp":
        return _webp_probe(data)
    raise DesignEditorialAssetProvenanceError("Editorial assets may declare only image/jpeg or image/webp.")


def _normalise_file_record(
    value: Mapping[str, Any],
    *,
    label: str,
    role: str,
    root_prefix: str,
) -> dict[str, Any]:
    fields = _VARIANT_FIELDS if "role" in value else _FILE_FIELDS
    record = _exact_fields(value, fields, label=label)
    if "role" in record:
        declared_role = record.get("role")
        if declared_role != role or declared_role not in FILE_ROLES - {"source"}:
            raise DesignEditorialAssetProvenanceError(
                f"{label} role must be the declared small or large variant role."
            )
    path = _safe_relative_path(record.get("path"), label=f"{label} path")
    if not _under_prefix(path, root_prefix):
        raise DesignEditorialAssetProvenanceError(f"{label} path must stay under {root_prefix}.")
    media_type = record.get("media_type")
    expected_suffix = ".jpg" if role == "source" else ".webp"
    expected_media_type = "image/jpeg" if role == "source" else "image/webp"
    if Path(path).suffix.casefold() != expected_suffix or media_type != expected_media_type:
        raise DesignEditorialAssetProvenanceError(
            f"{label} extension and media type do not match its controlled role."
        )
    byte_count = _positive_int(
        record.get("bytes"),
        label=f"{label} bytes",
        maximum=_MAX_IMAGE_BYTES,
    )
    width = _positive_int(
        record.get("width"),
        label=f"{label} width",
        maximum=8192,
    )
    height = _positive_int(
        record.get("height"),
        label=f"{label} height",
        maximum=8192,
    )
    frame_count = _positive_int(
        record.get("frame_count"),
        label=f"{label} frame_count",
        maximum=1,
    )
    if record.get("animation") != "static":
        raise DesignEditorialAssetProvenanceError(f"{label} must declare a static image.")
    metadata_profile = record.get("metadata_profile")
    expected_metadata_profile = "technical-exif-only" if role == "source" else "none"
    if metadata_profile != expected_metadata_profile:
        raise DesignEditorialAssetProvenanceError(
            f"{label} must use metadata profile {expected_metadata_profile}."
        )
    metadata_sha256 = _sha256(
        record.get("metadata_sha256"),
        label=f"{label} metadata SHA-256",
    )
    if role != "source" and metadata_sha256 != _EMPTY_SHA256:
        raise DesignEditorialAssetProvenanceError(
            f"{label} WebP must contain no embedded EXIF, XMP or ICC metadata."
        )
    return {
        **({"role": role} if role != "source" else {}),
        "path": path,
        "sha256": _sha256(record.get("sha256"), label=f"{label} SHA-256"),
        "media_type": expected_media_type,
        "bytes": byte_count,
        "width": width,
        "height": height,
        "frame_count": frame_count,
        "animation": "static",
        "metadata_profile": expected_metadata_profile,
        "metadata_sha256": metadata_sha256,
    }


def _audit_file_record(
    root: Path,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    path = str(record["path"])
    candidate, safety = _file_safety(root, path, max_bytes=_MAX_IMAGE_BYTES)
    actual_sha256 = ""
    probe: dict[str, Any] = {}
    errors: list[str] = []
    if safety["regular_file"]:
        try:
            actual_sha256 = _sha256_file(candidate)
            probe = _probe_image(candidate, str(record["media_type"]))
        except DesignEditorialAssetProvenanceError as exc:
            errors.append(str(exc))
    integrity_matches = (
        safety["regular_file"]
        and actual_sha256 == record["sha256"]
        and candidate.stat().st_size == record["bytes"]
        and probe.get("media_type") == record["media_type"]
        and probe.get("width") == record["width"]
        and probe.get("height") == record["height"]
        and probe.get("frame_count") == record["frame_count"]
        and probe.get("animation") == record["animation"]
        and probe.get("metadata_profile") == record["metadata_profile"]
        and probe.get("metadata_sha256") == record["metadata_sha256"]
    )
    if probe.get("animation") == "animated":
        errors.append("Animated WebP content is prohibited.")
    if probe.get("metadata_profile") == "embedded":
        errors.append("WebP EXIF, XMP and ICC metadata are prohibited.")
    return {
        "path": path,
        "sha256": record["sha256"],
        "media_type": record["media_type"],
        "bytes": record["bytes"],
        "width": record["width"],
        "height": record["height"],
        "frame_count": record["frame_count"],
        "animation": record["animation"],
        "metadata_profile": record["metadata_profile"],
        "metadata_sha256": record["metadata_sha256"],
        **safety,
        "hash_matches": bool(actual_sha256 and actual_sha256 == record["sha256"]),
        "magic_mime_matches": bool(probe and probe.get("media_type") == record["media_type"]),
        "dimensions_match": bool(
            probe and probe.get("width") == record["width"] and probe.get("height") == record["height"]
        ),
        "static_single_frame": bool(
            probe and probe.get("animation") == "static" and probe.get("frame_count") == 1
        ),
        "metadata_matches": bool(
            probe
            and probe.get("metadata_profile") == record["metadata_profile"]
            and probe.get("metadata_sha256") == record["metadata_sha256"]
        ),
        "integrity_matches": bool(integrity_matches),
        "errors": errors,
    }


def _normalise_representation(value: object) -> dict[str, str]:
    raw = _exact_fields(
        value,
        _REPRESENTATION_FIELDS,
        label="Asset representation safety",
    )
    classification = raw.get("classification")
    if not isinstance(classification, str) or classification not in REPRESENTATION_PROFILES:
        raise DesignEditorialAssetProvenanceError(
            "Representation classification is outside the controlled taxonomy."
        )
    expected_risk, expected_boundary = REPRESENTATION_PROFILES[classification]
    if raw.get("risk") != expected_risk or raw.get("boundary") != expected_boundary:
        raise DesignEditorialAssetProvenanceError(
            "Representation risk and boundary must match the controlled class."
        )
    return {
        "classification": classification,
        "risk": expected_risk,
        "boundary": expected_boundary,
    }


def _copy_is_representationally_safe(
    representation: Mapping[str, str],
    *,
    alt: str,
    caption: str,
) -> bool:
    classification = representation["classification"]
    alt_lower = alt.casefold()
    caption_lower = caption.casefold()
    if not any(word in alt_lower for word in ("editorial", "concept")):
        return False
    if not any(word in caption_lower for word in ("editorial", "concept")):
        return False
    if classification == "abstract-editorial":
        return "not" in caption_lower and any(
            word in caption_lower for word in ("evidence", "data", "measurement")
        )
    if classification == "concept-system-not-data":
        return all(
            "not" in text and any(word in text for word in ("data", "evidence", "measurement"))
            for text in (alt_lower, caption_lower)
        )
    if classification == "concept-lab-not-facility":
        return all(
            "not" in text
            and any(word in text for word in ("facility", "facilities"))
            and any(word in text for word in ("data", "hardware", "evidence"))
            for text in (alt_lower, caption_lower)
        )
    return False


def _normalise_placement(
    value: Mapping[str, Any],
    *,
    variant_roles: set[str],
    representation: Mapping[str, str],
) -> dict[str, Any]:
    raw = _exact_fields(value, _PLACEMENT_FIELDS, label="Asset placement")
    route_scope = raw.get("route_scope")
    if not isinstance(route_scope, str) or route_scope not in ROUTE_DESTINATIONS:
        raise DesignEditorialAssetProvenanceError(
            "Asset placement route is outside the controlled public routes."
        )
    destination_path = _safe_relative_path(
        raw.get("destination_path"),
        label="Asset placement destination path",
    )
    if destination_path not in ROUTE_DESTINATIONS[route_scope]:
        raise DesignEditorialAssetProvenanceError(
            "Asset placement destination is not valid for its exact public route."
        )
    surface_id = raw.get("surface_id")
    if not isinstance(surface_id, str) or not _SURFACE_ID.fullmatch(surface_id):
        raise DesignEditorialAssetProvenanceError(
            "Asset placement surface_id must be a controlled identifier."
        )
    raw_roles = raw.get("variant_roles")
    if (
        not isinstance(raw_roles, list)
        or not raw_roles
        or not all(isinstance(role, str) for role in raw_roles)
        or len(raw_roles) != len(set(raw_roles))
        or set(raw_roles) != {"small", "large"}
        or set(raw_roles) != variant_roles
    ):
        raise DesignEditorialAssetProvenanceError(
            "Asset placement must bind exactly one small and one large variant."
        )
    alt = _safe_text(raw.get("alt"), label="Asset placement alt", maximum=220)
    caption = _safe_text(
        raw.get("caption"),
        label="Asset placement caption",
        maximum=260,
    )
    credit = _safe_text(
        raw.get("credit"),
        label="Asset placement credit",
        maximum=220,
    )
    if not _copy_is_representationally_safe(
        representation,
        alt=alt,
        caption=caption,
    ):
        raise DesignEditorialAssetProvenanceError(
            "Alt and caption do not state the controlled non-evidence, "
            "non-data, or non-facility boundary required by this "
            "representational-safety class."
        )
    return {
        "route_scope": route_scope,
        "destination_path": destination_path,
        "surface_id": surface_id,
        "variant_roles": sorted(raw_roles),
        "alt": alt,
        "caption": caption,
        "credit": credit,
    }


def _normalise_rights(value: object) -> dict[str, Any]:
    raw = _exact_fields(value, _RIGHTS_FIELDS, label="Asset rights decision")
    state_value = raw.get("state")
    named = raw.get("named_human_decision")
    evidence = raw.get("decision_evidence")
    if state_value not in RIGHTS_STATES:
        raise DesignEditorialAssetProvenanceError("Rights decision state is outside the controlled taxonomy.")
    if state_value == "pending":
        if named is not False or evidence is not None:
            raise DesignEditorialAssetProvenanceError(
                "Pending rights state must record no named human decision and no decision evidence."
            )
        return {
            "state": "pending",
            "named_human_decision": False,
            "decision_evidence": None,
        }
    if named is not True:
        raise DesignEditorialAssetProvenanceError(
            "Approved or rejected rights state requires a named human decision."
        )
    binding = _exact_fields(
        evidence,
        _RIGHTS_BINDING_FIELDS,
        label="Human rights decision evidence",
    )
    path = _safe_relative_path(
        binding.get("path"),
        label="Human rights decision evidence path",
    )
    if not _under_prefix(path, SAFE_ROOTS["rights_decisions"]):
        raise DesignEditorialAssetProvenanceError(
            "Human rights decisions must remain in the controlled redacted rights-decisions root."
        )
    if Path(path).suffix.casefold() != ".json":
        raise DesignEditorialAssetProvenanceError("Human rights decision evidence must be JSON.")
    return {
        "state": state_value,
        "named_human_decision": True,
        "decision_evidence": {
            "path": path,
            "sha256": _sha256(
                binding.get("sha256"),
                label="Human rights decision evidence SHA-256",
            ),
        },
    }


def _normalise_asset(value: Mapping[str, Any]) -> dict[str, Any]:
    raw = _exact_fields(value, _ASSET_FIELDS, label="Editorial asset")
    asset_id = _identifier(raw.get("asset_id"), label="Editorial asset id")
    public_post_url = _public_post_url(
        raw.get("public_post_url"),
        label=f"{asset_id} public post URL",
    )
    delivery = _exact_fields(
        raw.get("delivery_evidence"),
        _DELIVERY_BINDING_FIELDS,
        label=f"{asset_id} delivery evidence",
    )
    snapshot_id = _identifier(
        delivery.get("snapshot_id"),
        label=f"{asset_id} delivery snapshot id",
    )
    if (
        delivery.get("evidence_code") != "shareable-assets-message-observed"
        or delivery.get("rights_effect") != "none"
    ):
        raise DesignEditorialAssetProvenanceError(
            "Substack shareable-assets messages are delivery/provenance evidence "
            "only and must retain rights_effect=none."
        )
    source_asset = _normalise_file_record(
        _exact_fields(
            raw.get("source_asset"),
            _FILE_FIELDS,
            label=f"{asset_id} source asset",
        ),
        label=f"{asset_id} source asset",
        role="source",
        root_prefix=SAFE_ROOTS["source_assets"],
    )
    raw_variants = raw.get("variants")
    if (
        not isinstance(raw_variants, Sequence)
        or isinstance(raw_variants, (str, bytes))
        or len(raw_variants) != 2
    ):
        raise DesignEditorialAssetProvenanceError(
            f"{asset_id} must declare exactly one small and one large WebP variant."
        )
    variants: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for item in raw_variants:
        if not isinstance(item, Mapping):
            raise DesignEditorialAssetProvenanceError(f"{asset_id} variants must be objects.")
        role_value = item.get("role")
        if role_value not in {"small", "large"}:
            raise DesignEditorialAssetProvenanceError(f"{asset_id} variant role must be small or large.")
        role = str(role_value)
        if role in seen_roles:
            raise DesignEditorialAssetProvenanceError(f"{asset_id} variant roles must be unique.")
        seen_roles.add(role)
        variants.append(
            _normalise_file_record(
                item,
                label=f"{asset_id} {role} variant",
                role=role,
                root_prefix=SAFE_ROOTS["website_assets"],
            )
        )
    if seen_roles != {"small", "large"}:
        raise DesignEditorialAssetProvenanceError(f"{asset_id} must bind both small and large variants.")
    variants.sort(key=lambda item: str(item["role"]))
    variant_by_role = {str(item["role"]): item for item in variants}
    if (
        variant_by_role["small"]["width"] != 720
        or variant_by_role["small"]["height"] != 405
        or variant_by_role["large"]["width"] != 1200
        or variant_by_role["large"]["height"] != 675
        or source_asset["width"] != 1200
        or source_asset["height"] != 675
    ):
        raise DesignEditorialAssetProvenanceError(
            f"{asset_id} must retain exact 16:9 source, 720x405, and 1200x675 dimensions."
        )
    representation = _normalise_representation(raw.get("representation"))
    raw_placements = raw.get("placements")
    if (
        not isinstance(raw_placements, Sequence)
        or isinstance(raw_placements, (str, bytes))
        or not raw_placements
    ):
        raise DesignEditorialAssetProvenanceError(f"{asset_id} must declare at least one exact placement.")
    placements: list[dict[str, Any]] = []
    seen_placements: set[tuple[str, str, str]] = set()
    for item in raw_placements:
        if not isinstance(item, Mapping):
            raise DesignEditorialAssetProvenanceError(f"{asset_id} placements must be objects.")
        placement = _normalise_placement(
            item,
            variant_roles=seen_roles,
            representation=representation,
        )
        key = (
            str(placement["route_scope"]),
            str(placement["destination_path"]),
            str(placement["surface_id"]),
        )
        if key in seen_placements:
            raise DesignEditorialAssetProvenanceError(f"{asset_id} placement bindings must be unique.")
        seen_placements.add(key)
        placements.append(placement)
    placements.sort(
        key=lambda item: (
            str(item["route_scope"]),
            str(item["destination_path"]),
            str(item["surface_id"]),
        )
    )
    return {
        "asset_id": asset_id,
        "public_post_url": public_post_url,
        "delivery_evidence": {
            "snapshot_id": snapshot_id,
            "evidence_code": "shareable-assets-message-observed",
            "rights_effect": "none",
        },
        "source_asset": source_asset,
        "variants": variants,
        "representation": representation,
        "placements": placements,
        "rights_decision": _normalise_rights(raw.get("rights_decision")),
    }


def asset_scope_sha256(asset: Mapping[str, Any]) -> str:
    """Hash every asset field controlled by a human rights decision.

    The rights object itself is excluded so a decision can bind the immutable
    asset, variant, representation, route, destination and copy scope.
    """

    raw = _exact_fields(asset, _ASSET_FIELDS, label="Editorial asset scope")
    normalised = _normalise_asset(raw)
    payload = {key: value for key, value in normalised.items() if key != "rights_decision"}
    return _json_sha256(payload)


def _public_file_audit(
    value: Mapping[str, Any],
    *,
    include_path: bool,
) -> dict[str, Any]:
    """Retain integrity evidence without leaking private source locations."""

    fields = (
        "sha256",
        "media_type",
        "bytes",
        "width",
        "height",
        "frame_count",
        "animation",
        "metadata_profile",
        "metadata_sha256",
        "available",
        "inside_repository",
        "regular_file",
        "reparse_free",
        "single_link",
        "hardlink_count",
        "bytes_within_limit",
        "hash_matches",
        "magic_mime_matches",
        "dimensions_match",
        "static_single_frame",
        "metadata_matches",
        "integrity_matches",
        "errors",
    )
    public = {field: value.get(field) for field in fields}
    if include_path:
        public["path"] = value.get("path")
    if "role" in value:
        public["role"] = value.get("role")
    return public


def _public_evidence_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    """Expose snapshot integrity and counts, never the local snapshot path."""

    allowed = (
        "kind",
        "schema",
        "snapshot_id",
        "sha256",
        "privacy_safe",
        "available",
        "inside_repository",
        "regular_file",
        "reparse_free",
        "single_link",
        "hardlink_count",
        "bytes_within_limit",
        "hash_matches",
        "item_count",
        "file_count",
        "rights_effect",
    )
    return {field: value.get(field) for field in allowed if field in value}


def _public_rights_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    """Expose controlled state and closure only, never people or evidence paths."""

    return {
        "state": value.get("state"),
        "named_human_decision": value.get("named_human_decision") is True,
        "decision_valid": value.get("decision_valid") is True,
        "asset_scope_sha256": value.get("asset_scope_sha256"),
        "rights_basis": value.get("rights_basis"),
    }


def _public_asset_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": value["asset_id"],
        "public_post_url": value["public_post_url"],
        "delivery_evidence": {
            "evidence_code": value["delivery_evidence"]["evidence_code"],
            "rights_effect": value["delivery_evidence"]["rights_effect"],
            "binding_matches": value["delivery_evidence"]["binding_matches"],
        },
        "source_asset": _public_file_audit(
            value["source_asset"],
            include_path=False,
        ),
        "variants": [_public_file_audit(item, include_path=True) for item in value["variants"]],
        "representation": dict(value["representation"]),
        "placements": [dict(item) for item in value["placements"]],
        "surface_binding": dict(value["surface_binding"]),
        "rights": _public_rights_summary(value["rights"]),
        "current_reference_routes": list(value["current_reference_routes"]),
        "current_use_authorised": value["current_use_authorised"] is True,
        "candidate_use_ready": value["candidate_use_ready"] is True,
        "blocking_codes": list(value["blocking_codes"]),
    }


def _worker_capsule_from(
    asset: Mapping[str, Any],
    audit_asset: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one deterministic public-safe capsule from an approved exact scope."""

    if audit_asset.get("candidate_use_ready") is not True:
        raise DesignEditorialAssetProvenanceError(
            f"Editorial asset {asset.get('asset_id')} is not candidate-use-ready."
        )
    raw_decision = audit_asset.get("rights")
    if not isinstance(raw_decision, Mapping):
        raise DesignEditorialAssetProvenanceError("Candidate-ready asset lost its audited rights summary.")
    decision = _public_rights_summary(raw_decision)
    capsule: dict[str, Any] = {
        "schema": WORKER_CAPSULE_SCHEMA,
        "asset_id": asset["asset_id"],
        "public_post_url": asset["public_post_url"],
        "website_variants": [
            {
                "role": item["role"],
                "path": item["path"],
                "sha256": item["sha256"],
                "media_type": item["media_type"],
                "bytes": item["bytes"],
                "width": item["width"],
                "height": item["height"],
                "animation": item["animation"],
                "metadata_profile": item["metadata_profile"],
            }
            for item in asset["variants"]
        ],
        "representation": dict(asset["representation"]),
        "placements": [dict(item) for item in asset["placements"]],
        "rights": {
            "state": "approved",
            "asset_scope_sha256": decision["asset_scope_sha256"],
            "usage_scope": RIGHTS_USAGE_SCOPE,
        },
        "authority": {
            "source_content_available": False,
            "source_paths_available": False,
            "rights_evidence_available": False,
            "raw_correspondence_access": "none",
            "source_register_access": "none",
            "website_mutation": "staged worker patch only",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
        },
    }
    capsule["asset_capsule_sha256"] = _json_sha256(capsule)
    return capsule


def _validate_rights_decision(
    root: Path,
    rights: Mapping[str, Any],
    *,
    asset_id: str,
    asset_scope: str,
    reviewed_at: datetime,
) -> dict[str, Any]:
    state_value = str(rights["state"])
    if state_value == "pending":
        return {
            "state": "pending",
            "named_human_decision": False,
            "decision_valid": False,
            "decision_id": None,
            "rights_basis": None,
            "asset_scope_sha256": asset_scope,
        }
    binding = rights["decision_evidence"]
    if not isinstance(binding, Mapping):
        raise DesignEditorialAssetProvenanceError(
            "Non-pending rights state requires one exact decision binding."
        )
    path = str(binding["path"])
    candidate, safety = _file_safety(root, path, max_bytes=_MAX_EVIDENCE_BYTES)
    valid = bool(safety["regular_file"])
    decision_id: str | None = None
    rights_basis: str | None = None
    if valid:
        valid = _sha256_file(candidate) == binding["sha256"]
    decision: dict[str, Any] = {}
    if valid:
        decision = _exact_fields(
            _read_json(candidate, label="Human rights decision"),
            _RIGHTS_DECISION_FIELDS,
            label="Human rights decision",
        )
        if decision.get("schema") != RIGHTS_DECISION_SCHEMA:
            raise DesignEditorialAssetProvenanceError(
                f"Human rights decision schema must be {RIGHTS_DECISION_SCHEMA}."
            )
        decision_id = _identifier(
            decision.get("decision_id"),
            label="Human rights decision id",
        )
        decision_asset_id = _identifier(
            decision.get("asset_id"),
            label="Human rights decision asset id",
        )
        decision_value = decision.get("decision")
        if decision_value not in {"approved", "rejected"}:
            raise DesignEditorialAssetProvenanceError("Human rights decision must be approved or rejected.")
        _controlled_named_rights_reviewer(
            decision.get("decided_by"),
            label="Human rights decision maker",
        )
        decided_at = _parse_datetime(
            decision.get("decided_at"),
            label="Human rights decision decided_at",
        )
        if decided_at > reviewed_at:
            raise DesignEditorialAssetProvenanceError("Human rights decision cannot be future-dated.")
        rights_basis_value = decision.get("rights_basis")
        if rights_basis_value not in RIGHTS_BASES:
            raise DesignEditorialAssetProvenanceError(
                "Human rights decision must name a controlled rights basis."
            )
        rights_basis = str(rights_basis_value)
        if decision.get("usage_scope") != RIGHTS_USAGE_SCOPE:
            raise DesignEditorialAssetProvenanceError(
                "Human rights decision must remain bound to exact routes, destinations, copy, and variants."
            )
        if (
            _sha256(
                decision.get("asset_scope_sha256"),
                label="Human rights decision asset scope SHA-256",
            )
            != asset_scope
        ):
            raise DesignEditorialAssetProvenanceError(
                "Human rights decision has drifted from the exact asset scope."
            )
        if decision.get("boundary_acknowledgement") != RIGHTS_BOUNDARY_ACKNOWLEDGEMENT:
            raise DesignEditorialAssetProvenanceError(
                "Human rights decision must acknowledge the representation boundary."
            )
        valid = (
            decision_asset_id == asset_id
            and decision_value == state_value
            and rights["named_human_decision"] is True
        )
    return {
        "state": state_value,
        "named_human_decision": rights["named_human_decision"],
        "decision_valid": bool(valid),
        "decision_id": decision_id if valid else None,
        "rights_basis": rights_basis if valid else None,
        "asset_scope_sha256": asset_scope,
    }


def _normalise_inventory_file(value: Mapping[str, Any]) -> dict[str, Any]:
    raw = _exact_fields(
        value,
        _INVENTORY_FILE_FIELDS,
        label="Redacted inventory file",
    )
    asset_id = _identifier(raw.get("asset_id"), label="Inventory asset id")
    role_value = raw.get("role")
    if role_value not in FILE_ROLES:
        raise DesignEditorialAssetProvenanceError("Inventory file role is outside the controlled taxonomy.")
    role = str(role_value)
    root_prefix = SAFE_ROOTS["source_assets"] if role == "source" else SAFE_ROOTS["website_assets"]
    file_value = {key: item for key, item in raw.items() if key not in {"asset_id", "role"}}
    return {
        "asset_id": asset_id,
        "role": role,
        **_normalise_file_record(
            file_value,
            label=f"Inventory {asset_id} {role}",
            role=role,
            root_prefix=root_prefix,
        ),
    }


def _validate_delivery_snapshot(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    raw = _exact_fields(
        value,
        _DELIVERY_SNAPSHOT_FIELDS,
        label="Redacted delivery evidence snapshot",
    )
    if raw.get("schema") != DELIVERY_SNAPSHOT_SCHEMA:
        raise DesignEditorialAssetProvenanceError(
            f"Delivery snapshot schema must be {DELIVERY_SNAPSHOT_SCHEMA}."
        )
    snapshot_id = _identifier(
        raw.get("snapshot_id"),
        label="Delivery snapshot id",
    )
    _parse_datetime(raw.get("observed_at"), label="Delivery snapshot observed_at")
    if raw.get("source_channel") != "substack-shareable-assets-email":
        raise DesignEditorialAssetProvenanceError(
            "Delivery snapshot must use the controlled redacted source-channel code."
        )
    if raw.get("privacy") != PRIVACY_BOUNDARY:
        raise DesignEditorialAssetProvenanceError(
            "Delivery snapshot must exclude correspondence, identifiers, "
            "credentials, and private source registers."
        )
    if raw.get("rights_effect") != "none":
        raise DesignEditorialAssetProvenanceError("Delivery evidence must retain rights_effect=none.")
    items_value = raw.get("items")
    if not isinstance(items_value, Sequence) or isinstance(items_value, (str, bytes)) or not items_value:
        raise DesignEditorialAssetProvenanceError("Delivery snapshot must contain redacted per-asset items.")
    items: dict[str, dict[str, Any]] = {}
    for item_value in items_value:
        item = _exact_fields(
            item_value,
            _DELIVERY_ITEM_FIELDS,
            label="Redacted delivery evidence item",
        )
        asset_id = _identifier(item.get("asset_id"), label="Delivery item asset id")
        if asset_id in items:
            raise DesignEditorialAssetProvenanceError("Delivery evidence asset ids must be unique.")
        post_url = _public_post_url(
            item.get("public_post_url"),
            label=f"{asset_id} delivery public post URL",
        )
        source_path = _safe_relative_path(
            item.get("source_asset_path"),
            label=f"{asset_id} delivery source asset path",
        )
        if not _under_prefix(source_path, SAFE_ROOTS["source_assets"]):
            raise DesignEditorialAssetProvenanceError(
                "Delivery source asset path must remain under the safe source root."
            )
        if (
            item.get("evidence_code") != "shareable-assets-message-observed"
            or item.get("rights_effect") != "none"
        ):
            raise DesignEditorialAssetProvenanceError(
                "Shareable-assets messages establish delivery only, not rights."
            )
        items[asset_id] = {
            "asset_id": asset_id,
            "public_post_url": post_url,
            "source_asset_path": source_path,
            "evidence_code": "shareable-assets-message-observed",
            "rights_effect": "none",
        }
    return (
        {
            "schema": DELIVERY_SNAPSHOT_SCHEMA,
            "snapshot_id": snapshot_id,
            "rights_effect": "none",
            "item_count": len(items),
        },
        items,
    )


def _validate_inventory_snapshot(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    raw = _exact_fields(
        value,
        _INVENTORY_SNAPSHOT_FIELDS,
        label="Redacted local asset inventory snapshot",
    )
    if raw.get("schema") != INVENTORY_SNAPSHOT_SCHEMA:
        raise DesignEditorialAssetProvenanceError(
            f"Inventory snapshot schema must be {INVENTORY_SNAPSHOT_SCHEMA}."
        )
    snapshot_id = _identifier(
        raw.get("snapshot_id"),
        label="Inventory snapshot id",
    )
    _parse_datetime(raw.get("captured_at"), label="Inventory snapshot captured_at")
    if raw.get("privacy") != PRIVACY_BOUNDARY:
        raise DesignEditorialAssetProvenanceError(
            "Inventory snapshot must exclude private source registers and identifiers."
        )
    if raw.get("boundary") != "local bytes and mappings only; no rights, publication or deployment authority":
        raise DesignEditorialAssetProvenanceError(
            "Inventory snapshot must retain its non-authoritative boundary."
        )
    files_value = raw.get("files")
    if not isinstance(files_value, Sequence) or isinstance(files_value, (str, bytes)) or not files_value:
        raise DesignEditorialAssetProvenanceError("Inventory snapshot must contain exact local file records.")
    files: dict[tuple[str, str], dict[str, Any]] = {}
    for file_value in files_value:
        if not isinstance(file_value, Mapping):
            raise DesignEditorialAssetProvenanceError("Inventory snapshot files must be objects.")
        item = _normalise_inventory_file(file_value)
        key = (str(item["asset_id"]), str(item["role"]))
        if key in files:
            raise DesignEditorialAssetProvenanceError("Inventory asset/role bindings must be unique.")
        files[key] = item
    return (
        {
            "schema": INVENTORY_SNAPSHOT_SCHEMA,
            "snapshot_id": snapshot_id,
            "file_count": len(files),
        },
        files,
    )


def _load_evidence_snapshots(
    root: Path,
    values: object,
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[tuple[str, str], dict[str, Any]],
    bool,
]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != 2:
        raise DesignEditorialAssetProvenanceError(
            "Manifest must bind exactly the redacted delivery and local inventory snapshots."
        )
    summaries: list[dict[str, Any]] = []
    delivery_items: dict[str, dict[str, Any]] = {}
    inventory_files: dict[tuple[str, str], dict[str, Any]] = {}
    seen_kinds: set[str] = set()
    all_safe = True
    for value in values:
        binding = _exact_fields(
            value,
            _EVIDENCE_BINDING_FIELDS,
            label="Editorial evidence snapshot binding",
        )
        kind_value = binding.get("kind")
        if kind_value not in EVIDENCE_KINDS or kind_value in seen_kinds:
            raise DesignEditorialAssetProvenanceError(
                "Evidence snapshots must bind each controlled kind exactly once."
            )
        kind = str(kind_value)
        seen_kinds.add(kind)
        path = _safe_relative_path(
            binding.get("path"),
            label=f"{kind} snapshot path",
        )
        if (
            not _under_prefix(path, SAFE_ROOTS["redacted_evidence"])
            or _under_prefix(path, SAFE_ROOTS["rights_decisions"])
            or Path(path).suffix.casefold() != ".json"
        ):
            raise DesignEditorialAssetProvenanceError(
                "Redacted evidence snapshots must be JSON directly under the "
                "controlled editorial-assets evidence root."
            )
        expected_sha256 = _sha256(
            binding.get("sha256"),
            label=f"{kind} snapshot SHA-256",
        )
        candidate, safety = _file_safety(
            root,
            path,
            max_bytes=_MAX_EVIDENCE_BYTES,
        )
        hash_matches = bool(safety["regular_file"] and _sha256_file(candidate) == expected_sha256)
        snapshot_safe = bool(safety["regular_file"] and hash_matches)
        snapshot_summary: dict[str, Any] = {
            "kind": kind,
            "path": path,
            "sha256": expected_sha256,
            **safety,
            "hash_matches": hash_matches,
            "privacy_safe": False,
        }
        if snapshot_safe:
            parsed = _read_json(candidate, label=f"{kind} snapshot")
            if kind == "redacted-delivery-evidence":
                safe_summary, delivery_items = _validate_delivery_snapshot(parsed)
            else:
                safe_summary, inventory_files = _validate_inventory_snapshot(parsed)
            snapshot_summary.update(safe_summary)
            snapshot_summary["privacy_safe"] = True
        all_safe = all_safe and snapshot_safe and snapshot_summary["privacy_safe"]
        summaries.append(snapshot_summary)
    if seen_kinds != EVIDENCE_KINDS:
        raise DesignEditorialAssetProvenanceError("Manifest evidence snapshot kinds are incomplete.")
    summaries.sort(key=lambda item: str(item["kind"]))
    return summaries, delivery_items, inventory_files, all_safe


def _inventory_record_for(
    inventory: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    asset_id: str,
    role: str,
) -> Mapping[str, Any] | None:
    return inventory.get((asset_id, role))


def _file_record_matches_inventory(
    file_record: Mapping[str, Any],
    inventory_record: Mapping[str, Any] | None,
) -> bool:
    if inventory_record is None:
        return False
    inventory_file = {
        key: value for key, value in inventory_record.items() if key not in {"asset_id", "role"}
    }
    candidate_file = {key: value for key, value in file_record.items() if key != "role"}
    return inventory_file == candidate_file


class _HTMLNode:
    """Minimal ordered HTML node used for structural surface verification."""

    def __init__(self, tag: str, attributes: Mapping[str, str]) -> None:
        self.tag = tag
        self.attributes = dict(attributes)
        self.parts: list[str | _HTMLNode] = []


class _SurfaceHTMLParser(HTMLParser):
    """Build a small fail-closed tree without browser or network behavior."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _HTMLNode("__root__", {})
        self.stack = [self.root]
        self.errors: list[str] = []
        self.node_count = 0

    def _append_node(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
        *,
        push: bool,
    ) -> None:
        normalised: dict[str, str] = {}
        for raw_name, raw_value in attributes:
            name = raw_name.casefold()
            if name in normalised:
                self.errors.append("duplicate-html-attribute")
            normalised[name] = "" if raw_value is None else raw_value
        node = _HTMLNode(tag.casefold(), normalised)
        self.stack[-1].parts.append(node)
        self.node_count += 1
        if self.node_count > 50_000:
            raise DesignEditorialAssetProvenanceError(
                "Editorial destination contains too many HTML elements."
            )
        if push and node.tag not in _HTML_VOID_TAGS:
            self.stack.append(node)

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self._append_node(tag, attrs, push=True)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self._append_node(tag, attrs, push=False)

    def handle_endtag(self, tag: str) -> None:
        normalised = tag.casefold()
        if normalised in _HTML_VOID_TAGS:
            self.errors.append("closed-html-void-element")
            return
        if len(self.stack) == 1:
            self.errors.append("unmatched-html-end-tag")
            return
        if self.stack[-1].tag == normalised:
            self.stack.pop()
            return
        self.errors.append("mismatched-html-end-tag")
        matching_index = next(
            (index for index in range(len(self.stack) - 2, 0, -1) if self.stack[index].tag == normalised),
            None,
        )
        if matching_index is not None:
            del self.stack[matching_index:]

    def handle_data(self, data: str) -> None:
        self.stack[-1].parts.append(data)

    def close(self) -> None:
        super().close()
        if len(self.stack) != 1:
            self.errors.append("unclosed-html-element")


def _walk_html(node: _HTMLNode) -> list[_HTMLNode]:
    nodes: list[_HTMLNode] = []
    pending = [part for part in reversed(node.parts) if isinstance(part, _HTMLNode)]
    while pending:
        current = pending.pop()
        nodes.append(current)
        pending.extend(part for part in reversed(current.parts) if isinstance(part, _HTMLNode))
    return nodes


def _html_node_hidden(node: _HTMLNode) -> bool:
    if node.tag in _HTML_HIDDEN_TAGS:
        return True
    # Browser-native containers can suppress an otherwise exact source
    # surface without using CSS.  Treat a closed dialog and an inert subtree
    # as unavailable so source-level replay cannot certify hidden artwork.
    if node.tag == "dialog" and "open" not in node.attributes:
        return True
    if "inert" in node.attributes:
        return True
    if "hidden" in node.attributes:
        return True
    if node.attributes.get("aria-hidden", "").casefold() == "true":
        return True
    style = re.sub(r"\s+", "", node.attributes.get("style", "").casefold())
    return any(
        declaration in style
        for declaration in (
            "display:none",
            "visibility:hidden",
            "content-visibility:hidden",
        )
    )


def _visible_html_text(node: _HTMLNode, *, ancestor_hidden: bool = False) -> str:
    hidden = ancestor_hidden or _html_node_hidden(node)
    if hidden:
        return ""
    fragments: list[str] = []
    for part in node.parts:
        if isinstance(part, str):
            fragments.append(part)
        else:
            fragments.append(_visible_html_text(part))
    return re.sub(r"\s+", " ", "".join(fragments)).strip()


def _hidden_html_node_ids(root: _HTMLNode) -> set[int]:
    hidden_ids: set[int] = set()
    pending: list[tuple[_HTMLNode, bool]] = [(root, False)]
    while pending:
        node, ancestor_hidden = pending.pop()
        hidden = ancestor_hidden or _html_node_hidden(node)
        if hidden:
            hidden_ids.add(id(node))
        children = [part for part in node.parts if isinstance(part, _HTMLNode)]
        # In a closed details element only its first direct summary remains
        # rendered.  Every other direct child and descendant belongs to the
        # collapsed content and must not satisfy an editorial surface.
        visible_summary: _HTMLNode | None = None
        if node.tag == "details" and "open" not in node.attributes:
            visible_summary = next(
                (child for child in children if child.tag == "summary"),
                None,
            )
        pending.extend(
            (
                child,
                hidden
                or (node.tag == "details" and "open" not in node.attributes and child is not visible_summary),
            )
            for child in reversed(children)
        )
    return hidden_ids


def _canonical_media_reference(
    raw_value: str,
    *,
    destination_path: str,
    json_root_relative: bool,
) -> tuple[str | None, str | None]:
    value = raw_value.strip()
    if not value or value != raw_value:
        return None, "noncanonical-media-source"
    if any(ord(character) < 32 for character in value):
        return None, "noncanonical-media-source"
    if "\\" in value or "%" in value:
        return None, "aliased-media-source"
    split = urlsplit(value)
    scheme = split.scheme.casefold()
    if scheme in {"blob", "data"}:
        return None, "nonlocal-media-source"
    if scheme or split.netloc or value.startswith("//"):
        return None, "remote-media-source"
    if split.query or split.fragment:
        return None, "decorated-media-source"
    path = split.path
    if not path:
        return None, "noncanonical-media-source"
    if path.startswith("/"):
        candidate = f"website/{path.lstrip('/')}"
    elif json_root_relative and path.startswith("assets/"):
        candidate = f"website/{path}"
    else:
        candidate = posixpath.join(posixpath.dirname(destination_path), path)
    normalised = posixpath.normpath(candidate)
    if normalised == "website" or not normalised.startswith("website/"):
        return None, "media-path-escape"
    return normalised, None


def _exact_variant_reference(
    variant_path: str,
    *,
    destination_path: str,
    json_root_relative: bool,
) -> str:
    if json_root_relative:
        prefix = "website/"
        if not variant_path.startswith(prefix):
            raise DesignEditorialAssetProvenanceError(
                "Editorial website variant escaped the controlled website root."
            )
        return variant_path.removeprefix(prefix)
    return posixpath.relpath(
        variant_path,
        posixpath.dirname(destination_path),
    )


def _srcset_entries(value: str) -> tuple[list[tuple[str, str | None]], list[str]]:
    if value.casefold().startswith(("data:", "blob:")):
        return [(value, None)], []
    entries: list[tuple[str, str | None]] = []
    errors: list[str] = []
    for candidate in value.split(","):
        fields = candidate.strip().split()
        if not fields or len(fields) > 2:
            errors.append("invalid-srcset")
            continue
        descriptor = fields[1] if len(fields) == 2 else None
        if descriptor is not None and not re.fullmatch(
            r"(?:[1-9][0-9]*w|[1-9][0-9]*(?:\.[0-9]+)?x)",
            descriptor,
        ):
            errors.append("invalid-srcset")
        entries.append((fields[0], descriptor))
    if not entries:
        errors.append("invalid-srcset")
    return entries, errors


def _html_media_occurrences(
    root: _HTMLNode,
    *,
    destination_path: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    occurrences: list[dict[str, Any]] = []
    errors: list[str] = []
    for node in _walk_html(root):
        style = node.attributes.get("style", "")
        if "url(" in style.casefold():
            occurrences.append(
                {
                    "node": node,
                    "tag": node.tag,
                    "attribute": "style",
                    "raw": style,
                    "canonical": None,
                    "descriptor": None,
                    "error": "inline-style-media-source-not-allowed",
                }
            )
        if node.tag not in _MEDIA_TAGS:
            continue
        for attribute, value in node.attributes.items():
            if attribute not in _MEDIA_SOURCE_ATTRIBUTES:
                continue
            if attribute in {"srcset", "data-srcset", "imagesrcset"}:
                entries, srcset_errors = _srcset_entries(value)
                errors.extend(srcset_errors)
            else:
                entries = [(value, None)]
            for raw, descriptor in entries:
                canonical, error = _canonical_media_reference(
                    raw,
                    destination_path=destination_path,
                    json_root_relative=False,
                )
                occurrences.append(
                    {
                        "node": node,
                        "tag": node.tag,
                        "attribute": attribute,
                        "raw": raw,
                        "canonical": canonical,
                        "descriptor": descriptor,
                        "error": error,
                    }
                )
    return occurrences, errors


def _surface_probe_base(
    placement: Mapping[str, Any],
    *,
    public_post_url: str,
    variant_by_role: Mapping[str, Mapping[str, Any]],
    destination_regular_file: bool,
) -> dict[str, Any]:
    expected = {
        "route_scope": placement["route_scope"],
        "destination_path": placement["destination_path"],
        "surface_id": placement["surface_id"],
        "public_post_url": public_post_url,
        "variants": [
            {
                "role": role,
                "path": variant_by_role[role]["path"],
                "media_type": variant_by_role[role]["media_type"],
                "width": variant_by_role[role]["width"],
                "height": variant_by_role[role]["height"],
            }
            for role in placement["variant_roles"]
        ],
        "alt": placement["alt"],
        "caption": placement["caption"],
        "credit": placement["credit"],
    }
    return {
        **dict(placement),
        "destination_regular_file": destination_regular_file,
        # Static parsing can reject explicit and browser-native hidden
        # containers, but it cannot prove computed CSS, geometry, occlusion,
        # or interaction state.  Every structurally valid surface therefore
        # remains explicitly subject to exact browser-runtime visibility
        # verification downstream.
        "computed_visibility_state": RUNTIME_VISIBILITY_REQUIRED_STATE,
        "runtime_visibility_required": True,
        "currently_referenced": False,
        "state": "absent",
        "surface_unique": False,
        "post_url_present": False,
        "variants_present": False,
        "alt_present": False,
        "caption_present": False,
        "credit_present": False,
        "no_extra_media_sources": False,
        "binding_complete": False,
        "finding_codes": [],
        "expected_binding_sha256": _json_sha256(expected),
        "observation_sha256": _json_sha256(
            {
                "destination_regular_file": destination_regular_file,
                "state": "absent",
            }
        ),
    }


def _finish_surface_probe(
    probe: dict[str, Any],
    *,
    referenced: bool,
    findings: set[str],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    probe["currently_referenced"] = referenced
    probe["finding_codes"] = sorted(findings)
    probe["binding_complete"] = bool(referenced and not findings)
    probe["state"] = "bound" if probe["binding_complete"] else ("drift" if referenced else "absent")
    probe["observation_sha256"] = _json_sha256(
        {
            **dict(observation),
            "currently_referenced": referenced,
            "state": probe["state"],
            "finding_codes": probe["finding_codes"],
        }
    )
    return probe


def _probe_html_placement(
    text: str,
    placement: Mapping[str, Any],
    *,
    public_post_url: str,
    variant_by_role: Mapping[str, Mapping[str, Any]],
    destination_regular_file: bool,
) -> dict[str, Any]:
    destination_path = str(placement["destination_path"])
    surface_id = str(placement["surface_id"])
    probe = _surface_probe_base(
        placement,
        public_post_url=public_post_url,
        variant_by_role=variant_by_role,
        destination_regular_file=destination_regular_file,
    )
    parser = _SurfaceHTMLParser()
    parse_failed = False
    try:
        parser.feed(text)
        parser.close()
    except (DesignEditorialAssetProvenanceError, UnicodeError, ValueError):
        parse_failed = True
    nodes = _walk_html(parser.root)
    hidden_node_ids = _hidden_html_node_ids(parser.root)
    surface_nodes = [node for node in nodes if node.attributes.get("data-editorial-surface-id") == surface_id]
    surface_id_counts: dict[str, int] = {}
    for node in nodes:
        declared = node.attributes.get("data-editorial-surface-id")
        if declared is not None:
            surface_id_counts[declared] = surface_id_counts.get(declared, 0) + 1
    occurrences, occurrence_errors = _html_media_occurrences(
        parser.root,
        destination_path=destination_path,
    )
    expected_paths = {role: str(variant_by_role[role]["path"]) for role in placement["variant_roles"]}
    expected_references = {
        role: _exact_variant_reference(
            path,
            destination_path=destination_path,
            json_root_relative=False,
        )
        for role, path in expected_paths.items()
    }
    expected_reference_by_path = {path: expected_references[role] for role, path in expected_paths.items()}
    expected_occurrences = {
        role: [item for item in occurrences if item["canonical"] == path]
        for role, path in expected_paths.items()
    }
    referenced = bool(
        surface_nodes
        or any(expected_occurrences.values())
        or (
            not destination_regular_file
            and bool(text)
            and (surface_id in text or any(Path(path).name in text for path in expected_paths.values()))
        )
    )
    if not referenced:
        return _finish_surface_probe(
            probe,
            referenced=False,
            findings=set(),
            observation={
                "destination_regular_file": destination_regular_file,
                "surface_count": 0,
                "expected_variant_counts": {
                    role: len(items) for role, items in sorted(expected_occurrences.items())
                },
            },
        )

    findings: set[str] = set()
    if not destination_regular_file:
        findings.add("destination-not-regular")
    if parse_failed or parser.errors:
        findings.add("malformed-html")
    if occurrence_errors:
        findings.update(occurrence_errors)
    duplicate_ids = sorted(declared for declared, count in surface_id_counts.items() if count != 1)
    if duplicate_ids:
        findings.add("duplicate-editorial-surface-id")
    if not surface_nodes:
        findings.add("surface-id-missing")
    elif len(surface_nodes) != 1:
        findings.add("surface-id-not-unique")
    if any(id(node) in hidden_node_ids for node in surface_nodes):
        findings.add("hidden-surface-binding")

    target_nodes: list[_HTMLNode] = []
    target_node_ids: set[int] = set()
    if surface_nodes:
        for surface_node in surface_nodes:
            for node in [surface_node, *_walk_html(surface_node)]:
                if id(node) not in target_node_ids:
                    target_nodes.append(node)
                    target_node_ids.add(id(node))
        if any(
            "data-editorial-surface-id" in descendant.attributes
            for surface_node in surface_nodes
            for descendant in _walk_html(surface_node)
        ):
            findings.add("nested-editorial-surface")

    target_occurrences = [item for item in occurrences if id(item["node"]) in target_node_ids]
    expected_path_values = set(expected_paths.values())
    invalid_target_sources = [item for item in target_occurrences if item["error"] is not None]
    if invalid_target_sources:
        findings.update(str(item["error"]) for item in invalid_target_sources)
    extra_target_sources = [
        item
        for item in target_occurrences
        if item["error"] is not None
        or item["canonical"] not in expected_path_values
        or (
            item["canonical"] in expected_path_values
            and item["raw"] != expected_reference_by_path[item["canonical"]]
        )
    ]
    probe["no_extra_media_sources"] = bool(target_node_ids and not extra_target_sources)
    if extra_target_sources:
        findings.add("extra-media-source")

    for role, items in expected_occurrences.items():
        target_items = [item for item in items if id(item["node"]) in target_node_ids]
        exact_target_items = [item for item in target_items if item["raw"] == expected_references[role]]
        if len(items) != 1:
            findings.add(f"{role}-variant-reference-count")
        if len(target_items) != len(items):
            findings.add("variant-reference-outside-surface")
        if target_items and not exact_target_items:
            findings.add("noncanonical-variant-reference")
        if len(exact_target_items) != 1:
            findings.add(f"{role}-variant-not-bound")
    probe["variants_present"] = all(
        len(items) == 1
        and id(items[0]["node"]) in target_node_ids
        and items[0]["raw"] == expected_references[role]
        for role, items in expected_occurrences.items()
    )

    pictures = [node for node in target_nodes if node.tag == "picture"]
    sources = [node for node in target_nodes if node.tag == "source"]
    images = [node for node in target_nodes if node.tag == "img"]
    if any(id(node) in hidden_node_ids for node in [*pictures, *sources, *images]):
        findings.add("hidden-surface-binding")
    if len(pictures) != 1:
        findings.add("picture-element-count")
    if len(sources) != 1:
        findings.add("source-element-count")
    if len(images) != 1:
        findings.add("image-element-count")
    picture_descendant_ids = {id(node) for node in (_walk_html(pictures[0]) if len(pictures) == 1 else [])}
    if (len(sources) == 1 and id(sources[0]) not in picture_descendant_ids) or (
        len(images) == 1 and id(images[0]) not in picture_descendant_ids
    ):
        findings.add("picture-child-binding-drift")
    if len(sources) == 1:
        source = sources[0]
        matching_small = [
            item
            for item in target_occurrences
            if item["node"] is source
            and item["attribute"] == "srcset"
            and item["canonical"] == expected_paths["small"]
            and item["raw"] == expected_references["small"]
        ]
        descriptor = matching_small[0]["descriptor"] if len(matching_small) == 1 else None
        if (
            len(matching_small) != 1
            or source.attributes.get("type") != "image/webp"
            or descriptor not in {None, f"{variant_by_role['small']['width']}w"}
        ):
            findings.add("small-variant-element-binding")
    if len(images) == 1:
        image = images[0]
        matching_large = [
            item
            for item in target_occurrences
            if item["node"] is image
            and item["attribute"] == "src"
            and item["canonical"] == expected_paths["large"]
            and item["raw"] == expected_references["large"]
        ]
        if len(matching_large) != 1:
            findings.add("large-variant-element-binding")
        probe["alt_present"] = image.attributes.get("alt") == placement["alt"]
        if not probe["alt_present"]:
            findings.add("alt-binding-drift")
        if image.attributes.get("width") != str(variant_by_role["large"]["width"]) or image.attributes.get(
            "height"
        ) != str(variant_by_role["large"]["height"]):
            findings.add("image-dimension-binding-drift")

    anchors = [node for node in target_nodes if node.tag == "a"]
    exact_anchors = [node for node in anchors if node.attributes.get("href") == public_post_url]
    probe["post_url_present"] = bool(
        len(anchors) == 1 and len(exact_anchors) == 1 and id(exact_anchors[0]) not in hidden_node_ids
    )
    if not probe["post_url_present"]:
        findings.add("public-post-anchor-binding-drift")

    figcaptions = [node for node in target_nodes if node.tag == "figcaption"]
    probe["caption_present"] = bool(
        len(figcaptions) == 1
        and id(figcaptions[0]) not in hidden_node_ids
        and _visible_html_text(figcaptions[0]) == placement["caption"]
    )
    if not probe["caption_present"]:
        findings.add("caption-binding-drift")
    probe["credit_present"] = any(
        _visible_html_text(node) == placement["credit"]
        for node in target_nodes
        if node is not surface_nodes[0] and id(node) not in hidden_node_ids
    )
    if not probe["credit_present"]:
        findings.add("credit-binding-drift")

    probe["surface_unique"] = bool(
        len(surface_nodes) == 1 and not duplicate_ids and "nested-editorial-surface" not in findings
    )
    return _finish_surface_probe(
        probe,
        referenced=True,
        findings=findings,
        observation={
            "destination_regular_file": destination_regular_file,
            "parser_error_count": len(parser.errors) + int(parse_failed),
            "surface_count": len(surface_nodes),
            "duplicate_surface_id_count": len(duplicate_ids),
            "expected_variant_counts": {
                role: len(items) for role, items in sorted(expected_occurrences.items())
            },
            "target_media_source_count": len(target_occurrences),
            "picture_count": len(pictures),
            "source_count": len(sources),
            "image_count": len(images),
            "anchor_count": len(anchors),
            "exact_anchor_count": len(exact_anchors),
            "alt_present": probe["alt_present"],
            "caption_present": probe["caption_present"],
            "credit_present": probe["credit_present"],
        },
    )


class _DuplicateJSONKeyError(ValueError):
    pass


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKeyError(key)
        result[key] = value
    return result


def _walk_json(value: object) -> list[object]:
    values: list[object] = []
    pending = [value]
    while pending:
        current = pending.pop()
        values.append(current)
        if isinstance(current, Mapping):
            pending.extend(reversed(list(current.values())))
        elif isinstance(current, list):
            pending.extend(reversed(current))
    return values


def _json_media_field(key: str) -> bool:
    normalised = key.casefold()
    if normalised in {
        "artwork_alt",
        "artwork_caption",
        "artwork_credit",
    }:
        return False
    return (
        normalised in _JSON_MEDIA_FIELDS
        or "image" in normalised
        or "artwork" in normalised
        or normalised.endswith(("_src", "_srcset", "_thumbnail", "_poster"))
    )


def _json_string_leaves(value: object) -> list[str]:
    return [item for item in _walk_json(value) if isinstance(item, str)]


def _json_descendant_ids(value: object) -> set[int]:
    return {id(item) for item in _walk_json(value) if isinstance(item, (Mapping, list))}


def _probe_json_placement(
    text: str,
    placement: Mapping[str, Any],
    *,
    public_post_url: str,
    variant_by_role: Mapping[str, Mapping[str, Any]],
    destination_regular_file: bool,
) -> dict[str, Any]:
    destination_path = str(placement["destination_path"])
    surface_id = str(placement["surface_id"])
    probe = _surface_probe_base(
        placement,
        public_post_url=public_post_url,
        variant_by_role=variant_by_role,
        destination_regular_file=destination_regular_file,
    )
    expected_paths = {role: str(variant_by_role[role]["path"]) for role in placement["variant_roles"]}
    expected_references = {
        role: _exact_variant_reference(
            path,
            destination_path=destination_path,
            json_root_relative=True,
        )
        for role, path in expected_paths.items()
    }
    expected_reference_by_path = {path: expected_references[role] for role, path in expected_paths.items()}
    parsed: object = None
    parse_error = False
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_strict_json_object,
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        _DuplicateJSONKeyError,
    ):
        parse_error = True
    if parse_error or not isinstance(parsed, (Mapping, list)):
        referenced = bool(
            surface_id in text or any(Path(path).name in text for path in expected_paths.values())
        )
        parse_findings = {"malformed-json"} if referenced else set()
        if referenced and not destination_regular_file:
            parse_findings.add("destination-not-regular")
        return _finish_surface_probe(
            probe,
            referenced=referenced,
            findings=parse_findings,
            observation={
                "destination_regular_file": destination_regular_file,
                "parse_error": True,
            },
        )

    mappings = [item for item in _walk_json(parsed) if isinstance(item, Mapping)]
    surface_id_counts: dict[str, int] = {}
    for item in mappings:
        declared = item.get("surface_id")
        if isinstance(declared, str):
            surface_id_counts[declared] = surface_id_counts.get(declared, 0) + 1
    target_records = [item for item in mappings if item.get("surface_id") == surface_id]

    media_occurrences: list[dict[str, Any]] = []
    all_expected_occurrences: dict[str, list[dict[str, Any]]] = {
        role: [] for role in placement["variant_roles"]
    }
    for owner in mappings:
        for raw_key, raw_value in owner.items():
            key = str(raw_key)
            is_media_field = _json_media_field(key)
            if isinstance(raw_value, str):
                leaves = [raw_value]
            elif is_media_field:
                leaves = _json_string_leaves(raw_value)
            else:
                leaves = []
            for leaf in leaves:
                canonical, error = _canonical_media_reference(
                    leaf,
                    destination_path=destination_path,
                    json_root_relative=True,
                )
                for role, expected_path in expected_paths.items():
                    if canonical == expected_path:
                        all_expected_occurrences[role].append(
                            {
                                "owner": owner,
                                "key": key,
                                "raw": leaf,
                                "canonical": canonical,
                                "error": error,
                            }
                        )
                if is_media_field:
                    media_occurrences.append(
                        {
                            "owner": owner,
                            "key": key,
                            "raw": leaf,
                            "canonical": canonical,
                            "error": error,
                        }
                    )
            if is_media_field and not leaves:
                media_occurrences.append(
                    {
                        "owner": owner,
                        "key": key,
                        "raw": None,
                        "canonical": None,
                        "error": "invalid-json-media-field",
                    }
                )

    referenced = bool(target_records or any(all_expected_occurrences.values()))
    if not referenced:
        return _finish_surface_probe(
            probe,
            referenced=False,
            findings=set(),
            observation={
                "destination_regular_file": destination_regular_file,
                "surface_count": 0,
                "expected_variant_counts": {
                    role: len(items) for role, items in sorted(all_expected_occurrences.items())
                },
            },
        )

    findings: set[str] = set()
    if not destination_regular_file:
        findings.add("destination-not-regular")
    duplicate_ids = sorted(declared for declared, count in surface_id_counts.items() if count != 1)
    if duplicate_ids:
        findings.add("duplicate-editorial-surface-id")
    if not target_records:
        findings.add("surface-id-missing")
    elif len(target_records) != 1:
        findings.add("surface-id-not-unique")

    target_record: Mapping[str, Any] | None = target_records[0] if len(target_records) == 1 else None
    target_descendant_ids = _json_descendant_ids(target_record) if target_record is not None else set()
    target_media = [item for item in media_occurrences if id(item["owner"]) in target_descendant_ids]
    expected_path_values = set(expected_paths.values())
    invalid_target_sources = [item for item in target_media if item["error"] is not None]
    if invalid_target_sources:
        findings.update(str(item["error"]) for item in invalid_target_sources)
    extra_target_sources = [
        item
        for item in target_media
        if item["error"] is not None
        or item["canonical"] not in expected_path_values
        or item["key"] not in {"artwork", "artwork_small"}
        or (
            item["canonical"] in expected_path_values
            and item["raw"] != expected_reference_by_path[item["canonical"]]
        )
    ]
    probe["no_extra_media_sources"] = bool(
        target_record is not None and not extra_target_sources and len(target_media) == 2
    )
    if extra_target_sources or (target_record is not None and len(target_media) != 2):
        findings.add("extra-media-source")

    for role, items in all_expected_occurrences.items():
        target_items = [item for item in items if id(item["owner"]) in target_descendant_ids]
        exact_target_items = [item for item in target_items if item["raw"] == expected_references[role]]
        if len(items) != 1:
            findings.add(f"{role}-variant-reference-count")
        if len(target_items) != len(items):
            findings.add("variant-reference-outside-surface")
        if target_items and not exact_target_items:
            findings.add("noncanonical-variant-reference")
        if len(exact_target_items) != 1:
            findings.add(f"{role}-variant-not-bound")
    probe["variants_present"] = all(
        len(items) == 1
        and id(items[0]["owner"]) in target_descendant_ids
        and items[0]["raw"] == expected_references[role]
        for role, items in all_expected_occurrences.items()
    )

    link_fields: list[str] = []
    if target_record is not None:
        link_fields = [key for key in ("url", "public_post_url") if key in target_record]
        probe["post_url_present"] = bool(
            len(link_fields) == 1 and target_record.get(link_fields[0]) == public_post_url
        )
        probe["alt_present"] = target_record.get("artwork_alt") == placement["alt"]
        probe["caption_present"] = target_record.get("artwork_caption") == placement["caption"]
        probe["credit_present"] = target_record.get("artwork_credit") == placement["credit"]
        small_path, small_error = _canonical_media_reference(
            str(target_record.get("artwork_small", "")),
            destination_path=destination_path,
            json_root_relative=True,
        )
        large_path, large_error = _canonical_media_reference(
            str(target_record.get("artwork", "")),
            destination_path=destination_path,
            json_root_relative=True,
        )
        if (
            small_error is not None
            or small_path != expected_paths["small"]
            or target_record.get("artwork_small") != expected_references["small"]
        ):
            findings.add("small-variant-element-binding")
        if (
            large_error is not None
            or large_path != expected_paths["large"]
            or target_record.get("artwork") != expected_references["large"]
        ):
            findings.add("large-variant-element-binding")
    if not probe["post_url_present"]:
        findings.add("public-post-anchor-binding-drift")
    if not probe["alt_present"]:
        findings.add("alt-binding-drift")
    if not probe["caption_present"]:
        findings.add("caption-binding-drift")
    if not probe["credit_present"]:
        findings.add("credit-binding-drift")

    probe["surface_unique"] = bool(len(target_records) == 1 and not duplicate_ids)
    return _finish_surface_probe(
        probe,
        referenced=True,
        findings=findings,
        observation={
            "destination_regular_file": destination_regular_file,
            "surface_count": len(target_records),
            "duplicate_surface_id_count": len(duplicate_ids),
            "expected_variant_counts": {
                role: len(items) for role, items in sorted(all_expected_occurrences.items())
            },
            "target_media_source_count": len(target_media),
            "link_field_count": len(link_fields),
            "post_url_present": probe["post_url_present"],
            "alt_present": probe["alt_present"],
            "caption_present": probe["caption_present"],
            "credit_present": probe["credit_present"],
        },
    )


def _probe_placement(
    root: Path,
    placement: Mapping[str, Any],
    *,
    public_post_url: str,
    variant_by_role: Mapping[str, Mapping[str, Any]],
    website_root_relative: str,
) -> dict[str, Any]:
    destination_path = str(placement["destination_path"])
    destination_parts = Path(destination_path).parts
    if not destination_parts or destination_parts[0] != "website":
        raise DesignEditorialAssetProvenanceError(
            "Editorial destination must remain below the controlled website root."
        )
    projected_destination = (Path(website_root_relative) / Path(*destination_parts[1:])).as_posix()
    candidate, safety = _file_safety(
        root,
        projected_destination,
        max_bytes=_MAX_DESTINATION_BYTES,
    )
    text = ""
    if safety["regular_file"]:
        try:
            text = candidate.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            text = ""
    suffix = Path(destination_path).suffix.casefold()
    if suffix == ".html":
        return _probe_html_placement(
            text,
            placement,
            public_post_url=public_post_url,
            variant_by_role=variant_by_role,
            destination_regular_file=bool(safety["regular_file"]),
        )
    if suffix == ".json":
        return _probe_json_placement(
            text,
            placement,
            public_post_url=public_post_url,
            variant_by_role=variant_by_role,
            destination_regular_file=bool(safety["regular_file"]),
        )
    probe = _surface_probe_base(
        placement,
        public_post_url=public_post_url,
        variant_by_role=variant_by_role,
        destination_regular_file=bool(safety["regular_file"]),
    )
    referenced = bool(safety["available"])
    findings = {"unsupported-destination-format"} if referenced else set()
    return _finish_surface_probe(
        probe,
        referenced=referenced,
        findings=findings,
        observation={
            "destination_regular_file": bool(safety["regular_file"]),
            "unsupported_destination_format": True,
        },
    )


def _surface_binding_payload(
    *,
    asset_id: str,
    website_projection: str,
    placement_audits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    placements: list[dict[str, Any]] = []
    for item in placement_audits:
        row: dict[str, Any] = {
            "route_scope": item["route_scope"],
            "destination_path": item["destination_path"],
            "surface_id": item["surface_id"],
            "state": item["state"],
            "computed_visibility_state": item["computed_visibility_state"],
            "runtime_visibility_required": (item["runtime_visibility_required"] is True),
            "destination_regular_file": (item["destination_regular_file"] is True),
            "currently_referenced": (item["currently_referenced"] is True),
            "binding_complete": item["binding_complete"] is True,
            "expected_binding_sha256": (item["expected_binding_sha256"]),
            "observation_sha256": item["observation_sha256"],
            "finding_codes": list(item["finding_codes"]),
        }
        row["surface_binding_sha256"] = _json_sha256(row)
        placements.append(row)
    placements.sort(
        key=lambda item: (
            str(item["route_scope"]),
            str(item["destination_path"]),
            str(item["surface_id"]),
        )
    )
    payload: dict[str, Any] = {
        "schema": SURFACE_BINDING_SCHEMA,
        "asset_id": asset_id,
        "website_projection": website_projection,
        "computed_visibility_state": RUNTIME_VISIBILITY_REQUIRED_STATE,
        "runtime_visibility_required": True,
        "placements": placements,
        "summary": {
            "declared_placement_count": len(placements),
            "referenced_placement_count": sum(item["currently_referenced"] is True for item in placements),
            "bound_placement_count": sum(item["binding_complete"] is True for item in placements),
            "drift_placement_count": sum(item["state"] == "drift" for item in placements),
            "runtime_visibility_required_count": sum(
                item["runtime_visibility_required"] is True for item in placements
            ),
        },
    }
    payload["surface_bindings_sha256"] = _json_sha256(payload)
    return payload


def _verify_normalised_asset_surface_bindings(
    asset: Mapping[str, Any],
    *,
    root: Path,
    website_root: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    website_root_relative, website_projection = _controlled_website_projection(
        root,
        website_root,
    )
    variant_by_role = {str(item["role"]): item for item in asset["variants"]}
    placement_audits = [
        _probe_placement(
            root,
            placement,
            public_post_url=str(asset["public_post_url"]),
            variant_by_role=variant_by_role,
            website_root_relative=website_root_relative,
        )
        for placement in asset["placements"]
    ]
    payload = _surface_binding_payload(
        asset_id=str(asset["asset_id"]),
        website_projection=website_projection,
        placement_audits=placement_audits,
    )
    return payload, placement_audits


def verify_editorial_asset_surface_bindings(
    asset: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    website_root: Path | None = None,
) -> dict[str, Any]:
    """Return a deterministic, privacy-safe structural binding receipt.

    The input is one manifest asset record. ``website_root`` may select only the
    canonical ``website/`` directory or one deterministic
    ``artifacts/website-candidates/<run-id>/website`` projection. The receipt
    exposes only controlled public route identifiers, projection kind,
    booleans, finding codes, and hashes; source paths, rights evidence, people,
    provider identifiers, candidate run ids, and arbitrary destination content
    are excluded.
    """

    root = _find_repo_root(repo_root)
    normalised = _normalise_asset(asset)
    payload, _ = _verify_normalised_asset_surface_bindings(
        normalised,
        root=root,
        website_root=website_root,
    )
    return payload


def _normalise_unmapped(value: Mapping[str, Any]) -> dict[str, Any]:
    raw = _exact_fields(value, _UNMAPPED_FIELDS, label="Unmapped editorial asset")
    asset_id = _identifier(raw.get("asset_id"), label="Unmapped asset id")
    if (
        raw.get("mapping_state") != "unmapped"
        or raw.get("rights_state") != "not-authorised"
        or raw.get("reason_code") != "no-direct-public-post-or-variant-binding"
    ):
        raise DesignEditorialAssetProvenanceError(
            "Unmapped assets must remain explicitly not authorised because no "
            "direct public post and variant binding exists."
        )
    return {
        "asset_id": asset_id,
        "source_asset": _normalise_file_record(
            _exact_fields(
                raw.get("source_asset"),
                _FILE_FIELDS,
                label=f"{asset_id} unmapped source asset",
            ),
            label=f"{asset_id} unmapped source asset",
            role="source",
            root_prefix=SAFE_ROOTS["source_assets"],
        ),
        "mapping_state": "unmapped",
        "rights_state": "not-authorised",
        "reason_code": "no-direct-public-post-or-variant-binding",
    }


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


def audit_design_editorial_asset_provenance(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Audit exact local editorial assets without granting publication authority."""

    root = _find_repo_root(repo_root)
    canonical_path, canonical_relative = _canonical_manifest_path(root, manifest_path)
    raw = _exact_fields(
        manifest,
        _MANIFEST_FIELDS,
        label="Editorial asset provenance manifest",
    )
    if raw.get("schema") != MANIFEST_SCHEMA:
        raise DesignEditorialAssetProvenanceError(
            f"Editorial asset manifest schema must be {MANIFEST_SCHEMA}."
        )
    manifest_id = _identifier(raw.get("manifest_id"), label="Manifest id")
    issued_at = _parse_datetime(raw.get("issued_at"), label="Manifest issued_at")
    reviewed_at = (as_of or datetime.now(UTC)).astimezone(UTC)
    if reviewed_at < issued_at:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset manifest cannot be audited before its issued_at."
        )
    if raw.get("authority") != NON_AUTHORITATIVE_AUTHORITY:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset manifest must retain the non-authoritative boundary."
        )
    if raw.get("global_artwork_policy") != GLOBAL_NOT_CLEARED_POLICY:
        raise DesignEditorialAssetProvenanceError(
            "Global artwork policy must remain not-cleared and false for use."
        )
    if raw.get("safe_roots") != SAFE_ROOTS:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset manifest safe roots must match the controlled contract."
        )
    persisted = _read_json(canonical_path, label="Canonical editorial asset manifest")
    file_bound = _json_sha256(persisted) == _json_sha256(raw)

    (
        evidence_summaries,
        delivery_items,
        inventory_files,
        evidence_safe,
    ) = _load_evidence_snapshots(root, raw.get("evidence_snapshots"))

    raw_assets = raw.get("assets")
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes)) or not raw_assets:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset manifest must contain exact mapped asset records."
        )
    assets: list[dict[str, Any]] = []
    normalised_assets: dict[str, dict[str, Any]] = {}
    seen_asset_ids: set[str] = set()
    all_files_safe = True
    delivery_closed = True
    inventory_closed = True
    for raw_asset in raw_assets:
        if not isinstance(raw_asset, Mapping):
            raise DesignEditorialAssetProvenanceError("Editorial assets must be objects.")
        asset = _normalise_asset(raw_asset)
        asset_id = str(asset["asset_id"])
        if asset_id in seen_asset_ids:
            raise DesignEditorialAssetProvenanceError("Editorial asset ids must be unique.")
        seen_asset_ids.add(asset_id)
        normalised_assets[asset_id] = asset
        delivery_item = delivery_items.get(asset_id)
        delivery_matches = bool(
            delivery_item
            and delivery_item["public_post_url"] == asset["public_post_url"]
            and delivery_item["source_asset_path"] == asset["source_asset"]["path"]
            and delivery_item["evidence_code"] == asset["delivery_evidence"]["evidence_code"]
            and delivery_item["rights_effect"] == "none"
            and asset["delivery_evidence"]["rights_effect"] == "none"
            and asset["delivery_evidence"]["snapshot_id"]
            == next(
                (
                    item.get("snapshot_id")
                    for item in evidence_summaries
                    if item["kind"] == "redacted-delivery-evidence"
                ),
                None,
            )
        )
        delivery_closed = delivery_closed and delivery_matches

        source_audit = _audit_file_record(root, asset["source_asset"])
        source_inventory_matches = _file_record_matches_inventory(
            asset["source_asset"],
            _inventory_record_for(
                inventory_files,
                asset_id=asset_id,
                role="source",
            ),
        )
        variant_audits: list[dict[str, Any]] = []
        variants_inventory_match = True
        for variant in asset["variants"]:
            role = str(variant["role"])
            variant_audit = _audit_file_record(root, variant)
            variant_audit["role"] = role
            variant_audits.append(variant_audit)
            variants_inventory_match = variants_inventory_match and _file_record_matches_inventory(
                variant,
                _inventory_record_for(
                    inventory_files,
                    asset_id=asset_id,
                    role=role,
                ),
            )
        inventory_matches = source_inventory_matches and variants_inventory_match
        inventory_closed = inventory_closed and inventory_matches
        file_integrity = bool(
            source_audit["integrity_matches"] and all(item["integrity_matches"] for item in variant_audits)
        )
        all_files_safe = all_files_safe and file_integrity

        asset_scope = asset_scope_sha256(asset)
        rights_summary = _validate_rights_decision(
            root,
            asset["rights_decision"],
            asset_id=asset_id,
            asset_scope=asset_scope,
            reviewed_at=reviewed_at,
        )
        surface_binding, placement_audits = _verify_normalised_asset_surface_bindings(
            asset,
            root=root,
        )
        current_reference_routes = sorted(
            {str(item["route_scope"]) for item in placement_audits if item["currently_referenced"]}
        )
        current_use_authorised = bool(
            current_reference_routes
            and rights_summary["state"] == "approved"
            and rights_summary["decision_valid"]
        )
        candidate_use_ready = bool(
            file_bound
            and evidence_safe
            and delivery_matches
            and inventory_matches
            and file_integrity
            and rights_summary["state"] == "approved"
            and rights_summary["named_human_decision"]
            and rights_summary["decision_valid"]
        )
        blocking_codes: list[str] = []
        if not file_bound:
            blocking_codes.append("manifest-not-canonical-bound")
        if not evidence_safe:
            blocking_codes.append("redacted-evidence-not-safe")
        if not delivery_matches:
            blocking_codes.append("delivery-binding-drift")
        if not inventory_matches:
            blocking_codes.append("inventory-binding-drift")
        if not file_integrity:
            blocking_codes.append("asset-byte-integrity-failed")
        if rights_summary["state"] == "pending":
            blocking_codes.append("named-human-rights-decision-missing")
        elif not rights_summary["decision_valid"]:
            blocking_codes.append("human-rights-decision-invalid")
        if current_reference_routes and not current_use_authorised:
            blocking_codes.append("currently-referenced-without-rights")
        if any(item["currently_referenced"] and not item["binding_complete"] for item in placement_audits):
            blocking_codes.append("current-placement-copy-binding-drift")
        assets.append(
            {
                "asset_id": asset_id,
                "public_post_url": asset["public_post_url"],
                "delivery_evidence": {
                    **asset["delivery_evidence"],
                    "binding_matches": delivery_matches,
                },
                "source_asset": source_audit,
                "variants": variant_audits,
                "representation": asset["representation"],
                "placements": placement_audits,
                "surface_binding": surface_binding,
                "rights": rights_summary,
                "current_reference_routes": current_reference_routes,
                "current_use_authorised": current_use_authorised,
                "candidate_use_ready": candidate_use_ready,
                "blocking_codes": sorted(set(blocking_codes)),
            }
        )
    assets.sort(key=lambda item: str(item["asset_id"]))

    raw_unmapped = raw.get("unmapped_assets")
    if not isinstance(raw_unmapped, Sequence) or isinstance(raw_unmapped, (str, bytes)):
        raise DesignEditorialAssetProvenanceError("Unmapped editorial assets must be an explicit list.")
    unmapped: list[dict[str, Any]] = []
    seen_unmapped: set[str] = set()
    for raw_item in raw_unmapped:
        if not isinstance(raw_item, Mapping):
            raise DesignEditorialAssetProvenanceError("Unmapped editorial assets must be objects.")
        item = _normalise_unmapped(raw_item)
        asset_id = str(item["asset_id"])
        if asset_id in seen_asset_ids or asset_id in seen_unmapped:
            raise DesignEditorialAssetProvenanceError(
                "Mapped and unmapped editorial asset ids must be globally unique."
            )
        seen_unmapped.add(asset_id)
        source_audit = _audit_file_record(root, item["source_asset"])
        inventory_matches = _file_record_matches_inventory(
            item["source_asset"],
            _inventory_record_for(
                inventory_files,
                asset_id=asset_id,
                role="source",
            ),
        )
        all_files_safe = all_files_safe and bool(source_audit["integrity_matches"])
        inventory_closed = inventory_closed and inventory_matches
        unmapped.append(
            {
                "asset_id": asset_id,
                "source_asset": source_audit,
                "mapping_state": "unmapped",
                "rights_state": "not-authorised",
                "reason_code": "no-direct-public-post-or-variant-binding",
                "inventory_binding_matches": inventory_matches,
                "candidate_use_ready": False,
            }
        )
    unmapped.sort(key=lambda item: str(item["asset_id"]))

    known_inventory_keys = (
        {(str(asset["asset_id"]), "source") for asset in assets}
        | {
            (str(asset["asset_id"]), str(variant["role"]))
            for asset in assets
            for variant in asset["variants"]
        }
        | {(str(item["asset_id"]), "source") for item in unmapped}
    )
    inventory_exact = set(inventory_files) == known_inventory_keys
    inventory_closed = inventory_closed and inventory_exact
    delivery_exact = set(delivery_items) == seen_asset_ids
    delivery_closed = delivery_closed and delivery_exact

    unapproved_current_assets = [
        str(item["asset_id"])
        for item in assets
        if item["current_reference_routes"] and not item["current_use_authorised"]
    ]
    current_copy_drift_assets = [
        str(item["asset_id"])
        for item in assets
        if "current-placement-copy-binding-drift" in item["blocking_codes"]
    ]
    candidate_ready_assets = [str(item["asset_id"]) for item in assets if item["candidate_use_ready"]]
    integrity_passed = bool(
        file_bound and evidence_safe and all_files_safe and delivery_closed and inventory_closed
    )
    passed = bool(integrity_passed and not unapproved_current_assets and not current_copy_drift_assets)
    if unapproved_current_assets:
        state_value = "blocked-unapproved-current-use"
    elif not integrity_passed or current_copy_drift_assets:
        state_value = "blocked"
    elif candidate_ready_assets:
        state_value = "candidate-use-ready"
    else:
        state_value = "pending-rights"

    checks = [
        _check(
            "canonical-manifest-binding",
            file_bound,
            "The audited declaration matches the canonical single-link local JSON file.",
            path=canonical_relative,
        ),
        _check(
            "global-artwork-policy-not-cleared",
            raw.get("global_artwork_policy") == GLOBAL_NOT_CLEARED_POLICY,
            "Per-asset review never changes the global not-cleared artwork policy.",
        ),
        _check(
            "redacted-evidence-integrity",
            evidence_safe,
            "Only hash-bound redacted delivery and local inventory snapshots were read.",
            snapshot_ids=[item.get("snapshot_id") for item in evidence_summaries if item.get("snapshot_id")],
            snapshot_sha256s=[item["sha256"] for item in evidence_summaries],
        ),
        _check(
            "delivery-rights-separation",
            delivery_closed,
            "Shareable-assets messages are bound as delivery evidence with rights_effect=none.",
            asset_ids=sorted(seen_asset_ids),
        ),
        _check(
            "asset-byte-and-inventory-integrity",
            all_files_safe and inventory_closed,
            "Every declared file is regular, single-link, reparse-free, hash-, MIME-, dimension-, frame-, byte-, and metadata-bound.",
            inventory_exact=inventory_exact,
        ),
        _check(
            "current-use-rights-closure",
            not unapproved_current_assets,
            "No canonical website reference may be treated as authorised without an exact named human rights decision.",
            unapproved_current_asset_ids=unapproved_current_assets,
        ),
        _check(
            "current-placement-copy-closure",
            not current_copy_drift_assets,
            "Referenced placements must retain one exact structural surface, "
            "public-post anchor, local WebP variants, alt, caption, and credit binding.",
            copy_drift_asset_ids=current_copy_drift_assets,
        ),
        _check(
            "candidate-rights-closure",
            all(
                not item["candidate_use_ready"]
                or (
                    item["rights"]["state"] == "approved"
                    and item["rights"]["named_human_decision"]
                    and item["rights"]["decision_valid"]
                )
                for item in assets
            ),
            "Candidate-use-ready is possible only for an exact asset scope approved by a separate named human decision.",
            candidate_use_ready_asset_ids=candidate_ready_assets,
        ),
    ]

    public_assets = [_public_asset_audit(item) for item in assets]
    public_unmapped = [
        {
            "asset_id": item["asset_id"],
            "source_asset": _public_file_audit(
                item["source_asset"],
                include_path=False,
            ),
            "mapping_state": item["mapping_state"],
            "rights_state": item["rights_state"],
            "reason_code": item["reason_code"],
            "inventory_binding_matches": item["inventory_binding_matches"],
            "candidate_use_ready": False,
        }
        for item in unmapped
    ]
    asset_capsules = [
        _worker_capsule_from(normalised_assets[str(item["asset_id"])], item)
        for item in assets
        if item["candidate_use_ready"]
    ]
    asset_capsules.sort(key=lambda item: str(item["asset_id"]))
    route_asset_capsules: list[dict[str, Any]] = []
    for capsule in asset_capsules:
        variants_by_role = {str(item["role"]): item for item in capsule["website_variants"]}
        for placement in capsule["placements"]:
            selected_variants = [dict(variants_by_role[str(role)]) for role in placement["variant_roles"]]
            route_capsule: dict[str, Any] = {
                "route_scope": placement["route_scope"],
                "asset_id": capsule["asset_id"],
                "public_post_url": capsule["public_post_url"],
                "website_variants": selected_variants,
                "representation": dict(capsule["representation"]),
                "placement": dict(placement),
                "rights": dict(capsule["rights"]),
                "asset_capsule_sha256": capsule["asset_capsule_sha256"],
            }
            route_capsule["route_asset_capsule_sha256"] = _json_sha256(route_capsule)
            route_asset_capsules.append(route_capsule)
    route_asset_capsules.sort(
        key=lambda item: (
            str(item["route_scope"]),
            str(item["asset_id"]),
            str(item["placement"]["destination_path"]),
            str(item["placement"]["surface_id"]),
        )
    )
    surface_bindings = [dict(item["surface_binding"]) for item in assets]
    surface_bindings.sort(key=lambda item: str(item["asset_id"]))
    coverage_rows = [
        {
            "asset_id": item["asset_id"],
            "variant_bindings": [
                {
                    "role": variant["role"],
                    "path": variant["path"],
                    "sha256": variant["sha256"],
                }
                for variant in item["variants"]
            ],
            "current_reference_routes": list(item["current_reference_routes"]),
            "current_use_authorised": item["current_use_authorised"] is True,
            "placement_copy_closed": ("current-placement-copy-binding-drift" not in item["blocking_codes"]),
            "surface_bindings_sha256": item["surface_binding"]["surface_bindings_sha256"],
        }
        for item in assets
    ]
    coverage_rows.sort(key=lambda item: str(item["asset_id"]))
    public_coverage = {
        "coverage_sha256": _json_sha256(coverage_rows),
        "currently_referenced_asset_count": sum(bool(item["current_reference_routes"]) for item in assets),
        "authorised_current_asset_count": sum(
            bool(item["current_reference_routes"]) and item["current_use_authorised"] is True
            for item in assets
        ),
        "unapproved_current_asset_count": len(unapproved_current_assets),
        "current_copy_drift_asset_count": len(current_copy_drift_assets),
        "all_current_references_authorised": not unapproved_current_assets,
        "all_current_copy_bindings_closed": not current_copy_drift_assets,
    }

    return {
        "schema": AUDIT_SCHEMA,
        "reviewed_at": _iso(reviewed_at),
        "state": state_value,
        "passed": passed,
        "receipt_authority": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": NON_AUTHORITATIVE_AUTHORITY,
        "global_artwork_policy": GLOBAL_NOT_CLEARED_POLICY,
        "manifest": {
            "manifest_id": manifest_id,
            "path": canonical_relative,
            "sha256": _sha256_file(canonical_path),
            "file_bound": file_bound,
        },
        "evidence_snapshots": [_public_evidence_summary(item) for item in evidence_summaries],
        "assets": public_assets,
        "unmapped_assets": public_unmapped,
        "asset_capsules": asset_capsules,
        "asset_capsules_sha256": _json_sha256(asset_capsules),
        "route_asset_capsules": route_asset_capsules,
        "route_asset_capsules_sha256": _json_sha256(route_asset_capsules),
        "surface_bindings": surface_bindings,
        "surface_bindings_sha256": _json_sha256(surface_bindings),
        "public_coverage": public_coverage,
        "summary": {
            "mapped_asset_count": len(assets),
            "unmapped_asset_count": len(unmapped),
            "currently_referenced_asset_count": sum(
                bool(item["current_reference_routes"]) for item in assets
            ),
            "unapproved_current_asset_count": len(unapproved_current_assets),
            "current_copy_drift_asset_count": len(current_copy_drift_assets),
            "named_human_decision_count": sum(
                bool(item["rights"]["named_human_decision"]) for item in assets
            ),
            "candidate_use_ready_count": len(candidate_ready_assets),
            "asset_capsule_count": len(asset_capsules),
            "route_asset_capsule_count": len(route_asset_capsules),
        },
        "checks": checks,
        "next_gate": (
            "owner records a separate named human rights decision for each exact "
            "asset scope, then a staged worker applies only the emitted safe "
            "capsule before existing visual, accessibility, claim, performance, "
            "backup, release and deployment gates"
        ),
    }


def audit_design_editorial_asset_provenance_file(
    path: Path | None = None,
    *,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Read and audit the canonical editorial asset provenance manifest."""

    root = _find_repo_root(repo_root)
    canonical_path, _ = _canonical_manifest_path(root, path)
    return audit_design_editorial_asset_provenance(
        _read_json(canonical_path, label="Canonical editorial asset manifest"),
        manifest_path=canonical_path,
        repo_root=root,
        as_of=as_of,
    )


def build_editorial_asset_worker_capsule(
    asset_id: str,
    *,
    manifest_path: Path | None = None,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Return a privacy-safe capsule only for one approved exact asset record."""

    controlled_asset_id = _identifier(asset_id, label="Worker capsule asset id")
    root = _find_repo_root(repo_root)
    canonical_path, _ = _canonical_manifest_path(root, manifest_path)
    manifest = _read_json(canonical_path, label="Canonical editorial asset manifest")
    audit = audit_design_editorial_asset_provenance(
        manifest,
        manifest_path=canonical_path,
        repo_root=root,
        as_of=as_of,
    )
    audit_asset = next(
        (item for item in audit["assets"] if item["asset_id"] == controlled_asset_id),
        None,
    )
    if not isinstance(audit_asset, Mapping):
        raise DesignEditorialAssetProvenanceError(f"Unknown mapped editorial asset: {controlled_asset_id}.")
    if not audit_asset.get("candidate_use_ready"):
        raise DesignEditorialAssetProvenanceError(
            f"Editorial asset {controlled_asset_id} is not candidate-use-ready."
        )
    normalised_manifest = _exact_fields(
        manifest,
        _MANIFEST_FIELDS,
        label="Canonical editorial asset manifest",
    )
    raw_asset = next(
        (
            item
            for item in normalised_manifest["assets"]
            if isinstance(item, Mapping) and item.get("asset_id") == controlled_asset_id
        ),
        None,
    )
    if not isinstance(raw_asset, Mapping):
        raise DesignEditorialAssetProvenanceError(
            "Candidate-ready asset disappeared from the canonical manifest."
        )
    asset = _normalise_asset(raw_asset)
    return _worker_capsule_from(asset, audit_asset)


def _normalise_rights_preparation_request(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    raw = _exact_fields(
        value,
        _RIGHTS_PREPARATION_REQUEST_FIELDS,
        label="Editorial rights decision preparation request",
    )
    if raw.get("schema") != RIGHTS_PREPARATION_REQUEST_SCHEMA:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation request schema must be "
            f"{RIGHTS_PREPARATION_REQUEST_SCHEMA}."
        )
    decision = raw.get("decision")
    if decision not in {"approved", "rejected"}:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation must explicitly say approved or rejected."
        )
    rights_basis = raw.get("rights_basis")
    if rights_basis not in RIGHTS_BASES:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation must use one controlled rights basis."
        )
    decided_by = _controlled_named_rights_reviewer(
        raw.get("decided_by"),
        label="Editorial rights decision preparation reviewer",
    )
    decided_at = _parse_datetime(
        raw.get("decided_at"),
        label="Editorial rights decision preparation decided_at",
    )
    raw_asset_ids = raw.get("asset_ids")
    if (
        not isinstance(raw_asset_ids, Sequence)
        or isinstance(raw_asset_ids, (str, bytes))
        or not raw_asset_ids
        or len(raw_asset_ids) > 64
    ):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation requires 1-64 exact asset ids."
        )
    asset_ids = [
        _identifier(
            asset_id,
            label=f"Editorial rights decision preparation asset id {index}",
        )
        for index, asset_id in enumerate(raw_asset_ids)
    ]
    if len(asset_ids) != len(set(asset_ids)):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation asset ids must be unique."
        )
    asset_ids = sorted(asset_ids)
    manifest_sha256 = _sha256(
        raw.get("manifest_sha256"),
        label="Editorial rights decision preparation manifest SHA-256",
    )
    raw_scopes = raw.get("asset_scopes")
    if not isinstance(raw_scopes, Mapping):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation asset_scopes must be one exact object."
        )
    asset_scopes: dict[str, str] = {}
    for raw_asset_id, raw_scope in raw_scopes.items():
        asset_id = _identifier(
            raw_asset_id,
            label="Editorial rights decision preparation asset scope id",
        )
        if asset_id in asset_scopes:
            raise DesignEditorialAssetProvenanceError(
                "Editorial rights decision preparation asset scope ids must be unique."
            )
        asset_scopes[asset_id] = _sha256(
            raw_scope,
            label=f"Editorial rights decision preparation {asset_id} scope SHA-256",
        )
    if set(asset_scopes) != set(asset_ids):
        missing = sorted(set(asset_ids) - set(asset_scopes))
        extra = sorted(set(asset_scopes) - set(asset_ids))
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation asset_scopes must have the "
            f"same exact key set as asset_ids (missing={missing}, extra={extra})."
        )
    if raw.get("usage_scope") != RIGHTS_USAGE_SCOPE:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation must explicitly acknowledge "
            f"the exact usage scope: {RIGHTS_USAGE_SCOPE}."
        )
    if raw.get("boundary_acknowledgement") != RIGHTS_BOUNDARY_ACKNOWLEDGEMENT:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation must explicitly acknowledge "
            "the exact controlled representation boundary."
        )
    return {
        "schema": RIGHTS_PREPARATION_REQUEST_SCHEMA,
        "asset_ids": asset_ids,
        "asset_scopes": {asset_id: asset_scopes[asset_id] for asset_id in asset_ids},
        "boundary_acknowledgement": str(raw["boundary_acknowledgement"]),
        "decision": str(decision),
        "decided_by": decided_by,
        "decided_at": _iso(decided_at),
        "manifest_sha256": manifest_sha256,
        "rights_basis": str(rights_basis),
        "usage_scope": str(raw["usage_scope"]),
    }


_RIGHTS_PREPARATION_ALLOWED_BLOCKERS = frozenset(
    {
        "current-placement-copy-binding-drift",
        "currently-referenced-without-rights",
        "named-human-rights-decision-missing",
    }
)


def _rights_preparation_snapshot(
    *,
    root: Path,
    manifest_path: Path,
    asset_ids: Sequence[str],
    decided_at: datetime,
    reviewed_at: datetime,
) -> dict[str, Any]:
    """Re-audit and bind each exact current asset scope before any write."""

    manifest = _read_json(
        manifest_path,
        label="Canonical editorial asset manifest",
    )
    audit = audit_design_editorial_asset_provenance(
        manifest,
        manifest_path=manifest_path,
        repo_root=root,
        as_of=reviewed_at,
    )
    raw = _exact_fields(
        manifest,
        _MANIFEST_FIELDS,
        label="Canonical editorial asset manifest",
    )
    issued_at = _parse_datetime(
        raw.get("issued_at"),
        label="Canonical editorial asset manifest issued_at",
    )
    if decided_at < issued_at:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision cannot predate the exact manifest scope it approves or rejects."
        )
    raw_assets = raw.get("assets")
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes)):
        raise DesignEditorialAssetProvenanceError(
            "Canonical editorial asset manifest assets must remain a sequence."
        )
    assets_by_id: dict[str, dict[str, Any]] = {}
    for value in raw_assets:
        if not isinstance(value, Mapping):
            raise DesignEditorialAssetProvenanceError(
                "Canonical editorial asset manifest contains an invalid asset."
            )
        asset = _normalise_asset(value)
        assets_by_id[str(asset["asset_id"])] = asset
    unknown = sorted(set(asset_ids) - set(assets_by_id))
    if unknown:
        raise DesignEditorialAssetProvenanceError(f"Unknown exact mapped editorial asset ids: {unknown}.")
    audit_assets = {
        str(item["asset_id"]): item
        for item in audit.get("assets", [])
        if isinstance(item, Mapping) and isinstance(item.get("asset_id"), str)
    }
    scopes: dict[str, str] = {}
    for asset_id in asset_ids:
        asset = assets_by_id[asset_id]
        rights = asset["rights_decision"]
        if not isinstance(rights, Mapping) or rights.get("state") != "pending":
            raise DesignEditorialAssetProvenanceError(
                f"Editorial asset {asset_id} already has a non-pending canonical rights state."
            )
        audited = audit_assets.get(asset_id)
        if not isinstance(audited, Mapping):
            raise DesignEditorialAssetProvenanceError(
                f"Editorial asset {asset_id} disappeared from the current provenance audit."
            )
        blockers = {str(code) for code in audited.get("blocking_codes", []) if isinstance(code, str)}
        unsafe_blockers = sorted(blockers - _RIGHTS_PREPARATION_ALLOWED_BLOCKERS)
        if unsafe_blockers:
            raise DesignEditorialAssetProvenanceError(
                f"Editorial asset {asset_id} has unsafe provenance blockers: {unsafe_blockers}."
            )
        source_audit = audited.get("source_asset")
        variant_audits = audited.get("variants")
        delivery = audited.get("delivery_evidence")
        if (
            not isinstance(source_audit, Mapping)
            or source_audit.get("integrity_matches") is not True
            or not isinstance(variant_audits, Sequence)
            or isinstance(variant_audits, (str, bytes))
            or len(variant_audits) != 2
            or any(
                not isinstance(item, Mapping) or item.get("integrity_matches") is not True
                for item in variant_audits
            )
            or not isinstance(delivery, Mapping)
            or delivery.get("binding_matches") is not True
        ):
            raise DesignEditorialAssetProvenanceError(
                f"Editorial asset {asset_id} failed current byte or delivery provenance re-audit."
            )
        scope = asset_scope_sha256(asset)
        audited_rights = audited.get("rights")
        if not isinstance(audited_rights, Mapping) or audited_rights.get("asset_scope_sha256") != scope:
            raise DesignEditorialAssetProvenanceError(
                f"Editorial asset {asset_id} scope disagrees with the current provenance audit."
            )
        scopes[asset_id] = scope
    return {
        "manifest_id": _identifier(
            raw.get("manifest_id"),
            label="Canonical editorial asset manifest id",
        ),
        "manifest_sha256": _sha256_file(manifest_path),
        "manifest_json_sha256": _json_sha256(manifest),
        "provenance_audit_sha256": _json_sha256(audit),
        "asset_scopes": scopes,
    }


def _assert_rights_preparation_snapshot_current(
    *,
    root: Path,
    manifest_path: Path,
    snapshot: Mapping[str, Any],
) -> None:
    """Reject manifest, rights-state, or exact asset-scope drift around commit."""

    current_path, _ = _canonical_manifest_path(root, manifest_path)
    if _sha256_file(current_path) != snapshot.get("manifest_sha256"):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights preparation stopped because the canonical manifest drifted."
        )
    current = _read_json(
        current_path,
        label="Canonical editorial asset manifest scope recheck",
    )
    if _json_sha256(current) != snapshot.get("manifest_json_sha256"):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights preparation stopped because the canonical manifest scope drifted."
        )
    raw = _exact_fields(
        current,
        _MANIFEST_FIELDS,
        label="Canonical editorial asset manifest scope recheck",
    )
    if raw.get("global_artwork_policy") != GLOBAL_NOT_CLEARED_POLICY:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights preparation requires the global not-cleared policy."
        )
    raw_assets = raw.get("assets")
    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes)):
        raise DesignEditorialAssetProvenanceError(
            "Canonical editorial asset manifest scope recheck has invalid assets."
        )
    current_assets: dict[str, dict[str, Any]] = {}
    for value in raw_assets:
        if not isinstance(value, Mapping):
            raise DesignEditorialAssetProvenanceError(
                "Canonical editorial asset manifest scope recheck contains an invalid asset."
            )
        asset = _normalise_asset(value)
        current_assets[str(asset["asset_id"])] = asset
    expected_scopes = snapshot.get("asset_scopes")
    if not isinstance(expected_scopes, Mapping):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights preparation lost its exact asset-scope snapshot."
        )
    for asset_id, expected_scope in expected_scopes.items():
        current_asset = current_assets.get(str(asset_id))
        if not isinstance(current_asset, Mapping):
            raise DesignEditorialAssetProvenanceError(
                "Editorial rights preparation stopped because an asset scope disappeared."
            )
        rights = current_asset.get("rights_decision")
        if (
            not isinstance(rights, Mapping)
            or rights.get("state") != "pending"
            or asset_scope_sha256(current_asset) != expected_scope
        ):
            raise DesignEditorialAssetProvenanceError(
                f"Editorial rights preparation stopped because {asset_id} scope drifted."
            )


def _decision_output_path(
    *,
    asset_id: str,
    decided_at: datetime,
    request_sha256: str,
) -> str:
    timestamp = decided_at.strftime("%Y%m%dT%H%M%SZ").casefold()
    asset_token = asset_id
    if len(asset_token) > 56:
        asset_token = f"{asset_token[:40]}-{hashlib.sha256(asset_id.encode('utf-8')).hexdigest()[:12]}"
    filename = f"{timestamp}-{asset_token}-{request_sha256[:16].casefold()}.rights-decision.v1.json"
    return (Path(SAFE_ROOTS["rights_decisions"]) / filename).as_posix()


def _proposal_output_path(
    *,
    decided_at: datetime,
    request_sha256: str,
) -> str:
    timestamp = decided_at.strftime("%Y%m%dT%H%M%SZ").casefold()
    filename = f"{timestamp}-{request_sha256[:20].casefold()}-manifest-binding-proposal.v1.json"
    return (DEFAULT_RIGHTS_PROPOSAL_ROOT / filename).as_posix()


def _encoded_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _ensure_safe_output_directory(root: Path, relative: Path) -> Path:
    if not relative.parts:
        raise DesignEditorialAssetProvenanceError("Immutable editorial rights output directory is missing.")
    cursor = root
    for part in relative.parts:
        cursor /= part
        if cursor.exists() or cursor.is_symlink():
            if _component_has_reparse_point(cursor) or not cursor.is_dir():
                raise DesignEditorialAssetProvenanceError(
                    "Immutable editorial rights output may not traverse a link, "
                    "reparse point, or non-directory."
                )
            continue
        try:
            cursor.mkdir()
        except FileExistsError as exc:
            if _component_has_reparse_point(cursor) or not cursor.is_dir():
                raise DesignEditorialAssetProvenanceError(
                    "Immutable editorial rights output directory raced with an unsafe path."
                ) from exc
    return cursor


def _exclusive_link(staged: Path, target: Path) -> None:
    """Retain one fully written temporary file without replacing a target."""

    os.link(staged, target)


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)


def _write_immutable_json_batch(
    outputs: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    root: Path,
    precommit: Callable[[], None],
    postcommit: Callable[[], None],
) -> list[Path]:
    """Write a preflighted JSON batch all-or-none using exclusive atomic links."""

    if not outputs:
        raise DesignEditorialAssetProvenanceError("Immutable editorial rights output batch cannot be empty.")
    prepared: list[tuple[Path, Path, str]] = []
    targets: list[Path] = []
    target_relatives: set[str] = set()
    for raw_relative, payload in outputs:
        relative = _safe_relative_path(
            raw_relative,
            label="Immutable editorial rights output path",
        )
        if relative in target_relatives:
            raise DesignEditorialAssetProvenanceError(
                "Immutable editorial rights output paths must be unique."
            )
        target_relatives.add(relative)
        relative_path = Path(relative)
        _ensure_safe_output_directory(root, relative_path.parent)
        target = root / relative_path
        if target.exists() or target.is_symlink():
            raise DesignEditorialAssetProvenanceError(
                f"Immutable editorial rights output already exists: {relative}."
            )
        encoded = _encoded_json(payload)
        if not 0 < len(encoded) <= _MAX_EVIDENCE_BYTES:
            raise DesignEditorialAssetProvenanceError(
                f"Immutable editorial rights output is outside the size limit: {relative}."
            )
        targets.append(target)

    committed: list[tuple[Path, str]] = []
    staged_paths: list[Path] = []
    try:
        for (relative, payload), target in zip(outputs, targets, strict=True):
            encoded = _encoded_json(payload)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=str(target.parent),
            )
            temporary = Path(temporary_name)
            staged_paths.append(temporary)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            temporary_relative = temporary.relative_to(root).as_posix()
            _, safety = _file_safety(
                root,
                temporary_relative,
                max_bytes=_MAX_EVIDENCE_BYTES,
            )
            expected_sha256 = hashlib.sha256(encoded).hexdigest().upper()
            if not safety["regular_file"] or _sha256_file(temporary) != expected_sha256:
                raise DesignEditorialAssetProvenanceError(
                    f"Immutable editorial rights output staging failed: {relative}."
                )
            prepared.append((temporary, target, expected_sha256))

        precommit()
        for temporary, target, expected_sha256 in prepared:
            try:
                _exclusive_link(temporary, target)
            except FileExistsError as exc:
                raise DesignEditorialAssetProvenanceError(
                    f"Immutable editorial rights output already exists: "
                    f"{target.relative_to(root).as_posix()}."
                ) from exc
            except OSError as exc:
                raise DesignEditorialAssetProvenanceError(
                    "Could not atomically retain immutable editorial rights output: "
                    f"{target.relative_to(root).as_posix()}."
                ) from exc
            committed.append((target, expected_sha256))

        for temporary in staged_paths:
            temporary.unlink()
        staged_paths.clear()

        for target, expected_sha256 in committed:
            relative = target.relative_to(root).as_posix()
            _, safety = _file_safety(
                root,
                relative,
                max_bytes=_MAX_EVIDENCE_BYTES,
            )
            if not safety["regular_file"] or _sha256_file(target) != expected_sha256:
                raise DesignEditorialAssetProvenanceError(
                    f"Immutable editorial rights output failed exact read-back: {relative}."
                )
            _fsync_directory(target.parent)
        postcommit()
        return [target for target, _ in committed]
    except Exception as exc:
        rollback_failures: list[str] = []
        for target, expected_sha256 in reversed(committed):
            try:
                if target.is_file() and not target.is_symlink() and _sha256_file(target) == expected_sha256:
                    target.unlink()
                elif target.exists() or target.is_symlink():
                    rollback_failures.append(target.relative_to(root).as_posix())
            except OSError:
                rollback_failures.append(target.relative_to(root).as_posix())
        for temporary in staged_paths:
            try:
                if temporary.exists() or temporary.is_symlink():
                    temporary.unlink()
            except OSError:
                rollback_failures.append(temporary.relative_to(root).as_posix())
        if rollback_failures:
            raise DesignEditorialAssetProvenanceError(
                "Editorial rights preparation failed and could not prove complete "
                f"rollback for: {sorted(set(rollback_failures))}."
            ) from exc
        raise


def prepare_editorial_asset_rights_decisions(
    request: Mapping[str, Any],
    *,
    manifest_path: Path | None = None,
    repo_root: Path | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Persist explicit per-asset decisions and a proposal without binding them.

    The caller must supply the exact controlled request. This function records
    that explicit human decision; it never infers rights, edits the canonical
    manifest, changes the global ``not-cleared`` policy, or grants candidate,
    package, release, credential, network, or deployment authority.
    """

    root = _find_repo_root(repo_root)
    canonical_path, canonical_relative = _canonical_manifest_path(
        root,
        manifest_path,
    )
    normalised = _normalise_rights_preparation_request(request)
    if _sha256_file(canonical_path) != normalised["manifest_sha256"]:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation manifest SHA-256 does not "
            "match the exact current canonical manifest."
        )
    reviewed_at = (as_of or datetime.now(UTC)).astimezone(UTC)
    decided_at = _parse_datetime(
        normalised["decided_at"],
        label="Editorial rights decision preparation decided_at",
    )
    if decided_at > reviewed_at:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation cannot be future-dated."
        )
    asset_ids = [str(value) for value in normalised["asset_ids"]]
    snapshot = _rights_preparation_snapshot(
        root=root,
        manifest_path=canonical_path,
        asset_ids=asset_ids,
        decided_at=decided_at,
        reviewed_at=reviewed_at,
    )
    if snapshot["manifest_sha256"] != normalised["manifest_sha256"]:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation manifest SHA-256 drifted "
            "during the current provenance re-audit."
        )
    requested_asset_scopes = normalised["asset_scopes"]
    if not isinstance(requested_asset_scopes, Mapping) or requested_asset_scopes != snapshot["asset_scopes"]:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation asset_scopes do not match "
            "the exact current re-audited asset scopes."
        )
    request_sha256 = _json_sha256(normalised)
    decision_outputs: list[tuple[str, Mapping[str, Any]]] = []
    bindings: list[dict[str, Any]] = []
    asset_scopes = requested_asset_scopes
    timestamp = decided_at.strftime("%Y%m%dT%H%M%SZ").casefold()
    for asset_id in asset_ids:
        scope = _sha256(
            asset_scopes.get(asset_id),
            label=f"{asset_id} explicitly acknowledged asset scope SHA-256",
        )
        decision_seed = hashlib.sha256(f"{request_sha256}:{asset_id}".encode()).hexdigest()
        decision_id = f"rights-{timestamp}-{decision_seed[:24]}"
        decision: dict[str, Any] = {
            "schema": RIGHTS_DECISION_SCHEMA,
            "decision_id": decision_id,
            "asset_id": asset_id,
            "decision": normalised["decision"],
            "decided_by": normalised["decided_by"],
            "decided_at": normalised["decided_at"],
            "rights_basis": normalised["rights_basis"],
            "usage_scope": normalised["usage_scope"],
            "asset_scope_sha256": scope,
            "boundary_acknowledgement": normalised["boundary_acknowledgement"],
        }
        decision_path = _decision_output_path(
            asset_id=asset_id,
            decided_at=decided_at,
            request_sha256=request_sha256,
        )
        decision_sha256 = hashlib.sha256(_encoded_json(decision)).hexdigest().upper()
        decision_outputs.append((decision_path, decision))
        bindings.append(
            {
                "asset_id": asset_id,
                "asset_scope_sha256": scope,
                "rights_decision": {
                    "state": normalised["decision"],
                    "named_human_decision": True,
                    "decision_evidence": {
                        "path": decision_path,
                        "sha256": decision_sha256,
                    },
                },
            }
        )

    proposal_path = _proposal_output_path(
        decided_at=decided_at,
        request_sha256=request_sha256,
    )
    proposal: dict[str, Any] = {
        "schema": RIGHTS_BINDING_PROPOSAL_SCHEMA,
        "state": "manifest-binding-proposal-only",
        "prepared_at": _iso(reviewed_at),
        "proposal_path": proposal_path,
        "request_sha256": request_sha256,
        "request": {
            "decision": normalised["decision"],
            "decided_at": normalised["decided_at"],
            "manifest_sha256": normalised["manifest_sha256"],
            "rights_basis": normalised["rights_basis"],
            "asset_ids_sha256": _json_sha256(asset_ids),
            "asset_scopes_sha256": _json_sha256(requested_asset_scopes),
            "usage_scope": normalised["usage_scope"],
            "boundary_acknowledgement": normalised["boundary_acknowledgement"],
        },
        "manifest": {
            "path": canonical_relative,
            "manifest_id": snapshot["manifest_id"],
            "sha256": snapshot["manifest_sha256"],
            "json_sha256": snapshot["manifest_json_sha256"],
            "provenance_audit_sha256": snapshot["provenance_audit_sha256"],
            "global_artwork_policy": "not-cleared",
            "mutated": False,
        },
        "proposed_bindings": bindings,
        "summary": {
            "requested_asset_count": len(asset_ids),
            "separate_decision_file_count": len(bindings),
            "proposed_manifest_binding_count": len(bindings),
            "canonical_manifest_mutation_count": 0,
        },
        "privacy": {
            **PRIVACY_BOUNDARY,
            "reviewer_identity_in_proposal": "excluded",
            "decision_files": "controlled rights-decisions root only",
        },
        "authority": RIGHTS_PREPARATION_AUTHORITY,
        "receipt_authority": False,
        "candidate_use_rights_ready": False,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "next_gate": (
            "A separate controlled review may bind each exact proposal into the "
            "canonical provenance manifest; rerun the current provenance audit "
            "before any candidate asset workflow."
        ),
    }
    proposal["proposal_sha256"] = _json_sha256(proposal)

    def assert_snapshot_current() -> None:
        _assert_rights_preparation_snapshot_current(
            root=root,
            manifest_path=canonical_path,
            snapshot=snapshot,
        )

    _write_immutable_json_batch(
        [*decision_outputs, (proposal_path, proposal)],
        root=root,
        precommit=assert_snapshot_current,
        postcommit=assert_snapshot_current,
    )
    return proposal


def _read_rights_preparation_request_file(
    path: Path,
    *,
    root: Path,
) -> dict[str, Any]:
    candidate = path if path.is_absolute() else root / path
    lexical = Path(os.path.abspath(candidate))
    try:
        relative = lexical.relative_to(root).as_posix()
    except ValueError as exc:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights preparation request must remain inside the repository."
        ) from exc
    if not _under_prefix(relative, DEFAULT_RIGHTS_REQUEST_ROOT.as_posix()):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights preparation request must remain below "
            f"{DEFAULT_RIGHTS_REQUEST_ROOT.as_posix()}/."
        )
    unresolved, safety = _file_safety(
        root,
        relative,
        max_bytes=_MAX_EVIDENCE_BYTES,
    )
    if not safety["regular_file"] or unresolved.suffix.casefold() != ".json":
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights preparation request must be one regular, single-link, reparse-free JSON file."
        )
    try:
        parsed = json.loads(
            unresolved.read_text(encoding="utf-8-sig"),
            object_pairs_hook=_strict_json_object,
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        _DuplicateJSONKeyError,
    ) as exc:
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation request must be strict "
            "UTF-8 JSON without duplicate object keys."
        ) from exc
    if not isinstance(parsed, Mapping):
        raise DesignEditorialAssetProvenanceError(
            "Editorial rights decision preparation request must be one JSON object."
        )
    return dict(parsed)


def write_editorial_asset_provenance_audit(
    receipt: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Persist one immutable, privacy-redacted audit below ``docs/audits``."""

    if receipt.get("schema") != AUDIT_SCHEMA:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset audit output requires the canonical audit schema."
        )
    if receipt.get("receipt_authority") is not False:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset audit output cannot grant receipt authority."
        )
    if receipt.get("release_eligible") is not False:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset audit output cannot grant release authority."
        )
    if receipt.get("package_authority") != "none" or receipt.get("deployment_authority") != "none":
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset audit output cannot grant package or deployment authority."
        )

    root = _find_repo_root(repo_root)
    target = output_path if output_path.is_absolute() else root / output_path
    target = target.resolve()
    allowed = (root / DEFAULT_AUDIT_ROOT).resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise DesignEditorialAssetProvenanceError(
            "Editorial asset audits must stay below docs/audits/."
        ) from exc
    if target.exists() or target.is_symlink():
        raise DesignEditorialAssetProvenanceError("Editorial asset audit output already exists.")

    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
    try:
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(encoded)
    except FileExistsError as exc:
        raise DesignEditorialAssetProvenanceError("Editorial asset audit output already exists.") from exc
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit exact Aureon editorial artwork provenance and rights without "
            "importing assets or mutating a website. An explicit preparation "
            "request may record separate immutable per-asset decisions and a "
            "proposal-only binding receipt without changing the manifest."
        )
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--prepare-rights-request",
        type=Path,
        help=(
            "Read one strict, manifest- and asset-scope-bound v1 request below "
            "artifacts/website-operator/editorial-rights-requests/ and write "
            "separate immutable decisions plus a proposal-only artifact."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.prepare_rights_request is not None:
        if args.output is not None:
            raise DesignEditorialAssetProvenanceError(
                "--output cannot be combined with --prepare-rights-request."
            )
        root = _find_repo_root(args.repo_root)
        request = _read_rights_preparation_request_file(
            args.prepare_rights_request,
            root=root,
        )
        proposal = prepare_editorial_asset_rights_decisions(
            request,
            manifest_path=args.manifest,
            repo_root=root,
        )
        print(json.dumps(proposal, ensure_ascii=True, indent=2))
        return 0
    receipt = audit_design_editorial_asset_provenance_file(
        args.manifest,
        repo_root=args.repo_root,
    )
    if args.output:
        write_editorial_asset_provenance_audit(
            receipt,
            args.output,
            repo_root=args.repo_root,
        )
    else:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
