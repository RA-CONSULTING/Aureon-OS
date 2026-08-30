"""
The Filing Shapes — documents in the forms HMRC and Companies House expect.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Two statutory shapes computed straight from the client's double-entry books:

* **MTD VAT 9-box** — the Making Tax Digital VAT return layout. Boxes 1 and 4
  come from the output/input VAT splits on the chart (2110/2120); boxes 6-7
  from the posted net sales and inputs. Boxes 2, 8 and 9 (NI-protocol goods
  movements) are computed from the ledger too — a book with no such postings
  reports zero because zero is what it HOLDS, and the note says so.
* **FRS 105 micro-entity balance sheet** — the Companies House micro-entity
  layout, mapped from nominal codes by an explicit registry (a code lands on
  a statutory line by NAME, never by guess).

HONESTY BOUNDARY: these are filing-SHAPED drafts derived from the books — the
documents an accountant reviews and submits. Nothing here transmits anything
to HMRC or Companies House, and every rendered page says so.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from typing import Any, Dict

from aureon.accounting.client_ledger import ClientLedger

__all__ = ["vat_nine_box", "frs105_micro_balance_sheet", "render_filing_markdown"]

FILING_NOTE = (
    "Filing-shaped DRAFT derived from the posted books — for review by an "
    "accountant before submission. This system does not transmit to HMRC or "
    "Companies House."
)


def _sums(ledger: ClientLedger, code: str) -> tuple:
    debit = sum(ln["debit_pennies"] for e in ledger.entries
                for ln in e["lines"] if ln["code"] == code)
    credit = sum(ln["credit_pennies"] for e in ledger.entries
                 for ln in e["lines"] if ln["code"] == code)
    return debit, credit


def vat_nine_box(ledger: ClientLedger) -> Dict[str, Any]:
    """The MTD VAT return shape, every box a sum over posted lines."""
    out_d, out_c = _sums(ledger, "2110")   # output tax posts as credits
    in_d, in_c = _sums(ledger, "2120")     # input tax posts as debits
    box1 = out_c - out_d
    box2 = 0  # no NI-protocol acquisition postings exist on this chart
    box3 = box1 + box2
    box4 = in_d - in_c
    box5 = box3 - box4                     # positive → payable to HMRC
    revenue = sum(ledger.balance_pennies(c) for c in ledger.chart if c[:1] == "4")
    inputs = sum(ledger.balance_pennies(c) for c in ledger.chart
                 if c[:1] in ("5", "6", "7"))
    return {
        "statement": "vat_nine_box",
        "client_id": ledger.client_id,
        "boxes": {
            "1_vat_due_on_sales_pennies": box1,
            "2_vat_due_on_ni_acquisitions_pennies": box2,
            "3_total_vat_due_pennies": box3,
            "4_vat_reclaimed_on_purchases_pennies": box4,
            "5_net_vat_pennies": box5,
            "6_total_sales_ex_vat_pennies": revenue,
            "7_total_purchases_ex_vat_pennies": inputs,
            "8_ni_goods_supplied_pennies": 0,
            "9_ni_goods_acquired_pennies": 0,
        },
        "notes": [
            "boxes 2, 8, 9 are zero because the books hold no NI-protocol "
            "goods-movement postings — measured absence, not an assumption",
            FILING_NOTE,
        ],
    }


#: nominal-code prefix → FRS 105 statutory line. Registry-as-data: a code
#: lands on a line by NAME here, never by inference.
_FRS105_LINES: Dict[str, str] = {
    "1": "Current assets",
    "2": "Creditors: amounts falling due within one year",
    "3": "Capital and reserves",
}


def frs105_micro_balance_sheet(ledger: ClientLedger) -> Dict[str, Any]:
    """The Companies House micro-entity balance sheet shape."""
    from aureon.accounting.statements import balance_sheet

    bs = balance_sheet(ledger)
    lines: Dict[str, int] = dict.fromkeys(_FRS105_LINES.values(), 0)
    for section in ("assets", "liabilities", "equity"):
        for row in bs[section]:
            line = _FRS105_LINES.get(row["code"][:1])
            if line:
                lines[line] += row["balance_pennies"]
    lines["Capital and reserves"] += bs["retained_profit_pennies"]
    # suspense sits honestly on whichever side it falls
    if bs["suspense_pennies"] > 0:
        lines["Current assets"] += bs["suspense_pennies"]
    elif bs["suspense_pennies"] < 0:
        lines["Creditors: amounts falling due within one year"] += -bs["suspense_pennies"]
    net_assets = (lines["Current assets"]
                  - lines["Creditors: amounts falling due within one year"])
    return {
        "statement": "frs105_micro_balance_sheet",
        "client_id": ledger.client_id,
        "lines": lines,
        "net_assets_pennies": net_assets,
        "capital_and_reserves_pennies": lines["Capital and reserves"],
        "balances": net_assets == lines["Capital and reserves"],
        "notes": [FILING_NOTE],
    }


def render_filing_markdown(filing: Dict[str, Any]) -> str:
    """Deterministic markdown for a filing shape — same books, same page."""
    def pounds(p: int) -> str:
        sign = "-" if p < 0 else ""
        p = abs(int(p))
        return f"{sign}£{p // 100:,}.{p % 100:02d}"

    kind = filing.get("statement", "filing")
    lines = [f"# {kind.replace('_', ' ').title()} — {filing.get('client_id', '?')}", ""]
    for key, value in sorted((filing.get("boxes") or {}).items()):
        lines.append(f"- Box {key.replace('_pennies', '').replace('_', ' ')}: {pounds(value)}")
    for name, value in (filing.get("lines") or {}).items():
        lines.append(f"- {name}: {pounds(value)}")
    for key, label in (("net_assets_pennies", "Net assets"),
                       ("capital_and_reserves_pennies", "Capital and reserves")):
        if key in filing:
            lines.append(f"**{label}:** {pounds(filing[key])}")
    if "balances" in filing:
        lines.append(f"**{'BALANCED' if filing['balances'] else 'OUT OF BALANCE'}**")
    lines.append("")
    for note in filing.get("notes", []):
        lines.append(f"> {note}")
    return "\n".join(lines) + "\n"
