r"""Harmonic affect synthesis pipeline.

This module implements a lightweight, fully testable version of the
"harmonic synthesis" narrative frequently referenced in the repository
documentation.  The goal is to make the high level pipeline – tokenisation,
affect extraction, codex lookups, harmonic synthesis and broadcast – concrete
and reproducible.

Given a configuration that specifies the available affects and the
corresponding frequency/decay/weight parameters, the :class:`HarmonicPipeline`
class can analyse natural language input, derive affect intensities and emit a
resonant waveform based on the canonical

.. math:: \sum_i A_i e^{-\beta_i t} \sin(2\pi f_i t)

expression supplied in the user specification.  Explainability is provided via
an annotated trace describing how every stage contributed to the final result.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

import numpy as np


_TOKEN_PATTERN = re.compile(r"[A-Za-z']+")


@dataclass(frozen=True)
class AffectParameters:
    """Configuration for a single affect channel."""

    freq_mult: float
    decay: float
    weight: float


@dataclass(frozen=True)
class AffectContribution:
    """Summary of how an affect influenced the harmonic output."""

    affect: str
    count: int
    intensity: float
    frequency_hz: float
    decay: float
    amplitude: float


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable pipeline configuration."""

    steps: List[str]
    affect_params: Dict[str, AffectParameters]
    base_frequency_hz: float
    waveform_expression: str
    explainability: bool = False

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "PipelineConfig":
        """Parse a configuration dictionary into ``PipelineConfig``."""

        steps = list(mapping.get("pipeline", []))
        affect_spec = mapping.get("affect_to_params", {})
        affect_params: Dict[str, AffectParameters] = {}
        for affect, params in affect_spec.items():
            affect_params[str(affect)] = AffectParameters(
                freq_mult=float(params.get("freq_mult", 1.0)),
                decay=float(params.get("decay", 0.01)),
                weight=float(params.get("weight", 1.0)),
            )
        return cls(
            steps=steps,
            affect_params=affect_params,
            base_frequency_hz=float(mapping.get("base_frequency_hz", 7.83)),
            waveform_expression=str(mapping.get("waveform", "")),
            explainability=bool(mapping.get("explainability", False)),
        )


