#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AUREON PLAY-BOARD OPTIMIZER — DYNAMIC STRATEGY SELECTOR            ║
║                                                                              ║
║  The organism holds all plays in central knowledge. At any moment it scores  ║
║  every play against live market regime, news, planetary/geo signals, and     ║
║  harmonic state, then selects the best play (or composes fragments of        ║
║  several plays) for the active symbol.                                       ║
║                                                                              ║
║  Output: aureon_radar/state/play_board_plan.json                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import math
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_RADAR_ROOT = Path(__file__).resolve().parent
_STATE_DIR = _RADAR_ROOT / "state"
_STATE_DIR.mkdir(parents=True, exist_ok=True)
_OUT_PATH = _STATE_DIR / "play_board_plan.json"

# Input state paths
_VOLATILITY_SCAN_PATH = _STATE_DIR / "volatility_scan.json"
_AGENCY_REPORT_PATH = _RADAR_ROOT.parent / "aureon_fusion" / "state" / "queen_mind" / "agency_company_report.json"
_HNC_STATE_PATH = _RADAR_ROOT.parent / "aureon_fusion" / "state" / "hnc_core_state.json"
_AURIS_PATH = _STATE_DIR / "auris_nodes.json"
_DREAMT_PLAYS_PATH = _STATE_DIR / "dreamt_plays.json"
_HOMING_TARGET_PATH = _STATE_DIR / "homing_target.json"
_FUSED_SIGNALS_PATH = _RADAR_ROOT / "fused_signals.jsonl"
_PLANETARY_SIGNALS_PATH = _RADAR_ROOT / "planetary_signals.jsonl"

