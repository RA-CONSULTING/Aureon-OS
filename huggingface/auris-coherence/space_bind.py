"""Guarded Gradio bind for an Aureon Hugging Face Space.

The default listen address is 127.0.0.1. Gradio share stays off.
A 0.0.0.0 bind needs Gary's own yes and an explicit listener flag.
This module does not read a secret file and does not print secret values.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REQUIRED_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP": "1",
    "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
    "AUREON_ENABLE_AUTONOMOUS_CONTROL": "0",
    "AUREON_ACTIVATE_ON_IMPORT": "0",
}

_SECRET_NAMES = {
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "HUGGINGFACE_TOKEN",
    "HF_API_TOKEN",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
}
_SECRET_PARTS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "CREDENTIAL",
    "API_KEY",
    "APIKEY",
    "PRIVATE_KEY",
    "ACCESS_KEY",
)
_SECRET_PREFIXES = (
    "KRAKEN_",
    "BINANCE_",
    "ALPACA_",
    "CAPITAL_",
    "COINBASE_",
)
_DOTENV_NAMES = (".env", ".env.local", ".env.production")


class _BlockDotenv:
    """Refuse python-dotenv so a Space process cannot load a secret file."""

    def find_spec(self, fullname, path, target=None):
        if fullname == "dotenv" or fullname.startswith("dotenv."):
            raise ImportError(
                "dotenv is refused in the Hugging Face Space. No secret file is read."
            )
        return None


def is_secret_name(name: str) -> bool:
    upper = name.upper()
    if upper in _SECRET_NAMES or upper.startswith(_SECRET_PREFIXES):
        return True
    return any(part in upper for part in _SECRET_PARTS)


def scrub(env: dict[str, str]) -> list[str]:
    """Drop secret names from env. The return value is names, never values."""

    removed = []
    for name in list(env):
        if is_secret_name(name) and str(env.get(name, "")).strip():
            env.pop(name, None)
            removed.append(name)
    removed.sort()
    return removed


def install(env: dict[str, str] | None = None, meta_path: list | None = None) -> list[str]:
    """Block dotenv and scrub secrets. Returns the removed names."""

    path = sys.meta_path if meta_path is None else meta_path
    if not any(isinstance(item, _BlockDotenv) for item in path):
        path.insert(0, _BlockDotenv())
    target = os.environ if env is None else env
    return scrub(target)


def assert_no_dotenv_file(space_dir: Path) -> None:
    """Stop when a dotenv file is sitting in the Space directory. Do not open it."""

    for name in _DOTENV_NAMES:
        if (space_dir / name).is_file():
            raise SystemExit(
                f"{name} is in the Space directory. It is not read. "
                "Move it out before launch."
            )


def assert_trading_off(env: dict[str, str]) -> None:
    for name, expected in REQUIRED_ENV.items():
        if env.get(name) != expected:
            raise SystemExit(f"{name} must be {expected}. Live trading stays off.")


def resolve_bind(env: dict[str, str]) -> str:
    """127.0.0.1 unless Gary's yes and the listener flag both ask for 0.0.0.0."""

    if env.get("AUREON_HF_SHARE") == "1" or env.get("GRADIO_SHARE") == "1":
        raise SystemExit("Gradio share is a public listener and stays off.")
    requested = env.get("AUREON_HF_BIND", "127.0.0.1").strip() or "127.0.0.1"
    if requested in {"127.0.0.1", "localhost"}:
        return "127.0.0.1"
    gary = env.get("AUREON_HF_GARY_YES") == "1"
    listener = env.get("AUREON_HF_LISTENER") == "1"
    if requested == "0.0.0.0" and gary and listener:
        return "0.0.0.0"
    raise SystemExit(
        "Hugging Face Space bind stays on 127.0.0.1. "
        "A listener on 0.0.0.0 needs AUREON_HF_GARY_YES=1 and AUREON_HF_LISTENER=1. "
        "Gradio share stays off."
    )


def resolve_port(env: dict[str, str]) -> int:
    raw = env.get("PORT", "7860").strip() or "7860"
    try:
        port = int(raw)
    except ValueError as exc:
        raise SystemExit("PORT must be an integer") from exc
    if port <= 0 or port > 65535:
        raise SystemExit("PORT must be an integer")
    return port


def launch(
    demo,
    *,
    env: dict[str, str] | None = None,
    space_dir: Path | None = None,
    meta_path: list | None = None,
) -> None:
    """Bind the Gradio app. share is always false. Secrets are scrubbed first."""

    target = os.environ if env is None else env
    directory = Path(space_dir) if space_dir is not None else Path(__file__).resolve().parent
    assert_no_dotenv_file(directory)
    install(target, meta_path)
    assert_trading_off(target)
    target["GRADIO_ANALYTICS_ENABLED"] = "0"
    demo.launch(
        server_name=resolve_bind(target),
        server_port=resolve_port(target),
        share=False,
        show_error=False,
    )
