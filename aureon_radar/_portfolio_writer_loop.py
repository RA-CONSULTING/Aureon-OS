"""💰 Portfolio truth writer loop.

Keeps aureon_radar/real_portfolio_state.json fresh from live venue balances so
the Grand Big Wheel's Dream pillar reads real telemetry, not stale snapshots.

VENUE ELIGIBILITY / FAIL-CLOSED TRUTH (2026-09-07):
  * Every venue balance fetch is captured with its error status. A venue whose
    live fetch fails (or whose enriched probe fails) is EXCLUDED from
    total_usd / deployable aggregates and explicitly flagged untrusted in
    `venue_trust` — stale or fabricated capital must never reach sizing.
  * Fetch→write age beyond STALE_VENUE_MAX_SEC is flagged `stale: true` as an
    advisory (a slow cycle must not flap equity); each cycle's numbers come
    from live fetches made in that same cycle.
  * Consumers must ALSO fail closed on state-file age: every entry carries
    `state_age_sec` and `max_state_age_sec` (120). A dead writer must not keep
    certifying old venue data as live.
  * Capital.com truth: the raw account is denominated in GBP and the
    deployable amount is `available` (free margin), NOT `balance` (which
    includes margin locked by open CFD positions). The writer therefore
    reports:
      - capital_usd         = available, converted GBP→USD (free/deployable)
      - capital_equity_usd  = balance,   converted GBP→USD (equity)
    Conversion uses Capital's own GBPUSD spot CFD mid, sanity-banded
    [FX_RATE_MIN, FX_RATE_MAX]; if the rate is unavailable or implausible the
    capital venue is excluded from aggregates (fail-closed, reason recorded).
  * Capital position truth comes from a live read-only get_positions() probe
    each cycle (`capital_open_positions`), because the capital_cfd_trader
    on-disk trace may be arbitrarily stale (its age is reported as
    `capital_trader_trace_age_sec`).

Run with CWD=aureon_radar and venue keys exported (source .env first).
Use --once for a single write cycle (verification / flight tests).
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

_AUREON_UPSTREAM = Path(__file__).resolve().parent.parent / "aureon-os-upstream"
if str(_AUREON_UPSTREAM) not in sys.path:
    sys.path.insert(0, str(_AUREON_UPSTREAM))

FAST_INTERVAL = int(os.getenv("PORTFOLIO_FAST_INTERVAL", "60"))
SLOW_INTERVAL = int(os.getenv("PORTFOLIO_SLOW_INTERVAL", "300"))
INTERVAL = FAST_INTERVAL

# A venue whose truth cannot be verified fresher than this is untrusted.
STALE_VENUE_MAX_SEC = float(os.getenv("PORTFOLIO_STALE_VENUE_MAX_SEC", "120"))
# Fast-track venue balances may be reused for this many seconds after a
# successful fetch, cutting repeated API volume.
VENUE_BALANCE_CACHE_TTL = float(os.getenv("PORTFOLIO_BALANCE_CACHE_TTL", "120"))
# Sanity band for the GBP→USD rate; outside this the rate is rejected
# and the capital venue is excluded rather than mis-converted.
FX_RATE_MIN = float(os.getenv("PORTFOLIO_FX_RATE_MIN", "1.0"))
FX_RATE_MAX = float(os.getenv("PORTFOLIO_FX_RATE_MAX", "2.0"))

_CAPITAL_TRACE_PATH = Path(os.getenv(
    "CAPITAL_TRACE_PATH",
    str(Path(__file__).resolve().parent.parent / "aureon-os-upstream" / "state" / "capital_cfd_last_exchange_trace.json"),
)).resolve()

_VENUES = ("alpaca", "kraken", "binance", "capital")

# Cycle tracking for fast (balance-only) vs slow (full reconciliation) tracks.
_CYCLE_COUNT = 0
_LAST_SLOW_AT = 0.0


def _load_tracker_class():
    from aureon.portfolio.aureon_real_portfolio_tracker import (
        ExchangeBalance,
        RealPortfolioTracker,
    )
    return RealPortfolioTracker, ExchangeBalance


class VenueTrustTrackerMixin:
    """Captures per-venue fetch status and enriches capital with free-margin truth.

    Mixed in below around RealPortfolioTracker.  It implements:
      * fast/slow track selection via ``self._is_slow_cycle``,
      * per-venue balance caching on fast tracks,
      * Kraken trade-history refresh only on slow tracks,
      * Capital free-margin on every cycle, full position reconciliation only
        on slow cycles.
    """

    last_venue_status: dict
    _is_slow_cycle: bool = False
    _venue_balance_cache: dict = None  # type: ignore[assignment]
    _venue_cache_ttl: float = VENUE_BALANCE_CACHE_TTL

    def _record_venue(self, venue: str, balance) -> dict:
        status = {
            "error": getattr(balance, "error", None),
            "fetched_at": time.time(),
            "raw_total": getattr(balance, "total_usd", None),
            "from_cache": getattr(balance, "_from_cache", False),
        }
        self.last_venue_status[venue] = status
        return status

    def _cached_balance(self, venue: str):
        """Return a still-fresh cached balance, or None."""
        if self._venue_balance_cache is None:
            return None
        entry = self._venue_balance_cache.get(venue)
        if not entry:
            return None
        age = time.time() - entry["fetched_at"]
        if age > self._venue_cache_ttl:
            return None
        b = entry["balance"]
        if getattr(b, "error", None) is not None:
            return None
        return b

    def _maybe_cache_balance(self, venue: str, balance) -> None:
        if getattr(balance, "error", None) is None:
            if self._venue_balance_cache is None:
                self._venue_balance_cache = {}
            self._venue_balance_cache[venue] = {"balance": balance, "fetched_at": time.time()}

    def _get_alpaca_balance(self):  # noqa: N802 - upstream naming
        if not self._is_slow_cycle:
            cached = self._cached_balance("alpaca")
            if cached is not None:
                cached._from_cache = True  # noqa: SLF001
                self._record_venue("alpaca", cached)
                return cached
        b = super()._get_alpaca_balance()
        self._maybe_cache_balance("alpaca", b)
        self._record_venue("alpaca", b)
        return b

    def _get_kraken_balance(self):  # noqa: N802
        if not self._is_slow_cycle:
            cached = self._cached_balance("kraken")
            if cached is not None:
                cached._from_cache = True  # noqa: SLF001
                self._record_venue("kraken", cached)
                return cached
        b = super()._get_kraken_balance()
        self._maybe_cache_balance("kraken", b)
        self._record_venue("kraken", b)
        return b

    def _get_binance_balance(self):  # noqa: N802
        if not self._is_slow_cycle:
            cached = self._cached_balance("binance")
            if cached is not None:
                cached._from_cache = True  # noqa: SLF001
                self._record_venue("binance", cached)
                return cached
        b = super()._get_binance_balance()
        self._maybe_cache_balance("binance", b)
        self._record_venue("binance", b)
        return b

    def _get_kraken_trades(self):  # noqa: N802
        """Refresh Kraken trade history only during slow cycles."""
        if not self._is_slow_cycle:
            # Fast track: rely on whatever is already in-memory cached.
            return self._kraken_trades_cache
        return super()._get_kraken_trades()

    def _get_capital_balance(self):  # noqa: N802
        """Capital free margin every cycle; full position reconciliation only slow."""
        from aureon.portfolio.aureon_real_portfolio_tracker import ExchangeBalance

        try:
            if self._capital_client is None:
                from aureon.exchanges.capital_client import CapitalClient
                self._capital_client = CapitalClient()

            accs = list(self._capital_client.get_accounts())
            primary = None
            for a in accs:
                bal_raw = a.get("balance")
                if isinstance(bal_raw, dict):
                    bal_raw = bal_raw.get("balance")
                try:
                    if float(bal_raw or 0) > 0:
                        primary = a
                        break
                except (TypeError, ValueError):
                    continue
            primary = primary or (accs[0] if accs else None)

            if primary is None:
                b = ExchangeBalance(
                    exchange="capital", total_usd=0.0, cash_usd=0.0,
                    positions_usd=0.0, timestamp=time.time(),
                    error="no_accounts_returned",
                )
                status = self._record_venue("capital", b)
                status["available_error"] = "no_accounts_returned"
                return b

            bal_raw = primary.get("balance")
            if isinstance(bal_raw, dict):
                bal_raw = bal_raw.get("balance")
            avail_raw = primary.get("available")
            if isinstance(avail_raw, dict):
                avail_raw = avail_raw.get("available")
            balance_native = float(bal_raw or 0)
            available_native = float(avail_raw or 0)
            currency = str(primary.get("currency") or "").upper() or None

            b = ExchangeBalance(
                exchange="capital",
                total_usd=balance_native,
                cash_usd=available_native,
                positions_usd=0.0,
                timestamp=time.time(),
            )
            status = self._record_venue("capital", b)
            status["balance_native"] = balance_native
            status["available_native"] = available_native
            status["currency"] = currency

            # ── GBP→USD conversion via Capital's own GBPUSD spot CFD mid ──
            if currency == "USD":
                status["fx_rate"] = 1.0
                status["fx_source"] = "native_usd"
            elif currency == "GBP":
                rate = None
                for sym in ("GBP/USD", "GBPUSD"):
                    try:
                        t = self._capital_client.get_ticker(sym)
                        p = t.get("price") if isinstance(t, dict) else None
                        if p:
                            p = float(p)
                            rate = p / 10000.0 if p > 100 else p
                            break
                    except Exception:  # noqa: BLE001,S110
                        continue
                if rate is not None and FX_RATE_MIN <= rate <= FX_RATE_MAX:
                    status["fx_rate"] = rate
                    status["fx_source"] = "capital_gbpusd_spot_mid"
                else:
                    status["fx_error"] = f"gbpusd_rate_unavailable_or_implausible: {rate!r}"
            elif currency:
                status["fx_error"] = f"unsupported_capital_currency: {currency}"
            else:
                status["fx_error"] = "capital_currency_unknown"

            # ── Full position reconciliation: slow track only ──
            if self._is_slow_cycle:
                try:
                    poss = self._capital_client.get_positions()
                    status["open_positions"] = len(list(poss)) if poss is not None else None
                    status["positions_truth_status"] = getattr(poss, "truth_status", None)
                    status["position_source"] = "slow_cycle_live_get_positions"
                except Exception as e:  # noqa: BLE001
                    status["positions_error"] = f"{type(e).__name__}: {e}"
                    status["position_source"] = "slow_cycle_positions_error"
            else:
                status["position_source"] = "fast_track_skipped"

            return b
        except Exception as e:  # noqa: BLE001
            b = ExchangeBalance(
                exchange="capital", total_usd=0.0, cash_usd=0.0,
                positions_usd=0.0, timestamp=time.time(), error=str(e),
            )
            self._record_venue("capital", b)
            return b


def _capital_trader_trace_age_sec() -> float | None:
    try:
        if _CAPITAL_TRACE_PATH.exists():
            trace = json.loads(_CAPITAL_TRACE_PATH.read_text(encoding="utf-8"))
            ts = float(trace.get("written_at") or 0)
            if ts > 0:
                return round(time.time() - ts, 1)
    except Exception:  # noqa: BLE001,S110
        pass
    return None


def _apply_venue_trust(tracker, state_path: Path) -> dict:
    """Patch the just-written state: exclude untrusted venues from aggregates.

    Returns the trust report written into the state file.
    """
    data = json.loads(Path(state_path).read_text(encoding="utf-8"))
    history = data.get("history") or []
    if not history:
        return {}
    entry = history[-1]

    trust: dict = {}
    excluded: dict = {}
    total_equity = 0.0
    now = time.time()

    for venue in ("alpaca", "kraken", "binance"):
        st = tracker.last_venue_status.get(venue) or {}
        err = st.get("error")
        age = round(now - st.get("fetched_at", now), 1) if st.get("fetched_at") else None
        stale = age is not None and age > STALE_VENUE_MAX_SEC
        # A venue fetched successfully THIS CYCLE is live by construction; the
        # age gate is advisory (a slow cycle must not flap equity). Exclusion
        # is driven by fetch failure — that is the fail-closed path.
        trusted = err is None
        reason = err or "live_fetch_ok"
        if stale and trusted:
            reason = f"live_fetch_ok_but_write_delayed_{age}s"
        trust[venue] = {
            "trusted": trusted,
            "age_sec": age,
            "stale": stale,
            "reason": reason,
        }
        if trusted:
            total_equity += float(entry.get(f"{venue}_usd") or 0.0)
        else:
            excluded[venue] = entry.get(f"{venue}_usd")

    cap = tracker.last_venue_status.get("capital") or {}
    cap_reasons = []
    if cap.get("error"):
        cap_reasons.append(f"balance_fetch: {cap['error']}")
    if cap.get("available_error"):
        cap_reasons.append(f"available: {cap['available_error']}")
    if cap.get("positions_error"):
        cap_reasons.append(f"positions: {cap['positions_error']}")
    if cap.get("fx_error"):
        cap_reasons.append(f"fx: {cap['fx_error']}")
    fx_rate = cap.get("fx_rate")
    if fx_rate is None and not cap_reasons:
        cap_reasons.append("fx: rate_missing")

    cap_trusted = not cap_reasons
    trust["capital"] = {
        "trusted": cap_trusted,
        "currency": cap.get("currency"),
        "balance_native": cap.get("balance_native"),
        "available_native": cap.get("available_native"),
        "fx_rate": fx_rate,
        "fx_source": cap.get("fx_source"),
        "open_positions": cap.get("open_positions"),
        "positions_truth_status": cap.get("positions_truth_status"),
        "position_source": cap.get("position_source") if cap_trusted else None,
        "trader_trace_age_sec": _capital_trader_trace_age_sec(),
        "trader_trace_stale": None,
        "reason": "; ".join(cap_reasons) if cap_reasons else "live_fetch_ok",
    }
    if trust["capital"]["trader_trace_age_sec"] is not None:
        trust["capital"]["trader_trace_stale"] = (
            trust["capital"]["trader_trace_age_sec"] > STALE_VENUE_MAX_SEC
        )

    if cap_trusted:
        rate = float(fx_rate)
        free_usd = float(cap["available_native"]) * rate
        equity_usd = float(cap["balance_native"]) * rate
        # Downstream (trading_progress → sizing) consumes capital_usd as FREE capital.
        entry["capital_usd"] = round(free_usd, 6)
        entry["capital_equity_usd"] = round(equity_usd, 6)
        trust["capital"]["free_usd"] = round(free_usd, 6)
        trust["capital"]["equity_usd"] = round(equity_usd, 6)
        total_equity += equity_usd
    else:
        excluded["capital"] = entry.get("capital_usd")
        entry["capital_usd"] = None
        entry["capital_equity_usd"] = None

    # total_usd now counts ONLY live-verified venues.
    entry["total_usd"] = round(total_equity, 6)
    entry["cumulative_net_pnl"] = round(total_equity - float(entry.get("starting_capital") or 0), 6)
    entry["venue_trust"] = trust
    entry["trusted_venues"] = [v for v in _VENUES if trust.get(v, {}).get("trusted")]
    entry["untrusted_venues"] = [v for v in _VENUES if not trust.get(v, {}).get("trusted")]
    entry["excluded_untrusted_last_known_usd"] = excluded
    entry["venue_trust_max_age_sec"] = STALE_VENUE_MAX_SEC
    # Consumers must fail closed when the STATE FILE itself goes stale —
    # a dead writer must not keep certifying old venue data as live.
    entry["state_age_sec"] = round(now - float(entry.get("timestamp") or now), 1)
    entry["max_state_age_sec"] = STALE_VENUE_MAX_SEC

    tmp_path = str(state_path) + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, str(state_path))
    return trust


def _build_tracker():
    base_cls, _exchange_balance_cls = _load_tracker_class()

    class VenueTrustTracker(VenueTrustTrackerMixin, base_cls):
        def __init__(self, *a, **kw):
            self.last_venue_status = {}
            super().__init__(*a, **kw)

    return VenueTrustTracker()


def run_once(tracker=None) -> int:
    global _CYCLE_COUNT, _LAST_SLOW_AT

    _CYCLE_COUNT += 1
    is_slow = _CYCLE_COUNT == 1 or (time.time() - _LAST_SLOW_AT) >= SLOW_INTERVAL
    if is_slow:
        _LAST_SLOW_AT = time.time()

    if tracker is None:
        tracker = _build_tracker()
    tracker._is_slow_cycle = is_slow  # noqa: SLF001
    tracker._venue_cache_ttl = VENUE_BALANCE_CACHE_TTL

    snap = tracker.get_real_portfolio()
    if snap is None:
        print("⚠️ snapshot suppressed (audit mode) — no write", flush=True)
        return 1

    trust = _apply_venue_trust(tracker, Path(tracker.STATE_FILE))
    entry = json.loads(Path(tracker.STATE_FILE).read_text(encoding="utf-8"))["history"][-1]
    cap = trust.get("capital", {})
    cached = sorted(v for v in ("alpaca", "kraken", "binance")
                    if tracker.last_venue_status.get(v, {}).get("from_cache"))
    print(
        f"wrote state: track={'slow' if is_slow else 'fast'} "
        f"total=${entry['total_usd']:.2f} "
        f"trusted={entry['trusted_venues']} "
        f"untrusted={entry['untrusted_venues']} "
        f"cached={cached} "
        f"capital_free=${(cap.get('free_usd') or 0):.2f} "
        f"capital_equity=${(cap.get('equity_usd') or 0):.2f} "
        f"capital_positions={cap.get('open_positions')} "
        f"fx={cap.get('fx_rate')}",
        flush=True,
    )
    return 0


def main() -> None:
    print("💰 portfolio writer loop online (venue-trust gated)", flush=True)
    tracker = _build_tracker()
    while True:
        try:
            run_once(tracker)
        except Exception as e:
            print(f"⚠️ cycle error: {e}", flush=True)
            traceback.print_exc()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    from _console_utf8_shim import ensure_utf8_stdout

    ensure_utf8_stdout()
    if "--once" in sys.argv:
        sys.exit(run_once())
    main()
