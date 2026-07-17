"""Shared environment loading for Aureon runtime entrypoints.

This keeps live launchers, exchange clients, and diagnostics aligned on one
repo-local .env loading policy without ever logging secret values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, MutableMapping, Optional

from aureon.harmonic.hnc_quantum_packet_crypto import (
    ENV_PACKET_PREFIX,
    HNCPacketError,
    LEGACY_MASTER_KEY_ENV,
    MASTER_KEY_ENV,
    decode_env_packet,
    is_env_packet,
)


SECRET_KEYS = {
    "KRAKEN_API_KEY",
    "KRAKEN_API_SECRET",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "BINANCE_SECRET_KEY",
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "CAPITAL_API_KEY",
    "CAPITAL_PASSWORD",
    "CAPITAL_API_PASSWORD",
    "CAPITAL_API_SECRET",
    "COINAPI_API_KEY",
    "COINAPI_KEY",
    "SUPABASE_ANON_KEY",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
    "GEMINI_API_KEY",
    "ANTHROPIC_API_KEY",
    MASTER_KEY_ENV,
    LEGACY_MASTER_KEY_ENV,
}

KRAKEN_REQUIRED_ENV = ("KRAKEN_API_KEY", "KRAKEN_API_SECRET")

CREDENTIAL_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ALPACA_API_SECRET", ("ALPACA_SECRET_KEY", "ALPACA_SECRET")),
    ("ALPACA_KEY", ("ALPACA_API_KEY",)),
    ("ALPACA_SECRET", ("ALPACA_SECRET_KEY", "ALPACA_API_SECRET")),
    ("APCA_API_KEY_ID", ("ALPACA_API_KEY",)),
    ("APCA_API_SECRET_KEY", ("ALPACA_SECRET_KEY", "ALPACA_API_SECRET", "ALPACA_SECRET")),
    ("BINANCE_SECRET", ("BINANCE_API_SECRET", "BINANCE_SECRET_KEY")),
    ("BINANCE_KEY", ("BINANCE_API_KEY",)),
    ("BINANCE_SECRET_KEY", ("BINANCE_API_SECRET", "BINANCE_SECRET")),
    ("CAPITAL_API_PASSWORD", ("CAPITAL_PASSWORD",)),
    ("CAPITAL_API_SECRET", ("CAPITAL_PASSWORD", "CAPITAL_API_PASSWORD")),
    ("CAPITAL_DEMO_MODE", ("CAPITAL_DEMO",)),
    ("CAPITAL_USER", ("CAPITAL_IDENTIFIER",)),
    ("COINAPI_API_KEY", ("COINAPI_KEY",)),
    ("SUPABASE_URL", ("VITE_SUPABASE_URL",)),
    ("SUPABASE_ANON_KEY", ("VITE_SUPABASE_PUBLISHABLE_KEY",)),
)

EXCHANGE_REQUIRED_ENV: dict[str, tuple[str, ...]] = {
    "kraken": ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"),
    "binance": ("BINANCE_API_KEY", "BINANCE_API_SECRET"),
    "alpaca": ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
    "capital": ("CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD"),
}

EXCHANGE_ENABLE_FLAGS: dict[str, tuple[str, ...]] = {
    "kraken": ("ENABLE_KRAKEN", "KRAKEN_LIVE"),
    "binance": ("ENABLE_BINANCE", "BINANCE_LIVE"),
    "alpaca": ("ENABLE_ALPACA", "ALPACA_LIVE"),
    "capital": ("ENABLE_CAPITAL", "CAPITAL_LIVE"),
}

# ── AI provider credentials for the Aureon Operator switchboard ───────────────
# Mirrors EXCHANGE_REQUIRED_ENV: each provider is only fanned out to when its
# key is present. Absent keys degrade gracefully to stub/local adapters so the
# operator always runs offline (see aureon/operator/providers.py).
AI_PROVIDER_REQUIRED_ENV: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "grok": ("XAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
}

TRUTHY = {"1", "true", "yes", "y", "on"}


@dataclass
class EnvLoadReport:
    loaded: bool
    loaded_paths: list[str] = field(default_factory=list)
    candidate_paths: list[str] = field(default_factory=list)
    aliases_applied: list[dict[str, str]] = field(default_factory=list)
    packets_decoded: list[dict[str, str]] = field(default_factory=list)
    packet_errors: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "loaded": self.loaded,
            "loaded_paths": list(self.loaded_paths),
            "candidate_paths": list(self.candidate_paths),
            "aliases_applied": list(self.aliases_applied),
            "packets_decoded": list(self.packets_decoded),
            "packet_errors": list(self.packet_errors),
            "errors": list(self.errors),
        }


def resolve_repo_root(start: Optional[Path] = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def candidate_env_paths(repo_root: Optional[Path] = None) -> list[Path]:
    root = resolve_repo_root(repo_root)
    candidates: list[Path] = []
    for env_name in ("AUREON_ENV_FILE", "DOTENV_PATH"):
        value = os.environ.get(env_name, "").strip()
        if value:
            candidates.append(Path(value).expanduser())

    candidates.extend(
        [
            root / ".env",
            root / ".env.local",
            root / ".env.production",
        ]
    )

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        try:
            key = str(candidate.resolve())
        except Exception:
            key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _parse_env_line(line: str) -> Optional[tuple[str, str]]:
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.startswith("export "):
        raw = raw[len("export ") :].strip()
    if "=" not in raw:
        return None
    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if (
        len(value) >= 2
        and value[0] == value[-1]
        and value[0] in {"'", '"'}
    ):
        value = value[1:-1]
    return key, value


def _fallback_load_env_file(
    path: Path,
    environ: MutableMapping[str, str],
    override: bool,
) -> None:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = _parse_env_line(line)
        if not parsed:
            continue
        key, value = parsed
        if override or key not in environ:
            environ[key] = value


def apply_env_aliases(
    environ: Optional[MutableMapping[str, str]] = None,
    *,
    override: bool = False,
) -> list[dict[str, str]]:
    env = os.environ if environ is None else environ
    applied: list[dict[str, str]] = []
    for target, sources in CREDENTIAL_ALIASES:
        if not override and str(env.get(target, "") or "").strip():
            continue
        for source in sources:
            source_value = str(env.get(source, "") or "")
            if source_value.strip():
                env[target] = source_value
                applied.append({"target": target, "source": source})
                break
    return applied


def decode_hnc_env_packets(
    environ: Optional[MutableMapping[str, str]] = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    env = os.environ if environ is None else environ
    master_key = str(env.get(MASTER_KEY_ENV) or env.get(LEGACY_MASTER_KEY_ENV) or "").strip()
    decoded: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    if not master_key:
        return decoded, errors
    for key, value in list(env.items()):
        if key in {MASTER_KEY_ENV, LEGACY_MASTER_KEY_ENV}:
            continue
        if not is_env_packet(value):
            continue
        try:
            env[key] = decode_env_packet(str(value), master_key, env_key=key)
            decoded.append({"key": key, "format": ENV_PACKET_PREFIX.rstrip(":")})
        except HNCPacketError as exc:
            errors.append({"key": key, "error": str(exc)})
        except Exception as exc:
            errors.append({"key": key, "error": f"{type(exc).__name__}: {exc}"})
    return decoded, errors


def load_aureon_environment(
    repo_root: Optional[Path] = None,
    *,
    override: bool = False,
    environ: Optional[MutableMapping[str, str]] = None,
) -> EnvLoadReport:
    env = os.environ if environ is None else environ
    candidates = candidate_env_paths(repo_root)
    report = EnvLoadReport(
        loaded=False,
        candidate_paths=[str(path) for path in candidates],
    )

    for path in candidates:
        try:
            if not path.exists() or not path.is_file():
                continue
            try:
                if env is os.environ:
                    from dotenv import load_dotenv

                    load_dotenv(dotenv_path=str(path), override=override)
                else:
                    _fallback_load_env_file(path, env, override=override)
                loaded = True
            except Exception:
                _fallback_load_env_file(path, env, override=override)
                loaded = True
            if loaded:
                report.loaded = True
                report.loaded_paths.append(str(path))
        except Exception as exc:
            report.errors.append(f"{path}: {type(exc).__name__}: {exc}")
    report.packets_decoded, report.packet_errors = decode_hnc_env_packets(env)
    report.aliases_applied = apply_env_aliases(env, override=False)
    return report


# The credentials the long-running HNC processes actually consume. Reported as
# presence booleans only by ``bootstrap_credentials`` — never their values.
HNC_RUNTIME_KEYS: tuple[str, ...] = (
    "NASA_API_KEY",
    "NOAA_API_KEY",
    "USGS_API_KEY",
    "FIRMS_MAP_KEY",
    "FRED_API_KEY",
    "AUREON_LLM_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
)


def bootstrap_credentials(
    repo_root: Optional[Path] = None,
    *,
    override: bool = False,
) -> dict:
    """One call every HNC entrypoint makes so **all keys** reach the process.

    Composes the two credential planes the repo already has:

      1. ``load_aureon_environment`` — the canonical ``.env`` policy (all
         candidate paths + HNC env-packet decode + credential aliases).
      2. the encrypted provider keystore (the Providers/Connections UI control
         plane) — layered on top so UI-stored keys take effect too.

    Returns a small, secret-safe self-check the daemons can log at boot:
    presence **booleans only** for the runtime keys — never a value, never a
    length that could leak a short secret. Never raises: a missing keystore or
    dotenv degrades to "just what's already in the environment".
    """
    report = load_aureon_environment(repo_root, override=override)

    keystore_applied = False
    try:  # best effort — the keystore is optional (needs the operator extra)
        from aureon.operator import keystore

        keystore.apply_to_env()
        keystore_applied = True
    except Exception:  # noqa: BLE001 - a missing/locked keystore must not be fatal
        keystore_applied = False

    try:  # best effort — the feature switchboard is the human on/off control plane
        from aureon.operator import feature_switchboard

        feature_switchboard.apply_to_env()
    except Exception:  # noqa: BLE001 - a missing/locked store must not be fatal
        pass

    present = {key: bool(info["set"]) for key, info in env_presence(HNC_RUNTIME_KEYS).items()}
    return {
        "loaded": report.loaded,
        "loaded_paths": list(report.loaded_paths),
        "aliases_applied": len(report.aliases_applied),
        "packets_decoded": len(report.packets_decoded),
        "keystore_applied": keystore_applied,
        "present": present,
    }


def env_truthy(
    name: str,
    environ: Optional[MutableMapping[str, str]] = None,
    default: bool = False,
) -> bool:
    env = os.environ if environ is None else environ
    value = env.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in TRUTHY


def enabled_credential_groups(
    environ: Optional[MutableMapping[str, str]] = None,
) -> dict[str, tuple[str, ...]]:
    env = os.environ if environ is None else environ
    groups: dict[str, tuple[str, ...]] = {}
    for exchange, flags in EXCHANGE_ENABLE_FLAGS.items():
        if any(env_truthy(flag, env) for flag in flags):
            groups[exchange] = EXCHANGE_REQUIRED_ENV[exchange]
    return groups


def env_presence(
    keys: Iterable[str],
    environ: Optional[MutableMapping[str, str]] = None,
) -> dict[str, dict[str, object]]:
    env = os.environ if environ is None else environ
    status: dict[str, dict[str, object]] = {}
    for key in keys:
        value = str(env.get(key, "") or "")
        status[key] = {
            "set": bool(value.strip()),
            "length": len(value),
            "secret": key in SECRET_KEYS,
            "hnc_packet": is_env_packet(value),
        }
    return status


def missing_env(
    keys: Iterable[str],
    environ: Optional[MutableMapping[str, str]] = None,
) -> list[str]:
    env = os.environ if environ is None else environ
    return [key for key in keys if not str(env.get(key, "") or "").strip()]


def env_status_summary(keys: Iterable[str]) -> str:
    presence = env_presence(keys)
    return ", ".join(f"{key}={'set' if info['set'] else 'missing'}" for key, info in presence.items())


__all__ = [
    "AI_PROVIDER_REQUIRED_ENV",
    "CREDENTIAL_ALIASES",
    "EnvLoadReport",
    "EXCHANGE_REQUIRED_ENV",
    "HNC_RUNTIME_KEYS",
    "KRAKEN_REQUIRED_ENV",
    "apply_env_aliases",
    "bootstrap_credentials",
    "candidate_env_paths",
    "enabled_credential_groups",
    "decode_hnc_env_packets",
    "env_presence",
    "env_status_summary",
    "env_truthy",
    "load_aureon_environment",
    "missing_env",
    "resolve_repo_root",
]
