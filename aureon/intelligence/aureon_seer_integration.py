#!/usr/bin/env python3
"""
AUREON QUADRUMVIRATE CONSENSUS - Four-Pillar Ecosystem Integration
=====================================================
"Four minds, one truth. The Queen, King, Seer and Lyra must all agree.
 When is the right moment? They confer, they calculate, they decide together."

Wires ALL FOUR Pillars into the Aureon trading ecosystem:
  - Feeds live market data to Seer's 5 Oracles and Lyra's 6 Chambers
  - Runs FOUR-PILLAR freeway consensus (Queen + King + Seer + Lyra)
  - Temporal Consensus Engine: "WHEN is the best time?" not just "should we?"
  - Probability Field Collapse: each confirming signal narrows the outcome
  - Deep Propagation: iterative multi-wave cognitive convergence
  - Broadcasts consensus events to the ThoughtBus

THE QUADRUMVIRATE (Four Pillars):
  Queen (aureon_queen_hive_mind.py)  - Trading cognition (11+ systems = VETO power)
  King  (king_accounting.py)         - Financial truth (5 Royal Deciphers)
  Seer  (aureon_seer.py)             - Cosmic coherence (5 Oracles)
  Lyra  (aureon_lyra.py)             - Emotional frequency (6 Chambers, 22+ systems)

FREEWAY CONSENSUS:
  ALL 4 must independently vote PASS. Queen has absolute veto.

TEMPORAL CONSENSUS:
  When consensus says "not now", the system computes WHEN:
  - Market session windows (London/NY overlap = prime time)
  - Day-of-week patterns (learned from history)
  - Lunar/cosmic alignment windows
  - Lyra emotional cycle phases
  → Output: optimal_window_utc, wait_seconds, reasoning

PROBABILITY FIELD COLLAPSE:
  Each confirming signal reduces entropy in the decision field.
  More signals aligned = tighter probability = more confident action.
  Four-wave computation: Cognition → Emotion → Cosmos → Finance
  Each wave either reinforces or attenuates the prior, collapsing the
  probability distribution toward a decisive action.

Gary Leckey | February 2026
"""

import time
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

# Sacred constants
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio 1.618...
SCHUMANN_HZ = 7.83

# Lazy imports
_seer = None
_king = None
_lyra = None
_triumvirate = None

# ─── Enigma Symbol Universe (updated via Thought Bus) ───
# Shared state updated whenever the CryptoEnigmaSymbolMachine publishes a
# `symbol.new_discoveries` thought.  All four Pillars read this dict during
# their wave calculations so they are aware of new / emerging assets.
_ENIGMA_SYMBOL_UNIVERSE: Dict[str, Any] = {
    "total": 0,
    "newborns": [],          # symbols ≤ 7 days old
    "emerging": [],           # 8-30 days old
    "new_count": 0,           # count in most recent discovery batch
    "tiers": {},              # {tier_label: [sym, ...]} full breakdown
    "last_update": 0.0,       # unix timestamp of last Thought Bus update
    "source": "none",         # 'thought_bus' or 'enigma_direct'
}
_enigma_bus_wired: bool = False

# Pillar snipe nominations — populated by collapse_probability_field(), drained by orca
_PENDING_PILLAR_SNIPE_REQUESTS: List[Dict[str, Any]] = []


def _on_enigma_discovery(thought) -> None:
    """
    Thought Bus handler for ``symbol.new_discoveries``.
    Keeps _ENIGMA_SYMBOL_UNIVERSE in sync so every Pillar can see new listings.
    """
    global _ENIGMA_SYMBOL_UNIVERSE
    try:
        payload = thought.payload if hasattr(thought, "payload") else (thought or {})
        if isinstance(payload, dict):
            _ENIGMA_SYMBOL_UNIVERSE["new_count"] = payload.get("count", 0)
            new_syms = payload.get("new_symbols", [])
            # Accumulate newborns (keep last 200 unique)
            seen = set(_ENIGMA_SYMBOL_UNIVERSE["newborns"])
            for s in new_syms:
                if s not in seen:
                    _ENIGMA_SYMBOL_UNIVERSE["newborns"].append(s)
                    seen.add(s)
            _ENIGMA_SYMBOL_UNIVERSE["newborns"] = _ENIGMA_SYMBOL_UNIVERSE["newborns"][-200:]
            total = payload.get("total", 0)
            if total:
                _ENIGMA_SYMBOL_UNIVERSE["total"] = total
            _ENIGMA_SYMBOL_UNIVERSE["last_update"] = time.time()
            _ENIGMA_SYMBOL_UNIVERSE["source"] = "thought_bus"
            logger.debug(
                "Enigma universe updated via Thought Bus: %d total, %d new",
                _ENIGMA_SYMBOL_UNIVERSE["total"],
                _ENIGMA_SYMBOL_UNIVERSE["new_count"],
            )
    except Exception as e:
        logger.debug("_on_enigma_discovery error: %s", e)


def update_enigma_universe_direct(report) -> None:
    """
    Direct injection from orca (or any caller holding an EnigmaReport).
    Called after every 30-min rediscovery cycle so the Pillars always have
    fresh data even when ThoughtBus pubsub is unavailable.

    Args:
        report: EnigmaReport dataclass from CryptoEnigmaSymbolMachine.discover_all()
                Fields used:
                  total_symbols     - int   total catalogued symbols
                  new_since_last_scan - int count of new symbols in this scan
                  new_listings      - List[str] symbols new in this scan
                  by_tier           - Dict[str, List[str]] tier breakdown (if present)
    """
    global _ENIGMA_SYMBOL_UNIVERSE
    try:
        # new_listings is List[str] (raw symbol strings)
        new_listings = list(getattr(report, "new_listings", []))
        new_count = int(getattr(report, "new_since_last_scan", len(new_listings)))
        total = int(getattr(report, "total_symbols", _ENIGMA_SYMBOL_UNIVERSE["total"]))
        # by_tier may be Dict[str, List[str]] or Dict[str, List[DiscoveredSymbol]]
        tiers: Dict[str, list] = {}
        for tier_label, syms in getattr(report, "by_tier", {}).items():
            if syms and hasattr(syms[0], "symbol"):
                tiers[str(tier_label)] = [s.symbol for s in syms[:50]]
            else:
                tiers[str(tier_label)] = [str(s) for s in syms[:50]]
        emerging = tiers.get("🚀 EMERGING", tiers.get("EMERGING", []))
        # Merge new_listings into accumulated newborns list (keep last 200)
        prev_newborns = _ENIGMA_SYMBOL_UNIVERSE["newborns"]
        combined = list(dict.fromkeys(new_listings + prev_newborns))  # dedup, new first
        _ENIGMA_SYMBOL_UNIVERSE.update({
            "total": total,
            "newborns": combined[:200],
            "emerging": emerging[:100],
            "new_count": new_count,
            "tiers": tiers,
            "last_update": time.time(),
            "source": "enigma_direct",
        })
        logger.info(
            "Enigma universe (direct): %d total symbols, %d new this scan, %d emerging",
            total, new_count, len(emerging),
        )
    except Exception as e:
        logger.debug("update_enigma_universe_direct error: %s", e)


