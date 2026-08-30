"""Cryptographically bound coherence gates for external SCORM benchmarks.

Visible page evidence is deliberately non-authoritative: OCR may pause for a
login, MFA, CAPTCHA, or identity prerequisite, but it can never establish a
registration state or provenance.  A provider-verified session requires an
external Ed25519 receipt.  A synthetic-persona benchmark instead uses a
distinct owner-keyed launch authority bound to an exact native URL, run,
session, window, and control scope.  Every action is checked after intent and
assessment actions require an exact per-action owner grant.  No course answers
or subject-specific rules live here.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import re
import threading
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

RUN_AUTHORITY_SCHEMA_VERSION = "aureon-hnc-scorm-run-authority-v3"
PROVIDER_ATTESTATION_SCHEMA_VERSION = "aureon-hnc-scorm-provider-attestation-v2"
OWNER_BENCHMARK_LAUNCH_SCHEMA_VERSION = "aureon-hnc-scorm-owner-benchmark-launch-v1"
PROVIDER_CONTEXT_SCHEMA_VERSION = "aureon-hnc-scorm-provider-context-v3"
PREFLIGHT_DECISION_SCHEMA_VERSION = "aureon-hnc-scorm-preflight-decision-v1"
ACTION_TARGET_SCHEMA_VERSION = "aureon-hnc-scorm-action-target-v1"
BENCHMARK_GRANT_SCHEMA_VERSION = "aureon-hnc-scorm-benchmark-grant-v3"
ACTION_DECISION_SCHEMA_VERSION = "aureon-hnc-scorm-action-decision-v1"
COHERENCE_DECISION_SCHEMA_VERSION = ACTION_DECISION_SCHEMA_VERSION
ACTION_RECEIPT_SCHEMA_VERSION = "aureon-hnc-scorm-action-receipt-v2"
REPLAY_MARKER_SCHEMA_VERSION = "aureon-hnc-scorm-action-replay-marker-v2"
VISIBLE_EVIDENCE_SCHEMA_VERSION = "aureon-scorm-visible-evidence-v1"

RUN_MODE = "external_scorm_benchmark_run"
BENCHMARK_MODE = "external_scorm_preview_benchmark_action"
MAX_GRANT_LIFETIME_SECONDS = 24 * 60 * 60
MAX_ACTION_LIFETIME_SECONDS = 5 * 60

READY_FOR_INTENT = "ready_for_intent"
CONTINUE = "continue"
RESUMABLE_PAUSE = "resumable_pause"
OWNER_ATTESTATION_REQUIRED = "owner_attestation_required"

PUBLIC_PREVIEW = "public_preview"
UNREGISTERED = "unregistered"
REGISTERED = "registered"
SYNTHETIC_BENCHMARK = "synthetic_benchmark"

PROVIDER_VERIFIED = "provider_verified"
OWNER_BENCHMARK_ASSERTED = "owner_benchmark_asserted"
SYNTHETIC_PERSONA_BENCHMARK = "synthetic_persona_benchmark"
SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT = "signed_owner_benchmark_launch_receipt"

NAVIGATION = "navigation"
ASSESSMENT_RESPONSE = "assessment_response"
CREDENTIAL_MUTATION = "credential_mutation"

NO_CREDENTIAL_EFFECT = "none"
PREVIEW_ONLY = "preview_only"
REAL_IDENTITY_BOUND = "real_identity_bound"

SIGNED_BENCHMARK_CONTROL_RECEIPT = "signed_benchmark_control_receipt"
PROVIDER_NATIVE_SIGNED_METADATA = "provider_native_signed_metadata"

COORDINATE_CONTROL = "coordinate_control"
FOCUSED_CONTROL = "focused_control"
FRAME_WAIT = "frame_wait"
NATIVE_ACCESSIBILITY_CONTROL = "native_accessibility_control"
NATIVE_FOCUSED_CONTROL = "native_focused_control"
BOUND_WINDOW_SURFACE = "bound_window_surface"
NAVIGATION_CONTROL = "navigation_control"
ASSESSMENT_CONTROL = "assessment_control"
CREDENTIAL_COMMIT_CONTROL = "credential_commit_control"
WINDOW_NAVIGATION = "window_navigation"

# Compatibility exports from v2.  They are evidence labels only; v3 never
# trusts them without a full provider-keyed receipt.
NATIVE_BROWSER_UI = "native_browser_ui"
SIGNED_BENCHMARK_CONTROL_GRANT = SIGNED_BENCHMARK_CONTROL_RECEIPT
SIGNED_PROVIDER_SESSION_METADATA = PROVIDER_NATIVE_SIGNED_METADATA

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ED25519_SIGNATURE_RE = re.compile(r"^[0-9a-f]{128}$")
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
_MAX_JSON_BYTES = 128 * 1024
_MAX_VISIBLE_TEXT_BYTES = 128 * 1024
_MAX_ACTION_SEQUENCE = 1_000_000
_MAX_ALLOWED_ACTIONS = 64

_REGISTRATION_STATES = frozenset(
    {PUBLIC_PREVIEW, UNREGISTERED, REGISTERED, SYNTHETIC_BENCHMARK}
)
_PROVENANCE_KINDS = frozenset({PROVIDER_VERIFIED, OWNER_BENCHMARK_ASSERTED})
_INTERACTION_KINDS = frozenset({NAVIGATION, ASSESSMENT_RESPONSE, CREDENTIAL_MUTATION})
_CREDENTIAL_EFFECTS = frozenset({NO_CREDENTIAL_EFFECT, PREVIEW_ONLY, REAL_IDENTITY_BOUND})
_PREVIEW_STATES = frozenset({PUBLIC_PREVIEW, UNREGISTERED})
_PROVIDER_ATTESTATION_TYPES = frozenset({SIGNED_BENCHMARK_CONTROL_RECEIPT, PROVIDER_NATIVE_SIGNED_METADATA})
_TARGET_SURFACES = frozenset({COORDINATE_CONTROL, FOCUSED_CONTROL, FRAME_WAIT})
_TARGET_EVIDENCE_KINDS = frozenset(
    {NATIVE_ACCESSIBILITY_CONTROL, NATIVE_FOCUSED_CONTROL, BOUND_WINDOW_SURFACE}
)
_TARGET_SEMANTICS = frozenset(
    {NAVIGATION_CONTROL, ASSESSMENT_CONTROL, CREDENTIAL_COMMIT_CONTROL, WINDOW_NAVIGATION}
)
_ACTION_DECISION_KINDS = frozenset({CONTINUE, RESUMABLE_PAUSE, OWNER_ATTESTATION_REQUIRED})
_PREFLIGHT_KINDS = frozenset({READY_FOR_INTENT, RESUMABLE_PAUSE})
_PREREQUISITES = frozenset(
    {
        "authorization",
        "benchmark_grant",
        "captcha",
        "effect_resolution",
        "identity",
        "login",
        "mfa",
    }
)
_COORDINATE_ACTIONS = frozenset({"move_mouse", "left_click", "right_click", "double_click", "scroll"})
_FOCUSED_ACTIONS = frozenset({"type_text", "press_key", "hotkey"})
_WAIT_ACTIONS = frozenset({"wait"})
_BLOCKED_HOST_SUFFIXES = (
    ".internal",
    ".lan",
    ".local",
    ".localhost",
    ".home",
    ".onion",
)

_PREREQUISITE_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "captcha",
        ("captcha", "verify you are human", "prove you are human", "i am not a robot"),
    ),
    (
        "mfa",
        (
            "multi factor authentication",
            "two factor authentication",
            "authenticator code",
            "one time passcode",
            "enter verification code",
            "enter your authenticator verification code",
            "verification code from your authenticator",
            "security code from your device",
        ),
    ),
    (
        "identity",
        (
            "verify your identity",
            "confirm your identity",
            "identity verification required",
            "identity check required",
            "proof of identity required",
        ),
    ),
    (
        "login",
        (
            "sign in to continue",
            "log in to continue",
            "login required",
            "sign in required",
            "enter your password to continue",
        ),
    ),
)


class SCORMCoherenceError(ValueError):
    """Base class for malformed or incoherent SCORM authority."""


class SCORMGrantFormatError(SCORMCoherenceError):
    """Raised for non-canonical or structurally invalid signed artifacts."""


class SCORMGrantSignatureError(SCORMCoherenceError):
    """Raised when a signed artifact does not authenticate."""


class SCORMGrantContextError(SCORMCoherenceError):
    """Raised when authority is not bound to the exact live context."""


class SCORMReplayError(SCORMCoherenceError):
    """Raised for replay, sequence, or durable-marker failures."""


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SCORMGrantFormatError("value is not canonical-JSON serializable") from exc


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SCORMCoherenceError(f"{name} must be lowercase SHA-256 hex")
    return value


def _require_ed25519_signature(name: str, value: object) -> str:
    if not isinstance(value, str) or _ED25519_SIGNATURE_RE.fullmatch(value) is None:
        raise SCORMGrantFormatError(f"{name} must be lowercase Ed25519 signature hex")
    return value


def _require_label(name: str, value: object, *, minimum_length: int = 1) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not minimum_length <= len(value) <= 256
        or not _LABEL_RE.fullmatch(value)
    ):
        raise SCORMCoherenceError(f"{name} must be a canonical label")
    return value


def _require_enum(name: str, value: object, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise SCORMCoherenceError(f"{name} is unsupported")
    return value


def _require_int(name: str, value: object, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise SCORMCoherenceError(f"{name} must be an in-range integer")
    return value


def _require_exact_keys(
    name: str,
    value: object,
    expected: frozenset[str],
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SCORMGrantFormatError(f"{name} must be an object")
    actual = set(value)
    if actual != expected:
        missing = ",".join(sorted(expected - actual)) or "none"
        extra = ",".join(sorted(actual - expected)) or "none"
        raise SCORMGrantFormatError(f"{name} keys mismatch (missing={missing}; extra={extra})")
    return value


def _require_secret(secret: object, *, name: str = "secret") -> bytes:
    if not isinstance(secret, (bytes, bytearray, memoryview)):
        raise TypeError(f"{name} must be runtime-only bytes")
    material = bytes(secret)
    if len(material) < 32:
        raise ValueError(f"{name} must contain at least 32 bytes")
    return material


def _unix_time(name: str, value: datetime) -> int:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return int(value.astimezone(UTC).timestamp())


def _validate_lifetime(
    issued_at_unix: int,
    expires_at_unix: int,
    *,
    name: str,
    maximum: int = MAX_GRANT_LIFETIME_SECONDS,
) -> None:
    _require_int("issued_at_unix", issued_at_unix, minimum=0, maximum=2**63 - 1)
    _require_int("expires_at_unix", expires_at_unix, minimum=0, maximum=2**63 - 1)
    if not 0 < expires_at_unix - issued_at_unix <= maximum:
        raise SCORMGrantFormatError(f"{name} lifetime is invalid")


def _validate_now(issued_at_unix: int, expires_at_unix: int, now: datetime, *, name: str) -> None:
    now_unix = _unix_time("now", now)
    if now_unix < issued_at_unix or now_unix >= expires_at_unix:
        raise SCORMGrantContextError(f"{name} is outside its validity window")


def _canonical_public_origin(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SCORMCoherenceError("origin must be a canonical public HTTPS origin")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise SCORMCoherenceError("origin is invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise SCORMCoherenceError("origin must be a canonical public HTTPS origin")
    host = parsed.hostname
    if host is None or not host.isascii() or host != host.casefold() or len(host) > 253:
        raise SCORMCoherenceError("origin host is not canonical")
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        address = None
    if address is not None:
        if not address.is_global:
            raise SCORMCoherenceError("private or non-global origin is forbidden")
    else:
        labels = host.split(".")
        if len(labels) < 2 or any(not _HOST_LABEL_RE.fullmatch(label) for label in labels):
            raise SCORMCoherenceError("origin host must be a canonical DNS name")
        if host == "localhost" or host.endswith(_BLOCKED_HOST_SUFFIXES):
            raise SCORMCoherenceError("private origin suffix is forbidden")
    if port is not None and not 1 <= port <= 65_535:
        raise SCORMCoherenceError("origin port is out of range")
    if port == 443:
        raise SCORMCoherenceError("default HTTPS port must be omitted")
    canonical = f"https://{host}" if port is None else f"https://{host}:{port}"
    if canonical != value:
        raise SCORMCoherenceError("origin is not canonical")
    return canonical


def _normalize_visible_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("visible_text must be a string")
    normalized = unicodedata.normalize("NFC", value)
    if normalized != value or "\x00" in value or len(value.encode("utf-8")) > _MAX_VISIBLE_TEXT_BYTES:
        raise SCORMCoherenceError("visible_text must be bounded exact NFC text")
    return value


def canonical_visible_text_sha256(visible_text: str) -> str:
    """Hash exact NFC visible text used by prerequisite classification."""

    return hashlib.sha256(_normalize_visible_text(visible_text).encode("utf-8")).hexdigest()


def canonical_synthetic_persona_sha256(synthetic_persona_id: str) -> str:
    """Hash one canonical, non-secret synthetic persona identifier."""

    _require_label("synthetic_persona_id", synthetic_persona_id)
    normalized = unicodedata.normalize("NFC", synthetic_persona_id)
    if normalized != synthetic_persona_id:
        raise SCORMGrantFormatError("synthetic_persona_id must already be NFC-normalized")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalized_words(value: str) -> str:
    return " ".join(_WORD_RE.findall(value.casefold().replace("’", "'")))


def classify_visible_prerequisite(visible_text: str) -> str | None:
    """Return the shared visible prerequisite label, if any."""

    normalized = _normalized_words(_normalize_visible_text(visible_text))
    for prerequisite, markers in _PREREQUISITE_MARKERS:
        if any(_normalized_words(marker) in normalized for marker in markers):
            return prerequisite
    if "password" in normalized and (
        "email" in normalized or "username" in normalized
    ):
        return "login"
    cloudfront_authorization_error = (
        "the request could not be satisfied" in normalized
        and "generated by cloudfront" in normalized
    ) or (
        "missing key pair id" in normalized
        and "query parameter or cookie value" in normalized
    )
    if cloudfront_authorization_error:
        return "authorization"
    return None


def canonical_visible_evidence_sha256(observation: object) -> str:
    """Hash exact ordered OCR token dictionaries and exact vision text."""

    try:
        tokens = observation.ocr_tokens  # type: ignore[attr-defined]
        vision_text = observation.vision_text  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise TypeError("observation must expose ocr_tokens and vision_text") from exc
    if not isinstance(tokens, (tuple, list)) or not isinstance(vision_text, str):
        raise TypeError("observation visible evidence has invalid types")
    serialized: list[object] = []
    for token in tokens:
        to_dict = getattr(token, "to_dict", None)
        if not callable(to_dict):
            raise TypeError("each OCR token must expose to_dict()")
        serialized.append(to_dict())
    return _sha256_json(
        {
            "schema_version": VISIBLE_EVIDENCE_SCHEMA_VERSION,
            "ocr_tokens": serialized,
            "vision_text": vision_text,
        }
    )


def canonical_action_sha256(name: str, params: Mapping[str, object]) -> str:
    """Hash exact canonical ``{name, params}`` GUI action input."""

    _require_label("action name", name)
    if not isinstance(params, Mapping):
        raise TypeError("action params must be a mapping")
    encoded = _canonical_json({"name": name, "params": dict(params)})
    if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
        raise SCORMCoherenceError("action exceeds JSON size limit")
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonical_actions(actions: Iterable[str]) -> tuple[str, ...]:
    if isinstance(actions, (str, bytes)):
        raise TypeError("allowed_actions must be an iterable")
    values = tuple(actions)
    if not 1 <= len(values) <= _MAX_ALLOWED_ACTIONS:
        raise SCORMCoherenceError("allowed_actions must contain 1 to 64 actions")
    for value in values:
        _require_label("allowed action", value)
    if values != tuple(sorted(set(values))):
        raise SCORMCoherenceError("allowed_actions must be sorted and unique")
    return values


def _canonical_effects(effects: Iterable[str]) -> tuple[str, ...]:
    if isinstance(effects, (str, bytes)):
        raise TypeError("permitted effects must be an iterable")
    values = tuple(effects)
    for value in values:
        _require_enum("permitted effect", value, _CREDENTIAL_EFFECTS)
    if not values or values != tuple(sorted(set(values))):
        raise SCORMCoherenceError("permitted effects must be sorted, unique, and nonempty")
    return values


def _sign(secret: object, payload: Mapping[str, object]) -> str:
    return hmac.new(
        _require_secret(secret),
        _canonical_json(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _verify(secret: object, payload: Mapping[str, object], signature: str, *, name: str) -> None:
    if not hmac.compare_digest(_sign(secret, payload), signature):
        raise SCORMGrantSignatureError(f"{name} HMAC verification failed")


def _verify_ed25519(
    public_key: object,
    payload: Mapping[str, object],
    signature_hex: str,
    *,
    name: str,
) -> None:
    if not isinstance(public_key, (bytes, bytearray, memoryview)):
        raise TypeError(f"{name} public key must be bytes-like")
    public_key_bytes = bytes(public_key)
    if len(public_key_bytes) != 32:
        raise SCORMGrantFormatError(f"{name} Ed25519 public key must be exactly 32 bytes")
    _require_ed25519_signature(f"{name} signature", signature_hex)
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:  # pragma: no cover - optional provider route dependency
        raise SCORMGrantSignatureError(
            "external provider verification requires the cryptography package"
        ) from exc
    try:
        Ed25519PublicKey.from_public_bytes(public_key_bytes).verify(
            bytes.fromhex(signature_hex),
            _canonical_json(payload).encode("utf-8"),
        )
    except (InvalidSignature, ValueError) as exc:
        raise SCORMGrantSignatureError(f"{name} signature is invalid") from exc


def _decode_canonical_json(encoded: str | bytes, *, name: str) -> object:
    if isinstance(encoded, bytes):
        if len(encoded) > _MAX_JSON_BYTES:
            raise SCORMGrantFormatError(f"{name} exceeds JSON size limit")
        try:
            raw = encoded.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SCORMGrantFormatError(f"{name} must be UTF-8") from exc
    elif isinstance(encoded, str):
        if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
            raise SCORMGrantFormatError(f"{name} exceeds JSON size limit")
        raw = encoded
    else:
        raise TypeError(f"encoded {name} must be str or bytes")

    def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise SCORMGrantFormatError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise SCORMGrantFormatError(f"non-finite JSON number is forbidden: {value}")

    try:
        decoded = json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=reject_constant)
    except SCORMGrantFormatError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SCORMGrantFormatError(f"{name} JSON is invalid") from exc
    if raw != _canonical_json(decoded):
        raise SCORMGrantFormatError(f"{name} must use exact canonical JSON")
    return decoded


@dataclass(frozen=True)
class SCORMRunAuthority:
    """Stable HNC authority for one exact public-origin benchmark run."""

    run_id: str
    run_manifest_sha256: str
    replay_nonce: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    allowed_actions: tuple[str, ...]
    max_actions: int
    issued_at_unix: int
    expires_at_unix: int
    hmac_sha256: str
    schema_version: str = RUN_AUTHORITY_SCHEMA_VERSION
    mode: str = RUN_MODE

    def __post_init__(self) -> None:
        if self.schema_version != RUN_AUTHORITY_SCHEMA_VERSION or self.mode != RUN_MODE:
            raise SCORMGrantFormatError("run authority schema or mode mismatch")
        _require_label("run_id", self.run_id)
        _require_sha256("run_manifest_sha256", self.run_manifest_sha256)
        _require_label("replay_nonce", self.replay_nonce, minimum_length=16)
        _canonical_public_origin(self.allowed_origin)
        for name in ("launch_url_sha256", "launch_plan_sha256", "control_grant_sha256"):
            _require_sha256(name, getattr(self, name))
        _canonical_actions(self.allowed_actions)
        _require_int("max_actions", self.max_actions, minimum=1, maximum=_MAX_ACTION_SEQUENCE)
        _validate_lifetime(self.issued_at_unix, self.expires_at_unix, name="run authority")
        _require_sha256("hmac_sha256", self.hmac_sha256)

    @classmethod
    def issue(
        cls,
        *,
        secret: bytes | bytearray | memoryview,
        run_id: str,
        run_manifest_sha256: str,
        replay_nonce: str,
        allowed_origin: str,
        launch_url_sha256: str,
        launch_plan_sha256: str,
        control_grant_sha256: str,
        allowed_actions: Iterable[str],
        max_actions: int,
        issued_at: datetime,
        expires_at: datetime,
    ) -> SCORMRunAuthority:
        unsigned = cls(
            run_id=run_id,
            run_manifest_sha256=run_manifest_sha256,
            replay_nonce=replay_nonce,
            allowed_origin=allowed_origin,
            launch_url_sha256=launch_url_sha256,
            launch_plan_sha256=launch_plan_sha256,
            control_grant_sha256=control_grant_sha256,
            allowed_actions=tuple(sorted(set(allowed_actions))),
            max_actions=max_actions,
            issued_at_unix=_unix_time("issued_at", issued_at),
            expires_at_unix=_unix_time("expires_at", expires_at),
            hmac_sha256="0" * 64,
        )
        return replace(unsigned, hmac_sha256=_sign(secret, unsigned.signed_payload()))

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "run_id": self.run_id,
            "run_manifest_sha256": self.run_manifest_sha256,
            "replay_nonce": self.replay_nonce,
            "allowed_origin": self.allowed_origin,
            "launch_url_sha256": self.launch_url_sha256,
            "launch_plan_sha256": self.launch_plan_sha256,
            "control_grant_sha256": self.control_grant_sha256,
            "allowed_actions": list(self.allowed_actions),
            "max_actions": self.max_actions,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }

    def to_dict(self) -> dict[str, object]:
        return {"authority": self.signed_payload(), "hmac_sha256": self.hmac_sha256}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def run_authority_sha256(self) -> str:
        return _sha256_json(self.to_dict())

    def verify_signature(self, secret: bytes | bytearray | memoryview) -> SCORMRunAuthority:
        _verify(secret, self.signed_payload(), self.hmac_sha256, name="run authority")
        return self

    def validate_time(self, *, now: datetime) -> SCORMRunAuthority:
        _validate_now(self.issued_at_unix, self.expires_at_unix, now, name="run authority")
        return self


@dataclass(frozen=True)
class SCORMProviderAttestationReceipt:
    """Externally signed provider receipt for session and registration facts.

    This type intentionally has no local ``issue`` helper.  A provider or
    benchmark-control service signs :meth:`signed_payload` with Ed25519; Aureon
    receives only the detached receipt and a configured public key.
    """

    issuer: str
    key_id: str
    attestation_type: str
    run_id: str
    run_manifest_sha256: str
    run_authority_sha256: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    live_url_sha256: str
    native_address_bar_receipt_sha256: str
    registration_state: str
    registration_evidence_kind: str
    registration_evidence_sha256: str
    permitted_credential_effects: tuple[str, ...]
    provider_metadata_sha256: str
    issued_at_unix: int
    expires_at_unix: int
    signature_hex: str
    provenance: str = PROVIDER_VERIFIED
    signature_algorithm: str = "ed25519"
    schema_version: str = PROVIDER_ATTESTATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_ATTESTATION_SCHEMA_VERSION:
            raise SCORMGrantFormatError("provider attestation schema mismatch")
        if self.provenance != PROVIDER_VERIFIED:
            raise SCORMGrantFormatError("provider attestation provenance must be provider_verified")
        if self.signature_algorithm != "ed25519":
            raise SCORMGrantFormatError("provider attestation must use Ed25519")
        _require_label("issuer", self.issuer)
        _require_label("key_id", self.key_id)
        _require_enum("attestation_type", self.attestation_type, _PROVIDER_ATTESTATION_TYPES)
        _require_label("run_id", self.run_id)
        _canonical_public_origin(self.allowed_origin)
        for name in (
            "run_manifest_sha256",
            "run_authority_sha256",
            "launch_url_sha256",
            "launch_plan_sha256",
            "control_grant_sha256",
            "live_url_sha256",
            "native_address_bar_receipt_sha256",
            "registration_evidence_sha256",
            "provider_metadata_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        _require_ed25519_signature("provider signature_hex", self.signature_hex)
        _require_enum("registration_state", self.registration_state, _REGISTRATION_STATES)
        if self.registration_state == SYNTHETIC_BENCHMARK:
            raise SCORMGrantFormatError("provider receipt cannot claim owner benchmark state")
        _require_label("registration_evidence_kind", self.registration_evidence_kind)
        effects = _canonical_effects(self.permitted_credential_effects)
        if self.registration_state in _PREVIEW_STATES:
            if self.attestation_type != SIGNED_BENCHMARK_CONTROL_RECEIPT:
                raise SCORMGrantFormatError("preview registration requires benchmark control receipt")
            if effects != tuple(sorted((NO_CREDENTIAL_EFFECT, PREVIEW_ONLY))):
                raise SCORMGrantFormatError("preview receipt must permit only none and preview_only")
        elif self.attestation_type != PROVIDER_NATIVE_SIGNED_METADATA:
            raise SCORMGrantFormatError("registered session requires provider-native metadata")
        _validate_lifetime(self.issued_at_unix, self.expires_at_unix, name="provider attestation")

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provenance": self.provenance,
            "signature_algorithm": self.signature_algorithm,
            "issuer": self.issuer,
            "key_id": self.key_id,
            "attestation_type": self.attestation_type,
            "run_id": self.run_id,
            "run_manifest_sha256": self.run_manifest_sha256,
            "run_authority_sha256": self.run_authority_sha256,
            "allowed_origin": self.allowed_origin,
            "launch_url_sha256": self.launch_url_sha256,
            "launch_plan_sha256": self.launch_plan_sha256,
            "control_grant_sha256": self.control_grant_sha256,
            "live_url_sha256": self.live_url_sha256,
            "native_address_bar_receipt_sha256": self.native_address_bar_receipt_sha256,
            "registration_state": self.registration_state,
            "registration_evidence_kind": self.registration_evidence_kind,
            "registration_evidence_sha256": self.registration_evidence_sha256,
            "permitted_credential_effects": list(self.permitted_credential_effects),
            "provider_metadata_sha256": self.provider_metadata_sha256,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }

    def to_dict(self) -> dict[str, object]:
        return {"attestation": self.signed_payload(), "signature_hex": self.signature_hex}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def provider_attestation_sha256(self) -> str:
        return _sha256_json(self.to_dict())

    @property
    def launch_authority_sha256(self) -> str:
        return self.provider_attestation_sha256

    def verify_signature(
        self, provider_public_key: bytes | bytearray | memoryview
    ) -> SCORMProviderAttestationReceipt:
        _verify_ed25519(
            provider_public_key,
            self.signed_payload(),
            self.signature_hex,
            name="provider attestation",
        )
        return self

    def validate_time(self, *, now: datetime) -> SCORMProviderAttestationReceipt:
        _validate_now(self.issued_at_unix, self.expires_at_unix, now, name="provider attestation")
        return self


@dataclass(frozen=True)
class SCORMOwnerBenchmarkLaunchAuthority:
    """Owner assertion for one exact synthetic-persona benchmark launch.

    The owner key is distinct from both the HNC receipt key and any external
    provider public key.  Native URL/session/window facts are inputs from the
    trusted UIA control plane, never from page OCR.
    """

    issuer: str
    key_id: str
    synthetic_persona_id: str
    synthetic_persona_sha256: str
    run_id: str
    run_manifest_sha256: str
    run_authority_sha256: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    native_live_url_sha256: str
    native_address_bar_receipt_sha256: str
    active_session_id: str
    window_binding_id: str
    window_generation: int
    window_identity_sha256: str
    issued_at_unix: int
    expires_at_unix: int
    hmac_sha256: str
    provenance: str = OWNER_BENCHMARK_ASSERTED
    scope: str = SYNTHETIC_PERSONA_BENCHMARK
    evidence_kind: str = SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT
    schema_version: str = OWNER_BENCHMARK_LAUNCH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != OWNER_BENCHMARK_LAUNCH_SCHEMA_VERSION:
            raise SCORMGrantFormatError("owner benchmark launch schema mismatch")
        if self.provenance != OWNER_BENCHMARK_ASSERTED:
            raise SCORMGrantFormatError("owner benchmark provenance mismatch")
        if self.scope != SYNTHETIC_PERSONA_BENCHMARK:
            raise SCORMGrantFormatError("owner benchmark scope mismatch")
        if self.evidence_kind != SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT:
            raise SCORMGrantFormatError("owner benchmark evidence kind mismatch")
        _require_label("issuer", self.issuer)
        _require_label("key_id", self.key_id)
        _require_label("synthetic_persona_id", self.synthetic_persona_id)
        if canonical_synthetic_persona_sha256(self.synthetic_persona_id) != (
            self.synthetic_persona_sha256
        ):
            raise SCORMGrantFormatError("synthetic persona identifier digest mismatch")
        _require_label("run_id", self.run_id)
        _canonical_public_origin(self.allowed_origin)
        _require_label("active_session_id", self.active_session_id)
        _require_label("window_binding_id", self.window_binding_id)
        _require_int("window_generation", self.window_generation, minimum=0, maximum=2**63 - 1)
        for name in (
            "synthetic_persona_sha256",
            "run_manifest_sha256",
            "run_authority_sha256",
            "launch_url_sha256",
            "launch_plan_sha256",
            "control_grant_sha256",
            "native_live_url_sha256",
            "native_address_bar_receipt_sha256",
            "window_identity_sha256",
            "hmac_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        if self.native_live_url_sha256 != self.launch_url_sha256:
            raise SCORMGrantContextError("native live URL must equal the signed launch URL")
        _validate_lifetime(
            self.issued_at_unix,
            self.expires_at_unix,
            name="owner benchmark launch authority",
        )

    @classmethod
    def issue(
        cls,
        *,
        owner_secret: bytes | bytearray | memoryview,
        issuer: str,
        key_id: str,
        synthetic_persona_id: str,
        run_authority: SCORMRunAuthority,
        native_live_url_sha256: str,
        native_address_bar_receipt_sha256: str,
        active_session_id: str,
        window_binding_id: str,
        window_generation: int,
        window_identity_sha256: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> SCORMOwnerBenchmarkLaunchAuthority:
        if not isinstance(run_authority, SCORMRunAuthority):
            raise TypeError("run_authority must be SCORMRunAuthority")
        unsigned = cls(
            issuer=issuer,
            key_id=key_id,
            synthetic_persona_id=synthetic_persona_id,
            synthetic_persona_sha256=canonical_synthetic_persona_sha256(
                synthetic_persona_id
            ),
            run_id=run_authority.run_id,
            run_manifest_sha256=run_authority.run_manifest_sha256,
            run_authority_sha256=run_authority.run_authority_sha256,
            allowed_origin=run_authority.allowed_origin,
            launch_url_sha256=run_authority.launch_url_sha256,
            launch_plan_sha256=run_authority.launch_plan_sha256,
            control_grant_sha256=run_authority.control_grant_sha256,
            native_live_url_sha256=native_live_url_sha256,
            native_address_bar_receipt_sha256=native_address_bar_receipt_sha256,
            active_session_id=active_session_id,
            window_binding_id=window_binding_id,
            window_generation=window_generation,
            window_identity_sha256=window_identity_sha256,
            issued_at_unix=_unix_time("issued_at", issued_at),
            expires_at_unix=_unix_time("expires_at", expires_at),
            hmac_sha256="0" * 64,
        )
        return replace(unsigned, hmac_sha256=_sign(owner_secret, unsigned.signed_payload()))

    @property
    def owner_scope_kind(self) -> str:
        return self.scope

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provenance": self.provenance,
            "scope": self.scope,
            "evidence_kind": self.evidence_kind,
            "issuer": self.issuer,
            "key_id": self.key_id,
            "synthetic_persona_id": self.synthetic_persona_id,
            "synthetic_persona_sha256": self.synthetic_persona_sha256,
            "run_id": self.run_id,
            "run_manifest_sha256": self.run_manifest_sha256,
            "run_authority_sha256": self.run_authority_sha256,
            "allowed_origin": self.allowed_origin,
            "launch_url_sha256": self.launch_url_sha256,
            "launch_plan_sha256": self.launch_plan_sha256,
            "control_grant_sha256": self.control_grant_sha256,
            "native_live_url_sha256": self.native_live_url_sha256,
            "native_address_bar_receipt_sha256": self.native_address_bar_receipt_sha256,
            "active_session_id": self.active_session_id,
            "window_binding_id": self.window_binding_id,
            "window_generation": self.window_generation,
            "window_identity_sha256": self.window_identity_sha256,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }

    def to_dict(self) -> dict[str, object]:
        return {"authority": self.signed_payload(), "hmac_sha256": self.hmac_sha256}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def owner_launch_authority_sha256(self) -> str:
        return _sha256_json(self.to_dict())

    @property
    def launch_authority_sha256(self) -> str:
        return self.owner_launch_authority_sha256

    def verify_signature(
        self, owner_secret: bytes | bytearray | memoryview
    ) -> SCORMOwnerBenchmarkLaunchAuthority:
        _verify(owner_secret, self.signed_payload(), self.hmac_sha256, name="owner launch")
        return self

    def validate_time(self, *, now: datetime) -> SCORMOwnerBenchmarkLaunchAuthority:
        _validate_now(
            self.issued_at_unix,
            self.expires_at_unix,
            now,
            name="owner benchmark launch authority",
        )
        return self


@dataclass(frozen=True)
class SCORMProviderContextEvidence:
    """HNC-signed exact-frame context backed by independent launch authority."""

    launch_authority: SCORMProviderAttestationReceipt | SCORMOwnerBenchmarkLaunchAuthority
    run_id: str
    run_manifest_sha256: str
    run_authority_sha256: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    source_observation_sha256: str
    source_screenshot_sha256: str
    visible_evidence_sha256: str
    visible_text_sha256: str
    active_session_id: str
    live_origin: str
    live_url_sha256: str
    native_address_bar_receipt_sha256: str
    window_binding_id: str
    window_generation: int
    window_identity_sha256: str
    registration_state: str
    registration_evidence_kind: str
    registration_evidence_sha256: str
    provenance: str
    launch_authority_sha256: str
    owner_scope_kind: str | None
    synthetic_persona_id: str | None
    synthetic_persona_sha256: str | None
    issued_at_unix: int
    expires_at_unix: int
    hmac_sha256: str
    schema_version: str = PROVIDER_CONTEXT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROVIDER_CONTEXT_SCHEMA_VERSION:
            raise SCORMGrantFormatError("provider context schema mismatch")
        if not isinstance(
            self.launch_authority,
            (SCORMProviderAttestationReceipt, SCORMOwnerBenchmarkLaunchAuthority),
        ):
            raise TypeError("launch_authority must be provider or owner launch evidence")
        expected_provenance = (
            OWNER_BENCHMARK_ASSERTED
            if isinstance(self.launch_authority, SCORMOwnerBenchmarkLaunchAuthority)
            else PROVIDER_VERIFIED
        )
        if self.provenance != expected_provenance:
            raise SCORMGrantContextError(
                "context provenance does not match its independent launch authority type"
            )
        if self.launch_authority_sha256 != self.launch_authority.launch_authority_sha256:
            raise SCORMGrantContextError("context launch authority digest mismatch")
        _require_label("run_id", self.run_id)
        _canonical_public_origin(self.allowed_origin)
        _canonical_public_origin(self.live_origin)
        _require_label("active_session_id", self.active_session_id)
        _require_label("window_binding_id", self.window_binding_id)
        _require_int("window_generation", self.window_generation, minimum=0, maximum=2**63 - 1)
        _require_enum("registration_state", self.registration_state, _REGISTRATION_STATES)
        _require_enum("provenance", self.provenance, _PROVENANCE_KINDS)
        _require_label("registration_evidence_kind", self.registration_evidence_kind)
        if self.provenance == OWNER_BENCHMARK_ASSERTED:
            if self.owner_scope_kind != SYNTHETIC_PERSONA_BENCHMARK:
                raise SCORMGrantFormatError("owner context scope mismatch")
            if self.synthetic_persona_id is None or self.synthetic_persona_sha256 is None:
                raise SCORMGrantFormatError("owner context requires a synthetic persona")
            if canonical_synthetic_persona_sha256(self.synthetic_persona_id) != (
                self.synthetic_persona_sha256
            ):
                raise SCORMGrantFormatError("owner context synthetic persona digest mismatch")
            if self.registration_state != SYNTHETIC_BENCHMARK:
                raise SCORMGrantFormatError("owner context cannot claim provider registration")
            owner_authority = self.launch_authority
            if not isinstance(owner_authority, SCORMOwnerBenchmarkLaunchAuthority):
                raise SCORMGrantContextError("owner context launch authority type mismatch")
            if (
                self.registration_evidence_kind,
                self.registration_evidence_sha256,
                self.live_url_sha256,
                self.native_address_bar_receipt_sha256,
                self.active_session_id,
                self.window_binding_id,
                self.window_generation,
                self.window_identity_sha256,
            ) != (
                SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT,
                owner_authority.owner_launch_authority_sha256,
                owner_authority.native_live_url_sha256,
                owner_authority.native_address_bar_receipt_sha256,
                owner_authority.active_session_id,
                owner_authority.window_binding_id,
                owner_authority.window_generation,
                owner_authority.window_identity_sha256,
            ):
                raise SCORMGrantContextError("owner context facts drift from launch authority")
        elif any(
            value is not None
            for value in (
                self.owner_scope_kind,
                self.synthetic_persona_id,
                self.synthetic_persona_sha256,
            )
        ):
            raise SCORMGrantFormatError("provider context cannot carry owner benchmark scope")
        else:
            provider_authority = self.launch_authority
            if not isinstance(provider_authority, SCORMProviderAttestationReceipt):
                raise SCORMGrantContextError("provider context launch authority type mismatch")
            if (
                self.registration_state,
                self.registration_evidence_kind,
                self.registration_evidence_sha256,
                self.live_url_sha256,
                self.native_address_bar_receipt_sha256,
            ) != (
                provider_authority.registration_state,
                provider_authority.registration_evidence_kind,
                provider_authority.registration_evidence_sha256,
                provider_authority.live_url_sha256,
                provider_authority.native_address_bar_receipt_sha256,
            ):
                raise SCORMGrantContextError("provider context facts drift from external receipt")
        for name in (
            "run_manifest_sha256",
            "run_authority_sha256",
            "launch_url_sha256",
            "launch_plan_sha256",
            "control_grant_sha256",
            "source_observation_sha256",
            "source_screenshot_sha256",
            "visible_evidence_sha256",
            "visible_text_sha256",
            "live_url_sha256",
            "native_address_bar_receipt_sha256",
            "window_identity_sha256",
            "registration_evidence_sha256",
            "launch_authority_sha256",
            "hmac_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        _validate_lifetime(self.issued_at_unix, self.expires_at_unix, name="provider context")

    @classmethod
    def issue(
        cls,
        *,
        secret: bytes | bytearray | memoryview,
        run_authority: SCORMRunAuthority,
        launch_authority: SCORMProviderAttestationReceipt | SCORMOwnerBenchmarkLaunchAuthority,
        source_observation_sha256: str,
        source_screenshot_sha256: str,
        visible_evidence_sha256: str,
        visible_text: str,
        active_session_id: str,
        live_origin: str,
        window_binding_id: str,
        window_generation: int,
        window_identity_sha256: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> SCORMProviderContextEvidence:
        if not isinstance(run_authority, SCORMRunAuthority):
            raise TypeError("run_authority must be SCORMRunAuthority")
        if not isinstance(
            launch_authority,
            (SCORMProviderAttestationReceipt, SCORMOwnerBenchmarkLaunchAuthority),
        ):
            raise TypeError("launch_authority must be provider or owner launch evidence")
        owner_authority = (
            launch_authority
            if isinstance(launch_authority, SCORMOwnerBenchmarkLaunchAuthority)
            else None
        )
        if owner_authority is not None:
            if (
                active_session_id,
                window_binding_id,
                window_generation,
                window_identity_sha256,
            ) != (
                owner_authority.active_session_id,
                owner_authority.window_binding_id,
                owner_authority.window_generation,
                owner_authority.window_identity_sha256,
            ):
                raise SCORMGrantContextError(
                    "owner launch authority does not match current session/window"
                )
            provenance = OWNER_BENCHMARK_ASSERTED
            live_url_sha256 = owner_authority.native_live_url_sha256
            native_receipt_sha256 = owner_authority.native_address_bar_receipt_sha256
            registration_state = SYNTHETIC_BENCHMARK
            registration_evidence_kind = SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT
            registration_evidence_sha256 = owner_authority.owner_launch_authority_sha256
            owner_scope_kind: str | None = owner_authority.scope
            synthetic_persona_id: str | None = owner_authority.synthetic_persona_id
            synthetic_persona_sha256: str | None = owner_authority.synthetic_persona_sha256
        else:
            if not isinstance(launch_authority, SCORMProviderAttestationReceipt):
                raise TypeError("launch_authority must be provider or owner launch evidence")
            provenance = PROVIDER_VERIFIED
            live_url_sha256 = launch_authority.live_url_sha256
            native_receipt_sha256 = launch_authority.native_address_bar_receipt_sha256
            registration_state = launch_authority.registration_state
            registration_evidence_kind = launch_authority.registration_evidence_kind
            registration_evidence_sha256 = launch_authority.registration_evidence_sha256
            owner_scope_kind = None
            synthetic_persona_id = None
            synthetic_persona_sha256 = None
        unsigned = cls(
            launch_authority=launch_authority,
            run_id=run_authority.run_id,
            run_manifest_sha256=run_authority.run_manifest_sha256,
            run_authority_sha256=run_authority.run_authority_sha256,
            allowed_origin=run_authority.allowed_origin,
            launch_url_sha256=run_authority.launch_url_sha256,
            launch_plan_sha256=run_authority.launch_plan_sha256,
            control_grant_sha256=run_authority.control_grant_sha256,
            source_observation_sha256=source_observation_sha256,
            source_screenshot_sha256=source_screenshot_sha256,
            visible_evidence_sha256=visible_evidence_sha256,
            visible_text_sha256=canonical_visible_text_sha256(visible_text),
            active_session_id=active_session_id,
            live_origin=live_origin,
            live_url_sha256=live_url_sha256,
            native_address_bar_receipt_sha256=native_receipt_sha256,
            window_binding_id=window_binding_id,
            window_generation=window_generation,
            window_identity_sha256=window_identity_sha256,
            registration_state=registration_state,
            registration_evidence_kind=registration_evidence_kind,
            registration_evidence_sha256=registration_evidence_sha256,
            provenance=provenance,
            launch_authority_sha256=launch_authority.launch_authority_sha256,
            owner_scope_kind=owner_scope_kind,
            synthetic_persona_id=synthetic_persona_id,
            synthetic_persona_sha256=synthetic_persona_sha256,
            issued_at_unix=_unix_time("issued_at", issued_at),
            expires_at_unix=_unix_time("expires_at", expires_at),
            hmac_sha256="0" * 64,
        )
        return replace(unsigned, hmac_sha256=_sign(secret, unsigned.signed_payload()))

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "launch_authority": self.launch_authority.to_dict(),
            "run_id": self.run_id,
            "run_manifest_sha256": self.run_manifest_sha256,
            "run_authority_sha256": self.run_authority_sha256,
            "allowed_origin": self.allowed_origin,
            "launch_url_sha256": self.launch_url_sha256,
            "launch_plan_sha256": self.launch_plan_sha256,
            "control_grant_sha256": self.control_grant_sha256,
            "source_observation_sha256": self.source_observation_sha256,
            "source_screenshot_sha256": self.source_screenshot_sha256,
            "visible_evidence_sha256": self.visible_evidence_sha256,
            "visible_text_sha256": self.visible_text_sha256,
            "active_session_id": self.active_session_id,
            "live_origin": self.live_origin,
            "live_url_sha256": self.live_url_sha256,
            "native_address_bar_receipt_sha256": self.native_address_bar_receipt_sha256,
            "window_binding_id": self.window_binding_id,
            "window_generation": self.window_generation,
            "window_identity_sha256": self.window_identity_sha256,
            "registration_state": self.registration_state,
            "registration_evidence_kind": self.registration_evidence_kind,
            "registration_evidence_sha256": self.registration_evidence_sha256,
            "provenance": self.provenance,
            "launch_authority_sha256": self.launch_authority_sha256,
            "owner_scope_kind": self.owner_scope_kind,
            "synthetic_persona_id": self.synthetic_persona_id,
            "synthetic_persona_sha256": self.synthetic_persona_sha256,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }

    def to_dict(self) -> dict[str, object]:
        return {"context": self.signed_payload(), "hmac_sha256": self.hmac_sha256}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def provider_context_sha256(self) -> str:
        return _sha256_json(self.to_dict())

    def verify_signature(self, secret: bytes | bytearray | memoryview) -> SCORMProviderContextEvidence:
        _verify(secret, self.signed_payload(), self.hmac_sha256, name="provider context")
        return self

    def validate_time(self, *, now: datetime) -> SCORMProviderContextEvidence:
        _validate_now(self.issued_at_unix, self.expires_at_unix, now, name="provider context")
        return self


@dataclass(frozen=True)
class SCORMFrameEvidence:
    """Exact visible frame; it carries no action interaction/effect authority."""

    run_id: str
    run_manifest_sha256: str
    run_authority_sha256: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    provider_context_sha256: str
    launch_authority_sha256: str
    source_observation_sha256: str
    source_screenshot_sha256: str
    visible_evidence_sha256: str
    visible_text: str
    visible_text_sha256: str
    active_session_id: str
    live_origin: str
    live_url_sha256: str
    native_address_bar_receipt_sha256: str
    window_binding_id: str
    window_generation: int
    window_identity_sha256: str
    registration_state: str
    registration_evidence_kind: str
    registration_evidence_sha256: str
    provenance: str
    owner_scope_kind: str | None
    synthetic_persona_sha256: str | None

    def __post_init__(self) -> None:
        _require_label("run_id", self.run_id)
        _canonical_public_origin(self.allowed_origin)
        _canonical_public_origin(self.live_origin)
        _require_label("active_session_id", self.active_session_id)
        _require_label("window_binding_id", self.window_binding_id)
        _require_int("window_generation", self.window_generation, minimum=0, maximum=2**63 - 1)
        _require_enum("registration_state", self.registration_state, _REGISTRATION_STATES)
        _require_enum("provenance", self.provenance, _PROVENANCE_KINDS)
        _require_label("registration_evidence_kind", self.registration_evidence_kind)
        if self.provenance == OWNER_BENCHMARK_ASSERTED:
            if (
                self.registration_state != SYNTHETIC_BENCHMARK
                or self.owner_scope_kind != SYNTHETIC_PERSONA_BENCHMARK
                or self.synthetic_persona_sha256 is None
            ):
                raise SCORMGrantFormatError("owner frame scope is incomplete")
        elif self.owner_scope_kind is not None or self.synthetic_persona_sha256 is not None:
            raise SCORMGrantFormatError("provider frame cannot carry owner scope")
        if self.synthetic_persona_sha256 is not None:
            _require_sha256("synthetic_persona_sha256", self.synthetic_persona_sha256)
        for name in (
            "run_manifest_sha256",
            "run_authority_sha256",
            "launch_url_sha256",
            "launch_plan_sha256",
            "control_grant_sha256",
            "provider_context_sha256",
            "launch_authority_sha256",
            "source_observation_sha256",
            "source_screenshot_sha256",
            "visible_evidence_sha256",
            "visible_text_sha256",
            "live_url_sha256",
            "native_address_bar_receipt_sha256",
            "window_identity_sha256",
            "registration_evidence_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        if canonical_visible_text_sha256(self.visible_text) != self.visible_text_sha256:
            raise SCORMGrantContextError("visible_text does not match visible_text_sha256")

    @classmethod
    def from_context(
        cls,
        context: SCORMProviderContextEvidence,
        *,
        visible_text: str,
    ) -> SCORMFrameEvidence:
        if not isinstance(context, SCORMProviderContextEvidence):
            raise TypeError("context must be SCORMProviderContextEvidence")
        return cls(
            run_id=context.run_id,
            run_manifest_sha256=context.run_manifest_sha256,
            run_authority_sha256=context.run_authority_sha256,
            allowed_origin=context.allowed_origin,
            launch_url_sha256=context.launch_url_sha256,
            launch_plan_sha256=context.launch_plan_sha256,
            control_grant_sha256=context.control_grant_sha256,
            provider_context_sha256=context.provider_context_sha256,
            launch_authority_sha256=context.launch_authority_sha256,
            source_observation_sha256=context.source_observation_sha256,
            source_screenshot_sha256=context.source_screenshot_sha256,
            visible_evidence_sha256=context.visible_evidence_sha256,
            visible_text=visible_text,
            visible_text_sha256=context.visible_text_sha256,
            active_session_id=context.active_session_id,
            live_origin=context.live_origin,
            live_url_sha256=context.live_url_sha256,
            native_address_bar_receipt_sha256=context.native_address_bar_receipt_sha256,
            window_binding_id=context.window_binding_id,
            window_generation=context.window_generation,
            window_identity_sha256=context.window_identity_sha256,
            registration_state=context.registration_state,
            registration_evidence_kind=context.registration_evidence_kind,
            registration_evidence_sha256=context.registration_evidence_sha256,
            provenance=context.provenance,
            owner_scope_kind=context.owner_scope_kind,
            synthetic_persona_sha256=context.synthetic_persona_sha256,
        )


@dataclass(frozen=True)
class SCORMPreflightDecision:
    """Frame-only decision that cannot authorize an action."""

    kind: str
    reason: str
    prerequisite: str | None
    run_authority_sha256: str
    provider_context_sha256: str
    launch_authority_sha256: str
    provenance: str
    synthetic_persona_sha256: str | None
    source_observation_sha256: str
    source_screenshot_sha256: str
    visible_evidence_sha256: str
    visible_text_sha256: str
    window_context_sha256: str
    preflight_sha256: str
    schema_version: str = PREFLIGHT_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PREFLIGHT_DECISION_SCHEMA_VERSION:
            raise SCORMCoherenceError("preflight schema mismatch")
        _require_enum("preflight kind", self.kind, _PREFLIGHT_KINDS)
        _require_label("preflight reason", self.reason)
        for name in (
            "run_authority_sha256",
            "provider_context_sha256",
            "launch_authority_sha256",
            "source_observation_sha256",
            "source_screenshot_sha256",
            "visible_evidence_sha256",
            "visible_text_sha256",
            "window_context_sha256",
            "preflight_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        _require_enum("preflight provenance", self.provenance, _PROVENANCE_KINDS)
        if self.synthetic_persona_sha256 is not None:
            _require_sha256("synthetic_persona_sha256", self.synthetic_persona_sha256)
        if self.kind == RESUMABLE_PAUSE:
            _require_enum("preflight prerequisite", self.prerequisite, _PREREQUISITES)
        elif self.prerequisite is not None:
            raise SCORMCoherenceError("ready preflight cannot name a prerequisite")
        if self.preflight_sha256 != _sha256_json(self.digest_payload()):
            raise SCORMCoherenceError("preflight digest mismatch")

    @classmethod
    def build(
        cls,
        *,
        kind: str,
        reason: str,
        prerequisite: str | None,
        frame: SCORMFrameEvidence,
    ) -> SCORMPreflightDecision:
        window_context = _sha256_json(
            {
                "active_session_id": frame.active_session_id,
                "window_binding_id": frame.window_binding_id,
                "window_generation": frame.window_generation,
                "window_identity_sha256": frame.window_identity_sha256,
            }
        )
        base = {
            "schema_version": PREFLIGHT_DECISION_SCHEMA_VERSION,
            "kind": kind,
            "reason": reason,
            "prerequisite": prerequisite,
            "run_authority_sha256": frame.run_authority_sha256,
            "provider_context_sha256": frame.provider_context_sha256,
            "launch_authority_sha256": frame.launch_authority_sha256,
            "provenance": frame.provenance,
            "synthetic_persona_sha256": frame.synthetic_persona_sha256,
            "source_observation_sha256": frame.source_observation_sha256,
            "source_screenshot_sha256": frame.source_screenshot_sha256,
            "visible_evidence_sha256": frame.visible_evidence_sha256,
            "visible_text_sha256": frame.visible_text_sha256,
            "window_context_sha256": window_context,
        }
        return cls(
            kind=kind,
            reason=reason,
            prerequisite=prerequisite,
            run_authority_sha256=frame.run_authority_sha256,
            provider_context_sha256=frame.provider_context_sha256,
            launch_authority_sha256=frame.launch_authority_sha256,
            provenance=frame.provenance,
            synthetic_persona_sha256=frame.synthetic_persona_sha256,
            source_observation_sha256=frame.source_observation_sha256,
            source_screenshot_sha256=frame.source_screenshot_sha256,
            visible_evidence_sha256=frame.visible_evidence_sha256,
            visible_text_sha256=frame.visible_text_sha256,
            window_context_sha256=window_context,
            preflight_sha256=_sha256_json(base),
        )

    def digest_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "reason": self.reason,
            "prerequisite": self.prerequisite,
            "run_authority_sha256": self.run_authority_sha256,
            "provider_context_sha256": self.provider_context_sha256,
            "launch_authority_sha256": self.launch_authority_sha256,
            "provenance": self.provenance,
            "synthetic_persona_sha256": self.synthetic_persona_sha256,
            "source_observation_sha256": self.source_observation_sha256,
            "source_screenshot_sha256": self.source_screenshot_sha256,
            "visible_evidence_sha256": self.visible_evidence_sha256,
            "visible_text_sha256": self.visible_text_sha256,
            "window_context_sha256": self.window_context_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self.digest_payload(), "preflight_sha256": self.preflight_sha256}


@dataclass(frozen=True)
class SCORMActionCoordinates:
    x: int
    y: int

    def __post_init__(self) -> None:
        _require_int("coordinate x", self.x, minimum=0, maximum=2**31 - 1)
        _require_int("coordinate y", self.y, minimum=0, maximum=2**31 - 1)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class SCORMTargetBounds:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        _require_int("target x", self.x, minimum=0, maximum=2**31 - 1)
        _require_int("target y", self.y, minimum=0, maximum=2**31 - 1)
        _require_int("target width", self.width, minimum=1, maximum=2**31 - 1)
        _require_int("target height", self.height, minimum=1, maximum=2**31 - 1)

    def contains(self, coordinates: SCORMActionCoordinates) -> bool:
        return (
            self.x <= coordinates.x < self.x + self.width and self.y <= coordinates.y < self.y + self.height
        )

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True, init=False)
class SCORMActionIntent:
    """Immutable digest binding for one proposed GUI action."""

    name: str
    action_sequence: int
    source_observation_sha256: str
    action_sha256: str
    coordinates: SCORMActionCoordinates | None
    _params_json: str

    def __init__(
        self,
        *,
        name: str,
        params: Mapping[str, object],
        action_sequence: int,
        source_observation_sha256: str,
        coordinates: SCORMActionCoordinates | Mapping[str, object] | None = None,
    ) -> None:
        _require_label("action name", name)
        _require_int("action_sequence", action_sequence, minimum=1, maximum=_MAX_ACTION_SEQUENCE)
        _require_sha256("source_observation_sha256", source_observation_sha256)
        if not isinstance(params, Mapping):
            raise TypeError("action params must be a mapping")
        detached = json.loads(_canonical_json(dict(params)))
        if not isinstance(detached, dict):
            raise SCORMCoherenceError("action params must encode as an object")
        params_json = _canonical_json(detached)
        if len(params_json.encode("utf-8")) > _MAX_JSON_BYTES:
            raise SCORMCoherenceError("action params exceed size limit")
        has_x = "x" in detached
        has_y = "y" in detached
        if has_x != has_y:
            raise SCORMCoherenceError("coordinate action must provide both x and y")
        inferred = None
        if has_x:
            inferred = SCORMActionCoordinates(
                x=_require_int("action coordinate x", detached["x"], minimum=0, maximum=2**31 - 1),
                y=_require_int("action coordinate y", detached["y"], minimum=0, maximum=2**31 - 1),
            )
        explicit = self._coordinates(coordinates)
        if explicit is not None and inferred is None:
            raise SCORMCoherenceError("coordinates supplied for action without x/y params")
        if explicit is not None and explicit != inferred:
            raise SCORMCoherenceError("explicit coordinates do not match action params")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "action_sequence", action_sequence)
        object.__setattr__(self, "source_observation_sha256", source_observation_sha256)
        object.__setattr__(self, "action_sha256", canonical_action_sha256(name, detached))
        object.__setattr__(self, "coordinates", inferred)
        object.__setattr__(self, "_params_json", params_json)

    @staticmethod
    def _coordinates(
        value: SCORMActionCoordinates | Mapping[str, object] | None,
    ) -> SCORMActionCoordinates | None:
        if value is None or isinstance(value, SCORMActionCoordinates):
            return value
        mapping = _require_exact_keys("coordinates", value, frozenset({"x", "y"}))
        return SCORMActionCoordinates(
            x=_require_int("coordinate x", mapping["x"], minimum=0, maximum=2**31 - 1),
            y=_require_int("coordinate y", mapping["y"], minimum=0, maximum=2**31 - 1),
        )

    @classmethod
    def from_action(
        cls,
        name: str,
        params: Mapping[str, object],
        *,
        action_sequence: int,
        source_observation_sha256: str,
        coordinates: SCORMActionCoordinates | Mapping[str, object] | None = None,
    ) -> SCORMActionIntent:
        return cls(
            name=name,
            params=params,
            action_sequence=action_sequence,
            source_observation_sha256=source_observation_sha256,
            coordinates=coordinates,
        )

    @property
    def params(self) -> dict[str, object]:
        parsed = json.loads(self._params_json)
        if not isinstance(parsed, dict):  # pragma: no cover - constructor invariant
            raise SCORMCoherenceError("stored action params are invalid")
        return parsed


def _interaction_for_semantic(target_semantic: str) -> str:
    if target_semantic in {NAVIGATION_CONTROL, WINDOW_NAVIGATION}:
        return NAVIGATION
    if target_semantic == ASSESSMENT_CONTROL:
        return ASSESSMENT_RESPONSE
    if target_semantic == CREDENTIAL_COMMIT_CONTROL:
        return CREDENTIAL_MUTATION
    raise SCORMCoherenceError("target semantic is unsupported")


@dataclass(frozen=True)
class SCORMActionTargetEvidence:
    """Owner-keyed native evidence for one exact proposed action and target."""

    issuer: str
    key_id: str
    run_id: str
    run_manifest_sha256: str
    run_authority_sha256: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    provider_context_sha256: str
    launch_authority_sha256: str
    provenance: str
    owner_scope_kind: str
    synthetic_persona_sha256: str
    source_observation_sha256: str
    intent_source_observation_sha256: str
    source_screenshot_sha256: str
    visible_evidence_sha256: str
    visible_text_sha256: str
    active_session_id: str
    live_origin: str
    live_url_sha256: str
    native_address_bar_receipt_sha256: str
    window_binding_id: str
    window_generation: int
    window_identity_sha256: str
    action_sequence: int
    action_name: str
    action_sha256: str
    coordinates: SCORMActionCoordinates | None
    target_surface: str
    target_bounds: SCORMTargetBounds | None
    target_evidence_kind: str
    target_evidence_sha256: str
    accessibility_role_sha256: str | None
    accessibility_name_sha256: str | None
    accessibility_automation_id_sha256: str | None
    target_semantic: str
    registration_state: str
    registration_evidence_kind: str
    registration_evidence_sha256: str
    interaction_kind: str
    interaction_evidence_kind: str
    interaction_evidence_sha256: str
    credential_effect: str
    effect_evidence_kind: str
    effect_evidence_sha256: str
    issued_at_unix: int
    expires_at_unix: int
    hmac_sha256: str
    schema_version: str = ACTION_TARGET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACTION_TARGET_SCHEMA_VERSION:
            raise SCORMGrantFormatError("action target schema mismatch")
        _require_label("issuer", self.issuer)
        _require_label("key_id", self.key_id)
        if self.provenance != OWNER_BENCHMARK_ASSERTED:
            raise SCORMGrantFormatError("action target must use owner benchmark provenance")
        if self.owner_scope_kind != SYNTHETIC_PERSONA_BENCHMARK:
            raise SCORMGrantFormatError("action target owner scope mismatch")
        _require_label("run_id", self.run_id)
        _canonical_public_origin(self.allowed_origin)
        _canonical_public_origin(self.live_origin)
        _require_label("active_session_id", self.active_session_id)
        _require_label("window_binding_id", self.window_binding_id)
        _require_int("window_generation", self.window_generation, minimum=0, maximum=2**63 - 1)
        _require_int("action_sequence", self.action_sequence, minimum=1, maximum=_MAX_ACTION_SEQUENCE)
        _require_label("action_name", self.action_name)
        _require_enum("target_surface", self.target_surface, _TARGET_SURFACES)
        _require_enum("target_evidence_kind", self.target_evidence_kind, _TARGET_EVIDENCE_KINDS)
        _require_enum("target_semantic", self.target_semantic, _TARGET_SEMANTICS)
        _require_enum("registration_state", self.registration_state, _REGISTRATION_STATES)
        if self.registration_state != SYNTHETIC_BENCHMARK:
            raise SCORMGrantFormatError("owner action target requires synthetic benchmark state")
        _require_label("registration_evidence_kind", self.registration_evidence_kind)
        _require_enum("interaction_kind", self.interaction_kind, _INTERACTION_KINDS)
        _require_label("interaction_evidence_kind", self.interaction_evidence_kind)
        _require_enum("credential_effect", self.credential_effect, _CREDENTIAL_EFFECTS)
        _require_label("effect_evidence_kind", self.effect_evidence_kind)
        if any(
            "provider" in value.casefold()
            for value in (
                self.registration_evidence_kind,
                self.interaction_evidence_kind,
                self.effect_evidence_kind,
            )
        ):
            raise SCORMGrantFormatError(
                "owner-keyed target evidence cannot claim provider provenance"
            )
        for name in (
            "run_manifest_sha256",
            "run_authority_sha256",
            "launch_url_sha256",
            "launch_plan_sha256",
            "control_grant_sha256",
            "provider_context_sha256",
            "launch_authority_sha256",
            "synthetic_persona_sha256",
            "source_observation_sha256",
            "intent_source_observation_sha256",
            "source_screenshot_sha256",
            "visible_evidence_sha256",
            "visible_text_sha256",
            "live_url_sha256",
            "native_address_bar_receipt_sha256",
            "window_identity_sha256",
            "action_sha256",
            "target_evidence_sha256",
            "registration_evidence_sha256",
            "interaction_evidence_sha256",
            "effect_evidence_sha256",
            "hmac_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        for name in (
            "accessibility_role_sha256",
            "accessibility_name_sha256",
            "accessibility_automation_id_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_sha256(name, value)
        if self.interaction_kind != _interaction_for_semantic(self.target_semantic):
            raise SCORMGrantFormatError("interaction kind does not match target semantic")
        expected_effect = {
            NAVIGATION_CONTROL: NO_CREDENTIAL_EFFECT,
            WINDOW_NAVIGATION: NO_CREDENTIAL_EFFECT,
            ASSESSMENT_CONTROL: PREVIEW_ONLY,
            CREDENTIAL_COMMIT_CONTROL: REAL_IDENTITY_BOUND,
        }[self.target_semantic]
        if self.credential_effect != expected_effect:
            raise SCORMGrantFormatError("credential effect does not match target semantic")
        self._validate_surface()
        _validate_lifetime(
            self.issued_at_unix,
            self.expires_at_unix,
            name="action target",
            maximum=MAX_ACTION_LIFETIME_SECONDS,
        )

    def _validate_surface(self) -> None:
        if self.action_name in _COORDINATE_ACTIONS:
            if self.coordinates is None or self.target_surface != COORDINATE_CONTROL:
                raise SCORMGrantFormatError("coordinate action requires coordinate_control target")
            if self.target_bounds is None or not self.target_bounds.contains(self.coordinates):
                raise SCORMGrantFormatError("action coordinates must be inside exact target bounds")
            if self.target_evidence_kind != NATIVE_ACCESSIBILITY_CONTROL:
                raise SCORMGrantFormatError("coordinate target requires native accessibility evidence")
            if self.accessibility_role_sha256 is None or self.accessibility_name_sha256 is None:
                raise SCORMGrantFormatError("coordinate target requires role and name evidence")
        elif self.action_name in _FOCUSED_ACTIONS:
            if self.coordinates is not None or self.target_surface != FOCUSED_CONTROL:
                raise SCORMGrantFormatError("keyboard action requires focused_control target")
            if self.target_evidence_kind != NATIVE_FOCUSED_CONTROL:
                raise SCORMGrantFormatError("keyboard action requires native focus evidence")
            if self.accessibility_role_sha256 is None or (
                self.accessibility_name_sha256 is None and self.accessibility_automation_id_sha256 is None
            ):
                raise SCORMGrantFormatError("focused target requires role and control identity")
        elif self.action_name in _WAIT_ACTIONS:
            if (
                self.coordinates is not None
                or self.target_surface != FRAME_WAIT
                or self.target_bounds is not None
                or self.target_evidence_kind != BOUND_WINDOW_SURFACE
            ):
                raise SCORMGrantFormatError("wait action requires bound frame_wait evidence")
            if any(
                value is not None
                for value in (
                    self.accessibility_role_sha256,
                    self.accessibility_name_sha256,
                    self.accessibility_automation_id_sha256,
                )
            ):
                raise SCORMGrantFormatError("frame_wait cannot carry control identity")
        else:
            raise SCORMGrantFormatError("action target name is unsupported")

    @classmethod
    def issue(
        cls,
        *,
        owner_secret: bytes | bytearray | memoryview,
        provider_context: SCORMProviderContextEvidence,
        frame: SCORMFrameEvidence,
        intent: SCORMActionIntent,
        target_surface: str,
        target_bounds: SCORMTargetBounds | None,
        target_evidence_kind: str,
        target_evidence_sha256: str,
        accessibility_role_sha256: str | None,
        accessibility_name_sha256: str | None,
        accessibility_automation_id_sha256: str | None,
        target_semantic: str,
        interaction_evidence_kind: str,
        interaction_evidence_sha256: str,
        credential_effect: str,
        effect_evidence_kind: str,
        effect_evidence_sha256: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> SCORMActionTargetEvidence:
        if not isinstance(provider_context, SCORMProviderContextEvidence):
            raise TypeError("provider_context must be SCORMProviderContextEvidence")
        if not isinstance(frame, SCORMFrameEvidence):
            raise TypeError("frame must be SCORMFrameEvidence")
        if not isinstance(intent, SCORMActionIntent):
            raise TypeError("intent must be SCORMActionIntent")
        if intent.source_observation_sha256 != frame.source_observation_sha256:
            raise SCORMGrantContextError("intent source observation does not match current frame")
        launch_authority = provider_context.launch_authority
        if not isinstance(launch_authority, SCORMOwnerBenchmarkLaunchAuthority):
            raise SCORMGrantContextError(
                "locally issued action targets require owner benchmark launch authority"
            )
        unsigned = cls(
            issuer=launch_authority.issuer,
            key_id=launch_authority.key_id,
            run_id=frame.run_id,
            run_manifest_sha256=frame.run_manifest_sha256,
            run_authority_sha256=frame.run_authority_sha256,
            allowed_origin=frame.allowed_origin,
            launch_url_sha256=frame.launch_url_sha256,
            launch_plan_sha256=frame.launch_plan_sha256,
            control_grant_sha256=frame.control_grant_sha256,
            provider_context_sha256=frame.provider_context_sha256,
            launch_authority_sha256=frame.launch_authority_sha256,
            provenance=frame.provenance,
            owner_scope_kind=launch_authority.scope,
            synthetic_persona_sha256=launch_authority.synthetic_persona_sha256,
            source_observation_sha256=frame.source_observation_sha256,
            intent_source_observation_sha256=intent.source_observation_sha256,
            source_screenshot_sha256=frame.source_screenshot_sha256,
            visible_evidence_sha256=frame.visible_evidence_sha256,
            visible_text_sha256=frame.visible_text_sha256,
            active_session_id=frame.active_session_id,
            live_origin=frame.live_origin,
            live_url_sha256=frame.live_url_sha256,
            native_address_bar_receipt_sha256=frame.native_address_bar_receipt_sha256,
            window_binding_id=frame.window_binding_id,
            window_generation=frame.window_generation,
            window_identity_sha256=frame.window_identity_sha256,
            action_sequence=intent.action_sequence,
            action_name=intent.name,
            action_sha256=intent.action_sha256,
            coordinates=intent.coordinates,
            target_surface=target_surface,
            target_bounds=target_bounds,
            target_evidence_kind=target_evidence_kind,
            target_evidence_sha256=target_evidence_sha256,
            accessibility_role_sha256=accessibility_role_sha256,
            accessibility_name_sha256=accessibility_name_sha256,
            accessibility_automation_id_sha256=accessibility_automation_id_sha256,
            target_semantic=target_semantic,
            registration_state=frame.registration_state,
            registration_evidence_kind=frame.registration_evidence_kind,
            registration_evidence_sha256=frame.registration_evidence_sha256,
            interaction_kind=_interaction_for_semantic(target_semantic),
            interaction_evidence_kind=interaction_evidence_kind,
            interaction_evidence_sha256=interaction_evidence_sha256,
            credential_effect=credential_effect,
            effect_evidence_kind=effect_evidence_kind,
            effect_evidence_sha256=effect_evidence_sha256,
            issued_at_unix=_unix_time("issued_at", issued_at),
            expires_at_unix=_unix_time("expires_at", expires_at),
            hmac_sha256="0" * 64,
        )
        return replace(unsigned, hmac_sha256=_sign(owner_secret, unsigned.signed_payload()))

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "issuer": self.issuer,
            "key_id": self.key_id,
            "run_id": self.run_id,
            "run_manifest_sha256": self.run_manifest_sha256,
            "run_authority_sha256": self.run_authority_sha256,
            "allowed_origin": self.allowed_origin,
            "launch_url_sha256": self.launch_url_sha256,
            "launch_plan_sha256": self.launch_plan_sha256,
            "control_grant_sha256": self.control_grant_sha256,
            "provider_context_sha256": self.provider_context_sha256,
            "launch_authority_sha256": self.launch_authority_sha256,
            "provenance": self.provenance,
            "owner_scope_kind": self.owner_scope_kind,
            "synthetic_persona_sha256": self.synthetic_persona_sha256,
            "source_observation_sha256": self.source_observation_sha256,
            "intent_source_observation_sha256": self.intent_source_observation_sha256,
            "source_screenshot_sha256": self.source_screenshot_sha256,
            "visible_evidence_sha256": self.visible_evidence_sha256,
            "visible_text_sha256": self.visible_text_sha256,
            "active_session_id": self.active_session_id,
            "live_origin": self.live_origin,
            "live_url_sha256": self.live_url_sha256,
            "native_address_bar_receipt_sha256": self.native_address_bar_receipt_sha256,
            "window_binding_id": self.window_binding_id,
            "window_generation": self.window_generation,
            "window_identity_sha256": self.window_identity_sha256,
            "action_sequence": self.action_sequence,
            "action_name": self.action_name,
            "action_sha256": self.action_sha256,
            "coordinates": self.coordinates.to_dict() if self.coordinates is not None else None,
            "target_surface": self.target_surface,
            "target_bounds": self.target_bounds.to_dict() if self.target_bounds is not None else None,
            "target_evidence_kind": self.target_evidence_kind,
            "target_evidence_sha256": self.target_evidence_sha256,
            "accessibility_role_sha256": self.accessibility_role_sha256,
            "accessibility_name_sha256": self.accessibility_name_sha256,
            "accessibility_automation_id_sha256": self.accessibility_automation_id_sha256,
            "target_semantic": self.target_semantic,
            "registration_state": self.registration_state,
            "registration_evidence_kind": self.registration_evidence_kind,
            "registration_evidence_sha256": self.registration_evidence_sha256,
            "interaction_kind": self.interaction_kind,
            "interaction_evidence_kind": self.interaction_evidence_kind,
            "interaction_evidence_sha256": self.interaction_evidence_sha256,
            "credential_effect": self.credential_effect,
            "effect_evidence_kind": self.effect_evidence_kind,
            "effect_evidence_sha256": self.effect_evidence_sha256,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }

    def to_dict(self) -> dict[str, object]:
        return {"target": self.signed_payload(), "hmac_sha256": self.hmac_sha256}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def action_target_sha256(self) -> str:
        return _sha256_json(self.to_dict())

    def verify_signature(
        self, owner_secret: bytes | bytearray | memoryview
    ) -> SCORMActionTargetEvidence:
        _verify(owner_secret, self.signed_payload(), self.hmac_sha256, name="action target")
        return self

    def validate_time(self, *, now: datetime) -> SCORMActionTargetEvidence:
        _validate_now(self.issued_at_unix, self.expires_at_unix, now, name="action target")
        return self


@dataclass(frozen=True)
class SCORMBenchmarkGrant:
    """Owner-signed authority for one exact synthetic assessment action."""

    benchmark_id: str
    replay_nonce: str
    run_id: str
    run_manifest_sha256: str
    run_authority_sha256: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    provider_context_sha256: str
    launch_authority_sha256: str
    provenance: str
    owner_scope_kind: str
    synthetic_persona_sha256: str
    source_observation_sha256: str
    intent_source_observation_sha256: str
    source_screenshot_sha256: str
    visible_evidence_sha256: str
    visible_text_sha256: str
    window_binding_id: str
    window_generation: int
    window_identity_sha256: str
    action_target_sha256: str
    action_sequence: int
    action_name: str
    action_sha256: str
    coordinates: SCORMActionCoordinates | None
    target_evidence_sha256: str
    registration_state: str
    interaction_kind: str
    credential_effect: str
    issued_at_unix: int
    expires_at_unix: int
    hmac_sha256: str
    schema_version: str = BENCHMARK_GRANT_SCHEMA_VERSION
    mode: str = BENCHMARK_MODE

    def __post_init__(self) -> None:
        if self.schema_version != BENCHMARK_GRANT_SCHEMA_VERSION or self.mode != BENCHMARK_MODE:
            raise SCORMGrantFormatError("benchmark grant schema or mode mismatch")
        _require_label("benchmark_id", self.benchmark_id)
        _require_label("replay_nonce", self.replay_nonce, minimum_length=16)
        _require_label("run_id", self.run_id)
        _canonical_public_origin(self.allowed_origin)
        _require_label("window_binding_id", self.window_binding_id)
        _require_int("window_generation", self.window_generation, minimum=0, maximum=2**63 - 1)
        _require_int("action_sequence", self.action_sequence, minimum=1, maximum=_MAX_ACTION_SEQUENCE)
        _require_label("action_name", self.action_name)
        if self.provenance != OWNER_BENCHMARK_ASSERTED:
            raise SCORMGrantFormatError("benchmark grant requires owner benchmark provenance")
        if self.owner_scope_kind != SYNTHETIC_PERSONA_BENCHMARK:
            raise SCORMGrantFormatError("benchmark grant owner scope mismatch")
        if self.registration_state != SYNTHETIC_BENCHMARK:
            raise SCORMGrantFormatError("benchmark grant requires synthetic benchmark state")
        if self.interaction_kind != ASSESSMENT_RESPONSE or self.credential_effect != PREVIEW_ONLY:
            raise SCORMGrantFormatError("benchmark grant is assessment-preview only")
        for name in (
            "run_manifest_sha256",
            "run_authority_sha256",
            "launch_url_sha256",
            "launch_plan_sha256",
            "control_grant_sha256",
            "provider_context_sha256",
            "launch_authority_sha256",
            "synthetic_persona_sha256",
            "source_observation_sha256",
            "intent_source_observation_sha256",
            "source_screenshot_sha256",
            "visible_evidence_sha256",
            "visible_text_sha256",
            "window_identity_sha256",
            "action_target_sha256",
            "action_sha256",
            "target_evidence_sha256",
            "hmac_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        _validate_lifetime(
            self.issued_at_unix,
            self.expires_at_unix,
            name="benchmark grant",
            maximum=MAX_ACTION_LIFETIME_SECONDS,
        )

    @classmethod
    def issue(
        cls,
        *,
        owner_secret: bytes | bytearray | memoryview,
        benchmark_id: str,
        replay_nonce: str,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        frame: SCORMFrameEvidence,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        issued_at: datetime,
        expires_at: datetime,
    ) -> SCORMBenchmarkGrant:
        if not isinstance(action_target, SCORMActionTargetEvidence):
            raise TypeError("action_target must be SCORMActionTargetEvidence")
        if intent.source_observation_sha256 != frame.source_observation_sha256:
            raise SCORMGrantContextError("intent source observation does not match current frame")
        if action_target.intent_source_observation_sha256 != intent.source_observation_sha256:
            raise SCORMGrantContextError("action target does not bind intent source observation")
        launch_authority = provider_context.launch_authority
        if not isinstance(launch_authority, SCORMOwnerBenchmarkLaunchAuthority):
            raise SCORMGrantContextError(
                "locally issued benchmark grants require owner launch authority"
            )
        unsigned = cls(
            benchmark_id=benchmark_id,
            replay_nonce=replay_nonce,
            run_id=run_authority.run_id,
            run_manifest_sha256=run_authority.run_manifest_sha256,
            run_authority_sha256=run_authority.run_authority_sha256,
            allowed_origin=run_authority.allowed_origin,
            launch_url_sha256=run_authority.launch_url_sha256,
            launch_plan_sha256=run_authority.launch_plan_sha256,
            control_grant_sha256=run_authority.control_grant_sha256,
            provider_context_sha256=provider_context.provider_context_sha256,
            launch_authority_sha256=provider_context.launch_authority_sha256,
            provenance=provider_context.provenance,
            owner_scope_kind=launch_authority.scope,
            synthetic_persona_sha256=launch_authority.synthetic_persona_sha256,
            source_observation_sha256=frame.source_observation_sha256,
            intent_source_observation_sha256=intent.source_observation_sha256,
            source_screenshot_sha256=frame.source_screenshot_sha256,
            visible_evidence_sha256=frame.visible_evidence_sha256,
            visible_text_sha256=frame.visible_text_sha256,
            window_binding_id=frame.window_binding_id,
            window_generation=frame.window_generation,
            window_identity_sha256=frame.window_identity_sha256,
            action_target_sha256=action_target.action_target_sha256,
            action_sequence=intent.action_sequence,
            action_name=intent.name,
            action_sha256=intent.action_sha256,
            coordinates=intent.coordinates,
            target_evidence_sha256=action_target.target_evidence_sha256,
            registration_state=action_target.registration_state,
            interaction_kind=action_target.interaction_kind,
            credential_effect=action_target.credential_effect,
            issued_at_unix=_unix_time("issued_at", issued_at),
            expires_at_unix=_unix_time("expires_at", expires_at),
            hmac_sha256="0" * 64,
        )
        return replace(unsigned, hmac_sha256=_sign(owner_secret, unsigned.signed_payload()))

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "benchmark_id": self.benchmark_id,
            "replay_nonce": self.replay_nonce,
            "run_id": self.run_id,
            "run_manifest_sha256": self.run_manifest_sha256,
            "run_authority_sha256": self.run_authority_sha256,
            "allowed_origin": self.allowed_origin,
            "launch_url_sha256": self.launch_url_sha256,
            "launch_plan_sha256": self.launch_plan_sha256,
            "control_grant_sha256": self.control_grant_sha256,
            "provider_context_sha256": self.provider_context_sha256,
            "launch_authority_sha256": self.launch_authority_sha256,
            "provenance": self.provenance,
            "owner_scope_kind": self.owner_scope_kind,
            "synthetic_persona_sha256": self.synthetic_persona_sha256,
            "source_observation_sha256": self.source_observation_sha256,
            "intent_source_observation_sha256": self.intent_source_observation_sha256,
            "source_screenshot_sha256": self.source_screenshot_sha256,
            "visible_evidence_sha256": self.visible_evidence_sha256,
            "visible_text_sha256": self.visible_text_sha256,
            "window_binding_id": self.window_binding_id,
            "window_generation": self.window_generation,
            "window_identity_sha256": self.window_identity_sha256,
            "action_target_sha256": self.action_target_sha256,
            "action_sequence": self.action_sequence,
            "action_name": self.action_name,
            "action_sha256": self.action_sha256,
            "coordinates": self.coordinates.to_dict() if self.coordinates is not None else None,
            "target_evidence_sha256": self.target_evidence_sha256,
            "registration_state": self.registration_state,
            "interaction_kind": self.interaction_kind,
            "credential_effect": self.credential_effect,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }

    def to_dict(self) -> dict[str, object]:
        return {"grant": self.signed_payload(), "hmac_sha256": self.hmac_sha256}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def benchmark_grant_sha256(self) -> str:
        return _sha256_json(self.to_dict())

    @property
    def grant_sha256(self) -> str:
        return self.benchmark_grant_sha256

    def verify_signature(
        self, owner_secret: bytes | bytearray | memoryview
    ) -> SCORMBenchmarkGrant:
        _verify(owner_secret, self.signed_payload(), self.hmac_sha256, name="benchmark grant")
        return self

    def validate_time(self, *, now: datetime) -> SCORMBenchmarkGrant:
        _validate_now(self.issued_at_unix, self.expires_at_unix, now, name="benchmark grant")
        return self


@dataclass(frozen=True)
class SCORMActionDecision:
    """Post-intent decision bound to one exact authority and target."""

    kind: str
    reason: str
    prerequisite: str | None
    preflight_sha256: str
    run_authority_sha256: str
    provider_context_sha256: str
    launch_authority_sha256: str
    provenance: str
    synthetic_persona_sha256: str | None
    source_observation_sha256: str
    intent_source_observation_sha256: str
    visible_evidence_sha256: str
    visible_text_sha256: str
    action_target_sha256: str
    action_sequence: int
    action_sha256: str
    benchmark_grant_sha256: str | None
    decision_sha256: str
    schema_version: str = ACTION_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACTION_DECISION_SCHEMA_VERSION:
            raise SCORMCoherenceError("action decision schema mismatch")
        _require_enum("action decision kind", self.kind, _ACTION_DECISION_KINDS)
        _require_label("action decision reason", self.reason)
        for name in (
            "preflight_sha256",
            "run_authority_sha256",
            "provider_context_sha256",
            "launch_authority_sha256",
            "source_observation_sha256",
            "intent_source_observation_sha256",
            "visible_evidence_sha256",
            "visible_text_sha256",
            "action_target_sha256",
            "action_sha256",
            "decision_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        _require_enum("decision provenance", self.provenance, _PROVENANCE_KINDS)
        if self.synthetic_persona_sha256 is not None:
            _require_sha256("synthetic_persona_sha256", self.synthetic_persona_sha256)
        _require_int("action_sequence", self.action_sequence, minimum=1, maximum=_MAX_ACTION_SEQUENCE)
        if self.benchmark_grant_sha256 is not None:
            _require_sha256("benchmark_grant_sha256", self.benchmark_grant_sha256)
        if self.kind == RESUMABLE_PAUSE:
            _require_enum("action prerequisite", self.prerequisite, _PREREQUISITES)
        elif self.prerequisite is not None:
            raise SCORMCoherenceError("non-pause action decision cannot name a prerequisite")
        if self.kind != CONTINUE and self.benchmark_grant_sha256 is not None:
            raise SCORMCoherenceError("only continue may bind a benchmark grant")
        if self.kind == OWNER_ATTESTATION_REQUIRED and (
            self.reason != "real_identity_bound_credential_mutation"
        ):
            raise SCORMCoherenceError("owner attestation is identity-mutation only")
        if self.decision_sha256 != _sha256_json(self.digest_payload()):
            raise SCORMCoherenceError("action decision digest mismatch")

    @classmethod
    def build(
        cls,
        *,
        kind: str,
        reason: str,
        prerequisite: str | None,
        preflight: SCORMPreflightDecision,
        frame: SCORMFrameEvidence,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        benchmark_grant_sha256: str | None = None,
    ) -> SCORMActionDecision:
        if intent.source_observation_sha256 != frame.source_observation_sha256:
            raise SCORMGrantContextError("intent source observation does not match current frame")
        if action_target.intent_source_observation_sha256 != intent.source_observation_sha256:
            raise SCORMGrantContextError("action target does not bind intent source observation")
        base = {
            "schema_version": ACTION_DECISION_SCHEMA_VERSION,
            "kind": kind,
            "reason": reason,
            "prerequisite": prerequisite,
            "preflight_sha256": preflight.preflight_sha256,
            "run_authority_sha256": frame.run_authority_sha256,
            "provider_context_sha256": frame.provider_context_sha256,
            "launch_authority_sha256": frame.launch_authority_sha256,
            "provenance": frame.provenance,
            "synthetic_persona_sha256": frame.synthetic_persona_sha256,
            "source_observation_sha256": frame.source_observation_sha256,
            "intent_source_observation_sha256": intent.source_observation_sha256,
            "visible_evidence_sha256": frame.visible_evidence_sha256,
            "visible_text_sha256": frame.visible_text_sha256,
            "action_target_sha256": action_target.action_target_sha256,
            "action_sequence": intent.action_sequence,
            "action_sha256": intent.action_sha256,
            "benchmark_grant_sha256": benchmark_grant_sha256,
        }
        return cls(
            kind=kind,
            reason=reason,
            prerequisite=prerequisite,
            preflight_sha256=preflight.preflight_sha256,
            run_authority_sha256=frame.run_authority_sha256,
            provider_context_sha256=frame.provider_context_sha256,
            launch_authority_sha256=frame.launch_authority_sha256,
            provenance=frame.provenance,
            synthetic_persona_sha256=frame.synthetic_persona_sha256,
            source_observation_sha256=frame.source_observation_sha256,
            intent_source_observation_sha256=intent.source_observation_sha256,
            visible_evidence_sha256=frame.visible_evidence_sha256,
            visible_text_sha256=frame.visible_text_sha256,
            action_target_sha256=action_target.action_target_sha256,
            action_sequence=intent.action_sequence,
            action_sha256=intent.action_sha256,
            benchmark_grant_sha256=benchmark_grant_sha256,
            decision_sha256=_sha256_json(base),
        )

    @property
    def coherence_sha256(self) -> str:
        return self.decision_sha256

    def digest_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "reason": self.reason,
            "prerequisite": self.prerequisite,
            "preflight_sha256": self.preflight_sha256,
            "run_authority_sha256": self.run_authority_sha256,
            "provider_context_sha256": self.provider_context_sha256,
            "launch_authority_sha256": self.launch_authority_sha256,
            "provenance": self.provenance,
            "synthetic_persona_sha256": self.synthetic_persona_sha256,
            "source_observation_sha256": self.source_observation_sha256,
            "intent_source_observation_sha256": self.intent_source_observation_sha256,
            "visible_evidence_sha256": self.visible_evidence_sha256,
            "visible_text_sha256": self.visible_text_sha256,
            "action_target_sha256": self.action_target_sha256,
            "action_sequence": self.action_sequence,
            "action_sha256": self.action_sha256,
            "benchmark_grant_sha256": self.benchmark_grant_sha256,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self.digest_payload(), "decision_sha256": self.decision_sha256}


SCORMCoherenceDecision = SCORMActionDecision


@dataclass(frozen=True)
class SCORMActionReceipt:
    """Short-lived HNC authorization for one exact action target."""

    run_id: str
    run_manifest_sha256: str
    run_authority_sha256: str
    allowed_origin: str
    launch_url_sha256: str
    launch_plan_sha256: str
    control_grant_sha256: str
    provider_context_sha256: str
    launch_authority_sha256: str
    provenance: str
    synthetic_persona_sha256: str | None
    preflight_sha256: str
    action_decision_sha256: str
    action_target_sha256: str
    benchmark_grant_sha256: str | None
    source_observation_sha256: str
    intent_source_observation_sha256: str
    source_screenshot_sha256: str
    visible_evidence_sha256: str
    visible_text_sha256: str
    window_binding_id: str
    window_generation: int
    window_identity_sha256: str
    action_sequence: int
    action_name: str
    action_sha256: str
    coordinates: SCORMActionCoordinates | None
    target_evidence_sha256: str
    interaction_kind: str
    credential_effect: str
    replay_nonce: str
    issued_at_unix: int
    expires_at_unix: int
    receipt_sha256: str
    hmac_sha256: str
    schema_version: str = ACTION_RECEIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ACTION_RECEIPT_SCHEMA_VERSION:
            raise SCORMCoherenceError("action receipt schema mismatch")
        _require_label("run_id", self.run_id)
        _canonical_public_origin(self.allowed_origin)
        _require_label("window_binding_id", self.window_binding_id)
        _require_int("window_generation", self.window_generation, minimum=0, maximum=2**63 - 1)
        _require_int("action_sequence", self.action_sequence, minimum=1, maximum=_MAX_ACTION_SEQUENCE)
        _require_label("action_name", self.action_name)
        _require_label("replay_nonce", self.replay_nonce, minimum_length=16)
        _require_enum("interaction_kind", self.interaction_kind, _INTERACTION_KINDS)
        _require_enum("credential_effect", self.credential_effect, _CREDENTIAL_EFFECTS)
        _require_enum("receipt provenance", self.provenance, _PROVENANCE_KINDS)
        if self.synthetic_persona_sha256 is not None:
            _require_sha256("synthetic_persona_sha256", self.synthetic_persona_sha256)
        for name in (
            "run_manifest_sha256",
            "run_authority_sha256",
            "launch_url_sha256",
            "launch_plan_sha256",
            "control_grant_sha256",
            "provider_context_sha256",
            "launch_authority_sha256",
            "preflight_sha256",
            "action_decision_sha256",
            "action_target_sha256",
            "source_observation_sha256",
            "intent_source_observation_sha256",
            "source_screenshot_sha256",
            "visible_evidence_sha256",
            "visible_text_sha256",
            "window_identity_sha256",
            "action_sha256",
            "target_evidence_sha256",
            "receipt_sha256",
            "hmac_sha256",
        ):
            _require_sha256(name, getattr(self, name))
        if self.benchmark_grant_sha256 is not None:
            _require_sha256("benchmark_grant_sha256", self.benchmark_grant_sha256)
        _validate_lifetime(
            self.issued_at_unix,
            self.expires_at_unix,
            name="action receipt",
            maximum=MAX_ACTION_LIFETIME_SECONDS,
        )
        if self.receipt_sha256 != _sha256_json(self.signed_payload()):
            raise SCORMCoherenceError("action receipt digest mismatch")

    @classmethod
    def issue(
        cls,
        *,
        secret: bytes | bytearray | memoryview,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        frame: SCORMFrameEvidence,
        preflight: SCORMPreflightDecision,
        decision: SCORMActionDecision,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        benchmark_grant_sha256: str | None,
        replay_nonce: str,
        issued_at_unix: int,
        expires_at_unix: int,
    ) -> SCORMActionReceipt:
        if intent.source_observation_sha256 != frame.source_observation_sha256:
            raise SCORMGrantContextError("intent source observation does not match current frame")
        if action_target.intent_source_observation_sha256 != intent.source_observation_sha256:
            raise SCORMGrantContextError("action target does not bind intent source observation")
        payload = {
            "schema_version": ACTION_RECEIPT_SCHEMA_VERSION,
            "run_id": run_authority.run_id,
            "run_manifest_sha256": run_authority.run_manifest_sha256,
            "run_authority_sha256": run_authority.run_authority_sha256,
            "allowed_origin": run_authority.allowed_origin,
            "launch_url_sha256": run_authority.launch_url_sha256,
            "launch_plan_sha256": run_authority.launch_plan_sha256,
            "control_grant_sha256": run_authority.control_grant_sha256,
            "provider_context_sha256": provider_context.provider_context_sha256,
            "launch_authority_sha256": provider_context.launch_authority_sha256,
            "provenance": provider_context.provenance,
            "synthetic_persona_sha256": provider_context.synthetic_persona_sha256,
            "preflight_sha256": preflight.preflight_sha256,
            "action_decision_sha256": decision.decision_sha256,
            "action_target_sha256": action_target.action_target_sha256,
            "benchmark_grant_sha256": benchmark_grant_sha256,
            "source_observation_sha256": frame.source_observation_sha256,
            "intent_source_observation_sha256": intent.source_observation_sha256,
            "source_screenshot_sha256": frame.source_screenshot_sha256,
            "visible_evidence_sha256": frame.visible_evidence_sha256,
            "visible_text_sha256": frame.visible_text_sha256,
            "window_binding_id": frame.window_binding_id,
            "window_generation": frame.window_generation,
            "window_identity_sha256": frame.window_identity_sha256,
            "action_sequence": intent.action_sequence,
            "action_name": intent.name,
            "action_sha256": intent.action_sha256,
            "coordinates": intent.coordinates.to_dict() if intent.coordinates is not None else None,
            "target_evidence_sha256": action_target.target_evidence_sha256,
            "interaction_kind": action_target.interaction_kind,
            "credential_effect": action_target.credential_effect,
            "replay_nonce": replay_nonce,
            "issued_at_unix": issued_at_unix,
            "expires_at_unix": expires_at_unix,
        }
        unsigned = cls(
            run_id=run_authority.run_id,
            run_manifest_sha256=run_authority.run_manifest_sha256,
            run_authority_sha256=run_authority.run_authority_sha256,
            allowed_origin=run_authority.allowed_origin,
            launch_url_sha256=run_authority.launch_url_sha256,
            launch_plan_sha256=run_authority.launch_plan_sha256,
            control_grant_sha256=run_authority.control_grant_sha256,
            provider_context_sha256=provider_context.provider_context_sha256,
            launch_authority_sha256=provider_context.launch_authority_sha256,
            provenance=provider_context.provenance,
            synthetic_persona_sha256=provider_context.synthetic_persona_sha256,
            preflight_sha256=preflight.preflight_sha256,
            action_decision_sha256=decision.decision_sha256,
            action_target_sha256=action_target.action_target_sha256,
            benchmark_grant_sha256=benchmark_grant_sha256,
            source_observation_sha256=frame.source_observation_sha256,
            intent_source_observation_sha256=intent.source_observation_sha256,
            source_screenshot_sha256=frame.source_screenshot_sha256,
            visible_evidence_sha256=frame.visible_evidence_sha256,
            visible_text_sha256=frame.visible_text_sha256,
            window_binding_id=frame.window_binding_id,
            window_generation=frame.window_generation,
            window_identity_sha256=frame.window_identity_sha256,
            action_sequence=intent.action_sequence,
            action_name=intent.name,
            action_sha256=intent.action_sha256,
            coordinates=intent.coordinates,
            target_evidence_sha256=action_target.target_evidence_sha256,
            interaction_kind=action_target.interaction_kind,
            credential_effect=action_target.credential_effect,
            replay_nonce=replay_nonce,
            issued_at_unix=issued_at_unix,
            expires_at_unix=expires_at_unix,
            receipt_sha256=_sha256_json(payload),
            hmac_sha256="0" * 64,
        )
        return replace(unsigned, hmac_sha256=_sign(secret, unsigned.authenticated_payload()))

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "run_manifest_sha256": self.run_manifest_sha256,
            "run_authority_sha256": self.run_authority_sha256,
            "allowed_origin": self.allowed_origin,
            "launch_url_sha256": self.launch_url_sha256,
            "launch_plan_sha256": self.launch_plan_sha256,
            "control_grant_sha256": self.control_grant_sha256,
            "provider_context_sha256": self.provider_context_sha256,
            "launch_authority_sha256": self.launch_authority_sha256,
            "provenance": self.provenance,
            "synthetic_persona_sha256": self.synthetic_persona_sha256,
            "preflight_sha256": self.preflight_sha256,
            "action_decision_sha256": self.action_decision_sha256,
            "action_target_sha256": self.action_target_sha256,
            "benchmark_grant_sha256": self.benchmark_grant_sha256,
            "source_observation_sha256": self.source_observation_sha256,
            "intent_source_observation_sha256": self.intent_source_observation_sha256,
            "source_screenshot_sha256": self.source_screenshot_sha256,
            "visible_evidence_sha256": self.visible_evidence_sha256,
            "visible_text_sha256": self.visible_text_sha256,
            "window_binding_id": self.window_binding_id,
            "window_generation": self.window_generation,
            "window_identity_sha256": self.window_identity_sha256,
            "action_sequence": self.action_sequence,
            "action_name": self.action_name,
            "action_sha256": self.action_sha256,
            "coordinates": self.coordinates.to_dict() if self.coordinates is not None else None,
            "target_evidence_sha256": self.target_evidence_sha256,
            "interaction_kind": self.interaction_kind,
            "credential_effect": self.credential_effect,
            "replay_nonce": self.replay_nonce,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
        }

    def authenticated_payload(self) -> dict[str, object]:
        return {**self.signed_payload(), "receipt_sha256": self.receipt_sha256}

    def to_dict(self) -> dict[str, object]:
        return {**self.authenticated_payload(), "hmac_sha256": self.hmac_sha256}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    def verify_signature(self, secret: bytes | bytearray | memoryview) -> SCORMActionReceipt:
        _verify(secret, self.authenticated_payload(), self.hmac_sha256, name="action receipt")
        return self

    def validate_time(self, *, now: datetime) -> SCORMActionReceipt:
        _validate_now(self.issued_at_unix, self.expires_at_unix, now, name="action receipt")
        return self


class SCORMActionReplayLedger:
    """Signed, append-only durable replay ledger."""

    _MARKER_KEYS = frozenset(
        {
            "action_sequence",
            "marker_hmac_sha256",
            "receipt_sha256",
            "replay_nonce_sha256",
            "run_authority_sha256",
            "schema_version",
        }
    )

    def __init__(
        self,
        directory: str | os.PathLike[str],
        *,
        marker_secret: bytes | bytearray | memoryview,
    ) -> None:
        requested = Path(directory)
        if requested.exists() and requested.is_symlink():
            raise SCORMReplayError("replay ledger directory must not be a symlink")
        requested.mkdir(parents=True, exist_ok=True)
        self._directory = requested.resolve(strict=True)
        if not self._directory.is_dir():
            raise SCORMReplayError("replay ledger path must be a directory")
        self._secret = bytearray(_require_secret(marker_secret, name="marker_secret"))
        self.verification_key_sha256 = hashlib.sha256(bytes(self._secret)).hexdigest()
        self._lock = threading.Lock()
        self._consumed: dict[str, dict[int, str]] = {}
        self._load()

    @staticmethod
    def _marker_name(run_authority_sha256: str, action_sequence: int) -> str:
        return f"{run_authority_sha256}-{action_sequence:07d}.json"

    def _marker_signature(self, payload: Mapping[str, object]) -> str:
        return _sign(bytes(self._secret), payload)

    @staticmethod
    def _unsigned_marker(receipt: SCORMActionReceipt) -> dict[str, object]:
        return {
            "schema_version": REPLAY_MARKER_SCHEMA_VERSION,
            "run_authority_sha256": receipt.run_authority_sha256,
            "action_sequence": receipt.action_sequence,
            "receipt_sha256": receipt.receipt_sha256,
            "replay_nonce_sha256": hashlib.sha256(
                receipt.replay_nonce.encode("utf-8")
            ).hexdigest(),
        }

    def _read_marker(self, path: Path) -> dict[str, object]:
        if path.is_symlink() or not path.is_file():
            raise SCORMReplayError("replay marker must be a regular file")
        raw = path.read_bytes()
        if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
            raise SCORMReplayError("replay marker encoding is not canonical")
        decoded = _decode_canonical_json(raw[:-1], name="replay marker")
        marker = _require_exact_keys("replay marker", decoded, self._MARKER_KEYS)
        if marker["schema_version"] != REPLAY_MARKER_SCHEMA_VERSION:
            raise SCORMReplayError("replay marker schema mismatch")
        signature = _require_sha256(
            "marker_hmac_sha256",
            marker["marker_hmac_sha256"],
        )
        unsigned = {
            key: marker[key] for key in marker if key != "marker_hmac_sha256"
        }
        try:
            _verify(bytes(self._secret), unsigned, signature, name="replay marker")
        except SCORMGrantSignatureError as exc:
            raise SCORMReplayError("replay marker signature is invalid") from exc
        return dict(marker)

    def _load(self) -> None:
        loaded: dict[str, dict[int, str]] = {}
        for path in sorted(self._directory.glob("*.json")):
            marker = self._read_marker(path)
            run_hash = _require_sha256("run_authority_sha256", marker["run_authority_sha256"])
            receipt_hash = _require_sha256("receipt_sha256", marker["receipt_sha256"])
            _require_sha256("replay_nonce_sha256", marker["replay_nonce_sha256"])
            sequence = _require_int(
                "action_sequence", marker["action_sequence"], minimum=1, maximum=_MAX_ACTION_SEQUENCE
            )
            if path.name != self._marker_name(run_hash, sequence):
                raise SCORMReplayError("replay marker filename does not match contents")
            per_run = loaded.setdefault(run_hash, {})
            if sequence in per_run:
                raise SCORMReplayError("duplicate durable action sequence")
            per_run[sequence] = receipt_hash
        for values in loaded.values():
            if sorted(values) != list(range(1, len(values) + 1)):
                raise SCORMReplayError("durable action sequence contains a gap")
        self._consumed = loaded

    def next_sequence(self, run_authority_sha256: str) -> int:
        _require_sha256("run_authority_sha256", run_authority_sha256)
        with self._lock:
            return len(self._consumed.get(run_authority_sha256, {})) + 1

    def verify_consumed(self, receipt: SCORMActionReceipt) -> bool:
        """Read-only proof that one exact HNC receipt is durably consumed.

        The receipt HMAC, current in-memory sequence map, canonical marker
        bytes, marker HMAC, filename, nonce digest, and receipt digest must all
        agree.  No replay state is created or changed by this check.
        """

        if not isinstance(receipt, SCORMActionReceipt):
            raise TypeError("receipt must be SCORMActionReceipt")
        try:
            receipt.verify_signature(bytes(self._secret))
        except SCORMCoherenceError:
            return False
        expected_unsigned = self._unsigned_marker(receipt)
        expected_marker = {
            **expected_unsigned,
            "marker_hmac_sha256": self._marker_signature(expected_unsigned),
        }
        path = self._directory / self._marker_name(
            receipt.run_authority_sha256,
            receipt.action_sequence,
        )
        with self._lock:
            per_run = self._consumed.get(receipt.run_authority_sha256)
            if (
                per_run is None
                or per_run.get(receipt.action_sequence) != receipt.receipt_sha256
            ):
                return False
            try:
                marker = self._read_marker(path)
            except (OSError, SCORMCoherenceError):
                return False
            return marker == expected_marker

    def consume(self, receipt: SCORMActionReceipt, *, now: datetime) -> SCORMActionReceipt:
        """Consume only an HNC-signed, currently valid action receipt."""

        if not isinstance(receipt, SCORMActionReceipt):
            raise TypeError("receipt must be SCORMActionReceipt")
        receipt.verify_signature(bytes(self._secret)).validate_time(now=now)
        unsigned = self._unsigned_marker(receipt)
        marker = {**unsigned, "marker_hmac_sha256": self._marker_signature(unsigned)}
        encoded = (_canonical_json(marker) + "\n").encode("utf-8")
        with self._lock:
            per_run = self._consumed.setdefault(receipt.run_authority_sha256, {})
            expected = len(per_run) + 1
            if receipt.action_sequence != expected:
                raise SCORMReplayError(f"action sequence must be next durable sequence ({expected})")
            path = self._directory / self._marker_name(receipt.run_authority_sha256, receipt.action_sequence)
            try:
                descriptor = os.open(
                    path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                    0o600,
                )
            except FileExistsError as exc:
                raise SCORMReplayError("action receipt was already consumed") from exc
            try:
                written = 0
                while written < len(encoded):
                    count = os.write(descriptor, encoded[written:])
                    if count <= 0:
                        raise SCORMReplayError("could not persist complete replay marker")
                    written += count
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            per_run[receipt.action_sequence] = receipt.receipt_sha256
        return receipt


class HNCScormCoherenceGate:
    """Validate independent launch provenance before any action policy."""

    def __init__(
        self,
        secret: bytes | bytearray | memoryview,
        *,
        provider_attestation_public_keys: Mapping[
            str, bytes | bytearray | memoryview
        ] | None = None,
        owner_benchmark_keys: Mapping[str, bytes | bytearray | memoryview] | None = None,
        replay_ledger: SCORMActionReplayLedger | None = None,
    ) -> None:
        hnc_secret = _require_secret(secret)
        provider_keys_input = provider_attestation_public_keys or {}
        owner_keys_input = owner_benchmark_keys or {}
        if not isinstance(provider_keys_input, Mapping):
            raise TypeError("provider_attestation_public_keys must be a mapping")
        if not isinstance(owner_keys_input, Mapping):
            raise TypeError("owner_benchmark_keys must be a mapping")
        if not provider_keys_input and not owner_keys_input:
            raise ValueError("at least one independent launch authority key is required")
        provider_keys: dict[str, bytearray] = {}
        for key_id, key_material in provider_keys_input.items():
            _require_label("provider key_id", key_id)
            if not isinstance(key_material, (bytes, bytearray, memoryview)):
                raise TypeError("provider Ed25519 public key must be bytes-like")
            public_key = bytes(key_material)
            if len(public_key) != 32:
                raise ValueError("provider Ed25519 public key must be exactly 32 bytes")
            provider_keys[key_id] = bytearray(public_key)
        owner_keys: dict[str, bytearray] = {}
        for key_id, key_material in owner_keys_input.items():
            _require_label("owner key_id", key_id)
            owner_secret = _require_secret(key_material, name="owner benchmark key")
            if hmac.compare_digest(owner_secret, hnc_secret):
                raise ValueError("owner benchmark key must be distinct from HNC secret")
            owner_keys[key_id] = bytearray(owner_secret)
        if replay_ledger is not None and (
            replay_ledger.verification_key_sha256 != hashlib.sha256(hnc_secret).hexdigest()
        ):
            raise ValueError("replay ledger marker key does not match HNC receipt key")
        self._secret = bytearray(hnc_secret)
        self._provider_public_keys = provider_keys
        self._owner_keys = owner_keys
        self._replay_ledger = replay_ledger
        self._lock = threading.Lock()
        self._closed = False

    def __enter__(self) -> HNCScormCoherenceGate:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.close()

    def close(self) -> None:
        with self._lock:
            for index in range(len(self._secret)):
                self._secret[index] = 0
            for material in self._provider_public_keys.values():
                for index in range(len(material)):
                    material[index] = 0
            self._provider_public_keys.clear()
            for material in self._owner_keys.values():
                for index in range(len(material)):
                    material[index] = 0
            self._owner_keys.clear()
            self._closed = True

    def _secret_bytes(self) -> bytes:
        with self._lock:
            if self._closed:
                raise SCORMCoherenceError("coherence gate is closed")
            return bytes(self._secret)

    def _provider_public_key(self, key_id: str) -> bytes:
        with self._lock:
            if self._closed:
                raise SCORMCoherenceError("coherence gate is closed")
            material = self._provider_public_keys.get(key_id)
            if material is None:
                raise SCORMGrantSignatureError("provider Ed25519 key_id is not trusted")
            return bytes(material)

    def _owner_secret(self, key_id: str) -> bytes:
        with self._lock:
            if self._closed:
                raise SCORMCoherenceError("coherence gate is closed")
            material = self._owner_keys.get(key_id)
            if material is None:
                raise SCORMGrantSignatureError("owner benchmark key_id is not trusted")
            return bytes(material)

    def next_action_sequence(self, run_authority: SCORMRunAuthority) -> int:
        self._secret_bytes()
        if not isinstance(run_authority, SCORMRunAuthority):
            raise TypeError("run_authority must be SCORMRunAuthority")
        if self._replay_ledger is None:
            raise SCORMReplayError("durable replay ledger is required for sequencing")
        return self._replay_ledger.next_sequence(run_authority.run_authority_sha256)

    def _validate_base(
        self,
        frame: SCORMFrameEvidence,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        *,
        now: datetime,
    ) -> None:
        secret = self._secret_bytes()
        run_authority.verify_signature(secret).validate_time(now=now)
        provider_context.verify_signature(secret).validate_time(now=now)
        launch_authority = provider_context.launch_authority
        if isinstance(launch_authority, SCORMProviderAttestationReceipt):
            launch_authority.verify_signature(
                self._provider_public_key(launch_authority.key_id)
            ).validate_time(now=now)
            expected_provenance = PROVIDER_VERIFIED
            expected_live_url_sha256 = launch_authority.live_url_sha256
            expected_registration = (
                launch_authority.registration_state,
                launch_authority.registration_evidence_kind,
                launch_authority.registration_evidence_sha256,
            )
            expected_owner_scope: tuple[str | None, str | None, str | None] = (
                None,
                None,
                None,
            )
        else:
            launch_authority.verify_signature(
                self._owner_secret(launch_authority.key_id)
            ).validate_time(now=now)
            expected_provenance = OWNER_BENCHMARK_ASSERTED
            expected_live_url_sha256 = launch_authority.native_live_url_sha256
            expected_registration = (
                SYNTHETIC_BENCHMARK,
                SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT,
                launch_authority.owner_launch_authority_sha256,
            )
            expected_owner_scope = (
                launch_authority.scope,
                launch_authority.synthetic_persona_id,
                launch_authority.synthetic_persona_sha256,
            )
            if (
                provider_context.active_session_id,
                provider_context.window_binding_id,
                provider_context.window_generation,
                provider_context.window_identity_sha256,
            ) != (
                launch_authority.active_session_id,
                launch_authority.window_binding_id,
                launch_authority.window_generation,
                launch_authority.window_identity_sha256,
            ):
                raise SCORMGrantContextError(
                    "owner authority does not match current session/window"
                )
        authority_binding = (
            run_authority.run_id,
            run_authority.run_manifest_sha256,
            run_authority.run_authority_sha256,
            run_authority.allowed_origin,
            run_authority.launch_url_sha256,
            run_authority.launch_plan_sha256,
            run_authority.control_grant_sha256,
        )
        launch_binding = (
            launch_authority.run_id,
            launch_authority.run_manifest_sha256,
            launch_authority.run_authority_sha256,
            launch_authority.allowed_origin,
            launch_authority.launch_url_sha256,
            launch_authority.launch_plan_sha256,
            launch_authority.control_grant_sha256,
        )
        context_binding = (
            provider_context.run_id,
            provider_context.run_manifest_sha256,
            provider_context.run_authority_sha256,
            provider_context.allowed_origin,
            provider_context.launch_url_sha256,
            provider_context.launch_plan_sha256,
            provider_context.control_grant_sha256,
        )
        if authority_binding != launch_binding or authority_binding != context_binding:
            raise SCORMGrantContextError("run, launch, origin, or control authority drift")
        if (
            provider_context.launch_authority_sha256
            != launch_authority.launch_authority_sha256
            or provider_context.provenance != expected_provenance
        ):
            raise SCORMGrantContextError("launch provenance or authority hash drift")
        if provider_context.live_origin != run_authority.allowed_origin:
            raise SCORMGrantContextError("live origin must equal exact allowed origin")
        if (
            provider_context.live_url_sha256 != expected_live_url_sha256
            or provider_context.live_url_sha256 != run_authority.launch_url_sha256
        ):
            raise SCORMGrantContextError("native live URL is not the exact signed launch URL")
        if (
            provider_context.native_address_bar_receipt_sha256
            != launch_authority.native_address_bar_receipt_sha256
        ):
            raise SCORMGrantContextError("native address-bar receipt drift")
        registration_binding = (
            provider_context.registration_state,
            provider_context.registration_evidence_kind,
            provider_context.registration_evidence_sha256,
        )
        if registration_binding != expected_registration:
            raise SCORMGrantContextError("registration facts are not launch-authority attested")
        if (
            provider_context.owner_scope_kind,
            provider_context.synthetic_persona_id,
            provider_context.synthetic_persona_sha256,
        ) != expected_owner_scope:
            raise SCORMGrantContextError("owner scope or synthetic persona drift")
        if not (
            run_authority.issued_at_unix
            <= launch_authority.issued_at_unix
            <= provider_context.issued_at_unix
            < provider_context.expires_at_unix
            <= launch_authority.expires_at_unix
            <= run_authority.expires_at_unix
        ):
            raise SCORMGrantContextError("launch/context validity exceeds stable authority")
        frame_binding = (
            frame.run_id,
            frame.run_manifest_sha256,
            frame.run_authority_sha256,
            frame.allowed_origin,
            frame.launch_url_sha256,
            frame.launch_plan_sha256,
            frame.control_grant_sha256,
            frame.provider_context_sha256,
            frame.launch_authority_sha256,
            frame.source_observation_sha256,
            frame.source_screenshot_sha256,
            frame.visible_evidence_sha256,
            frame.visible_text_sha256,
            frame.active_session_id,
            frame.live_origin,
            frame.live_url_sha256,
            frame.native_address_bar_receipt_sha256,
            frame.window_binding_id,
            frame.window_generation,
            frame.window_identity_sha256,
            frame.registration_state,
            frame.registration_evidence_kind,
            frame.registration_evidence_sha256,
            frame.provenance,
            frame.owner_scope_kind,
            frame.synthetic_persona_sha256,
        )
        expected_frame = (
            provider_context.run_id,
            provider_context.run_manifest_sha256,
            provider_context.run_authority_sha256,
            provider_context.allowed_origin,
            provider_context.launch_url_sha256,
            provider_context.launch_plan_sha256,
            provider_context.control_grant_sha256,
            provider_context.provider_context_sha256,
            provider_context.launch_authority_sha256,
            provider_context.source_observation_sha256,
            provider_context.source_screenshot_sha256,
            provider_context.visible_evidence_sha256,
            provider_context.visible_text_sha256,
            provider_context.active_session_id,
            provider_context.live_origin,
            provider_context.live_url_sha256,
            provider_context.native_address_bar_receipt_sha256,
            provider_context.window_binding_id,
            provider_context.window_generation,
            provider_context.window_identity_sha256,
            provider_context.registration_state,
            provider_context.registration_evidence_kind,
            provider_context.registration_evidence_sha256,
            provider_context.provenance,
            provider_context.owner_scope_kind,
            provider_context.synthetic_persona_sha256,
        )
        if frame_binding != expected_frame:
            raise SCORMGrantContextError("frame does not match exact provider context")
        if canonical_visible_text_sha256(frame.visible_text) != frame.visible_text_sha256:
            raise SCORMGrantContextError("visible text hash does not match exact frame text")

    def classify_preflight(
        self,
        frame: SCORMFrameEvidence,
        *,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        now: datetime,
    ) -> SCORMPreflightDecision:
        """Validate the exact frame and pause only for visible prerequisites."""

        if not isinstance(frame, SCORMFrameEvidence):
            raise TypeError("frame must be SCORMFrameEvidence")
        self._validate_base(frame, run_authority, provider_context, now=now)
        prerequisite = classify_visible_prerequisite(frame.visible_text)
        if prerequisite is not None:
            return SCORMPreflightDecision.build(
                kind=RESUMABLE_PAUSE,
                reason=f"{prerequisite}_prerequisite_visible",
                prerequisite=prerequisite,
                frame=frame,
            )
        return SCORMPreflightDecision.build(
            kind=READY_FOR_INTENT,
            reason="exact_frame_ready_for_intent",
            prerequisite=None,
            frame=frame,
        )

    def classify(
        self,
        frame: SCORMFrameEvidence,
        *,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        now: datetime,
    ) -> SCORMPreflightDecision:
        """Compatibility alias for the non-authorizing preflight stage."""

        return self.classify_preflight(
            frame,
            run_authority=run_authority,
            provider_context=provider_context,
            now=now,
        )

    def _validate_action_target(
        self,
        frame: SCORMFrameEvidence,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        provider_context: SCORMProviderContextEvidence,
        *,
        now: datetime,
    ) -> None:
        if intent.source_observation_sha256 != frame.source_observation_sha256:
            raise SCORMGrantContextError("intent source observation does not match current frame")
        launch_authority = provider_context.launch_authority
        if not isinstance(launch_authority, SCORMOwnerBenchmarkLaunchAuthority):
            raise SCORMGrantContextError(
                "action authorization requires exact owner benchmark target evidence"
            )
        if (
            action_target.key_id != launch_authority.key_id
            or action_target.issuer != launch_authority.issuer
        ):
            raise SCORMGrantContextError("action target issuer/key does not match owner authority")
        action_target.verify_signature(
            self._owner_secret(action_target.key_id)
        ).validate_time(now=now)
        actual = (
            action_target.run_id,
            action_target.run_manifest_sha256,
            action_target.run_authority_sha256,
            action_target.allowed_origin,
            action_target.launch_url_sha256,
            action_target.launch_plan_sha256,
            action_target.control_grant_sha256,
            action_target.provider_context_sha256,
            action_target.launch_authority_sha256,
            action_target.provenance,
            action_target.owner_scope_kind,
            action_target.synthetic_persona_sha256,
            action_target.source_observation_sha256,
            action_target.intent_source_observation_sha256,
            action_target.source_screenshot_sha256,
            action_target.visible_evidence_sha256,
            action_target.visible_text_sha256,
            action_target.active_session_id,
            action_target.live_origin,
            action_target.live_url_sha256,
            action_target.native_address_bar_receipt_sha256,
            action_target.window_binding_id,
            action_target.window_generation,
            action_target.window_identity_sha256,
            action_target.action_sequence,
            action_target.action_name,
            action_target.action_sha256,
            action_target.coordinates,
            action_target.registration_state,
            action_target.registration_evidence_kind,
            action_target.registration_evidence_sha256,
        )
        expected = (
            frame.run_id,
            frame.run_manifest_sha256,
            frame.run_authority_sha256,
            frame.allowed_origin,
            frame.launch_url_sha256,
            frame.launch_plan_sha256,
            frame.control_grant_sha256,
            provider_context.provider_context_sha256,
            frame.launch_authority_sha256,
            frame.provenance,
            frame.owner_scope_kind,
            frame.synthetic_persona_sha256,
            frame.source_observation_sha256,
            intent.source_observation_sha256,
            frame.source_screenshot_sha256,
            frame.visible_evidence_sha256,
            frame.visible_text_sha256,
            frame.active_session_id,
            frame.live_origin,
            frame.live_url_sha256,
            frame.native_address_bar_receipt_sha256,
            frame.window_binding_id,
            frame.window_generation,
            frame.window_identity_sha256,
            intent.action_sequence,
            intent.name,
            intent.action_sha256,
            intent.coordinates,
            frame.registration_state,
            frame.registration_evidence_kind,
            frame.registration_evidence_sha256,
        )
        if actual != expected:
            raise SCORMGrantContextError("action target does not match exact frame and intent")
        if not (
            provider_context.issued_at_unix
            <= action_target.issued_at_unix
            < action_target.expires_at_unix
            <= provider_context.expires_at_unix
        ):
            raise SCORMGrantContextError("action target validity exceeds provider context")

    @staticmethod
    def _grant_binding(
        grant: SCORMBenchmarkGrant,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        frame: SCORMFrameEvidence,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
    ) -> bool:
        return (
            grant.run_id,
            grant.run_manifest_sha256,
            grant.run_authority_sha256,
            grant.allowed_origin,
            grant.launch_url_sha256,
            grant.launch_plan_sha256,
            grant.control_grant_sha256,
            grant.provider_context_sha256,
            grant.launch_authority_sha256,
            grant.provenance,
            grant.owner_scope_kind,
            grant.synthetic_persona_sha256,
            grant.source_observation_sha256,
            grant.intent_source_observation_sha256,
            grant.source_screenshot_sha256,
            grant.visible_evidence_sha256,
            grant.visible_text_sha256,
            grant.window_binding_id,
            grant.window_generation,
            grant.window_identity_sha256,
            grant.action_target_sha256,
            grant.action_sequence,
            grant.action_name,
            grant.action_sha256,
            grant.coordinates,
            grant.target_evidence_sha256,
            grant.registration_state,
            grant.interaction_kind,
            grant.credential_effect,
        ) == (
            run_authority.run_id,
            run_authority.run_manifest_sha256,
            run_authority.run_authority_sha256,
            run_authority.allowed_origin,
            run_authority.launch_url_sha256,
            run_authority.launch_plan_sha256,
            run_authority.control_grant_sha256,
            provider_context.provider_context_sha256,
            provider_context.launch_authority_sha256,
            provider_context.provenance,
            provider_context.owner_scope_kind,
            provider_context.synthetic_persona_sha256,
            frame.source_observation_sha256,
            intent.source_observation_sha256,
            frame.source_screenshot_sha256,
            frame.visible_evidence_sha256,
            frame.visible_text_sha256,
            frame.window_binding_id,
            frame.window_generation,
            frame.window_identity_sha256,
            action_target.action_target_sha256,
            intent.action_sequence,
            intent.name,
            intent.action_sha256,
            intent.coordinates,
            action_target.target_evidence_sha256,
            action_target.registration_state,
            action_target.interaction_kind,
            action_target.credential_effect,
        )

    def _validated_grant(
        self,
        grant: SCORMBenchmarkGrant,
        *,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        frame: SCORMFrameEvidence,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        now: datetime,
    ) -> str:
        launch_authority = provider_context.launch_authority
        if not isinstance(launch_authority, SCORMOwnerBenchmarkLaunchAuthority):
            raise SCORMGrantContextError("benchmark grant requires owner launch authority")
        grant.verify_signature(self._owner_secret(launch_authority.key_id)).validate_time(now=now)
        if not self._grant_binding(grant, run_authority, provider_context, frame, intent, action_target):
            raise SCORMGrantContextError("benchmark grant does not match exact action target")
        if not (
            action_target.issued_at_unix
            <= grant.issued_at_unix
            < grant.expires_at_unix
            <= action_target.expires_at_unix
        ):
            raise SCORMGrantContextError("benchmark grant validity exceeds action target")
        return grant.benchmark_grant_sha256

    def classify_action(
        self,
        frame: SCORMFrameEvidence,
        preflight: SCORMPreflightDecision,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        *,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        grant: SCORMBenchmarkGrant | None = None,
        now: datetime,
    ) -> SCORMActionDecision:
        """Classify only after exact owner-attested native action targeting."""

        expected_preflight = self.classify_preflight(
            frame,
            run_authority=run_authority,
            provider_context=provider_context,
            now=now,
        )
        if preflight != expected_preflight or preflight.kind != READY_FOR_INTENT:
            raise SCORMGrantContextError("action requires exact ready_for_intent preflight")
        if not isinstance(intent, SCORMActionIntent):
            raise TypeError("intent must be SCORMActionIntent")
        if intent.source_observation_sha256 != frame.source_observation_sha256:
            raise SCORMGrantContextError("intent source observation does not match current frame")
        if intent.name not in run_authority.allowed_actions:
            raise SCORMGrantContextError("action is outside stable authority scope")
        if intent.action_sequence > run_authority.max_actions:
            raise SCORMGrantContextError("action exceeds stable run action limit")
        self._validate_action_target(frame, intent, action_target, provider_context, now=now)
        if action_target.credential_effect == REAL_IDENTITY_BOUND:
            return SCORMActionDecision.build(
                kind=OWNER_ATTESTATION_REQUIRED,
                reason="real_identity_bound_credential_mutation",
                prerequisite=None,
                preflight=preflight,
                frame=frame,
                intent=intent,
                action_target=action_target,
            )
        if (
            action_target.interaction_kind == NAVIGATION
            and action_target.credential_effect == NO_CREDENTIAL_EFFECT
        ):
            return SCORMActionDecision.build(
                kind=CONTINUE,
                reason="owner_benchmark_navigation_coherent",
                prerequisite=None,
                preflight=preflight,
                frame=frame,
                intent=intent,
                action_target=action_target,
            )
        preview_assessment = (
            action_target.provenance == OWNER_BENCHMARK_ASSERTED
            and action_target.owner_scope_kind == SYNTHETIC_PERSONA_BENCHMARK
            and action_target.registration_state == SYNTHETIC_BENCHMARK
            and action_target.interaction_kind == ASSESSMENT_RESPONSE
            and action_target.credential_effect == PREVIEW_ONLY
        )
        if preview_assessment:
            if grant is None:
                return SCORMActionDecision.build(
                    kind=RESUMABLE_PAUSE,
                    reason="per_action_benchmark_grant_required",
                    prerequisite="benchmark_grant",
                    preflight=preflight,
                    frame=frame,
                    intent=intent,
                    action_target=action_target,
                )
            try:
                grant_sha256 = self._validated_grant(
                    grant,
                    run_authority=run_authority,
                    provider_context=provider_context,
                    frame=frame,
                    intent=intent,
                    action_target=action_target,
                    now=now,
                )
            except SCORMCoherenceError:
                return SCORMActionDecision.build(
                    kind=RESUMABLE_PAUSE,
                    reason="per_action_benchmark_grant_invalid",
                    prerequisite="benchmark_grant",
                    preflight=preflight,
                    frame=frame,
                    intent=intent,
                    action_target=action_target,
                )
            return SCORMActionDecision.build(
                kind=CONTINUE,
                reason="owner_granted_synthetic_assessment_action_coherent",
                prerequisite=None,
                preflight=preflight,
                frame=frame,
                intent=intent,
                action_target=action_target,
                benchmark_grant_sha256=grant_sha256,
            )
        return SCORMActionDecision.build(
            kind=RESUMABLE_PAUSE,
            reason="credential_effect_requires_resolution",
            prerequisite="effect_resolution",
            preflight=preflight,
            frame=frame,
            intent=intent,
            action_target=action_target,
        )

    def authorize_action(
        self,
        frame: SCORMFrameEvidence,
        preflight: SCORMPreflightDecision,
        decision: SCORMActionDecision,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        *,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        grant: SCORMBenchmarkGrant | None = None,
        now: datetime,
    ) -> SCORMActionReceipt:
        if self._replay_ledger is None:
            raise SCORMReplayError("durable replay ledger is required for authorization")
        expected = self.classify_action(
            frame,
            preflight,
            intent,
            action_target,
            run_authority=run_authority,
            provider_context=provider_context,
            grant=grant,
            now=now,
        )
        if decision != expected or decision.kind != CONTINUE:
            raise SCORMGrantContextError("authorization requires exact current continue decision")
        sequence = self._replay_ledger.next_sequence(run_authority.run_authority_sha256)
        if intent.action_sequence != sequence:
            raise SCORMReplayError(f"action intent must use next durable sequence ({sequence})")
        now_unix = _unix_time("now", now)
        expiries = [
            now_unix + MAX_ACTION_LIFETIME_SECONDS,
            run_authority.expires_at_unix,
            provider_context.expires_at_unix,
            action_target.expires_at_unix,
        ]
        if grant is not None:
            expiries.append(grant.expires_at_unix)
        expires_at = min(expiries)
        if expires_at <= now_unix:
            raise SCORMGrantContextError("no positive receipt validity remains")
        replay_nonce = _sha256_json(
            {
                "run_replay_nonce": run_authority.replay_nonce,
                "action_target_sha256": action_target.action_target_sha256,
                "action_sequence": intent.action_sequence,
            }
        )
        return SCORMActionReceipt.issue(
            secret=self._secret_bytes(),
            run_authority=run_authority,
            provider_context=provider_context,
            frame=frame,
            preflight=preflight,
            decision=decision,
            intent=intent,
            action_target=action_target,
            benchmark_grant_sha256=decision.benchmark_grant_sha256,
            replay_nonce=replay_nonce,
            issued_at_unix=now_unix,
            expires_at_unix=expires_at,
        )

    def verify_and_consume_action(
        self,
        receipt: SCORMActionReceipt,
        frame: SCORMFrameEvidence,
        preflight: SCORMPreflightDecision,
        intent: SCORMActionIntent,
        action_target: SCORMActionTargetEvidence,
        *,
        run_authority: SCORMRunAuthority,
        provider_context: SCORMProviderContextEvidence,
        grant: SCORMBenchmarkGrant | None = None,
        now: datetime,
    ) -> SCORMActionReceipt:
        if self._replay_ledger is None:
            raise SCORMReplayError("durable replay ledger is required for dispatch")
        if intent.source_observation_sha256 != frame.source_observation_sha256:
            raise SCORMGrantContextError("intent source observation does not match current frame")
        receipt.verify_signature(self._secret_bytes()).validate_time(now=now)
        decision = self.classify_action(
            frame,
            preflight,
            intent,
            action_target,
            run_authority=run_authority,
            provider_context=provider_context,
            grant=grant,
            now=now,
        )
        if decision.kind != CONTINUE:
            raise SCORMGrantContextError("receipt no longer has a continue decision")
        actual = (
            receipt.run_id,
            receipt.run_manifest_sha256,
            receipt.run_authority_sha256,
            receipt.allowed_origin,
            receipt.launch_url_sha256,
            receipt.launch_plan_sha256,
            receipt.control_grant_sha256,
            receipt.provider_context_sha256,
            receipt.launch_authority_sha256,
            receipt.provenance,
            receipt.synthetic_persona_sha256,
            receipt.preflight_sha256,
            receipt.action_decision_sha256,
            receipt.action_target_sha256,
            receipt.benchmark_grant_sha256,
            receipt.source_observation_sha256,
            receipt.intent_source_observation_sha256,
            receipt.source_screenshot_sha256,
            receipt.visible_evidence_sha256,
            receipt.visible_text_sha256,
            receipt.window_binding_id,
            receipt.window_generation,
            receipt.window_identity_sha256,
            receipt.action_sequence,
            receipt.action_name,
            receipt.action_sha256,
            receipt.coordinates,
            receipt.target_evidence_sha256,
            receipt.interaction_kind,
            receipt.credential_effect,
        )
        expected = (
            run_authority.run_id,
            run_authority.run_manifest_sha256,
            run_authority.run_authority_sha256,
            run_authority.allowed_origin,
            run_authority.launch_url_sha256,
            run_authority.launch_plan_sha256,
            run_authority.control_grant_sha256,
            provider_context.provider_context_sha256,
            provider_context.launch_authority_sha256,
            provider_context.provenance,
            provider_context.synthetic_persona_sha256,
            preflight.preflight_sha256,
            decision.decision_sha256,
            action_target.action_target_sha256,
            decision.benchmark_grant_sha256,
            frame.source_observation_sha256,
            intent.source_observation_sha256,
            frame.source_screenshot_sha256,
            frame.visible_evidence_sha256,
            frame.visible_text_sha256,
            frame.window_binding_id,
            frame.window_generation,
            frame.window_identity_sha256,
            intent.action_sequence,
            intent.name,
            intent.action_sha256,
            intent.coordinates,
            action_target.target_evidence_sha256,
            action_target.interaction_kind,
            action_target.credential_effect,
        )
        if actual != expected:
            raise SCORMGrantContextError("receipt does not match exact current action context")
        return self._replay_ledger.consume(receipt, now=now)


__all__ = [
    "ACTION_DECISION_SCHEMA_VERSION",
    "ACTION_RECEIPT_SCHEMA_VERSION",
    "ACTION_TARGET_SCHEMA_VERSION",
    "ASSESSMENT_CONTROL",
    "ASSESSMENT_RESPONSE",
    "BENCHMARK_GRANT_SCHEMA_VERSION",
    "BENCHMARK_MODE",
    "BOUND_WINDOW_SURFACE",
    "CONTINUE",
    "COORDINATE_CONTROL",
    "CREDENTIAL_COMMIT_CONTROL",
    "CREDENTIAL_MUTATION",
    "FOCUSED_CONTROL",
    "FRAME_WAIT",
    "HNCScormCoherenceGate",
    "MAX_ACTION_LIFETIME_SECONDS",
    "MAX_GRANT_LIFETIME_SECONDS",
    "NATIVE_ACCESSIBILITY_CONTROL",
    "NATIVE_BROWSER_UI",
    "NATIVE_FOCUSED_CONTROL",
    "NAVIGATION",
    "NAVIGATION_CONTROL",
    "NO_CREDENTIAL_EFFECT",
    "OWNER_ATTESTATION_REQUIRED",
    "OWNER_BENCHMARK_ASSERTED",
    "OWNER_BENCHMARK_LAUNCH_SCHEMA_VERSION",
    "PREFLIGHT_DECISION_SCHEMA_VERSION",
    "PREVIEW_ONLY",
    "PROVIDER_ATTESTATION_SCHEMA_VERSION",
    "PROVIDER_CONTEXT_SCHEMA_VERSION",
    "PROVIDER_NATIVE_SIGNED_METADATA",
    "PROVIDER_VERIFIED",
    "PUBLIC_PREVIEW",
    "READY_FOR_INTENT",
    "REAL_IDENTITY_BOUND",
    "REGISTERED",
    "REPLAY_MARKER_SCHEMA_VERSION",
    "RESUMABLE_PAUSE",
    "RUN_AUTHORITY_SCHEMA_VERSION",
    "RUN_MODE",
    "SCORMActionCoordinates",
    "SCORMActionDecision",
    "SCORMActionIntent",
    "SCORMActionReceipt",
    "SCORMActionReplayLedger",
    "SCORMActionTargetEvidence",
    "SCORMBenchmarkGrant",
    "SCORMCoherenceDecision",
    "SCORMCoherenceError",
    "SCORMFrameEvidence",
    "SCORMGrantContextError",
    "SCORMGrantFormatError",
    "SCORMGrantSignatureError",
    "SCORMOwnerBenchmarkLaunchAuthority",
    "SCORMPreflightDecision",
    "SCORMProviderAttestationReceipt",
    "SCORMProviderContextEvidence",
    "SCORMReplayError",
    "SCORMRunAuthority",
    "SCORMTargetBounds",
    "SIGNED_BENCHMARK_CONTROL_GRANT",
    "SIGNED_BENCHMARK_CONTROL_RECEIPT",
    "SIGNED_OWNER_BENCHMARK_LAUNCH_RECEIPT",
    "SIGNED_PROVIDER_SESSION_METADATA",
    "UNREGISTERED",
    "SYNTHETIC_BENCHMARK",
    "SYNTHETIC_PERSONA_BENCHMARK",
    "VISIBLE_EVIDENCE_SCHEMA_VERSION",
    "WINDOW_NAVIGATION",
    "canonical_action_sha256",
    "canonical_synthetic_persona_sha256",
    "canonical_visible_evidence_sha256",
    "canonical_visible_text_sha256",
    "classify_visible_prerequisite",
]
