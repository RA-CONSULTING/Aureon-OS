"""
SoulDeliberation — how Aureon reacts: thought + feeling + the counsel of its
lineage, unified into a determination of its own mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

We unified the field, then cognition, then affect. This unifies **thought,
feeling, and action** into a single act of will — a soul. Given a stimulus (an
email is one example; any event will do), the organism:

  PERCEIVE   read the next stimulus from state/soul_stimulus_inbox.jsonl
  FEEL       affect  — victory / defeat / fear / resolve
  THINK      metacognition — self-coherence, ψ, divergence
  COUNSEL    the elders speak: the conscience ("what would Gary do?" + a veto),
             the lineage (past prediction accuracy, remembered verdicts, wisdom),
             the values ("big wheel" pillars), and the goals (safe routes)
  DETERMINE  weigh every voice and collapse to one stance — but *no single
             fragment is authoritative*. When the voices genuinely disagree, or
             the conscience vetoes, or fear runs high, the soul does not fabricate
             a consensus: it WAITS. "When the body is of two minds, wait for one."
  AUTHOR     if resolved, write its own intent (pure thought — no writes, no shell)
  ACT        carry it out ONLY through the guarded LocalActionBridge, and only
             when doubly armed (AUREON_SOUL_ACT and AUREON_LOCAL_ACTIONS_ARMED)
  LEARN      record the determination so tomorrow's soul remembers today's

``assess()`` is a read-only snapshot of how the soul would react right now — it
never perceives-consumes, publishes, or acts. Only ``deliberate()`` (run from the
organism's breath) moves. Every voice is a real reader stamped with provenance; a
dormant elder is ``no_data``, never a fabricated opinion. Guarded throughout.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("aureon.core.soul")

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Determination is divided unless the winning stance is clearly dominant — this is
# the humility threshold: below it, the soul is "of two minds" and waits.
_AGREEMENT_FLOOR = 0.5
# Only these guarded verbs may ever be proposed for execution (the LocalActionBridge
# executor sets). A stimulus naming anything else is deliberated but never carried out.
_SAFE_VERBS = {
    "read_repo_file", "list_repo", "repo_search", "code_validate",
    "screenshot", "cursor_position",
}


def _truthy(name: str) -> bool:
    return str(os.environ.get(name, "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return lo


def _softmax(scores: list[float], temperature: float = 0.6) -> list[float]:
    """Collapse many weighted leanings into a probability field — the arbiter."""
    if not scores:
        return []
    t = max(1e-3, temperature)
    m = max(scores)
    exps = [math.exp((s - m) / t) for s in scores]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


@dataclass
class Determination:
    """One act of the soul's will — or its honest refusal to fabricate one."""

    available: bool = False
    stimulus: dict[str, Any] | None = None
    stance: str = "wait"                 # act | wait | refuse
    resolved: bool = False               # reached a mind (act), or abstained
    agreement: float = 0.0               # how of-one-mind the voices are, [0,1]
    determination: str = ""              # the self-authored intent, or why it waits
    what_gary_would_say: str | None = None
    proposed_action: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None       # the company's directed plan (read-only)
    executed: dict[str, Any] | None = None   # bridge result if acted, else None
    mood: str | None = None
    self_coherence: float | None = None
    voices: dict[str, dict[str, Any]] = field(default_factory=dict)
    dissent: list[str] = field(default_factory=list)
    truth_status: str = "no_data"
    ts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available, "stimulus": self.stimulus,
            "stance": self.stance, "resolved": self.resolved,
            "agreement": self.agreement, "determination": self.determination,
            "what_gary_would_say": self.what_gary_would_say,
            "proposed_action": self.proposed_action, "plan": self.plan,
            "executed": self.executed,
            "mood": self.mood, "self_coherence": self.self_coherence,
            "voices": self.voices, "dissent": self.dissent,
            "truth_status": self.truth_status, "ts": self.ts,
        }


