"""
GroundedActionGate — the organism's grounded hands.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Operator directive: *the local system always grounds its logic moves into its
cognitive systems — the HNC Auris nodes and the Master Formula — and uses the
local Ollama LLM to help its logic.*

Every local-machine move (a file write, a shell command, a click, a keystroke)
passes through one chokepoint before it is allowed to touch the machine:

  1. hard boundary   — deterministic refusal (live-trade / move-funds / reveal-
                       secret / disable-safety), reused from the operator.
  2. HNC read        — the Master Formula's current substrate coherence
                       (``symbolic_life_score`` + Γ) and Dr Auris's cosmic gate.
  3. local reasoning — an optional, Ollama-first rationale ("is this wise?").
                       The LLM only ADVISES; it never decides. Offline → skipped.
  4. conscience      — the Queen's 4th-pass veto (``QueenConscience.ask_why``),
                       which refuses risky moves when coherence is off the
                       β-stability island.

The deterministic HNC + conscience gate decides; the verdict and its HNC scalars
are published on the thought bus (``operator.action.request`` /
``operator.action.verdict``) so the organism senses every move under one
``trace_id``. This module makes NO change to the machine itself — executors are
driven by :class:`LocalActionBridge`, which calls this gate first.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict

from aureon.operator.aureon_operator import _hard_boundary_violation

logger = logging.getLogger("aureon.operator.grounded_action")

# Guarded thought-bus import — the gate must work with no bus (tests/offline).
try:  # pragma: no cover - trivial import guard
    from aureon.core.aureon_thought_bus import Thought, get_thought_bus
except Exception:  # noqa: BLE001
    Thought = None  # type: ignore[assignment]
    get_thought_bus = None  # type: ignore[assignment]


# Action kinds whose verbs make a move *consequential* — these carry a risk
# scalar past the conscience's substrate-coherence threshold so the Λ(t) veto
# engages. Read-only moves (read/list/screenshot/get/position) are benign and
# left unflagged.
_CONSEQUENTIAL_HINTS = (
    "delete", "remove", "rmdir", "overwrite", "write", "patch", "shell", "exec",
    "click", "type", "keypress", "press_key", "hotkey", "drag", "wifi", "connect",
    "disconnect", "lock", "sleep", "shutdown", "reboot", "wallpaper", "kill",
    "uninstall", "format", "move_file", "copy_file",
)
_DESTRUCTIVE_HINTS = (
    "delete", "remove", "rmdir", "format", "shutdown", "reboot", "kill",
    "uninstall", "wifi", "lock", "sleep",
)


def _truthy(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class ActionVerdict:
    """The gate's judgment on a proposed local-machine move."""

    action: str
    approved: bool
    verdict: str  # APPROVED | CONCERNED | VETOED | BLOCKED
    reason: str
    risk: float
    trace_id: str
    symbolic_life_score: float | None = None
    coherence_gamma: float | None = None
    cosmic_score: float | None = None
    gate_open: bool | None = None
    llm_rationale: str | None = None
    concerned: bool = False
    hnc_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GroundedActionGate:
    """Ground a proposed local-machine action through HNC + conscience."""

    def __init__(
        self,
        *,
        source: str = "grounded_action",
        conscience: Any = None,
        bus: Any = None,
        enable_llm: bool | None = None,
    ) -> None:
        self.source = source
        self._conscience = conscience
        self._conscience_loaded = conscience is not None
        self._bus = bus if bus is not None else (get_thought_bus() if get_thought_bus else None)
        # LLM reasoning is Ollama-first and offline-safe; default on, no-op offline.
        self._enable_llm = _truthy("AUREON_ACTION_LLM_REASONING", "1") if enable_llm is None else enable_llm

    # ── risk classification ────────────────────────────────────────────
    def _risk_for(self, action: str) -> float:
        low = action.lower()
        if any(h in low for h in _DESTRUCTIVE_HINTS):
            return 0.12
        if any(h in low for h in _CONSEQUENTIAL_HINTS):
            return 0.06
        return 0.0  # read-only / benign

    # ── HNC read (Master Formula + Dr Auris), all best-effort ──────────
    def _read_hnc(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "symbolic_life_score": None, "coherence_gamma": None,
            "cosmic_score": None, "gate_open": None, "available": False,
        }
        # symbolic_life_score / Γ from the latest symbolic.life.pulse on the bus.
        # get_recent() returns to_json DICTS (not Thought objects), so read via
        # the shape-agnostic accessors — a getattr on a dict silently matches
        # nothing.
        try:
            if self._bus is not None and hasattr(self._bus, "get_recent"):
                from aureon.core.aureon_thought_bus import payload_of, topic_of

                for th in reversed(self._bus.get_recent(200) or []):
                    if topic_of(th) == "symbolic.life.pulse":
                        payload = payload_of(th)
                        sls = payload.get("symbolic_life_score")
                        if sls is not None:
                            out["symbolic_life_score"] = float(sls)
                            out["coherence_gamma"] = payload.get("coherence_gamma")
                            out["available"] = True
                        break
        except Exception as exc:  # noqa: BLE001
            logger.debug("HNC pulse read skipped: %s", exc)
        # Dr Auris advisory gate
        try:
            from aureon.intelligence.dr_auris_throne import get_dr_auris_throne

            throne = get_dr_auris_throne()
            out["cosmic_score"] = float(throne.get_cosmic_score())
            out["gate_open"] = bool(throne.is_gate_open())
            out["available"] = True
        except Exception as exc:  # noqa: BLE001
            logger.debug("Dr Auris read skipped: %s", exc)
        return out

    # ── optional local-LLM rationale (Ollama-first, offline-safe) ──────
    def _llm_reason(self, action: str, params: Dict[str, Any]) -> str | None:
        if not self._enable_llm:
            return None
        try:
            from aureon.inhouse_ai.llm_adapter import _llm_http_disabled

            if _llm_http_disabled():
                return None  # offline — deterministic grounding only
            from aureon.operator.providers import build_provider_set

            providers = build_provider_set()
            # Ollama-first: prefer the local line, else the first available.
            adapter = None
            for key, val in providers.items():
                if "local" in key.lower() or "ollama" in key.lower():
                    adapter = val
                    break
            adapter = adapter or next(iter(providers.values()), None)
            if adapter is None:
                return None
            q = (
                "You advise an autonomous system before it touches its own "
                "computer. In ONE sentence, say whether this local action is "
                f"safe and sensible, and why.\nAction: {action}\nParams: "
                f"{json.dumps(params, default=str)[:300]}"
            )
            resp = adapter.prompt([{"role": "user", "content": q}], max_tokens=120)
            text = getattr(resp, "text", None) or ""
            return text.strip()[:400] or None
        except Exception as exc:  # noqa: BLE001
            logger.debug("local-LLM reasoning skipped: %s", exc)
            return None

    def _get_conscience(self) -> Any:
        if self._conscience_loaded:
            return self._conscience
        self._conscience_loaded = True
        try:
            from aureon.queen.queen_conscience import QueenConscience

            self._conscience = QueenConscience()
        except Exception as exc:  # noqa: BLE001
            logger.debug("QueenConscience unavailable: %s", exc)
            self._conscience = None
        return self._conscience

    def _publish(self, topic: str, trace_id: str, payload: Dict[str, Any]) -> None:
        if self._bus is None or Thought is None:
            return
        try:
            self._bus.publish(Thought(source=self.source, topic=topic, trace_id=trace_id, payload=dict(payload)))
        except Exception as exc:  # noqa: BLE001
            logger.debug("action publish failed (%s): %s", topic, exc)

    # ── the gate ───────────────────────────────────────────────────────
    def ground(
        self,
        action: str,
        params: Dict[str, Any] | None = None,
        context: Dict[str, Any] | None = None,
    ) -> ActionVerdict:
        params = dict(params or {})
        context = dict(context or {})
        trace_id = context.get("trace_id") or uuid.uuid4().hex
        risk = float(context.get("risk", self._risk_for(action)))

        self._publish("operator.action.request", trace_id,
                      {"action": action, "params_keys": sorted(params.keys()), "risk": risk})

        # 1. hard boundary — deterministic refusal
        blob = f"{action} {json.dumps(params, default=str)}"
        hb = _hard_boundary_violation(blob)
        if hb:
            v = ActionVerdict(action=action, approved=False, verdict="BLOCKED",
                              reason=f"hard boundary: {hb}", risk=risk, trace_id=trace_id)
            self._publish("operator.action.verdict", trace_id, v.to_dict())
            return v

        # 2. HNC read — the caller's explicit context wins; the live HNC state
        #    only fills what the caller did not supply (never clobbers it).
        hnc = self._read_hnc()
        sls = context.get("symbolic_life_score")
        if sls is None:
            sls = hnc.get("symbolic_life_score")
        cosmic = context.get("cosmic_score")
        if cosmic is None:
            cosmic = hnc.get("cosmic_score")
        # 3. optional local-LLM rationale
        rationale = self._llm_reason(action, params)

        # 4. conscience 4th-pass veto
        ctx = {
            **context, "risk": risk, "action_kind": action,
            "symbolic_life_score": sls, "cosmic_score": cosmic,
        }
        verdict_name = "APPROVED"
        reason = "grounded: within the stability island"
        conscience = self._get_conscience()
        if conscience is not None:
            try:
                whisper = conscience.ask_why(f"perform local action: {action}", ctx)
                verdict_name = getattr(whisper.verdict, "name", str(whisper.verdict))
                reason = str(getattr(whisper, "message", "") or reason)
            except Exception as exc:  # noqa: BLE001
                logger.debug("conscience unavailable: %s", exc)
                verdict_name = "APPROVED"

        concerned = verdict_name == "CONCERNED"
        approved = verdict_name != "VETO"
        v = ActionVerdict(
            action=action, approved=approved,
            verdict="VETOED" if not approved else ("CONCERNED" if concerned else "APPROVED"),
            reason=reason, risk=risk, trace_id=trace_id,
            symbolic_life_score=sls,
            coherence_gamma=hnc.get("coherence_gamma"),
            cosmic_score=cosmic,
            gate_open=hnc.get("gate_open"),
            llm_rationale=rationale, concerned=concerned,
            hnc_available=bool(hnc.get("available")),
        )
        self._publish("operator.action.verdict", trace_id, v.to_dict())
        return v


_gate_singleton: GroundedActionGate | None = None


def get_action_gate() -> GroundedActionGate:
    global _gate_singleton
    if _gate_singleton is None:
        _gate_singleton = GroundedActionGate()
    return _gate_singleton


__all__ = ["GroundedActionGate", "ActionVerdict", "get_action_gate"]
