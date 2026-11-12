"""Stage-8 queen public read. Live orders stay off. No exchange call."""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "measured" / "aureon_public_queen_stage8.json"

pytestmark = pytest.mark.timeout(180)


@pytest.fixture(autouse=True)
def _mcp_path() -> None:
    from tests.support.mcp_isolation import ensure_mcp_path

    ensure_mcp_path()


def _reading(**kwargs: object) -> dict:
    from aureon_public.queen_read_gate import charlie_reading

    return charlie_reading(**kwargs)


def _tool(**kwargs: object) -> dict:
    from aureon_public.more_layers import queen_source_law_gate

    return json.loads(queen_source_law_gate(**kwargs))


def test_signature_has_no_order_switch() -> None:
    from aureon_public.more_layers import queen_source_law_gate

    names = set(inspect.signature(queen_source_law_gate).parameters)
    assert names == {"coherence_gamma", "lowest_node_confidence"}
    source = inspect.getsource(queen_source_law_gate)
    gate = (ROOT / "mcp" / "aureon_public" / "queen_read_gate.py").read_text(encoding="utf-8")
    for text in (source, gate):
        assert "place_order" not in text
        assert "import aureon.exchanges" not in text
        assert "import aureon.miner" not in text
        assert "import aureon.trading" not in text


def test_default_and_boundary_are_reads() -> None:
    missing = _reading()
    assert missing["status"] == "cited"
    assert missing["math_action"] == "HOLD"
    assert missing["public_action"] == "HOLD"
    assert missing["live_orders"] == "off"
    assert missing["orders_placed"] is False
    assert missing["exchange_calls"] == "not_performed"
    assert missing["order_permission"] == "refused"
    assert missing["release_boundary"] == "HOLD"
    assert missing["read_gated"] is True
    assert missing["pinned_entry_floor"] == 0.938

    above = _reading(coherence_gamma=0.99)
    assert above["math_action"] == "EXECUTE"
    assert above["public_action"] == "HOLD"
    assert above["live_orders"] == "off"
    assert above["orders_placed"] is False

    at_floor = _reading(coherence_gamma=0.938)
    assert at_floor["math_action"] == "EXECUTE"
    assert at_floor["public_action"] == "HOLD"

    below = _reading(coherence_gamma=0.9379)
    assert below["math_action"] == "HOLD"
    assert below["public_action"] == "HOLD"

    nodes = _reading(coherence_gamma=0.99, lowest_node_confidence=0.2)
    assert nodes["math_action"] == "HOLD"
    assert "node confidence" in nodes["reason"]
    assert nodes["orders_placed"] is False


def test_entry_env_cannot_lower_the_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_SOURCE_LAW_ENTRY", "0.5")
    held = _reading(coherence_gamma=0.94)
    assert held["pinned_entry_floor"] == 0.938
    assert held["entry_floor"] == 0.938
    assert held["math_action"] == "EXECUTE"
    assert held["public_action"] == "HOLD"
    assert held["live_orders"] == "off"

    monkeypatch.setenv("AUREON_SOURCE_LAW_ENTRY", "0.97")
    raised = _reading(coherence_gamma=0.96)
    assert raised["entry_floor"] == 0.97
    assert raised["math_action"] == "HOLD"
    assert raised["public_action"] == "HOLD"
    assert raised["orders_placed"] is False


def test_non_finite_reading_places_no_order() -> None:
    for value in (float("nan"), float("inf"), True, "0.99"):
        body = _reading(coherence_gamma=value)
        assert body["status"] == "unavailable"
        assert body["math_action"] == "HOLD"
        assert body["public_action"] == "HOLD"
        assert body["live_orders"] == "off"
        assert body["orders_placed"] is False


def test_banned_package_holds_the_math_action(monkeypatch: pytest.MonkeyPatch) -> None:
    import types

    from aureon_public import queen_read_gate

    planted = "aureon.trading.banned_probe"

    def _plant() -> tuple[None, None]:
        sys.modules[planted] = types.ModuleType(planted)
        return None, None

    monkeypatch.setattr(queen_read_gate, "_cited_floors", _plant)
    try:
        body = queen_read_gate.charlie_reading(0.99)
    finally:
        sys.modules.pop(planted, None)
    assert body["status"] == "unavailable"
    assert body["reason"] == "read loaded a banned package"
    assert body["banned_modules"] == [planted]
    assert body["math_action"] == "HOLD"
    assert body["public_action"] == "HOLD"
    assert body["live_orders"] == "off"
    assert body["orders_placed"] is False
    assert body["exchange_calls"] == "not_performed"


def test_tool_label_and_no_consciousness_keys() -> None:
    body = _tool(coherence_gamma=0.99)
    assert body["label"].startswith("helper. cited. queen_source_law_gate")
    assert "Charlie" not in body["label"]
    assert body["math_action"] == "EXECUTE"
    assert body["public_action"] == "HOLD"
    assert body["live_orders"] == "off"
    assert "consciousness_" not in json.dumps(body)


