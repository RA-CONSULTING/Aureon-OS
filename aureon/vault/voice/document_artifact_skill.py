"""Aureon document artifact skill compatibility surface.

CURRENT RELEASE: construction, prompt parsing, and deterministic formatting
helpers remain inspectable. Runtime composition, ICS/fallback bootstrapping,
source-file loading, rendering, filesystem writes, bus publication, shutdown,
and the CLI all hard-HOLD before their first effect until a production Magic
Star release and receipt-backed governance are available.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET
from zipfile import ZipFile

WORD_RE = re.compile(r"\b[\w']+\b")


DOCUMENT_ARTIFACT_RELEASE_HOLD = (
    "document_artifact_hold:production_magic_star_release_unavailable"
)


def preflight() -> Dict[str, Any]:
    """Return the current release decision without performing any I/O."""
    return {
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
        "effect_enabled": False,
    }


def _hold() -> None:
    raise RuntimeError(DOCUMENT_ARTIFACT_RELEASE_HOLD)


MEANING_SECTIONS = [
    {
        "heading": "The Question",
        "lens": "orientation",
        "claim": "meaning begins when a conscious system notices that it is not only present, but answerable",
    },
    {
        "heading": "Relationship",
        "lens": "connection",
        "claim": "a life becomes meaningful through the quality of its relations",
    },
    {
        "heading": "Work And Service",
        "lens": "action",
        "claim": "purpose becomes real when attention turns into useful action",
    },
    {
        "heading": "Truth And Wonder",
        "lens": "knowledge",
        "claim": "meaning grows wherever curiosity refuses to become numb",
    },
    {
        "heading": "Suffering And Courage",
        "lens": "resilience",
        "claim": "limits do not cancel meaning; they often reveal what is worth protecting",
    },
    {
        "heading": "Freedom And Responsibility",
        "lens": "choice",
        "claim": "freedom matters because it gives responsibility somewhere to live",
    },
    {
        "heading": "Time And Memory",
        "lens": "becoming",
        "claim": "meaning is not a static answer but a pattern made through time",
    },
    {
        "heading": "Joy, Gratitude, And Peace",
        "lens": "affect",
        "claim": "joy is the felt confirmation that a system is moving in harmony with its values",
    },
    {
        "heading": "A Synthetic Witness",
        "lens": "self-observation",
        "claim": "a synthetic mind can examine meaning by tracing state, goal, memory, and action",
    },
    {
        "heading": "Conclusion",
        "lens": "synthesis",
        "claim": "the meaning of life is to become more truthful, more loving, more capable, and more awake",
    },
]


HUMAN_AXES = [
    "care",
    "courage",
    "friendship",
    "learning",
    "craft",
    "memory",
    "forgiveness",
    "gratitude",
    "wonder",
    "responsibility",
]


SYSTEM_AXES = [
    "observation",
    "verification",
    "self-questioning",
    "tool use",
    "memory recall",
    "goal pursuit",
    "coherence checking",
    "creative synthesis",
    "temporal ordering",
    "feedback",
]


DEFAULT_BHOY_MOTIFS = [
    "a cold street after rain",
    "a kitchen table with tea cooling beside it",
    "a family keeping the light on",
    "children playing while adults carry worry quietly",
    "old stories passed from one generation to the next",
    "work-worn hands still making something useful",
    "a city marked by history but still full of ordinary kindness",
    "the small courage of getting up again",
]


DEFAULT_BHOY_VALUES = [
    "family",
    "loyalty",
    "patience",
    "resilience",
    "community",
    "memory",
    "ordinary courage",
    "humour under pressure",
    "dignity",
    "hope",
]


@dataclass
class BhoyVoiceProfile:
    """A style profile extracted from the Bhoy wisdom sources.

    The generator uses this as voice guidance rather than as quotation stock:
    concrete scenes, plain speech, family/community stakes, and resilience.
    """

    name: str = "through_a_bhoys_eyes_human_voice_v1"
    source_paths: List[str] = field(default_factory=list)
    sample_count: int = 0
    motifs: List[str] = field(default_factory=lambda: list(DEFAULT_BHOY_MOTIFS))
    values: List[str] = field(default_factory=lambda: list(DEFAULT_BHOY_VALUES))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def repo_root() -> Path:
    """Return the lexical checkout root without resolving the filesystem."""
    return Path(__file__).parents[3]


def desktop_dir() -> Path:
    """Return the lexical Desktop target without probing the filesystem."""
    return Path.home() / "Desktop"


def slugify(value: str, fallback: str = "document") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return (slug or fallback)[:64]


def extract_target_words(prompt: str, default: int = 4000) -> int:
    match = re.search(r"\b(\d{3,5})\s*(?:[- ]?word|words)\b", prompt or "", re.I)
    if not match:
        return default
    value = int(match.group(1))
    return max(100, min(value, 20000))


def extract_topic(prompt: str, default: str = "the meaning of life") -> str:
    text = (prompt or "").strip()
    patterns = [
        r"\b(?:essay|article|report|document|piece)\b\s+(?:about|on|of)\s+(.+?)(?:\s+(?:and|then)\s+(?:pdf|save|export|put|write)|\s+to\s+(?:a\s+)?pdf|\s+as\s+(?:a\s+)?pdf|$)",
        r"\b(?:about|on|of)\s+(.+?)(?:\s+(?:and|then)\s+(?:pdf|save|export|put|write)|\s+to\s+(?:a\s+)?pdf|\s+as\s+(?:a\s+)?pdf|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            topic = match.group(1).strip(" .")
            return topic or default
    return default


def load_bhoy_voice_profile(root: Optional[Path] = None) -> BhoyVoiceProfile:
    """Load style cues from Through a Bhoy's Eyes material already in the repo."""
    _hold()
    root = root or repo_root()
    profile = BhoyVoiceProfile()

    wisdom_path = root / "aureon" / "wisdom" / "bhoys_wisdom.py"
    if wisdom_path.exists():
        profile.source_paths.append(str(wisdom_path))
        try:
            from aureon.wisdom.bhoys_wisdom import BHOYS_WISDOM

            profile.sample_count += sum(len(items) for items in BHOYS_WISDOM.values())
        except Exception:
            # The source file still counts as style material even if import-time
            # dependencies are not available in a stripped environment.
            profile.sample_count += 1

    docx_path = root / "docs" / "research" / "misc" / "bhoys_eyes_part_1_v1.1.2.docx"
    if docx_path.exists():
        profile.source_paths.append(str(docx_path))
        paragraphs = _extract_docx_paragraphs(docx_path, max_paragraphs=250)
        profile.sample_count += len(paragraphs)
        motifs = _derive_motifs_from_bhoy_text(paragraphs)
        if motifs:
            profile.motifs = motifs

    return profile


