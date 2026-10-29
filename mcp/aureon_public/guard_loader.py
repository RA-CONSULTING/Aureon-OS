"""Apply huggingface/hnc-field/guard.py without keeping its directory change.

The Space module chdirs into the Space and may put the checkout on sys.path.
This loader reuses that module, restores the working directory, and prefers an
installed aureon distribution over the checkout when one is importable.

When that install is missing, imports fall back to the checkout. Callers must
read aureon_source() rather than assume the documented pin.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from aureon_public.paths import repo_root, space_guard

_DONE = False
PINNED_COMMIT = "a00f744d2e686e916e45b81dd4222408c368e305"


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
    if not origin:
        return
    origin_path = Path(origin)
    if _outside_checkout(origin_path, root) and _direct_url_commit(origin_path) == PINNED_COMMIT:
        sys.path[:] = trimmed


def _outside_checkout(origin: Path, root: Path) -> bool:
    resolved = origin.resolve()
    root_resolved = root.resolve()
    return resolved != root_resolved and root_resolved not in resolved.parents


def _direct_url_commit(origin: Path) -> str | None:
    """Commit recorded beside an installed aureon, if direct_url.json has one."""

    site = origin.resolve().parent.parent
    for dist in sorted(site.glob("aureon-*.dist-info")):
        direct = dist / "direct_url.json"
        if not direct.is_file():
            continue
        try:
            payload = json.loads(direct.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        vcs = payload.get("vcs_info") if isinstance(payload, dict) else None
        commit = vcs.get("commit_id") if isinstance(vcs, dict) else None
        if isinstance(commit, str) and commit.strip():
            return commit.strip()
    return None


def _git_commit(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    commit = result.stdout.strip()
    if len(commit) == 40 and all(character in "0123456789abcdef" for character in commit):
        return commit
    return "unknown"


def describe_aureon_source(origin: Path | None, root: Path) -> dict[str, str]:
    """Say which tree answered. Pinned only when direct_url.json names the pin."""

    if origin is not None and _outside_checkout(origin, root):
        commit = _direct_url_commit(origin)
        if commit == PINNED_COMMIT:
            return {"kind": "pinned", "commit": commit}
        return {"kind": "checkout", "commit": "unknown"}
    return {"kind": "checkout", "commit": _git_commit(root)}


def aureon_source() -> dict[str, str]:
    """The aureon import this process will use, after the guard has chosen a path."""

    apply_space_guard()
    root = repo_root()
    found = importlib.util.find_spec("aureon")
    origin_text = getattr(found, "origin", None) if found is not None else None
    origin = Path(origin_text) if origin_text else None
    return describe_aureon_source(origin, root)
