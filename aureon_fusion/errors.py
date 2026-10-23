"""Local error sink. A webhook is used only when AUREON_ERROR_WEBHOOK_URL is set.

Nothing in this module signs up for a vendor or sends data unless that
environment variable is present. Tests leave it unset.
"""

from __future__ import annotations

import json
import os
import traceback
import urllib.request
from typing import Any

from .logging_json import log_event


def capture_exception(exc: BaseException, **context: Any) -> dict[str, Any]:
    record = log_event(
        "error",
        "exception",
        error_type=type(exc).__name__,
        error_message=str(exc)[:500],
        traceback=traceback.format_exc(limit=8)[-2000:],
        **context,
    )
    path = os.environ.get("AUREON_ERROR_LOG_PATH")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    url = os.environ.get("AUREON_ERROR_WEBHOOK_URL")
    if url:
        body = json.dumps(
            {"service": "aureon-fusion", "live_trading": False, "event": record},
            default=str,
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            record["webhook_status"] = response.status
    return record
