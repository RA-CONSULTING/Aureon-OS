"""Verify a captured Home.pl read-back against an exact release manifest.

This module deliberately contains no upload, delete, credential, or network
operation.  It compares already-captured local package/read-back artifacts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

from .common import (
    CapabilityInputError,
    CapabilityResult,
    finding,
    read_text,
    require_mapping,
    require_safe_relative_path,
    sha256_file,
)

SKILL_ID = "homepl_deploy_cache_ssl_readback"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CREDENTIAL_KEYS = {"password", "pass", "secret", "token", "api_key", "private_key", "username"}


def verify_homepl_readback(
    candidate_root: Path,
    manifest_path: str,
    readback_root: Path,
    tls_state: Mapping[str, object],
) -> CapabilityResult:
    """Compare manifest, candidate, read-back, and caller-supplied TLS facts."""

    if set(tls_state) & _CREDENTIAL_KEYS:
        raise CapabilityInputError("tls_state must not contain credentials or identity secrets")
    manifest_safe, source = read_text(candidate_root, manifest_path, suffixes={".json"})
    try:
        raw = json.loads(source)
    except json.JSONDecodeError as exc:
        raise CapabilityInputError("release manifest must be valid JSON") from exc
    manifest = require_mapping(raw, "release manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise CapabilityInputError("release manifest files must be a non-empty list")
    if not readback_root.resolve(strict=True).is_dir():
        raise CapabilityInputError("readback_root must be an existing directory")
    ids: list[str] = []
    candidate_mismatch: list[str] = []
    readback_mismatch: list[str] = []
    evidence = [manifest_safe]
    for index, value in enumerate(files):
        row = require_mapping(value, f"files[{index}]")
        relative = require_safe_relative_path(row.get("path"), f"files[{index}].path")
        declared_hash = row.get("sha256")
        declared_size = row.get("size")
        if (
            relative in ids
            or not isinstance(declared_hash, str)
            or not _SHA256.fullmatch(declared_hash)
            or not isinstance(declared_size, int)
            or declared_size < 0
        ):
            raise CapabilityInputError(
                "manifest paths must be unique with lowercase SHA-256 and non-negative size"
            )
        ids.append(relative)
        try:
            candidate_hash, candidate_size = sha256_file(candidate_root, relative)
        except CapabilityInputError:
            candidate_mismatch.append(relative)
        else:
            if candidate_hash != declared_hash or candidate_size != declared_size:
                candidate_mismatch.append(relative)
        try:
            readback_hash, readback_size = sha256_file(readback_root, relative)
        except CapabilityInputError:
            readback_mismatch.append(relative)
        else:
            if readback_hash != declared_hash or readback_size != declared_size:
                readback_mismatch.append(relative)
            evidence.append(f"readback:{relative}#sha256={readback_hash}")
    hostname = tls_state.get("hostname")
    tls_ok = (
        isinstance(hostname, str)
        and bool(hostname.strip())
        and tls_state.get("valid") is True
        and tls_state.get("protocol") in {"TLSv1.2", "TLSv1.3"}
    )
    cache_state = manifest.get("cache_version")
    findings = (
        finding(
            "candidate-manifest-match",
            not candidate_mismatch,
            "Candidate files match the release manifest."
            if not candidate_mismatch
            else f"Candidate mismatch: {', '.join(candidate_mismatch)}.",
        ),
        finding(
            "live-readback-match",
            not readback_mismatch,
            "Captured Home.pl read-back matches every manifest file."
            if not readback_mismatch
            else f"Read-back mismatch: {', '.join(readback_mismatch)}.",
        ),
        finding("tls-state", tls_ok, "TLS hostname validity and protocol are captured and acceptable."),
        finding(
            "cache-version",
            isinstance(cache_state, str) and bool(cache_state.strip()),
            "The release manifest carries an explicit cache version.",
        ),
        finding(
            "verification-only",
            True,
            "This capability performed no network, credential, upload, or delete operation.",
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={"manifest_file_count": len(ids), "readback_mismatch_count": len(readback_mismatch)},
    )
