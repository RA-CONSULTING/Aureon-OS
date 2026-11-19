"""Append-only ledger of exchange-confirmed fills from the Orca kill chain.

``orca_executions.json`` is an attempt log. It records ERROR, NO_FUNDS,
BUY_FAILED, ARBITRAGE_LOGGED and other outcomes, and it is written relative
to the process cwd. This module does not read that file.

A row is written only from an exchange response whose status is FILLED,
PARTIALLY_FILLED, or Kraken's closed (stored as the venue status), with a
filled quantity greater than zero and a real exchange order id. Requested
quantity, dry-run, not-submitted, paper, and shadow responses write nothing.

``aureon_owned_qty`` is buys minus sells for one venue and symbol, using that
filled quantity. A missing, unreadable, corrupt, or partially written ledger
returns zero and does not raise. PR #370 consumes this helper for exit caps.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX only
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # pragma: no cover - Windows only
    msvcrt = None  # type: ignore[assignment]

logger = logging.getLogger("aureon.orca_real_fills")

SOURCE = "orca_kill_chain"
CONFIRMED_FILL_STATUSES = frozenset({"FILLED", "PARTIALLY_FILLED", "CLOSED"})
_PLACEHOLDER_IDS = frozenset({"", "none", "null", "unknown", "n/a", "na", "0", "-1"})
_NON_FILL_TRUTH = frozenset(
    {"simulated", "not_submitted", "paper", "shadow", "dry_run", "dry-run"}
)
_QTY_KEYS = ("executedQty", "filled_qty", "filledQty", "executed_qty")
_ORDER_ID_KEYS = ("orderId", "provider_order_id", "exchange_order_id")
_CLIENT_ID_KEYS = (
    "clientOrderId",
    "provider_client_order_id",
    "cl_ord_id",
    "client_order_id",
)
_AVG_PRICE_KEYS = ("avgPrice", "avg_fill_price", "filled_avg_price", "avg_price")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        marker = parent / "aureon_radar" / "bots" / "orca_unified_kill_chain.py"
        if marker.is_file():
            return parent
    return here.parents[2]


LEDGER_PATH = _repo_root() / "state" / "aureon_real_fills.jsonl"


def _ledger(path: Path | None) -> Path:
    return LEDGER_PATH if path is None else Path(path)


def _positive_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        qty = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, ArithmeticError):
        return None
    if not qty.is_finite() or qty <= 0:
        return None
    return qty


def _filled_qty(payload: dict[str, Any]) -> Decimal | None:
    """Exchange filled quantity. Requested size is never read.

    A present quantity field that is zero, negative, or not a number means
    this response is not a positive fill, even if another quantity field is.
    """
    found: list[Decimal] = []
    for key in _QTY_KEYS:
        if key not in payload:
            continue
        raw = payload.get(key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        qty = _positive_decimal(raw)
        if qty is None:
            return None
        found.append(qty)
    if not found or any(qty != found[0] for qty in found):
        return None
    return found[0]


def _text_id(value: Any) -> str | None:
    if isinstance(value, list):
        if len(value) != 1:
            return None
        value = value[0]
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if text.lower() in _PLACEHOLDER_IDS:
        return None
    return text


def _order_id(payload: dict[str, Any]) -> str | None:
    for key in _ORDER_ID_KEYS:
        found = _text_id(payload.get(key))
        if found is not None:
            return found
    return None


def _client_order_id(payload: dict[str, Any]) -> str | None:
    for key in _CLIENT_ID_KEYS:
        if payload.get(key) is None:
            continue
        return _text_id(payload.get(key))
    return None


def _avg_price(payload: dict[str, Any]) -> str | None:
    found: list[Decimal] = []
    for key in _AVG_PRICE_KEYS:
        raw = payload.get(key)
        if raw is None or raw == "":
            continue
        price = _positive_decimal(raw)
        if price is None:
            return None
        found.append(price)
    if not found or any(price != found[0] for price in found):
        return None
    return format(found[0], "f")


def _status(payload: dict[str, Any]) -> str | None:
    raw = payload.get("status")
    if raw is None:
        return None
    status = str(raw).strip().upper().replace(" ", "_").replace("-", "_")
    if status not in CONFIRMED_FILL_STATUSES:
        return None
    return status


def _not_a_live_fill(payload: dict[str, Any]) -> bool:
    if payload.get("dryRun") is True or payload.get("dry_run") is True:
        return True
    if payload.get("shadow") is True or payload.get("paper") is True:
        return True
    if payload.get("submitted") is False:
        return True
    if payload.get("generated_values") is True:
        return True
    truth = str(payload.get("truth_status") or "").strip().lower()
    data_status = str(payload.get("data_status") or "").strip().lower()
    mode = str(payload.get("mode") or "").strip().lower()
    return bool(
        truth in _NON_FILL_TRUTH or data_status in _NON_FILL_TRUTH or mode in _NON_FILL_TRUTH
    )


def _side(payload: dict[str, Any], fallback: str) -> str | None:
    raw = payload.get("side")
    chosen = fallback if raw is None or str(raw).strip() == "" else str(raw)
    side = chosen.strip().upper()
    if side not in {"BUY", "SELL"}:
        return None
    sent = str(fallback or "").strip().upper()
    if sent and sent != side:
        return None
    return side


def _timestamp(payload: dict[str, Any]) -> str:
    for key in ("timestamp", "provider_timestamp", "source_timestamp"):
        raw = payload.get(key)
        if isinstance(raw, str) and "T" in raw:
            return raw
    return datetime.now(UTC).isoformat()


def confirmed_fill_record(
    venue: str,
    symbol: str,
    side: str,
    response: Any,
) -> dict[str, Any] | None:
    """Normalize one confirmed fill, or None when the response is not one."""
    if not isinstance(response, dict) or response.get("error"):
        return None
    if _not_a_live_fill(response):
        return None
    status = _status(response)
    filled = _filled_qty(response)
    order_id = _order_id(response)
    normalized_side = _side(response, side)
    venue_key = str(venue or "").strip().lower()
    symbol_key = str(symbol or "").strip().upper()
    if (
        status is None
        or filled is None
        or order_id is None
        or normalized_side is None
        or not venue_key
        or not symbol_key
    ):
        return None
    qty_text = format(filled, "f")
    return {
        "venue": venue_key,
        "symbol": symbol_key,
        "side": normalized_side,
        "status": status,
        "filled_qty": qty_text,
        "executedQty": qty_text,
        "avg_price": _avg_price(response),
        "exchange_order_id": order_id,
        "client_order_id": _client_order_id(response),
        "timestamp": _timestamp(response),
        "source": SOURCE,
    }


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    """Lock a sidecar so append and read do not tear a line."""
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        elif msvcrt is not None:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:  # pragma: no cover - Windows and POSIX both lock above
            raise OSError("no file lock available for the real-fill ledger")
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _read_rows(path: Path) -> list[dict[str, Any]] | None:
    """Rows, an empty list when the file is absent, or None when it is not trustworthy."""
    if not path.exists():
        return []
    if not path.is_file():
        raise OSError(f"real fill ledger is not a file: {path}")
    text = path.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(row, dict):
            return None
        rows.append(row)
    return rows


def _countable_qty(row: dict[str, Any]) -> Decimal | None:
    if _not_a_live_fill(row):
        return None
    if _status(row) is None or _order_id(row) is None:
        return None
    return _filled_qty(row)


def record_confirmed_fill(
    venue: str,
    symbol: str,
    side: str,
    response: Any,
    *,
    ledger_path: Path | None = None,
) -> dict[str, Any] | None:
    """Append one confirmed fill. Returns the row, or None when nothing was written.

    A write failure is logged and not raised, so the order path keeps its own result.
    """
    record = confirmed_fill_record(venue, symbol, side, response)
    if record is None:
        return None
    path = _ledger(ledger_path)
    try:
        _append(path, record)
    except Exception as exc:
        logger.error(
            "real fill not recorded venue=%s symbol=%s side=%s status=%s "
            "exchange_order_id=%s filled_qty=%s: %s: %s",
            record["venue"],
            record["symbol"],
            record["side"],
            record["status"],
            record["exchange_order_id"],
            record["filled_qty"],
            type(exc).__name__,
            exc,
        )
        return None
    return record


def _append(path: Path, record: dict[str, Any]) -> None:
    with _exclusive_lock(path):
        rows = _read_rows(path)
        if rows is None:
            raise OSError(f"real fill ledger corrupt or partial: {path}")
        new_qty = Decimal(record["filled_qty"])
        for row in rows:
            if (
                str(row.get("venue") or "").strip().lower() == record["venue"]
                and str(row.get("symbol") or "").strip().upper() == record["symbol"]
                and str(row.get("side") or "").strip().upper() == record["side"]
                and str(row.get("exchange_order_id") or "") == record["exchange_order_id"]
            ):
                existing = _filled_qty(row)
                if existing is not None and existing >= new_qty:
                    return
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def aureon_owned_qty(
    venue: str,
    symbol: str,
    *,
    ledger_path: Path | None = None,
) -> Decimal:
    """Filled buys minus filled sells for this venue and symbol.

    Any missing, unreadable, corrupt, or partially written ledger is zero.
    This never raises.
    """
    venue_key = str(venue or "").strip().lower()
    symbol_key = str(symbol or "").strip().upper()
    if not venue_key or not symbol_key:
        return Decimal(0)
    path = _ledger(ledger_path)
    if not path.exists():
        return Decimal(0)
    try:
        with _exclusive_lock(path):
            rows = _read_rows(path)
    except Exception as exc:
        logger.error(
            "real fill ledger unreadable path=%s; owned qty 0: %s: %s",
            path,
            type(exc).__name__,
            exc,
        )
        return Decimal(0)
    if rows is None:
        logger.error("real fill ledger corrupt or partial path=%s; owned qty 0", path)
        return Decimal(0)
    best: dict[tuple[str, str], Decimal] = {}
    for row in rows:
        if str(row.get("venue") or "").strip().lower() != venue_key:
            continue
        if str(row.get("symbol") or "").strip().upper() != symbol_key:
            continue
        side = str(row.get("side") or "").strip().upper()
        if side not in {"BUY", "SELL"}:
            continue
        qty = _countable_qty(row)
        order_id = _order_id(row)
        if qty is None or order_id is None:
            continue
        key = (side, order_id)
        previous = best.get(key)
        if previous is None or qty > previous:
            best[key] = qty
    bought = sum((qty for (side, _order), qty in best.items() if side == "BUY"), Decimal(0))
    sold = sum((qty for (side, _order), qty in best.items() if side == "SELL"), Decimal(0))
    return bought - sold
