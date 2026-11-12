"""Follow-up to the CN50 guard (#284): every ORCA path that reads Capital
positions filters them through split_owned_positions, and the live kill chain
re-checks the adopted list at the moment of closing."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FILTERED = {
    "aureon_radar/bots/orca_complete_kill_cycle.py": 4,
    "aureon/bots/orca_complete_kill_cycle.py": 4,
    "aureon/bots/orca_unified_kill_chain.py": 1,
    "aureon_radar/bots/orca_unified_kill_chain.py": 1,
}
RAW_READ = re.compile(r"=\s*(?:self\.)?capital(?:_client)?\.get_positions\(\)")


def _text(rel):
    return (REPO / rel).read_bytes().decode("utf-8", errors="replace")


def test_no_unfiltered_capital_position_reads_remain():
    for rel, expected in FILTERED.items():
        text = _text(rel)
        assert not RAW_READ.search(text), rel
        assert text.count("split_owned_positions(") >= expected, rel


def test_live_kill_chain_rechecks_adoption_before_closing():
    text = _text("aureon_radar/bots/orca_unified_kill_chain.py")
    branch = text.index("if exchange == 'capital':")
    lock = text.index("not in adopted_deal_ids()", branch)
    close = text.index("client.close_position(target['id'])", branch)
    assert branch < lock < close


def test_close_lock_refuses_unadopted_deal(monkeypatch):
    from aureon.exchanges.orca_capital_ownership import adopted_deal_ids, ADOPT_ENV
    monkeypatch.delenv(ADOPT_ENV, raising=False)
    assert "CN50-MANUAL" not in adopted_deal_ids()
    monkeypatch.setenv(ADOPT_ENV, "ORCA-1")
    assert "ORCA-1" in adopted_deal_ids() and "CN50-MANUAL" not in adopted_deal_ids()


def test_line_endings_preserved():
    assert b"\r\n" in (REPO / "aureon_radar/bots/orca_complete_kill_cycle.py").read_bytes()
    assert b"\r\n" not in (REPO / "aureon/bots/orca_complete_kill_cycle.py").read_bytes()
