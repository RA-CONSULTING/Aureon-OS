"""Local HTTP profile for a self-hosted Aureon machine.

The profile names the bind address and serves the frontend tree over HTTP.
It does not read or write credentials. Live trading stays off.
"""

from __future__ import annotations

import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND = ROOT / "frontend"


def service_environment(organ: str, env: dict | None = None, required: bool = False) -> dict:
    """Return the spawn environment for a local HTTP organ.

    ``required`` means the organ must not start without this profile. The
    profile is this module. It never injects an API key or a secret.
    """

    base = dict(env or {})
    base["AUREON_HTTP_PROFILE"] = "local"
    base["AUREON_LIVE_TRADING"] = "0"
    base["AUREON_FUSION_ARM_LIVE"] = ""
    base["AUREON_DISABLE_REAL_ORDERS"] = "1"
    base["AUREON_DISABLE_EXCHANGE_MUTATIONS"] = "1"
    base["AUREON_ORDER_INTENT_PUBLISH"] = "0"
    if organ == "frontend_vite":
        base.setdefault("AUREON_FRONTEND_HOST", "127.0.0.1")
        base.setdefault("AUREON_FRONTEND_PORT", "5173")
        base.setdefault("AUREON_FRONTEND_ROOT", str(DEFAULT_FRONTEND))
        gateway = (
            os.environ.get("AUREON_SEAT_GATEWAY_PORT")
            or base.get("AUREON_SEAT_GATEWAY_PORT")
            or os.environ.get("AUREON_OPERATOR_PORT")
            or base.get("AUREON_OPERATOR_PORT")
            or "8790"
        )
        market = (
            os.environ.get("AUREON_SEAT_MARKET_PORT")
            or base.get("AUREON_SEAT_MARKET_PORT")
            or "8791"
        )
        gateway = str(gateway)
        market = str(market)
        base["AUREON_SEAT_GATEWAY_PORT"] = gateway
        base["AUREON_SEAT_MARKET_PORT"] = market
        base["AUREON_OPERATOR_PORT"] = gateway
        base["VITE_OPERATOR_PORT"] = gateway
        base["VITE_MARKET_STATUS_PORT"] = market
        base["AUREON_OPERATOR_URL"] = f"http://127.0.0.1:{gateway}"
        base["VITE_OPERATOR_URL"] = f"http://127.0.0.1:{gateway}"
        base["VITE_MARKET_STATUS_URL"] = f"http://127.0.0.1:{market}"
        base["AUREON_TERMINAL_STATE_URL"] = f"http://127.0.0.1:{market}"
    elif organ == "operator_gateway":
        base.setdefault("AUREON_OPERATOR_BIND", "127.0.0.1")
        base.setdefault("AUREON_OPERATOR_HOST", "127.0.0.1")
        base.setdefault("AUREON_OPERATOR_PORT", "8790")
    if required and base.get("AUREON_HTTP_PROFILE") != "local":
        raise RuntimeError("local HTTP profile missing")
    return base


def frontend_command(env: dict | None = None) -> list[str]:
    """Command that serves the frontend tree when the Windows Node path is absent."""

    chosen = service_environment("frontend_vite", env or os.environ, required=True)
    return [
        sys.executable,
        "-m",
        "aureon.operator.local_http_profile",
        "--serve",
        "--host",
        str(chosen["AUREON_FRONTEND_HOST"]),
        "--port",
        str(chosen["AUREON_FRONTEND_PORT"]),
        "--root",
        str(chosen["AUREON_FRONTEND_ROOT"]),
    ]


def serve(host: str, port: int, root: Path) -> None:
    directory = str(root)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aureon.operator.local_http_profile")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--root", default=str(DEFAULT_FRONTEND))
    args = parser.parse_args(argv)
    if not args.serve:
        parser.print_help()
        return 2
    root = Path(args.root)
    if not (root / "index.html").is_file():
        print(f"frontend index missing: {root / 'index.html'}", file=sys.stderr)
        return 2
    print(f"frontend http://{args.host}:{args.port}/  live_trading=false", flush=True)
    serve(args.host, args.port, root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
