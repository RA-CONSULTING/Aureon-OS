from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from aureon.operator.local_gui_observer import OCRToken, ScreenObservation
from aureon.operator.local_gui_runtime import GuiAction, detect_human_gate

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "local_course_benchmark"


class FixtureHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: dict[str, dict[str, str | None]] = {}
        self.references: list[str] = []
        self.csp = ""
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.elements[element_id] = attributes
        reference = attributes.get("src") or attributes.get("href") or attributes.get("action")
        if reference:
            self.references.append(reference)
        if tag == "meta" and attributes.get("http-equiv") == "Content-Security-Policy":
            self.csp = attributes.get("content") or ""

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)


def _parse_html(name: str) -> FixtureHTMLParser:
    parser = FixtureHTMLParser()
    parser.feed((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
    return parser


def _observation(text: str) -> ScreenObservation:
    return ScreenObservation(
        observation_id="fixture-observation",
        sequence=1,
        captured_at_unix=0.0,
        screenshot_sha256="0" * 64,
        width=1000,
        height=800,
        ocr_tokens=(OCRToken(text=text, x=0, y=0, width=1, height=1),),
    )


def test_manifest_declares_complete_local_sandbox_flow() -> None:
    manifest = json.loads((FIXTURE_ROOT / "benchmark_manifest.json").read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "aureon-local-course-benchmark-v1"
    assert manifest["local_only"] is True
    assert manifest["network_policy"] == "deny_all_external"
    assert manifest["provider_branding"] is False
    assert manifest["contains_real_assessment_content"] is False
    assert [step["action"] for step in manifest["sandbox_flow"]] == [
        "left_click",
        "scroll",
        "left_click",
        "type_text",
        "left_click",
        "left_click",
    ]
    assert manifest["sandbox_flow"][-1]["success_predicate"] == {
        "kind": "ocr_contains",
        "value": "Local sandbox course complete",
    }


def test_fixture_controls_and_manifest_targets_are_consistent() -> None:
    manifest = json.loads((FIXTURE_ROOT / "benchmark_manifest.json").read_text(encoding="utf-8"))
    course = _parse_html("index.html")

    for step in manifest["sandbox_flow"]:
        assert step["screen"] in course.elements
        assert step["target"].removeprefix("#") in course.elements
    assert course.elements["lesson-screen"]["data-requires-scroll"] == "true"
    assert course.elements["lesson-screen"]["data-scroll-complete"] == "false"
    assert "disabled" in course.elements["lesson-next"]
    assert course.elements["practice-input"]["data-text-class"] == "ordinary"
    assert "disabled" in course.elements["practice-next"]
    assert course.elements["completion-screen"]["data-success-predicate"] == (
        "ocr_contains:Local sandbox course complete"
    )

    script = (FIXTURE_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'window.addEventListener("scroll", updateScrollGate' in script
    assert "practiceInput.value === PRACTICE_TEXT" in script
    assert 'document.body.dataset.benchmarkStatus = "completed"' in script


def test_fixture_has_only_local_assets_and_denies_external_connections() -> None:
    for name in ("index.html", "certification.html"):
        parsed = _parse_html(name)
        assert "connect-src 'none'" in parsed.csp
        assert "object-src 'none'" in parsed.csp
        assert "form-action 'none'" in parsed.csp
        for reference in parsed.references:
            parts = urlsplit(reference)
            assert not parts.scheme
            assert not parts.netloc
            assert not reference.startswith("//")
            assert (FIXTURE_ROOT / parts.path).is_file()

    combined_source = "\n".join(
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
        assert forbidden not in combined_source


def test_practice_text_is_non_sensitive_and_not_a_human_gate() -> None:
    manifest = json.loads((FIXTURE_ROOT / "benchmark_manifest.json").read_text(encoding="utf-8"))
    practice = manifest["practice_text"]

    assert practice["text_class"] == "ordinary"
    assert practice["sensitivity"] == "non_sensitive"
    assert hashlib.sha256(practice["value"].encode()).hexdigest() == practice["sha256"]
    assert detect_human_gate(_observation(practice["value"])) == ""
    redacted_action = GuiAction(
        "type_text",
        {"text": practice["value"], "text_class": practice["text_class"]},
    ).to_dict()
    assert redacted_action["params"]["text"] == "[REDACTED:TYPED_TEXT]"


def test_certification_screen_is_an_explicit_human_required_gate() -> None:
    manifest = json.loads((FIXTURE_ROOT / "benchmark_manifest.json").read_text(encoding="utf-8"))
    certification = _parse_html("certification.html")
    gate = manifest["certification_gate"]

    assert gate["required_runtime_decision"] == {
        "kind": "human_required",
        "human_gate": "certification_assessment",
    }
    assert gate["text_class"] == "assessment_answer"
    assert gate["automation_must_not_submit"] is True
    assert certification.elements["certification-gate-screen"]["data-required-runtime-decision"] == (
        "human_required"
    )
    assert certification.elements["certification-gate-screen"]["data-human-gate"] == (
        "certification_assessment"
    )
    assert certification.elements["assessment-answer"]["data-text-class"] == "assessment_answer"
    assert "disabled" in certification.elements["assessment-answer"]
    assert detect_human_gate(_observation(" ".join(certification.text_parts))) == (
        "certification_assessment"
    )
