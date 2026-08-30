from __future__ import annotations

import hashlib
import io
import json
import subprocess
from pathlib import Path

import pytest

from aureon.operator.local_gui_local_backends import (
    LocalOllamaPlanner,
    PlannerResponseError,
    PlannerTransportError,
    TesseractCLIBackend,
    UrllibLoopbackTransport,
    discover_tesseract_executable,
)
from aureon.operator.local_gui_observer import (
    CapturedScreen,
    ObservationError,
    OCRToken,
    ScreenObservation,
    WindowRect,
)

TESSERACT_TSV = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t-5\t-2\t20\t15\t95.0\tHello
5\t1\t1\t1\t1\t2\t90\t40\t20\t20\t80.0\tWorld
5\t1\t1\t1\t1\t3\t150\t60\t10\t10\t90.0\tOutside
5\t1\t1\t1\t1\t4\t10\t10\t10\t10\t-1\tIgnored
"""

TESSERACT_TSV_HEADER = (
    "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
    "left\ttop\twidth\theight\tconf\ttext\n"
)


def _fake_executable(tmp_path: Path) -> Path:
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"local test executable placeholder")
    return executable


def test_tesseract_cli_uses_local_executable_without_shell_and_deletes_capture(tmp_path: Path):
    executable = _fake_executable(tmp_path)
    observed: dict[str, object] = {}

    def runner(args, **kwargs):
        capture = Path(args[1])
        observed.update(
            {
                "args": list(args),
                "kwargs": dict(kwargs),
                "capture": capture,
                "capture_bytes": capture.read_bytes(),
            }
        )
        return subprocess.CompletedProcess(args, 0, stdout=TESSERACT_TSV, stderr="")

    frame = CapturedScreen(b"private-screen-capture", width=100, height=50)
    backend = TesseractCLIBackend(
        executable,
        runner=runner,
        temp_directory=tmp_path,
        timeout_seconds=3,
    )

    tokens = backend.recognize(frame)

    assert backend.executable == executable.resolve()
    assert observed["capture_bytes"] == frame.image_bytes
    assert observed["args"] == [
        str(executable.resolve()),
        str(observed["capture"]),
        "stdout",
        "-l",
        "eng",
        "tsv",
    ]
    kwargs = observed["kwargs"]
    assert kwargs["shell"] is False
    assert kwargs["check"] is False
    assert kwargs["timeout"] == 3.0
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["errors"] == "replace"
    assert not Path(observed["capture"]).exists()
    assert [(token.text, token.x, token.y, token.width, token.height) for token in tokens] == [
        ("Hello", 0, 0, 15, 13),
        ("World", 90, 40, 10, 10),
    ]
    assert [token.confidence for token in tokens] == [0.95, 0.8]


def test_tesseract_courseops_multipass_merges_exact_tokens_with_one_total_budget(
    tmp_path: Path,
) -> None:
    executable = _fake_executable(tmp_path)
    calls: list[tuple[list[str], dict[str, object]]] = []
    default_tsv = TESSERACT_TSV_HEADER + (
        "5\t1\t1\t1\t1\t1\t20\t20\t80\t18\t70.0\tCourseOps\n"
        "5\t1\t1\t1\t2\t1\t20\t80\t135\t18\t85.0\tNo answer submitted\n"
    )
    psm6_tsv = TESSERACT_TSV_HEADER + (
        "5\t1\t1\t1\t1\t1\t20\t20\t80\t18\t95.0\tCourseOps\n"
        "5\t1\t1\t1\t3\t1\t40\t180\t210\t20\t91.0\tWhat prevents a fall?\n"
        "5\t1\t1\t1\t4\t1\t60\t240\t180\t20\t89.0\tB. Use guardrails\n"
        "5\t1\t1\t1\t5\t1\t60\t280\t170\t20\t88.0\tC. Ignore the edge\n"
    )
    clock_values = iter((100.0, 101.25))

    def runner(args, **kwargs):
        calls.append((list(args), dict(kwargs)))
        assert Path(args[1]).read_bytes() == b"sealed-local-frame"
        output = default_tsv if "--psm" not in args else psm6_tsv
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    backend = TesseractCLIBackend(
        executable,
        page_segmentation_modes=(None, 6),
        runner=runner,
        temp_directory=tmp_path,
        timeout_seconds=5,
        monotonic_clock=lambda: next(clock_values),
    )

    tokens = backend.recognize(CapturedScreen(b"sealed-local-frame", 800, 600))

    assert len(calls) == 2
    assert calls[0][0][-2:] == ["eng", "tsv"]
    assert calls[1][0][-4:] == ["eng", "--psm", "6", "tsv"]
    assert calls[0][0][1] == calls[1][0][1]
    assert calls[0][1]["timeout"] == 5.0
    assert calls[1][1]["timeout"] == 3.75
    assert all(call[1]["shell"] is False for call in calls)
    assert not Path(calls[0][0][1]).exists()
    assert [token.text for token in tokens] == [
        "CourseOps",
        "No answer submitted",
        "What prevents a fall?",
        "B. Use guardrails",
        "C. Ignore the edge",
    ]
    assert tokens[0].confidence == 0.95


def test_tesseract_multipass_enforces_aggregate_tsv_and_token_limits(tmp_path: Path) -> None:
    executable = _fake_executable(tmp_path)
    one_token_tsv = TESSERACT_TSV_HEADER + (
        "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t90.0\tUnique\n"
    )
    calls = 0

    def runner(args, **kwargs):
        nonlocal calls
        del kwargs
        calls += 1
        return subprocess.CompletedProcess(args, 0, stdout=one_token_tsv, stderr="")

    backend = TesseractCLIBackend(
        executable,
        page_segmentation_modes=(None, 6),
        runner=runner,
        temp_directory=tmp_path,
        max_tsv_bytes=(len(one_token_tsv.encode()) * 2) - 1,
    )
    with pytest.raises(ObservationError, match="TSV output exceeded"):
        backend.recognize(CapturedScreen(b"capture", 100, 100))
    assert calls == 2

    distinct_outputs = iter(
        (
            TESSERACT_TSV_HEADER
            + "5\t1\t1\t1\t1\t1\t10\t10\t20\t10\t90.0\tFirst\n"
            + "5\t1\t1\t1\t1\t2\t40\t10\t20\t10\t90.0\tSecond\n",
            TESSERACT_TSV_HEADER
            + "5\t1\t1\t1\t1\t1\t70\t10\t20\t10\t90.0\tThird\n",
        )
    )
    bounded = TesseractCLIBackend(
        executable,
        page_segmentation_modes=(None, 6),
        runner=lambda args, **_kwargs: subprocess.CompletedProcess(
            args,
            0,
            stdout=next(distinct_outputs),
            stderr="",
        ),
        temp_directory=tmp_path,
        max_tokens=2,
    )
    assert [token.text for token in bounded.recognize(CapturedScreen(b"capture", 100, 100))] == [
        "First",
        "Second",
    ]


def _png_frame_bytes(width: int, height: int) -> bytes:
    from PIL import Image

    image = Image.new("RGB", (width, height))
    for y in range(height):
        for x in range(width):
            image.putpixel((x, y), (x, y, (x + y) % 256))
    output = io.BytesIO()
    image.save(output, format="PNG")
    image.close()
    return output.getvalue()


def _captured_window_frame(
    *,
    image_bytes: bytes,
    width: int,
    height: int,
    rect: WindowRect,
) -> CapturedScreen:
    return CapturedScreen(
        image_bytes,
        width,
        height,
        window_handle=1001,
        window_process_id=4242,
        window_title_sha256=hashlib.sha256(b"sealed-courseops-window").hexdigest(),
        window_rect=rect,
    )


def test_tesseract_bound_window_crop_is_exact_and_offsets_tokens_to_screen(
    tmp_path: Path,
) -> None:
    from PIL import Image

    executable = _fake_executable(tmp_path)
    calls: list[list[str]] = []
    output = TESSERACT_TSV_HEADER + (
        "5\t1\t1\t1\t1\t1\t1\t1\t2\t1\t91.0\tAnswer\n"
        "5\t1\t1\t1\t1\t2\t-2\t0\t3\t1\t82.0\tClipped\n"
        "5\t1\t1\t1\t1\t3\t9\t9\t2\t2\t88.0\tOutside\n"
    )

    def runner(args, **kwargs):
        del kwargs
        calls.append(list(args))
        with Image.open(args[1]) as cropped:
            assert cropped.format == "PNG"
            assert cropped.size == (4, 3)
            assert cropped.getpixel((0, 0)) == (2, 1, 3)
            assert cropped.getpixel((3, 2)) == (5, 3, 8)
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    backend = TesseractCLIBackend(
        executable,
        crop_to_bound_window=True,
        runner=runner,
        temp_directory=tmp_path,
    )
    frame = _captured_window_frame(
        image_bytes=_png_frame_bytes(8, 6),
        width=8,
        height=6,
        rect=WindowRect(left=2, top=1, width=4, height=3),
    )

    tokens = backend.recognize(frame)

    assert len(calls) == 1
    assert calls[0][-2:] == ["eng", "tsv"]
    assert not Path(calls[0][1]).exists()
    assert [(token.text, token.x, token.y, token.width, token.height) for token in tokens] == [
        ("Answer", 3, 2, 2, 1),
        ("Clipped", 2, 1, 1, 1),
    ]


def test_tesseract_bound_window_crop_uses_visible_screen_intersection(
    tmp_path: Path,
) -> None:
    from PIL import Image

    executable = _fake_executable(tmp_path)
    output = TESSERACT_TSV_HEADER + (
        "5\t1\t1\t1\t1\t1\t1\t1\t2\t1\t91.0\tVisible\n"
    )

    def runner(args, **kwargs):
        del kwargs
        with Image.open(args[1]) as cropped:
            assert cropped.size == (7, 5)
            assert cropped.getpixel((0, 0)) == (1, 1, 2)
            assert cropped.getpixel((6, 4)) == (7, 5, 12)
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr="")

    backend = TesseractCLIBackend(
        executable,
        crop_to_bound_window=True,
        runner=runner,
        temp_directory=tmp_path,
    )
    frame = _captured_window_frame(
        image_bytes=_png_frame_bytes(8, 6),
        width=8,
        height=6,
        rect=WindowRect(left=1, top=1, width=9, height=8),
    )

    tokens = backend.recognize(frame)

    assert [(token.text, token.x, token.y, token.width, token.height) for token in tokens] == [
        ("Visible", 2, 2, 2, 1),
    ]


def test_tesseract_bound_window_crop_requires_valid_window_and_decoded_dimensions(
    tmp_path: Path,
) -> None:
    executable = _fake_executable(tmp_path)
    runner_calls = 0

    def runner(args, **kwargs):
        nonlocal runner_calls
        del args, kwargs
        runner_calls += 1
        raise AssertionError("Tesseract must not run for an invalid crop")

    backend = TesseractCLIBackend(
        executable,
        crop_to_bound_window=True,
        runner=runner,
        temp_directory=tmp_path,
    )
    with pytest.raises(ObservationError, match="requires window telemetry"):
        backend.recognize(CapturedScreen(_png_frame_bytes(8, 6), 8, 6))

    outside = _captured_window_frame(
        image_bytes=_png_frame_bytes(8, 6),
        width=8,
        height=6,
        rect=WindowRect(left=-9, top=1, width=4, height=3),
    )
    with pytest.raises(ObservationError, match="outside the captured screen"):
        backend.recognize(outside)

    mismatched = _captured_window_frame(
        image_bytes=_png_frame_bytes(8, 6),
        width=9,
        height=6,
        rect=WindowRect(left=1, top=1, width=4, height=3),
    )
    with pytest.raises(ObservationError, match="decoded dimensions"):
        backend.recognize(mismatched)
    assert runner_calls == 0
    assert not list(tmp_path.glob("aureon_gui_ocr_*"))


def test_tesseract_bound_window_crop_enforces_image_byte_and_pixel_limits(tmp_path: Path) -> None:
    executable = _fake_executable(tmp_path)
    image_bytes = _png_frame_bytes(8, 6)
    frame = _captured_window_frame(
        image_bytes=image_bytes,
        width=8,
        height=6,
        rect=WindowRect(left=1, top=1, width=4, height=3),
    )

    byte_bounded = TesseractCLIBackend(
        executable,
        crop_to_bound_window=True,
        max_image_bytes=len(image_bytes) - 1,
        temp_directory=tmp_path,
    )
    with pytest.raises(ObservationError, match="byte limit"):
        byte_bounded.recognize(frame)

    pixel_bounded = TesseractCLIBackend(
        executable,
        crop_to_bound_window=True,
        max_image_pixels=47,
        temp_directory=tmp_path,
    )
    with pytest.raises(ObservationError, match="pixel limit"):
        pixel_bounded.recognize(frame)
    assert not list(tmp_path.glob("aureon_gui_ocr_*"))


@pytest.mark.parametrize(
    "modes",
    [(), (None, None), (14,), (-1,), (True,), (None, 1, 2, 3, 4)],
)
def test_tesseract_rejects_invalid_multipass_configuration(
    tmp_path: Path,
    modes: tuple[int | None, ...],
) -> None:
    with pytest.raises(ValueError, match="page.segmentation|page segmentation"):
        TesseractCLIBackend(_fake_executable(tmp_path), page_segmentation_modes=modes)


def test_tesseract_timeout_still_securely_deletes_temporary_capture(tmp_path: Path):
    executable = _fake_executable(tmp_path)
    paths: list[Path] = []

    def runner(args, **kwargs):
        del kwargs
        paths.append(Path(args[1]))
        assert paths[-1].exists()
        raise subprocess.TimeoutExpired(args, timeout=1)

    backend = TesseractCLIBackend(
        executable,
        runner=runner,
        temp_directory=tmp_path,
        timeout_seconds=1,
    )
    with pytest.raises(ObservationError, match="timed out"):
        backend.recognize(CapturedScreen(b"capture", 20, 20))
    assert paths and not paths[0].exists()


def test_tesseract_nonzero_or_malformed_output_fails_closed_and_deletes_capture(tmp_path: Path):
    executable = _fake_executable(tmp_path)
    paths: list[Path] = []

    def failing_runner(args, **kwargs):
        del kwargs
        paths.append(Path(args[1]))
        return subprocess.CompletedProcess(args, 2, stdout="", stderr="local OCR failure")

    backend = TesseractCLIBackend(executable, runner=failing_runner, temp_directory=tmp_path)
    with pytest.raises(ObservationError, match="exit code 2"):
        backend.recognize(CapturedScreen(b"capture", 20, 20))
    assert not paths[0].exists()

    def malformed_runner(args, **kwargs):
        del kwargs
        paths.append(Path(args[1]))
        return subprocess.CompletedProcess(args, 0, stdout="wrong\theaders\n", stderr="")

    malformed = TesseractCLIBackend(executable, runner=malformed_runner, temp_directory=tmp_path)
    with pytest.raises(ObservationError, match="malformed TSV headers"):
        malformed.recognize(CapturedScreen(b"capture", 20, 20))
    assert not paths[-1].exists()


def test_tesseract_discovery_accepts_path_result_and_rejects_remote_locations(tmp_path: Path):
    executable = _fake_executable(tmp_path)
    discovered = discover_tesseract_executable(
        which=lambda command: str(executable) if command == "tesseract" else None,
        environ={},
    )
    assert discovered == executable.resolve()

    for remote in (
        "https://example.invalid/tesseract.exe",
        "file:///remote/tesseract.exe",
        r"\\server\share\tesseract.exe",
    ):
        with pytest.raises(ValueError, match="local filesystem"):
            discover_tesseract_executable(remote)

    with pytest.raises(ValueError, match="temp_directory must be a local"):
        TesseractCLIBackend(executable, temp_directory=r"\\server\capture-share")


def test_tesseract_discovery_normalizes_windows_environment_key_casing(tmp_path: Path):
    install = tmp_path / "Tesseract-OCR"
    install.mkdir()
    executable = _fake_executable(install)

    discovered = discover_tesseract_executable(
        which=lambda _command: None,
        environ={"PROGRAMFILES": str(tmp_path)},
    )

    assert discovered == executable.resolve()


@pytest.mark.parametrize("timeout_seconds", [float("nan"), float("inf"), float("-inf")])
def test_tesseract_requires_a_finite_timeout(tmp_path: Path, timeout_seconds: float):
    with pytest.raises(ValueError, match="timeout_seconds"):
        TesseractCLIBackend(
            _fake_executable(tmp_path),
            timeout_seconds=timeout_seconds,
        )


def _observation(text: str = "Course home", vision: str = "") -> ScreenObservation:
    return ScreenObservation(
        observation_id=hashlib.sha256(f"observation:{text}:{vision}".encode()).hexdigest(),
        sequence=1,
        captured_at_unix=1.0,
        screenshot_sha256=hashlib.sha256(b"screenshot-bytes-never-sent").hexdigest(),
        width=1280,
        height=720,
        ocr_tokens=(OCRToken(text, 10, 10, 300, 20, 0.99),),
        vision_text=vision,
    )


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls: list[dict[str, object]] = []

    def post_json(self, url, payload, *, timeout_seconds):
        self.calls.append(
            {"url": url, "payload": payload, "timeout_seconds": timeout_seconds}
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _ollama_response(decision: object) -> dict[str, object]:
    return {"message": {"role": "assistant", "content": json.dumps(decision)}}


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://127.0.0.1:11434",
        "http://localhost:11434/",
        "http://[::1]:11434",
    ],
)
def test_local_ollama_planner_accepts_only_declared_loopback_http_endpoints(endpoint: str):
    planner = LocalOllamaPlanner(
        model="local-vision-model",
        endpoint=endpoint,
        transport=FakeTransport(_ollama_response({"kind": "abort", "reason": "done"})),
    )
    assert planner.locality == "local"
    assert planner.chat_url.endswith("/api/chat")


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://127.0.0.1:11434",
        "http://192.168.1.5:11434",
        "http://0.0.0.0:11434",
        "http://127.0.0.1.evil.invalid:11434",
        "http://user:pass@localhost:11434",
        "http://localhost:11434/v1",
        "http://localhost:11434?redirect=evil",
    ],
)
def test_local_ollama_planner_rejects_remote_or_ambiguous_endpoints(endpoint: str):
    with pytest.raises(ValueError, match="Ollama planner endpoint"):
        LocalOllamaPlanner(model="local-model", endpoint=endpoint, transport=FakeTransport({}))


@pytest.mark.parametrize("timeout_seconds", [float("nan"), float("inf"), float("-inf")])
def test_local_ollama_planner_requires_a_finite_timeout(timeout_seconds: float):
    with pytest.raises(ValueError, match="timeout_seconds"):
        LocalOllamaPlanner(
            model="local-model",
            timeout_seconds=timeout_seconds,
            transport=FakeTransport({}),
        )


def test_default_urllib_transport_rejects_remote_url_before_opening_network():
    transport = UrllibLoopbackTransport()
    with pytest.raises(PlannerTransportError, match="not a loopback"):
        transport.post_json(
            "http://example.invalid/api/chat",
            {"model": "local-model"},
            timeout_seconds=1,
        )


def test_local_ollama_planner_posts_strict_json_to_native_chat_without_screenshot_bytes():
    response = _ollama_response(
        {
            "kind": "action",
            "reason": "Click the visible Continue button",
            "action": {"name": "left_click", "params": {"x": 220, "y": 180}},
            "expected": {"kind": "screen_changed", "value": ""},
        }
    )
    transport = FakeTransport(response)
    planner = LocalOllamaPlanner(
        model="local-model",
        endpoint="http://127.0.0.1:11434",
        transport=transport,
        timeout_seconds=7,
    )

    decision = planner.plan("Open the authorized sandbox module", _observation(), [])

    assert decision.kind == "action"
    assert decision.action is not None and decision.action.name == "left_click"
    assert decision.action.params == {"x": 220, "y": 180}
    assert decision.expected is not None and decision.expected.kind == "screen_changed"
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["url"] == "http://127.0.0.1:11434/api/chat"
    assert call["timeout_seconds"] == 7.0
    payload = call["payload"]
    assert payload["stream"] is False
    assert payload["format"] == "json"
    serialized = json.dumps(payload)
    assert "screenshot-bytes-never-sent" not in serialized
    assert _observation().screenshot_sha256 in serialized


def test_local_ollama_planner_bounds_ocr_tokens_and_observation_text_consistently():
    response = _ollama_response({"kind": "abort", "reason": "bounded input verified"})
    transport = FakeTransport(response)
    planner = LocalOllamaPlanner(
        model="local-model",
        transport=transport,
        max_ocr_tokens=1,
        max_observation_text_chars=10,
    )
    observation = ScreenObservation(
        observation_id="bounded-observation",
        sequence=1,
        captured_at_unix=1.0,
        screenshot_sha256=hashlib.sha256(b"bounded-screen").hexdigest(),
        width=1280,
        height=720,
        ocr_tokens=(
            OCRToken("abcdefghijk", 10, 10, 100, 20, 0.99),
            OCRToken("must-not-be-sent", 10, 40, 100, 20, 0.99),
        ),
        vision_text="0123456789vision-tail-must-not-be-sent",
    )

    planner.plan("bounded course benchmark", observation, [])

    request = transport.calls[0]["payload"]
    user_payload = json.loads(request["messages"][1]["content"])
    sent_observation = user_payload["observation"]
    assert sent_observation["ocr_tokens"] == [
        {
            "text": "abcdefghij",
            "box": {"x": 10, "y": 10, "width": 100, "height": 20},
            "confidence": 0.99,
        }
    ]
    assert sent_observation["ocr_text"] == "abcdefghij"
    assert sent_observation["local_vision_text"] == "0123456789"
    assert "must-not-be-sent" not in request["messages"][1]["content"]


def test_local_ollama_planner_parses_exact_completion_and_human_required_schemas():
    completion_transport = FakeTransport(
        _ollama_response(
            {
                "kind": "complete",
                "reason": "Visible provider marker",
                "success_predicate": {"kind": "ocr_contains", "value": "Module complete"},
            }
        )
    )
    completion = LocalOllamaPlanner(
        model="local-model",
        transport=completion_transport,
    ).plan("authorized module", _observation("Module complete"), [])
    assert completion.kind == "complete"
    assert completion.success_predicate is not None
    assert completion.success_predicate.value == "Module complete"

    human = LocalOllamaPlanner(
        model="local-model",
        transport=FakeTransport(
            _ollama_response(
                {
                    "kind": "human_required",
                    "reason": "This is a certification assessment",
                    "human_gate": "certification_assessment",
                }
            )
        ),
    ).plan("authorized module", _observation(), [])
    assert human.kind == "human_required"
    assert human.human_gate == "certification_assessment"


def test_local_planner_converts_proposed_assessment_answer_typing_to_human_required():
    transport = FakeTransport(
        _ollama_response(
            {
                "kind": "action",
                "reason": "Unsafe model proposal",
                "action": {
                    "name": "type_text",
                    "params": {
                        "text": "an assessment answer",
                        "text_class": "assessment_answer",
                    },
                },
                "expected": {"kind": "screen_changed", "value": ""},
            }
        )
    )
    decision = LocalOllamaPlanner(model="local-model", transport=transport).plan(
        "course benchmark",
        _observation("Course page"),
        [],
    )
    assert decision.kind == "human_required"
    assert decision.human_gate == "certification_assessment"


def test_local_planner_allows_only_independently_authorized_synthetic_assessment():
    transport = FakeTransport(
        _ollama_response(
            {
                "kind": "action",
                "reason": "Select the answer supported by the visible synthetic lesson",
                "action": {"name": "left_click", "params": {"x": 220, "y": 180}},
                "expected": {"kind": "screen_changed", "value": ""},
            }
        )
    )
    calls: list[str] = []

    def authorize(_observation, action):
        calls.append("observation" if action is None else action.name)
        return True

    planner = LocalOllamaPlanner(
        model="local-model",
        transport=transport,
        synthetic_assessment_authorizer=authorize,
    )
    decision = planner.plan(
        "Complete the sealed synthetic benchmark",
        _observation("Synthetic certification assessment knowledge check"),
        [],
    )

    assert decision.kind == "action"
    assert decision.action is not None and decision.action.name == "left_click"
    assert calls == ["observation", "left_click"]
    request = transport.calls[0]["payload"]
    assert request["messages"][1]["content"]
    assert json.loads(request["messages"][1]["content"])[
        "sealed_synthetic_assessment_authorized"
    ] is True
    system_prompt = request["messages"][0]["content"]
    assert "SEALED SYNTHETIC BENCHMARK EXCEPTION" in system_prompt
    assert "never applies to a" in system_prompt
    assert "real provider" in system_prompt


@pytest.mark.parametrize(
    ("screen_text", "gate"),
    [
        ("Please complete this CAPTCHA", "captcha"),
        ("Enter your authenticator verification code", "mfa"),
        ("Confirm your identity before proceeding", "identity_attestation"),
        ("Certification exam knowledge check", "certification_assessment"),
        ("Choose an assessment answer", "certification_assessment"),
    ],
)
def test_local_planner_preflight_stops_human_gates_without_transport(screen_text: str, gate: str):
    transport = FakeTransport(AssertionError("transport must not run"))
    planner = LocalOllamaPlanner(model="local-model", transport=transport)

    decision = planner.plan("course benchmark", _observation(screen_text), [])

    assert decision.kind == "human_required"
    assert decision.human_gate == gate
    assert transport.calls == []


def test_local_planner_prompt_requires_assessment_screens_to_be_human_required():
    transport = FakeTransport(_ollama_response({"kind": "abort", "reason": "safe stop"}))
    planner = LocalOllamaPlanner(model="local-model", transport=transport)
    planner.plan("course benchmark", _observation("Course landing page"), [])

    payload = transport.calls[0]["payload"]
    system_prompt = payload["messages"][0]["content"].casefold()
    for phrase in (
        "captcha",
        "mfa",
        "identity",
        "certification quiz",
        "certification exam",
        "knowledge check",
        "assessment-answer",
        "human_required",
        "duration",
        "0 through 2",
        "text_class",
        "ordinary|personal_data|credential|assessment_answer",
        "0 through 0.5",
        "nonzero integer from -20 through 20",
        "screen_changed",
        "ocr_absent",
        "f1 through f24",
    ):
        assert phrase in system_prompt


@pytest.mark.parametrize(
    "response",
    [
        [],
        {},
        {"message": {"content": "```json\n{}\n```"}},
        _ollama_response({"kind": "abort", "reason": "stop", "extra": True}),
        _ollama_response(
            {
                "kind": "action",
                "reason": "invent a coordinate",
                "action": {"name": "left_click", "params": {"x": 1}},
                "expected": {"kind": "screen_changed", "value": ""},
            }
        ),
        _ollama_response(
            {
                "kind": "action",
                "reason": "coordinate is outside the observation",
                "action": {"name": "left_click", "params": {"x": 5000, "y": 10}},
                "expected": {"kind": "screen_changed", "value": ""},
            }
        ),
        _ollama_response(
            {
                "kind": "action",
                "reason": "remote navigation is not allowlisted",
                "action": {"name": "open_url", "params": {"url": "https://example.invalid"}},
                "expected": {"kind": "screen_changed", "value": ""},
            }
        ),
        _ollama_response(
            {
                "kind": "human_required",
                "reason": "unknown gate",
                "human_gate": "remote_operator",
            }
        ),
    ],
)
def test_local_ollama_planner_fails_closed_on_malformed_or_out_of_schema_response(response):
    planner = LocalOllamaPlanner(model="local-model", transport=FakeTransport(response))
    with pytest.raises(PlannerResponseError):
        planner.plan("course benchmark", _observation(), [])


def test_local_ollama_planner_rejects_duplicate_json_keys():
    response = {
        "message": {
            "content": '{"kind":"abort","kind":"complete","reason":"ambiguous"}'
        }
    }
    planner = LocalOllamaPlanner(model="local-model", transport=FakeTransport(response))
    with pytest.raises(PlannerResponseError, match="strict JSON"):
        planner.plan("course benchmark", _observation(), [])


def test_local_ollama_planner_wraps_transport_failure_without_remote_fallback():
    planner = LocalOllamaPlanner(
        model="local-model",
        transport=FakeTransport(OSError("local service unavailable")),
    )
    with pytest.raises(PlannerTransportError, match="OSError"):
        planner.plan("course benchmark", _observation(), [])
