"""One-line JSON logs. Authorization headers and token fields are never written."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

_REDACT = {
    "authorization",
    "token",
    "api_key",
    "api_secret",
    "secret",
    "password",
    "aureon_fusion_api_token",
}


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if str(key).lower() in _REDACT:
                cleaned[key] = "[redacted]"
            else:
                cleaned[key] = _clean(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def log_event(level: str, event: str, **fields: Any) -> dict[str, Any]:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
        "service": "aureon-fusion",
        "live_trading": False,
    }
    record.update(_clean(fields))
    line = json.dumps(record, sort_keys=True, default=str)
    sys.stderr.write(line + "\n")
    sys.stderr.flush()
    path = os.environ.get("AUREON_LOG_PATH")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return record
