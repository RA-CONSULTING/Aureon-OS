"""
Filing shapes, categorization, and the payroll journal — the pipeline closes.

Pins: the VAT 9-box sums only what the books hold (boxes 2/8/9 zero by
measured absence); FRS 105 proves net assets = capital and reserves; the
categorization court moves suspense by explicit rule or agent seat and NEVER
forces the unexplained; a computed payslip lands as one balanced entry; the
full march (file drop → categorize → payroll → filings) leaves the books
balanced with a measured coordination coherence.
"""

from __future__ import annotations

import pytest

from aureon.accounting.categorize import CategoryRule, recategorize_suspense
from aureon.accounting.client_ledger import ClientLedger, Posting
from aureon.accounting.file_drop import ingest_file
from aureon.accounting.filings import (
    frs105_micro_balance_sheet,
    render_filing_markdown,
    vat_nine_box,
)
from aureon.accounting.payroll_journal import post_payslip
from aureon.accounting.uk_payroll_reference import payslip_breakdown


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


def test_vat_nine_box_sums_only_what_the_books_hold():
    led = ClientLedger("ra-consulting")
    led.post("invoice", [Posting("1000", debit_pennies=120_000),
                         Posting("4000", credit_pennies=100_000),
                         Posting("2110", credit_pennies=20_000)])
    led.post("supplies", [Posting("7100", debit_pennies=50_000),
                          Posting("2120", debit_pennies=10_000),
                          Posting("1000", credit_pennies=60_000)])
    v = vat_nine_box(led)["boxes"]
    assert v["1_vat_due_on_sales_pennies"] == 20_000
    assert v["4_vat_reclaimed_on_purchases_pennies"] == 10_000
    assert v["5_net_vat_pennies"] == 10_000
    assert v["6_total_sales_ex_vat_pennies"] == 100_000
    assert v["7_total_purchases_ex_vat_pennies"] == 50_000
    assert v["2_vat_due_on_ni_acquisitions_pennies"] == 0
    md = render_filing_markdown(vat_nine_box(led))
    assert "does not transmit" in md and "£200.00" in md


def test_frs105_micro_shape_proves_itself():
    led = ClientLedger("acme-ltd")
    led.post("capital", [Posting("1000", debit_pennies=100_000),
                         Posting("3000", credit_pennies=100_000)])
    led.post("sale", [Posting("1000", debit_pennies=60_000),
                      Posting("4000", credit_pennies=60_000)])
    f = frs105_micro_balance_sheet(led)
    assert f["balances"] is True
    assert f["net_assets_pennies"] == f["capital_and_reserves_pennies"] == 160_000
    assert "BALANCED" in render_filing_markdown(f)


def test_categorization_by_rule_agent_and_honest_refusal(tmp_path):
    f = tmp_path / "statement.csv"
    f.write_text("date,description,amount\n"
                 "2026-01-05,Client payment ACME,1200.00\n"
                 "2026-01-06,Office rent January,-850.00\n"
                 "2026-01-07,Completely mysterious,-42.00\n", encoding="utf-8")
    led = ClientLedger("ra-consulting")
    ingest_file("bank_csv", f, led)
    assert led.suspense_pennies() != 0

    rules = [CategoryRule("client payment", "4000"), CategoryRule("rent", "7000")]
    out = recategorize_suspense(led, rules)
    assert out["moved"] == 2 and out["still_in_suspense"] == 1
    # the mystery pound is STILL in suspense — never forced
    assert led.suspense_pennies() == 4_200
    assert led.trial_balance()["balanced"] is True
    assert led.balance_pennies("4000") == 120_000
    assert led.balance_pennies("7000") == 85_000

    # the agent seat names the mystery — and an idempotent second pass moves nothing
    out2 = recategorize_suspense(led, rules, decide=lambda desc, amt: "7100")
    assert out2["moved"] == 1 and out2["suspense_pennies_remaining"] == 0
    out3 = recategorize_suspense(led, rules, decide=lambda desc, amt: "7100")
    assert out3["moved"] == 0


def test_agent_returning_unknown_code_is_refused_and_recorded(tmp_path):
    f = tmp_path / "s.csv"
    f.write_text("date,description,amount\n2026-01-05,Oddity,10.00\n", encoding="utf-8")
    led = ClientLedger("acme-ltd")
    ingest_file("bank_csv", f, led)
    out = recategorize_suspense(led, [], decide=lambda d, a: "8888")
    assert out["refused"] == 1
    assert led.trial_balance()["balanced"] is True
    assert any(not s.ok and "8888" in s.detail for s in led.coordination)


def test_payslip_lands_as_one_balanced_entry():
    led = ClientLedger("ra-consulting")
    led.post("capital", [Posting("1000", debit_pennies=10_000_000),
                         Posting("3000", credit_pennies=10_000_000)])
    slip = payslip_breakdown(30_000_00)
    assert post_payslip(led, slip, "employee-001") is not None
    assert led.trial_balance()["balanced"] is True
    assert led.balance_pennies("6000") == 30_000_00
    assert led.balance_pennies("6100") == slip["employer_ni_pennies"]
    assert led.balance_pennies("2200") == (slip["income_tax_pennies"]
                                           + slip["employee_ni_pennies"]
                                           + slip["employer_ni_pennies"])
    # coordination coherence is measured over the real march
    rep = led.coordination_report()
    assert rep["coordination_coherence"] == 1.0
