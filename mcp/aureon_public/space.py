"""Hugging Face Space entry for aureon-public. This file does not deploy it.

The process sets AUREON_PUBLIC_REQUIRE_PIN=1 and AUREON_OBSERVER_MODE=dry_run.
AUREON_PUBLIC_SWEEP must be unset. The image must not contain an API key.
Set AUREON_PUBLIC_API_KEY at runtime to require a bearer token. Set
AUREON_PUBLIC_OPEN=1, with no key, to serve the read-only surface on a
public bind. With neither, the listener is 127.0.0.1.
"""

from __future__ import annotations

import json
import os
import sys

from aureon_public.http_guard import resolve_http_bind
from aureon_public.server import (
    build_server,
    enforce_public_pin,
    refuse_sweep_environment,
    serve_streamable_http,
)

_QUEEN_MODULE = "queen/temporal_ground.py"
_QUEEN_SYMBOL = "compute_zpe_ground"
_QUEEN_REASON = "plan stage 4 is not open"
_CLOSED_PACKAGES = ("miner", "accounting", "queen", "exchanges", "trading")


def prepare_space_environment() -> None:
    """Pin, dry-run, and the sweep refusal. Does not set a key or OPEN."""

    if os.environ.get("AUREON_PUBLIC_SWEEP"):
        raise SystemExit("AUREON_PUBLIC_SWEEP must not be set. The server will not start.")
    mode = os.environ.get("AUREON_OBSERVER_MODE", "").strip()
    if mode and mode != "dry_run":
        raise SystemExit("AUREON_OBSERVER_MODE must be dry_run.")
    os.environ["AUREON_OBSERVER_MODE"] = "dry_run"
    os.environ["AUREON_PUBLIC_REQUIRE_PIN"] = "1"
    refuse_sweep_environment()
    enforce_public_pin()


def closed_stage_report() -> dict:
    """Stage 3 and 4 stay closed inside this entry point."""

    from aureon_public.body import body_call, package_depth

    depth = package_depth()
    queen_text = body_call(_QUEEN_MODULE, _QUEEN_SYMBOL)
    queen = json.loads(queen_text)
    packages = {name: depth[name] for name in _CLOSED_PACKAGES}
    reachable = {name: packages[name]["reachable"] for name in _CLOSED_PACKAGES}
    queen_refused = queen.get("called") is not True and queen.get("reason") == _QUEEN_REASON
    closed = all(reachable[name] == 0 for name in _CLOSED_PACKAGES)
    return {
        "closed_packages_reachable": reachable,
        "observer_mode": os.environ.get("AUREON_OBSERVER_MODE", ""),
        "ok": bool(queen_refused and closed and os.environ.get("AUREON_OBSERVER_MODE") == "dry_run"),
        "queen_call": queen,
        "require_pin": os.environ.get("AUREON_PUBLIC_REQUIRE_PIN", ""),
        "sweep_set": bool(os.environ.get("AUREON_PUBLIC_SWEEP")),
    }


def space_host() -> str:
    """0.0.0.0 when a key or OPEN=1 allows it. Otherwise 127.0.0.1."""

    requested = os.environ.get("AUREON_PUBLIC_HOST", "").strip()
    if not requested:
        unlocked = bool(os.environ.get("AUREON_PUBLIC_API_KEY", "").strip())
        unlocked = unlocked or os.environ.get("AUREON_PUBLIC_OPEN") == "1"
        requested = "0.0.0.0" if unlocked else "127.0.0.1"
    return resolve_http_bind(requested)


def space_port() -> int:
    raw = os.environ.get("PORT", "7860").strip() or "7860"
    try:
        port = int(raw)
    except ValueError as exc:
        raise SystemExit("PORT must be an integer") from exc
    if port <= 0:
        raise SystemExit("PORT must be an integer")
    return port


def main(argv: list[str] | None = None) -> None:
    """Serve Streamable HTTP, or print the closed-stage report for --check."""

    args = list(sys.argv[1:] if argv is None else argv)
    prepare_space_environment()
    if "--check" in args:
        report = closed_stage_report()
        sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")
        if not report["ok"]:
            raise SystemExit(1)
        return
    host = space_host()
    port = space_port()
    server = build_server(host=host, port=port)
    serve_streamable_http(server, host, port)


if __name__ == "__main__":
    main()
