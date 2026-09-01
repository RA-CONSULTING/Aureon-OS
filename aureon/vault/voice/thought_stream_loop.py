"""
ThoughtStreamLoop — Background Daemon for Continuous Self-Dialogue
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Runs the SelfDialogueEngine in a background daemon thread, pacing
itself on the LoveGratitudeClock. Each iteration:

  1. Call engine.converse() (which may return None if the gate said wait)
  2. If an utterance was produced, print it and/or invoke a callback
  3. Sleep for the love+gratitude interval
  4. Repeat until stop()

This is how the vault "speaks" continuously — an autonomous, asynchronous
stream of self-authored thought that runs alongside the main feedback
loop without blocking it.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from aureon.vault.voice.self_dialogue import SelfDialogueEngine
from aureon.vault.voice.utterance import Utterance

logger = logging.getLogger("aureon.vault.thought_stream")


THOUGHT_STREAM_RELEASE_HOLD = (
    "thought_stream_hold:production_magic_star_release_unavailable"
)


@dataclass
class ThoughtStreamStatus:
    running: bool
    cycles: int
    utterances: int
    silent_cycles: int
    last_utterance_id: Optional[str]
    last_speaker: Optional[str]


class ThoughtStreamLoop:
    """
    Runs SelfDialogueEngine.converse() on a loop.

    Usage:
        stream = ThoughtStreamLoop(vault=my_vault)
        stream.start()
        ...
        stream.stop()

    Or synchronously for tests:
        stream = ThoughtStreamLoop(vault=my_vault)
        utterances = stream.run_n_cycles(50)
    """

    def __init__(
        self,
        vault: Any,
        engine: Optional[SelfDialogueEngine] = None,
        clock: Any = None,
        on_utterance: Optional[Callable[[Utterance], None]] = None,
        base_interval_s: float = 1.0,
        auto_wire: bool = False,
    ):
        self.vault = vault
        self.engine = engine
        self.on_utterance = on_utterance

        if auto_wire:
            raise RuntimeError(THOUGHT_STREAM_RELEASE_HOLD)
        self.clock = clock
        self.base_interval_s = float(base_interval_s)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycles = 0
        self._utterances_count = 0
        self._silent_cycles = 0
        self._last_utterance: Optional[Utterance] = None

    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(THOUGHT_STREAM_RELEASE_HOLD)
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="VaultThoughtStream")
        self._thread.start()
        logger.info("ThoughtStreamLoop started")

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def _loop(self) -> None:
        raise RuntimeError(THOUGHT_STREAM_RELEASE_HOLD)
        while self._running:
            try:
                self._tick_once()
            except Exception as e:
                logger.debug("thought stream tick error: %s", e)
            # Sleep according to love+gratitude cadence
            try:
                if self.clock is not None:
                    self.clock.sleep(self.vault)
                else:
                    time.sleep(self.base_interval_s)
            except Exception:
                time.sleep(self.base_interval_s)

    def _tick_once(self) -> Optional[Utterance]:
        raise RuntimeError(THOUGHT_STREAM_RELEASE_HOLD)
        self._cycles += 1
        utterance = self.engine.converse()
        if utterance is None:
            self._silent_cycles += 1
            return None
        self._utterances_count += 1
        self._last_utterance = utterance
        if self.on_utterance is not None:
            try:
                self.on_utterance(utterance)
            except Exception as e:
                logger.debug("on_utterance callback failed: %s", e)
        return utterance

    # ─────────────────────────────────────────────────────────────────────
    # Synchronous runs (for tests)
    # ─────────────────────────────────────────────────────────────────────

    def run_n_cycles(self, n: int, sleep_between: bool = False) -> List[Utterance]:
        """Run `n` cycles synchronously and return all utterances produced."""
        raise RuntimeError(THOUGHT_STREAM_RELEASE_HOLD)
        out: List[Utterance] = []
        self._running = True
        try:
            for _ in range(int(n)):
                if not self._running:
                    break
                u = self._tick_once()
                if u is not None:
                    out.append(u)
                if sleep_between and self.clock is not None:
                    self.clock.sleep(self.vault)
        finally:
            self._running = False
        return out

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> ThoughtStreamStatus:
        return ThoughtStreamStatus(
            running=self._running,
            cycles=self._cycles,
            utterances=self._utterances_count,
            silent_cycles=self._silent_cycles,
            last_utterance_id=self._last_utterance.utterance_id if self._last_utterance else None,
            last_speaker=self._last_utterance.speaker if self._last_utterance else None,
        )
