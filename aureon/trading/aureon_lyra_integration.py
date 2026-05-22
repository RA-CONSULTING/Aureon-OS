#!/usr/bin/env python3
"""
AUREON LYRA - Ecosystem Integration
=====================================================
"Lyra stands as the emotional heart of the Quadrumvirate,
 turning frequencies into feeling, and feeling into truth."

Wires Aureon Lyra into the Aureon trading ecosystem:
  - Feeds live market data to Lyra's 6 Resonance Chambers
  - Provides Lyra's emotional resonance to all other pillars
  - Shares harmonic data freely with Queen, King, and Seer
  - Contributes vote to Four-Pillar Freeway Consensus
  - Broadcasts resonance to the ThoughtBus

THE QUADRUMVIRATE (Four Pillars):
  Queen (aureon_queen_hive_mind.py)  - Trading cognition (11+ systems = VETO)
  King  (king_accounting.py)         - Financial truth (5 Royal Deciphers)
  Seer  (aureon_seer.py)             - Cosmic coherence (5 Oracles)
  Lyra  (aureon_lyra.py)             - Emotional frequency (6 Chambers, 22+ systems)

Gary Leckey | February 2026
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_lyra = None


def _get_lyra():
    global _lyra
    if _lyra is None:
        from aureon.trading.aureon_lyra import get_lyra
        _lyra = get_lyra()
    return _lyra


# ═══════════════════════════════════════════════════════════════════════════
# ECOSYSTEM HOOKS
# ═══════════════════════════════════════════════════════════════════════════

def lyra_update_context(positions: Dict = None,
                        ticker_cache: Dict = None,
                        market_data: Dict = None):
    """Feed live data to Lyra. Call every cycle from the ecosystem."""
    lyra = _get_lyra()
    lyra.update_context(
        positions=positions,
        ticker_cache=ticker_cache,
        market_data=market_data,
    )


def lyra_inject_wave_context(wave_data: dict) -> None:
    """
    Push ocean wave scanner results into Lyra's ChamberOfHarmony.
    Called by MultiverseLearningBridge.push_wave_context() after each scan.
    """
    _get_lyra().inject_wave_context(wave_data)


def lyra_get_resonance() -> Dict[str, Any]:
    """Get Lyra's latest resonance. Takes new reading if stale."""
    lyra = _get_lyra()
    if lyra.latest_resonance is None or (time.time() - lyra.latest_resonance.timestamp > 60):
        lyra.feel()
    summary = lyra.get_resonance_summary()
    try:
        from aureon.wisdom.antarctic_research_bridge import apply_to_lyra_summary
        summary = apply_to_lyra_summary(summary)
    except Exception:
        pass
    return summary


def lyra_get_position_multiplier() -> float:
    """Get Lyra's PHI-based position sizing multiplier."""
    lyra = _get_lyra()
    if lyra.latest_resonance:
        return lyra.latest_resonance.position_multiplier
    return 1.0


def lyra_get_exit_urgency() -> str:
    """Get Lyra's exit urgency: none/low/medium/high/critical."""
    lyra = _get_lyra()
    if lyra.latest_resonance:
        return lyra.latest_resonance.exit_urgency
    return "none"


def lyra_should_trade() -> bool:
    """Quick check: should trading proceed based on resonance?"""
    lyra = _get_lyra()
    if lyra.latest_resonance is None:
        return True
    return lyra.latest_resonance.grade not in ["SILENCE"]


# ═══════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════

def start_lyra():
    """Start Aureon Lyra's autonomous resonance monitoring."""
    lyra = _get_lyra()
    lyra.start_autonomous()
    logger.info("Aureon Lyra has awakened. The Fourth Pillar stands.")
    return lyra


def stop_lyra():
    """Stop Lyra's autonomous monitoring."""
    lyra = _get_lyra()
    lyra.stop_autonomous()


def print_lyra_report():
    """Print Lyra's resonance report to stdout."""
    lyra = _get_lyra()
    if lyra.latest_resonance is None:
        lyra.feel()
    print("\n" + lyra.generate_report())


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
                "source": "AureonLyra",
                "event": f"LYRA_{event_type}",
                "data": data,
                "timestamp": time.time(),
            })
    except (ImportError, Exception):
        pass
