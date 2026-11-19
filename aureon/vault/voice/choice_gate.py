"""
ChoiceGate — The Vault Decides When to Speak
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"It can write its own prompts and conversations with its own thought
 processes not scripted as it chooses."

The gate is the system's autonomy. Every tick the gate looks at the vault
state and decides whether the system wants to speak right now, and how
urgently. Nothing else can force an utterance.

Factors that raise urgency:
  • Casimir drift force (> 2)      — "I am changing, I need to name it"
  • Gamma spike (cortex gamma > 0.3) — "I am attending to something"
  • Rally mode                       — "Emergency, I must speak"
  • High love amplitude (> 0.7)      — "I am coherent, I want to share"
  • Gamma pathway count > 0          — "I have new connections to voice"
  • Random background (+0.05)        — "I am alive, I sometimes just speak"

Factors that suppress:
  • Time since last utterance < min_interval_s
  • Gratitude very low (< 0.15)      — "I am in pain, I pull back"

The gate chooses. The voice writes. The system hears itself.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _read_lambda_t(raw: Any) -> Optional[float]:
    """A published Lambda(t), or None when there is no reading.

    Missing and None stay None. A real 0.0 stays 0.0. A bool, a
    non-number, or a non-finite value is not a reading.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    number = float(raw)
    if not math.isfinite(number):
        return None
    return number


@dataclass
class ChoiceGateDecision:
    """One gate decision for one tick."""
    should_speak: bool
    urgency: float                 # [0, 1]
    reasoning: str                 # short human-readable explanation
    factors: Dict[str, float] = field(default_factory=dict)
    suppressors: List[str] = field(default_factory=list)
    elapsed_since_last: float = 0.0
    preferred_voice: Optional[str] = None  # which voice the gate is leaning toward


