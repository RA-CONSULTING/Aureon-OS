"""phi_radar adopts and closes only allowlisted or Aureon-opened Capital deals."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


class _RecordingClose:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return {"success": True}


def _load_phi_radar():
    radar_dir = ROOT / "aureon_radar"
    if str(radar_dir) not in sys.path:
        sys.path.insert(0, str(radar_dir))
    name = "aureon_phi_radar_capital_ownership_test"
    existing = sys.modules.get(name)
    existing_file = getattr(existing, "__file__", None) if existing is not None else None
    if existing_file and Path(existing_file).resolve() == (radar_dir / "aureon_phi_radar.py").resolve():
        return existing
    spec = importlib.util.spec_from_file_location(name, radar_dir / "aureon_phi_radar.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _minimal_radar(phi):
    radar = phi.AureonPhiRadar.__new__(phi.AureonPhiRadar)
    radar._existing_positions_reconciled = False
    radar.live_positions = []
    radar.symbol_sectors = {"ETHUSD": "crypto", "CN50": "index"}
    radar.honey_ladder = SimpleNamespace(max_hold_seconds=60)
    radar._attach_dtp = lambda pot: None
    radar._save_state = lambda: None
    radar.router = SimpleNamespace()
    return radar


def _broker_pos(deal_id: str, symbol: str = "CN50", venue: str = "capital"):
    return {
        "deal_id": deal_id,
        "symbol": symbol,
        "direction": "LONG",
        "size": 0.087,
        "entry_price": 1.0,
        "venue": venue,
    }


def _pot(deal_id: str, symbol: str = "ETHUSD", venue: str = "capital"):
    return SimpleNamespace(
        deal_id=deal_id,
        symbol=symbol,
        direction="LONG",
        entry_price=1000.0,
        venue=venue,
        size=0.02,
    )


def _write_entry_record(path: Path, deal_id: str, stage: str = "CAPITAL_CONFIRMED"):
    path.write_text(
        json.dumps(
            {
                "stage": stage,
                "deal_id": deal_id,
                "symbol": "ETHUSD",
                "direction": "LONG",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_phi_radar_skips_non_adopted_broker_deals(monkeypatch, tmp_path):
    phi = _load_phi_radar()
    monkeypatch.setenv("AUREON_ORCA_CAPITAL_ADOPT_DEALS", "ADOPTED-1")
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", tmp_path / "trade_ledger.jsonl", raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)
    radar = _minimal_radar(phi)
    radar.router.get_open_positions = lambda: [
        _broker_pos("MANUAL-CN50", "CN50"),
        _broker_pos("ADOPTED-1", "US100"),
    ]
    radar._reconcile_existing_live_positions()
    assert [p.deal_id for p in radar.live_positions] == ["ADOPTED-1"]


def test_phi_radar_still_closes_its_own(monkeypatch, tmp_path):
    phi = _load_phi_radar()
    monkeypatch.setenv("AUREON_ORCA_CAPITAL_ADOPT_DEALS", "")
    ledger = tmp_path / "trade_ledger.jsonl"
    _write_entry_record(ledger, "AUREON-OWN-1")
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", ledger, raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)
    radar = _minimal_radar(phi)
    radar.router.close_position = _RecordingClose()
    own = _pot("AUREON-OWN-1")
    foreign = _pot("MANUAL-CN50", symbol="CN50")
    assert radar._close_live_position(own, 1010.0, "target_hit") is True
    assert radar.router.close_position.calls == [
        {
            "deal_id": "AUREON-OWN-1",
            "venue": "capital",
            "symbol": "ETHUSD",
            "size": 0.02,
            "direction": "LONG",
        }
    ]
    assert radar._close_live_position(foreign, 1.1, "target_hit") is False
    assert len(radar.router.close_position.calls) == 1


def test_phi_radar_fails_closed_on_ownership_error(monkeypatch, tmp_path):
    phi = _load_phi_radar()

    def boom(*_args, **_kwargs):
        raise RuntimeError("ownership source unavailable")

    import aureon.exchanges.orca_capital_ownership as ownership

    monkeypatch.setattr(ownership, "adopted_deal_ids", boom)
    ledger = tmp_path / "trade_ledger.jsonl"
    _write_entry_record(ledger, "ANY")
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", ledger, raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)
    if hasattr(phi, "_phi_capital_deal_owned"):
        assert phi._phi_capital_deal_owned("ANY", "capital") is False

    radar = _minimal_radar(phi)
    radar.router.get_open_positions = lambda: [_broker_pos("ANY", "ETHUSD")]
    radar.router.close_position = _RecordingClose()
    radar._reconcile_existing_live_positions()
    assert radar.live_positions == []
    assert radar._close_live_position(_pot("ANY"), 1010.0, "error-path") is False
    assert radar.router.close_position.calls == []


# ── Reconciliation must not launder a manual deal into ownership ──────────

GARY = "GARY_MANUAL_CN50"
SIZE = 0.087


def _cap_pos(deal_id: str, epic: str = "CN50", direction: str = "BUY", size: float = SIZE,
             deal_reference=None):
    position = {"dealId": deal_id, "direction": direction, "size": size}
    if deal_reference:
        position["dealReference"] = deal_reference
    return {"position": position, "market": {"epic": epic}}


class _FakeCapital:
    """Fake Capital client: serves the ledger, reconciliation, snapshot and confirm reads."""

    def __init__(self, positions, snapshot="live", confirms=None):
        self.positions = list(positions)
        self.snapshot = snapshot  # "live" | "none" | "raise"
        self.confirms = dict(confirms or {})

    def get_positions(self):
        return list(self.positions)

    def get_live_positions(self):
        return list(self.positions)

    def get_live_positions_snapshot(self):
        if self.snapshot == "raise":
            raise RuntimeError("positions read failed")
        if self.snapshot == "none":
            return None
        return list(self.positions)

    def get_live_deal_confirmation(self, ref):
        return self.confirms.get(ref)


def _ledger_setup(monkeypatch, tmp_path, adopt=""):
    phi = _load_phi_radar()
    import aureon_trade_ledger as tl

    path = tmp_path / "trade_ledger.jsonl"
    monkeypatch.setenv("AUREON_ORCA_CAPITAL_ADOPT_DEALS", adopt)
    monkeypatch.setattr(tl, "LEDGER_FILE", path)
    monkeypatch.setattr(tl.time, "sleep", lambda *_a: None)
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", path, raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)
    return phi, tl, path


def _confirmed_rows(path: Path, deal_id=None):
    if not path.is_file():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if r.get("stage") == "CAPITAL_CONFIRMED"
            and (deal_id is None or r.get("deal_id") == deal_id)]


def _cn50_shadow():
    return SimpleNamespace(symbol="CN50", direction="LONG")


def _setup_radar(phi, tl, cap):
    radar = _minimal_radar(phi)
    radar.capital_dual = cap
    return radar, tl.TradeLedger(cap)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("yes", False),
        (1, False),
        ("true", False),
        (1.0, False),
        ([1], False),
        (True, True),
    ],
)
def test_ledger_only_strict_true_is_recorded_as_reconciled(monkeypatch, tmp_path, value, expected):
    """Pin TradeLedger.capital_confirmed: only reconciled is True marks the row."""
    _phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    deal_id = "LEDGER-RECONCILED-PIN"
    ledger = tl.TradeLedger(_FakeCapital([_cap_pos(deal_id)]))
    ledger.capital_confirmed("AUD-T-RECONCILED", deal_id, {"reconciled": value})
    rows = _confirmed_rows(path, deal_id)
    assert len(rows) == 1
    assert rows[0]["reconciled"] is expected


def test_reconcile_does_not_adopt_manual_deal_open_before_order(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    # Even a confirmation that points at the pre-existing deal is refused.
    cap = _FakeCapital([_cap_pos(GARY)], confirms={"o_REF1": [GARY]})
    radar, ledger = _setup_radar(phi, tl, cap)
    snapshot = radar._capital_deal_id_snapshot()
    assert snapshot == frozenset({GARY})
    for ref in ("o_REF1", None):
        got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-1", SIZE, ledger,
                                             pre_order_deal_ids=snapshot, order_ref=ref)
        assert got is None
    assert _confirmed_rows(path, GARY) == []
    assert phi._phi_capital_deal_owned(GARY, "capital") is False


def test_reference_adopts_only_that_deal_even_with_another_new_same_size_deal(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([], confirms={"o_REF2": ["AUREON-NEW-1"]})
    radar, ledger = _setup_radar(phi, tl, cap)
    snapshot = radar._capital_deal_id_snapshot()
    assert snapshot == frozenset()
    # Gary opens the same CN50 BUY, same size, by hand after the snapshot;
    # his deal is listed first.
    cap.positions += [_cap_pos("GARY_NEW_CN50"), _cap_pos("AUREON-NEW-1")]
    got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-2", SIZE, ledger,
                                         pre_order_deal_ids=snapshot, order_ref="o_REF2")
    assert got == "AUREON-NEW-1"
    rows = _confirmed_rows(path)
    assert [r["deal_id"] for r in rows] == ["AUREON-NEW-1"]
    assert rows[0]["reconciled"] is True and rows[0]["pre_order_snapshot_excluded"] is True
    assert phi._phi_capital_deal_owned("AUREON-NEW-1", "capital") is True
    assert phi._phi_capital_deal_owned("GARY_NEW_CN50", "capital") is False


def test_reference_matches_position_deal_reference_without_confirm(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([])
    radar, ledger = _setup_radar(phi, tl, cap)
    snapshot = radar._capital_deal_id_snapshot()
    cap.positions += [_cap_pos("GARY_NEW_CN50"),
                      _cap_pos("AUREON-NEW-3", deal_reference="o_REF3")]
    got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-3", SIZE, ledger,
                                         pre_order_deal_ids=snapshot, order_ref="o_REF3")
    assert got == "AUREON-NEW-3"
    assert phi._phi_capital_deal_owned("GARY_NEW_CN50", "capital") is False


def test_no_reference_reconciles_nothing_even_for_single_same_size_new_deal(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([])
    radar, ledger = _setup_radar(phi, tl, cap)
    snapshot = radar._capital_deal_id_snapshot()
    cap.positions.append(_cap_pos("GARY_NEW_CN50"))  # opened by hand in the window
    for ref in (None, "", "unknown"):
        got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-4", SIZE, ledger,
                                             pre_order_deal_ids=snapshot, order_ref=ref)
        assert got is None
    assert _confirmed_rows(path) == []
    assert phi._phi_capital_deal_owned("GARY_NEW_CN50", "capital") is False


def test_referenced_deal_with_wrong_epic_size_or_direction_adopts_nothing(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cases = [
        _cap_pos("AUREON-X", epic="CN50X"),
        _cap_pos("AUREON-X", size=0.09),
        _cap_pos("AUREON-X", direction="SELL"),
        _cap_pos("AUREON-X", size="n/a"),
    ]
    for pos in cases:
        cap = _FakeCapital([], confirms={"o_REF5": ["AUREON-X"]})
        radar, ledger = _setup_radar(phi, tl, cap)
        snapshot = radar._capital_deal_id_snapshot()
        cap.positions.append(pos)
        got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-5", SIZE, ledger,
                                             pre_order_deal_ids=snapshot, order_ref="o_REF5")
        assert got is None, pos
    assert _confirmed_rows(path) == []


def test_two_referenced_new_deals_adopt_nothing(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([], confirms={"o_REF6": ["AUREON-A", "AUREON-B"]})
    radar, ledger = _setup_radar(phi, tl, cap)
    snapshot = radar._capital_deal_id_snapshot()
    cap.positions += [_cap_pos("AUREON-A"), _cap_pos("AUREON-B")]
    got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-6", SIZE, ledger,
                                         pre_order_deal_ids=snapshot, order_ref="o_REF6")
    assert got is None
    assert _confirmed_rows(path) == []


def test_zero_or_unknown_size_reconciles_nothing(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([], confirms={"o_REF7": ["AUREON-NEW-7"]})
    radar, ledger = _setup_radar(phi, tl, cap)
    snapshot = radar._capital_deal_id_snapshot()
    cap.positions.append(_cap_pos("AUREON-NEW-7"))
    for size in (0.0, None, float("nan"), -SIZE):
        got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-7", size, ledger,
                                             pre_order_deal_ids=snapshot, order_ref="o_REF7")
        assert got is None
    assert _confirmed_rows(path) == []


def test_snapshot_failure_reconciles_nothing(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    for mode in ("raise", "none"):
        cap = _FakeCapital([_cap_pos(GARY)], snapshot=mode, confirms={"o_REF8": ["AUREON-NEW-2"]})
        radar, ledger = _setup_radar(phi, tl, cap)
        snapshot = radar._capital_deal_id_snapshot()
        assert snapshot is None
        cap.positions.append(_cap_pos("AUREON-NEW-2"))
        got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-8", SIZE, ledger,
                                             pre_order_deal_ids=snapshot, order_ref="o_REF8")
        assert got is None
    # A client with no snapshot read at all is also "unknown", never "empty".
    radar = _minimal_radar(phi)
    radar.capital_dual = SimpleNamespace(get_live_positions=lambda: [])
    assert radar._capital_deal_id_snapshot() is None
    assert _confirmed_rows(path) == []
    assert phi._phi_capital_deal_owned("AUREON-NEW-2", "capital") is False


def test_guard_ignores_reconciled_rows_unless_allowlisted(monkeypatch, tmp_path):
    phi, _tl, path = _ledger_setup(monkeypatch, tmp_path, adopt="ALLOW-1")
    rows = [
        # What the old reconciliation path could leave for a manual deal.
        {"stage": "CAPITAL_CONFIRMED", "deal_id": GARY, "reconciled": True},
        {"stage": "CAPITAL_CONFIRMED", "deal_id": "ODD-1", "reconciled": "yes",
         "pre_order_snapshot_excluded": "yes"},
        {"stage": "CAPITAL_CONFIRMED", "deal_id": "ALLOW-1", "reconciled": True},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n{not json GARY\n",
                    encoding="utf-8")
    assert phi._phi_capital_deal_owned(GARY, "capital") is False
    assert phi._phi_capital_deal_owned("ODD-1", "capital") is False
    assert phi._phi_capital_deal_owned("ALLOW-1", "capital") is True


def _order_path_radar(phi, tl, cap, place_order):
    radar = _minimal_radar(phi)
    radar.capital_dual = SimpleNamespace(
        authenticated=True,
        get_live_positions=cap.get_live_positions,
        get_live_positions_snapshot=cap.get_live_positions_snapshot,
        get_live_deal_confirmation=cap.get_live_deal_confirmation,
    )
    radar.capital_live = SimpleNamespace(get_account_balance=lambda: 1000.0)
    radar._trade_ledger = tl.TradeLedger(cap)
    radar.price_stale_after_sec = 90
    radar.honey_ladder = SimpleNamespace(max_hold_seconds=60, source_records={}, honey_pot=None)
    radar._live_trading_gate_allowed = lambda *_a: True
    radar._daily_live_cap_reached = lambda: False
    radar._get_price = lambda *_a, **_k: 100.0
    radar._matrix_approves = lambda *_a: True
    radar._calculate_position_size = lambda **_k: SIZE
    radar._notional_cap_exceeded = lambda *_a: False
    radar._compute_stop_level = lambda *_a: 98.5
    radar._expectancy_gate_verdict = lambda *_a: {"allowed": True}
    radar._floor_clamp_tp = lambda _d, _p, t: t
    radar._log_order_failed = lambda *_a: None
    radar.adopted = []
    radar._adopt_honey_pot = lambda shadow, deal_id, size, venue="capital": radar.adopted.append(deal_id)
    radar.router = SimpleNamespace(
        aggregate_exposure=lambda: {"position_exposure": 0.0, "limit": 1.0, "utilization_pct": 0.0},
        place_order=place_order,
    )
    return radar


def _order_shadow():
    return SimpleNamespace(symbol="CN50", direction="LONG", status="HIT", ladder_rung=1,
                           source="test", entry_price=100.0, target_price=102.0,
                           _audit_id="AUD-T-9")


def test_order_path_timeout_does_not_adopt_manual_deal(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([_cap_pos(GARY)])

    def timeout(**_kw):
        cap.positions.append(_cap_pos("GARY_NEW_CN50"))  # opened by hand meanwhile
        raise TimeoutError("order call timed out")

    radar = _order_path_radar(phi, tl, cap, timeout)
    shadow = _order_shadow()
    radar._execute_honey_pot(shadow)
    assert radar.adopted == []
    assert shadow.status == "FAILED"
    assert _confirmed_rows(path) == []
    assert phi._phi_capital_deal_owned(GARY, "capital") is False
    assert phi._phi_capital_deal_owned("GARY_NEW_CN50", "capital") is False


def test_order_path_error_without_reference_adopts_nothing(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([])

    def error_no_ref(**_kw):
        cap.positions.append(_cap_pos("GARY_NEW_CN50"))
        return {"dealId": "unknown", "size": SIZE, "error": "timeout after send"}

    radar = _order_path_radar(phi, tl, cap, error_no_ref)
    radar._execute_honey_pot(_order_shadow())
    assert radar.adopted == []
    assert phi._phi_capital_deal_owned("GARY_NEW_CN50", "capital") is False


def test_order_path_reference_adopts_only_aureons_deal(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([_cap_pos(GARY)], confirms={"o_REF9": ["AUREON-NEW-9"]})

    def acknowledged(**_kw):
        # Capital's POST /positions only acknowledges with a dealReference
        # (o_REF9); the opened position's dealId (AUREON-NEW-9) differs and
        # is only known from /confirms. Gary opens a same-size CN50 BUY by
        # hand in the same window, listed first.
        cap.positions += [_cap_pos("GARY_NEW_CN50"),
                          _cap_pos("AUREON-NEW-9", deal_reference="p_AUREON-NEW-9")]
        return {"dealId": "o_REF9", "dealReference": "o_REF9", "account": "capital_live",
                "size": SIZE, "error": None, "venue": "capital"}

    radar = _order_path_radar(phi, tl, cap, acknowledged)
    radar._execute_honey_pot(_order_shadow())
    assert radar.adopted == ["AUREON-NEW-9"]
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    # The reference is never compared against position dealIds as if it were one.
    assert all(r.get("deal_id") != "o_REF9" for r in rows)
    assert [r["deal_id"] for r in _confirmed_rows(path)] == ["AUREON-NEW-9"]
    assert phi._phi_capital_deal_owned("AUREON-NEW-9", "capital") is True
    assert phi._phi_capital_deal_owned("GARY_NEW_CN50", "capital") is False
    assert phi._phi_capital_deal_owned(GARY, "capital") is False


def test_dual_snapshot_read_is_none_on_failure_not_empty():
    _load_phi_radar()
    import aureon_dual_capital as dual

    class _Resp:
        def __init__(self, code, body):
            self.status_code = code
            self._body = body

        def json(self):
            return self._body

    def conn(request):
        c = dual.DualCapitalConnector.__new__(dual.DualCapitalConnector)
        c.live = SimpleNamespace(_request=request)
        return c

    def boom(*_a, **_k):
        raise ConnectionError("down")

    assert conn(boom).get_live_positions_snapshot() is None
    assert conn(lambda *_a, **_k: _Resp(500, {})).get_live_positions_snapshot() is None
    assert conn(lambda *_a, **_k: _Resp(200, {})).get_live_positions_snapshot() is None
    assert conn(lambda *_a, **_k: _Resp(200, {"positions": []})).get_live_positions_snapshot() == []
    pos = [_cap_pos(GARY)]
    assert conn(lambda *_a, **_k: _Resp(200, {"positions": pos})).get_live_positions_snapshot() == pos


def test_dual_deal_confirmation_uses_confirm_order():
    _load_phi_radar()
    import aureon_dual_capital as dual

    def conn(confirm_order):
        c = dual.DualCapitalConnector.__new__(dual.DualCapitalConnector)
        c.live = SimpleNamespace(confirm_order=confirm_order)
        return c

    seen = []

    def ok(ref):
        seen.append(ref)
        return {"dealReference": "o_R", "dealStatus": "ACCEPTED", "dealId": "D-1",
                "affectedDeals": [{"dealId": "D-1", "status": "OPENED"},
                                  {"dealId": "D-0", "status": "CLOSED"}]}

    assert conn(ok).get_live_deal_confirmation("o_R") == ["D-1"]
    assert seen == ["o_R"]
    assert conn(ok).get_live_deal_confirmation("") is None
    assert conn(ok).get_live_deal_confirmation("o_OTHER") is None  # reference mismatch
    assert conn(lambda _r: {"error": "404"}).get_live_deal_confirmation("o_R") is None
    assert conn(lambda _r: {"dealReference": "o_R", "dealStatus": "REJECTED",
                            "affectedDeals": []}).get_live_deal_confirmation("o_R") == []
    assert conn(lambda _r: {"dealReference": "o_R", "dealStatus": "ACCEPTED",
                            "dealId": "D-2"}).get_live_deal_confirmation("o_R") == ["D-2"]

    def boom(_r):
        raise ConnectionError("down")

    assert conn(boom).get_live_deal_confirmation("o_R") is None


def test_capital_receipt_keeps_deal_reference_separate():
    _load_phi_radar()
    import aureon_dual_capital as dual
    import multi_exchange_router as mer

    class _Resp:
        status_code = 200

        def json(self):
            return {"dealReference": "o_A"}

    c = dual.DualCapitalConnector.__new__(dual.DualCapitalConnector)
    client = SimpleNamespace(demo_mode=False, _request=lambda *_a, **_k: _Resp())
    c._symbol_to_epic = lambda _client, sym: sym
    c._get_symbol_category = lambda _sym: "indices"
    c._get_dealing_rules = lambda _sym: {"minDealSize": 0.01}
    receipt = c._place_order(client, "CN50", "BUY", SIZE)
    assert receipt["dealReference"] == "o_A"
    assert receipt["dealId"] == "o_A"  # acceptance id, unchanged for callers

    router = mer.MultiExchangeRouter.__new__(mer.MultiExchangeRouter)
    router._capital_connector = lambda: SimpleNamespace(
        place_live_order=lambda **_k: {"dealId": "o_A", "dealReference": "o_A", "size": SIZE})
    routed = router._route_capital("CN50", "buy", SIZE, 98.5, 102.0)
    assert routed["dealReference"] == "o_A"


def test_live_log_reference_is_not_treated_as_a_deal_id(monkeypatch, tmp_path):
    phi, _tl, _path = _ledger_setup(monkeypatch, tmp_path)
    live = tmp_path / "live_trades.jsonl"
    live.write_text(json.dumps({"dealId": None, "dealReference": "o_X", "venue": "capital"}) + "\n"
                    + json.dumps({"dealId": "D-REAL", "dealReference": "o_Y"}) + "\n",
                    encoding="utf-8")
    assert phi._phi_capital_deal_owned("o_X", "capital") is False
    assert phi._phi_capital_deal_owned("o_Y", "capital") is False
    assert phi._phi_capital_deal_owned("D-REAL", "capital") is True


def test_order_path_confirm_pointing_at_preexisting_deal_adopts_nothing(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([_cap_pos(GARY)], confirms={"o_BAD": [GARY]})

    def acknowledged(**_kw):
        return {"dealId": "o_BAD", "dealReference": "o_BAD", "size": SIZE,
                "error": None, "venue": "capital"}

    radar = _order_path_radar(phi, tl, cap, acknowledged)
    radar._execute_honey_pot(_order_shadow())
    assert radar.adopted == []
    assert phi._phi_capital_deal_owned(GARY, "capital") is False


def test_exception_path_uses_reference_and_real_size(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([], confirms={"o_REF10": ["AUREON-NEW-10"]})

    def acknowledged(**_kw):
        cap.positions += [_cap_pos("GARY_NEW_CN50"), _cap_pos("AUREON-NEW-10")]
        return {"dealId": "o_REF10", "dealReference": "o_REF10", "size": SIZE,
                "error": None, "venue": "capital"}

    radar = _order_path_radar(phi, tl, cap, acknowledged)
    calls = []

    def adopt_fails_once(shadow, deal_id, size, venue="capital"):
        calls.append((deal_id, size))
        if len(calls) == 1:
            raise RuntimeError("adopt failed after the order")

    radar._adopt_honey_pot = adopt_fails_once
    radar._execute_honey_pot(_order_shadow())
    # The exception path re-reconciles with the order's reference and size.
    assert calls == [("AUREON-NEW-10", SIZE), ("AUREON-NEW-10", SIZE)]
    assert phi._phi_capital_deal_owned("GARY_NEW_CN50", "capital") is False


# ── Charlie's #383 HOLD: pin the writer and the confirm/snapshot edges ─────


def test_unknown_reference_reconciles_nothing_even_if_something_answers_to_it(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    # Worst case: a confirm and a new position both answer to "unknown".
    cap = _FakeCapital([], confirms={"unknown": ["NEW-U"], "UNKNOWN": ["NEW-U"]})
    radar, ledger = _setup_radar(phi, tl, cap)
    snapshot = radar._capital_deal_id_snapshot()
    cap.positions.append(_cap_pos("NEW-U", deal_reference="unknown"))
    for ref in ("unknown", "UNKNOWN", " Unknown "):
        got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-U", SIZE, ledger,
                                             pre_order_deal_ids=snapshot, order_ref=ref)
        assert got is None, ref
    assert _confirmed_rows(path) == []
    assert phi._phi_capital_deal_owned("NEW-U", "capital") is False


def test_snapshot_entry_without_deal_id_makes_snapshot_unknown(monkeypatch, tmp_path):
    phi, tl, _path = _ledger_setup(monkeypatch, tmp_path)
    blank = {"position": {"direction": "BUY", "size": SIZE}, "market": {"epic": "CN50"}}
    for bad in (blank, _cap_pos(""), {"market": {"epic": "CN50"}}, "not-a-dict"):
        cap = _FakeCapital([_cap_pos(GARY), bad])
        radar, _ledger = _setup_radar(phi, tl, cap)
        # An unreadable entry could be Gary's deal; never treat it as absent.
        assert radar._capital_deal_id_snapshot() is None, bad


def test_dual_deal_confirmation_rejected_with_deal_id_opens_nothing():
    _load_phi_radar()
    import aureon_dual_capital as dual

    c = dual.DualCapitalConnector.__new__(dual.DualCapitalConnector)
    for status in ("REJECTED", "rejected", "", None):
        reply = {"dealReference": "o_R", "dealStatus": status, "dealId": "D-REJ",
                 "affectedDeals": []}
        c.live = SimpleNamespace(confirm_order=lambda _r, reply=reply: reply)
        assert c.get_live_deal_confirmation("o_R") == [], status


def _scan_radar(phi, tmp_path, place_order):
    radar = _minimal_radar(phi)
    radar.state = phi.SystemState.ARMED
    radar.symbol_keys = ["CN50"]
    radar.live_trades_today = 0
    radar.price_history = {}
    radar.current_play_plan = None
    shadows = []
    radar.honey_ladder = SimpleNamespace(
        max_hold_seconds=60, shadow_runs=shadows, honey_pot=None,
        get_sector_heat=lambda: {}, update_shadow=lambda *_a: None,
        add_shadow=lambda **kw: shadows.append(SimpleNamespace(**kw)))
    radar.scanner = SimpleNamespace(
        feed_price=lambda *_a: None, calculate_volatility=lambda _s: 0.01,
        money_flow_score=lambda _s: 0.5, detect_breakout=lambda _s: (True, "LONG", 0.9))
    radar.play_board = SimpleNamespace(build_plan=lambda *_a, **_k: None)
    radar.capital_dual = SimpleNamespace(calculate_micro_tp=lambda **_k: 102.0,
                                         get_live_balance=lambda: 0.0)
    radar.capital_live = SimpleNamespace()
    for name in ("_reconcile_existing_live_positions", "_reconcile_persisted_honey_pot",
                 "_check_honey_pot", "_check_demo_shadows", "_try_auto_arm",
                 "_promote_to_honey_pot"):
        setattr(radar, name, lambda: None)
    radar._read_fused_signals = lambda: {}
    radar._get_price = lambda *_a, **_k: 100.0
    radar._generate_signal = lambda *_a, **_k: None
    radar._probability_threshold = lambda: 0.0
    radar._compute_stop_level = lambda *_a: 98.5
    radar._compute_live_size = lambda *_a: SIZE
    radar._expectancy_gate_verdict = lambda *_a: {"allowed": True}
    radar._floor_clamp_tp = lambda _d, _p, t: t
    radar._max_hold_seconds = lambda _s: 60
    radar.router = SimpleNamespace(
        aggregate_exposure=lambda: {"position_exposure": 0.0, "limit": 1.0, "utilization_pct": 0.0},
        place_order=place_order)
    return radar


def test_scan_live_log_writes_reference_only_ack_without_deal_id(monkeypatch, tmp_path):
    """The main LIVE loop's live_trades.jsonl writer, not just the reader."""
    phi, _tl, _path = _ledger_setup(monkeypatch, tmp_path)
    import aureon_dual_capital as dual
    import multi_exchange_router as mer

    # Capital's POST /positions answers with only a dealReference.
    class _Resp:
        status_code = 200

        def json(self):
            return {"dealReference": "o_LIVE1"}

    conn = dual.DualCapitalConnector.__new__(dual.DualCapitalConnector)
    conn._symbol_to_epic = lambda _client, sym: sym
    conn._get_symbol_category = lambda _sym: "indices"
    conn._get_dealing_rules = lambda _sym: {"minDealSize": 0.01}
    client = SimpleNamespace(demo_mode=False, _request=lambda *_a, **_k: _Resp())
    router = mer.MultiExchangeRouter.__new__(mer.MultiExchangeRouter)
    router._capital_connector = lambda: SimpleNamespace(
        place_live_order=lambda **_k: conn._place_order(client, "CN50", "BUY", SIZE))
    sent = []

    def place_order(**kw):
        sent.append(kw)
        routed = router._route_capital(kw["symbol"], kw["direction"], kw["size"],
                                       kw["stop_level"], kw["profit_level"])
        return {**routed, "venue": "capital"}

    intel = SimpleNamespace(adjusted_probability=0.9, action="TRADE", risk_flags=[])
    pm = SimpleNamespace(evaluate_signal=lambda **_k: intel, should_trade=lambda *_a, **_k: True,
                         get_matrix=lambda: SimpleNamespace(explain=lambda *_a: ""))
    monkeypatch.setitem(sys.modules, "radar_probability_matrix", pm)
    monkeypatch.setitem(sys.modules, "aureon_capital_momentum_bridge", None)
    monkeypatch.setenv("HOMING_ENABLED", "0")
    monkeypatch.setenv("LIVE", "1")
    live = tmp_path / "live_trades.jsonl"
    monkeypatch.setattr(phi, "LIVE_LOG", live)

    radar = _scan_radar(phi, tmp_path, place_order)
    radar.scan()
    assert len(sent) == 1
    rows = [json.loads(line) for line in live.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["dealId"] is None
    assert rows[0]["dealReference"] == "o_LIVE1"
    # So the reader never treats the acknowledgement reference as an owned deal.
    assert phi._phi_capital_deal_owned("o_LIVE1", "capital") is False


# ── panic() closes only an owned Capital deal, through the router ─────────

class _PanicRouter:
    def __init__(self):
        self.calls = []

    def close_position(self, **kwargs):
        self.calls.append(kwargs)
        return {"success": True}


class _PanicDual:
    def __init__(self, positions):
        self.positions = positions
        self.closed = []

    def get_live_positions(self):
        return list(self.positions)

    def close_live_position(self, deal_id):
        self.closed.append(deal_id)
        return {"success": True}


def _panic_radar(phi, positions):
    radar = phi.AureonPhiRadar.__new__(phi.AureonPhiRadar)
    radar._save_state = lambda: None
    radar.capital_dual = _PanicDual(positions)
    radar.router = _PanicRouter()
    return radar


def _live_pos(deal_id, epic="CN50"):
    return {
        "market": {"epic": epic},
        "position": {"dealId": deal_id, "direction": "BUY", "size": 0.087},
    }


def test_panic_skips_gary_manual_cn50(monkeypatch, tmp_path):
    phi = _load_phi_radar()
    monkeypatch.delenv("AUREON_ORCA_CAPITAL_ADOPT_DEALS", raising=False)
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", tmp_path / "trade_ledger.jsonl", raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)
    radar = _panic_radar(phi, [_live_pos("GARY_MANUAL_CN50"), {"position": {}}])
    radar.panic()
    assert radar.router.calls == []
    assert radar.capital_dual.closed == []
    assert radar.state == phi.SystemState.PANIC


def test_panic_ownership_error_closes_nothing(monkeypatch, tmp_path):
    phi = _load_phi_radar()
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", tmp_path / "trade_ledger.jsonl", raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)

    def boom(*_args, **_kwargs):
        raise RuntimeError("ownership source unavailable")

    monkeypatch.setattr(phi, "_phi_capital_deal_owned", boom)
    radar = _panic_radar(phi, [_live_pos("AUREON-OWN-1", "ETHUSD"), _live_pos("GARY_MANUAL_CN50")])
    radar.panic()
    assert radar.router.calls == []
    assert radar.capital_dual.closed == []


def test_panic_closes_owned_deal_through_router(monkeypatch, tmp_path):
    phi = _load_phi_radar()
    monkeypatch.delenv("AUREON_ORCA_CAPITAL_ADOPT_DEALS", raising=False)
    ledger = tmp_path / "trade_ledger.jsonl"
    _write_entry_record(ledger, "AUREON-OWN-1")
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", ledger, raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)
    radar = _panic_radar(
        phi,
        [_live_pos("GARY_MANUAL_CN50"), _live_pos("AUREON-OWN-1", "ETHUSD"), {"not": "a position"}],
    )
    radar.panic()
    assert radar.capital_dual.closed == []
    assert [call["deal_id"] for call in radar.router.calls] == ["AUREON-OWN-1"]
    assert radar.router.calls[0]["venue"] == "capital"
    assert radar.router.calls[0]["symbol"] == "ETHUSD"


def test_panic_closes_every_owned_deal(monkeypatch, tmp_path):
    """Several Aureon deals are all closed. A manual deal in the middle is not."""
    phi = _load_phi_radar()
    monkeypatch.delenv("AUREON_ORCA_CAPITAL_ADOPT_DEALS", raising=False)
    ledger = tmp_path / "trade_ledger.jsonl"
    ledger.write_text(
        "".join(
            json.dumps({"stage": "CAPITAL_CONFIRMED", "deal_id": deal, "symbol": "ETHUSD", "direction": "LONG"}) + "\n"
            for deal in ("AUREON-OWN-1", "AUREON-OWN-2", "AUREON-OWN-3")
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(phi, "_PHI_ENTRY_LEDGER", ledger, raising=False)
    monkeypatch.setattr(phi, "LIVE_LOG", tmp_path / "live_trades.jsonl", raising=False)
    radar = _panic_radar(
        phi,
        [
            _live_pos("AUREON-OWN-1", "ETHUSD"),
            _live_pos("GARY_MANUAL_CN50"),
            _live_pos("AUREON-OWN-2", "US100"),
            {"position": {}},
            _live_pos("AUREON-OWN-3", "GOLD"),
        ],
    )
    radar.panic()
    assert radar.capital_dual.closed == []
    assert [call["deal_id"] for call in radar.router.calls] == [
        "AUREON-OWN-1",
        "AUREON-OWN-2",
        "AUREON-OWN-3",
    ]
    assert [call["symbol"] for call in radar.router.calls] == ["ETHUSD", "US100", "GOLD"]


def test_panic_source_checks_ownership_before_router_close():
    """Removing the ownership call, or closing before it, fails this assert."""
    import ast

    path = ROOT / "aureon_radar" / "aureon_phi_radar.py"
    tree = ast.parse(path.read_bytes().decode("utf-8"))
    panic = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "panic"
    )
    calls = [
        node for node in ast.walk(panic)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    owned_lines = [
        node.lineno for node in ast.walk(panic)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "_phi_capital_deal_owned"
    ]
    close_lines = [node.lineno for node in calls if node.func.attr == "close_position"]
    direct = [node.lineno for node in calls if node.func.attr == "close_live_position"]
    returns_in_except = [
        child for node in ast.walk(panic)
        if isinstance(node, ast.ExceptHandler)
        for child in ast.walk(node)
        if isinstance(child, ast.Return)
    ]
    assert owned_lines, "panic() no longer asks _phi_capital_deal_owned"
    assert close_lines, "panic() no longer closes through the router"
    assert min(owned_lines) < min(close_lines)
    assert direct == []
    assert returns_in_except, "an ownership error no longer stops the close"
