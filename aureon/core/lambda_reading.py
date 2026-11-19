"""Lambda(t) as a measurement.

A missing value, ``None``, a bool, or a non-finite number is not a reading.
An explicit ``0.0`` stays ``0.0``. Callers must use ``is None``, never ``if not``,
because a flat field is falsy and is still a reading.
"""

from __future__ import annotations

import math
from typing import Any, Mapping


def lambda_reading(value: Any) -> float | None:
    """Return a finite Lambda(t), or None when nothing was measured."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    return number


def format_lambda(value: Any, spec: str = ".4f") -> str:
    """Format a reading. A gap is the words ``no reading``, not ``0.0000``."""
    number = lambda_reading(value)
    if number is None:
        return "no reading"
    return format(number, spec)


def lambda_from_mapping(mapping: Any, key: str = "lambda_t") -> float | None:
    """Read ``key`` only when the mapping actually carries it."""
    if not isinstance(mapping, Mapping) or key not in mapping:
        return None
    return lambda_reading(mapping[key])
