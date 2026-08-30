"""
HMRC developer standards — the MTD VAT return in the EXACT shape HMRC accepts.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The King's Court's ``vat_nine_box`` computes the boxes from the posted books;
this module presses them into the request-body schema of HMRC's **VAT (MTD)
API v1.0** — field names, ranges, precisions, and cross-field rules taken
from the PUBLISHED OpenAPI specification on the HMRC Developer Hub, not from
memory:

    source: https://developer.service.hmrc.gov.uk/api-documentation/docs/
            api/service/vat-api/1.0  (OAS resolved), retrieved 2026-08-07

The spec, as published:

* All 11 body fields required: ``periodKey`` (4 alphanumeric chars, may
  include #), ``vatDueSales``, ``vatDueAcquisitions``, ``totalVatDue``,
  ``vatReclaimedCurrPeriod`` (monetary, 2 dp, ±9,999,999,999,999.99),
  ``netVatDue`` (0 to 99,999,999,999.99 — NON-NEGATIVE), the four
  ``totalValue*ExVAT`` boxes (whole pounds only, ±9,999,999,999,999), and
  ``finalised`` (boolean declaration).
* Cross-field: ``totalVatDue`` = vatDueSales + vatDueAcquisitions;
  ``netVatDue`` = ABSOLUTE difference of totalVatDue and
  vatReclaimedCurrPeriod.

``build_vat_return`` maps our measured 9-box (integer pennies) onto that
schema; ``validate_vat_return`` re-checks EVERY published rule and returns
named violations — a payload that fails the standard is refused with reasons,
never shipped quietly.

HONESTY BOUNDARY: this builds and validates the HMRC-shaped document. It
does NOT transmit — live submission additionally requires OAuth 2.0 and the
legally-mandated fraud-prevention (Gov-Client-*/Gov-Vendor-*) headers, which
belong to a credentialed transport layer, not to the books.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

__all__ = ["HMRC_VAT_MTD_SOURCE", "build_vat_return", "validate_vat_return"]

HMRC_VAT_MTD_SOURCE = {
    "api": "VAT (MTD)",
    "version": "1.0",
    "spec_url": ("https://developer.service.hmrc.gov.uk/api-documentation/docs/"
                 "api/service/vat-api/1.0"),
    "retrieved": "2026-08-07",
    "note": ("field names, ranges, precisions and cross-field rules copied from the "
             "published OpenAPI specification — verify against the Hub before any "
             "live submission; this system does not transmit"),
}

_MONETARY_FIELDS = ("vatDueSales", "vatDueAcquisitions", "totalVatDue",
                    "vatReclaimedCurrPeriod")
_WHOLE_POUND_FIELDS = ("totalValueSalesExVAT", "totalValuePurchasesExVAT",
                       "totalValueGoodsSuppliedExVAT", "totalAcquisitionsExVAT")
_REQUIRED = ("periodKey", *_MONETARY_FIELDS, "netVatDue", *_WHOLE_POUND_FIELDS,
             "finalised")
_MONETARY_MAX = Decimal("9999999999999.99")
_NET_VAT_MAX = Decimal("99999999999.99")
_WHOLE_MAX = 9_999_999_999_999
_PERIOD_KEY_RE = re.compile(r"^[A-Za-z0-9#]{4}$")


def _pounds_2dp(pennies: int) -> Decimal:
    """Integer pennies → exact pounds with 2 decimal places."""
    return (Decimal(int(pennies)) / Decimal(100)).quantize(Decimal("0.01"))


def build_vat_return(nine_box: dict[str, Any], period_key: str,
                     finalised: bool = False) -> dict[str, Any]:
    """Press a measured ``vat_nine_box`` result into the HMRC v1.0 body schema.

    Boxes 1-5 carry exact 2-dp pounds from the posted pennies. Boxes 6-9 are
    whole pounds per the spec — any truncated pennies are REPORTED in
    ``rounding_notes``, never hidden. ``netVatDue`` is the absolute value of
    our signed box 5, exactly as the published rule demands.
    """
    boxes = nine_box["boxes"]
    rounding_notes: list[str] = []

    def whole_pounds(field: str, pennies: int) -> int:
        pounds, rem = divmod(abs(int(pennies)), 100)
        sign = -1 if pennies < 0 else 1
        if rem:
            rounding_notes.append(
                f"{field}: {rem}p truncated to whole pounds (spec: whole pounds, "
                f"zeroed decimals)")
        return sign * pounds

    payload: dict[str, Any] = {
        "periodKey": str(period_key),
        "vatDueSales": _pounds_2dp(boxes["1_vat_due_on_sales_pennies"]),
        "vatDueAcquisitions": _pounds_2dp(boxes["2_vat_due_on_ni_acquisitions_pennies"]),
        "totalVatDue": _pounds_2dp(boxes["3_total_vat_due_pennies"]),
        "vatReclaimedCurrPeriod": _pounds_2dp(
            boxes["4_vat_reclaimed_on_purchases_pennies"]),
        "netVatDue": abs(_pounds_2dp(boxes["5_net_vat_pennies"])),
        "totalValueSalesExVAT": whole_pounds(
            "totalValueSalesExVAT", boxes["6_total_sales_ex_vat_pennies"]),
        "totalValuePurchasesExVAT": whole_pounds(
            "totalValuePurchasesExVAT", boxes["7_total_purchases_ex_vat_pennies"]),
        "totalValueGoodsSuppliedExVAT": whole_pounds(
            "totalValueGoodsSuppliedExVAT", boxes["8_ni_goods_supplied_pennies"]),
        "totalAcquisitionsExVAT": whole_pounds(
            "totalAcquisitionsExVAT", boxes["9_ni_goods_acquired_pennies"]),
        "finalised": bool(finalised),
    }
    return {
        "payload": payload,
        "violations": validate_vat_return(payload),
        "rounding_notes": rounding_notes,
        "source": dict(HMRC_VAT_MTD_SOURCE),
        "client_id": nine_box.get("client_id", "?"),
        "boundary": ("HMRC-shaped document built and validated against the published "
                     "v1.0 schema — NOT transmitted; live submission requires OAuth "
                     "and the mandated fraud-prevention headers"),
    }


def validate_vat_return(payload: dict[str, Any]) -> list[str]:
    """Every published rule re-checked; returns NAMED violations (empty = clean)."""
    v: list[str] = []
    missing = [f for f in _REQUIRED if f not in payload]
    if missing:
        v.append(f"missing required fields: {missing}")
        return v

    if not _PERIOD_KEY_RE.match(str(payload["periodKey"])):
        v.append("periodKey: must be exactly 4 alphanumeric characters "
                 "(may include #)")

    def dec(field: str) -> Decimal | None:
        try:
            return Decimal(str(payload[field]))
        except Exception:  # noqa: BLE001 — a non-numeric field is a violation, not a crash
            v.append(f"{field}: not a number")
            return None

    for field in _MONETARY_FIELDS:
        d = dec(field)
        if d is None:
            continue
        if d != d.quantize(Decimal("0.01")):
            v.append(f"{field}: more than 2 decimal places ({d})")
        if not (-_MONETARY_MAX <= d <= _MONETARY_MAX):
            v.append(f"{field}: outside ±{_MONETARY_MAX} ({d})")

    net = dec("netVatDue")
    if net is not None:
        if net < 0:
            v.append(f"netVatDue: must be non-negative ({net})")
        if net > _NET_VAT_MAX:
            v.append(f"netVatDue: above {_NET_VAT_MAX} ({net})")
        if net != net.quantize(Decimal("0.01")):
            v.append(f"netVatDue: more than 2 decimal places ({net})")

    for field in _WHOLE_POUND_FIELDS:
        d = dec(field)
        if d is None:
            continue
        if d != d.to_integral_value():
            v.append(f"{field}: whole pounds only per spec ({d})")
        if not (-_WHOLE_MAX <= d <= _WHOLE_MAX):
            v.append(f"{field}: outside ±{_WHOLE_MAX} ({d})")

    if not isinstance(payload["finalised"], bool):
        v.append("finalised: must be a boolean declaration")

    # cross-field rules, verbatim from the published spec
    b1, b2 = dec("vatDueSales"), dec("vatDueAcquisitions")
    b3, b4 = dec("totalVatDue"), dec("vatReclaimedCurrPeriod")
    if b1 is not None and b2 is not None and b3 is not None and b3 != b1 + b2:
        v.append(f"totalVatDue: must equal vatDueSales + vatDueAcquisitions "
                 f"({b3} != {b1} + {b2})")
    if (b3 is not None and b4 is not None and net is not None
            and net != abs(b3 - b4)):
        v.append(f"netVatDue: must be the absolute difference of totalVatDue and "
                 f"vatReclaimedCurrPeriod ({net} != |{b3} - {b4}|)")
    return v
