"""The committed stdio and Streamable HTTP proof, plus the SDK pin."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.timeout(180)


def _record() -> dict:
    return json.loads((ROOT / "measured" / "aureon_public_protocol.json").read_text(encoding="utf-8"))


def _names(pages: list[dict], key: str) -> list[str]:
    names: list[str] = []
    for page in pages:
        for item in page[key]:
            names.append(item["name"])
    return names


def _call_text(result: dict) -> str:
    parts = []
    for block in result["content"]:
        text = block.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts)


def test_mcp_requirement_stays_on_1_30_and_excludes_v2() -> None:
    requirements = (ROOT / "mcp" / "aureon_public" / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (ROOT / "mcp" / "pyproject.toml").read_text(encoding="utf-8")
    plan = (ROOT / "mcp" / "aureon_public" / "COVERAGE_PLAN.md").read_text(encoding="utf-8")
    for text in (requirements, pyproject):
        assert "mcp==1.30.0,<2" in text
    assert "MCPServer" in plan
    assert "The claim is true." in plan
    assert "Migration to SDK v2 is a later decision." in plan
    for source in (
        "https://pypi.org/pypi/mcp/json",
        "https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.0.0",
        "https://py.sdk.modelcontextprotocol.io/v2/migration/",
        "https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp/server/__init__.py",
        "https://github.com/modelcontextprotocol/python-sdk/blob/v2.3.0/src/mcp/server/mcpserver/server.py",
        "https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v2.3.0/src/mcp/server/fastmcp/__init__.py",
        "https://py.sdk.modelcontextprotocol.io/v1/",
    ):
        assert source in plan


def test_protocol_record_has_both_transports_and_the_pin() -> None:
    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.measurement_stamp import CODE_COMMIT_NOTE, PIN_AUREON_TREE
    from aureon_public.server import build_server

    record = _record()
    environment = record["environment"]
    assert environment["require_pin"] == "1"
    assert environment["mcp"] == "1.30.0"
    assert environment["aureon_source"]["kind"] == "pinned"
    assert environment["aureon_source"]["commit"] == PINNED_COMMIT
    assert environment["aureon_tree"] == PIN_AUREON_TREE
    assert environment["pin_aureon_tree"] == PIN_AUREON_TREE
    assert environment["pin"] == PINNED_COMMIT
    assert environment["code_commit_note"] == CODE_COMMIT_NOTE
    assert len(environment["code_commit"]) == 40
    assert "site-packages" in environment["aureon_file"]

    http = record["streamable_http"]
    assert http["host"] == "127.0.0.1"
    assert http["url"] == f"http://127.0.0.1:{http['port']}/mcp"
    assert isinstance(http["port"], int)

    import asyncio

    server = build_server()
    registered = asyncio.run(server.list_tools())
    expected_tools = sorted(item.name for item in registered)
    expected_resources = sorted(str(item.uri) for item in asyncio.run(server.list_resources()))
    expected_prompts = sorted(item.name for item in asyncio.run(server.list_prompts()))

    for transport in (record["stdio"], http):
        assert transport["initialize"]["serverInfo"]["name"] == "aureon-public"
        assert sorted(_names(transport["tools_list"], "tools")) == expected_tools
        assert "alignment_consonance_read" in _names(transport["tools_list"], "tools")
        resource_uris = []
        for page in transport["resources_list"]:
            for item in page["resources"]:
                resource_uris.append(str(item["uri"]))
        assert sorted(resource_uris) == expected_resources
        assert sorted(_names(transport["prompts_list"], "prompts")) == expected_prompts
        call = transport["tools_call"]
        assert call["name"] == "alignment_consonance_read"
        assert call["arguments"] == {"ratio": 1.0}
        assert call["result"]["isError"] is False
        body = json.loads(_call_text(call["result"]))
        assert body["status"] == "cited"
        assert body["called"] is True
        assert body["result"] == 1.0
        assert body["label"] == "cited. alignment/harmonic_resonance.py consonance_score ran."
        assert body["aureon_source"]["kind"] == "pinned"
        assert body["aureon_source"]["commit"] == PINNED_COMMIT
        assert body["input_source"] == "tests/stress/stress_test_inhouse_ai.py::test_harmonic_math"
        assert "consciousness_" not in json.dumps(body)
