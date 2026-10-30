"""FastMCP server aureon-public. stdio by default, streamable HTTP optional."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from aureon_public import body, layers, surfaces, tools
from aureon_public.guard_loader import PINNED_COMMIT, apply_space_guard, aureon_source
from aureon_public.text import SERVER_PLAIN

SERVER_INSTRUCTIONS = (
    f"{SERVER_PLAIN} "
    "This server is read-only. It does not place orders, read keys, start circulation, "
    "self-code, self-repair, or write the repository or state/."
)


def refuse_sweep_environment() -> None:
    """AUREON_PUBLIC_SWEEP is not a server mode. Setting it must not start the server."""

    if os.environ.get("AUREON_PUBLIC_SWEEP"):
        raise SystemExit("AUREON_PUBLIC_SWEEP must not be set. The server will not start.")


def enforce_public_pin(source: dict[str, str] | None = None) -> None:
    """Refuse to start when public hosting requires the pinned commit.

    AUREON_PUBLIC_REQUIRE_PIN=1 is unset for local runs. Those runs still
    report aureon_source. Public hosting must set the variable.
    """

    if os.environ.get("AUREON_PUBLIC_REQUIRE_PIN") != "1":
        return
    current = aureon_source() if source is None else source
    if current.get("kind") == "pinned" and current.get("commit") == PINNED_COMMIT:
        return
    raise SystemExit(
        "AUREON_PUBLIC_REQUIRE_PIN=1 requires aureon_source kind pinned "
        f"at {PINNED_COMMIT}. This process would use {current}."
    )


def build_server(host: str = "127.0.0.1", port: int = 8077) -> FastMCP:
    """Register the milestone-1 tools, resources, and prompts."""

    refuse_sweep_environment()
    apply_space_guard()
    source = aureon_source()
    instructions = (
        f"{SERVER_INSTRUCTIONS} "
        f"aureon_source={json.dumps(source, sort_keys=True)}"
    )
    server = FastMCP(
        "aureon-public",
        instructions=instructions,
        host=host,
        port=port,
        streamable_http_path="/mcp",
        # JSON responses and no session. GET /mcp is not a long-lived event
        # stream. The HTTP guard answers that GET with 405 so it cannot hold
        # an in-flight call slot.
        json_response=True,
        stateless_http=True,
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
        *layers.public_layer_tools(),
        body.body_call,
        body.body_surface,
        body.body_depth,
        body.body_registry,
    ):
        server.tool()(fn)
    server.resource("aureon://packages", mime_type="application/json")(layers.packages_resource)
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
    server.resource("aureon://body/depth", mime_type="application/json")(body.body_depth)
    server.resource("aureon://body/registry", mime_type="application/json")(body.body_registry)
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


def serve_streamable_http(server: FastMCP, host: str, port: int) -> None:
    """Listen with the bearer check and the rate, size, and timeout limits."""

    import uvicorn

    from aureon_public.http_guard import PublicHttpMiddleware, load_http_limits

    app = PublicHttpMiddleware(server.streamable_http_app(), load_http_limits())
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    uvicorn.Server(config).run()


def main(argv: list[str] | None = None) -> None:
    """stdio, or streamable HTTP when --transport streamable-http is set."""

    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="aureon-public")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8077)
    args = parser.parse_args(argv)
    refuse_sweep_environment()
    apply_space_guard()
    enforce_public_pin()
    if args.transport == "stdio":
        build_server().run(transport="stdio")
        return
    from aureon_public.http_guard import resolve_http_bind

    host = resolve_http_bind(args.host)
    server = build_server(host=host, port=args.port)
    serve_streamable_http(server, host, args.port)


if __name__ == "__main__":
    main()
