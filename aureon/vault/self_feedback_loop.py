"""
AureonSelfFeedbackLoop — The Top-Level Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"The system treats itself and its contents as one big vault ...
 feeds back on itself and learns like shuffling Fibonacci cards at
 the speed of love and gratitude, self-quantifies via Casimir,
 actively metacognitive via the Auris nodes, deploys agents via HNC
 that act like white blood cells through the mycelium-cortex feedback
 loop, and pings the ThoughtBus with harmonic heartbeats."

Each tick runs the full synthesis:

  1. INGEST    — drain pending ThoughtBus events into the vault
  2. SHUFFLE   — FibonacciCardShuffler reorders recent cards
  3. QUANTIFY  — CasimirQuantifier measures vault drift
  4. VOTE      — AurisMetacognition runs the 9-node voter
  5. DEPLOY    — HNCDeployer decides how many cells to spawn
  6. HEAL      — WhiteCellAgent engages detected threats
  7. RALLY     — RallyCoordinator toggles burst mode
  8. PING      — HarmonicPinger emits the heartbeat
  9. FEEDBACK  — update gratitude from white cell outcomes
 10. SLEEP     — LoveGratitudeClock.sleep()
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from aureon.vault.aureon_vault import AureonVault
from aureon.vault.fibonacci_shuffler import FibonacciCardShuffler
from aureon.vault.love_gratitude_clock import LoveGratitudeClock
from aureon.vault.casimir_quantifier import CasimirQuantifier
from aureon.vault.auris_metacognition import AurisMetacognition
from aureon.vault.hnc_deployer import HNCDeployer
from aureon.vault.white_cell import (
    WhiteCellAgent,
    ThreatReport,
    detect_threats,
)
from aureon.vault.harmonic_pinger import HarmonicPinger
from aureon.vault.rally_coordinator import RallyCoordinator

# Provider and self-coder imports are deliberately absent while release is
# unavailable. Merely importing this module must remain inert.
SelfDialogueEngine = None
Utterance = None
_VOICE_AVAILABLE = False
get_self_enhancement_engine = None
_ENHANCE_AVAILABLE = False

logger = logging.getLogger("aureon.vault.loop")

SELF_FEEDBACK_RELEASE_HOLD = (
    "aureon_self_feedback_loop_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# TickResult — one cycle's worth of telemetry
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class TickResult:
    cycle: int
    timestamp: float
    vault_size: int
    casimir_force: float
    auris_consensus: str
    auris_agreeing: int
    auris_confidence: float
    cells_deployed: int
    cells_success: int
    rally_active: bool
    dominant_frequency_hz: int
    love_amplitude: float
    gratitude_score: float
    ping_sent: bool
    duration_s: float
    # Voice layer (optional)
    spoke: bool = False
    speaker: str = ""
    listener: str = ""
    utterance_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle": self.cycle,
            "timestamp": self.timestamp,
            "vault_size": self.vault_size,
            "casimir_force": round(self.casimir_force, 6),
            "auris_consensus": self.auris_consensus,
            "auris_agreeing": self.auris_agreeing,
            "auris_confidence": round(self.auris_confidence, 4),
            "cells_deployed": self.cells_deployed,
            "cells_success": self.cells_success,
            "rally_active": self.rally_active,
            "dominant_frequency_hz": self.dominant_frequency_hz,
            "love_amplitude": round(self.love_amplitude, 6),
            "gratitude_score": round(self.gratitude_score, 6),
            "ping_sent": self.ping_sent,
            "duration_s": round(self.duration_s, 4),
            "spoke": self.spoke,
            "speaker": self.speaker,
            "listener": self.listener,
            "utterance_preview": self.utterance_preview,
        }


# ─────────────────────────────────────────────────────────────────────────────
# AureonSelfFeedbackLoop
# ─────────────────────────────────────────────────────────────────────────────


class AureonSelfFeedbackLoop:
    """
    The top-level vault self-feedback orchestrator.

    Usage:
        loop = AureonSelfFeedbackLoop()
        loop.run(cycles=50)
        print(loop.get_status())

    or in background:
        loop = AureonSelfFeedbackLoop()
        loop.start()  # daemon thread
        ...
        loop.stop()
    """

    def __init__(
        self,
        vault: Optional[AureonVault] = None,
        base_interval_s: float = 1.0,
        tau_s: float = 30.0,
        max_cells_per_tick: int = 8,
        rally_burst_ticks: int = 20,
        rally_casimir_threshold: float = 5.0,
        auto_wire_bus: bool = False,
        enable_voice: bool = False,
        enable_self_enhancement: bool = False,
        enable_native_casimir: bool = False,
        enable_harmonic_buses: bool = False,
        enhance_every_n_ticks: int = 30,
    ):
        if any((
            auto_wire_bus,
            enable_voice,
            enable_self_enhancement,
            enable_native_casimir,
            enable_harmonic_buses,
        )):
            raise RuntimeError(SELF_FEEDBACK_RELEASE_HOLD)
        self.loop_id = uuid.uuid4().hex[:8]
        self.vault = vault or AureonVault()
        if auto_wire_bus:
            self.vault.wire_thought_bus()

        self.shuffler = FibonacciCardShuffler(love_bias=1.0)
        self.clock = LoveGratitudeClock(base_interval_s=base_interval_s)
        self.casimir = CasimirQuantifier(
            tau_s=tau_s,
            use_native_engine=enable_native_casimir,
        )
        self.auris = AurisMetacognition()
        self.deployer = HNCDeployer(max_cells_per_tick=max_cells_per_tick)
        self.pinger = HarmonicPinger(
            enable_chirp_bus=enable_harmonic_buses,
            enable_thought_bus=enable_harmonic_buses,
        )
        self.rally = RallyCoordinator(
            burst_ticks=rally_burst_ticks,
            casimir_threshold=rally_casimir_threshold,
        )

        # Optional voice layer — the vault talks to itself
        self.voice_engine: Any = None
        if enable_voice and _VOICE_AVAILABLE:
            try:
                self.voice_engine = SelfDialogueEngine(vault=self.vault)
            except Exception as e:
                logger.debug("voice engine init failed: %s", e)
                self.voice_engine = None

        self._cycle: int = 0
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._tick_history: List[TickResult] = []
        self._max_history: int = 500
        self._created_at: float = time.time()
        self._total_cells_deployed: int = 0
        self._total_cells_success: int = 0
        self._total_utterances: int = 0
        self._last_tick: Optional[TickResult] = None

        # Self-enhancement: Queen writes code to enhance herself.
        self._enhance_enabled = enable_self_enhancement and _ENHANCE_AVAILABLE
        self._enhance_every_n = max(1, enhance_every_n_ticks)
        self._total_enhancements: int = 0
        if self._enhance_enabled:
            try:
                self._enhancer = get_self_enhancement_engine(vault=self.vault)
            except Exception as e:
                logger.debug("self_enhancement_engine init failed: %s", e)
                self._enhancer = None
                self._enhance_enabled = False
        else:
            self._enhancer = None

    # ─────────────────────────────────────────────────────────────────────
    # One tick
    # ─────────────────────────────────────────────────────────────────────

    def tick(self) -> TickResult:
        """Run one full cycle of the self-feedback loop."""
        raise RuntimeError(SELF_FEEDBACK_RELEASE_HOLD)
        start = time.time()
        self._cycle += 1

        # 1. INGEST — ensure the vault has some minimum state even when the
        # bus is silent (synthetic boot signal so empty vaults still learn)
        if len(self.vault) < 3:
            self.vault.ingest(
                topic="vault.bootstrap",
                payload={"cycle": self._cycle, "loop_id": self.loop_id},
                category="bootstrap",
            )

        # 2. SHUFFLE — golden-ratio replay of recent cards (pure observation,
        # does not mutate vault; the shuffle walks the deck to touch every
        # card's love_weight in the fibonacci stride pattern)
        self.shuffler.shuffle(self.vault.recent(n=64))

        # 3. QUANTIFY — Casimir force between present and past vault
        reading = self.casimir.measure(self.vault)

        # 4. VOTE — 9 Auris nodes inspect the vault
        vote_result = self.auris.vote(self.vault)

        # 5. DEPLOY — HNC decides how many white cells to spawn
        decision = self.deployer.should_deploy(self.vault, vote_result)

        # 6. HEAL — actually engage detected threats with white cells
        cells_deployed = 0
        cells_success = 0
        if decision.count > 0:
            threats = detect_threats(self.vault, max_threats=decision.count)
            if not threats and decision.count > 0:
                # Synthesise a generic "cycle integrity" threat so the cell
                # still has something to engage
                threats = [ThreatReport(
                    threat_id=f"cycle_{self._cycle}",
                    kind="casimir_drift",
                    description=f"scheduled maintenance tick {self._cycle}",
                    severity=0.3,
                )]
            for threat in threats[:decision.count]:
                cell = WhiteCellAgent()
                outcome = cell.engage(threat)
                cells_deployed += 1
                if outcome.success:
                    cells_success += 1
                # Fold the outcome into the vault as an execution card
                self.vault.ingest(
                    topic="skill.executed.white_cell",
                    payload={
                        "ok": outcome.success,
                        "skill_name": outcome.recovery_skill_name or "",
                        "error": outcome.error,
                        "duration_s": outcome.duration_s,
                        "threat_kind": threat.kind,
                    },
                    category="skill_execution",
                )

        self._total_cells_deployed += cells_deployed
        self._total_cells_success += cells_success

        # 7. RALLY — toggle burst mode based on vote + Casimir force
        self.rally.update(self.vault, vote_result)

        # 8. PING — emit the harmonic heartbeat on the current dominant freq
        freq = int(self.vault.dominant_frequency_hz or 528)
        love = float(self.vault.love_amplitude or 0.5)
        conf = float(vote_result.confidence)
        ping_result = self.pinger.ping(
            frequency_hz=freq,
            coherence=max(0.0, min(1.0, love)),
            confidence=max(0.0, min(1.0, conf)),
            payload={
                "cycle": self._cycle,
                "vault_size": len(self.vault),
                "casimir_force": reading.force,
                "auris_consensus": vote_result.consensus,
                "rally_active": self.rally.active,
                "loop_id": self.loop_id,
            },
        )

        # 9. SPEAK — the vault talks to itself (choice gate decides whether)
        spoke = False
        speaker_name = ""
        listener_name = ""
        utterance_preview = ""
        if self.voice_engine is not None:
            try:
                utterance = self.voice_engine.converse()
                if utterance is not None:
                    spoke = True
                    self._total_utterances += 1
                    speaker_name = utterance.speaker
                    listener_name = utterance.listener
                    if utterance.statement and utterance.statement.text:
                        utterance_preview = utterance.statement.text.strip().replace("\n", " ")[:120]
            except Exception as e:
                logger.debug("voice step error: %s", e)

        # 10. ENHANCE — every N ticks, Queen writes code to enhance herself.
        # Runs in the same thread but is gated by the cycle counter so it
        # doesn't slow every tick; heavy LLM work is bounded by the engine.
        if (
            self._enhance_enabled
            and self._enhancer is not None
            and (self._cycle % self._enhance_every_n) == 0
        ):
            try:
                rec = self._enhancer.enhance_once()
                if rec.registered:
                    self._total_enhancements += 1
                    logger.info(
                        "[loop] self-enhancement: new skill '%s' registered "
                        "(cycle=%d)",
                        rec.skill_name, self._cycle,
                    )
            except Exception as e:
                logger.debug("enhancement step error: %s", e)

        # Record the tick
        result = TickResult(
            cycle=self._cycle,
            timestamp=start,
            vault_size=len(self.vault),
            casimir_force=reading.force,
            auris_consensus=vote_result.consensus,
            auris_agreeing=vote_result.agreeing,
            auris_confidence=vote_result.confidence,
            cells_deployed=cells_deployed,
            cells_success=cells_success,
            rally_active=self.rally.active,
            dominant_frequency_hz=freq,
            love_amplitude=love,
            gratitude_score=self.vault.gratitude_score,
            ping_sent=ping_result.sent_thought or ping_result.sent_chirp,
            duration_s=time.time() - start,
            spoke=spoke,
            speaker=speaker_name,
            listener=listener_name,
            utterance_preview=utterance_preview,
        )

        self._tick_history.append(result)
        if len(self._tick_history) > self._max_history:
            self._tick_history = self._tick_history[-self._max_history:]
        self._last_tick = result

        return result

    # ─────────────────────────────────────────────────────────────────────
    # Run loops
    # ─────────────────────────────────────────────────────────────────────

    def run(self, cycles: Optional[int] = None, sleep_between: bool = False) -> List[TickResult]:
        """
        Run the feedback loop synchronously.

        Args:
            cycles: number of cycles to run (None = infinite)
            sleep_between: whether to honor the LoveGratitudeClock cadence
                           (False runs tight for tests; True uses real timing)
        """
        raise RuntimeError(SELF_FEEDBACK_RELEASE_HOLD)
        results: List[TickResult] = []
        i = 0
        self._running = True
        try:
            while self._running:
                if cycles is not None and i >= cycles:
                    break
                result = self.tick()
                results.append(result)
                if sleep_between:
                    self.clock.sleep(self.vault)
                i += 1
        finally:
            self._running = False
        return results

    def start(self) -> None:
        """Start the loop in a background daemon thread using the real clock."""
        raise RuntimeError(SELF_FEEDBACK_RELEASE_HOLD)
        if self._running:
            return
        self._running = True

        def _loop():
            while self._running:
                try:
                    self.tick()
                except Exception as e:
                    logger.error("tick failed: %s", e)
                # Respect love+gratitude cadence
                try:
                    self.clock.sleep(self.vault)
                except Exception:
                    time.sleep(1.0)

        self._thread = threading.Thread(target=_loop, daemon=True, name=f"VaultLoop-{self.loop_id}")
        self._thread.start()

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    # ─────────────────────────────────────────────────────────────────────
    # Status / introspection
    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        voice_status = None
        if self.voice_engine is not None:
            try:
                voice_status = self.voice_engine.get_status()
            except Exception:
                voice_status = None
        return {
            "loop_id": self.loop_id,
            "cycles": self._cycle,
            "running": self._running,
            "uptime_s": round(time.time() - self._created_at, 2),
            "total_cells_deployed": self._total_cells_deployed,
            "total_cells_success": self._total_cells_success,
            "total_utterances": self._total_utterances,
            "cell_success_rate": (
                self._total_cells_success / max(self._total_cells_deployed, 1)
            ),
            "total_enhancements": self._total_enhancements,
            "enhancement_enabled": self._enhance_enabled,
            "vault": self.vault.get_status(),
            "clock": self.clock.get_status(),
            "casimir": self.casimir.get_status(),
            "auris": self.auris.get_status(),
            "deployer": self.deployer.get_status(),
            "pinger": self.pinger.get_status(),
            "rally": self.rally.get_status(),
            "voice": voice_status,
            "last_tick": self._last_tick.to_dict() if self._last_tick else None,
        }

    @property
    def tick_history(self) -> List[TickResult]:
        return list(self._tick_history)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────────────────────────────────────

_loop_instance: Optional[AureonSelfFeedbackLoop] = None
_loop_lock = threading.Lock()


def get_self_feedback_loop(**kwargs) -> AureonSelfFeedbackLoop:
    """Return the singleton self-feedback loop, creating it on first call."""
    global _loop_instance
    with _loop_lock:
        if _loop_instance is None:
            _loop_instance = AureonSelfFeedbackLoop(**kwargs)
        return _loop_instance
