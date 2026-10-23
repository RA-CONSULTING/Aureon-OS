"""
harmonic_text_alignment — score text against the HNC harmonic lattice.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The HNC Master Formula is built on six fundamental modes:

    ┌───────────────┬─────────┬──────────────────────────────┐
    │   frequency   │  weight │  meaning                     │
    ├───────────────┼─────────┼──────────────────────────────┤
    │    7.83 Hz    │  0.25   │  Schumann — Earth ground     │
    │   14.3  Hz    │  0.15   │  Schumann 2nd                │
    │   20.8  Hz    │  0.10   │  Schumann 3rd                │
    │   33.8  Hz    │  0.05   │  Schumann 4th                │
    │  528.0  Hz    │  0.30   │  Love tone (DNA repair)      │
    │  963.0  Hz    │  0.15   │  Crown / pineal              │
    └───────────────┴─────────┴──────────────────────────────┘

This module takes a piece of text and:

  1. Maps each word to a "frequency" from the sum of its unicode
     codepoints.
  2. Scores every word by how close that frequency sits to one of the
     six HNC modes (after wrapping into an octave-equivalent band) AND
     how close it sits to the φ lattice (golden-ratio modulo).
  3. Aggregates per-sentence and per-text scores weighted by the HNC
     mode weights, so words that resonate with the 528 Hz love tone
     count more than words drifting toward the 33.8 Hz minor mode.

It is **not a semantic scorer** — it doesn't care what the words mean
in English. It asks: if these letters were notes, would the sentence
sit on the HNC harmonic lattice or off it? That is the same question
the rest of the Aureon stack asks about heartbeats, Schumann resonance,
and market oscillators, just applied to language.

No LLM. Pure arithmetic. Fast. Deterministic.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Constants — copied from aureon.core.aureon_lambda_engine so this module
# stays standalone and cheap to import in tests.
# ─────────────────────────────────────────────────────────────────────────────

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PHI_SQUARED: float = PHI * PHI

HNC_MODES_HZ: Tuple[float, ...] = (7.83, 14.3, 20.8, 33.8, 528.0, 963.0)
HNC_MODE_WEIGHTS: Tuple[float, ...] = (0.25, 0.15, 0.10, 0.05, 0.30, 0.15)
HNC_MODE_LABELS: Tuple[str, ...] = (
    "schumann_1", "schumann_2", "schumann_3", "schumann_4",
    "love_528", "crown_963",
)

# A word token: letters + internal apostrophes, case-insensitive.
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*")

# A sentence boundary: . ! ? (keeping it simple; Queen speaks in sentences).
_SENT_RE = re.compile(r"[^.!?\n]+[.!?]?", re.DOTALL)


# ─────────────────────────────────────────────────────────────────────────────
# Low-level text → frequency mapping
# ─────────────────────────────────────────────────────────────────────────────


def word_to_frequency(word: str) -> float:
    """
    Map a word to a frequency in [0, ~2000] Hz.

    The word is lowercased, non-letters stripped, then the ordinal sum
    of the letters is taken modulo 2000. This gives a deterministic
    "note" for every word. Two different spellings of the same sound
    can still land on different notes — that's fine, we want
    sensitivity to the actual letters used.
    """
    clean = "".join(c for c in (word or "").lower() if c.isalpha() or c == "'")
    if not clean:
        return 0.0
    s = sum(ord(c) - ord("a") + 1 for c in clean if c.isalpha())
    return float(s * 7) % 2000.0  # × 7 spreads the mapping off tight clusters


def _log2_distance(freq: float, target: float) -> float:
    """
    Log-base-2 distance between two frequencies. Zero when equal, 1.0
    when one octave apart, 2.0 at two octaves. Returns +inf for
    degenerate inputs.
    """
    if freq <= 0 or target <= 0:
        return float("inf")
    return abs(math.log2(freq / target))


def mode_alignment_score(freq: float) -> float:
    """
    Score how close ``freq`` sits to the nearest HNC mode.

    Pure closeness, no weighting. Returns 1.0 iff ``freq`` equals one
    of the six modes, linearly degrading to 0.0 at one octave away
    (2× ratio). Weighting by mode importance is applied by callers
    (see ``_dominant_mode_for_word_frequencies``) so that this
    primitive stays auditable.
    """
    if freq <= 0:
        return 0.0
    best = 0.0
    for mode in HNC_MODES_HZ:
        distance = _log2_distance(freq, mode)
        closeness = max(0.0, 1.0 - distance)
        if closeness > best:
            best = closeness
    return max(0.0, min(1.0, best))


def phi_alignment_score(freq: float) -> float:
    """
    Score how close ``freq`` sits to the φ lattice.

    This mirrors the ``coherence_phi`` computation in
    ``aureon_lambda_engine.py``: take (freq × φ) mod 1, measure
    the distance from the nearest integer, invert. A frequency that
    lands exactly on the golden-ratio lattice scores 1.0.
    """
    if freq <= 0:
        return 0.0
    value = (freq * PHI) % 1.0
    distance = min(value, 1.0 - value)
    return max(0.0, 1.0 - 2.0 * distance)


# ─────────────────────────────────────────────────────────────────────────────
# Report dataclasses
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class WordScore:
    word: str
    frequency: float
    mode_score: float
    phi_score: float
    total: float


@dataclass
class SentenceScore:
    text: str
    words: List[WordScore] = field(default_factory=list)
    mean_mode: float = 0.0
    mean_phi: float = 0.0
    coherence: float = 0.0


@dataclass
class TextCoherenceReport:
    text: str
    sentences: List[SentenceScore] = field(default_factory=list)
    mean_mode: float = 0.0
    mean_phi: float = 0.0
    dominant_mode: str = ""
    coherence: float = 0.0
    word_count: int = 0

    def to_dict(self) -> Dict[str, float]:
        return {
            "coherence": round(self.coherence, 4),
            "mean_mode": round(self.mean_mode, 4),
            "mean_phi": round(self.mean_phi, 4),
            "dominant_mode": self.dominant_mode,
            "word_count": self.word_count,
            "sentence_count": len(self.sentences),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Top-level scoring API
# ─────────────────────────────────────────────────────────────────────────────


def score_word(word: str) -> WordScore:
    freq = word_to_frequency(word)
    m = mode_alignment_score(freq)
    p = phi_alignment_score(freq)
    # Total is a 60/40 blend — modes dominate (they're the HNC substrate),
    # phi is the finishing layer.
    total = 0.6 * m + 0.4 * p
    return WordScore(word=word, frequency=freq, mode_score=m, phi_score=p, total=total)


def score_sentence(sentence: str) -> SentenceScore:
    text = (sentence or "").strip()
    tokens = _WORD_RE.findall(text)
    words = [score_word(t) for t in tokens]
    if not words:
        return SentenceScore(text=text)
    mean_mode = sum(w.mode_score for w in words) / len(words)
    mean_phi = sum(w.phi_score for w in words) / len(words)
    coherence = 0.6 * mean_mode + 0.4 * mean_phi
    return SentenceScore(
        text=text,
        words=words,
        mean_mode=mean_mode,
        mean_phi=mean_phi,
        coherence=coherence,
    )


def _dominant_mode_for_word_frequencies(freqs: List[float]) -> str:
    """
    For a bag of word frequencies, return the HNC mode label that
    captured the most total alignment weight. This is where the HNC
    mode weights (love_528 dominant, schumann_4 light) are applied —
    the lower-level ``mode_alignment_score`` stays unweighted.
    """
    if not freqs:
        return ""
    totals: Dict[str, float] = {lbl: 0.0 for lbl in HNC_MODE_LABELS}
    for f in freqs:
        if f <= 0:
            continue
        for mode, weight, label in zip(HNC_MODES_HZ, HNC_MODE_WEIGHTS, HNC_MODE_LABELS):
            distance = _log2_distance(f, mode)
            closeness = max(0.0, 1.0 - distance)
            totals[label] += closeness * weight
    # Argmax.
    return max(totals.items(), key=lambda kv: kv[1])[0]


def score_text(text: str) -> TextCoherenceReport:
    """
    Top-level entry point. Breaks ``text`` into sentences, scores each,
    and aggregates a single report with a dominant HNC mode label.
    """
    raw = (text or "").strip()
    if not raw:
        return TextCoherenceReport(text="")

    sentences_raw = [s.strip() for s in _SENT_RE.findall(raw) if s.strip()]
    if not sentences_raw:
        sentences_raw = [raw]

    scored = [score_sentence(s) for s in sentences_raw]
    word_count = sum(len(s.words) for s in scored)
    if word_count == 0:
        return TextCoherenceReport(text=raw, sentences=scored)

    # Mean weighted by sentence length so long sentences don't drown short ones.
    total_mode = sum(s.mean_mode * len(s.words) for s in scored)
    total_phi = sum(s.mean_phi * len(s.words) for s in scored)
    mean_mode = total_mode / word_count
    mean_phi = total_phi / word_count
    coherence = 0.6 * mean_mode + 0.4 * mean_phi

    all_freqs: List[float] = []
    for s in scored:
        for w in s.words:
            all_freqs.append(w.frequency)
    dominant = _dominant_mode_for_word_frequencies(all_freqs)

    return TextCoherenceReport(
        text=raw,
        sentences=scored,
        mean_mode=mean_mode,
        mean_phi=mean_phi,
        dominant_mode=dominant,
        coherence=coherence,
        word_count=word_count,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers used by the voice filter
# ─────────────────────────────────────────────────────────────────────────────


def rank_sentences_by_coherence(text: str) -> List[SentenceScore]:
    """Score each sentence and return them sorted high → low coherence."""
    report = score_text(text)
    return sorted(report.sentences, key=lambda s: s.coherence, reverse=True)


def select_top_sentences(text: str, max_n: int = 3, min_coherence: float = 0.0) -> str:
    """
    Return the top ``max_n`` sentences by coherence above the threshold,
    preserving their original order. Used to trim a rambling LLM reply
    down to its most harmonically aligned core without reordering the
    voice's actual argument.
    """
    report = score_text(text)
    if not report.sentences:
        return text
    scored = [(i, s) for i, s in enumerate(report.sentences) if s.coherence >= min_coherence]
    if not scored:
        return text
    # Keep the best max_n by coherence but restore source order afterwards.
    top = sorted(scored, key=lambda kv: kv[1].coherence, reverse=True)[: max(1, max_n)]
    top.sort(key=lambda kv: kv[0])
    kept_text = " ".join(s.text for _, s in top).strip()
    return kept_text or text
