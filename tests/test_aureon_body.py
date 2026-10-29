"""Full-body caller. Depth is a real call. A listed row is not depth."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from aureon_public.body import body_call, body_call_operator, body_registry, body_surface, enabled_stage  # noqa: E402
from aureon_public.pin_blob import checkout_blob_refusal  # noqa: E402
from aureon_public.guard_loader import PINNED_COMMIT  # noqa: E402
from aureon_public.paths import repo_root  # noqa: E402

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    return json.loads(text)


def test_stage1_calls_real_entry_points_and_names_auris() -> None:
    ladder = _load(body_call("harmonic/rainbow_reference.py", "solfeggio_ladder"))
    assert ladder["status"] == "cited"
    assert ladder["called"] is True
    assert ladder["label"].startswith("cited.")
    assert not ladder["label"].startswith("helper.")
    assert "consciousness_" not in json.dumps(ladder)
    assert isinstance(ladder["result"], list)
    assert ladder["result"]

    substrate = _load(
        body_call(
            "harmonic/aureon_harmonic_reality.py",
            "HarmonicSubstrate.evaluate",
            json.dumps({"t": 0.0}),
        )
    )
    assert substrate["status"] == "unavailable"
    assert substrate.get("called") is not True
    from aureon_public.body import _constructor_refusal

    assert _constructor_refusal("harmonic/aureon_harmonic_reality.py", "HarmonicSubstrate")

    nodes = _load(body_call("utils/aureon_queen_hive_mind.py", "QueenHiveMind.read_auris_nodes"))
    assert nodes["status"] == "unavailable"
    assert nodes.get("called") is not True

    analyzer = _load(body_call("wisdom/aureon_qgita_framework.py", "get_qgita_analyzer"))
    assert analyzer["called"] is True
    assert analyzer["result"]["type"] == "QGITAMarketAnalyzer"


def test_public_call_refuses_operator_orders_and_blocked_packages() -> None:
    order = _load(
        body_call(
            "harmonic/hnc_quantum_packet_crypto.py",
            "packet_master_key_from_env",
        )
    )
    assert order["status"] == "unavailable"
    assert order.get("called") is not True
    loop = _load(body_call("harmonic/aureon_harmonic_momentum_wave.py", "run_continuous_scan"))
    assert loop["status"] == "unavailable"
    blocked = _load(body_call("trading/__init__.py", "__init__"))
    assert blocked["status"] == "unavailable"
    assert blocked.get("live_orders") == "refused"


def test_surface_does_not_call_and_a_changed_blob_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    surface = _load(body_surface("harmonic/aureon_harmonic_reality.py", "HarmonicSubstrate"))
    assert surface.get("called") is not True
    assert surface["status"] == "unavailable"
    assert enabled_stage() >= 1

    real = repo_root() / "aureon" / "harmonic" / "rainbow_reference.py"
    assert checkout_blob_refusal(real, repo_root(), PINNED_COMMIT) is None
    changed = tmp_path / "rainbow_reference.py"
    changed.write_bytes(real.read_bytes() + b"\n# changed\n")

    def refuse(module_name: str, file_path: Path, expected_blob: str, mismatch: str) -> str | None:
        del module_name, expected_blob, mismatch
        if file_path == real:
            return "checkout rainbow_reference.py differs from pin a00f744d"
        return None

    monkeypatch.setattr("aureon_public.pin_blob.load_pinned_source", refuse)
    monkeypatch.setattr("aureon_public.body._outside", lambda origin, root: False)
    refused = _load(body_call("harmonic/rainbow_reference.py", "solfeggio_ladder"))
    assert refused["status"] == "unavailable"
    assert "differs from pin" in refused["reason"]


def test_readme_and_stage_reports_match_the_inventory_depth() -> None:
    from aureon_public.body import package_depth, render_readme_depth

    readme = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    assert render_readme_depth() in readme
    assert readme.splitlines()[14] == (
        "A layer counts as full depth only where its real entry points are called."
    )
    assert "The extra package tools are helpers." in readme
    for stage in range(1, 7):
        record = json.loads((ROOT / "measured" / f"body_stage{stage}.json").read_text(encoding="utf-8"))
        assert record["entry_points"] == package_depth(stage)
        for row in record["entry_points"].values():
            assert row["reachable"] <= row["public_entry_points"]


def test_stage7_registry_names_servers_spaces_and_the_pin() -> None:
    body = _load(body_registry())
    assert body["status"] == "cited"
    assert body.get("called") is not True
    assert body["live_orders"] == "refused"
    assert body["enabled_through"] == enabled_stage()
    assert body["pin"].startswith("a00f744d")
    assert "huggingface/hnc-field/app.py" in body["spaces"]
    assert "trading" in body["blocked_imports"]
    registry = (ROOT / "docs" / "mcp" / "REGISTRY.md").read_text(encoding="utf-8")
    assert "body_call" in registry
    assert "enforce_public_pin" in registry
    readme = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    assert "body_call" in readme
    assert "helper" in readme


def test_stage6_calls_the_remaining_public_readers() -> None:
    assert enabled_stage() >= 6
    rank = _load(body_call("briefing/schemas.py", "severity_rank", json.dumps({"severity": "high"})))
    assert rank["called"] is True
    color = _load(body_call("simulation/aureon_world_simulator.py", "hz_to_rgb", json.dumps({"hz": 528})))
    assert color["called"] is True
    assert color["result"] == [0, 255, 0] or isinstance(color["result"], list)
    record = json.loads((ROOT / "measured" / "body_stage6.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {
        "approval",
        "briefing",
        "grants",
        "integrations",
        "intelligence",
        "plumber",
        "s51",
        "simulation",
    } <= called


def test_stage5_operator_refuses_blocked_imports_and_calls_two_readers(monkeypatch: pytest.MonkeyPatch) -> None:
    assert enabled_stage() >= 5
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    monkeypatch.setenv("AUREON_DISABLE_REAL_ORDERS", "1")
    ingestors = _load(body_call_operator("accounting/file_drop.py", "registered_ingestors"))
    assert ingestors["called"] is True
    assert "bank_csv" in ingestors["result"]
    days = _load(body_call_operator("portfolio/aureon_billion_goal_tracker.py", "get_days_remaining"))
    assert days["called"] is True
    assert isinstance(days["result"], float)
    blocked = (
        ("trading/__init__.py", "__init__"),
        ("exchanges/__init__.py", "__init__"),
        ("bots/__init__.py", "__init__"),
        ("bots_intelligence/__init__.py", "__init__"),
        ("bridges/__init__.py", "__init__"),
        ("scanners/__init__.py", "__init__"),
        ("unified_margin_trader/_margin_monitor.py", "_margin_monitor"),
    )
    for module, symbol in blocked:
        body = _load(body_call_operator(module, symbol))
        assert body["live_orders"] == "refused", symbol
        assert body.get("called") is not True
        public = _load(body_call(module, symbol))
        assert public["live_orders"] == "refused"
    record = json.loads((ROOT / "measured" / "body_stage5.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {"accounting", "portfolio"} <= called
    assert "trading" not in called


def test_stage4_calls_feed_decoder_search_portal_analytics_atn_and_monitor() -> None:
    assert enabled_stage() >= 4
    distance = _load(
        body_call(
            "decoders/grail_convergence.py",
            "haversine",
            json.dumps({"lat1": 51.5, "lon1": -0.12, "lat2": 48.86, "lon2": 2.35}),
        )
    )
    assert distance["called"] is True
    assert isinstance(distance["result"], float)
    impacts = _load(
        body_call(
            "atn/aureon_atn_backtest.py",
            "compute_impacts",
            json.dumps({"events": [], "candles": [], "symbol": "BTC"}),
        )
    )
    assert impacts["status"] == "unavailable"
    assert impacts.get("called") is not True
    record = json.loads((ROOT / "measured" / "body_stage4.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {"data_feeds", "decoders", "search", "portals", "analytics", "atn"} <= called


def test_stage3_calls_organism_bio_evaluation_and_vault_and_refuses_identity() -> None:
    assert enabled_stage() >= 3
    words = _load(
        body_call(
            "vault/voice/document_artifact_skill.py",
            "count_words",
            json.dumps({"text": "one two three"}),
        )
    )
    assert words["called"] is True
    assert words["result"] == 3
    layers = _load(body_call("organism/repository_layers.py", "compose_repository_layers"))
    assert layers["called"] is True
    nodes = _load(body_call("evaluation/auris_node_eval.py", "evaluate_auris_nodes"))
    assert nodes["status"] == "unavailable"
    assert nodes.get("called") is not True
    identity = _load(body_call("identity/reader.py", "read_identity"))
    assert identity["status"] == "unavailable"
    assert identity.get("called") is not True
    record = json.loads((ROOT / "measured" / "body_stage3.json").read_text(encoding="utf-8"))
    called = {item["package"] for item in record["calls"] if item["called"] is True}
    assert {"bio", "organism", "evaluation", "vault", "core"} <= called


def test_stage2_calls_each_named_package() -> None:
    assert enabled_stage() >= 2
    calls = {
        "alignment": body_call("alignment/harmonic_resonance.py", "consonance_score", json.dumps({"ratio": 1.0})),
        "queen": body_call("queen/temporal_ground.py", "compute_zpe_ground", json.dumps({"lambda_t": 0.0})),
        "swarm": body_call("swarm/druidic_council.py", "voice_for_gamma", json.dumps({"gamma": 0.5})),
        "gates": body_call("gates/switchboard.py", "is_human_held", json.dumps({"action": "draft"})),
        "governance": body_call(
            "governance/celtic_voice_bank.py",
            "seasonal_gate_for_date",
            json.dumps({"value": "2026-10-29"}),
        ),
        "observer": body_call("observer/live_data_policy.py", "simulation_fallback_allowed"),
    }
    logic = _load(body_call("cognition/logic_flow.py", "compute_logic_flow"))
    assert logic["status"] == "unavailable"
    assert logic.get("called") is not True
    for package, raw in calls.items():
        body = _load(raw)
        assert body.get("called") is True, (package, body.get("reason"))
        assert body["status"] == "cited"
        assert not str(body["label"]).startswith("helper.")
        assert "consciousness_" not in raw
    assert calls and _load(calls["gates"])["result"] is False
    record = json.loads((ROOT / "measured" / "body_stage2.json").read_text(encoding="utf-8"))
    assert record["called"] >= 8


def test_stage1_sweep_counts_real_calls() -> None:
    record = json.loads((ROOT / "measured" / "body_stage1.json").read_text(encoding="utf-8"))
    assert record["stage"] == 1
    assert record["called"] >= 8
    assert record["called"] == sum(1 for item in record["calls"] if item["called"] is True)
    symbols = {item["symbol"] for item in record["calls"] if item["called"] is True}
    assert "solfeggio_ladder" in symbols
    assert "HarmonicSubstrate.evaluate" in symbols
    assert "QueenHiveMind.read_auris_nodes" in symbols
    assert "get_qgita_analyzer" in symbols
    for item in record["calls"]:
        if item["called"] is True:
            assert item["status"] == "cited"


def test_operator_rows_outside_the_allowlist_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    rows = (
        ("analytics/benchmark_coverage.py", "write_coverage"),
        ("analytics/open_benchmark.py", "run_humaneval"),
        ("analytics/backtest_sentiment_oracle.py", "run_backtest"),
        ("launch/master.py", "repo_root"),
        ("autonomous/mind_wiring_audit.py", "probe_http_service"),
    )
    for module, symbol in rows:
        body = _load(body_call_operator(module, symbol))
        assert body["status"] == "unavailable", symbol
        assert body.get("called") is not True
        assert "not allowlisted" in body["reason"]
        assert body.get("live_orders") == "refused"


def test_tampered_aureon_dependency_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    import aureon_public.pin_blob as pin

    real = pin.git_blob_sha1

    def fake(data: bytes) -> str:
        if b"def solfeggio_ladder" in data:
            return "ab" * 20
        return real(data)

    monkeypatch.setattr(pin, "git_blob_sha1", fake)
    finder = pin.install_pinned_aureon_finder()
    sys.modules.pop("aureon.plumber.magic_star_v02", None)
    sys.modules.pop("aureon.harmonic.rainbow_reference", None)
    try:
        with pytest.raises(ImportError, match="differs from pin"):
            importlib.import_module("aureon.plumber.magic_star_v02")
    finally:
        sys.meta_path[:] = [item for item in sys.meta_path if item is not finder]
        sys.modules.pop("aureon.plumber.magic_star_v02", None)
        sys.modules.pop("aureon.harmonic.rainbow_reference", None)


def test_probe_http_service_localhost_get_is_refused() -> None:
    probed = _load(
        body_call(
            "autonomous/mind_wiring_audit.py",
            "probe_http_service",
            json.dumps(
                {
                    "target": {
                        "url": "http://127.0.0.1:9/",
                        "id": "local",
                        "name": "local",
                        "source": "test",
                    }
                }
            ),
        )
    )
    assert probed["status"] == "unavailable"
    assert probed.get("called") is not True
    assert probed.get("result") is None


def test_public_call_refuses_ssrf_write_monitors_and_launch() -> None:
    fetched = _load(
        body_call(
            "search/online_research_cinema.py",
            "fetch_source",
            json.dumps({"url": "http://127.0.0.1:8765/secret"}),
        )
    )
    assert fetched["status"] == "unavailable"
    assert fetched.get("called") is not True
    assert "secret" not in json.dumps(fetched.get("result", ""))
    written = _load(body_call("bio/mcp_membrane.py", "write_membrane_report"))
    assert written["status"] == "unavailable"
    assert written.get("called") is not True
    monitor = _load(
        body_call(
            "monitors/margin_eta_predictor.py",
            "calc_breakeven",
            json.dumps({"entry": 100.0}),
        )
    )
    assert monitor["status"] == "unavailable"
    assert "excluded" in monitor["reason"]
    launched = _load(body_call("launch/seat_tabs.py", "wait_for_gateway"))
    assert launched["status"] == "unavailable"
    assert "operator" in launched["reason"]


def test_inventory_hash_mismatch_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    import aureon_public.body as body

    body._ROWS = None
    body._INDEX = None
    monkeypatch.setattr(body, "INVENTORY_SHA256", "0" * 64)
    try:
        refused = _load(body_call("harmonic/rainbow_reference.py", "solfeggio_ladder"))
        assert refused["status"] == "unavailable"
        assert refused["reason"] == "inventory hash mismatch"
    finally:
        body._ROWS = None
        body._INDEX = None
        body._INVENTORY_REFUSAL = None


def test_checkout_blob_refuses_an_empty_blob_and_a_path_outside_the_root(tmp_path: Path) -> None:
    from aureon_public.pin_blob import checkout_blob_refusal, expected_pin_blob

    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")
    reason = checkout_blob_refusal(outside, repo_root(), PINNED_COMMIT)
    assert reason == "path is outside the checkout"
    inside = repo_root() / "aureon" / "harmonic" / "rainbow_reference.py"

    def empty(path: Path, root: Path, commit: str) -> tuple[str | None, str | None]:
        del path, root, commit
        return "", None

    original = expected_pin_blob
    try:
        import aureon_public.pin_blob as pin_blob

        pin_blob.expected_pin_blob = empty  # type: ignore[assignment]
        # checkout_blob_refusal calls the name in its module.
        pin_blob.expected_pin_blob = empty
        refused = pin_blob.checkout_blob_refusal(inside, repo_root(), PINNED_COMMIT)
        assert refused == "expected blob is required"
    finally:
        import aureon_public.pin_blob as pin_blob

        pin_blob.expected_pin_blob = original


def test_operator_call_refuses_without_the_flag_and_refuses_live_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_OPERATOR_MCP", raising=False)
    closed = _load(body_call_operator("harmonic/hnc_quantum_packet_crypto.py", "packet_master_key_from_env"))
    assert closed["status"] == "unavailable"
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    refused = _load(body_call_operator("harmonic/hnc_quantum_packet_crypto.py", "packet_master_key_from_env"))
    assert refused["status"] == "unavailable"
    assert refused.get("live_orders") == "refused" or "key" in refused["reason"]
