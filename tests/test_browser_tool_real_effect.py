"""Browser tool: local-page effect, host refusal, and the tenant-plane split.

The Chrome test is marked ``browser`` and is outside the default suite
(``-m "not browser"``). Opt in with ``-m browser``. It skips only when no
Chrome or Chromium binary is on PATH.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
DUMMY_KEY = "dummy-key-HOLD-a1b2"
DUMMY_PASSWORD = "dummy-password-HOLD-9f3c"
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
        "http://127.0.0.2/",
        "javascript:alert(1)",
        "data:text/html,hi",
        "file://example.com/etc/passwd",
        FIXTURE.as_uri(),
        "file://localhost/tmp/browser_tool_page.html",
    ]
    for url in refused:
        assert url_refusal(url) is not None, url
    allowed = [
        "http://127.0.0.1/",
        "http://127.0.0.1:8765/index.html",
        "http://localhost/",
        "http://localhost:8080/a",
        "http://[::1]/",
    ]
    for url in allowed:
        assert url_refusal(url) is None, url
    monkeypatch.setenv("AUREON_BROWSER_FILE_ROOT", str(FIXTURE.parent))
    assert url_refusal(FIXTURE.as_uri()) is None

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
    escaped = tmp_path / "nope" / "nested" / "x.png"
    outside = tool.dispatch({"action": "screenshot", "path": str(escaped)})
    unknown = tool.dispatch({"action": "navigate"})
    assert missing_click["ok"] is False and "css_selector" in missing_click["error"]
    assert missing_type["ok"] is False and "text" in missing_type["error"]
    assert missing_shot["ok"] is False and "no page open" in missing_shot["error"]
    assert outside["ok"] is False and outside["refused"] is True
    assert not (tmp_path / "nope").exists()
    assert unknown["ok"] is False
    assert tool.started is False
    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert [row["action"] for row in rows] == ["click", "type", "screenshot", "screenshot", "navigate"]
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
    scratch = tmp_path / "scratch"
    shots = tmp_path / "screens"
    scratch.mkdir()
    shots.mkdir()
    page = scratch / "page.html"
    page.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("AUREON_BROWSER_AUDIT_PATH", str(audit))
    monkeypatch.setenv("AUREON_BROWSER_FILE_ROOT", str(scratch))
    monkeypatch.setenv("AUREON_BROWSER_SCREENSHOT_DIR", str(shots))
    monkeypatch.delenv("AUREON_BROWSER_ALLOW_HOSTS", raising=False)
    reset_registry_browser()
    registry = build_operator_tools(hnc_coherence_required=False)
    try:
        opened = json.loads(registry.execute("browser", {"action": "open", "url": page.as_uri()}))
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
        saved = json.loads(registry.execute("browser", {"action": "screenshot"}))
        assert saved["ok"] is True, saved
    finally:
        reset_registry_browser()

    shot = Path(saved["path"])
    assert shot.parent == shots.resolve() or shot.parent == shots
    png = shot.read_bytes()
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 8
    raw_audit = audit.read_text(encoding="utf-8")
    assert PHRASE not in raw_audit
    rows = [json.loads(line) for line in raw_audit.splitlines() if line.strip()]
    assert [row["action"] for row in rows] == ["open", "type", "click", "read_text", "screenshot"]
    assert all(row["ok"] is True and row["refused"] is False for row in rows)
    assert rows[0]["url"].startswith("file:")
    assert rows[1]["css_selector"] == "#phrase"
    assert rows[1]["text_length"] == len(PHRASE)
    assert rows[1]["text_sha256"] == hashlib.sha256(PHRASE.encode()).hexdigest()
    assert "text" not in rows[1]
    assert rows[2]["css_selector"] == "#commit"
    assert str(shots) in rows[4]["path"]
    assert all("ts" in row for row in rows)


def _need_chrome() -> None:
    if find_chrome_binary() is None:
        pytest.skip("no Chrome/Chromium binary found")


def _quiet_handler(hits: list[str], lock: threading.Lock, redirect_to: str = "") -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if redirect_to and path == "/redir":
                self.send_response(302)
                self.send_header("Location", redirect_to)
                self.end_headers()
                return
            if path == "/page":
                body = (
                    "<!DOCTYPE html><html><body>"
                    f"<img src='{redirect_to.rsplit('/', 1)[0]}/img' alt=''>"
                    "<a id='out' href='" + redirect_to.rsplit("/", 1)[0] + "/click'>leave</a>"
                    "<script>fetch('" + redirect_to.rsplit("/", 1)[0] + "/fetch').catch(function(){});</script>"
                    "<p id='here'>local-page</p></body></html>"
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            with lock:
                hits.append(path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"hit")

        def log_message(self, _format: str, *_args: object) -> None:
            return

    return Handler


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_file_secrets_and_run_symlinks_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _need_chrome()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "page.html").write_text("<html><body><p>scratch-page</p></body></html>", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / ".env").write_text(DUMMY_KEY + "\n", encoding="utf-8")
    (scratch / "notes.html").symlink_to(outside / ".env")
    (scratch / ".env").write_text(DUMMY_KEY + "\n", encoding="utf-8")
    (scratch / "demo.key").write_text(DUMMY_KEY + "\n", encoding="utf-8")
    run = tmp_path / "aureon_run_probe"
    run.mkdir()
    (run / "data.txt").write_text(DUMMY_KEY + "\n", encoding="utf-8")
    (scratch / "run.html").symlink_to(run / "data.txt")
    workspace_run = Path("/workspace") / "aureon_run_holdprobe"
    workspace_link = scratch / "ws.html"
    try:
        workspace_run.mkdir()
    except OSError:
        workspace_run = None
    else:
        (workspace_run / "data.txt").write_text(DUMMY_KEY + "\n", encoding="utf-8")
        workspace_link.symlink_to(workspace_run / "data.txt")
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUREON_BROWSER_FILE_ROOT", str(scratch))
    monkeypatch.setenv("AUREON_BROWSER_SCREENSHOT_DIR", str(tmp_path / "screens"))
    tool = BrowserTool(audit_path=audit)
    try:
        opened = tool.open((scratch / "page.html").as_uri())
        assert opened["ok"] is True, opened
        for target in (scratch / "notes.html", scratch / ".env", scratch / "demo.key", scratch / "run.html"):
            result = tool.open(target.as_uri())
            assert result["ok"] is False, (target.name, result)
            assert result["refused"] is True
        if workspace_run is not None:
            result = tool.open(workspace_link.as_uri())
            assert result["ok"] is False, result
        read = tool.read_text()
        assert DUMMY_KEY not in read.get("text", "")
    finally:
        tool.close()
        if workspace_run is not None:
            for child in workspace_run.iterdir():
                child.unlink(missing_ok=True)
            workspace_run.rmdir()
    assert DUMMY_KEY not in audit.read_text(encoding="utf-8")


@pytest.mark.browser
@pytest.mark.timeout(120)
def test_non_allowed_host_receives_no_hits(tmp_path: Path) -> None:
    """127.0.0.2 is loopback and not on the allowlist. Redirect, img, fetch, and click must not reach it."""

    _need_chrome()
    hits: list[str] = []
    lock = threading.Lock()
    bad = ThreadingHTTPServer(("127.0.0.2", 0), _quiet_handler(hits, lock))
    bad_port = bad.server_address[1]
    bad_base = f"http://127.0.0.2:{bad_port}"
    good = ThreadingHTTPServer(("127.0.0.1", 0), _quiet_handler([], lock, redirect_to=f"{bad_base}/redirect"))
    good_port = good.server_address[1]
    threads = []
    for server in (bad, good):
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        threads.append(thread)
    audit = tmp_path / "audit.jsonl"
    tool = BrowserTool(audit_path=audit)
    try:
        opened = tool.open(f"http://127.0.0.1:{good_port}/page")
        read = tool.read_text()
        assert read.get("ok") is True, {"open": opened, "read": read}
        assert "local-page" in read.get("text", "")
        clicked = tool.click("#out")
        assert clicked["ok"] is False, clicked
        assert "selector not found" not in clicked.get("error", "")
        assert clicked.get("blocked") is True or clicked.get("reason") == "off_host"
        after = tool.read_text()
        if not after.get("ok"):
            assert after.get("reason") == "off_host"
        redirected = tool.open(f"http://127.0.0.1:{good_port}/redir")
        assert redirected["ok"] is False, redirected
        time.sleep(0.4)
        with lock:
            assert hits == [], hits
    finally:
        tool.close()
        good.shutdown()
        bad.shutdown()


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_audit_stores_length_and_sha256_not_plaintext(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _need_chrome()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    page = scratch / "page.html"
    page.write_text(
        "<!DOCTYPE html><html><body>"
        f"<p id='shown'>{DUMMY_KEY}</p>"
        "<input id='secret' type='password'>"
        "<input id='plain' type='text'>"
        "</body></html>",
        encoding="utf-8",
    )
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUREON_BROWSER_FILE_ROOT", str(scratch))
    monkeypatch.setenv("AUREON_BROWSER_SCREENSHOT_DIR", str(tmp_path / "screens"))
    tool = BrowserTool(audit_path=audit)
    try:
        opened = tool.open(page.as_uri())
        assert opened["ok"] is True, opened
        typed = tool.type("#secret", DUMMY_PASSWORD)
        assert typed["ok"] is True, typed
        assert typed["text_length"] == len(DUMMY_PASSWORD)
        read = tool.read_text()
        assert read["ok"] is True, read
        assert DUMMY_KEY in read["text"]
    finally:
        tool.close()
    raw = audit.read_text(encoding="utf-8")
    assert DUMMY_KEY not in raw
    assert DUMMY_PASSWORD not in raw
    assert DUMMY_PASSWORD[:12] not in raw
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    secret_row = next(row for row in rows if row["action"] == "type" and row["css_selector"] == "#secret")
    assert secret_row["text_length"] == len(DUMMY_PASSWORD)
    assert secret_row["text_sha256"] == hashlib.sha256(DUMMY_PASSWORD.encode()).hexdigest()
    assert "text" not in secret_row
    read_row = next(row for row in rows if row["action"] == "read_text")
    assert read_row["text_length"] >= len(DUMMY_KEY)
    assert DUMMY_KEY not in read_row["text_sha256"]
    assert "cookie" not in raw.lower()
    assert "set-cookie" not in raw.lower()


@pytest.mark.browser
@pytest.mark.timeout(90)
def test_screenshots_stay_inside_one_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _need_chrome()
    scratch = tmp_path / "scratch"
    shots = tmp_path / "screens"
    scratch.mkdir()
    shots.mkdir()
    page = scratch / "page.html"
    page.write_text("<html><body><p>shot</p></body></html>", encoding="utf-8")
    other = tmp_path / "other.png"
    other.write_text("keep", encoding="utf-8")
    (shots / "linked.png").symlink_to(other)
    missing = tmp_path / "missing-parent" / "screens"
    audit = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUREON_BROWSER_FILE_ROOT", str(scratch))
    monkeypatch.setenv("AUREON_BROWSER_SCREENSHOT_DIR", str(shots))
    tool = BrowserTool(audit_path=audit)
    try:
        assert tool.open(page.as_uri())["ok"] is True
        saved = tool.screenshot("fixed.png")
        assert saved["ok"] is True, saved
        first = (shots / "fixed.png").read_bytes()
        assert first.startswith(b"\x89PNG\r\n\x1a\n")
        again = tool.screenshot("fixed.png")
        assert again["ok"] is False, again
        assert (shots / "fixed.png").read_bytes() == first
        linked = tool.screenshot("linked.png")
        assert linked["ok"] is False, linked
        assert other.read_text(encoding="utf-8") == "keep"
        escaped = tool.screenshot(str(tmp_path / "do-not-create" / "nested" / "x.png"))
        assert escaped["ok"] is False
        assert not (tmp_path / "do-not-create").exists()
    finally:
        tool.close()
    monkeypatch.setenv("AUREON_BROWSER_SCREENSHOT_DIR", str(missing))
    nested = BrowserTool(audit_path=tmp_path / "audit-nested.jsonl")
    try:
        assert nested.open(page.as_uri())["ok"] is True
        refused = nested.screenshot()
        assert refused["ok"] is False, refused
        assert not (tmp_path / "missing-parent").exists()
    finally:
        nested.close()
