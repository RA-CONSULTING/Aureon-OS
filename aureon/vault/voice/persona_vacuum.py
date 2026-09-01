"""
PersonaVacuum — Ten Voices in Superposition, Collapsed on Observation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT RELEASE: collapse, speaking, bus wiring, chorus publication, vault
feedback, action dispatch, and goal dispatch are hard-HOLD. The algorithms
remain inspectable, but no effect runs without a production Magic Star release.

The PersonaVacuum mirrors the 10-9-1 Source Law pattern at the persona layer:

    superposition  : ten ResonantPersona instances, none speaking
    passive input  : dj.track.drop (beat energy)
                     queen.source_law.cognition (Λ, ψ, Γ, node readings)
    trigger        : persona.observe (a thought on the bus, or a direct call)
    collapse       : softmax affinity over all ten → sample one → that one speaks
    output         : persona.collapse   {winner, probabilities}
                     persona.thought    {VoiceStatement payload}
                     vault.ingest(topic="persona.thought", payload=...)

Between observations the vacuum is idle — no polling, no prompt composition.
Matches the "Pandora's box sealed" discipline of
aureon/queen/queen_source_law.py.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import math
import random
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from aureon.vault.voice.affinity_chorus import AffinityChorus
from aureon.vault.voice.aureon_personas import (
    AUREON_PERSONA_REGISTRY,
    ResonantPersona,
    build_aureon_personas,
)
from aureon.vault.voice.persona_action import (
    ActionExecution,
    PersonaAction,
    PersonaActuator,
)
from aureon.vault.voice.utterance import VoiceStatement

logger = logging.getLogger("aureon.vault.voice.persona_vacuum")


PERSONA_VACUUM_RELEASE_HOLD = (
    "persona_vacuum_hold:production_magic_star_release_unavailable"
)

_DEFAULT_TEMPERATURE = 1.0


def _seed_from_scores(scores: Dict[str, float]) -> int:
    """Stable integer seed derived from a merged affinity map.

    Two vacuums that see the same map produce the same seed, so their
    softmax sampling agrees. Independent of transient vault state.
    """
    if not scores:
        return 0
    import hashlib
    canonical = ",".join(f"{k}:{scores[k]:.9f}" for k in sorted(scores.keys()))
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _softmax(scores: List[float], temperature: float) -> List[float]:
    """Numerically stable softmax with temperature. Empty input → []."""
    if not scores:
        return []
    t = max(1e-6, float(temperature))
    scaled = [float(s) / t for s in scores]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    z = sum(exps)
    if z <= 0:
        return [1.0 / len(scores)] * len(scores)
    return [e / z for e in exps]


class PersonaVacuum:
    """Ten resonant personas held in superposition; collapses on observation."""

    def __init__(
        self,
        adapter: Any = None,
        personas: Optional[Dict[str, ResonantPersona]] = None,
        thought_bus: Any = None,
        rng: Optional[random.Random] = None,
        temperature: Optional[float] = None,
        vault: Any = None,
        actuator: Optional[PersonaActuator] = None,
        chorus: Optional[AffinityChorus] = None,
        peer_id: Optional[str] = None,
        seed_fn: Optional[Callable[[], int]] = None,
    ):
        self._personas: Dict[str, ResonantPersona] = dict(personas or {})
        self._rng = rng or random.Random()
        self._temperature = self._resolve_temperature(temperature)
        self._lock = threading.Lock()
        self._latest_cognition: Dict[str, Any] = {}
        self._latest_drop: Dict[str, Any] = {}
        # symbolic_life_score from the most recent symbolic.life.pulse
        # — fallback when no vault attribute is available. The vault
        # attribute (set by SymbolicLifeBridge.pulse) takes precedence.
        self._latest_sls: Optional[float] = None
        self._last_winner: Optional[str] = None
        self._last_probabilities: Dict[str, float] = {}
        self._collapse_count = 0
        self._thought_bus = thought_bus
        self._subscribed = False
        self._vault_ref = vault
        self._actuator: PersonaActuator = actuator if actuator is not None else PersonaActuator(
            vault=vault,
            thought_bus=self._thought_bus,
        )
        self._last_action_execution: Optional[ActionExecution] = None
        self._last_goal_execution: Optional[ActionExecution] = None

        # Unified-collapse wiring — when a chorus is attached, affinity
        # vectors from all participating vacuums merge before softmax.
        # Combined with a seed_fn derived from a shared signal (usually
        # the vault fingerprint), two vacuums seeing the same merged
        # affinity will sample the same winner.
        self._chorus: Optional[AffinityChorus] = chorus
        self._seed_fn: Optional[Callable[[], int]] = seed_fn
        self._peer_id: str = str(peer_id) if peer_id else f"vacuum-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _resolve_temperature(explicit: Optional[float]) -> float:
        if explicit is not None:
            try:
                return max(1e-6, float(explicit))
            except (TypeError, ValueError):
                pass
        return _DEFAULT_TEMPERATURE

    @staticmethod
    def _load_thought_bus() -> Any:
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            return get_thought_bus()
        except Exception as e:
            logger.debug("PersonaVacuum: thought bus unavailable: %s", e)
            return None

    # ─────────────────────────────────────────────────────────────────────
    # Bus wiring
    # ─────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to the three trigger topics. Safe to call twice."""
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        if self._subscribed or self._thought_bus is None:
            return
        try:
            self._thought_bus.subscribe("dj.track.drop", self._on_drop)
            self._thought_bus.subscribe("queen.source_law.cognition", self._on_cognition)
            self._thought_bus.subscribe("persona.observe", self._on_observe_trigger)
            # Stage 4.3c — track the entity's substrate coherence so
            # _sample() can weight persona affinity by current SLS.
            self._thought_bus.subscribe("symbolic.life.pulse", self._on_symbolic_life_pulse)
            self._subscribed = True
            logger.info("[PERSONA VACUUM] subscribed; %d personas in superposition", len(self._personas))
        except Exception as e:
            logger.debug("PersonaVacuum: subscribe failed: %s", e)

    def _on_symbolic_life_pulse(self, thought: Any) -> None:
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        sls = payload.get("symbolic_life_score")
        if sls is None:
            return
        try:
            self._latest_sls = max(0.0, min(1.0, float(sls)))
        except (TypeError, ValueError):
            self._latest_sls = None

    def _current_sls(self, vault: Any) -> Optional[float]:
        """Resolve the current symbolic_life_score: vault attribute first
        (set by SymbolicLifeBridge.pulse), then the latest bus pulse."""
        if vault is not None:
            sls = getattr(vault, "current_symbolic_life_score", None)
            if sls is not None:
                try:
                    return max(0.0, min(1.0, float(sls)))
                except (TypeError, ValueError):
                    pass
        return self._latest_sls

    def _on_drop(self, thought: Any) -> None:
        payload = getattr(thought, "payload", {}) or {}
        if isinstance(payload, dict):
            with self._lock:
                self._latest_drop = dict(payload)

    def _on_cognition(self, thought: Any) -> None:
        payload = getattr(thought, "payload", {}) or {}
        if isinstance(payload, dict):
            with self._lock:
                self._latest_cognition = dict(payload)

    def _on_observe_trigger(self, thought: Any) -> None:
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        vault = payload.get("vault") if isinstance(payload, dict) else None
        self.observe(vault)

    # ─────────────────────────────────────────────────────────────────────
    # Collapse
    # ─────────────────────────────────────────────────────────────────────

    def observe(self, vault: Any = None) -> Optional[VoiceStatement]:
        """Open the box. Sample one persona. Have it speak. Publish. Feed back."""
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        state = self._build_state(vault)
        winner_name, probs, scores = self._sample(state)
        if winner_name is None:
            return None

        persona = self._personas[winner_name]
        statement = self._safe_speak(persona, vault, state)

        with self._lock:
            self._collapse_count += 1
            self._last_winner = winner_name
            self._last_probabilities = dict(probs)

        self._publish_collapse(winner_name, probs, scores, state)
        if statement is not None:
            self._publish_thought(statement)
            self._feed_vault(vault, statement)

        # Act, don't just speak. If the winning persona has a live trigger
        # for this state, hand its PersonaAction to the actuator.
        try:
            action = persona.propose_action(state)
        except Exception as e:
            logger.debug("PersonaVacuum: %s propose_action failed: %s", persona.NAME, e)
            action = None
        if action is not None:
            # The observe-time vault takes precedence over any init-time
            # vault — callers may observe against a different AureonVault
            # per call (mesh peers, embedded copies, test fixtures).
            if vault is not None:
                self._actuator.vault = vault
            self._last_action_execution = self._actuator.dispatch(
                persona.NAME, action, dict(state, persona=persona.NAME),
            )

        # Goals — strictly-triggered multi-step intentions. Under much
        # stricter conditions than propose_action so the backlog doesn't
        # flood. The actuator publishes ``goal.submit.request`` on the bus
        # for the existing aureon/core/goal_execution_engine to pick up.
        try:
            goal_text = persona.propose_goal(state)
        except Exception as e:
            logger.debug("PersonaVacuum: %s propose_goal failed: %s", persona.NAME, e)
            goal_text = None
        if goal_text:
            self._last_goal_execution = self._actuator.dispatch(
                persona.NAME,
                PersonaAction(
                    kind="goal.submit",
                    topic=str(goal_text),
                    payload={},
                    reason=f"{persona.NAME} proposes goal under strict trigger",
                    urgency=0.9,
                ),
                dict(state, persona=persona.NAME),
            )
        return statement

    def _build_state(self, vault: Any) -> Dict[str, Any]:
        """Vault slice ∪ latest cognition ∪ latest drop ∪ current SLS."""
        base: Dict[str, Any] = {}
        if vault is not None:
            try:
                base = dict(ResonantPersona._extract_slice(self._any_persona(), vault))
            except Exception as e:
                logger.debug("PersonaVacuum: vault slice failed: %s", e)
        with self._lock:
            cognition = dict(self._latest_cognition)
            drop = dict(self._latest_drop)
        base["consciousness_psi"] = float(cognition.get("consciousness_psi", 0.0) or 0.0)
        base["coherence_gamma"] = float(cognition.get("coherence_gamma", 0.0) or 0.0)
        base["consciousness_level"] = str(cognition.get("consciousness_level", "") or "")
        base["confidence"] = float(cognition.get("confidence", 0.0) or 0.0)
        base["node_readings"] = dict(cognition.get("node_readings") or {})
        base["dj_drop"] = drop
        # Stage 4.3c — surface the entity's substrate coherence so
        # _sample() can weight persona affinity by it.
        sls = self._current_sls(vault)
        if sls is not None:
            base["symbolic_life_score"] = sls
        return base

    def _any_persona(self) -> ResonantPersona:
        return next(iter(self._personas.values()))

    # ─────────────────────────────────────────────────────────────────────
    # Unified collapse (quorum phase)
    # ─────────────────────────────────────────────────────────────────────

    def contribute_affinity(self, vault: Any = None) -> Dict[str, float]:
        """Compute this vacuum's per-persona affinity for the current
        state and publish it to the chorus. This is the "many thoughts"
        phase — call it on every participating vacuum BEFORE any of
        them collapses, so each sampler sees the complete merged map.

        Returns the local score vector for inspection.
        """
        if self._chorus is not None:
            raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        state = self._build_state(vault)
        scores: Dict[str, float] = {}
        for name, persona in self._personas.items():
            try:
                v = float(persona.compute_affinity(state))
            except Exception:
                v = 0.0
            scores[name] = max(0.0, v)
        if self._chorus is not None:
            try:
                self._chorus.publish(self._peer_id, scores)
            except Exception as e:
                logger.debug("PersonaVacuum: chorus publish failed: %s", e)
        return scores

    def _sample(
        self, state: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, float], Dict[str, float]]:
        if self._chorus is not None:
            raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        names: List[str] = list(self._personas.keys())
        if not names:
            return None, {}, {}

        # 1. Local per-persona affinity — this vacuum's own "thought".
        local_scores: Dict[str, float] = {}
        for name in names:
            try:
                v = float(self._personas[name].compute_affinity(state))
            except Exception as e:
                logger.debug("PersonaVacuum: %s affinity failed: %s", name, e)
                v = 0.0
            local_scores[name] = max(0.0, v)

        # 2. If a chorus is attached, publish our vector so other vacuums
        #    can see it, then ask the chorus for the merged score map —
        #    many thoughts summed into one.
        if self._chorus is not None:
            try:
                self._chorus.publish(self._peer_id, local_scores)
            except Exception as e:
                logger.debug("PersonaVacuum: chorus publish failed: %s", e)
            try:
                merged_map = self._chorus.merged(
                    self_scores=local_scores,
                    self_peer_id=self._peer_id,
                )
            except Exception as e:
                logger.debug("PersonaVacuum: chorus merge failed: %s", e)
                merged_map = dict(local_scores)
        else:
            merged_map = dict(local_scores)

        raw: List[float] = [max(0.0, float(merged_map.get(n, 0.0))) for n in names]

        # Stage 4.3c — weight raw affinity by per-persona SLS modifier so
        # the ten facets serve one fluctuating state. Structure-building
        # personas (Engineer / QuantumPhysicist / Left, SLS_BIAS < 0)
        # rise when SLS is low; meaning-propagating personas (Mystic /
        # Painter / Elder / Right, SLS_BIAS > 0) rise when SLS is high.
        # Personas with SLS_BIAS = 0 are unaffected.
        sls = state.get("symbolic_life_score")
        if sls is not None:
            for i, n in enumerate(names):
                try:
                    mod = float(self._personas[n].sls_affinity_modifier(sls))
                except Exception as e:
                    logger.debug("PersonaVacuum: %s sls_modifier failed: %s", n, e)
                    mod = 1.0
                raw[i] = raw[i] * max(0.0, mod)

        probs = _softmax(raw, self._temperature)

        # 3. RNG for sampling.
        #    - Explicit seed_fn takes precedence (e.g. a shared tick
        #      counter, or an operator-supplied fingerprint).
        #    - Otherwise, if a chorus is attached, derive the seed from
        #      the merged affinity vector. Two vacuums that see the same
        #      merged map (what the chorus is FOR) get the same seed and
        #      collapse to the same winner — "one softmax, one draw,
        #      one voice".
        #    - Falling back to the vacuum's own rng means classical
        #      independent sampling.
        rng: random.Random = self._rng
        if self._seed_fn is not None:
            try:
                rng = random.Random(int(self._seed_fn()))
            except Exception as e:
                logger.debug("PersonaVacuum: seed_fn failed: %s", e)
        elif self._chorus is not None:
            rng = random.Random(_seed_from_scores(merged_map))

        r = rng.random()
        cum = 0.0
        winner = names[-1]
        for name, p in zip(names, probs):
            cum += p
            if r <= cum:
                winner = name
                break
        prob_dict = {n: p for n, p in zip(names, probs)}
        score_dict = {n: s for n, s in zip(names, raw)}
        return winner, prob_dict, score_dict

    def _safe_speak(
        self,
        persona: ResonantPersona,
        vault: Any,
        state: Optional[Dict[str, Any]] = None,
    ) -> Optional[VoiceStatement]:
        """Compose the persona's prompt from the *enriched* state the vacuum
        built (vault slice ∪ latest cognition ∪ latest DJ drop) and call the
        adapter directly, so cognition / drop fields appear in the prompt.

        Falls back to `persona.speak(vault)` if no state was supplied — this
        preserves the original behaviour for callers that don't build state.
        """
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        if state is None:
            try:
                return persona.speak(vault)
            except Exception as e:
                logger.debug("PersonaVacuum: %s speak failed: %s", persona.NAME, e)
                return None

        try:
            prompt_lines = persona._compose_prompt_lines(state)
        except Exception as e:
            logger.debug("PersonaVacuum: %s compose failed: %s", persona.NAME, e)
            return None
        if not prompt_lines:
            return None
        prompt = "\n".join(prompt_lines).strip()
        system_prompt = persona._system_prompt()

        response_text = ""
        model_name = ""
        tokens = 0
        if persona.adapter is not None:
            try:
                response = persona.adapter.prompt(
                    messages=[{"role": "user", "content": prompt}],
                    system=system_prompt,
                    max_tokens=persona.max_tokens,
                )
                response_text = (getattr(response, "text", "") or "").strip()
                model_name = getattr(response, "model", "") or ""
                usage = getattr(response, "usage", None)
                if isinstance(usage, dict):
                    tokens = int(usage.get("total_tokens", 0) or 0)
            except Exception as e:
                logger.debug("PersonaVacuum: %s adapter failed: %s", persona.NAME, e)
                response_text = f"[{persona.NAME}] adapter failed: {e}"
        else:
            response_text = f"[{persona.NAME}] no adapter."

        try:
            fp = vault.fingerprint() if vault is not None and hasattr(vault, "fingerprint") else ""
        except Exception:
            fp = ""

        return VoiceStatement(
            voice=persona.NAME,
            text=response_text,
            vault_fingerprint=str(fp or ""),
            prompt_used=prompt,
            system_prompt=system_prompt,
            model=model_name,
            tokens=tokens,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Publishing + vault feedback
    # ─────────────────────────────────────────────────────────────────────

    def _publish_collapse(
        self,
        winner: str,
        probs: Dict[str, float],
        scores: Dict[str, float],
        state: Dict[str, Any],
    ) -> None:
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="persona_vacuum",
                topic="persona.collapse",
                payload={
                    "winner": winner,
                    "probabilities": {k: round(v, 6) for k, v in probs.items()},
                    "scores": {k: round(v, 6) for k, v in scores.items()},
                    "cycle": self._collapse_count,
                    "temperature": self._temperature,
                    "trigger_state": {
                        "coherence_gamma": state.get("coherence_gamma"),
                        "consciousness_psi": state.get("consciousness_psi"),
                        "drop_energy": (state.get("dj_drop") or {}).get("energy"),
                    },
                },
            ))
        except Exception as e:
            logger.debug("PersonaVacuum: collapse publish failed: %s", e)

    def _publish_thought(self, statement: VoiceStatement) -> None:
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="persona_vacuum",
                topic="persona.thought",
                payload=statement.to_dict(),
            ))
        except Exception as e:
            logger.debug("PersonaVacuum: thought publish failed: %s", e)

    def _feed_vault(self, vault: Any, statement: VoiceStatement) -> None:
        raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
        if vault is None:
            return
        ingest: Optional[Callable] = getattr(vault, "ingest", None)
        if not callable(ingest):
            return
        try:
            ingest(topic="persona.thought", payload=statement.to_dict())
        except Exception as e:
            logger.debug("PersonaVacuum: vault ingest failed: %s", e)

    # ─────────────────────────────────────────────────────────────────────
    # Introspection
    # ─────────────────────────────────────────────────────────────────────

    @property
    def chorus(self) -> Optional[AffinityChorus]:
        return self._chorus

    @property
    def peer_id(self) -> str:
        return self._peer_id

    @property
    def actuator(self) -> PersonaActuator:
        return self._actuator

    @property
    def last_action_execution(self) -> Optional[ActionExecution]:
        return self._last_action_execution

    @property
    def last_goal_execution(self) -> Optional[ActionExecution]:
        return self._last_goal_execution

    @property
    def last_winner(self) -> Optional[str]:
        return self._last_winner

    @property
    def last_probabilities(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._last_probabilities)

    @property
    def collapse_count(self) -> int:
        return self._collapse_count

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def persona_names(self) -> List[str]:
        return list(self._personas.keys())

    def status(self) -> Dict[str, Any]:
        return {
            "status": "HOLD",
            "reason_code": "production_magic_star_release_unavailable",
            "production_ready": False,
            "effect_enabled": False,
            "subscribed": False,
            "persona_count": len(self._personas),
            "collapse_count": self._collapse_count,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────────────────────────────────────


_PERSONA_VACUUM: Optional[PersonaVacuum] = None
_SINGLETON_LOCK = threading.Lock()


def get_persona_vacuum() -> PersonaVacuum:
    """Return the process-wide PersonaVacuum, creating and wiring it on first use."""
    raise RuntimeError(PERSONA_VACUUM_RELEASE_HOLD)
    global _PERSONA_VACUUM
    with _SINGLETON_LOCK:
        if _PERSONA_VACUUM is None:
            _PERSONA_VACUUM = PersonaVacuum()
            _PERSONA_VACUUM.start()
        return _PERSONA_VACUUM


__all__ = [
    "PERSONA_VACUUM_RELEASE_HOLD",
    "PersonaVacuum",
    "get_persona_vacuum",
]
