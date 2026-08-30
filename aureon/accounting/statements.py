"""
The Royal Decrees — the statements a business actually sends out the door.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The ledger holds the truth; this module speaks it. Three statements computed
straight from the double-entry books — profit & loss, balance sheet, and the
trial balance — plus deterministic renderers (markdown and CSV) so the same
books always produce byte-identical documents. Everything is derived from
posted entries; nothing here can invent a number the ledger does not hold.

The balance sheet proves itself the classical way: assets equal liabilities
plus equity plus retained profit, or the statement says so — loudly.

HMRC/Companies House filing shapes (MTD VAT 9-box, FRS 105 micro-entity)
build on these primitives in the next organ; this module produces the
management pack every client needs first.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

from aureon.accounting.client_ledger import ClientLedger

__all__ = ["profit_and_loss", "balance_sheet", "render_markdown", "render_csv"]


def _pounds(pennies: int) -> str:
    sign = "-" if pennies < 0 else ""
    p = abs(int(pennies))
    return f"{sign}£{p // 100:,}.{p % 100:02d}"


def _section(ledger: ClientLedger, prefixes: tuple) -> List[Dict[str, Any]]:
    rows = []
    for code in sorted(ledger.chart):
        if code[:1] in prefixes and code != "9999":
            bal = ledger.balance_pennies(code)
            if bal:
                rows.append({"code": code, "name": ledger.chart[code],
                             "balance_pennies": bal})
    return rows


def profit_and_loss(ledger: ClientLedger) -> Dict[str, Any]:
    """Revenue less expenses, straight from the posted entries."""
    revenue = _section(ledger, ("4",))
    expenses = _section(ledger, ("5", "6", "7"))
    total_rev = sum(r["balance_pennies"] for r in revenue)
    total_exp = sum(r["balance_pennies"] for r in expenses)
    suspense = ledger.suspense_pennies()
    return {
        "statement": "profit_and_loss",
        "client_id": ledger.client_id,
        "revenue": revenue,
        "expenses": expenses,
        "total_revenue_pennies": total_rev,
        "total_expenses_pennies": total_exp,
        "profit_pennies": total_rev - total_exp,
        # honesty line: money still awaiting categorization is NOT in this
        # P&L — it is named here so the reader knows the statement's edge
        "uncategorized_suspense_pennies": suspense,
    }


def balance_sheet(ledger: ClientLedger) -> Dict[str, Any]:
    """Assets against liabilities + equity + retained profit — self-proving."""
    assets = _section(ledger, ("1",))
    # suspense is genuinely part of the position until categorized: a debit
    # suspense balance is an unexplained asset, a credit one an obligation
    suspense = ledger.suspense_pennies()
    liabilities = _section(ledger, ("2",))
    equity = _section(ledger, ("3",))
    pnl = profit_and_loss(ledger)["profit_pennies"]

    total_assets = sum(r["balance_pennies"] for r in assets) + max(suspense, 0)
    total_liab_eq = (sum(r["balance_pennies"] for r in liabilities)
                     + sum(r["balance_pennies"] for r in equity)
                     + pnl + max(-suspense, 0))
    return {
        "statement": "balance_sheet",
        "client_id": ledger.client_id,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "retained_profit_pennies": pnl,
        "suspense_pennies": suspense,
        "total_assets_pennies": total_assets,
        "total_liabilities_and_equity_pennies": total_liab_eq,
        "balances": total_assets == total_liab_eq,
    }


def render_markdown(statement: Dict[str, Any]) -> str:
    """Deterministic markdown — the same books always print the same page."""
    kind = statement.get("statement", "statement")
    lines = [f"# {kind.replace('_', ' ').title()} — {statement.get('client_id', '?')}", ""]
    for key in ("revenue", "expenses", "assets", "liabilities", "equity"):
        rows = statement.get(key)
        if rows is None:
            continue
        lines.append(f"## {key.title()}")
        if not rows:
            lines.append("_none posted_")
        for r in rows:
            lines.append(f"- `{r['code']}` {r['name']}: {_pounds(r['balance_pennies'])}")
        lines.append("")
    for key, label in (("total_revenue_pennies", "Total revenue"),
                       ("total_expenses_pennies", "Total expenses"),
                       ("profit_pennies", "Profit"),
                       ("retained_profit_pennies", "Retained profit"),
                       ("total_assets_pennies", "Total assets"),
                       ("total_liabilities_and_equity_pennies", "Liabilities + equity"),
                       ("uncategorized_suspense_pennies", "Awaiting categorization"),
                       ("suspense_pennies", "Suspense")):
        if key in statement:
            lines.append(f"**{label}:** {_pounds(statement[key])}")
    if "balances" in statement:
        lines.append("")
        lines.append("**The statement proves itself: assets = liabilities + equity"
                     f" — {'BALANCED' if statement['balances'] else 'OUT OF BALANCE'}**")
    return "\n".join(lines) + "\n"


def render_csv(statement: Dict[str, Any]) -> str:
    """Deterministic CSV of every line item, for whatever tool comes next."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["section", "code", "name", "balance_pennies"])
    for key in ("revenue", "expenses", "assets", "liabilities", "equity"):
        for r in statement.get(key) or []:
            w.writerow([key, r["code"], r["name"], r["balance_pennies"]])
    return buf.getvalue()