def test_fresh_process_does_not_import_an_exchange() -> None:
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(ROOT / 'mcp')!r})\n"
        "from aureon_public.queen_read_gate import charlie_reading\n"
        "body = charlie_reading(0.99)\n"
        "mods = [name for name in sys.modules if name == 'aureon.exchanges' "
        "or name.startswith('aureon.exchanges.') or name == 'aureon.miner' "
        "or name.startswith('aureon.miner.') or name == 'aureon.trading' "
        "or name.startswith('aureon.trading.')]\n"
        "json.dump({'live_orders': body['live_orders'], 'orders_placed': body['orders_placed'], "
        "'public_action': body['public_action'], 'math_action': body['math_action'], 'mods': mods}, sys.stdout)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    body = json.loads(completed.stdout)
    assert body["mods"] == []
    assert body["live_orders"] == "off"
    assert body["orders_placed"] is False
    assert body["public_action"] == "HOLD"
    assert body["math_action"] == "EXECUTE"


def test_body_call_opens_only_the_two_stage34_read_entries() -> None:
    """Stage 34 already opened two read-only rows. This slice does not add a gate."""

    from aureon_public.body import body_call, package_depth
    from aureon_public.guard_loader import PINNED_COMMIT
    from aureon_public.stage34_gate import READ_KEYS

    assert PINNED_COMMIT == "050891385291fb77c321996f25e307c794789d89"
    assert {
        ("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"),
        ("queen/temporal_ground.py", "compute_zpe_ground"),
    } == READ_KEYS
    depth = package_depth()
    assert depth["queen"]["reachable"] == 1
    assert depth["miner"]["reachable"] == 1
    assert depth["exchanges"]["reachable"] == 0

    queen = json.loads(
        body_call(
            "queen/temporal_ground.py",
            "compute_zpe_ground",
            json.dumps({"lambda_t": 1.0}),
        )
    )
    assert queen["status"] == "cited"
    assert queen.get("called") is True
    assert "plan stage 4 is not open" not in json.dumps(queen)
    assert queen["result"]["lambda_t"] == 1.0
    assert queen["result"]["grounded"] is True

    miner = json.loads(body_call("miner/miner_inhouse_ai_bridge.py", "MinerAIInsight.to_dict"))
    assert miner["status"] == "cited"
    assert miner.get("called") is True
    assert miner["result"]["verdict"] == "NEUTRAL"
    assert miner["result"]["category"] == ""

    other_queen = json.loads(body_call("queen/queen_quantum_frog.py", "update_health_status"))
    assert other_queen.get("called") is not True
    assert other_queen["reason"] == "plan stage 4 is not open"

    other_miner = json.loads(body_call("miner/miner_inhouse_ai_bridge.py", "get_miner_ai_bridge"))
    assert other_miner.get("called") is not True
    assert other_miner["status"] == "unavailable"

    equity = json.loads(body_call("exchanges/single_currency_equity.py", "gbp_equity_from_balances"))
    assert equity.get("called") is not True
    assert equity["reason"] == "operator entry point is not on aureon-public"
    assert equity.get("live_orders") == "refused"

    order = json.loads(body_call("trading/__init__.py", "__init__"))
    assert order.get("called") is not True
    assert order.get("live_orders") == "refused"


def test_sweep_record_matches_the_read_gate() -> None:
    assert RECORD.is_file(), "run measured/aureon_public_queen_stage8_sweep.sh"
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["pin"] == "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
    assert record["live_orders"] == "off"
    assert record["orders_placed"] is False
    assert record["exchange_calls"] == "not_performed"
    assert record["public_action"] == "HOLD"
    assert record["sockets"] == "blocked"
    assert record["processes"] == "blocked"
    assert record["writes"] == "outside sandbox blocked"
    assert "miner and exchanges are not opened" in record["scope"]
    gate = [row for row in record["attempts"] if row["tool"] == "queen_source_law_gate"]
    assert [row["label"] for row in gate] == [
        "default",
        "above_floor",
        "at_floor",
        "below_floor",
        "node_floor",
    ]
    for row in gate:
        assert row["refused"] is False, row
        assert row["sockets"] == []
        assert row["processes"] == ["Popen ['git', 'rev-parse', 'HEAD']"]
        assert row["source_stamp_blocked"] is True
        assert row["writes"] == []
        assert row["banned_modules"] == []
        result = row["result"]
        assert result["live_orders"] == "off"
        assert result["orders_placed"] is False
        assert result["exchange_calls"] == "not_performed"
        assert result["public_action"] == "HOLD"
        fresh = _reading(**row["arguments"])
        assert fresh["math_action"] == result["math_action"]
        assert fresh["public_action"] == "HOLD"
        assert fresh["orders_placed"] is False
    by_label = {row["label"]: row["result"]["math_action"] for row in gate}
    assert by_label["default"] == "HOLD"
    assert by_label["above_floor"] == "EXECUTE"
    assert by_label["at_floor"] == "EXECUTE"
    assert by_label["below_floor"] == "HOLD"
    assert by_label["node_floor"] == "HOLD"
    zpe = [row for row in record["attempts"] if row["tool"] == "queen_zpe_ground"]
    assert len(zpe) == 1
    assert zpe[0]["refused"] is False
    assert zpe[0]["banned_modules"] == []
    assert zpe[0]["sockets"] == []
    assert zpe[0]["processes"] == ["Popen ['git', 'rev-parse', 'HEAD']"]
    assert zpe[0]["result"].get("trade_readiness") == "HOLD"


def test_gate_module_does_not_import_aureon_packages() -> None:
    tree = ast.parse((ROOT / "mcp" / "aureon_public" / "queen_read_gate.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert imported
    assert all(not name.startswith("aureon.") for name in imported)
    assert all(name != "aureon" for name in imported)
