"""
🕶️ Voice / glasses bridge — the "brain chip without circuits" seam.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The vision: a two-way conversation with Aureon streamed to a pair of Ray-Ban
glasses — you talk, Aureon answers, no PC load, the data centre a black box.

This module is the SKETCH of that path, not the finished thing. It wires a
transcribed utterance → :class:`AureonOperator` → text-for-speech, and marks the
capture/playback edges with ``# TODO(glasses)`` so the hardware layer has clean
seams to land on. It leans on the existing unified voice agent
(``aureon/autonomous/aureon_unified_voice_agent.py``) when present, and falls
back to returning plain text otherwise.

Nothing here reaches the network by itself — it only calls the operator, which
is offline-first.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict

from aureon.operator.aureon_operator import AureonOperator

logger = logging.getLogger("aureon.operator.voice_bridge")


@dataclass
class VoiceTurn:
    """One round-trip of the two-way conversation."""

    heard: str = ""
    spoke: str = ""
    trace_id: str = ""
    verdict: str = "APPROVED"
    blocked: bool = False
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heard": self.heard,
            "spoke": self.spoke,
            "trace_id": self.trace_id,
            "verdict": self.verdict,
            "blocked": self.blocked,
            "detail": self.detail,
        }


class VoiceGlassesBridge:
    """Routes a spoken utterance through the operator and returns speakable text."""

    def __init__(self, operator: AureonOperator | None = None, session_id: str | None = None):
        self.operator = operator or AureonOperator()
        self.session_id = session_id
        self._voice_agent = None
        self._voice_agent_tried = False

    # -- capture edge -----------------------------------------------------------

    def listen(self) -> str:
        """
        Return the next transcribed utterance from the glasses mic.

        # TODO(glasses): wire Ray-Ban mic capture + streaming STT here. For now
        # this raises so callers use ``say()`` with an already-transcribed string.
        """
        raise NotImplementedError(
            "glasses mic capture not wired yet — call say(transcribed_text) instead"
        )

    # -- the round-trip ---------------------------------------------------------

    def say(self, utterance: str) -> VoiceTurn:
        """Take a transcribed utterance, route it through the operator, return the reply."""
        resp = self.operator.respond(utterance, session_id=self.session_id)
        turn = VoiceTurn(
            heard=utterance,
            spoke=resp.text,
            trace_id=resp.trace_id,
            verdict=resp.conscience_verdict,
            blocked=resp.blocked,
            detail={
                "providers": [a.provider for a in resp.answers if a.ok],
                "agreement": resp.consensus.agreement if resp.consensus else 0.0,
                "sources": [s.get("path", "") for s in (resp.grounding.sources if resp.grounding else [])],
            },
        )
        self._speak(turn.spoke)
        return turn

    # -- playback edge ----------------------------------------------------------

    def _speak(self, text: str) -> None:
        """
        Emit ``text`` as speech to the glasses earpiece.

        Uses the unified voice agent's TTS if available; otherwise a no-op.
        # TODO(glasses): route audio to the Ray-Ban speaker / bone-conduction path.
        """
        agent = self._get_voice_agent()
        if agent is None:
            logger.debug("no voice agent; would speak: %s", text[:80])
            return
        for method in ("speak", "say", "tts"):
            fn = getattr(agent, method, None)
            if callable(fn):
                try:
                    fn(text)
                    return
                except Exception as exc:  # noqa: BLE001
                    logger.debug("voice agent %s failed: %s", method, exc)
        logger.debug("voice agent present but no speak method; text: %s", text[:80])

    def _get_voice_agent(self):
        if self._voice_agent_tried:
            return self._voice_agent
        self._voice_agent_tried = True
        try:
            from aureon.autonomous import aureon_unified_voice_agent as uva

            for factory in ("get_voice_agent", "AureonUnifiedVoiceAgent", "VoiceAgent"):
                obj = getattr(uva, factory, None)
                if obj is not None:
                    self._voice_agent = obj() if callable(obj) else obj
                    break
        except Exception as exc:  # noqa: BLE001
            logger.debug("unified voice agent unavailable: %s", exc)
            self._voice_agent = None
        return self._voice_agent


__all__ = ["VoiceGlassesBridge", "VoiceTurn"]
