"""Round-1 fix loop checks that stay off the network and place no order."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


def test_isolate_clears_aureon_flags_and_exchange_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    from conftest import _isolate_leaked_credentials

    monkeypatch.setenv("ALPACA_API_KEY", "leak")
    monkeypatch.setenv("APCA_API_SECRET_KEY", "leak")
    monkeypatch.setenv("KRAKEN_API_SECRET", "leak")
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    monkeypatch.setenv("AUREON_CUSTOM_LEAK", "1")
    monkeypatch.setenv("AUREON_THOUGHT_BUS_PATH", "/tmp/keep-journal")
    _isolate_leaked_credentials()
    assert "ALPACA_API_KEY" not in os.environ
    assert "APCA_API_SECRET_KEY" not in os.environ
    assert "KRAKEN_API_SECRET" not in os.environ
    assert "AUREON_CUSTOM_LEAK" not in os.environ
    assert os.environ["AUREON_LIVE_TRADING"] == "0"
    assert "AUREON_DISABLE_REAL_ORDERS" not in os.environ
    assert "AUREON_DISABLE_EXCHANGE_MUTATIONS" not in os.environ
    assert os.environ["AUREON_AUTONOMY_MODE"] == "guarded"
    assert os.environ["AUREON_THOUGHT_BUS_PATH"] == "/tmp/keep-journal"


def test_alpaca_aliases_fill_canonical_names_from_apca() -> None:
    from aureon.core.aureon_env import apply_env_aliases, missing_env

    env = {
        "APCA_API_KEY_ID": "key-from-apca",
        "APCA_API_SECRET_KEY": "secret-from-apca",
    }
    applied = apply_env_aliases(env, override=False)
    assert missing_env(("ALPACA_API_KEY", "ALPACA_SECRET_KEY"), env) == []
    assert env["ALPACA_API_KEY"] == "key-from-apca"
    assert {"target": "ALPACA_API_KEY", "source": "APCA_API_KEY_ID"} in applied
    assert {"target": "ALPACA_SECRET_KEY", "source": "APCA_API_SECRET_KEY"} in applied


def test_child_env_keeps_exchange_keys_a_spec_snapshot_emptied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.launch.master import child_env

    (tmp_path / ".env").write_text(
        "ALPACA_API_KEY=from-dotenv\nALPACA_SECRET_KEY=from-dotenv-secret\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.setenv("AUREON_AUTONOMY_MODE", "guarded")
    env = child_env(
        tmp_path,
        {"env": {"ALPACA_API_KEY": "", "ALPACA_SECRET_KEY": "", "AUREON_LIVE_TRADING": "0"}},
    )
    assert env["ALPACA_API_KEY"] == "from-dotenv"
    assert env["ALPACA_SECRET_KEY"] == "from-dotenv-secret"
    assert env["AUREON_LIVE_TRADING"] == "0"


def test_invalid_nonce_persists_a_higher_floor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aureon.exchanges.kraken_client as kraken

    nonce_file = tmp_path / "nonce"
    monkeypatch.setattr(kraken, "NONCE_FILE", str(nonce_file))
    monkeypatch.setattr(kraken.time, "time_ns", lambda: 1_000)
    stored = kraken._persist_nonce_floor(100, "EAPI:Invalid nonce")
    assert stored >= 100 + 1_000_000_000
    assert int(nonce_file.read_text(encoding="utf-8")) == stored
    climbed = kraken._persist_nonce_floor(stored, "EAPI:Invalid nonce")
    assert climbed >= stored + 1_000_000_000


def test_binance_http_451_is_region_blocked() -> None:
    from aureon.exchanges.binance_client import BinanceClient

    client = BinanceClient.__new__(BinanceClient)
    client.base = "https://api.binance.com"
    client.init_error = ""
    client.last_error = ""
    client.dry_run = True
    client.use_testnet = False
    client.uk_mode = False

    class _Response:
        status_code = 451

    class _Session:
        def get(self, *_args, **_kwargs):
            return _Response()

    client.session = _Session()
    client._margin_enabled = lambda: False
    report = client.diagnose_ready()
    assert report["network_ok"] is False
    assert report["init_error"] == "region blocked"
    assert report["init_error"] != "network_unavailable"


def test_seat_ports_follow_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.launch.seat_tabs import _env
    import aureon.operator.seat_proxy as seat_proxy

    monkeypatch.setenv("AUREON_SEAT_GATEWAY_PORT", "18790")
    monkeypatch.setenv("AUREON_SEAT_MARKET_PORT", "18791")
    monkeypatch.setenv("AUREON_FRONTEND_BRIDGE_PORT", "18787")
    monkeypatch.setenv("AUREON_MARKET_STATUS_URL", "http://127.0.0.1:18791/health")
    env = _env()
    assert env["AUREON_OPERATOR_PORT"] == "18790"
    assert env["VITE_OPERATOR_URL"] == "http://127.0.0.1:18790"
    assert env["AUREON_MARKET_STATUS_URL"] == "http://127.0.0.1:18791/health"
    assert env["NEXUS_WS_HOST"] == "127.0.0.1"
    assert env["AUREON_FRONTEND_BRIDGE_PORT"] == "18787"
    assert env["AUREON_LIVE_TRADING"] == "0"
    market = seat_proxy.seat_by_id("market-status")
    assert market is not None
    assert seat_proxy._resolved_upstream(market) == "http://127.0.0.1:18791/health"
    bridge = seat_proxy.seat_by_id("live-bridge")
    assert bridge is not None
    for seat_id in ("system-hub", "bot-hunter", "dashboard-api"):
        reading = seat_proxy.read_seat(seat_id)
        assert reading["available"] is False
        assert reading["payload"] is None
        assert "Retired" in str(reading["reason"])


def test_faculty_readings_publish_a_baton_link_without_ollama() -> None:
    from aureon.core.aureon_thought_bus import clear_thought_bus, get_thought_bus
    from aureon.core.organism_circulation import publish_faculty_reading

    clear_thought_bus()
    bus = get_thought_bus()
    publish_faculty_reading("metacognition", {"truth_status": "no_data", "reason": "no model is called"})
    publish_faculty_reading(
        "self_questioning",
        {"available": False, "reason": "no question is invented and no model is called", "live_trading": False},
    )
    recent = bus.get_recent(20)
    topics = [item.get("topic") for item in recent]
    sources = [item.get("source") for item in recent]
    assert "organism.metacognition" in topics
    assert "organism.self_questioning" in topics
    assert topics.count("baton.link") >= 2
    assert "metacognition" in sources
    assert "self_questioning" in sources
    assert all(item.get("payload", {}).get("ollama") is False for item in recent if item.get("topic") == "baton.link")


def test_fresh_box_preflight_and_offline_benchmark(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.autonomous.aureon_internal_self_coder import (
        ensure_hnc_master_key_preflight,
        openai_compatible_model_endpoint,
    )
    from aureon.autonomous.self_coder_benchmark import run_harness
    from aureon.harmonic.hnc_quantum_packet_crypto import MASTER_KEY_ENV

    monkeypatch.delenv(MASTER_KEY_ENV, raising=False)
    monkeypatch.delenv("HNC_PACKET_MASTER_KEY", raising=False)
    monkeypatch.delenv("AUREON_SELF_CODER_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("AUREON_SELF_CODER_API_KEY", raising=False)
    prepared = ensure_hnc_master_key_preflight(tmp_path)
    assert prepared["ready"] is True
    assert prepared["source"] == "generated"
    assert prepared["key_material_returned"] is False
    assert (tmp_path / "state" / "hnc_packet_master_key").is_file()
    assert os.environ[MASTER_KEY_ENV]
    rendered = json.dumps(prepared)
    assert os.environ[MASTER_KEY_ENV] not in rendered
    endpoint = openai_compatible_model_endpoint()
    assert endpoint["base_url"] == "http://127.0.0.1:8000/v1"
    assert endpoint["model"] == "kimi-k2.5"
    assert endpoint["api_key_configured"] is False
    assert endpoint["api_key_returned"] is False
    monkeypatch.setenv("AUREON_SELF_CODER_OPENAI_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("AUREON_SELF_CODER_MODEL", "kimi-k2.5")
    moved = openai_compatible_model_endpoint()
    assert moved["base_url"] == "http://127.0.0.1:9/v1"
    report = run_harness(tmp_path)
    assert report["offline_fixture"]["counts_as_result"] is False
    assert report["offline_fixture"]["executed"] is False
    assert report["model_call"]["attempted"] is True
    assert report["model_call"]["ok"] is False
    assert report["swe_bench"]["executed"] is False
    assert report["livecodebench"]["executed"] is False
    assert report["harness"].startswith("model-written Python")
    assert "not the official SWE-bench" in report["harness"]
    assert "not a kernel sandbox" in report["harness"]
    assert "machine with no secrets" in report["harness"]
    assert "measured_swe_bench_verified_pct" not in report
    assert "measured_livecodebench_v6_pct" not in report
    assert report["model_python_task_pass_pct"]["swe_rows"] is None
    assert report["model_python_task_pass_pct"]["livecode_rows"] is None
    assert report["published_reference"]["swe_bench_verified_pct"] == 76.8
    assert report["published_reference"]["livecodebench_v6_pct"] == 85.0
    assert report["published_reference"]["source"].startswith("published score")


def test_benchmark_scores_a_configured_model_and_dataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from aureon.autonomous.self_coder_benchmark import run_harness

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or 0)
            self.rfile.read(length)
            body = json.dumps(
                {"choices": [{"message": {"content": "def add(a, b):\n    return a + b\n"}}]}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):  # noqa: A003
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    import threading

    threading.Thread(target=server.serve_forever, daemon=True).start()
    dataset = tmp_path / "data" / "benchmarks" / "livecodebench"
    dataset.mkdir(parents=True)
    (dataset / "problems.jsonl").write_text(
        json.dumps({"question_id": "add", "prompt": "def add(a, b)", "tests": "assert add(1, 2) == 3"}) + "\n",
        encoding="utf-8",
    )
    swe = tmp_path / "data" / "benchmarks" / "swebench"
    swe.mkdir(parents=True)
    (swe / "instances.jsonl").write_text(
        json.dumps({"instance_id": "add", "problem_statement": "def add(a, b)", "tests": "assert add(2, 2) == 4"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AUREON_SELF_CODER_OPENAI_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setenv("AUREON_SELF_CODER_MODEL", "local-test")
    try:
        report = run_harness(tmp_path)
    finally:
        server.shutdown()
    assert report["model_call"]["ok"] is True
    assert report["offline_fixture"]["counts_as_result"] is False
    assert "not the official SWE-bench" in report["harness"]
    assert "not a kernel sandbox" in report["harness"]
    assert "machine with no secrets" in report["harness"]
    assert report["model_python_task_pass_pct"]["livecode_rows"] == 100.0
    assert report["model_python_task_pass_pct"]["swe_rows"] == 100.0
    assert report["livecodebench"]["executed"] is True
    assert report["swe_bench"]["executed"] is True


def test_benchmark_child_cannot_see_parent_exchange_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon.autonomous.self_coder_benchmark import _run_python

    monkeypatch.setenv("KRAKEN_API_SECRET", "super-secret-kraken")
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    monkeypatch.setenv("BINANCE_API_KEY", "binance-secret")
    code = "import os, socket\n"
    tests = (
        "assert 'KRAKEN_API_SECRET' not in os.environ\n"
        "assert 'BINANCE_API_KEY' not in os.environ\n"
        "assert 'AUREON_LIVE_TRADING' not in os.environ\n"
        "assert not any(name.startswith('AUREON_') for name in os.environ)\n"
        "assert 'super-secret-kraken' not in os.environ.values()\n"
        "try:\n"
        "    socket.create_connection(('127.0.0.1', 9), timeout=0.2)\n"
        "except OSError:\n"
        "    pass\n"
        "else:\n"
        "    raise SystemExit('network opened')\n"
    )
    assert _run_python(code, tests) is True


def test_benchmark_namespace_hides_parent_environ(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from aureon.autonomous import self_coder_benchmark as bench

    bench._NAMESPACE_READY = None
    if bench._namespace_command(tmp_path / "runner.py") is None:
        pytest.skip("unshare user namespace is not available")
    monkeypatch.setenv("KRAKEN_API_SECRET", "super-secret-kraken")
    code = (
        "import os, socket, importlib\n"
        "secret = 'super-secret-kraken'\n"
        "assert secret not in os.environ.values()\n"
        "for pid in os.listdir('/proc'):\n"
        "    if not pid.isdigit():\n"
        "        continue\n"
        "    try:\n"
        "        data = open(f'/proc/{pid}/environ', 'rb').read().decode('latin1')\n"
        "    except OSError:\n"
        "        continue\n"
        "    assert secret not in data\n"
        "importlib.reload(socket)\n"
        "sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "sock.settimeout(0.3)\n"
        "try:\n"
        "    sock.connect(('1.1.1.1', 80))\n"
        "except OSError:\n"
        "    pass\n"
        "else:\n"
        "    raise SystemExit('network opened')\n"
    )
    assert bench._run_python(code, "") is True
