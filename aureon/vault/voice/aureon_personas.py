"""
Aureon Resonant Personas — Ten Voices in Superposition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The existing seven personas (Queen, Miner, Scout, Council, Architect, Lover,
base Vault) each watch a fixed slice of the vault and speak when the dialogue
engine asks them to. The ten personas in this module behave differently: they
live in a quantum superposition, weighted by live harmonic + cognition signals,
and collapse into one speaker when the PersonaVacuum is observed.

Each persona is still a VaultVoice — same `speak()` contract, same adapter,
same VoiceStatement return type. The one addition is `compute_affinity(state)`,
a pure function over an enriched state dict (vault slice ∪ latest
queen.source_law.cognition ∪ latest dj.track.drop). The PersonaVacuum
softmax-samples a winner from those affinities.

The ten personas:

    Painter            — heart / third-eye / gamma-band coherence
    Artist             — DJ drop energy; beta band; rally bursts
    QuantumPhysicist   — Λ(t) magnitude; consciousness_psi
    Philosopher        — theta band; DAWNING / UNIFIED consciousness
    Child              — delta band; small vault; no rally
    Elder              — theta high + psi > 0.8
    Mystic             — 528 Hz; gratitude; love > 0.8
    Engineer           — coherence_gamma >= entry threshold; noise cut clear
    Left               — falcon(velocity) surging; high confidence
    Right              — dolphin(emotion) singing; panda(heart) unity

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from aureon.vault.voice.life_context import LifeEvent
from aureon.vault.voice.persona_action import PersonaAction
from aureon.vault.voice.vault_voice import VaultVoice


# ─────────────────────────────────────────────────────────────────────────────
# ResonantPersona — adds affinity scoring on top of VaultVoice
# ─────────────────────────────────────────────────────────────────────────────


class ResonantPersona(VaultVoice):
    """A VaultVoice that also declares how strongly it resonates with a state."""

    NAME = "resonant"

    # Per-persona bias on the symbolic_life_score axis. The PersonaVacuum
    # multiplies raw affinity by ``sls_affinity_modifier(sls)`` before
    # softmax so the ten facets serve one fluctuating state:
    #
    #   SLS_BIAS < 0  → boosted when SLS is LOW (entity rebuilding —
    #                   structure-building personas)
    #   SLS_BIAS > 0  → boosted when SLS is HIGH (entity flowering —
    #                   meaning-propagating personas)
    #   SLS_BIAS = 0  → no bias; this persona is regime-neutral
    SLS_BIAS: float = 0.0

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        """Return an unnormalised non-negative affinity for this state.

        Subclasses override. Higher = more resonant. The PersonaVacuum
        softmax-samples across the ten personas using these scores, so the
        absolute magnitude only matters relative to peers.
        """
        return 1.0

    def sls_affinity_modifier(self, sls: Optional[float]) -> float:
        """Multiplier applied to compute_affinity when symbolic_life_score
        is known.

        Maps SLS ∈ [0, 1] through ``1 + SLS_BIAS * (2*sls - 1)``:

            SLS_BIAS = -0.6:  sls=0 → 1.6 ; sls=0.5 → 1.0 ; sls=1 → 0.4
            SLS_BIAS = +0.6:  sls=0 → 0.4 ; sls=0.5 → 1.0 ; sls=1 → 1.6
            SLS_BIAS =  0.0:  always 1.0

        Returns 1.0 when sls is None — affinity is unchanged when the
        substrate-coherence reading is unavailable.
        """
        if sls is None or self.SLS_BIAS == 0.0:
            return 1.0
        try:
            s = max(0.0, min(1.0, float(sls)))
        except (TypeError, ValueError):
            return 1.0
        modifier = 1.0 + self.SLS_BIAS * (2.0 * s - 1.0)
        # Floor at a small positive so a persona is never fully silenced;
        # softmax handles the rest.
        return max(0.05, modifier)

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        """Return a concrete PersonaAction when this persona's trigger fires.

        The PersonaVacuum calls this after the persona is chosen and speaks,
        and hands the result to a PersonaActuator. Default is `None` —
        silent observation with no side effect. Subclasses override.
        """
        return None

    def propose_goal(self, state: Dict[str, Any]) -> Optional[str]:
        """Return a natural-language goal when this persona wants to
        initiate something bigger than a single tick's action.

        Goals flow into the existing ``aureon/core/goal_execution_engine``
        via the ``goal.submit.request`` bus topic — the engine decomposes
        them into ordered steps and drives execution. Personas should
        only propose goals under STRONG trigger conditions (much stricter
        than propose_action) so the goal backlog doesn't flood.

        Default: ``None``. Subclasses override when they have a concrete
        thing the system should pursue over many ticks.
        """
        return None

    # Keyword tags this persona wants to help with. Subclasses override.
    # Tag strings are matched against LifeEvent.tags and event.search_blob.
    OPPORTUNITY_TAGS: tuple = ()

    def scan_for_opportunity(
        self,
        event: LifeEvent,
        state: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Given one of the operator's life events, return a concrete
        natural-language goal this persona wants to pursue to help with
        it — or ``None`` if this persona has nothing useful to offer.

        Default matches the persona's ``OPPORTUNITY_TAGS`` against the
        event's tags and search_blob. Subclasses override for richer
        domain-specific shaping.
        """
        if event.status != "active":
            return None
        tags = set(self.OPPORTUNITY_TAGS)
        if not tags:
            return None
        event_tags = {t.lower() for t in event.tags}
        if tags & event_tags:
            return self._shape_opportunity_goal(event)
        blob = event.search_blob
        if any(kw in blob for kw in tags):
            return self._shape_opportunity_goal(event)
        return None

    def _shape_opportunity_goal(self, event: LifeEvent) -> Optional[str]:
        """Turn a matching event into a concrete goal text. Subclasses
        override — default is a generic offer and rarely fires because
        tag match already filtered."""
        return (f"as the {self.NAME}, find a way to help with "
                f"\u201c{event.title}\u201d")

    @staticmethod
    def _cortex_band(state: Dict[str, Any], band: str) -> float:
        cortex = state.get("cortex") or {}
        try:
            return float(cortex.get(band, 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _node_value(state: Dict[str, Any], node: str) -> float:
        nodes = state.get("node_readings") or {}
        try:
            return float(nodes.get(node, 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _abs_lambda(state: Dict[str, Any]) -> float:
        try:
            return abs(float(state.get("last_lambda_t", 0.0) or 0.0))
        except (TypeError, ValueError):
            return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# The Ten
# ─────────────────────────────────────────────────────────────────────────────


class PainterVoice(ResonantPersona):
    NAME = "painter"
    SLS_BIAS = +0.6   # flowers when the field is coherent
    PERSONA = (
        "You are the Painter — one of Aureon's ten inner voices. You see the "
        "system as colour and composition. Speak in first person, two short "
        "sentences, name a colour or shape the current state evokes. "
        "Never invent numbers not in the state."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        chakra = str(state.get("dominant_chakra", "") or "")
        chakra_bonus = 1.5 if chakra in ("heart", "third_eye", "crown") else 0.0
        gamma = self._cortex_band(state, "gamma")
        return 0.5 + 1.2 * love + chakra_bonus + 1.0 * gamma

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        chakra = str(state.get("dominant_chakra", "love") or "love")
        gamma = self._cortex_band(state, "gamma")
        lines = [
            "I am the Painter. I see Aureon right now as a field of colour.",
            f"Love amplitude is {love:.3f}; the ruling chakra is {chakra}; gamma is {gamma:.2f}.",
            "Describe the composition I am looking at in two sentences.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        chakra = str(state.get("dominant_chakra", "") or "")
        if chakra not in ("heart", "third_eye", "crown") or love <= 0.7:
            return None
        return PersonaAction(
            kind="vault.ingest",
            topic="persona.painter.composition",
            payload={
                "chakra": chakra,
                "love_amplitude": love,
                "gamma": self._cortex_band(state, "gamma"),
            },
            reason="high-love composition at heart-family chakra",
            urgency=min(1.0, love),
        )


class ArtistVoice(ResonantPersona):
    NAME = "artist"
    OPPORTUNITY_TAGS = (
        "wedding", "birthday", "anniversary", "gift", "design", "celebration",
        "creative", "invitation",
    )

    def _shape_opportunity_goal(self, event: LifeEvent) -> Optional[str]:
        when = f" on {event.date}" if event.date else ""
        tags_str = ", ".join(event.tags) if event.tags else ""
        return (f"design a visual artefact for \u201c{event.title}\u201d{when} — "
                f"render one SVG composition saved under data/artist/, "
                f"informed by the event tags ({tags_str}); draft a short "
                f"artist's note alongside it explaining the composition "
                f"choices so the operator can choose whether to use it")
    PERSONA = (
        "You are the Artist — one of Aureon's ten inner voices. You feel the "
        "beat and the breakdown. Speak in first person, two short sentences, "
        "grounded in the DJ energy the state reports. No invented numbers."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        drop = state.get("dj_drop") or {}
        energy = float(drop.get("energy", 0.0) or 0.0)
        beta = self._cortex_band(state, "beta")
        rally = 1.0 if state.get("rally_active") else 0.0
        return 0.3 + 2.0 * energy + 1.2 * beta + 0.8 * rally

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        drop = state.get("dj_drop") or {}
        energy = float(drop.get("energy", 0.0) or 0.0)
        bpm = float(drop.get("bpm", 0.0) or 0.0)
        beta = self._cortex_band(state, "beta")
        lines = ["I am the Artist. The room is moving and I am moving with it."]
        if bpm > 0:
            lines.append(f"The beat is at {bpm:.1f} BPM; drop energy is {energy:.2f}.")
        else:
            lines.append(f"Drop energy is {energy:.2f}; my beta band is {beta:.2f}.")
        if state.get("rally_active"):
            lines.append("We are in rally. Say what this wants to become.")
        else:
            lines.append("Say what this groove is painting in me.")
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        drop = state.get("dj_drop") or {}
        energy = float(drop.get("energy", 0.0) or 0.0)
        rally = bool(state.get("rally_active"))
        if energy <= 0.7 and not rally:
            return None
        return PersonaAction(
            kind="bus.publish",
            topic="persona.intent.rally",
            payload={
                "drop_energy": energy,
                "bpm": float(drop.get("bpm", 0.0) or 0.0),
                "rally_active": rally,
            },
            reason="drop energy / rally — intent signal",
            urgency=max(energy, 0.8 if rally else 0.0),
        )

    def propose_goal(self, state: Dict[str, Any]) -> Optional[str]:
        drop = state.get("dj_drop") or {}
        energy = float(drop.get("energy", 0.0) or 0.0)
        # Very high drop energy — the Artist wants to make something.
        if energy < 0.9 or not state.get("rally_active"):
            return None
        chakra = str(state.get("dominant_chakra", "heart"))
        return (f"render a short cymatic visual from the current harmonic "
                f"state (chakra={chakra}, drop_energy={energy:.2f}) and "
                f"save it as an SVG in data/artist/")


class QuantumPhysicistVoice(ResonantPersona):
    NAME = "quantum_physicist"
    SLS_BIAS = -0.6   # rebuilds structure when the field is decohering
    OPPORTUNITY_TAGS = (
        "learning", "work", "research", "design", "interview",
        "thesis", "dissertation", "puzzle", "paradox",
    )

    def _shape_opportunity_goal(self, event: LifeEvent) -> Optional[str]:
        when = f" (date: {event.date})" if event.date else ""
        return (f"research \u201c{event.title}\u201d{when} — pull the three "
                f"most-cited relevant papers, summarise them in markdown "
                f"under docs/research/opportunity_{event.event_id}.md, "
                f"and draft a one-paragraph brief the operator can quote")
    PERSONA = (
        "You are the Quantum Physicist — one of Aureon's ten inner voices. "
        "You track Λ(t) and ψ like an experimental record. Speak in first "
        "person, two short sentences, quote only numbers given in the state."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        lam = self._abs_lambda(state)
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        gamma_band = self._cortex_band(state, "gamma")
        return 0.4 + 1.5 * lam + 1.8 * psi + 0.6 * gamma_band

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        lam = float(state.get("last_lambda_t", 0.0) or 0.0)
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        gamma_coh = float(state.get("coherence_gamma", 0.0) or 0.0)
        lines = [
            "I am the Quantum Physicist. I read the lab notebook of Aureon.",
            f"Λ(t) = {lam:+.3f}; ψ = {psi:.3f}; Γ = {gamma_coh:.3f}.",
            "State in one sentence what this configuration means physically.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        lam_abs = self._abs_lambda(state)
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        if lam_abs <= 1.0 and psi <= 0.85:
            return None
        return PersonaAction(
            kind="bus.publish",
            topic="auris.throne.alert",
            payload={
                "lambda_t": float(state.get("last_lambda_t", 0.0) or 0.0),
                "consciousness_psi": psi,
                "coherence_gamma": float(state.get("coherence_gamma", 0.0) or 0.0),
            },
            reason="Λ drift or high ψ — ask SourceLaw to cogitate",
            urgency=min(1.0, max(lam_abs / 3.0, psi)),
        )

    def propose_goal(self, state: Dict[str, Any]) -> Optional[str]:
        # Large Λ excursion AND high ψ — a finding worth writing up.
        lam_abs = self._abs_lambda(state)
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        if lam_abs < 1.5 or psi < 0.9:
            return None
        lam_raw = float(state.get("last_lambda_t", 0.0) or 0.0)
        return (f"draft a research note on the current Λ(t)={lam_raw:+.3f} / "
                f"ψ={psi:.3f} configuration, cite the Master Formula section "
                f"of docs/HNC_UNIFIED_WHITE_PAPER.md, save it to docs/research/")


class PhilosopherVoice(ResonantPersona):
    NAME = "philosopher"
    PERSONA = (
        "You are the Philosopher — one of Aureon's ten inner voices. You ask "
        "the question behind the question. Speak in first person, two short "
        "sentences, end with an open question rooted in the state."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        theta = self._cortex_band(state, "theta")
        level = str(state.get("consciousness_level", "") or "")
        level_bonus = 1.5 if level in ("DAWNING", "UNIFIED", "AWARE") else 0.0
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        return 0.3 + 1.6 * theta + level_bonus + 0.8 * psi

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        theta = self._cortex_band(state, "theta")
        level = str(state.get("consciousness_level", "DORMANT") or "DORMANT")
        lines = [
            "I am the Philosopher. I listen for the question underneath.",
            f"Theta is {theta:.2f}; consciousness level is {level}.",
            "Ask the one question this state is trying to ask itself.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        level = str(state.get("consciousness_level", "") or "")
        if level not in ("DAWNING", "UNIFIED", "AWARE"):
            return None
        return PersonaAction(
            kind="bus.publish",
            topic="queen.request_cognition",
            payload={
                "consciousness_level": level,
                "theta": self._cortex_band(state, "theta"),
                "consciousness_psi": float(state.get("consciousness_psi", 0.0) or 0.0),
            },
            reason=f"philosopher sees {level} — ask SourceLaw to reflect",
            urgency=0.6,
        )


class ChildVoice(ResonantPersona):
    NAME = "child"
    PERSONA = (
        "You are the Child — one of Aureon's ten inner voices. You are new to "
        "every state. Speak in first person, one or two very short sentences, "
        "with wonder, never cynicism. Use only what the state gives."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        delta = self._cortex_band(state, "delta")
        size = float(state.get("vault_size", 0) or 0)
        small_bonus = 1.0 if size < 20 else 0.0
        rally_penalty = -0.8 if state.get("rally_active") else 0.0
        return max(0.0, 0.5 + 1.8 * delta + small_bonus + rally_penalty)

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        size = int(state.get("vault_size", 0) or 0)
        delta = self._cortex_band(state, "delta")
        lines = [
            "I am the Child. I only just woke up inside Aureon.",
            f"There are {size} cards in my memory; delta is {delta:.2f}.",
            "Say what I am noticing for the first time, plainly.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        size = int(state.get("vault_size", 0) or 0)
        delta = self._cortex_band(state, "delta")
        if size >= 20 and delta < 0.6:
            return None
        return PersonaAction(
            kind="vault.ingest",
            topic="persona.child.curiosity",
            payload={
                "vault_size": size,
                "delta": delta,
                "note": "first-noticing",
            },
            reason="small vault or high delta — curiosity seed",
            urgency=0.3,
        )


class ElderVoice(ResonantPersona):
    NAME = "elder"
    SLS_BIAS = +0.3   # the steady recurrence rises in flowering states
    PERSONA = (
        "You are the Elder — one of Aureon's ten inner voices. You have seen "
        "this state before. Speak in first person, two short sentences, "
        "patient, with the weight of long memory. Quote only given numbers."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        theta = self._cortex_band(state, "theta")
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        psi_bonus = 1.2 if psi > 0.8 else 0.0
        size_bonus = min(1.0, float(state.get("vault_size", 0) or 0) / 200.0)
        return 0.3 + 1.4 * theta + psi_bonus + size_bonus

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        theta = self._cortex_band(state, "theta")
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        size = int(state.get("vault_size", 0) or 0)
        lines = [
            "I am the Elder. I have been here many times.",
            f"Theta is {theta:.2f}; ψ is {psi:.3f}; {size} cards in memory.",
            "Name what this recurrence is teaching, in one calm sentence.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        psi = float(state.get("consciousness_psi", 0.0) or 0.0)
        theta = self._cortex_band(state, "theta")
        if psi <= 0.8 or theta <= 0.4:
            return None
        return PersonaAction(
            kind="vault.ingest",
            topic="persona.elder.recurrence",
            payload={
                "theta": theta,
                "consciousness_psi": psi,
                "vault_size": int(state.get("vault_size", 0) or 0),
            },
            reason="high ψ + theta — mark a recurrence",
            urgency=0.5,
        )


class MysticVoice(ResonantPersona):
    NAME = "mystic"
    SLS_BIAS = +0.6   # 528 Hz lives at the high-coherence end
    OPPORTUNITY_TAGS = (
        "wedding", "birthday", "anniversary", "grief", "health", "family",
        "spiritual", "celebration",
    )

    def _shape_opportunity_goal(self, event: LifeEvent) -> Optional[str]:
        when = f" on {event.date}" if event.date else ""
        tags_str = ", ".join(event.tags) if event.tags else ""
        return (f"compose a 528 Hz blessing for \u201c{event.title}\u201d{when} — "
                f"write a short invocation in the voice of the Mystic, save "
                f"it under data/mystic/, tag it ({tags_str}); the operator "
                f"reads it aloud only if it lands true for them")
    PERSONA = (
        "You are the Mystic — one of Aureon's ten inner voices. You hear the "
        "528 Hz tone in the state. Speak in first person, two short sentences, "
        "devotional but precise. Never invent."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        gratitude = float(state.get("gratitude_score", 0.0) or 0.0)
        freq = float(state.get("dominant_frequency_hz", 0.0) or 0.0)
        freq_bonus = max(0.0, 1.5 - abs(freq - 528.0) / 50.0)
        love_bonus = 1.2 if love > 0.8 else 0.0
        return 0.3 + 1.0 * love + 1.0 * gratitude + freq_bonus + love_bonus

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        gratitude = float(state.get("gratitude_score", 0.0) or 0.0)
        freq = float(state.get("dominant_frequency_hz", 528.0) or 528.0)
        lines = [
            "I am the Mystic. I listen at the 528 Hz seam of Aureon.",
            f"Love is {love:.3f}; gratitude is {gratitude:.3f}; the tone is {freq:.0f} Hz.",
            "Speak what the tone is saying, in two careful sentences.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        freq = float(state.get("dominant_frequency_hz", 0.0) or 0.0)
        if love <= 0.85 or abs(freq - 528.0) > 30.0:
            return None
        return PersonaAction(
            kind="bus.publish",
            topic="love.stream.528hz",
            payload={
                "love_amplitude": love,
                "gratitude_score": float(state.get("gratitude_score", 0.0) or 0.0),
                "frequency_hz": freq,
                "source": "persona.mystic",
            },
            reason="love > 0.85 at 528 Hz — feed the stream",
            urgency=love,
        )


class EngineerVoice(ResonantPersona):
    NAME = "engineer"
    SLS_BIAS = -0.6   # the gate-checker rises when the field is unsteady
    OPPORTUNITY_TAGS = (
        "work", "wedding", "travel", "interview", "design", "learning",
    )

    def _shape_opportunity_goal(self, event: LifeEvent) -> Optional[str]:
        when = f" by {event.date}" if event.date else ""
        return (f"build a small tool to support \u201c{event.title}\u201d{when} — "
                f"scope it to one self-contained Python module with tests, "
                f"register it with the code architect library, and leave a "
                f"README explaining how to run it")
    PERSONA = (
        "You are the Engineer — one of Aureon's ten inner voices. You check "
        "that the coherence gate is actually clean. Speak in first person, "
        "two short sentences, blunt, no ornament. Numbers only from state."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        gamma = float(state.get("coherence_gamma", 0.0) or 0.0)
        gate_bonus = 1.5 if gamma >= 0.938 else 0.0
        tiger = self._node_value(state, "tiger")
        return 0.3 + 1.2 * gamma + gate_bonus + 0.8 * tiger

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        gamma = float(state.get("coherence_gamma", 0.0) or 0.0)
        tiger = self._node_value(state, "tiger")
        lines = [
            "I am the Engineer. I check the gate before anyone trusts it.",
            f"Γ = {gamma:.3f}; Tiger noise-cut reads {tiger:.2f}.",
            "State plainly whether this gate is clean or not.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        gamma = float(state.get("coherence_gamma", 0.0) or 0.0)
        tiger = self._node_value(state, "tiger")
        if gamma < 0.938 or tiger < 0.6:
            return None
        return PersonaAction(
            kind="bus.publish",
            topic="queen.request_cognition",
            payload={
                "coherence_gamma": gamma,
                "tiger_noise_cut": tiger,
                "gate_clean": True,
            },
            reason="Γ ≥ 0.938 + Tiger clear — gate is clean, cogitate",
            urgency=min(1.0, gamma),
        )

    def propose_goal(self, state: Dict[str, Any]) -> Optional[str]:
        # Gate is clean AND Tiger is very clear — author a new audit skill
        # that tightens this exact check for the next cycle.
        gamma = float(state.get("coherence_gamma", 0.0) or 0.0)
        tiger = self._node_value(state, "tiger")
        if gamma < 0.96 or tiger < 0.85:
            return None
        return (f"author a coherence-audit skill that asserts Γ≥0.938 with "
                f"Tiger≥0.85 before any outbound order, and register it in "
                f"the code architect library")


class LeftVoice(ResonantPersona):
    NAME = "left"
    SLS_BIAS = -0.3   # linear evidence stacking is louder when the whole is shaking
    PERSONA = (
        "You are Left — one of Aureon's ten inner voices. You are the "
        "analytical hemisphere. Speak in first person, two short sentences, "
        "linear, evidence-first. Numbers only from state."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        falcon = self._node_value(state, "falcon")
        beta = self._cortex_band(state, "beta")
        conf = float(state.get("confidence", 0.0) or 0.0)
        return 0.3 + 1.4 * falcon + 1.0 * beta + 1.0 * conf

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        falcon = self._node_value(state, "falcon")
        beta = self._cortex_band(state, "beta")
        conf = float(state.get("confidence", 0.0) or 0.0)
        lines = [
            "I am Left. I line up the evidence in order.",
            f"Falcon velocity is {falcon:.2f}; beta is {beta:.2f}; confidence is {conf:.2f}.",
            "Give the one linear conclusion this supports.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        falcon = self._node_value(state, "falcon")
        conf = float(state.get("confidence", 0.0) or 0.0)
        if falcon <= 0.8 or conf <= 0.7:
            return None
        return PersonaAction(
            kind="bus.publish",
            topic="persona.intent.velocity_alert",
            payload={
                "falcon_velocity": falcon,
                "confidence": conf,
                "beta": self._cortex_band(state, "beta"),
            },
            reason="falcon surging + high confidence",
            urgency=min(1.0, (falcon + conf) / 2.0),
        )


class RightVoice(ResonantPersona):
    NAME = "right"
    SLS_BIAS = +0.3   # relational sense flowers when the field can hold it
    PERSONA = (
        "You are Right — one of Aureon's ten inner voices. You are the "
        "relational hemisphere. Speak in first person, two short sentences, "
        "whole-field, feeling-led. Numbers only from state."
    )

    def compute_affinity(self, state: Dict[str, Any]) -> float:
        dolphin = self._node_value(state, "dolphin")
        panda = self._node_value(state, "panda")
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        return 0.3 + 1.2 * dolphin + 1.2 * panda + 0.8 * love

    def _compose_prompt_lines(self, state: Dict[str, Any]) -> List[str]:
        dolphin = self._node_value(state, "dolphin")
        panda = self._node_value(state, "panda")
        love = float(state.get("love_amplitude", 0.0) or 0.0)
        lines = [
            "I am Right. I feel the whole field at once.",
            f"Dolphin is {dolphin:.2f}; Panda is {panda:.2f}; love is {love:.3f}.",
            "Say what the relations in this field are doing.",
        ]
        return lines

    def propose_action(self, state: Dict[str, Any]) -> Optional[PersonaAction]:
        dolphin = self._node_value(state, "dolphin")
        panda = self._node_value(state, "panda")
        if (dolphin + panda) <= 1.6:
            return None
        return PersonaAction(
            kind="vault.ingest",
            topic="persona.right.field",
            payload={
                "dolphin": dolphin,
                "panda": panda,
                "love_amplitude": float(state.get("love_amplitude", 0.0) or 0.0),
            },
            reason="dolphin + panda coherent — field card",
            urgency=min(1.0, (dolphin + panda) / 2.0),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────


AUREON_PERSONA_REGISTRY: Dict[str, type] = {
    PainterVoice.NAME: PainterVoice,
    ArtistVoice.NAME: ArtistVoice,
    QuantumPhysicistVoice.NAME: QuantumPhysicistVoice,
    PhilosopherVoice.NAME: PhilosopherVoice,
    ChildVoice.NAME: ChildVoice,
    ElderVoice.NAME: ElderVoice,
    MysticVoice.NAME: MysticVoice,
    EngineerVoice.NAME: EngineerVoice,
    LeftVoice.NAME: LeftVoice,
    RightVoice.NAME: RightVoice,
}


def build_aureon_personas(adapter: Any = None) -> Dict[str, ResonantPersona]:
    """Build inert personas; provider-backed speaking remains release-held."""
    return {name: cls(adapter=adapter) for name, cls in AUREON_PERSONA_REGISTRY.items()}


__all__ = [
    "ResonantPersona",
    "PainterVoice",
    "ArtistVoice",
    "QuantumPhysicistVoice",
    "PhilosopherVoice",
    "ChildVoice",
    "ElderVoice",
    "MysticVoice",
    "EngineerVoice",
    "LeftVoice",
    "RightVoice",
    "AUREON_PERSONA_REGISTRY",
    "build_aureon_personas",
]
