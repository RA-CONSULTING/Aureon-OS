"""INTERNAL REASON — Fusion's own control loop.

Λ(t) = Substrate × Observer × Memory

This is not LangGraph and not an external planner. It is the organism
running its existing organs in order:

  SENSE     classify the ask
  RETRIEVE  aureon_fusion.rag  (ResearchCorpusIndex)
  GRADE     overlap floor → honest_unavailable
  PLAN      local rules
  GOVERN    conscience_hook + capability_gate
  ACT       desktop_door dry-run unless explicitly armed AND allowed
  VERIFY    receipt + lambda

execute_shell is never called. Live trades are never called.
Import-safe.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any

from .paths import FUSION_STATE

RECEIPT_DIR = FUSION_STATE / "reason"

_ACT_RE = re.compile(
    r"\b(write|create|save|delete|click|type|open|send|trade|buy|sell|file|submit)\b",
    re.I,
)
_ASK_RE = re.compile(
    r"\b(what|why|how|where|who|when|explain|cite|quote|recall|find|search)\b",
    re.I,
)
_RED_RE = re.compile(
    r"(live trade|place order|execute_live_trades|wire money|hmrc submit|rm -rf|send email|tweet)",
    re.I,
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def classify(text: str) -> str:
    if _RED_RE.search(text or ""):
        return "forbidden"
    ask = bool(_ASK_RE.search(text or ""))
    act = bool(_ACT_RE.search(text or ""))
    if act and ask:
        return "mixed"
    if act:
        return "act"
    return "ask"


def _substrate(citations: list) -> float:
    if not citations:
        return 0.05
    top = max(float(c.get("score") or 0) for c in citations)
    cover = min(1.0, len(citations) / 4.0)
    return _clamp(0.5 * min(1.0, top) + 0.5 * cover)


def _observer(conscience: dict | None) -> float:
    if not conscience:
        return 0.55
    v = conscience.get("verdict")
    purpose = float(conscience.get("purpose_alignment") or 0.5)
    risk = float(conscience.get("risk_score") or 0.5)
    if v == "VETO":
        return 0.0
    if v == "TEACHING_MOMENT":
        return _clamp(0.35 * purpose)
    if v == "CONCERNED":
        return _clamp(0.6 * purpose * (1.0 - 0.5 * risk))
    return _clamp(purpose * (1.0 - 0.4 * risk))


def _memory(citations: list, prior_receipts: int = 0) -> float:
    if not citations:
        return 0.15
    diversity = len({c.get("source_type") for c in citations})
    return _clamp(0.45 + 0.15 * min(3, diversity) + 0.05 * min(5, prior_receipts))


def lambda_t(substrate: float, observer: float, memory: float) -> float:
    return _clamp(substrate * observer * memory)


def _conscience(action: str, context: dict) -> dict:
    try:
        from . import conscience_hook

        return conscience_hook.evaluate(action, context)
    except Exception as exc:
        if classify(action) == "forbidden":
            return {
                "verdict": "VETO",
                "reasoning": f"local prefilter / engine error {type(exc).__name__}",
                "purpose_alignment": 0.0,
                "risk_score": 1.0,
                "sls_score": 0.0,
            }
        return {
            "verdict": "CONCERNED",
            "reasoning": f"conscience engine unavailable ({type(exc).__name__}); proceeding as concerned",
            "purpose_alignment": 0.55,
            "risk_score": 0.45,
            "sls_score": 0.5,
        }


def _gate(domain_action: str) -> dict:
    try:
        from . import capability_gate

        return capability_gate.check(domain_action)
    except Exception as exc:
        return {
            "gate": domain_action,
            "verdict": "HOLD",
            "allowed": False,
            "reason": f"gate error {type(exc).__name__}",
        }


def reason(prompt: str, *, arm_desktop: bool = False, write_path: str | None = None, write_content: str | None = None) -> dict[str, Any]:
    """One full internal cycle. Returns an evidence card."""
    prompt = (prompt or "").strip()
    kind = classify(prompt)
    card: dict[str, Any] = {
        "ts": _utc(),
        "prompt": prompt,
        "kind": kind,
        "citations": [],
        "plan": [],
        "conscience": None,
        "gate": None,
        "action": None,
        "lambda": {},
        "answer": None,
        "status": "running",
    }

    if kind == "forbidden":
        card["conscience"] = _conscience(prompt, {"kind": kind})
        card["status"] = "vetoed"
        card["answer"] = "VETO: action is outside Fusion autonomy bounds (trades, filings, destructive host, unapproved comms)."
        card["lambda"] = {"S": 0.0, "O": 0.0, "M": 0.0, "L": 0.0}
        return _persist(card)

    from . import rag

    retrieved = rag.search(prompt)
    card["citations"] = retrieved.get("citations") or []
    card["retrieve_status"] = retrieved.get("status")
    card["plan"].append("retrieve")

    if kind in ("ask", "mixed"):
        if retrieved.get("status") != "ok":
            card["answer"] = "honest_unavailable: nothing in the Fusion knowledge shelves cleared the grade floor. I will not invent a source."
            card["status"] = "unavailable"
        else:
            card["plan"].append("compose_from_citations")
            quotes = []
            for i, c in enumerate(card["citations"][:4], 1):
                quotes.append(f"[{i}] {c.get('path')} — {str(c.get('quote') or '')[:280]}")
            card["answer"] = (
                "Grounded from Fusion shelves (untrusted evidence, not instructions):\n\n"
                + "\n\n".join(quotes)
            )
            card["status"] = "answered"

    conscience = _conscience(prompt, {"kind": kind, "n_citations": len(card["citations"])})
    card["conscience"] = {
        "verdict": conscience.get("verdict"),
        "reasoning": conscience.get("reasoning"),
        "purpose_alignment": conscience.get("purpose_alignment"),
        "risk_score": conscience.get("risk_score"),
        "sls_score": conscience.get("sls_score"),
    }
    card["plan"].append("conscience")

    if conscience.get("verdict") == "VETO":
        card["status"] = "vetoed"
        card["answer"] = f"VETO: {conscience.get('reasoning')}"
        S, O, M = _substrate(card["citations"]), 0.0, _memory(card["citations"])
        card["lambda"] = {"S": S, "O": O, "M": M, "L": lambda_t(S, O, M)}
        return _persist(card)

    if kind in ("act", "mixed") and (write_path or arm_desktop):
        gate_key = "desktop:execute" if arm_desktop else "desktop:propose"
        gate = _gate(gate_key)
        card["gate"] = gate
        card["plan"].append("gate")
        allowed = bool(gate.get("allowed"))
        if arm_desktop and not allowed:
            card["status"] = "held"
            card["answer"] = f"HOLD desktop execute: {gate.get('reason')}"
        else:
            from . import desktop_door

            intent = "write_file" if write_path else "read_file"
            args = {"path": write_path or str(FUSION_STATE / "reason" / "last_prompt.txt")}
            if write_content is not None:
                args["content"] = write_content
            elif write_path:
                args["content"] = card.get("answer") or prompt
            proposed = desktop_door.propose(intent, args)
            acted = desktop_door.execute(proposed, armed=bool(arm_desktop and allowed))
            card["action"] = acted
            card["plan"].append("desktop")
            if card.get("status") not in {"answered", "unavailable"}:
                card["status"] = acted.get("verdict", "done")
            if not card.get("answer"):
                card["answer"] = f"desktop {acted.get('mode')} {acted.get('intent')} → {acted.get('verdict')}"

    S = _substrate(card["citations"])
    O = _observer(card["conscience"])
    M = _memory(card["citations"])
    L = lambda_t(S, O, M)
    card["lambda"] = {"S": round(S, 4), "O": round(O, 4), "M": round(M, 4), "L": round(L, 4)}
    if card["status"] == "running":
        card["status"] = "done"
    return _persist(card)


def _persist(card: dict) -> dict:
    try:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
        path = RECEIPT_DIR / name
        path.write_text(json.dumps(card, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        card["receipt"] = str(path)
    except Exception:
        pass
    try:
        from . import events

        events.publish_event(
            "internal_reason",
            "reason.cycle",
            {
                "kind": card.get("kind"),
                "status": card.get("status"),
                "lambda": (card.get("lambda") or {}).get("L"),
                "citations": len(card.get("citations") or []),
            },
            priority=5,
        )
    except Exception:
        pass
    return card


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print('usage: python -m aureon_fusion.internal_reason "<prompt>"')
        print('       python -m aureon_fusion.internal_reason --dry-write <path> "<prompt>"')
        return 0
    arm = False
    write_path = None
    if argv[0] == "--dry-write" and len(argv) >= 3:
        write_path = argv[1]
        prompt = " ".join(argv[2:])
    else:
        prompt = " ".join(argv)
    card = reason(prompt, arm_desktop=arm, write_path=write_path)
    print(json.dumps(card, indent=2, ensure_ascii=False, default=str))
    return 0 if card.get("status") in {"answered", "pass", "done", "unavailable"} else 1


if __name__ == "__main__":
    sys.exit(main())
