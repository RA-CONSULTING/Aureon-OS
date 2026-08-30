"""CourseOps-only canonical pixel stability fingerprint.

This local helper deliberately does not replace the raw screenshot SHA used by
ScreenReel evidence, content-addressed artifacts, or the governed desktop CAS.
It supplies only a settling key for the known eight-pixel browser scrollbar
gutter at the right edge of the exact bound window.
"""

from __future__ import annotations

import hashlib
import io
import json

from aureon.operator.local_gui_observer import CapturedScreen, ObservationError

STABILITY_SCHEMA_VERSION = "aureon-courseops-stability-pixels-v1"
RIGHT_SCROLLBAR_GUTTER_PIXELS = 8
MAX_FRAME_BYTES = 64 * 1024 * 1024
MAX_FRAME_PIXELS = 50_000_000


def _decode_rgba(frame: CapturedScreen):
    if len(frame.image_bytes) > MAX_FRAME_BYTES or frame.width * frame.height > MAX_FRAME_PIXELS:
        raise ObservationError("courseops_stability_frame_limit_exceeded")
    expected_format: str
    if frame.mime_type == "image/png":
        if not frame.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ObservationError("courseops_stability_png_signature_mismatch")
        expected_format = "PNG"
    elif frame.mime_type == "image/jpeg":
        if not frame.image_bytes.startswith(b"\xff\xd8\xff"):
            raise ObservationError("courseops_stability_jpeg_signature_mismatch")
        expected_format = "JPEG"
    else:  # CapturedScreen also validates this, but keep the boundary fail-closed.
        raise ObservationError("courseops_stability_mime_type_unsupported")

    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - live screen capture already requires Pillow
        raise ObservationError("courseops_stability_pillow_unavailable") from exc
    try:
        with Image.open(io.BytesIO(frame.image_bytes)) as source:
            if source.format != expected_format:
                raise ObservationError("courseops_stability_encoded_format_mismatch")
            if source.size != (frame.width, frame.height):
                raise ObservationError("courseops_stability_dimension_mismatch")
            if int(getattr(source, "n_frames", 1)) != 1:
                raise ObservationError("courseops_stability_multiframe_image_rejected")
            source.load()
            return source.convert("RGBA")
    except ObservationError:
        raise
    except Exception as exc:
        raise ObservationError("courseops_stability_image_decode_failed") from exc


def _validated_region(frame: CapturedScreen) -> tuple[int, int, int, int]:
    rect = frame.window_rect
    if rect is None:
        raise ObservationError("courseops_stability_requires_bound_window")
    right = rect.left + rect.width
    bottom = rect.top + rect.height
    if rect.left < 0 or rect.top < 0 or right > frame.width or bottom > frame.height:
        raise ObservationError("courseops_stability_window_outside_frame")
    content_right = right - RIGHT_SCROLLBAR_GUTTER_PIXELS
    if content_right <= rect.left:
        raise ObservationError("courseops_stability_window_has_no_content_region")
    return rect.left, rect.top, content_right, bottom


class CourseOps21StabilityFingerprint:
    """Hash canonical RGBA pixels while omitting only the scrollbar gutter."""

    locality = "local"
    profile = STABILITY_SCHEMA_VERSION

    def fingerprint(self, frame: CapturedScreen) -> str:
        if not isinstance(frame, CapturedScreen):
            raise TypeError("frame must be a CapturedScreen")
        image = _decode_rgba(frame)
        left, top, right, bottom = _validated_region(frame)
        rect = frame.window_rect
        assert rect is not None
        header = json.dumps(
            {
                "bound_window": rect.to_dict(),
                "canonical_mode": "RGBA",
                "excluded_right_edge_pixels": RIGHT_SCROLLBAR_GUTTER_PIXELS,
                "hashed_region": {
                    "height": bottom - top,
                    "left": left,
                    "top": top,
                    "width": right - left,
                },
                "schema_version": STABILITY_SCHEMA_VERSION,
                "source_dimensions": {"height": frame.height, "width": frame.width},
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        digest = hashlib.sha256()
        digest.update(header)
        digest.update(b"\n")
        digest.update(image.crop((left, top, right, bottom)).tobytes("raw", "RGBA"))
        return digest.hexdigest()


__all__ = [
    "CourseOps21StabilityFingerprint",
    "RIGHT_SCROLLBAR_GUTTER_PIXELS",
    "STABILITY_SCHEMA_VERSION",
]
