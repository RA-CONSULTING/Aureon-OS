"""Browser tool: local-page effect, host refusal, and the tenant-plane split.

The Chrome test is marked ``browser`` and is outside the default suite
(``-m "not browser"``). Opt in with ``-m browser``. It skips only when no
Chrome or Chromium binary is on PATH.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.inhouse_ai.browser_tool import (
    BrowserTool,
    default_audit_path,
    find_chrome_binary,
    reset_registry_browser,
    url_refusal,
)
from aureon.inhouse_ai.tool_registry import ToolEffect, ToolRegistry
from aureon.operator.tools import TENANT_ALLOWED_TOOLS, build_operator_tools

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "browser_tool_page.html"
PHRASE = "phi-squared"
_ACTIONS = ["open", "read_text", "click", "type", "screenshot"]


def test_browser_builtin_schema_names_each_action() -> None:
    registry = ToolRegistry(include_builtins=True, hnc_coherence_required=False)
    tool = registry.get("browser")
    assert tool is not None
    assert tool.input_schema["properties"]["action"]["enum"] == _ACTIONS
    assert tool.input_schema["additionalProperties"] is False
    assert tool.input_schema["required"] == ["action"]
    for field in ("url", "css_selector", "text", "path"):
        assert field in tool.input_schema["properties"]
    assert tool.effect == ToolEffect.PRIVILEGED
    assert tool.operation_id == "aureon.inhouse.browser.v1"


def test_non_local_hosts_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_BROWSER_ALLOW_HOSTS", raising=False)
    refused = [
        "https://example.com/",
        "http://example.com/path",
        "http://8.8.8.8/",
        "http://0.0.0.0/",
        "http://127.0.0.1.evil.com/",
        "http://localhost.evil.com/",
        "https://127.0.0.1/",
        "javascript:alert(1)",
        "data:text/html,hi",
        "file://example.com/etc/passwd",
    ]
    for url in refused:
        assert url_refusal(url) is not None, url
    allowed = [
        "http://127.0.0.1/",
        "http://127.0.0.1:8765/index.html",
        "http://localhost/",
        "http://localhost:8080/a",
        "http://[::1]/",
        FIXTURE.as_uri(),
        "file://localhost/tmp/browser_tool_page.html",
    ]
    for url in allowed:
        assert url_refusal(url) is None, url

    audit = tmp_path / "audit.jsonl"
    tool = BrowserTool(audit_path=audit)
    result = tool.open("https://example.com/")
    assert result["ok"] is False
    assert result["refused"] is True
    assert "example.com" in result["error"]
    assert tool.started is False
    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["action"] == "open"
    assert rows[0]["ok"] is False
    assert rows[0]["refused"] is True


def test_allowlist_env_permits_named_hosts_and_keeps_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_BROWSER_ALLOW_HOSTS", raising=False)
    assert url_refusal("https://example.com/") is not None
    monkeypatch.setenv("AUREON_BROWSER_ALLOW_HOSTS", "example.com, CDN.Test")
    assert url_refusal("https://example.com/docs") is None
    assert url_refusal("http://cdn.test/x") is None
    assert url_refusal("https://example.com.evil.test/") is not None
    assert url_refusal("https://other.test/") is not None
    assert url_refusal("http://127.0.0.1:9/") is None
    assert url_refusal("http://localhost/x") is None
    monkeypatch.setenv("AUREON_BROWSER_ALLOW_HOSTS", "*")
    assert url_refusal("https://example.com/") is not None


def test_default_audit_path_is_state_jsonl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_BROWSER_AUDIT_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    assert default_audit_path() == Path("state/browser_tool_audit.jsonl")
    assert default_audit_path().resolve() == (tmp_path / "state" / "browser_tool_audit.jsonl").resolve()
    custom = tmp_path / "custom.jsonl"
    monkeypatch.setenv("AUREON_BROWSER_AUDIT_PATH", str(custom))
    assert default_audit_path() == custom


def test_tenant_plane_lacks_browser_tool() -> None:
    admin = build_operator_tools()
    tenant = build_operator_tools(
        allow_writes=False,
        allow_shell=False,
        allowlist=TENANT_ALLOWED_TOOLS,
    )
    assert "browser" in set(admin.names())
    admin_tool = admin.get("browser")
    assert admin_tool is not None
    assert admin_tool.input_schema["properties"]["action"]["enum"] == _ACTIONS
    assert "browser" not in set(tenant.names())
    assert "browser" not in TENANT_ALLOWED_TOOLS
    assert set(tenant.names()) == {"code_validate"}


def test_browser_actions_require_their_fields(tmp_path: Path) -> None:
    audit = tmp_path / "audit.jsonl"
    tool = BrowserTool(audit_path=audit)
    missing_click = tool.dispatch({"action": "click"})
    missing_type = tool.dispatch({"action": "type", "css_selector": "#phrase"})
    missing_shot = tool.dispatch({"action": "screenshot"})
    unknown = tool.dispatch({"action": "navigate"})
    assert missing_click["ok"] is False and "css_selector" in missing_click["error"]
    assert missing_type["ok"] is False and "text" in missing_type["error"]
    assert missing_shot["ok"] is False and "path" in missing_shot["error"]
    assert unknown["ok"] is False
    assert tool.started is False
    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert [row["action"] for row in rows] == ["click", "type", "screenshot", "navigate"]
    assert all(row["ok"] is False for row in rows)


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_browser_tool_opens_types_clicks_reads_and_screenshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if find_chrome_binary() is None:
        pytest.skip("no Chrome/Chromium binary found")
    audit = tmp_path / "browser_tool_audit.jsonl"
    shot = tmp_path / "shots" / "page.png"
    monkeypatch.setenv("AUREON_BROWSER_AUDIT_PATH", str(audit))
    monkeypatch.delenv("AUREON_BROWSER_ALLOW_HOSTS", raising=False)
    reset_registry_browser()
    registry = build_operator_tools(hnc_coherence_required=False)
    try:
        opened = json.loads(registry.execute("browser", {"action": "open", "url": FIXTURE.as_uri()}))
        assert opened["ok"] is True, opened
        assert opened["refused"] is False
        typed = json.loads(
            registry.execute(
                "browser",
                {"action": "type", "css_selector": "#phrase", "text": PHRASE},
            )
        )
        assert typed["ok"] is True, typed
        clicked = json.loads(registry.execute("browser", {"action": "click", "css_selector": "#commit"}))
        assert clicked["ok"] is True, clicked
        read = json.loads(registry.execute("browser", {"action": "read_text"}))
        assert read["ok"] is True, read
        assert f"committed:{PHRASE}" in read["text"]
        saved = json.loads(registry.execute("browser", {"action": "screenshot", "path": str(shot)}))
        assert saved["ok"] is True, saved
    finally:
        reset_registry_browser()

    png = shot.read_bytes()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 8
    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [row["action"] for row in rows] == ["open", "type", "click", "read_text", "screenshot"]
    assert all(row["ok"] is True and row["refused"] is False for row in rows)
    assert rows[0]["url"].startswith("file:")
    assert rows[1]["css_selector"] == "#phrase"
    assert rows[1]["text"] == PHRASE
    assert rows[2]["css_selector"] == "#commit"
    assert rows[4]["path"] == str(shot)
    assert all("ts" in row for row in rows)