@dataclass(frozen=True)
class PipelineResult:
    """Container returned by :class:`HarmonicPipeline`."""

    tokens: List[str]
    affect_contributions: List[AffectContribution]
    waveform: List[float]
    knowledge_hits: Dict[str, str]
    metadata: Dict[str, Any]
    explanation: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Serialise the result to a plain dictionary."""

        return {
            "tokens": list(self.tokens),
            "affect_contributions": [
                {
                    "affect": contribution.affect,
                    "count": contribution.count,
                    "intensity": contribution.intensity,
                    "frequency_hz": contribution.frequency_hz,
                    "decay": contribution.decay,
                    "amplitude": contribution.amplitude,
                }
                for contribution in self.affect_contributions
            ],
            "waveform": list(self.waveform),
            "knowledge_hits": dict(self.knowledge_hits),
            "metadata": dict(self.metadata),
            "explanation": self.explanation,
        }

    @property
    def dominant_affect(self) -> Optional[str]:
        """Return the affect with the highest amplitude, if any."""

        if not self.affect_contributions:
            return None
        dominant = max(self.affect_contributions, key=lambda item: item.amplitude)
        return dominant.affect if dominant.amplitude > 0 else None


class HarmonicPipeline:
    """Execute the harmonic affect synthesis pipeline."""

    def __init__(
        self,
        config: PipelineConfig,
        *,
        lexicon: Optional[Mapping[str, Iterable[str]]] = None,
        knowledge_base: Optional[Mapping[str, str]] = None,
        sample_rate: int = 128,
        duration: float = 1.5,
    ) -> None:
        self.config = config
        self.sample_rate = int(sample_rate)
        self.duration = float(duration)

        # Default lexicon maps affect names to themselves so that the bare
        # affect words work without additional configuration.
        if lexicon is None:
            lexicon = {affect: (affect,) for affect in config.affect_params}

        normalised_lexicon: Dict[str, tuple[str, ...]] = {}
        for token, affects in lexicon.items():
            affect_tuple = tuple(str(affect) for affect in affects)
            if affect_tuple:
                normalised_lexicon[token.lower()] = affect_tuple
        self.lexicon = normalised_lexicon

        self.knowledge_base = {token.lower(): text for token, text in (knowledge_base or {}).items()}

    # ------------------------------------------------------------------
    def process(
        self,
        text: str,
        *,
        sample_rate: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> PipelineResult:
        """Run the configured pipeline over ``text`` and return a result."""

        tokens = self._tokenize(text)
        sample_rate = int(sample_rate or self.sample_rate)
        duration = float(duration or self.duration)

        affect_counts = self._extract_affects(tokens)
        contributions = self._build_contributions(affect_counts)
        knowledge_hits = self._lookup_codex(tokens)
        waveform = self._synthesise(contributions, sample_rate=sample_rate, duration=duration)

        metadata = {
            "pipeline": list(self.config.steps),
            "base_frequency_hz": self.config.base_frequency_hz,
            "sample_rate_hz": sample_rate,
            "duration_s": duration,
        }
        if contributions:
            metadata["dominant_affect"] = max(contributions, key=lambda item: item.amplitude).affect

        explanation = self._build_explanation(
            tokens=tokens,
            affect_counts=affect_counts,
            contributions=contributions,
            knowledge_hits=knowledge_hits,
            waveform=waveform,
            sample_rate=sample_rate,
            duration=duration,
        )

        return PipelineResult(
            tokens=tokens,
            affect_contributions=contributions,
            waveform=waveform,
            knowledge_hits=knowledge_hits,
            metadata=metadata,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    def _tokenize(self, text: str) -> List[str]:
        return [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)]

    def _extract_affects(self, tokens: Iterable[str]) -> Dict[str, int]:
        counts: Dict[str, int] = {affect: 0 for affect in self.config.affect_params}
        for token in tokens:
            for affect in self.lexicon.get(token, ()):  # type: ignore[arg-type]
                if affect in counts:
                    counts[affect] += 1
        return counts

    def _build_contributions(self, affect_counts: Mapping[str, int]) -> List[AffectContribution]:
        contributions: List[AffectContribution] = []
        total_hits = sum(max(count, 0) for count in affect_counts.values())

        for affect, params in self.config.affect_params.items():
            count = int(affect_counts.get(affect, 0))
            intensity = (count / total_hits) if total_hits else 0.0
            frequency = self.config.base_frequency_hz * params.freq_mult
            amplitude = params.weight * intensity
            contribution = AffectContribution(
                affect=affect,
                count=count,
                intensity=float(intensity),
                frequency_hz=float(frequency),
                decay=float(params.decay),
                amplitude=float(amplitude),
            )
            contributions.append(contribution)

        return contributions

    def _lookup_codex(self, tokens: Iterable[str]) -> Dict[str, str]:
        hits: Dict[str, str] = {}
        for token in tokens:
            key = token.lower()
            if key in self.knowledge_base and key not in hits:
                hits[key] = self.knowledge_base[key]
                continue
            for affect in self.lexicon.get(key, ()):  # type: ignore[arg-type]
                if affect in self.knowledge_base and affect not in hits:
                    hits[affect] = self.knowledge_base[affect]
                    break
        return hits

    def _synthesise(
        self,
        contributions: Iterable[AffectContribution],
        *,
        sample_rate: int,
        duration: float,
    ) -> List[float]:
        num_samples = max(1, int(round(sample_rate * duration)))
        time = np.linspace(0.0, duration, num_samples, endpoint=False, dtype=np.float64)
        waveform = np.zeros_like(time)

        for contribution in contributions:
            if contribution.amplitude == 0.0:
                continue
            envelope = np.exp(-contribution.decay * time)
            harmonic = np.sin(2.0 * math.pi * contribution.frequency_hz * time)
            waveform += contribution.amplitude * envelope * harmonic

        if np.any(waveform):
            max_amp = float(np.max(np.abs(waveform)))
            if max_amp > 0:
                waveform = waveform / max_amp

        return waveform.astype(float).tolist()

    def _build_explanation(
        self,
        *,
        tokens: List[str],
        affect_counts: Mapping[str, int],
        contributions: List[AffectContribution],
        knowledge_hits: Mapping[str, str],
        waveform: List[float],
        sample_rate: int,
        duration: float,
    ) -> Optional[str]:
        if not self.config.explainability:
            return None

        lines: List[str] = []
        lines.append(f"tokenize → {len(tokens)} tokens")

        active_affects = [f"{affect}×{count}" for affect, count in affect_counts.items() if count > 0]
        if active_affects:
            lines.append("affect-extract → " + ", ".join(active_affects))
        else:
            lines.append("affect-extract → no affective matches")

        if knowledge_hits:
            lines.append("codex-lookup → " + ", ".join(sorted(knowledge_hits)))
        else:
            lines.append("codex-lookup → no codex entries")

        if contributions:
            summary = ", ".join(
                f"{c.affect}: {c.frequency_hz:.2f}Hz/β={c.decay:.3f}/A={c.amplitude:.3f}"
                for c in contributions
            )
            lines.append("harmonic-synthesis → " + summary)
        else:
            lines.append("harmonic-synthesis → no configured affects")

        lines.append(
            "broadcast → {samples} samples @ {rate} Hz ({duration:.2f}s)".format(
                samples=len(waveform), rate=sample_rate, duration=duration
            )
        )

        return "\n".join(lines)


__all__ = [
    "AffectContribution",
    "AffectParameters",
    "HarmonicPipeline",
    "PipelineConfig",
    "PipelineResult",
]
