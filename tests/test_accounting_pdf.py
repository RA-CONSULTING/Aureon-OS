"""
The Royal Press — deterministic, dependency-free PDF pressing of real books.

Pins: valid PDF structure (header, object offsets in the xref that actually
land on their objects, trailer, EOF); same books → identical bytes; long
documents paginate; the client pack presses every statutory document from
the REAL renderers with the honesty boundary carried onto the page.
"""

from __future__ import annotations

import re

import pytest

from aureon.accounting.client_ledger import ClientLedger, Posting
from aureon.accounting.pdf_writer import client_pack, press_pdf


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


def _books() -> ClientLedger:
    led = ClientLedger("ra-consulting")
    led.post("capital", [Posting("1000", debit_pennies=500_000),
                         Posting("3000", credit_pennies=500_000)], when=1.0)
    led.post("invoice", [Posting("1000", debit_pennies=120_000),
                         Posting("4000", credit_pennies=100_000),
                         Posting("2110", credit_pennies=20_000)], when=2.0)
    return led


def test_pressed_pdf_has_valid_structure():
    pdf = press_pdf("Trial balance — ra-consulting", "line one\nline two (with parens)")
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.rstrip().endswith(b"%%EOF")
    # every xref offset must land exactly on its "N 0 obj" header
    xref_at = int(pdf.rsplit(b"startxref", 1)[1].split()[0])
    assert pdf[xref_at:xref_at + 4] == b"xref"
    entries = re.findall(rb"(\d{10}) 00000 n", pdf[xref_at:])
    for num, off in enumerate(entries, start=1):
        at = int(off)
        assert pdf[at:].startswith(b"%d 0 obj" % num)
    # parens escaped inside the content stream, never raw
    assert b"\\(with parens\\)" in pdf


def test_same_books_press_the_same_bytes():
    a = client_pack(_books())
    b = client_pack(_books())
    assert set(a) == {"trial_balance.pdf", "profit_and_loss.pdf", "balance_sheet.pdf",
                      "vat_nine_box.pdf", "frs105_micro.pdf"}
    for name in a:
        assert a[name] == b[name], f"{name} not deterministic"
        assert a[name].startswith(b"%PDF-1.4")


def test_long_document_paginates():
    text = "\n".join(f"row {i}" for i in range(200))
    pdf = press_pdf("Ledger", text)
    assert pdf.count(b"/Type /Page ") >= 2
    m = re.search(rb"/Count (\d+)", pdf)
    assert m and int(m.group(1)) >= 2


def test_pack_carries_the_honesty_boundary():
    pack = client_pack(_books())
    # the filing note travels from the renderer onto the pressed page
    assert b"does not transmit" in pack["vat_nine_box.pdf"]
    assert b"does not transmit" in pack["frs105_micro.pdf"]
    assert b"BALANCED" in pack["trial_balance.pdf"]
