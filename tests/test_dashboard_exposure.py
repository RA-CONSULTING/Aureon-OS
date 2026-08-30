"""
Aureon Power Station — network exposure of the :8080 dashboard.

The Power Station binds ``0.0.0.0`` (containerised and DigitalOcean deploys need it, and the platform's
health check reaches it from outside the container) and served ``/api/status`` with **no credential at
all**. That payload is not cosmetic: it carries ``total_reserves`` / ``total_deployed`` /
``net_energy_gained`` plus every open position with symbol, exchange, entry / current / target price and
live PnL. An adversarial audit reached exactly this port from the operator host.

Three opt-in controls, each pinned here, all defaulting to today's behaviour so no running deployment
changes when this lands:

  * ``AUREON_DASHBOARD_TOKEN``  — require a bearer (or ``?token=``, since a browser navigating to the
    dashboard cannot set a header) on ``/`` and ``/api/status``. ``/health`` stays open: it is a
    liveness probe and carries no financial data.
  * ``AUREON_DASHBOARD_PUBLIC`` — serve a money-redacted status, so the dashboard can be streamed
    publicly without publishing reserves and live positions.
  * ``AUREON_DASHBOARD_BIND``  — restrict the bind interface.

Redaction must be **honest**: withheld keys are ``None`` and named in ``redacted``, never replaced with
plausible-looking numbers (the repo forbids fabricated data).
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("aiohttp", reason="the dashboard web server requires aiohttp")

import aureon.queen.queen_power_dashboard as dash  # noqa: E402


class _Req:
    """Minimal stand-in for an aiohttp request: only headers + query are consulted."""

    def __init__(self, auth: str | None = None, token: str | None = None) -> None:
        self.headers = {"Authorization": auth} if auth else {}
        self.query = {"token": token} if token else {}


_SAMPLE = {
    "cycle": 42,
    "uptime_seconds": 900.0,
    "total_energy": 412345.67,
    "total_reserves": 88888.0,
    "total_deployed": 12904.31,
    "net_energy_gained": 1904.22,
    "energy_conserved": 12.0,
    "energy_growth": 500.0,
    "positions": [{
        "symbol": "BTC/GBP", "exchange": "kraken", "entry_price": 51230.0,
        "current_price": 52042.0, "target_price": 53000.0,
        "current_pnl": 812.44, "current_pnl_pct": 1.6, "progress": 40.0,
    }],
    "relay_energy": {"total": 99999.0, "idle": 5.0, "positions": 3.0, "positions_count": 3},
}


# ── default: unchanged ──────────────────────────────────────────────────────────

def test_no_token_configured_leaves_access_unchanged(monkeypatch):
    """Zero regression: an existing deployment that sets nothing keeps working exactly as before."""
    monkeypatch.delenv("AUREON_DASHBOARD_TOKEN", raising=False)
    assert dash._authorized(_Req()) is True


def test_public_mode_is_off_by_default(monkeypatch):
    monkeypatch.delenv("AUREON_DASHBOARD_PUBLIC", raising=False)
    assert dash._dashboard_public_mode() is False


# ── token gate ─────────────────────────────────────────────────────────────────

def test_token_gate_refuses_missing_and_wrong_credentials(monkeypatch):
    monkeypatch.setenv("AUREON_DASHBOARD_TOKEN", "s3cret")
    assert dash._authorized(_Req()) is False
    assert dash._authorized(_Req(auth="Bearer nope")) is False
    assert dash._authorized(_Req(auth="s3cret")) is False          # missing the Bearer scheme
    assert dash._authorized(_Req(token="nope")) is False


def test_token_gate_accepts_bearer_and_query_token(monkeypatch):
    """The query form exists because a browser opening the dashboard cannot set a header."""
    monkeypatch.setenv("AUREON_DASHBOARD_TOKEN", "s3cret")
    assert dash._authorized(_Req(auth="Bearer s3cret")) is True
    assert dash._authorized(_Req(token="s3cret")) is True


def test_non_ascii_credential_is_refused_not_a_crash(monkeypatch):
    """compare_digest raises TypeError on non-ASCII str, so compare bytes — a unicode header must be
    a clean refusal, never an unhandled 500."""
    monkeypatch.setenv("AUREON_DASHBOARD_TOKEN", "s3cret")
    assert dash._authorized(_Req(auth="Bearer ké¥-nön-ascii")) is False
    assert dash._authorized(_Req(token="ké¥-nön-ascii")) is False


def test_whitespace_only_token_is_treated_as_unset(monkeypatch):
    """A stray space in the env must not flip the dashboard into permanently-locked-out."""
    monkeypatch.setenv("AUREON_DASHBOARD_TOKEN", "   ")
    assert dash._authorized(_Req()) is True


# ── honest redaction ───────────────────────────────────────────────────────────

def test_public_mode_withholds_every_financial_figure():
    red = dash._redact_money(_SAMPLE)
    for key in dash._MONEY_FIELDS:
        assert red.get(key) is None, f"{key} survived redaction"
    position = red["positions"][0]
    for key in dash._POSITION_MONEY_FIELDS:
        assert position.get(key) is None, f"positions[].{key} survived redaction"
    # and no financial VALUE survives anywhere in the serialized payload
    blob = json.dumps(red, default=str)
    for value in ("412345.67", "88888", "12904.31", "51230.0", "812.44", "99999.0"):
        assert value not in blob, f"{value} still present in the redacted payload"


def test_redaction_keeps_the_organism_view():
    """The point is that the dashboard stays watchable — only the money goes."""
    red = dash._redact_money(_SAMPLE)
    assert red["cycle"] == 42
    assert red["uptime_seconds"] == 900.0
    assert red["positions"][0]["symbol"] == "BTC/GBP"
    assert red["positions"][0]["exchange"] == "kraken"
    assert red["positions"][0]["progress"] == 40.0
    assert red["relay_energy"] == {"positions_count": 3}


def test_redaction_is_honest_about_what_it_removed():
    """No fabricated data: withheld means None and named, never a plausible substitute number."""
    red = dash._redact_money(_SAMPLE)
    assert red["redacted"], "the redacted key list must be present"
    assert "total_reserves" in red["redacted"]
    assert any(k.startswith("positions[].") for k in red["redacted"])
    assert "withheld" in red["redaction_note"]
    assert "not zero" in red["redaction_note"]


def test_redaction_tolerates_a_payload_without_the_expected_shape():
    """get_dashboard_data is defensive elsewhere; redaction must not raise on partial input."""
    for payload in ({}, {"cycle": 1}, {"positions": None}, {"positions": ["not-a-dict"]},
                    {"relay_energy": None}):
        out = dash._redact_money(payload)
        assert isinstance(out, dict)
        assert "redacted" in out