def _wire_enigma_subscription() -> None:
    """Subscribe to symbol.new_discoveries on the Thought Bus (called once at import)."""
    global _enigma_bus_wired
    if _enigma_bus_wired:
        return
    try:
        from aureon.core.aureon_thought_bus import ThoughtBus as _TB
        bus = _TB.get_instance() if hasattr(_TB, "get_instance") else None
        if bus and hasattr(bus, "subscribe"):
            bus.subscribe("symbol.new_discoveries", _on_enigma_discovery)
            _enigma_bus_wired = True
            logger.info("Seer Integration subscribed to symbol.new_discoveries")
    except Exception as e:
        logger.debug("Could not wire Enigma Thought Bus subscription: %s", e)


def get_enigma_universe_snapshot() -> Dict[str, Any]:
    """Return a lightweight copy of the current Enigma symbol universe for pillar use."""
    return {
        "total_symbols": _ENIGMA_SYMBOL_UNIVERSE["total"],
        "newborns": list(_ENIGMA_SYMBOL_UNIVERSE["newborns"][:20]),
        "emerging": list(_ENIGMA_SYMBOL_UNIVERSE["emerging"][:20]),
        "new_count": _ENIGMA_SYMBOL_UNIVERSE["new_count"],
        "tiers_summary": {k: len(v) for k, v in _ENIGMA_SYMBOL_UNIVERSE["tiers"].items()},
        "last_update": _ENIGMA_SYMBOL_UNIVERSE["last_update"],
        "source": _ENIGMA_SYMBOL_UNIVERSE["source"],
        "staleness_secs": round(time.time() - _ENIGMA_SYMBOL_UNIVERSE["last_update"], 0)
            if _ENIGMA_SYMBOL_UNIVERSE["last_update"] else None,
    }


def flush_pillar_snipe_requests() -> List[Dict[str, Any]]:
    """
    Return and clear all pending Pillar snipe nominations.
    Called by orca after every Quadrumvirate consensus so the engine can
    attempt to buy each symbol the 4 Pillars nominated.

    Returns:
        List of dicts: [{"symbol": str, "nominators": [str], "score_sum": float}, ...]
        Sorted by number of nominators descending (most agreed-upon first).
    """
    global _PENDING_PILLAR_SNIPE_REQUESTS
    if not _PENDING_PILLAR_SNIPE_REQUESTS:
        return []
    # Deduplicate: merge nominations for the same symbol
    merged: Dict[str, Dict] = {}
    for nom in _PENDING_PILLAR_SNIPE_REQUESTS:
        sym = nom.get("symbol", "")
        if not sym:
            continue
        if sym not in merged:
            merged[sym] = {"symbol": sym, "nominators": [], "score_sum": 0.0}
        for nr in nom.get("nominators", [nom.get("nominator", "?")]):
            if nr not in merged[sym]["nominators"]:
                merged[sym]["nominators"].append(nr)
        merged[sym]["score_sum"] += nom.get("score_sum", nom.get("score", 0.5))
    _PENDING_PILLAR_SNIPE_REQUESTS = []  # Clear
    result = sorted(merged.values(), key=lambda x: (len(x["nominators"]), x["score_sum"]), reverse=True)
    return result


def _get_seer():
    global _seer
    if _seer is None:
        from aureon.intelligence.aureon_seer import get_seer
        _seer = get_seer()
    return _seer


def _get_king():
    global _king
    if _king is None:
        try:
            from aureon.bots.king_accounting import get_king
            _king = get_king()
        except ImportError:
            _king = None
    return _king


def _get_lyra():
    global _lyra
    if _lyra is None:
        try:
            from aureon.trading.aureon_lyra import get_lyra
            _lyra = get_lyra()
        except ImportError:
            _lyra = None
    return _lyra


def _get_triumvirate():
    global _triumvirate
    if _triumvirate is None:
        from aureon.utils.aureon_triumvirate import get_triumvirate
        _triumvirate = get_triumvirate()
    return _triumvirate


# ═══════════════════════════════════════════════════════════════════════════
# ECOSYSTEM HOOKS - Called by the trading engine
# ═══════════════════════════════════════════════════════════════════════════

def seer_update_context(positions: Dict = None,
                        ticker_cache: Dict = None,
                        market_data: Dict = None,
                        trade_history: list = None):
    """
    Feed live data to the Seer. Call this every cycle from the ecosystem.
    """
    seer = _get_seer()
    seer.update_context(
        positions=positions,
        ticker_cache=ticker_cache,
        market_data=market_data,
        trade_history=trade_history,
    )


def seer_inject_wave_context(wave_data: dict) -> None:
    """
    Push ocean wave scanner results into the Seer's OracleOfHarmony.
    Called by MultiverseLearningBridge.push_wave_context() after each scan.
    """
    _get_seer().inject_wave_context(wave_data)


