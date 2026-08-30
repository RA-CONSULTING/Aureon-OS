"""Verify static website runtime measurement integrity without producing it.

The verifier authenticates one pre-existing measurement document, replays the
complete ``website/`` file manifest, and checks two independently stored but
byte-identical derivative replicas.  Image media type and dimensions come from
PNG, JPEG, or WebP headers rather than filenames or declarations.  Header
inspection is not a full decode, and byte copies placed under a different run
remain copyable static artifacts rather than independently produced evidence.

This module has no encoder, subprocess, writer, emitter, candidate, package,
release, deployment, network, or credential capability.  A passing result is
deliberately production-blocked and is not eligible for proposal compilation.
The isolated launcher binds exact supplied source hashes, but reviewed pins
remain external governance inputs and are not established by this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Final

MEASUREMENT_SCHEMA = "aureon.website-runtime-measurement-static-integrity.v1"
VERIFIED_STATE = "static-integrity-verified-production-blocked"
VERIFICATION_MODE = "static-artifact-integrity-only"
SOURCE_ROOT = Path("website")
IMPLEMENTATION_PATH = Path("aureon/operator/website_runtime_measurement_provenance.py")
TRUSTED_LAUNCHER_PATH = Path("tools/run-website-runtime-measurement-provenance.py")
REPLICA_ROOT = PurePosixPath(
    "artifacts/website-operator/runtime-optimisations/measurement-provenance/replicas"
)
MEASUREMENT_ROOT = PurePosixPath("artifacts/website-operator/runtime-optimisations/measurements")

MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_REVIEWED_SOURCE_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TREE_BYTES = 512 * 1024 * 1024
MAX_FILES = 5_000
MAX_TRANSFORMATIONS = 5_000
MAX_DIMENSION = 20_000
MAX_PIXELS = 400_000_000
MAX_CLOCK_SKEW = timedelta(minutes=5)


NO_AUTHORITY: Final[Mapping[str, object]] = MappingProxyType(
    {
        "scope": "read-only static artifact integrity verification only",
        "source_selection_authority": "none",
        "measurement_creation_authority": "none",
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "encoding_execution": "none",
        "css_transformation_execution": "none",
        "reference_mutation": "none",
        "candidate_authority": "none",
        "staging_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "network_access": "none",
        "credential_access": "none",
    }
)

_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_SAFE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,80}\Z")
_UTC_DATE_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z\Z")
_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
_MEDIA_SUFFIXES: Final[Mapping[str, frozenset[str]]] = {
    "image/png": frozenset({".png"}),
    "image/jpeg": frozenset({".jpg", ".jpeg"}),
    "image/webp": frozenset({".webp"}),
}
_TOP_FIELDS = frozenset(
    {
        "schema",
        "observed_at",
        "run_id",
        "state",
        "mode",
        "source_manifest",
        "transformations",
        "summary",
        "eligible_for_proposal_compilation",
        "authority",
        "payload_sha256",
    }
)
_MANIFEST_FIELDS = frozenset({"root", "file_count", "total_bytes", "manifest_sha256", "tree_sha256", "files"})
_FILE_FIELDS = frozenset({"path", "bytes", "sha256"})
_TRANSFORMATION_FIELDS = frozenset(
    {
        "id",
        "source_path",
        "source_sha256",
        "source_bytes",
        "source_media_type",
        "source_width",
        "source_height",
        "projected_runtime_path",
        "projected_sha256",
        "projected_bytes",
        "projected_media_type",
        "projected_width",
        "projected_height",
        "expected_saving_bytes",
        "replicas",
        "source_master_preserved",
        "execution_state",
    }
)
_REPLICA_FIELDS = frozenset({"role", "path", "file_sha256", "bytes", "media_type", "width", "height"})
_SUMMARY_FIELDS = frozenset(
    {
        "transformation_count",
        "source_bytes",
        "projected_bytes",
        "expected_saving_bytes",
        "replica_bytes",
    }
)


class WebsiteRuntimeMeasurementProvenanceError(ValueError):
    """The static measurement evidence or one of its bound files is unsafe."""


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WebsiteRuntimeMeasurementProvenanceError("Value is not canonical JSON.") from exc


def _json_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest().upper()


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _expect_fields(value: object, expected: frozenset[str], *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} must contain exactly its defined fields.")
    if any(not isinstance(key, str) for key in value):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} field names must be strings.")
    return value


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} must be a string.")
    return value


def _integer(value: object, *, label: str, minimum: int = 0, maximum: int = MAX_FILE_BYTES) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} is outside its integer bound.")
    return value


def _sha256(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    if _SHA256.fullmatch(result) is None:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} must be 64 uppercase hexadecimal digits.")
    return result


def _safe_id(value: object, *, label: str) -> str:
    result = _string(value, label=label)
    if _SAFE_ID.fullmatch(result) is None:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} is not a safe identifier.")
    return result


def _safe_relative(value: object, *, label: str) -> PurePosixPath:
    raw = _string(value, label=label)
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\" in raw
        or "\x00" in raw
        or raw.startswith("/")
        or raw.endswith("/")
        or "//" in raw
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != raw
    ):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} is not a safe relative POSIX path.")
    for part in path.parts:
        if (
            unicodedata.normalize("NFC", part) != part
            or part.endswith((" ", "."))
            or any(ord(character) < 32 or character in '<>:"|?*' for character in part)
        ):
            raise WebsiteRuntimeMeasurementProvenanceError(
                f"{label} contains a non-portable or alias-prone path component."
            )
    return path


def _is_link_or_reparse(path: Path) -> bool:
    details = path.lstat()
    attributes = int(getattr(details, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400) or 0x400)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & reparse)


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
        and int(left.st_dev) == int(right.st_dev)
        and int(left.st_ino) == int(right.st_ino)
    )


def _repo_root(value: Path) -> Path:
    root = Path(os.path.abspath(value))
    for component in (root, *root.parents):
        if (component.exists() or component.is_symlink()) and _is_link_or_reparse(component):
            raise WebsiteRuntimeMeasurementProvenanceError(
                "Repository root may not cross a link or reparse point."
            )
    if not root.is_dir():
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Repository root must be an ordinary, non-reparse directory."
        )
    return root


def _joined_path(root: Path, relative: PurePosixPath, *, label: str) -> Path:
    target = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current /= part
        if (current.exists() or current.is_symlink()) and _is_link_or_reparse(current):
            raise WebsiteRuntimeMeasurementProvenanceError(f"{label} may not cross a link or reparse point.")
    try:
        common = os.path.commonpath((str(root), str(target)))
    except ValueError as exc:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} escapes the repository.") from exc
    if os.path.normcase(common) != os.path.normcase(str(root)):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} escapes the repository.")
    return target


def _read_ordinary_file(
    path: Path,
    *,
    label: str,
    maximum_bytes: int = MAX_FILE_BYTES,
    expected_sha256: str | None = None,
    expected_bytes: int | None = None,
) -> bytes:
    if not path.is_file() or _is_link_or_reparse(path):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} must be an ordinary file.")
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or int(before.st_nlink) != 1:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} must be an ordinary single-link file.")
    size = int(before.st_size)
    if size > maximum_bytes or (expected_bytes is not None and size != expected_bytes):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} byte count does not match its binding.")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not _same_identity(before, opened):
            raise WebsiteRuntimeMeasurementProvenanceError(f"{label} changed before its handle opened.")
        payload = stream.read(maximum_bytes + 1)
    after = path.lstat()
    if (
        len(payload) > maximum_bytes
        or len(payload) != size
        or not _same_identity(opened, after)
        or int(after.st_nlink) != 1
    ):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} changed while it was read.")
    if expected_sha256 is not None and _bytes_sha256(payload) != expected_sha256:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} SHA-256 does not match its binding.")
    return payload


def _reject_constant(value: str) -> object:
    raise WebsiteRuntimeMeasurementProvenanceError(f"JSON constant {value!r} is not permitted.")


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise WebsiteRuntimeMeasurementProvenanceError(f"Duplicate JSON field {key!r} is not permitted.")
        result[key] = value
    return result


def _load_json(payload: bytes, *, label: str) -> dict[str, Any]:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} may not contain a UTF-8 BOM.")
    try:
        text = payload.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_pairs_object, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} is not strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} must be a JSON object.")
    return value


def _manifest_row(relative: str, payload: bytes) -> dict[str, object]:
    return {"path": relative, "bytes": len(payload), "sha256": _bytes_sha256(payload)}


def _snapshot_website(root: Path) -> dict[str, object]:
    website = _joined_path(root, PurePosixPath(SOURCE_ROOT.as_posix()), label="Website root")
    if not website.is_dir() or _is_link_or_reparse(website):
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Website source root must be an ordinary, non-reparse directory."
        )
    pending: list[tuple[Path, PurePosixPath]] = [(website, PurePosixPath("."))]
    rows: list[dict[str, object]] = []
    portable_paths: set[str] = set()
    total = 0
    while pending:
        directory, relative_directory = pending.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise WebsiteRuntimeMeasurementProvenanceError("Website source tree cannot be scanned.") from exc
        for entry in entries:
            entry_path = Path(entry.path)
            relative = (
                PurePosixPath(entry.name)
                if relative_directory == PurePosixPath(".")
                else relative_directory / entry.name
            )
            _safe_relative(relative.as_posix(), label="Website source tree path")
            portable = unicodedata.normalize("NFC", relative.as_posix()).casefold()
            if portable in portable_paths:
                raise WebsiteRuntimeMeasurementProvenanceError(
                    "Website source tree contains a portable case-fold path collision."
                )
            portable_paths.add(portable)
            details = entry_path.lstat()
            attributes = int(getattr(details, "st_file_attributes", 0) or 0)
            if entry.is_symlink() or bool(
                attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400) or 0x400)
            ):
                raise WebsiteRuntimeMeasurementProvenanceError(
                    "Website source tree may not contain links or reparse points."
                )
            if stat.S_ISDIR(details.st_mode):
                pending.append((entry_path, relative))
                continue
            if not stat.S_ISREG(details.st_mode) or int(details.st_nlink) != 1:
                raise WebsiteRuntimeMeasurementProvenanceError(
                    "Website source tree may contain only ordinary single-link files."
                )
            if len(rows) >= MAX_FILES or int(details.st_size) > MAX_TREE_BYTES - total:
                raise WebsiteRuntimeMeasurementProvenanceError(
                    "Website source tree exceeds its fixed bounds."
                )
            payload = _read_ordinary_file(
                entry_path,
                label=f"Website source file {relative.as_posix()}",
                maximum_bytes=MAX_TREE_BYTES - total,
            )
            total += len(payload)
            rows.append(_manifest_row(relative.as_posix(), payload))
    rows.sort(key=lambda row: str(row["path"]))
    digest = _json_sha256(rows)
    return {
        "root": SOURCE_ROOT.as_posix(),
        "file_count": len(rows),
        "total_bytes": total,
        "manifest_sha256": digest,
        "tree_sha256": digest,
        "files": rows,
    }


def _dimension(value: object, *, label: str) -> int:
    return _integer(value, label=label, minimum=1, maximum=MAX_DIMENSION)


def _validate_dimensions(width: int, height: int, *, label: str) -> None:
    if width * height > MAX_PIXELS:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} pixel count exceeds its bound.")


def _png_probe(payload: bytes) -> tuple[str, int, int]:
    if (
        len(payload) < 24
        or payload[:8] != b"\x89PNG\r\n\x1a\n"
        or payload[12:16] != b"IHDR"
        or int.from_bytes(payload[8:12], "big") != 13
    ):
        raise WebsiteRuntimeMeasurementProvenanceError("PNG header is invalid or incomplete.")
    return "image/png", int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")


def _jpeg_probe(payload: bytes) -> tuple[str, int, int]:
    if len(payload) < 4 or payload[:2] != b"\xff\xd8":
        raise WebsiteRuntimeMeasurementProvenanceError("JPEG header is invalid or incomplete.")
    position = 2
    start_of_frame = frozenset({0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF})
    while position < len(payload):
        if payload[position] != 0xFF:
            break
        while position < len(payload) and payload[position] == 0xFF:
            position += 1
        if position >= len(payload):
            break
        marker = payload[position]
        position += 1
        if marker == 0xDA:
            break
        if marker in {0x01, *range(0xD0, 0xD9)}:
            continue
        if position + 2 > len(payload):
            break
        segment_length = int.from_bytes(payload[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > len(payload):
            break
        if marker in start_of_frame:
            if segment_length < 7:
                break
            height = int.from_bytes(payload[position + 3 : position + 5], "big")
            width = int.from_bytes(payload[position + 5 : position + 7], "big")
            return "image/jpeg", width, height
        position += segment_length
    raise WebsiteRuntimeMeasurementProvenanceError("JPEG dimensions are absent from its header.")


def _webp_probe(payload: bytes) -> tuple[str, int, int]:
    if (
        len(payload) < 30
        or payload[:4] != b"RIFF"
        or payload[8:12] != b"WEBP"
        or int.from_bytes(payload[4:8], "little") + 8 != len(payload)
    ):
        raise WebsiteRuntimeMeasurementProvenanceError("WebP header is invalid or incomplete.")
    kind = payload[12:16]
    chunk_size = int.from_bytes(payload[16:20], "little")
    if 20 + chunk_size > len(payload):
        raise WebsiteRuntimeMeasurementProvenanceError("WebP chunk exceeds its file bound.")
    if kind == b"VP8X" and chunk_size >= 10:
        width = 1 + int.from_bytes(payload[24:27], "little")
        height = 1 + int.from_bytes(payload[27:30], "little")
    elif kind == b"VP8 " and chunk_size >= 10 and payload[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(payload[26:28], "little") & 0x3FFF
        height = int.from_bytes(payload[28:30], "little") & 0x3FFF
    elif kind == b"VP8L" and chunk_size >= 5 and payload[20] == 0x2F:
        b1, b2, b3, b4 = payload[21:25]
        width = 1 + (((b2 & 0x3F) << 8) | b1)
        height = 1 + (((b4 & 0x0F) << 10) | (b3 << 2) | ((b2 & 0xC0) >> 6))
    else:
        raise WebsiteRuntimeMeasurementProvenanceError("WebP dimensions are absent from its header.")
    return "image/webp", width, height


def _image_probe(payload: bytes, *, label: str) -> tuple[str, int, int]:
    try:
        if payload.startswith(b"\x89PNG"):
            result = _png_probe(payload)
        elif payload.startswith(b"\xff\xd8"):
            result = _jpeg_probe(payload)
        elif payload.startswith(b"RIFF"):
            result = _webp_probe(payload)
        else:
            raise WebsiteRuntimeMeasurementProvenanceError("unsupported image header")
    except WebsiteRuntimeMeasurementProvenanceError as exc:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{label} has no valid PNG/JPEG/WebP header.") from exc
    _validate_dimensions(result[1], result[2], label=label)
    return result


def _require_media_path(path: PurePosixPath, media_type: str, *, label: str) -> None:
    if media_type not in _MEDIA_TYPES or path.suffix.lower() not in _MEDIA_SUFFIXES[media_type]:
        raise WebsiteRuntimeMeasurementProvenanceError(
            f"{label} suffix does not match its header-derived media type."
        )


def _require_declared_manifest(value: object, actual: Mapping[str, object]) -> list[Mapping[str, Any]]:
    manifest = _expect_fields(value, _MANIFEST_FIELDS, label="source_manifest")
    if manifest["root"] != SOURCE_ROOT.as_posix():
        raise WebsiteRuntimeMeasurementProvenanceError("source_manifest.root must be website.")
    files = manifest["files"]
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise WebsiteRuntimeMeasurementProvenanceError("source_manifest.files exceeds its list bound.")
    checked: list[Mapping[str, Any]] = []
    previous = ""
    for index, item in enumerate(files):
        row = _expect_fields(item, _FILE_FIELDS, label=f"source_manifest.files[{index}]")
        path = _safe_relative(row["path"], label=f"source_manifest.files[{index}].path").as_posix()
        if path <= previous:
            raise WebsiteRuntimeMeasurementProvenanceError(
                "source_manifest.files must be unique and strictly path-sorted."
            )
        previous = path
        _integer(row["bytes"], label=f"source_manifest.files[{index}].bytes", maximum=MAX_TREE_BYTES)
        _sha256(row["sha256"], label=f"source_manifest.files[{index}].sha256")
        checked.append(row)
    digest = _json_sha256([dict(row) for row in checked])
    if (
        _integer(manifest["file_count"], label="source_manifest.file_count", maximum=MAX_FILES)
        != len(checked)
        or _integer(manifest["total_bytes"], label="source_manifest.total_bytes", maximum=MAX_TREE_BYTES)
        != sum(int(row["bytes"]) for row in checked)
        or _sha256(manifest["manifest_sha256"], label="source_manifest.manifest_sha256") != digest
        or _sha256(manifest["tree_sha256"], label="source_manifest.tree_sha256") != digest
        or dict(manifest) != dict(actual)
    ):
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Declared source manifest does not exactly match the complete website tree."
        )
    return checked


def _require_replica(
    root: Path,
    value: object,
    *,
    role: str,
    run_id: str,
    transformation_id: str,
    index: int,
) -> tuple[Mapping[str, Any], bytes, tuple[str, int, int]]:
    row = _expect_fields(value, _REPLICA_FIELDS, label=f"replicas[{index}]")
    if row["role"] != role:
        raise WebsiteRuntimeMeasurementProvenanceError("Replica roles must be replica-a then replica-b.")
    relative = _safe_relative(row["path"], label=f"replicas[{index}].path")
    required_prefix = REPLICA_ROOT / run_id / transformation_id / role
    if relative.parts[: len(required_prefix.parts)] != required_prefix.parts:
        raise WebsiteRuntimeMeasurementProvenanceError(f"{role} must be stored below its fixed replica root.")
    expected_hash = _sha256(row["file_sha256"], label=f"replicas[{index}].file_sha256")
    expected_bytes = _integer(row["bytes"], label=f"replicas[{index}].bytes", minimum=1)
    payload = _read_ordinary_file(
        _joined_path(root, relative, label=f"{role} artifact"),
        label=f"{role} artifact",
        expected_sha256=expected_hash,
        expected_bytes=expected_bytes,
    )
    probed = _image_probe(payload, label=f"{role} artifact")
    media_type = _string(row["media_type"], label=f"replicas[{index}].media_type")
    width = _dimension(row["width"], label=f"replicas[{index}].width")
    height = _dimension(row["height"], label=f"replicas[{index}].height")
    _validate_dimensions(width, height, label=f"replicas[{index}]")
    _require_media_path(relative, media_type, label=f"replicas[{index}].path")
    if probed != (media_type, width, height):
        raise WebsiteRuntimeMeasurementProvenanceError(
            f"{role} header does not match its media and dimension binding."
        )
    return row, payload, probed


def _require_transformations(
    root: Path,
    value: object,
    manifest_rows: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
) -> dict[str, int]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_TRANSFORMATIONS:
        raise WebsiteRuntimeMeasurementProvenanceError("transformations must be a bounded non-empty list.")
    manifest = {str(row["path"]): row for row in manifest_rows}
    ids: set[str] = set()
    source_paths: set[str] = set()
    projected_paths: set[str] = set()
    replica_paths: set[str] = set()
    totals = {
        "transformation_count": len(value),
        "source_bytes": 0,
        "projected_bytes": 0,
        "expected_saving_bytes": 0,
        "replica_bytes": 0,
    }
    for index, item in enumerate(value):
        row = _expect_fields(item, _TRANSFORMATION_FIELDS, label=f"transformations[{index}]")
        transform_id = _safe_id(row["id"], label=f"transformations[{index}].id")
        source_path = _safe_relative(row["source_path"], label=f"transformations[{index}].source_path")
        projected_path = _safe_relative(
            row["projected_runtime_path"],
            label=f"transformations[{index}].projected_runtime_path",
        )
        if (
            transform_id in ids
            or source_path.as_posix() in source_paths
            or projected_path.as_posix() in projected_paths
        ):
            raise WebsiteRuntimeMeasurementProvenanceError(
                "Transformation ids, source paths, and projected paths must each be unique."
            )
        ids.add(transform_id)
        source_paths.add(source_path.as_posix())
        projected_paths.add(projected_path.as_posix())
        source_manifest_row = manifest.get(source_path.as_posix())
        source_hash = _sha256(row["source_sha256"], label=f"transformations[{index}].source_sha256")
        source_bytes = _integer(
            row["source_bytes"], label=f"transformations[{index}].source_bytes", minimum=1
        )
        if source_manifest_row is None or dict(source_manifest_row) != {
            "path": source_path.as_posix(),
            "bytes": source_bytes,
            "sha256": source_hash,
        }:
            raise WebsiteRuntimeMeasurementProvenanceError(
                "Transformation source does not exactly bind one complete-manifest file."
            )
        source_payload = _read_ordinary_file(
            _joined_path(root / SOURCE_ROOT, source_path, label="Transformation source"),
            label=f"Transformation source {source_path.as_posix()}",
            expected_sha256=source_hash,
            expected_bytes=source_bytes,
        )
        source_probe = _image_probe(source_payload, label="Transformation source")
        source_media = _string(row["source_media_type"], label=f"transformations[{index}].source_media_type")
        source_width = _dimension(row["source_width"], label=f"transformations[{index}].source_width")
        source_height = _dimension(row["source_height"], label=f"transformations[{index}].source_height")
        _require_media_path(source_path, source_media, label="Transformation source_path")
        if source_probe != (source_media, source_width, source_height):
            raise WebsiteRuntimeMeasurementProvenanceError(
                "Transformation source header does not match its media and dimension binding."
            )
        replicas = row["replicas"]
        if not isinstance(replicas, list) or len(replicas) != 2:
            raise WebsiteRuntimeMeasurementProvenanceError(
                "Every transformation requires exactly two replicas."
            )
        replica_a, payload_a, probe_a = _require_replica(
            root,
            replicas[0],
            role="replica-a",
            run_id=run_id,
            transformation_id=transform_id,
            index=0,
        )
        replica_b, payload_b, probe_b = _require_replica(
            root,
            replicas[1],
            role="replica-b",
            run_id=run_id,
            transformation_id=transform_id,
            index=1,
        )
        paths = {str(replica_a["path"]), str(replica_b["path"])}
        if len(paths) != 2 or replica_paths.intersection(paths):
            raise WebsiteRuntimeMeasurementProvenanceError(
                "Replica artifact paths must be globally distinct."
            )
        replica_paths.update(paths)
        if payload_a != payload_b or dict(replica_a) | {"role": "replica-a", "path": ""} != dict(
            replica_b
        ) | {"role": "replica-a", "path": ""}:
            raise WebsiteRuntimeMeasurementProvenanceError(
                "The two replica artifacts and their non-location bindings must be identical."
            )
        projected_hash = _sha256(row["projected_sha256"], label=f"transformations[{index}].projected_sha256")
        projected_bytes = _integer(
            row["projected_bytes"], label=f"transformations[{index}].projected_bytes", minimum=1
        )
        projected_media = _string(
            row["projected_media_type"], label=f"transformations[{index}].projected_media_type"
        )
        projected_width = _dimension(
            row["projected_width"], label=f"transformations[{index}].projected_width"
        )
        projected_height = _dimension(
            row["projected_height"], label=f"transformations[{index}].projected_height"
        )
        _require_media_path(projected_path, projected_media, label="projected_runtime_path")
        expected_saving = _integer(
            row["expected_saving_bytes"],
            label=f"transformations[{index}].expected_saving_bytes",
            minimum=1,
        )
        if (
            projected_hash != str(replica_a["file_sha256"])
            or projected_bytes != int(replica_a["bytes"])
            or probe_a != probe_b
            or probe_a != (projected_media, projected_width, projected_height)
            or (projected_width, projected_height) != (source_width, source_height)
            or source_bytes - projected_bytes != expected_saving
            or projected_bytes >= source_bytes
            or row["source_master_preserved"] is not True
            or row["execution_state"] != "pre-existing-static-artifacts-only"
        ):
            raise WebsiteRuntimeMeasurementProvenanceError(
                "Transformation integrity, dimensions, arithmetic, or static-only state is invalid."
            )
        totals["source_bytes"] += source_bytes
        totals["projected_bytes"] += projected_bytes
        totals["expected_saving_bytes"] += expected_saving
        totals["replica_bytes"] += projected_bytes * 2
    return totals


def require_measurement_provenance(
    value: object,
    *,
    repo_root: Path,
    source_snapshot: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Validate one static-integrity document and every file it binds, without writing.

    This compatibility name does not imply producer, invocation, decode, or
    source-plan provenance.  Prefer ``require_static_measurement_integrity``.
    """

    root = _repo_root(repo_root)
    document = _expect_fields(value, _TOP_FIELDS, label="measurement evidence")
    if document["schema"] != MEASUREMENT_SCHEMA:
        raise WebsiteRuntimeMeasurementProvenanceError("Measurement schema is not static-integrity v1.")
    run_id = _safe_id(document["run_id"], label="run_id")
    observed_at = _string(document["observed_at"], label="observed_at")
    if _UTC_DATE_TIME.fullmatch(observed_at) is None:
        raise WebsiteRuntimeMeasurementProvenanceError(
            "observed_at must be an exact UTC date-time ending in Z."
        )
    try:
        observed = datetime.fromisoformat(observed_at.removesuffix("Z") + "+00:00").astimezone(UTC)
    except ValueError as exc:
        raise WebsiteRuntimeMeasurementProvenanceError("observed_at is not a valid timestamp.") from exc
    if observed > datetime.now(UTC) + MAX_CLOCK_SKEW:
        raise WebsiteRuntimeMeasurementProvenanceError(
            "observed_at exceeds the maximum five-minute future clock skew."
        )
    # Deliberately local and duplicated: validation must not resolve a
    # rebindable module-level authority object or constructor.
    canonical_authority: dict[str, object] = {
        "scope": "read-only static artifact integrity verification only",
        "source_selection_authority": "none",
        "measurement_creation_authority": "none",
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "encoding_execution": "none",
        "css_transformation_execution": "none",
        "reference_mutation": "none",
        "candidate_authority": "none",
        "staging_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "network_access": "none",
        "credential_access": "none",
    }
    if (
        document["state"] != VERIFIED_STATE
        or document["mode"] != VERIFICATION_MODE
        or document["eligible_for_proposal_compilation"] is not False
        or document["authority"] != canonical_authority
    ):
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Measurement state, mode, eligibility, and authority must remain production-blocked."
        )
    expected_payload_hash = _sha256(document["payload_sha256"], label="payload_sha256")
    payload = dict(document)
    payload.pop("payload_sha256")
    if _json_sha256(payload) != expected_payload_hash:
        raise WebsiteRuntimeMeasurementProvenanceError("Measurement payload SHA-256 is invalid.")
    first_snapshot = dict(source_snapshot or _snapshot_website(root))
    manifest_rows = _require_declared_manifest(document["source_manifest"], first_snapshot)
    totals = _require_transformations(
        root,
        document["transformations"],
        manifest_rows,
        run_id=run_id,
    )
    summary = _expect_fields(document["summary"], _SUMMARY_FIELDS, label="summary")
    checked_summary = {
        key: _integer(
            summary[key],
            label=f"summary.{key}",
            minimum=1,
            maximum=(MAX_FILE_BYTES * MAX_TRANSFORMATIONS * 2),
        )
        for key in _SUMMARY_FIELDS
    }
    if checked_summary != totals:
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Measurement summary does not equal transformation arithmetic."
        )
    second_snapshot = _snapshot_website(root)
    if first_snapshot != second_snapshot:
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Website source manifest changed during static provenance verification."
        )
    return deepcopy(dict(document))


