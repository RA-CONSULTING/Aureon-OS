#!/usr/bin/env python3
"""
ask_aureon.py — talk to the Aureon persona vacuum.

Two modes. ONE-SHOT (pass a question as an argument):

    python scripts/ask_aureon.py "are we in a coherent state?"
    python scripts/ask_aureon.py "what should I pay attention to?" --mood mystic_love

REPL (no question argument — drops you into a conversational loop):

    python scripts/ask_aureon.py
    python scripts/ask_aureon.py --mood recurrence            # start in a mood
    echo -e "what is this?\\n/stats\\n/bye" | python scripts/ask_aureon.py

In REPL mode every turn grows the vault: the exchange is ingested as a
`conversation.turn` card, so later collapses see an ever-larger memory
and the personas can quote what was said earlier. Meta-commands:

    /help            list commands
    /stats           vault + winner histogram + action counters
    /history [n]     show the last n exchanges (default 10)
    /mood <name>     switch mood presets (ten available, 'none' to clear)
    /forget          wipe the conversation transcript (vault cards stay)
    /bye  or  /quit  exit with a summary

No API keys. A lightweight, deterministic PersonaResponseAdapter generates
persona-voiced text from (a) the persona identity embedded in the system
prompt, (b) the state cues the persona composed into its user-prompt,
and (c) if the conversation has run more than one turn, a tail of the
transcript so the answer stays continuous.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
import threading
import time
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.core.aureon_thought_bus import Thought, ThoughtBus
from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse
from aureon.obsidian_paths import resolve_obsidian_vault_path
from aureon.vault.aureon_vault import AureonVault
from aureon.vault.obsidian_adapter import ObsidianVaultAdapter
from aureon.vault.voice.aureon_personas import (
    AUREON_PERSONA_REGISTRY,
    ResonantPersona,
)
from aureon.vault.voice.persona_vacuum import PersonaVacuum


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic persona-voiced response adapter
# ─────────────────────────────────────────────────────────────────────────────


# Opening line per persona — matches the voice declared in PERSONA system
# prompts. Kept short so the state cues the persona itself composed (the
# user-prompt lines) dominate the reply.
_PERSONA_OPENERS: Dict[str, str] = {
    "painter":          "I see it as colour and form.",
    "artist":           "I feel the beat moving.",
    "quantum_physicist":"I read the lab notebook.",
    "philosopher":      "The question beneath your question is this:",
    "child":            "I am noticing something for the first time.",
    "elder":            "I have been here before.",
    "mystic":           "The 528 Hz seam is open in me.",
    "engineer":         "I checked the gate.",
    "left":             "Taking the evidence in order:",
    "right":            "Feeling the whole field at once:",
}

# Closing cadence that gives each persona a signature without repeating.
_PERSONA_CLOSERS: Dict[str, str] = {
    "painter":          "— the composition is alive.",
    "artist":           "— it wants to become something.",
    "quantum_physicist":"— that is the physical reading.",
    "philosopher":      "— sit with that.",
    "child":            "— is that true for you too?",
    "elder":            "— this will pass as it always does.",
    "mystic":           "— love holds.",
    "engineer":         "— that is what the numbers show.",
    "left":             "— that is the linear conclusion.",
    "right":            "— the relations are doing that work.",
}


_NAME_PAT = re.compile(r"^You are (?:the\s+)?([A-Za-z][\w\s]*?)\s*[—\-]")


def _detect_persona_name(system_prompt: str) -> str:
    """Pull the persona name out of the VaultVoice-style system prompt."""
    m = _NAME_PAT.match(system_prompt or "")
    if not m:
        return "voice"
    raw = m.group(1).strip().lower()
    # Map common surface forms back to our registry keys
    if raw.startswith("queen"):
        return "queen"
    if raw == "quantum physicist":
        return "quantum_physicist"
    if raw in _PERSONA_OPENERS:
        return raw
    return raw.replace(" ", "_")


class PersonaResponseAdapter(LLMAdapter):
    """Builds a reply from the state cues already present in the prompt +
    the operator's question, in the voice declared by the system prompt.
    No network, no LLM. Deterministic under a fixed RNG seed.

    The `session` reference (set by ConversationSession.attach) lets the
    adapter look at previous turns so the reply can echo continuity —
    e.g. "earlier Mystic answered you this: ..." — when we're past
    turn 1.
    """

    def __init__(self, question: str, seed: int = 0):
        self.question = str(question or "").strip()
        self._rng = random.Random(seed)
        self.session: Optional["ConversationSession"] = None

    def prompt(
        self,
        messages: List[Dict[str, Any]],
        system: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        name = _detect_persona_name(system)
        user_text = ""
        for m in messages or []:
            if m.get("role") == "user":
                user_text = str(m.get("content") or "")
                break

        state_lines = self._extract_state_cues(user_text)
        opener = _PERSONA_OPENERS.get(name, "I am the voice of the vault.")
        closer = _PERSONA_CLOSERS.get(name, "")
        cue = self._summarise_cues(state_lines)
        answer = self._answer_from_cues(name, cue)

        reply_bits: List[str] = [opener]
        if cue:
            reply_bits.append(cue)
        continuity = self._continuity_bit(current_persona=name)
        if continuity:
            reply_bits.append(continuity)
        if self.question:
            reply_bits.append(f"You asked: \u201c{self.question}\u201d")
            reply_bits.append(answer)
        else:
            reply_bits.append(answer)
        if closer:
            reply_bits.append(closer)

        text = " ".join(bit.rstrip() for bit in reply_bits if bit).strip()
        return LLMResponse(text=text, stop_reason="end_turn", model="persona-voice-local")

    def _continuity_bit(self, current_persona: str = "") -> str:
        """Remind the operator of context from earlier turns.

        Three layers (kept to one short sentence so answers aren't buried):
          1. Self-memory — if THIS persona has spoken before, they
             acknowledge their own prior turn.
          2. Cross-memory — reference the previous user turn's speaker
             and question so the conversation feels continuous.
          3. Ambient memory — if the ambient engine has run and produced
             idle collapses, surface the most recent one.
        """
        if self.session is None:
            return ""

        # Layer 1: this persona's own prior turn, if any.
        if current_persona and self.session.transcript:
            mine = self.session.recent_for_persona(current_persona, n=1)
            if mine:
                prev = mine[-1]
                prev_q = (prev.get("question") or "").strip()
                prev_turn = prev.get("turn", 0)
                if prev_q and prev_turn and prev_turn != len(self.session.transcript) + 1:
                    return (f"I return — on turn {prev_turn} you asked me "
                            f"\u201c{prev_q}\u201d and I answered then.")

        # Layer 2: previous user turn overall.
        bit = ""
        if self.session.transcript:
            last = self.session.transcript[-1]
            last_q = (last.get("question") or "").strip()
            last_persona = last.get("persona", "")
            if last_q and last_persona:
                bit = (f"Just before me, you asked \u201c{last_q}\u201d and "
                       f"{last_persona} answered.")

        # Layer 3: latest ambient (idle) collapse, if any.
        if (self.session.ambient is not None
                and self.session.ambient.ambient_transcript):
            idle = self.session.ambient.ambient_transcript[-1]
            idle_voice = idle.get("persona", "")
            idle_mood = idle.get("mood", "")
            if idle_voice:
                amb = (f"While you were quiet, {idle_voice} drifted "
                       f"through (mood={idle_mood}).")
                return (bit + " " + amb).strip() if bit else amb

        return bit

    def stream(self, *a, **kw):
        r = self.prompt(*a, **kw)
        from aureon.inhouse_ai.llm_adapter import StreamChunk  # type: ignore
        words = r.text.split(" ")
        for i, w in enumerate(words):
            yield StreamChunk(text=w + (" " if i < len(words) - 1 else ""))
        yield StreamChunk(done=True, stop_reason=r.stop_reason)

    def health_check(self) -> bool:
        return True

    # ─── helpers ─────────────────────────────────────────────────────────

    def _extract_state_cues(self, prompt: str) -> List[str]:
        """Keep only lines that mention numbers — those carry the state."""
        cues: List[str] = []
        for raw in (prompt or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            if re.search(r"[-+]?\d", line):
                cues.append(line)
        return cues

    def _summarise_cues(self, cues: List[str]) -> str:
        if not cues:
            return ""
        # Pick at most 2 cue lines (the numerically-densest ones) and join.
        scored = sorted(cues, key=lambda s: -len(re.findall(r"\d", s)))
        chosen = scored[:2]
        joined = "; ".join(c.rstrip(".") for c in chosen)
        return f"Right now: {joined}."

    def _answer_from_cues(self, persona: str, cue: str) -> str:
        """Shape a short answer that ties the question back to the state."""
        if persona == "engineer":
            return "The coherence reading and the noise-cut say what they say; do not override them with wish."
        if persona == "quantum_physicist":
            return "The Λ(t) magnitude and ψ tell you the configuration; read them straight."
        if persona == "philosopher":
            return "The question is whether you are seeing what is, or what you need to be true."
        if persona == "mystic":
            return "Stand in the 528 Hz, keep gratitude near, and let the answer meet you."
        if persona == "painter":
            return "Trust the composition in front of you; add one more stroke where it is quiet."
        if persona == "child":
            return "I would ask the simplest piece first and listen for a long time."
        if persona == "elder":
            return "This pattern returns; do the steady thing you already know works."
        if persona == "artist":
            return "Move with the drop; the next phrase names itself."
        if persona == "left":
            return "Line up the measurable pieces; the action follows from them in order."
        if persona == "right":
            return "Feel the relations — Dolphin and Panda tell you which bond is carrying weight."
        return "Stay with the state as it is; answer from there."


# ─────────────────────────────────────────────────────────────────────────────
# Mood presets — same ten as the live runner, so the tester can steer
# which persona is likely to win.
# ─────────────────────────────────────────────────────────────────────────────


def apply_mood(vault: AureonVault, mood: str, bus: ThoughtBus) -> str:
    # Neutral baseline — chakra=solar so Painter is NOT boosted unless the
    # mood explicitly asks for it.
    cortex = {"delta": 0.1, "theta": 0.1, "alpha": 0.1, "beta": 0.1, "gamma": 0.1}
    love = 0.4
    freq = 432.0
    chakra = "solar"
    rally = False
    cognition = {
        "coherence_gamma": 0.4, "consciousness_psi": 0.4,
        "consciousness_level": "DORMANT", "confidence": 0.4,
        "node_readings": {"tiger": 0.3, "falcon": 0.3, "dolphin": 0.3, "panda": 0.3, "clownfish": 0.3},
    }
    dj: Dict[str, Any] = {}

    if mood == "gate_clean":
        cognition.update({"coherence_gamma": 0.96, "node_readings": {"tiger": 0.92}})
        cortex["beta"] = 0.6
    elif mood == "lambda_drift":
        vault.last_lambda_t = 1.6
        cognition.update({"consciousness_psi": 0.92, "consciousness_level": "UNIFIED"})
    elif mood == "dawning":
        cognition.update({"consciousness_psi": 0.78, "consciousness_level": "DAWNING"})
        cortex["theta"] = 0.75
    elif mood == "rally_drop":
        rally = True
        dj = {"energy": 0.9, "bpm": 128.0}
        cortex["beta"] = 0.75
    elif mood == "mystic_love":
        love = 0.94
        freq = 528.0
        chakra = "heart"
    elif mood == "heart_paint":
        love = 0.85
        chakra = "third_eye"
        cortex["gamma"] = 0.85
    elif mood == "velocity":
        cognition.update({"node_readings": {"falcon": 0.92}, "confidence": 0.88})
        cortex["beta"] = 0.7
    elif mood == "heart_field":
        cognition.update({"node_readings": {"dolphin": 0.9, "panda": 0.9}})
        love = 0.75
    elif mood == "curiosity":
        cortex["delta"] = 0.9
    elif mood == "recurrence":
        cognition.update({"consciousness_psi": 0.9})
        cortex["theta"] = 0.8
    else:
        return "neutral"

    vault.love_amplitude = love
    vault.dominant_frequency_hz = freq
    vault.dominant_chakra = chakra
    vault.rally_active = rally
    vault.cortex_snapshot = cortex

    bus.publish(Thought(source="ask", topic="queen.source_law.cognition", payload=cognition))
    if dj:
        bus.publish(Thought(source="ask", topic="dj.track.drop", payload=dj))
    return mood


# ─────────────────────────────────────────────────────────────────────────────
# Question injection — extend each persona's composed prompt with the Q
# ─────────────────────────────────────────────────────────────────────────────


_INJECTED_FLAG = "_ask_aureon_injected"


def _install_question_reader(persona: ResonantPersona) -> None:
    """Install a stable wrapper on `_compose_prompt_lines` that reads the
    persona's current `_ask_question` attribute. Installed once per persona
    — subsequent calls via `inject_question_into_prompts` only update the
    attribute, so the wrapper never stacks."""
    if getattr(persona, _INJECTED_FLAG, False):
        return
    original = persona._compose_prompt_lines

    def wrapped(state, _orig=original, _persona=persona):
        lines = list(_orig(state))
        q = getattr(_persona, "_ask_question", "") or ""
        if q:
            lines.append(f"An operator asks: \u201c{q}\u201d — answer in your voice.")
        return lines

    persona._compose_prompt_lines = wrapped  # type: ignore[attr-defined]
    setattr(persona, _INJECTED_FLAG, True)


def inject_question_into_prompts(personas: Dict[str, ResonantPersona], question: str) -> None:
    """Set the current question on every persona. The stable wrapper picks
    it up at compose time."""
    for persona in personas.values():
        _install_question_reader(persona)
        persona._ask_question = str(question or "")  # type: ignore[attr-defined]


def _clear_question_injection(personas: Dict[str, ResonantPersona]) -> None:
    """Clear the pending question on every persona so the next prompt
    composition uses only state cues."""
    for persona in personas.values():
        persona._ask_question = ""  # type: ignore[attr-defined]


# ─────────────────────────────────────────────────────────────────────────────
# ConversationSession — carries memory across turns
# ─────────────────────────────────────────────────────────────────────────────


class ConversationSession:
    """Ties together the bus, vault, vacuum, and adapter across turns."""

    MOODS = (
        "gate_clean", "lambda_drift", "dawning", "rally_drop", "mystic_love",
        "heart_paint", "velocity", "heart_field", "curiosity", "recurrence",
    )

    def __init__(self, bus: ThoughtBus, vault: AureonVault,
                 vacuum: PersonaVacuum, adapter: "PersonaResponseAdapter",
                 current_mood: Optional[str] = None):
        self.bus = bus
        self.vault = vault
        self.vacuum = vacuum
        self.adapter = adapter
        self.adapter.session = self
        self.transcript: List[Dict[str, Any]] = []
        self.current_mood = current_mood or ""
        # Serialise foreground (ask) and background (ambient) observes so
        # they don't collide on the adapter's question field.
        self.lock = threading.RLock()
        self.ambient: Optional["AmbientEngine"] = None
        self.obsidian: Optional[ObsidianVaultAdapter] = None
        # Track files we've written so /stats can report them.
        self._obsidian_written: int = 0

    def attach_obsidian(self, root: str = "") -> str:
        """Enable Obsidian mirroring against the folder at `root`.

        Creates the folder if it doesn't exist. Returns the absolute path
        it's writing into.
        """
        p = resolve_obsidian_vault_path(root)
        p.mkdir(parents=True, exist_ok=True)
        self.obsidian = ObsidianVaultAdapter(vault=self.vault, obsidian_root=p)
        return str(p)

    def detach_obsidian(self) -> None:
        self.obsidian = None

    def mirror_to_obsidian(self, card: Any) -> None:
        """Write a VaultContent to the Obsidian folder, if one is attached.

        Augments the card's payload with a `title` and a formatted `body`
        so the exported markdown note is human-readable rather than a
        JSON dump.
        """
        if self.obsidian is None or card is None:
            return
        try:
            topic = getattr(card, "source_topic", "") or ""
            payload = dict(getattr(card, "payload", {}) or {})
            if topic in ("conversation.turn", "conversation.ambient"):
                payload.setdefault("title", _format_turn_title(payload))
                payload.setdefault("body", _format_turn_body(payload))
                card.payload = payload
            out_path = self.obsidian.sync_out(card)
            if out_path is not None:
                self._obsidian_written += 1
        except Exception:
            pass

    # ─── turn mechanics ──────────────────────────────────────────────────

    def ask(self, question: str) -> Dict[str, Any]:
        question = (question or "").strip()
        if not question:
            return {}
        with self.lock:
            # Re-apply the mood at each turn so the vault state reflects
            # the intended regime; otherwise ride whatever ambient state
            # has drifted to since the last turn.
            if self.current_mood:
                apply_mood(self.vault, self.current_mood, self.bus)

            # Update the adapter's question and re-inject the question
            # line into every persona's composed prompt.
            self.adapter.question = question
            inject_question_into_prompts(self.vacuum._personas, question)

            # Tighten softmax when a mood is set so the intended persona
            # wins reliably; otherwise let the state decide.
            self.vacuum._temperature = 0.25 if self.current_mood else 1.0

            statement = self.vacuum.observe(self.vault)
            winner = self.vacuum.last_winner or "?"
            prob = self.vacuum.last_probabilities.get(winner, 0.0)
            action_rec = self.vacuum.last_action_execution
            text = statement.text if statement is not None else "(silence)"

            turn_rec: Dict[str, Any] = {
                "turn": len(self.transcript) + 1,
                "ts": time.time(),
                "mood": self.current_mood or "neutral",
                "question": question,
                "persona": winner,
                "probability": prob,
                "response": text,
                "action_kind": action_rec.action.kind if action_rec else "",
                "action_topic": action_rec.action.topic if action_rec else "",
            }
            self.transcript.append(turn_rec)
            # Clear the injected question so an ambient observe doesn't
            # accidentally re-ask it.
            self.adapter.question = ""
            _clear_question_injection(self.vacuum._personas)

        # Persist the exchange as a vault card so memory accumulates.
        card = None
        try:
            card = self.vault.ingest(topic="conversation.turn", payload=dict(turn_rec))
        except Exception:
            pass
        self.mirror_to_obsidian(card)
        return turn_rec

    # ─── introspection ───────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        winners: Dict[str, int] = {}
        kinds: Dict[str, int] = {}
        topics: Dict[str, int] = {}
        for t in self.transcript:
            winners[t["persona"]] = winners.get(t["persona"], 0) + 1
            if t["action_kind"]:
                kinds[t["action_kind"]] = kinds.get(t["action_kind"], 0) + 1
            if t["action_topic"]:
                topics[t["action_topic"]] = topics.get(t["action_topic"], 0) + 1
        return {
            "turns": len(self.transcript),
            "vault_cards": len(self.vault),
            "current_mood": self.current_mood or "neutral",
            "winner_histogram": dict(sorted(winners.items(), key=lambda kv: -kv[1])),
            "action_kinds": kinds,
            "action_topics": topics,
            "obsidian_path": str(self.obsidian.obsidian_root) if self.obsidian else "",
            "obsidian_written": self._obsidian_written,
        }

    def recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return list(self.transcript[-int(max(1, n)):])

    def recent_for_persona(self, name: str, n: int = 1) -> List[Dict[str, Any]]:
        """Turns in which the given persona was the winner, oldest → newest."""
        if not name:
            return []
        hits = [t for t in self.transcript if t.get("persona") == name]
        return hits[-int(max(1, n)):]


# ─────────────────────────────────────────────────────────────────────────────
# Obsidian mirror formatting
# ─────────────────────────────────────────────────────────────────────────────


def _format_turn_title(turn: Dict[str, Any]) -> str:
    persona = str(turn.get("persona") or "voice")
    n = turn.get("turn")
    if turn.get("ambient"):
        return f"ambient {n} · {persona}"
    q = (turn.get("question") or "").strip()
    q_short = (q[:48] + "…") if len(q) > 48 else q
    return f"turn {n} · {persona} · {q_short}" if q_short else f"turn {n} · {persona}"


def _format_turn_body(turn: Dict[str, Any]) -> str:
    persona = str(turn.get("persona") or "voice")
    mood = str(turn.get("mood") or "neutral")
    prob = float(turn.get("probability") or 0.0)
    response = str(turn.get("response") or "").strip()
    action_kind = str(turn.get("action_kind") or "")
    action_topic = str(turn.get("action_topic") or "")
    is_ambient = bool(turn.get("ambient"))
    lines: List[str] = []
    header = f"### {'Ambient' if is_ambient else 'Turn'} {turn.get('turn','?')} — {persona}"
    if mood and mood != "neutral":
        header += f"  *(mood: {mood})*"
    lines.append(header)
    lines.append("")
    if not is_ambient:
        q = (turn.get("question") or "").strip()
        if q:
            lines.append(f"**You:** {q}")
            lines.append("")
    lines.append(f"**{persona} answered** *(p={prob:.3f})*:")
    lines.append("")
    lines.append("> " + response.replace("\n", "\n> "))
    lines.append("")
    if action_kind:
        lines.append(f"*action:* `{action_kind}` → `{action_topic}`")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# AmbientEngine — keeps the system moving between user turns
# ─────────────────────────────────────────────────────────────────────────────


PHI = (1 + 5 ** 0.5) / 2
PHI_SQUARED = PHI * PHI


class AmbientEngine:
    """Drives mood cycles + optional idle observes on a background thread.

    The engine:
      1. Picks a random mood every `mood_interval_s`.
      2. Applies it to the vault (which publishes cognition / drops).
      3. Every Nth beat, performs an "idle observe" on the vacuum — a
         persona collapses, speaks from pure state (no user question),
         and the turn is stored as an ambient turn so later user turns
         can reference it.
    Serialises with the session lock so user turns never collide with
    background work.
    """

    def __init__(
        self,
        session: "ConversationSession",
        *,
        mood_interval_s: float = PHI_SQUARED,
        observe_every: int = 3,
        seed: Optional[int] = None,
    ):
        self.session = session
        self.mood_interval_s = float(mood_interval_s)
        self.observe_every = max(1, int(observe_every))
        self._rng = random.Random(seed)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick = 0
        self.ambient_transcript: List[Dict[str, Any]] = []

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="AmbientEngine", daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    @property
    def running(self) -> bool:
        return self._running

    def _loop(self) -> None:
        while self._running:
            time.sleep(self.mood_interval_s)
            if not self._running:
                break
            try:
                self._beat()
            except Exception:
                # Never crash the background thread.
                pass

    def _beat(self) -> None:
        mood = self._rng.choice(ConversationSession.MOODS)
        with self.session.lock:
            # Apply a random mood so cognition / drop state evolves.
            apply_mood(self.session.vault, mood, self.session.bus)
            self._tick += 1

            # Idle observe every Nth beat — no question, pure-state voice.
            if self._tick % self.observe_every != 0:
                return
            self.session.adapter.question = ""
            _clear_question_injection(self.session.vacuum._personas)
            self.session.vacuum._temperature = 0.25

            statement = self.session.vacuum.observe(self.session.vault)
            winner = self.session.vacuum.last_winner or "?"
            prob = self.session.vacuum.last_probabilities.get(winner, 0.0)
            action_rec = self.session.vacuum.last_action_execution
            text = statement.text if statement is not None else "(silence)"
            rec = {
                "turn": self._tick,
                "ts": time.time(),
                "mood": mood,
                "persona": winner,
                "probability": prob,
                "response": text,
                "action_kind": action_rec.action.kind if action_rec else "",
                "action_topic": action_rec.action.topic if action_rec else "",
                "ambient": True,
            }
            self.ambient_transcript.append(rec)
            card = None
            try:
                card = self.session.vault.ingest(
                    topic="conversation.ambient", payload=dict(rec),
                )
            except Exception:
                pass
            self.session.mirror_to_obsidian(card)


# ─────────────────────────────────────────────────────────────────────────────
# REPL — commands and loop
# ─────────────────────────────────────────────────────────────────────────────


_HELP = """\
  /help                  this help
  /stats                 show conversation + vault stats
  /history [n]           show last n exchanges (default 10)
  /ambient [n]           show last n ambient (idle) collapses (default 5)
  /mood <name|none>      change or clear mood
                         moods: gate_clean lambda_drift dawning rally_drop
                                mystic_love heart_paint velocity heart_field
                                curiosity recurrence
  /live on|off           start/stop the ambient background engine —
                         when ON, the system keeps moving between your
                         questions; mood cycles, idle observes, state drifts
  /obsidian <path|off>   enable/disable mirroring every turn to an
                         Obsidian folder as a markdown note
  /forget                clear transcript (vault + ambient cards are kept)
  /bye  /quit  /exit     exit
"""


def _print_turn(turn: Dict[str, Any]) -> None:
    mood = turn["mood"] if turn["mood"] != "neutral" else ""
    mood_s = f"  (mood={mood})" if mood else ""
    prob = turn["probability"]
    print()
    print(f"[{turn['persona']}]{mood_s}  p={prob:.3f}  turn={turn['turn']}")
    print(turn["response"])
    if turn["action_kind"]:
        print(f"\u25b8 action: {turn['action_kind']}  \u2192  {turn['action_topic']}")


def _print_stats(session: ConversationSession) -> None:
    s = session.stats()
    print()
    print(f"turns:        {s['turns']}")
    print(f"vault cards:  {s['vault_cards']}")
    print(f"current mood: {s['current_mood']}")
    if s["winner_histogram"]:
        print("winners:")
        for name, count in s["winner_histogram"].items():
            bar = "\u2588" * count
            print(f"  {name:<20s} {count:4d}  {bar}")
    if s["action_topics"]:
        print("action topics:")
        for topic, count in sorted(s["action_topics"].items(), key=lambda kv: -kv[1]):
            print(f"  {topic:<40s} {count:4d}")
    if s["obsidian_path"]:
        print(f"obsidian:     {s['obsidian_path']}  (written: {s['obsidian_written']})")


def _print_history(session: ConversationSession, n: int) -> None:
    if not session.transcript:
        print("(no exchanges yet)")
        return
    for t in session.recent(n):
        snippet = (t["response"] or "").replace("\n", " ")
        if len(snippet) > 140:
            snippet = snippet[:137] + "..."
        print(f"  [{t['turn']:3d}] ({t['persona']:<18s}) {t['question']}")
        print(f"          {snippet}")


def run_repl(session: ConversationSession) -> int:
    print("aureon persona vacuum — REPL. type /help for commands, /bye to exit.")
    if session.current_mood:
        print(f"starting mood: {session.current_mood}")
    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            if line.startswith("/"):
                if not _dispatch_command(session, line):
                    break
                continue
            turn = session.ask(line)
            if turn:
                _print_turn(turn)
    finally:
        if session.ambient is not None and session.ambient.running:
            session.ambient.stop()
        print()
        print("\u2501" * 72)
        print("session summary")
        print("\u2501" * 72)
        _print_stats(session)
        if session.ambient is not None and session.ambient.ambient_transcript:
            print(f"ambient turns: {len(session.ambient.ambient_transcript)}")
    return 0


def _dispatch_command(session: ConversationSession, line: str) -> bool:
    """Run a /slash command. Return False to exit the REPL."""
    parts = line[1:].split()
    if not parts:
        return True
    cmd = parts[0].lower()
    rest = parts[1:]
    if cmd in ("bye", "quit", "exit"):
        return False
    if cmd == "help":
        print(_HELP)
    elif cmd == "stats":
        _print_stats(session)
    elif cmd == "history":
        n = int(rest[0]) if rest and rest[0].isdigit() else 10
        _print_history(session, n)
    elif cmd == "mood":
        if not rest:
            print(f"current mood: {session.current_mood or 'neutral'}")
        else:
            target = rest[0].lower()
            if target in ("none", "neutral", "clear"):
                session.current_mood = ""
                print("mood cleared.")
            elif target in ConversationSession.MOODS:
                session.current_mood = target
                print(f"mood set to {target}.")
            else:
                print(f"unknown mood {target!r}. valid: {', '.join(ConversationSession.MOODS)}")
    elif cmd == "forget":
        session.transcript.clear()
        if session.ambient is not None:
            session.ambient.ambient_transcript.clear()
        print("transcript cleared; vault cards kept.")
    elif cmd == "ambient":
        n = int(rest[0]) if rest and rest[0].isdigit() else 5
        if session.ambient is None or not session.ambient.ambient_transcript:
            print("(no ambient turns — use /live on to start the ambient engine)")
        else:
            for t in session.ambient.ambient_transcript[-n:]:
                snippet = (t["response"] or "").replace("\n", " ")
                if len(snippet) > 140:
                    snippet = snippet[:137] + "..."
                print(f"  [{t['turn']:3d}] ({t['persona']:<18s}, mood={t['mood']})")
                print(f"          {snippet}")
    elif cmd == "obsidian":
        if not rest:
            if session.obsidian is None:
                print("obsidian mirror is OFF. use /obsidian <path> to enable.")
            else:
                print(f"obsidian mirror → {session.obsidian.obsidian_root}  "
                      f"(written: {session._obsidian_written})")
        elif rest[0].lower() in ("off", "none", "disable"):
            if session.obsidian is None:
                print("already off.")
            else:
                session.detach_obsidian()
                print("obsidian mirror OFF.")
        else:
            path = session.attach_obsidian(rest[0])
            print(f"obsidian mirror ON → {path}")
    elif cmd == "live":
        target = (rest[0].lower() if rest else "")
        if target == "on":
            if session.ambient is None:
                session.ambient = AmbientEngine(session)
            if not session.ambient.running:
                session.ambient.start()
            print(f"ambient engine ON  (mood cycle ≈ {PHI_SQUARED:.2f}s, observe every "
                  f"{session.ambient.observe_every} beats)")
        elif target == "off":
            if session.ambient is not None and session.ambient.running:
                session.ambient.stop()
                print("ambient engine OFF")
            else:
                print("ambient engine already off")
        else:
            state = "ON" if (session.ambient and session.ambient.running) else "OFF"
            print(f"ambient engine is {state}. use /live on or /live off")
    else:
        print(f"unknown command: /{cmd}. try /help")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def _build_session(seed: int, mood: str) -> ConversationSession:
    bus = ThoughtBus(max_memory=2000)
    vault = AureonVault()
    vault.love_amplitude = 0.4
    vault.gratitude_score = 0.5
    vault.dominant_chakra = "solar"
    vault.dominant_frequency_hz = 432.0
    vault.cortex_snapshot = {"delta": 0.1, "theta": 0.1, "alpha": 0.1, "beta": 0.1, "gamma": 0.1}

    adapter = PersonaResponseAdapter(question="", seed=seed)
    personas: Dict[str, ResonantPersona] = {
        name: cls(adapter=adapter) for name, cls in AUREON_PERSONA_REGISTRY.items()
    }
    vacuum = PersonaVacuum(
        personas=personas,
        thought_bus=bus,
        vault=vault,
        rng=random.Random(seed),
        temperature=1.0,
    )
    # Wire subscribers once; subsequent mood applications hit live subs.
    bus.subscribe("queen.source_law.cognition", vacuum._on_cognition)
    bus.subscribe("dj.track.drop", vacuum._on_drop)

    # Baseline cognition so the very first collapse has something to read.
    bus.publish(Thought(
        source="ask",
        topic="queen.source_law.cognition",
        payload={
            "coherence_gamma": 0.5, "consciousness_psi": 0.5,
            "consciousness_level": "AWARE", "confidence": 0.5,
            "node_readings": {"tiger": 0.4, "falcon": 0.4, "dolphin": 0.4, "panda": 0.4},
        },
    ))

    return ConversationSession(bus=bus, vault=vault, vacuum=vacuum,
                               adapter=adapter, current_mood=mood or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Talk to the Aureon persona vacuum.")
    ap.add_argument("question", nargs="*", help="question — free text; omit to enter REPL")
    ap.add_argument("--mood", default="", help="optional mood preset")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for reproducible collapse")
    ap.add_argument("--repl", action="store_true",
                    help="force REPL mode even if a question was provided")
    ap.add_argument("--live", action="store_true",
                    help="start the ambient background engine at session launch")
    ap.add_argument(
        "--obsidian",
        default=str(resolve_obsidian_vault_path()),
        help=(
            "folder to mirror every conversation turn into as markdown "
            "(default: AUREON_OBSIDIAN_VAULT_PATH or ~/AureonObsidianVault)"
        ),
    )
    ap.add_argument(
        "--no-obsidian",
        action="store_true",
        help="disable the default Obsidian mirror for this session",
    )
    args = ap.parse_args()

    question = " ".join(args.question).strip()
    session = _build_session(seed=args.seed, mood=args.mood)

    if args.live:
        session.ambient = AmbientEngine(session, seed=args.seed)
        session.ambient.start()

    if args.obsidian and not args.no_obsidian:
        path = session.attach_obsidian(args.obsidian)
        print(f"obsidian mirror enabled → {path}")

    if question and not args.repl:
        # One-shot mode — stage 1 behaviour.
        turn = session.ask(question)
        print()
        print("\u2501" * 72)
        print(f"You: {question}")
        if session.current_mood:
            print(f"(mood preset: {session.current_mood})")
        print("\u2501" * 72)
        _print_turn(turn)
        print()
        return 0

    # REPL mode.
    if question:
        # User passed both a question and --repl — answer it first, then
        # drop into the loop.
        turn = session.ask(question)
        _print_turn(turn)
    return run_repl(session)


if __name__ == "__main__":
    raise SystemExit(main())
