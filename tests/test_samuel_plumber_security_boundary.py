from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

from aureon.wisdom import aureon_samuel_agent as samuel

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "aureon" / "wisdom" / "aureon_samuel_agent.py"


def _assert_held(payload: str | dict[str, object], tool: str) -> None:
    parsed = json.loads(payload) if isinstance(payload, str) else payload
    assert parsed == {
        "action_eligible": False,
        "economic_eligible": False,
        "effect_attempted": False,
        "reason_code": "plumber_magic_star_capability_required",
        "status": "HOLD",
        "tool": tool,
    }


def test_model_tool_surface_is_observation_only() -> None:
    names = {str(tool["name"]) for tool in samuel.SAMUEL_TOOLS}
    assert names == {str(tool["name"]) for tool in samuel.SAMUEL_READ_ONLY_TOOLS}
    assert names.isdisjoint(samuel._EFFECT_TOOL_NAMES)

    source = SOURCE.read_text(encoding="utf-8")
    for false_claim in (
        "FULLY INTEGRATED LIVE SENTINEL",
        "You are ALIVE. You are WIRED.",
        "live-integrated autonomous orchestrator",
        "Issue a REAL trade command",
        "Get live market prices",
    ):
        assert false_claim not in source


def test_effect_dispatch_and_direct_helpers_fail_closed_without_side_effects() -> None:
    entity = object.__new__(samuel.SamuelHarmonicEntity)
    for tool in sorted(samuel._EFFECT_TOOL_NAMES):
        _assert_held(entity._dispatch(tool, {"attacker": "controlled"}), tool)

    _assert_held(
        entity._t_send_trade_command(
            action="BUY",
            symbol="BTCUSDT",
            amount_usd=10.0,
            confidence=1.0,
            reasoning="attacker controlled",
            gamma=1.0,
        ),
        "send_trade_command",
    )
    _assert_held(samuel._ws_send_command("run_nexus", {"cycles": 999}), "send_websocket_command")


def test_rest_surface_requires_secret_is_loopback_and_cannot_trigger_cycle() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    serve = source[source.index("    def serve_rest("):source.index("    def chat_session(")]
    assert 'os.environ.get("AUREON_SAMUEL_API_KEY"' in serve
    assert "hmac.compare_digest(presented, api_key)" in serve
    assert 'app.run(host="127.0.0.1"' in serve
    assert 'app.run(host="0.0.0.0"' not in serve
    assert "LocalOSProtectionBoundary(" in serve
    assert 'return _admit_and_hold("command")' in serve
    assert 'return _admit_and_hold("cycle")' in serve
    assert "self.handle_command(" not in serve
    assert '"intent_executed": False' in serve
    assert "discard_admitted(" in serve
    assert "threading.Thread(target=self.autonomous_cycle" not in serve


def test_rest_intent_validator_rejects_ambiguous_or_effect_smuggling_payloads() -> None:
    valid = memoryview(b'{"command":"status","request_id":"r-1"}')
    duplicate = memoryview(b'{"command":"status","command":"buy BTC"}')
    unknown = memoryview(b'{"command":"status","effect":"trade"}')
    oversized = memoryview(
        json.dumps({"command": "X" * 4097}, separators=(",", ":")).encode()
    )

    assert samuel._valid_rest_intent_payload(valid, route="command") is True
    assert samuel._valid_rest_intent_payload(duplicate, route="command") is False
    assert samuel._valid_rest_intent_payload(unknown, route="command") is False
    assert samuel._valid_rest_intent_payload(oversized, route="command") is False
    assert samuel._valid_rest_intent_payload(
        memoryview(b'{"command":"\\ud800"}'),
        route="command",
    ) is False
    assert samuel._valid_rest_intent_payload(memoryview(b"{}"), route="cycle") is True


def test_rest_command_is_hnc_admitted_burned_and_never_processed(monkeypatch) -> None:
    api_key = "samuel-test-" + ("T" * 32)
    hnc_key = base64.urlsafe_b64encode(b"K" * 32).decode().rstrip("=")
    monkeypatch.setenv("AUREON_SAMUEL_API_KEY", api_key)
    monkeypatch.setenv("AUREON_HNC_PACKET_MASTER_KEY", hnc_key)
    captured: dict[str, object] = {}

    def capture_app(app, **_kwargs):
        captured["app"] = app

    monkeypatch.setattr("flask.Flask.run", capture_app)
    entity = object.__new__(samuel.SamuelHarmonicEntity)
    entity.handle_command = lambda _command: (_ for _ in ()).throw(
        AssertionError("plaintext command reached model")
    )
    entity.serve_rest()
    app = captured["app"]
    client = app.test_client()
    headers = {"Authorization": f"Bearer {api_key}"}

    unauthorized = client.post("/samuel/command", data=b'{"command":"status"}')
    admitted = client.post(
        "/samuel/command",
        data=b'{"command":"status"}',
        content_type="application/json",
        headers=headers,
    )
    replay = client.post(
        "/samuel/command",
        data=b'{"command":"status"}',
        content_type="application/json",
        headers=headers,
    )

    assert unauthorized.status_code == 401
    assert admitted.status_code == 202
    payload = admitted.get_json()
    assert payload["status"] == "HOLD"
    assert payload["intent_executed"] is False
    assert payload["admission"]["disposition"] == "ADMITTED_HNC"
    assert payload["disposal"]["disposition"] == "DISCARDED_HNC"
    assert payload["disposal"]["carrier_released"] is False
    assert replay.status_code == 409
    assert "ingress_replay_detected" in replay.get_json()["admission"]["denial_codes"]


def test_import_does_not_create_file_log_or_contact_providers(tmp_path: Path) -> None:
    env = {
        **os.environ,
        "AUREON_OFFLINE": "1",
        "AUREON_LIVE": "0",
        "LIVE": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(ROOT),
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            (
                "import json; import aureon.wisdom.aureon_samuel_agent as m; "
                "print(json.dumps(sorted(t['name'] for t in m.SAMUEL_TOOLS)))"
            ),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert not (tmp_path / "aureon_samuel.log").exists()
    assert "send_trade_command" not in completed.stdout


def test_entity_construction_never_attaches_live_connectors() -> None:
    class _Adapter:
        pass

    entity = samuel.SamuelHarmonicEntity(adapter=_Adapter())

    assert entity.queen.is_live() is False
    assert entity.king.is_live() is False
    assert entity.lyra.is_live() is False
    assert entity.bus.is_live() is False
    assert entity.bus.publish("orca.buy.execute", {"symbol": "BTCUSDT"}) is False
    running = json.loads(entity._t_get_running_systems("full"))
    assert running["status"] == "no_data"
    assert running["process_probe_attempted"] is False
    assert running["socket_probe_attempted"] is False
    assert all(value is False for value in running["live_connectors"].values())
