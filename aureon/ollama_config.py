"""Shared, secret-safe Ollama local and cloud configuration.

Ollama's local API does not require an API key. Direct requests to
``ollama.com`` do, using ``Authorization: Bearer $OLLAMA_API_KEY``. Aureon
historically also accepted ``AUREON_OLLAMA_API_KEY`` and
``AUREON_LLM_API_KEY``; the official name is primary while both aliases
remain supported.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse


DEFAULT_OLLAMA_NATIVE_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_OPENAI_BASE_URL = f"{DEFAULT_OLLAMA_NATIVE_BASE_URL}/v1"
OLLAMA_CLOUD_NATIVE_BASE_URL = "https://ollama.com"
OLLAMA_CLOUD_OPENAI_BASE_URL = "https://ollama.com/v1"
OLLAMA_API_KEY_ENVS = (
    "OLLAMA_API_KEY",
    "AUREON_OLLAMA_API_KEY",
    "AUREON_LLM_API_KEY",
)

logger = logging.getLogger("aureon.ollama_config")

EXTERNAL_LLM_FALLBACK_ENV = "AUREON_EXTERNAL_LLM_FALLBACK"
DEFAULT_EXTERNAL_LLM_FALLBACK = "ollama"
OLLAMA_REASONING_EFFORT_ENV = "AUREON_OLLAMA_REASONING_EFFORT"
DEFAULT_OLLAMA_REASONING_EFFORT = "none"
_RUNTIME_BOOTSTRAP_LOCK = threading.Lock()
_RUNTIME_BOOTSTRAP_ATTEMPTED = False


def _first_nonempty(*values: Optional[str]) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _resolve_ollama_api_key_and_source(
    api_key: Optional[str] = None,
) -> Tuple[str, str]:
    if api_key is not None:
        return str(api_key).strip(), "explicit"
    for name in OLLAMA_API_KEY_ENVS:
        value = str(os.environ.get(name, "") or "").strip()
        if value:
            return value, name
    return "", ""


def resolve_ollama_api_key(api_key: Optional[str] = None) -> str:
    """Return an explicit or environment-provided Ollama API key."""

    return _resolve_ollama_api_key_and_source(api_key)[0]


def _hostname(base_url: str) -> str:
    try:
        return str(urlparse(str(base_url)).hostname or "").lower()
    except Exception:
        return ""


def is_ollama_cloud_url(base_url: str) -> bool:
    """Return whether a URL targets Ollama's hosted service."""

    host = _hostname(base_url)
    return host == "ollama.com" or host.endswith(".ollama.com")


def is_loopback_url(base_url: str) -> bool:
    host = _hostname(base_url)
    return host in {"localhost", "127.0.0.1", "::1"}


def looks_like_ollama_url(base_url: str) -> bool:
    """Conservatively identify Ollama endpoints without claiming generic LLMs."""

    text = str(base_url or "").strip().lower()
    if not text:
        return False
    if is_ollama_cloud_url(text):
        return True
    try:
        parsed = urlparse(text)
        if is_loopback_url(text) and parsed.port == 11434:
            return True
        return "ollama" in str(parsed.hostname or "").lower()
    except Exception:
        return "ollama" in text or ":11434" in text


def resolve_external_llm_fallback() -> str:
    """Return the configured repo-wide external LLM fallback provider."""

    value = str(
        os.environ.get(EXTERNAL_LLM_FALLBACK_ENV, DEFAULT_EXTERNAL_LLM_FALLBACK)
        or DEFAULT_EXTERNAL_LLM_FALLBACK
    ).strip().lower()
    aliases = {
        "ollama_cloud": "ollama",
        "ollama-cloud": "ollama",
        "cloud_ollama": "ollama",
        "disabled": "none",
        "off": "none",
        "false": "none",
        "0": "none",
    }
    return aliases.get(value, value)


def resolve_ollama_reasoning_effort() -> str:
    """Return a supported Ollama reasoning level for compatible cloud calls."""

    value = str(
        os.environ.get(OLLAMA_REASONING_EFFORT_ENV, DEFAULT_OLLAMA_REASONING_EFFORT)
        or DEFAULT_OLLAMA_REASONING_EFFORT
    ).strip().lower()
    aliases = {"off": "none", "false": "none", "0": "none"}
    value = aliases.get(value, value)
    return value if value in {"none", "low", "medium", "high"} else DEFAULT_OLLAMA_REASONING_EFFORT


def _ollama_runtime_env_present() -> bool:
    native = str(os.environ.get("AUREON_OLLAMA_BASE_URL", "") or "").strip()
    compatible = str(os.environ.get("AUREON_LLM_BASE_URL", "") or "").strip()
    return bool(native or (compatible and looks_like_ollama_url(compatible)))


