"""Canonical text for evidence files. Same values, same bytes."""

from __future__ import annotations

import csv
import io
import json
import math
from typing import Any


def plain(value: Any) -> Any:
    """Turn repo and NumPy scalars into JSON-safe Python values."""

    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"non-finite float: {value!r}")
        return number
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    item = getattr(value, "item", None)
    if callable(item):
        return plain(item())
    raise TypeError(f"cannot serialize {type(value).__name__}")


def dump(payload: Any) -> str:
    return json.dumps(plain(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"


def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(int(value))
    if isinstance(value, float):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"non-finite float: {value!r}")
        return json.dumps(number)
    if isinstance(value, str):
        return value
    item = getattr(value, "item", None)
    if callable(item):
        return cell(item())
    raise TypeError(f"cannot format {type(value).__name__}")


def csv_text(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=fieldnames,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({name: cell(row.get(name)) for name in fieldnames})
    text = buffer.getvalue()
    if not text.endswith("\n"):
        text += "\n"
    return text