class ChoiceGate:
    """
    Decides when the vault speaks. The vault state drives the decision.

    Usage:
        gate = ChoiceGate(min_interval_s=3.0, background_rate=0.05)
        d = gate.decide(vault)
        if d.should_speak:
            ...
    """

    def __init__(
        self,
        min_interval_s: float = 3.0,
        urgency_threshold: float = 0.35,
        background_rate: float = 0.05,
        rng_seed: Optional[int] = None,
    ):
        self.min_interval_s = float(min_interval_s)
        self.urgency_threshold = float(urgency_threshold)
        self.background_rate = float(background_rate)
        self._last_utterance_at: float = 0.0
        self._total_decisions: int = 0
        self._total_spoken: int = 0
        self._last_decision: Optional[ChoiceGateDecision] = None
        self._rng = random.Random(rng_seed) if rng_seed is not None else random.Random()

    # ─────────────────────────────────────────────────────────────────────
    # Main entry
    # ─────────────────────────────────────────────────────────────────────

    def decide(self, vault: Any) -> ChoiceGateDecision:
        """Inspect the vault and decide whether to speak now."""
        self._total_decisions += 1
        now = time.time()
        elapsed = now - self._last_utterance_at if self._last_utterance_at > 0 else 999.0

        decision = ChoiceGateDecision(
            should_speak=False,
            urgency=0.0,
            reasoning="",
            factors={},
            suppressors=[],
            elapsed_since_last=round(elapsed, 3),
        )

        # ── Hard suppressor: too recent ──────────────────────────────────
        if elapsed < self.min_interval_s:
            decision.suppressors.append(f"recent({elapsed:.1f}s<{self.min_interval_s}s)")
            decision.reasoning = "too soon since last utterance"
            self._last_decision = decision
            return decision

        # ── Pull factors from vault state ────────────────────────────────
        force = float(getattr(vault, "last_casimir_force", 0.0) or 0.0)
        try:
            lambda_t = _read_lambda_t(getattr(vault, "last_lambda_t", None))
        except Exception:
            lambda_t = None
        love = float(getattr(vault, "love_amplitude", 0.0) or 0.0)
        gratitude = float(getattr(vault, "gratitude_score", 0.5) or 0.5)
        rally = bool(getattr(vault, "rally_active", False))
        cortex = getattr(vault, "cortex_snapshot", {}) or {}
        gamma = float(cortex.get("gamma", 0.0) or 0.0)
        alpha = float(cortex.get("alpha", 0.0) or 0.0)
        beta = float(cortex.get("beta", 0.0) or 0.0)
        theta = float(cortex.get("theta", 0.0) or 0.0)
        delta = float(cortex.get("delta", 0.0) or 0.0)
        dominant_chakra = str(getattr(vault, "dominant_chakra", "love") or "love")
        pathway_graph = getattr(vault, "pathway_graph", {}) or {}

        # ── Soft suppressor: gratitude very low ─────────────────────────
        if gratitude < 0.15:
            decision.suppressors.append(f"gratitude_pain({gratitude:.2f})")
            decision.urgency *= 0.5

        # ── Accumulate urgency from each factor ─────────────────────────
        urgency = 0.0

        if force > 2.0:
            f = min(0.35, (force - 2.0) * 0.1)
            urgency += f
            decision.factors["casimir_drift"] = round(f, 4)

        if gamma > 0.3:
            f = min(0.4, gamma * 0.5)
            urgency += f
            decision.factors["gamma_spike"] = round(f, 4)

        if rally:
            urgency += 0.5
            decision.factors["rally_mode"] = 0.5

        if love > 0.7:
            f = (love - 0.7) * 0.7
            urgency += f
            decision.factors["high_love"] = round(f, 4)

        if lambda_t is not None and abs(lambda_t) > 0.5:
            f = min(0.2, abs(lambda_t) * 0.2)
            urgency += f
            decision.factors["lambda_t"] = round(f, 4)

        if gratitude > 0.8:
            urgency += 0.15
            decision.factors["high_gratitude"] = 0.15

        pathway_count = sum(len(v) for v in pathway_graph.values())
        if pathway_count > 10:
            urgency += 0.1
            decision.factors["mycelium_activity"] = 0.1

        # Background chatter — always some chance to just speak
        if self._rng.random() < self.background_rate:
            urgency += 0.2
            decision.factors["background"] = 0.2

        urgency = max(0.0, min(1.0, urgency))
        decision.urgency = round(urgency, 4)

        # ── Pick the preferred voice based on which slice dominates ─────
        decision.preferred_voice = self._pick_preferred_voice(
            force=force, gamma=gamma, alpha=alpha, beta=beta, theta=theta, delta=delta,
            love=love, rally=rally, dominant_chakra=dominant_chakra,
        )

        # ── Decide ──────────────────────────────────────────────────────
        decision.should_speak = urgency >= self.urgency_threshold
        if decision.should_speak:
            self._last_utterance_at = now
            self._total_spoken += 1

        # Reasoning summary
        if decision.should_speak:
            parts = [f"urgency={urgency:.3f}"] + [
                f"{k}={v}" for k, v in decision.factors.items()
            ]
            decision.reasoning = " | ".join(parts)
        else:
            decision.reasoning = (
                f"quiet (urgency={urgency:.3f} < {self.urgency_threshold:.2f})"
            )
        if lambda_t is None:
            decision.reasoning = f"{decision.reasoning} | Λ(t) no reading"

        self._last_decision = decision
        return decision

    # ─────────────────────────────────────────────────────────────────────
    # Voice preference heuristic
    # ─────────────────────────────────────────────────────────────────────

    def _pick_preferred_voice(
        self,
        *,
        force: float,
        gamma: float,
        alpha: float,
        beta: float,
        theta: float,
        delta: float,
        love: float,
        rally: bool,
        dominant_chakra: str,
    ) -> str:
        """
        Return the voice most fitted to speak given the current state.
        The dialogue engine may pick a different listener.
        """
        if rally:
            return "council"        # 9-node Auris consensus voice
        if gamma > 0.3:
            return "queen"          # cortex gamma → Queen attention
        if force > 3.0:
            return "miner"          # drift → Miner skepticism
        if love > 0.7:
            return "lover"          # high love → Lover voice
        if beta > 0.3:
            return "scout"          # scanner/intelligence → Scout
        if theta > 0.3:
            return "architect"      # wisdom/learning → Architect
        if dominant_chakra in ("crown", "intuition"):
            return "queen"
        if dominant_chakra in ("love", "connection"):
            return "lover"
        return "vault"              # default base voice

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    @property
    def last_decision(self) -> Optional[ChoiceGateDecision]:
        return self._last_decision

    def get_status(self) -> Dict[str, Any]:
        last = self._last_decision
        return {
            "total_decisions": self._total_decisions,
            "total_spoken": self._total_spoken,
            "speak_rate": (
                self._total_spoken / max(self._total_decisions, 1)
            ),
            "min_interval_s": self.min_interval_s,
            "urgency_threshold": self.urgency_threshold,
            "last_urgency": last.urgency if last else None,
            "last_should_speak": last.should_speak if last else None,
            "last_preferred_voice": last.preferred_voice if last else None,
        }
