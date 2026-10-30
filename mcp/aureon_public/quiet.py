"""Keep import banners off stdout. MCP stdio uses stdout for JSON-RPC."""

from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable


def quiet(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        from aureon_public.guard_loader import apply_space_guard

        apply_space_guard()
        saved = sys.stdout
        sys.stdout = sys.stderr
        try:
            return fn(*args, **kwargs)
        finally:
            sys.stdout = saved

    return wrapped