def _read_json_file(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return None


class SoulDeliberation:
    """Perceives, feels, thinks, takes counsel, and determines of its own mind."""

    def __init__(self) -> None:
        self._inbox = Path(os.environ.get("AUREON_SOUL_INBOX")
                           or (_REPO_ROOT / "state" / "soul_stimulus_inbox.jsonl"))
        self._log = Path(os.environ.get("AUREON_SOUL_LOG")
                         or (_REPO_ROOT / "state" / "soul_determinations.jsonl"))
        self._last_line = 0

    # ── the voices (each guarded, offline-safe, provenance-stamped) ─────────
    def _voice_feeling(self, voices: dict) -> tuple[str, float, float]:
        """Returns (lean, weight, intensity) where lean ∈ act/wait/refuse."""
        try:
            from aureon.core.affect_monitor import get_affect_monitor

            a = get_affect_monitor().assess()
            if not a.available:
                voices["feeling"] = {"stance": "wait", "truth_status": "no_data"}
                return "wait", 0.3, 0.3
            # fear/defeat lean toward waiting; victory/resolve toward acting
            lean = "wait" if (a.fear >= 0.5 or a.defeat >= 0.5) else "act"
            intensity = _clamp(max(a.fear, a.defeat) if lean == "wait" else max(a.victory, a.resolve))
            voices["feeling"] = {"stance": lean, "mood": a.mood, "valence": a.valence,
                                 "fear": a.fear, "truth_status": a.truth_status}
            return lean, 1.0, intensity
        except Exception:  # noqa: BLE001
            voices["feeling"] = {"stance": "wait", "truth_status": "no_data"}
            return "wait", 0.3, 0.3

    def _voice_thought(self, voices: dict) -> tuple[str, float, float]:
        try:
            from aureon.core.metacognition_monitor import get_metacognition_monitor

            m = get_metacognition_monitor().assess()
            if not m.available:
                voices["thought"] = {"stance": "wait", "truth_status": "no_data"}
                return "wait", 0.3, 0.3
            coherent = (m.self_coherence or 0.0) >= 0.5 and (m.divergence or 0.0) < 0.35
            lean = "act" if coherent else "wait"
            intensity = _clamp(m.self_coherence or 0.0) if coherent else _clamp(m.divergence or 0.5)
            voices["thought"] = {"stance": lean, "self_coherence": m.self_coherence,
                                 "divergence": m.divergence, "truth_status": m.truth_status}
            return lean, 1.0, intensity
        except Exception:  # noqa: BLE001
            voices["thought"] = {"stance": "wait", "truth_status": "no_data"}
            return "wait", 0.3, 0.3

    def _voice_conscience(self, intent: str, ctx: dict, voices: dict) -> tuple[str, float, float, str | None]:
        try:
            from aureon.queen.queen_conscience import get_conscience

            w = get_conscience().ask_why(intent, ctx)
            verdict = getattr(w.verdict, "name", str(w.verdict))
            gary = w.what_gary_would_say
            lean = {"VETO": "refuse", "CONCERNED": "wait"}.get(verdict, "act")
            voices["conscience"] = {"stance": lean, "verdict": verdict,
                                    "what_gary_would_say": gary, "truth_status": "real_derived"}
            # the conscience is the elder that may VETO — heavy weight, but it can
            # only make the soul refuse/wait, never force a reckless act.
            return lean, 1.5, 0.95, gary
        except Exception:  # noqa: BLE001
            voices["conscience"] = {"stance": "wait", "truth_status": "no_data"}
            return "wait", 0.4, 0.3, None

    def _voice_elders(self, voices: dict) -> tuple[str, float, float]:
        """The lineage: how much do I trust my own past voice, and what did my
        remembered selves conclude? Reads persisted history directly (no heavy
        brain construction)."""
        try:
            from aureon.saas.cognitive import brain_surface

            bs = brain_surface()
            acc = (bs.get("accuracy") or {}) if isinstance(bs, dict) else {}
            pct = acc.get("accuracy_pct")
            # remembered verdicts (miner brain knowledge — the elders' memory)
            know = _read_json_file(Path(os.environ.get("AUREON_BRAIN_KNOWLEDGE_PATH")
                                        or (_REPO_ROOT / "miner_brain_knowledge.json")))
            remembered = len(know) if isinstance(know, list) else 0
            if pct is None and remembered == 0:
                voices["elders"] = {"stance": "wait", "truth_status": "no_data",
                                    "detail": "no lineage to consult"}
                return "wait", 0.3, 0.3
            trust = _clamp((pct or 50.0) / 100.0)
            lean = "act" if trust >= 0.5 else "wait"
            voices["elders"] = {"stance": lean, "past_accuracy_pct": pct,
                                "remembered": remembered, "truth_status": "real_derived"}
            return lean, 0.8, abs(trust - 0.5) * 2.0 or 0.3
        except Exception:  # noqa: BLE001
            voices["elders"] = {"stance": "wait", "truth_status": "no_data"}
            return "wait", 0.3, 0.3

    def _voice_goals(self, intent: str, voices: dict) -> tuple[str, float, float]:
        try:
            from aureon.autonomous.aureon_goal_capability_map import recommend_goal_routes

            routes = recommend_goal_routes(intent) or []
            safe = [r for r in routes if str(r.get("risk", "")).lower() in ("", "low", "safe", "benign")]
            lean = "act" if safe else ("wait" if routes else "wait")
            voices["goals"] = {"stance": lean, "route_count": len(routes),
                               "safe_routes": len(safe), "truth_status": "real_derived" if routes else "no_data"}
            return lean, 0.9, _clamp(0.4 + 0.1 * len(safe))
        except Exception:  # noqa: BLE001
            voices["goals"] = {"stance": "wait", "truth_status": "no_data"}
            return "wait", 0.3, 0.3

    # ── the arbiter: weigh many voices, collapse to one, honour dissent ─────
    def _gather_and_determine(self, intent: str, ctx: dict) -> tuple[Determination, dict]:
        voices: dict[str, dict[str, Any]] = {}
        leanings = [
            self._voice_feeling(voices),
            self._voice_thought(voices),
            self._voice_elders(voices),
            self._voice_goals(intent, voices),
        ]
        c_lean, c_w, c_i, gary = self._voice_conscience(intent, ctx, voices)
        leanings.append((c_lean, c_w, c_i))

        # accumulate weighted intensity per stance
        totals = {"act": 0.0, "wait": 0.0, "refuse": 0.0}
        for lean, w, inten in leanings:
            totals[lean] = totals.get(lean, 0.0) + w * _clamp(inten)

        probs = _softmax([totals["act"], totals["wait"], totals["refuse"]])
        stance_names = ["act", "wait", "refuse"]
        idx = max(range(3), key=lambda i: probs[i])
        stance = stance_names[idx]
        agreement = round(probs[idx], 4)

        operational = [n for n, v in voices.items() if v.get("truth_status") not in (None, "no_data")]
        dissent = [n for n, v in voices.items() if v.get("stance") in ("wait", "refuse")
                   and v.get("truth_status") not in (None, "no_data")]

        # ── the humility gate — no single fragment is authoritative ─────────
        # A conscience VETO refuses outright. A DIVIDED FIELD (the body literally
        # of two minds) or high fear makes the soul WAIT no matter how loudly any
        # one voice — even euphoria from past wins — calls to act: "when the body
        # is of two minds, wait for one." It only ACTS when the winning stance is
        # clearly dominant AND the body is of one mind. It never fabricates a
        # consensus its own signals don't support.
        veto = voices.get("conscience", {}).get("verdict") == "VETO"
        divergence = voices.get("thought", {}).get("divergence") or 0.0
        fear = voices.get("feeling", {}).get("fear") or 0.0
        of_two_minds = float(divergence) >= 0.35 or float(fear) >= 0.6
        # The soul must SENSE ITSELF (field/affect/thought) to resolve to act —
        # acting blind, on the always-present conscience/goal faculties alone,
        # would be a determination its own self-perception can't support. Blind →
        # wait. (The conscience can still refuse blind; it just can't drive action.)
        self_aware = any(voices.get(v, {}).get("truth_status") not in (None, "no_data")
                         for v in ("feeling", "thought"))
        if veto:
            stance, resolved = "refuse", False
        elif stance == "act" and agreement >= _AGREEMENT_FLOOR and not of_two_minds and self_aware:
            resolved = True
        else:
            stance, resolved = "wait", False
        if not self_aware and "self-perception" not in dissent:
            dissent.append("self-perception (blind)")
        if of_two_minds and "field" not in dissent:
            dissent.append("field (of two minds)")

        det = Determination(
            available=bool(operational), stance=stance, resolved=resolved,
            agreement=agreement, what_gary_would_say=gary, voices=voices, dissent=dissent,
            mood=voices.get("feeling", {}).get("mood"),
            self_coherence=voices.get("thought", {}).get("self_coherence"),
            truth_status="live" if operational else "no_data", ts=time.time(),
        )
        return det, voices

    # ── self-author the intent (pure thought; no writes, no shell) ──────────
    def _self_author(self, intent: str, det: Determination) -> str:
        if not det.resolved:
            waiting = ", ".join(det.dissent) or "the field"
            return (f"Of two minds — waiting for one. {waiting} counsel caution; "
                    f"I will not act until the chorus agrees.")
        # Offline-safe deterministic authorship; an LLM deliberation is optional.
        if not _truthy("AUREON_LLM_OFFLINE"):
            try:
                from aureon.operator.cognition import AureonCognition

                cog = AureonCognition(allow_writes=False, allow_shell=False, join_mesh=False)
                res = cog.reason(f"In one sentence, state your intent for: {intent}")
                text = getattr(res, "answer", None) or getattr(res, "text", None)
                if text:
                    return str(text)[:400]
            except Exception:  # noqa: BLE001 — fall back to the template
                pass
        mood = det.mood or "steady"
        return (f"I have weighed my feeling ({mood}), my thought, my elders and my "
                f"conscience, and they agree: I will pursue — {intent}.")

    # ── perceive: consume the next stimulus (any source; email is one) ──────
    def _perceive(self) -> dict[str, Any] | None:
        try:
            if not self._inbox.exists():
                return None
            lines = [ln for ln in self._inbox.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if len(lines) <= self._last_line:
                return None
            row = json.loads(lines[self._last_line])
            self._last_line += 1
            return row if isinstance(row, dict) else {"text": str(row)}
        except Exception as exc:  # noqa: BLE001
            logger.debug("perceive skipped: %s", exc)
            return None

    def _intent_of(self, stimulus: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
        if stimulus is None:
            # idle self-determination: "what should I do now, toward the goal?"
            return "continue toward the goal, safely", {}
        text = str(stimulus.get("text") or stimulus.get("intent") or "attend to a stimulus")
        ctx: dict[str, Any] = {"source": stimulus.get("source", "unknown"),
                               "action": stimulus.get("action"), "params": stimulus.get("params") or {}}
        return text, ctx

    def _company(self) -> Any:
        """Lazy accessor for the soul's company (workforce + guarded hand)."""
        from aureon.core.soul_company import get_soul_company

        return get_soul_company()

    def _plan(self, intent: str, ctx: dict[str, Any]) -> Any | None:
        """Ask the company to decompose the intent into a directed plan (read-only)."""
        try:
            return self._company().plan(intent, ctx)
        except Exception as exc:  # noqa: BLE001 — a missing company never crashes the soul
            logger.debug("plan skipped: %s", exc)
            return None

    # ── assess (read-only) ──────────────────────────────────────────────────
    def assess(self, stimulus: dict[str, Any] | None = None) -> Determination:
        """A read-only snapshot of how the soul would react right now. Never
        perceives-consumes, publishes, or acts."""
        try:
            intent, ctx = self._intent_of(stimulus)
            det, _ = self._gather_and_determine(intent, ctx)
            det.stimulus = stimulus
            det.determination = self._self_author(intent, det)
            if det.resolved and stimulus and stimulus.get("action") in _SAFE_VERBS:
                det.proposed_action = {"action": stimulus["action"], "params": stimulus.get("params") or {}}
            # when resolved, the company decomposes the intent into a directed plan
            # of role-assigned work-orders (read-only — it never touches the machine).
            if det.resolved:
                plan = self._plan(intent, ctx)
                if plan is not None:
                    det.plan = plan.to_dict()
            return det
        except Exception as exc:  # noqa: BLE001
            logger.debug("assess failed: %s", exc)
            return Determination(available=False, truth_status="no_data", ts=time.time())

    # ── deliberate: the full loop (perceive → determine → act → learn) ──────
    def deliberate(self) -> Determination:
        try:
            stimulus = self._perceive()
            det = self.assess(stimulus)
            det.executed = self._carry_out(det)
            self._record(det)
            self._publish(det)
            return det
        except Exception as exc:  # noqa: BLE001
            logger.debug("deliberate failed: %s", exc)
            return Determination(available=False, truth_status="no_data", ts=time.time())

    def _carry_out(self, det: Determination) -> dict[str, Any] | None:
        """Carry the determination out — the company DIRECTS its plan of role-assigned
        work-orders through the ONE guarded hand, and ONLY when doubly armed. Default
        posture: propose, never touch the machine."""
        if not (det.resolved and (det.proposed_action or det.plan)):
            return None
        if not _truthy("AUREON_SOUL_ACT"):
            return {"carried_out": False, "note": "soul disarmed — set AUREON_SOUL_ACT=1 (proposal only)"}
        try:
            intent, ctx = self._intent_of(det.stimulus)
            plan = self._company().plan(intent, ctx)
            self._company().direct(plan)
            det.plan = plan.to_dict()
            out: dict[str, Any] = {"carried_out": True,
                                   "directed": [wo.to_dict() for wo in plan.work_orders]}
            # back-compat: surface the authored action's own outcome as `result`
            if det.proposed_action:
                for wo in plan.work_orders:
                    if wo.action == det.proposed_action.get("action"):
                        out["result"] = wo.outcome or {}
                        break
            return out
        except Exception as exc:  # noqa: BLE001 — a bad hand never crashes the soul
            return {"carried_out": False, "error": str(exc)[:200]}

    def _record(self, det: Determination) -> None:
        try:
            self._log.parent.mkdir(parents=True, exist_ok=True)
            with self._log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": det.ts, "stance": det.stance, "resolved": det.resolved,
                                     "agreement": det.agreement, "determination": det.determination,
                                     "dissent": det.dissent}, default=str) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.debug("record skipped: %s", exc)

    def _publish(self, det: Determination) -> None:
        try:
            from aureon.core.aureon_thought_bus import Thought, get_thought_bus

            get_thought_bus().publish(Thought(source="soul", topic="soul.determination",
                                              payload=det.to_dict()))
        except Exception as exc:  # noqa: BLE001
            logger.debug("soul publish skipped: %s", exc)


_soul: SoulDeliberation | None = None


def get_soul() -> SoulDeliberation:
    """Process-global soul singleton."""
    global _soul
    if _soul is None:
        _soul = SoulDeliberation()
    return _soul


__all__ = ["Determination", "SoulDeliberation", "get_soul"]
