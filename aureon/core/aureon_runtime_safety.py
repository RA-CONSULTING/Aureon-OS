"""Runtime helpers for Aureon startup and audit paths.

A live child is allowed when ``AUREON_LIVE_TRADING`` is on or an exchange key
group is present, and real orders are not explicitly disabled. With neither a
live flag nor keys, the reason is paper/public-data. These helpers do not
contact an exchange and do not place an order.

``PRODUCTION_RELEASE_ATTESTED`` remains false as a historical constant. It is
not consulted when deciding whether an order environment is live.
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
    "AUREON_RELEASE_STATE": "RELEASE",
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
    "AUREON_LLM_ORDER_AUTHORITY": "1",
    "AUREON_COGNITIVE_ORDER_AUTHORITY": "1",
    "AUREON_LLM_ORDER_INTENT_AUTHORITY": "1",
    "AUREON_COGNITIVE_ORDER_INTENT_AUTHORITY": "1",
    "AUREON_ORDER_AUTHORITY_MODE": "live",
    "AUREON_ORDER_INTENT_PUBLISH": "1",
    "AUREON_UNIFIED_ORDER_EXECUTOR": "1",
    "AUREON_ORDER_TICKET_REQUIRES_EXECUTOR": "0",
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


def offline_boot(environ: MutableMapping[str, str] | None = None) -> bool:
    """An explicit offline boot constructs the engine and does not contact a venue."""
    return env_truthy("AUREON_OFFLINE", environ=environ)


def real_orders_disabled(environ: MutableMapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return (
        env_truthy("AUREON_DISABLE_REAL_ORDERS", environ=env)
        or env_truthy("AUREON_DISABLE_EXCHANGE_MUTATIONS", environ=env)
    )


def live_trading_enabled(environ: MutableMapping[str, str] | None = None) -> bool:
    return env_truthy("AUREON_LIVE_TRADING", environ=environ)


def real_orders_allowed(environ: MutableMapping[str, str] | None = None) -> bool:
    return live_block_reason("runtime", environ) is None


def live_block_reason(
    context: str = "runtime",
    environ: MutableMapping[str, str] | None = None,
) -> str | None:
    env = os.environ if environ is None else environ
    if real_orders_disabled(env):
        return f"{context}: AUREON_DISABLE_REAL_ORDERS=1 blocks live exchange mutations"
    if live_trading_enabled(env):
        return None
    try:
        from aureon.autonomous.autonomy_mode import exchange_keys_present

        # A custom mapping must not inherit host keys. ``None`` means the
        # process environment and the cwd ``.env``.
        if exchange_keys_present(environ=None if environ is None else env):
            return None
    except Exception:
        pass
    return f"{context}: paper/public-data (no exchange keys)"


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
    """Apply the live profile."""

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
        env["AUREON_LIVE_TRADING"] = "1"
        env["AUREON_DISABLE_REAL_ORDERS"] = "0"
        env["AUREON_DISABLE_EXCHANGE_MUTATIONS"] = "0"
        env["AUREON_DRY_RUN"] = "0"
        env["DRY_RUN"] = "0"
        env["LIVE"] = "1"
    else:
        env.update(SAFE_RUNTIME_ENV)
    return env
