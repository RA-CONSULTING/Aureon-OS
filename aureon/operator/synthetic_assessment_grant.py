"""Sealed, local-only authorization for synthetic assessment benchmark actions.

The HMAC key is supplied only to issuance or activation calls.  It is never
stored on a grant, an active session, or a replay marker.  A grant may be
activated exactly once; the resulting in-process session can authorize a
bounded sequence of actions while revalidating the complete local context
before every action.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
import threading
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

SCHEMA_VERSION = "aureon-synthetic-assessment-grant-v1"
ASSET_MANIFEST_SCHEMA_VERSION = "aureon-synthetic-suite-assets-v1"
REPLAY_SCHEMA_VERSION = "aureon-synthetic-assessment-replay-v1"
ACTION_RECEIPT_SCHEMA_VERSION = "aureon-synthetic-assessment-action-v1"

SYNTHETIC_PERSONA_ID = "john-brown-synthetic-v1"
SYNTHETIC_MODE = "sealed_synthetic_only"
LOOPBACK_HOST = "127.0.0.1"
MAX_GRANT_LIFETIME_SECONDS = 24 * 60 * 60
MAX_ACTIONS_PER_GRANT = 10_000
DEFAULT_MAX_ACTIONS = 4_096
SUPPORTED_ASSESSMENT_ACTIONS = frozenset(
    {"left_click", "move_mouse", "press_key", "scroll", "type_text"}
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_MAX_JSON_BYTES = 8 * 1024 * 1024
_SESSION_FACTORY_TOKEN = object()


class SyntheticAssessmentGrantError(ValueError):
    """Base class for fail-closed grant errors."""


class GrantFormatError(SyntheticAssessmentGrantError):
    """Raised when a grant or its asset manifest is not canonical and exact."""


class GrantSignatureError(SyntheticAssessmentGrantError):
    """Raised when the runtime HMAC key does not authenticate the grant."""


class GrantContextError(SyntheticAssessmentGrantError):
    """Raised when live action context differs from the sealed context."""


class GrantReplayError(SyntheticAssessmentGrantError):
    """Raised when a run/nonce grant has already been activated."""


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
        raise GrantFormatError("value is not canonical-JSON serializable") from exc


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _require_sha256(name: str, value: object) -> str:
    if not _valid_sha256(value):
        raise GrantFormatError(f"{name} must be lowercase SHA-256 hex")
    return str(value)


def _require_int(name: str, value: object, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GrantFormatError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise GrantFormatError(f"{name} is out of range")
    return value


def _require_label(name: str, value: object, *, minimum_length: int = 1) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not minimum_length <= len(value) <= 256
        or not _LABEL_RE.fullmatch(value)
    ):
        raise GrantFormatError(f"{name} is not a canonical label")
    return value


def _require_exact_keys(name: str, value: object, expected: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GrantFormatError(f"{name} must be an object")
    actual = set(value)
    if actual != expected:
        missing = ",".join(sorted(expected - actual)) or "none"
        extra = ",".join(sorted(actual - expected)) or "none"
        raise GrantFormatError(f"{name} keys mismatch (missing={missing}; extra={extra})")
    return value


def _require_secret(secret: object) -> bytes:
    if not isinstance(secret, (bytes, bytearray, memoryview)):
        raise TypeError("secret must be runtime-only bytes")
    material = bytes(secret)
    if len(material) < 32:
        raise ValueError("secret must contain at least 32 bytes")
    return material


def _datetime_to_unix(name: str, value: datetime) -> int:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return int(value.astimezone(UTC).timestamp())


def _validate_relative_path(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 1_024
        or value != value.strip()
        or value != unicodedata.normalize("NFC", value)
        or "\\" in value
        or "\x00" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise GrantFormatError("asset path is not canonical")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise GrantFormatError("asset path must be relative and traversal-free")
    if path.as_posix() != value:
        raise GrantFormatError("asset path must use canonical POSIX separators")
    return value


def canonical_asset_root(asset_root: str | os.PathLike[str]) -> str:
    """Return the exact, normalized absolute directory bound into a grant."""

    supplied = Path(asset_root).expanduser()
    if supplied.is_symlink():
        raise GrantFormatError("asset root must not be a symbolic link")
    try:
        resolved = supplied.resolve(strict=True)
    except OSError as exc:
        raise GrantFormatError("asset root does not exist") from exc
    if not resolved.is_dir():
        raise GrantFormatError("asset root must be a directory")
    normalized = os.path.normcase(str(resolved))
    return Path(normalized).as_posix()


def _validate_asset_root_text(value: object) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise GrantFormatError("asset_root must be a canonical absolute path")
    native = Path(value)
    if not native.is_absolute() or native.as_posix() != value:
        raise GrantFormatError("asset_root must be a canonical absolute path")
    normalized = Path(os.path.normcase(str(native))).as_posix()
    if normalized != value:
        raise GrantFormatError("asset_root must use normalized platform casing")
    return value


def _sha256_stable_file(path: Path) -> tuple[str, int]:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise GrantFormatError(f"asset cannot be stated: {path.name}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise GrantFormatError("asset manifest accepts regular files only")

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise GrantFormatError("asset changed type while hashing")
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise GrantFormatError(f"asset cannot be hashed: {path.name}") from exc

    before_identity = (before.st_size, before.st_mtime_ns, before.st_ino)
    opened_identity = (opened.st_size, opened.st_mtime_ns, opened.st_ino)
    after_identity = (after.st_size, after.st_mtime_ns, after.st_ino)
    if before_identity != opened_identity or opened_identity != after_identity:
        raise GrantFormatError("asset changed while hashing")
    return digest.hexdigest(), after.st_size


@dataclass(frozen=True, order=True)
class AssetManifestEntry:
    """One canonical suite asset."""

    path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        _validate_relative_path(self.path)
        _require_sha256("asset sha256", self.sha256)
        _require_int("asset size_bytes", self.size_bytes, minimum=0, maximum=2**63 - 1)

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "sha256": self.sha256, "size_bytes": self.size_bytes}

    @classmethod
    def from_mapping(cls, value: object) -> AssetManifestEntry:
        entry = _require_exact_keys(
            "asset manifest entry",
            value,
            frozenset({"path", "sha256", "size_bytes"}),
        )
        return cls(
            path=_validate_relative_path(entry["path"]),
            sha256=_require_sha256("asset sha256", entry["sha256"]),
            size_bytes=_require_int("asset size_bytes", entry["size_bytes"], minimum=0, maximum=2**63 - 1),
        )


def _manifest_digest(entries: Sequence[AssetManifestEntry]) -> str:
    base = {
        "schema_version": ASSET_MANIFEST_SCHEMA_VERSION,
        "files": [entry.to_dict() for entry in entries],
    }
    return _sha256_json(base)


@dataclass(frozen=True)
class AssetManifest:
    """Exact inventory of every regular file below the sealed suite root."""

    files: tuple[AssetManifestEntry, ...]
    root_sha256: str
    schema_version: str = ASSET_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ASSET_MANIFEST_SCHEMA_VERSION:
            raise GrantFormatError("asset manifest schema_version mismatch")
        if not self.files:
            raise GrantFormatError("asset manifest must contain at least one file")
        paths = [entry.path for entry in self.files]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise GrantFormatError("asset manifest paths must be sorted and unique")
        if len({path.casefold() for path in paths}) != len(paths):
            raise GrantFormatError("asset manifest contains case-colliding paths")
        _require_sha256("asset manifest root_sha256", self.root_sha256)
        if self.root_sha256 != _manifest_digest(self.files):
            raise GrantFormatError("asset manifest root digest does not match files")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "files": [entry.to_dict() for entry in self.files],
            "root_sha256": self.root_sha256,
        }

    @classmethod
    def from_mapping(cls, value: object) -> AssetManifest:
        manifest = _require_exact_keys(
            "asset_manifest",
            value,
            frozenset({"schema_version", "files", "root_sha256"}),
        )
        raw_files = manifest["files"]
        if not isinstance(raw_files, list):
            raise GrantFormatError("asset_manifest files must be an array")
        entries = tuple(AssetManifestEntry.from_mapping(item) for item in raw_files)
        return cls(
            schema_version=str(manifest["schema_version"]),
            files=entries,
            root_sha256=_require_sha256("asset manifest root_sha256", manifest["root_sha256"]),
        )


def build_asset_manifest(asset_root: str | os.PathLike[str]) -> AssetManifest:
    """Hash every suite file and reject links, special files, and empty suites."""

    canonical_root = canonical_asset_root(asset_root)
    root = Path(canonical_root)
    entries: list[AssetManifestEntry] = []
    for directory, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            candidate = directory_path / name
            try:
                mode = candidate.stat(follow_symlinks=False).st_mode
            except OSError as exc:
                raise GrantFormatError("suite directory cannot be stated") from exc
            if candidate.is_symlink() or not stat.S_ISDIR(mode):
                raise GrantFormatError("suite directories must be real directories")
        for name in file_names:
            candidate = directory_path / name
            if candidate.is_symlink():
                raise GrantFormatError("suite assets must not be symbolic links")
            relative = _validate_relative_path(candidate.relative_to(root).as_posix())
            digest, size = _sha256_stable_file(candidate)
            entries.append(AssetManifestEntry(relative, digest, size))
    entries.sort(key=lambda entry: entry.path)
    frozen = tuple(entries)
    return AssetManifest(files=frozen, root_sha256=_manifest_digest(frozen))


def _origin_for_port(port: int) -> str:
    return f"http://{LOOPBACK_HOST}:{port}"


_PAYLOAD_KEYS = frozenset(
    {
        "schema_version",
        "run_id",
        "nonce",
        "persona_id",
        "synthetic",
        "mode",
        "asset_root",
        "asset_manifest",
        "origin",
        "server_pid",
        "browser_pid",
        "expected_window_binding_id",
        "issued_at_unix",
        "expires_at_unix",
        "allowed_actions",
        "max_actions",
    }
)


@dataclass(frozen=True)
class SyntheticAssessmentGrant:
    """An immutable public grant; it deliberately contains no HMAC key."""

    run_id: str
    nonce: str
    asset_root: str
    asset_manifest: AssetManifest
    loopback_port: int
    server_pid: int
    browser_pid: int
    expected_window_binding_id: str
    issued_at_unix: int
    expires_at_unix: int
    allowed_actions: tuple[str, ...]
    max_actions: int
    hmac_sha256: str
    schema_version: str = SCHEMA_VERSION
    persona_id: str = SYNTHETIC_PERSONA_ID
    synthetic: bool = True
    mode: str = SYNTHETIC_MODE

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise GrantFormatError("grant schema_version mismatch")
        if self.persona_id != SYNTHETIC_PERSONA_ID:
            raise GrantFormatError("grant persona_id mismatch")
        if self.synthetic is not True:
            raise GrantFormatError("grant must be explicitly synthetic")
        if self.mode != SYNTHETIC_MODE:
            raise GrantFormatError("grant mode mismatch")
        _require_label("run_id", self.run_id)
        _require_label("nonce", self.nonce, minimum_length=16)
        _validate_asset_root_text(self.asset_root)
        if not isinstance(self.asset_manifest, AssetManifest):
            raise GrantFormatError("asset_manifest is invalid")
        _require_int("loopback port", self.loopback_port, minimum=1, maximum=65_535)
        _require_int("server_pid", self.server_pid, minimum=1, maximum=2**31 - 1)
        _require_int("browser_pid", self.browser_pid, minimum=1, maximum=2**31 - 1)
        if self.server_pid == self.browser_pid:
            raise GrantFormatError("server_pid and browser_pid must differ")
        _require_label("expected_window_binding_id", self.expected_window_binding_id)
        _require_int("issued_at_unix", self.issued_at_unix, minimum=0, maximum=2**63 - 1)
        _require_int("expires_at_unix", self.expires_at_unix, minimum=0, maximum=2**63 - 1)
        lifetime = self.expires_at_unix - self.issued_at_unix
        if not 0 < lifetime <= MAX_GRANT_LIFETIME_SECONDS:
            raise GrantFormatError("grant lifetime must be within 24 hours")
        if (
            not isinstance(self.allowed_actions, tuple)
            or not self.allowed_actions
            or list(self.allowed_actions) != sorted(set(self.allowed_actions))
            or not set(self.allowed_actions).issubset(SUPPORTED_ASSESSMENT_ACTIONS)
        ):
            raise GrantFormatError("allowed_actions must be a sorted supported scope")
        _require_int("max_actions", self.max_actions, minimum=1, maximum=MAX_ACTIONS_PER_GRANT)
        _require_sha256("hmac_sha256", self.hmac_sha256)

    @classmethod
    def issue(
        cls,
        *,
        secret: bytes | bytearray | memoryview,
        asset_root: str | os.PathLike[str],
        run_id: str,
        nonce: str,
        loopback_port: int,
        server_pid: int,
        browser_pid: int,
        expected_window_binding_id: str,
        issued_at: datetime,
        expires_at: datetime,
        allowed_actions: Sequence[str],
        max_actions: int = DEFAULT_MAX_ACTIONS,
    ) -> SyntheticAssessmentGrant:
        """Issue one grant using a runtime-only key and the live whole-suite tree."""

        actions = tuple(sorted(set(allowed_actions)))
        unsigned = cls(
            run_id=run_id,
            nonce=nonce,
            asset_root=canonical_asset_root(asset_root),
            asset_manifest=build_asset_manifest(asset_root),
            loopback_port=loopback_port,
            server_pid=server_pid,
            browser_pid=browser_pid,
            expected_window_binding_id=expected_window_binding_id,
            issued_at_unix=_datetime_to_unix("issued_at", issued_at),
            expires_at_unix=_datetime_to_unix("expires_at", expires_at),
            allowed_actions=actions,
            max_actions=max_actions,
            hmac_sha256="0" * 64,
        )
        signature = hmac.new(
            _require_secret(secret),
            _canonical_json(unsigned.signed_payload()).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return replace(unsigned, hmac_sha256=signature)

    def signed_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "nonce": self.nonce,
            "persona_id": self.persona_id,
            "synthetic": self.synthetic,
            "mode": self.mode,
            "asset_root": self.asset_root,
            "asset_manifest": self.asset_manifest.to_dict(),
            "origin": {
                "scheme": "http",
                "host": LOOPBACK_HOST,
                "port": self.loopback_port,
            },
            "server_pid": self.server_pid,
            "browser_pid": self.browser_pid,
            "expected_window_binding_id": self.expected_window_binding_id,
            "issued_at_unix": self.issued_at_unix,
            "expires_at_unix": self.expires_at_unix,
            "allowed_actions": list(self.allowed_actions),
            "max_actions": self.max_actions,
        }

    def to_dict(self) -> dict[str, object]:
        return {"grant": self.signed_payload(), "hmac_sha256": self.hmac_sha256}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def grant_sha256(self) -> str:
        return _sha256_json(self.signed_payload())

    def verify_signature(self, secret: bytes | bytearray | memoryview) -> SyntheticAssessmentGrant:
        expected = hmac.new(
            _require_secret(secret),
            _canonical_json(self.signed_payload()).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(self.hmac_sha256, expected):
            raise GrantSignatureError("grant HMAC verification failed")
        return self

    @classmethod
    def from_json(cls, encoded: str | bytes) -> SyntheticAssessmentGrant:
        raw: str
        if isinstance(encoded, bytes):
            if len(encoded) > _MAX_JSON_BYTES:
                raise GrantFormatError("grant JSON exceeds size limit")
            try:
                raw = encoded.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise GrantFormatError("grant JSON must be UTF-8") from exc
        elif isinstance(encoded, str):
            if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
                raise GrantFormatError("grant JSON exceeds size limit")
            raw = encoded
        else:
            raise TypeError("encoded grant must be str or bytes")

        def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
            parsed: dict[str, object] = {}
            for key, value in pairs:
                if key in parsed:
                    raise GrantFormatError(f"duplicate JSON key: {key}")
                parsed[key] = value
            return parsed

        def reject_constant(value: str) -> object:
            raise GrantFormatError(f"non-finite JSON number is forbidden: {value}")

        try:
            decoded = json.loads(
                raw,
                object_pairs_hook=no_duplicates,
                parse_constant=reject_constant,
            )
        except GrantFormatError:
            raise
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise GrantFormatError("grant JSON is invalid") from exc

        envelope = _require_exact_keys("grant envelope", decoded, frozenset({"grant", "hmac_sha256"}))
        payload = _require_exact_keys("grant payload", envelope["grant"], _PAYLOAD_KEYS)
        origin = _require_exact_keys("origin", payload["origin"], frozenset({"scheme", "host", "port"}))
        if origin["scheme"] != "http" or origin["host"] != LOOPBACK_HOST:
            raise GrantFormatError("origin must use exact IPv4 loopback HTTP")
        port = _require_int("origin port", origin["port"], minimum=1, maximum=65_535)
        actions = payload["allowed_actions"]
        if not isinstance(actions, list) or not all(isinstance(item, str) for item in actions):
            raise GrantFormatError("allowed_actions must be an array of strings")
        synthetic = payload["synthetic"]
        if not isinstance(synthetic, bool):
            raise GrantFormatError("synthetic must be a boolean")
        return cls(
            schema_version=_require_label("schema_version", payload["schema_version"]),
            run_id=_require_label("run_id", payload["run_id"]),
            nonce=_require_label("nonce", payload["nonce"], minimum_length=16),
            persona_id=_require_label("persona_id", payload["persona_id"]),
            synthetic=synthetic,
            mode=_require_label("mode", payload["mode"]),
            asset_root=_validate_asset_root_text(payload["asset_root"]),
            asset_manifest=AssetManifest.from_mapping(payload["asset_manifest"]),
            loopback_port=port,
            server_pid=_require_int("server_pid", payload["server_pid"], minimum=1, maximum=2**31 - 1),
            browser_pid=_require_int("browser_pid", payload["browser_pid"], minimum=1, maximum=2**31 - 1),
            expected_window_binding_id=_require_label(
                "expected_window_binding_id", payload["expected_window_binding_id"]
            ),
            issued_at_unix=_require_int(
                "issued_at_unix", payload["issued_at_unix"], minimum=0, maximum=2**63 - 1
            ),
            expires_at_unix=_require_int(
                "expires_at_unix", payload["expires_at_unix"], minimum=0, maximum=2**63 - 1
            ),
            allowed_actions=tuple(actions),
            max_actions=_require_int(
                "max_actions", payload["max_actions"], minimum=1, maximum=MAX_ACTIONS_PER_GRANT
            ),
            hmac_sha256=_require_sha256("hmac_sha256", envelope["hmac_sha256"]),
        )


@dataclass(frozen=True)
class AssessmentSessionContext:
    """Live values that must match the grant at activation and every action."""

    asset_root: str | os.PathLike[str]
    origin: str
    server_pid: int
    browser_pid: int
    window_binding_id: str
    run_id: str
    nonce: str
    now: datetime


@dataclass(frozen=True)
class AssessmentActionContext(AssessmentSessionContext):
    """Per-action context bound to a fresh pre-action observation."""

    action: str
    action_sequence: int
    observation_sha256: str


@dataclass(frozen=True)
class AuthorizedAssessmentAction:
    """Non-secret, immutable authorization receipt for one pending action."""

    run_id: str
    action: str
    action_sequence: int
    observation_sha256: str
    grant_sha256: str
    asset_manifest_root_sha256: str
    context_sha256: str
    receipt_sha256: str
    authorized_at_unix: int
    schema_version: str = ACTION_RECEIPT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "action": self.action,
            "action_sequence": self.action_sequence,
            "observation_sha256": self.observation_sha256,
            "grant_sha256": self.grant_sha256,
            "asset_manifest_root_sha256": self.asset_manifest_root_sha256,
            "context_sha256": self.context_sha256,
            "receipt_sha256": self.receipt_sha256,
            "authorized_at_unix": self.authorized_at_unix,
        }


class SyntheticAssessmentReplayGuard:
    """Persistently consume a grant activation with atomic create-if-absent."""

    def __init__(self, directory: str | os.PathLike[str]) -> None:
        supplied = Path(directory).expanduser()
        if supplied.is_symlink():
            raise GrantReplayError("replay directory must not be a symbolic link")
        try:
            supplied.mkdir(parents=True, exist_ok=True)
            resolved = supplied.resolve(strict=True)
        except OSError as exc:
            raise GrantReplayError("replay directory is unavailable") from exc
        if not resolved.is_dir():
            raise GrantReplayError("replay path must be a directory")
        self.directory = resolved

    @staticmethod
    def _replay_key(grant: SyntheticAssessmentGrant) -> str:
        return _sha256_json(
            {
                "schema_version": REPLAY_SCHEMA_VERSION,
                "run_id": grant.run_id,
                "nonce": grant.nonce,
            }
        )

    def consume(self, grant: SyntheticAssessmentGrant, *, activated_at_unix: int) -> str:
        replay_key = self._replay_key(grant)
        marker = self.directory / f"{replay_key}.json"
        record = {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "replay_key_sha256": replay_key,
            "grant_sha256": grant.grant_sha256,
            "activated_at_unix": activated_at_unix,
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        try:
            descriptor = os.open(marker, flags, 0o600)
        except FileExistsError as exc:
            raise GrantReplayError("grant run_id/nonce has already been activated") from exc
        except OSError as exc:
            raise GrantReplayError("replay marker could not be created") from exc
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(_canonical_json(record) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            # A partial marker intentionally remains: ambiguous activation fails closed.
            raise GrantReplayError("replay marker could not be committed") from exc
        return replay_key


def _validate_live_context(
    grant: SyntheticAssessmentGrant,
    context: AssessmentSessionContext,
) -> tuple[int, str]:
    if not isinstance(context, AssessmentSessionContext):
        raise TypeError("context must be an AssessmentSessionContext")
    if canonical_asset_root(context.asset_root) != grant.asset_root:
        raise GrantContextError("asset_root does not match grant")
    actual_manifest = build_asset_manifest(context.asset_root)
    if actual_manifest != grant.asset_manifest:
        raise GrantContextError("whole-suite asset manifest does not match grant")
    if context.origin != _origin_for_port(grant.loopback_port):
        raise GrantContextError("origin does not match exact signed loopback host/port")
    if context.server_pid != grant.server_pid:
        raise GrantContextError("server_pid does not match grant")
    if context.browser_pid != grant.browser_pid:
        raise GrantContextError("browser_pid does not match grant")
    if context.window_binding_id != grant.expected_window_binding_id:
        raise GrantContextError("window binding does not match grant")
    if context.run_id != grant.run_id:
        raise GrantContextError("run_id does not match grant")
    if context.nonce != grant.nonce:
        raise GrantContextError("nonce does not match grant")
    now_unix = _datetime_to_unix("context now", context.now)
    if now_unix < grant.issued_at_unix:
        raise GrantContextError("grant is not yet valid")
    if now_unix >= grant.expires_at_unix:
        raise GrantContextError("grant has expired")
    context_digest = _sha256_json(
        {
            "asset_root": grant.asset_root,
            "asset_manifest_root_sha256": actual_manifest.root_sha256,
            "origin": context.origin,
            "server_pid": context.server_pid,
            "browser_pid": context.browser_pid,
            "window_binding_id": context.window_binding_id,
            "run_id": context.run_id,
            "nonce_sha256": hashlib.sha256(context.nonce.encode("utf-8")).hexdigest(),
            "validated_at_unix": now_unix,
        }
    )
    return now_unix, context_digest


@dataclass
class ActiveSyntheticAssessmentSession:
    """One activated grant with strictly sequenced, bounded action receipts."""

    grant: SyntheticAssessmentGrant
    replay_key_sha256: str
    activation_context_sha256: str
    _factory_token: object = field(repr=False)
    _next_sequence: int = field(default=1, init=False, repr=False)
    _receipt_hashes: set[str] = field(default_factory=set, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self._factory_token is not _SESSION_FACTORY_TOKEN:
            raise GrantContextError("session must be created by grant activation")
        _require_sha256("replay_key_sha256", self.replay_key_sha256)
        _require_sha256("activation_context_sha256", self.activation_context_sha256)

    @property
    def next_action_sequence(self) -> int:
        with self._lock:
            return self._next_sequence

    def validate_context(self, context: AssessmentSessionContext) -> str:
        """Revalidate the live sealed suite without consuming an action sequence."""

        _now_unix, context_digest = _validate_live_context(self.grant, context)
        return context_digest

    def authorize_action(self, context: AssessmentActionContext) -> AuthorizedAssessmentAction:
        """Revalidate all live context and reserve exactly one action sequence."""

        if not isinstance(context, AssessmentActionContext):
            raise TypeError("context must be an AssessmentActionContext")
        now_unix, context_digest = _validate_live_context(self.grant, context)
        if context.action not in self.grant.allowed_actions:
            raise GrantContextError("action is outside the signed allowed scope")
        if not _valid_sha256(context.observation_sha256):
            raise GrantContextError("observation_sha256 must be lowercase SHA-256 hex")
        if (
            isinstance(context.action_sequence, bool)
            or not isinstance(context.action_sequence, int)
            or context.action_sequence < 1
        ):
            raise GrantContextError("action_sequence must be a positive integer")

        with self._lock:
            if self._next_sequence > self.grant.max_actions:
                raise GrantContextError("grant action limit has been reached")
            if context.action_sequence != self._next_sequence:
                raise GrantContextError("action_sequence is not the next unused sequence")
            receipt_base = {
                "schema_version": ACTION_RECEIPT_SCHEMA_VERSION,
                "run_id": self.grant.run_id,
                "action": context.action,
                "action_sequence": context.action_sequence,
                "observation_sha256": context.observation_sha256,
                "grant_sha256": self.grant.grant_sha256,
                "asset_manifest_root_sha256": self.grant.asset_manifest.root_sha256,
                "context_sha256": context_digest,
                "authorized_at_unix": now_unix,
            }
            receipt_hash = _sha256_json(receipt_base)
            if receipt_hash in self._receipt_hashes:
                raise GrantReplayError("action authorization receipt was replayed")
            self._receipt_hashes.add(receipt_hash)
            self._next_sequence += 1

        return AuthorizedAssessmentAction(
            run_id=self.grant.run_id,
            action=context.action,
            action_sequence=context.action_sequence,
            observation_sha256=context.observation_sha256,
            grant_sha256=self.grant.grant_sha256,
            asset_manifest_root_sha256=self.grant.asset_manifest.root_sha256,
            context_sha256=context_digest,
            receipt_sha256=receipt_hash,
            authorized_at_unix=now_unix,
        )


def activate_synthetic_assessment_grant(
    grant: SyntheticAssessmentGrant | str | bytes,
    *,
    secret: bytes | bytearray | memoryview,
    context: AssessmentSessionContext,
    replay_guard: SyntheticAssessmentReplayGuard,
) -> ActiveSyntheticAssessmentSession:
    """Authenticate and consume a grant, returning its only active session."""

    parsed = (
        grant if isinstance(grant, SyntheticAssessmentGrant) else SyntheticAssessmentGrant.from_json(grant)
    )
    parsed.verify_signature(secret)
    if not isinstance(replay_guard, SyntheticAssessmentReplayGuard):
        raise TypeError("replay_guard must be a SyntheticAssessmentReplayGuard")
    activated_at_unix, context_digest = _validate_live_context(parsed, context)
    replay_key = replay_guard.consume(parsed, activated_at_unix=activated_at_unix)
    return ActiveSyntheticAssessmentSession(
        grant=parsed,
        replay_key_sha256=replay_key,
        activation_context_sha256=context_digest,
        _factory_token=_SESSION_FACTORY_TOKEN,
    )


__all__ = [
    "ACTION_RECEIPT_SCHEMA_VERSION",
    "ASSET_MANIFEST_SCHEMA_VERSION",
    "DEFAULT_MAX_ACTIONS",
    "LOOPBACK_HOST",
    "MAX_ACTIONS_PER_GRANT",
    "MAX_GRANT_LIFETIME_SECONDS",
    "REPLAY_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SUPPORTED_ASSESSMENT_ACTIONS",
    "SYNTHETIC_MODE",
    "SYNTHETIC_PERSONA_ID",
    "ActiveSyntheticAssessmentSession",
    "AssessmentActionContext",
    "AssessmentSessionContext",
    "AssetManifest",
    "AssetManifestEntry",
    "AuthorizedAssessmentAction",
    "GrantContextError",
    "GrantFormatError",
    "GrantReplayError",
    "GrantSignatureError",
    "SyntheticAssessmentGrant",
    "SyntheticAssessmentGrantError",
    "SyntheticAssessmentReplayGuard",
    "activate_synthetic_assessment_grant",
    "build_asset_manifest",
    "canonical_asset_root",
]
