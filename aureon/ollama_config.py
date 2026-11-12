"""Shared, secret-safe Ollama local and cloud configuration.

Ollama's local API does not require an API key. Direct requests to
``ollama.com`` do, using ``Authorization: Bearer $OLLAMA_API_KEY``. Aureon
historically also accepted ``AUREON_OLLAMA_API_KEY`` and
``AUREON_LLM_API_KEY``; the official name is primary while both aliases
remain supported.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

from filelock import FileLock


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

# Daily Ollama call/token accounting
OLLAMA_DAILY_CAP_ENV = "AUREON_OLLAMA_DAILY_CAP"
DEFAULT_OLLAMA_DAILY_CAP = 200
OLLAMA_USAGE_PATH_ENV = "AUREON_OLLAMA_USAGE_PATH"

# Cross-organism shared atomic Ollama budget (coordinated across all consumers)
AUREON_OLLAMA_DAILY_SHARED_CAP_ENV = "AUREON_OLLAMA_DAILY_SHARED_CAP"
DEFAULT_OLLAMA_DAILY_SHARED_CAP = 50
AUREON_OLLAMA_SHARED_BUDGET_PATH_ENV = "AUREON_OLLAMA_SHARED_BUDGET_PATH"

_RUNTIME_BOOTSTRAP_LOCK = threading.Lock()
_RUNTIME_BOOTSTRAP_ATTEMPTED = False


class OllamaDailyBudgetExceeded(RuntimeError):
    """Raised when a call would exceed the soft daily Ollama cap.

    Callers (e.g. ollama_switchboard) can catch this and degrade to disk
    cache / stale data.
    """


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _usage_path() -> Path:
    explicit = os.getenv(OLLAMA_USAGE_PATH_ENV)
    if explicit:
        return Path(explicit)
    # Default: workspace/aureon_fusion/state/ollama_usage.json
    # __file__ = aureon-os-upstream/aureon/ollama_config.py
    return Path(__file__).resolve().parents[2] / "aureon_fusion" / "state" / "ollama_usage.json"


def _load_usage() -> Dict[str, Any]:
    path = _usage_path()
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                rec = json.load(f)
            if isinstance(rec, dict) and rec.get("day") == _today():
                return rec
    except Exception as exc:
        logger.warning("Failed to load ollama_usage.json: %s", exc)
    return {
        "day": _today(),
        "calls": 0,
        "est_tokens": 0,
        "by_host": {},
    }


def _save_usage(rec: Dict[str, Any]) -> None:
    path = _usage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as exc:
        logger.warning("Failed to persist ollama_usage.json: %s", exc)


_USAGE_LOCK = threading.Lock()
_USAGE_CACHE: Dict[str, Dict[str, Any]] = {}


def _get_usage() -> Dict[str, Any]:
    """In-memory singleton per process plus disk persistence."""
    today = _today()
    cached = _USAGE_CACHE.get("record")
    if cached is not None and cached.get("day") == today:
        return cached
    rec = _load_usage()
    _USAGE_CACHE["record"] = rec
    return rec


def _estimate_tokens(text: Any) -> int:
    text = str(text or "")
    if not text:
        return 0
    # Rough estimate: ~4 characters per token; ensure non-zero for any text.
    return max(1, len(text) // 4)


def resolve_ollama_daily_cap() -> int:
    """Soft daily call cap. <=0 means unlimited."""
    raw = os.getenv(OLLAMA_DAILY_CAP_ENV)
    if raw is None:
        return DEFAULT_OLLAMA_DAILY_CAP
    try:
        value = int(raw.strip())
        return value
    except ValueError:
        return DEFAULT_OLLAMA_DAILY_CAP


def resolve_ollama_shared_cap() -> int:
    """Shared, cross-process daily Ollama call cap. <=0 means unlimited."""
    raw = os.getenv(AUREON_OLLAMA_DAILY_SHARED_CAP_ENV)
    if raw is None:
        return DEFAULT_OLLAMA_DAILY_SHARED_CAP
    try:
        return int(raw.strip())
    except ValueError:
        return DEFAULT_OLLAMA_DAILY_SHARED_CAP


def _shared_budget_path() -> Path:
    explicit = os.getenv(AUREON_OLLAMA_SHARED_BUDGET_PATH_ENV)
    if explicit:
        return Path(explicit)
    return Path(__file__).resolve().parents[2] / "aureon_fusion" / "state" / "ollama_budget.json"


def _load_shared_budget(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                rec = json.load(f)
            if (
                isinstance(rec, dict)
                and rec.get("day") == _today()
                and isinstance(rec.get("remaining_calls"), int)
                and isinstance(rec.get("cap"), int)
            ):
                return rec
    except Exception:
        pass
    cap = resolve_ollama_shared_cap()
    return {"day": _today(), "remaining_calls": cap, "cap": cap}


def _save_shared_budget(path: Path, rec: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def ensure_ollama_shared_budget() -> Dict[str, Any]:
    """Load/reset the shared budget file at day start.

    Returns the current budget record without consuming a call.
    """
    path = _shared_budget_path()
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        existed = path.exists()
        rec = _load_shared_budget(path)
        if not existed or rec["day"] != _today():
            cap = resolve_ollama_shared_cap()
            rec = {"day": _today(), "remaining_calls": cap, "cap": cap}
            _save_shared_budget(path, rec)
    return dict(rec)


def _atomic_decrement_shared_budget(path: Path) -> Dict[str, Any]:
    lock_path = path.with_suffix(path.suffix + ".lock")
    with FileLock(str(lock_path)):
        rec = _load_shared_budget(path)
        if rec["remaining_calls"] <= 0:
            raise OllamaDailyBudgetExceeded("shared_budget_exhausted")
        rec["remaining_calls"] -= 1
        _save_shared_budget(path, rec)
    return dict(rec)


def get_ollama_usage() -> Dict[str, Any]:
    """Return current usage counters (calls, est_tokens, by_host)."""
    with _USAGE_LOCK:
        return dict(_get_usage())


def check_ollama_daily_budget(base_url: Optional[str] = None, *,
                              est_tokens: int = 0) -> None:
    """Fail-closed gate: enforce the daily Ollama budget.

    First checks the legacy per-process call ceiling (``AUREON_OLLAMA_DAILY_CAP``),
    then atomically decrements the shared cross-consumer budget file
    (``AUREON_OLLAMA_DAILY_SHARED_CAP``).  Raises
    ``OllamaDailyBudgetExceeded`` with reason ``shared_budget_exhausted`` when
    the shared pool is empty.  ``est_tokens`` is recorded by
    ``record_ollama_call``; this gate counts calls.
    """
    # Legacy per-process cap (kept for existing callers/selftests).
    legacy_cap = resolve_ollama_daily_cap()
    if legacy_cap > 0:
        with _USAGE_LOCK:
            rec = _get_usage()
            if rec["day"] != _today():
                rec = _load_usage()
                _USAGE_CACHE["record"] = rec
            if rec["calls"] >= legacy_cap:
                raise OllamaDailyBudgetExceeded("shared_budget_exhausted")

    # Shared cross-consumer atomic budget.
    shared_cap = resolve_ollama_shared_cap()
    if shared_cap <= 0:
        return
    _atomic_decrement_shared_budget(_shared_budget_path())


def record_ollama_call(
    base_url: Optional[str] = None,
    *,
    prompt_text: Any = None,
    response_text: Any = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Increment Ollama usage counters and persist to disk.

    Token estimation: if explicit token counts are not supplied, they are
    estimated from prompt/response text length. The file shape is
    ``{day, calls, est_tokens, by_host}`` as required.
    """
    host = _hostname(base_url) if base_url else "unknown"
    est = 0
    if prompt_tokens is not None:
        est += max(0, int(prompt_tokens))
    else:
        est += _estimate_tokens(prompt_text)
    if completion_tokens is not None:
        est += max(0, int(completion_tokens))
    else:
        est += _estimate_tokens(response_text)

    with _USAGE_LOCK:
        rec = _get_usage()
        if rec["day"] != _today():
            rec = _load_usage()
            _USAGE_CACHE["record"] = rec
        rec["calls"] = int(rec.get("calls", 0)) + 1
        rec["est_tokens"] = int(rec.get("est_tokens", 0)) + est
        by_host = rec.setdefault("by_host", {})
        host_rec = by_host.setdefault(host, {"calls": 0, "est_tokens": 0})
        host_rec["calls"] = int(host_rec.get("calls", 0)) + 1
        host_rec["est_tokens"] = int(host_rec.get("est_tokens", 0)) + est
        _save_usage(rec)
        return dict(rec)


