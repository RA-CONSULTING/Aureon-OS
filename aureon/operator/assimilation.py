"""
Controlled Assimilation — only the realized, validated increment joins the collective.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The write-back half of the Borg clause. Task-local acquisition is free —
whatever the tools found may be used to finish THIS cake. But the collective
memory is gated: a turn's knowledge record is appended to the assimilation
ledger ONLY when every check holds:

* **realized**  — the answer materialized (Film-Reel ledger says so);
* **approved**  — the conscience did not veto and no boundary blocked it;
* **complete**  — the bake seal is ``complete: true``;
* **status ok** — the turn was ``ok`` (never an ``[ERROR]``/fault record).

A refused write-back is NAMED (which check failed), never silent — and
nothing parked, vetoed, or half-baked ever enters the collective. There is
no unconstrained assimilation.

The ledger lives in ``state/`` (runtime memory, gitignored) and stores
knowledge REFERENCES — trace id, prompt digest, knowledge reach, source
paths, tools consulted — an auditable record of what the organism actually
learned from, never raw scraped content.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("aureon.operator.assimilation")

__all__ = ["assimilate", "ledger_path"]

_REPO_ROOT = Path(__file__).resolve().parents[2]


def ledger_path() -> Path:
    """The assimilation ledger location (env-overridable for tests)."""
    override = os.environ.get("AUREON_ASSIMILATION_PATH", "").strip()
    if override:
        return Path(override)
    return _REPO_ROOT / "state" / "assimilated_knowledge.jsonl"


def assimilate(res: Any) -> Dict[str, Any]:
    """Gate one turn's knowledge record into the collective — or refuse, named.

    Returns ``{assimilated, checks, reason?}``. Append-only; a write failure
    is reported honestly, never masked as success.
    """
    act = res.actualization or {}
    bake = res.bake or {}
    checks = {
        "realized": act.get("answer") == "realized",
        "approved": (not res.blocked
                     and res.conscience_verdict != "VETO"),
        "complete": bake.get("complete") is True,
        "status_ok": res.status() == "ok",
    }
    if not all(checks.values()):
        failed = sorted(k for k, v in checks.items() if not v)
        return {"assimilated": False, "checks": checks,
                "reason": (f"write-back refused: {', '.join(failed)} — nothing "
                           "parked, vetoed, or half-baked enters the collective")}

    env = res.envelope()
    record = {
        "ts": round(time.time(), 3),
        "trace_id": res.trace_id,
        "prompt_sha": hashlib.sha256((res.prompt or "").encode("utf-8")).hexdigest()[:16],
        "knowledge_reach": env.get("knowledge_reach", []),
        "sources": [s.get("path", "") for s in env.get("sources", [])],
        "tools_consulted": sorted({t.tool for t in res.tool_calls if not t.blocked}),
        "grounded": bool(res.grounded),
    }
    try:
        path = ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except Exception as exc:  # noqa: BLE001 — a failed write is reported, never masked
        logger.debug("assimilation write failed: %s", exc)
        return {"assimilated": False, "checks": checks,
                "reason": f"ledger write failed: {exc}"}
    return {"assimilated": True, "checks": checks}
