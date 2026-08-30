"""Bounded local pixel grounding for the sealed CourseOps-21 benchmark.

The hook consumes only the in-memory, target-window-masked frame and OCR boxes
already present in the observation pipeline.  It never reads the fixture,
filesystem, DOM, browser state, or network.  Pixels establish the control
geometry; OCR may attach one of a small set of semantic control labels.
"""

from __future__ import annotations

import io
import json
import re
from collections import deque
from dataclasses import dataclass
from typing import Sequence

from aureon.operator.local_gui_observer import CapturedScreen, ObservationError, OCRToken

VISION_SCHEMA_VERSION = "aureon-courseops-vision-v1"
VISION_SOURCE = "pixel_green+ocr"
MAX_CANDIDATES = 64
MAX_FRAME_BYTES = 64 * 1024 * 1024
MAX_FRAME_PIXELS = 16_777_216

_WORD = re.compile(r"[a-z0-9]+")
_LABEL_PHRASES = (
    ("open local course inbox", "open_local_course_inbox"),
    ("open course inbox", "open_local_course_inbox"),
    ("begin synthetic knowledge check", "begin_synthetic_assessment"),
    ("begin knowledge check", "begin_synthetic_assessment"),
    ("download synthetic test certificate", "download_synthetic_certificate"),
    ("download test certificate", "download_synthetic_certificate"),
    ("return to course inbox", "return_to_course_inbox"),
    ("return to inbox", "return_to_course_inbox"),
    ("submit synthetic answer", "submit_synthetic_answer"),
    ("submit answer", "submit_synthetic_answer"),
    ("open course", "open_course"),
)


@dataclass(frozen=True)
class _Bounds:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2


def _normalized(value: str) -> str:
    return " ".join(_WORD.findall(value.casefold()))


def _is_control_green(red: int, green: int, blue: int) -> bool:
    """Select moderately dark green/teal fills, including hover variants.

    Relative-channel constraints are intentional: they cover both the idle and
    hover fills without binding the detector to one exact fixture RGB value.
    Geometry and density gates below reject small green text and decoration.
    """

    return (
        45 <= green <= 180
        and red <= 115
        and green - red >= 24
        and green - blue >= 4
        and blue - red >= 12
    )


def _window_crop(frame: CapturedScreen) -> tuple[int, int, int, int]:
    rect = frame.window_rect
    if rect is None:
        raise ObservationError("courseops_vision_requires_bound_window")
    left = max(0, rect.left)
    top = max(0, rect.top)
    right = min(frame.width, rect.left + rect.width)
    bottom = min(frame.height, rect.top + rect.height)
    if left >= right or top >= bottom:
        raise ObservationError("courseops_vision_window_outside_frame")
    return left, top, right, bottom


def _load_rgb(frame: CapturedScreen):
    if frame.mime_type != "image/png" or not frame.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ObservationError("courseops_vision_requires_png")
    if len(frame.image_bytes) > MAX_FRAME_BYTES or frame.width * frame.height > MAX_FRAME_PIXELS:
        raise ObservationError("courseops_vision_frame_limit_exceeded")
    try:
        from PIL import Image
    except Exception as exc:  # pragma: no cover - GUI capture already requires Pillow
        raise ObservationError("courseops_vision_pillow_unavailable") from exc
    try:
        with Image.open(io.BytesIO(frame.image_bytes)) as source:
            source.load()
            if source.size != (frame.width, frame.height):
                raise ObservationError("courseops_vision_dimension_mismatch")
            return source.convert("RGB")
    except ObservationError:
        raise
    except Exception as exc:
        raise ObservationError("courseops_vision_invalid_png") from exc


