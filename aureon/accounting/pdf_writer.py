"""
The Royal Press — deterministic PDFs from the books, no external wheel.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The statements and filing shapes already render deterministic markdown; this
module presses those pages into PDF — the format an accountant, HMRC clerk,
or Companies House reviewer actually opens. It writes the PDF byte-for-byte
by hand (header, page tree, Courier text streams, xref, trailer): no
reportlab, no fpdf, no network, no timestamps in the file — the SAME books
always press the SAME bytes, so a client pack can be diffed and audited.

``client_pack`` assembles the full document set for one client from the real
renderers (trial balance, P&L, balance sheet, MTD VAT 9-box, FRS 105) — every
page still carrying the honesty boundary its renderer printed on it.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

from aureon.accounting.client_ledger import ClientLedger

__all__ = ["press_pdf", "client_pack"]

_PAGE_W, _PAGE_H = 595, 842          # A4 in points
_MARGIN, _LEAD = 40, 12              # left/top margin, line leading
_LINES_PER_PAGE = (_PAGE_H - 2 * _MARGIN) // _LEAD


def _escape(line: str) -> bytes:
    """One text line as a PDF string: WinAnsi bytes, specials escaped."""
    raw = line.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _content_stream(lines: list[str]) -> bytes:
    parts = [b"BT /F1 10 Tf %d %d Td %d TL" % (_MARGIN, _PAGE_H - _MARGIN, _LEAD)]
    for line in lines:
        parts.append(b"(" + _escape(line) + b") Tj T*")
    parts.append(b"ET")
    return b"\n".join(parts)


def press_pdf(title: str, text: str) -> bytes:
    """Press a text document (e.g. a rendered markdown page) into PDF bytes.

    Deterministic by construction: no creation date, no random IDs — the
    same title and text always produce identical bytes.
    """
    all_lines = [title, "=" * min(len(title), 90), ""]
    all_lines += [ln.rstrip() for ln in str(text).splitlines()]
    pages = [all_lines[i:i + _LINES_PER_PAGE]
             for i in range(0, len(all_lines), _LINES_PER_PAGE)] or [[""]]

    # object numbering: 1 catalog · 2 pages · 3 font · then per page (page, stream)
    objects: list[bytes] = []
    n_pages = len(pages)
    page_ids = [4 + 2 * i for i in range(n_pages)]
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier "
                   b"/Encoding /WinAnsiEncoding >>")
    for i, page_lines in enumerate(pages):
        stream = _content_stream(page_lines)
        objects.append(
            (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
             f"/Resources << /Font << /F1 3 0 R >> >> "
             f"/Contents {page_ids[i] + 1} 0 R >>").encode("ascii"))
        objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for num, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (num, body)
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, xref_at))
    return bytes(out)


def client_pack(ledger: ClientLedger) -> dict[str, bytes]:
    """The full PDF document set for one client, pressed from the real books.

    Every document is derived by the same renderers the tests pin — the pack
    is a faithful pressing, never a re-computation.
    """
    from aureon.accounting.filings import (
        frs105_micro_balance_sheet,
        render_filing_markdown,
        vat_nine_box,
    )
    from aureon.accounting.statements import balance_sheet, profit_and_loss, render_markdown

    tb = ledger.trial_balance()
    tb_lines = [f"{r['code']}  {r['name']:<40} Dr {r['debit_pennies']:>12}p  "
                f"Cr {r['credit_pennies']:>12}p" for r in tb["rows"]]
    tb_lines += ["", f"TOTALS: Dr {tb['total_debit_pennies']}p / Cr {tb['total_credit_pennies']}p "
                     f"— {'BALANCED' if tb['balanced'] else 'OUT OF BALANCE'}"]

    cid = ledger.client_id
    return {
        "trial_balance.pdf": press_pdf(f"Trial balance — {cid}", "\n".join(tb_lines)),
        "profit_and_loss.pdf": press_pdf(
            f"Profit & loss — {cid}", render_markdown(profit_and_loss(ledger))),
        "balance_sheet.pdf": press_pdf(
            f"Balance sheet — {cid}", render_markdown(balance_sheet(ledger))),
        "vat_nine_box.pdf": press_pdf(
            f"MTD VAT 9-box draft — {cid}", render_filing_markdown(vat_nine_box(ledger))),
        "frs105_micro.pdf": press_pdf(
            f"FRS 105 micro-entity draft — {cid}",
            render_filing_markdown(frs105_micro_balance_sheet(ledger))),
    }
