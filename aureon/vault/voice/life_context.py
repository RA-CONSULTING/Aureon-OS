"""
LifeContext — the operator's life, legible to every persona
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WorldSense covers the cosmos and the market; LifeContext covers *you*.
It holds the operator-supplied events, commitments, concerns, and
interests that personas scan for opportunities to help.

If you add a ``LifeEvent`` with title "wedding on May 12", the Artist
sees it and wants to design an invitation; the Mystic sees it and wants
to compose a 528 Hz blessing; the Engineer sees it and wants to build
an RSVP form; the Philosopher sees it and wants to ask what the
ceremony is really for. Each persona's ``scan_for_opportunity`` hook
turns a known life event into a concrete goal text that flows into
the existing goal pipeline.

Events persist as vault cards (``life.event`` topic) so:
  * mesh gossip carries them to every connected machine
  * the Obsidian mirror writes them to disk as markdown notes
  * ``AureonVault.fingerprint()`` shifts when events change, so the
    unified-collapse seed registers the change

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger("aureon.vault.voice.life_context")

_LIFE_EVENT_TOPIC: str = "life.event"
LIFE_CONTEXT_RELEASE_HOLD = (
    "life_context_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class LifeEvent:
    """One operator-supplied life event the personas can act on."""

    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    description: str = ""
    date: str = ""                       # free text — "May 12 2026", "next Friday", etc.
    tags: List[str] = field(default_factory=list)
    status: str = "active"               # active | archived | completed
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "tags": list(self.tags),
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LifeEvent":
        return cls(
            event_id=str(d.get("event_id") or uuid.uuid4().hex[:8]),
            title=str(d.get("title") or ""),
            description=str(d.get("description") or ""),
            date=str(d.get("date") or ""),
            tags=[str(t) for t in (d.get("tags") or [])],
            status=str(d.get("status") or "active"),
            created_at=float(d.get("created_at") or time.time()),
        )

    @property
    def search_blob(self) -> str:
        """All text associated with the event, lowercased, for keyword scans."""
        return " ".join([
            self.title.lower(),
            self.description.lower(),
            self.date.lower(),
            " ".join(t.lower() for t in self.tags),
        ]).strip()


# ─────────────────────────────────────────────────────────────────────────────
# LifeContext
# ─────────────────────────────────────────────────────────────────────────────


class LifeContext:
    """In-process store of the operator's life events.

    Thread-safe and vault-persistent: each ``add`` writes a ``life.event``
    card. Rebuilding a LifeContext in a new process from the existing
    vault is a matter of calling ``load_from_vault(vault)`` which scans
    cards with that source topic.
    """

    def __init__(self, vault: Any = None):
        self._lock = threading.RLock()
        self._events: Dict[str, LifeEvent] = {}
        self._vault = vault

    # ─── mutation ────────────────────────────────────────────────────────

    def add(
        self,
        title: str,
        *,
        description: str = "",
        date: str = "",
        tags: Optional[Sequence[str]] = None,
    ) -> LifeEvent:
        if self._vault is not None:
            raise RuntimeError(LIFE_CONTEXT_RELEASE_HOLD)
        title = str(title or "").strip()
        if not title:
            raise ValueError("LifeEvent title is required")
        tags = list(tags or [])
        tags.extend(self._auto_extract_tags(title + " " + description))
        # Dedupe tags, preserve order.
        seen: set = set()
        ordered: List[str] = []
        for t in tags:
            tl = t.lower().strip()
            if tl and tl not in seen:
                seen.add(tl)
                ordered.append(tl)
        event = LifeEvent(title=title, description=description, date=date, tags=ordered)
        with self._lock:
            self._events[event.event_id] = event
        self._persist(event)
        return event

    def remove(self, event_id: str) -> bool:
        with self._lock:
            return self._events.pop(event_id, None) is not None

    def archive(self, event_id: str) -> bool:
        if self._vault is not None:
            raise RuntimeError(LIFE_CONTEXT_RELEASE_HOLD)
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return False
            event.status = "archived"
        self._persist(event)
        return True

    def complete(self, event_id: str) -> bool:
        if self._vault is not None:
            raise RuntimeError(LIFE_CONTEXT_RELEASE_HOLD)
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return False
            event.status = "completed"
        self._persist(event)
        return True

    # ─── read ────────────────────────────────────────────────────────────

    def active(self) -> List[LifeEvent]:
        with self._lock:
            return [e for e in self._events.values() if e.status == "active"]

    def all(self) -> List[LifeEvent]:
        with self._lock:
            return list(self._events.values())

    def get(self, event_id: str) -> Optional[LifeEvent]:
        with self._lock:
            return self._events.get(event_id)

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)

    # ─── vault integration ───────────────────────────────────────────────

    def _persist(self, event: LifeEvent) -> None:
        if self._vault is None:
            return
        raise RuntimeError(LIFE_CONTEXT_RELEASE_HOLD)
        if not hasattr(self._vault, "ingest"):
            return
        try:
            self._vault.ingest(topic=_LIFE_EVENT_TOPIC, payload=event.to_dict())
        except Exception as e:
            logger.debug("LifeContext: vault persist failed: %s", e)

    def load_from_vault(self, vault: Any) -> int:
        """Rebuild the in-memory event table from vault cards on the
        ``life.event`` topic. Returns the number of events loaded."""
        raise RuntimeError(LIFE_CONTEXT_RELEASE_HOLD)
        self._vault = vault
        if vault is None:
            return 0
        contents = getattr(vault, "_contents", None)
        if not contents:
            return 0
        count = 0
        with self._lock:
            self._events.clear()
            for card in contents.values():
                if getattr(card, "source_topic", "") != _LIFE_EVENT_TOPIC:
                    continue
                payload = getattr(card, "payload", {}) or {}
                try:
                    event = LifeEvent.from_dict(payload)
                except Exception:
                    continue
                self._events[event.event_id] = event
                count += 1
        return count

    # ─── auto-tagging — keyword heuristics ───────────────────────────────

    _TAG_KEYWORDS = {
        "wedding": ("wedding", "marriage", "ceremony"),
        "birthday": ("birthday", "birth day"),
        "anniversary": ("anniversary",),
        "gift": ("gift", "present"),
        "design": ("design", "invitation", "poster"),
        "travel": ("travel", "trip", "flight", "journey"),
        "interview": ("interview", "job", "hiring"),
        "health": ("surgery", "doctor", "hospital", "illness", "recovery"),
        "grief": ("funeral", "grief", "loss", "passed", "memorial"),
        "family": ("mother", "father", "son", "daughter", "sister", "brother",
                   "partner", "wife", "husband"),
        "celebration": ("party", "celebration", "toast"),
        "creative": ("song", "album", "painting", "novel", "film", "game"),
        "work": ("deadline", "client", "pitch", "launch", "proposal"),
        "learning": ("course", "exam", "thesis", "dissertation"),
        "spiritual": ("retreat", "meditation", "pilgrimage"),
    }

    @classmethod
    def _auto_extract_tags(cls, text: str) -> List[str]:
        t = (text or "").lower()
        hits: List[str] = []
        for tag, keywords in cls._TAG_KEYWORDS.items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", t):
                    hits.append(tag)
                    break
        return hits


__all__ = [
    "LIFE_CONTEXT_RELEASE_HOLD",
    "LifeEvent",
    "LifeContext",
]
