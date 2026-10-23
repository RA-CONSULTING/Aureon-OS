"""🧺 STASH POCKETS — per-goal scratch pads that crystallize into the dataset.

Fusion-native port of the upstream read-only reference
aureon-os-upstream/aureon/queen/queen_stash_pockets.py (pure local — zero
network). During a goal the Queen dumps intermediate findings into a small
pocket; when the pocket MATURES (enough entries or explicitly closed) its
content crystallizes into KnowledgeDataset fragments instead of
evaporating — the research faculty's output becomes retained memory.

Fusion adaptations vs upstream:
  • Pockets persist under state/stash_pockets/<pocket_id>.json so a
    restart never loses open scratch pads.
  • Crystallization appends defensively to
    state/queen_mind/knowledge_dataset.json (read-modify-write, atomic
    tmp+rename, fragments capped at 2000). At cap, fragments fall over to
    state/queen_mind/stash_crystallized.jsonl (append-only, never lost).
  • Every crystallized fragment is provenance-tagged: "stash_pocket",
    its goal, and its creation timestamp.
  • No ElephantMemory / ThoughtBus / interpreter couplings (those organs
    live upstream); close() simply marks the pocket closed — mature_pockets()
    performs the crystallization.

Doctrine:
  • Pure local. Zero HTTP. Zero aureon imports — nothing here needs them.
  • NEVER raises: every public call is fail-closed. A corrupt dataset or
    a missing state dir degrades to an honest empty result, never a crash
    in the Queen's cycle.
  • Atomic writes everywhere (tmp + os.replace).

API:
    create_pocket(goal)                 -> pocket dict
    add_finding(pocket_id, text)        -> entry dict | None
    mature_pockets()                    -> list[crystallized fragment dicts]
    list_pockets()                      -> list[pocket dicts]

CLI:
    python -m aureon_fusion.stash_pockets demo    # pocket lifecycle + crystallization
    python -m aureon_fusion.stash_pockets list    # persisted pockets
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import FUSION_STATE

logger = logging.getLogger("aureon_fusion.stash_pockets")

STATE_DIR = FUSION_STATE / "stash_pockets"
QUEEN_MIND = FUSION_STATE / "queen_mind"
KNOWLEDGE_DATASET = QUEEN_MIND / "knowledge_dataset.json"
STASH_CRYSTALLIZED = QUEEN_MIND / "stash_crystallized.jsonl"

# A pocket crystallizes once it holds this many findings (or is closed).
MATURITY_MIN_ENTRIES = 3
# Dataset fragment cap — beyond this, crystallization falls over to the
# jsonl overflow file so research output is never silently dropped.
MAX_DATASET_FRAGMENTS = 2000


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)


def _read_json_defensive(path: Path, default: Any) -> Any:
    """Read JSON; any failure (missing, corrupt, partial write) -> default."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.debug("read %s failed: %s", path, exc)
        return default


# ─────────────────────────────────────────────────────────────────────────────
# StashEntry — one finding
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class StashEntry:
    """One dumped finding during a goal."""

    key: str = ""
    value: str = ""
    tags: List[str] = field(default_factory=list)
    phase_angle: float = 0.0    # math angle protocol — radians [0, 2π]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# StashPocket — one per goal
# ─────────────────────────────────────────────────────────────────────────────


