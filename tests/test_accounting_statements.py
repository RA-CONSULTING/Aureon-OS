"""
The Royal Decrees — statements derived from the books, never invented.

Pins: P&L is revenue minus expenses from posted entries only; the balance
sheet proves assets = liabilities + equity + retained profit; suspense is
surfaced honestly on both statements; renderers are deterministic
(byte-identical on identical books) and carry every line item.
"""

from __future__ import annotations

import pytest

from aureon.accounting.client_ledger import ClientLedger, Posting
from aureon.accounting.statements import (
    balance_sheet,
    profit_and_loss,
    render_csv,
    render_markdown,
)


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


def _books() -> ClientLedger:
    led = ClientLedger("ra-consulting")
    # capital in, a sale with VAT, wages, rent — a real month in miniature
    led.post("opening capital", [Posting("1000", debit_pennies=500_000),
                                 Posting("3000", credit_pennies=500_000)])
    led.post("consulting invoice", [Posting("1000", debit_pennies=120_000),
                                    Posting("4000", credit_pennies=100_000),
                                    Posting("2100", credit_pennies=20_000)])
    led.post("payroll", [Posting("6000", debit_pennies=80_000),
                         Posting("1000", credit_pennies=80_000)])
    led.post("rent", [Posting("7000", debit_pennies=30_000),
                      Posting("1000", credit_pennies=30_000)])
    return led


def test_profit_and_loss_from_posted_entries_only():
    pnl = profit_and_loss(_books())
    assert pnl["total_revenue_pennies"] == 100_000
    assert pnl["total_expenses_pennies"] == 110_000
    assert pnl["profit_pennies"] == -10_000
    assert pnl["uncategorized_suspense_pennies"] == 0


def test_balance_sheet_proves_itself():
    bs = balance_sheet(_books())
    assert bs["balances"] is True
    # bank: 500,000 + 120,000 − 80,000 − 30,000
    assert bs["total_assets_pennies"] == 510_000
    # VAT owed 20,000 + capital 500,000 + retained −10,000
    assert bs["total_liabilities_and_equity_pennies"] == 510_000


def test_suspense_is_surfaced_not_hidden():
    led = _books()
    led.post("unexplained receipt", [Posting("1000", debit_pennies=5_000),
                                     Posting("9999", credit_pennies=5_000)])
    pnl = profit_and_loss(led)
    assert pnl["uncategorized_suspense_pennies"] == -5_000
    assert pnl["profit_pennies"] == -10_000  # suspense never leaks into P&L
    bs = balance_sheet(led)
    assert bs["balances"] is True            # and the position still proves


def test_renderers_deterministic_and_complete():
    led = _books()
    md1, md2 = render_markdown(profit_and_loss(led)), render_markdown(profit_and_loss(led))
    assert md1 == md2
    assert "£1,000.00" in md1 and "Profit" in md1
    bs_md = render_markdown(balance_sheet(led))
    assert "BALANCED" in bs_md
    csv_text = render_csv(balance_sheet(led))
    assert csv_text.splitlines()[0] == "section,code,name,balance_pennies"
    assert any(",2100," in ln for ln in csv_text.splitlines())
