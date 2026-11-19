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