def tracked_ollama_call(
    base_url: Optional[str],
    fn: Callable[[], Any],
    *,
    prompt_text: Any = None,
    prompt_tokens: Optional[int] = None,
    response_token_extractor: Optional[Callable[[Any], int]] = None,
) -> Any:
    """Choke-point wrapper: check cap, call ``fn()``, record usage.

    ``response_token_extractor`` may convert the returned object into a token
    count or string for estimation. Exceptions from ``fn`` propagate without
    recording usage so failed calls are not charged.
    """
    est_prompt = prompt_tokens if prompt_tokens is not None else _estimate_tokens(prompt_text)
    check_ollama_daily_budget(base_url, est_tokens=est_prompt)
    result = fn()
    completion = None
    if response_token_extractor is not None:
        try:
            completion = response_token_extractor(result)
            if not isinstance(completion, int):
                completion = str(completion)
        except Exception:
            completion = None
    record_ollama_call(
        base_url=base_url,
        prompt_text=prompt_text,
        prompt_tokens=prompt_tokens,
        response_text=completion if isinstance(completion, str) else None,
        completion_tokens=completion if isinstance(completion, int) else None,
    )
    return result


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


def is_ollama_cloud_model(model: Any) -> bool:
    """Return whether a model id is an Ollama cloud-backed model.

    Ollama serves cloud models (e.g. ``glm-5.3:cloud``) through the local
    proxy under the ``:cloud`` suffix.  These are thinking models: without
    reasoning control they spend bounded token budgets on hidden
    reasoning and return no visible answer.
    """

    return str(model or "").strip().lower().endswith(":cloud")


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
    "DEFAULT_OLLAMA_DAILY_CAP",
    "DEFAULT_OLLAMA_DAILY_SHARED_CAP",
    "EXTERNAL_LLM_FALLBACK_ENV",
    "OLLAMA_API_KEY_ENVS",
    "OLLAMA_DAILY_CAP_ENV",
    "OLLAMA_REASONING_EFFORT_ENV",
    "AUREON_OLLAMA_DAILY_SHARED_CAP_ENV",
    "AUREON_OLLAMA_SHARED_BUDGET_PATH_ENV",
    "OLLAMA_CLOUD_NATIVE_BASE_URL",
    "OLLAMA_CLOUD_OPENAI_BASE_URL",
    "OllamaDailyBudgetExceeded",
    "is_loopback_url",
    "is_ollama_cloud_url",
    "looks_like_ollama_url",
    "ensure_ollama_runtime_config",
    "ensure_ollama_shared_budget",
    "ollama_authorization_headers",
    "ollama_config_snapshot",
    "resolve_external_llm_fallback",
    "resolve_ollama_reasoning_effort",
    "resolve_ollama_api_key",
    "resolve_ollama_native_base_url",
    "resolve_ollama_openai_base_url",
    "resolve_ollama_daily_cap",
    "resolve_ollama_shared_cap",
    "get_ollama_usage",
    "check_ollama_daily_budget",
    "record_ollama_call",
    "tracked_ollama_call",
]
