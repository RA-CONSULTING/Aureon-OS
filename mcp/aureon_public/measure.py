"""One stdio session: list the catalog and call each tool once. Writes raw JSON."""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from aureon_public import paths
from aureon_public.guard_loader import apply_space_guard


def _text_content(result: Any) -> str:
    parts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


def _environment() -> dict[str, Any]:
    apply_space_guard()
    import aureon

    direct = None
    try:
        dist = importlib.metadata.distribution("aureon")
        raw = dist.read_text("direct_url.json")
        direct = json.loads(raw) if raw else None
    except Exception as exc:  # noqa: BLE001 - the record should say the pin was not readable
        direct = {"error": type(exc).__name__}
    return {
        "aureon_file": aureon.__file__,
        "aureon_direct_url": direct,
        "python": sys.executable,
    }


async def _session(out_path: Path) -> dict[str, Any]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONUNBUFFERED": "1",
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "aureon_public"],
        env=env,
        cwd=str(Path.cwd()),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()
            calls = {}
            for name, arguments in (
                ("hnc_reality_step", {}),
                ("hnc_canonical_read", {}),
                ("hnc_blend_read", {}),
                ("lambda_engine_step", {}),
                ("auris_nodes", {}),
                ("auris_coherence", {}),
                ("qgita_analyze", {}),
                ("organism_replay_read", {}),
                ("organism_catalog", {}),
            ):
                result = await session.call_tool(name, arguments)
                calls[name] = {
                    "arguments": arguments,
                    "isError": result.isError,
                    "text": _text_content(result),
                }
            # The class default is multiverse on. Record the other committed path
            # beside it so the two coherences are not mixed.
            off = await session.call_tool("hnc_reality_step", {"enable_multiverse": False})
            calls["hnc_reality_step_multiverse_off"] = {
                "arguments": {"enable_multiverse": False},
                "isError": off.isError,
                "text": _text_content(off),
                "note": "Not the class default. Committed multiverse-off path.",
            }
            resource_bodies = {}
            for item in resources.resources:
                uri = str(item.uri)
                body = await session.read_resource(uri)
                chunks = []
                for block in body.contents:
                    content = getattr(block, "content", None)
                    text = getattr(block, "text", None)
                    if text is not None:
                        chunks.append(text)
                    elif content is not None:
                        chunks.append(str(content))
                resource_bodies[uri] = "\n".join(chunks)
            prompt_bodies = {}
            for item in prompts.prompts:
                rendered = await session.get_prompt(item.name)
                messages = []
                for message in rendered.messages:
                    content = message.content
                    messages.append(getattr(content, "text", str(content)))
                prompt_bodies[item.name] = messages
    record = {
        "environment": _environment(),
        "instructions_checked_in_process": True,
        "prompts": [
            {"name": item.name, "description": item.description}
            for item in prompts.prompts
        ],
        "prompt_bodies": prompt_bodies,
        "resources": [
            {"uri": str(item.uri), "name": item.name, "description": item.description}
            for item in resources.resources
        ],
        "resource_bodies": resource_bodies,
        "tools": [
            {
                "name": item.name,
                "description": item.description,
                "inputSchema": item.inputSchema,
            }
            for item in tools.tools
        ],
        "calls": calls,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-measure")
    parser.add_argument(
        "--out",
        type=Path,
        default=paths.repo_root() / "measured" / "aureon_public_run.json",
    )
    args = parser.parse_args(argv)
    asyncio.run(_session(args.out))


if __name__ == "__main__":
    main()