def seer_get_vision() -> Dict[str, Any]:
    """
    Get the Seer's latest vision. If no recent vision exists, take a new reading.
    Returns a dict with score, grade, action, risk_modifier, prophecy.
    """
    seer = _get_seer()
    if seer.latest_vision is None or (time.time() - seer.latest_vision.timestamp > 60):
        seer.see()
    summary = seer.get_vision_summary()
    try:
        from aureon.wisdom.antarctic_research_bridge import apply_to_seer_summary
        summary = apply_to_seer_summary(summary)
    except Exception:
        pass
    return summary


def seer_get_risk_modifier() -> float:
    """
    Get the Seer's risk modifier for position sizing.
    >1.0 = increase size, <1.0 = decrease size.
    """
    seer = _get_seer()
    if seer.latest_vision:
        return seer.latest_vision.risk_modifier
    return 1.0


def seer_should_trade() -> bool:
    """
    Quick check: should the Queen trade right now?
    Returns False if the Seer's vision is FOG or BLIND.
    """
    seer = _get_seer()
    if seer.latest_vision is None:
        return True  # No vision yet, don't block
    return seer.latest_vision.grade not in ["BLIND"]


# ═══════════════════════════════════════════════════════════════════════════
# FOUR-PILLAR FREEWAY CONSENSUS (QUADRUMVIRATE)
# ═══════════════════════════════════════════════════════════════════════════