def verify_measurement_provenance_file(
    *,
    repo_root: Path,
    measurement_path: str,
    expected_measurement_sha256: str,
) -> dict[str, Any]:
    """Authenticate and verify an existing static-integrity file; never create one."""

    root = _repo_root(repo_root)
    relative = _safe_relative(measurement_path, label="measurement_path")
    if relative.parent != MEASUREMENT_ROOT or not relative.name.endswith(
        ".measurement-static-integrity.v1.json"
    ):
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Measurement evidence must be one direct controlled-root static-integrity v1 file."
        )
    expected = _sha256(expected_measurement_sha256, label="expected_measurement_sha256")
    payload = _read_ordinary_file(
        _joined_path(root, relative, label="Measurement evidence"),
        label="Measurement evidence",
        maximum_bytes=MAX_JSON_BYTES,
        expected_sha256=expected,
    )
    document = _load_json(payload, label="Measurement evidence")
    validated = require_measurement_provenance(document, repo_root=root)
    expected_name = f"{validated['run_id']}.measurement-static-integrity.v1.json"
    if relative.name != expected_name:
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Measurement evidence filename must bind its exact run_id."
        )
    return validated


# Preferred public names describe the bounded result.  Compatibility aliases
# retain the original ingress while production integration remains blocked.
require_static_measurement_integrity = require_measurement_provenance
verify_static_measurement_integrity_file = verify_measurement_provenance_file


