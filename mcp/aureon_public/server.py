"""FastMCP server aureon-public. stdio by default, streamable HTTP optional."""

from __future__ import annotations

import argparse
import logging
import sys

from mcp.server.fastmcp import FastMCP

from aureon_public import surfaces, tools
from aureon_public.guard_loader import apply_space_guard
from aureon_public.text import SERVER_PLAIN

SERVER_INSTRUCTIONS = (
    f"{SERVER_PLAIN} "
    "This server is read-only. It does not place orders, read keys, start circulation, "
    "self-code, self-repair, or write the repository or state/."
)


def build_server(host: str = "127.0.0.1", port: int = 8077) -> FastMCP:
    """Register the milestone-1 tools, resources, and prompts."""

    apply_space_guard()
    server = FastMCP(
        "aureon-public",
        instructions=SERVER_INSTRUCTIONS,
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )
    for fn in (
        tools.hnc_reality_step,
        tools.hnc_canonical_read,
        tools.hnc_blend_read,
        tools.lambda_engine_step,
        tools.auris_nodes,
        tools.auris_coherence,
        tools.qgita_analyze,
        tools.organism_replay_read,
        tools.organism_catalog,
    ):
        server.tool()(fn)
    server.resource(
        "aureon://hnc/harmonic-reality/defaults",
        mime_type="application/json",
    )(surfaces.harmonic_reality_defaults)
    server.resource(
        "aureon://hnc/lambda-engine/defaults",
        mime_type="application/json",
    )(surfaces.lambda_engine_defaults)
    server.resource(
        "aureon://hnc/params/code-defaults",
        mime_type="application/json",
    )(surfaces.hnc_params_code_defaults)
    server.resource(
        "aureon://auris/nodes",
        mime_type="application/json",
        description=surfaces.auris_nodes_resource.__doc__,
    )(surfaces.auris_nodes_resource)
    server.resource("aureon://organism/seats", mime_type="application/json")(surfaces.organism_seats_resource)
    server.resource("aureon://organism/nodes", mime_type="application/json")(surfaces.organism_nodes_resource)
    server.resource("aureon://organism/systems", mime_type="application/json")(surfaces.organism_systems_resource)
    server.resource("aureon://holds", mime_type="application/json")(surfaces.holds_resource)
    server.resource("aureon://replay/brain", mime_type="application/json")(surfaces.replay_brain_resource)
    server.resource("aureon://replay/qgita", mime_type="application/json")(surfaces.replay_qgita_resource)
    server.resource("aureon://replay/organism", mime_type="application/json")(surfaces.replay_organism_resource)
    server.resource(
        "aureon://replay/auris",
        mime_type="application/json",
        description=surfaces.replay_auris_resource.__doc__,
    )(surfaces.replay_auris_resource)
    for fn in (
        surfaces.explain_two_lambda_implementations,
        surfaces.explain_auris_four_meanings,
        surfaces.explain_qgita_adapter,
        surfaces.explain_organism_replay,
    ):
        server.prompt()(fn)
    return server


def main(argv: list[str] | None = None) -> None:
    """stdio, or streamable HTTP when --transport streamable-http is set."""

    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="aureon-public")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8077)
    args = parser.parse_args(argv)
    server = build_server(host=args.host, port=args.port)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
