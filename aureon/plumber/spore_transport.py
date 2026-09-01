"""Order-independent transport for already-encrypted Plumber bytes.

The transport fragments ciphertext only.  It neither accepts plaintext nor
handles encryption keys, shares, reconstruction, or release authorization.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from .crypto import b64url_decode, b64url_encode, domain_hash, sha256_hex
from .schema import (
    DenialCode,
    SchemaError,
    format_timestamp,
    parse_timestamp,
    require_aware_datetime,
    require_exact_keys,
    require_int,
    require_nonblank,
    require_sha256,
)

SPORE_MANIFEST_SCHEMA = "aureon.plumber.spore-manifest.v0"
SPORE_FRAGMENT_SCHEMA = "aureon.plumber.spore-fragment.v0"

# Transport remains a bounded local-laboratory format.  The total ceiling
# accommodates a maximum-sized protected payload plus an AEAD tag without
# permitting a manifest to request unbounded fragment allocation.
MAX_SPORE_CIPHERTEXT_BYTES = 16 * 1024 * 1024 + 16
MAX_SPORE_FRAGMENT_BYTES = 1024 * 1024
MAX_SPORE_FRAGMENT_COUNT = 4096
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_FRAGMENT_FIELDS = (
    "schema",
    "packet_identity",
    "stream_identity",
    "temporal_epoch",
    "fragment_index",
    "fragment_count",
    "route_commitment",
    "challenge_commitment",
    "expires_at",
    "ciphertext_fragment_commitment",
    "ciphertext_fragment",
    "fragment_commitment",
)

_MANIFEST_FIELDS = (
    "schema",
    "packet_identity",
    "stream_identity",
    "temporal_epoch",
    "route_commitment",
    "challenge_commitment",
    "expires_at",
    "fragment_count",
    "ciphertext_size",
    "ciphertext_commitment",
    "fragment_commitments",
    "manifest_commitment",
)


def _fragment_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    return {
        field: values[field]
        for field in _FRAGMENT_FIELDS
        if field not in {"ciphertext_fragment", "fragment_commitment"}
    }


def _manifest_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    return {field: values[field] for field in _MANIFEST_FIELDS if field != "manifest_commitment"}


def _preflight_fragment_decoded_size(value: Any) -> int:
    """Return canonical base64url's predicted size without decoding bytes."""

    if not isinstance(value, str) or not value or "=" in value:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_fragment")
    maximum_encoded_chars = (4 * MAX_SPORE_FRAGMENT_BYTES + 2) // 3
    if len(value) > maximum_encoded_chars:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_fragment")
    if len(value) % 4 == 1 or _B64URL_RE.fullmatch(value) is None:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_fragment")
    decoded_size = (len(value) * 3) // 4
    if decoded_size < 1 or decoded_size > MAX_SPORE_FRAGMENT_BYTES:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_fragment")
    return decoded_size


