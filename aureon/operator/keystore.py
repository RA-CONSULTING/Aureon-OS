"""
Aureon Operator — encrypted provider keystore.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Instance-owned API keys for the LLM switchboard, entered in the Providers UI and
kept **encrypted at rest** (Fernet) at ``~/.aureon/provider_keys.json.enc`` with
the key file ``~/.aureon/provider_keys.key`` (mode 0600). Never committed.

The keystore is the *control plane*: ``apply_to_env()`` injects stored values
into ``os.environ`` under each provider's env vars (from ``provider_catalog``),
so the existing env-driven adapters pick them up on the next switchboard build.
A disabled provider has its key env removed so its line drops out.

Everything read back out is **masked** (last 4 only). No full key is ever
returned or logged.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from aureon.operator.provider_catalog import get_provider, managed_env_vars

logger = logging.getLogger("aureon.operator.keystore")

CONFIG_DIR = Path.home() / ".aureon"
KEY_PATH = CONFIG_DIR / "provider_keys.key"
STORE_PATH = CONFIG_DIR / "provider_keys.json.enc"

_FIELDS = ("api_key", "base_url", "model", "enabled")


def model_env(registry_name: str) -> str:
    """Uniform per-provider model-override env var (applied in default_registry)."""
    return f"AUREON_MODEL_{registry_name.upper()}"


def _fernet():
    from cryptography.fernet import Fernet

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not KEY_PATH.exists():
        KEY_PATH.write_bytes(Fernet.generate_key())
        try:
            KEY_PATH.chmod(0o600)
        except OSError:  # pragma: no cover - best effort on odd filesystems
            pass
    return Fernet(KEY_PATH.read_bytes())


def load() -> Dict[str, Dict[str, Any]]:
    """Decrypt and return the keystore, or ``{}`` if missing/unreadable."""
    if not STORE_PATH.exists():
        return {}
    try:
        raw = _fernet().decrypt(STORE_PATH.read_bytes())
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001 — a corrupt store must not sink the operator
        logger.warning("provider keystore unreadable: %s", type(exc).__name__)
        return {}


def _persist(data: Dict[str, Dict[str, Any]]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    token = _fernet().encrypt(json.dumps(data).encode("utf-8"))
    STORE_PATH.write_bytes(token)
    try:
        STORE_PATH.chmod(0o600)
    except OSError:  # pragma: no cover
        pass


def save_provider(
    provider_id: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    enabled: bool | None = None,
) -> Dict[str, Any]:
    """Merge the given fields into a provider's entry and persist. Only provided
    (non-None) fields change. Returns the stored entry (unmasked, in-process)."""
    if get_provider(provider_id) is None:
        raise KeyError(f"unknown provider: {provider_id}")
    data = load()
    entry = data.get(provider_id, {"enabled": True})
    if api_key is not None:
        entry["api_key"] = api_key.strip()
    if base_url is not None:
        entry["base_url"] = base_url.strip()
    if model is not None:
        entry["model"] = model.strip()
    if enabled is not None:
        entry["enabled"] = bool(enabled)
    data[provider_id] = entry
    _persist(data)
    return entry


def delete_provider(provider_id: str) -> None:
    """Forget a provider's stored config and unset its env vars."""
    data = load()
    if provider_id in data:
        del data[provider_id]
        _persist(data)
    info = get_provider(provider_id)
    if info:
        for var in (info.key_env, info.base_url_env, model_env(info.registry_name)):
            if var:
                os.environ.pop(var, None)


def apply_to_env() -> None:
    """Inject stored config into ``os.environ`` so the switchboard uses it.

    Enabled entries set their key/base-URL/model env vars; disabled entries have
    their key env removed (dropping the line). Providers with no keystore entry
    are left untouched, so keys supplied via a real ``.env`` still work.
    """
    data = load()
    for provider_id, entry in data.items():
        info = get_provider(provider_id)
        if info is None:
            continue
        enabled = bool(entry.get("enabled", True))
        key = str(entry.get("api_key", "") or "")
        base_url = str(entry.get("base_url", "") or "")
        model = str(entry.get("model", "") or "")
        if enabled:
            if key and info.key_env:
                os.environ[info.key_env] = key
            if base_url and info.base_url_env:
                os.environ[info.base_url_env] = base_url
            if model:
                os.environ[model_env(info.registry_name)] = model
        else:
            # Turn the line off without forgetting the key.
            if info.key_env:
                os.environ.pop(info.key_env, None)
            if info.key_optional and info.base_url_env:
                # keyless (Ollama) lines are enabled by base-URL presence
                os.environ.pop(info.base_url_env, None)


def _mask(key: str) -> str:
    key = str(key or "")
    if not key:
        return ""
    return ("•" * 4) + key[-4:] if len(key) > 4 else "•" * len(key)


def masked_view() -> Dict[str, Dict[str, Any]]:
    """Safe view of the keystore for the UI — never the full key."""
    data = load()
    view: Dict[str, Dict[str, Any]] = {}
    for provider_id, entry in data.items():
        key = str(entry.get("api_key", "") or "")
        view[provider_id] = {
            "has_key": bool(key),
            "key_masked": _mask(key),
            "base_url": str(entry.get("base_url", "") or ""),
            "model": str(entry.get("model", "") or ""),
            "enabled": bool(entry.get("enabled", True)),
        }
    return view


__all__ = [
    "load",
    "save_provider",
    "delete_provider",
    "apply_to_env",
    "masked_view",
    "model_env",
    "managed_env_vars",
    "STORE_PATH",
    "KEY_PATH",
]