def get_triumvirate_consensus(queen_confidence: float = 0.5,
                              queen_data: Dict[str, Any] = None,
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    FOUR-PILLAR FREEWAY CONSENSUS: All 4 pillars must independently vote PASS.
    Queen has ABSOLUTE VETO (she has 11+ connected systems).

    Now includes Lyra (4th pillar) for emotional/harmonic gating.

    Args:
        queen_confidence: 0.0-1.0 from Queen's cognition systems
        queen_data: Additional data from Queen's subsystems
        context: Event context for control handoff

    Returns:
        Full consensus dict with action, votes, data exchange, and controller.
    """
    triumvirate = _get_triumvirate()
    seer = _get_seer()

    # Ensure Seer has a recent vision
    if seer.latest_vision is None or (time.time() - seer.latest_vision.timestamp > 60):
        seer.see()

    vision = seer.latest_vision
    seer_grade = vision.grade if vision else "BLIND"
    seer_score = vision.unified_score if vision else 0.0

    # Build Seer data from vision
    seer_data = {}
    if vision:
        seer_data = {
            "risk_modifier": vision.risk_modifier,
            "action": vision.action,
            "prophecy": vision.prophecy,
            "gaia_score": vision.gaia.score if vision.gaia else 0.5,
            "cosmos_score": vision.cosmos.score if vision.cosmos else 0.5,
            "harmony_score": vision.harmony.score if vision.harmony else 0.5,
            "spirits_score": vision.spirits.score if vision.spirits else 0.5,
            "time_score": vision.timeline.score if vision.timeline else 0.5,
            "trend": seer.get_trend().get("trend", "STABLE"),
            # ─── Margin signals from OracleOfMargin via SeerVision ───
            "margin_recommendation": getattr(vision, 'margin_recommendation', 'NONE'),
            "margin_leverage": getattr(vision, 'margin_leverage', 0),
            "margin_conviction": getattr(vision, 'margin_conviction', 0.0),
        }

    # Get King's health and analytical data
    king_health = "STABLE"
    king_data = {}
    king = _get_king()
    if king:
        try:
            pnl = king.treasury.omega.get_summary()
            wr = pnl.get("win_rate", 50)
            total_pnl = pnl.get("total_realized_pnl", 0)

            if total_pnl > 0 and wr >= 55:
                king_health = "PROSPEROUS"
            elif total_pnl > 0 and wr >= 50:
                king_health = "STABLE"
            elif total_pnl > 0:
                king_health = "STABLE"
            elif total_pnl > -50:
                king_health = "STRAINED"
            else:
                king_health = "BANKRUPT"

            # King shares analytical data freely
            king_data = {
                "total_realized_pnl": total_pnl,
                "win_rate": wr,
                "unrealized_pnl": pnl.get("unrealized_pnl", 0),
                "total_fees": pnl.get("total_fees_paid", pnl.get("total_fees", 0)),
                "equity": pnl.get("equity", 0),
                "wins": pnl.get("wins", 0),
                "losses": pnl.get("losses", 0),
                "total_trades": pnl.get("total_trades", 0),
                "cost_basis_available": True,
                "drawdown_pct": 0.0,
                "tax_liability": 0.0,
            }

            # Enrich with portfolio snapshot if available
            try:
                gamma = king.treasury.gamma
                if gamma and hasattr(gamma, 'peak_equity') and gamma.peak_equity > 0:
                    equity = king_data.get("equity", 0) or gamma.peak_equity
                    if equity > 0:
                        dd = ((gamma.peak_equity - equity) / gamma.peak_equity) * 100
                        king_data["drawdown_pct"] = round(max(0, dd), 2)
            except Exception:
                pass

            # Enrich with tax data if available
            try:
                psi = king.treasury.psi
                if psi and hasattr(psi, 'get_tax_summary'):
                    tax_sum = psi.get_tax_summary()
                    king_data["tax_liability"] = tax_sum.get("total_taxable", 0)
            except Exception:
                pass
        except Exception:
            pass

    # ─── Get Lyra's resonance and emotional data (4th pillar) ───
    lyra_grade = "PARTIAL_HARMONY"
    lyra_score = 0.5
    lyra_data = {}
    lyra = _get_lyra()
    if lyra:
        try:
            if lyra.latest_resonance is None or (time.time() - lyra.latest_resonance.timestamp > 60):
                lyra.feel()
            res = lyra.latest_resonance
            if res:
                lyra_grade = res.grade
                lyra_score = res.unified_score
                lyra_data = {
                    "emotional_frequency": res.emotional_frequency,
                    "emotional_zone": res.emotional_zone,
                    "position_multiplier": res.position_multiplier,
                    "exit_urgency": res.exit_urgency,
                    "action": res.action,
                    "song": res.song if hasattr(res, 'song') else "",
                    "emotion_score": getattr(res, 'emotion_score', 0.5),
                    "earth_score": getattr(res, 'earth_score', 0.5),
                    "harmony_score": getattr(res, 'harmony_score', 0.5),
                    "voice_score": getattr(res, 'voice_score', 0.5),
                    "solfeggio_score": getattr(res, 'solfeggio_score', 0.5),
                    "spirit_score": getattr(res, 'spirit_score', 0.5),
                    "trend": getattr(res, 'trend', "STABLE"),
                }
        except Exception as e:
            logger.debug(f"Lyra resonance read error: {e}")

    # ─── Inject Enigma symbol universe into every Pillar’s data dict ───
    # Each Pillar evaluator will read this and nominate newborns for sniping.
    _univ = get_enigma_universe_snapshot()
    if _univ["total_symbols"] > 0 and (_univ.get("staleness_secs") or 9999) < 3600:
        _universe_ctx = {"symbol_universe": _univ}
        queen_data = dict(queen_data or {})
        queen_data.update(_universe_ctx)
        king_data  = dict(king_data);  king_data.update(_universe_ctx)
        seer_data  = dict(seer_data);  seer_data.update(_universe_ctx)
        lyra_data  = dict(lyra_data);  lyra_data.update(_universe_ctx)

    # ─── Run FOUR-PILLAR freeway consensus ───
    consensus = triumvirate.evaluate_consensus(
        queen_confidence=queen_confidence,
        king_health=king_health,
        seer_grade=seer_grade,
        seer_score=seer_score,
        lyra_grade=lyra_grade,
        lyra_score=lyra_score,
        queen_data=queen_data,
        king_data=king_data,
        seer_data=seer_data,
        lyra_data=lyra_data,
        context=context,
    )

    # ─── Collect Pillar snipe nominations into global pending queue ───
    _pillar_snipes = (consensus.data_exchange or {}).get("nominated_snipes", [])
    if _pillar_snipes:
        _PENDING_PILLAR_SNIPE_REQUESTS.extend(_pillar_snipes)
        logger.info(
            "Pillars nominated %d symbol(s) for sniping: %s",
            len(_pillar_snipes),
            [n.get("symbol") for n in _pillar_snipes[:5]],
        )

    result = {
        "timestamp": consensus.timestamp,
        "consensus_action": consensus.action,
        "passed": consensus.passed,
        "queen_vetoed": consensus.queen_vetoed,
        "active_controller": consensus.active_controller,
        "alignment_score": consensus.alignment_score,
        "reason": consensus.reason,
        "pillars": {
            "queen": {
                "vote": consensus.queen_vote.vote,
                "confidence": consensus.queen_vote.score,
                "grade": consensus.queen_vote.grade,
                "reason": consensus.queen_vote.reason,
                "connected_systems": consensus.queen_vote.connected_systems,
                "role": "Trading Cognition",
            },
            "king": {
                "vote": consensus.king_vote.vote,
                "health": consensus.king_vote.grade,
                "score": consensus.king_vote.score,
                "reason": consensus.king_vote.reason,
                "connected_systems": consensus.king_vote.connected_systems,
                "role": "Financial Truth",
            },
            "seer": {
                "vote": consensus.seer_vote.vote,
                "grade": consensus.seer_vote.grade,
                "score": consensus.seer_vote.score,
                "reason": consensus.seer_vote.reason,
                "connected_systems": consensus.seer_vote.connected_systems,
                "role": "Cosmic Coherence",
            },
            "lyra": {
                "vote": consensus.lyra_vote.vote if consensus.lyra_vote else "ABSTAIN",
                "grade": consensus.lyra_vote.grade if consensus.lyra_vote else "UNKNOWN",
                "score": consensus.lyra_vote.score if consensus.lyra_vote else 0.5,
                "reason": consensus.lyra_vote.reason if consensus.lyra_vote else "Lyra unavailable",
                "connected_systems": consensus.lyra_vote.connected_systems if consensus.lyra_vote else 0,
                "role": "Emotional Frequency",
            },
        },
        "data_exchange": consensus.data_exchange,
        # ─── Pillar Council dialogue ───
        "council": {},
        # Actionable modifiers for sizing and urgency
        "risk_modifier": seer_data.get("risk_modifier", 1.0),
        "position_multiplier": lyra_data.get("position_multiplier", 1.0),
        "exit_urgency": lyra_data.get("exit_urgency", "none"),
        "combined_sizing_modifier": seer_data.get("risk_modifier", 1.0) * lyra_data.get("position_multiplier", 1.0),
        # ─── Margin signals for revenue maximization ───
        "margin_recommendation": seer_data.get("margin_recommendation", "NONE"),
        "margin_leverage": seer_data.get("margin_leverage", 0),
        "margin_conviction": seer_data.get("margin_conviction", 0.0),
    }

    # ─── Include Pillar Council dialogue if session was held ───
    cs = consensus.council_session
    if cs:
        result["council"] = {
            "session_id": cs.session_id,
            "consensus_impact": cs.consensus_impact,
            "transcript": cs.transcript,
            "puzzle_pieces": {
                b.pillar.lower(): b.key_insight for b in cs.briefings
            },
            "adjustments": {
                pillar: {
                    "original": adj.get("original_score", 0),
                    "adjusted": adj.get("adjusted_score", 0),
                    "delta": adj.get("delta", 0),
                    "reason": adj.get("reason", ""),
                }
                for pillar, adj in cs.adjustments.items()
            },
        }
        logger.info(
            "PILLAR COUNCIL #%d complete | Impact: %s",
            cs.session_id, cs.consensus_impact
        )

    # Broadcast to ThoughtBus (consensus + council dialogue)
    _broadcast("TRIUMVIRATE_FREEWAY_CONSENSUS", result)

    # Broadcast the council transcript separately for any listener
    if cs:
        _broadcast("PILLAR_COUNCIL_DIALOGUE", {
            "session_id": cs.session_id,
            "impact": cs.consensus_impact,
            "puzzle_pieces": result["council"].get("puzzle_pieces", {}),
            "adjustments": result["council"].get("adjustments", {}),
            "transcript": cs.transcript,
        })

    return result


def get_active_controller() -> str:
    """Get which pillar currently has control authority."""
    triumvirate = _get_triumvirate()
    return triumvirate.get_active_controller().value


def get_triumvirate_summary() -> Dict[str, Any]:
    """Get the Triumvirate's current state summary."""
    triumvirate = _get_triumvirate()
    return triumvirate.get_summary()


# ═══════════════════════════════════════════════════════════════════════════
# TEMPORAL CONSENSUS ENGINE
# "Not just should we trade — WHEN is the optimal moment?"
# ═══════════════════════════════════════════════════════════════════════════

# Market session definitions (UTC hours)
MARKET_SESSIONS = {
    "SYDNEY":      {"open": 22, "close": 7,  "weight": 0.50},  # 22:00-07:00 UTC
    "TOKYO":       {"open": 0,  "close": 9,  "weight": 0.55},  # 00:00-09:00 UTC
    "LONDON":      {"open": 8,  "close": 17, "weight": 0.75},  # 08:00-17:00 UTC
    "NEW_YORK":    {"open": 13, "close": 22, "weight": 0.70},  # 13:00-22:00 UTC
    "LONDON_NY":   {"open": 13, "close": 17, "weight": 0.90},  # 13:00-17:00 UTC (OVERLAP = PRIME)
    "TOKYO_LONDON": {"open": 8, "close": 9,  "weight": 0.80},  # 08:00-09:00 UTC (OVERLAP)
}

# Day-of-week patterns (0=Monday, 6=Sunday) — empirical trading data
DAY_WEIGHTS = {
    0: 0.70,  # Monday — slow start, false signals after weekend
    1: 0.80,  # Tuesday — good momentum
    2: 0.85,  # Wednesday — PEAK mid-week activity
    3: 0.80,  # Thursday — good, but watch for Friday positioning
    4: 0.65,  # Friday — profit-taking, reduced conviction
    5: 0.30,  # Saturday — crypto only, thin liquidity
    6: 0.35,  # Sunday — crypto only, building before Monday
}

# Lunar phase multiplier (0.0=New Moon, 0.5=Full Moon, 1.0=next New)
LUNAR_CYCLE_DAYS = 29.53
# Reference: Jan 29, 2025 was a New Moon (epoch for calculation)
LUNAR_EPOCH = datetime(2025, 1, 29, tzinfo=timezone.utc)


def _get_lunar_phase() -> Tuple[float, str]:
    """Calculate current lunar phase (0-1) and human-readable name."""
    now = datetime.now(timezone.utc)
    days_since_new = (now - LUNAR_EPOCH).total_seconds() / 86400.0
    phase = (days_since_new % LUNAR_CYCLE_DAYS) / LUNAR_CYCLE_DAYS

    if phase < 0.125:
        name = "NEW_MOON"
    elif phase < 0.25:
        name = "WAXING_CRESCENT"
    elif phase < 0.375:
        name = "FIRST_QUARTER"
    elif phase < 0.5:
        name = "WAXING_GIBBOUS"
    elif phase < 0.625:
        name = "FULL_MOON"
    elif phase < 0.75:
        name = "WANING_GIBBOUS"
    elif phase < 0.875:
        name = "LAST_QUARTER"
    else:
        name = "WANING_CRESCENT"

    return phase, name


def _get_lunar_multiplier(phase: float) -> float:
    """
    Lunar tidal torsion scalar.
    New Moon and Full Moon = syzygy = heightened market volatility.
    Quarter moons = neap tides = calmer markets.
    """
    # Syzygy peaks at 0.0 (new) and 0.5 (full): +20% energy
    # Neap troughs at 0.25 and 0.75: -10% energy
    return 1.0 + 0.20 * abs(math.cos(2 * math.pi * phase))


def _get_active_sessions(hour_utc: int) -> List[str]:
    """Return list of active market sessions for the given UTC hour."""
    active = []
    for name, sess in MARKET_SESSIONS.items():
        o, c = sess["open"], sess["close"]
        if o < c:
            if o <= hour_utc < c:
                active.append(name)
        else:  # Wraps midnight (e.g. Sydney 22-07)
            if hour_utc >= o or hour_utc < c:
                active.append(name)
    return active


def _compute_session_score(hour_utc: int) -> Tuple[float, List[str]]:
    """Compute session quality score and list active sessions."""
    active = _get_active_sessions(hour_utc)
    if not active:
        return 0.3, ["OFF_HOURS"]
    # Take the best session weight (overlaps are already defined)
    best_weight = max(MARKET_SESSIONS[s]["weight"] for s in active)
    return best_weight, active


def _find_next_prime_window(now_utc: datetime) -> Tuple[datetime, str, float]:
    """
    Scan forward from now to find the next high-quality trading window.
    Returns (window_start_utc, reason, expected_score).
    """
    best_score = 0.0
    best_hour_offset = 1
    best_reason = ""

    # Look ahead up to 24 hours in 1-hour increments
    for offset_hours in range(1, 25):
        future = now_utc + timedelta(hours=offset_hours)
        future_hour = future.hour
        future_dow = future.weekday()

        session_score, sessions = _compute_session_score(future_hour)
        day_weight = DAY_WEIGHTS.get(future_dow, 0.5)
        combined = session_score * day_weight

        if combined > best_score:
            best_score = combined
            best_hour_offset = offset_hours
            best_reason = f"{', '.join(sessions)} on {future.strftime('%A')} {future.strftime('%H:%M')} UTC"

    window_start = now_utc + timedelta(hours=best_hour_offset)
    return window_start, best_reason, best_score


def get_temporal_consensus() -> Dict[str, Any]:
    """
    TEMPORAL CONSENSUS: Multi-dimensional time analysis.
    Combines market sessions, day patterns, lunar phase, Seer Oracle of Time,
    and Lyra emotional cycles into a unified temporal score.

    Returns:
        Dict with:
            temporal_score: 0.0-1.0 overall favorability of THIS moment
            trade_now: bool - should we trade right now?
            sessions: list of active market sessions
            day_weight: float - day-of-week factor
            lunar_phase: str - current lunar phase name
            lunar_multiplier: float - tidal torsion scalar
            optimal_window: dict - if not now, when is best?
            reasoning: str - human-readable explanation
    """
    now = datetime.now(timezone.utc)
    hour_utc = now.hour
    dow = now.weekday()

    # ─── Layer 1: Market session scoring ───
    session_score, active_sessions = _compute_session_score(hour_utc)

    # ─── Layer 2: Day-of-week scoring ───
    day_weight = DAY_WEIGHTS.get(dow, 0.5)

    # ─── Layer 3: Lunar phase ───
    lunar_phase, lunar_name = _get_lunar_phase()
    lunar_mul = _get_lunar_multiplier(lunar_phase)

    # ─── Layer 4: Seer Oracle of Time (if available) ───
    seer_time_score = 0.5
    seer = _get_seer()
    if seer and seer.latest_vision:
        try:
            tl = seer.latest_vision.timeline
            if tl:
                seer_time_score = tl.score
        except Exception:
            pass

    # ─── Layer 5: Lyra emotional cycle phase ───
    lyra_energy = 0.5
    lyra = _get_lyra()
    if lyra and lyra.latest_resonance:
        try:
            lyra_energy = lyra.latest_resonance.unified_score
        except Exception:
            pass

    # ─── Combine with PHI-weighted convergence ───
    # Session (30%) + Day (15%) + Lunar (10%) + Seer Time (25%) + Lyra (20%)
    temporal_score = (
        0.30 * session_score +
        0.15 * day_weight +
        0.10 * min(1.0, lunar_mul - 0.5) +  # Normalize lunar 0.8-1.2 → 0.3-0.7
        0.25 * seer_time_score +
        0.20 * lyra_energy
    )

    # Clamp
    temporal_score = max(0.0, min(1.0, temporal_score))

    # ─── Decision: trade now or wait? ───
    trade_now = temporal_score >= 0.50

    # ─── If not now, find the next good window ───
    optimal_window = None
    if not trade_now:
        window_start, reason, expected_score = _find_next_prime_window(now)
        wait_seconds = (window_start - now).total_seconds()
        optimal_window = {
            "window_start_utc": window_start.isoformat(),
            "wait_seconds": int(wait_seconds),
            "wait_human": f"{int(wait_seconds // 3600)}h {int((wait_seconds % 3600) // 60)}m",
            "expected_score": round(expected_score, 3),
            "reason": reason,
        }

    # ─── Build reasoning ───
    reasons = []
    if "LONDON_NY" in active_sessions:
        reasons.append("London/NY overlap = PRIME trading window")
    elif "LONDON" in active_sessions:
        reasons.append("London session active")
    elif "NEW_YORK" in active_sessions:
        reasons.append("New York session active")
    elif "TOKYO_LONDON" in active_sessions:
        reasons.append("Tokyo/London overlap")
    elif "TOKYO" in active_sessions:
        reasons.append("Tokyo session (moderate)")
    elif "SYDNEY" in active_sessions:
        reasons.append("Sydney session (low liquidity)")
    else:
        reasons.append("OFF HOURS - no major sessions active")

    reasons.append(f"{now.strftime('%A')} (weight {day_weight:.0%})")
    reasons.append(f"Lunar: {lunar_name} (x{lunar_mul:.2f})")

    if seer_time_score >= 0.7:
        reasons.append(f"Seer sees FAVORABLE time ({seer_time_score:.0%})")
    elif seer_time_score < 0.4:
        reasons.append(f"Seer sees UNFAVORABLE time ({seer_time_score:.0%})")

    if lyra_energy >= 0.7:
        reasons.append(f"Lyra emotional energy HIGH ({lyra_energy:.0%})")
    elif lyra_energy < 0.4:
        reasons.append(f"Lyra emotional energy LOW ({lyra_energy:.0%})")

    return {
        "temporal_score": round(temporal_score, 4),
        "trade_now": trade_now,
        "sessions": active_sessions,
        "session_score": round(session_score, 3),
        "day_weight": round(day_weight, 3),
        "day_name": now.strftime('%A'),
        "hour_utc": hour_utc,
        "lunar_phase": lunar_name,
        "lunar_phase_value": round(lunar_phase, 4),
        "lunar_multiplier": round(lunar_mul, 4),
        "seer_time_score": round(seer_time_score, 4),
        "lyra_energy": round(lyra_energy, 4),
        "optimal_window": optimal_window,
        "reasoning": " | ".join(reasons),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PROBABILITY FIELD COLLAPSE ENGINE
# "Each confirming signal reduces entropy. Four waves converge."
# ═══════════════════════════════════════════════════════════════════════════

def collapse_probability_field(queen_confidence: float = 0.5,
                               queen_data: Dict[str, Any] = None,
                               symbol: str = "",
                               context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    FOUR-WAVE PROBABILITY FIELD COLLAPSE

    Each wave either reinforces or attenuates the decision field.
    More aligned signals = lower entropy = more confident action.

    Wave 1 - COGNITION (Queen): Trading algorithms, pattern recognition
    Wave 2 - EMOTION (Lyra): Harmonic resonance, market sentiment frequency
    Wave 3 - COSMOS (Seer): Cosmic alignment, temporal coherence, earth
    Wave 4 - FINANCE (King): P&L truth, cost basis, portfolio health

    The four waves propagate through the field. Each confirming wave
    MULTIPLIES the coherence (phi-scaled), each contradicting wave
    attenuates it. The field collapses toward a decisive action.

    Returns:
        Dict with:
            field_coherence: 0.0-1.0 how collapsed the field is
            field_entropy: inverse of coherence (uncertainty remaining)
            action: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL / HALT
            consensus: full Quadrumvirate consensus result
            temporal: temporal consensus result
            waves: individual wave readings
            collapse_narrative: human-readable story
    """
    # ─── Wave 1: COGNITION (Queen) ───
    wave1 = {
        "name": "COGNITION",
        "source": "Queen",
        "score": queen_confidence,
        "bias": "BUY" if queen_confidence >= 0.55 else ("SELL" if queen_confidence < 0.40 else "NEUTRAL"),
    }

    # ─── Wave 2: EMOTION (Lyra) ───
    lyra = _get_lyra()
    lyra_score = 0.5
    lyra_bias = "NEUTRAL"
    if lyra and lyra.latest_resonance:
        try:
            if time.time() - lyra.latest_resonance.timestamp > 60:
                lyra.feel()
            res = lyra.latest_resonance
            lyra_score = res.unified_score
            lyra_bias = res.action if res.action else "HOLD"
        except Exception:
            pass
    wave2 = {"name": "EMOTION", "source": "Lyra", "score": lyra_score, "bias": lyra_bias}

    # ─── Wave 3: COSMOS (Seer) ───
    seer = _get_seer()
    seer_score = 0.5
    seer_bias = "NEUTRAL"
    if seer:
        try:
            if seer.latest_vision is None or (time.time() - seer.latest_vision.timestamp > 60):
                seer.see()
            vis = seer.latest_vision
            if vis:
                seer_score = vis.unified_score
                seer_bias = vis.action if vis.action else "HOLD"
        except Exception:
            pass
    wave3 = {"name": "COSMOS", "source": "Seer", "score": seer_score, "bias": seer_bias}

    # ─── Wave 4: FINANCE (King) ───
    king = _get_king()
    king_score = 0.5
    king_bias = "NEUTRAL"
    if king:
        try:
            pnl = king.treasury.omega.get_summary()
            wr = pnl.get("win_rate", 50.0)
            total_pnl = pnl.get("total_realized_pnl", 0)
            king_score = min(1.0, max(0.0, wr / 100.0))
            if total_pnl > 0 and wr >= 55:
                king_bias = "BUY"
                king_score = min(1.0, 0.5 + total_pnl / 500.0)
            elif total_pnl < -20:
                king_bias = "SELL"
                king_score = max(0.1, 0.5 + total_pnl / 200.0)
            else:
                king_bias = "NEUTRAL"
        except Exception:
            pass
    wave4 = {"name": "FINANCE", "source": "King", "score": king_score, "bias": king_bias}

    waves = [wave1, wave2, wave3, wave4]

    # ─── Probability Field Collapse Calculation ───
    # 1. Compute mean signal strength
    scores = [w["score"] for w in waves]
    mean_score = sum(scores) / len(scores)

    # 2. Compute variance (entropy proxy)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    # Max variance is 0.25 (one at 0, one at 1)
    entropy = min(1.0, variance / 0.25)

    # 3. Coherence = inverse entropy, boosted by phi when aligned
    coherence = 1.0 - entropy

    # 4. Bias alignment check: how many waves agree?
    buy_signals = sum(1 for w in waves if w["bias"] in ("BUY", "BUY_BIAS", "STRONG_BUY", "BUY_BOOST"))
    sell_signals = sum(1 for w in waves if w["bias"] in ("SELL", "SELL_BIAS", "STRONG_SELL", "SELL_PRESSURE"))
    neutral_signals = len(waves) - buy_signals - sell_signals

    # Alignment bonus: unanimous = phi boost, 3/4 = moderate boost
    if buy_signals == 4 or sell_signals == 4:
        coherence = min(1.0, coherence * PHI)  # Phi-scaled unanimous boost
    elif buy_signals >= 3 or sell_signals >= 3:
        coherence = min(1.0, coherence * 1.25)  # 3/4 aligned boost
    elif buy_signals == 2 and sell_signals == 2:
        coherence *= 0.5  # Split field = high entropy, low coherence

    coherence = max(0.0, min(1.0, coherence))
    entropy = 1.0 - coherence

    # ─── Determine dominant action from collapsed field ───
    if buy_signals > sell_signals:
        if coherence >= 0.85 and mean_score >= 0.70:
            action = "STRONG_BUY"
        elif coherence >= 0.60 and mean_score >= 0.55:
            action = "BUY"
        else:
            action = "HOLD"
    elif sell_signals > buy_signals:
        if coherence >= 0.85 and mean_score <= 0.35:
            action = "STRONG_SELL"
        elif coherence >= 0.60 and mean_score <= 0.45:
            action = "SELL"
        else:
            action = "HOLD"
    else:
        action = "HOLD"

    # ─── Wave 0 enhancement: Enigma Symbol Universe awareness ───
    # If the Enigma Machine has discovered new NEWBORN/EMERGING symbols recently,
    # the discovery momentum is factored into Queen's cognition wave so all
    # four Pillars are aware when fresh instruments enter the ecosystem.
    universe = get_enigma_universe_snapshot()
    if universe["total_symbols"] > 0:
        newborn_count = len(universe["newborns"])
        emerging_count = len(universe["emerging"])
        recent = (universe["staleness_secs"] or 9999) < 1800  # fresh within 30 min
        if newborn_count > 0 and recent:
            # New assets detected: slightly boost Queen's wave score (discovery confidence)
            discovery_boost = min(0.05, newborn_count * 0.003)
            wave1["score"] = min(1.0, wave1["score"] + discovery_boost)
            wave1["discovery_boost"] = discovery_boost
            wave1["newborns_detected"] = newborn_count
            logger.debug(
                "Enigma discovery boost +%.3f applied (newborns=%d, emerging=%d)",
                discovery_boost, newborn_count, emerging_count,
            )
        # Attach universe context for Lyra (emotional excitement around new assets)
        if emerging_count > 5 and recent:
            wave2["emerging_market_energy"] = min(1.0, 0.5 + emerging_count * 0.005)
        # Pass universe into context so triumvirate.evaluate_consensus() can use it
        if context is None:
            context = {}
        context["symbol_universe"] = universe
        context["enigma_newborns"] = universe["newborns"]
        context["enigma_total"] = universe["total_symbols"]

    # ─── Run full Quadrumvirate consensus ───
    consensus = get_triumvirate_consensus(
        queen_confidence=queen_confidence,
        queen_data=queen_data,
        context=context,
    )

    # ─── Override action if consensus HALTs ───
    if consensus.get("consensus_action") == "HALT":
        action = "HALT"

    # ─── Temporal analysis ───
    temporal = get_temporal_consensus()

    # If temporal says "not now" and field says BUY, downgrade to HOLD
    if not temporal["trade_now"] and action in ("BUY", "STRONG_BUY"):
        action = "HOLD"

    # ─── Build collapse narrative ───
    narrative_parts = []
    narrative_parts.append(f"Field coherence: {coherence:.0%} (entropy {entropy:.0%})")
    narrative_parts.append(f"Waves: {buy_signals} BUY, {sell_signals} SELL, {neutral_signals} NEUTRAL")
    for w in waves:
        narrative_parts.append(f"  {w['source']}: {w['bias']} ({w['score']:.0%})")
    narrative_parts.append(f"Temporal: {temporal['reasoning']}")
    if temporal.get("optimal_window"):
        ow = temporal["optimal_window"]
        narrative_parts.append(f"  Wait {ow['wait_human']} for {ow['reason']}")
    narrative_parts.append(f"Quadrumvirate: {consensus.get('consensus_action', 'UNKNOWN')}")
    narrative_parts.append(f"COLLAPSED ACTION: {action}")

    return {
        "field_coherence": round(coherence, 4),
        "field_entropy": round(entropy, 4),
        "action": action,
        "mean_score": round(mean_score, 4),
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "consensus": consensus,
        "temporal": temporal,
        "waves": waves,
        "collapse_narrative": "\n".join(narrative_parts),
        "symbol": symbol,
    }


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED GATE: "Should we trade RIGHT NOW?"
# Called once per scan cycle to gate all trading activity.
# ═══════════════════════════════════════════════════════════════════════════

def quadrumvirate_should_trade(queen_confidence: float = 0.5,
                               queen_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    UNIFIED PRE-SCAN GATE: All four pillars + temporal + field collapse.

    Call this ONCE before any scan/trade cycle. Returns a simple
    go/no-go with full reasoning and timing guidance.

    Returns:
        Dict with:
            should_trade: bool
            action: str ("BUY"/"SELL"/"HOLD"/"HALT")
            field_coherence: float 0-1
            temporal_score: float 0-1
            alignment_score: float 0-1
            sizing_modifier: float (apply to position size)
            wait_guidance: dict or None (if should wait, when to resume)
            summary: str (one-line summary)
            detail: str (full narrative)
    """
    # Run the full probability field collapse
    field = collapse_probability_field(
        queen_confidence=queen_confidence,
        queen_data=queen_data,
    )

    consensus = field["consensus"]
    temporal = field["temporal"]
    action = field["action"]

    # Determine if we should trade
    should_trade = (
        action in ("BUY", "STRONG_BUY", "SELL", "STRONG_SELL") and
        consensus.get("passed", False) and
        temporal.get("trade_now", True)
    )

    # Combined sizing modifier from Seer risk + Lyra position multiplier
    sizing_mod = consensus.get("combined_sizing_modifier", 1.0)

    # Wait guidance if not trading
    wait_guidance = None
    if not should_trade and temporal.get("optimal_window"):
        wait_guidance = temporal["optimal_window"]

    # Summary line
    pillars_status = []
    for name in ["queen", "king", "seer", "lyra"]:
        p = consensus.get("pillars", {}).get(name, {})
        vote = p.get("vote", "?")
        grade = p.get("grade", p.get("health", "?"))
        emoji = "PASS" if vote == "PASS" else "BLOCK"
        pillars_status.append(f"{name.capitalize()}={emoji}({grade})")

    summary = (
        f"{'GO' if should_trade else 'WAIT'} | "
        f"Action={action} | "
        f"Coherence={field['field_coherence']:.0%} | "
        f"Time={temporal['temporal_score']:.0%} | "
        f"{' | '.join(pillars_status)}"
    )

    return {
        "should_trade": should_trade,
        "action": action,
        "field_coherence": field["field_coherence"],
        "field_entropy": field["field_entropy"],
        "temporal_score": temporal["temporal_score"],
        "alignment_score": consensus.get("alignment_score", 0.0),
        "sizing_modifier": sizing_mod,
        "exit_urgency": consensus.get("exit_urgency", "none"),
        "wait_guidance": wait_guidance,
        "active_controller": consensus.get("active_controller", "QUEEN"),
        "summary": summary,
        "detail": field["collapse_narrative"],
        "waves": field["waves"],
        "temporal": temporal,
        "consensus": consensus,
        # ─── Margin signals (bubbled up so Orca can read them at top level) ───
        "margin_recommendation": consensus.get("margin_recommendation", "NONE"),
        "margin_leverage": consensus.get("margin_leverage", 0),
        "margin_conviction": consensus.get("margin_conviction", 0.0),
    }


# ═══════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════

def start_seer():
    """
    Start Aureon the Seer's autonomous monitoring.
    Call this from the main trading engine startup.
    """
    seer = _get_seer()
    seer.start_autonomous()
    # Initialize the Triumvirate engine
    _get_triumvirate()
    logger.info("Aureon the Seer has awakened. The Third Pillar stands.")
    logger.info("The Triumvirate Freeway Consensus is online.")
    return seer


def stop_seer():
    """Stop the Seer's autonomous monitoring."""
    seer = _get_seer()
    seer.stop_autonomous()


def print_seer_report():
    """Print the Seer's vision report to stdout."""
    seer = _get_seer()
    if seer.latest_vision is None:
        seer.see()
    print("\n" + seer.generate_report())


# ═══════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _broadcast(event_type: str, data: Dict):
    """Broadcast to ThoughtBus if available."""
    try:
        from aureon.autonomous.aureon_mind_thought_action_hub import ThoughtBus
        bus = ThoughtBus.get_instance() if hasattr(ThoughtBus, "get_instance") else None
        if bus and hasattr(bus, "emit"):
            bus.emit({
                "source": "AureonTheSeer",
                "event": f"SEER_{event_type}",
                "data": data,
                "timestamp": time.time(),
            })
    except (ImportError, Exception):
        pass


# ─── Wire Enigma subscription at module load time ───
_wire_enigma_subscription()
