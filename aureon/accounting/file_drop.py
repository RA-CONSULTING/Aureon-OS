"""
The File Drop — the accounting body's front door for raw client documents.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A client drops a file; the King reads it. This module turns raw files into
normalized transactions and posts them to the client's double-entry books —
with the same honesty the trading organism lives by:

* Ingestors join by NAME in an explicit registry (a format is registered,
  never inferred from a guess at the bytes).
* Every parsed row carries provenance (file, row number, ingestor).
* A malformed row is a NAMED blocker — reported, skipped, never repaired
  into invented numbers.
* Money that cannot yet be categorized posts to SUSPENSE (9999) — the
  accountant's honest bucket — so the books stay balanced while the
  categorization decision (human or agent) is still to come.

First registered format: ``bank_csv`` — the universal SME starting point
(``date,description,amount`` with amount in pounds, negative = money out).

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

from aureon.accounting.client_ledger import ClientLedger, Posting

__all__ = ["IngestResult", "ingest_file", "registered_ingestors", "ingest_bank_csv"]

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")


@dataclass
class IngestResult:
    """What one file-drop actually did — rows in, entries posted, blockers named."""

    client_id: str
    source_file: str
    ingestor: str
    rows_seen: int = 0
    entries_posted: int = 0
    suspense_pennies_added: int = 0
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"client_id": self.client_id, "source_file": self.source_file,
                "ingestor": self.ingestor, "rows_seen": self.rows_seen,
                "entries_posted": self.entries_posted,
                "suspense_pennies_added": self.suspense_pennies_added,
                "blockers": list(self.blockers)}


def _parse_date(raw: str) -> float:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).replace(
                tzinfo=UTC).timestamp()
        except ValueError:
            continue
    raise ValueError(f"unrecognized date {raw!r} (accepted: {', '.join(_DATE_FORMATS)})")


def _parse_amount_pennies(raw: str) -> int:
    cleaned = raw.strip().replace(",", "").replace("£", "")
    if not cleaned:
        raise ValueError("empty amount")
    pounds = round(float(cleaned) * 100)
    return int(pounds)


def ingest_bank_csv(path: Path, ledger: ClientLedger) -> IngestResult:
    """Bank statement CSV → balanced journal entries.

    Money in: debit bank (1000), credit suspense (9999).
    Money out: credit bank, debit suspense. Categorization out of suspense is
    a SEPARATE, later decision — this stage never guesses a P&L line.
    """
    result = IngestResult(client_id=ledger.client_id, source_file=str(path),
                          ingestor="bank_csv")
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        result.blockers.append(f"{path}: unreadable ({exc}) — nothing ingested")
        return result

    reader = csv.DictReader(text.splitlines())
    fields = {f.strip().lower() for f in (reader.fieldnames or [])}
    required = {"date", "description", "amount"}
    if not required <= fields:
        result.blockers.append(
            f"{path}: header must contain {sorted(required)} (got "
            f"{sorted(fields) or 'no header'}) — nothing ingested")
        return result

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        result.rows_seen += 1
        norm = {str(k).strip().lower(): str(v or "").strip() for k, v in row.items()}
        try:
            ts = _parse_date(norm["date"])
            pennies = _parse_amount_pennies(norm["amount"])
            desc = norm["description"]
            if not desc:
                raise ValueError("empty description")
            if pennies == 0:
                raise ValueError("zero amount")
        except ValueError as exc:
            result.blockers.append(f"{path}:{i}: {exc} — row skipped, never guessed")
            continue

        provenance = f"{Path(path).name}:{i} via bank_csv"
        if pennies > 0:
            postings = [Posting("1000", debit_pennies=pennies, memo=provenance),
                        Posting("9999", credit_pennies=pennies, memo=desc)]
        else:
            postings = [Posting("9999", debit_pennies=-pennies, memo=desc),
                        Posting("1000", credit_pennies=-pennies, memo=provenance)]
        entry_id = ledger.post(desc, postings, reference=provenance, when=ts)
        if entry_id is not None:
            result.entries_posted += 1
            result.suspense_pennies_added += abs(pennies)
    return result


#: Formats join by NAME — the same explicit-registration doctrine as the
#: SaaS defense catalog. An unregistered kind is a named refusal.
_INGESTORS: Dict[str, Callable[[Path, ClientLedger], IngestResult]] = {
    "bank_csv": ingest_bank_csv,
}


def registered_ingestors() -> List[str]:
    return sorted(_INGESTORS)


def ingest_file(kind: str, path: Path, ledger: ClientLedger) -> IngestResult:
    """The front door: dispatch a dropped file to its registered ingestor."""
    fn = _INGESTORS.get(kind)
    if fn is None:
        return IngestResult(
            client_id=ledger.client_id, source_file=str(path), ingestor=kind,
            blockers=[f"no ingestor registered for kind {kind!r} — "
                      f"registered: {registered_ingestors()}"])
    return fn(Path(path), ledger)