class StashPocket:
    """A scratch pad scoped to a single goal. Findings are dumped here;
    on maturity the pocket crystallizes into dataset fragments."""

    def __init__(self, goal_id: str, owner: str = "queen",
                 pocket_id: Optional[str] = None):
        self.goal_id = goal_id
        self.owner = owner
        self.pocket_id = pocket_id or uuid.uuid4().hex[:10]
        self.entries: List[StashEntry] = []
        self.opened_at = time.time()
        self.closed_at: Optional[float] = None
        self.crystallized_at: Optional[float] = None
        self.crystals: int = 0
        self._lock = threading.Lock()

    def dump(self, key: str, value: str,
             tags: Optional[List[str]] = None,
             phase_angle: Optional[float] = None) -> StashEntry:
        if phase_angle is None:
            phase_angle = self._text_to_phase(value)
        entry = StashEntry(key=key or "", value=value or "",
                           tags=list(tags or []), phase_angle=phase_angle)
        with self._lock:
            self.entries.append(entry)
        return entry

    def retrieve(self, query: str = "", tag: str = "") -> List[StashEntry]:
        with self._lock:
            results = list(self.entries)
        if tag:
            results = [e for e in results if tag in e.tags]
        if query:
            q = query.lower()
            results = [e for e in results
                       if q in e.value.lower() or q in e.key.lower()]
        return results

    @property
    def is_mature(self) -> bool:
        return self.closed_at is not None or \
            len(self.entries) >= MATURITY_MIN_ENTRIES

    @property
    def already_crystallized(self) -> bool:
        return self.crystallized_at is not None

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pocket_id": self.pocket_id,
                "goal_id": self.goal_id,
                "owner": self.owner,
                "opened_at": self.opened_at,
                "closed_at": self.closed_at,
                "crystallized_at": self.crystallized_at,
                "crystals": self.crystals,
                "entry_count": len(self.entries),
                "entries": [e.to_dict() for e in self.entries],
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StashPocket":
        p = cls(goal_id=str(data.get("goal_id") or "goal"),
                owner=str(data.get("owner") or "queen"),
                pocket_id=str(data.get("pocket_id") or ""))
        p.opened_at = float(data.get("opened_at") or time.time())
        p.closed_at = data.get("closed_at")
        p.crystallized_at = data.get("crystallized_at")
        p.crystals = int(data.get("crystals") or 0)
        for raw in data.get("entries") or []:
            try:
                p.entries.append(StashEntry(
                    key=str(raw.get("key") or ""),
                    value=str(raw.get("value") or ""),
                    tags=list(raw.get("tags") or []),
                    phase_angle=float(raw.get("phase_angle") or 0.0),
                    timestamp=float(raw.get("timestamp") or time.time()),
                ))
            except Exception:
                continue
        return p

    @staticmethod
    def _text_to_phase(text: str) -> float:
        """Map text to a phase angle [0, 2π] deterministically."""
        if not text:
            return 0.0
        total = sum(ord(c) for c in text[:200])
        return (total % 1000) / 1000.0 * 2 * math.pi


# ─────────────────────────────────────────────────────────────────────────────
# Crystallization — pocket -> KnowledgeDataset fragments
# ─────────────────────────────────────────────────────────────────────────────


def _fragment_from_entry(pocket: StashPocket, entry: StashEntry) -> Dict[str, Any]:
    """One pocket entry -> a dataset fragment matching the live schema,
    provenance-tagged stash_pocket + goal + created_at."""
    created_iso = datetime.fromtimestamp(
        entry.timestamp, tz=timezone.utc).isoformat()
    return {
        "text": entry.value,
        "tags": ["stash_pocket", f"goal:{pocket.goal_id}",
                 f"created:{created_iso}"] + list(entry.tags),
        "source_goal": f"stash_pocket:{pocket.goal_id}",
        "source_owner": "stash_pockets",
        "phase_angle": round(float(entry.phase_angle), 8),
        "coherence_score": 0.5,
        "timestamp": float(entry.timestamp),
        "times_retrieved": 0,
        "data_type": "fact",
        "category": "research",
        "meaning": "",
        "related_indices": [],
        "interpretation_source": "raw",
        "interpretation_confidence": 0.0,
        "who": [],
        "what": entry.key,
        "where": [],
        "when_rel": created_iso,
        "why": "",
        "how": "",
    }


