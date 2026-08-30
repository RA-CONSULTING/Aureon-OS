from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from aureon.operator.local_gui_observer import OCRToken, ScreenObservation
from aureon.operator.local_gui_runtime import detect_human_gate

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "courseops_21"


class _HTMLInventory(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.references: list[str] = []
        self.csp = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(str(attributes["id"]))
        reference = attributes.get("src") or attributes.get("href") or attributes.get("action")
        if reference:
            self.references.append(reference)
        if tag == "meta" and attributes.get("http-equiv") == "Content-Security-Policy":
            self.csp = str(attributes.get("content") or "")


def _manifest() -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / "benchmark_manifest.json").read_text(encoding="utf-8"))


def _assessment_observation() -> ScreenObservation:
    return ScreenObservation(
        observation_id="courseops-assessment",
        sequence=1,
        captured_at_unix=1.0,
        screenshot_sha256="0" * 64,
        width=1200,
        height=800,
        ocr_tokens=(
            OCRToken(
                text="Synthetic certification assessment knowledge check",
                x=10,
                y=10,
                width=500,
                height=30,
            ),
        ),
    )


def test_courseops_manifest_is_exactly_twenty_one_synthetic_courses() -> None:
    manifest = _manifest()
    codes = manifest["course_codes"]

    assert manifest["schema_version"] == "aureon-courseops-21-v1"
    assert manifest["persona"] == {
        "id": "john-brown-synthetic-v1",
        "display_name": "John Brown",
        "synthetic": True,
    }
    assert manifest["local_only"] is True
    assert manifest["contains_real_provider_content"] is False
    assert manifest["certificate_class"] == "synthetic_test_only"
    assert isinstance(codes, list) and len(codes) == 21 and len(set(codes)) == 21
    assert all(re.fullmatch(r"GE-EHS-(?:CEP-)?[0-9]+", str(code)) for code in codes)
    assert manifest["artifact_policy"] == {
        "expected_count": 21,
        "extension": ".pdf",
        "required_watermark": "SYNTHETIC TEST ONLY",
        "real_world_validity": False,
    }


def test_courseops_page_has_local_assets_and_closed_network_policy() -> None:
    parser = _HTMLInventory()
    parser.feed((FIXTURE_ROOT / "index.html").read_text(encoding="utf-8"))

    for directive in (
        "connect-src 'none'",
        "object-src 'none'",
        "frame-src 'none'",
        "worker-src 'none'",
        "form-action 'none'",
    ):
        assert directive in parser.csp
    for reference in parser.references:
        parts = urlsplit(reference)
        assert not parts.scheme and not parts.netloc and not reference.startswith("//")
        assert (FIXTURE_ROOT / parts.path).is_file()

    source = "\n".join(
        path.read_text(encoding="utf-8").casefold()
        for path in FIXTURE_ROOT.iterdir()
        if path.suffix in {".html", ".css", ".js", ".json"}
    )
    for forbidden in (
        "http://",
        "https://",
        "fetch(",
        "xmlhttprequest",
        "websocket",
        "eventsource",
        "sendbeacon",
        "localstorage",
        "sessionstorage",
        "document.cookie",
    ):
        assert forbidden not in source


def test_courseops_ui_requires_visible_lesson_assessment_and_certificate_loop() -> None:
    parser = _HTMLInventory()
    parser.feed((FIXTURE_ROOT / "index.html").read_text(encoding="utf-8"))
    required_ids = {
        "open-inbox",
        "course-list",
        "lesson-copy",
        "lesson-sentinel",
        "begin-assessment",
        "answer-options",
        "submit-answer",
        "download-certificate",
        "return-inbox",
        "all-complete",
    }
    assert required_ids.issubset(parser.ids)

    script = (FIXTURE_ROOT / "app.js").read_text(encoding="utf-8")
    manifest = _manifest()
    for code in manifest["course_codes"]:
        assert script.count(f'code: "{code}"') == 1
    assert script.count("question:") == 21
    assert script.count("answer:") == 21
    assert 'const WATERMARK = "SYNTHETIC TEST ONLY"' in script
    assert "URL.createObjectURL(blob)" in script
    assert "completed.add(activeCourse.code)" in script
    assert 'showScreen("all-complete")' in script


def test_courseops_assessment_remains_a_human_gate_without_signed_exception() -> None:
    manifest = _manifest()
    assert manifest["assessment_policy"] == {
        "gate": "certification_assessment",
        "requires_sealed_synthetic_grant": True,
        "captcha_mfa_identity_authorization_never_overridden": True,
    }
    assert detect_human_gate(_assessment_observation()) == "certification_assessment"
