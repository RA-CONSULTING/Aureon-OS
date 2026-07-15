"""
ApprovalQueue — the director's desk: Aureon prepares the big plays, Gary decides.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Aureon runs the reversible day-to-day itself. But the big, irreversible plays — a
live trade, moving money, submitting a grant, a reply that leaves the building —
belong to the director. This is where they wait for him.

The organism **prepares** each such move and `propose()`s it here; Gary reviews it
(console, watch, or by email reply) and `decide()`s approve or reject. That decision
is **recorded** — it is the human gate — and it is *all* this module does. It never
executes the move. By construction there is **no consumer** of the queue that fires a
live trade / payment / filing / outbound email: approving only flips the item's status
to ``approved``, leaving the actual irreversible execution to Gary's deliberate hand
(or a live executor he arms himself, separately and explicitly). Aureon runs full
speed up to the edge of consequence; the human blesses the step across it.

Backed by an append-only JSONL log (`state/approvals.jsonl`) via ``bus_trace`` —
atomic, bounded, multi-writer-safe, never-raises. Current state is the fold of the
append log (latest status per id). Guarded throughout.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

logger = logging.getLogger("aureon.core.approval_queue")

_TRACE = "approvals"
# When this many proposals already await the director, the organism stops piling on
# more — it senses its own backlog and waits for the desk to clear (backpressure).
_DEFAULT_MAX_PENDING = 5
_KINDS = {"trade", "email", "payment", "filing", "grant", "deal", "other"}
_OPEN = "pending"
_DECISIONS = {"approve": "approved", "reject": "rejected"}


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class ApprovalQueue:
    """Prepare → propose → (human) decide → record. Never executes."""

    def __init__(self, *, cap: int = 500) -> None:
        self._cap = cap

    # ── propose (Aureon prepares a big play; nothing executes) ──────────────
    def propose(self, kind: str, summary: str, params: dict[str, Any] | None = None,
                prepared_by: str = "soul", *, risk: str = "high") -> str | None:
        """Enqueue one PENDING proposal for the human. Returns its id, or None if a
        matching pending item already exists (dedup) or on any error. Never executes."""
        try:
            k = kind if kind in _KINDS else "other"
            text = str(summary or "").strip()[:400] or "(no summary)"
            # dedup against open items of the same kind + summary
            for item in self.pending():
                if item.get("kind") == k and item.get("summary") == text:
                    return None
            item_id = _new_id()
            self._append({
                "event": "proposed", "id": item_id, "kind": k, "summary": text,
                "params": dict(params or {}), "prepared_by": str(prepared_by),
                "risk": str(risk), "requires_human": True, "status": _OPEN,
                "note": "", "created_at": time.time(), "decided_at": None,
            })
            return item_id
        except Exception as exc:  # noqa: BLE001 — a desk that jams never crashes the organism
            logger.debug("propose skipped: %s", exc)
            return None

    # ── decide (the human gate; records only, never executes) ───────────────
    def decide(self, item_id: str, decision: str, approver: str = "gary",
               note: str = "") -> dict[str, Any] | None:
        """Record the human's approve/reject. This is the gate — it does NOT execute
        the move. Returns the updated item, or None if unknown/already decided."""
        try:
            status = _DECISIONS.get(str(decision).strip().lower())
            if status is None:
                return None
            item = self.get(item_id)
            if item is None or item.get("status") != _OPEN:
                return None
            self._append({
                "event": "decided", "id": item_id, "kind": item.get("kind"),
                "summary": item.get("summary"), "params": item.get("params"),
                "prepared_by": item.get("prepared_by"), "risk": item.get("risk"),
                "requires_human": True, "status": status, "note": str(note)[:400],
                "approver": str(approver), "created_at": item.get("created_at"),
                "decided_at": time.time(),
            })
            return self.get(item_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("decide skipped: %s", exc)
            return None

    # ── read (fold the append log to latest-per-id) ─────────────────────────
    def _fold(self) -> dict[str, dict[str, Any]]:
        from aureon.core.bus_trace import read_trace

        latest: dict[str, dict[str, Any]] = {}
        for row in read_trace(_TRACE, limit=self._cap):
            rid = row.get("id")
            if rid:
                latest[str(rid)] = row
        return latest

    def get(self, item_id: str) -> dict[str, Any] | None:
        return self._fold().get(str(item_id))

    def pending(self) -> list[dict[str, Any]]:
        items = [r for r in self._fold().values() if r.get("status") == _OPEN]
        return sorted(items, key=lambda r: r.get("created_at") or 0.0)

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        items = sorted(self._fold().values(), key=lambda r: r.get("created_at") or 0.0, reverse=True)
        return items[: max(1, limit)]

    # ── the organism senses its own desk (backpressure) ────────────────────
    def _max_pending(self) -> int:
        try:
            return max(1, int(os.environ.get("AUREON_APPROVAL_MAX_PENDING", "") or _DEFAULT_MAX_PENDING))
        except (TypeError, ValueError):
            return _DEFAULT_MAX_PENDING

    def backlog(self) -> dict[str, Any]:
        """How much the director's desk is holding — the organism's read of being
        blocked on the human. ``blocked`` is the backpressure signal."""
        pend = self.pending()
        now = time.time()
        oldest = min((float(r.get("created_at") or now) for r in pend), default=now)
        cap = self._max_pending()
        return {"pending_count": len(pend), "oldest_age_s": round(now - oldest, 1),
                "max_pending": cap, "blocked": len(pend) >= cap}

    def is_backpressured(self) -> bool:
        """True when the desk is full — prepare no more until the director clears it."""
        try:
            return bool(self.backlog()["blocked"])
        except Exception:  # noqa: BLE001 — never block the organism on a read error
            return False

    def summary(self) -> dict[str, Any]:
        folded = list(self._fold().values())
        counts: dict[str, int] = {}
        for r in folded:
            s = str(r.get("status") or "?")
            counts[s] = counts.get(s, 0) + 1
        return {"pending": self.pending(), "recent": self.recent(20),
                "counts": counts, "total": len(folded), "backlog": self.backlog(),
                "note": "records the human decision; never executes the live move"}

    def _append(self, payload: dict[str, Any]) -> None:
        from aureon.core.bus_trace import append_trace

        append_trace(_TRACE, payload, cap=self._cap)


_queue: ApprovalQueue | None = None


def get_approval_queue() -> ApprovalQueue:
    """Process-global approval-queue singleton (the director's desk)."""
    global _queue
    if _queue is None:
        _queue = ApprovalQueue()
    return _queue


__all__ = ["ApprovalQueue", "get_approval_queue"]
