"""Alignment layer tools. Fixed inputs are the harmonic-math stress test."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    return json.loads(text)


def test_coverage_plan_matches_the_inventory() -> None:
    from aureon_public.body import INVENTORY_SHA256, _BLOCKED, package_depth
    from aureon_public.coverage_plan import plan_rows, render

    text = (ROOT / "mcp" / "aureon_public" / "COVERAGE_PLAN.md").read_text(encoding="utf-8")
    assert text == render()
    assert INVENTORY_SHA256 in text
    rows = plan_rows()
    depth = package_depth()
    assert sum(row["listed"] for row in rows) == 20083
    assert sum(row["public_entry_points"] for row in rows) == sum(
        item["public_entry_points"] for item in depth.values()
    )
    assert sum(row["reachable"] for row in rows) == sum(item["reachable"] for item in depth.values())
    assert rows[0]["package"] == "alignment"
    assert rows[0]["stage"] == 1
    last = [row["package"] for row in rows if row["stage"] == 4]
    for name in (*_BLOCKED, "unified_margin_trader"):
        assert name in last
    alignment = next(row for row in rows if row["package"] == "alignment")
    assert alignment["public_entry_points"] == 24
    assert alignment["reachable"] == 12
    assert alignment["opened_by_allowlist"] == 3


def test_constructor_allowlist_is_three_dataclasses() -> None:
    from aureon_public.body import _CONSTRUCTOR_ALLOWLIST, _function_source
    from aureon_public.inventory_scan import source_is_risky

    assert _CONSTRUCTOR_ALLOWLIST == {
        ("alignment/harmonic_resonance.py", "HarmonicAnalysis"),
        ("alignment/pillar_alignment.py", "AlignmentCycleResult"),
        ("alignment/unified_directive.py", "MasterDirective"),
    }
    for module, class_name in _CONSTRUCTOR_ALLOWLIST:
        source = _function_source(module, f"{class_name}.__init__")
        assert source_is_risky(source) is False
    assert ("alignment/pillar_alignment.py", "PillarAlignment") not in _CONSTRUCTOR_ALLOWLIST
    assert ("alignment/unified_directive.py", "UnifiedHarmonicDirective") not in _CONSTRUCTOR_ALLOWLIST


def test_alignment_tools_match_the_harmonic_math_baseline() -> None:
    """Inequalities copied from tests/stress/stress_test_inhouse_ai.py::test_harmonic_math."""

    from aureon_public.alignment_layer import (
        AGREE_SIGNALS,
        SPLIT_SIGNALS,
        alignment_consonance_read,
        alignment_frequency_harmony,
        alignment_full_analysis,
        alignment_geometric_mean,
        alignment_phase_coherence,
        alignment_signal_consensus,
    )

    def score(raw: str) -> dict:
        body = _load(raw)
        assert body["status"] == "cited", body
        assert body["called"] is True
        assert "consciousness_" not in raw
        assert not str(body["label"]).startswith("helper.")
        return body

    assert abs(score(alignment_consonance_read(1.0))["result"] - 1.0) <= 0.001
    assert abs(score(alignment_consonance_read(2.0))["result"] - 1.0) <= 0.001
    assert abs(score(alignment_consonance_read(1.5))["result"] - 1.0) <= 0.001
    assert score(alignment_consonance_read(math.sqrt(2)))["result"] >= 0.9

    agree = score(alignment_signal_consensus(json.dumps(AGREE_SIGNALS)))
    assert abs(agree["result"][0] - 1.0) <= 0.001
    split = score(alignment_signal_consensus(json.dumps(SPLIT_SIGNALS)))
    assert abs(split["result"][0] - (1 / 3)) <= 0.01

    aligned = score(alignment_phase_coherence(json.dumps([0.0, 0.0, 0.0])))
    assert abs(aligned["result"] - 1.0) <= 0.001
    scattered = score(
        alignment_phase_coherence(json.dumps([0.0, 2 * math.pi / 3, 4 * math.pi / 3]))
    )
    assert scattered["result"] <= 0.01

    assert abs(score(alignment_geometric_mean(json.dumps([1, 1, 1, 1])))["result"] - 1.0) <= 0.001
    assert score(alignment_geometric_mean(json.dumps([1, 1, 1, 0])))["result"] <= 0.01

    perfect = score(alignment_full_analysis())
    assert perfect["result"]["lighthouse_cleared"] is True
    assert perfect["result"]["alignment_score"] >= 0.94
    scattered_stack = [
        {
            "pillar": f"P{index}",
            "signal": "BUY" if index < 2 else "SELL" if index < 4 else "NEUTRAL",
            "confidence": 0.5,
            "coherence": 0.4,
            "frequency_hz": 528.0,
        }
        for index in range(6)
    ]
    disagreement = score(alignment_full_analysis(json.dumps(scattered_stack), 0.0))
    assert disagreement["result"]["lighthouse_cleared"] is False

    lock = score(alignment_frequency_harmony())
    assert lock["result"][0] >= 0.99


def test_alignment_fixed_inputs_and_refused_entry_points() -> None:
    from aureon_public.alignment_layer import (
        alignment_cycle_to_dict,
        alignment_derive_phase,
        alignment_directive_to_dict,
        alignment_harmonic_to_dict,
        alignment_pillar_factory,
        alignment_signal_consensus,
        alignment_unified_factory,
    )
    from aureon_public.body import body_call

    phase = _load(alignment_derive_phase(528.0, 0.0, "BUY"))
    assert phase["called"] is True
    assert phase["result"] == 0.0
    sell = _load(alignment_derive_phase(528.0, 0.0, "SELL"))
    assert math.isclose(sell["result"], math.pi)

    surface = _load(alignment_harmonic_to_dict())
    assert surface["called"] is True
    assert surface["result"]["dominant_signal"] == "NEUTRAL"
    assert surface["result"]["lighthouse_cleared"] is False

    cycle = _load(alignment_cycle_to_dict("fixed", 0.0))
    assert cycle["called"] is True
    assert cycle["result"]["cycle_id"] == "fixed"
    assert cycle["result"]["timestamp"] == 0.0

    directive = _load(alignment_directive_to_dict("fixed", 0.0))
    assert directive["called"] is True
    assert directive["result"]["directive_id"] == "fixed"
    assert directive["result"]["timestamp"] == 0.0
    assert directive["result"]["dominant_frequency_hz"] == 528.0

    for raw in (alignment_pillar_factory(), alignment_unified_factory()):
        body = _load(raw)
        assert body["status"] == "cited"
        assert body["called"] is True
        assert "consciousness_" not in raw

    missing = _load(alignment_signal_consensus("not-json"))
    assert missing["status"] == "unavailable"
    assert missing.get("called") is not True

    refused_name = _load(
        body_call("alignment/pillar_alignment.py", "PillarAlignment.run_synthetic_cycle")
    )
    assert refused_name["status"] == "unavailable"
    assert refused_name.get("called") is not True
    assert "name is not called" in refused_name["reason"]

    refused_constructor = _load(
        body_call("alignment/pillar_alignment.py", "PillarAlignment.load_pillars")
    )
    assert refused_constructor["status"] == "unavailable"
    assert "constructor is not allowlisted" in refused_constructor["reason"]

    trading = _load(body_call("trading/__init__.py", "__init__"))
    assert trading["live_orders"] == "refused"
    assert trading.get("called") is not True


def test_alignment_measured_record_is_a_pinned_run() -> None:
    from aureon_public.guard_loader import PINNED_COMMIT

    record = json.loads(
        (ROOT / "measured" / "aureon_public_alignment.json").read_text(encoding="utf-8")
    )
    direct = record["environment"]["aureon_direct_url"]
    assert direct["vcs_info"]["commit_id"] == PINNED_COMMIT
    assert record["environment"]["python"].endswith("/python")
    assert "python3.12" in record["environment"]["aureon_file"] or record["environment"][
        "python"
    ].startswith("/tmp/aureon-public-venv/")
    for name, call in record["calls"].items():
        body = json.loads(call["text"])
        assert body["aureon_source"]["kind"] == "pinned", name
        assert body["aureon_source"]["commit"] == PINNED_COMMIT
        assert "consciousness_" not in call["text"]
        assert call["isError"] is False
