"""Keep import banners off stdout. MCP stdio uses stdout for JSON-RPC."""

from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable


def quiet(fn: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        saved = sys.stdout
        sys.stdout = sys.stderr
        try:
            return fn(*args, **kwargs)
        finally:
            sys.stdout = saved

    return wrapped
