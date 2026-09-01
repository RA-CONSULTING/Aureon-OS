#!/usr/bin/env python3
"""Inert release facade for the unreleased interactive persona launcher."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict

ASK_AUREON_RELEASE_HOLD = (
    "ask_aureon_hold:production_magic_star_release_unavailable"
)


def preflight() -> Dict[str, Any]:
    return {
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
        "effect_enabled": False,
        "browser_or_repl_started": False,
        "thread_started": False,
        "obsidian_attached": False,
        "vault_mutated": False,
        "bus_mutated": False,
    }


def _raise_hold() -> None:
    raise RuntimeError(ASK_AUREON_RELEASE_HOLD)


def apply_mood(*_args: Any, **_kwargs: Any) -> str:
    _raise_hold()


class PersonaResponseAdapter:
    """Compatibility shell for benchmark discovery; generation is held."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def prompt(self, *_args: Any, **_kwargs: Any) -> Any:
        _raise_hold()

    def stream(self, *_args: Any, **_kwargs: Any) -> Any:
        _raise_hold()

    def health_check(self) -> bool:
        return False


class ConversationSession:
    """Compatibility shell whose mutating conversation methods are held."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.ambient = None
        self.obsidian = None
        self.transcript: list[Dict[str, Any]] = []

    def attach_obsidian(self, *_args: Any, **_kwargs: Any) -> str:
        _raise_hold()

    def mirror_to_obsidian(self, *_args: Any, **_kwargs: Any) -> None:
        _raise_hold()

    def ask(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        _raise_hold()

    def detach_obsidian(self) -> None:
        self.obsidian = None

    def stats(self) -> Dict[str, Any]:
        return dict(preflight(), turns=0)


class AmbientEngine:
    """Compatibility shell that cannot create a background thread."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._running = False

    def start(self) -> None:
        _raise_hold()

    def stop(self) -> None:
        self._running = False

    @property
    def running(self) -> bool:
        return False

    def _loop(self) -> None:
        _raise_hold()

    def _beat(self) -> None:
        _raise_hold()


def _build_session(*_args: Any, **_kwargs: Any) -> ConversationSession:
    _raise_hold()


def main(_argv: list[str] | None = None) -> int:
    print(json.dumps(preflight(), sort_keys=True), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
