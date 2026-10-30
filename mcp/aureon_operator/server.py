"""stdio-only operator server. Refuses live orders. Does not start without an env flag."""

from __future__ import annotations

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

from aureon_public.body import body_call_operator
from aureon_public.guard_loader import apply_space_guard
from aureon_public.layers import PACKAGES
from aureon_public.quiet import quiet
from aureon_public.tools import _dumps

OPERATOR_FLAG = "AUREON_OPERATOR_MCP"


def operator_enabled() -> bool:
    return os.environ.get(OPERATOR_FLAG) == "1"


def refuse_start_unless_enabled() -> None:
    """Public default is off. A missing flag is a refusal, not a prompt."""

    if operator_enabled():
        return
    raise SystemExit(
        f"{OPERATOR_FLAG}=1 is required. This server stays off and places no live order."
    )


def refuse_non_stdio(transport: str) -> None:
    if transport != "stdio":
        raise SystemExit("aureon-operator is stdio only. No HTTP transport is started.")


@quiet
def operator_private_layers() -> str:
    """Packages that stay off the public server. Provenance: inferred.

    No blocked module is imported. Live orders are refused. Keys are not read.

    Args:
        none: This tool takes no inputs. Label: inferred, the disposition table.
    """

    rows = [row for row in PACKAGES if row["kind"] == "operator"]
    rows.append(
        {
            "package": "unified_margin_trader",
            "kind": "operator",
            "reason": "Blocked import name. No live orders.",
        }
    )
    return _dumps(
        {
            "label": "inferred. Names only. Imports were not performed.",
            "live_orders": "refused",
            "packages": rows,
            "provenance": "inferred",
            "status": "inferred",
        }
    )


@quiet
def refuse_live_order(symbol: str = "") -> str:
    """Refuse an order. Provenance: cited. No exchange function is called.

    Args:
        symbol: Ignored. Present so a caller can see the refusal. Label: cited, this refusal.
    """

    del symbol
    return _dumps(
        {
            "label": "cited. Live orders are refused. No order function ran.",
            "live_orders": "refused",
            "provenance": "cited",
            "status": "unavailable",
        }
    )


def build_operator_server() -> FastMCP:
    apply_space_guard()
    os.environ["AUREON_DISABLE_REAL_ORDERS"] = "1"
    server = FastMCP(
        "aureon-operator",
        instructions=(
            "Operator stdio server. Live orders are refused. "
            "Keys are not read. AUREON_OPERATOR_MCP=1 is required to start."
        ),
    )
    server.tool()(operator_private_layers)
    server.tool()(refuse_live_order)
    server.tool()(body_call_operator)
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-operator")
    parser.add_argument("--transport", default="stdio")
    args = parser.parse_args(argv)
    refuse_non_stdio(args.transport)
    refuse_start_unless_enabled()
    build_operator_server().run(transport="stdio")


if __name__ == "__main__":
    main()
