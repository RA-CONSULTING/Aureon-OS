"""SCORM-player-only stability fingerprint for dynamic media frames.

The raw screenshot SHA remains the action CAS and evidence identity.  This
profile is used only to decide when two observations around a playing course
movie have settled.  It hashes the exact bound window after blanking the
central media surface; the course title, page number, browser chrome, and
outer controls remain in the stability digest.
"""

from __future__ import annotations

import hashlib
import io
import json

from aureon.operator.local_gui_observer import CapturedScreen, ObservationError

STABILITY_SCHEMA_VERSION = "aureon-scorm-player-stability-pixels-v1"
MAX_FRAME_BYTES = 64 * 1024 * 1024
MAX_FRAME_PIXELS = 50_000_000


def dynamic_media_region(
    left: int, top: int, width: int, height: int
) -> tuple[int, int, int, int]:
    """Return the bounded central media region in absolute screen pixels."""

    return (
        left + (width * 1) // 5,
        top + (height * 9) // 50,
        left + (width * 4) // 5,
        top + (height * 7) // 10,
    )


def _decode_rgba(frame: CapturedScreen):
    if len(frame.image_bytes) > MAX_FRAME_BYTES or frame.width * frame.height > MAX_FRAME_PIXELS:
        raise ObservationError("scorm_stability_frame_limit_exceeded")
    if frame.mime_type == "image/png":
        if not frame.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ObservationError("scorm_stability_png_signature_mismatch")
        expected_format = "PNG"
    elif frame.mime_type == "image/jpeg":
        if not frame.image_bytes.startswith(b"\xff\xd8\xff"):
            raise ObservationError("scorm_stability_jpeg_signature_mismatch")
        expected_format = "JPEG"
    else:
        raise ObservationError("scorm_stability_mime_type_unsupported")
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - screen capture already needs Pillow
        raise ObservationError("scorm_stability_pillow_unavailable") from exc
    try:
        with Image.open(io.BytesIO(frame.image_bytes)) as source:
            if source.format != expected_format:
                raise ObservationError("scorm_stability_encoded_format_mismatch")
            if source.size != (frame.width, frame.height):
                raise ObservationError("scorm_stability_dimension_mismatch")
            if int(getattr(source, "n_frames", 1)) != 1:
                raise ObservationError("scorm_stability_multiframe_image_rejected")
            source.load()
            return source.convert("RGBA")
    except ObservationError:
        raise
    except Exception as exc:
        raise ObservationError("scorm_stability_image_decode_failed") from exc


class SCORMPlayerStabilityFingerprint:
    """Hash the bound window with only its central moving-media region blanked."""

    locality = "local"
    profile = STABILITY_SCHEMA_VERSION

    def fingerprint(self, frame: CapturedScreen) -> str:
        if not isinstance(frame, CapturedScreen):
            raise TypeError("frame must be a CapturedScreen")
        rect = frame.window_rect
        if rect is None:
            raise ObservationError("scorm_stability_requires_bound_window")
        right = rect.left + rect.width
        bottom = rect.top + rect.height
        if rect.left < 0 or rect.top < 0 or right > frame.width or bottom > frame.height:
            raise ObservationError("scorm_stability_window_outside_frame")
        image = _decode_rgba(frame).crop((rect.left, rect.top, right, bottom))
        excluded = dynamic_media_region(0, 0, rect.width, rect.height)
        try:
            from PIL import ImageDraw

            ImageDraw.Draw(image).rectangle(excluded, fill=(0, 0, 0, 0))
        except Exception as exc:  # pragma: no cover - Pillow drawing is deterministic
            raise ObservationError("scorm_stability_media_mask_failed") from exc
        header = json.dumps(
            {
                "bound_window": rect.to_dict(),
                "canonical_mode": "RGBA",
                "excluded_media_region": {
                    "bottom": excluded[3],
                    "left": excluded[0],
                    "right": excluded[2],
                    "top": excluded[1],
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
        digest.update(image.tobytes("raw", "RGBA"))
        return digest.hexdigest()


__all__ = [
    "SCORMPlayerStabilityFingerprint",
    "STABILITY_SCHEMA_VERSION",
    "dynamic_media_region",
]
