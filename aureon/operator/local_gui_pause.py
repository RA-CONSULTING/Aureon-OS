"""Hash-only resumable pause checkpoints for the governed GUI runtime."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from aureon.operator.local_gui_observer import ScreenObservation
from aureon.operator.local_gui_runtime import PAUSE_KINDS, RuntimeTransition

PAUSE_CHECKPOINT_SCHEMA_VERSION = "aureon-local-gui-pause-v1"
MAX_CHECKPOINT_BYTES = 64 * 1024
_CHECKPOINT_KEYS = frozenset(
    {
        "build_sha256",
        "checkpoint_sha256",
        "control_grant_sha256",
        "goal_sha256",
        "history_sha256",
        "pause_kind",
        "paused_observation_id",
        "paused_screenshot_sha256",
        "run_sha256",
        "run_authority_sha256",
        "schema_version",
        "window_sha256",
    }
)


class PauseCheckpointError(RuntimeError):
    """A pause checkpoint could not be created or resumed exactly."""


def _valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64 or value != value.lower():
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _window_digest(observation: ScreenObservation) -> str:
    rect = observation.window_rect
    if (
        observation.window_handle is None
        or observation.window_process_id is None
        or observation.window_title_sha256 is None
        or rect is None
        or observation.dpi_x is None
        or observation.dpi_y is None
    ):
        raise PauseCheckpointError("pause_checkpoint_requires_exact_window_and_dpi")
    payload = {
        "dpi": {"x": float(observation.dpi_x), "y": float(observation.dpi_y)},
        "window": {
            "handle": observation.window_handle,
            "process_id": observation.window_process_id,
            "rect": rect.to_dict(),
            "title_sha256": observation.window_title_sha256,
        },
    }
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _history_digest(history: Sequence[RuntimeTransition]) -> str:
    payload = {"transitions": [transition.to_dict() for transition in history]}
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _strict_json(raw: bytes) -> dict[str, object]:
    if not raw or len(raw) > MAX_CHECKPOINT_BYTES:
        raise PauseCheckpointError("pause_checkpoint_size_invalid")

    def reject_constant(value: str) -> object:
        raise ValueError(f"non-finite constant: {value}")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        parsed: dict[str, object] = {}
        for key, value in pairs:
            if key in parsed:
                raise ValueError(f"duplicate key: {key}")
            parsed[key] = value
        return parsed

    try:
        parsed = json.loads(
            raw.decode("ascii"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PauseCheckpointError("pause_checkpoint_json_invalid") from exc
    if not isinstance(parsed, dict) or set(parsed) != _CHECKPOINT_KEYS:
        raise PauseCheckpointError("pause_checkpoint_schema_invalid")
    return {str(key): value for key, value in parsed.items()}


@dataclass(frozen=True)
class PauseCheckpoint:
    """Validated hash-only checkpoint metadata safe for runtime receipts."""

    checkpoint_sha256: str
    pause_kind: str
    paused_observation_id: str
    paused_screenshot_sha256: str
    window_sha256: str
    history_sha256: str


class HashOnlyPauseCheckpointStore:
    """Atomically create, validate, and consume one resumable checkpoint."""

    def __init__(
        self,
        path: str | Path,
        *,
        run_id: str,
        build_id: str,
        goal: str,
        run_authority_sha256: str,
        control_grant_sha256: str,
    ) -> None:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            raise ValueError("pause checkpoint path must be absolute")
        parent = candidate.parent.resolve()
        if str(parent).startswith("\\\\") or parent == Path(parent.anchor):
            raise ValueError("pause checkpoint path must be below a safe local directory")
        parent.mkdir(parents=True, exist_ok=True)
        if not parent.is_dir() or parent.is_symlink():
            raise ValueError("pause checkpoint parent must be a real local directory")
        resolved = (parent / candidate.name).resolve()
        try:
            resolved.relative_to(parent)
        except ValueError as exc:
            raise ValueError("pause checkpoint path escaped its local directory") from exc
        if not str(run_id or "").strip() or not str(build_id or "").strip():
            raise ValueError("pause checkpoint run and build identities are required")
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("pause checkpoint goal is required")
        if not _valid_sha256(run_authority_sha256):
            raise ValueError(
                "pause checkpoint run_authority_sha256 must be lowercase SHA-256"
            )
        if not _valid_sha256(control_grant_sha256):
            raise ValueError(
                "pause checkpoint control_grant_sha256 must be lowercase SHA-256"
            )
        self.path = resolved
        self._run_sha256 = _digest_text(str(run_id))
        self._build_sha256 = _digest_text(str(build_id))
        self._goal_sha256 = _digest_text(goal)
        self._run_authority_sha256 = run_authority_sha256
        self._control_grant_sha256 = control_grant_sha256
        self._loaded: PauseCheckpoint | None = None

    @property
    def exists(self) -> bool:
        return self.path.is_file() and not self.path.is_symlink()

    def create(
        self,
        observation: ScreenObservation,
        history: Sequence[RuntimeTransition],
        *,
        pause_kind: str,
    ) -> PauseCheckpoint:
        if not isinstance(observation, ScreenObservation):
            raise TypeError("pause checkpoint observation must be a ScreenObservation")
        if not _valid_sha256(observation.observation_id) or not _valid_sha256(
            observation.screenshot_sha256
        ):
            raise PauseCheckpointError("pause_checkpoint_observation_identity_invalid")
        if pause_kind not in PAUSE_KINDS:
            raise ValueError("pause checkpoint pause_kind is not allowlisted")
        if self.path.exists() or self.path.is_symlink():
            raise PauseCheckpointError("pause_checkpoint_already_exists")
        base: dict[str, object] = {
            "build_sha256": self._build_sha256,
            "control_grant_sha256": self._control_grant_sha256,
            "goal_sha256": self._goal_sha256,
            "history_sha256": _history_digest(history),
            "pause_kind": pause_kind,
            "paused_observation_id": observation.observation_id,
            "paused_screenshot_sha256": observation.screenshot_sha256,
            "run_sha256": self._run_sha256,
            "run_authority_sha256": self._run_authority_sha256,
            "schema_version": PAUSE_CHECKPOINT_SCHEMA_VERSION,
            "window_sha256": _window_digest(observation),
        }
        checkpoint_sha256 = hashlib.sha256(_canonical_bytes(base)).hexdigest()
        payload = {**base, "checkpoint_sha256": checkpoint_sha256}
        self._install_exclusive(_canonical_bytes(payload) + b"\n")
        checkpoint = self._validate(payload)
        self._loaded = checkpoint
        return checkpoint

    def load(self) -> PauseCheckpoint:
        if not self.path.is_file() or self.path.is_symlink():
            raise PauseCheckpointError("pause_checkpoint_missing")
        try:
            with self.path.open("rb") as handle:
                raw = handle.read(MAX_CHECKPOINT_BYTES + 1)
        except OSError as exc:
            raise PauseCheckpointError("pause_checkpoint_unreadable") from exc
        payload = _strict_json(raw)
        checkpoint = self._validate(payload)
        self._loaded = checkpoint
        return checkpoint

    def verify_checkpoint(
        self,
        observation: ScreenObservation,
        history: Sequence[RuntimeTransition],
        *,
        pause_kind: str,
        checkpoint_sha256: str,
    ) -> bool:
        """Read-only verify one persisted checkpoint against exact runtime state."""

        if type(observation) is not ScreenObservation:
            raise TypeError("pause checkpoint observation must be a ScreenObservation")
        if not isinstance(history, (tuple, list)) or any(
            type(transition) is not RuntimeTransition for transition in history
        ):
            raise TypeError("pause checkpoint history must contain RuntimeTransition values")
        if pause_kind not in PAUSE_KINDS or not _valid_sha256(checkpoint_sha256):
            return False
        try:
            checkpoint = self.load()
            window_sha256 = _window_digest(observation)
            history_sha256 = _history_digest(history)
        except (OSError, PauseCheckpointError, TypeError, ValueError):
            return False
        return (
            checkpoint.checkpoint_sha256 == checkpoint_sha256
            and checkpoint.pause_kind == pause_kind
            and checkpoint.paused_observation_id == observation.observation_id
            and checkpoint.paused_screenshot_sha256
            == observation.screenshot_sha256
            and checkpoint.window_sha256 == window_sha256
            and checkpoint.history_sha256 == history_sha256
        )

    def validate_fresh_observation_and_consume(self, observation: ScreenObservation) -> bool:
        checkpoint = self._loaded
        if checkpoint is None:
            raise PauseCheckpointError("pause_checkpoint_not_loaded")
        if not isinstance(observation, ScreenObservation):
            raise TypeError("resume observation must be a ScreenObservation")
        if observation.observation_id == checkpoint.paused_observation_id:
            raise PauseCheckpointError("resume_observation_not_fresh")
        if _window_digest(observation) != checkpoint.window_sha256:
            raise PauseCheckpointError("resume_window_binding_mismatch")
        current = self.load()
        if current.checkpoint_sha256 != checkpoint.checkpoint_sha256:
            raise PauseCheckpointError("pause_checkpoint_changed_before_consume")
        consumed = self.path.with_name(
            f"{self.path.stem}.{checkpoint.checkpoint_sha256}.consumed.json"
        )
        if consumed.exists() or consumed.is_symlink():
            raise PauseCheckpointError("pause_checkpoint_already_consumed")
        try:
            os.replace(self.path, consumed)
        except OSError as exc:
            raise PauseCheckpointError("pause_checkpoint_consume_failed") from exc
        self._loaded = None
        return True

    def _validate(
        self,
        payload: Mapping[str, object],
    ) -> PauseCheckpoint:
        if set(payload) != _CHECKPOINT_KEYS:
            raise PauseCheckpointError("pause_checkpoint_schema_invalid")
        if payload.get("schema_version") != PAUSE_CHECKPOINT_SCHEMA_VERSION:
            raise PauseCheckpointError("pause_checkpoint_schema_invalid")
        pause_kind = payload.get("pause_kind")
        if pause_kind not in PAUSE_KINDS:
            raise PauseCheckpointError("pause_checkpoint_kind_invalid")
        for field in _CHECKPOINT_KEYS - {"schema_version", "pause_kind"}:
            if not _valid_sha256(payload.get(field)):
                raise PauseCheckpointError(f"pause_checkpoint_{field}_invalid")
        expected_static = {
            "build_sha256": self._build_sha256,
            "control_grant_sha256": self._control_grant_sha256,
            "goal_sha256": self._goal_sha256,
            "run_sha256": self._run_sha256,
            "run_authority_sha256": self._run_authority_sha256,
        }
        if any(payload.get(key) != value for key, value in expected_static.items()):
            raise PauseCheckpointError("pause_checkpoint_context_mismatch")
        supplied_digest = str(payload["checkpoint_sha256"])
        base = {key: value for key, value in payload.items() if key != "checkpoint_sha256"}
        if hashlib.sha256(_canonical_bytes(base)).hexdigest() != supplied_digest:
            raise PauseCheckpointError("pause_checkpoint_digest_mismatch")
        return PauseCheckpoint(
            checkpoint_sha256=supplied_digest,
            pause_kind=str(pause_kind),
            paused_observation_id=str(payload["paused_observation_id"]),
            paused_screenshot_sha256=str(payload["paused_screenshot_sha256"]),
            window_sha256=str(payload["window_sha256"]),
            history_sha256=str(payload["history_sha256"]),
        )

    def _install_exclusive(self, raw: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            try:
                os.link(temporary, self.path)
            except FileExistsError as exc:
                raise PauseCheckpointError("pause_checkpoint_already_exists") from exc
            except OSError as exc:
                raise PauseCheckpointError("pause_checkpoint_atomic_write_failed") from exc
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


__all__ = [
    "HashOnlyPauseCheckpointStore",
    "MAX_CHECKPOINT_BYTES",
    "PAUSE_CHECKPOINT_SCHEMA_VERSION",
    "PauseCheckpoint",
    "PauseCheckpointError",
]
