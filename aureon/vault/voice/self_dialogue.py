"""
SelfDialogueEngine: the vault talks to itself.

The dialogue engine orchestrates exchanges between multiple `VaultVoice`
personas. Each self-directed turn:

  1. The ChoiceGate decides whether to speak at all.
  2. A speaker is chosen.
  3. The speaker generates a statement from live vault state.
  4. That statement is fed back into the vault.
  5. A different listener responds.
  6. The listener's response is also fed back.
  7. The full utterance is recorded and published.

Human-directed turns use a different path: the human message is heard by
the full internal chorus first, then one final voice responds after
listening to the whole system.
"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from aureon.vault.voice.choice_gate import ChoiceGate, ChoiceGateDecision
from aureon.vault.voice.utterance import Utterance, VoiceStatement
from aureon.vault.voice.vault_voice import VaultVoice

logger = logging.getLogger("aureon.vault.dialogue")


DEFAULT_VOICE_WEIGHTS: Dict[str, float] = {
    "vault": 0.10,
    "queen": 0.25,
    "miner": 0.15,
    "scout": 0.10,
    "council": 0.15,
    "architect": 0.10,
    "lover": 0.15,
}


SELF_DIALOGUE_RELEASE_HOLD = (
    "self_dialogue_hold:production_magic_star_release_unavailable"
)


class SelfDialogueEngine:
    """
    Manages the vault's conversation with itself.
    """

    def __init__(
        self,
        vault: Any,
        voices: Optional[Dict[str, VaultVoice]] = None,
        choice_gate: Optional[ChoiceGate] = None,
        thought_bus: Any = None,
        adapter: Any = None,
        voice_weights: Optional[Dict[str, float]] = None,
        max_history: int = 200,
        rng_seed: Optional[int] = None,
    ):
        self.vault = vault
        self.voices = dict(voices or {})
        self.gate = choice_gate or ChoiceGate()
        self.voice_weights = voice_weights or DEFAULT_VOICE_WEIGHTS.copy()
        self.max_history = int(max_history)
        self._history: List[Utterance] = []
        self._total_utterances: int = 0
        self._total_decisions: int = 0
        self._lock = threading.RLock()
        self._rng = random.Random(rng_seed) if rng_seed is not None else random.Random()

        self._thought_bus = None
        self._adapter_supplied = adapter is not None
        self._thought_bus_supplied = thought_bus is not None

    def _wire_thought_bus(self) -> None:
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus

            self._thought_bus = get_thought_bus()
        except Exception:
            self._thought_bus = None

    def converse(self) -> Optional[Utterance]:
        """
        Run one turn of self-dialogue. Returns the full Utterance or
        None if the choice gate said stay silent.
        """
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        with self._lock:
            self._total_decisions += 1

            decision = self.gate.decide(self.vault)
            if not decision.should_speak:
                return None

            speaker_name = self._pick_speaker(decision)
            speaker = self.voices.get(speaker_name) or self.voices["vault"]

            try:
                fp_before = self.vault.fingerprint()
            except Exception:
                fp_before = ""

            statement = speaker.speak(self.vault)
            if statement is None:
                return None

            self._feedback_into_vault(speaker_name, statement)

            listener_name = self._pick_listener(speaker_name, decision)
            listener = self.voices.get(listener_name) or self.voices["vault"]
            response = listener.speak(self.vault)

            if response is not None:
                self._feedback_into_vault(listener_name, response)

            try:
                fp_after = self.vault.fingerprint()
            except Exception:
                fp_after = ""

            utterance = Utterance(
                utterance_id=uuid.uuid4().hex[:8],
                timestamp=time.time(),
                speaker=speaker_name,
                listener=listener_name,
                statement=statement,
                response=response,
                chosen=True,
                reasoning=decision.reasoning,
                urgency=decision.urgency,
                vault_fingerprint_before=fp_before,
                vault_fingerprint_after=fp_after,
            )

            self._history.append(utterance)
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history :]
            self._total_utterances += 1

            self._publish(utterance, decision)
            return utterance

    def _pick_speaker(self, decision: ChoiceGateDecision) -> str:
        preferred = decision.preferred_voice
        if preferred and preferred in self.voices:
            return preferred
        return self._weighted_choice(self.voices.keys())

    def _pick_listener(self, speaker_name: str, decision: ChoiceGateDecision) -> str:
        candidates = [name for name in self.voices.keys() if name != speaker_name]
        if not candidates:
            return speaker_name
        return self._weighted_choice(candidates)

    def _weighted_choice(self, names) -> str:
        names = list(names)
        weights = [self.voice_weights.get(name, 0.1) for name in names]
        total = sum(weights)
        if total <= 0:
            return names[0]
        roll = self._rng.random() * total
        acc = 0.0
        for name, weight in zip(names, weights):
            acc += weight
            if roll <= acc:
                return name
        return names[-1]

    def respond_to_human(
        self,
        message: str,
        voice_name: Optional[str] = None,
    ) -> Optional[Utterance]:
        """
        The vault responds to a message from a human.

        The human message is first ingested into the vault, then every
        active voice contributes to an internal chorus. Those internal
        statements are fed back into the vault so the final reply is
        built from the whole system rather than from a single isolated
        persona.
        """
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        message = (message or "").strip()
        if not message:
            return None

        with self._lock:
            self._total_decisions += 1

            try:
                pre_love = float(getattr(self.vault, "love_amplitude", 0.0) or 0.0)
            except Exception:
                pre_love = 0.0

            try:
                self.vault.love_amplitude = max(pre_love, 0.6)
                self.vault.ingest(
                    topic="human.message",
                    payload={
                        "text": message[:2000],
                        "timestamp": time.time(),
                    },
                    category="human_message",
                )
            except Exception as e:
                logger.debug("human message ingest failed: %s", e)

            speaker_name = self._pick_human_responder(voice_name)
            speaker = self.voices[speaker_name]

            try:
                fp_before = self.vault.fingerprint()
            except Exception:
                fp_before = ""

            chorus = self._run_human_chorus(message)
            response = self._speak_with_human_context(
                speaker,
                message,
                chorus_context=chorus,
                synthesis_mode=True,
            )
            if response is None or not response.text.strip():
                return None

            self._feedback_into_vault(speaker_name, response)

            try:
                fp_after = self.vault.fingerprint()
            except Exception:
                fp_after = ""

            utterance = Utterance(
                utterance_id=uuid.uuid4().hex[:8],
                timestamp=time.time(),
                speaker="human",
                listener=speaker_name,
                statement=VoiceStatement(
                    voice="human",
                    text=message,
                    vault_fingerprint=fp_before,
                    prompt_used=message,
                ),
                chorus=chorus,
                response=response,
                chosen=True,
                reasoning=f"human_message -> chorus({len(chorus)}) -> {speaker_name}",
                urgency=1.0,
                vault_fingerprint_before=fp_before,
                vault_fingerprint_after=fp_after,
            )

            self._history.append(utterance)
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history :]
            self._total_utterances += 1

            self._publish(
                utterance,
                ChoiceGateDecision(
                    should_speak=True,
                    urgency=1.0,
                    reasoning=f"human_message -> chorus({len(chorus)})",
                    preferred_voice=speaker_name,
                ),
            )
            return utterance

    def _speak_with_human_context(
        self,
        voice: VaultVoice,
        human_message: str,
        chorus_context: Optional[List[VoiceStatement]] = None,
        synthesis_mode: bool = False,
    ) -> Optional[VoiceStatement]:
        """
        Call `voice.speak(vault)` with the human's message folded into the
        composed prompt. This is done by temporarily monkey-patching the
        voice's `_compose_prompt_lines` for one call.
        """
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        original = voice._compose_prompt_lines
        original_max_tokens = getattr(voice, "max_tokens", 240)
        target_max_tokens = 160 if synthesis_mode else 72

        def composed_with_human(state):
            lines = original(state)
            lines.append("")
            lines.append("A human is speaking to the whole vault right now.")
            lines.append("Their message is:")
            lines.append(f'    "{human_message[:1000]}"')
            if chorus_context:
                lines.append("")
                lines.append("I have also heard the internal chorus:")
                for item in chorus_context:
                    excerpt = self._excerpt_text(item.text, limit=140)
                    lines.append(f"  - {item.voice}: {excerpt}")
            lines.append("")
            if synthesis_mode:
                lines.append("Respond directly to the human after listening to the whole chorus.")
                lines.append("Integrate the system into one coherent answer instead of speaking in isolation.")
                lines.append(
                    "Do not narrate the process. Do not dump metrics unless they matter. Use 3-6 sentences."
                )
            else:
                lines.append("Offer one distinct contribution to the internal chorus before the final reply is given.")
                lines.append(
                    "Speak only as this voice, add real perspective instead of repeating numbers, and use 1-3 sentences."
                )
            return lines

        voice.max_tokens = min(int(original_max_tokens or 240), target_max_tokens)
        voice._compose_prompt_lines = composed_with_human  # type: ignore[method-assign]
        try:
            return voice.speak(self.vault)
        finally:
            voice.max_tokens = original_max_tokens
            voice._compose_prompt_lines = original  # type: ignore[method-assign]

    def _pick_human_responder(self, voice_name: Optional[str]) -> str:
        if voice_name and voice_name in self.voices:
            return voice_name
        decision = self.gate.decide(self.vault)
        preferred = decision.preferred_voice
        if preferred and preferred in self.voices:
            return preferred
        if "council" in self.voices:
            return "council"
        return next(iter(self.voices.keys()), "vault")

    def _run_human_chorus(self, human_message: str) -> List[VoiceStatement]:
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        chorus: List[VoiceStatement] = []
        for voice_name, voice in self.voices.items():
            statement = self._speak_with_human_context(
                voice,
                human_message,
                chorus_context=chorus,
                synthesis_mode=False,
            )
            if statement is None or not statement.text.strip():
                continue
            chorus.append(statement)
            self._feedback_into_vault(voice_name, statement)
        return chorus

    @staticmethod
    def _excerpt_text(text: str, limit: int = 220) -> str:
        text = " ".join((text or "").split())
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)].rstrip() + "..."

    def speak_as(self, voice_name: str) -> Optional[Utterance]:
        """
        Force a specific voice to speak right now, bypassing the gate.
        Useful for UI buttons.
        """
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        if voice_name not in self.voices:
            return None

        with self._lock:
            self._total_decisions += 1
            try:
                fp_before = self.vault.fingerprint()
            except Exception:
                fp_before = ""

            speaker = self.voices[voice_name]
            statement = speaker.speak(self.vault)
            if statement is None:
                return None
            self._feedback_into_vault(voice_name, statement)

            candidates = [name for name in self.voices.keys() if name != voice_name]
            listener_name = self._weighted_choice(candidates) if candidates else voice_name
            listener = self.voices.get(listener_name) or self.voices["vault"]
            response = listener.speak(self.vault)
            if response is not None:
                self._feedback_into_vault(listener_name, response)

            try:
                fp_after = self.vault.fingerprint()
            except Exception:
                fp_after = ""

            utterance = Utterance(
                utterance_id=uuid.uuid4().hex[:8],
                timestamp=time.time(),
                speaker=voice_name,
                listener=listener_name,
                statement=statement,
                response=response,
                chosen=True,
                reasoning=f"forced_speak({voice_name})",
                urgency=1.0,
                vault_fingerprint_before=fp_before,
                vault_fingerprint_after=fp_after,
            )
            self._history.append(utterance)
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history :]
            self._total_utterances += 1
            return utterance

    def _feedback_into_vault(self, voice_name: str, statement: VoiceStatement) -> None:
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        try:
            self.vault.ingest(
                topic=f"vault.voice.{voice_name}",
                payload={
                    "voice": voice_name,
                    "text": statement.text,
                    "prompt_used": statement.prompt_used,
                    "vault_fingerprint": statement.vault_fingerprint,
                    "model": statement.model,
                },
                category="vault_voice",
            )
        except Exception as e:
            logger.debug("feedback into vault failed: %s", e)

    def _publish(self, utterance: Utterance, decision: ChoiceGateDecision) -> None:
        raise RuntimeError(SELF_DIALOGUE_RELEASE_HOLD)
        if not self._thought_bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought

            self._thought_bus.publish(
                Thought(
                    source="vault.dialogue",
                    topic="vault.voice.utterance",
                    payload={
                        "utterance_id": utterance.utterance_id,
                        "speaker": utterance.speaker,
                        "listener": utterance.listener,
                        "urgency": utterance.urgency,
                        "reasoning": utterance.reasoning,
                        "chorus_count": len(utterance.chorus),
                        "statement_text": utterance.statement.text if utterance.statement else "",
                        "response_text": utterance.response.text if utterance.response else "",
                        "vault_fingerprint_before": utterance.vault_fingerprint_before,
                        "vault_fingerprint_after": utterance.vault_fingerprint_after,
                        "preferred_voice": decision.preferred_voice,
                    },
                )
            )
        except Exception:
            pass

    @property
    def history(self) -> List[Utterance]:
        with self._lock:
            return list(self._history)

    def last_utterance(self) -> Optional[Utterance]:
        with self._lock:
            return self._history[-1] if self._history else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_decisions": self._total_decisions,
                "total_utterances": self._total_utterances,
                "speak_rate": self._total_utterances / max(self._total_decisions, 1),
                "history_size": len(self._history),
                "voices": list(self.voices.keys()),
                "gate": self.gate.get_status(),
                "last_utterance": self._history[-1].to_dict() if self._history else None,
            }
