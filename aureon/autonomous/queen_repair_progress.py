"""Per-cycle progress ledger for the rule-based self-repair coder.

The repair child runs every cycle. Without memory it would re-try the same
patch that was reverted last time and never build on a win. This ledger records,
once per cycle, the failures that a repair turned green, the failures whose error
was narrowed (a shallower exception became a deeper one, e.g. ImportError became
an AssertionError further down), and the edits that were tried and reverted. A
later cycle reads the reverted edits and skips them, so she keeps trying new
things instead of looping on a known-inert patch.

Honest wording only: a recorded "fixed" means a previously-failing test passed
after the edit with no regression, never that the system is proven or alive.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

PROGRESS_PATH = "state/queen_repair_progress.jsonl"

# Rough depth order: a failure that moves from a shallow import/collection error
# to a deeper runtime or assertion error has been narrowed (more of the code ran).
_DEPTH = {
    "": 0,
    "SyntaxError": 1,
    "ImportError": 2,
    "ModuleNotFoundError": 2,
    "CollectionError": 2,
    "NameError": 3,
    "AttributeError": 3,
    "ModuleNotFound": 2,
    "TypeError": 4,
    "ValueError": 4,
    "KeyError": 4,
    "IndexError": 4,
    "RuntimeError": 4,
    "FileNotFoundError": 4,
    "AssertionError": 5,
    "Failed": 5,
}


def is_narrower(before: str, after: str) -> bool:
    """True when `after` is a strictly deeper exception than `before`.

    Deeper means more of the test's code executed before failing. Unknown
    exception names are treated as deep (4) so a move off an import/collection
    error still counts, but a move onto an import error never does.
    """

    if not after or before == after:
        return False
    b = _DEPTH.get(before, 4)
    a = _DEPTH.get(after, 4)
    return a > b


def reverted_changes(root: Path) -> set[str]:
    """`{path}::{change}` keys that a prior cycle tried and reverted (inert or regressing)."""

    keys: set[str] = set()
    path = Path(root) / PROGRESS_PATH
    if not path.is_file():
        return keys
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            for attempt in entry.get("attempts", []):
                if attempt.get("result") in {"reverted_inert", "reverted_regression"}:
                    change = attempt.get("change", "")
                    p = attempt.get("path", "")
                    if change:
                        keys.add(f"{p}::{change}")
    except (OSError, ValueError):
        return keys
    return keys


def record_cycle(root: Path, *, fixed: list[str], narrowed: list[dict[str, Any]],
                 attempts: list[dict[str, Any]], committed: bool, reason: str) -> Path:
    """Append one line describing this cycle. Never raises into the repair loop."""

    path = Path(root) / PROGRESS_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": time.time(),
            "pid": os.getpid(),
            "fixed": sorted(set(fixed)),
            "narrowed": narrowed,
            "attempts": attempts,
            "committed": bool(committed),
            "reason": reason,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        pass
    return path
