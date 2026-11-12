"""ORCA must not adopt or close Capital positions it did not open (CN50 guard)."""

from aureon.exchanges.orca_capital_ownership import (
    ADOPT_ENV,
    adopted_deal_ids,
    split_owned_positions,
)

# Shaped like Capital's /positions reply for Gary's manual CN50 buy.
CN50_MANUAL = {
    "market": {"epic": "CN50", "bid": 1.0},
    "position": {"dealId": "MANUAL-CN50", "dealReference": "REF-CN50", "size": 0.087, "direction": "BUY", "level": 1.0, "upl": 0.0},
}
ADOPTED = {
    "market": {"epic": "US100"},
    "position": {"dealId": "ORCA-1", "size": 0.1, "direction": "SELL", "upl": 2.0},
}


def test_empty_allowlist_adopts_nothing():
    owned, skipped = split_owned_positions([CN50_MANUAL, ADOPTED], env={})
    assert owned == []
    assert skipped == [CN50_MANUAL, ADOPTED]


def test_only_listed_deals_are_owned():
    env = {ADOPT_ENV: " ORCA-1 , "}
    owned, skipped = split_owned_positions([CN50_MANUAL, ADOPTED], env=env)
    assert owned == [ADOPTED]
    assert skipped == [CN50_MANUAL]


def test_deal_reference_also_matches_and_missing_ids_are_skipped():
    owned, _ = split_owned_positions([CN50_MANUAL], env={ADOPT_ENV: "REF-CN50"})
    assert owned == [CN50_MANUAL]
    no_id = {"market": {"epic": "X"}, "position": {"size": 1}}
    owned, skipped = split_owned_positions([no_id], env={ADOPT_ENV: "ORCA-1"})
    assert owned == [] and skipped == [no_id]


def test_adopted_ids_parsing():
    assert adopted_deal_ids({}) == set()
    assert adopted_deal_ids({ADOPT_ENV: "a,,b , "}) == {"a", "b"}


def test_live_monitor_refuses_to_close_unadopted_capital_deal(monkeypatch):
    import importlib.util
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "aureon_radar" / "bots" / "orca_live_monitor.py").read_text(encoding="utf-8")
    assert "split_owned_positions(capital.get_positions())" in src
    assert "not closing a position ORCA did not open" in src
    kc = (Path(__file__).resolve().parents[1] / "aureon_radar" / "bots" / "orca_unified_kill_chain.py").read_text(encoding="utf-8")
    assert "split_owned_positions(self.capital.get_positions())" in kc
