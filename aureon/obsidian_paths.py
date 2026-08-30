"""Canonical filesystem paths for Aureon's Obsidian integration.

The dedicated Obsidian vault lives outside the Git worktree.  Older Aureon
writers used ``.obsidian/...`` as a repo-relative note directory, while the
bridge already defaulted to ``~/AureonObsidianVault``.  These helpers keep one
source of truth and translate the legacy note prefix when running in a real
Git checkout.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union


PathLike = Union[str, os.PathLike[str]]

OBSIDIAN_VAULT_ENV = "AUREON_OBSIDIAN_VAULT_PATH"
DEFAULT_OBSIDIAN_VAULT_NAME = "AureonObsidianVault"
LEGACY_OBSIDIAN_PREFIX = ".obsidian"


def default_obsidian_vault_path() -> Path:
    """Return Aureon's user-local default vault path."""

    return Path.home() / DEFAULT_OBSIDIAN_VAULT_NAME


def resolve_obsidian_vault_path(vault_path: Optional[PathLike] = None) -> Path:
    """Resolve an explicit, environment, or default Obsidian vault root."""

    configured = str(vault_path or "").strip()
    if not configured:
        configured = os.environ.get(OBSIDIAN_VAULT_ENV, "").strip()
    path = Path(configured).expanduser() if configured else default_obsidian_vault_path()
    return path.resolve(strict=False)


def _is_git_checkout(repo_root: Optional[PathLike]) -> bool:
    if repo_root is None:
        return False
    root = Path(repo_root).expanduser()
    return (root / ".git").exists()


def resolve_obsidian_note_path(
    note_path: PathLike,
    *,
    repo_root: Optional[PathLike] = None,
    vault_path: Optional[PathLike] = None,
) -> Path:
    """Resolve a note path without letting it escape its intended root.

    Absolute paths remain explicit overrides.  A legacy relative path under
    ``.obsidian/`` is redirected to the dedicated vault when an environment or
    vault override is present, or when the caller is a real Git checkout.
    Temporary non-Git repositories retain repo-local behaviour for isolated
    tests and fixtures.  Other relative paths remain relative to ``repo_root``.
    """

    raw = Path(note_path).expanduser()
    if raw.is_absolute():
        return raw.resolve(strict=False)

    parts = raw.parts
    is_legacy = bool(parts) and parts[0].lower() == LEGACY_OBSIDIAN_PREFIX
    configured = bool(str(vault_path or "").strip()) or bool(
        os.environ.get(OBSIDIAN_VAULT_ENV, "").strip()
    )

    if is_legacy and (configured or _is_git_checkout(repo_root) or repo_root is None):
        relative = Path(*parts[1:])
        root = resolve_obsidian_vault_path(vault_path)
        resolved = (root / relative).resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Obsidian note path escapes vault: {note_path}") from exc
        return resolved

    if repo_root is not None:
        root = Path(repo_root).expanduser().resolve(strict=False)
        resolved = (root / raw).resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Relative note path escapes repository: {note_path}") from exc
        return resolved

    root = resolve_obsidian_vault_path(vault_path)
    resolved = (root / raw).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Obsidian note path escapes vault: {note_path}") from exc
    return resolved


__all__ = [
    "DEFAULT_OBSIDIAN_VAULT_NAME",
    "LEGACY_OBSIDIAN_PREFIX",
    "OBSIDIAN_VAULT_ENV",
    "default_obsidian_vault_path",
    "resolve_obsidian_note_path",
    "resolve_obsidian_vault_path",
]
