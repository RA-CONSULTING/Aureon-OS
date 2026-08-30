"""
HMRC developer standards — the books press into the published v1.0 schema.

Pins: the payload carries EXACTLY the 11 field names HMRC's VAT (MTD) API
v1.0 requires; boxes 1-5 are exact 2-dp pounds and boxes 6-9 whole pounds;
netVatDue is the non-negative absolute difference; every published range and
cross-field rule is enforced with NAMED violations; truncated pennies are
reported, never hidden; the whole pressing is deterministic and traceable to
the spec URL.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from aureon.accounting.client_ledger import ClientLedger, Posting
from aureon.accounting.filings import vat_nine_box
from aureon.accounting.hmrc_mtd import (
    HMRC_VAT_MTD_SOURCE,
    build_vat_return,
    validate_vat_return,
)

_HMRC_FIELDS = {
    "periodKey", "vatDueSales", "vatDueAcquisitions", "totalVatDue",
    "vatReclaimedCurrPeriod", "netVatDue", "totalValueSalesExVAT",
    "totalValuePurchasesExVAT", "totalValueGoodsSuppliedExVAT",
    "totalAcquisitionsExVAT", "finalised",
}


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


def _books() -> ClientLedger:
    led = ClientLedger("ra-consulting")
    led.post("invoice", [Posting("1100", debit_pennies=120_000),
                         Posting("4000", credit_pennies=100_000),
                         Posting("2110", credit_pennies=20_000)], when=1.0)
    led.post("supplier bill", [Posting("7100", debit_pennies=50_000),
                               Posting("2120", debit_pennies=10_000),
                               Posting("2000", credit_pennies=60_000)], when=2.0)
    return led


def test_payload_matches_the_published_schema_exactly():
    out = build_vat_return(vat_nine_box(_books()), "24A1")
    p = out["payload"]
    assert set(p) == _HMRC_FIELDS                       # names verbatim from the OAS
    assert p["vatDueSales"] == Decimal("200.00")
    assert p["vatDueAcquisitions"] == Decimal("0.00")
    assert p["totalVatDue"] == Decimal("200.00")
    assert p["vatReclaimedCurrPeriod"] == Decimal("100.00")
    assert p["netVatDue"] == Decimal("100.00")
    assert p["totalValueSalesExVAT"] == 1000            # whole pounds
    assert p["totalValuePurchasesExVAT"] == 500
    assert p["totalValueGoodsSuppliedExVAT"] == 0
    assert p["totalAcquisitionsExVAT"] == 0
    assert p["finalised"] is False
    assert out["violations"] == []                      # clean against every rule
    assert out["rounding_notes"] == []                  # nothing truncated here
    assert out["source"]["spec_url"] == HMRC_VAT_MTD_SOURCE["spec_url"]
    assert "does NOT transmit" in __import__("aureon.accounting.hmrc_mtd",
                                             fromlist=["__doc__"]).__doc__


def test_net_vat_due_is_absolute_when_reclaim_exceeds_output():
    led = ClientLedger("acme-ltd")
    led.post("big purchase", [Posting("7100", debit_pennies=500_000),
                              Posting("2120", debit_pennies=100_000),
                              Posting("2000", credit_pennies=600_000)], when=1.0)
    out = build_vat_return(vat_nine_box(led), "24A2")
    p = out["payload"]
    assert p["totalVatDue"] == Decimal("0.00")
    assert p["vatReclaimedCurrPeriod"] == Decimal("1000.00")
    assert p["netVatDue"] == Decimal("1000.00")         # absolute, never negative
    assert out["violations"] == []


def test_truncated_pennies_are_reported_never_hidden():
    led = ClientLedger("acme-ltd")
    led.post("odd invoice", [Posting("1100", debit_pennies=120_050),
                             Posting("4000", credit_pennies=100_042),
                             Posting("2110", credit_pennies=20_008)], when=1.0)
    out = build_vat_return(vat_nine_box(led), "24A3")
    assert out["payload"]["totalValueSalesExVAT"] == 1000   # 1000.42 → 1000
    assert any("totalValueSalesExVAT" in n and "42p truncated" in n
               for n in out["rounding_notes"])
    assert out["violations"] == []


def test_every_published_rule_refuses_with_a_named_violation():
    clean = build_vat_return(vat_nine_box(_books()), "24A1")["payload"]
    cases = [
        ({"periodKey": "TOOLONG"}, "periodKey"),
        ({"vatDueSales": Decimal("1.005")}, "decimal places"),
        ({"vatDueSales": Decimal("99999999999999.00")}, "outside"),
        ({"netVatDue": Decimal("-1.00")}, "non-negative"),
        ({"totalValueSalesExVAT": Decimal("10.50")}, "whole pounds"),
        ({"finalised": "yes"}, "boolean"),
        ({"totalVatDue": Decimal("999.00")}, "vatDueSales + vatDueAcquisitions"),
        ({"netVatDue": Decimal("42.00")}, "absolute difference"),
    ]
    for tamper, expect in cases:
        bad = {**clean, **tamper}
        violations = validate_vat_return(bad)
        assert violations, f"tamper {tamper} slipped through"
        assert any(expect in x for x in violations), (expect, violations)
    missing = {k: v for k, v in clean.items() if k != "netVatDue"}
    assert any("missing required" in x for x in validate_vat_return(missing))


def test_deterministic_pressing():
    a = build_vat_return(vat_nine_box(_books()), "24A1")
    b = build_vat_return(vat_nine_box(_books()), "24A1")
    assert a == b
