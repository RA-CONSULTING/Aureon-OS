"""Read-only public market series for the brain-proof harness.

The pack is bars and bid/ask prints from a public REST endpoint. It does not
read an exchange key, it does not send an order, and it does not start live
autonomy. Binance public klines are tried first. Kraken public OHLC and Spread
are the fallback. A failed fetch writes a HOLD receipt and does not invent prices.

The committed pack is the harness input. Fetching again replaces it.

Live fetch, when this machine can reach the public endpoints:

    AUREON_DISABLE_REAL_ORDERS=1 PYTHONPATH=. python3 -m aureon.evaluation.market_series --out reports/measured

Check a pack already on disk, with no network:

    PYTHONPATH=. python3 -m aureon.evaluation.market_series --check --out reports/measured
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

SCHEMA = "aureon.market-series.v1"
RELATIVE_JSON = "reports/measured/market_series.json"
RELATIVE_CSV = "reports/measured/market_series.csv"
RELATIVE_SPREAD_CSV = "reports/measured/market_spread.csv"
RELATIVE_MD = "reports/measured/market_series.md"
CLOSED_BARS = 168
INTERVAL_SECONDS = 3600
MIN_CLOSED_BARS = 10
_USER_AGENT = "aureon-market-series/1.0"
_BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
_BINANCE_BOOK = "https://api.binance.com/api/v3/ticker/bookTicker"
_KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"
_KRAKEN_SPREAD = "https://api.kraken.com/0/public/Spread"
_BINANCE_SYMBOL = "BTCUSDT"
_KRAKEN_PAIR = "XBTUSD"
_ENV_MARKERS = ("KEY", "SECRET", "TOKEN", "PASS", "PRIVATE")
_FORBIDDEN_TEXT = (
    "api_key",
    "api-key",
    "api_secret",
    "apisecret",
    "passphrase",
    "private_key",
    "authorization: bearer",
)
Transport = Callable[[str], tuple[int, bytes]]


def http_get(url: str, timeout: float = 20.0) -> tuple[int, bytes]:
    """GET one public URL. HTTP errors return the status and body. No key is added."""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read()
        except OSError:
            body = b""
        return int(exc.code), body


def _iso(unix_seconds: int) -> str:
    return datetime.fromtimestamp(int(unix_seconds), tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _finite(raw: Any) -> float | None:
    if isinstance(raw, bool) or raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return value


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _attempt(venue: str, endpoint: str, *, http_status: int | None, used: bool, error: str | None) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "error": error,
        "http_status": http_status,
        "used": used,
        "venue": venue,
    }


def _call(transport: Transport, url: str) -> tuple[dict[str, Any], bytes | None]:
    try:
        status, body = transport(url)
    except Exception as exc:  # noqa: BLE001 — the receipt names the type, never the message
        return _attempt("", "", http_status=None, used=False, error=type(exc).__name__), None
    if status != 200:
        error = "HTTPError" if status else "transport"
        return _attempt("", "", http_status=status, used=False, error=error), None
    return _attempt("", "", http_status=status, used=False, error=None), body


def _bar(
    open_time: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float,
) -> dict[str, Any] | None:
    if min(open_, high, low, close) <= 0 or high < low or volume < 0:
        return None
    mid = (high + low) / 2.0
    if mid <= 0:
        return None
    return {
        "open_time": int(open_time),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "range_fraction": (high - low) / mid,
    }


def _with_returns(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous: float | None = None
    for bar in bars:
        row = dict(bar)
        if previous is not None and previous > 0:
            row["return"] = (row["close"] - previous) / previous
        previous = row["close"]
        rows.append(row)
    return rows


def _parse_kraken_ohlc(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("error"):
        return []
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    rows: list[Any] = []
    for key, value in result.items():
        if key == "last" or not isinstance(value, list):
            continue
        rows = value
        break
    bars: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            continue
        open_time = _finite(row[0])
        open_ = _finite(row[1])
        high = _finite(row[2])
        low = _finite(row[3])
        close = _finite(row[4])
        volume = _finite(row[6])
        if None in {open_time, open_, high, low, close, volume}:
            continue
        parsed = _bar(int(open_time), open_, high, low, close, volume)
        if parsed is not None:
            bars.append(parsed)
    return bars


def _parse_binance_klines(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    bars: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        open_ms = _finite(row[0])
        open_ = _finite(row[1])
        high = _finite(row[2])
        low = _finite(row[3])
        close = _finite(row[4])
        volume = _finite(row[5])
        if None in {open_ms, open_, high, low, close, volume}:
            continue
        parsed = _bar(int(open_ms // 1000), open_, high, low, close, volume)
        if parsed is not None:
            bars.append(parsed)
    return bars


def _spread_row(stamp: Any, bid_raw: Any, ask_raw: Any) -> dict[str, Any] | None:
    time_value = _finite(stamp)
    bid = _finite(bid_raw)
    ask = _finite(ask_raw)
    if time_value is None or bid is None or ask is None:
        return None
    if bid <= 0 or ask < bid:
        return None
    mid = (ask + bid) / 2.0
    if mid <= 0:
        return None
    return {
        "ask": ask,
        "bid": bid,
        "spread": (ask - bid) / mid,
        "time": int(time_value),
    }


def _parse_kraken_spread(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("error"):
        return []
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    rows: list[Any] = []
    for key, value in result.items():
        if key == "last" or not isinstance(value, list):
            continue
        rows = value
        break
    prints: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 3:
            continue
        parsed = _spread_row(row[0], row[1], row[2])
        if parsed is not None:
            prints.append(parsed)
    return prints


def _parse_binance_book(payload: Any, observed_at: int) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    parsed = _spread_row(observed_at, payload.get("bidPrice"), payload.get("askPrice"))
    if parsed is None:
        return []
    return [parsed]


def _closed_window(bars: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Drop the in-progress bar both venues append, then keep the tail."""

    ordered = sorted(bars, key=lambda item: item["open_time"])
    deduped: dict[int, dict[str, Any]] = {}
    for bar in ordered:
        deduped[int(bar["open_time"])] = bar
    ordered = [deduped[key] for key in sorted(deduped)]
    if len(ordered) < 2:
        return [], 0
    closed = ordered[:-1]
    dropped = 1
    if len(closed) > CLOSED_BARS:
        closed = closed[-CLOSED_BARS:]
    return _with_returns(closed), dropped


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def derive_fields(bars: list[dict[str, Any]], spread_prints: list[dict[str, Any]]) -> dict[str, Any]:
    """Window statistics the Auris call consumes. Missing fields stay omitted."""

    fields: dict[str, Any] = {}
    inputs: dict[str, float] = {}
    if len(bars) >= 2 and bars[0]["close"] > 0:
        momentum = (bars[-1]["close"] - bars[0]["close"]) / bars[0]["close"]
        fields["momentum"] = {
            "clock": "ohlc window, first close to last close",
            "definition": "(last close - first close) / first close",
            "evidence_tag": "measured",
            "value": momentum,
        }
        inputs["momentum"] = momentum
    ranges = [float(bar["range_fraction"]) for bar in bars if _finite(bar.get("range_fraction")) is not None]
    volatility = _mean(ranges)
    if volatility is not None:
        fields["volatility"] = {
            "clock": "ohlc window",
            "definition": "mean of (high - low) / ((high + low) / 2) over the closed bars",
            "evidence_tag": "measured",
            "value": volatility,
        }
        inputs["volatility"] = volatility
    volumes = [float(bar["volume"]) for bar in bars]
    if volumes and max(volumes) > 0:
        volume = volumes[-1] / max(volumes)
        fields["volume"] = {
            "clock": "ohlc window",
            "definition": "last bar base volume / max base volume in the closed window",
            "evidence_tag": "measured",
            "value": volume,
            "volume_base_last": volumes[-1],
            "volume_base_max": max(volumes),
        }
        inputs["volume"] = volume
    if spread_prints:
        latest = spread_prints[-1]
        fields["spread"] = {
            "clock": "latest public bid/ask print, not an OHLC bar",
            "definition": "(ask - bid) / ((ask + bid) / 2) of the latest print",
            "evidence_tag": "measured",
            "print_time": latest["time"],
            "value": latest["spread"],
        }
        inputs["spread"] = float(latest["spread"])
    return {"auris_inputs": inputs, "fields": fields}