def _append_overflow(fragments: List[Dict[str, Any]]) -> int:
    """Dataset at cap: crystallize into stash_crystallized.jsonl instead.
    Append-only with a sidecar lock file for inter-process safety."""
    if not fragments:
        return 0
    lock_path = STASH_CRYSTALLIZED.with_suffix(".lock")
    try:
        import msvcrt  # Windows advisory byte-range lock
        with open(lock_path, "a+b") as lockf, \
                open(STASH_CRYSTALLIZED, "a", encoding="utf-8") as out:
            lockf.seek(0)
            try:
                msvcrt.locking(lockf.fileno(), msvcrt.LK_LOCK, 1)
            except Exception:
                pass
            try:
                for frag in fragments:
                    out.write(json.dumps(frag, ensure_ascii=False) + "\n")
            finally:
                try:
                    lockf.seek(0)
                    msvcrt.locking(lockf.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
        return len(fragments)
    except Exception as exc:
        logger.debug("overflow append failed: %s", exc)
        return 0


def _crystallize(pocket: StashPocket) -> List[Dict[str, Any]]:
    """Turn a mature pocket's entries into retained dataset fragments.
    Read-modify-write on knowledge_dataset.json, atomic tmp+rename. At
    the fragment cap, overflow goes to stash_crystallized.jsonl. Never
    raises; returns the fragments actually crystallized."""
    fragments = [_fragment_from_entry(pocket, e) for e in pocket.entries]
    if not fragments:
        return []
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        QUEEN_MIND.mkdir(parents=True, exist_ok=True)
        dataset = _read_json_defensive(KNOWLEDGE_DATASET, None)
        if not isinstance(dataset, dict):
            # Missing or corrupt dataset: rebuild the envelope honestly.
            dataset = {"fragments": [], "saved_at": _utcnow_iso(),
                       "version": 1}
        existing = dataset.get("fragments")
        if not isinstance(existing, list):
            existing = []
        if len(existing) >= MAX_DATASET_FRAGMENTS:
            written = _append_overflow(fragments)
            pocket.crystals = written
            return fragments[:written]
        capacity = MAX_DATASET_FRAGMENTS - len(existing)
        to_dataset = fragments[:capacity]
        overflow = fragments[capacity:]
        dataset["fragments"] = existing + to_dataset
        dataset["saved_at"] = _utcnow_iso()
        _atomic_write_json(KNOWLEDGE_DATASET, dataset)
        written = len(to_dataset)
        if overflow:
            written += _append_overflow(overflow)
        pocket.crystals = written
        return fragments[:written]
    except Exception as exc:
        logger.debug("crystallize failed for %s: %s", pocket.pocket_id, exc)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Fusion-native manager (module-level, persists across calls)
# ─────────────────────────────────────────────────────────────────────────────


class _Manager:
    def __init__(self):
        self._lock = threading.RLock()
        self._open: Dict[str, StashPocket] = {}
        self._closed: List[StashPocket] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            for path in sorted(STATE_DIR.glob("*.json")):
                try:
                    data = _read_json_defensive(path, None)
                    if not isinstance(data, dict):
                        continue
                    pocket = StashPocket.from_dict(data)
                    if pocket.closed_at is not None:
                        self._closed.append(pocket)
                    else:
                        self._open[pocket.pocket_id] = pocket
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("pocket load failed: %s", exc)

    def _persist(self, pocket: StashPocket) -> None:
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            _atomic_write_json(STATE_DIR / f"{pocket.pocket_id}.json",
                               pocket.to_dict())
        except Exception as exc:
            logger.debug("pocket persist failed: %s", exc)


_manager = _Manager()


def create_pocket(goal: str, owner: str = "queen") -> Dict[str, Any]:
    """Open a new scratch pad for a goal. Fail-closed: on any internal
    error returns a synthetic closed pocket dict so callers never crash."""
    try:
        with _manager._lock:
            _manager._ensure_loaded()
            pocket = StashPocket(goal_id=str(goal or "goal"), owner=owner)
            _manager._open[pocket.pocket_id] = pocket
            _manager._persist(pocket)
            return {"pocket_id": pocket.pocket_id, "goal_id": pocket.goal_id,
                    "owner": pocket.owner, "created": True}
    except Exception as exc:
        logger.debug("create_pocket failed: %s", exc)
        return {"pocket_id": "", "goal_id": str(goal or "goal"),
                "owner": owner, "created": False, "error": str(exc)}


def add_finding(pocket_id: str, text: str,
                key: str = "", tags: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Dump one finding into a pocket. Returns the entry dict, or None if
    the pocket is unknown or anything fails (fail-closed)."""
    try:
        with _manager._lock:
            _manager._ensure_loaded()
            pocket = _manager._open.get(str(pocket_id))
            if pocket is None:
                return None
            entry = pocket.dump(key=key, value=text, tags=tags)
            _manager._persist(pocket)
            return entry.to_dict()
    except Exception as exc:
        logger.debug("add_finding failed: %s", exc)
        return None


def close_pocket(pocket_id: str) -> Optional[Dict[str, Any]]:
    """Close a pocket: it becomes mature and eligible for crystallization."""
    try:
        with _manager._lock:
            _manager._ensure_loaded()
            pocket = _manager._open.pop(str(pocket_id), None)
            if pocket is None:
                return None
            pocket.closed_at = time.time()
            _manager._closed.append(pocket)
            _manager._persist(pocket)
            return {"pocket_id": pocket.pocket_id, "goal_id": pocket.goal_id,
                    "entries": len(pocket.entries), "closed": True}
    except Exception as exc:
        logger.debug("close_pocket failed: %s", exc)
        return None


def mature_pockets() -> List[Dict[str, Any]]:
    """Crystallize every open pocket that has matured (enough entries or
    closed). Returns the list of crystallized fragments. Never raises."""
    crystallized: List[Dict[str, Any]] = []
    try:
        with _manager._lock:
            _manager._ensure_loaded()
            for pocket_id, pocket in list(_manager._open.items()):
                if not pocket.is_mature or pocket.already_crystallized:
                    continue
                frags = _crystallize(pocket)
                if frags:
                    pocket.crystallized_at = time.time()
                    crystallized.extend(frags)
                    _manager._persist(pocket)
            # Closed-but-uncrystallized pockets (e.g. closed pre-restart).
            for pocket in _manager._closed:
                if pocket.already_crystallized or not pocket.entries:
                    continue
                frags = _crystallize(pocket)
                if frags:
                    pocket.crystallized_at = time.time()
                    crystallized.extend(frags)
                    _manager._persist(pocket)
    except Exception as exc:
        logger.debug("mature_pockets failed: %s", exc)
    return crystallized


def list_pockets() -> List[Dict[str, Any]]:
    """All known pockets (open + closed), freshest first. Never raises."""
    try:
        with _manager._lock:
            _manager._ensure_loaded()
            pockets = list(_manager._open.values()) + list(_manager._closed)
            pockets.sort(key=lambda p: p.opened_at, reverse=True)
            return [{
                "pocket_id": p.pocket_id,
                "goal_id": p.goal_id,
                "owner": p.owner,
                "entries": len(p.entries),
                "mature": p.is_mature,
                "crystallized": p.crystallized_at is not None,
                "crystals": p.crystals,
                "opened_at": p.opened_at,
            } for p in pockets]
    except Exception as exc:
        logger.debug("list_pockets failed: %s", exc)
        return []


def status() -> Dict[str, Any]:
    pockets = list_pockets()
    return {
        "open": sum(1 for p in pockets if not p["mature"]),
        "mature_pending": sum(1 for p in pockets
                              if p["mature"] and not p["crystallized"]),
        "crystallized": sum(1 for p in pockets if p["crystallized"]),
        "total": len(pockets),
        "fragments_crystallized": sum(p["crystals"] for p in pockets),
        "dataset": str(KNOWLEDGE_DATASET),
        "overflow": str(STASH_CRYSTALLIZED),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _emit(payload: Any) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _cmd_demo() -> int:
    """Full pocket lifecycle: create -> findings -> maturity -> crystallize."""
    goal = f"demo_goal_{uuid.uuid4().hex[:6]}"
    pocket = create_pocket(goal, owner="demo")
    pid = pocket.get("pocket_id") or ""
    findings = [
        "demo: phase-coherent dumps group by angle, not keyword",
        "demo: pocket lifecycle survives restart via state/stash_pockets/",
        "demo: mature pockets crystallize into knowledge_dataset fragments",
    ]
    added = [add_finding(pid, t, key=f"step_{i}")
             for i, t in enumerate(findings, 1)]
    crystallized = mature_pockets()
    _emit({
        "demo": {
            "created": pocket,
            "findings_added": sum(1 for a in added if a),
            "crystallized_now": len(crystallized),
            "crystallized_sample": (crystallized[0] if crystallized else None),
            "status": status(),
        }
    })
    return 0


def _cmd_list() -> int:
    _emit({"pockets": list_pockets(), "status": status()})
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    cmd = args[0] if args else "list"
    try:
        if cmd == "demo":
            return _cmd_demo()
        if cmd == "list":
            return _cmd_list()
        _emit({"error": f"unknown command: {cmd}",
               "usage": "python -m aureon_fusion.stash_pockets demo|list"})
        return 2
    except Exception as exc:  # outermost fail-closed guard
        print(f"stash_pockets: degraded: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
