"""Strict-JSON sanitation shared by browser-facing HTTP surfaces."""

from __future__ import annotations

import math
from typing import Any


def json_safe(value: Any) -> Any:
    """Recursively replace non-finite floats with JSON ``null`` values."""

    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


__all__ = ["json_safe"]