def _connected_control_bounds(frame: CapturedScreen) -> tuple[_Bounds, ...]:
    image = _load_rgb(frame)
    left, top, right, bottom = _window_crop(frame)
    crop = image.crop((left, top, right, bottom))
    crop_width, crop_height = crop.size
    mask = bytearray(
        _is_control_green(red, green, blue)
        for red, green, blue in crop.getdata()
    )

    components: list[_Bounds] = []
    for origin in range(len(mask)):
        if not mask[origin]:
            continue
        mask[origin] = 0
        queue: deque[int] = deque((origin,))
        origin_y, origin_x = divmod(origin, crop_width)
        min_x = max_x = origin_x
        min_y = max_y = origin_y
        pixels = 0
        while queue:
            index = queue.popleft()
            y, x = divmod(index, crop_width)
            pixels += 1
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            if x and mask[index - 1]:
                mask[index - 1] = 0
                queue.append(index - 1)
            if x + 1 < crop_width and mask[index + 1]:
                mask[index + 1] = 0
                queue.append(index + 1)
            if y and mask[index - crop_width]:
                mask[index - crop_width] = 0
                queue.append(index - crop_width)
            if y + 1 < crop_height and mask[index + crop_width]:
                mask[index + crop_width] = 0
                queue.append(index + crop_width)

        width = max_x - min_x + 1
        height = max_y - min_y + 1
        bounding_area = width * height
        clipped = (
            min_x == 0
            or min_y == 0
            or max_x == crop_width - 1
            or max_y == crop_height - 1
        )
        if (
            clipped
            or width < 64
            or width > min(720, crop_width - 2)
            or height < 30
            or height > min(120, crop_height - 2)
            or bounding_area < 1_000
            or pixels * 100 < bounding_area * 58
        ):
            continue
        components.append(_Bounds(left + min_x, top + min_y, width, height))

    return tuple(sorted(components, key=lambda item: (item.y, item.x))[:MAX_CANDIDATES])


def _token_near_bounds(token: OCRToken, bounds: _Bounds) -> bool:
    token_center_x = token.x + token.width // 2
    token_center_y = token.y + token.height // 2
    return (
        bounds.x - 12 <= token_center_x < bounds.right + 12
        and bounds.y - 8 <= token_center_y < bounds.bottom + 8
    )


def _label_from_text(value: str) -> str | None:
    normalized = _normalized(value)
    for phrase, label in _LABEL_PHRASES:
        if phrase in normalized:
            return label
    return None


def _screen_labels(
    bounds: Sequence[_Bounds],
    tokens: Sequence[OCRToken],
) -> tuple[str, ...]:
    screen_text = _normalized(" ".join(token.text for token in tokens if token.text))
    labels: list[str | None] = []
    for candidate in bounds:
        nearby = sorted(
            (token for token in tokens if token.text and _token_near_bounds(token, candidate)),
            key=lambda token: (token.y, token.x, token.text.casefold()),
        )
        labels.append(_label_from_text(" ".join(token.text for token in nearby)))

    for index, label in enumerate(labels):
        if label is not None:
            continue
        inferred = "unknown_green_control"
        if (
            "assignment handoff" in screen_text
            or "local safety courses are ready" in screen_text
        ) and len(bounds) == 1:
            inferred = "open_local_course_inbox"
        elif "assigned courses" in screen_text or "synthetic assignments" in screen_text:
            inferred = "open_course"
        elif "end of synthetic lesson" in screen_text or "read the full lesson" in screen_text:
            inferred = "begin_synthetic_assessment"
        elif "synthetic certification assessment" in screen_text or "choose the best answer" in screen_text:
            inferred = "submit_synthetic_answer"
        elif "synthetic course passed" in screen_text or "visible answer matched" in screen_text:
            if (len(bounds) > 1 and index == len(bounds) - 1) or (
                "certificate downloaded" in screen_text and len(bounds) == 1
            ):
                inferred = "return_to_course_inbox"
            else:
                inferred = "download_synthetic_certificate"
        labels[index] = inferred
    return tuple(str(label) for label in labels)


class CourseOps21VisionHook:
    """Describe green control regions from in-memory pixels only."""

    locality = "local"

    def describe(self, frame: CapturedScreen, tokens: Sequence[OCRToken]) -> str:
        if not isinstance(frame, CapturedScreen):
            raise TypeError("frame must be a CapturedScreen")
        if not isinstance(tokens, Sequence) or not all(isinstance(token, OCRToken) for token in tokens):
            raise TypeError("tokens must contain OCRToken instances")
        bounds = _connected_control_bounds(frame)
        labels = _screen_labels(bounds, tokens)
        candidates = [
            {
                "bounds": {
                    "height": candidate.height,
                    "width": candidate.width,
                    "x": candidate.x,
                    "y": candidate.y,
                },
                "center": {"x": candidate.center_x, "y": candidate.center_y},
                "label": label,
                "source": VISION_SOURCE,
            }
            for candidate, label in zip(bounds, labels, strict=True)
        ]
        return json.dumps(
            {"candidates": candidates, "schema_version": VISION_SCHEMA_VERSION},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )


__all__ = [
    "CourseOps21VisionHook",
    "MAX_CANDIDATES",
    "VISION_SCHEMA_VERSION",
    "VISION_SOURCE",
]
