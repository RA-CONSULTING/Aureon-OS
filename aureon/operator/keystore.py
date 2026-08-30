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

**Per-tenant isolation.** Every function takes an optional ``tenant``. With
``tenant=None`` (the single-operator default) the global store is used, exactly
as before. With a tenant (a Supabase JWT ``sub``, set on ``g.tenant`` by the
operator gate) the keys live in an isolated per-tenant file
``~/.aureon/tenants/<tenant>/provider_keys.json.enc`` — one tenant can never read
another's keys. Critically, ``apply_to_env()`` is **global-only and never takes a
tenant**: injecting a tenant's key into the process ``os.environ`` would leak it
into every other request, so a tenant write must never call it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict

from aureon.ollama_config import OLLAMA_API_KEY_ENVS
from aureon.operator.provider_catalog import get_provider, managed_env_vars

logger = logging.getLogger("aureon.operator.keystore")

CONFIG_DIR = Path.home() / ".aureon"
KEY_PATH = CONFIG_DIR / "provider_keys.key"
STORE_PATH = CONFIG_DIR / "provider_keys.json.enc"
TENANTS_DIR = CONFIG_DIR / "tenants"

_FIELDS = ("api_key", "base_url", "model", "enabled")
_SAFE_TENANT = re.compile(r"[A-Za-z0-9_-]{1,128}")


def _provider_key_envs(info: Any) -> tuple[str, ...]:
    if str(getattr(info, "id", "") or "") == "ollama":
        return OLLAMA_API_KEY_ENVS
    return (info.key_env,) if getattr(info, "key_env", "") else ()


def _safe_tenant(tenant: str) -> str:
    """A filesystem-safe, collision-free directory name for a tenant id.

    The tenant id is a JWT ``sub`` (normally a UUID). Even though the token is signed, defend against
    path traversal: accept a strict whitelist verbatim, otherwise fall back to a SHA-256 hash — so a
    crafted ``sub`` can never escape ``TENANTS_DIR``.

    The two forms are kept in **disjoint namespaces** by prefix. Without that, they share one
    directory space and collide: a SHA-256 hex digest itself matches the whitelist, so a tenant whose
    ``sub`` is literally the digest of another tenant's crafted ``sub`` would be handed that tenant's
    store — reading their keys and taking over their rotations. ``v_`` (verbatim) and ``h_`` (hashed)
    can never produce the same name, because a verbatim id is always re-prefixed.
    """
    if _SAFE_TENANT.fullmatch(tenant):
        return f"v_{tenant}"
    return f"h_{hashlib.sha256(tenant.encode('utf-8')).hexdigest()}"


def _store_path(tenant: str | None) -> Path:
    """Where a store lives: the global file for ``None``, an isolated per-tenant file otherwise."""
    if not tenant:
        return STORE_PATH
    return TENANTS_DIR / _safe_tenant(tenant) / "provider_keys.json.enc"


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


def load(tenant: str | None = None) -> Dict[str, Dict[str, Any]]:
    """Decrypt and return a keystore, or ``{}`` if missing/unreadable.

    ``tenant=None`` reads the global store; a tenant reads only that tenant's isolated file.
    """
    path = _store_path(tenant)
    if not path.exists():
        return {}
    try:
        raw = _fernet().decrypt(path.read_bytes())
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001 — a corrupt store must not sink the operator
        logger.warning("provider keystore unreadable: %s", type(exc).__name__)
        return {}


#: Serializes every read-modify-write of a keystore. ``save_provider`` / ``delete_provider`` each
#: ``load()`` the whole store, mutate one entry, and write it all back — so two concurrent writes race
#: and the loser's change is silently discarded. Reproduced: 24 concurrent ``save_provider`` calls for
#: one tenant left exactly ONE provider stored. A user connecting two models at once would lose one.
#: Re-entrant because ``delete_provider`` calls ``load`` and ``_persist`` while already holding it.
_WRITE_LOCK = threading.RLock()


def _persist(data: Dict[str, Dict[str, Any]], tenant: str | None = None) -> None:
    """Encrypt and write a store **atomically**.

    A direct ``write_bytes`` truncates before it writes, so an interrupted write leaves a partial file
    — and a partial Fernet token cannot be decrypted. ``load`` swallows that and returns ``{}``, so the
    tenant's keys do not merely vanish: the next ``save_provider`` then persists only its own entry,
    making the loss permanent. Write a sibling temp file and ``os.replace`` it into place instead —
    atomic on POSIX within one filesystem, so a reader sees either the old store or the new one.
    """
    path = _store_path(tenant)
    path.parent.mkdir(parents=True, exist_ok=True)
    token = _fernet().encrypt(json.dumps(data).encode("utf-8"))
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_bytes(token)
        try:
            tmp.chmod(0o600)   # tighten before it becomes visible under the real name
        except OSError:  # pragma: no cover
            pass
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _known(provider_id: str) -> bool:
    """A stored id is valid if it's an LLM provider OR a catalog connection."""
    if get_provider(provider_id) is not None:
        return True
    from aureon.operator.connections_catalog import get_connection

    return get_connection(provider_id) is not None


