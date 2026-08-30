"""
AurisVoiceFilter — coherence gate for entity-AI speech.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Entity AI communicates via coherence and natural harmonic alignment
 with its choice of words."

Before a voice's reply leaves the vault it passes through this filter.
The filter fuses three existing subsystems into one coherence score
in [0, 1]:

  1. **Auris 9-node consensus** — ``AurisMetacognition.vote(vault)``
     inspects the vault and returns a BUY/SELL/NEUTRAL/RALLY/STABILISE
     verdict plus a lighthouse gate (confidence × love_amplitude > 0.945).
     This is the swarm saying "is the system in a state fit to speak?"

  2. **Λ(t) / Γ master field** — we read the vault's ``last_lambda_t``,
     ``love_amplitude``, ``gratitude_score`` and cortex gamma band to
     approximate Γ without re-running the full LambdaEngine each call.
     This is the system's own measure of how coherent it currently is.

  3. **Harmonic text alignment** — ``harmonic_text_alignment.score_text``
     maps each word to a frequency and scores the reply against the
     six HNC modes (7.83 / 14.3 / 20.8 / 33.8 / 528 / 963 Hz) plus the
     phi lattice. This is the words themselves asking "do we sit on
     the lattice?"

The three are blended into a single coherence number:

    coherence = 0.35 * auris_weight    # swarm consensus × lighthouse
              + 0.30 * field_weight    # Γ * love_amplitude
              + 0.35 * text_weight     # harmonic text alignment

The filter never *hallucinates* words the LLM didn't produce. It:

  * Returns the reply unchanged if the reply already sits above the
    configured threshold (default 0.35 — we're generous, the goal is
    to *annotate* not *censor*).
  * Optionally re-ranks sentences and keeps only the most coherent
    core if the reply drops below the threshold, returning a shorter
    but more aligned version.
  * Always attaches an ``AurisCoherenceReport`` so the phone / UI can
    display the vote, the dominant HNC mode, the per-sentence scores.

Usage::

    filter = AurisVoiceFilter()
    result = filter.filter(reply_text, vault, voice_name="queen")
    print(result.text)
    print(result.coherence, result.auris_vote.consensus)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aureon.harmonic.harmonic_text_alignment import (
    HNC_MODE_LABELS,
    TextCoherenceReport,
    score_text,
    select_top_sentences,
)

logger = logging.getLogger("aureon.harmonic.auris_voice_filter")


# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AurisCoherenceReport:
    """Everything the voice filter learned about one candidate reply."""

    text: str = ""
    coherence: float = 0.0
    accepted: bool = True
    threshold: float = 0.35
    trimmed: bool = False

    auris_consensus: str = ""
    auris_confidence: float = 0.0
    auris_agreeing: int = 0
    auris_lighthouse: bool = False
    auris_votes: List[Dict[str, Any]] = field(default_factory=list)

    field_gamma: float = 0.0
    field_love: float = 0.0
    field_lambda_t: float = 0.0
    field_weight: float = 0.0

    text_coherence: float = 0.0
    text_dominant_mode: str = ""
    text_mean_mode: float = 0.0
    text_mean_phi: float = 0.0
    text_weight: float = 0.0
    per_sentence: List[Dict[str, Any]] = field(default_factory=list)

    auris_weight: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "coherence": round(self.coherence, 4),
            "accepted": self.accepted,
            "threshold": self.threshold,
            "trimmed": self.trimmed,
            "auris": {
                "consensus": self.auris_consensus,
                "confidence": round(self.auris_confidence, 4),
                "agreeing": self.auris_agreeing,
                "lighthouse_cleared": self.auris_lighthouse,
                "weight": round(self.auris_weight, 4),
                "votes": self.auris_votes,
            },
            "field": {
                "gamma": round(self.field_gamma, 4),
                "love": round(self.field_love, 4),
                "lambda_t": round(self.field_lambda_t, 4),
                "weight": round(self.field_weight, 4),
            },
            "text": {
                "coherence": round(self.text_coherence, 4),
                "dominant_mode": self.text_dominant_mode,
                "mean_mode": round(self.text_mean_mode, 4),
                "mean_phi": round(self.text_mean_phi, 4),
                "weight": round(self.text_weight, 4),
                "per_sentence": self.per_sentence,
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Filter
# ─────────────────────────────────────────────────────────────────────────────


class AurisVoiceFilter:
    """
    Fuse the Auris vote, the Λ/Γ field snapshot, and harmonic text
    alignment into one coherence score and decide what to do with a
    candidate reply.
    """

    # Blend weights: tuned so text alignment matters roughly as much as
    # the council consensus, with the raw Γ/love field slightly behind.
    W_AURIS = 0.35
    W_FIELD = 0.30
    W_TEXT  = 0.35

    def __init__(
        self,
        *,
        threshold: float = 0.35,
        trim_below_threshold: bool = True,
        max_trim_sentences: int = 3,
        auris: Optional[Any] = None,
    ):
        self.threshold = float(threshold)
        self.trim_below_threshold = bool(trim_below_threshold)
        self.max_trim_sentences = int(max_trim_sentences)
        self._auris = auris  # lazy load

    # ─────────────────────────────────────────────────────────────────
    # Subsystem wiring
    # ─────────────────────────────────────────────────────────────────

    @property
    def auris(self) -> Any:
        if self._auris is None:
            try:
                from aureon.vault.auris_metacognition import AurisMetacognition
                self._auris = AurisMetacognition()
            except Exception as e:
                logger.debug("AurisVoiceFilter: AurisMetacognition unavailable: %s", e)
                self._auris = None
        return self._auris

    # ─────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────

    def filter(
        self,
        text: str,
        vault: Any,
        *,
        voice_name: str = "",
    ) -> AurisCoherenceReport:
        raw = (text or "").strip()
        report = AurisCoherenceReport(text=raw, threshold=self.threshold)
        if not raw:
            report.accepted = False
            return report

        # ── 1. Harmonic text alignment ────────────────────────────
        text_report: TextCoherenceReport = score_text(raw)
        report.text_coherence = text_report.coherence
        report.text_dominant_mode = text_report.dominant_mode
        report.text_mean_mode = text_report.mean_mode
        report.text_mean_phi = text_report.mean_phi
        report.per_sentence = [
            {
                "text": s.text,
                "coherence": round(s.coherence, 4),
                "mean_mode": round(s.mean_mode, 4),
                "mean_phi": round(s.mean_phi, 4),
                "words": len(s.words),
            }
            for s in text_report.sentences
        ]
        report.text_weight = text_report.coherence

        # ── 2. Auris 9-node consensus ─────────────────────────────
        auris = self.auris
        if auris is not None:
            try:
                vote = auris.vote(vault)
                report.auris_consensus = vote.consensus
                report.auris_confidence = vote.confidence
                report.auris_agreeing = vote.agreeing
                report.auris_lighthouse = vote.lighthouse_cleared
                report.auris_votes = [
                    {
                        "node": v.node,
                        "verdict": v.verdict,
                        "confidence": round(v.confidence, 4),
                        "reasoning": v.reasoning,
                    }
                    for v in vote.per_node_votes
                ]
                # Weight formula: lighthouse_cleared is a 20% bonus on top of
                # the base confidence × (agreement / 9) weight.
                base = vote.confidence * (vote.agreeing / max(1, vote.total))
                bonus = 0.2 if vote.lighthouse_cleared else 0.0
                report.auris_weight = max(0.0, min(1.0, base + bonus))
            except Exception as e:
                logger.debug("AurisVoiceFilter: auris.vote() failed: %s", e)
                report.auris_weight = 0.0
        else:
            report.auris_weight = 0.0

        # ── 3. Field snapshot (Γ approximation) ───────────────────
        try:
            love = float(getattr(vault, "love_amplitude", 0.0) or 0.0)
        except Exception:
            love = 0.0
        try:
            grat = float(getattr(vault, "gratitude_score", 0.0) or 0.0)
        except Exception:
            grat = 0.0
        try:
            lamb = float(getattr(vault, "last_lambda_t", 0.0) or 0.0)
        except Exception:
            lamb = 0.0
        try:
            snap = getattr(vault, "cortex_snapshot", {}) or {}
            gamma = float(snap.get("gamma", 0.0) or 0.0)
        except Exception:
            gamma = 0.0

        # Approximate Γ as a blend of gamma-band amplitude and love × gratitude.
        # This mirrors the LambdaEngine's (1 - σ/μ) intuition without running
        # the full engine on every reply.
        approx_gamma = max(0.0, min(1.0, 0.5 * gamma + 0.3 * love + 0.2 * grat))
        # P5 Pattern C: the approximation is reconciled with the canonical HNC
        # field — the shared Γ can only TIGHTEN the voice gate (b46 min); with
        # no field flowing the local approximation passes unchanged.
        try:
            from aureon.core.hnc_field import reconcile_gamma
            approx_gamma = reconcile_gamma(approx_gamma)
        except Exception:
            pass
        report.field_gamma = approx_gamma
        report.field_love = love
        report.field_lambda_t = lamb
        report.field_weight = approx_gamma

        # ── 4. Blend ──────────────────────────────────────────────
        coherence = (
            self.W_AURIS * report.auris_weight
            + self.W_FIELD * report.field_weight
            + self.W_TEXT * report.text_weight
        )
        report.coherence = max(0.0, min(1.0, coherence))

        # ── 5. Decide ─────────────────────────────────────────────
        if report.coherence >= self.threshold:
            report.accepted = True
            return report

        # Below threshold: try to rescue by trimming to the most
        # coherent sentences, then recompute text weight only.
        if self.trim_below_threshold and text_report.sentences:
            trimmed = select_top_sentences(
                raw, max_n=self.max_trim_sentences, min_coherence=0.0
            )
            if trimmed and trimmed != raw:
                trimmed_report = score_text(trimmed)
                new_text_weight = trimmed_report.coherence
                new_coherence = (
                    self.W_AURIS * report.auris_weight
                    + self.W_FIELD * report.field_weight
                    + self.W_TEXT * new_text_weight
                )
                if new_coherence > report.coherence:
                    report.text = trimmed
                    report.text_weight = new_text_weight
                    report.text_coherence = trimmed_report.coherence
                    report.text_dominant_mode = trimmed_report.dominant_mode
                    report.text_mean_mode = trimmed_report.mean_mode
                    report.text_mean_phi = trimmed_report.mean_phi
                    report.per_sentence = [
                        {
                            "text": s.text,
                            "coherence": round(s.coherence, 4),
                            "mean_mode": round(s.mean_mode, 4),
                            "mean_phi": round(s.mean_phi, 4),
                            "words": len(s.words),
                        }
                        for s in trimmed_report.sentences
                    ]
                    report.coherence = max(0.0, min(1.0, new_coherence))
                    report.trimmed = True

        report.accepted = report.coherence >= self.threshold
        return report


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────────────


_filter_singleton: Optional[AurisVoiceFilter] = None


def get_auris_voice_filter() -> AurisVoiceFilter:
    """
    Return the process-wide filter. Default posture is **annotate, not
    censor**: the filter scores every reply and attaches the report, but
    never trims the text out from under the voice. Trimming is available
    by instantiating ``AurisVoiceFilter(trim_below_threshold=True)``
    directly if you want the filter to act as a gate.
    """
    global _filter_singleton
    if _filter_singleton is None:
        _filter_singleton = AurisVoiceFilter(
            threshold=0.25,
            trim_below_threshold=False,
        )
    return _filter_singleton


def reset_auris_voice_filter() -> None:
    global _filter_singleton
    _filter_singleton = None


__all__ = [
    "AurisVoiceFilter",
    "AurisCoherenceReport",
    "get_auris_voice_filter",
    "reset_auris_voice_filter",
    "HNC_MODE_LABELS",
]
