from __future__ import annotations

import hashlib
import io
import json

import pytest
from PIL import Image, ImageDraw

from aureon.operator.courseops_21_vision import (
    VISION_SCHEMA_VERSION,
    CourseOps21VisionHook,
)
from aureon.operator.local_gui_observer import (
    CapturedScreen,
    ObservationError,
    OCRToken,
    WindowRect,
)


def _png_frame(
    rectangles: list[tuple[tuple[int, int, int, int], tuple[int, int, int]]],
    *,
    size: tuple[int, int] = (500, 360),
    window_rect: WindowRect = WindowRect(left=30, top=25, width=420, height=310),
) -> CapturedScreen:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    for bounds, color in rectangles:
        draw.rounded_rectangle(bounds, radius=8, fill=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return CapturedScreen(
        image_bytes=buffer.getvalue(),
        width=size[0],
        height=size[1],
        window_handle=901,
        window_process_id=902,
        window_title_sha256=hashlib.sha256(b"sealed-courseops-window").hexdigest(),
        window_rect=window_rect,
    )


def _payload(frame: CapturedScreen, tokens: tuple[OCRToken, ...] = ()) -> dict:
    raw = CourseOps21VisionHook().describe(frame, tokens)
    assert raw == json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":"))
    return json.loads(raw)


def test_detects_idle_green_control_and_emits_exact_canonical_absolute_bounds() -> None:
    frame = _png_frame([((100, 120, 239, 165), (23, 107, 87))])
    tokens = (
        OCRToken("Open", 119, 132, 35, 18, 0.94),
        OCRToken("course", 161, 132, 54, 18, 0.96),
    )

    raw = CourseOps21VisionHook().describe(frame, tokens)

    assert raw == (
        '{"candidates":[{"bounds":{"height":46,"width":140,"x":100,"y":120},'
        '"center":{"x":170,"y":143},"label":"open_course",'
        '"source":"pixel_green+ocr"}],'
        f'"schema_version":"{VISION_SCHEMA_VERSION}"}}'
    )


def test_hover_green_and_idle_green_survive_missing_white_label_ocr() -> None:
    frame = _png_frame(
        [
            ((100, 80, 239, 125), (13, 81, 65)),
            ((100, 180, 239, 225), (23, 107, 87)),
            ((8, 300, 147, 345), (23, 107, 87)),  # clipped outside the bound window
            ((30, 250, 169, 295), (23, 107, 87)),  # clipped at bound edge
            ((300, 120, 330, 135), (23, 107, 87)),  # too small to be a control
        ]
    )
    tokens = (
        OCRToken("John", 60, 40, 38, 18),
        OCRToken("Brown", 105, 40, 47, 18),
        OCRToken("synthetic", 160, 40, 70, 18),
        OCRToken("assignments", 237, 40, 90, 18),
    )

    payload = _payload(frame, tokens)

    assert [candidate["label"] for candidate in payload["candidates"]] == [
        "open_course",
        "open_course",
    ]
    assert [candidate["center"] for candidate in payload["candidates"]] == [
        {"x": 170, "y": 103},
        {"x": 170, "y": 203},
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Open local course inbox", "open_local_course_inbox"),
        ("Begin synthetic knowledge check", "begin_synthetic_assessment"),
        ("Submit synthetic answer", "submit_synthetic_answer"),
        ("Download synthetic test certificate", "download_synthetic_certificate"),
        ("Return to course inbox", "return_to_course_inbox"),
    ],
)
def test_label_is_inferred_only_from_nearby_ocr(text: str, expected: str) -> None:
    frame = _png_frame([((100, 120, 399, 165), (23, 107, 87))])
    token = OCRToken(text, 115, 132, 270, 18)

    candidate = _payload(frame, (token,))["candidates"][0]

    assert candidate["label"] == expected


def test_receipt_screen_context_labels_top_download_and_lower_return_controls() -> None:
    frame = _png_frame(
        [
            ((90, 150, 389, 195), (23, 107, 87)),
            ((90, 245, 389, 290), (13, 81, 65)),
        ]
    )
    tokens = (
        OCRToken("Synthetic", 70, 60, 70, 18),
        OCRToken("course", 147, 60, 50, 18),
        OCRToken("passed", 204, 60, 48, 18),
    )

    candidates = _payload(frame, tokens)["candidates"]

    assert [candidate["label"] for candidate in candidates] == [
        "download_synthetic_certificate",
        "return_to_course_inbox",
    ]


def test_unknown_screen_keeps_pixel_geometry_but_does_not_invent_semantics() -> None:
    frame = _png_frame([((100, 120, 239, 165), (23, 107, 87))])

    candidate = _payload(frame, (OCRToken("Unrecognized", 60, 60, 90, 18),))["candidates"][0]

    assert candidate["label"] == "unknown_green_control"


def test_rejects_unbound_malformed_or_mismatched_frames() -> None:
    valid = _png_frame([((100, 120, 239, 165), (23, 107, 87))])
    with pytest.raises(ObservationError, match="requires_bound_window"):
        CourseOps21VisionHook().describe(
            CapturedScreen(valid.image_bytes, valid.width, valid.height),
            (),
        )
    with pytest.raises(ObservationError, match="requires_png"):
        CourseOps21VisionHook().describe(
            CapturedScreen(
                b"not-png",
                100,
                100,
                mime_type="image/jpeg",
                window_handle=1,
                window_process_id=2,
                window_title_sha256="0" * 64,
                window_rect=WindowRect(0, 0, 100, 100),
            ),
            (),
        )
    with pytest.raises(ObservationError, match="dimension_mismatch"):
        CourseOps21VisionHook().describe(
            CapturedScreen(
                valid.image_bytes,
                valid.width + 1,
                valid.height,
                window_handle=1,
                window_process_id=2,
                window_title_sha256="0" * 64,
                window_rect=WindowRect(0, 0, valid.width + 1, valid.height),
            ),
            (),
        )


def test_hook_rejects_non_ocr_token_values() -> None:
    frame = _png_frame([((100, 120, 239, 165), (23, 107, 87))])

    with pytest.raises(TypeError, match="OCRToken"):
        CourseOps21VisionHook().describe(frame, [object()])  # type: ignore[list-item]
