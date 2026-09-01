"""
HarmonicPinger — ThoughtBus + ChirpBus Harmonic Heartbeat
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Giving the ThoughtBus system harmonic pings for neural pathway connectivity."

Each tick of the self-feedback loop emits a "ping" on both:

  • ChirpBus: an 8-byte packet tuned to the current dominant frequency.
    Any subsystem listening on that frequency wakes up. Others stay asleep.
  • ThoughtBus: a 'vault.heartbeat' Thought with full vault status so
    higher-level subscribers can trace the feedback loop.

The ChirpBus path is the real harmonic ping (kHz-rate, low-latency). The
ThoughtBus path is the observability channel.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("aureon.vault.pinger")

HARMONIC_PINGER_RELEASE_HOLD = (
    "harmonic_pinger_hold:production_magic_star_release_unavailable"
)


@dataclass
class PingResult:
    sent_chirp: bool
    sent_thought: bool
    frequency_hz: int
    coherence: float
    timestamp: float


class HarmonicPinger:
    """
    Dual-channel ping emitter.

    Usage:
        pinger = HarmonicPinger()
        result = pinger.ping(frequency_hz=528, coherence=0.85,
                             payload={"cycle": 42})
    """

    def __init__(
        self,
        *,
        enable_chirp_bus: bool = False,
        enable_thought_bus: bool = False,
    ):
        if enable_chirp_bus or enable_thought_bus:
            raise RuntimeError(HARMONIC_PINGER_RELEASE_HOLD)
        self._chirp_bus: Any = None
        self._thought_bus: Any = None
        self._chirp_kind: str = "stub"
        self._total_pings: int = 0
        self._chirp_success: int = 0
        self._thought_success: int = 0
        if enable_chirp_bus:
            self._load_chirp_bus()
        if enable_thought_bus:
            self._load_thought_bus()

    def _load_chirp_bus(self) -> None:
        raise RuntimeError(HARMONIC_PINGER_RELEASE_HOLD)
        try:
            from aureon.core.aureon_chirp_bus import get_chirp_bus
            self._chirp_bus = get_chirp_bus(create_if_missing=True)
            self._chirp_kind = "native" if self._chirp_bus is not None else "stub"
            if self._chirp_kind == "native":
                logger.info("HarmonicPinger: wired to native ChirpBus")
        except Exception as e:
            logger.debug("ChirpBus unavailable: %s", e)
            self._chirp_bus = None
            self._chirp_kind = "stub"

    def _load_thought_bus(self) -> None:
        raise RuntimeError(HARMONIC_PINGER_RELEASE_HOLD)
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._thought_bus = get_thought_bus()
        except Exception as e:
            logger.debug("ThoughtBus unavailable: %s", e)
            self._thought_bus = None

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def ping(
        self,
        frequency_hz: int = 528,
        coherence: float = 1.0,
        confidence: float = 1.0,
        payload: Optional[Dict[str, Any]] = None,
    ) -> PingResult:
        """Emit a ping on both channels. Returns PingResult."""
        raise RuntimeError(HARMONIC_PINGER_RELEASE_HOLD)
        self._total_pings += 1
        freq_int = int(max(0, min(65535, frequency_hz)))
        coh = float(max(0.0, min(1.0, coherence)))
        conf = float(max(0.0, min(1.0, confidence)))

        chirp_ok = self._emit_chirp(freq_int, coh, conf)
        thought_ok = self._emit_thought(freq_int, coh, conf, payload or {})

        if chirp_ok:
            self._chirp_success += 1
        if thought_ok:
            self._thought_success += 1

        return PingResult(
            sent_chirp=chirp_ok,
            sent_thought=thought_ok,
            frequency_hz=freq_int,
            coherence=coh,
            timestamp=time.time(),
        )

    def _emit_chirp(self, freq: int, coh: float, conf: float) -> bool:
        """Emit a ChirpPacket PING on the real ChirpBus if available."""
        raise RuntimeError(HARMONIC_PINGER_RELEASE_HOLD)
        if not self._chirp_bus:
            return False
        try:
            # Prefer the high-level emit_message helper if present
            if hasattr(self._chirp_bus, "emit_message"):
                try:
                    from aureon.core.aureon_chirp_bus import ChirpType, ChirpDirection
                    return bool(self._chirp_bus.emit_message(
                        message="vault-heartbeat",
                        direction=ChirpDirection.UP,
                        coherence=coh,
                        confidence=conf,
                        symbol="vault",
                        frequency=freq,
                        amplitude=int(128 + coh * 127),
                        message_type=ChirpType.PING,
                    ))
                except Exception:
                    return bool(self._chirp_bus.emit_message(
                        message="vault-heartbeat",
                        coherence=coh,
                        confidence=conf,
                        frequency=freq,
                    ))

            # Fall back to the low-level emit(packet)
            if hasattr(self._chirp_bus, "emit"):
                try:
                    from aureon.core.aureon_chirp_bus import ChirpPacket, ChirpType, ChirpDirection
                    packet = ChirpPacket(
                        message_type=ChirpType.PING,
                        direction=ChirpDirection.UP,
                        coherence=coh,
                        confidence=conf,
                        frequency=freq,
                        amplitude=int(128 + coh * 127),
                    )
                    return bool(self._chirp_bus.emit(packet))
                except Exception:
                    pass
        except Exception as e:
            logger.debug("chirp emit failed: %s", e)

        return False

    def _emit_thought(
        self,
        freq: int,
        coh: float,
        conf: float,
        payload: Dict[str, Any],
    ) -> bool:
        """Publish a heartbeat Thought for observability."""
        raise RuntimeError(HARMONIC_PINGER_RELEASE_HOLD)
        if not self._thought_bus:
            return False
        try:
            from aureon.core.aureon_thought_bus import Thought
            full = dict(payload or {})
            full.update({
                "frequency_hz": freq,
                "coherence": coh,
                "confidence": conf,
            })
            self._thought_bus.publish(Thought(
                source="vault.pinger",
                topic="vault.heartbeat",
                payload=full,
            ))
            return True
        except Exception as e:
            logger.debug("thought emit failed: %s", e)
            return False

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "chirp_kind": self._chirp_kind,
            "chirp_bus_wired": self._chirp_bus is not None,
            "thought_bus_wired": self._thought_bus is not None,
            "total_pings": self._total_pings,
            "chirp_success": self._chirp_success,
            "thought_success": self._thought_success,
        }
