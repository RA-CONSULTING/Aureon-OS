"""Local preflight for the internal self-coder.

The self-coder module itself does not read or write ``os.environ``. This
helper does, so a fresh box can hold an HNC proposal key and name an
OpenAI-compatible model without that write landing in the coder file.
The key is not printed and is not written into ``.env``.
"""

from __future__ import annotations

import base64
import os
import secrets
from pathlib import Path
from typing import Any


def _canonical_hnc_master_key() -> str:
    raw = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def ensure_hnc_master_key_preflight(root: Path) -> dict[str, Any]:
    """Use an existing key, or read or generate ``state/hnc_packet_master_key``."""

    from aureon.harmonic.hnc_quantum_packet_crypto import (
        MASTER_KEY_ENV,
        normalize_hnc_key_material,
        packet_master_key_from_env,
    )

    source = "env"
    existing = packet_master_key_from_env().strip()
    path = Path(root) / "state" / "hnc_packet_master_key"
    if not existing:
        if path.is_file():
            existing = path.read_text(encoding="utf-8").strip()
            source = "state_file"
        else:
            existing = _canonical_hnc_master_key()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(existing + "\n", encoding="utf-8")
            try:
                path.chmod(0o600)
            except OSError:
                pass
            source = "generated"
        os.environ[MASTER_KEY_ENV] = existing
    try:
        normalize_hnc_key_material(packet_master_key_from_env())
        ready = True
        reason = "ready"
    except Exception:
        ready = False
        reason = "master_key_invalid"
    return {
        "ready": ready,
        "source": source,
        "key_material_returned": False,
        "reason": reason,
        "state_file": str(path),
    }


def openai_compatible_model_endpoint() -> dict[str, Any]:
    """Read the self-coder model endpoint. The API key is not returned."""

    base = (os.environ.get("AUREON_SELF_CODER_OPENAI_BASE_URL") or "http://127.0.0.1:8000/v1").strip()
    model = (os.environ.get("AUREON_SELF_CODER_MODEL") or "kimi-k2.5").strip()
    return {
        "base_url": base.rstrip("/"),
        "model": model,
        "api_key_configured": bool((os.environ.get("AUREON_SELF_CODER_API_KEY") or "").strip()),
        "api_key_returned": False,
        "wire_api": "openai-chat-completions",
    }