def _time_range(bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not bars:
        return None
    start = int(bars[0]["open_time"])
    end = int(bars[-1]["open_time"]) + INTERVAL_SECONDS
    return {
        "clock": "ohlc bar open time; end is the last kept bar open time plus the interval",
        "end": _iso(end),
        "end_unix": end,
        "start": _iso(start),
        "start_unix": start,
    }


def _spread_range(prints: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not prints:
        return None
    start = int(prints[0]["time"])
    end = int(prints[-1]["time"])
    return {
        "clock": "public bid/ask print time",
        "end": _iso(end),
        "end_unix": end,
        "note": "This is the venue's recent spread window, not a print for every OHLC bar.",
        "prints": len(prints),
        "start": _iso(start),
        "start_unix": start,
    }


def _base_pack() -> dict[str, Any]:
    return {
        "authenticated": False,
        "evidence_tag": "hold",
        "key_group": None,
        "key_material": "none",
        "live_autonomy": False,
        "live_trading": False,
        "orders_placed": False,
        "schema": SCHEMA,
    }


def assemble_pack(
    *,
    venue: str,
    symbol: str,
    source: str,
    spread_source: str | None,
    venue_interval: str,
    bars: list[dict[str, Any]],
    spread_prints: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    capture: dict[str, Any],
    fetched_at: str,
    parser: str,
) -> dict[str, Any]:
    """Build a loaded pack from parsed public rows. The caller has already dropped the open bar."""

    spread_prints = sorted(spread_prints, key=lambda item: (int(item["time"]), float(item["bid"]), float(item["ask"])))
    derived = derive_fields(bars, spread_prints)
    key_group = f"public:{venue}"
    pack = _base_pack()
    pack.update(
        {
            "attempts": attempts,
            "auris_inputs": derived["auris_inputs"],
            "bar_count": len(bars),
            "bars": bars,
            "capture": capture,
            "dropped_incomplete_bar": True,
            "evidence_tag": "measured",
            "fetched_at": fetched_at,
            "fields": derived["fields"],
            "files": {
                "bars_csv": RELATIVE_CSV,
                "json": RELATIVE_JSON,
                "markdown": RELATIVE_MD,
                "spread_csv": RELATIVE_SPREAD_CSV if spread_prints else None,
            },
            "interval": "1h",
            "interval_seconds": INTERVAL_SECONDS,
            "key_group": key_group,
            "parser": parser,
            "provenance": {
                "authenticated": False,
                "fetched_at": fetched_at,
                "generator": "aureon.evaluation.market_series",
                "key_group": key_group,
                "key_material": "none",
                "orders": "none",
            },
            "source": source,
            "spread_prints": spread_prints,
            "spread_source": spread_source,
            "spread_time_range": _spread_range(spread_prints),
            "symbol": symbol,
            "time_range": _time_range(bars),
            "venue": venue,
            "venue_interval": venue_interval,
            "verdict": "loaded",
        }
    )
    return pack


def hold_receipt(reason: str, attempts: list[dict[str, Any]], fetched_at: str | None = None) -> dict[str, Any]:
    """An honest skip. No prices are filled in."""

    pack = _base_pack()
    pack.update(
        {
            "attempts": attempts,
            "auris_inputs": {},
            "bar_count": 0,
            "bars": [],
            "fetched_at": fetched_at or _now_iso(),
            "fields": {},
            "provenance": {
                "authenticated": False,
                "fetched_at": fetched_at or _now_iso(),
                "generator": "aureon.evaluation.market_series",
                "key_group": None,
                "key_material": "none",
                "orders": "none",
            },
            "reason": reason,
            "spread_prints": [],
            "verdict": "HOLD",
        }
    )
    return pack


def _json_body(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _finish_attempt(base: dict[str, Any], venue: str, endpoint: str, *, used: bool) -> dict[str, Any]:
    done = dict(base)
    done["venue"] = venue
    done["endpoint"] = endpoint
    done["used"] = used
    return done


def fetch_public_pack(transport: Transport | None = None, *, fetched_at: str | None = None) -> dict[str, Any]:
    """Fetch one public series. `transport` is the HTTP GET, so tests stay offline."""

    get = transport or http_get
    stamp = fetched_at or _now_iso()
    attempts: list[dict[str, Any]] = []
    binance_url = (
        f"{_BINANCE_KLINES}?symbol={_BINANCE_SYMBOL}&interval=1h&limit={CLOSED_BARS + 1}"
    )
    binance_call, binance_body = _call(get, binance_url)
    binance_bars: list[dict[str, Any]] = []
    parsed_ok = False
    if binance_body is not None:
        try:
            binance_bars = _parse_binance_klines(_json_body(binance_body))
            parsed_ok = True
        except (UnicodeDecodeError, json.JSONDecodeError):
            binance_call = dict(binance_call)
            binance_call["error"] = "JSONDecodeError"
            binance_body = None
    closed, _dropped = _closed_window(binance_bars)
    if parsed_ok and binance_body is not None and len(closed) >= MIN_CLOSED_BARS:
        attempts.append(_finish_attempt(binance_call, "binance", _BINANCE_KLINES, used=True))
        book_url = f"{_BINANCE_BOOK}?symbol={_BINANCE_SYMBOL}"
        book_call, book_body = _call(get, book_url)
        prints: list[dict[str, Any]] = []
        observed = _iso_unix(stamp)
        if book_body is not None:
            try:
                prints = _parse_binance_book(_json_body(book_body), observed)
                book_error = None if prints else "no bid/ask"
            except (UnicodeDecodeError, json.JSONDecodeError):
                book_error = "JSONDecodeError"
                book_body = None
        else:
            book_error = book_call.get("error")
        book_attempt = _finish_attempt(book_call, "binance", _BINANCE_BOOK, used=bool(prints))
        if book_error and not prints:
            book_attempt["error"] = book_error
            book_attempt["used"] = False
        attempts.append(book_attempt)
        capture = {"ohlc_bytes": len(binance_body), "ohlc_sha256": _sha256(binance_body)}
        if book_body is not None and prints:
            capture["spread_bytes"] = len(book_body)
            capture["spread_sha256"] = _sha256(book_body)
        return assemble_pack(
            venue="binance",
            symbol=_BINANCE_SYMBOL,
            source=_BINANCE_KLINES,
            spread_source=_BINANCE_BOOK if prints else None,
            venue_interval="1h",
            bars=closed,
            spread_prints=prints,
            attempts=attempts,
            capture=capture,
            fetched_at=stamp,
            parser="binance-klines-v1",
        )
    attempts.append(_finish_attempt(binance_call, "binance", _BINANCE_KLINES, used=False))
    if binance_body is not None and not parsed_ok:
        pass
    elif binance_body is not None and len(closed) < MIN_CLOSED_BARS:
        attempts[-1]["error"] = "fewer than 10 closed bars"

    kraken_url = f"{_KRAKEN_OHLC}?pair={_KRAKEN_PAIR}&interval=60"
    kraken_call, kraken_body = _call(get, kraken_url)
    kraken_bars: list[dict[str, Any]] = []
    if kraken_body is not None:
        try:
            kraken_bars = _parse_kraken_ohlc(_json_body(kraken_body))
        except (UnicodeDecodeError, json.JSONDecodeError):
            kraken_call = dict(kraken_call)
            kraken_call["error"] = "JSONDecodeError"
            kraken_body = None
    closed, _dropped = _closed_window(kraken_bars)
    if kraken_body is None or len(closed) < MIN_CLOSED_BARS:
        attempts.append(_finish_attempt(kraken_call, "kraken", _KRAKEN_OHLC, used=False))
        if kraken_body is not None and attempts[-1]["error"] is None:
            attempts[-1]["error"] = "fewer than 10 closed bars"
        return hold_receipt(
            "public fetch did not return a closed bar series; no prices were invented",
            attempts,
            stamp,
        )
    attempts.append(_finish_attempt(kraken_call, "kraken", _KRAKEN_OHLC, used=True))
    spread_url = f"{_KRAKEN_SPREAD}?pair={_KRAKEN_PAIR}"
    spread_call, spread_body = _call(get, spread_url)
    prints = []
    if spread_body is not None:
        try:
            prints = _parse_kraken_spread(_json_body(spread_body))
            spread_error = None if prints else "no bid/ask"
        except (UnicodeDecodeError, json.JSONDecodeError):
            spread_error = "JSONDecodeError"
            spread_body = None
    else:
        spread_error = spread_call.get("error")
    spread_attempt = _finish_attempt(spread_call, "kraken", _KRAKEN_SPREAD, used=bool(prints))
    if spread_error and not prints:
        spread_attempt["error"] = spread_error
        spread_attempt["used"] = False
    attempts.append(spread_attempt)
    capture = {"ohlc_bytes": len(kraken_body), "ohlc_sha256": _sha256(kraken_body)}
    if spread_body is not None and prints:
        capture["spread_bytes"] = len(spread_body)
        capture["spread_sha256"] = _sha256(spread_body)
    return assemble_pack(
        venue="kraken",
        symbol=_KRAKEN_PAIR,
        source=_KRAKEN_OHLC,
        spread_source=_KRAKEN_SPREAD if prints else None,
        venue_interval="60",
        bars=closed,
        spread_prints=prints,
        attempts=attempts,
        capture=capture,
        fetched_at=stamp,
        parser="kraken-ohlc-v1",
    )


def _iso_unix(stamp: str) -> int:
    parsed = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    return int(parsed.timestamp())


def _same(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    left_num = _finite(left)
    right_num = _finite(right)
    if left_num is None or right_num is None:
        return left == right
    return left_num == right_num


def verify_pack(pack: dict[str, Any]) -> list[str]:
    """Recompute the Auris inputs from the stored bars. A HOLD receipt has nothing to recompute."""

    if not isinstance(pack, dict):
        return ["market series pack is not an object"]
    if pack.get("schema") != SCHEMA:
        return [f"schema is {pack.get('schema')!r}"]
    if pack.get("verdict") != "loaded":
        return []
    problems: list[str] = []
    if pack.get("orders_placed") is not False or pack.get("live_trading") is not False:
        problems.append("pack claims trading that this fetcher cannot do")
    if pack.get("authenticated") is not False or pack.get("key_material") != "none":
        problems.append("pack is not a public unauthenticated series")
    key_group = pack.get("key_group")
    if key_group not in {"public:binance", "public:kraken"}:
        problems.append("key group is not a public venue label")
    provenance = pack.get("provenance") if isinstance(pack.get("provenance"), dict) else {}
    if provenance.get("key_group") != key_group:
        problems.append("provenance key group does not match the pack")
    bars = pack.get("bars")
    prints = pack.get("spread_prints")
    if not isinstance(bars, list) or not isinstance(prints, list):
        return problems + ["bars or spread prints are missing"]
    if len(bars) < MIN_CLOSED_BARS:
        problems.append("fewer than 10 closed bars")
    derived = derive_fields(bars, prints)
    stored_inputs = pack.get("auris_inputs") if isinstance(pack.get("auris_inputs"), dict) else None
    if stored_inputs is None:
        problems.append("auris inputs are missing")
    else:
        if set(stored_inputs) != set(derived["auris_inputs"]):
            problems.append("auris inputs do not match the bars and spread prints")
        else:
            for key, value in derived["auris_inputs"].items():
                if not _same(stored_inputs.get(key), value):
                    problems.append(f"auris input {key} does not match the series")
    stored_fields = pack.get("fields") if isinstance(pack.get("fields"), dict) else {}
    for key, field in derived["fields"].items():
        stored = stored_fields.get(key)
        if not isinstance(stored, dict) or not _same(stored.get("value"), field.get("value")):
            problems.append(f"field {key} does not match the series")
        elif stored.get("evidence_tag") != "measured":
            problems.append(f"field {key} is not tagged measured")
    leaks = _leaks(_dumps(pack))
    problems.extend(leaks)
    return problems


def _leaks(blob: str) -> list[str]:
    folded = blob.casefold()
    problems = [f"pack text contains {token}" for token in _FORBIDDEN_TEXT if token in folded]
    for name, value in os.environ.items():
        upper = name.upper()
        if not any(marker in upper for marker in _ENV_MARKERS):
            continue
        if value and len(value) >= 8 and value in blob:
            problems.append(f"pack text contains the value of env {name}")
    return problems


def load_market_series(root: Path) -> dict[str, Any]:
    """Load the committed pack. This does not fetch. A bad pack becomes HOLD."""

    path = Path(root) / RELATIVE_JSON
    if not path.is_file():
        return hold_receipt(
            "reports/measured/market_series.json is not in this checkout",
            [],
        ) | {"verdict": "absent", "path": RELATIVE_JSON}
    try:
        pack = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return hold_receipt("market series pack is not readable json", []) | {"path": RELATIVE_JSON}
    if not isinstance(pack, dict):
        return hold_receipt("market series pack is not an object", []) | {"path": RELATIVE_JSON}
    problems = verify_pack(pack)
    if problems:
        receipt = hold_receipt("; ".join(problems), list(pack.get("attempts") or []))
        receipt["path"] = RELATIVE_JSON
        receipt["verify"] = problems
        return receipt
    loaded = dict(pack)
    loaded["path"] = RELATIVE_JSON
    return loaded


def series_summary(pack: dict[str, Any]) -> dict[str, Any]:
    """The brain-proof slice. Bars stay in the pack file."""

    return {
        "authenticated": pack.get("authenticated"),
        "bar_count": pack.get("bar_count"),
        "evidence_tag": pack.get("evidence_tag"),
        "fetched_at": pack.get("fetched_at"),
        "interval": pack.get("interval"),
        "key_group": pack.get("key_group"),
        "key_material": pack.get("key_material"),
        "live_trading": False,
        "orders_placed": False,
        "path": pack.get("path") or RELATIVE_JSON,
        "reason": pack.get("reason"),
        "source": pack.get("source"),
        "spread_source": pack.get("spread_source"),
        "spread_time_range": pack.get("spread_time_range"),
        "symbol": pack.get("symbol"),
        "time_range": pack.get("time_range"),
        "venue": pack.get("venue"),
        "verdict": pack.get("verdict"),
    }


def render_market_markdown(pack: dict[str, Any]) -> str:
    time_range = pack.get("time_range") or {}
    spread_range = pack.get("spread_time_range") or {}
    fields = pack.get("fields") or {}
    lines = [
        "# Public market series",
        "",
        "Read-only bars for the brain proof. No exchange key was read. No order was sent. "
        "Live autonomy stays off. This is not a claim that the system is conscious or alive.",
        "",
        f"Verdict: **{pack.get('verdict')}**. Evidence tag `{pack.get('evidence_tag')}`.",
        f"Key group `{pack.get('key_group')}`. Key material `{pack.get('key_material')}`.",
        (
            f"Source `{pack.get('source')}` symbol `{pack.get('symbol')}` "
            f"interval `{pack.get('interval')}` venue interval `{pack.get('venue_interval')}`."
        ),
        (
            f"OHLC time range `{time_range.get('start')}` to `{time_range.get('end')}` "
            f"({pack.get('bar_count')} closed bars). {time_range.get('clock', '')}"
        ),
        (
            f"Spread source `{pack.get('spread_source')}`. "
            f"Spread time range `{spread_range.get('start')}` to `{spread_range.get('end')}` "
            f"({spread_range.get('prints')} prints). {spread_range.get('note', '')}"
        ),
        "The last venue bar is dropped because the public candle response includes the in-progress bar.",
        "",
        "Fetch attempts, public endpoints only:",
    ]
    for attempt in pack.get("attempts") or []:
        lines.append(
            f"- `{attempt.get('venue')}` `{attempt.get('endpoint')}` "
            f"status `{attempt.get('http_status')}` used `{attempt.get('used')}` "
            f"error `{attempt.get('error')}`."
        )
    lines.extend(
        [
            "",
            "Auris inputs are one window texture, not a substitute for a missing node:",
        ]
    )
    for name in ("volatility", "momentum", "volume", "spread"):
        field = fields.get(name) or {}
        lines.append(
            f"- `{name}` `{field.get('value')}` tag `{field.get('evidence_tag')}`. "
            f"{field.get('definition', 'not supplied')}. Clock: {field.get('clock', 'n/a')}."
        )
    lines.extend(
        [
            "",
            "Per-bar `range_fraction` and `return` are on the bars. The first bar has no return. "
            "Nothing missing is filled with zero.",
            "Trade-outcome labels: **HOLD**. Signal-in-noise labels: **HOLD**. Release boundary: **HOLD**.",
            "",
            "JSON is the harness input. The CSV files are the same bars and the same spread prints.",
            "",
            "Live fetch, public endpoints only:",
            "",
            "```bash",
            "AUREON_DISABLE_REAL_ORDERS=1 PYTHONPATH=. python3 -m aureon.evaluation.market_series --out reports/measured",
            "```",
            "",
            "Check the file already on disk, without fetching:",
            "",
            "```bash",
            "PYTHONPATH=. python3 -m aureon.evaluation.market_series --check --out reports/measured",
            "```",
            "",
        ]
    )
    if pack.get("reason"):
        lines.insert(4, f"Reason: {pack['reason']}")
        lines.insert(5, "")
    return "\n".join(lines)


def _write_bars_csv(path: Path, bars: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["open_time", "open", "high", "low", "close", "volume", "range_fraction", "return"]
        )
        for bar in bars:
            writer.writerow(
                [
                    bar.get("open_time"),
                    bar.get("open"),
                    bar.get("high"),
                    bar.get("low"),
                    bar.get("close"),
                    bar.get("volume"),
                    bar.get("range_fraction"),
                    "" if "return" not in bar else bar.get("return"),
                ]
            )


def _write_spread_csv(path: Path, prints: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "bid", "ask", "spread"])
        for item in prints:
            writer.writerow([item.get("time"), item.get("bid"), item.get("ask"), item.get("spread")])


def write_pack(out: Path, pack: dict[str, Any]) -> dict[str, Any]:
    """Write JSON, CSV, and markdown. Refuses a blob that carries key material."""

    out.mkdir(parents=True, exist_ok=True)
    text = _dumps(pack)
    leaks = _leaks(text)
    if leaks:
        pack = hold_receipt(
            "refused to write the pack because it failed the redaction check: " + "; ".join(leaks),
            list(pack.get("attempts") or []),
            pack.get("fetched_at"),
        )
        text = _dumps(pack)
    (out / "market_series.json").write_text(text, encoding="utf-8")
    (out / "market_series.md").write_text(render_market_markdown(pack), encoding="utf-8")
    bars = pack.get("bars") if isinstance(pack.get("bars"), list) else []
    prints = pack.get("spread_prints") if isinstance(pack.get("spread_prints"), list) else []
    if pack.get("verdict") == "loaded" and bars:
        _write_bars_csv(out / "market_series.csv", bars)
    else:
        stale = out / "market_series.csv"
        if stale.is_file():
            stale.unlink()
    if pack.get("verdict") == "loaded" and prints:
        _write_spread_csv(out / "market_spread.csv", prints)
    else:
        stale_spread = out / "market_spread.csv"
        if stale_spread.is_file():
            stale_spread.unlink()
    return pack


def _repo_root(out: Path) -> Path:
    """`--out reports/measured` is the pack directory. The loader wants the repo root."""

    resolved = out.resolve()
    if resolved.name == "measured" and resolved.parent.name == "reports":
        return resolved.parent.parent
    if (resolved / "reports" / "measured" / "market_series.json").is_file():
        return resolved
    return resolved


def _summary_line(pack: dict[str, Any]) -> str:
    if pack.get("verdict") != "loaded":
        return f"market series HOLD {pack.get('reason')}"
    window = pack.get("time_range") or {}
    return (
        f"market series loaded {pack.get('key_group')} {pack.get('symbol')} "
        f"{pack.get('interval')} bars={pack.get('bar_count')} "
        f"{window.get('start')} {window.get('end')} orders=none"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a public OHLCV and spread series. No key. No order."
    )
    parser.add_argument("--out", type=Path, default=Path("reports/measured"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Recompute the pack at --out and do not fetch.",
    )
    args = parser.parse_args(argv)
    if args.check:
        pack = load_market_series(_repo_root(args.out))
        print(_summary_line(pack))
        return 0 if pack.get("verdict") == "loaded" else 2
    pack = fetch_public_pack()
    problems = verify_pack(json.loads(_dumps(pack)))
    if pack.get("verdict") == "loaded" and problems:
        pack = hold_receipt("pack failed verification: " + "; ".join(problems), list(pack.get("attempts") or []))
    written = write_pack(args.out, pack)
    print(_summary_line(written))
    return 0 if written.get("verdict") == "loaded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
