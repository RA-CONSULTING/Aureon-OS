"""
The King's Court foundation — double-entry for any client, honest at every step.

Pins: postings balance or are refused (and the refusal is recorded), unknown
nominal codes are refused, the trial balance proves itself, file-drop rows
carry provenance and land in suspense (never guessed into a P&L line),
malformed rows are named blockers, the pay roster computes published-rate
payslips deterministically, and a dark HNC field reports gamma=None — never
an invented number.
"""

from __future__ import annotations

import pytest

from aureon.accounting.client_ledger import ClientLedger, Posting
from aureon.accounting.file_drop import ingest_file, registered_ingestors
from aureon.accounting.uk_payroll_reference import payslip_breakdown


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    # accounting must behave identically whether the field is live or dark;
    # tests pin the DARK posture (gamma None) so no ambient trace leaks in
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


# ── the ledger ────────────────────────────────────────────────────────────────

def test_balanced_posting_and_trial_balance():
    led = ClientLedger("ra-consulting")
    eid = led.post("invoice paid by customer",
                   [Posting("1000", debit_pennies=120_000),
                    Posting("4000", credit_pennies=100_000),
                    Posting("2100", credit_pennies=20_000)])
    assert eid is not None
    tb = led.trial_balance()
    assert tb["balanced"] is True
    assert tb["total_debit_pennies"] == tb["total_credit_pennies"] == 120_000
    assert led.balance_pennies("4000") == 100_000
    assert led.balance_pennies("2100") == 20_000


def test_unbalanced_and_unknown_code_refused_and_recorded():
    led = ClientLedger("ra-consulting")
    assert led.post("broken", [Posting("1000", debit_pennies=100)]) is None
    assert led.post("bad code", [Posting("1000", debit_pennies=100),
                                 Posting("8888", credit_pennies=100)]) is None
    assert led.entries == []
    rep = led.coordination_report()
    assert rep["steps_total"] == 2 and rep["steps_ok"] == 0
    assert rep["coordination_coherence"] == 0.0
    # the dark field is reported dark — never a substituted number
    assert all(s["gamma"] is None for s in rep["steps"])


def test_coordination_coherence_is_measured_fraction():
    led = ClientLedger("acme-ltd")
    led.post("ok", [Posting("1000", debit_pennies=50), Posting("3000", credit_pennies=50)])
    led.post("broken", [Posting("1000", debit_pennies=1)])
    rep = led.coordination_report()
    assert rep["steps_total"] == 2
    assert rep["coordination_coherence"] == 0.5


def test_client_id_required():
    with pytest.raises(ValueError):
        ClientLedger("  ")


# ── the file drop ─────────────────────────────────────────────────────────────

def test_bank_csv_rows_post_balanced_into_suspense(tmp_path):
    f = tmp_path / "statement.csv"
    f.write_text("date,description,amount\n"
                 "2026-01-05,Client payment,1200.00\n"
                 "06/01/2026,Office rent,-850.50\n", encoding="utf-8")
    led = ClientLedger("ra-consulting")
    res = ingest_file("bank_csv", f, led)
    assert res.rows_seen == 2 and res.entries_posted == 2 and not res.blockers
    assert led.trial_balance()["balanced"] is True
    assert led.balance_pennies("1000") == 120_000 - 85_050
    # uncategorized money WAITS in suspense — never guessed into a P&L line
    assert led.suspense_pennies() == -(120_000 - 85_050)
    # provenance travels with every entry
    assert all("statement.csv" in e["reference"] for e in led.entries)


def test_malformed_rows_are_named_blockers_never_guessed(tmp_path):
    f = tmp_path / "statement.csv"
    f.write_text("date,description,amount\n"
                 "not-a-date,Mystery,10.00\n"
                 "2026-01-07,,25.00\n"
                 "2026-01-08,Zero line,0\n"
                 "2026-01-09,Good row,99.99\n", encoding="utf-8")
    led = ClientLedger("acme-ltd")
    res = ingest_file("bank_csv", f, led)
    assert res.entries_posted == 1
    assert len(res.blockers) == 3
    assert all("statement.csv" in b for b in res.blockers)
    assert led.trial_balance()["balanced"] is True


def test_missing_header_and_unregistered_kind_refused(tmp_path):
    f = tmp_path / "odd.csv"
    f.write_text("when,what,how_much\n2026-01-05,x,1.00\n", encoding="utf-8")
    led = ClientLedger("acme-ltd")
    res = ingest_file("bank_csv", f, led)
    assert res.entries_posted == 0 and res.blockers
    res2 = ingest_file("carrier_pigeon", f, led)
    assert res2.entries_posted == 0
    assert "no ingestor registered" in res2.blockers[0]
    assert "bank_csv" in registered_ingestors()


# ── the open pay roster ──────────────────────────────────────────────────────

def test_ruk_payslip_hand_computed_30k():
    p = payslip_breakdown(30_000_00)
    assert p["personal_allowance_pennies"] == 12_570_00
    assert p["income_tax_pennies"] == 3_486_00          # 17,430 × 20%
    assert p["employee_ni_pennies"] == 1_394_40         # (30,000−12,570) × 8%
    assert p["employer_ni_pennies"] == 3_750_00         # (30,000−5,000) × 15%
    assert p["net_pay_pennies"] == 30_000_00 - 3_486_00 - 1_394_40
    assert "NOT a filing authority" in p["source_note"]


def test_allowance_tapers_to_zero_above_125140():
    p = payslip_breakdown(130_000_00)
    assert p["personal_allowance_pennies"] == 0
    # 37,700×20% + 74,870×40% + 17,430×45%
    assert p["income_tax_pennies"] == 4_533_150


def test_scottish_bands_differ_from_ruk():
    s = payslip_breakdown(30_000_00, scotland=True)
    # 2,827×19% + 12,094×20% + 2,509×21% = 3,482.82
    assert s["income_tax_pennies"] == 3_482_82
    assert s["income_tax_pennies"] != payslip_breakdown(30_000_00)["income_tax_pennies"]


def test_ni_category_roster():
    assert payslip_breakdown(30_000_00, ni_category="C")["employee_ni_pennies"] == 0
    # under-21 relief: employer pays nothing below the upper limit
    assert payslip_breakdown(30_000_00, ni_category="M")["employer_ni_pennies"] == 0
    with pytest.raises(ValueError):
        payslip_breakdown(30_000_00, ni_category="Q")


def test_payslip_deterministic():
    assert payslip_breakdown(47_123_45) == payslip_breakdown(47_123_45)