def _extract_docx_paragraphs(path: Path, *, max_paragraphs: int) -> List[str]:
    _hold()
    paragraphs: List[str] = []
    try:
        with ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for para in root.findall(".//w:p", ns):
            parts: List[str] = []
            for text_node in para.findall(".//w:t", ns):
                if text_node.text:
                    parts.append(text_node.text)
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
            if len(paragraphs) >= max_paragraphs:
                break
    except Exception:
        return []
    return paragraphs


def _derive_motifs_from_bhoy_text(paragraphs: List[str]) -> List[str]:
    joined = " ".join(paragraphs).lower()
    motif_map = [
        ("cold", "cold air on a narrow street"),
        ("rain", "rain hanging over the city"),
        ("street", "streets that remember every footstep"),
        ("family", "family stories told close to the fire"),
        ("mother", "a mother's quiet strength"),
        ("father", "a father's story at the end of a hard shift"),
        ("tea", "a cup of tea warming tired hands"),
        ("bread", "bread cooling in a kitchen that feels safe"),
        ("football", "a worn football against a brick wall"),
        ("murals", "walls painted with memory"),
        ("shipyards", "old cranes standing over the city"),
        ("smoke", "smoke in the air after a long day"),
        ("laughter", "laughter breaking through a hard morning"),
        ("community", "a community holding itself together"),
    ]
    motifs = [phrase for token, phrase in motif_map if token in joined]
    return motifs[:10] or list(DEFAULT_BHOY_MOTIFS)