@dataclass(frozen=True, slots=True)
class SporeFragment:
    schema: str
    packet_identity: str
    stream_identity: str
    temporal_epoch: int
    fragment_index: int
    fragment_count: int
    route_commitment: str
    challenge_commitment: str
    expires_at: str
    ciphertext_fragment_commitment: str
    ciphertext_fragment: str
    fragment_commitment: str

    def __post_init__(self) -> None:
        if self.schema != SPORE_FRAGMENT_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        for field in ("packet_identity", "stream_identity"):
            require_nonblank(getattr(self, field), field=field)
        require_int(self.temporal_epoch, field="temporal_epoch", minimum=1)
        require_int(self.fragment_count, field="fragment_count", minimum=1)
        if self.fragment_count > MAX_SPORE_FRAGMENT_COUNT:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_count")
        require_int(self.fragment_index, field="fragment_index", minimum=0)
        if self.fragment_index >= self.fragment_count:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_index")
        for field in (
            "route_commitment",
            "challenge_commitment",
            "ciphertext_fragment_commitment",
            "fragment_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        parse_timestamp(self.expires_at, field="expires_at")
        try:
            chunk = b64url_decode(
                self.ciphertext_fragment,
                max_bytes=MAX_SPORE_FRAGMENT_BYTES,
            )
        except ValueError as exc:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_fragment") from exc
        if sha256_hex(chunk) != self.ciphertext_fragment_commitment:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_fragment_commitment")
        if domain_hash("aureon.plumber.spore-fragment.v0", _fragment_payload(self.to_dict())) != self.fragment_commitment:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_commitment")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _FRAGMENT_FIELDS, field="spore_fragment"))

    def to_dict(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in _FRAGMENT_FIELDS}

    def public_summary(self) -> dict[str, Any]:
        return {
            field: getattr(self, field)
            for field in _FRAGMENT_FIELDS
            if field != "ciphertext_fragment"
        }


@dataclass(frozen=True, slots=True)
class SporeManifest:
    schema: str
    packet_identity: str
    stream_identity: str
    temporal_epoch: int
    route_commitment: str
    challenge_commitment: str
    expires_at: str
    fragment_count: int
    ciphertext_size: int
    ciphertext_commitment: str
    fragment_commitments: tuple[str, ...]
    manifest_commitment: str

    def __post_init__(self) -> None:
        if self.schema != SPORE_MANIFEST_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        for field in ("packet_identity", "stream_identity"):
            require_nonblank(getattr(self, field), field=field)
        require_int(self.temporal_epoch, field="temporal_epoch", minimum=1)
        require_int(self.fragment_count, field="fragment_count", minimum=1)
        require_int(self.ciphertext_size, field="ciphertext_size", minimum=1)
        if self.fragment_count > MAX_SPORE_FRAGMENT_COUNT:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_count")
        if self.ciphertext_size > MAX_SPORE_CIPHERTEXT_BYTES:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_size")
        if (
            self.fragment_count > self.ciphertext_size
            or self.ciphertext_size
            > self.fragment_count * MAX_SPORE_FRAGMENT_BYTES
        ):
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_capacity")
        for field in (
            "route_commitment",
            "challenge_commitment",
            "ciphertext_commitment",
            "manifest_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        if not isinstance(self.fragment_commitments, tuple) or len(self.fragment_commitments) != self.fragment_count:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_commitments")
        for commitment in self.fragment_commitments:
            require_sha256(commitment, field="fragment_commitments")
        parse_timestamp(self.expires_at, field="expires_at")
        if domain_hash("aureon.plumber.spore-manifest.v0", _manifest_payload(self.to_dict())) != self.manifest_commitment:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="manifest_commitment")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        parsed = require_exact_keys(value, _MANIFEST_FIELDS, field="spore_manifest")
        if not isinstance(parsed["fragment_commitments"], list):
            raise SchemaError(DenialCode.INVALID_TYPE, field="fragment_commitments")
        if len(parsed["fragment_commitments"]) > MAX_SPORE_FRAGMENT_COUNT:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_commitments")
        parsed["fragment_commitments"] = tuple(parsed["fragment_commitments"])
        return cls(**parsed)

    def to_dict(self) -> dict[str, Any]:
        return {
            **{field: getattr(self, field) for field in _MANIFEST_FIELDS if field != "fragment_commitments"},
            "fragment_commitments": list(self.fragment_commitments),
        }

    def public_summary(self) -> dict[str, Any]:
        return self.to_dict()


def fragment_ciphertext(
    ciphertext: bytes,
    *,
    packet_identity: str,
    stream_identity: str,
    temporal_epoch: int,
    route_id: str,
    challenge_commitment: str,
    expires_at: datetime,
    fragment_size: int = 16_384,
) -> tuple[SporeManifest, tuple[SporeFragment, ...]]:
    if not isinstance(ciphertext, bytes) or not ciphertext:
        raise SchemaError(DenialCode.INVALID_TYPE, field="ciphertext")
    require_nonblank(packet_identity, field="packet_identity")
    require_nonblank(stream_identity, field="stream_identity")
    require_nonblank(route_id, field="route_id")
    require_int(temporal_epoch, field="temporal_epoch", minimum=1)
    require_int(fragment_size, field="fragment_size", minimum=16)
    if len(ciphertext) > MAX_SPORE_CIPHERTEXT_BYTES:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext")
    if fragment_size > MAX_SPORE_FRAGMENT_BYTES:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_size")
    fragment_count = (len(ciphertext) + fragment_size - 1) // fragment_size
    if fragment_count > MAX_SPORE_FRAGMENT_COUNT:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_count")
    require_sha256(challenge_commitment, field="challenge_commitment")
    expiry = format_timestamp(expires_at)
    route_commitment = domain_hash("aureon.plumber.spore-route.v0", route_id)
    fragments: list[SporeFragment] = []
    for index, offset in enumerate(range(0, len(ciphertext), fragment_size)):
        chunk = ciphertext[offset : offset + fragment_size]
        values: dict[str, Any] = {
            "schema": SPORE_FRAGMENT_SCHEMA,
            "packet_identity": packet_identity,
            "stream_identity": stream_identity,
            "temporal_epoch": temporal_epoch,
            "fragment_index": index,
            "fragment_count": fragment_count,
            "route_commitment": route_commitment,
            "challenge_commitment": challenge_commitment,
            "expires_at": expiry,
            "ciphertext_fragment_commitment": sha256_hex(chunk),
            "ciphertext_fragment": b64url_encode(chunk),
        }
        fragments.append(
            SporeFragment(
                **values,
                fragment_commitment=domain_hash(
                    "aureon.plumber.spore-fragment.v0",
                    _fragment_payload(values),
                ),
            )
        )
    manifest_values: dict[str, Any] = {
        "schema": SPORE_MANIFEST_SCHEMA,
        "packet_identity": packet_identity,
        "stream_identity": stream_identity,
        "temporal_epoch": temporal_epoch,
        "route_commitment": route_commitment,
        "challenge_commitment": challenge_commitment,
        "expires_at": expiry,
        "fragment_count": len(fragments),
        "ciphertext_size": len(ciphertext),
        "ciphertext_commitment": sha256_hex(ciphertext),
        "fragment_commitments": tuple(item.fragment_commitment for item in fragments),
    }
    manifest = SporeManifest(
        **manifest_values,
        manifest_commitment=domain_hash(
            "aureon.plumber.spore-manifest.v0",
            _manifest_payload(manifest_values),
        ),
    )
    return manifest, tuple(fragments)


