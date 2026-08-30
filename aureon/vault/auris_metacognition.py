"""
AurisMetacognition — 9-Node Metacognitive Consensus
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Metacognitive actively via the Auris nodes logic system."

A deterministic 9-node voter. Each node (Tiger, Falcon, Hummingbird,
Dolphin, Deer, Owl, Panda, CargoShip, Clownfish) looks at a specific
slice of the vault state and returns one of:

    BUY  — act, grow, deploy more
    SELL — retract, consolidate, conserve
    NEUTRAL — no strong signal
    RALLY — emergency, enter burst mode
    STABILISE — system is drifting, pull back toward base state

Tally follows the existing Aureon Auris logic:
    < 5 nodes agreeing on the majority → NEUTRAL, confidence 0.3
    5–7 agreeing                       → majority, confidence 0.7
    8–9 agreeing                       → majority, confidence 0.95

No LLM calls. Pure vault inspection.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# NODES — same list as the existing AurisAgent in pillar_agents.py
# ─────────────────────────────────────────────────────────────────────────────

NODES: List[str] = [
    "Tiger", "Falcon", "Hummingbird", "Dolphin", "Deer",
    "Owl", "Panda", "CargoShip", "Clownfish",
]

LIGHTHOUSE_THRESHOLD: float = 0.945


# ─────────────────────────────────────────────────────────────────────────────
# Vote result dataclasses
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class NodeVote:
    node: str
    verdict: str                       # BUY | SELL | NEUTRAL | RALLY | STABILISE
    confidence: float                  # per-node confidence [0, 1]
    reasoning: str                     # short explanation


@dataclass
class AurisVoteResult:
    consensus: str                     # majority verdict
    confidence: float                  # global confidence (0.3 / 0.7 / 0.95)
    agreeing: int                      # how many nodes match consensus
    total: int                         # total nodes (9)
    lighthouse_cleared: bool           # confidence × love_amplitude > threshold?
    per_node_votes: List[NodeVote] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consensus": self.consensus,
            "confidence": round(self.confidence, 4),
            "agreeing": self.agreeing,
            "total": self.total,
            "lighthouse_cleared": self.lighthouse_cleared,
            "timestamp": self.timestamp,
            "per_node_votes": [
                {
                    "node": v.node,
                    "verdict": v.verdict,
                    "confidence": round(v.confidence, 4),
                    "reasoning": v.reasoning,
                }
                for v in self.per_node_votes
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# AurisMetacognition
# ─────────────────────────────────────────────────────────────────────────────


class AurisMetacognition:
    """
    9-node deterministic voter over the vault state.

    Usage:
        auris = AurisMetacognition()
        result = auris.vote(vault)
        print(result.consensus, result.confidence)
    """

    def __init__(self):
        self._last_result: Optional[AurisVoteResult] = None
        self._total_votes: int = 0

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def vote(self, vault: Any) -> AurisVoteResult:
        """Run all 9 nodes and return the consensus verdict."""
        votes = [
            self._tiger(vault),
            self._falcon(vault),
            self._hummingbird(vault),
            self._dolphin(vault),
            self._deer(vault),
            self._owl(vault),
            self._panda(vault),
            self._cargoship(vault),
            self._clownfish(vault),
        ]

        consensus, agreeing, confidence = self._tally(votes)

        # Lighthouse = confidence × love_amplitude > 0.945
        love = float(getattr(vault, "love_amplitude", 0.0) or 0.0)
        lighthouse = (confidence * love) > LIGHTHOUSE_THRESHOLD

        # P5 Pattern C: the Auris consensus confidence is reconciled with the
        # canonical HNC field before anyone acts on it — the shared Γ can only
        # TIGHTEN the vote (b46 min), and with no field flowing the nodes'
        # own figure passes unchanged.
        try:
            from aureon.core.hnc_field import reconcile_gamma
            confidence = reconcile_gamma(confidence)
        except Exception:
            pass

        result = AurisVoteResult(
            consensus=consensus,
            confidence=confidence,
            agreeing=agreeing,
            total=len(NODES),
            lighthouse_cleared=lighthouse,
            per_node_votes=votes,
        )
        self._last_result = result
        self._total_votes += 1
        return result

    # ─────────────────────────────────────────────────────────────────────
    # Individual nodes — each inspects a different vault slice
    # ─────────────────────────────────────────────────────────────────────

    def _tiger(self, vault: Any) -> NodeVote:
        """Tiger amplifies volatility — watches Casimir drift."""
        force = float(getattr(vault, "last_casimir_force", 0.0) or 0.0)
        if force > 6.0:
            return NodeVote("Tiger", "RALLY", 0.9, f"drift force {force:.2f} — rally")
        if force > 3.0:
            return NodeVote("Tiger", "BUY", 0.7, f"drift force {force:.2f} — act")
        if force < 0.5:
            return NodeVote("Tiger", "NEUTRAL", 0.4, f"drift force {force:.2f} — quiet")
        return NodeVote("Tiger", "BUY", 0.6, f"drift force {force:.2f} — moderate")

    def _falcon(self, vault: Any) -> NodeVote:
        """Falcon rides momentum — tracks Λ(t) sign and magnitude."""
        lam = float(getattr(vault, "last_lambda_t", 0.0) or 0.0)
        if lam > 0.5:
            return NodeVote("Falcon", "BUY", 0.8, f"Λ(t)={lam:.3f} — strong up")
        if lam < -0.5:
            return NodeVote("Falcon", "SELL", 0.8, f"Λ(t)={lam:.3f} — strong down")
        if abs(lam) < 0.1:
            return NodeVote("Falcon", "NEUTRAL", 0.5, f"Λ(t)={lam:.3f} — flat")
        return NodeVote("Falcon", "BUY" if lam > 0 else "SELL", 0.6,
                        f"Λ(t)={lam:.3f}")

    def _hummingbird(self, vault: Any) -> NodeVote:
        """Hummingbird stabilises — pulls back toward the 528 Hz love tone."""
        dominant_freq = float(getattr(vault, "dominant_frequency_hz", 528.0) or 528.0)
        deviation = abs(dominant_freq - 528.0) / 528.0
        if deviation < 0.02:
            return NodeVote("Hummingbird", "BUY", 0.85,
                            f"on the love tone ({dominant_freq:.1f} Hz)")
        if deviation < 0.1:
            return NodeVote("Hummingbird", "NEUTRAL", 0.6,
                            f"near love tone ({dominant_freq:.1f} Hz)")
        return NodeVote("Hummingbird", "STABILISE", 0.7,
                        f"far from love tone ({dominant_freq:.1f} Hz)")

    def _dolphin(self, vault: Any) -> NodeVote:
        """Dolphin reads emotional drift via love amplitude trend."""
        love = float(getattr(vault, "love_amplitude", 0.5) or 0.5)
        if love > 0.7:
            return NodeVote("Dolphin", "BUY", 0.85, f"love rising ({love:.2f})")
        if love < 0.3:
            return NodeVote("Dolphin", "STABILISE", 0.7, f"love low ({love:.2f})")
        return NodeVote("Dolphin", "NEUTRAL", 0.5, f"love mid ({love:.2f})")

    def _deer(self, vault: Any) -> NodeVote:
        """Deer watches failures — votes STABILISE when gratitude drops."""
        gratitude = float(getattr(vault, "gratitude_score", 0.5) or 0.5)
        if gratitude < 0.3:
            return NodeVote("Deer", "STABILISE", 0.9, f"gratitude low ({gratitude:.2f})")
        if gratitude > 0.8:
            return NodeVote("Deer", "BUY", 0.7, f"gratitude high ({gratitude:.2f})")
        return NodeVote("Deer", "NEUTRAL", 0.5, f"gratitude mid ({gratitude:.2f})")

    def _owl(self, vault: Any) -> NodeVote:
        """Owl recognises patterns — checks cortex dominant band."""
        cortex = getattr(vault, "cortex_snapshot", {}) or {}
        if not cortex:
            return NodeVote("Owl", "NEUTRAL", 0.4, "no cortex data")
        dominant = max(cortex.items(), key=lambda kv: kv[1], default=("alpha", 0))
        band, amp = dominant
        if band == "gamma" and amp > 0.3:
            return NodeVote("Owl", "RALLY", 0.8, f"gamma spike {amp:.2f}")
        if band == "alpha" and amp > 0.3:
            return NodeVote("Owl", "BUY", 0.7, f"alpha dominant {amp:.2f}")
        if band == "delta" and amp > 0.3:
            return NodeVote("Owl", "STABILISE", 0.7, f"delta rest {amp:.2f}")
        return NodeVote("Owl", "NEUTRAL", 0.5, f"band={band} amp={amp:.2f}")

    def _panda(self, vault: Any) -> NodeVote:
        """Panda analyses volume — checks total vault size."""
        size = len(vault) if hasattr(vault, "__len__") else 0
        max_size = int(getattr(vault, "max_size", 10000) or 10000)
        fill_ratio = size / max(max_size, 1)
        if fill_ratio > 0.8:
            return NodeVote("Panda", "STABILISE", 0.7, f"vault {fill_ratio:.0%} full")
        if fill_ratio > 0.3:
            return NodeVote("Panda", "BUY", 0.7, f"vault {fill_ratio:.0%} full")
        return NodeVote("Panda", "NEUTRAL", 0.4, f"vault {fill_ratio:.0%} full")

    def _cargoship(self, vault: Any) -> NodeVote:
        """CargoShip tracks macro Γ = mean cortex amplitude."""
        cortex = getattr(vault, "cortex_snapshot", {}) or {}
        if not cortex:
            return NodeVote("CargoShip", "NEUTRAL", 0.4, "no cortex data")
        mean_amp = sum(cortex.values()) / max(len(cortex), 1)
        if mean_amp > 0.4:
            return NodeVote("CargoShip", "BUY", 0.7, f"macro Γ={mean_amp:.2f}")
        if mean_amp < 0.1:
            return NodeVote("CargoShip", "STABILISE", 0.6, f"macro Γ={mean_amp:.2f}")
        return NodeVote("CargoShip", "NEUTRAL", 0.5, f"macro Γ={mean_amp:.2f}")

    def _clownfish(self, vault: Any) -> NodeVote:
        """Clownfish counter-trends — looks for anomalies in dominant chakra."""
        chakra = str(getattr(vault, "dominant_chakra", "love") or "love")
        if chakra in ("love", "connection"):
            return NodeVote("Clownfish", "BUY", 0.7, f"chakra={chakra}")
        if chakra in ("foundation", "liberation"):
            return NodeVote("Clownfish", "STABILISE", 0.6, f"chakra={chakra}")
        if chakra == "crown":
            return NodeVote("Clownfish", "RALLY", 0.8, f"chakra={chakra}")
        return NodeVote("Clownfish", "NEUTRAL", 0.5, f"chakra={chakra}")

    # ─────────────────────────────────────────────────────────────────────
    # Tally
    # ─────────────────────────────────────────────────────────────────────

    def _tally(self, votes: List[NodeVote]):
        """
        Return (consensus, agreeing_count, global_confidence).

        Rules:
            < 5 agree → NEUTRAL at 0.3
            5–7 agree → majority at 0.7
            8–9 agree → majority at 0.95
        """
        counter = Counter(v.verdict for v in votes)
        if not counter:
            return "NEUTRAL", 0, 0.3

        verdict, count = counter.most_common(1)[0]

        if count < 5:
            return "NEUTRAL", count, 0.3
        if count <= 7:
            return verdict, count, 0.7
        return verdict, count, 0.95

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    @property
    def last_result(self) -> Optional[AurisVoteResult]:
        return self._last_result

    def get_status(self) -> Dict[str, Any]:
        last = self._last_result
        return {
            "total_votes": self._total_votes,
            "nodes": NODES,
            "last_consensus": last.consensus if last else None,
            "last_confidence": round(last.confidence, 4) if last else None,
            "last_agreeing": last.agreeing if last else None,
            "last_lighthouse": last.lighthouse_cleared if last else None,
        }
