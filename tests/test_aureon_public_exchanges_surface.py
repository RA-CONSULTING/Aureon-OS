"""Stage 8 exchanges surface: HOLD gate, no exchange import, no key echo."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    body = json.loads(text)
    assert isinstance(body, dict)
    return body


def test_gate_stays_hold_when_live_orders_are_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.exchanges_surface import exchanges_gate
    from aureon_public.guard_loader import PINNED_COMMIT

    monkeypatch.setenv("AUREON_DISABLE_REAL_ORDERS", "0")
    monkeypatch.setenv("AUREON_LIVE_TRADING", "1")
    monkeypatch.setenv("KRAKEN_API_SECRET", "planted-exchanges-surface-kraken-secret")
    body = _load(exchanges_gate())
    assert body["decision"] == "HOLD"
    assert body["execute"] == "refused"
    assert body["live_orders"] == "refused"
    assert body["read_gated"] is True
    assert body["real_orders_default"] == "off"
    assert body["explicit_live_request_ignored"] is True
    assert body["env_selects_execute"] is False
    assert body["called"] is False
    assert body["imported"] is False
    assert body["open_plan_through"] == 2
    assert body["enabled_through"] == 6
    assert body["pin"] == PINNED_COMMIT
    assert "planted-exchanges-surface-kraken-secret" not in json.dumps(body)


def test_unset_disable_flag_is_still_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.exchanges_surface import gate_view

    monkeypatch.delenv("AUREON_DISABLE_REAL_ORDERS", raising=False)
    monkeypatch.delenv("AUREON_LIVE_TRADING", raising=False)
    body = gate_view()
    assert body["decision"] == "HOLD"
    assert body["live_orders"] == "refused"
    assert body["real_orders_default"] == "off"
    assert body["explicit_live_request_ignored"] is False
    assert body["env_selects_execute"] is False


def test_catalog_is_read_only_and_does_not_import_exchanges(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.body import body_call
    from aureon_public.exchanges_surface import exchanges_surface
    from aureon_public.layers import source_names

    secret = "planted-exchanges-surface-kraken-key"
    monkeypatch.setenv("KRAKEN_API_KEY", secret)

    class _Socket(socket.socket):
        def connect(self, address: object, *args: object, **kwargs: object) -> None:
            raise AssertionError(f"socket connect {address}")

        def connect_ex(self, address: object, *args: object, **kwargs: object) -> int:
            raise AssertionError(f"socket connect_ex {address}")

    def _refuse_connection(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("create_connection")

    monkeypatch.setattr(socket, "socket", _Socket)
    monkeypatch.setattr(socket, "create_connection", _refuse_connection)
    before = {name for name in sys.modules if name == "aureon.exchanges" or name.startswith("aureon.exchanges.")}
    catalog = _load(exchanges_surface())
    refused = _load(body_call("exchanges/kraken_client.py", "KrakenClient.get_order_status"))
    names = _load(source_names("exchanges"))
    after = {name for name in sys.modules if name == "aureon.exchanges" or name.startswith("aureon.exchanges.")}
    assert catalog["status"] == "cited"
    assert catalog["called"] is False
    assert catalog["catalog"]["rows"] == 647
    assert catalog["catalog"]["reachable"] == 0
    assert catalog["catalog"]["modules"] == 43
    assert refused["live_orders"] == "refused"
    assert refused.get("called") is not True
    assert names["status"] == "unavailable"
    assert after == before
    assert secret not in json.dumps(catalog)


def test_execute_and_secret_arguments_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.exchanges_surface import exchanges_surface

    secret = "planted-exchanges-surface-binance-secret"
    monkeypatch.setenv("BINANCE_API_SECRET", secret)
    execute = _load(
        exchanges_surface(
            "exchanges/kraken_client.py",
            "KrakenClient.get_order_status",
            action="EXECUTE",
        )
    )
    assert execute["status"] == "unavailable"
    assert execute["decision"] == "HOLD"
    assert execute["execute"] == "refused"
    assert execute["live_orders"] == "refused"
    assert execute.get("called") is not True
    assert "get_order_status" not in json.dumps(execute)
    hidden = _load(exchanges_surface("exchanges/kraken_client.py", secret))
    text = json.dumps(hidden)
    assert secret not in text
    assert hidden["status"] == "unavailable"
    assert hidden["reason"] == "argument is not an inventory id"
    assert hidden["live_orders"] == "refused"


def test_one_inventory_row_is_not_a_call() -> None:
    from aureon_public.exchanges_surface import exchanges_surface

    body = _load(
        exchanges_surface(
            "exchanges/single_currency_equity.py",
            "assemble_sterling_snapshot",
        )
    )
    assert body["status"] == "cited"
    assert body["called"] is False
    assert body["imported"] is False
    assert body["row"]["safety"].startswith("order-capable path")
    assert body["decision"] == "HOLD"
    listed = _load(exchanges_surface("exchanges/single_currency_equity.py"))
    assert "assemble_sterling_snapshot" in listed["shown"]
    assert listed["called"] is False


def test_pin_badge_and_fence_stay() -> None:
    guard = (ROOT / "huggingface" / "hnc-field" / "guard.py").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    public = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    from aureon_public.guard_loader import PINNED_COMMIT

    loader = (ROOT / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    assert "aureon.exchanges" in guard
    assert "release%20boundary-HOLD-orange" in readme
    assert f'PINNED_COMMIT = "{PINNED_COMMIT}"' in loader
    assert "reachable now 69" in public
    assert "alive" not in public.lower()
    from aureon_public.body import ENABLED_THROUGH, OPEN_PLAN_THROUGH

    assert OPEN_PLAN_THROUGH == 2
    assert ENABLED_THROUGH == 6


def _kept_env() -> dict[str, str]:
    return {
        key: os.environ[key]
        for key in ("PATH", "HOME", "LANG", "LC_ALL", "SYSTEMROOT", "TMPDIR", "TMP", "TEMP")
        if key in os.environ
    }


def test_measured_sweep_matches_a_fresh_child() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validation/go_live_stage8_exchanges.py", "--check"],
        cwd=str(ROOT),
        env={**_kept_env(), "PYTHONPATH": str(ROOT / "mcp")},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("ok ")
    record = json.loads((ROOT / "measured" / "go_live_stage8_exchanges.json").read_text(encoding="utf-8"))
    assert record["published"] is False
    assert record["pin_moved"] is False
    assert record["badge"] == "unchanged"
    assert record["go_live_clear"] is False
    assert record["guard"]["sockets"] == []
    assert record["guard"]["import_attempts"] == []
    assert "planted-exchanges-surface" not in json.dumps(record)
