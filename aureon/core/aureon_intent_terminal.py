"""
aureon_intent_terminal.py — Say what you want, aureon does it.

A terminal REPL that turns natural-language intent into structured
authoring.request payloads the self-authoring stack already knows how
to dispatch. Two parser paths:

    LLM PATH (preferred)  — sends the user text + an action schema to
                            the Ollama adapter wired into the authoring
                            loop. Ollama returns a JSON intent; we
                            dispatch it.
    KEYWORD PATH (fallback)  — regex + verb recognition for common asks.
                            Works even when Ollama is offline.

Supported actions the terminal can dispatch:

    wire <module>         → authoring.research: wire_in_dormant
    fix <file|module>     → authoring.research: repair_syntax / refine
    edit <file>: <spec>   → propose_edit (freeform; requires old/new)
    ab <file>: <spec>     → propose_comparison (aureon vs human)
    bootstrap             → authoring.request kind=bootstrap
    execute <skill>       → run a skill through the architect
    score <id> <n>        → observer score for an applied edit
    backtest <id>         → run backtest on an applied edit
    status                → authoring loop status
    reachability          → who is wired
    narrate [N]           → recent N who/why stories
    wheel [N]             → aggregate movement across last N edits
    digest [N]            → consciousness digest window N
    pending               → list pending edits awaiting confirm
    confirm <pending_id>  → apply a pending edit
    reject <pending_id>   → discard a pending edit
    help                  → list commands
    quit | exit           → leave

Typical session:

    you> wire aureon.atn into ICS so we get real backtesting
    aureon> queued authoring.research for aureon.atn.aureon_atn_backtest
            (swarm dispatch on next cadence; watch state/
            integrations_pending/)
    you> narrate 5
    aureon> [2026-... variant=aureon score=0.9 ...] ...
    you> confirm pe_abc
    aureon> applied; verdict=positive; continuity swap ok

Nothing in this module modifies code directly — it only speaks on the
ThoughtBus via authoring.request / authoring.research and calls
existing singleton APIs. The integrator, scanner, swarm, refinement
loop, and continuity engine do the rest.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("aureon.core.intent_terminal")

_REPO_ROOT = Path(__file__).resolve().parents[2]


# ─────────────────────────────────────────────────────────────────────────────
# Schema of dispatchable actions
# ─────────────────────────────────────────────────────────────────────────────

ACTION_SCHEMA: Dict[str, Dict[str, Any]] = {
    "wire": {
        "description": "Wire a dormant aureon.* module into the ICS runtime.",
        "fields": {"target_module": "dotted module path (e.g. aureon.atn.aureon_atn_backtest)"},
        "produces": {"topic": "authoring.research", "kind": "research",
                     "intent": "wire_in_dormant"},
    },
    "fix": {
        "description": "Ask the architect to propose a fix for a file or module.",
        "fields": {"target_path_or_module": "repo-rel path or dotted module",
                   "note": "optional freeform issue description"},
        "produces": {"topic": "authoring.research", "kind": "research",
                     "intent": "refine_regression"},
    },
    "edit": {
        "description": "Propose a direct edit (path + old_text + new_text).",
        "fields": {"path": "repo-rel path",
                   "old_text": "exact anchor — must match once",
                   "new_text": "replacement",
                   "rationale": "one-line why"},
        "produces": {"api": "integrator.propose_edit"},
    },
    "ab": {
        "description": "Propose an A/B comparison — aureon vs human variant.",
        "fields": {"path": "repo-rel path",
                   "old_text": "exact anchor",
                   "aureon_new_text": "aureon variant",
                   "human_new_text": "human variant",
                   "rationale": "one-line why"},
        "produces": {"api": "integrator.propose_comparison"},
    },
    "bootstrap": {
        "description": "Bootstrap the L0 atomic VM primitive skills.",
        "fields": {},
        "produces": {"topic": "authoring.request", "kind": "bootstrap"},
    },
    "execute": {
        "description": "Execute a named skill through the architect's executor.",
        "fields": {"name": "skill name"},
        "produces": {"topic": "authoring.request", "kind": "execute"},
    },
    "score": {
        "description": "Record an observer score for an applied edit.",
        "fields": {"applied_id": "pending_id of the applied edit",
                   "score": "0.0..1.0",
                   "comment": "optional"},
        "produces": {"api": "refinement.score"},
    },
    "backtest": {
        "description": "Run a backtest on an applied edit.",
        "fields": {"applied_id": "pending_id of the applied edit",
                   "mode": "fast | full"},
        "produces": {"api": "refinement.backtest"},
    },
    "status": {
        "description": "Authoring loop + stack status.",
        "fields": {},
        "produces": {"api": "authoring_loop.get_status"},
    },
    "reachability": {
        "description": "Show which modules are wired (reach_ratio).",
        "fields": {},
        "produces": {"api": "introspection.reachability"},
    },
    "narrate": {
        "description": "Recent N who/why stories.",
        "fields": {"limit": "N (default 10)"},
        "produces": {"api": "narrator.print_recent"},
    },
    "wheel": {
        "description": "Aggregate what moved across recent edits.",
        "fields": {"window": "N (default 20)"},
        "produces": {"api": "narrator.wheel_delta"},
    },
    "digest": {
        "description": "Consciousness scoring digest.",
        "fields": {"window": "N (default 50)"},
        "produces": {"api": "refinement.consciousness_digest"},
    },
    "pending": {
        "description": "List pending edits awaiting confirm.",
        "fields": {},
        "produces": {"api": "integrator.list_pending"},
    },
    "confirm": {
        "description": "Apply a pending edit by id.",
        "fields": {"pending_id": "pe_..."},
        "produces": {"api": "integrator.confirm_edit"},
    },
    "reject": {
        "description": "Discard a pending edit by id.",
        "fields": {"pending_id": "pe_...", "reason": "optional"},
        "produces": {"api": "integrator.reject_edit"},
    },
    "help": {
        "description": "List commands.",
        "fields": {},
        "produces": {"api": "terminal.help"},
    },
    "quit": {
        "description": "Leave.",
        "fields": {},
        "produces": {"api": "terminal.quit"},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Intent parsing — keyword fallback
# ─────────────────────────────────────────────────────────────────────────────

_QUIT_WORDS = {"quit", "exit", ":q", "q", "bye"}


def _keyword_parse(text: str) -> Dict[str, Any]:
    """Deterministic fallback when no LLM is available."""
    low = text.strip().lower()
    if not low:
        return {"action": "", "args": {}}
    if low in _QUIT_WORDS:
        return {"action": "quit", "args": {}}
    if low == "help":
        return {"action": "help", "args": {}}
    if low in ("status", "state"):
        return {"action": "status", "args": {}}
    if low in ("reachability", "wired?"):
        return {"action": "reachability", "args": {}}
    if low == "bootstrap":
        return {"action": "bootstrap", "args": {}}
    if low == "pending":
        return {"action": "pending", "args": {}}

    # narrate [N]
    m = re.match(r"^narrate(?:\s+(\d+))?\s*$", low)
    if m:
        return {"action": "narrate", "args": {"limit": int(m.group(1) or 10)}}
    m = re.match(r"^wheel(?:\s+(\d+))?\s*$", low)
    if m:
        return {"action": "wheel", "args": {"window": int(m.group(1) or 20)}}
    m = re.match(r"^digest(?:\s+(\d+))?\s*$", low)
    if m:
        return {"action": "digest", "args": {"window": int(m.group(1) or 50)}}

    m = re.match(r"^(confirm|reject)\s+(\S+)(?:\s+(.*))?$", low)
    if m:
        verb, pid, rest = m.groups()
        return {"action": verb, "args": {"pending_id": pid, "reason": (rest or "")}}

    m = re.match(r"^score\s+(\S+)\s+([0-9.]+)(?:\s+(.*))?$", low)
    if m:
        pid, score, comment = m.groups()
        return {"action": "score", "args": {
            "applied_id": pid, "score": float(score), "comment": comment or ""}}

    m = re.match(r"^backtest\s+(\S+)(?:\s+(fast|full))?\s*$", low)
    if m:
        pid, mode = m.groups()
        return {"action": "backtest", "args": {
            "applied_id": pid, "mode": mode or "fast"}}

    m = re.match(r"^execute\s+(\S+)\s*$", low)
    if m:
        return {"action": "execute", "args": {"name": m.group(1)}}

    # "wire <module>" or "activate <module>" or "bring <module> online"
    m = re.match(r"^(?:wire|activate|bring)\s+(\S+)", low)
    if m:
        tgt = m.group(1).rstrip(".,;:")
        if not tgt.startswith("aureon."):
            tgt = "aureon." + tgt
        return {"action": "wire", "args": {"target_module": tgt}}

    # "fix <path or module> [: comment]"
    m = re.match(r"^(?:fix|repair)\s+(\S+)(?:\s*[:]\s*(.*))?$", low)
    if m:
        tgt, note = m.groups()
        return {"action": "fix", "args": {
            "target_path_or_module": tgt, "note": note or ""}}

    # Fallback: treat the whole line as a research prompt the architect
    # can think about.
    return {
        "action": "fix",
        "args": {"target_path_or_module": "(unspecified)", "note": text},
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM intent parser (uses whatever adapter the authoring loop has)
# ─────────────────────────────────────────────────────────────────────────────

_LLM_ADAPTER_CACHE: Dict[str, Any] = {}


def _get_llm_adapter() -> Optional[Any]:
    """
    Return a usable Ollama adapter. Cache it so we only pay the
    construction cost once per terminal session. Order of preference:
        1. adapter already wired on the authoring loop
        2. adapter on the architect's SkillWriter
        3. live-catalog Ollama adapter on the fast nerve lane
    """
    if "adapter" in _LLM_ADAPTER_CACHE:
        return _LLM_ADAPTER_CACHE["adapter"]
    adapter = None
    try:
        from aureon.core.aureon_cognitive_authoring_loop import get_authoring_loop
        loop = get_authoring_loop()
        adapter = loop.ollama_adapter or (
            getattr(getattr(loop.architect, "writer", None), "adapter", None)
            if loop.architect else None
        )
    except Exception as e:
        logger.debug("loop adapter probe: %s", e)
    if adapter is None:
        try:
            from aureon.integrations.ollama import OllamaModelSwitchboard

            adapter, selection = OllamaModelSwitchboard().adapter_for("fast")
            logger.debug("intent parser routed to Ollama fast nerve: %s", selection.model)
            # Health probe
            try:
                healthy = adapter.bridge.health_check()
            except Exception:
                healthy = False
            if not healthy:
                adapter = None
        except Exception as e:
            logger.debug("adapter construction failed: %s", e)
            adapter = None
    _LLM_ADAPTER_CACHE["adapter"] = adapter
    return adapter


def _llm_parse(text: str) -> Optional[Dict[str, Any]]:
    """
    Ask Ollama to classify the user's text into one of the actions in
    ACTION_SCHEMA. Returns None if no adapter is available or parsing
    fails — caller falls back to keyword parse.
    """
    adapter = _get_llm_adapter()
    if adapter is None:
        return None
    try:
        schema_text = "\n".join(
            f"  {name}: {spec['description']} fields={list(spec['fields'].keys())}"
            for name, spec in ACTION_SCHEMA.items()
        )
        system_msg = (
            "You are Aureon's intent parser. The user speaks natural "
            "language; you produce one JSON object of the form "
            '{"action": "<one of the action names>", "args": {...}}. '
            "Choose the single action that best matches. Do NOT add "
            "commentary. Do NOT wrap in code fences. Respond with the "
            "JSON only.\n\n"
            "Available actions:\n"
            f"{schema_text}"
        )
        messages = [{"role": "user", "content": text}]
        reply = adapter.prompt(
            messages=messages,
            system=system_msg,
            max_tokens=256,
            temperature=0.1,
            format="json",
        )
        text_out = getattr(reply, "text", None) or str(reply)
        if not text_out:
            return None
        # Extract first top-level JSON object.
        i = text_out.find("{")
        if i < 0:
            return None
        depth = 0
        end = -1
        for j, ch in enumerate(text_out[i:], start=i):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        if end < 0:
            return None
        parsed = json.loads(text_out[i:end])
        if not isinstance(parsed, dict) or "action" not in parsed:
            return None
        parsed.setdefault("args", {})
        return parsed
    except Exception as e:
        logger.debug("LLM parse failed: %s", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch — wire parsed intents into the running stack
# ─────────────────────────────────────────────────────────────────────────────

def _coerce_int(value: Any, default: int) -> int:
    """Pull the first integer out of anything. Falls back to default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return default  # bools sneak through isinstance(value, int)
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value)
    m = re.search(r"-?\d+", s)
    if m:
        try:
            return int(m.group(0))
        except Exception:
            return default
    return default


