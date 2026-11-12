"""Check that a dotted module exists without importing any part of it.

``importlib.util.find_spec("a.b.c")`` imports ``a`` and ``a.b`` for real so it
can read their ``__path__``. For a reachability probe that runs package
``__init__`` code, which can pull in exchange clients and start background
pieces. This walks the package folders with ``PathFinder`` instead: it reads
specs and never executes a module.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from typing import Optional, Sequence


def module_spec_exists(module: str) -> bool:
    """True when ``module`` can be found on disk; no module code runs."""
    parts = module.split(".")
    if not module or any(not part for part in parts):
        return False
    search: Optional[Sequence[str]] = None
    for depth in range(1, len(parts) + 1):
        name = ".".join(parts[:depth])
        loaded = sys.modules.get(name)
        if loaded is not None:
            spec = getattr(loaded, "__spec__", None)
            locations = getattr(loaded, "__path__", None)
        else:
            try:
                if depth == 1:
                    # A top-level name has no parent to import, so find_spec runs nothing.
                    spec = importlib.util.find_spec(name)
                else:
                    spec = importlib.machinery.PathFinder.find_spec(name, search)
            except (ImportError, ValueError):
                return False
            if spec is None:
                return False
            locations = spec.submodule_search_locations
        if depth == len(parts):
            return loaded is not None or spec is not None
        if locations is None:
            return False  # a plain module has no submodules
        search = list(locations)
    return False
