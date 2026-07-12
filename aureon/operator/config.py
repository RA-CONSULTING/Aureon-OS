"""
Aureon Operator — configuration & model registry.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Everything the operator's behaviour depends on lives here as data, so the same
binary is a dev toy or a production switchboard depending only on the environment
it boots in. Two objects:

  • ``OperatorConfig`` — timeouts, retries, concurrency, cache, gate thresholds.
    ``OperatorConfig.from_env()`` reads ``AUREON_OPERATOR_*`` overrides.
  • ``ModelSpec`` + ``DEFAULT_REGISTRY`` — the line-up. Any flagship model
    (OpenAI, xAI/Grok, Gemini, Anthropic) or a self-hosted / recorded backend is
    just a row here. Add a row → it's on the switchboard. Keyless rows are
    skipped at assembly time, so the registry can list every model you *might*
    use and the runtime uses only the ones actually configured.

Pure data — no provider imports here, so ``providers.py`` can import this
without a cycle.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class OperatorConfig:
    """Runtime knobs for the switchboard. Env overrides via AUREON_OPERATOR_*."""

    # per-line call behaviour
    request_timeout_s: float = 30.0
    max_retries: int = 2                # attempts beyond the first = retries
    retry_backoff_s: float = 0.5        # base; doubles each retry
    max_tokens: int = 800
    temperature: float = 0.5

    # fan-out
    parallel: bool = True
    max_workers: int = 6

    # circuit breaker (per line, per-process)
    breaker_threshold: int = 3          # consecutive failures before a line trips
    breaker_cooldown_s: float = 30.0

    # consensus / veto gates
    consensus_min_agreement: float = 0.0   # informational by default; >0 flags low-coherence
    veto_enabled: bool = True

    # cache
    cache_enabled: bool = True
    cache_ttl_s: float = 900.0
    cache_max_entries: int = 512

    # observability
    metrics_enabled: bool = True
    structured_logs: bool = True

    @classmethod
    def from_env(cls) -> "OperatorConfig":
        return cls(
            request_timeout_s=_env_float("AUREON_OPERATOR_TIMEOUT_S", 30.0),
            max_retries=_env_int("AUREON_OPERATOR_MAX_RETRIES", 2),
            retry_backoff_s=_env_float("AUREON_OPERATOR_RETRY_BACKOFF_S", 0.5),
            max_tokens=_env_int("AUREON_OPERATOR_MAX_TOKENS", 800),
            temperature=_env_float("AUREON_OPERATOR_TEMPERATURE", 0.5),
            parallel=_env_bool("AUREON_OPERATOR_PARALLEL", True),
            max_workers=_env_int("AUREON_OPERATOR_MAX_WORKERS", 6),
            breaker_threshold=_env_int("AUREON_OPERATOR_BREAKER_THRESHOLD", 3),
            breaker_cooldown_s=_env_float("AUREON_OPERATOR_BREAKER_COOLDOWN_S", 30.0),
            consensus_min_agreement=_env_float("AUREON_OPERATOR_MIN_AGREEMENT", 0.0),
            veto_enabled=_env_bool("AUREON_OPERATOR_VETO", True),
            cache_enabled=_env_bool("AUREON_OPERATOR_CACHE", True),
            cache_ttl_s=_env_float("AUREON_OPERATOR_CACHE_TTL_S", 900.0),
            cache_max_entries=_env_int("AUREON_OPERATOR_CACHE_MAX", 512),
            metrics_enabled=_env_bool("AUREON_OPERATOR_METRICS", True),
            structured_logs=_env_bool("AUREON_OPERATOR_STRUCTURED_LOGS", True),
        )


@dataclass
class ModelSpec:
    """One row of the switchboard registry — a model that *may* be dialled."""

    name: str
    kind: str                       # openai | grok | gemini | anthropic | local | recorded | stub
    model: str = ""
    key_env: Optional[str] = None   # env var that must be set for this line to be live
    base_url_env: Optional[str] = None
    enabled: bool = True
    weight: float = 1.0             # consensus weight (reserved for weighted collapse)
    options: dict = field(default_factory=dict)

    def key_present(self) -> bool:
        if not self.key_env:
            return True  # local / recorded / stub lines need no key
        return bool(str(os.environ.get(self.key_env, "") or "").strip())


# The default flagship line-up. Every row is optional; keyless rows are skipped
# at assembly time. This is the "any flagship model, or several" surface.
DEFAULT_REGISTRY: Tuple[ModelSpec, ...] = (
    ModelSpec("openai", "openai", "gpt-4o-mini", key_env="OPENAI_API_KEY", base_url_env="OPENAI_BASE_URL"),
    ModelSpec("grok", "grok", "grok-2-latest", key_env="XAI_API_KEY", base_url_env="XAI_BASE_URL"),
    ModelSpec("gemini", "gemini", "gemini-1.5-flash", key_env="GEMINI_API_KEY", base_url_env="GEMINI_BASE_URL"),
    ModelSpec("anthropic", "anthropic", "claude-3-5-sonnet-latest", key_env="ANTHROPIC_API_KEY"),
    ModelSpec("local", "local", "", key_env=None, base_url_env="AUREON_LLM_BASE_URL", enabled=False),
)


def default_registry() -> List[ModelSpec]:
    return list(DEFAULT_REGISTRY)


__all__ = ["OperatorConfig", "ModelSpec", "DEFAULT_REGISTRY", "default_registry"]
