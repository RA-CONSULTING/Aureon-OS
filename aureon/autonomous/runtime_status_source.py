"""Runtime status loader shared by read-only evidence reports."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
DEFAULT_RUNTIME_STATUS_URL = "http://127.0.0.1:8791/api/terminal-state"


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else default
    except Exception:
        return default


def _same_repo(root: Path) -> bool:
    try:
        return root.resolve() == REPO_ROOT.resolve()
    except Exception:
        return False


def _status_file_matches(payload: dict[str, Any], expected: Path) -> bool:
    raw = payload.get("status_file")
    if not raw:
        return True
    try:
        return Path(str(raw)).resolve() == expected.resolve()
    except Exception:
        return False


def read_runtime_status(
    root: Path | None = None,
    *,
    rel_path: Path = RUNTIME_STATUS_PATH,
    timeout_sec: float = 20.0,
) -> dict[str, Any]:
    """Read runtime status, preferring the local API overlay for the live repo.

    The runtime file can briefly contain an old tick-stale classification while
    the status API has fresher watchdog interpretation. Tests and alternate
    roots keep using the local file only.
    """

    root_path = (root or REPO_ROOT).resolve()
    file_path = rel_path if rel_path.is_absolute() else root_path / rel_path
    file_payload = _read_json(file_path, {})
    if not isinstance(file_payload, dict):
        file_payload = {}

    if os.getenv("AUREON_DISABLE_RUNTIME_STATUS_API", "").strip() == "1" or not _same_repo(root_path):
        return file_payload

    url = os.getenv("AUREON_RUNTIME_STATUS_URL", DEFAULT_RUNTIME_STATUS_URL).strip()
    if not url:
        return file_payload
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as response:
            api_payload = json.loads(response.read().decode("utf-8"))
        if isinstance(api_payload, dict) and _status_file_matches(api_payload, file_path):
            return api_payload
    except Exception:
        pass
    return file_payload