def reassemble_ciphertext(
    manifest: SporeManifest,
    fragments: Sequence[SporeFragment],
    *,
    now: datetime,
) -> bytes:
    if not isinstance(manifest, SporeManifest):
        raise SchemaError(DenialCode.INVALID_TYPE, field="manifest")
    if isinstance(fragments, (str, bytes, bytearray)) or not isinstance(fragments, Sequence):
        raise SchemaError(DenialCode.INVALID_TYPE, field="fragments")
    if manifest.fragment_count > MAX_SPORE_FRAGMENT_COUNT:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_count")
    if manifest.ciphertext_size > MAX_SPORE_CIPHERTEXT_BYTES:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_size")
    expiry = parse_timestamp(manifest.expires_at, field="expires_at")
    if require_aware_datetime(now, field="now") >= expiry:
        raise SchemaError(DenialCode.FRAGMENT_EXPIRED)
    if len(fragments) != manifest.fragment_count:
        raise SchemaError(DenialCode.FRAGMENT_SET_INCOMPLETE)
    by_index: dict[int, SporeFragment] = {}
    for fragment in fragments:
        if not isinstance(fragment, SporeFragment):
            raise SchemaError(DenialCode.FRAGMENT_INVALID)
        if fragment.fragment_index in by_index:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="duplicate_fragment_index")
        if (
            fragment.packet_identity != manifest.packet_identity
            or fragment.stream_identity != manifest.stream_identity
            or fragment.temporal_epoch != manifest.temporal_epoch
            or fragment.fragment_count != manifest.fragment_count
            or fragment.route_commitment != manifest.route_commitment
            or fragment.challenge_commitment != manifest.challenge_commitment
            or fragment.expires_at != manifest.expires_at
        ):
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_binding")
        if manifest.fragment_commitments[fragment.fragment_index] != fragment.fragment_commitment:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="fragment_commitment")
        by_index[fragment.fragment_index] = fragment
    if set(by_index) != set(range(manifest.fragment_count)):
        raise SchemaError(DenialCode.FRAGMENT_SET_INCOMPLETE)
    predicted_size = 0
    encoded_size = 0
    for index in range(manifest.fragment_count):
        encoded_fragment = by_index[index].ciphertext_fragment
        predicted_size += _preflight_fragment_decoded_size(encoded_fragment)
        encoded_size += len(encoded_fragment)
        if predicted_size > manifest.ciphertext_size:
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_size")
    maximum_encoded_size = (
        (4 * manifest.ciphertext_size + 2) // 3
        + 2 * manifest.fragment_count
    )
    if predicted_size != manifest.ciphertext_size or encoded_size > maximum_encoded_size:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_size")
    assembled = bytearray()
    for index in range(manifest.fragment_count):
        try:
            chunk = b64url_decode(
                by_index[index].ciphertext_fragment,
                max_bytes=MAX_SPORE_FRAGMENT_BYTES,
            )
        except ValueError as exc:
            raise SchemaError(
                DenialCode.FRAGMENT_INVALID,
                field="ciphertext_fragment",
            ) from exc
        if sha256_hex(chunk) != by_index[index].ciphertext_fragment_commitment:
            raise SchemaError(
                DenialCode.FRAGMENT_INVALID,
                field="ciphertext_fragment_commitment",
            )
        if (
            len(assembled) + len(chunk) > manifest.ciphertext_size
            or len(assembled) + len(chunk) > MAX_SPORE_CIPHERTEXT_BYTES
        ):
            raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_size")
        assembled.extend(chunk)
    ciphertext = bytes(assembled)
    if len(ciphertext) != manifest.ciphertext_size or sha256_hex(ciphertext) != manifest.ciphertext_commitment:
        raise SchemaError(DenialCode.FRAGMENT_INVALID, field="ciphertext_commitment")
    return ciphertext


__all__ = [
    "MAX_SPORE_CIPHERTEXT_BYTES",
    "MAX_SPORE_FRAGMENT_BYTES",
    "MAX_SPORE_FRAGMENT_COUNT",
    "SPORE_FRAGMENT_SCHEMA",
    "SPORE_MANIFEST_SCHEMA",
    "SporeFragment",
    "SporeManifest",
    "fragment_ciphertext",
    "reassemble_ciphertext",
]
