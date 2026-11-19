"""phi_radar adopts and closes only allowlisted or Aureon-opened Capital deals."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

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


# ── Main live loop ("[LIVE] Routing order") must confirm the reference ──

LIVE_REF = "o_REF_LIVE"
LIVE_DEAL = "AUREON-LIVE-1"


def _live_ack(**overrides):
    receipt = {
        "dealId": LIVE_REF,
        "dealReference": LIVE_REF,
        "account": "capital_live",
        "size": SIZE,
        "error": None,
        "venue": "capital",
    }
    receipt.update(overrides)
    return receipt


def _run_live_loop(monkeypatch, tmp_path, ack, confirms, *, append_deal=None, confirm_raises=False):
    phi, _tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([_cap_pos(GARY)], confirms=confirms if isinstance(confirms, dict) else {})
    if confirm_raises:
        def _boom(_ref):
            raise ConnectionError("confirm down")
        cap.get_live_deal_confirmation = _boom
    seen = []
    if not confirm_raises:
        _orig = cap.get_live_deal_confirmation

        def _watch(ref):
            seen.append(ref)
            return _orig(ref)

        cap.get_live_deal_confirmation = _watch
    placed = []

    def place_order(**kwargs):
        placed.append(kwargs)
        if append_deal:
            cap.positions.append(_cap_pos(append_deal))
        return ack

    radar = _minimal_radar(phi)
    radar.capital_dual = cap
    radar.capital_live = cap
    cap.calculate_micro_tp = lambda **_k: 101.0
    cap.get_live_balance = lambda: 0
    radar.state = phi.SystemState.ARMED
    radar.symbol_keys = ["CN50"]
    radar.price_history = {}
    radar.live_trades_today = 0
    radar._honey_pot_reconciled = True
    radar._existing_positions_reconciled = True
    radar._check_demo_shadows = lambda: None
    radar._read_fused_signals = lambda: {}
    radar._get_price = lambda *_a, **_k: 100.0
    radar._compute_stop_level = lambda *_a: 98.5
    radar._compute_live_size = lambda *_a, **_k: SIZE
    radar._expectancy_gate_verdict = lambda *_a: {"allowed": True}
    radar._floor_clamp_tp = lambda _d, _p, target: target
    radar.scanner = SimpleNamespace(
        feed_price=lambda *_a, **_k: None,
        calculate_volatility=lambda *_a: 0.01,
        money_flow_score=lambda *_a: 0.5,
        detect_breakout=lambda *_a: (True, "LONG", 0.9),
    )
    radar.play_board = SimpleNamespace(build_plan=lambda *_a, **_k: {"execution": {}})
    import honey_ladder
    radar.honey_ladder = honey_ladder.HoneyLadder()
    radar.router = SimpleNamespace(
        aggregate_exposure=lambda: {"position_exposure": 0.0, "limit": 1.0, "utilization_pct": 0.0},
        place_order=place_order,
        close_position=_RecordingClose(),
        get_open_positions=lambda: [],
    )
    _install_scan_stubs(monkeypatch, radar)
    radar.scan()
    return phi, radar, path, placed, seen


def _install_scan_stubs(monkeypatch, radar):
    import radar_probability_matrix as rpm

    intel = SimpleNamespace(adjusted_probability=0.8, action="APPROVE", risk_flags=[])
    monkeypatch.setattr(rpm, "evaluate_signal", lambda **_k: intel)
    monkeypatch.setattr(rpm, "should_trade", lambda *_a, **_k: True)
    monkeypatch.setattr(rpm, "get_matrix", lambda: SimpleNamespace(explain=lambda *_a, **_k: "ok"))
    bridge = types.ModuleType("aureon_capital_momentum_bridge")

    class _QuietScanner:
        def __init__(self, *_a, **_k):
            pass

        def feed_prices_from_capital(self, *_a, **_k):
            return None

        def scan_all(self):
            return []

        def write_signals(self, *_a, **_k):
            return None

    bridge.CapitalMomentumScanner = _QuietScanner
    monkeypatch.setitem(sys.modules, "aureon_capital_momentum_bridge", bridge)
    monkeypatch.setenv("LIVE", "1")
    monkeypatch.setenv("HOMING_ENABLED", "0")


def _assert_live_loop_unmanaged(phi, radar, path, *deal_ids):
    assert radar.live_positions == []
    assert _confirmed_rows(path) == []
    for deal_id in deal_ids:
        assert phi._phi_capital_deal_owned(deal_id, "capital") is False


def test_live_loop_opened_confirm_stores_real_deal_and_guard_closes(monkeypatch, tmp_path):
    phi, radar, path, placed, seen = _run_live_loop(
        monkeypatch, tmp_path, _live_ack(), {LIVE_REF: [LIVE_DEAL]}, append_deal=LIVE_DEAL)
    assert placed, "live loop did not route an order"
    assert len(radar.live_positions) == 1
    pot = radar.live_positions[0]
    assert pot.deal_id == LIVE_DEAL
    assert getattr(pot, "deal_reference", None) == LIVE_REF
    assert seen == [LIVE_REF]
    rows = _confirmed_rows(path, LIVE_DEAL)
    assert len(rows) == 1
    assert rows[0]["capital_confirmed"] is True
    assert phi._phi_capital_deal_owned(LIVE_DEAL, "capital") is True
    assert phi._phi_capital_deal_owned(GARY, "capital") is False
    assert phi._phi_capital_deal_owned(LIVE_REF, "capital") is False
    assert radar._close_live_position(pot, 101.0, "target_hit") is True
    assert radar.router.close_position.calls == [{
        "deal_id": LIVE_DEAL,
        "venue": "capital",
        "symbol": "CN50",
        "size": SIZE,
        "direction": "LONG",
    }]
    # Placement itself is unchanged: the broker still receives a stop and a limit.
    assert placed[0]["stop_level"] == 98.5
    assert placed[0]["profit_level"] == 101.0


def test_live_loop_rejected_confirm_stores_no_deal(monkeypatch, tmp_path, caplog):
    caplog.set_level("ERROR")
    phi, radar, path, _placed, _seen = _run_live_loop(
        monkeypatch, tmp_path, _live_ack(), {LIVE_REF: []})
    _assert_live_loop_unmanaged(phi, radar, path, LIVE_REF, LIVE_DEAL, GARY)
    assert "unconfirmed" in caplog.text.lower()


def test_live_loop_confirm_error_stores_no_deal(monkeypatch, tmp_path, caplog):
    caplog.set_level("ERROR")
    phi, radar, path, _placed, _seen = _run_live_loop(
        monkeypatch, tmp_path, _live_ack(), {}, confirm_raises=True)
    _assert_live_loop_unmanaged(phi, radar, path, LIVE_REF, GARY)
    assert "unconfirmed" in caplog.text.lower() or "confirm failed" in caplog.text.lower()


def test_live_loop_missing_confirm_stores_no_deal(monkeypatch, tmp_path, caplog):
    caplog.set_level("ERROR")
    phi, radar, path, _placed, _seen = _run_live_loop(
        monkeypatch, tmp_path, _live_ack(), {LIVE_REF: None})
    _assert_live_loop_unmanaged(phi, radar, path, LIVE_REF, GARY)


def test_live_loop_no_reference_stores_no_deal(monkeypatch, tmp_path, caplog):
    caplog.set_level("ERROR")
    phi, radar, path, _placed, seen = _run_live_loop(
        monkeypatch, tmp_path, _live_ack(dealId="o_NOREF", dealReference=None), {})
    _assert_live_loop_unmanaged(phi, radar, path, "o_NOREF", LIVE_REF, GARY)
    assert seen == []


def test_live_loop_two_opened_deals_store_neither_and_not_gary(monkeypatch, tmp_path, caplog):
    caplog.set_level("ERROR")
    phi, radar, path, _placed, _seen = _run_live_loop(
        monkeypatch, tmp_path, _live_ack(), {LIVE_REF: [GARY, LIVE_DEAL]}, append_deal=LIVE_DEAL)
    _assert_live_loop_unmanaged(phi, radar, path, GARY, LIVE_DEAL, LIVE_REF)
    assert "unconfirmed" in caplog.text.lower()


def test_live_loop_non_capital_keeps_its_deal_id(monkeypatch, tmp_path):
    ack = _live_ack(dealId="ALPACA-1", dealReference=None, venue="alpaca", account="alpaca_live")
    phi, radar, _path, placed, seen = _run_live_loop(monkeypatch, tmp_path, ack, {})
    assert placed
    assert seen == []
    assert len(radar.live_positions) == 1
    assert radar.live_positions[0].deal_id == "ALPACA-1"
    assert phi._phi_capital_deal_owned("ALPACA-1", "alpaca") is True


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


def test_capital_connector_place_order_keeps_reference_and_opened_deal_id():
    """CapitalConnector.place_order must not copy dealReference into dealId."""
    phi = _load_phi_radar()
    connector = phi.CapitalConnector.__new__(phi.CapitalConnector)
    seen = []

    def place_market_order(**_k):
        return {"dealReference": "o_CONN"}

    def confirm_order(ref):
        seen.append(ref)
        return {
            "dealReference": ref,
            "dealStatus": "ACCEPTED",
            "affectedDeals": [
                {"dealId": "D-OPEN", "status": "OPENED"},
                {"dealId": "D-OLD", "status": "CLOSED"},
            ],
        }

    connector.client = SimpleNamespace(
        place_market_order=place_market_order,
        confirm_order=confirm_order,
    )
    receipt = connector.place_order("CN50", "BUY", SIZE)
    assert seen == ["o_CONN"]
    assert receipt["dealReference"] == "o_CONN"
    assert receipt["dealId"] == "D-OPEN"
    assert receipt["status"] == "submitted"

    def rejected(_ref):
        return {"dealReference": "o_CONN", "dealStatus": "REJECTED",
                "dealId": "D-REJ", "affectedDeals": []}

    connector.client.confirm_order = rejected
    refused = connector.place_order("CN50", "LONG", SIZE)
    assert refused["dealReference"] == "o_CONN"
    assert refused["dealId"] is None

    def missing(_ref):
        return {"error": "404"}

    connector.client.confirm_order = missing
    absent = connector.place_order("CN50", "SHORT", SIZE)
    assert absent["dealReference"] == "o_CONN"
    assert absent["dealId"] is None
