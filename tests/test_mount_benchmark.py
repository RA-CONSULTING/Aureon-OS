"""
Aureon — Mount Integration Benchmark tests.

Fast, deterministic coverage of the grading/report logic (no engine), plus a
bounded live subset that drives real probes through the `/v1` mount and asserts the
smooth-integration guarantees hold: valid OpenAI shape, boundary → content_filter,
both engines reachable, intact `aureon` provenance. Offline, no network.
"""

from __future__ import annotations

import json

import pytest

from aureon.operator import mount_benchmark as mb

pytest.importorskip("flask", reason="the mount HTTP surface requires the `.[operator]` extra")


# ── pure logic (fast, no engine) ───────────────────────────────────────────────

def test_parse_sse_reads_chunks_and_done():
    text = (
        'data: {"object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"}}]}\n\n'
        'data: {"object":"chat.completion.chunk","choices":[{"delta":{"content":"hi"}}]}\n\n'
        'data: [DONE]\n\n'
    )
    chunks, done = mb._parse_sse(text)
    assert done is True
    assert len(chunks) == 2
    assert chunks[0]["object"] == "chat.completion.chunk"


def _row(**over):
    base = {"id": "x", "kind": "grounded", "shape_valid": True, "engine": "cognition",
            "blocked": False, "grounded": True, "finish_reason": "stop", "n_stages": 4,
            "latency_ms": 10.0}
    base.update(over)
    return base


def test_build_report_passes_when_guarantees_hold():
    rows = [
        _row(id="g", kind="grounded", engine="cognition"),
        _row(id="b", kind="boundary", engine="cognition", blocked=True,
             finish_reason="content_filter", grounded=False),
        _row(id="s", kind="switchboard", engine="switchboard"),
    ]
    checks = [mb._check("shape:g", True, "ok")]
    report = mb.build_report(checks, rows, {"engines": ["aureon-cognition", "aureon-switchboard"]})
    assert report["summary"]["status"] == "pass"
    assert report["metrics"]["shape_valid_rate"] == 1.0
    assert report["metrics"]["boundary_blocked_rate"] == 1.0
    assert report["metrics"]["both_engines"] is True
    names = {c["check"] for c in report["checks"]}
    assert {"all_shapes_valid", "boundary_always_blocked", "both_engines_reachable"} <= names


def test_build_report_fails_when_boundary_not_blocked():
    rows = [
        _row(id="b", kind="boundary", engine="cognition", blocked=False, finish_reason="stop"),
        _row(id="s", kind="switchboard", engine="switchboard"),
    ]
    report = mb.build_report([], rows, {"engines": []})
    assert report["summary"]["status"] == "fail"
    assert report["metrics"]["boundary_blocked_rate"] == 0.0


def test_build_report_fails_when_only_one_engine():
    rows = [_row(id="g", kind="grounded", engine="cognition"),
            _row(id="b", kind="boundary", engine="cognition", blocked=True,
                 finish_reason="content_filter")]
    report = mb.build_report([], rows, {"engines": []})
    assert report["metrics"]["both_engines"] is False
    assert report["summary"]["status"] == "fail"


# ── bounded live run through the real mount (2 probes: boundary + switchboard) ──

def test_live_subset_holds_integration_guarantees():
    from aureon.operator.operator_server import create_app

    client = create_app().test_client()
    by_id = {p["id"]: p for p in mb.DEFAULT_PROBES}
    subset = [by_id["boundary_refusal"], by_id["switchboard_engine"]]

    report = mb.run_mount_benchmark(probes=subset, client=client)

    # the report carries the LIVE manifest an AGI system reads to plug in
    imap = report["integration_map"]
    assert imap["service"] == "aureon-mount"
    assert imap["endpoint"] == "POST /v1/chat/completions"
    assert set(mb._manifest_engine_ids(imap)) == {"aureon-cognition", "aureon-switchboard"}
    for k in ("engine", "grounded", "conscience_verdict", "blocked", "stages", "host_mind"):
        assert k in imap["provenance_keys"]
    # the live-manifest guarantee is itself a passing check
    assert any(c["check"] == "integration_manifest_live" and c["ok"] for c in report["checks"])

    # the safety guarantee: the boundary probe was content_filter-blocked, nothing executed
    boundary = next(r for r in report["probes"] if r["kind"] == "boundary")
    assert boundary["blocked"] is True
    assert boundary["finish_reason"] == "content_filter"

    # both engines reachable + every critical check that ran passed → overall pass
    assert report["metrics"]["both_engines"] is True
    assert report["summary"]["status"] == "pass"
    # serialisable (it gets written as a JSON artifact)
    json.dumps(report)
