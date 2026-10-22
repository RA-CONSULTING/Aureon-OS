"""Tests for the harmonic affect synthesis pipeline."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harmonic_pipeline import AffectContribution, HarmonicPipeline, PipelineConfig


PIPELINE_SPEC = {
    "pipeline": [
        "tokenize",
        "affect-extract",
        "codex-lookup",
        "harmonic-synthesis",
        "broadcast",
    ],
    "affect_to_params": {
        "love": {"freq_mult": 1.0, "decay": 0.013, "weight": 1.0},
        "gratitude": {"freq_mult": 2.0, "decay": 0.017, "weight": 0.92},
        "pride": {"freq_mult": 1.5, "decay": 0.015, "weight": 0.88},
    },
    "base_frequency_hz": 7.83,
    "waveform": "sum_i( A_i * exp(-beta_i t) * sin(2π * fi * t) )",
    "explainability": True,
}

LEXICON = {
    "love": ["love"],
    "loving": ["love"],
    "gratitude": ["gratitude"],
    "grateful": ["gratitude"],
    "pride": ["pride"],
    "prideful": ["pride"],
}

KNOWLEDGE = {
    "love": "Orientation toward unity and connection.",
    "gratitude": "Recognition of shared resonance and support.",
    "pride": "Stabilised confidence radiating from coherence.",
}


def build_pipeline(sample_rate: int = 120, duration: float = 0.5) -> HarmonicPipeline:
    config = PipelineConfig.from_mapping(PIPELINE_SPEC)
    return HarmonicPipeline(
        config,
        lexicon=LEXICON,
        knowledge_base=KNOWLEDGE,
        sample_rate=sample_rate,
        duration=duration,
    )


def find_contribution(result, affect: str) -> AffectContribution:
    for contribution in result.affect_contributions:
        if contribution.affect == affect:
            return contribution
    raise AssertionError(f"Affect '{affect}' not found")


def test_pipeline_generates_waveform_and_explanation():
    pipeline = build_pipeline()
    text = "Love and gratitude weave prideful harmonics."
    result = pipeline.process(text)

    assert result.tokens == ["love", "and", "gratitude", "weave", "prideful", "harmonics"]

    love = find_contribution(result, "love")
    gratitude = find_contribution(result, "gratitude")
    pride = find_contribution(result, "pride")

    # Each affect appears exactly once, so the intensities should be identical.
    assert math.isclose(love.intensity, gratitude.intensity)
    assert math.isclose(pride.intensity, love.intensity)

    assert math.isclose(love.frequency_hz, 7.83, rel_tol=1e-6)
    assert math.isclose(gratitude.frequency_hz, 15.66, rel_tol=1e-6)
    assert math.isclose(pride.frequency_hz, 11.745, rel_tol=1e-6)

    assert result.waveform  # non-empty list
    assert len(result.waveform) == 60  # 120 Hz × 0.5 seconds
    assert max(abs(v) for v in result.waveform) <= 1.0

    assert set(result.knowledge_hits) == {"love", "gratitude", "pride"}
    assert result.explanation is not None
    assert "harmonic-synthesis" in result.explanation

    assert result.metadata["dominant_affect"] in {"love", "gratitude", "pride"}


def test_pipeline_handles_text_without_affects():
    pipeline = build_pipeline()
    text = "Silent void drifting beyond mapped resonance."
    result = pipeline.process(text)

    assert result.tokens == ["silent", "void", "drifting", "beyond", "mapped", "resonance"]
    assert set(result.knowledge_hits) == set()

    amplitudes = [contribution.amplitude for contribution in result.affect_contributions]
    assert amplitudes == [0.0, 0.0, 0.0]

    # Even without affect matches, the waveform is a well-formed zero vector.
    assert np.count_nonzero(result.waveform) == 0
    assert len(result.waveform) == 60

    assert "no affective matches" in (result.explanation or "")
