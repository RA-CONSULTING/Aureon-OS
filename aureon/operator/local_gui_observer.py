"""Local-only screen observation contracts for Aureon's GUI operator.

This module deliberately contains no concrete desktop or network implementation.
The production runtime must inject a screenshot backend, an OCR backend, and,
optionally, a vision hook that explicitly declares itself local-only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence, runtime_checkable

FRAME_ARTIFACT_SCHEMA_VERSION = "aureon-screenreel-frame-artifact-v1"
_STABILITY_PROFILE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789._-")


class ObservationError(RuntimeError):
    """Raised when a screen observation cannot be produced safely."""


class GatewayObservationRejectedError(ObservationError):
    """Structured, public-safe rejection from the governed screenshot gateway."""

    def __init__(self, reason: str) -> None:
        if (
            not isinstance(reason, str)
            or not 1 <= len(reason) <= 128
            or any(character not in _STABILITY_PROFILE_CHARS for character in reason)
        ):
            raise ValueError("gateway observation rejection reason must be a safe label")
        self.reason = reason
        super().__init__(f"gateway_observation_or_evidence_failed:{reason}")


def _valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _valid_stability_profile(value: object) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 128
        and value[0] in "abcdefghijklmnopqrstuvwxyz0123456789"
        and all(character in _STABILITY_PROFILE_CHARS for character in value)
    )


def _positive_integer(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class WindowRect:
    """Native screen-space rectangle retained without a plaintext title."""

    left: int
    top: int
    width: int
    height: int

    def __post_init__(self) -> None:
        for name in ("left", "top", "width", "height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"window rect {name} must be an integer")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("window rect width and height must be positive")

    def to_dict(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class CursorTelemetry:
    """Validated pointer position with a compact planner-safe representation."""

    x: int
    y: int

    def __post_init__(self) -> None:
        for name in ("x", "y"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"cursor {name} must be a non-negative integer")

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class FrameArtifactReference:
    """Safe, content-addressed reference to one retained PNG and its metadata."""

    sha256: str
    byte_length: int
    width: int
    height: int
    mime_type: str
    png_relative_path: str
    metadata_relative_path: str
    metadata_sha256: str

    def __post_init__(self) -> None:
        if not _valid_sha256(self.sha256):
            raise ValueError("frame artifact sha256 must be lowercase SHA-256")
        if not _valid_sha256(self.metadata_sha256):
            raise ValueError("frame artifact metadata_sha256 must be lowercase SHA-256")
        _positive_integer("frame artifact byte_length", self.byte_length)
        _positive_integer("frame artifact width", self.width)
        _positive_integer("frame artifact height", self.height)
        if self.mime_type != "image/png":
            raise ValueError("frame artifact mime_type must be image/png")
        for name in ("png_relative_path", "metadata_relative_path"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or "\\" in value:
                raise ValueError(f"{name} must be a non-empty POSIX relative path")
            candidate = Path(value)
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError(f"{name} must remain relative to the artifact store")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": FRAME_ARTIFACT_SCHEMA_VERSION,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "dimensions": {"width": self.width, "height": self.height},
            "mime_type": self.mime_type,
            "png_relative_path": self.png_relative_path,
            "metadata_relative_path": self.metadata_relative_path,
            "metadata_sha256": self.metadata_sha256,
        }


def _validate_frame_telemetry(
    *,
    width: int,
    height: int,
    cursor_x: int | None,
    cursor_y: int | None,
    window_handle: int | None,
    window_process_id: int | None,
    window_title_sha256: str | None,
    window_rect: WindowRect | None,
    dpi_x: float | None,
    dpi_y: float | None,
) -> None:
    cursor_present = (cursor_x is not None, cursor_y is not None)
    if cursor_present[0] != cursor_present[1]:
        raise ValueError("cursor_x and cursor_y must be supplied together")
    if cursor_x is not None and cursor_y is not None:
        if isinstance(cursor_x, bool) or not isinstance(cursor_x, int):
            raise TypeError("cursor_x must be an integer")
        if isinstance(cursor_y, bool) or not isinstance(cursor_y, int):
            raise TypeError("cursor_y must be an integer")
        if not 0 <= cursor_x < width or not 0 <= cursor_y < height:
            raise ValueError("cursor coordinates must lie inside the captured screen")

    window_values = (window_handle, window_process_id, window_title_sha256, window_rect)
    if any(value is not None for value in window_values) and not all(
        value is not None for value in window_values
    ):
        raise ValueError("window handle, PID, title hash, and rect must be supplied together")
    if window_handle is not None:
        _positive_integer("window_handle", window_handle)
        _positive_integer("window_process_id", window_process_id)
        if not _valid_sha256(window_title_sha256):
            raise ValueError("window_title_sha256 must be lowercase SHA-256")
        if not isinstance(window_rect, WindowRect):
            raise TypeError("window_rect must be a WindowRect")

    dpi_present = (dpi_x is not None, dpi_y is not None)
    if dpi_present[0] != dpi_present[1]:
        raise ValueError("dpi_x and dpi_y must be supplied together")
    for name, value in (("dpi_x", dpi_x), ("dpi_y", dpi_y)):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric")
        if not math.isfinite(float(value)) or not 1.0 <= float(value) <= 1_000.0:
            raise ValueError(f"{name} must be finite and between 1 and 1000")


def _telemetry_dict(
    *,
    cursor_x: int | None,
    cursor_y: int | None,
    window_handle: int | None,
    window_process_id: int | None,
    window_title_sha256: str | None,
    window_rect: WindowRect | None,
    dpi_x: float | None,
    dpi_y: float | None,
) -> dict[str, object]:
    cursor = None if cursor_x is None else {"x": cursor_x, "y": cursor_y}
    window = None
    if window_handle is not None:
        assert window_process_id is not None
        assert window_title_sha256 is not None
        assert window_rect is not None
        window = {
            "handle": window_handle,
            "process_id": window_process_id,
            "title_sha256": window_title_sha256,
            "rect": window_rect.to_dict(),
        }
    if dpi_x is None:
        dpi = None
    else:
        assert dpi_y is not None
        dpi = {"x": float(dpi_x), "y": float(dpi_y)}
    return {"cursor": cursor, "window": window, "dpi": dpi}


@dataclass(frozen=True)
class CapturedScreen:
    """An in-memory screen capture supplied by an injected backend."""

    image_bytes: bytes
    width: int
    height: int
    mime_type: str = "image/png"
    cursor_x: int | None = None
    cursor_y: int | None = None
    window_handle: int | None = None
    window_process_id: int | None = None
    window_title_sha256: str | None = None
    window_rect: WindowRect | None = None
    dpi_x: float | None = None
    dpi_y: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.image_bytes, bytes) or not self.image_bytes:
            raise ValueError("image_bytes must be non-empty bytes")
        if isinstance(self.width, bool) or not isinstance(self.width, int) or self.width <= 0:
            raise ValueError("width must be a positive integer")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or self.height <= 0:
            raise ValueError("height must be a positive integer")
        if self.mime_type not in {"image/png", "image/jpeg"}:
            raise ValueError("mime_type must be image/png or image/jpeg")
        _validate_frame_telemetry(
            width=self.width,
            height=self.height,
            cursor_x=self.cursor_x,
            cursor_y=self.cursor_y,
            window_handle=self.window_handle,
            window_process_id=self.window_process_id,
            window_title_sha256=self.window_title_sha256,
            window_rect=self.window_rect,
            dpi_x=self.dpi_x,
            dpi_y=self.dpi_y,
        )

    @property
    def cursor(self) -> CursorTelemetry | None:
        if self.cursor_x is None or self.cursor_y is None:
            return None
        return CursorTelemetry(self.cursor_x, self.cursor_y)


class FrameArtifactStore:
    """Retain PNG frames below one injected run directory by SHA-256.

    Files are installed with an exclusive hard-link from a private temporary
    file, so a concurrent writer can never replace an existing content address.
    Existing targets are accepted only when their bytes match exactly.
    """

    def __init__(self, run_directory: str | Path) -> None:
        raw = Path(run_directory).expanduser()
        if not raw.is_absolute():
            raise ValueError("frame artifact run_directory must be absolute")
        root = raw.resolve()
        if str(root).startswith("\\\\") or root == Path(root.anchor):
            raise ValueError("frame artifact run_directory must be a safe local directory")
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir() or root.is_symlink():
            raise ValueError("frame artifact run_directory must be a real directory")
        self.run_directory = root

    def retain(self, frame: CapturedScreen, *, screenshot_sha256: str) -> FrameArtifactReference:
        if not isinstance(frame, CapturedScreen):
            raise TypeError("frame must be a CapturedScreen")
        if frame.mime_type != "image/png":
            raise ObservationError("frame_artifact_store_requires_png")
        if not frame.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ObservationError("frame_artifact_invalid_png_signature")
        calculated = hashlib.sha256(frame.image_bytes).hexdigest()
        if calculated != screenshot_sha256 or not _valid_sha256(screenshot_sha256):
            raise ObservationError("frame_artifact_hash_mismatch")

        png_relative = Path("screenreel_frames") / "sha256" / calculated[:2] / f"{calculated}.png"
        metadata_relative = png_relative.with_suffix(".json")
        png_path = self._safe_target(png_relative)
        metadata_path = self._safe_target(metadata_relative)
        self._install_exclusive(png_path, frame.image_bytes)

        metadata = {
            "schema_version": FRAME_ARTIFACT_SCHEMA_VERSION,
            "sha256": calculated,
            "byte_length": len(frame.image_bytes),
            "dimensions": {"width": frame.width, "height": frame.height},
            "mime_type": frame.mime_type,
            "png_relative_path": png_relative.as_posix(),
        }
        metadata_bytes = (
            json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode("utf-8")
        metadata_sha256 = hashlib.sha256(metadata_bytes).hexdigest()
        self._install_exclusive(metadata_path, metadata_bytes)
        return FrameArtifactReference(
            sha256=calculated,
            byte_length=len(frame.image_bytes),
            width=frame.width,
            height=frame.height,
            mime_type=frame.mime_type,
            png_relative_path=png_relative.as_posix(),
            metadata_relative_path=metadata_relative.as_posix(),
            metadata_sha256=metadata_sha256,
        )

    def _safe_target(self, relative: Path) -> Path:
        target = (self.run_directory / relative).resolve()
        try:
            target.relative_to(self.run_directory)
        except ValueError as exc:
            raise ObservationError("frame_artifact_path_escaped_run_directory") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.is_symlink():
            raise ObservationError("frame_artifact_parent_must_not_be_symlink")
        return target

    @staticmethod
    def _install_exclusive(path: Path, payload: bytes) -> None:
        if path.exists():
            try:
                if path.is_file() and path.read_bytes() == payload:
                    return
            except OSError as exc:
                raise ObservationError("frame_artifact_existing_target_unreadable") from exc
            raise ObservationError("frame_artifact_existing_target_mismatch")

        temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
        try:
            descriptor = os.open(str(temporary), flags, 0o600)
            try:
                view = memoryview(payload)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("short frame artifact write")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            try:
                os.link(temporary, path)
            except FileExistsError as exc:
                if not path.is_file() or path.read_bytes() != payload:
                    raise ObservationError("frame_artifact_concurrent_target_mismatch") from exc
        except ObservationError:
            raise
        except Exception as exc:
            raise ObservationError("frame_artifact_atomic_write_failed") from exc
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


@dataclass(frozen=True)
class OCRToken:
    """One OCR token and its screen-space bounding box."""

    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("OCR token text must be a string")
        for name in ("x", "y", "width", "height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"OCR token {name} must be an integer")
        if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("OCR token box must be positive and non-negative")
        if self.confidence is not None and not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("OCR confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "box": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
            },
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ScreenObservation:
    """Hash-bound, planner-safe description of one freshly captured screen."""

    observation_id: str
    sequence: int
    captured_at_unix: float
    screenshot_sha256: str
    width: int
    height: int
    ocr_tokens: tuple[OCRToken, ...]
    vision_text: str = ""
    mime_type: str = "image/png"
    cursor_x: int | None = None
    cursor_y: int | None = None
    window_handle: int | None = None
    window_process_id: int | None = None
    window_title_sha256: str | None = None
    window_rect: WindowRect | None = None
    dpi_x: float | None = None
    dpi_y: float | None = None
    frame_artifact: FrameArtifactReference | None = None
    stability_profile: str | None = None
    stability_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, str) or not self.observation_id.strip():
            raise ValueError("observation_id must be a non-empty string")
        _positive_integer("sequence", self.sequence)
        if (
            isinstance(self.captured_at_unix, bool)
            or not isinstance(self.captured_at_unix, (int, float))
            or not math.isfinite(float(self.captured_at_unix))
        ):
            raise ValueError("captured_at_unix must be finite")
        if not _valid_sha256(self.screenshot_sha256):
            raise ValueError("screenshot_sha256 must be lowercase SHA-256")
        _positive_integer("width", self.width)
        _positive_integer("height", self.height)
        if not isinstance(self.ocr_tokens, tuple) or not all(
            isinstance(token, OCRToken) for token in self.ocr_tokens
        ):
            raise TypeError("ocr_tokens must be a tuple of OCRToken instances")
        if not isinstance(self.vision_text, str):
            raise TypeError("vision_text must be a string")
        if (self.stability_profile is None) != (self.stability_sha256 is None):
            raise ValueError("stability_profile and stability_sha256 must be supplied together")
        if self.stability_profile is not None and not _valid_stability_profile(
            self.stability_profile
        ):
            raise ValueError("stability_profile must be a bounded lowercase identifier")
        if self.stability_sha256 is not None and not _valid_sha256(self.stability_sha256):
            raise ValueError("stability_sha256 must be lowercase SHA-256 when supplied")
        if self.mime_type not in {"image/png", "image/jpeg"}:
            raise ValueError("mime_type must be image/png or image/jpeg")
        _validate_frame_telemetry(
            width=self.width,
            height=self.height,
            cursor_x=self.cursor_x,
            cursor_y=self.cursor_y,
            window_handle=self.window_handle,
            window_process_id=self.window_process_id,
            window_title_sha256=self.window_title_sha256,
            window_rect=self.window_rect,
            dpi_x=self.dpi_x,
            dpi_y=self.dpi_y,
        )
        if self.frame_artifact is not None:
            if not isinstance(self.frame_artifact, FrameArtifactReference):
                raise TypeError("frame_artifact must be a FrameArtifactReference")
            if (
                self.frame_artifact.sha256 != self.screenshot_sha256
                or self.frame_artifact.width != self.width
                or self.frame_artifact.height != self.height
                or self.frame_artifact.mime_type != self.mime_type
            ):
                raise ValueError("frame_artifact does not match the observation")

    @property
    def cursor(self) -> CursorTelemetry | None:
        if self.cursor_x is None or self.cursor_y is None:
            return None
        return CursorTelemetry(self.cursor_x, self.cursor_y)

    @property
    def ocr_text(self) -> str:
        return " ".join(token.text for token in self.ocr_tokens if token.text).strip()

    def to_dict(self) -> dict[str, object]:
        result = {
            "observation_id": self.observation_id,
            "sequence": self.sequence,
            "captured_at_unix": self.captured_at_unix,
            "screenshot_sha256": self.screenshot_sha256,
            "dimensions": {"width": self.width, "height": self.height},
            "ocr_tokens": [token.to_dict() for token in self.ocr_tokens],
            "ocr_text": self.ocr_text,
            "vision_text": self.vision_text,
            "mime_type": self.mime_type,
        }
        if self.stability_sha256 is not None:
            result["stability_profile"] = self.stability_profile
            result["stability_sha256"] = self.stability_sha256
        result.update(self.telemetry_dict())
        result["frame_artifact"] = (
            self.frame_artifact.to_dict() if self.frame_artifact is not None else None
        )
        return result

    def telemetry_dict(self) -> dict[str, object]:
        """Return pointer/window/DPI metadata with no OCR, vision, or raw pixels."""

        return _telemetry_dict(
            cursor_x=self.cursor_x,
            cursor_y=self.cursor_y,
            window_handle=self.window_handle,
            window_process_id=self.window_process_id,
            window_title_sha256=self.window_title_sha256,
            window_rect=self.window_rect,
            dpi_x=self.dpi_x,
            dpi_y=self.dpi_y,
        )

    def receipt_dict(self) -> dict[str, object]:
        """Return the evidence-safe ScreenReel identity for transition ledgers."""

        result: dict[str, object] = {
            "observation_id": self.observation_id,
            "sequence": self.sequence,
            "captured_at_unix": self.captured_at_unix,
            "screenshot_sha256": self.screenshot_sha256,
            "dimensions": {"width": self.width, "height": self.height},
            "mime_type": self.mime_type,
        }
        if self.stability_sha256 is not None:
            result["stability_profile"] = self.stability_profile
            result["stability_sha256"] = self.stability_sha256
        result.update(self.telemetry_dict())
        result["frame_artifact"] = (
            self.frame_artifact.to_dict() if self.frame_artifact is not None else None
        )
        return result


@runtime_checkable
class ScreenshotBackend(Protocol):
    """Injected local screenshot provider."""

    def capture(self) -> CapturedScreen:
        """Capture the current screen without performing any other action."""


@runtime_checkable
class OCRBackend(Protocol):
    """Injected OCR implementation; it must not mutate the desktop."""

    def recognize(self, frame: CapturedScreen) -> Sequence[OCRToken]:
        """Return screen-space OCR tokens for ``frame``."""


@runtime_checkable
class LocalVisionHook(Protocol):
    """Optional visual description hook that is contractually local-only."""

    @property
    def locality(self) -> str:
        """Return exactly ``local``; remote hooks are rejected."""

    def describe(self, frame: CapturedScreen, tokens: Sequence[OCRToken]) -> str:
        """Return a concise local visual description of ``frame``."""


@runtime_checkable
class LocalStabilityFingerprint(Protocol):
    """Optional local-only canonical pixel fingerprint provider."""

    @property
    def locality(self) -> str:
        """Return exactly ``local``; remote providers are rejected."""

    @property
    def profile(self) -> str:
        """Return a bounded lowercase identifier for the canonical hash profile."""

    def fingerprint(self, frame: CapturedScreen) -> str:
        """Return one lowercase SHA-256 derived from canonical local pixels."""


class LocalGUIObserver:
    """Compose injected capture/OCR/vision components into safe observations."""

    def __init__(
        self,
        screenshot_backend: ScreenshotBackend,
        ocr_backend: OCRBackend,
        *,
        vision_hook: LocalVisionHook | None = None,
        stability_fingerprint: LocalStabilityFingerprint | None = None,
        artifact_store: FrameArtifactStore | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if vision_hook is not None and getattr(vision_hook, "locality", "") != "local":
            raise ValueError("vision_hook must declare locality='local'")
        if (
            stability_fingerprint is not None
            and getattr(stability_fingerprint, "locality", "") != "local"
        ):
            raise ValueError("stability_fingerprint must declare locality='local'")
        stability_profile = (
            None
            if stability_fingerprint is None
            else getattr(stability_fingerprint, "profile", None)
        )
        if stability_fingerprint is not None and not _valid_stability_profile(
            stability_profile
        ):
            raise ValueError("stability_fingerprint must declare a valid profile")
        self._screenshot_backend = screenshot_backend
        self._ocr_backend = ocr_backend
        self._vision_hook = vision_hook
        self._stability_fingerprint = stability_fingerprint
        self._stability_profile = stability_profile
        if artifact_store is not None and not isinstance(artifact_store, FrameArtifactStore):
            raise TypeError("artifact_store must be a FrameArtifactStore")
        self._artifact_store = artifact_store
        self._clock = clock
        self._sequence = 0

    def observe(self) -> ScreenObservation:
        """Capture a fresh screen and bind its derived evidence to a SHA-256."""

        try:
            frame = self._screenshot_backend.capture()
            stability_sha256 = None
            if self._stability_fingerprint is not None:
                stability_sha256 = self._stability_fingerprint.fingerprint(frame)
                if not _valid_sha256(stability_sha256):
                    raise ObservationError("stability_fingerprint_must_be_lowercase_sha256")
            tokens = tuple(self._ocr_backend.recognize(frame))
            self._validate_token_boxes(tokens, frame)
            vision_text = ""
            if self._vision_hook is not None:
                vision_text = str(self._vision_hook.describe(frame, tokens) or "").strip()
        except (ObservationError, TypeError, ValueError):
            raise
        except Exception as exc:  # noqa: BLE001 - backends are injected boundaries
            raise ObservationError(f"screen observation failed: {type(exc).__name__}: {exc}") from exc

        self._sequence += 1
        captured_at = float(self._clock())
        if not math.isfinite(captured_at):
            raise ObservationError("observation clock must return a finite value")
        screenshot_sha256 = hashlib.sha256(frame.image_bytes).hexdigest()
        frame_artifact = None
        if self._artifact_store is not None:
            frame_artifact = self._artifact_store.retain(
                frame,
                screenshot_sha256=screenshot_sha256,
            )
        telemetry = _telemetry_dict(
            cursor_x=frame.cursor_x,
            cursor_y=frame.cursor_y,
            window_handle=frame.window_handle,
            window_process_id=frame.window_process_id,
            window_title_sha256=frame.window_title_sha256,
            window_rect=frame.window_rect,
            dpi_x=frame.dpi_x,
            dpi_y=frame.dpi_y,
        )
        identity_record: dict[str, object] = {
            "sequence": self._sequence,
            "captured_at_unix": captured_at,
            "screenshot_sha256": screenshot_sha256,
            "width": frame.width,
            "height": frame.height,
            "mime_type": frame.mime_type,
            "telemetry": telemetry,
            "frame_artifact_sha256": (
                frame_artifact.metadata_sha256 if frame_artifact is not None else None
            ),
        }
        if stability_sha256 is not None:
            identity_record["stability_profile"] = self._stability_profile
            identity_record["stability_sha256"] = stability_sha256
        identity_material = json.dumps(
            identity_record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        observation_id = hashlib.sha256(identity_material).hexdigest()
        return ScreenObservation(
            observation_id=observation_id,
            sequence=self._sequence,
            captured_at_unix=captured_at,
            screenshot_sha256=screenshot_sha256,
            width=frame.width,
            height=frame.height,
            ocr_tokens=tokens,
            vision_text=vision_text,
            mime_type=frame.mime_type,
            cursor_x=frame.cursor_x,
            cursor_y=frame.cursor_y,
            window_handle=frame.window_handle,
            window_process_id=frame.window_process_id,
            window_title_sha256=frame.window_title_sha256,
            window_rect=frame.window_rect,
            dpi_x=frame.dpi_x,
            dpi_y=frame.dpi_y,
            frame_artifact=frame_artifact,
            stability_profile=self._stability_profile,
            stability_sha256=stability_sha256,
        )

    @staticmethod
    def _validate_token_boxes(tokens: Sequence[OCRToken], frame: CapturedScreen) -> None:
        for token in tokens:
            if not isinstance(token, OCRToken):
                raise TypeError("OCR backend must return OCRToken instances")
            if token.x + token.width > frame.width or token.y + token.height > frame.height:
                raise ObservationError("OCR token box lies outside the captured screen")


__all__ = [
    "CapturedScreen",
    "CursorTelemetry",
    "FRAME_ARTIFACT_SCHEMA_VERSION",
    "FrameArtifactReference",
    "FrameArtifactStore",
    "GatewayObservationRejectedError",
    "LocalGUIObserver",
    "LocalStabilityFingerprint",
    "LocalVisionHook",
    "OCRBackend",
    "OCRToken",
    "ObservationError",
    "ScreenObservation",
    "ScreenshotBackend",
    "WindowRect",
]
