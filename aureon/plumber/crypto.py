"""Small, strict cryptographic helpers for the Aureon Plumber v0 protocol.

This module deliberately implements no packet encryption or key custody.  It
provides deterministic encoding, hashes, and Ed25519 signatures for the
metadata contracts used by the foundational Plumber modules.  Public HNC
geometry and observer values are authenticated context, never secret entropy.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_HEX_RE = re.compile(r"^[0-9a-f]+$")


class CryptoContractError(ValueError):
    """A stable, non-secret cryptographic contract failure."""

    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _normalize_json_value(value: Any, *, path: str = "$") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        # JSON leaves number canonicalization underspecified across runtimes.
        # Protocol builders use integers or canonical decimal strings instead.
        raise CryptoContractError("json_float_not_supported")
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CryptoContractError("json_object_key_must_be_string")
            normalized[key] = _normalize_json_value(item, path=f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        return [_normalize_json_value(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    raise CryptoContractError("unsupported_json_type")


def canonical_json_bytes(value: Any) -> bytes:
    """Encode one JSON value deterministically, rejecting unsafe extensions."""

    normalized = _normalize_json_value(value)
    try:
        rendered = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CryptoContractError("json_encoding_failed") from exc
    return rendered.encode("utf-8")


def decode_canonical_json(
    data: bytes | str,
    *,
    require_mapping: bool = False,
    max_bytes: int = 1_048_576,
) -> Any:
    """Strictly decode canonical UTF-8 JSON.

    The byte representation must already equal :func:`canonical_json_bytes`.
    This prevents alternate encodings from changing what a signature means.
    """

    if type(max_bytes) is not int or max_bytes < 1:
        raise CryptoContractError("json_input_size_invalid")
    if isinstance(data, str):
        raw = data.encode("utf-8", errors="strict")
    elif isinstance(data, bytes):
        raw = data
    else:
        raise CryptoContractError("json_input_must_be_bytes_or_string")
    if not raw or len(raw) > max_bytes:
        raise CryptoContractError("json_input_size_invalid")
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise CryptoContractError("json_duplicate_object_key")
            result[key] = item
        return result

    def reject_constant(_value: str) -> Any:
        raise CryptoContractError("non_finite_json_number")

    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CryptoContractError("json_decoding_failed") from exc
    _normalize_json_value(value)
    if canonical_json_bytes(value) != raw:
        raise CryptoContractError("json_encoding_not_canonical")
    if require_mapping and not isinstance(value, dict):
        raise CryptoContractError("json_root_must_be_object")
    return value


def sha256_hex(value: bytes | str | Mapping[str, Any] | Sequence[Any]) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = canonical_json_bytes(value)
    return hashlib.sha256(data).hexdigest()


def domain_hash(domain: str, value: Any) -> str:
    if not isinstance(domain, str):
        raise CryptoContractError("hash_domain_invalid")
    name = domain.strip()
    if not name or "\x00" in name:
        raise CryptoContractError("hash_domain_invalid")
    return hashlib.sha256(name.encode("ascii", errors="strict") + b"\x00" + canonical_json_bytes(value)).hexdigest()


def b64url_encode(data: bytes) -> str:
    if not isinstance(data, bytes) or not data:
        raise CryptoContractError("base64url_input_must_be_nonempty_bytes")
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(value: str, *, expected_bytes: int | None = None) -> bytes:
    if not isinstance(value, str):
        raise CryptoContractError("base64url_encoding_invalid")
    text = value
    if expected_bytes is not None and (type(expected_bytes) is not int or expected_bytes < 1):
        raise CryptoContractError("base64url_length_invalid")
    if not text or "=" in text or _B64URL_RE.fullmatch(text) is None:
        raise CryptoContractError("base64url_encoding_invalid")
    try:
        decoded = base64.b64decode(
            text + "=" * (-len(text) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise CryptoContractError("base64url_encoding_invalid") from exc
    if not decoded or b64url_encode(decoded) != text:
        raise CryptoContractError("base64url_encoding_not_canonical")
    if expected_bytes is not None and len(decoded) != expected_bytes:
        raise CryptoContractError("base64url_length_invalid")
    return decoded


def hex_decode(value: str, *, expected_bytes: int) -> bytes:
    if type(expected_bytes) is not int or expected_bytes < 1:
        raise CryptoContractError("hex_length_invalid")
    if not isinstance(value, str):
        raise CryptoContractError("hex_encoding_invalid")
    text = value
    if len(text) != expected_bytes * 2 or _HEX_RE.fullmatch(text) is None:
        raise CryptoContractError("hex_encoding_invalid")
    try:
        return bytes.fromhex(text)
    except ValueError as exc:  # pragma: no cover - guarded by the regex
        raise CryptoContractError("hex_encoding_invalid") from exc


def generate_ed25519_private_key() -> Ed25519PrivateKey:
    """Generate an in-memory key.  The caller owns all custody decisions."""

    return Ed25519PrivateKey.generate()


def ed25519_public_key_hex(key: Ed25519PrivateKey | Ed25519PublicKey) -> str:
    public_key = key.public_key() if isinstance(key, Ed25519PrivateKey) else key
    if not isinstance(public_key, Ed25519PublicKey):
        raise CryptoContractError("ed25519_key_type_invalid")
    return cast(
        str,
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex(),
    )


def load_ed25519_public_key(value: str | bytes | Ed25519PublicKey) -> Ed25519PublicKey:
    if isinstance(value, Ed25519PublicKey):
        return value
    raw = value if isinstance(value, bytes) else hex_decode(value, expected_bytes=32)
    if len(raw) != 32:
        raise CryptoContractError("ed25519_public_key_length_invalid")
    try:
        return Ed25519PublicKey.from_public_bytes(raw)
    except ValueError as exc:
        raise CryptoContractError("ed25519_public_key_invalid") from exc


def load_ed25519_private_key(value: str | bytes | Ed25519PrivateKey) -> Ed25519PrivateKey:
    if isinstance(value, Ed25519PrivateKey):
        return value
    raw = value if isinstance(value, bytes) else hex_decode(value, expected_bytes=32)
    if len(raw) != 32:
        raise CryptoContractError("ed25519_private_key_length_invalid")
    try:
        return Ed25519PrivateKey.from_private_bytes(raw)
    except ValueError as exc:
        raise CryptoContractError("ed25519_private_key_invalid") from exc


def sign_ed25519(
    private_key: str | bytes | Ed25519PrivateKey,
    value: Any,
    *,
    domain: str,
) -> str:
    message = bytes.fromhex(domain_hash(domain, value))
    return cast(str, load_ed25519_private_key(private_key).sign(message).hex())


def verify_ed25519(
    public_key: str | bytes | Ed25519PublicKey,
    value: Any,
    signature_hex: str,
    *,
    domain: str,
) -> bool:
    try:
        signature = hex_decode(signature_hex, expected_bytes=64)
        message = bytes.fromhex(domain_hash(domain, value))
        load_ed25519_public_key(public_key).verify(signature, message)
    except (CryptoContractError, InvalidSignature, ValueError, TypeError):
        return False
    return True


__all__ = [
    "CryptoContractError",
    "b64url_decode",
    "b64url_encode",
    "canonical_json_bytes",
    "decode_canonical_json",
    "domain_hash",
    "ed25519_public_key_hex",
    "generate_ed25519_private_key",
    "hex_decode",
    "load_ed25519_private_key",
    "load_ed25519_public_key",
    "sha256_hex",
    "sign_ed25519",
    "verify_ed25519",
]