# Vocabulary
_LONG_NAMES = {"LONG", "BUY", "BULLISH"}
_SHORT_NAMES = {"SHORT", "SELL", "BEARISH"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return payload if isinstance(payload, dict) else default
    except Exception:
        pass
    return default


def _finite(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    return None


def _normalize_direction(d: Any) -> str:
    s = str(d or "").strip().upper()
    if s in _LONG_NAMES:
        return "LONG"
    if s in _SHORT_NAMES:
        return "SHORT"
    return "NEUTRAL"


def _read_signal_file(path: Path, ttl_sec: float = 300.0) -> Dict[str, Dict[str, Any]]:
    """Read latest fresh signals from a JSONL signal file."""
    signals: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return signals
    now = time.time()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sig = json.loads(line)
                except Exception:
                    continue
                sym = str(sig.get("symbol") or "").upper()
                if not sym:
                    continue
                ts = sig.get("timestamp")
                if ts:
                    try:
                        ts_norm = str(ts).replace("Z", "+00:00")
                        age = now - datetime.fromisoformat(ts_norm).timestamp()
                    except Exception:
                        age = float("inf")
                else:
                    age = float("inf")
                if age <= ttl_sec:
                    signals[sym] = sig
    except Exception:
        pass
    return signals


@dataclass
class PlayFragment:
    """A single strategy fragment that can be selected or combined."""
    name: str
    archetype: str
    description: str
    direction: str
    # Conditions this fragment prefers (0..1 each)
    regime_fit: Dict[str, float] = field(default_factory=dict)
    # Score weights
    volatility_weight: float = 0.0
    momentum_weight: float = 0.0
    mean_revert_weight: float = 0.0
    news_weight: float = 0.0
    planetary_weight: float = 0.0
    harmonic_weight: float = 0.0
    # Execution params when this fragment is selected
    target_style: str = "micro"       # micro | momentum | swing
    dtp_activation_gbp: float = 0.01
    dtp_trail_pct: float = 0.005
    max_hold_minutes: int = 10
    size_multiplier: float = 1.0
    requires_shadow: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# PLAY REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

_PLAY_REGISTRY: List[PlayFragment] = [
    PlayFragment(
        name="scalp_micro_tick",
        archetype="scalping",
        description="Penny-profit micro-scalp on high-confidence volatility.",
        direction="NEUTRAL",
        regime_fit={"high_volatility": 0.9, "trending": 0.4, "ranging": 0.7},
        volatility_weight=0.8,
        momentum_weight=0.3,
        target_style="micro",
        dtp_activation_gbp=0.01,
        dtp_trail_pct=0.005,
        max_hold_minutes=10,
        size_multiplier=1.0,
        requires_shadow=True,
    ),
    PlayFragment(
        name="momentum_burst_capture",
        archetype="momentum",
        description="Ride a confirmed momentum burst with wider profit target.",
        direction="NEUTRAL",
        regime_fit={"trending": 0.9, "high_volatility": 0.7, "breakout": 0.8},
        volatility_weight=0.5,
        momentum_weight=0.9,
        news_weight=0.4,
        target_style="momentum",
        dtp_activation_gbp=0.10,
        dtp_trail_pct=0.01,
        max_hold_minutes=60,
        size_multiplier=1.5,
        requires_shadow=False,
    ),
    PlayFragment(
        name="mean_revert_snap",
        archetype="mean_reversion",
        description="Fade an extended move back toward harmonic mean.",
        direction="NEUTRAL",
        regime_fit={"ranging": 0.8, "overextended": 0.9, "high_volatility": 0.6},
        mean_revert_weight=0.9,
        harmonic_weight=0.6,
        target_style="momentum",
        dtp_activation_gbp=0.05,
        dtp_trail_pct=0.008,
        max_hold_minutes=45,
        size_multiplier=1.0,
        requires_shadow=True,
    ),
    PlayFragment(
        name="news_spike_defense",
        archetype="event",
        description="React to news/geo shock with quick in/out and dead-man exit.",
        direction="NEUTRAL",
        regime_fit={"news_spike": 0.95, "high_volatility": 0.8, "geo_active": 0.7},
        news_weight=0.95,
        volatility_weight=0.6,
        target_style="micro",
        dtp_activation_gbp=0.02,
        dtp_trail_pct=0.003,
        max_hold_minutes=5,
        size_multiplier=1.2,
        requires_shadow=False,
    ),
    PlayFragment(
        name="planetary_aligned_swing",
        archetype="planetary",
        description="Hold while planetary/harmonic conditions align with price.",
        direction="NEUTRAL",
        regime_fit={"planetary_aligned": 0.9, "harmonic_strong": 0.8, "trending": 0.5},
        planetary_weight=0.9,
        harmonic_weight=0.8,
        target_style="swing",
        dtp_activation_gbp=0.20,
        dtp_trail_pct=0.015,
        max_hold_minutes=180,
        size_multiplier=1.0,
        requires_shadow=True,
    ),
    PlayFragment(
        name="harmonic_lidar_precision",
        archetype="harmonic",
        description="Use harmonic lidar resonance for precision entry/exit.",
        direction="NEUTRAL",
        regime_fit={"harmonic_strong": 0.95, "ranging": 0.6, "trending": 0.5},
        harmonic_weight=0.95,
        volatility_weight=0.4,
        target_style="momentum",
        dtp_activation_gbp=0.05,
        dtp_trail_pct=0.008,
        max_hold_minutes=30,
        size_multiplier=1.3,
        requires_shadow=True,
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET CONTEXT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketContext:
    symbol: str = ""
    direction: str = "NEUTRAL"
    volatility_score: float = 0.0
    momentum_score: float = 0.0
    mean_revert_score: float = 0.0
    news_score: float = 0.0
    planetary_score: float = 0.0
    harmonic_score: float = 0.0
    hnc_gamma: Optional[float] = None
    auris_coherence: Optional[float] = None
    regime: str = "unknown"
    time_of_day_minutes: int = 0
    asset_class: str = "commodity"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlayBoardOptimizer:
    """Select and compose the best strategy plays for the current moment."""

    def __init__(self):
        self.registry = _PLAY_REGISTRY

    def _load_inputs(self) -> Dict[str, Any]:
        return {
            "volatility": _read_json(_VOLATILITY_SCAN_PATH, {}) or {},
            "agency": _read_json(_AGENCY_REPORT_PATH, {}) or {},
            "hnc": _read_json(_HNC_STATE_PATH, {}) or {},
            "auris": _read_json(_AURIS_PATH, {}) or {},
            "dreams": _read_json(_DREAMT_PLAYS_PATH, {}) or {},
            "homing": _read_json(_HOMING_TARGET_PATH, {}) or {},
            "fused": _read_signal_file(_FUSED_SIGNALS_PATH),
            "planetary": _read_signal_file(_PLANETARY_SIGNALS_PATH),
        }

    def _hnc_gamma(self, hnc: Dict[str, Any]) -> Optional[float]:
        for key in ("coherence_gamma", "gamma", "coherence", "Γ"):
            g = _finite(hnc.get(key))
            if g is not None:
                return g
        return None

    def _auris_coherence(self, auris: Dict[str, Any]) -> Optional[float]:
        nodes = auris.get("nodes") or {}
        vals = [_finite(v.get("coherence") or v.get("score"))
                for v in nodes.values() if isinstance(v, dict)]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    def _volatility_context(self, symbol: str, vol_scan: Dict[str, Any]) -> Tuple[float, str]:
        ranking = vol_scan.get("ranking") or []
        for cand in ranking:
            if isinstance(cand, dict) and str(cand.get("symbol") or "").upper() == symbol:
                return float(_finite(cand.get("volatility_score")) or 0.0), str(cand.get("category") or "")
        top = vol_scan.get("top_target") or {}
        if str(top.get("symbol") or "").upper() == symbol:
            return float(_finite(top.get("volatility_score")) or 0.0), str(top.get("category") or "")
        return 0.0, ""

    def _price_history_metrics(self, prices: Optional[List[float]]) -> Dict[str, float]:
        """Compute volatility, momentum, and mean-reversion scores from live prices."""
        empty = {"volatility": 0.0, "momentum": 0.0, "mean_revert": 0.0}
        if not prices or len(prices) < 10:
            return empty
        clean = [float(p) for p in prices if isinstance(p, (int, float)) and p > 0]
        if len(clean) < 10:
            return empty

        recent = clean[-min(42, len(clean)):]
        returns = [(recent[i] - recent[i - 1]) / recent[i - 1]
                   for i in range(1, len(recent))]
        if len(returns) < 2:
            return empty

        # Normalised intraday volatility: typical hourly std ~0.0007 -> modest score
        vol_norm = min(1.0, statistics.stdev(returns) * 15.0)

        # Momentum from recent price excursion, scaled so ~5% move = 1.0
        lookback = max(len(clean) // 4, 5)
        start = clean[-lookback]
        end = clean[-1]
        mom_norm = min(1.0, abs(end - start) / start * 20.0)

        # Mean-reversion: z-score vs recent 20-bar window
        window = clean[-min(20, len(clean)):]
        mean = statistics.mean(window)
        stdev = statistics.stdev(window) if len(window) > 1 else 0.0
        z_score = (end - mean) / stdev if stdev > 0 else 0.0
        mean_rev_norm = min(1.0, abs(z_score) / 2.0)

        return {
            "volatility": vol_norm,
            "momentum": mom_norm,
            "mean_revert": mean_rev_norm,
        }

    def _build_context(
        self,
        symbol: str,
        inputs: Dict[str, Any],
        price_history: Optional[List[float]] = None,
        signal_confidence: float = 0.0,
        direction: Optional[str] = None,
        volatility: Optional[float] = None,
        money_flow: Optional[float] = None,
    ) -> MarketContext:
        vol_scan = inputs["volatility"]
        agency = inputs["agency"]
        hnc = inputs["hnc"]
        auris = inputs["auris"]
        fused = inputs["fused"]
        planetary = inputs["planetary"]
        dreams = inputs["dreams"]

        # Caller-supplied telemetry is freshest
        hist_metrics = self._price_history_metrics(price_history)
        vol_score, category = self._volatility_context(symbol, vol_scan)
        if volatility is not None:
            # Scanner volatility is annualised; tanh maps typical 0.2-1.5 range to 0-1
            vol_score = max(vol_score, min(1.0, math.tanh(abs(float(volatility)))))
        vol_score = max(vol_score, hist_metrics["volatility"])

        # Direction from caller override, then fused / agency / planetary consensus
        direction = _normalize_direction(direction) if direction else "NEUTRAL"
        conf = signal_confidence
        for sig in (fused.get(symbol), planetary.get(symbol)):
            if sig:
                c = _finite(sig.get("confidence")) or 0.0
                if c > conf:
                    conf = c
                if direction == "NEUTRAL":
                    direction = _normalize_direction(sig.get("direction"))
        agency_top = agency.get("top_target") or {}
        if str(agency_top.get("symbol") or "").upper() == symbol:
            c = _finite(agency.get("confidence")) or 0.0
            if c > conf:
                conf = c
            if direction == "NEUTRAL":
                direction = _normalize_direction(agency.get("consensus"))

        # Momentum: live telemetry + dreamt plays + money-flow pressure
        mom_score = max(hist_metrics["momentum"], conf)
        if money_flow is not None:
            mom_score = max(mom_score, abs(float(money_flow)))
        for p in (dreams.get("plays") or []):
            if str(p.get("symbol") or "").upper() == symbol:
                mom_score = max(mom_score, _finite(p.get("simulated", {}).get("p_reach")) or 0.0)
        mom_score = min(1.0, mom_score)

        # Mean-revert score: high if price is extended vs recent mean
        mean_rev_score = max(hist_metrics["mean_revert"], min(1.0, vol_score * 0.5))

        # News score: high when fused signals have source news/geo
        news_score = 0.0
        if symbol in fused:
            src = str(fused[symbol].get("source") or "").lower()
            if any(k in src for k in ("news", "geo", "event", "funding")):
                news_score = 0.8

        # Planetary score
        planetary_score = 0.0
        if symbol in planetary:
            planetary_score = _finite(planetary[symbol].get("confidence")) or 0.0

        # Harmonic score from auris + dreams
        harmonic_score = self._auris_coherence(auris) or 0.0
        for p in (dreams.get("plays") or []):
            if str(p.get("symbol") or "").upper() == symbol:
                if (p.get("archetype") or "").startswith(("phase_", "harmonic")):
                    harmonic_score = max(harmonic_score, _finite(p.get("simulated", {}).get("p_reach")) or 0.0)

        # Regime classification tuned for play-board selection
        gamma = self._hnc_gamma(hnc)
        if mom_score > 0.6 and vol_score > 0.3:
            regime = "breakout"
        elif mom_score > 0.5:
            regime = "trending"
        elif vol_score > 0.5 and mean_rev_score > 0.5:
            regime = "overextended"
        elif vol_score > 0.5:
            regime = "high_volatility"
        elif vol_score < 0.3 and mean_rev_score < 0.3:
            regime = "ranging"
        else:
            regime = "mixed"

        # Time of day (UTC minutes)
        now = datetime.now(timezone.utc)
        tod_min = now.hour * 60 + now.minute

        return MarketContext(
            symbol=symbol,
            direction=direction,
            volatility_score=vol_score,
            momentum_score=mom_score,
            mean_revert_score=mean_rev_score,
            news_score=news_score,
            planetary_score=planetary_score,
            harmonic_score=harmonic_score,
            hnc_gamma=gamma,
            auris_coherence=self._auris_coherence(auris),
            regime=regime,
            time_of_day_minutes=tod_min,
            asset_class=category or "commodity",
        )

    def _score_fragment(self, fragment: PlayFragment, ctx: MarketContext) -> float:
        """Score a play fragment against the market context."""
        # Direction agreement: 1.0 if fragment direction matches or is neutral
        frag_dir = _normalize_direction(fragment.direction)
        if frag_dir != "NEUTRAL" and frag_dir != ctx.direction:
            return 0.0

        # Regime fit
        regime_fit = fragment.regime_fit.get(ctx.regime, 0.3)

        # Signal-weighted score
        signal_score = (
            fragment.volatility_weight * ctx.volatility_score
            + fragment.momentum_weight * ctx.momentum_score
            + fragment.mean_revert_weight * ctx.mean_revert_score
            + fragment.news_weight * ctx.news_score
            + fragment.planetary_weight * ctx.planetary_score
            + fragment.harmonic_weight * ctx.harmonic_score
        )
        # Normalize by total weights to keep 0..1
        total_weight = (
            fragment.volatility_weight
            + fragment.momentum_weight
            + fragment.mean_revert_weight
            + fragment.news_weight
            + fragment.planetary_weight
            + fragment.harmonic_weight
        )
        if total_weight > 0:
            signal_score /= total_weight
        else:
            signal_score = 0.0

        # HNC coherence gate: below 0.25 we do not play
        if ctx.hnc_gamma is not None and ctx.hnc_gamma < 0.25:
            return 0.0

        # Combine regime fit and signal score
        score = 0.4 * regime_fit + 0.6 * signal_score

        # Boost if auris coherent
        if ctx.auris_coherence is not None and ctx.auris_coherence >= 0.6:
            score *= 1.1

        return min(1.0, max(0.0, score))

    def select_plays(
        self,
        symbol: str,
        price_history: Optional[List[float]] = None,
        signal_confidence: float = 0.0,
        direction: Optional[str] = None,
        volatility: Optional[float] = None,
        money_flow: Optional[float] = None,
    ) -> Tuple[MarketContext, List[Dict[str, Any]], Optional[PlayFragment]]:
        """Return context, scored fragments, and the selected primary play."""
        inputs = self._load_inputs()
        ctx = self._build_context(
            symbol,
            inputs,
            price_history=price_history,
            signal_confidence=signal_confidence,
            direction=direction,
            volatility=volatility,
            money_flow=money_flow,
        )

        scored = []
        for fragment in self.registry:
            score = self._score_fragment(fragment, ctx)
            if score > 0.0:
                d = fragment.to_dict()
                d["fit_score"] = round(score, 4)
                scored.append(d)

        scored.sort(key=lambda x: x["fit_score"], reverse=True)
        primary = None
        # Strong external signal lowers the bar so the organism actually plays
        threshold = 0.25 if signal_confidence >= 0.60 else 0.30
        if scored and scored[0]["fit_score"] >= threshold:
            primary = PlayFragment(**{k: v for k, v in scored[0].items() if k != "fit_score"})

        return ctx, scored, primary

    def build_plan(
        self,
        symbol: str,
        price_history: Optional[List[float]] = None,
        signal_confidence: float = 0.0,
        direction: Optional[str] = None,
        volatility: Optional[float] = None,
        money_flow: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Build the full play-board plan for a symbol.

        Optional live telemetry from the caller is preferred over stale files:
        price_history, signal_confidence, direction, volatility, money_flow.
        """
        ctx, scored, primary = self.select_plays(
            symbol,
            price_history=price_history,
            signal_confidence=signal_confidence,
            direction=direction,
            volatility=volatility,
            money_flow=money_flow,
        )

        # Compose auxiliary fragments: pieces of other plays that also fit
        auxiliaries = []
        if primary:
            for s in scored[1:4]:
                if s["fit_score"] >= 0.25 and s["archetype"] != primary.archetype:
                    auxiliaries.append({
                        "name": s["name"],
                        "archetype": s["archetype"],
                        "fit_score": s["fit_score"],
                        "borrowed_element": self._borrowed_element(s, primary),
                    })

        plan = {
            "ts": _utc_now_iso(),
            "symbol": symbol,
            "context": ctx.to_dict(),
            "scored_plays": scored,
            "primary_play": primary.to_dict() if primary else None,
            "auxiliary_fragments": auxiliaries,
            "execution": self._execution_plan(primary, auxiliaries),
        }
        return plan

    def _borrowed_element(self, fragment_dict: Dict[str, Any], primary: PlayFragment) -> str:
        """Describe what element of this fragment can be borrowed by the primary play."""
        if fragment_dict["news_weight"] > primary.news_weight:
            return "news_spike_exit"
        if fragment_dict["planetary_weight"] > primary.planetary_weight:
            return "planetary_timing_filter"
        if fragment_dict["mean_revert_weight"] > primary.mean_revert_weight:
            return "mean_revert_profit_target"
        if fragment_dict["harmonic_weight"] > primary.harmonic_weight:
            return "harmonic_lidar_entry"
        return "confirmation_signal"

    def _execution_plan(self, primary: Optional[PlayFragment], auxiliaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Translate selected play(s) into execution parameters."""
        if not primary:
            return {
                "action": "NO_PLAY",
                "target_style": "micro",
                "dtp_activation_gbp": 0.01,
                "dtp_trail_pct": 0.005,
                "max_hold_minutes": 10,
                "size_multiplier": 1.0,
                "requires_shadow": True,
                "reason": "no play scored above threshold",
            }

        # If auxiliaries suggest news/geo risk, tighten the dead-man switch
        news_borrowed = any(a["borrowed_element"] == "news_spike_exit" for a in auxiliaries)
        planetary_borrowed = any(a["borrowed_element"] == "planetary_timing_filter" for a in auxiliaries)

        dtp_activation = primary.dtp_activation_gbp
        dtp_trail = primary.dtp_trail_pct
        max_hold = primary.max_hold_minutes
        size_mult = primary.size_multiplier

        if news_borrowed:
            dtp_activation = min(dtp_activation, 0.02)
            dtp_trail = min(dtp_trail, 0.003)
            max_hold = min(max_hold, 5)

        if planetary_borrowed and dtp_activation < 0.05:
            dtp_activation = 0.05

        return {
            "action": "EXECUTE",
            "target_style": primary.target_style,
            "dtp_activation_gbp": dtp_activation,
            "dtp_trail_pct": dtp_trail,
            "max_hold_minutes": max_hold,
            "size_multiplier": size_mult,
            "requires_shadow": primary.requires_shadow,
            "primary_archetype": primary.archetype,
            "reason": f"{primary.name} selected; {len(auxiliaries)} auxiliary fragments borrowed",
        }

    def write_plan(self, symbol: str) -> Dict[str, Any]:
        plan = self.build_plan(symbol)
        try:
            with open(_OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
        except Exception as exc:
            print(f"[PLAY_BOARD] failed to write plan: {exc}")
        return plan


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aureon Play-Board Optimizer")
    parser.add_argument("--symbol", default="NATURALGAS", help="Symbol to build plan for")
    args = parser.parse_args()

    opt = PlayBoardOptimizer()
    plan = opt.write_plan(args.symbol.upper())
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
