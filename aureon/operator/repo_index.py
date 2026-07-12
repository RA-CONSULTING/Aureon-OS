"""
Aureon Operator — repo-wide grounding index.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The switchboard's grounding used to see only a curated slice of ``docs/``. For a
cognition whose paths must "touch every piece of the repo", that isn't enough.

This wraps the existing :class:`ResearchCorpusIndex` (reused verbatim — same
TF-IDF, same cache, same search API) but points it at the **repo root** and
widens the ingest set to ``.md`` + ``.py`` + ``.txt`` + ``.pdf`` with a deny-list
for vendored / generated / binary trees. It writes its own cache
(``state/operator_repo_index.json``) so the Queen-voice docs index
(``state/research_index.json``) is left completely untouched.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import List, Optional

from aureon.queen.research_corpus_index import ResearchCorpusIndex, Snippet

logger = logging.getLogger("aureon.operator.repo_index")

# Repo root = two levels up from aureon/operator/repo_index.py
REPO_ROOT = Path(__file__).resolve().parents[2]

# Directories / path fragments we never index: vendored, generated, binary,
# historical, or runtime-state trees. Matched both as path components and as
# substrings by ResearchCorpusIndex._iter_source_files.
_EXCLUDE = (
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    "frontend", "state", "imports", "archive", "queen_backups",
    "VERIFICATION AND VALIDATION", "data/ephemeral", ".venv", "venv",
    "dist", "build", "site-packages",
)

_INGEST = (".md", ".py", ".txt", ".pdf")

_instance: Optional[ResearchCorpusIndex] = None
_lock = threading.Lock()


def get_operator_repo_index() -> ResearchCorpusIndex:
    """Process-wide singleton repo-wide index (docs + code)."""
    global _instance
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is None:
            _instance = ResearchCorpusIndex(
                root=str(REPO_ROOT),
                cache_path=str(REPO_ROOT / "state" / "operator_repo_index.json"),
                exclude=_EXCLUDE,
                ingest_exts=_INGEST,
            )
    return _instance


def reset_operator_repo_index() -> None:
    """Test hook — drop the singleton so the next call rebuilds."""
    global _instance
    with _lock:
        _instance = None


def repo_search(query: str, top_k: int = 4) -> List[Snippet]:
    """Convenience: ensure-built repo-wide search."""
    idx = get_operator_repo_index()
    idx.ensure_built()
    return idx.search(query, top_k=top_k)


__all__ = ["get_operator_repo_index", "reset_operator_repo_index", "repo_search", "REPO_ROOT"]