def save_provider(
    provider_id: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    enabled: bool | None = None,
    extra: Dict[str, str] | None = None,
    tenant: str | None = None,
) -> Dict[str, Any]:
    """Merge the given fields into a provider's entry and persist. Only provided
    (non-None) fields change. ``extra`` holds secondary credential envs (e.g. a
    Telegram chat id) as ``{ENV_VAR: value}``. ``tenant`` scopes the write to that
    tenant's isolated store (``None`` ⇒ the global store). Returns the stored entry."""
    if not _known(provider_id):
        raise KeyError(f"unknown provider: {provider_id}")
    # The lock must span load→mutate→persist, not just the write: the whole store is rewritten, so a
    # concurrent save that read the same snapshot would drop this entry (or have its own dropped).
    with _WRITE_LOCK:
        data = load(tenant)
        entry = data.get(provider_id, {"enabled": True})
        if api_key is not None:
            entry["api_key"] = api_key.strip()
        if base_url is not None:
            entry["base_url"] = base_url.strip()
        if model is not None:
            entry["model"] = model.strip()
        if enabled is not None:
            entry["enabled"] = bool(enabled)
        if extra:
            merged = dict(entry.get("extra", {}))
            merged.update({k: str(v).strip() for k, v in extra.items() if v is not None})
            entry["extra"] = merged
        data[provider_id] = entry
        _persist(data, tenant)
        return entry


def delete_provider(provider_id: str, *, tenant: str | None = None) -> None:
    """Forget a provider's stored config. For the global store also unset its env
    vars; a **tenant delete never touches ``os.environ``** (that is the leak vector)."""
    with _WRITE_LOCK:                      # same read-modify-write hazard as save_provider
        data = load(tenant)
        entry = data.get(provider_id, {})
        if provider_id in data:
            del data[provider_id]
            _persist(data, tenant)
    if tenant is not None:
        # Tenant keys never enter the process env, so there is nothing to unset.
        return
    info = get_provider(provider_id)
    if info:  # LLM provider
        for var in (
            *_provider_key_envs(info),
            info.base_url_env,
            model_env(info.registry_name),
            *(
                ("AUREON_LLM_MODEL", "AUREON_OLLAMA_MODEL")
                if str(getattr(info, "id", "") or "") == "ollama"
                else ()
            ),
        ):
            if var:
                os.environ.pop(var, None)
        return
    from aureon.operator.connections_catalog import get_connection

    conn = get_connection(provider_id)
    if conn:  # data-source connection
        for var in conn.credential_env:
            os.environ.pop(var, None)
        for var in (entry.get("extra") or {}):
            os.environ.pop(var, None)


def apply_to_env() -> None:
    """Inject stored config into ``os.environ`` so the switchboard uses it.

    Enabled entries set their key/base-URL/model env vars; disabled entries have
    their key env removed (dropping the line). Providers with no keystore entry
    are left untouched, so keys supplied via a real ``.env`` still work.
    """
    from aureon.operator.connections_catalog import get_connection

    data = load()
    for provider_id, entry in data.items():
        enabled = bool(entry.get("enabled", True))
        key = str(entry.get("api_key", "") or "")
        info = get_provider(provider_id)
        if info is not None:
            # ── LLM provider (base_url + model semantics) ──
            base_url = str(entry.get("base_url", "") or "")
            model = str(entry.get("model", "") or "")
            if enabled:
                if key:
                    for key_env in _provider_key_envs(info):
                        os.environ[key_env] = key
                if base_url and info.base_url_env:
                    os.environ[info.base_url_env] = base_url
                if model:
                    os.environ[model_env(info.registry_name)] = model
                    if str(getattr(info, "id", "") or "") == "ollama":
                        os.environ["AUREON_LLM_MODEL"] = model
                        os.environ["AUREON_OLLAMA_MODEL"] = model
            else:
                for key_env in _provider_key_envs(info):
                    os.environ.pop(key_env, None)
                if str(getattr(info, "id", "") or "") == "ollama":
                    os.environ.pop("AUREON_LLM_MODEL", None)
                    os.environ.pop("AUREON_OLLAMA_MODEL", None)
                if info.key_optional and info.base_url_env:
                    os.environ.pop(info.base_url_env, None)
            continue
        conn = get_connection(provider_id)
        if conn is None:
            continue
        # ── data-source connection (primary key + extra envs) ──
        extra = entry.get("extra") or {}
        if enabled:
            if key and conn.key_env:
                os.environ[conn.key_env] = key
            for var, val in extra.items():
                if val:
                    os.environ[var] = str(val)
        else:
            for var in conn.credential_env:
                os.environ.pop(var, None)
            for var in extra:
                os.environ.pop(var, None)


def mask(key: str) -> str:
    """Public last-4 mask for safe display (e.g. ••••1234)."""
    key = str(key or "")
    if not key:
        return ""
    return ("•" * 4) + key[-4:] if len(key) > 4 else "•" * len(key)


# Back-compat internal alias.
_mask = mask


def masked_view(tenant: str | None = None) -> Dict[str, Dict[str, Any]]:
    """Safe view of a keystore for the UI — never the full key. ``tenant`` scopes
    it to that tenant's isolated store (``None`` ⇒ global)."""
    data = load(tenant)
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
    "mask",
    "model_env",
    "managed_env_vars",
    "STORE_PATH",
    "KEY_PATH",
]
