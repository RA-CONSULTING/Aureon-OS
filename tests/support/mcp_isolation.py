"""Keep MCP import-guard side effects inside MCP tests only."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_PATH = str(_REPO_ROOT / "mcp")


def ensure_mcp_path() -> None:
    if _MCP_PATH not in sys.path:
        sys.path.insert(0, _MCP_PATH)


def pinned_finders_on_meta_path() -> list[Any]:
    from aureon_public.pin_blob import PinnedAureonFinder

    return [finder for finder in sys.meta_path if isinstance(finder, PinnedAureonFinder)]


def teardown_guard_leaks() -> None:
    """Remove MCP guard finders and the loaded Space guard module from this process."""

    from aureon_public.pin_blob import PinnedAureonFinder

    sys.meta_path[:] = [
        finder
        for finder in sys.meta_path
        if not isinstance(finder, PinnedAureonFinder) and type(finder).__name__ != "_BlockTrading"
    ]
    sys.modules.pop("aureon_hf_space_guard", None)
    try:
        import aureon_public.guard_loader as guard_loader

        guard_loader._DONE = False
    except ImportError:
        pass


def load_public_test_bindings(module: ModuleType) -> None:
    """Import aureon_public inside the MCP test module, not at collection import time."""

    ensure_mcp_path()
    name = module.__name__
    if name.endswith("test_aureon_public_mcp"):
        from aureon_public import surfaces, tools
        from aureon_public.guard_loader import PINNED_COMMIT, aureon_source, describe_aureon_source
        from aureon_public.server import SERVER_INSTRUCTIONS, build_server
        from aureon_public.text import SERVER_PLAIN

        module.tools = tools
        module.surfaces = surfaces
        module.PINNED_COMMIT = PINNED_COMMIT
        module.aureon_source = aureon_source
        module.describe_aureon_source = describe_aureon_source
        module.SERVER_INSTRUCTIONS = SERVER_INSTRUCTIONS
        module.build_server = build_server
        module.SERVER_PLAIN = SERVER_PLAIN
    elif name.endswith("test_aureon_body"):
        from aureon_public.body import (
            body_call,
            body_call_operator,
            body_registry,
            body_surface,
            enabled_stage,
        )
        from aureon_public.guard_loader import PINNED_COMMIT
        from aureon_public.paths import repo_root
        from aureon_public.pin_blob import checkout_blob_refusal

        module.body_call = body_call
        module.body_call_operator = body_call_operator
        module.body_registry = body_registry
        module.body_surface = body_surface
        module.enabled_stage = enabled_stage
        module.PINNED_COMMIT = PINNED_COMMIT
        module.repo_root = repo_root
        module.checkout_blob_refusal = checkout_blob_refusal


def is_mcp_test_module(module_name: str) -> bool:
    base = module_name.rsplit(".", 1)[-1]
    if base in {"test_aureon_public_mcp", "test_aureon_body"}:
        return True
    if base.startswith("test_mcp_") and module_name.startswith("tests.bio."):
        return True
    return False
