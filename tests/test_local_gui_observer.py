from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from aureon.operator.local_gui_observer import (
    CapturedScreen,
    FrameArtifactStore,
    LocalGUIObserver,
    ObservationError,
    OCRToken,
    WindowRect,
)


@dataclass
class _ScreenshotBackend:
    frame: CapturedScreen

    def capture(self) -> CapturedScreen:
        return self.frame


class _OCRBackend:
    def recognize(self, frame: CapturedScreen):
        return [OCRToken("Continue", 2, 3, min(20, frame.width), min(10, frame.height), 0.99)]


def _telemetry_frame() -> CapturedScreen:
    return CapturedScreen(
        b"\x89PNG\r\n\x1a\nscreenreel-png-payload",
        width=100,
        height=50,
        cursor_x=21,
        cursor_y=22,
        window_handle=1001,
        window_process_id=4242,
        window_title_sha256=hashlib.sha256(b"Synthetic Course Window").hexdigest(),
        window_rect=WindowRect(left=-10, top=0, width=110, height=50),
        dpi_x=96.0,
        dpi_y=96.0,
    )


def test_captured_screen_defaults_remain_compatible_and_telemetry_is_strict():
    default = CapturedScreen(b"frame", 10, 10)
    assert default.cursor_x is None
    assert default.window_handle is None

    with pytest.raises(ValueError, match="supplied together"):
        CapturedScreen(b"frame", 10, 10, cursor_x=1)
    with pytest.raises(ValueError, match="inside the captured screen"):
        CapturedScreen(b"frame", 10, 10, cursor_x=10, cursor_y=1)
    with pytest.raises(ValueError, match="handle, PID, title hash, and rect"):
        CapturedScreen(b"frame", 10, 10, window_handle=1)
    with pytest.raises(ValueError, match="dpi_x and dpi_y"):
        CapturedScreen(b"frame", 10, 10, dpi_x=96.0)
    with pytest.raises(ValueError, match="finite and between"):
        CapturedScreen(b"frame", 10, 10, dpi_x=float("nan"), dpi_y=96.0)
    with pytest.raises(ValueError, match="width and height must be positive"):
        WindowRect(left=0, top=0, width=0, height=10)


def test_observer_propagates_pointer_window_rect_and_dpi_without_plaintext_title():
    frame = _telemetry_frame()
    observed = LocalGUIObserver(
        _ScreenshotBackend(frame),
        _OCRBackend(),
        clock=lambda: 123.0,
    ).observe()

    assert (observed.cursor_x, observed.cursor_y) == (21, 22)
    assert observed.window_handle == 1001
    assert observed.window_process_id == 4242
    assert observed.window_rect == WindowRect(left=-10, top=0, width=110, height=50)
    assert (observed.dpi_x, observed.dpi_y) == (96.0, 96.0)
    receipt = observed.receipt_dict()
    assert receipt["cursor"] == {"x": 21, "y": 22}
    assert receipt["window"]["title_sha256"] == frame.window_title_sha256
    assert "Synthetic Course Window" not in json.dumps(receipt, sort_keys=True)


def test_frame_artifact_store_retains_content_addressed_png_and_metadata(tmp_path: Path):
    frame = _telemetry_frame()
    store = FrameArtifactStore(tmp_path.resolve())
    observer = LocalGUIObserver(
        _ScreenshotBackend(frame),
        _OCRBackend(),
        artifact_store=store,
        clock=lambda: 123.0,
    )

    first = observer.observe()
    second = observer.observe()

    assert first.frame_artifact is not None
    assert second.frame_artifact == first.frame_artifact
    reference = first.frame_artifact
    png_path = tmp_path / Path(reference.png_relative_path)
    metadata_path = tmp_path / Path(reference.metadata_relative_path)
    assert png_path.read_bytes() == frame.image_bytes
    metadata_bytes = metadata_path.read_bytes()
    assert hashlib.sha256(metadata_bytes).hexdigest() == reference.metadata_sha256
    metadata = json.loads(metadata_bytes)
    assert metadata == {
        "schema_version": "aureon-screenreel-frame-artifact-v1",
        "sha256": hashlib.sha256(frame.image_bytes).hexdigest(),
        "byte_length": len(frame.image_bytes),
        "dimensions": {"width": 100, "height": 50},
        "mime_type": "image/png",
        "png_relative_path": reference.png_relative_path,
    }
    serialized = json.dumps(first.to_dict(), sort_keys=True)
    assert "screenreel-png-payload" not in serialized
    assert str(tmp_path.resolve()) not in serialized
    assert len(list(tmp_path.rglob("*.png"))) == 1
    assert len(list(tmp_path.rglob("*.json"))) == 1


def test_frame_artifact_store_rejects_existing_content_address_with_wrong_bytes(
    tmp_path: Path,
):
    frame = _telemetry_frame()
    store = FrameArtifactStore(tmp_path.resolve())
    digest = hashlib.sha256(frame.image_bytes).hexdigest()
    reference = store.retain(frame, screenshot_sha256=digest)
    target = tmp_path / Path(reference.png_relative_path)
    target.write_bytes(b"tampered")

    with pytest.raises(ObservationError, match="existing_target_mismatch"):
        store.retain(frame, screenshot_sha256=digest)


def test_frame_artifact_store_rejects_relative_or_filesystem_root(tmp_path: Path):
    with pytest.raises(ValueError, match="must be absolute"):
        FrameArtifactStore(Path("relative-run"))
    with pytest.raises(ValueError, match="safe local directory"):
        FrameArtifactStore(Path(tmp_path.anchor))


def test_artifact_store_requires_png_and_hash_match(tmp_path: Path):
    store = FrameArtifactStore(tmp_path.resolve())
    jpeg = CapturedScreen(b"jpeg", 10, 10, mime_type="image/jpeg")
    with pytest.raises(ObservationError, match="requires_png"):
        store.retain(jpeg, screenshot_sha256=hashlib.sha256(jpeg.image_bytes).hexdigest())

    frame = CapturedScreen(b"\x89PNG\r\n\x1a\npng", 10, 10)
    with pytest.raises(ObservationError, match="hash_mismatch"):
        store.retain(frame, screenshot_sha256="0" * 64)