def _coerce_float(value: Any, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value)
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if m:
        try:
            return float(m.group(0))
        except Exception:
            return default
    return default


class IntentDispatcher:
    """
    Calls the existing singletons. Nothing new here — this is just the
    routing layer that converts a parsed {action, args} into the right
    API call or bus publish.
    """

    def __init__(self) -> None:
        self._loop = None
        self._bus = None
        self._integrator = None
        self._refinement = None
        self._introspection = None
        self._narrator = None
        self._architect = None

    def _lazy(self) -> None:
        if self._bus is None:
            try:
                from aureon.core.aureon_thought_bus import get_thought_bus
                self._bus = get_thought_bus()
            except Exception:
                self._bus = None
        if self._loop is None:
            try:
                from aureon.core.aureon_cognitive_authoring_loop import get_authoring_loop
                self._loop = get_authoring_loop()
            except Exception:
                self._loop = None
        if self._integrator is None:
            try:
                from aureon.core.aureon_code_integrator import get_code_integrator
                self._integrator = get_code_integrator()
            except Exception:
                self._integrator = None
        if self._refinement is None:
            try:
                from aureon.core.aureon_self_refinement_loop import get_refinement_loop
                self._refinement = get_refinement_loop()
            except Exception:
                self._refinement = None
        if self._introspection is None:
            try:
                from aureon.core.aureon_self_introspection import get_self_introspection
                self._introspection = get_self_introspection()
            except Exception:
                self._introspection = None
        if self._narrator is None:
            try:
                from aureon.core.aureon_narrative import get_narrator
                self._narrator = get_narrator()
            except Exception:
                self._narrator = None

    def dispatch(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        self._lazy()
        action = str(intent.get("action") or "").strip().lower()
        args = intent.get("args") or {}
        if not isinstance(args, dict):
            args = {}

        if action in ("quit", "exit"):
            return {"ok": True, "action": action, "stop": True}

        if action == "help":
            lines = []
            for name, spec in ACTION_SCHEMA.items():
                flds = ", ".join(spec["fields"].keys()) or "-"
                lines.append(f"  {name:<12}  {spec['description']}  [{flds}]")
            return {"ok": True, "help": "\n".join(lines)}

        if action == "status":
            if self._loop is None:
                return {"ok": False, "error": "authoring loop unavailable"}
            return {"ok": True, "status": self._loop.get_status()}

        if action == "reachability":
            if self._introspection is None:
                return {"ok": False, "error": "introspection unavailable"}
            r = self._introspection.reachability()
            return {"ok": True, "reach_ratio": r["reach_ratio"],
                    "reachable_count": r["reachable_count"],
                    "dormant_count": r["dormant_count"],
                    "all_count": r["all_count"],
                    "top_dormant_packages": dict(list(r["dormant_by_package"].items())[:8])}

        if action == "bootstrap":
            return self._submit({"kind": "bootstrap"})

        if action == "execute":
            return self._submit({"kind": "execute", "name": str(args.get("name") or "")})

        if action == "pending":
            if self._integrator is None:
                return {"ok": False, "error": "integrator unavailable"}
            return {"ok": True, "pending": self._integrator.list_pending()}

        if action == "confirm":
            if self._integrator is None:
                return {"ok": False, "error": "integrator unavailable"}
            return self._integrator.confirm_edit(str(args.get("pending_id") or ""))

        if action == "reject":
            if self._integrator is None:
                return {"ok": False, "error": "integrator unavailable"}
            return self._integrator.reject_edit(
                str(args.get("pending_id") or ""),
                reason=str(args.get("reason") or ""),
            )

        if action == "score":
            if self._refinement is None:
                return {"ok": False, "error": "refinement loop unavailable"}
            return self._refinement.score(
                applied_id=str(args.get("applied_id") or ""),
                score=_coerce_float(args.get("score"), 0.0),
                comment=str(args.get("comment") or ""),
            )

        if action == "backtest":
            if self._refinement is None:
                return {"ok": False, "error": "refinement loop unavailable"}
            return self._refinement.backtest(
                applied_id=str(args.get("applied_id") or ""),
                mode=str(args.get("mode") or "fast"),
            )

        if action == "narrate":
            if self._narrator is None:
                return {"ok": False, "error": "narrator unavailable"}
            return {"ok": True, "stories": self._narrator.print_recent(
                limit=_coerce_int(args.get("limit"), 10))}

        if action == "wheel":
            if self._narrator is None:
                return {"ok": False, "error": "narrator unavailable"}
            return {"ok": True, "wheel": self._narrator.wheel_delta(
                window=_coerce_int(args.get("window"), 20))}

        if action == "digest":
            if self._refinement is None:
                return {"ok": False, "error": "refinement loop unavailable"}
            return {"ok": True, "digest": self._refinement.consciousness_digest(
                window=_coerce_int(args.get("window"), 50))}

        if action == "wire":
            tgt = str(args.get("target_module") or "").strip()
            if not tgt:
                return {"ok": False, "error": "target_module required"}
            return self._publish_research({
                "kind": "research",
                "intent": "wire_in_dormant",
                "target_module": tgt,
                "rationale": f"User intent: wire {tgt} into ICS.",
                "self_check_origin": "user_intent",
                "severity": 0.6,
            })

        if action == "fix":
            tgt = str(args.get("target_path_or_module") or "").strip()
            note = str(args.get("note") or "")
            return self._publish_research({
                "kind": "research",
                "intent": "user_fix_request",
                "target_path": tgt,
                "rationale": note or f"User-requested fix for {tgt}",
                "self_check_origin": "user_intent",
                "severity": 0.5,
            })

        if action == "edit":
            if self._integrator is None:
                return {"ok": False, "error": "integrator unavailable"}
            return self._integrator.propose_edit(
                target_path=str(args.get("path") or ""),
                old_text=str(args.get("old_text") or ""),
                new_text=str(args.get("new_text") or ""),
                rationale=str(args.get("rationale") or "user intent"),
            )

        if action == "ab":
            if self._integrator is None:
                return {"ok": False, "error": "integrator unavailable"}
            return self._integrator.propose_comparison(
                target_path=str(args.get("path") or ""),
                old_text=str(args.get("old_text") or ""),
                aureon_new_text=str(args.get("aureon_new_text") or ""),
                human_new_text=str(args.get("human_new_text") or ""),
                rationale=str(args.get("rationale") or "user intent"),
            )

        return {"ok": False, "error": f"unknown action: {action}"}

    def _submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._loop is None:
            return {"ok": False, "error": "authoring loop unavailable"}
        return self._loop.submit(payload)

    def _publish_research(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self._bus is None:
            return {"ok": False, "error": "thought bus unavailable"}
        try:
            self._bus.publish("authoring.research", payload, source="intent_terminal")
            return {"ok": True, "published": "authoring.research",
                    "intent": payload.get("intent"),
                    "target": payload.get("target_module") or payload.get("target_path")}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Terminal REPL
# ─────────────────────────────────────────────────────────────────────────────

_BANNER = (
    "Aureon Intent Terminal\n"
    "  Say what you want. aureon figures out the action.\n"
    "  'help' for the action list, 'quit' to leave.\n"
)


def _render(result: Dict[str, Any]) -> str:
    # Keep help + stories + wheel human-friendly; everything else JSON.
    if "help" in result:
        return "actions:\n" + result["help"]
    if "stories" in result:
        return result["stories"]
    return json.dumps(result, indent=2, default=str)


def repl(use_llm: bool = True) -> None:
    print(_BANNER, flush=True)
    dispatcher = IntentDispatcher()
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        intent = None
        if use_llm:
            intent = _llm_parse(text)
        if intent is None:
            intent = _keyword_parse(text)
        print(f"[intent] {intent.get('action')} args={intent.get('args')}", flush=True)
        result = dispatcher.dispatch(intent)
        print(_render(result), flush=True)
        if result.get("stop"):
            break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Aureon intent terminal.")
    parser.add_argument("--no-llm", action="store_true",
                        help="Disable LLM parsing; keyword-only.")
    parser.add_argument("--say", default=None,
                        help="Single non-interactive intent to dispatch, then exit.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    )

    if args.say:
        dispatcher = IntentDispatcher()
        intent = (None if args.no_llm else _llm_parse(args.say)) or _keyword_parse(args.say)
        print(f"[intent] {intent.get('action')} args={intent.get('args')}", flush=True)
        result = dispatcher.dispatch(intent)
        print(_render(result))
    else:
        repl(use_llm=not args.no_llm)
