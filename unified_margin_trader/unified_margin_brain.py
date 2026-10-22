"""Unified margin decision brain.

The margin trader already gathers many specialist signals: live flow,
probability, timeline, harmonic alignment, fee models, dynamic collateral,
and temporal trade cognition. This module turns those loose signals into one
auditable decision object.

It never places orders. It only answers: is this candidate worth shadowing or
waiting on, why, and what ETA/risk/probability made that decision?
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Sequence


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except (TypeError, ValueError):
        pass
    return default


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, _finite(value, low)))


def _as_mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _human_time(epoch: Optional[float] = None) -> Dict[str, Any]:
    ts = time.time() if epoch is None else float(epoch)
    dt = datetime.fromtimestamp(ts).astimezone()
    return {
        "epoch": round(ts, 3),
        "iso": dt.isoformat(timespec="seconds"),
        "date": dt.date().isoformat(),
        "time": dt.strftime("%H:%M:%S"),
        "weekday": dt.strftime("%A"),
        "minute_of_day": dt.hour * 60 + dt.minute,
        "timezone": dt.tzname() or "",
    }


def _normalise_population_score(score: float, population_scores: Sequence[float]) -> float:
    values = [_finite(v) for v in population_scores if math.isfinite(_finite(v, float("nan")))]
    if not values:
        return _clamp(score / 10.0)
    low = min(values)
    high = max(values)
    if high <= low:
        return _clamp(score / max(abs(high), 10.0))
    return _clamp((score - low) / (high - low))


def _mean(values: Sequence[float], default: float = 0.0) -> float:
    clean = [float(v) for v in values if math.isfinite(float(v))]
    if not clean:
        return default
    return sum(clean) / len(clean)


@dataclass(frozen=True)
class MarginBrainConfig:
    min_confidence: float = 0.40
    min_probability: float = 0.45
    max_risk: float = 0.82
    max_eta_minutes: float = 15.0
    hard_eta_minutes: float = 45.0
    min_route_to_profit: float = 0.10
    min_goal_score: float = 0.05


@dataclass
class MarginBrainDecision:
    pair: str
    side: str
    approved: bool
    action: str
    confidence: float
    probability: float
    coherence: float
    risk: float
    urgency: float
    eta_minutes: float
    score: float
    adjusted_score: float
    required_move_pct: float
    estimated_fees: float
    route_to_profit: float
    goal_score: float
    decided_at: Dict[str, Any]
    vetoes: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    sources: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": self.pair,
            "side": self.side,
            "approved": self.approved,
            "action": self.action,
            "confidence": round(self.confidence, 6),
            "probability": round(self.probability, 6),
            "coherence": round(self.coherence, 6),
            "risk": round(self.risk, 6),
            "urgency": round(self.urgency, 6),
            "eta_minutes": round(self.eta_minutes, 6),
            "score": round(self.score, 6),
            "adjusted_score": round(self.adjusted_score, 6),
            "required_move_pct": round(self.required_move_pct, 6),
            "estimated_fees": round(self.estimated_fees, 6),
            "route_to_profit": round(self.route_to_profit, 6),
            "goal_score": round(self.goal_score, 6),
            "decided_at": dict(self.decided_at),
            "vetoes": list(self.vetoes),
            "reasons": list(self.reasons),
            "sources": dict(self.sources),
        }


class UnifiedMarginDecisionBrain:
    """Fuse margin signals into an auditable approve/wait/reject decision."""

    def __init__(self, config: Optional[MarginBrainConfig] = None) -> None:
        self.config = config or MarginBrainConfig()

    def evaluate_candidate(
        self,
        candidate: Mapping[str, Any],
        cognition_context: Optional[Mapping[str, Any]] = None,
        population_scores: Sequence[float] = (),
        now: Optional[float] = None,
    ) -> MarginBrainDecision:
        ctx = dict(cognition_context or {})
        sources = _as_mapping(ctx.get("sources"))
        projection = _as_mapping(sources.get("projection") or ctx.get("projection"))
        timeline = _as_mapping(sources.get("timeline") or ctx.get("timeline"))
        alignment = _as_mapping(sources.get("alignment") or ctx.get("alignment"))

        pair = str(candidate.get("pair") or ctx.get("pair") or "")
        side = str(candidate.get("side") or ctx.get("side") or "buy").lower()
        score = _finite(candidate.get("score"))
        required_move_pct = max(0.0, _finite(candidate.get("required_move_pct", ctx.get("required_move_pct"))))
        estimated_fees = max(0.0, _finite(candidate.get("estimated_fees")))
        spread_pct = max(0.0, _finite(candidate.get("spread_pct")))
        eta_minutes = _finite(candidate.get("eta_minutes", ctx.get("eta_minutes")), 999.0)
        route_to_profit = max(0.0, _finite(candidate.get("route_to_profit", ctx.get("route_to_profit"))))
        goal_score = max(0.0, _finite(candidate.get("goal_score", ctx.get("goal_score"))))
        profit_target_usd = max(0.0, _finite(candidate.get("profit_target_usd", ctx.get("profit_target_usd"))))

        score_conf = _normalise_population_score(score, population_scores)
        goal_conf = _clamp(goal_score / 3.5)
        route_conf = _clamp(route_to_profit / (route_to_profit + 1.0)) if route_to_profit > 0 else 0.0
        cognition_conf = _clamp(ctx.get("confidence"), 0.05, 0.99)
        projection_conf = _clamp(projection.get("confidence"))
        live_match = _clamp(projection.get("live_match"))
        timeline_conf = _clamp(timeline.get("confidence"))
        alignment_conf = self._normalise_alignment(alignment.get("score"))

        eta_valid = eta_minutes > 0.0 and eta_minutes < 999.0
        eta_conf = self._eta_confidence(eta_minutes) if eta_valid else 0.0

        move_risk = _clamp(required_move_pct / 2.0)
        spread_risk = _clamp(spread_pct / 0.50)
        time_risk = _clamp(eta_minutes / max(self.config.hard_eta_minutes, 1.0)) if eta_valid else 1.0
        if profit_target_usd > 0:
            cost_risk = _clamp(estimated_fees / max(profit_target_usd + estimated_fees, 1e-9))
        else:
            cost_risk = _clamp(estimated_fees / 1.0)

        base_probability = _clamp(ctx.get("probability"), 0.0, 0.99)
        support = _mean([
            score_conf,
            goal_conf,
            route_conf,
            eta_conf,
            cognition_conf,
            projection_conf,
            live_match,
            timeline_conf,
            alignment_conf,
        ], default=0.0)
        confidence = _clamp(
            support * 0.45
            + cognition_conf * 0.20
            + score_conf * 0.15
            + route_conf * 0.10
            + (1.0 - move_risk) * 0.10
        )
        probability = max(base_probability, _clamp(0.35 + confidence * 0.55))
        risk = _clamp(
            move_risk * 0.30
            + spread_risk * 0.16
            + time_risk * 0.22
            + cost_risk * 0.16
            + (1.0 - probability) * 0.16
        )
        coherence = _clamp(support * 0.70 + (1.0 - risk) * 0.30)
        urgency = _clamp(eta_conf * 0.45 + route_conf * 0.35 + live_match * 0.20)

        vetoes: list[str] = []
        if not eta_valid:
            vetoes.append("eta_unbounded")
        elif eta_minutes > self.config.hard_eta_minutes:
            vetoes.append("eta_too_slow")
        if confidence < self.config.min_confidence:
            vetoes.append("low_confidence")
        if probability < self.config.min_probability:
            vetoes.append("low_probability")
        if risk > self.config.max_risk:
            vetoes.append("risk_too_high")
        if route_to_profit < self.config.min_route_to_profit and goal_score < self.config.min_goal_score:
            vetoes.append("weak_route_to_profit")
        if required_move_pct <= 0:
            vetoes.append("missing_required_move")

        approved = not vetoes
        action = "approve_shadow" if approved else "wait"
        adjusted_score = score * (0.80 + coherence * 0.35 + urgency * 0.20 - risk * 0.25)
        if not approved:
            adjusted_score = min(adjusted_score, score)

        reasons = self._build_reasons(
            approved=approved,
            vetoes=vetoes,
            confidence=confidence,
            probability=probability,
            risk=risk,
            eta_minutes=eta_minutes,
            route_to_profit=route_to_profit,
        )

        return MarginBrainDecision(
            pair=pair,
            side=side,
            approved=approved,
            action=action,
            confidence=confidence,
            probability=probability,
            coherence=coherence,
            risk=risk,
            urgency=urgency,
            eta_minutes=eta_minutes,
            score=score,
            adjusted_score=adjusted_score,
            required_move_pct=required_move_pct,
            estimated_fees=estimated_fees,
            route_to_profit=route_to_profit,
            goal_score=goal_score,
            decided_at=_human_time(now),
            vetoes=vetoes,
            reasons=reasons,
            sources={
                "score_confidence": round(score_conf, 6),
                "goal_confidence": round(goal_conf, 6),
                "route_confidence": round(route_conf, 6),
                "eta_confidence": round(eta_conf, 6),
                "cognition_confidence": round(cognition_conf, 6),
                "projection_confidence": round(projection_conf, 6),
                "live_match": round(live_match, 6),
                "timeline_confidence": round(timeline_conf, 6),
                "alignment_confidence": round(alignment_conf, 6),
                "move_risk": round(move_risk, 6),
                "spread_risk": round(spread_risk, 6),
                "time_risk": round(time_risk, 6),
                "cost_risk": round(cost_risk, 6),
            },
        )

    def _eta_confidence(self, eta_minutes: float) -> float:
        eta = max(0.0, _finite(eta_minutes))
        soft = max(1.0, float(self.config.max_eta_minutes))
        hard = max(soft, float(self.config.hard_eta_minutes))
        if eta <= soft:
            return _clamp(0.65 + 0.35 * (1.0 - eta / soft))
        return _clamp(0.65 * (1.0 - (eta - soft) / max(hard - soft, 1.0)))

    @staticmethod
    def _normalise_alignment(value: Any) -> float:
        raw = _finite(value)
        if 0.0 <= raw <= 1.0:
            return raw
        return _clamp((raw + 2.0) / 4.0)

    @staticmethod
    def _build_reasons(
        *,
        approved: bool,
        vetoes: Sequence[str],
        confidence: float,
        probability: float,
        risk: float,
        eta_minutes: float,
        route_to_profit: float,
    ) -> list[str]:
        if approved:
            return [
                f"approved: confidence={confidence:.2f} probability={probability:.2f}",
                f"eta={eta_minutes:.2f}m route_to_profit={route_to_profit:.2f}",
                f"risk={risk:.2f} inside threshold",
            ]
        reasons = [f"wait: {veto}" for veto in vetoes]
        reasons.append(
            f"observed confidence={confidence:.2f} probability={probability:.2f} risk={risk:.2f}"
        )
        return reasons
