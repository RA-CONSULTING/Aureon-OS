from __future__ import annotations

import json

from aureon.trading.official_market_context import (
    CFTC_GOLD_URI,
    NOAA_KP_URI,
    TREASURY_URI,
    fetch_cftc_gold_context,
    fetch_noaa_kp_context,
    fetch_treasury_yield_context,
)

NOW = 1_786_480_000.0


class _Response:
    def __init__(self, *, payload=None, content: bytes = b""):
        self.payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_cftc_reader_selects_exact_gold_and_derives_positioning() -> None:
    row = {
        "id": "260804088691F",
        "report_date_as_yyyy_mm_dd": "2026-08-04T00:00:00.000",
        "contract_market_name": "GOLD",
        "market_and_exchange_names": "GOLD - COMMODITY EXCHANGE INC.",
        "futonly_or_combined": "FutOnly",
        "noncomm_positions_long_all": "227013",
        "noncomm_positions_short_all": "29379",
        "comm_positions_long_all": "71832",
        "comm_positions_short_all": "298323",
        "open_interest_all": "371551",
    }
    session = _Session([_Response(payload=[row])])

    context = fetch_cftc_gold_context(session=session, clock=lambda: NOW)

    assert session.calls[0][0] == CFTC_GOLD_URI
    assert session.calls[0][1]["params"]["$where"] == (
        "contract_market_name='GOLD' AND futonly_or_combined='FutOnly'"
    )
    assert context["payload"]["noncommercial_net_contracts"] == 197634
    assert context["payload"]["commercial_net_contracts"] == -226491


def test_treasury_reader_selects_latest_official_curve_row() -> None:
    xml = b"""<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices">
      <entry><content><m:properties><d:NEW_DATE>2026-08-11T00:00:00</d:NEW_DATE>
      <d:BC_2YEAR>4.10</d:BC_2YEAR><d:BC_5YEAR>4.30</d:BC_5YEAR>
      <d:BC_10YEAR>4.60</d:BC_10YEAR><d:BC_30YEAR>5.20</d:BC_30YEAR>
      </m:properties></content></entry>
      <entry><content><m:properties><d:NEW_DATE>2026-08-12T00:00:00</d:NEW_DATE>
      <d:BC_2YEAR>4.20</d:BC_2YEAR><d:BC_5YEAR>4.38</d:BC_5YEAR>
      <d:BC_10YEAR>4.68</d:BC_10YEAR><d:BC_30YEAR>5.24</d:BC_30YEAR>
      </m:properties></content></entry>
    </feed>"""
    session = _Session([_Response(content=xml)])

    context = fetch_treasury_yield_context(session=session, clock=lambda: NOW)

    assert session.calls[0][0] == TREASURY_URI
    assert context["payload"] == {
        "date": "2026-08-12T00:00:00",
        "five_year_yield_pct": 4.38,
        "ten_year_yield_pct": 4.68,
        "thirty_year_yield_pct": 5.24,
        "two_year_yield_pct": 4.2,
    }


def test_noaa_reader_selects_latest_kp_without_action_authority() -> None:
    session = _Session(
        [
            _Response(
                payload=[
                    {"time_tag": "2026-08-13T13:00:00Z", "Kp": 2.33, "station_count": 8},
                    {"time_tag": "2026-08-13T14:00:00Z", "Kp": 3.00, "station_count": 8},
                ]
            )
        ]
    )

    context = fetch_noaa_kp_context(session=session, clock=lambda: NOW)

    assert session.calls == [(NOAA_KP_URI, {"timeout": 20})]
    assert context["payload"]["estimated_kp"] == 3.0
    assert "action_eligible" not in json.dumps(context)
