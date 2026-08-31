from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.autonomous import aureon_agent_core as agent_core_module
from aureon.autonomous.aureon_agent_core import AureonAgentCore


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SOURCE = REPO_ROOT / "aureon" / "autonomous" / "aureon_agent_core.py"
FACE_SOURCE = REPO_ROOT / "aureon" / "autonomous" / "aureon_face_app.py"


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def test_sources_have_no_raw_process_network_provider_or_dynamic_code_path() -> None:
    forbidden_calls = {
        "eval",
        "exec",
        "compile",
        "os.system",
        "os.startfile",
        "subprocess.run",
        "subprocess.Popen",
        "webbrowser.open",
        "requests.get",
        "requests.post",
        "requests.request",
        "httpx.get",
        "httpx.post",
        "urllib.request.urlopen",
    }
    for source_path in (CORE_SOURCE, FACE_SOURCE):
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = {
            _qualified_name(node.func)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        assert calls.isdisjoint(forbidden_calls)
        assert not any(
            keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
        )

    core_source = CORE_SOURCE.read_text(encoding="utf-8")
    face_source = FACE_SOURCE.read_text(encoding="utf-8")
    assert "AUREON_SOVEREIGN_MODE" not in core_source
    assert "aureon.exchanges" not in core_source
    assert "aureon.exchanges" not in face_source
    assert "aureon_penny_hunter" not in face_source
    assert "sys.exit(" not in face_source
    assert "load_dotenv" not in face_source


def test_process_file_browser_and_dynamic_code_effects_hold_without_mutation(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sentinel = workspace / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    destination = workspace / "destination.txt"
    created_dir = workspace / "created"
    core = AureonAgentCore(workspace_roots=[workspace])

    receipts = [
        core.execute_shell("echo unsafe"),
        core.open_app("notepad"),
        core.kill_process("123"),
        core.open_url("https://example.com"),
        core.open_file(str(sentinel)),
        core.write_file(str(sentinel), "changed"),
        core.copy_file(str(sentinel), str(destination)),
        core.move_file(str(sentinel), str(destination)),
        core.delete_file(str(sentinel), confirm=True),
        core.create_dir(str(created_dir)),
        core.execute_python("raise RuntimeError('must not execute')"),
        core.create_script(str(workspace / "generated.py"), "print('must not write')"),
        core.run_script(str(workspace / "missing.py")),
    ]

    assert all(receipt["status"] == "hold" for receipt in receipts)
    assert all(receipt["success"] is False for receipt in receipts)
    assert all(receipt["plumber_release_required"] is True for receipt in receipts)
    assert sentinel.read_text(encoding="utf-8") == "unchanged"
    assert not destination.exists()
    assert not created_dir.exists()
    assert not (workspace / "generated.py").exists()


def test_workspace_reads_deny_credentials_vcs_wallets_keys_and_oversize(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "safe.txt").write_text("safe", encoding="utf-8")
    (workspace / ".env").write_text("TOKEN=secret", encoding="utf-8")
    (workspace / ".env1").write_text("TOKEN=alternate-secret", encoding="utf-8")
    (workspace / ".environment").write_text("TOKEN=alternate-secret", encoding="utf-8")
    (workspace / "id_rsa").write_text("private", encoding="utf-8")
    (workspace / "wallet.key").write_text("private", encoding="utf-8")
    (workspace / "server.pem").write_text("private", encoding="utf-8")
    (workspace / "token.json").write_text("private", encoding="utf-8")
    (workspace / ".git").mkdir()
    (workspace / ".git" / "config").write_text("credential", encoding="utf-8")
    (workspace / "large.txt").write_bytes(b"x" * (1024 * 1024 + 1))
    core = AureonAgentCore(workspace_roots=[workspace])

    assert core.read_file("safe.txt") == "safe"
    for denied in (
        ".env",
        ".env1",
        ".environment",
        ".env::$DATA",
        "id_rsa",
        "wallet.key",
        "server.pem",
        "token.json",
        ".git/config",
    ):
        assert core.read_file(denied) == "ERROR: workspace_sensitive_path_denied"
    assert core.read_file("NUL") == "ERROR: workspace_special_device_path_denied"
    assert core.read_file("large.txt") == "ERROR: workspace_file_too_large"

    listed = {entry["name"] for entry in core.list_dir(".") if "name" in entry}
    assert "safe.txt" in listed
    assert listed.isdisjoint(
        {".env", ".env1", ".environment", "id_rsa", "wallet.key", "server.pem", "token.json", ".git"}
    )
    found = "\n".join(core.find_files(".", "*"))
    assert "safe.txt" in found
    assert all(
        name not in found
        for name in (
            ".env",
            ".env1",
            ".environment",
            "id_rsa",
            "wallet.key",
            "server.pem",
            "token.json",
            ".git",
        )
    )

    oversized = core.execute("read_file", {"path": "x" * (64 * 1024)})
    assert oversized["success"] is False
    assert oversized["error"] == "bounded_object_params_required"


def test_action_audit_never_persists_tool_plaintext(monkeypatch, tmp_path) -> None:
    audit_path = tmp_path / "agent_action_log.jsonl"
    state_path = tmp_path.resolve()
    monkeypatch.setattr(agent_core_module, "STATE_DIR", state_path)
    monkeypatch.setattr(agent_core_module, "ACTION_LOG_PATH", audit_path)
    core = AureonAgentCore(workspace_roots=[tmp_path])

    secret = "DO-NOT-PERSIST-PLAINTEXT"
    core.log_action(
        "read_file",
        {"success": True, "status": "ok", "effect": "file.read", "result": secret},
    )

    persisted = audit_path.read_text(encoding="utf-8")
    assert secret not in persisted
    payload = json.loads(persisted)
    assert payload["status"] == "ok"
    assert payload["effect"] == "file.read"
    assert "summary" not in payload


def test_keyword_search_observation_forces_helper_no_write(monkeypatch, tmp_path) -> None:
    from aureon.search import local_keyword_search

    captured: dict[str, object] = {}

    def fake_search(**kwargs):
        captured.update(kwargs)
        return {
            "status": "success",
            "summary": {
                "scanned_file_count": 0,
                "match_count": 0,
                "matched_file_count": 0,
            },
            "matched_paths": [],
        }

    monkeypatch.setattr(local_keyword_search, "run_keyword_search", fake_search)
    core = AureonAgentCore(workspace_roots=[tmp_path])
    result = core.keyword_search_files("needle")

    assert result["status"] == "success"
    assert captured["write_artifact"] is False


def test_face_parser_output_cannot_bypass_exact_tool_allowlist(monkeypatch) -> None:
    from aureon.autonomous import aureon_face_app as face

    calls: list[tuple[str, dict]] = []

    class _Agent:
        def execute(self, intent, params):
            calls.append((intent, params))
            raise AssertionError("unallowlisted parser output reached AgentCore")

    class _Parser:
        @staticmethod
        def parse(_text):
            return [
                {
                    "tool": "agent",
                    "method": "write_file",
                    "params": {"path": "owned.txt", "content": "owned"},
                    "description": "write",
                },
                {
                    "tool": "agent",
                    "method": "open_app",
                    "params": {"app_name": "powershell"},
                    "description": "launch",
                },
                {
                    "tool": "shell",
                    "method": "whoami",
                    "params": {},
                    "description": "shell",
                },
            ]

    monkeypatch.setattr(face.state, "agent", _Agent())
    monkeypatch.setattr(face.state, "parser", _Parser())
    response = face._rule_based_respond("perform unsafe parser route")

    assert response["action"] == "command"
    assert calls == []
    assert "face_tool_not_released_by_plumber_magic_star" in response["text"]


def test_workspace_symlink_escape_is_denied(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside-secret", encoding="utf-8")
    link = workspace / "escape.txt"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {type(exc).__name__}")

    core = AureonAgentCore(workspace_roots=[workspace])
    assert core.read_file("escape.txt") == "ERROR: workspace_path_outside_allowlist"
    assert "escape.txt" not in {
        entry["name"] for entry in core.list_dir(".") if "name" in entry
    }


def test_injected_web_reader_enforces_https_host_peer_and_no_redirect() -> None:
    calls: list[str] = []

    def good_reader(url: str) -> dict:
        calls.append(url)
        return {
            "final_url": url,
            "redirected": False,
            "peer_ip": "8.8.8.8",
            "status_code": 200,
            "text": "bounded response",
        }

    core = AureonAgentCore(
        web_reader=good_reader,
        allowed_web_hosts=["example.com"],
    )
    for url in (
        "http://example.com/",
        "https://example.net/",
        "https://user@example.com/",
        "https://example.com/#fragment",
        "https://example.com:444/",
    ):
        assert core.web_fetch(url)["success"] is False
    assert calls == []
    assert core.web_fetch("https://example.com/resource") == {
        "success": True,
        "url": "https://example.com/resource",
        "status_code": 200,
        "text": "bounded response",
    }

    private_literal = AureonAgentCore(
        web_reader=good_reader,
        allowed_web_hosts=["127.0.0.1"],
    )
    assert private_literal.web_fetch("https://127.0.0.1/")["error"] == "web_url_private_host_denied"

    def private_peer(url: str) -> dict:
        return {"final_url": url, "peer_ip": "127.0.0.1", "status_code": 200, "text": "x"}

    rebound = AureonAgentCore(web_reader=private_peer, allowed_web_hosts=["example.com"])
    assert rebound.web_fetch("https://example.com/")["error"] == "web_reader_private_peer_denied"

    def redirected(url: str) -> dict:
        return {"final_url": "https://example.com/other", "peer_ip": "8.8.8.8", "status_code": 200, "text": "x"}

    redirect_core = AureonAgentCore(web_reader=redirected, allowed_web_hosts=["example.com"])
    assert redirect_core.web_fetch("https://example.com/")["error"] == "web_redirect_denied"

    def failing_reader(_url: str) -> dict:
        raise RuntimeError("do-not-reflect-secret")

    failure_core = AureonAgentCore(web_reader=failing_reader, allowed_web_hosts=["example.com"])
    failure = failure_core.web_fetch("https://example.com/")
    assert failure == {"success": False, "error": "web_reader_failed"}
    assert "secret" not in json.dumps(failure)


def test_sql_env_flag_cannot_restore_mutation(monkeypatch) -> None:
    class _Cursor:
        description = [("value",)]

        def fetchall(self):
            return [(1,)]

    class _Connection:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def execute(self, sql: str):
            self.calls.append(sql)
            return _Cursor()

    connection = _Connection()
    monkeypatch.setenv("AUREON_SOVEREIGN_MODE", "1")
    core = AureonAgentCore(knowledge_connection=connection)

    blocked = core.query_knowledge("WITH doomed AS (DELETE FROM secrets RETURNING *) SELECT * FROM doomed")
    assert blocked == [{"error": "Blocked keyword in SQL: delete."}]
    assert connection.calls == []
    assert core.query_knowledge("SELECT 1 AS value") == [{"value": 1}]
    assert connection.calls == ["SELECT 1 AS value"]


def test_default_account_and_trade_paths_never_construct_provider_clients() -> None:
    core = AureonAgentCore()

    balances = core.get_balances()
    assert set(balances) == {"binance", "alpaca", "capital", "kraken"}
    assert all(item["data_status"] == "no_data" for item in balances.values())
    trade = core.place_order("kraken", "BTC/USD", "buy", 0.01)
    assert trade["status"] == "hold"
    assert trade["magic_star_required"] is True


def test_agent_core_dispatcher_cannot_self_attest_execution(monkeypatch) -> None:
    from aureon.queen import queen_force_trade_governance as governance

    monkeypatch.setattr(
        governance,
        "claim_queen_force_trade_authority",
        lambda **_kwargs: SimpleNamespace(allowed=True, missing_requirements=[]),
    )
    core = AureonAgentCore(
        trade_authorization_provider=lambda _plan: object(),
        final_trade_dispatcher=lambda _plan: {
            "status": "EXECUTED",
            "success": True,
            "provider_receipt_id": "self-attested",
        },
    )

    receipt = core.place_order("kraken", "BTC/USD", "buy", 0.01)

    assert receipt["success"] is False
    assert receipt["status"] == "pending_reconciliation"
    assert receipt["error"] == "independent_provider_readback_required"
    assert receipt["dispatcher_acknowledgement_untrusted"] is True
    assert "provider_receipt_id" not in receipt


def test_face_http_control_requires_strong_bearer(monkeypatch) -> None:
    from aureon.autonomous import aureon_face_app as face

    client = face.app.test_client()
    monkeypatch.delenv("AUREON_FACE_BEARER_TOKEN", raising=False)
    assert client.get("/api/status").status_code == 503
    monkeypatch.setenv("AUREON_FACE_BEARER_TOKEN", "weak")
    assert client.get("/api/status").status_code == 503

    token = "A" * 48
    monkeypatch.setenv("AUREON_FACE_BEARER_TOKEN", token)
    assert client.get("/api/status").status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get(
        "/api/status", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 200


def test_face_socket_control_requires_strong_bearer(monkeypatch) -> None:
    from aureon.autonomous import aureon_face_app as face

    if not face.HAS_SOCKETIO:
        pytest.skip("flask-socketio runtime unavailable")
    token = "A" * 48
    monkeypatch.setenv("AUREON_FACE_BEARER_TOKEN", token)
    unauthenticated_socket = face.socketio.test_client(face.app)
    assert unauthenticated_socket.is_connected() is False
    authenticated_socket = face.socketio.test_client(face.app, auth={"token": token})
    assert authenticated_socket.is_connected() is True
    authenticated_socket.emit("user_message", {"text": "x" * (8 * 1024 + 1)})
    received = authenticated_socket.get_received()
    assert any(
        event["name"] == "queen_error"
        and event["args"][0]["error"] == "face_message_too_large"
        for event in received
    )
    authenticated_socket.disconnect()


def test_face_effect_tools_and_normal_browser_ui_remain_explicitly_on_hold(monkeypatch) -> None:
    from aureon.autonomous import aureon_face_app as face

    class _Agent:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("unallowlisted effect must not reach AgentCore")

    monkeypatch.setattr(face.state, "agent", _Agent())
    for name in ("execute_shell", "open_app", "open_url", "write_file", "delete_file", "execute_python"):
        payload = json.loads(face._execute_tool(name, {}))
        assert payload["status"] == "hold"
        assert payload["magic_star_required"] is True
    oversized = json.loads(face._execute_tool("read_file", {"path": "x" * (16 * 1024 + 1)}))
    assert oversized["error"] == "tool_params_too_large"
    cyclic: dict = {}
    cyclic["self"] = cyclic
    malformed = json.loads(face._execute_tool("read_file", cyclic))
    assert malformed["error"] == "tool_params_invalid"

    monkeypatch.delenv("AUREON_FACE_BEARER_TOKEN", raising=False)
    assert face.main([]) == 2
    preflight = face.server_preflight()
    assert preflight["status"] == "hold"
    assert preflight["bind_host"] == "127.0.0.1"
    assert preflight["browser_ui"] == "hold_authenticated_api_clients_only"
    assert preflight["economic_effects"] == "plumber_magic_star_release_required"


def test_face_source_contains_no_false_live_or_effect_capability_claims() -> None:
    source = FACE_SOURCE.read_text(encoding="utf-8")
    for false_claim in (
        "watching the markets 24/7",
        "learn from every trade",
        "full laptop control",
        "trade across 4 exchanges",
        "all systems are online",
    ):
        assert false_claim not in source
