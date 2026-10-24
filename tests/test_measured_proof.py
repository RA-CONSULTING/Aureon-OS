"""The committed measured-proof files match a fresh run. HOLD stays HOLD."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MEASURED = ROOT / "reports" / "measured"


def _load(name: str) -> dict:
    return json.loads((MEASURED / name).read_text(encoding="utf-8"))


def test_brain_proof_matches_the_committed_run_and_holds_without_labels():
    from aureon.evaluation.brain_proof import evaluate_brain
    from aureon.harmonic.aureon_harmonic_reality import (
        DEFAULT_ALPHA,
        DEFAULT_BETA,
        DEFAULT_DELTA_T,
        DEFAULT_G,
        DEFAULT_TAU,
    )

    fresh = json.loads(json.dumps(evaluate_brain(ROOT), sort_keys=True))
    assert fresh == _load("brain.json")
    assert _load("auris_nodes.json") == fresh["auris"]
    assert _load("qgita_snr.json") == fresh["qgita"]
    hnc = fresh["hnc"]
    assert hnc["parameters"]["alpha"] == DEFAULT_ALPHA
    assert hnc["parameters"]["beta"] == DEFAULT_BETA
    assert hnc["parameters"]["tau"] == DEFAULT_TAU
    assert hnc["parameters"]["g"] == DEFAULT_G
    assert hnc["parameters"]["delta_t"] == DEFAULT_DELTA_T
    assert hnc["enable_multiverse"] is False
    assert hnc["multiverse_extension"]["verdict"] == "measured"
    assert hnc["multiverse_extension"]["series_identical"] is True
    assert hnc["multiverse_extension"]["recorded_noise_all_zero"] is True
    assert "unseeded" not in hnc["multiverse_extension"]["reason"]
    assert fresh["qgita"]["derived_series"]["series_class"] == "derived"
    assert fresh["qgita"]["derived_series"]["evidence_tag"] == "cited-unverified"
    assert "public market data" in fresh["qgita"]["derived_series"]["provenance"]
    assert fresh["auris"]["trade_readiness"]["verdict"] == "HOLD"
    assert "Owl" in fresh["auris"]["hold_nodes"]
    assert "Clownfish" in fresh["auris"]["hold_nodes"]
    assert "hit_rate" not in fresh["auris"]
    assert fresh["qgita"]["derived_series"]["detection_rate"] is None
    assert fresh["qgita"]["derived_series"]["false_alarm_rate"] is None
    assert fresh["qgita"]["derived_series"]["rates_verdict"] == "HOLD"
    assert fresh["qgita"]["on_hnc_series"]["detection_rate"] is None
    assert fresh["together"]["auris_joined_to_lambda"]["verdict"] == "HOLD"
    assert fresh["external_llm"] is False
    assert fresh["live_trading"] is False
    assert fresh["orders_placed"] is False
    assert "conscious" in fresh["note"]
    assert "alive" in fresh["note"]


def test_self_coder_offline_hold_matches_the_committed_run(monkeypatch: pytest.MonkeyPatch):
    from aureon.autonomous.self_coder_benchmark import run_harness

    monkeypatch.delenv("AUREON_SELF_CODER_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("AUREON_SELF_CODER_API_KEY", raising=False)
    fresh = run_harness(ROOT)
    committed = _load("self_coder.json")
    assert fresh["external_provider"]["called"] is False
    assert fresh["external_provider"]["enabled"] is False
    assert fresh["external_provider"]["counts_as_aureon_brain"] is False
    assert fresh["model_call"]["attempted"] is False
    assert fresh["humaneval"]["status"] == "not_attempted"
    assert fresh["humaneval"]["counts_as_aureon_score"] is False
    assert fresh["humaneval"]["counts_as_model_score"] is False
    assert fresh["humaneval"]["external_provider_called"] is False
    assert fresh["humaneval"]["attempted"] == 0
    assert fresh["humaneval"]["passed"] == 0
    assert fresh["humaneval"]["not_attempted"] == fresh["humaneval"]["rows"]
    assert fresh["humaneval"]["measured_pct"] is None
    assert fresh["humaneval"]["dataset"] == "data/research/open_benchmarks/humaneval.jsonl"
    assert fresh["humaneval"]["per_row_auris_qgita"]["kind"] == "synthetic"
    assert "not a market" in fresh["humaneval"]["per_row_auris_qgita"]["note"]
    assert "not a coding score" in fresh["humaneval"]["per_row_auris_qgita"]["note"]
    assert fresh["flagship_comparison"]["status"] == "HOLD"
    assert fresh["flagship_comparison"]["this_run_humaneval_pct"] is None
    assert fresh["flagship_comparison"]["this_run_swe_bench_pct"] is None
    assert fresh["flagship_comparison"]["published_references_are_not_this_run"] is True
    assert fresh["model_python_task_pass_pct"]["humaneval_rows"] is None
    assert fresh["model_python_task_pass_pct"]["swe_rows"] is None
    assert fresh["endpoint"]["api_key_returned"] is False
    assert fresh["endpoint"]["api_key_configured"] is False
    assert fresh["humaneval"]["results"][0]["self_coder_status"] == "internal_self_coder_disabled"
    assert fresh["humaneval"]["results"][0]["program_emitted"] is False
    assert committed["humaneval"]["status"] == fresh["humaneval"]["status"]
    assert committed["humaneval"]["rows"] == fresh["humaneval"]["rows"]
    assert committed["humaneval"]["measured_pct"] == fresh["humaneval"]["measured_pct"]
    assert committed["humaneval"]["not_attempted"] == fresh["humaneval"]["not_attempted"]
    assert committed["humaneval"]["results"] == fresh["humaneval"]["results"]
    assert committed["external_provider"]["called"] is False
    assert committed["flagship_comparison"]["this_run_humaneval_pct"] is None
    assert committed["dataset_solution_smoke"]["counts_as_model_score"] is False
    assert committed["live_trading"] is False


def _without_timing(report: dict) -> dict:
    body = json.loads(json.dumps(report))
    body.get("connectivity", {}).pop("timing", None)
    return body


def test_organism_connectivity_and_self_model_match_the_committed_run():
    from aureon.evaluation.organism_proof import evaluate_organism

    fresh = evaluate_organism()
    committed = _load("organism.json")
    assert _without_timing(fresh) == _without_timing(committed)
    connectivity = fresh["connectivity"]
    assert connectivity["timing"]["elapsed_s"] > 0
    assert connectivity["timing"]["messages_per_second"] > 0
    latency = connectivity["timing"]["latency_s"]
    assert latency["count"] == connectivity["latency_samples"]
    assert latency["min"] >= 0
    assert latency["max"] >= latency["min"]
    assert fresh["external_llm"] is False
    assert fresh["ollama"] is False
    assert fresh["cognition"] == "internal"
    assert fresh["live_trading"] is False
    assert fresh["orders_placed"] is False
    assert fresh["self_model"]["fault"]["origin"] == "synthetic"
    assert "injected by the harness" in fresh["self_model"]["fault"]["note"]
    assert fresh["self_model"]["external_llm"] is False
    prediction = fresh["self_model"]["prediction"]
    fault = fresh["self_model"]["fault"]
    assert prediction["accuracy"] > prediction["baseline_accuracy"]
    assert fault["detection_rate"] > fault["baseline_detection_rate"]
    assert "conscious" in fresh["note"]
    assert "alive" in fresh["note"]
    assert connectivity["http_seat_bound"] is False
    assert committed["live_trading"] is False


def test_a_disconnected_circulation_seat_fails_the_connectivity_audit():
    from aureon.evaluation.organism_proof import evaluate_organism

    fresh = evaluate_organism(disabled=("queen",))
    connectivity = fresh["connectivity"]
    assert "queen" in connectivity["isolated"]
    assert connectivity["verdict"] == "fail"
    assert connectivity["seats"]["queen"]["published"] == 0
    assert connectivity["seats"]["queen"]["consumed"] == 0
    assert connectivity["score"] < 1
    assert connectivity["score"] == connectivity["connected"] / connectivity["roster"]
    assert fresh["external_llm"] is False
    assert fresh["live_trading"] is False


def test_humaneval_reference_solution_runs_in_the_harness():
    from aureon.autonomous.self_coder_benchmark import (
        _load_jsonl,
        _run_python,
        humaneval_reference_program,
        humaneval_tests,
    )

    rows = _load_jsonl(ROOT / "data" / "research" / "open_benchmarks" / "humaneval.jsonl")
    row = next(item for item in rows if item["task_id"] == "HumanEval/2")
    assert _run_python(humaneval_reference_program(row), humaneval_tests(row)) is True


def test_configured_endpoint_can_score_a_humaneval_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    from aureon.autonomous.self_coder_benchmark import run_harness

    row = {
        "task_id": "HumanEval/add",
        "prompt": "def add(a, b):\n",
        "entry_point": "add",
        "canonical_solution": "    return a + b\n",
        "test": "def check(candidate):\n    assert candidate(1, 2) == 3\n",
    }
    path = tmp_path / "humaneval.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

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
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("AUREON_SELF_CODER_OPENAI_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setenv("AUREON_SELF_CODER_MODEL", "local-test")
    monkeypatch.setenv("AUREON_SELF_CODER_HUMANEVAL_PATH", str(path))
    monkeypatch.delenv("AUREON_SELF_CODER_ALLOW_EXTERNAL", raising=False)
    calls = {"n": 0}
    original = Handler.do_POST

    def counting_post(self):  # noqa: N802
        calls["n"] += 1
        original(self)

    Handler.do_POST = counting_post
    try:
        quiet = run_harness(tmp_path)
        assert calls["n"] == 0
        assert quiet["external_provider"]["called"] is False
        assert quiet["humaneval"]["measured_pct"] is None
        assert quiet["humaneval"]["status"] == "not_attempted"
        assert quiet["humaneval"]["counts_as_aureon_score"] is False
        assert quiet["humaneval"]["not_attempted"] == 1
        assert quiet["model_python_task_pass_pct"]["humaneval_rows"] is None
        assert quiet["flagship_comparison"]["this_run_humaneval_pct"] is None
        assert quiet["flagship_comparison"]["status"] == "HOLD"
        monkeypatch.setenv("AUREON_SELF_CODER_ALLOW_EXTERNAL", "1")
        report = run_harness(tmp_path)
    finally:
        server.shutdown()
    assert calls["n"] > 0
    assert report["external_provider"]["called"] is True
    assert report["external_provider"]["counts_as_aureon_brain"] is False
    assert report["external_provider"]["humaneval_pct"] == 100.0
    assert report["humaneval"]["measured_pct"] is None
    assert report["humaneval"]["counts_as_aureon_score"] is False
    assert report["humaneval"]["status"] == "not_attempted"
    assert report["model_python_task_pass_pct"]["humaneval_rows"] is None
    assert report["flagship_comparison"]["status"] == "HOLD"
    assert report["flagship_comparison"]["this_run_humaneval_pct"] is None
    assert report["flagship_comparison"]["published_references_are_not_this_run"] is True
