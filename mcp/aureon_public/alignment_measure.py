"""One stdio session that calls the alignment tools. Writes raw JSON.

Run from measured/aureon_public_alignment_run.sh. Do not hand-edit the output.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from aureon_public import paths
from aureon_public.alignment_layer import TOOLS
from aureon_public.guard_loader import apply_space_guard


def _text_content(result: Any) -> str:
    parts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts)


def _defaults(fn: Any) -> dict[str, Any]:
    signature = inspect.signature(fn)
    arguments = {}
    for name, param in signature.parameters.items():
        if param.default is inspect.Parameter.empty:
            continue
        if param.default == "":
            continue
        arguments[name] = param.default
    return arguments


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
    from aureon_public.measurement_stamp import measurement_stamp

    return {
        "aureon_direct_url": direct,
        "aureon_file": aureon.__file__,
        "python": sys.executable,
        **measurement_stamp(),
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
            calls = {}
            for fn in TOOLS:
                arguments = _defaults(fn)
                result = await session.call_tool(fn.__name__, arguments)
                text = _text_content(result)
                record_call = {
                    "arguments": arguments,
                    "isError": result.isError,
                    "text": text,
                }
                try:
                    body = json.loads(text)
                except json.JSONDecodeError:
                    body = None
                if isinstance(body, dict) and body.get("input_source"):
                    record_call["input_note"] = body.get("input_note")
                    record_call["input_source"] = body["input_source"]
                calls[fn.__name__] = record_call
    record = {"calls": calls, "environment": _environment()}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-alignment-measure")
    parser.add_argument(
        "--out",
        type=Path,
        default=paths.repo_root() / "measured" / "aureon_public_alignment.json",
    )
    args = parser.parse_args(argv)
    asyncio.run(_session(args.out))


if __name__ == "__main__":
    main()
