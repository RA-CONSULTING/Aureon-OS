"""Process-wide credential isolation for held, non-executor cloud services.

The Cloud Run trading executor is the sole cloud process allowed to receive the
owner exchange bundle.  VM operator/read services load a large legacy Python
graph, and several of those modules still call ``load_dotenv(override=True)`` or
copy credential aliases from an encrypted keystore.  A one-time environment
scrub is therefore insufficient: a later import could put authority back.

This module installs a guarded ``os.environ`` before application imports.  The
guard permanently rejects every exchange credential alias consumed by the
repository and pins exchange mode flags to their held values.  It is independent
of python-dotenv behaviour and version.  Provider values are deliberately not in
the deny set; the validated NASA/NOAA/USGS/Ollama bundle remains available to
the operator and the two explicitly selected read organs.
"""
from __future__ import annotations

from collections.abc import Iterator, MutableMapping
import os
import sys
from typing import Any


CLOUD_CREDENTIAL_ISOLATION_ENV = "AUREON_CLOUD_CREDENTIAL_ISOLATION"
CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV = "AUREON_CLOUD_EXCHANGE_CREDENTIALS_PINNED"
PINNED_PROVIDER_ENV_VARS_ENV = "AUREON_PINNED_PROVIDER_ENV_VARS"

# Closed census of exchange credential names consumed by Python/TypeScript
# sources, the shared Aureon alias resolver, and preserved diagnostics.  Do not
# reduce this to the four canonical schemas: legacy loaders resolve these names
# bidirectionally and can otherwise recreate canonical authority after boot.
CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS = frozenset({
    "ALPACA_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET",
    "ALPACA_API_SECRET_KEY",
    "ALPACA_KEY",
    "ALPACA_SECRET",
    "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID",
    "APCA_API_SECRET_KEY",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "BINANCE_KEY",
    "BINANCE_SECRET",
    "BINANCE_SECRET_KEY",
    "BINANCE_TESTNET_API_KEY",
    "BINANCE_TESTNET_API_SECRET",
    "CAPITAL_API_KEY",
    "CAPITAL_API_PASSWORD",
    "CAPITAL_API_SECRET",
    "CAPITAL_EMAIL",
    "CAPITAL_IDENTIFIER",
    "CAPITAL_PASSWORD",
    "CAPITAL_USER",
    "KRAKEN_API_KEY",
    "KRAKEN_API_SECRET",
    "KRAKEN_PRIVATE_KEY",
    "KRAKEN_SECRET",
})

CLOUD_ENV_LOADER_CONTROL_VARS = frozenset({
    "AUREON_ENV_FILE",
    "DOTENV_PATH",
    "AUREON_HNC_PACKET_MASTER_KEY",
    "HNC_PACKET_MASTER_KEY",
})

CLOUD_EXCHANGE_MODE_ENV_VARS = frozenset({
    "ENABLE_ALPACA",
    "ENABLE_BINANCE",
    "ENABLE_CAPITAL",
    "ENABLE_KRAKEN",
    "ALPACA_LIVE",
    "APCA_LIVE",
    "BINANCE_LIVE",
    "CAPITAL_LIVE",
    "KRAKEN_LIVE",
    "KRAKEN_LIVE_ENABLED",
    "ALPACA_DRY_RUN",
    "ALPACA_PAPER",
    "BINANCE_DRY_RUN",
    "BINANCE_TESTNET",
    "BINANCE_USE_TESTNET",
    "CAPITAL_DEMO",
    "CAPITAL_DEMO_MODE",
    "KRAKEN_DRY_RUN",
    "CONFIRM_LIVE",
    "DRY_RUN",
    "LIVE",
})

CLOUD_OPERATOR_SAFE_MODE_ENV = {
    "ALPACA_DRY_RUN": "true",
    "ALPACA_PAPER": "true",
    "APCA_LIVE": "false",
    "BINANCE_DRY_RUN": "true",
    "BINANCE_TESTNET": "false",
    "BINANCE_USE_TESTNET": "false",
    "CAPITAL_DEMO": "1",
    "CAPITAL_DEMO_MODE": "1",
    "KRAKEN_DRY_RUN": "true",
    "KRAKEN_LIVE_ENABLED": "false",
    "CONFIRM_LIVE": "no",
    "DRY_RUN": "true",
    "LIVE": "0",
}

CLOUD_OPERATOR_SCRUBBED_ENV_VARS = frozenset(
    CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS
    | CLOUD_ENV_LOADER_CONTROL_VARS
    | CLOUD_EXCHANGE_MODE_ENV_VARS
)


def scrub_cloud_exchange_authority(environment: MutableMapping[str, str]) -> None:
    """Remove all inherited authority and install the held exchange modes."""
    for name in CLOUD_OPERATOR_SCRUBBED_ENV_VARS:
        environment.pop(name, None)
    environment.update(CLOUD_OPERATOR_SAFE_MODE_ENV)
    environment[CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV] = "1"
    environment["PYTHON_DOTENV_DISABLED"] = "1"


