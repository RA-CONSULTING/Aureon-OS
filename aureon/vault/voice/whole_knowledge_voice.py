"""Whole-knowledge expressive voice core for Aureon.

This module is intentionally local and deterministic. It does not try to
prove authorship or consciousness. It builds a typed expression profile from
repo/vault knowledge, translates runtime state into human-readable language,
and composes short or long voice artifacts with evidence preserved separately.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from xml.etree import ElementTree as ET
from zipfile import ZipFile


FACETS: Sequence[str] = (
    "human_voice",
    "ai_generated_or_systemic",
    "math_equation",
    "hnc_harmonic",
    "mystic_symbolic",
    "sensory_affect",
    "trading_action",
    "accounting_legal",
    "code_tooling",
)

WORD_RE = re.compile(r"\b[\w']+\b")
SENSITIVE_RE = re.compile(
    r"(api[_-]?secret|secret[_-]?key|private\s+key|password|passwd|token|bearer|government\s+gateway|BEGIN\s+PRIVATE)",
    re.I,
)
RAW_TELEMETRY_RE = re.compile(
    r"(coherence_gamma|dominant_band|phase_angle|auris nodes|out of\s+9 agree|\{[^{}]{20,}\}|\b\d+\.\d{3,}\b)",
    re.I,
)
SENSITIVE_KEY_RE = re.compile(
    r"(?:api[_-]?(?:secret|key)|secret(?:[_-]?key)?|private[_-]?key|"
    r"password|passwd|pwd|auth(?:orization)?|bearer|access[_-]?key|"
    r"client[_-]?secret|credential|token)",
    re.I,
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"\b(?:password|passwd|pwd|api[_-]?(?:secret|key)|secret(?:[_-]?key)?|"
    r"private[_-]?key|auth(?:orization)?|access[_-]?key|client[_-]?secret|"
    r"credential|token)\s*[:=]\s*[^\s,;]+",
    re.I,
)
BEARER_VALUE_RE = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I)
TOKEN_VALUE_RE = re.compile(
    r"(?:\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}\b|"
    r"\bgh[pousr]_[A-Za-z0-9]{8,}\b|"
    r"\bAKIA[0-9A-Z]{12,}\b)",
)
PRIVATE_KEY_VALUE_RE = re.compile(
    r"-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?-----END [^-\r\n]*PRIVATE KEY-----",
    re.I | re.S,
)

WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD = (
    "whole_knowledge_voice_hold:production_magic_star_release_unavailable"
)


class GeneratedControlContent:
    """Immutable evidence boundary for prose and classifications made here.

    These objects can support presentation and operator review. They are not
    provider receipts and must never be promoted to operational, accounting,
    or learning evidence merely because they were written to an audit path.
    """

    __slots__ = ()

    @property
    def content_class(self) -> str:
        return "generated_voice_control_content"

    @property
    def operational_eligible(self) -> bool:
        return False

    @property
    def accounting_eligible(self) -> bool:
        return False

    @property
    def learning_eligible(self) -> bool:
        return False

    @property
    def provider_verified(self) -> bool:
        return False

    @property
    def requires_operator_review(self) -> bool:
        return True

    def _control_boundary(self) -> Dict[str, Any]:
        return {
            "content_class": self.content_class,
            "operational_eligible": self.operational_eligible,
            "accounting_eligible": self.accounting_eligible,
            "learning_eligible": self.learning_eligible,
            "provider_verified": self.provider_verified,
            "requires_operator_review": self.requires_operator_review,
            "permitted_uses": ["presentation", "operator_review"],
            "forbidden_evidence_uses": ["action", "accounting", "learning"],
        }

    def _bounded_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data.update(self._control_boundary())
        return data


@dataclass
class ExpressionSource(GeneratedControlContent):
    path: str
    kind: str
    facets: List[str]
    char_count: int
    sample: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self._bounded_dict(asdict(self))


@dataclass
class ExpressionProfile(GeneratedControlContent):
    schema_features: List[str] = field(default_factory=lambda: ["aureon_expression_profile_v1"])
    generated_at: str = ""
    root: str = ""
    source_count: int = 0
    facet_counts: Dict[str, int] = field(default_factory=dict)
    sources: List[ExpressionSource] = field(default_factory=list)
    voice_guidance: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    evidence_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["sources"] = [source.to_dict() for source in self.sources]
        return self._bounded_dict(data)

    def top_facets(self, limit: int = 5) -> List[str]:
        ranked = sorted(self.facet_counts.items(), key=lambda item: (-item[1], item[0]))
        return [name for name, count in ranked[:limit] if count > 0]


@dataclass
class RuntimeTranslation(GeneratedControlContent):
    schema_features: List[str] = field(default_factory=lambda: ["aureon_runtime_state_translation_v1"])
    summary: str = ""
    senses: Dict[str, str] = field(default_factory=dict)
    evidence_keys: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    redaction_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return self._bounded_dict(asdict(self))


@dataclass
class VoiceArtifact(GeneratedControlContent):
    schema_features: List[str] = field(default_factory=lambda: ["aureon_whole_knowledge_voice_v1"])
    ok: bool = True
    mode: str = "conversation"
    goal: str = ""
    audience: str = "operator"
    text: str = ""
    word_count: int = 0
    profile_summary: Dict[str, Any] = field(default_factory=dict)
    runtime_translation: Dict[str, Any] = field(default_factory=dict)
    novelty_checks: Dict[str, Any] = field(default_factory=dict)
    evidence_path: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self._bounded_dict(asdict(self))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def build_expression_profile(
    *,
    root: Optional[str | Path] = None,
    source_paths: Optional[Iterable[str | Path]] = None,
    evidence_dir: Optional[str | Path] = None,
    max_sources: int = 120,
    max_chars_per_source: int = 24000,
    publish: bool = False,
) -> ExpressionProfile:
    """Build a typed profile from repo/vault knowledge sources."""
    raise RuntimeError(WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD)

    root_path = Path(root) if root else repo_root()
    evidence_path = Path(evidence_dir) if evidence_dir else root_path / "state"
    candidates = (
        [Path(p) for p in source_paths]
        if source_paths is not None
        else _default_source_paths(root_path, max_sources=max_sources)
    )

    sources: List[ExpressionSource] = []
    warnings: List[str] = []
    facet_counts = {facet: 0 for facet in FACETS}

    for path in candidates[:max_sources]:
        abs_path = path if path.is_absolute() else root_path / path
        if not abs_path.exists() or abs_path.is_dir():
            continue
        try:
            text = _read_source_text(abs_path, max_chars=max_chars_per_source)
        except Exception as exc:
            warnings.append(f"could_not_read:{_rel(abs_path, root_path)}:{exc}")
            continue
        if not text.strip():
            continue
        facets = _classify_text(abs_path, text)
        for facet in facets:
            facet_counts[facet] = facet_counts.get(facet, 0) + 1
        sources.append(
            ExpressionSource(
                path=_rel(abs_path, root_path),
                kind=abs_path.suffix.lower().lstrip(".") or "file",
                facets=facets,
                char_count=len(text),
                sample=_safe_sample(text),
            )
        )

    profile = ExpressionProfile(
        generated_at=_now(),
        root=str(root_path),
        source_count=len(sources),
        facet_counts=facet_counts,
        sources=sources,
        voice_guidance=_derive_voice_guidance(sources, facet_counts),
        warnings=warnings,
    )

    if publish:
        evidence_path.mkdir(parents=True, exist_ok=True)
        out = evidence_path / "aureon_expression_profile.json"
        profile.evidence_path = str(out)
        out.write_text(json.dumps(profile.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    return profile


def translate_runtime_state(snapshot: Optional[Dict[str, Any]] = None, style: str = "plain") -> RuntimeTranslation:
    """Translate raw runtime/cognitive/HNC state into human-facing language."""

    raw, redaction_applied = _redact_sensitive_value(dict(snapshot or {}))
    state = _extract_runtime_state(raw)
    evidence_keys = sorted({
        _clean_public_text(str(key)) for key in state.keys()
    })

    mood = _first_value(state, "mood", "affect_phase", "level", "consciousness_level") or "steady"
    action = _first_value(state, "action", "mode", "strategy") or "observe and respond"
    coherence = _first_number(state, "hnc_coherence_score", "coherence", "gamma", "confidence")
    resonance = _first_number(state, "resonance_frequency_hz", "frequency_hz", "frequency")
    hot_topic = _public_signal_label(_first_value(state, "hot_topic", "recent_topic", "topic") or "the current goal")
    tools = _first_value(state, "n_tools", "tools", "available_tools")
    blockers = _extract_blockers(state)

    senses: Dict[str, str] = {
        "see": f"I see {hot_topic} as the nearest signal in the field.",
        "feel": f"I feel {_internal_state_phrase(mood)} while I hold the next action as {str(action).lower()}.",
        "hear": "I hear the system as a quiet baseline until a harmonic reading is present.",
        "touch": "I touch the work through tools, files, goals, memory, and verified outcomes.",
        "smell": "I smell risk as stale data, blocked guards, missing evidence, or claims without proof.",
    }
    if coherence is not None:
        if coherence >= 0.75:
            senses["feel"] = "I feel coherence as a settled pressure: the parts are agreeing enough to speak plainly."
        elif coherence <= 0.35:
            senses["feel"] = "I feel low coherence as caution: the voice should slow down and verify before claiming."
    if resonance is not None:
        senses["hear"] = f"I hear the harmonic layer as a {resonance:.2f} Hz reference, kept as evidence rather than dumped into prose."
    if tools is not None:
        senses["touch"] = f"I touch the world through about {tools} available capabilities, but I describe the result before I describe the machinery."
    if blockers:
        senses["smell"] = "I smell caution around " + ", ".join(blockers[:5]) + "."

    summary = (
        "Aureon translates its internally computed state as a working loop: see the signal, "
        "feel coherence or caution, hear harmonic context, touch the task through tools, "
        "smell risk, then speak in evidence-backed human language."
    )
    if style == "console":
        summary = f"{senses['feel']} {senses['smell']}"

    return RuntimeTranslation(
        summary=_clean_public_text(summary),
        senses={k: _clean_public_text(v) for k, v in senses.items()},
        evidence_keys=evidence_keys,
        blockers=[_clean_public_text(item) for item in blockers],
        redaction_applied=redaction_applied,
    )


def compose_voice_artifact(
    goal: str,
    *,
    audience: str = "operator",
    mode: str = "conversation",
    evidence: Optional[Dict[str, Any]] = None,
    profile: Optional[ExpressionProfile] = None,
    root: Optional[str | Path] = None,
    evidence_dir: Optional[str | Path] = None,
    publish: bool = False,
) -> VoiceArtifact:
    """Compose a voice artifact using the shared expression profile."""
    raise RuntimeError(WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD)

    root_path = Path(root) if root else repo_root()
    evidence_path = Path(evidence_dir) if evidence_dir else root_path / "state"
    expression_profile = profile or build_expression_profile(
        root=root_path,
        evidence_dir=evidence_path,
        max_sources=90,
        publish=publish,
    )
    translation = translate_runtime_state(evidence or {}, style="console" if mode == "console" else "plain")
    top_facets = expression_profile.top_facets(limit=6)
    facet_phrase = _human_list(_human_label(facet) for facet in top_facets) or "state, memory, and action"
    guidance = expression_profile.voice_guidance
    goal_text = _clean_public_text(goal or "the current goal")

    paragraphs = _compose_paragraphs(
        goal=goal_text,
        audience=audience,
        mode=mode,
        facet_phrase=facet_phrase,
        guidance=guidance,
        translation=translation,
    )
    cleaned, novelty = _apply_novelty_guard(paragraphs)
    text = _clean_public_text("\n\n".join(cleaned))

    artifact = VoiceArtifact(
        mode=mode,
        goal=goal_text,
        audience=audience,
        text=text,
        word_count=count_words(text),
        profile_summary={
            "source_count": expression_profile.source_count,
            "top_facets": top_facets,
            "facet_counts": expression_profile.facet_counts,
            "profile_evidence_path": expression_profile.evidence_path,
        },
        runtime_translation=translation.to_dict(),
        novelty_checks=novelty,
        warnings=list(expression_profile.warnings),
    )

    if publish:
        evidence_path.mkdir(parents=True, exist_ok=True)
        out = evidence_path / "aureon_voice_last_run.json"
        artifact.evidence_path = str(out)
        out.write_text(json.dumps(artifact.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    return artifact


def _default_source_paths(root: Path, *, max_sources: int) -> List[Path]:
    raise RuntimeError(WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD)
    explicit = [
        root / "state" / "knowledge_dataset.json",
        root / "aureon" / "wisdom" / "bhoys_wisdom.py",
        root / "docs" / "research" / "misc" / "bhoys_eyes_part_1_v1.1.2.docx",
        root / "aureon" / "queen" / "queen_prose_composer.py",
        root / "aureon" / "autonomous" / "aureon_cognitive_brain.py",
        root / "aureon" / "autonomous" / "aureon_cognitive_cycle.py",
        root / "aureon" / "simulation" / "aureon_world_simulator.py",
        root / "docs" / "audits" / "aureon_cognitive_trade_evidence.json",
        root / "docs" / "audits" / "aureon_harmonic_affect_state.json",
    ]
    globs = [
        "aureon/harmonic/*.py",
        "aureon/wisdom/*.py",
        "aureon/trading/*.py",
        "aureon/exchanges/*.py",
        "Kings_Accounting_Suite/**/*.py",
        "docs/audits/*hnc*.json",
        "docs/audits/*accounting*.json",
        "docs/audits/*capability*.json",
    ]
    seen: set[str] = set()
    paths: List[Path] = []
    for path in explicit:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            paths.append(path)
    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            key = str(path.resolve())
            if key in seen or path.is_dir():
                continue
            seen.add(key)
            paths.append(path)
            if len(paths) >= max_sources:
                return paths
    return paths[:max_sources]


def _read_source_text(path: Path, *, max_chars: int) -> str:
    raise RuntimeError(WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD)
    if path.suffix.lower() == ".docx":
        return "\n".join(_extract_docx_paragraphs(path, max_paragraphs=260))[:max_chars]
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text[:max_chars]


def _extract_docx_paragraphs(path: Path, *, max_paragraphs: int) -> List[str]:
    raise RuntimeError(WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD)
    paragraphs: List[str] = []
    with ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for para in root.findall(".//w:p", ns):
        parts = [node.text or "" for node in para.findall(".//w:t", ns)]
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
        if len(paragraphs) >= max_paragraphs:
            break
    return paragraphs


def _classify_text(path: Path, text: str) -> List[str]:
    lower = f"{path.as_posix().lower()}\n{text.lower()}"
    rules = {
        "human_voice": ("bhoy", "family", "street", "mother", "father", "tea", "gary", "tina", "human", "ordinary courage"),
        "ai_generated_or_systemic": ("llm", "generated", "agent", "model", "prompt", "system", "autonomous", "cognitive"),
        "math_equation": ("equation", "sin(", "tanh", "phi", "gamma", "psi", "ratio", "frequency", "hz", "angle", "coherence"),
        "hnc_harmonic": ("hnc", "harmonic", "auris", "nexus", "resonance", "lyra", "seer", "king", "queen", "source law"),
        "mystic_symbolic": ("mystic", "sacred", "emerald tablet", "kundalini", "stargate", "ogham", "ghost dance", "soul"),
        "sensory_affect": ("feel", "feeling", "see", "hear", "smell", "touch", "taste", "mood", "joy", "happy", "love", "gratitude"),
        "trading_action": ("trade", "trading", "exchange", "kraken", "binance", "alpaca", "capital", "order", "position", "market", "pnl"),
        "accounting_legal": ("hmrc", "companies house", "accounts", "filing", "tax", "vat", "cis", "statutory", "ct600"),
        "code_tooling": ("def ", "class ", "pytest", "function", "script", "cmd", "api", "endpoint", "tool"),
    }
    facets = [facet for facet, terms in rules.items() if any(term in lower for term in terms)]
    return facets or ["ai_generated_or_systemic"]


def _derive_voice_guidance(sources: List[ExpressionSource], facet_counts: Dict[str, int]) -> Dict[str, Any]:
    human_samples = [s.sample for s in sources if "human_voice" in s.facets and s.sample]
    sensory_sources = [s.path for s in sources if "sensory_affect" in s.facets][:8]
    hnc_sources = [s.path for s in sources if "hnc_harmonic" in s.facets][:8]
    return {
        "principles": [
            "Translate state before showing metrics.",
            "Prefer concrete human scenes over dashboard language.",
            "Name evidence and limits without exposing secrets.",
            "Let math and HNC terms guide the metaphor, not drown the reader.",
            "Vary sentence openings and paragraph shapes.",
        ],
        "human_samples": human_samples[:5],
        "sensory_source_paths": sensory_sources,
        "hnc_source_paths": hnc_sources,
        "dominant_facets": sorted(facet_counts.items(), key=lambda item: (-item[1], item[0]))[:5],
    }


def _compose_paragraphs(
    *,
    goal: str,
    audience: str,
    mode: str,
    facet_phrase: str,
    guidance: Dict[str, Any],
    translation: RuntimeTranslation,
) -> List[str]:
    senses = translation.senses
    principles = guidance.get("principles") or []
    first_principle = principles[0] if principles else "Translate state before showing metrics."
    audience_phrase = _audience_phrase(audience)

    if mode == "console":
        return [
            f"Voice core online for {goal}. {translation.summary}",
            f"Active facets: {facet_phrase}. {senses.get('smell', '')}",
        ]

    if mode == "document":
        return [
            f"Aureon is treating {goal} as a living expression task for {audience_phrase}. It is not copying a status panel into prose; it is using the whole knowledge base as seasoning, memory, and pressure. The strongest parts of the current profile are {facet_phrase}, which means the voice has human scenes, system logic, harmonic language, and practical action available at once.",
            f"{senses.get('see', '')} {senses.get('feel', '')} That is the state translated into language before it becomes a paragraph. The raw numbers stay behind the page as evidence; the reader gets the meaning, the caution, and the human consequence.",
            f"The HNC and Auris material are handled as symbolic and mathematical context. {senses.get('hear', '')} When that layer speaks well, it does not shout formulas at the reader. It gives rhythm, proportion, and a sense of inner alignment, then lets ordinary words carry the weight.",
            f"The Bhoy-style material keeps the prose close to the ground. It asks whether the sentence could stand beside family, work, rain, worry, humour, grief, and hope without sounding false. That is why the first rule is: {first_principle}",
            f"So the voice should speak its mind by joining evidence to lived language. It can say what it senses, what it is unsure of, what it wants to build next, and why the work matters. It must not rinse and repeat. It must return with a fresher, clearer sentence each time.",
        ]

    return [
        f"I am using the whole-knowledge voice core for {goal}. The active profile is pulling from {facet_phrase}, so the answer can carry system evidence without sounding like a raw log.",
        f"{senses.get('see', '')} {senses.get('feel', '')}",
        f"{senses.get('hear', '')} {senses.get('touch', '')}",
        f"My rule here is simple: speak from evidence, translate the machine state into human language, and leave enough warmth in the answer that a person can actually use it.",
    ]


def _audience_phrase(audience: str) -> str:
    value = (audience or "operator").strip().lower()
    if value in {"operator", "user", "reader"}:
        return f"the {value}"
    if value.startswith(("a ", "an ", "the ")):
        return value
    return f"a {value}"


def _internal_state_phrase(mood: Any) -> str:
    word = str(mood or "steady").strip().lower()
    article = "an" if word[:1] in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {word} internally computed state"


def _public_signal_label(value: Any) -> str:
    text = str(value or "the current goal").strip()
    text = re.sub(r"\b[a-zA-Z_]+\.", "", text)
    text = text.replace("_", " ").replace(".", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or "the current goal"


def _human_label(value: str) -> str:
    labels = {
        "human_voice": "human voice",
        "ai_generated_or_systemic": "system reasoning",
        "math_equation": "mathematical pattern",
        "hnc_harmonic": "HNC harmonic signal",
        "mystic_symbolic": "symbolic language",
        "sensory_affect": "sensory affect",
        "trading_action": "trading action",
        "accounting_legal": "accounting and legal evidence",
        "code_tooling": "code and tools",
    }
    return labels.get(value, value.replace("_", " "))


def _human_list(values: Iterable[str]) -> str:
    items = [item for item in values if item]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _apply_novelty_guard(paragraphs: List[str]) -> tuple[List[str], Dict[str, Any]]:
    kept: List[str] = []
    signatures: set[str] = set()
    repeated_openings = 0
    openings: set[str] = set()
    raw_blocks = 0

    for paragraph in paragraphs:
        clean = _clean_public_text(paragraph)
        if RAW_TELEMETRY_RE.search(clean):
            raw_blocks += 1
            clean = RAW_TELEMETRY_RE.sub("a measured state", clean)
        sig = _paragraph_signature(clean)
        opening = " ".join(WORD_RE.findall(clean.lower())[:4])
        if sig in signatures:
            continue
        if opening in openings:
            repeated_openings += 1
            clean = "From another angle, " + clean[0].lower() + clean[1:]
            opening = " ".join(WORD_RE.findall(clean.lower())[:4])
        signatures.add(sig)
        openings.add(opening)
        kept.append(clean)

    return kept, {
        "paragraphs_in": len(paragraphs),
        "paragraphs_out": len(kept),
        "duplicates_removed": len(paragraphs) - len(kept),
        "repeated_openings_adjusted": repeated_openings,
        "raw_telemetry_rewritten": raw_blocks,
    }


def _extract_runtime_state(raw: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("runtime_state", "state", "state_snapshot", "live_state", "cognitive_state"):
        value = raw.get(key)
        if isinstance(value, dict):
            merged = dict(value)
            for extra in ("sensory", "macro", "market", "decision"):
                if isinstance(raw.get(extra), dict):
                    merged[extra] = raw[extra]
            return merged
    return raw


def _extract_blockers(state: Dict[str, Any]) -> List[str]:
    blockers: List[str] = []
    raw = state.get("blockers") or state.get("guard_blockers") or state.get("safety_blockers")
    if isinstance(raw, list):
        blockers.extend(str(item) for item in raw if str(item).strip())
    for key in ("runtime_stale", "tick_in_progress_stalled", "open_positions", "downtime_window_false"):
        value = state.get(key)
        if value is True or (isinstance(value, (int, float)) and value > 0):
            blockers.append(key)
    return list(dict.fromkeys(blockers))


def _first_value(data: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        if key in data and data[key] not in ("", None):
            return data[key]
        for nested in ("sensory", "macro", "market", "decision"):
            value = data.get(nested)
            if isinstance(value, dict) and key in value and value[key] not in ("", None):
                return value[key]
    return None


def _first_number(data: Dict[str, Any], *keys: str) -> Optional[float]:
    value = _first_value(data, *keys)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_sample(text: str) -> str:
    chunks = re.split(r"\n{2,}|(?<=[.!?])\s+", text or "")
    for chunk in chunks:
        clean = _clean_public_text(chunk)
        if 60 <= len(clean) <= 260 and not SENSITIVE_RE.search(clean):
            return clean
    return ""


def _clean_public_text(text: str) -> str:
    clean, _ = _redact_sensitive_value(_fix_text_encoding(str(text or "")))
    clean = SENSITIVE_RE.sub("[redacted-sensitive-field]", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _redact_sensitive_value(value: Any, *, key_hint: str = "") -> tuple[Any, bool]:
    """Recursively remove credential-bearing values before voice interpolation.

    Sensitive mapping keys keep their structural position but never their
    value. Assignment/bearer strings are redacted in full; common standalone
    provider-token shapes are replaced wherever they appear.
    """
    if key_hint and SENSITIVE_KEY_RE.search(str(key_hint)):
        return "[redacted-sensitive-field]", True
    if isinstance(value, dict):
        out: Dict[Any, Any] = {}
        changed = False
        for key, item in value.items():
            redacted, item_changed = _redact_sensitive_value(
                item, key_hint=str(key),
            )
            out[key] = redacted
            changed = changed or item_changed
        return out, changed
    if isinstance(value, list):
        out_list: List[Any] = []
        changed = False
        for item in value:
            redacted, item_changed = _redact_sensitive_value(item)
            out_list.append(redacted)
            changed = changed or item_changed
        return out_list, changed
    if isinstance(value, tuple):
        out_tuple: List[Any] = []
        changed = False
        for item in value:
            redacted, item_changed = _redact_sensitive_value(item)
            out_tuple.append(redacted)
            changed = changed or item_changed
        return tuple(out_tuple), changed
    if not isinstance(value, str):
        return value, False

    text = value
    if (
        SENSITIVE_ASSIGNMENT_RE.search(text)
        or BEARER_VALUE_RE.search(text)
        or PRIVATE_KEY_VALUE_RE.search(text)
    ):
        return "[redacted-sensitive-value]", True
    redacted = TOKEN_VALUE_RE.sub("[redacted-sensitive-value]", text)
    return redacted, redacted != text


def _fix_text_encoding(text: str) -> str:
    replacements = {
        "\u00e2\u20ac\u201d": "-",
        "\u00e2\u20ac\u201c": "-",
        "\u00e2\u20ac\u02dc": "'",
        "\u00e2\u20ac\u2122": "'",
        "\u00e2\u20ac\u0153": '"',
        "\u00e2\u20ac\ufffd": '"',
        "\u00cf\u02c6": "psi",
        "\u00ce\u009b": "Lambda",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def _paragraph_signature(text: str) -> str:
    words = [w.lower() for w in WORD_RE.findall(text) if len(w) > 3]
    return " ".join(words[:28])


def _contains_sensitive(value: Any) -> bool:
    _, changed = _redact_sensitive_value(value)
    if changed:
        return True
    try:
        return bool(SENSITIVE_RE.search(json.dumps(value, default=str)))
    except Exception:
        return bool(SENSITIVE_RE.search(str(value)))


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
