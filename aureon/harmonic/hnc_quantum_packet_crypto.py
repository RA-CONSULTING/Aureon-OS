"""HNC harmonic packet encryption and breaker checks.

This module gives Aureon a packet format that the HNC layer can inspect before
decoding: geometry, Auris node alignment, intent, and packet fingerprints are
authenticated with the payload. The secrecy carrier is AES-GCM with HKDF-SHA256
so the packet can be break-tested without putting credentials at risk.
"""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any, cast

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from aureon.core.hnc_params import HNCParams, load_params
from aureon.harmonic.hnc_symbolic_route_seal import (
    build_symbolic_route_seal,
    symbolic_route_public_summary,
    validate_symbolic_route_seal,
)

PACKET_MAGIC = "AUREON-HNC-QP"
PACKET_SCHEMA_VERSION = 1
ENV_PACKET_PREFIX = "hncqp1:"
MASTER_KEY_ENV = "AUREON_HNC_PACKET_MASTER_KEY"
LEGACY_MASTER_KEY_ENV = "HNC_PACKET_MASTER_KEY"
MIN_MASTER_KEY_BYTES = 32
LEGACY_MIN_MASTER_KEY_BYTES = 16
AES_GCM_NONCE_BYTES = 12
AES_GCM_TAG_BYTES = 16
PACKET_KDF_SALT_BYTES = 32
SWARM_DATA_KEY_BYTES = 32
SWARM_SHARE_BYTES = 32

# These are protocol safety limits, not allocation targets.  The repository
# singularity-vault profile can legitimately carry archives near 100 MiB, so
# the general packet ceiling remains above that profile while still rejecting
# attacker-controlled unbounded inputs before hashing or decoding them.
MAX_PLAINTEXT_BYTES = 128 * 1024 * 1024
MAX_CIPHERTEXT_BYTES = MAX_PLAINTEXT_BYTES + AES_GCM_TAG_BYTES
MAX_PACKET_JSON_BYTES = 192 * 1024 * 1024
MAX_ENV_PACKET_JSON_BYTES = 2 * 1024 * 1024
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 300_000
MAX_JSON_STRING_BYTES = MAX_PACKET_JSON_BYTES
MAX_FRAGMENT_COUNT = 262_144
MAX_FRAGMENT_BYTES = 4 * 1024 * 1024
MAX_SLIT_NAMES = 64
MAX_SLIT_NAME_BYTES = 128
MAX_SWARM_AGENTS = 32
MAX_SWARM_LOCKNOTES = MAX_SWARM_AGENTS * (MAX_SWARM_AGENTS - 1)
MAX_KEY_BYTES = 4096
MAX_PURPOSE_BYTES = 1024
MAX_AGENT_ID_BYTES = 128

_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
HNC_PACKET_EVIDENCE_WRITE_HOLD = "hnc_packet_evidence_filesystem_release_hold"

_PACKET_FIELDS = frozenset(
    {
        "magic",
        "schema_version",
        "metadata",
        "operator_aad",
        "nonce_b64",
        "ciphertext_b64",
        "packet_sha256",
    }
)
_SWARM_PACKET_FIELDS = _PACKET_FIELDS | {"swarm_locknotes"}
_COMMON_METADATA_FIELDS = frozenset(
    {
        "schema_version",
        "algorithm",
        "kdf",
        "digest",
        "operator_packet_name",
        "purpose",
        "created_at",
        "plaintext_size_bytes",
        "hnc_alignment",
        "hnc_alignment_sha256",
    }
)
_SINGLE_METADATA_FIELDS = _COMMON_METADATA_FIELDS | {"key_derivation_salt_b64"}
_LEGACY_SINGLE_METADATA_FIELDS = _COMMON_METADATA_FIELDS
_SWARM_METADATA_FIELDS = _COMMON_METADATA_FIELDS | {"swarm_security"}
_ALIGNMENT_FIELDS = frozenset(
    {
        "purpose",
        "geometry",
        "symbolic_route_seal",
        "hnc_params",
        "packet_contract",
        "hnc_alignment_sha256",
    }
)
_ALIGNMENT_FIELDS_WITH_EXTRA = _ALIGNMENT_FIELDS | {"extra"}
_HNC_PARAM_FIELDS = frozenset(
    {"alpha", "g", "beta", "tau", "delta_t", "fitted_at", "fitted_from", "r_squared"}
)
_PACKET_CONTRACT_FIELDS = frozenset(
    {
        "decode_requires_hnc_alignment",
        "decode_requires_authentic_geometry",
        "decode_requires_packet_integrity",
        "plaintext_never_returned_in_status",
    }
)
_GEOMETRY_FIELDS = frozenset(
    {
        "name",
        "sha_alias",
        "phi",
        "schumann_anchor_hz",
        "profit_anchor_hz",
        "coherence_anchor_hz",
        "unity_anchor_hz",
        "auris_nodes",
    }
)
_AURIS_NODE_FIELDS = frozenset({"name", "frequency_hz", "texture"})
_SWARM_SECURITY_FIELDS = frozenset(
    {
        "mode",
        "threshold_agents",
        "agent_count",
        "pair_count",
        "single_agent_can_decode",
        "locknote_policy",
    }
)
_SWARM_LOCKNOTE_FIELDS = frozenset(
    {
        "pair_id",
        "agent_id",
        "agent_slot_sha256",
        "nonce_b64",
        "encrypted_share_b64",
        "share_size_bytes",
        "threshold_role",
        "locknote_sha256",
    }
)
_STREAM_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "stream_type",
        "stream_id",
        "packet_sha256",
        "fragment_count",
        "packet_bytes_sha256",
        "slit_names",
        "reassembly_rule",
        "plaintext_visible_before_reassembly",
    }
)
_STREAM_FRAGMENT_FIELDS = frozenset(
    {
        "schema_version",
        "stream_type",
        "stream_id",
        "manifest_sha256",
        "manifest",
        "fragment_index",
        "fragment_count",
        "slit_name",
        "probability_weight",
        "phase_hint",
        "chunk_b64",
        "chunk_sha256",
        "secret_policy",
    }
)

DEFAULT_AURIS_NODES = (
    {"name": "tiger", "frequency_hz": 186.0, "texture": "volatility"},
    {"name": "falcon", "frequency_hz": 210.0, "texture": "momentum"},
    {"name": "hummingbird", "frequency_hz": 324.0, "texture": "frequency"},
    {"name": "dolphin", "frequency_hz": 432.0, "texture": "liquidity"},
    {"name": "deer", "frequency_hz": 396.0, "texture": "stability"},
    {"name": "owl", "frequency_hz": 528.0, "texture": "pattern"},
    {"name": "panda", "frequency_hz": 639.0, "texture": "harmony"},
    {"name": "cargoship", "frequency_hz": 174.0, "texture": "volume"},
    {"name": "clownfish", "frequency_hz": 285.0, "texture": "resilience"},
)

DEFAULT_GEOMETRY = {
    "name": "metatron_phi_auris_9_node_lattice",
    "sha_alias": "sha_246_operator_phrase_mapped_to_sha_256",
    "phi": 1.6180339887,
    "schumann_anchor_hz": 7.83,
    "profit_anchor_hz": 188.0,
    "coherence_anchor_hz": 741.0,
    "unity_anchor_hz": 963.0,
    "auris_nodes": [dict(node) for node in DEFAULT_AURIS_NODES],
}

DEFAULT_HARMONIC_SLITS = (
    "seer_future_wave",
    "lyra_affect_wave",
    "king_accounting_truth",
    "auris_9_node_consensus",
    "hnc_master_equation",
)

SWARM_MODE_TWO_WAY = "hnc_swarm_two_way_locknotes_v1"


class HNCPacketError(ValueError):
    """Raised when an HNC packet cannot be validated or decoded."""


@dataclass(frozen=True)
class HNCDecodedPacket:
    plaintext: bytes
    packet: dict[str, Any]
    decode_report: dict[str, Any]

    def text(self) -> str:
        return self.plaintext.decode("utf-8")