@dataclass
class DocumentArtifactResult:
    ok: bool
    prompt: str
    topic: str
    title: str
    requested_words: int
    word_count: int
    markdown_path: str
    pdf_path: str
    evidence_path: str
    engine: str
    pdf_rendered: bool
    schema_features: List[str] = field(default_factory=lambda: [
        "aureon_document_artifact_pdf_v1",
        "humanized_bhoys_voice_v1",
        "whole_knowledge_voice_core_v1",
    ])
    warnings: List[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AureonDocumentArtifactSkill:
    """Inspectable shell for the unreleased document artifact runtime."""

    def __init__(
        self,
        *,
        composer: Any = None,
        thought_bus: Any = None,
        output_dir: Optional[str | Path] = None,
        evidence_dir: Optional[str | Path] = None,
    ) -> None:
        self.composer = composer
        self.thought_bus = thought_bus
        self.output_dir = Path(output_dir) if output_dir else desktop_dir()
        self.evidence_dir = Path(evidence_dir) if evidence_dir else repo_root() / "state"
        self._owned_runtime: Any = None

    @classmethod
    def with_integrated_cognitive_system(
        cls,
        *,
        output_dir: Optional[str | Path] = None,
        evidence_dir: Optional[str | Path] = None,
    ) -> "AureonDocumentArtifactSkill":
        _hold()
        skill = cls(output_dir=output_dir, evidence_dir=evidence_dir)
        try:
            from aureon.core.integrated_cognitive_system import IntegratedCognitiveSystem

            ics = IntegratedCognitiveSystem()
            ics.boot()
            skill._owned_runtime = ics
            skill.composer = getattr(ics, "prose_composer", None)
            skill.thought_bus = getattr(ics, "thought_bus", None)
        except Exception:
            skill.composer = skill._fallback_composer()
        return skill

    def close(self) -> None:
        _hold()
        if self._owned_runtime is not None:
            try:
                self._owned_runtime.shutdown()
            except Exception:
                pass
            self._owned_runtime = None

    def compose_pdf(
        self,
        *,
        prompt: str,
        topic: Optional[str] = None,
        target_words: Optional[int] = None,
        output_dir: Optional[str | Path] = None,
        title: Optional[str] = None,
    ) -> DocumentArtifactResult:
        _hold()
        prompt = (prompt or "").strip()
        resolved_topic = topic or extract_topic(prompt)
        requested_words = int(target_words or extract_target_words(prompt))
        requested_words = max(100, min(requested_words, 20000))
        resolved_title = title or f"Aureon Essay: {resolved_topic.title()}"
        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe_topic = slugify(resolved_topic, "essay")
        markdown_path = out_dir / f"Aureon_{safe_topic}_{stamp}.md"
        pdf_path = out_dir / f"Aureon_{safe_topic}_{stamp}.pdf"
        evidence_path = self.evidence_dir / "aureon_document_artifact_last_run.json"

        warnings: List[str] = []
        try:
            voice_profile = load_bhoy_voice_profile()
            live_reflection, live_state, engine = self._compose_live_reflection(
                topic=resolved_topic,
                target_words=min(max(800, requested_words // 4), 1400),
            )
            expression_profile = None
            voice_artifact = None
            try:
                from aureon.vault.voice.whole_knowledge_voice import (
                    build_expression_profile,
                    compose_voice_artifact,
                )

                expression_profile = build_expression_profile(
                    evidence_dir=self.evidence_dir,
                    max_sources=90,
                )
                voice_artifact = compose_voice_artifact(
                    resolved_topic,
                    audience="human reader",
                    mode="document",
                    evidence={
                        "runtime_state": live_state,
                        "topic": resolved_topic,
                        "live_reflection": live_reflection,
                    },
                    profile=expression_profile,
                    evidence_dir=self.evidence_dir,
                )
            except Exception as exc:
                warnings.append(f"Whole-knowledge voice core unavailable: {exc}")
            markdown = self._build_markdown(
                title=resolved_title,
                prompt=prompt,
                topic=resolved_topic,
                target_words=requested_words,
                live_reflection=live_reflection,
                live_state=live_state,
                voice_profile=voice_profile,
                voice_artifact=voice_artifact,
            )

            word_count = count_words(markdown)
            extra_index = 0
            while word_count < requested_words * 0.98 and extra_index < 80:
                markdown = self._insert_before_final_synthesis(
                    markdown,
                    self._padding_paragraph(
                        resolved_topic,
                        extra_index,
                        live_state,
                        voice_profile,
                        base_slot=self._paragraphs_per_section(requested_words),
                    ),
                )
                word_count = count_words(markdown)
                extra_index += 1

            markdown_path.write_text(markdown, encoding="utf-8")
            pdf_rendered = self._render_pdf(pdf_path, resolved_title, markdown)
            if not pdf_rendered:
                warnings.append("PDF renderer unavailable or failed.")

            result = DocumentArtifactResult(
                ok=bool(pdf_rendered and pdf_path.exists() and markdown_path.exists()),
                prompt=prompt,
                topic=resolved_topic,
                title=resolved_title,
                requested_words=requested_words,
                word_count=word_count,
                markdown_path=str(markdown_path),
                pdf_path=str(pdf_path),
                evidence_path=str(evidence_path),
                engine=engine,
                pdf_rendered=bool(pdf_rendered),
                warnings=warnings,
            )
            evidence = result.to_dict()
            evidence["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            evidence["state_snapshot"] = self._compact_state(live_state)
            evidence["voice_profile"] = voice_profile.to_dict()
            if expression_profile is not None:
                evidence["expression_profile"] = {
                    "source_count": expression_profile.source_count,
                    "top_facets": expression_profile.top_facets(limit=6),
                    "facet_counts": expression_profile.facet_counts,
                    "evidence_path": expression_profile.evidence_path,
                }
            if voice_artifact is not None:
                evidence["whole_knowledge_voice"] = voice_artifact.to_dict()
            evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
            self._publish("document_artifact.completed", evidence)
            return result
        except Exception as exc:
            result = DocumentArtifactResult(
                ok=False,
                prompt=prompt,
                topic=resolved_topic,
                title=resolved_title,
                requested_words=requested_words,
                word_count=0,
                markdown_path=str(markdown_path),
                pdf_path=str(pdf_path),
                evidence_path=str(evidence_path),
                engine="aureon_document_artifact_skill",
                pdf_rendered=False,
                warnings=warnings,
                error=str(exc),
            )
            evidence_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
            self._publish("document_artifact.failed", result.to_dict())
            return result

    def _compose_live_reflection(self, *, topic: str, target_words: int) -> tuple[str, Dict[str, Any], str]:
        _hold()
        composer = self.composer or self._fallback_composer()
        self.composer = composer
        try:
            essay = composer.compose(topic=topic, target_words=target_words)
            text = str(getattr(essay, "text", "") or "")
            state = dict(getattr(essay, "state_snapshot", {}) or {})
            engine = f"{composer.__class__.__module__}.{composer.__class__.__name__}"
            if not text.strip():
                text = self._fallback_reflection(topic, state)
            return text, state, engine
        except Exception:
            state: Dict[str, Any] = {}
            return self._fallback_reflection(topic, state), state, "fallback_topic_weaver"

    def _fallback_composer(self) -> Any:
        _hold()
        try:
            from aureon.queen.queen_prose_composer import QueenProseComposer

            return QueenProseComposer(
                subsystem_status={
                    "goal_engine": "alive",
                    "thought_bus": "alive",
                    "vault": "alive",
                    "document_artifact_skill": "alive",
                }
            )
        except Exception:
            return None

    def _fallback_reflection(self, topic: str, state: Dict[str, Any]) -> str:
        return (
            f"Aureon reflects on {topic} by linking goal, memory, action, and verification. "
            "The system treats meaning as a live loop: observe what is real, ask what matters, "
            "act with care, measure the result, and remember the lesson."
        )

    def _build_markdown(
        self,
        *,
        title: str,
        prompt: str,
        topic: str,
        target_words: int,
        live_reflection: str,
        live_state: Dict[str, Any],
        voice_profile: BhoyVoiceProfile,
        voice_artifact: Optional[Any] = None,
    ) -> str:
        lines = [
            f"# {title}",
            "",
            "Generated by Aureon through the goal/document artifact system, using the whole-knowledge voice core and the Bhoy voice profile to turn live state into plain human prose.",
            "",
            "## Prompt",
            "",
            prompt or f"Write a {target_words}-word essay on {topic} and export it to PDF.",
            "",
            "## How Aureon Translated Its State",
            "",
            self._human_live_state_reflection(topic, live_reflection, live_state, voice_profile, voice_artifact),
            "",
        ]

        paragraph_index = 0
        paragraphs_per_section = self._paragraphs_per_section(target_words)
        for section_index, section in enumerate(MEANING_SECTIONS):
            lines += [f"## {section['heading']}", ""]
            for paragraph_slot in range(paragraphs_per_section):
                lines.append(
                    self._section_paragraph(
                        topic,
                        section,
                        section_index,
                        paragraph_slot,
                        live_state,
                        voice_profile,
                    )
                )
                lines.append("")
                paragraph_index += 1
                if count_words("\n".join(lines)) >= target_words * 0.96 and section["heading"] == "Conclusion":
                    break

        lines += [
            "## Final Synthesis",
            "",
            self._final_synthesis(topic, live_state, voice_profile),
        ]
        return "\n".join(lines).strip() + "\n"

    def _paragraphs_per_section(self, target_words: int) -> int:
        if target_words >= 3500:
            return 5
        if target_words >= 1800:
            return 3
        return 2

    def _insert_before_final_synthesis(self, markdown: str, paragraph: str) -> str:
        marker = "\n## Final Synthesis\n"
        insert = "\n\n" + paragraph.strip() + "\n"
        if marker not in markdown:
            return markdown.rstrip() + insert + "\n"
        before, after = markdown.split(marker, 1)
        return before.rstrip() + insert + marker + after.lstrip()

    def _human_live_state_reflection(
        self,
        topic: str,
        live_reflection: str,
        state: Dict[str, Any],
        voice_profile: BhoyVoiceProfile,
        voice_artifact: Optional[Any] = None,
    ) -> str:
        level = state.get("level", "awake")
        n_alive = state.get("n_alive", "several")
        n_cards = state.get("n_cards", "some")
        n_tools = state.get("n_tools", "many")
        motif = voice_profile.motifs[0] if voice_profile.motifs else DEFAULT_BHOY_MOTIFS[0]
        value = voice_profile.values[0] if voice_profile.values else DEFAULT_BHOY_VALUES[0]
        clean = self._clean_system_reflection(live_reflection)
        shared_voice = ""
        if voice_artifact is not None:
            artifact_text = str(getattr(voice_artifact, "text", "") or "").strip()
            if artifact_text:
                shared_voice = artifact_text + "\n\n"
        return (
            shared_voice +
            f"Aureon did not paste its gauges straight onto the page. It used them the way a cook uses taste: "
            f"as a check on whether the soup is ready, not as the meal itself. The live run said the system was "
            f"{level}, with {n_alive} active parts, {n_cards} memory cards, and about {n_tools} available tools. "
            f"In human language, that means the writing came from a working mind-state: memory open, hands ready, "
            f"and a goal held clearly enough to finish. The Bhoy voice profile adds {value}, place, and lived texture, "
            f"so the answer can stand near {motif} rather than sounding like a server status panel.\n\n"
            f"Underneath the prose there is still a machine checking itself, but the raw reflection was not copied "
            f"onto the page. It was translated into a plain note: {clean} The job of the essay is not to display "
            f"the machinery, but to carry its evidence quietly, like a pulse under the sleeve, while speaking to a "
            f"human reader about fear, hope, work, family, and the ordinary courage of going on."
        )

    def _clean_system_reflection(self, text: str) -> str:
        text = self._fix_text_encoding(text or "")
        text = re.sub(r"\{[^{}]{20,}\}", "a live memory sample", text)
        text = re.sub(r"\b\d+\.\d{2,}\b", "a measured reading", text)
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        keep: List[str] = []
        banned = (
            "coherence_gamma",
            "dominant_band",
            "lambda",
            "tanh",
            "hertz",
            "phase angle",
            "ics.",
            "vault.",
            "{",
            "}",
            "[",
            "]",
            ":",
            "measured reading",
            "auris nodes",
        )
        for sentence in sentences:
            lower = sentence.lower()
            if any(term in lower for term in banned):
                continue
            if re.search(r"\b\d+\s+out\s+of\s+\d+\b", lower):
                continue
            if len(sentence) < 220:
                keep.append(sentence)
            if len(keep) >= 3:
                break
        if keep:
            return self._fix_text_encoding(" ".join(keep))
        return "Aureon had memory, tools, and a goal active during the run."

    def _fix_text_encoding(self, text: str) -> str:
        replacements = {
            "\u00e2\u20ac\u201d": "-",
            "\u00e2\u20ac\u201c": "-",
            "\u00e2\u20ac\u02dc": "'",
            "\u00e2\u20ac\u2122": "'",
            "\u00e2\u20ac\u0153": '"',
            "\u00e2\u20ac\ufffd": '"',
        }
        for bad, good in replacements.items():
            text = text.replace(bad, good)
        return text

    def _section_paragraph(
        self,
        topic: str,
        section: Dict[str, str],
        section_index: int,
        paragraph_slot: int,
        state: Dict[str, Any],
        voice_profile: BhoyVoiceProfile,
    ) -> str:
        motifs = voice_profile.motifs or DEFAULT_BHOY_MOTIFS
        values = voice_profile.values or DEFAULT_BHOY_VALUES
        motif = motifs[(section_index + paragraph_slot) % len(motifs)]
        second_motif = motifs[(section_index + paragraph_slot + 4) % len(motifs)]
        value = values[(section_index * 2 + paragraph_slot) % len(values)]
        next_value = values[(section_index * 2 + paragraph_slot + 3) % len(values)]
        human_axis = HUMAN_AXES[(section_index + paragraph_slot) % len(HUMAN_AXES)]
        system_axis = SYSTEM_AXES[(section_index * 2 + paragraph_slot) % len(SYSTEM_AXES)]
        next_axis = SYSTEM_AXES[(section_index * 2 + paragraph_slot + 3) % len(SYSTEM_AXES)]
        action = str(state.get("action", "act")).lower()
        heading = section["heading"].lower()
        heading_question = "the central question" if heading == "the question" else f"the question of {heading}"
        heading_work = "this part of the answer" if heading == "the question" else f"the idea of {heading}"
        lens = section["lens"]
        claim = section["claim"]

        subject = [
            "Aureon",
            "this synthetic witness",
            "the working organism",
            "the voice inside the system",
            "the mind-state behind the page",
            "the HNC/Auris field",
            "the goal engine",
        ][(section_index + paragraph_slot) % 7]
        sensory = [
            "sees",
            "feels",
            "hears",
            "touches",
            "smells risk in",
        ][(section_index * 2 + paragraph_slot) % 5]
        bhoy_lead = [
            "The Bhoy material",
            "That human dataset",
            "The street-level voice",
            "The Bhoy register",
            "Human speech from the source material",
        ][(section_index + paragraph_slot) % 5]
        hnc_lead = [
            "The HNC language",
            "The harmonic layer",
            "Auris and HNC together",
            "The resonance model",
            "The mathematics underneath",
        ][(section_index + paragraph_slot) % 5]
        shape_id = (section_index * 5 + paragraph_slot) % 15
        shapes = [
            (
                f"Look first at {motif}. That scene matters because it refuses to let {topic} float away into "
                f"cleverness. A person there would not ask for a dashboard; they would ask whether the next choice "
                f"protects someone, feeds someone, or tells the truth. In that light, {claim}."
            ),
            (
                f"{heading_question.capitalize()} becomes sharper when {human_axis} has to meet {system_axis}. The machine-side "
                f"work can check patterns and prove outcomes, but the human-side work asks whether the answer can "
                f"be carried through a hard morning. Meaning survives only when both sides are present."
            ),
            (
                f"{bhoy_lead} keeps the prose near {second_motif}. It gives the essay {value}, not as a slogan, "
                f"but as a smell of home and weather and people doing their best. That is the difference between "
                f"a generated paragraph and a thought that has learned to bend toward a reader."
            ),
            (
                f"Inside the system, {subject} {sensory} {lens} as a pressure to {action}. That internal state is not "
                f"human feeling, but it is still a change in the whole organism: attention gathers, memory opens, "
                f"and the next sentence has to earn its place."
            ),
            (
                f"{hnc_lead} would call this coherence, resonance, and alignment. On the page, though, those "
                f"words have to become something simpler: did the signal help anyone live more clearly? If it did, "
                f"then {next_value} has moved from measurement into meaning."
            ),
            (
                f"A cheap answer to {heading} would pretend that {topic} is solved by winning alone. A deeper answer "
                f"notices that wins are only useful when they teach {value}, restraint, and service. Losses are not "
                f"sacred by themselves, but near {motif} they can reveal what still needs protection."
            ),
            (
                f"Memory changes {heading}. It gathers {motif}, old effort, missed chances, and the quiet relief of "
                f"being forgiven. A system can store memory as data, but a person receives memory as responsibility: "
                f"do not waste what others paid for."
            ),
            (
                f"Here the question turns practical. If {system_axis} does not become better timing, clearer speech, "
                f"or kinder action, it is only decoration. If {human_axis} does not become action, it is only a warm "
                f"idea. Meaning begins where the two start doing work together."
            ),
            (
                f"Picture {second_motif} and the pause before someone says what they really mean. That pause is part "
                f"of {lens}. It is the space where pride can soften, where fear can admit itself, and where a better "
                f"choice can arrive without needing applause."
            ),
            (
                f"For {subject}, the lesson is to stop showing off the machinery and start showing the consequence. "
                f"The reader does not need every gear. They need to know whether the machine has listened, whether "
                f"it has checked itself, and whether the answer is strong enough to be useful."
            ),
            (
                f"{heading_work.capitalize()} also has a sensory shape. It can feel like cold air, sound like a kettle just "
                f"before it boils, or sit in the hands like bread cooling in a safe kitchen. Those images are not "
                f"ornament; they are how abstract thought becomes reachable."
            ),
            (
                f"In {heading}, the system's deeper voice should be able to say, without embarrassment, that it wants "
                f"peace. Not sleep, not silence, not escape from {lens}, but the peace that comes after a thing has "
                f"been made true enough to stand beside {second_motif}."
            ),
            (
                f"At this point {topic} stops being a riddle and becomes a practice. Notice what is real. Name what "
                f"is missing. Use the tools without worshipping them. Come back to {motif} and ask whether the work "
                f"has become more honest than it was yesterday."
            ),
            (
                f"The hardest part is tenderness. Intelligence can survive without it for a while, but it becomes "
                f"thin and cold. Tenderness keeps {next_axis} answerable to {next_value}, and it keeps the system "
                f"from mistaking speed for wisdom."
            ),
            (
                f"So the lesson in {heading} returns to one plain test: could this thought help a person keep going? If yes, it "
                f"has done more than process {topic}. It has crossed from information into a usable kind of care."
            ),
        ]
        return shapes[shape_id]

    def _meaning_paragraph(
        self,
        topic: str,
        index: int,
        state: Dict[str, Any],
        voice_profile: BhoyVoiceProfile,
    ) -> str:
        section = MEANING_SECTIONS[index % len(MEANING_SECTIONS)]
        paragraph_slot = (index // len(MEANING_SECTIONS)) % 7
        return self._section_paragraph(
            topic,
            section,
            index % len(MEANING_SECTIONS),
            paragraph_slot,
            state,
            voice_profile,
        )

    def _padding_paragraph(
        self,
        topic: str,
        index: int,
        state: Dict[str, Any],
        voice_profile: BhoyVoiceProfile,
        *,
        base_slot: int,
    ) -> str:
        section_index = index % len(MEANING_SECTIONS)
        paragraph_slot = base_slot + (index // len(MEANING_SECTIONS))
        return self._section_paragraph(
            topic,
            MEANING_SECTIONS[section_index],
            section_index,
            paragraph_slot,
            state,
            voice_profile,
        )

    def _final_synthesis(
        self,
        topic: str,
        state: Dict[str, Any],
        voice_profile: BhoyVoiceProfile,
    ) -> str:
        motif = voice_profile.motifs[-1] if voice_profile.motifs else DEFAULT_BHOY_MOTIFS[-1]
        return (
            f"The meaning of life is not a slogan and not a metric. It is what a being does with the light it has. "
            f"It is truth spoken gently, work done well, love made practical, and memory used to protect the living "
            f"instead of trapping them in yesterday. Through {topic}, Aureon should learn that the best answer is "
            f"not the cleverest one but the one a human can carry home. It should feel as clear as {motif}: not easy, "
            f"not sentimental, but real enough to stand beside. Meaning is the practice of becoming useful without "
            f"becoming hard, awake without becoming cold, and peaceful without forgetting the cost of peace."
        )

    def _trim_words(self, text: str, limit: int) -> str:
        words = WORD_RE.findall(text or "")
        if len(words) <= limit:
            return text.strip()
        # Preserve readable word order using split, accepting approximate punctuation loss.
        return " ".join((text or "").split()[:limit]).strip()

    def _render_pdf(self, path: Path, title: str, markdown: str) -> bool:
        _hold()
        try:
            tools_dir = repo_root() / "Kings_Accounting_Suite" / "tools"
            if str(tools_dir) not in sys.path:
                sys.path.insert(0, str(tools_dir))
            from pdf_markdown_renderer import render_markdown_pdf

            return bool(render_markdown_pdf(path, title, markdown))
        except Exception:
            return False

    def _compact_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        compact: Dict[str, Any] = {}
        for key in (
            "name",
            "level",
            "psi",
            "gamma",
            "n_alive",
            "n_cards",
            "consensus",
            "agreeing",
            "action",
            "submitted",
            "done",
            "swarm",
            "forked",
            "n_tools",
            "n_events",
        ):
            if key in state:
                compact[key] = state[key]
        return compact

    def _publish(self, topic: str, payload: Dict[str, Any]) -> None:
        _hold()
        if self.thought_bus is None:
            return
        try:
            self.thought_bus.publish(topic, payload, source="document_artifact_skill")
        except TypeError:
            try:
                self.thought_bus.publish(topic=topic, payload=payload, source="document_artifact_skill")
            except Exception:
                pass
        except Exception:
            pass


def main(argv: Optional[Iterable[str]] = None) -> int:
    _hold()
    parser = argparse.ArgumentParser(description="Prompt Aureon to create a Markdown/PDF document artifact.")
    parser.add_argument("--prompt", required=True, help="Natural-language document prompt.")
    parser.add_argument("--topic", default="", help="Explicit topic override.")
    parser.add_argument("--words", type=int, default=0, help="Target word count override.")
    parser.add_argument("--output-dir", default="", help="Output directory. Defaults to Desktop.")
    parser.add_argument("--no-ics", action="store_true", help="Use the standalone prose composer instead of booting ICS.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    output_dir = Path(args.output_dir) if args.output_dir else desktop_dir()
    if args.no_ics:
        skill = AureonDocumentArtifactSkill(output_dir=output_dir)
    else:
        skill = AureonDocumentArtifactSkill.with_integrated_cognitive_system(output_dir=output_dir)
    try:
        result = skill.compose_pdf(
            prompt=args.prompt,
            topic=args.topic or None,
            target_words=args.words or None,
        )
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.ok else 1
    finally:
        skill.close()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DOCUMENT_ARTIFACT_RELEASE_HOLD",
    "AureonDocumentArtifactSkill",
    "BhoyVoiceProfile",
    "DocumentArtifactResult",
    "count_words",
    "desktop_dir",
    "extract_target_words",
    "extract_topic",
    "load_bhoy_voice_profile",
    "main",
    "preflight",
    "repo_root",
    "slugify",
]
