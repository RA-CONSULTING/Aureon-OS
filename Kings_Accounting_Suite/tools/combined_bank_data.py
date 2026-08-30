"""Combine repo-held bank/account exports into one accounting-period feed.

This module is deliberately read-only. It inventories transaction exports from
the repo, normalises the common statement formats into the accounting gateway
shape, parses supported bank-statement PDFs, and keeps unparsed PDFs/images as
evidence coverage.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Sequence


STANDARD_FIELDNAMES = ["Date", "Description", "Amount", "Balance"]
FULL_FIELDNAMES = [
    "Date",
    "Description",
    "Amount",
    "Balance",
    "Source File",
    "Source Account",
    "Source Directory",
    "Source Provider",
    "Flow Provider",
    "Transaction Code",
    "Duplicate Source Files",
    "Duplicate Source Accounts",
    "Duplicate Source Providers",
]

EVIDENCE_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"}
SKIP_DIR_NAMES = {
    ".git",
    ".claude",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "output",
    "cache",
}


@dataclass
class BankSourceSummary:
    path: str
    name: str
    source_account: str
    source_directory: str
    source_kind: str
    rows_read: int = 0
    rows_in_period: int = 0
    rows_imported: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class CombinedBankData:
    period_start: str
    period_end: str
    csv_sources: list[BankSourceSummary]
    evidence_files: list[dict[str, Any]]
    rows: list[dict[str, str]]
    duplicate_rows: int = 0
    total_rows_read: int = 0
    total_rows_in_period: int = 0
    skipped_rows: int = 0
    pdf_sources: list[BankSourceSummary] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def source_accounts(self) -> list[str]:
        values = {
            source.source_account
            for source in [*self.csv_sources, *self.pdf_sources]
            if source.source_account
        }
        return sorted(values)

    def to_standard_csv(self) -> str:
        return _rows_to_csv_string(self.rows, STANDARD_FIELDNAMES)

    def to_full_csv(self) -> str:
        return _rows_to_csv_string(self.rows, FULL_FIELDNAMES)

    def to_summary(self, combined_csv_path: str | Path | None = None) -> dict[str, Any]:
        summary = {
            "schema_version": "combined-bank-data-v1",
            "generated_at": self.generated_at,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "csv_source_count": len(self.csv_sources),
            "pdf_source_count": len(self.pdf_sources),
            "transaction_source_count": len(self.csv_sources) + len(self.pdf_sources),
            "evidence_file_count": len(self.evidence_files),
            "total_rows_read": self.total_rows_read,
            "rows_in_period_before_dedupe": self.total_rows_in_period,
            "unique_rows_in_period": len(self.rows),
            "duplicate_rows_removed": self.duplicate_rows,
            "skipped_rows": self.skipped_rows,
            "source_accounts": self.source_accounts,
            "source_provider_summary": summarise_rows_by_field(self.rows, "Source Provider"),
            "flow_provider_summary": summarise_rows_by_field(self.rows, "Flow Provider"),
            "source_account_row_summary": summarise_rows_by_field(self.rows, "Source Account"),
            "csv_sources": [asdict(source) for source in self.csv_sources],
            "pdf_sources": [asdict(source) for source in self.pdf_sources],
            "evidence_files": self.evidence_files,
        }
        if combined_csv_path is not None:
            summary["combined_csv_path"] = str(combined_csv_path)
        return summary


def combine_bank_data_for_period(
    repo_root: str | Path,
    period_start: str,
    period_end: str,
    *,
    raw_roots: Sequence[str | Path] | None = None,
    include_default_roots: bool = True,
) -> CombinedBankData:
    """Load every known repo-held bank/account source into one period dataset."""

    root = Path(repo_root)
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)

    source_roots = resolve_source_roots(root, raw_roots, include_default_roots=include_default_roots)
    csv_paths = discover_csv_sources(root, source_roots=source_roots)
    pdf_paths = discover_pdf_transaction_sources(root, source_roots=source_roots)
    evidence_files = discover_evidence_files(root, source_roots=source_roots)

    summaries: list[BankSourceSummary] = []
    pdf_summaries: list[BankSourceSummary] = []
    period_rows: list[dict[str, str]] = []
    total_rows_read = 0
    total_rows_in_period = 0
    skipped_rows = 0

    for path in csv_paths:
        summary = BankSourceSummary(
            path=str(path),
            name=path.name,
            source_account=infer_source_account(path),
            source_directory=source_directory_label(root, path),
            source_kind="csv_unknown",
        )
        try:
            rows, headers = read_csv_rows(path)
            summary.rows_read = len(rows)
            summary.source_kind = detect_source_kind(headers)
            total_rows_read += summary.rows_read

            for row in rows:
                normalised = normalise_transaction_row(
                    row,
                    path=path,
                    source_account=summary.source_account,
                    source_directory=summary.source_directory,
                )
                if normalised is None:
                    summary.rows_skipped += 1
                    skipped_rows += 1
                    continue
                row_date = date.fromisoformat(normalised["Date"])
                if start <= row_date <= end:
                    summary.rows_in_period += 1
                    summary.rows_imported += 1
                    total_rows_in_period += 1
                    period_rows.append(normalised)
        except Exception as exc:
            summary.errors.append(f"{type(exc).__name__}: {exc}")
        summaries.append(summary)

    for path in pdf_paths:
        summary = BankSourceSummary(
            path=str(path),
            name=path.name,
            source_account=infer_source_account(path),
            source_directory=source_directory_label(root, path),
            source_kind=detect_pdf_source_kind(path),
        )
        try:
            rows = read_pdf_statement_rows(
                path,
                source_account=summary.source_account,
                source_directory=summary.source_directory,
            )
            summary.rows_read = len(rows)
            total_rows_read += summary.rows_read

            for normalised in rows:
                row_date = date.fromisoformat(normalised["Date"])
                if start <= row_date <= end:
                    summary.rows_in_period += 1
                    summary.rows_imported += 1
                    total_rows_in_period += 1
                    period_rows.append(normalised)
        except Exception as exc:
            summary.errors.append(f"{type(exc).__name__}: {exc}")
        pdf_summaries.append(summary)

    unique_rows, duplicate_rows = unique_sorted_rows(period_rows)
    return CombinedBankData(
        period_start=period_start,
        period_end=period_end,
        csv_sources=summaries,
        evidence_files=evidence_files,
        rows=unique_rows,
        duplicate_rows=duplicate_rows,
        total_rows_read=total_rows_read,
        total_rows_in_period=total_rows_in_period,
        skipped_rows=skipped_rows,
        pdf_sources=pdf_summaries,
    )


def resolve_source_roots(
    repo_root: Path,
    raw_roots: Sequence[str | Path] | None = None,
    *,
    include_default_roots: bool = True,
) -> list[Path]:
    roots: list[Path] = []
    if include_default_roots:
        roots.extend([repo_root / "uploads", repo_root / "bussiness accounts"])
    for raw in raw_roots or []:
        path = Path(raw)
        if not path.is_absolute():
            path = repo_root / path
        roots.append(path)

    resolved: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        try:
            key = str(root.resolve()).lower()
        except Exception:
            key = str(root).lower()
        if key in seen:
            continue
        seen.add(key)
        resolved.append(root)
    return resolved


def discover_csv_sources(repo_root: Path, *, source_roots: Sequence[Path] | None = None) -> list[Path]:
    roots = list(source_roots) if source_roots is not None else resolve_source_roots(repo_root)
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.csv"), key=lambda p: str(p).lower()):
            if path.is_file() and not _is_skipped(path):
                paths.append(path)
    return paths


def discover_pdf_transaction_sources(repo_root: Path, *, source_roots: Sequence[Path] | None = None) -> list[Path]:
    """Find statement PDFs that add non-CSV bank-account transactions.

    The Revolut account-statement PDFs are retained as evidence because this
    repo also contains the richer Revolut transaction-report CSV for the same
    account. Zempler monthly PDFs are parsed because they represent a distinct
    business account that otherwise only existed as passive evidence.
    """

    paths: list[Path] = []
    roots = list(source_roots) if source_roots is not None else resolve_source_roots(repo_root)
    for source_root in roots:
        if not source_root.exists():
            continue
        paths.extend(
            path
            for path in sorted(source_root.rglob("Statement__GBP_*.pdf"), key=lambda p: str(p).lower())
            if path.is_file() and not _is_skipped(path)
        )
    return sorted(set(paths), key=lambda p: str(p).lower())


def discover_evidence_files(repo_root: Path, *, source_roots: Sequence[Path] | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    roots = list(source_roots) if source_roots is not None else resolve_source_roots(repo_root)
    for source_root in roots:
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*"), key=lambda p: str(p).lower()):
            if not path.is_file() or _is_skipped(path):
                continue
            if path.suffix.lower() not in EVIDENCE_SUFFIXES:
                continue
            stat = path.stat()
            records.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "source_account": infer_source_account(path),
                    "bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                }
            )
    return records


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    raw = ""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"):
        try:
            raw = path.read_text(encoding=encoding)
            break
        except UnicodeError as exc:
            last_error = exc
    if not raw and last_error is not None:
        raise last_error

    raw = raw.replace("\x00", "")
    stream = io.StringIO(raw)
    try:
        sample = stream.read(4096)
        stream.seek(0)
        dialect = csv.Sniffer().sniff(sample)
        reader = csv.DictReader(stream, dialect=dialect)
    except csv.Error:
        stream.seek(0)
        reader = csv.DictReader(stream)

    headers = [str(header or "").strip() for header in (reader.fieldnames or [])]
    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned: dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            clean_key = str(key).strip()
            if not clean_key:
                continue
            cleaned[clean_key] = str(value or "").strip()
        if any(cleaned.values()):
            rows.append(cleaned)
    return rows, headers


def detect_source_kind(headers: Iterable[str]) -> str:
    lowered = {header.strip().lower() for header in headers}
    if {"date", "description", "amount"}.issubset(lowered):
        return "statement_csv"
    if {"transaction date", "transaction code", "reference", "amount"}.issubset(lowered):
        return "transaction_report_csv"
    if {"date", "amount (gbp)"}.issubset(lowered):
        return "bank_export_csv"
    return "csv_unknown"


def detect_pdf_source_kind(path: Path) -> str:
    if path.name.startswith("Statement__GBP_"):
        return "zempler_statement_pdf"
    if path.name.startswith("account-statement_"):
        return "revolut_statement_pdf"
    return "statement_pdf"


def read_pdf_statement_rows(
    path: Path,
    *,
    source_account: str,
    source_directory: str,
) -> list[dict[str, str]]:
    text = extract_pdf_text(path)
    if path.name.startswith("Statement__GBP_"):
        return parse_zempler_statement_text(
            text,
            path=path,
            source_account=source_account,
            source_directory=source_directory,
        )
    return []


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError(f"pypdf unavailable: {exc}") from exc

    reader = PdfReader(str(path))
    chunks = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(chunks).replace("\x00", "")


def parse_zempler_statement_text(
    text: str,
    *,
    path: Path,
    source_account: str,
    source_directory: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    i = 0
    while i < len(lines):
        parsed_date = parse_date_value(lines[i])
        if parsed_date is None or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", lines[i]):
            i += 1
            continue

        i += 1
        transaction_code = ""
        if i < len(lines) and re.fullmatch(r"\d{4}", lines[i]):
            transaction_code = lines[i]
            i += 1

        description_parts: list[str] = []
        while i < len(lines) and not looks_like_money_line(lines[i]):
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}", lines[i]) or is_statement_footer(lines[i]):
                break
            description_parts.append(lines[i])
            i += 1

        if i >= len(lines) or not looks_like_money_line(lines[i]):
            continue
        amount = normalise_decimal(lines[i])
        i += 1

        while i < len(lines) and not looks_like_money_line(lines[i]):
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}", lines[i]) or is_statement_footer(lines[i]):
                break
            description_parts.append(lines[i])
            i += 1

        balance = ""
        if i < len(lines) and looks_like_money_line(lines[i]):
            balance = normalise_decimal(lines[i])
            i += 1

        if not amount:
            continue
        description = collapse_space(" ".join(description_parts)) or path.stem
        source_provider = infer_source_provider(path, source_account)
        rows.append(
            {
                "Date": parsed_date.isoformat(),
                "Description": description,
                "Amount": amount,
                "Balance": balance,
                "Source File": str(path),
                "Source Account": source_account,
                "Source Directory": source_directory,
                "Source Provider": source_provider,
                "Flow Provider": infer_flow_provider(description, source_provider),
                "Transaction Code": transaction_code,
                "Duplicate Source Files": "",
                "Duplicate Source Accounts": "",
                "Duplicate Source Providers": "",
            }
        )
    return rows


def looks_like_money_line(value: str) -> bool:
    text = collapse_space(value)
    if not text:
        return False
    # PDF text extraction frequently mangles the pound sign into the UTF-8/
    # latin-1 mojibake "Â£" — real Zempler statements come through that way,
    # so the optional "Â" is part of the money-line shape, not noise.
    return bool(
        re.fullmatch(r"-?\s*Â?[£Ł]\s*[\d, ]+\.\d{2}", text)
        or re.fullmatch(r"\(?-?\d{1,3}(?:,\d{3})*\.\d{2}\)?", text)
    )


def is_statement_footer(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith(
        (
            "zempler bank",
            "authorised by",
            "and regulated",
            "under firm reference",
            "zempler bank provides",
        )
    )


def normalise_transaction_row(
    row: dict[str, str],
    *,
    path: Path,
    source_account: str,
    source_directory: str,
) -> dict[str, str] | None:
    date_text = first_value(row, "Date", "Transaction date", "Transaction Date", "Txn Date", "Posted Date")
    parsed_date = parse_date_value(date_text)
    if parsed_date is None:
        return None

    amount = amount_from_row(row)
    if amount == "":
        return None

    balance = normalise_decimal(
        first_value(row, "Balance", "Available balance", "Available Balance", "Balance (GBP)", "Running Balance")
    )
    transaction_code = first_value(row, "Transaction code", "Transaction Code", "Type")
    description = first_value(
        row,
        "Description",
        "Reference",
        "Narrative",
        "Details",
        "Transaction description",
        "Transaction Description",
        "Memo",
        "Name",
    )
    if transaction_code and transaction_code not in description:
        description = f"{description} [{transaction_code}]".strip()
    if not description:
        description = path.stem

    source_provider = infer_source_provider(path, source_account)
    return {
        "Date": parsed_date.isoformat(),
        "Description": collapse_space(description),
        "Amount": amount,
        "Balance": balance,
        "Source File": str(path),
        "Source Account": source_account,
        "Source Directory": source_directory,
        "Source Provider": source_provider,
        "Flow Provider": infer_flow_provider(description, source_provider),
        "Transaction Code": transaction_code,
        "Duplicate Source Files": "",
        "Duplicate Source Accounts": "",
        "Duplicate Source Providers": "",
    }


def amount_from_row(row: dict[str, str]) -> str:
    amount = normalise_decimal(first_value(row, "Amount", "Value", "Sum", "Amount (GBP)"))
    if amount:
        return amount

    debit = normalise_decimal(first_value(row, "Debit", "Debit amount", "Paid out", "Money out"))
    credit = normalise_decimal(first_value(row, "Credit", "Credit amount", "Paid in", "Money in"))
    try:
        debit_value = Decimal(debit or "0")
        credit_value = Decimal(credit or "0")
    except InvalidOperation:
        return ""
    value = credit_value if credit_value != 0 else -abs(debit_value)
    return format_decimal(value)


def first_value(row: dict[str, str], *names: str) -> str:
    exact = {key: value for key, value in row.items()}
    lowered = {key.strip().lower(): key for key in row}
    for name in names:
        if name in exact and str(exact[name]).strip():
            return str(exact[name]).strip()
        key = lowered.get(name.strip().lower())
        if key and str(row.get(key, "")).strip():
            return str(row.get(key, "")).strip()
    return ""


def parse_date_value(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalise_decimal(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = (
        text.replace("GBP", "")
        .replace("gbp", "")
        .replace("Â£", "")  # mojibake pound from PDF extraction
        .replace("£", "")
        .replace("Ł", "")
    )
    text = text.replace(",", "").replace(" ", "")
    if text.endswith("-"):
        negative = True
        text = text[:-1]
    if not text:
        return ""
    try:
        value_decimal = Decimal(text)
    except InvalidOperation:
        return ""
    if negative:
        value_decimal = -abs(value_decimal)
    return format_decimal(value_decimal)


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def unique_sorted_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    seen: dict[tuple[str, str, str, str], dict[str, str]] = {}
    unique: list[dict[str, str]] = []
    duplicates = 0
    for row in rows:
        key = (
            row.get("Date", ""),
            collapse_space(row.get("Description", "")).lower(),
            money_key(row.get("Amount", "")),
            money_key(row.get("Balance", "")),
        )
        if key in seen:
            duplicates += 1
            merge_duplicate_source(seen[key], row)
            continue
        seen[key] = row
        unique.append(row)
    unique.sort(
        key=lambda row: (
            row.get("Date", ""),
            row.get("Source Account", ""),
            row.get("Description", ""),
            row.get("Amount", ""),
        )
    )
    return unique, duplicates


def merge_duplicate_source(existing: dict[str, str], duplicate: dict[str, str]) -> None:
    for field in ("Source File", "Source Account", "Source Directory", "Source Provider"):
        existing[field] = merge_semicolon_values(existing.get(field, ""), duplicate.get(field, ""))
    existing["Duplicate Source Files"] = merge_semicolon_values(
        existing.get("Duplicate Source Files", "") or existing.get("Source File", ""),
        duplicate.get("Source File", ""),
    )
    existing["Duplicate Source Accounts"] = merge_semicolon_values(
        existing.get("Duplicate Source Accounts", "") or existing.get("Source Account", ""),
        duplicate.get("Source Account", ""),
    )
    existing["Duplicate Source Providers"] = merge_semicolon_values(
        existing.get("Duplicate Source Providers", "") or existing.get("Source Provider", ""),
        duplicate.get("Source Provider", ""),
    )


def merge_semicolon_values(*values: str) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in split_semicolon_values(value):
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return "; ".join(merged)


def split_semicolon_values(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def money_key(value: str) -> str:
    normalised = normalise_decimal(value)
    return normalised if normalised else str(value or "").strip()


def infer_source_account(path: Path) -> str:
    name = path.name
    match = re.search(r"Transactions Report ([A-Za-z0-9]+)", name)
    if match:
        return match.group(1)
    if name.startswith("Statement__GBP_"):
        return "business_gbp_monthly"
    if name.startswith("account-statement_"):
        return "business_account_statement"
    if name.startswith("Statement_"):
        return "uploads_statement"
    return path.stem


def infer_source_provider(path: Path, source_account: str) -> str:
    name = path.name.lower()
    account = source_account.lower()
    if account == "business_gbp_monthly" or name.startswith("statement__gbp_"):
        return "zempler"
    if (
        account in {"msagm9ys", "business_account_statement", "uploads_statement"}
        or name.startswith("account-statement_")
        or name.startswith("transactions report ")
        or name.startswith("statement_")
    ):
        return "revolut"
    return "unknown"


def infer_flow_provider(description: str, source_provider: str) -> str:
    text = collapse_space(description).lower()
    if "sumup" in text or "ravenous" in text:
        return "sumup"
    if any(term in text for term in ("revolut", "revolot", "revolution", "r&a consulting")):
        return "revolut"
    return source_provider or "unknown"


def summarise_rows_by_field(rows: list[dict[str, str]], field: str) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        values = split_semicolon_values(row.get(field, "")) or ["unknown"]
        amount = Decimal(normalise_decimal(row.get("Amount", "")) or "0")
        for value in values:
            bucket = summary.setdefault(
                value,
                {
                    "rows": 0,
                    "money_in": "0.00",
                    "money_out": "0.00",
                    "net": "0.00",
                },
            )
            bucket["rows"] += 1
            bucket["money_in"] = format_decimal(Decimal(bucket["money_in"]) + (amount if amount > 0 else Decimal("0")))
            bucket["money_out"] = format_decimal(Decimal(bucket["money_out"]) + (amount if amount < 0 else Decimal("0")))
            bucket["net"] = format_decimal(Decimal(bucket["net"]) + amount)
    return dict(sorted(summary.items()))


def source_directory_label(repo_root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(repo_root)
    except ValueError:
        return path.parent.name
    return relative.parts[0] if relative.parts else path.parent.name


def collapse_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _rows_to_csv_string(rows: list[dict[str, str]], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return buffer.getvalue()


def _is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)