def _launcher_attestation() -> Mapping[str, object]:
    value = globals().get("__aureon_runtime_measurement_provenance_launcher_attestation__")
    expected = {
        "launcher_path",
        "launcher_sha256",
        "module_path",
        "module_sha256",
        "repo_root",
        "isolated",
        "no_site",
        "dont_write_bytecode",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise WebsiteRuntimeMeasurementProvenanceError("CLI requires an exact trusted-launcher attestation.")
    if (
        value["isolated"] is not True
        or value["no_site"] is not True
        or value["dont_write_bytecode"] is not True
        or _SHA256.fullmatch(str(value["launcher_sha256"])) is None
        or _SHA256.fullmatch(str(value["module_sha256"])) is None
    ):
        raise WebsiteRuntimeMeasurementProvenanceError("Trusted-launcher attestation is invalid.")
    root = _repo_root(Path(str(value["repo_root"])))
    expected_launcher = _joined_path(
        root,
        PurePosixPath(TRUSTED_LAUNCHER_PATH.as_posix()),
        label="Attested launcher",
    )
    expected_module = _joined_path(
        root,
        PurePosixPath(IMPLEMENTATION_PATH.as_posix()),
        label="Attested module",
    )
    attested_launcher = Path(os.path.abspath(str(value["launcher_path"])))
    attested_module = Path(os.path.abspath(str(value["module_path"])))
    if os.path.normcase(str(attested_launcher)) != os.path.normcase(
        str(expected_launcher)
    ) or os.path.normcase(str(attested_module)) != os.path.normcase(str(expected_module)):
        raise WebsiteRuntimeMeasurementProvenanceError(
            "Trusted-launcher attestation does not bind the exact canonical source paths."
        )
    _read_ordinary_file(
        expected_launcher,
        label="Attested launcher",
        maximum_bytes=MAX_REVIEWED_SOURCE_BYTES,
        expected_sha256=str(value["launcher_sha256"]),
    )
    _read_ordinary_file(
        expected_module,
        label="Attested module",
        maximum_bytes=MAX_REVIEWED_SOURCE_BYTES,
        expected_sha256=str(value["module_sha256"]),
    )
    # These exact supplied pins establish byte continuity for this invocation.
    # Whether the pins are reviewed remains an external registry/governance fact.
    return dict(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="website-runtime-measurement-provenance")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--measurement", required=True)
    parser.add_argument("--expected-measurement-sha256", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise WebsiteRuntimeMeasurementProvenanceError("CLI requires python -I -S -B.")
    attestation = _launcher_attestation()
    args = build_parser().parse_args(argv)
    requested_root = _repo_root(Path(args.repo_root))
    attested_root = _repo_root(Path(str(attestation["repo_root"])))
    if os.path.normcase(str(requested_root)) != os.path.normcase(str(attested_root)):
        raise WebsiteRuntimeMeasurementProvenanceError(
            "CLI repository root must equal the authenticated launcher repository."
        )
    result = verify_static_measurement_integrity_file(
        repo_root=requested_root,
        measurement_path=str(args.measurement),
        expected_measurement_sha256=str(args.expected_measurement_sha256),
    )
    print(f"static-integrity-valid: provenance-unverified; production-blocked ({result['run_id']})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WebsiteRuntimeMeasurementProvenanceError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
