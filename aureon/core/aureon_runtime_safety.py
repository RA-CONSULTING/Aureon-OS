"""Terminal-HOLD runtime safety helpers for Aureon startup and audit paths.

Environment flags are untrusted inputs and cannot authorize exchange mutation.
Until an independently attested production release boundary exists, every live
request is forced back to the safe audit profile and real orders remain denied.
"""

from __future__ import annotations

import os
from typing import Final, MutableMapping

TRUE_VALUES = {"1", "true", "yes", "y", "on"}
PRODUCTION_RELEASE_ATTESTED: Final = False

SAFE_RUNTIME_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DRY_RUN": "1",
    "DRY_RUN": "1",
    "LIVE": "0",
}

LIVE_RUNTIME_ENV = {
    "AUREON_RELEASE_STATE": "HOLD",
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "1",
    "AUREON_DRY_RUN": "1",
    "DRY_RUN": "1",
    "LIVE": "0",
    "CONFIRM_LIVE": "no",
    "KRAKEN_DRY_RUN": "true",
    "BINANCE_DRY_RUN": "true",
    "ALPACA_DRY_RUN": "true",
    "ALPACA_PAPER": "true",
    "PAPER_TRADING": "true",
    "PAPER_MODE": "true",
    "SIMULATION_MODE": "1",
    "DEMO_MODE": "1",
    "AUREON_LLM_LIVE_CAPABILITIES": "0",
    "AUREON_COGNITIVE_LIVE_MODE": "0",
    "AUREON_SELF_QUESTIONING_AI": "0",
    "AUREON_GOAL_CAPABILITY_DIRECTIVE": "goal-capability-v1",
    "AUREON_LLM_ORDER_AUTHORITY": "0",
    "AUREON_COGNITIVE_ORDER_AUTHORITY": "0",
    "AUREON_LLM_ORDER_INTENT_AUTHORITY": "0",
    "AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY": "0",
    "AUREON_ORDER_AUTHORITY_MODE": "intent_only_runtime_gated",
    "AUREON_ORDER_INTENT_PUBLISH": "1",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "0",
    "AUREON_ORDER_TICKET_REQUIRES_EXECUTOR": "1",
}


def env_truthy(
    name: str,
    default: bool = False,
    environ: MutableMapping[str, str] | None = None,
) -> bool:
    env = os.environ if environ is None else environ
    value = env.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in TRUE_VALUES


def audit_mode_enabled(environ: MutableMapping[str, str] | None = None) -> bool:
    return env_truthy("AUREON_AUDIT_MODE", environ=environ)


def real_orders_disabled(environ: MutableMapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return (
        env_truthy("AUREON_DISABLE_REAL_ORDERS", environ=env)
        or env_truthy("AUREON_DISABLE_EXCHANGE_MUTATIONS", environ=env)
    )


def live_trading_enabled(environ: MutableMapping[str, str] | None = None) -> bool:
    return env_truthy("AUREON_LIVE_TRADING", environ=environ)


def real_orders_allowed(environ: MutableMapping[str, str] | None = None) -> bool:
    del environ
    return PRODUCTION_RELEASE_ATTESTED


def live_block_reason(
    context: str = "runtime",
    environ: MutableMapping[str, str] | None = None,
) -> str | None:
    env = os.environ if environ is None else environ
    if not PRODUCTION_RELEASE_ATTESTED:
        return f"{context}: terminal production release HOLD blocks exchange mutations"
    if audit_mode_enabled(env):
        return f"{context}: AUREON_AUDIT_MODE=1 blocks live exchange mutations"
    if real_orders_disabled(env):
        return f"{context}: AUREON_DISABLE_REAL_ORDERS=1 blocks live exchange mutations"
    if not live_trading_enabled(env):
        return f"{context}: AUREON_LIVE_TRADING is not explicitly enabled"
    return None


def require_real_orders_allowed(
    context: str = "runtime",
    environ: MutableMapping[str, str] | None = None,
) -> None:
    reason = live_block_reason(context, environ)
    if reason:
        raise RuntimeError(reason)


def apply_safe_runtime_environment(
    environ: MutableMapping[str, str] | None = None,
) -> MutableMapping[str, str]:
    env = os.environ if environ is None else environ
    for key, value in SAFE_RUNTIME_ENV.items():
        env[key] = value
    return env


def apply_live_runtime_environment(
    environ: MutableMapping[str, str] | None = None,
) -> MutableMapping[str, str]:
    """Apply the terminal HOLD profile; environment flags cannot authorize live use."""

    env = os.environ if environ is None else environ
    for key, value in LIVE_RUNTIME_ENV.items():
        env[key] = value
    return env


def configure_runtime_environment(
    live: bool,
    environ: MutableMapping[str, str] | None = None,
) -> MutableMapping[str, str]:
    return apply_live_runtime_environment(environ) if live else apply_safe_runtime_environment(environ)


def runtime_mode_snapshot(
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    env = os.environ if environ is None else environ
    keys = sorted(set(SAFE_RUNTIME_ENV) | set(LIVE_RUNTIME_ENV))
    return {key: str(env.get(key, "")) for key in keys}


def child_env_for_mode(
    live: bool,
    base: MutableMapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env["PYTHONUNBUFFERED"] = "1"
    if live:
        require_real_orders_allowed("child trading process", env)
        env["AUREON_LIVE_TRADING"] = "1"
        env["AUREON_DISABLE_REAL_ORDERS"] = "0"
        env["AUREON_DRY_RUN"] = "0"
        env["DRY_RUN"] = "0"
        env["LIVE"] = "1"
    else:
        env.update(SAFE_RUNTIME_ENV)
    return env
