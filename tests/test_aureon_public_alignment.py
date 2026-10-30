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
    assert alignment["reachable"] == 11
    assert alignment["opened_by_allowlist"] == 3


def test_constructor_allowlist_keeps_the_alignment_dataclasses() -> None:
    from aureon_public.body import _CONSTRUCTOR_ALLOWLIST, _function_source
    from aureon_public.inventory_scan import source_is_risky

    assert {
        ("alignment/harmonic_resonance.py", "HarmonicAnalysis"),
        ("alignment/pillar_alignment.py", "AlignmentCycleResult"),
        ("alignment/unified_directive.py", "MasterDirective"),
    } <= _CONSTRUCTOR_ALLOWLIST
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

    pillar = _load(alignment_pillar_factory())
    assert pillar["status"] == "cited"
    assert pillar["called"] is True
    assert "consciousness_" not in json.dumps(pillar)
    assert pillar["result"]["fields"]["config"]["fields"]["auto_load_pillars"] is False

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


def test_default_fixtures_are_not_live_readings() -> None:
    from aureon_public.alignment_layer import (
        FIXTURE_NOTE,
        FIXTURE_SOURCE,
        alignment_consonance_read,
        alignment_full_analysis,
        alignment_signal_consensus,
    )

    default_full = _load(alignment_full_analysis())
    assert default_full["input_source"] == FIXTURE_SOURCE
    assert default_full["input_note"] == FIXTURE_NOTE
    note = default_full["input_note"].lower()
    assert "not a live market reading" in note
    assert "not a lighthouse reading" in note
    assert default_full["result"]["lighthouse_cleared"] is True
    assert default_full["result"]["dominant_signal"] == "BUY"
    assert default_full["result"]["alignment_score"] == 0.9898

    other = _load(alignment_consonance_read(2.0))
    assert "input_source" not in other
    split = _load(alignment_signal_consensus())
    assert split["input_source"] == FIXTURE_SOURCE


def test_stage1_tools_do_not_import_queen_miner_or_swarm_motion() -> None:
    import subprocess
    import sys

    code = """
import socket
import sys
sys.path.insert(0, sys.argv[1])
from aureon_public.alignment_layer import TOOLS as ALIGNMENT
from aureon_public.stage1_rest import TOOLS as STAGE1
from aureon_public.call_worker import _call
from aureon_public.body import dotted_for
import aureon_public.body as body

opened = []
def _refuse_socket(*args, **kwargs):
    opened.append((args, kwargs))
    raise RuntimeError("socket opened")
socket.socket = _refuse_socket
socket.create_connection = _refuse_socket

def inline(module, symbol, arguments, timeout):
    del timeout
    try:
        return "ok", _call(dotted_for(module), symbol, arguments, module)
    except Exception as exc:
        return "error", f"{type(exc).__name__}: {exc}"

body._call_in_subprocess = inline
tools = list(ALIGNMENT) + list(STAGE1)
names = [fn.__name__ for fn in tools]
if "alignment_unified_factory" in names:
    raise SystemExit("alignment_unified_factory is still a stage-1 tool")
for fn in tools:
    fn()
if opened:
    raise SystemExit("socket opened")
prefixes = (
    "aureon.miner",
    "aureon.queen",
    "aureon.swarm_motion",
    "aureon.inhouse_ai",
    "aureon.integrations.ollama",
    "requests",
    "httpx",
)
bad = []
for name in sys.modules:
    if name in {"requests", "httpx"} or name.startswith(("requests.", "httpx.")):
        bad.append(name)
        continue
    if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes):
        bad.append(name)
        continue
    lowered = name.lower()
    if "brain" in lowered or lowered.endswith("adapter") or ".adapter" in lowered or "ollama" in lowered:
        bad.append(name)
if bad:
    raise SystemExit("imported " + ", ".join(sorted(set(bad))))
"""
    mcp = str(ROOT / "mcp")
    completed = subprocess.run(
        [sys.executable, "-c", code, mcp],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout


def test_stage1_dispatch_does_not_load_inhouse_ai_or_ollama() -> None:
    """Every stage-1 tool goes through dispatch. Neither process loads the adapter chain."""

    import subprocess
    import sys

    code = r"""
import json
import os
import sys

os.environ["AUREON_PUBLIC_REPORT_MODULES"] = "1"
sys.path.insert(0, sys.argv[1])
from aureon_public.alignment_layer import TOOLS as ALIGNMENT
from aureon_public.stage1_rest import TOOLS as STAGE1
import aureon_public.body as body

tools = list(ALIGNMENT) + list(STAGE1)
names = [fn.__name__ for fn in tools]
banned = [
        name
        for name in names
        if name in {"alignment_unified_factory", "organism_compose_layers", "swarm_build_lane"}
    ]
if banned:
    raise SystemExit("removed tool still registered: " + ", ".join(banned))
body.reported_worker_modules.clear()
body.reported_worker_module_reports = 0
for fn in tools:
    raw = fn()
    loaded = json.loads(raw)
    if loaded.get("called") is not True:
        raise SystemExit(fn.__name__ + " did not run: " + raw[:400])

def forbidden(modules):
    return sorted(name for name in modules if "inhouse_ai" in name or "ollama_config" in name)

server = forbidden(sys.modules)
worker = forbidden(body.reported_worker_modules)
if server or worker:
    raise SystemExit(f"server={server} worker={worker}")
if body.reported_worker_module_reports != len(tools):
    raise SystemExit(
        f"worker reports {body.reported_worker_module_reports} for {len(tools)} tools"
    )
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(ROOT / "mcp")],
        cwd="/tmp",
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-4000:] + completed.stdout[-1000:]


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
    assert "alignment_unified_factory" not in record["calls"]
    fixture_calls = {
        "alignment_consonance_read",
        "alignment_frequency_harmony",
        "alignment_full_analysis",
        "alignment_geometric_mean",
        "alignment_phase_coherence",
        "alignment_signal_consensus",
    }
    for name, call in record["calls"].items():
        body = json.loads(call["text"])
        assert body["aureon_source"]["kind"] == "pinned", name
        assert body["aureon_source"]["commit"] == PINNED_COMMIT
        assert "consciousness_" not in call["text"]
        assert call["isError"] is False
        if name in fixture_calls:
            source = "tests/stress/stress_test_inhouse_ai.py::test_harmonic_math"
            assert call["input_source"] == source
            assert body["input_source"] == source
            assert "not a live market reading" in call["input_note"].lower()
            assert "not a lighthouse reading" in body["input_note"].lower()
    full = json.loads(record["calls"]["alignment_full_analysis"]["text"])
    assert full["result"]["lighthouse_cleared"] is True
    assert full["result"]["dominant_signal"] == "BUY"
    assert full["result"]["alignment_score"] == 0.9898
    for name in (
        "alignment_harmonic_to_dict",
        "alignment_cycle_to_dict",
        "alignment_directive_to_dict",
    ):
        call = record["calls"][name]
        body = json.loads(call["text"])
        assert "dataclass defaults" in body["input_note"]
        assert "not a reading" in body["input_note"]
        assert call["input_source"] == body["input_source"]
    derived = json.loads(record["calls"]["alignment_derive_phase"]["text"])
    assert "fixed example arguments" in derived["input_note"]
    assert "not a reading" in derived["input_note"]
    assert record["calls"]["alignment_derive_phase"]["input_source"] == derived["input_source"]