class CloudCredentialEnvironment(MutableMapping[str, str]):
    """Environment mapping that cannot acquire exchange credentials later."""

    def __init__(self, backing: MutableMapping[str, str]) -> None:
        self._backing = backing
        self._forbidden = frozenset(
            CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS
            | CLOUD_ENV_LOADER_CONTROL_VARS
            | (CLOUD_EXCHANGE_MODE_ENV_VARS - CLOUD_OPERATOR_SAFE_MODE_ENV.keys())
        )
        self._pinned = {
            **CLOUD_OPERATOR_SAFE_MODE_ENV,
            CLOUD_CREDENTIAL_ISOLATION_ENV: "1",
            CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV: "1",
            "PYTHON_DOTENV_DISABLED": "1",
        }
        self._backing.update(self._pinned)

    def __getitem__(self, key: str) -> str:
        if key in self._forbidden:
            raise KeyError(key)
        return self._backing[key]

    def __setitem__(self, key: str, value: str) -> None:
        if key in self._forbidden:
            self._backing.pop(key, None)
            return
        if key in self._pinned:
            self._backing[key] = self._pinned[key]
            return
        self._backing[key] = value

    def __delitem__(self, key: str) -> None:
        if key in self._forbidden:
            self._backing.pop(key, None)
            return
        if key in self._pinned:
            self._backing[key] = self._pinned[key]
            return
        del self._backing[key]

    def __iter__(self) -> Iterator[str]:
        return (key for key in self._backing if key not in self._forbidden)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def copy(self) -> dict[str, str]:
        """Match os._Environ.copy() for subprocess and legacy callers."""
        return {key: self._backing[key] for key in self}

    def clear(self) -> None:
        """Clear ordinary values without looping on the non-removable pins."""
        for key in tuple(self):
            if key not in self._pinned:
                self._backing.pop(key, None)
        self._backing.update(self._pinned)

    def popitem(self) -> tuple[str, str]:
        for key in tuple(self):
            if key not in self._pinned:
                value = self._backing.pop(key)
                return key, value
        raise KeyError("cloud environment contains only pinned values")

    def pin(self, values: MutableMapping[str, str] | dict[str, str]) -> None:
        """Pin validated non-exchange values against later dotenv replacement."""
        for key, value in values.items():
            if key in self._forbidden:
                continue
            self._backing[key] = value
            self._pinned[key] = value

    @property
    def forbidden_names(self) -> frozenset[str]:
        return self._forbidden

    @property
    def pinned_values(self) -> dict[str, str]:
        return dict(self._pinned)


_ORIGINAL_PUTENV = os.putenv
_ORIGINAL_UNSETENV = os.unsetenv
_ACTIVE_GUARD: CloudCredentialEnvironment | None = None


def _name_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode(sys.getfilesystemencoding(), "surrogateescape")
    return str(value)


def _value_like(key: Any, value: str) -> Any:
    if isinstance(key, bytes):
        return value.encode(sys.getfilesystemencoding(), "surrogateescape")
    return value


def _guarded_putenv(key: Any, value: Any) -> None:
    guard = _ACTIVE_GUARD
    name = _name_text(key)
    if guard is not None and name in guard.forbidden_names:
        _ORIGINAL_UNSETENV(key)
        return
    if guard is not None and name in guard.pinned_values:
        value = _value_like(key, guard.pinned_values[name])
    _ORIGINAL_PUTENV(key, value)


def _guarded_unsetenv(key: Any) -> None:
    guard = _ACTIVE_GUARD
    name = _name_text(key)
    if guard is not None and name in guard.pinned_values:
        _ORIGINAL_PUTENV(key, _value_like(key, guard.pinned_values[name]))
        return
    _ORIGINAL_UNSETENV(key)


def _pinned_provider_values(environment: MutableMapping[str, str]) -> dict[str, str]:
    names = {
        name.strip()
        for name in str(environment.get(PINNED_PROVIDER_ENV_VARS_ENV, "") or "").split(",")
        if name.strip()
    }
    values = {name: environment[name] for name in names if name in environment}
    marker = environment.get(PINNED_PROVIDER_ENV_VARS_ENV)
    if marker:
        values[PINNED_PROVIDER_ENV_VARS_ENV] = marker
    return values


def install_cloud_environment_guard() -> CloudCredentialEnvironment:
    """Install the process boundary once, before any application import."""
    global _ACTIVE_GUARD
    if isinstance(os.environ, CloudCredentialEnvironment):
        _ACTIVE_GUARD = os.environ
        os.environ.pin(_pinned_provider_values(os.environ))
        return os.environ

    original = os.environ
    provider_values = _pinned_provider_values(original)
    scrub_cloud_exchange_authority(original)
    guard = CloudCredentialEnvironment(original)
    guard.pin(provider_values)
    _ACTIVE_GUARD = guard
    os.environ = guard
    # Cover direct os.putenv/os.unsetenv calls as well as Mapping writes.  The
    # original os._Environ methods resolve these module globals dynamically.
    os.putenv = _guarded_putenv
    os.unsetenv = _guarded_unsetenv
    return guard


def pin_validated_environment(values: dict[str, str]) -> None:
    """Pin a validated Secret Manager bundle after in-process retrieval."""
    guard = install_cloud_environment_guard()
    pinned = dict(values)
    marker = os.environ.get(PINNED_PROVIDER_ENV_VARS_ENV)
    if marker:
        pinned[PINNED_PROVIDER_ENV_VARS_ENV] = marker
    guard.pin(pinned)


__all__ = [
    "CLOUD_CREDENTIAL_ISOLATION_ENV",
    "CLOUD_EXCHANGE_CREDENTIALS_PINNED_ENV",
    "CLOUD_EXCHANGE_CREDENTIAL_ENV_VARS",
    "CLOUD_ENV_LOADER_CONTROL_VARS",
    "CLOUD_EXCHANGE_MODE_ENV_VARS",
    "CLOUD_OPERATOR_SAFE_MODE_ENV",
    "CLOUD_OPERATOR_SCRUBBED_ENV_VARS",
    "CloudCredentialEnvironment",
    "scrub_cloud_exchange_authority",
    "install_cloud_environment_guard",
    "pin_validated_environment",
]
