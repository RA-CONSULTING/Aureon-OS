"""phi_radar adopts and closes only allowlisted or Aureon-opened Capital deals."""

from __future__ import annotations

import importlib.util
import json
import sys
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


def _cap_pos(deal_id: str, epic: str = "CN50", direction: str = "BUY"):
    return {"position": {"dealId": deal_id, "direction": direction}, "market": {"epic": epic}}


class _FakeCapital:
    """Fake Capital client: serves the ledger, reconciliation and snapshot reads."""

    def __init__(self, positions, snapshot="live"):
        self.positions = list(positions)
        self.snapshot = snapshot  # "live" | "none" | "raise"

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


def _confirmed_rows(path: Path, deal_id: str):
    if not path.is_file():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if r.get("stage") == "CAPITAL_CONFIRMED" and r.get("deal_id") == deal_id]


def _cn50_shadow():
    return SimpleNamespace(symbol="CN50", direction="LONG")


def test_reconcile_does_not_adopt_manual_deal_open_before_order(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([_cap_pos(GARY)])
    radar = _minimal_radar(phi)
    radar.capital_dual = cap
    ledger = tl.TradeLedger(cap)
    snapshot = radar._capital_deal_id_snapshot()
    assert snapshot == frozenset({GARY})
    got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-1", 0.087, ledger,
                                         pre_order_deal_ids=snapshot)
    assert got is None
    assert _confirmed_rows(path, GARY) == []
    assert phi._phi_capital_deal_owned(GARY, "capital") is False


def test_reconcile_adopts_genuinely_new_deal(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([_cap_pos(GARY)])
    radar = _minimal_radar(phi)
    radar.capital_dual = cap
    ledger = tl.TradeLedger(cap)
    snapshot = radar._capital_deal_id_snapshot()
    cap.positions.append(_cap_pos("AUREON-NEW-1"))  # created by Aureon's order
    got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-2", 0.087, ledger,
                                         pre_order_deal_ids=snapshot)
    assert got == "AUREON-NEW-1"
    rows = _confirmed_rows(path, "AUREON-NEW-1")
    assert len(rows) == 1
    assert rows[0]["reconciled"] is True and rows[0]["pre_order_snapshot_excluded"] is True
    assert phi._phi_capital_deal_owned("AUREON-NEW-1", "capital") is True
    assert phi._phi_capital_deal_owned(GARY, "capital") is False


def test_snapshot_failure_reconciles_nothing(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    for mode in ("raise", "none"):
        cap = _FakeCapital([_cap_pos(GARY)], snapshot=mode)
        radar = _minimal_radar(phi)
        radar.capital_dual = cap
        snapshot = radar._capital_deal_id_snapshot()
        assert snapshot is None
        cap.positions.append(_cap_pos("AUREON-NEW-2"))
        got = radar._reconcile_live_position(_cn50_shadow(), "AUD-T-3", 0.087,
                                             tl.TradeLedger(cap), pre_order_deal_ids=snapshot)
        assert got is None
    # A client with no snapshot read at all is also "unknown", never "empty".
    radar = _minimal_radar(phi)
    radar.capital_dual = SimpleNamespace(get_live_positions=lambda: [])
    assert radar._capital_deal_id_snapshot() is None
    assert path.read_text(encoding="utf-8").count("CAPITAL_CONFIRMED") == 0
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
    )
    radar.capital_live = SimpleNamespace(get_account_balance=lambda: 1000.0)
    radar._trade_ledger = tl.TradeLedger(cap)
    radar.price_stale_after_sec = 90
    radar.honey_ladder = SimpleNamespace(max_hold_seconds=60, source_records={}, honey_pot=None)
    radar._live_trading_gate_allowed = lambda *_a: True
    radar._daily_live_cap_reached = lambda: False
    radar._get_price = lambda *_a, **_k: 100.0
    radar._matrix_approves = lambda *_a: True
    radar._calculate_position_size = lambda **_k: 0.087
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
        raise TimeoutError("order call timed out")

    radar = _order_path_radar(phi, tl, cap, timeout)
    shadow = _order_shadow()
    radar._execute_honey_pot(shadow)
    assert radar.adopted == []
    assert shadow.status == "FAILED"
    assert _confirmed_rows(path, GARY) == []
    assert phi._phi_capital_deal_owned(GARY, "capital") is False


def test_order_path_timeout_adopts_deal_the_order_created(monkeypatch, tmp_path):
    phi, tl, path = _ledger_setup(monkeypatch, tmp_path)
    cap = _FakeCapital([_cap_pos(GARY)])

    def executed_then_timeout(**_kw):
        cap.positions.append(_cap_pos("AUREON-NEW-9"))
        return {"error": "timeout after execute"}

    radar = _order_path_radar(phi, tl, cap, executed_then_timeout)
    radar._execute_honey_pot(_order_shadow())
    assert radar.adopted == ["AUREON-NEW-9"]
    assert phi._phi_capital_deal_owned("AUREON-NEW-9", "capital") is True
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