def _b64url_encode(data: bytes) -> str:
    if not isinstance(data, bytes) or not data:
        raise HNCPacketError("base64url_input_must_be_nonempty_bytes")
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(
    data: str,
    *,
    expected_bytes: int | None = None,
    max_bytes: int | None = None,
) -> bytes:
    """Decode one canonical, unpadded base64url value with explicit bounds."""

    if not isinstance(data, str) or not data or "=" in data or _B64URL_RE.fullmatch(data) is None:
        raise HNCPacketError("base64url_encoding_invalid")
    if expected_bytes is not None and (type(expected_bytes) is not int or expected_bytes < 1):
        raise HNCPacketError("base64url_expected_length_invalid")
    if max_bytes is not None:
        if type(max_bytes) is not int or max_bytes < 1:
            raise HNCPacketError("base64url_maximum_length_invalid")
        max_encoded_chars = ((max_bytes + 2) // 3) * 4
        if len(data) > max_encoded_chars:
            raise HNCPacketError("base64url_decoded_value_too_large")
    try:
        decoded = base64.b64decode(
            data + "=" * (-len(data) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise HNCPacketError("base64url_encoding_invalid") from exc
    if not decoded or _b64url_encode(decoded) != data:
        raise HNCPacketError("base64url_encoding_not_canonical")
    if expected_bytes is not None and len(decoded) != expected_bytes:
        raise HNCPacketError("base64url_decoded_length_invalid")
    if max_bytes is not None and len(decoded) > max_bytes:
        raise HNCPacketError("base64url_decoded_value_too_large")
    return decoded


def _normalise_json_value(
    value: Any,
    *,
    depth: int = 0,
    budget: list[int] | None = None,
) -> Any:
    """Return a JSON-safe value while rejecting ambiguous or unbounded input."""

    if depth > MAX_JSON_DEPTH:
        raise HNCPacketError("json_maximum_depth_exceeded")
    counter = [0] if budget is None else budget
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        raise HNCPacketError("json_node_limit_exceeded")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        try:
            encoded_size = len(value.encode("utf-8", errors="strict"))
        except UnicodeEncodeError as exc:
            raise HNCPacketError("json_string_not_valid_utf8") from exc
        if encoded_size > MAX_JSON_STRING_BYTES:
            raise HNCPacketError("json_string_too_large")
        return value
    if type(value) is int:
        if abs(value) > (1 << 63) - 1:
            raise HNCPacketError("json_integer_out_of_range")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise HNCPacketError("json_non_finite_number")
        # Collapse negative zero so there is one protocol representation.
        return 0.0 if value == 0.0 else value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise HNCPacketError("json_object_key_must_be_string")
            if key in normalized:
                raise HNCPacketError("json_duplicate_object_key")
            normalized[key] = _normalise_json_value(item, depth=depth + 1, budget=counter)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview, str)):
        return [
            _normalise_json_value(item, depth=depth + 1, budget=counter)
            for item in value
        ]
    raise HNCPacketError("json_unsupported_type")


def canonical_json_bytes(value: Any, *, max_bytes: int | None = None) -> bytes:
    if max_bytes is None:
        max_bytes = MAX_PACKET_JSON_BYTES
    if type(max_bytes) is not int or max_bytes < 1 or max_bytes > MAX_PACKET_JSON_BYTES:
        raise HNCPacketError("json_maximum_size_invalid")
    normalized = _normalise_json_value(value)
    try:
        encoded = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise HNCPacketError("json_encoding_failed") from exc
    if not encoded or len(encoded) > max_bytes:
        raise HNCPacketError("json_encoded_value_too_large")
    return encoded


def _decode_canonical_json(
    data: bytes,
    *,
    max_bytes: int,
    require_mapping: bool = False,
) -> Any:
    """Decode exact canonical JSON, rejecting duplicate keys and extensions."""

    if not isinstance(data, bytes) or not data or len(data) > max_bytes:
        raise HNCPacketError("json_input_size_invalid")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise HNCPacketError("json_duplicate_object_key")
            result[key] = item
        return result

    def reject_constant(_value: str) -> Any:
        raise HNCPacketError("json_non_finite_number")

    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except HNCPacketError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise HNCPacketError("json_decoding_failed") from exc
    canonical = canonical_json_bytes(value, max_bytes=max_bytes)
    if canonical != data:
        raise HNCPacketError("json_encoding_not_canonical")
    if require_mapping and not isinstance(value, dict):
        raise HNCPacketError("json_root_must_be_object")
    return value


def sha256_hex(value: bytes | str | Mapping[str, Any]) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        try:
            data = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise HNCPacketError("sha256_string_not_valid_utf8") from exc
    else:
        data = canonical_json_bytes(value)
    return hashlib.sha256(data).hexdigest()


def _normalise_legacy_master_key(master_key: bytes | str) -> bytes:
    """Reproduce the pre-hardening v1 effective-key interpretation exactly."""

    if isinstance(master_key, bytes):
        key_bytes = master_key
    else:
        raw = str(master_key or "").strip()
        if raw.startswith(ENV_PACKET_PREFIX):
            raise HNCPacketError("master_key_must_not_be_an_hnc_packet")
        try:
            raw_bytes = raw.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise HNCPacketError("master_key_string_not_valid_utf8") from exc
        try:
            padding = "=" * (-len(raw) % 4)
            key_bytes = base64.urlsafe_b64decode((raw + padding).encode("ascii"))
            if len(key_bytes) < LEGACY_MIN_MASTER_KEY_BYTES:
                key_bytes = raw_bytes
        except (binascii.Error, UnicodeEncodeError, ValueError):
            key_bytes = raw_bytes
    if len(key_bytes) < LEGACY_MIN_MASTER_KEY_BYTES:
        raise HNCPacketError("master_key_too_short_minimum_16_bytes")
    return key_bytes


def normalize_hnc_key_material(
    master_key: bytes | str,
    *,
    packet: Mapping[str, Any] | None = None,
) -> bytes:
    """Normalize caller-supplied key material without claiming to measure entropy.

    New callers must supply at least 32 bytes of randomly generated secret
    material. Strings are *only* canonical unpadded base64url key material.
    Callers that hold raw key material must pass ``bytes``.

    Passing ``packet`` enables the old 16-byte/permissive-string interpretation
    only when that complete packet validates as the exact salt-less single-v1
    profile. This narrow compatibility path exists solely to decrypt or migrate
    packets persisted before the hardened key contract; builders never use it.
    """

    if packet is not None:
        validation = validate_hnc_packet_contract(packet)
        return _normalize_hnc_key_material_for_validated_contract(
            master_key,
            validation,
        )

    if isinstance(master_key, bytes):
        key_bytes = master_key
    elif isinstance(master_key, str):
        raw = master_key
        if raw.startswith(ENV_PACKET_PREFIX):
            raise HNCPacketError("master_key_must_not_be_an_hnc_packet")
        try:
            key_bytes = _b64url_decode(raw, max_bytes=MAX_KEY_BYTES)
        except HNCPacketError as exc:
            raise HNCPacketError(
                "master_key_string_must_be_canonical_unpadded_base64url"
            ) from exc
    else:
        raise HNCPacketError("master_key_must_be_bytes_or_string")
    if len(key_bytes) < MIN_MASTER_KEY_BYTES:
        raise HNCPacketError("master_key_too_short_minimum_32_bytes")
    if len(key_bytes) > MAX_KEY_BYTES:
        raise HNCPacketError("master_key_too_large_maximum_4096_bytes")
    return key_bytes


def _normalize_hnc_key_material_for_validated_contract(
    master_key: bytes | str,
    validation: Mapping[str, Any],
) -> bytes:
    """Select decode key semantics from one already-validated contract."""

    if validation.get("valid") is not True:
        raise HNCPacketError("legacy_key_packet_contract_invalid")
    if validation.get("legacy_key_derivation_profile") is True:
        return _normalise_legacy_master_key(master_key)
    return normalize_hnc_key_material(master_key)


# Backward-compatible private spelling for internal/existing imports.  New
# integrations should import ``normalize_hnc_key_material`` from this module.
_normalise_master_key = normalize_hnc_key_material


def _normalise_agent_secrets(
    agent_secrets: Mapping[str, bytes | str],
    *,
    require_two: bool,
    legacy_decode: bool = False,
) -> dict[str, bytes]:
    if not isinstance(agent_secrets, Mapping):
        raise HNCPacketError("agent_secrets_must_be_a_mapping")
    normalized: dict[str, bytes] = {}
    for raw_agent_id, secret in agent_secrets.items():
        if not isinstance(raw_agent_id, str):
            raise HNCPacketError("agent_id_must_be_a_string")
        agent_id = raw_agent_id.strip()
        agent_id = _bounded_nonblank(
            agent_id,
            code="agent_id_invalid",
            max_bytes=MAX_AGENT_ID_BYTES,
        )
        if agent_id in normalized:
            raise HNCPacketError("duplicate_normalized_agent_id")
        try:
            normalized[agent_id] = (
                _normalise_legacy_master_key(secret)
                if legacy_decode
                else _normalise_master_key(secret)
            )
        except HNCPacketError as exc:
            raise HNCPacketError(f"agent_secret_invalid:{agent_id}:{exc}") from exc
    if require_two and len(normalized) < 2:
        raise HNCPacketError("swarm_requires_at_least_two_agents")
    if len(normalized) > MAX_SWARM_AGENTS:
        raise HNCPacketError("swarm_agent_limit_exceeded")
    if len(set(normalized.values())) != len(normalized):
        raise HNCPacketError("swarm_agent_secrets_must_be_distinct")
    return normalized


def _bounded_nonblank(value: Any, *, code: str, max_bytes: int) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise HNCPacketError(code)
    try:
        encoded_size = len(value.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as exc:
        raise HNCPacketError(code) from exc
    if encoded_size > max_bytes:
        raise HNCPacketError(code)
    return value


def _has_exact_keys(value: Any, expected: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == expected


def _require_expected_aad_match(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any] | None,
) -> None:
    if expected is None:
        return
    if not isinstance(expected, Mapping):
        raise HNCPacketError("expected_operator_aad_must_be_a_mapping")
    if canonical_json_bytes(actual) != canonical_json_bytes(expected):
        raise HNCPacketError("operator_aad_mismatch")


def _finite_protocol_number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _hnc_param_value_reasons(params: Any) -> list[str]:
    if not isinstance(params, Mapping):
        return ["hnc_params_schema_mismatch"]
    reasons: list[str] = []
    for field in ("alpha", "g", "beta"):
        if not _finite_protocol_number(params.get(field)):
            reasons.append(f"hnc_params_{field}_invalid")
    for field in ("tau", "delta_t"):
        value = params.get(field)
        if type(value) is not int or value <= 0:
            reasons.append(f"hnc_params_{field}_invalid")
    fitted_at = params.get("fitted_at")
    if fitted_at is not None and (
        not _finite_protocol_number(fitted_at) or fitted_at < 0
    ):
        reasons.append("hnc_params_fitted_at_invalid")
    fitted_from = params.get("fitted_from")
    if fitted_from is not None:
        if not isinstance(fitted_from, str) or "\x00" in fitted_from:
            reasons.append("hnc_params_fitted_from_invalid")
        else:
            try:
                fitted_from_size = len(fitted_from.encode("utf-8", errors="strict"))
            except UnicodeEncodeError:
                fitted_from_size = MAX_PURPOSE_BYTES + 1
            if fitted_from_size > MAX_PURPOSE_BYTES:
                reasons.append("hnc_params_fitted_from_invalid")
    r_squared = params.get("r_squared")
    if r_squared is not None and (
        not _finite_protocol_number(r_squared) or not 0 <= r_squared <= 1
    ):
        reasons.append("hnc_params_r_squared_invalid")
    return reasons


def _geometry_value_reasons(geometry: Any) -> list[str]:
    """Validate the semantic shape authenticated as HNC geometry.

    Merely counting nine list entries is not enough: values such as nine
    ``None`` objects previously passed the packet contract and were reported as
    an Auris lattice.  Custom geometries remain supported, but they must use the
    complete bounded v1 shape and meaningful finite values.
    """

    reasons: list[str] = []
    if not _has_exact_keys(geometry, _GEOMETRY_FIELDS):
        reasons.append("geometry_schema_mismatch")
        nodes = geometry.get("auris_nodes") if isinstance(geometry, Mapping) else None
        if not isinstance(nodes, list) or len(nodes) != len(DEFAULT_AURIS_NODES):
            reasons.append("auris_9_node_lattice_missing")
        return reasons
    assert isinstance(geometry, Mapping)
    for field in ("name", "sha_alias"):
        try:
            geometry_text = _bounded_nonblank(
                geometry.get(field),
                code=f"geometry_{field}_invalid",
                max_bytes=MAX_SLIT_NAME_BYTES,
            )
        except HNCPacketError:
            _append_reason(reasons, f"geometry_{field}_invalid")
        else:
            if geometry_text != geometry_text.strip() or any(
                ord(character) < 32 or ord(character) == 127
                for character in geometry_text
            ):
                _append_reason(reasons, f"geometry_{field}_invalid")
    if geometry.get("sha_alias") != DEFAULT_GEOMETRY["sha_alias"]:
        _append_reason(reasons, "geometry_sha_alias_mismatch")
    phi = geometry.get("phi")
    if not _finite_protocol_number(phi) or not 1.0 < float(
        cast(int | float, phi)
    ) < 2.0:
        _append_reason(reasons, "geometry_phi_invalid")
    for field in (
        "schumann_anchor_hz",
        "profit_anchor_hz",
        "coherence_anchor_hz",
        "unity_anchor_hz",
    ):
        anchor_value = geometry.get(field)
        if (
            not _finite_protocol_number(anchor_value)
            or float(cast(int | float, anchor_value)) <= 0.0
            or float(cast(int | float, anchor_value)) > 1_000_000_000.0
        ):
            _append_reason(reasons, f"geometry_{field}_invalid")
    nodes = geometry.get("auris_nodes")
    if not isinstance(nodes, list) or len(nodes) != len(DEFAULT_AURIS_NODES):
        _append_reason(reasons, "auris_9_node_lattice_missing")
        return reasons
    names: set[str] = set()
    for index, node in enumerate(nodes):
        if not _has_exact_keys(node, _AURIS_NODE_FIELDS):
            _append_reason(reasons, f"geometry_auris_node_{index}_schema_mismatch")
            continue
        assert isinstance(node, Mapping)
        for field in ("name", "texture"):
            try:
                node_text = _bounded_nonblank(
                    node.get(field),
                    code=f"geometry_auris_node_{index}_{field}_invalid",
                    max_bytes=MAX_SLIT_NAME_BYTES,
                )
            except HNCPacketError:
                _append_reason(reasons, f"geometry_auris_node_{index}_{field}_invalid")
            else:
                if node_text != node_text.strip() or any(
                    ord(character) < 32 or ord(character) == 127
                    for character in node_text
                ):
                    _append_reason(
                        reasons,
                        f"geometry_auris_node_{index}_{field}_invalid",
                    )
                if field == "name":
                    if node_text in names:
                        _append_reason(reasons, "geometry_auris_node_names_not_distinct")
                    names.add(node_text)
        frequency = node.get("frequency_hz")
        if (
            not _finite_protocol_number(frequency)
            or float(cast(int | float, frequency)) <= 0.0
            or float(cast(int | float, frequency)) > 1_000_000_000.0
        ):
            _append_reason(reasons, f"geometry_auris_node_{index}_frequency_invalid")
    return reasons


def packet_master_key_from_env(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    value = env.get(MASTER_KEY_ENV) or env.get(LEGACY_MASTER_KEY_ENV) or ""
    return value if isinstance(value, str) else str(value)


def build_hnc_alignment_context(
    *,
    purpose: str,
    hnc_params: HNCParams | None = None,
    geometry: Mapping[str, Any] | None = None,
    operator_aad: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    purpose = _bounded_nonblank(purpose, code="purpose_invalid", max_bytes=MAX_PURPOSE_BYTES)
    if geometry is not None and not isinstance(geometry, Mapping):
        raise HNCPacketError("geometry_must_be_a_mapping")
    if operator_aad is not None and not isinstance(operator_aad, Mapping):
        raise HNCPacketError("operator_aad_must_be_a_mapping")
    if extra is not None and not isinstance(extra, Mapping):
        raise HNCPacketError("alignment_extra_must_be_a_mapping")
    params = hnc_params or load_params()
    route_seal = build_symbolic_route_seal(
        purpose=purpose,
        operator_aad=operator_aad,
        hnc_context=extra,
    )
    context = {
        "purpose": purpose,
        # Snapshot nested geometry so a returned packet cannot mutate the
        # process-wide defaults or the caller's source mapping by alias.
        "geometry": copy.deepcopy(
            dict(DEFAULT_GEOMETRY if geometry is None else geometry)
        ),
        "symbolic_route_seal": route_seal,
        "hnc_params": {
            "alpha": params.alpha,
            "g": params.g,
            "beta": params.beta,
            "tau": params.tau,
            "delta_t": params.delta_t,
            "fitted_at": params.fitted_at,
            "fitted_from": params.fitted_from,
            "r_squared": params.r_squared,
        },
        "packet_contract": {
            "decode_requires_hnc_alignment": True,
            "decode_requires_authentic_geometry": True,
            "decode_requires_packet_integrity": True,
            "plaintext_never_returned_in_status": True,
        },
    }
    geometry_reasons = _geometry_value_reasons(context["geometry"])
    if geometry_reasons:
        raise HNCPacketError("geometry_invalid:" + ",".join(geometry_reasons))
    param_reasons = _hnc_param_value_reasons(context["hnc_params"])
    if param_reasons:
        raise HNCPacketError("hnc_params_invalid:" + ",".join(param_reasons))
    if extra:
        context["extra"] = dict(extra)
    # Fail before encryption if fitted parameters, context, or geometry contain
    # non-finite, over-deep, or otherwise non-canonical JSON values.
    canonical_json_bytes(context)
    context["hnc_alignment_sha256"] = sha256_hex(
        {
            "purpose": context["purpose"],
            "geometry": context["geometry"],
            "symbolic_route_seal": context["symbolic_route_seal"],
            "hnc_params": context["hnc_params"],
            "packet_contract": context["packet_contract"],
            "extra": context.get("extra", {}),
        }
    )
    return context


def _derive_packet_key_from_material(
    key_material: bytes,
    metadata: Mapping[str, Any],
) -> bytes:
    encoded_salt = metadata.get("key_derivation_salt_b64")
    if encoded_salt is not None:
        salt = _b64url_decode(str(encoded_salt), expected_bytes=PACKET_KDF_SALT_BYTES)
    else:
        # Exact legacy-v1 compatibility for already persisted hncqp1 tokens.
        salt = hashlib.sha256(
            canonical_json_bytes(
                {
                    "magic": PACKET_MAGIC,
                    "schema_version": PACKET_SCHEMA_VERSION,
                    "purpose": metadata.get("purpose"),
                    "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
                    "geometry_name": (metadata.get("hnc_alignment") or {}).get("geometry", {}).get("name"),
                }
            )
        ).digest()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"aureon-hnc-quantum-packet-v1",
    ).derive(key_material)


def _derive_packet_key(master_key: bytes | str, metadata: Mapping[str, Any]) -> bytes:
    """Derive keys for new builders under the hardened key policy only."""

    return _derive_packet_key_from_material(
        _normalise_master_key(master_key),
        metadata,
    )


def _derive_agent_wrap_key_from_material(
    key_material: bytes,
    metadata: Mapping[str, Any],
    *,
    agent_id: str,
    pair_id: str,
) -> bytes:
    salt = hashlib.sha256(
        canonical_json_bytes(
            {
                "magic": PACKET_MAGIC,
                "schema_version": PACKET_SCHEMA_VERSION,
                "swarm_mode": SWARM_MODE_TWO_WAY,
                "purpose": metadata.get("purpose"),
                "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
                "agent_id": agent_id,
                "pair_id": pair_id,
            }
        )
    ).digest()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"aureon-hnc-swarm-locknote-v1",
    ).derive(key_material)


def _derive_agent_wrap_key(
    agent_secret: bytes | str,
    metadata: Mapping[str, Any],
    *,
    agent_id: str,
    pair_id: str,
) -> bytes:
    """Derive wrap keys for new builders under the hardened key policy."""

    return _derive_agent_wrap_key_from_material(
        _normalise_master_key(agent_secret),
        metadata,
        agent_id=agent_id,
        pair_id=pair_id,
    )


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise HNCPacketError("xor_share_length_mismatch")
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def _swarm_locknote_aad(metadata: Mapping[str, Any], *, agent_id: str, pair_id: str) -> bytes:
    return canonical_json_bytes(
        {
            "magic": PACKET_MAGIC,
            "schema_version": PACKET_SCHEMA_VERSION,
            "swarm_mode": SWARM_MODE_TWO_WAY,
            "purpose": metadata.get("purpose"),
            "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
            "agent_id": agent_id,
            "pair_id": pair_id,
        }
    )


def _packet_aad(metadata: Mapping[str, Any], operator_aad: Mapping[str, Any] | None) -> bytes:
    return canonical_json_bytes(
        {
            "magic": PACKET_MAGIC,
            "schema_version": PACKET_SCHEMA_VERSION,
            "metadata": metadata,
            "operator_aad": dict(operator_aad or {}),
        }
    )


def _without_packet_hash(packet: Mapping[str, Any]) -> dict[str, Any]:
    clean = dict(packet)
    clean.pop("packet_sha256", None)
    return clean


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _alignment_hash_payload(alignment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "purpose": alignment.get("purpose"),
        "geometry": alignment.get("geometry"),
        "symbolic_route_seal": alignment.get("symbolic_route_seal"),
        "hnc_params": alignment.get("hnc_params"),
        "packet_contract": alignment.get("packet_contract"),
        "extra": alignment.get("extra", {}),
    }


def _validate_swarm_locknotes(
    notes: Any,
    metadata: Mapping[str, Any],
    reasons: list[str],
) -> None:
    if not isinstance(notes, list) or not notes or len(notes) > MAX_SWARM_LOCKNOTES:
        _append_reason(reasons, "swarm_locknote_count_invalid")
        return

    notes_by_pair: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    agent_ids: set[str] = set()
    for note in notes:
        if not _has_exact_keys(note, _SWARM_LOCKNOTE_FIELDS):
            _append_reason(reasons, "swarm_locknote_schema_mismatch")
            continue
        assert isinstance(note, Mapping)
        agent_id = note.get("agent_id")
        pair_id = note.get("pair_id")
        try:
            agent_id = _bounded_nonblank(
                agent_id,
                code="swarm_locknote_agent_id_invalid",
                max_bytes=MAX_AGENT_ID_BYTES,
            )
        except HNCPacketError:
            _append_reason(reasons, "swarm_locknote_agent_id_invalid")
            continue
        if not isinstance(pair_id, str) or re.fullmatch(r"[0-9a-f]{24}", pair_id) is None:
            _append_reason(reasons, "swarm_locknote_pair_id_invalid")
            continue
        if note.get("agent_slot_sha256") != sha256_hex(agent_id):
            _append_reason(reasons, "swarm_locknote_agent_binding_mismatch")
        if note.get("share_size_bytes") != SWARM_SHARE_BYTES:
            _append_reason(reasons, "swarm_locknote_share_size_invalid")
        if note.get("threshold_role") != "two_way_locknote_half":
            _append_reason(reasons, "swarm_locknote_role_invalid")
        try:
            _b64url_decode(
                note.get("nonce_b64"),
                expected_bytes=AES_GCM_NONCE_BYTES,
            )
            _b64url_decode(
                note.get("encrypted_share_b64"),
                expected_bytes=SWARM_SHARE_BYTES + AES_GCM_TAG_BYTES,
            )
        except HNCPacketError:
            _append_reason(reasons, "swarm_locknote_cipher_encoding_invalid")
        clean_note = dict(note)
        expected_note_hash = clean_note.pop("locknote_sha256", None)
        if not isinstance(expected_note_hash, str) or _SHA256_RE.fullmatch(expected_note_hash) is None:
            _append_reason(reasons, "swarm_locknote_hash_invalid")
        else:
            try:
                computed_note_hash = sha256_hex(clean_note)
            except HNCPacketError:
                _append_reason(reasons, "swarm_locknote_hash_input_invalid")
            else:
                if expected_note_hash != computed_note_hash:
                    _append_reason(reasons, "swarm_locknote_hash_mismatch")
        notes_by_pair.setdefault(pair_id, []).append((agent_id, note))
        agent_ids.add(agent_id)

    purpose = metadata.get("purpose")
    if len(agent_ids) > MAX_SWARM_AGENTS:
        _append_reason(reasons, "swarm_agent_limit_exceeded")
        return
    actual_pairs: set[tuple[str, str]] = set()
    for pair_id, pair_notes in notes_by_pair.items():
        ids = sorted({agent_id for agent_id, _note in pair_notes})
        if len(pair_notes) != 2 or len(ids) != 2:
            _append_reason(reasons, "swarm_locknote_pair_shape_invalid")
            continue
        try:
            expected_pair_id = sha256_hex({"agents": ids, "purpose": purpose})[:24]
        except HNCPacketError:
            _append_reason(reasons, "swarm_locknote_pair_binding_input_invalid")
        else:
            if pair_id != expected_pair_id:
                _append_reason(reasons, "swarm_locknote_pair_binding_mismatch")
        actual_pairs.add((ids[0], ids[1]))

    expected_pairs = set(combinations(sorted(agent_ids), 2))
    if actual_pairs != expected_pairs:
        _append_reason(reasons, "swarm_locknote_pair_set_incomplete")

    swarm = metadata.get("swarm_security")
    if not _has_exact_keys(swarm, _SWARM_SECURITY_FIELDS):
        _append_reason(reasons, "swarm_security_schema_mismatch")
        return
    assert isinstance(swarm, Mapping)
    expected_pair_count = len(expected_pairs)
    if (
        swarm.get("mode") != SWARM_MODE_TWO_WAY
        or type(swarm.get("threshold_agents")) is not int
        or swarm.get("threshold_agents") != 2
        or type(swarm.get("agent_count")) is not int
        or swarm.get("agent_count") != len(agent_ids)
        or type(swarm.get("pair_count")) is not int
        or swarm.get("pair_count") != expected_pair_count
        or swarm.get("single_agent_can_decode") is not False
        or swarm.get("locknote_policy")
        != "any_valid_two_agent_pair_can_reconstruct_the_payload_key"
        or len(notes) != expected_pair_count * 2
    ):
        _append_reason(reasons, "swarm_security_contract_mismatch")


def build_hnc_quantum_packet(
    plaintext: bytes | str,
    master_key: bytes | str,
    *,
    purpose: str = "aureon.hnc.packet",
    operator_aad: Mapping[str, Any] | None = None,
    hnc_context: Mapping[str, Any] | None = None,
    geometry: Mapping[str, Any] | None = None,
    nonce: bytes | None = None,
) -> dict[str, Any]:
    """Encrypt one packet using a fresh per-packet HKDF salt.

    ``nonce`` exists only for deterministic protocol tests.  Reusing an
    explicitly supplied nonce remains safe for packets built here because each
    packet gets a fresh random 32-byte HKDF salt and therefore a distinct AES
    key.  Production callers should omit it and use the random 96-bit default.
    """

    if isinstance(plaintext, str):
        try:
            payload = plaintext.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise HNCPacketError("plaintext_not_valid_utf8") from exc
    elif isinstance(plaintext, (bytes, bytearray, memoryview)):
        payload = bytes(plaintext)
    else:
        raise HNCPacketError("plaintext_must_be_bytes_or_string")
    if len(payload) > MAX_PLAINTEXT_BYTES:
        raise HNCPacketError("plaintext_too_large")
    purpose = _bounded_nonblank(purpose, code="purpose_invalid", max_bytes=MAX_PURPOSE_BYTES)
    if operator_aad is not None and not isinstance(operator_aad, Mapping):
        raise HNCPacketError("operator_aad_must_be_a_mapping")
    if hnc_context is not None and not isinstance(hnc_context, Mapping):
        raise HNCPacketError("hnc_context_must_be_a_mapping")
    if geometry is not None and not isinstance(geometry, Mapping):
        raise HNCPacketError("geometry_must_be_a_mapping")
    alignment = build_hnc_alignment_context(
        purpose=purpose,
        geometry=geometry,
        operator_aad=operator_aad,
        extra=hnc_context,
    )
    metadata = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "algorithm": "AES-256-GCM",
        "kdf": "HKDF-SHA256",
        "digest": "SHA-256",
        "operator_packet_name": "HNC quantum harmonic packet",
        "purpose": purpose,
        "created_at": datetime.now(UTC).isoformat(),
        "plaintext_size_bytes": len(payload),
        "hnc_alignment": alignment,
        "hnc_alignment_sha256": alignment["hnc_alignment_sha256"],
        "key_derivation_salt_b64": _b64url_encode(os.urandom(PACKET_KDF_SALT_BYTES)),
    }
    if nonce is None:
        packet_nonce = os.urandom(AES_GCM_NONCE_BYTES)
    elif isinstance(nonce, (bytes, bytearray, memoryview)):
        packet_nonce = bytes(nonce)
    else:
        raise HNCPacketError("aes_gcm_nonce_must_be_bytes")
    if len(packet_nonce) != AES_GCM_NONCE_BYTES:
        raise HNCPacketError("aes_gcm_nonce_must_be_12_bytes")
    packet_key = _derive_packet_key(master_key, metadata)
    aad = _packet_aad(metadata, operator_aad)
    ciphertext = AESGCM(packet_key).encrypt(packet_nonce, payload, aad)
    packet = {
        "magic": PACKET_MAGIC,
        "schema_version": PACKET_SCHEMA_VERSION,
        "metadata": metadata,
        "operator_aad": dict(operator_aad or {}),
        "nonce_b64": _b64url_encode(packet_nonce),
        "ciphertext_b64": _b64url_encode(ciphertext),
    }
    packet["packet_sha256"] = sha256_hex(_without_packet_hash(packet))
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    return packet


def validate_hnc_packet_contract(packet: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    computed_packet_hash: str | None = None
    computed_alignment_hash: str | None = None
    symbolic_route_validation: dict[str, Any] | None = None
    ciphertext: bytes | None = None

    if not isinstance(packet, Mapping):
        return {
            "valid": False,
            "reasons": ["packet_must_be_a_mapping"],
            "packet_sha256": None,
            "computed_packet_sha256": None,
            "hnc_alignment_sha256": None,
            "computed_hnc_alignment_sha256": None,
            "auris_node_count": 0,
            "symbolic_route": None,
            "purpose": None,
        }
    try:
        canonical_json_bytes(packet)
    except HNCPacketError as exc:
        _append_reason(reasons, f"packet_json_invalid:{exc}")

    metadata = packet.get("metadata") if isinstance(packet.get("metadata"), Mapping) else {}
    is_swarm = "swarm_locknotes" in packet or "swarm_security" in metadata
    expected_packet_fields = _SWARM_PACKET_FIELDS if is_swarm else _PACKET_FIELDS
    if set(packet) != expected_packet_fields:
        _append_reason(reasons, "packet_schema_mismatch")

    expected_metadata_fields = _SWARM_METADATA_FIELDS if is_swarm else _SINGLE_METADATA_FIELDS
    legacy_single = not is_swarm and set(metadata) == _LEGACY_SINGLE_METADATA_FIELDS
    if set(metadata) != expected_metadata_fields and not legacy_single:
        _append_reason(reasons, "metadata_schema_mismatch")

    alignment = metadata.get("hnc_alignment") if isinstance(metadata.get("hnc_alignment"), Mapping) else {}
    expected_alignment_fields = (
        _ALIGNMENT_FIELDS_WITH_EXTRA if "extra" in alignment else _ALIGNMENT_FIELDS
    )
    if set(alignment) != expected_alignment_fields:
        _append_reason(reasons, "hnc_alignment_schema_mismatch")
    if "extra" in alignment and not isinstance(alignment.get("extra"), Mapping):
        _append_reason(reasons, "hnc_alignment_extra_schema_mismatch")
    if is_swarm and (
        not isinstance(alignment.get("extra"), Mapping)
        or alignment["extra"].get("swarm_mode") != SWARM_MODE_TWO_WAY
    ):
        _append_reason(reasons, "swarm_alignment_mode_mismatch")
    geometry = alignment.get("geometry") if isinstance(alignment.get("geometry"), Mapping) else {}
    symbolic_route_seal = alignment.get("symbolic_route_seal")
    nodes = geometry.get("auris_nodes") if isinstance(geometry.get("auris_nodes"), list) else []
    expected_hash = metadata.get("hnc_alignment_sha256")
    try:
        computed_alignment_hash = sha256_hex(_alignment_hash_payload(alignment))
        computed_packet_hash = sha256_hex(_without_packet_hash(packet))
    except HNCPacketError:
        _append_reason(reasons, "packet_hash_input_invalid")

    if packet.get("magic") != PACKET_MAGIC:
        _append_reason(reasons, "bad_magic")
    if type(packet.get("schema_version")) is not int or packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        _append_reason(reasons, "unsupported_schema_version")
    if type(metadata.get("schema_version")) is not int or metadata.get("schema_version") != PACKET_SCHEMA_VERSION:
        _append_reason(reasons, "metadata_schema_version_mismatch")
    if metadata.get("algorithm") != "AES-256-GCM":
        _append_reason(reasons, "unsupported_algorithm")
    if metadata.get("kdf") != "HKDF-SHA256":
        _append_reason(reasons, "unsupported_kdf")
    if metadata.get("digest") != "SHA-256":
        _append_reason(reasons, "unsupported_digest")
    expected_name = (
        "HNC swarm two-way harmonic locknote packet"
        if is_swarm
        else "HNC quantum harmonic packet"
    )
    if metadata.get("operator_packet_name") != expected_name:
        _append_reason(reasons, "operator_packet_name_mismatch")
    try:
        purpose = _bounded_nonblank(
            metadata.get("purpose"),
            code="purpose_invalid",
            max_bytes=MAX_PURPOSE_BYTES,
        )
    except HNCPacketError:
        purpose = None
        _append_reason(reasons, "purpose_invalid")
    if purpose is not None and alignment.get("purpose") != purpose:
        _append_reason(reasons, "hnc_alignment_purpose_mismatch")
    created_at = metadata.get("created_at")
    try:
        created = datetime.fromisoformat(created_at) if isinstance(created_at, str) else None
        if created is None or created.tzinfo is None or created.utcoffset() != UTC.utcoffset(created):
            raise ValueError
    except (TypeError, ValueError):
        _append_reason(reasons, "created_at_invalid")
    plaintext_size = metadata.get("plaintext_size_bytes")
    if type(plaintext_size) is not int or not 0 <= plaintext_size <= MAX_PLAINTEXT_BYTES:
        _append_reason(reasons, "plaintext_size_invalid")
    params = alignment.get("hnc_params")
    if not _has_exact_keys(params, _HNC_PARAM_FIELDS):
        _append_reason(reasons, "hnc_params_schema_mismatch")
    for param_reason in _hnc_param_value_reasons(params):
        _append_reason(reasons, param_reason)
    contract = alignment.get("packet_contract")
    if not _has_exact_keys(contract, _PACKET_CONTRACT_FIELDS) or any(
        contract.get(field) is not True for field in _PACKET_CONTRACT_FIELDS
    ):
        _append_reason(reasons, "packet_contract_schema_mismatch")
    if (
        not isinstance(expected_hash, str)
        or _SHA256_RE.fullmatch(expected_hash) is None
        or expected_hash != computed_alignment_hash
        or alignment.get("hnc_alignment_sha256") != expected_hash
    ):
        _append_reason(reasons, "hnc_alignment_hash_mismatch")
    supplied_packet_hash = packet.get("packet_sha256")
    if (
        not isinstance(supplied_packet_hash, str)
        or _SHA256_RE.fullmatch(supplied_packet_hash) is None
        or supplied_packet_hash != computed_packet_hash
    ):
        _append_reason(reasons, "packet_hash_mismatch")
    for geometry_reason in _geometry_value_reasons(geometry):
        _append_reason(reasons, geometry_reason)
    if not isinstance(symbolic_route_seal, Mapping):
        _append_reason(reasons, "symbolic_route_seal_required")
    else:
        try:
            symbolic_route_validation = validate_symbolic_route_seal(symbolic_route_seal)
        except Exception:
            symbolic_route_validation = {"valid": False, "reasons": ["symbolic_route_validation_failed"]}
        if not symbolic_route_validation.get("valid"):
            _append_reason(reasons, "symbolic_route_seal_mismatch")
        if purpose is not None and symbolic_route_seal.get("purpose") != purpose:
            _append_reason(reasons, "symbolic_route_purpose_mismatch")
    if not isinstance(packet.get("operator_aad"), Mapping):
        _append_reason(reasons, "operator_aad_schema_mismatch")
    try:
        _b64url_decode(packet.get("nonce_b64"), expected_bytes=AES_GCM_NONCE_BYTES)
        ciphertext = _b64url_decode(
            packet.get("ciphertext_b64"),
            max_bytes=MAX_CIPHERTEXT_BYTES,
        )
        if len(ciphertext) < AES_GCM_TAG_BYTES:
            raise HNCPacketError("ciphertext_too_short")
    except HNCPacketError:
        _append_reason(reasons, "cipher_material_invalid")
    if (
        ciphertext is not None
        and type(plaintext_size) is int
        and len(ciphertext) != plaintext_size + AES_GCM_TAG_BYTES
    ):
        _append_reason(reasons, "ciphertext_plaintext_size_mismatch")
    if not is_swarm and not legacy_single:
        try:
            _b64url_decode(
                metadata.get("key_derivation_salt_b64"),
                expected_bytes=PACKET_KDF_SALT_BYTES,
            )
        except HNCPacketError:
            _append_reason(reasons, "key_derivation_salt_invalid")
    if is_swarm:
        _validate_swarm_locknotes(packet.get("swarm_locknotes"), metadata, reasons)

    return {
        "valid": not reasons,
        "reasons": reasons,
        "packet_sha256": packet.get("packet_sha256"),
        "computed_packet_sha256": computed_packet_hash,
        "hnc_alignment_sha256": expected_hash,
        "computed_hnc_alignment_sha256": computed_alignment_hash,
        "auris_node_count": len(nodes),
        "symbolic_route": symbolic_route_validation,
        "purpose": purpose,
        "legacy_key_derivation_profile": legacy_single,
    }


def decode_hnc_quantum_packet(
    packet: Mapping[str, Any],
    master_key: bytes | str,
    *,
    expected_purpose: str | None = None,
    expected_operator_aad: Mapping[str, Any] | None = None,
) -> HNCDecodedPacket:
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    metadata = packet["metadata"]
    if expected_purpose is not None and metadata.get("purpose") != expected_purpose:
        raise HNCPacketError("unexpected_packet_purpose")
    operator_aad = dict(packet.get("operator_aad") or {})
    _require_expected_aad_match(operator_aad, expected_operator_aad)
    try:
        nonce = _b64url_decode(packet["nonce_b64"], expected_bytes=AES_GCM_NONCE_BYTES)
        ciphertext = _b64url_decode(packet["ciphertext_b64"], max_bytes=MAX_CIPHERTEXT_BYTES)
        key_material = _normalize_hnc_key_material_for_validated_contract(
            master_key,
            validation,
        )
        packet_key = _derive_packet_key_from_material(key_material, metadata)
        plaintext = AESGCM(packet_key).decrypt(nonce, ciphertext, _packet_aad(metadata, operator_aad))
    except InvalidTag as exc:
        raise HNCPacketError("packet_authentication_failed") from exc
    except HNCPacketError:
        raise
    except Exception as exc:
        raise HNCPacketError("packet_decode_failed") from exc
    if len(plaintext) != metadata.get("plaintext_size_bytes"):
        raise HNCPacketError("plaintext_size_mismatch")

    decode_report = {
        "decoded": True,
        "decoded_at": datetime.now(UTC).isoformat(),
        "purpose": metadata.get("purpose"),
        "plaintext_size_bytes": len(plaintext),
        "packet_contract": validation,
        "secret_policy": "plaintext_returned_to_caller_only_not_status",
    }
    return HNCDecodedPacket(plaintext=plaintext, packet=dict(packet), decode_report=decode_report)


def build_hnc_swarm_packet(
    plaintext: bytes | str,
    agent_secrets: Mapping[str, bytes | str],
    *,
    purpose: str = "aureon.hnc.swarm.packet",
    operator_aad: Mapping[str, Any] | None = None,
    hnc_context: Mapping[str, Any] | None = None,
    geometry: Mapping[str, Any] | None = None,
    nonce: bytes | None = None,
) -> dict[str, Any]:
    """Build a packet that requires two independent agent locknotes to decode.

    Each agent receives only an encrypted half-share. The payload key is rebuilt
    from a pair of shares, so a single agent secret cannot decrypt the packet.
    For a small swarm this creates every valid two-agent pair. ``nonce`` is a
    deterministic-test hook only; every call uses a fresh random data key, so
    repeating an injected nonce across calls does not repeat the AES-GCM key.
    Production callers should omit it.
    """

    agents = _normalise_agent_secrets(agent_secrets, require_two=True)
    if isinstance(plaintext, str):
        try:
            payload = plaintext.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise HNCPacketError("plaintext_not_valid_utf8") from exc
    elif isinstance(plaintext, (bytes, bytearray, memoryview)):
        payload = bytes(plaintext)
    else:
        raise HNCPacketError("plaintext_must_be_bytes_or_string")
    if len(payload) > MAX_PLAINTEXT_BYTES:
        raise HNCPacketError("plaintext_too_large")
    purpose = _bounded_nonblank(purpose, code="purpose_invalid", max_bytes=MAX_PURPOSE_BYTES)
    if operator_aad is not None and not isinstance(operator_aad, Mapping):
        raise HNCPacketError("operator_aad_must_be_a_mapping")
    if hnc_context is not None and not isinstance(hnc_context, Mapping):
        raise HNCPacketError("hnc_context_must_be_a_mapping")
    if hnc_context is not None and "swarm_mode" in hnc_context:
        raise HNCPacketError("hnc_context_reserved_key:swarm_mode")
    if geometry is not None and not isinstance(geometry, Mapping):
        raise HNCPacketError("geometry_must_be_a_mapping")
    alignment = build_hnc_alignment_context(
        purpose=purpose,
        geometry=geometry,
        operator_aad=operator_aad,
        extra={**dict(hnc_context or {}), "swarm_mode": SWARM_MODE_TWO_WAY},
    )
    metadata = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "algorithm": "AES-256-GCM",
        "kdf": "HKDF-SHA256",
        "digest": "SHA-256",
        "operator_packet_name": "HNC swarm two-way harmonic locknote packet",
        "purpose": purpose,
        "created_at": datetime.now(UTC).isoformat(),
        "plaintext_size_bytes": len(payload),
        "hnc_alignment": alignment,
        "hnc_alignment_sha256": alignment["hnc_alignment_sha256"],
        "swarm_security": {
            "mode": SWARM_MODE_TWO_WAY,
            "threshold_agents": 2,
            "agent_count": len(agents),
            "pair_count": len(agents) * (len(agents) - 1) // 2,
            "single_agent_can_decode": False,
            "locknote_policy": "any_valid_two_agent_pair_can_reconstruct_the_payload_key",
        },
    }
    data_key = os.urandom(SWARM_DATA_KEY_BYTES)
    if nonce is None:
        packet_nonce = os.urandom(AES_GCM_NONCE_BYTES)
    elif isinstance(nonce, (bytes, bytearray, memoryview)):
        packet_nonce = bytes(nonce)
    else:
        raise HNCPacketError("aes_gcm_nonce_must_be_bytes")
    if len(packet_nonce) != AES_GCM_NONCE_BYTES:
        raise HNCPacketError("aes_gcm_nonce_must_be_12_bytes")
    ciphertext = AESGCM(data_key).encrypt(packet_nonce, payload, _packet_aad(metadata, operator_aad))
    locknotes: list[dict[str, Any]] = []
    for agent_a, agent_b in combinations(sorted(agents), 2):
        pair_id = sha256_hex({"agents": [agent_a, agent_b], "purpose": purpose})[:24]
        share_a = os.urandom(SWARM_SHARE_BYTES)
        share_b = _xor_bytes(data_key, share_a)
        for agent_id, share in ((agent_a, share_a), (agent_b, share_b)):
            note_nonce = os.urandom(AES_GCM_NONCE_BYTES)
            wrap_key = _derive_agent_wrap_key(agents[agent_id], metadata, agent_id=agent_id, pair_id=pair_id)
            encrypted_share = AESGCM(wrap_key).encrypt(
                note_nonce,
                share,
                _swarm_locknote_aad(metadata, agent_id=agent_id, pair_id=pair_id),
            )
            note = {
                "pair_id": pair_id,
                "agent_id": agent_id,
                "agent_slot_sha256": sha256_hex(agent_id),
                "nonce_b64": _b64url_encode(note_nonce),
                "encrypted_share_b64": _b64url_encode(encrypted_share),
                "share_size_bytes": len(share),
                "threshold_role": "two_way_locknote_half",
            }
            note["locknote_sha256"] = sha256_hex(note)
            locknotes.append(note)
    packet = {
        "magic": PACKET_MAGIC,
        "schema_version": PACKET_SCHEMA_VERSION,
        "metadata": metadata,
        "operator_aad": dict(operator_aad or {}),
        "nonce_b64": _b64url_encode(packet_nonce),
        "ciphertext_b64": _b64url_encode(ciphertext),
        "swarm_locknotes": locknotes,
    }
    packet["packet_sha256"] = sha256_hex(_without_packet_hash(packet))
    # Exercise the complete protocol schema before returning a locally-built
    # packet, rather than deferring structural errors to a later decoder.
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    return packet


def _decrypt_swarm_share(
    note: Mapping[str, Any],
    metadata: Mapping[str, Any],
    agent_secret: bytes,
) -> bytes:
    agent_id = note["agent_id"]
    pair_id = note["pair_id"]
    expected_note_hash = note.get("locknote_sha256")
    clean_note = dict(note)
    clean_note.pop("locknote_sha256", None)
    if expected_note_hash != sha256_hex(clean_note):
        raise HNCPacketError("swarm_locknote_hash_mismatch")
    wrap_key = _derive_agent_wrap_key_from_material(
        agent_secret,
        metadata,
        agent_id=agent_id,
        pair_id=pair_id,
    )
    try:
        share = AESGCM(wrap_key).decrypt(
            _b64url_decode(note["nonce_b64"], expected_bytes=AES_GCM_NONCE_BYTES),
            _b64url_decode(
                note["encrypted_share_b64"],
                expected_bytes=SWARM_SHARE_BYTES + AES_GCM_TAG_BYTES,
            ),
            _swarm_locknote_aad(metadata, agent_id=agent_id, pair_id=pair_id),
        )
    except InvalidTag as exc:
        raise HNCPacketError("swarm_locknote_authentication_failed") from exc
    if len(share) != SWARM_SHARE_BYTES:
        raise HNCPacketError("swarm_share_length_invalid")
    return share


def decode_hnc_swarm_packet(
    packet: Mapping[str, Any],
    agent_secrets: Mapping[str, bytes | str],
    *,
    expected_purpose: str | None = None,
    expected_operator_aad: Mapping[str, Any] | None = None,
) -> HNCDecodedPacket:
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    metadata = packet["metadata"]
    swarm = metadata.get("swarm_security") if isinstance(metadata.get("swarm_security"), dict) else {}
    if swarm.get("mode") != SWARM_MODE_TWO_WAY:
        raise HNCPacketError("not_a_swarm_two_way_packet")
    if expected_purpose is not None and metadata.get("purpose") != expected_purpose:
        raise HNCPacketError("unexpected_packet_purpose")
    operator_aad = dict(packet.get("operator_aad") or {})
    _require_expected_aad_match(operator_aad, expected_operator_aad)
    notes = packet["swarm_locknotes"]
    # Schema-v1 swarm metadata has no hardened-key discriminator.  Preserve the
    # original effective agent-key interpretation for reads; builders still
    # call the strict default branch above and require 32-byte key material.
    available = _normalise_agent_secrets(
        agent_secrets,
        require_two=True,
        legacy_decode=True,
    )
    notes_by_pair: dict[str, list[Mapping[str, Any]]] = {}
    for note in notes:
        notes_by_pair.setdefault(note["pair_id"], []).append(note)

    failures: list[str] = []
    for pair_id, pair_notes in notes_by_pair.items():
        usable_notes = [note for note in pair_notes if note["agent_id"] in available]
        if len(usable_notes) != 2 or usable_notes[0]["agent_id"] == usable_notes[1]["agent_id"]:
            continue
        left, right = usable_notes
        try:
            left_share = _decrypt_swarm_share(left, metadata, available[left["agent_id"]])
            right_share = _decrypt_swarm_share(right, metadata, available[right["agent_id"]])
            data_key = _xor_bytes(left_share, right_share)
            plaintext = AESGCM(data_key).decrypt(
                _b64url_decode(packet["nonce_b64"], expected_bytes=AES_GCM_NONCE_BYTES),
                _b64url_decode(packet["ciphertext_b64"], max_bytes=MAX_CIPHERTEXT_BYTES),
                _packet_aad(metadata, operator_aad),
            )
            if len(plaintext) != metadata.get("plaintext_size_bytes"):
                raise HNCPacketError("plaintext_size_mismatch")
            return HNCDecodedPacket(
                plaintext=plaintext,
                packet=dict(packet),
                decode_report={
                    "decoded": True,
                    "decoded_at": datetime.now(UTC).isoformat(),
                    "purpose": metadata.get("purpose"),
                    "swarm_mode": SWARM_MODE_TWO_WAY,
                    "pair_id": pair_id,
                    "agents_used": sorted([left["agent_id"], right["agent_id"]]),
                    "single_agent_can_decode": False,
                    "packet_contract": validation,
                    "secret_policy": "plaintext_returned_to_caller_only_not_status",
                },
            )
        except (HNCPacketError, InvalidTag) as exc:
            failures.append(str(exc))
            continue
    raise HNCPacketError("no_valid_two_agent_locknote_pair:" + ",".join(failures[:3]))


def run_hnc_swarm_breaker_checks(packet: Mapping[str, Any], agent_secrets: Mapping[str, bytes | str]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    try:
        decode_hnc_swarm_packet(packet, agent_secrets)
        checks.append({"name": "valid_two_agent_pair_decode", "passed": True, "result": "decoded"})
    except HNCPacketError as exc:
        checks.append({"name": "valid_two_agent_pair_decode", "passed": False, "result": str(exc)})

    first_agent = next(iter(agent_secrets))
    try:
        decode_hnc_swarm_packet(packet, {first_agent: agent_secrets[first_agent]})
        checks.append({"name": "single_agent_decode_blocked", "passed": False, "result": "single_agent_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "single_agent_decode_blocked", "passed": True, "result": str(exc)})

    wrong: dict[str, bytes] = {}
    wrong_values: set[bytes] = set()
    for index, (agent, supplied_secret) in enumerate(agent_secrets.items()):
        supplied_bytes = normalize_hnc_key_material(supplied_secret)
        counter = 0
        candidate = hashlib.sha256(f"hnc-breaker-wrong-key:{index}:{counter}".encode("ascii")).digest()
        while candidate == supplied_bytes or candidate in wrong_values:
            counter += 1
            candidate = hashlib.sha256(
                f"hnc-breaker-wrong-key:{index}:{counter}".encode("ascii")
            ).digest()
        wrong[str(agent)] = candidate
        wrong_values.add(candidate)
    try:
        decode_hnc_swarm_packet(packet, wrong)
        checks.append({"name": "wrong_agent_secret_blocked", "passed": False, "result": "wrong_secret_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "wrong_agent_secret_blocked", "passed": True, "result": str(exc)})

    tampered = copy.deepcopy(dict(packet))
    if tampered.get("swarm_locknotes"):
        note = tampered["swarm_locknotes"][0]
        note["encrypted_share_b64"] = note["encrypted_share_b64"][:-1] + ("A" if note["encrypted_share_b64"][-1] != "A" else "B")
    try:
        decode_hnc_swarm_packet(tampered, agent_secrets)
        checks.append({"name": "locknote_tamper_blocked", "passed": False, "result": "tamper_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "locknote_tamper_blocked", "passed": True, "result": str(exc)})

    missing = copy.deepcopy(dict(packet))
    if missing.get("swarm_locknotes"):
        missing["swarm_locknotes"] = missing["swarm_locknotes"][:1]
        missing["packet_sha256"] = sha256_hex(_without_packet_hash(missing))
    try:
        decode_hnc_swarm_packet(missing, agent_secrets)
        checks.append({"name": "missing_pair_locknote_blocked", "passed": False, "result": "missing_pair_accepted"})
    except HNCPacketError as exc:
        checks.append({"name": "missing_pair_locknote_blocked", "passed": True, "result": str(exc)})

    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "swarm_mode": SWARM_MODE_TWO_WAY,
        "packet_sha256": packet.get("packet_sha256"),
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "secret_policy": "breaker_does_not_emit_plaintext",
    }


def encode_env_packet(value: str, master_key: bytes | str, *, env_key: str) -> str:
    env_key = _bounded_nonblank(env_key, code="env_key_invalid", max_bytes=MAX_PURPOSE_BYTES - 4)
    if not isinstance(value, str):
        raise HNCPacketError("env_value_must_be_a_string")
    packet = build_hnc_quantum_packet(
        value,
        master_key,
        purpose=f"env:{env_key}",
        operator_aad={"env_key": env_key},
        hnc_context={"domain": "local_env_credentials", "env_key": env_key},
    )
    return ENV_PACKET_PREFIX + _b64url_encode(
        canonical_json_bytes(packet, max_bytes=MAX_ENV_PACKET_JSON_BYTES)
    )


def is_env_packet(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(ENV_PACKET_PREFIX)


def _decode_env_packet_object(token: str) -> dict[str, Any]:
    if not isinstance(token, str):
        raise HNCPacketError("env_packet_must_be_a_string")
    raw = token.strip()
    if raw != token:
        raise HNCPacketError("env_packet_encoding_not_canonical")
    if not raw.startswith(ENV_PACKET_PREFIX):
        raise HNCPacketError("not_an_env_packet")
    encoded = raw[len(ENV_PACKET_PREFIX) :]
    packet_bytes = _b64url_decode(encoded, max_bytes=MAX_ENV_PACKET_JSON_BYTES)
    packet = _decode_canonical_json(
        packet_bytes,
        max_bytes=MAX_ENV_PACKET_JSON_BYTES,
        require_mapping=True,
    )
    assert isinstance(packet, dict)
    return packet


def decode_env_packet(token: str, master_key: bytes | str, *, env_key: str) -> str:
    if not isinstance(token, str):
        raise HNCPacketError("env_packet_must_be_a_string")
    raw = token.strip()
    if not raw.startswith(ENV_PACKET_PREFIX):
        return raw
    packet = _decode_env_packet_object(token)
    env_key = _bounded_nonblank(env_key, code="env_key_invalid", max_bytes=MAX_PURPOSE_BYTES - 4)
    decoded = decode_hnc_quantum_packet(
        packet,
        master_key,
        expected_purpose=f"env:{env_key}",
        expected_operator_aad={"env_key": env_key},
    )
    return decoded.text()


def env_packet_summary(token: str) -> dict[str, Any]:
    if not isinstance(token, str):
        return {"encoded": False}
    raw = token.strip()
    if not raw.startswith(ENV_PACKET_PREFIX):
        return {"encoded": False}
    try:
        packet = _decode_env_packet_object(token)
        validation = validate_hnc_packet_contract(packet)
        return {
            "encoded": True,
            "format": ENV_PACKET_PREFIX.rstrip(":"),
            "valid_contract": validation["valid"],
            "purpose": validation["purpose"],
            "packet_sha256": validation["packet_sha256"],
            "hnc_alignment_sha256": validation["hnc_alignment_sha256"],
            "legacy_key_derivation_profile": validation.get(
                "legacy_key_derivation_profile",
                False,
            ),
            "blockers": validation["reasons"],
        }
    except HNCPacketError as exc:
        return {"encoded": True, "valid_contract": False, "error": str(exc).split(":", 1)[0]}


def packet_public_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_hnc_packet_contract(packet)
    packet_mapping = packet if isinstance(packet, Mapping) else {}
    metadata = packet_mapping.get("metadata") if isinstance(packet_mapping.get("metadata"), Mapping) else {}
    alignment = metadata.get("hnc_alignment") if isinstance(metadata.get("hnc_alignment"), Mapping) else {}
    geometry = alignment.get("geometry") if isinstance(alignment.get("geometry"), Mapping) else {}
    symbolic_route = (
        alignment.get("symbolic_route_seal")
        if isinstance(alignment.get("symbolic_route_seal"), Mapping)
        else None
    )
    return {
        "magic": packet_mapping.get("magic"),
        "schema_version": packet_mapping.get("schema_version"),
        "purpose": metadata.get("purpose"),
        "algorithm": metadata.get("algorithm"),
        "kdf": metadata.get("kdf"),
        "digest": metadata.get("digest"),
        "plaintext_size_bytes": metadata.get("plaintext_size_bytes"),
        "hnc_alignment_sha256": metadata.get("hnc_alignment_sha256"),
        "packet_sha256": packet_mapping.get("packet_sha256"),
        "auris_node_count": validation.get("auris_node_count"),
        "valid_contract": validation["valid"],
        "legacy_key_derivation_profile": validation.get(
            "legacy_key_derivation_profile",
            False,
        ),
        "blockers": validation["reasons"],
        "geometry_name": geometry.get("name"),
        "symbolic_route": symbolic_route_public_summary(symbolic_route),
        "secret_policy": "no_plaintext_no_key_material",
    }


def _probability_weights(seed: str, count: int) -> list[float]:
    raw: list[int] = []
    for index in range(count):
        digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
        raw.append(max(1, int.from_bytes(digest[:4], "big")))
    total = float(sum(raw)) or 1.0
    return [value / total for value in raw]


def stream_hnc_probability_fragments(
    packet: Mapping[str, Any],
    *,
    fragment_size: int = 700,
    slit_names: tuple[str, ...] = DEFAULT_HARMONIC_SLITS,
) -> list[dict[str, Any]]:
    """Split an encrypted packet into order-independent HNC probability fragments.

    The fragments expose only transport geometry and packet hashes. The receiver
    must gather every fragment, verify the hashes, reassemble the packet, then
    pass the HNC packet contract before any plaintext can be decoded.
    """

    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    if type(fragment_size) is not int or fragment_size < 128:
        raise HNCPacketError("fragment_size_too_small_minimum_128")
    if fragment_size > MAX_FRAGMENT_BYTES:
        raise HNCPacketError("fragment_size_too_large")
    if (
        not isinstance(slit_names, (tuple, list))
        or not slit_names
        or len(slit_names) > MAX_SLIT_NAMES
    ):
        raise HNCPacketError("slit_names_invalid")
    normalized_slits: list[str] = []
    for slit_name in slit_names:
        normalized_slits.append(
            _bounded_nonblank(
                slit_name,
                code="slit_name_invalid",
                max_bytes=MAX_SLIT_NAME_BYTES,
            )
        )
    if len(set(normalized_slits)) != len(normalized_slits):
        raise HNCPacketError("slit_names_must_be_distinct")
    packet_bytes = canonical_json_bytes(packet, max_bytes=MAX_PACKET_JSON_BYTES)
    chunk_count = (len(packet_bytes) + fragment_size - 1) // fragment_size
    if not 1 <= chunk_count <= MAX_FRAGMENT_COUNT:
        raise HNCPacketError("fragment_count_limit_exceeded")
    chunks = [
        packet_bytes[index : index + fragment_size]
        for index in range(0, len(packet_bytes), fragment_size)
    ]
    stream_id = sha256_hex(
        {
            "packet_sha256": packet.get("packet_sha256"),
            "chunk_count": len(chunks),
            "slit_names": normalized_slits,
        }
    )
    weights = _probability_weights(stream_id, len(chunks))
    manifest = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "stream_type": "hnc_temporal_probability_stream",
        "stream_id": stream_id,
        "packet_sha256": packet.get("packet_sha256"),
        "fragment_count": len(chunks),
        "packet_bytes_sha256": sha256_hex(packet_bytes),
        "slit_names": normalized_slits,
        "reassembly_rule": "all_fragments_required_then_hnc_contract_decode",
        "plaintext_visible_before_reassembly": False,
    }
    manifest_sha256 = sha256_hex(manifest)
    fragments: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        slit_name = normalized_slits[index % len(normalized_slits)]
        fragments.append(
            {
                "schema_version": PACKET_SCHEMA_VERSION,
                "stream_type": "hnc_temporal_probability_fragment",
                "stream_id": stream_id,
                "manifest_sha256": manifest_sha256,
                "manifest": manifest,
                "fragment_index": index,
                "fragment_count": len(chunks),
                "slit_name": slit_name,
                "probability_weight": weights[index],
                "phase_hint": round((index + 1) / max(1, len(chunks)), 8),
                "chunk_b64": _b64url_encode(chunk),
                "chunk_sha256": sha256_hex(chunk),
                "secret_policy": "ciphertext_fragment_only_no_plaintext",
            }
        )
    return fragments


def reassemble_hnc_probability_fragments(fragments: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(fragments, list) or not fragments:
        raise HNCPacketError("no_fragments")
    if len(fragments) > MAX_FRAGMENT_COUNT:
        raise HNCPacketError("fragment_count_limit_exceeded")
    for fragment in fragments:
        if not _has_exact_keys(fragment, _STREAM_FRAGMENT_FIELDS):
            raise HNCPacketError("fragment_schema_mismatch")
    first = fragments[0]
    manifest = first["manifest"]
    if not _has_exact_keys(manifest, _STREAM_MANIFEST_FIELDS):
        raise HNCPacketError("manifest_schema_mismatch")
    assert isinstance(manifest, Mapping)
    try:
        canonical_json_bytes(manifest, max_bytes=MAX_ENV_PACKET_JSON_BYTES)
    except HNCPacketError as exc:
        raise HNCPacketError("manifest_json_invalid") from exc
    manifest_hash = sha256_hex(manifest)
    expected_manifest_hash = first["manifest_sha256"]
    if (
        not isinstance(expected_manifest_hash, str)
        or _SHA256_RE.fullmatch(expected_manifest_hash) is None
        or manifest_hash != expected_manifest_hash
    ):
        raise HNCPacketError("manifest_hash_mismatch")
    if (
        manifest.get("schema_version") != PACKET_SCHEMA_VERSION
        or manifest.get("stream_type") != "hnc_temporal_probability_stream"
        or manifest.get("reassembly_rule") != "all_fragments_required_then_hnc_contract_decode"
        or manifest.get("plaintext_visible_before_reassembly") is not False
    ):
        raise HNCPacketError("manifest_contract_mismatch")
    stream_id = manifest.get("stream_id")
    if not isinstance(stream_id, str) or _SHA256_RE.fullmatch(stream_id) is None:
        raise HNCPacketError("stream_id_invalid")
    if not isinstance(manifest.get("packet_sha256"), str) or _SHA256_RE.fullmatch(manifest["packet_sha256"]) is None:
        raise HNCPacketError("manifest_packet_hash_invalid")
    if not isinstance(manifest.get("packet_bytes_sha256"), str) or _SHA256_RE.fullmatch(manifest["packet_bytes_sha256"]) is None:
        raise HNCPacketError("manifest_bytes_hash_invalid")
    expected_count = manifest.get("fragment_count")
    if type(expected_count) is not int or not 1 <= expected_count <= MAX_FRAGMENT_COUNT:
        raise HNCPacketError("invalid_fragment_count")
    if len(fragments) != expected_count:
        raise HNCPacketError("missing_fragments")
    slit_names = manifest.get("slit_names")
    if (
        not isinstance(slit_names, list)
        or not slit_names
        or len(slit_names) > MAX_SLIT_NAMES
    ):
        raise HNCPacketError("manifest_slit_names_invalid")
    try:
        normalized_manifest_slits: list[str] = []
        for slit_name in slit_names:
            normalized_manifest_slits.append(
                _bounded_nonblank(
                    slit_name,
                    code="manifest_slit_name_invalid",
                    max_bytes=MAX_SLIT_NAME_BYTES,
                )
            )
    except HNCPacketError as exc:
        raise HNCPacketError("manifest_slit_names_invalid") from exc
    if len(set(normalized_manifest_slits)) != len(normalized_manifest_slits):
        raise HNCPacketError("manifest_slit_names_invalid")
    computed_stream_id = sha256_hex(
        {
            "packet_sha256": manifest["packet_sha256"],
            "chunk_count": expected_count,
            "slit_names": normalized_manifest_slits,
        }
    )
    if stream_id != computed_stream_id:
        raise HNCPacketError("stream_id_binding_mismatch")
    expected_weights = _probability_weights(stream_id, expected_count)

    by_index: dict[int, Mapping[str, Any]] = {}
    for fragment in fragments:
        if fragment["manifest"] != manifest or fragment["manifest_sha256"] != expected_manifest_hash:
            raise HNCPacketError("fragment_manifest_mismatch")
        if (
            fragment.get("schema_version") != PACKET_SCHEMA_VERSION
            or fragment.get("stream_type") != "hnc_temporal_probability_fragment"
            or fragment.get("stream_id") != stream_id
            or fragment.get("fragment_count") != expected_count
            or fragment.get("secret_policy") != "ciphertext_fragment_only_no_plaintext"
        ):
            raise HNCPacketError("fragment_contract_mismatch")
        index = fragment.get("fragment_index")
        if type(index) is not int or not 0 <= index < expected_count:
            raise HNCPacketError("fragment_index_invalid")
        if index in by_index:
            raise HNCPacketError("duplicate_fragment_index")
        if fragment.get("slit_name") != slit_names[index % len(slit_names)]:
            raise HNCPacketError("fragment_slit_mismatch")
        probability = fragment.get("probability_weight")
        phase = fragment.get("phase_hint")
        if (
            not isinstance(probability, (int, float))
            or isinstance(probability, bool)
            or not math.isfinite(float(probability))
            or not 0.0 < float(probability) <= 1.0
            or not isinstance(phase, (int, float))
            or isinstance(phase, bool)
            or not math.isfinite(float(phase))
            or not 0.0 < float(phase) <= 1.0
        ):
            raise HNCPacketError("fragment_probability_invalid")
        if (
            probability != expected_weights[index]
            or phase != round((index + 1) / expected_count, 8)
        ):
            raise HNCPacketError("fragment_probability_binding_mismatch")
        by_index[index] = fragment
    if len(by_index) != expected_count or min(by_index) != 0 or max(by_index) != expected_count - 1:
        raise HNCPacketError("missing_fragments")

    chunks: list[bytes] = []
    total_bytes = 0
    for index in range(expected_count):
        fragment = by_index[index]
        chunk_hash = fragment.get("chunk_sha256")
        if not isinstance(chunk_hash, str) or _SHA256_RE.fullmatch(chunk_hash) is None:
            raise HNCPacketError("fragment_chunk_hash_invalid")
        chunk = _b64url_decode(fragment.get("chunk_b64"), max_bytes=MAX_FRAGMENT_BYTES)
        if sha256_hex(chunk) != chunk_hash:
            raise HNCPacketError("fragment_chunk_hash_mismatch")
        total_bytes += len(chunk)
        if total_bytes > MAX_PACKET_JSON_BYTES:
            raise HNCPacketError("reassembled_packet_too_large")
        chunks.append(chunk)
    packet_bytes = b"".join(chunks)
    if sha256_hex(packet_bytes) != manifest.get("packet_bytes_sha256"):
        raise HNCPacketError("packet_bytes_hash_mismatch")
    packet = _decode_canonical_json(
        packet_bytes,
        max_bytes=MAX_PACKET_JSON_BYTES,
        require_mapping=True,
    )
    assert isinstance(packet, dict)
    validation = validate_hnc_packet_contract(packet)
    if not validation["valid"]:
        raise HNCPacketError("packet_contract_failed:" + ",".join(validation["reasons"]))
    if packet.get("packet_sha256") != manifest.get("packet_sha256"):
        raise HNCPacketError("packet_sha256_manifest_mismatch")
    return packet


def run_hnc_packet_breaker_checks(packet: Mapping[str, Any], master_key: bytes | str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def attempt(name: str, mutator) -> None:
        candidate = copy.deepcopy(dict(packet))
        mutator(candidate)
        try:
            decode_hnc_quantum_packet(candidate, master_key)
            checks.append({"name": name, "passed": False, "result": "tamper_accepted"})
        except HNCPacketError as exc:
            checks.append({"name": name, "passed": True, "result": str(exc)})

    attempt("ciphertext_bit_flip", lambda p: p.__setitem__("ciphertext_b64", p["ciphertext_b64"][:-1] + ("A" if p["ciphertext_b64"][-1] != "A" else "B")))
    attempt("geometry_frequency_tamper", lambda p: p["metadata"]["hnc_alignment"]["geometry"].__setitem__("profit_anchor_hz", 189.0))
    attempt("purpose_tamper", lambda p: p["metadata"].__setitem__("purpose", "env:ATTACKER_KEY"))
    attempt("operator_aad_tamper", lambda p: p.__setitem__("operator_aad", {"env_key": "ATTACKER_KEY"}))
    attempt("packet_hash_tamper", lambda p: p.__setitem__("packet_sha256", "0" * 64))

    try:
        fragments = stream_hnc_probability_fragments(packet, fragment_size=256)
        missing = fragments[:-1]
        try:
            reassemble_hnc_probability_fragments(missing)
            checks.append({"name": "temporal_fragment_missing", "passed": False, "result": "missing_fragment_accepted"})
        except HNCPacketError as exc:
            checks.append({"name": "temporal_fragment_missing", "passed": True, "result": str(exc)})
        tampered = copy.deepcopy(fragments)
        tampered[0]["chunk_b64"] = tampered[0]["chunk_b64"][:-1] + ("A" if tampered[0]["chunk_b64"][-1] != "A" else "B")
        try:
            reassemble_hnc_probability_fragments(tampered)
            checks.append({"name": "temporal_fragment_tamper", "passed": False, "result": "tampered_fragment_accepted"})
        except HNCPacketError as exc:
            checks.append({"name": "temporal_fragment_tamper", "passed": True, "result": str(exc)})
    except HNCPacketError as exc:
        checks.append({"name": "temporal_stream_build", "passed": False, "result": str(exc)})

    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "packet_sha256": packet.get("packet_sha256"),
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "secret_policy": "breaker_does_not_emit_plaintext",
    }


def build_hnc_packet_evidence(packet_tokens: Mapping[str, str]) -> dict[str, Any]:
    """Build fixed-shape metadata from contract-valid env packet tokens.

    The caller cannot inject arbitrary evidence values: every public summary is
    re-derived from a validated packet token and the encrypted values themselves
    are omitted.  This builder does not possess a decryption key and therefore
    makes no claim that AEAD authentication or plaintext recovery was verified.
    """

    if not isinstance(packet_tokens, Mapping) or not packet_tokens:
        raise HNCPacketError("evidence_packet_tokens_invalid")
    if len(packet_tokens) > 64:
        raise HNCPacketError("evidence_packet_token_limit_exceeded")
    summaries: dict[str, dict[str, Any]] = {}
    for key, token in packet_tokens.items():
        if not isinstance(key, str) or _ENV_KEY_RE.fullmatch(key) is None:
            raise HNCPacketError("evidence_env_key_invalid")
        if key in summaries:
            raise HNCPacketError("evidence_env_key_duplicate")
        if not isinstance(token, str) or not is_env_packet(token):
            raise HNCPacketError("evidence_env_packet_invalid")
        try:
            packet = _decode_env_packet_object(token)
        except HNCPacketError as exc:
            raise HNCPacketError("evidence_env_packet_invalid") from exc
        validation = validate_hnc_packet_contract(packet)
        if validation.get("valid") is not True:
            raise HNCPacketError("evidence_env_packet_contract_invalid")
        if (
            validation.get("purpose") != f"env:{key}"
            or packet.get("operator_aad") != {"env_key": key}
        ):
            raise HNCPacketError("evidence_env_packet_binding_invalid")
        summaries[key] = {
            "encoded": True,
            "format": ENV_PACKET_PREFIX.rstrip(":"),
            "valid_contract": True,
            "purpose": validation.get("purpose"),
            "packet_sha256": validation.get("packet_sha256"),
            "hnc_alignment_sha256": validation.get("hnc_alignment_sha256"),
            "legacy_key_derivation_profile": bool(
                validation.get("legacy_key_derivation_profile", False)
            ),
            "blockers": list(validation.get("reasons") or ()),
        }
    keys = sorted(summaries)
    payload: dict[str, Any] = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "evidence": {
            "event": "env_credentials_packetized",
            "updated_keys": keys,
            "encrypted_keys": keys,
            "packet_format": ENV_PACKET_PREFIX.rstrip(":"),
            "packet_summaries": {key: summaries[key] for key in keys},
        },
        "secret_policy": "metadata_only_no_values_returned",
    }
    canonical_json_bytes(payload, max_bytes=MAX_ENV_PACKET_JSON_BYTES)
    return payload


def write_hnc_packet_evidence(_summary: Mapping[str, Any], _path: Path) -> Path:
    """Hold the unreleased public filesystem writer before path inspection."""

    raise HNCPacketError(HNC_PACKET_EVIDENCE_WRITE_HOLD)


__all__ = [
    "ENV_PACKET_PREFIX",
    "HNCPacketError",
    "HNCDecodedPacket",
    "LEGACY_MASTER_KEY_ENV",
    "MASTER_KEY_ENV",
    "PACKET_MAGIC",
    "build_hnc_alignment_context",
    "build_hnc_packet_evidence",
    "build_hnc_quantum_packet",
    "canonical_json_bytes",
    "build_hnc_swarm_packet",
    "decode_env_packet",
    "decode_hnc_quantum_packet",
    "decode_hnc_swarm_packet",
    "encode_env_packet",
    "env_packet_summary",
    "is_env_packet",
    "normalize_hnc_key_material",
    "packet_master_key_from_env",
    "packet_public_summary",
    "reassemble_hnc_probability_fragments",
    "run_hnc_packet_breaker_checks",
    "run_hnc_swarm_breaker_checks",
    "sha256_hex",
    "stream_hnc_probability_fragments",
    "SWARM_MODE_TWO_WAY",
    "HNC_PACKET_EVIDENCE_WRITE_HOLD",
    "validate_hnc_packet_contract",
    "write_hnc_packet_evidence",
]
