"""Minimal geopolitical forensics adapter for harmonic nexus bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class _Case:
    cluster_id: str
    coherence: float
    energy_rate_per_minute_usd: float
    severity: str


@dataclass(frozen=True)
class _Finding:
    case: _Case
    lt_score: float


class GeopoliticalForensicsEngine:
    """Fallback implementation used when full forensics engine is unavailable."""

    def analyze(self, _subject: str) -> List[_Finding]:
        return [
            _Finding(
                case=_Case(
                    cluster_id="GEO-FALLBACK-001",
                    coherence=0.5,
                    energy_rate_per_minute_usd=0.0,
                    severity="low",
                ),
                lt_score=0.0,
            )
        ]
