"""Keep MCP import-guard side effects inside MCP tests only."""

from __future__ import annotations

import subprocess
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
    if "aureon_public" not in sys.modules:
        return []
    ensure_mcp_path()
    try:
        from aureon_public.pin_blob import PinnedAureonFinder
    except ImportError:
        return []
    return [finder for finder in sys.meta_path if isinstance(finder, PinnedAureonFinder)]


def teardown_guard_leaks() -> None:
    """Remove MCP guard finders and the loaded Space guard module from this process."""

    if "aureon_public" not in sys.modules:
        return
    ensure_mcp_path()
    try:
        from aureon_public.pin_blob import PinnedAureonFinder
    except ImportError:
        return
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


def import_blocked_in_fresh_guarded_process(module: str) -> None:
    """Apply the Space guard in a new interpreter and expect ``module`` import to fail."""

    code = (
        "import importlib\n"
        "import sys\n"
        f"sys.path.insert(0, {_MCP_PATH!r})\n"
        "from aureon_public.guard_loader import apply_space_guard\n"
        "apply_space_guard()\n"
        "try:\n"
        f"    importlib.import_module({module!r})\n"
        "except ImportError:\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit('import was not blocked')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"expected ImportError importing {module!r} under guard; "
            f"exit={completed.returncode} stderr={completed.stderr!r} stdout={completed.stdout!r}"
        )


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
    if base in {
        "test_aureon_public_mcp",
        "test_aureon_public_alignment",
        "test_aureon_public_stage1",
        "test_aureon_public_protocol",
        "test_aureon_public_space",
        "test_aureon_body",
    }:
        return True
    if base.startswith("test_mcp_") and module_name.startswith("tests.bio."):
        return True
    return False
