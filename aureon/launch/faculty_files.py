"""Honest faculty records for a checkout that has not yet seen a sample.

A missing state file becomes ``truth_status: no_data`` with the producer named.
No measurement is written. An existing file is left as the producer wrote it.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_absence(faculty: dict[str, Any], producer: str) -> Path | None:
    raw = str(faculty.get("path") or "")
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": str(faculty.get("name") or path.stem),
        "available": False,
        "truth_status": "no_data",
        "reason": (
            f"no sample yet: {path.name} is written by {producer}; "
            "this record does not invent a measurement"
        ),
        "timestamp": _now(),
        "live_trading": False,
    }
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def record_missing_faculties() -> list[str]:
    """Write an absence record for every faculty file that is not already there."""

    from aureon.launch.master import _faculty_producer, _faculties

    written: list[str] = []
    faculties, _error = _faculties()
    for faculty in faculties:
        path = Path(str(faculty.get("path") or ""))
        if path.is_file():
            continue
        saved = record_absence(faculty, _faculty_producer(faculty))
        if saved is not None:
            written.append(str(saved))
    return written