def ensure_ollama_runtime_config(
    *,
    explicit_config: bool = False,
    force: bool = False,
    repo_root: Optional[Path] = None,
) -> Dict[str, object]:
    """Load Aureon's credentials once before an implicit Ollama build.

    Launchers already bootstrap credentials, but standalone library consumers
    historically could construct an adapter first and silently land on
    localhost. This guarded, idempotent bootstrap aligns those consumers with
    the encrypted provider profile. Explicit settings, an already configured
    environment, pytest isolation, or ``AUREON_LLM_AUTO_BOOTSTRAP=0`` retain
    caller control.
    """

    global _RUNTIME_BOOTSTRAP_ATTEMPTED

    if explicit_config or _ollama_runtime_env_present():
        return ollama_config_snapshot()
    auto = str(os.environ.get("AUREON_LLM_AUTO_BOOTSTRAP", "1") or "1").strip().lower()
    if not force and auto in {"0", "false", "no", "off"}:
        return ollama_config_snapshot()
    if not force and os.environ.get("PYTEST_CURRENT_TEST"):
        return ollama_config_snapshot()
    if not force and resolve_external_llm_fallback() != "ollama":
        return ollama_config_snapshot()

    with _RUNTIME_BOOTSTRAP_LOCK:
        if not _RUNTIME_BOOTSTRAP_ATTEMPTED or force:
            _RUNTIME_BOOTSTRAP_ATTEMPTED = True
            try:
                from aureon.core.aureon_env import bootstrap_credentials

                root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
                bootstrap_credentials(root)
            except Exception as exc:  # fail-soft: local/default behaviour remains available
                logger.warning("Ollama runtime credential bootstrap failed: %s", type(exc).__name__)
    return ollama_config_snapshot()


def _native_root(base_url: str) -> str:
    root = str(base_url or "").strip().rstrip("/")
    lowered = root.lower()
    for suffix in ("/api", "/v1"):
        if lowered.endswith(suffix):
            return root[: -len(suffix)].rstrip("/")
    return root


def resolve_ollama_native_base_url(base_url: Optional[str] = None) -> str:
    """Resolve the native API root, including the compatible LLM URL alias."""

    configured = _first_nonempty(base_url, os.environ.get("AUREON_OLLAMA_BASE_URL"))
    if not configured:
        compatible = str(os.environ.get("AUREON_LLM_BASE_URL", "") or "").strip()
        if looks_like_ollama_url(compatible):
            configured = compatible
    return _native_root(configured or DEFAULT_OLLAMA_NATIVE_BASE_URL)


def resolve_ollama_openai_base_url(base_url: Optional[str] = None) -> str:
    """Resolve Ollama's OpenAI-compatible ``/v1`` endpoint."""

    configured = _first_nonempty(base_url, os.environ.get("AUREON_LLM_BASE_URL"))
    if not configured:
        configured = str(os.environ.get("AUREON_OLLAMA_BASE_URL", "") or "").strip()
    configured = configured or DEFAULT_OLLAMA_OPENAI_BASE_URL
    clean = configured.rstrip("/")
    if clean.lower().endswith("/v1"):
        return clean
    if looks_like_ollama_url(clean):
        return f"{_native_root(clean)}/v1"
    return clean


def ollama_authorization_headers(
    base_url: str,
    api_key: Optional[str] = None,
) -> Dict[str, str]:
    """Build a Bearer header without leaking a cloud key to local Ollama.

    An explicitly passed key remains an intentional override. The legacy
    ``AUREON_LLM_API_KEY`` also retains its historical custom-local-server
    behavior. Official Ollama cloud keys are withheld from loopback unless
    ``AUREON_OLLAMA_SEND_AUTH_TO_LOCAL=1`` is deliberately set.
    """

    key, source = _resolve_ollama_api_key_and_source(api_key)
    if not key:
        return {}
    allow_local = str(
        os.environ.get("AUREON_OLLAMA_SEND_AUTH_TO_LOCAL", "") or ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    if (
        is_loopback_url(base_url)
        and source not in {"explicit", "AUREON_LLM_API_KEY"}
        and not allow_local
    ):
        return {}
    return {"Authorization": f"Bearer {key}"}


def ollama_config_snapshot(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, object]:
    """Return configuration metadata containing no credential material."""

    native = resolve_ollama_native_base_url(base_url)
    key = resolve_ollama_api_key(api_key)
    headers = ollama_authorization_headers(native, api_key)
    return {
        "external_fallback": resolve_external_llm_fallback(),
        "reasoning_effort": resolve_ollama_reasoning_effort(),
        "native_base_url": native,
        "openai_base_url": resolve_ollama_openai_base_url(base_url),
        "cloud": is_ollama_cloud_url(native),
        "auth_required": is_ollama_cloud_url(native),
        "api_key_configured": bool(key),
        "authorization_header_enabled": bool(headers),
    }


__all__ = [
    "DEFAULT_EXTERNAL_LLM_FALLBACK",
    "DEFAULT_OLLAMA_REASONING_EFFORT",
    "DEFAULT_OLLAMA_NATIVE_BASE_URL",
    "DEFAULT_OLLAMA_OPENAI_BASE_URL",
    "EXTERNAL_LLM_FALLBACK_ENV",
    "OLLAMA_API_KEY_ENVS",
    "OLLAMA_REASONING_EFFORT_ENV",
    "OLLAMA_CLOUD_NATIVE_BASE_URL",
    "OLLAMA_CLOUD_OPENAI_BASE_URL",
    "is_loopback_url",
    "is_ollama_cloud_url",
    "looks_like_ollama_url",
    "ensure_ollama_runtime_config",
    "ollama_authorization_headers",
    "ollama_config_snapshot",
    "resolve_external_llm_fallback",
    "resolve_ollama_reasoning_effort",
    "resolve_ollama_api_key",
    "resolve_ollama_native_base_url",
    "resolve_ollama_openai_base_url",
]
