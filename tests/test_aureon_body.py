"""Full-body caller. Depth is a real call. A listed row is not depth."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from aureon_public.body import body_call, body_call_operator, body_surface, enabled_stage  # noqa: E402
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
    assert substrate["called"] is True
    assert isinstance(substrate["result"], float)

    nodes = _load(body_call("utils/aureon_queen_hive_mind.py", "QueenHiveMind.read_auris_nodes"))
    assert nodes["called"] is True
    assert nodes["auris_meaning"] == "nine nodes"
    assert "conjecture is not called" in nodes["auris_note"]
    assert "consciousness_" not in json.dumps(nodes)

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
    assert surface["called"] is False
    assert surface["status"] == "cited"
    assert "HarmonicSubstrate.evaluate" in surface["methods"]
    assert enabled_stage() >= 1

    real = repo_root() / "aureon" / "harmonic" / "rainbow_reference.py"
    assert checkout_blob_refusal(real, repo_root(), PINNED_COMMIT) is None
    changed = tmp_path / "rainbow_reference.py"
    changed.write_bytes(real.read_bytes() + b"\n# changed\n")

    def refuse(path: Path, root: Path, commit: str) -> str:
        del root, commit
        if path == real:
            return "checkout rainbow_reference.py differs from pin a00f744d"
        return None

    monkeypatch.setattr("aureon_public.body.checkout_blob_refusal", refuse)
    monkeypatch.setattr("aureon_public.body._outside", lambda origin, root: False)
    refused = _load(body_call("harmonic/rainbow_reference.py", "solfeggio_ladder"))
    assert refused["status"] == "unavailable"
    assert "differs from pin" in refused["reason"]


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


def test_operator_call_refuses_without_the_flag_and_refuses_live_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUREON_OPERATOR_MCP", raising=False)
    closed = _load(body_call_operator("harmonic/hnc_quantum_packet_crypto.py", "packet_master_key_from_env"))
    assert closed["status"] == "unavailable"
    monkeypatch.setenv("AUREON_OPERATOR_MCP", "1")
    refused = _load(body_call_operator("harmonic/hnc_quantum_packet_crypto.py", "packet_master_key_from_env"))
    assert refused["status"] == "unavailable"
    assert refused.get("live_orders") == "refused" or "key" in refused["reason"]
