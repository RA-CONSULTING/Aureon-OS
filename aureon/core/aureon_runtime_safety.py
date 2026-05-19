"""Runtime safety helpers for Aureon startup and audit paths.

The codebase has several launchers that can wake up trading systems.  These
helpers keep the safety policy consistent: real exchange mutations are allowed
only when explicitly enabled and when audit/order-disable flags are not set.
"""

from __future__ import annotations

import os
from typing import MutableMapping, Optional

TRUE_VALUES = {"1", "true", "yes", "y", "on"}

SAFE_RUNTIME_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DRY_RUN": "1",
    "DRY_RUN": "1",
    "LIVE": "0",
}

LIVE_RUNTIME_ENV = {
    "AUREON_AUDIT_MODE": "0",
    "AUREON_LIVE_TRADING": "1",
    "AUREON_DISABLE_REAL_ORDERS": "0",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS": "0",
    "AUREON_DRY_RUN": "0",
    "DRY_RUN": "0",
    "LIVE": "1",
    "CONFIRM_LIVE": "yes",
    "KRAKEN_DRY_RUN": "false",
    "BINANCE_DRY_RUN": "false",
    "ALPACA_DRY_RUN": "false",
    "ALPACA_PAPER": "false",
    "PAPER_TRADING": "false",
    "PAPER_MODE": "false",
    "SIMULATION_MODE": "0",
    "DEMO_MODE": "0",
    "AUREON_LLM_LIVE_CAPABILITIES": "1",
    "AUREON_COGNITIVE_LIVE_MODE": "1",
    "AUREON_SELF_QUESTIONING_AI": "1",
    "AUREON_GOAL_CAPABILITY_DIRECTIVE": "goal-capability-v1",
    "AUREON_LLM_ORDER_AUTHORITY": "0",
    "AUREON_COGNITIVE_ORDER_AUTHORITY": "0",
    "AUREON_LLM_ORDER_INTENT_AUTHORITY": "0",
    "AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY": "0",
    "AUREON_ORDER_AUTHORITY_MODE": "runtime_only",
    "AUREON_ORDER_INTENT_PUBLISH": "1",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "1",
    "AUREON_ORDER_TICKET_REQUIRES_EXECUTOR": "1",
}


def env_truthy(
    name: str,
    default: bool = False,
    environ: Optional[MutableMapping[str, str]] = None,
) -> bool:
    env = os.environ if environ is None else environ
    value = env.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in TRUE_VALUES


def audit_mode_enabled(environ: Optional[MutableMapping[str, str]] = None) -> bool:
    return env_truthy("AUREON_AUDIT_MODE", environ=environ)


def real_orders_disabled(environ: Optional[MutableMapping[str, str]] = None) -> bool:
    env = os.environ if environ is None else environ
    return (
        env_truthy("AUREON_DISABLE_REAL_ORDERS", environ=env)
        or env_truthy("AUREON_DISABLE_EXCHANGE_MUTATIONS", environ=env)
    )


def live_trading_enabled(environ: Optional[MutableMapping[str, str]] = None) -> bool:
    return env_truthy("AUREON_LIVE_TRADING", environ=environ)


def real_orders_allowed(environ: Optional[MutableMapping[str, str]] = None) -> bool:
    env = os.environ if environ is None else environ
    return (
        live_trading_enabled(env)
        and not audit_mode_enabled(env)
        and not real_orders_disabled(env)
    )


def live_block_reason(
    context: str = "runtime",
    environ: Optional[MutableMapping[str, str]] = None,
) -> Optional[str]:
    env = os.environ if environ is None else environ
    if audit_mode_enabled(env):
        return f"{context}: AUREON_AUDIT_MODE=1 blocks live exchange mutations"
    if real_orders_disabled(env):
        return f"{context}: AUREON_DISABLE_REAL_ORDERS=1 blocks live exchange mutations"
    if not live_trading_enabled(env):
        return f"{context}: AUREON_LIVE_TRADING is not explicitly enabled"
    return None


def require_real_orders_allowed(
    context: str = "runtime",
    environ: Optional[MutableMapping[str, str]] = None,
) -> None:
    reason = live_block_reason(context, environ)
    if reason:
        raise RuntimeError(reason)


def apply_safe_runtime_environment(
    environ: Optional[MutableMapping[str, str]] = None,
) -> MutableMapping[str, str]:
    env = os.environ if environ is None else environ
    for key, value in SAFE_RUNTIME_ENV.items():
        env[key] = value
    return env


def apply_live_runtime_environment(
    environ: Optional[MutableMapping[str, str]] = None,
) -> MutableMapping[str, str]:
    """Configure an explicit operator-requested live runtime profile.

    This removes audit/dry-run exchange blocks for the trading execution layer
    while keeping LLM/cognitive systems marked as non-order-authoritative.
    """

    env = os.environ if environ is None else environ
    for key, value in LIVE_RUNTIME_ENV.items():
        env[key] = value
    return env


def configure_runtime_environment(
    live: bool,
    environ: Optional[MutableMapping[str, str]] = None,
) -> MutableMapping[str, str]:
    return apply_live_runtime_environment(environ) if live else apply_safe_runtime_environment(environ)


def runtime_mode_snapshot(
    environ: Optional[MutableMapping[str, str]] = None,
) -> dict[str, str]:
    env = os.environ if environ is None else environ
    keys = sorted(set(SAFE_RUNTIME_ENV) | set(LIVE_RUNTIME_ENV))
    return {key: str(env.get(key, "")) for key in keys}


def child_env_for_mode(
    live: bool,
    base: Optional[MutableMapping[str, str]] = None,
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
