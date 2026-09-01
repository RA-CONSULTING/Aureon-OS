#!/usr/bin/env python3
"""Inert release facade for the unreleased autonomous persona loop."""

from __future__ import annotations

import json
import sys
from typing import Any, Dict

AUREON_LIVE_RELEASE_HOLD = (
    "run_aureon_live_hold:production_magic_star_release_unavailable"
)


def preflight() -> Dict[str, Any]:
    return {
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
        "effect_enabled": False,
        "bus_wired": False,
        "vault_mutated": False,
        "ambient_thread_started": False,
        "heartbeat_thread_started": False,
        "persona_observed": False,
    }


def _raise_hold() -> None:
    raise RuntimeError(AUREON_LIVE_RELEASE_HOLD)


class AmbientSignals:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._running = False

    def start(self) -> None:
        _raise_hold()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        _raise_hold()


class Heartbeat(AmbientSignals):
    pass


def main(_argv: list[str] | None = None) -> int:
    print(json.dumps(preflight(), sort_keys=True), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
