"""Apply huggingface/hnc-field/guard.py without keeping its directory change.

The Space module chdirs into the Space and may put the checkout on sys.path.
This loader reuses that module, restores the working directory, and prefers an
installed aureon distribution over the checkout when one is importable.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from aureon_public.paths import repo_root, space_guard

_DONE = False


def _same(path: str, root: Path) -> bool:
    candidate = path or os.getcwd()
    try:
        return Path(candidate).resolve() == root.resolve()
    except OSError:
        return False


def apply_space_guard() -> None:
    """Install the Space environment and the trading-import blocker."""

    global _DONE
    if _DONE:
        return
    root = repo_root()
    guard_path = space_guard()
    cwd = Path.cwd()
    real_chdir = os.chdir
    os.chdir = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    try:
        spec = importlib.util.spec_from_file_location("aureon_hf_space_guard", guard_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {guard_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["aureon_hf_space_guard"] = module
        spec.loader.exec_module(module)
    finally:
        os.chdir = real_chdir
    if Path.cwd() != cwd:
        real_chdir(cwd)
    os.environ.pop("AUREON_MCP_TRANSIT_KEY", None)
    _prefer_installed_aureon(root)
    _DONE = True


def _prefer_installed_aureon(root: Path) -> None:
    """Use the pinned install when it is present. Otherwise keep the checkout."""

    saved = list(sys.path)
    trimmed = [entry for entry in saved if not _same(entry, root)]
    sys.path[:] = trimmed
    try:
        found = importlib.util.find_spec("aureon")
    finally:
        sys.path[:] = saved
    origin = getattr(found, "origin", None) if found is not None else None
    if origin and root.resolve() not in Path(origin).resolve().parents and Path(origin).resolve() != root.resolve():
        sys.path[:] = trimmed
