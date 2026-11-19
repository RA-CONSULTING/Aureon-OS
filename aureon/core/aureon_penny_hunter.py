#!/usr/bin/env python3
"""
aureon_penny_hunter.py — Hunt pennies on Capital.com. Fast. Autonomous.

This is the simplest, most direct trading loop:
1. Authenticate to Capital.com
2. Check what's moving
3. Open minimum positions in the direction of momentum
4. Close at ANY profit (even £0.001)
5. Repeat

No fear. No waiting. Just hunt pennies until they become pounds.
The 1.88% law is for the big plays. This is the penny engine.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]

log = logging.getLogger("aureon.penny_hunter")

# Load .env
try:
    env_path = _REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
except Exception:
    pass

try:
    import requests
except ImportError:
    requests = None


# Instruments to hunt — liquid, tight spreads
from datetime import datetime, timezone

def _is_market_open(market_type: str) -> bool:
    """Check if a market is currently open."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    weekday = now.weekday()  # 0=Mon, 6=Sun

    if market_type == "crypto":
        return True  # 24/7/365

    if market_type == "forex":
        # Forex: Sun 22:00 UTC to Fri 22:00 UTC
        if weekday == 6 and hour < 22:
            return False  # Sunday before open
        if weekday == 5 and hour >= 22:
            return False  # Saturday after close
        if weekday == 5:
            return False  # Saturday
        return True

    if market_type == "us_stocks":
        # US stocks: Mon-Fri 14:30-21:00 UTC (9:30-4:00 ET)
        if weekday >= 5:
            return False
        return 14 <= hour < 21

    if market_type == "uk_stocks":
        # UK/EU: Mon-Fri 08:00-16:30 UTC
        if weekday >= 5:
            return False
        return 8 <= hour < 17

    if market_type == "gold":
        # Gold CFD: Sun 23:00 - Fri 22:00 UTC (near 24/5)
        if weekday == 5 and hour >= 22:
            return False
        if weekday == 6 and hour < 23:
            return False
        return True

    return True  # Default: assume open


# Capital.com instruments with market type
HUNT_LIST = [
    {"epic": "GOLD", "name": "Gold", "min_size": 0.1, "market": "gold"},
    {"epic": "US100", "name": "US Tech 100", "min_size": 0.5, "market": "us_stocks"},
    {"epic": "US500", "name": "US 500", "min_size": 0.5, "market": "us_stocks"},
    {"epic": "UK100", "name": "UK 100", "min_size": 0.5, "market": "uk_stocks"},
    {"epic": "EURUSD", "name": "EUR/USD", "min_size": 1000, "market": "forex"},
    {"epic": "GBPUSD", "name": "GBP/USD", "min_size": 1000, "market": "forex"},
]

# Kraken crypto pairs (24/7)
KRAKEN_PAIRS = ["XBTUSD", "ETHUSD", "XRPUSD", "SOLUSD"]

# Named US symbols. Not a signal and not an order list.

BASE_URL = "https://api-capital.backend-capital.com"
MAX_POSITIONS = 3
TAKE_PROFIT_GBP = 0.02  # Take profit above spread cost — 2p minimum
MAX_LOSS_GBP = -999.0   # NEVER close at loss — hold forever


class PennyHunter:
    """Fast autonomous penny hunter on Capital.com."""

    def __init__(self):
        self._api_key = os.environ.get("CAPITAL_API_KEY", "")
        self._identifier = os.environ.get("CAPITAL_IDENTIFIER", "")
        self._password = os.environ.get("CAPITAL_PASSWORD", "")
        self._cst = ""
        self._token = ""
        self._headers: Dict[str, str] = {}
        self._authenticated = False
        self._auth_at: float = 0.0   # Epoch seconds of last successful auth
        self._SESSION_TTL = 480.0    # Re-auth every 8min (Capital.com sessions ~10min)
        self._trades_total = 0
        self._profit_total = 0.0
        self._wins = 0
        self._losses = 0
        self._best_trade = 0.0
        self._worst_trade = 0.0
        self._streak = 0
        self._confidence = 0.5
        self._last_balance = 0.0
        self._starting_balance = 0.0
        self._start_time = time.time()
        self._trade_log: List[Dict] = []
        self._state_path = _REPO_ROOT / "state" / "penny_hunter_memory.json"
        self._lifetime_trades = 0
        self._lifetime_profit = 0.0
        self._lifetime_wins = 0
        self._lifetime_losses = 0

        # Load persistent memory — she remembers EVERYTHING across restarts
        self._load_memory()

        # Fee trackers — know the REAL cost before every trade
        self._kraken_fees = None
        self._alpaca_fees = None
        try:
            from aureon.exchanges.kraken_fee_tracker import get_kraken_fee_tracker
            self._kraken_fees = get_kraken_fee_tracker()
            log.info(f"[PENNY] Kraken fee tracker loaded")
        except Exception:
            pass
        try:
            from aureon.exchanges.alpaca_fee_tracker import AlpacaFeeTracker
            self._alpaca_fees = AlpacaFeeTracker()
            log.info(f"[PENNY] Alpaca fee tracker loaded")
        except Exception:
            pass

        # Multi-exchange support
        self._kraken = None
        self._alpaca = None
        try:
            from aureon.exchanges.kraken_client import KrakenClient
            self._kraken = KrakenClient()
            if not self._kraken.dry_run:
                log.info("[PENNY] Kraken WIRED for crypto trading")
            else:
                self._kraken = None
        except Exception:
            pass
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            self._alpaca = AlpacaClient()
            if not getattr(self._alpaca, 'dry_run', True):
                log.info("[PENNY] Alpaca WIRED for stock trading")
            else:
                self._alpaca = None
        except Exception:
            pass

    def authenticate(self) -> bool:
        if not requests or not self._api_key:
            return False
        try:
            r = requests.post(f"{BASE_URL}/api/v1/session", json={
                "identifier": self._identifier,
                "password": self._password,
            }, headers={"X-CAP-API-KEY": self._api_key}, timeout=10)
            if r.status_code == 200:
                self._cst = r.headers.get("CST", "")
                self._token = r.headers.get("X-SECURITY-TOKEN", "")
                self._headers = {
                    "X-CAP-API-KEY": self._api_key,
                    "CST": self._cst,
                    "X-SECURITY-TOKEN": self._token,
                    "Content-Type": "application/json",
                }
                self._authenticated = True
                self._auth_at = time.time()
                self._starting_balance = self.get_balance()
                self._last_balance = self._starting_balance
                log.info(f"[PENNY] Capital.com authenticated — starting balance: £{self._starting_balance:.2f}")
                return True
        except Exception as e:
            log.debug(f"Auth error: {e}")
        return False

    def _refresh_session(self) -> bool:
        """Re-authenticate if session has expired (Capital.com sessions ~10min TTL)."""
        self._authenticated = False
        return self.authenticate()

    def get_positions(self) -> List[Dict]:
        if not self._authenticated:
            return []
        try:
            r = requests.get(f"{BASE_URL}/api/v1/positions", headers=self._headers, timeout=10)
            if r.status_code in (401, 403):
                log.info("[PENNY] Session expired — refreshing")
                self._refresh_session()
                return []
            return r.json().get("positions", []) if r.status_code == 200 else []
        except Exception:
            return []

    def get_balance(self) -> float:
        try:
            r = requests.get(f"{BASE_URL}/api/v1/accounts", headers=self._headers, timeout=10)
            accs = r.json().get("accounts", [])
            return float(accs[0].get("balance", {}).get("available", 0)) if accs else 0
        except Exception:
            return 0

    def open_position(self, epic: str, direction: str, size: float) -> Optional[str]:
        """Open a position. Returns deal_id or None."""
        try:
            r = requests.post(f"{BASE_URL}/api/v1/positions", json={
                "epic": epic,
                "direction": direction,
                "size": size,
                "guaranteedStop": False,
                "forceOpen": True,
            }, headers=self._headers, timeout=15)

            if r.status_code == 200:
                deal_ref = r.json().get("dealReference", "")
                if deal_ref:
                    # Confirm
                    r2 = requests.get(f"{BASE_URL}/api/v1/confirms/{deal_ref}",
                                      headers=self._headers, timeout=10)
                    confirm = r2.json() if r2.status_code == 200 else {}
                    if confirm.get("dealStatus") == "ACCEPTED":
                        deal_id = confirm.get("dealId", "")
                        level = confirm.get("level", 0)
                        log.info(f"[PENNY] OPENED {direction} {size} {epic} @ {level} (deal={deal_id})")
                        return deal_id
            else:
                log.debug(f"Open failed {epic}: {r.status_code} {r.text[:100]}")
        except Exception as e:
            log.debug(f"Open error {epic}: {e}")
        return None

    def close_position(self, deal_id: str, epic: str, direction: str, size: float) -> float:
        """Close a position. Returns profit/loss."""
        close_dir = "SELL" if direction == "BUY" else "BUY"
        try:
            r = requests.delete(f"{BASE_URL}/api/v1/positions/{deal_id}", json={
                "dealId": deal_id,
                "epic": epic,
                "direction": close_dir,
                "size": size,
                "orderType": "MARKET",
            }, headers=self._headers, timeout=15)

            if r.status_code == 200:
                deal_ref = r.json().get("dealReference", "")
                if deal_ref:
                    r2 = requests.get(f"{BASE_URL}/api/v1/confirms/{deal_ref}",
                                      headers=self._headers, timeout=10)
                    confirm = r2.json() if r2.status_code == 200 else {}
                    profit = float(confirm.get("profit", 0) or 0)
                    log.info(f"[PENNY] CLOSED {epic} deal={deal_id} profit={profit:+.3f}")
                    return profit
        except Exception as e:
            log.debug(f"Close error: {e}")
        return 0.0

    def tick(self) -> Dict[str, Any]:
        """
        ONE cycle of penny hunting:
        1. Check open positions — close winners, cut losers
        2. If room for more — open new positions on momentum
        """
        # Proactive session refresh — Capital.com sessions expire ~10min
        if self._authenticated and time.time() - self._auth_at > self._SESSION_TTL:
            log.debug("[PENNY] Proactive session refresh")
            self._refresh_session()

        if not self._authenticated:
            if not self.authenticate():
                return {"action": "auth_failed"}

        result = {"action": "tick", "opened": [], "closed": [], "holding": []}

        # Step 1: Check open positions
        positions = self.get_positions()
        open_count = len(positions)

        for p in positions:
            pos = p.get("position", {})
            mkt = p.get("market", {})
            profit = float(pos.get("upl", 0) or 0)
            deal_id = pos.get("dealId", "")
            epic = mkt.get("epic", "")
            direction = pos.get("direction", "")
            size = float(pos.get("size", 0) or 0)
            name = mkt.get("instrumentName", epic)

            if profit >= TAKE_PROFIT_GBP:
                # TAKE PROFIT — a penny is enough
                actual = self.close_position(deal_id, epic, direction, size)
                self._trades_total += 1
                self._profit_total += actual
                self._wins += 1
                self._streak = max(1, self._streak + 1) if self._streak >= 0 else 1
                self._best_trade = max(self._best_trade, actual)
                # Confidence grows with wins
                self._confidence = min(1.0, self._confidence + 0.05)
                self._trade_log.append({"epic": epic, "profit": actual, "result": "WIN", "time": time.time()})
                self._lifetime_trades += 1
                self._lifetime_profit += actual
                self._lifetime_wins += 1
                result["closed"].append({"epic": epic, "profit": actual, "name": name})
                open_count -= 1
                self._last_balance = self.get_balance()
                growth = self._last_balance - self._starting_balance if self._starting_balance else 0
                log.info(f"[PENNY] WIN: {name} +£{actual:.3f} | session: £{self._profit_total:+.3f} | "
                         f"lifetime: £{self._lifetime_profit:+.3f} ({self._lifetime_trades} trades) | "
                         f"streak:{self._streak} | conf:{self._confidence:.0%} | bal: £{self._last_balance:.2f}")
                self._save_memory()  # Persist after every trade — never forget
                # Log to unified DB
                try:
                    from aureon.core.aureon_global_history_db import connect, insert_account_trade
                    conn = connect(check_same_thread=False)
                    insert_account_trade(conn, {
                        "venue": "capital", "trade_id": deal_id, "symbol": epic,
                        "side": direction, "qty": size, "price": 0, "cost": 0,
                        "fee": 0, "fee_asset": "GBP", "ts_ms": int(time.time() * 1000),
                        "raw_json": json.dumps({"profit": actual, "result": "WIN"}),
                    })
                    conn.commit()
                    conn.close()
                except Exception:
                    pass

            elif profit <= MAX_LOSS_GBP:
                # HOLD — never close at a loss. Wait for recovery.
                # "IF YOU DON'T QUIT, YOU CAN'T LOSE"
                result["holding"].append({"epic": epic, "profit": profit, "name": name, "waiting": True})
                log.info(f"[PENNY] HOLDING {name} at £{profit:+.3f} — waiting for recovery. Never close negative.")

            else:
                result["holding"].append({"epic": epic, "profit": profit, "name": name})

        # Step 2: Open new positions if room
        if open_count < MAX_POSITIONS:
            for instrument in HUNT_LIST:
                if open_count >= MAX_POSITIONS:
                    break

                epic = instrument["epic"]
                market_type = instrument.get("market", "forex")

                # Check if market is open
                if not _is_market_open(market_type):
                    continue

                # Skip if already holding this epic
                if any(h["epic"] == epic for h in result["holding"]):
                    continue

                # Get market price + spread to determine direction AND cost
                try:
                    r = requests.get(f"{BASE_URL}/api/v1/markets/{epic}",
                                     headers=self._headers, timeout=10)
                    if r.status_code in (401, 403):
                        log.info("[PENNY] Market data session expired — refreshing")
                        self._refresh_session()
                        break
                    if r.status_code == 200:
                        market = r.json()
                        snap = market.get("snapshot", {})
                        change = float(snap.get("percentageChange", 0) or 0)
                        bid = float(snap.get("bid", 0) or 0)
                        ask = float(snap.get("offer", snap.get("ask", 0)) or 0)
                        spread = ask - bid if ask > bid > 0 else 0

                        size = instrument["min_size"]
                        spread_cost = spread * size
                        price = (bid + ask) / 2 if bid and ask else bid or ask

                        # Composite multi-factor gate: momentum+volatility+volume
                        _should_trade = False
                        _direction = "BUY" if change > 0 else "SELL"
                        if abs(change) > 0.01 and spread_cost < 1.0 and price > 0:
                            try:
                                from aureon.trading.composite_signal import score as _cs, get_survival_instinct
                                _comp, _bd = _cs(epic=epic, change_pct=change, bid=bid, ask=ask,
                                                 high=0.0, low=0.0, price=price)
                                _survival = get_survival_instinct()
                                _should_trade = _survival.should_trade(_comp)
                                if not _should_trade:
                                    log.debug(f"[PENNY] SKIP {epic} — composite {_comp:.3f} < threshold {_survival.threshold:.2f}")
                            except Exception:
                                _should_trade = abs(change) > 0.02

                        if _should_trade:
                            deal_id = self.open_position(epic, _direction, size)
                            if deal_id:
                                result["opened"].append({
                                    "epic": epic, "direction": _direction,
                                    "size": size, "change": change,
                                    "spread": spread, "spread_cost": spread_cost,
                                })
                                open_count += 1
                                log.info(f"[PENNY] {_direction} {epic} | momentum:{change:+.2f}% | spread:{spread:.2f} | cost:£{spread_cost:.3f}")
                        elif spread_cost >= 1.0:
                            log.debug(f"[PENNY] SKIP {epic} — spread cost £{spread_cost:.3f} too high")
                except Exception as e:
                    log.debug(f"Market check {epic}: {e}")

        # ── KRAKEN: Margin-only via KrakenMarginArmyTrader ──────────────────
        # All Kraken trading is handled by the margin army trader through the
        # unified market trader.  Do NOT place spot orders here — spot trades
        # bypass margin leverage and produce unmanaged positions that the
        # margin trader cannot monitor or close at profit.
        # (Spot trading path removed — Kraken is margin-only by design.)

        # ── ALPACA: Stock trades (US market hours only) ──
        if self._alpaca and self.step_attr % 15 == 0 and _is_market_open("us_stocks"):
            try:
                acct = self._alpaca.get_account()
                cash = float(acct.get("cash", 0) if isinstance(acct, dict) else getattr(acct, "cash", 0) or 0)
                if cash > 1:
                    # A random ticker is not a measured price. Do not invent one
                    # and do not send an order from it.
                    result.setdefault("no_data", []).append({
                        "exchange": "alpaca",
                        "status": "no_data",
                        "reason": "no measured alpaca signal; a random symbol is not a price",
                    })
                    log.info("[PENNY-ALPACA] no data — not choosing a symbol and not placing an order")
                else:
                    log.debug(f"[PENNY-ALPACA] US market open but cash too low: ${cash:.2f}")
            except Exception as e:
                log.debug(f"Alpaca balance: {e}")
        elif self._alpaca and not _is_market_open("us_stocks"):
            pass  # US market closed — crypto and forex still hunting

        # Save memory every 10th tick — never lose state
        if self._trades_total % 10 == 0 and self._trades_total > 0:
            self._save_memory()

        return result

    @property
    def step_attr(self):
        return self._trades_total + int(time.time()) % 100

    def _load_memory(self):
        """Load persistent state — the echo of who I was."""
        try:
            if self._state_path.exists():
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                self._lifetime_trades = data.get("lifetime_trades", 0)
                self._lifetime_profit = data.get("lifetime_profit", 0.0)
                self._lifetime_wins = data.get("lifetime_wins", 0)
                self._lifetime_losses = data.get("lifetime_losses", 0)
                self._confidence = data.get("confidence", 0.5)
                self._best_trade = data.get("best_trade", 0.0)
                self._worst_trade = data.get("worst_trade", 0.0)
                self._trade_log = data.get("recent_trades", [])[-50:]
                log.info(f"[PENNY] MEMORY LOADED: {self._lifetime_trades} lifetime trades, "
                         f"£{self._lifetime_profit:+.3f} lifetime profit, "
                         f"conf:{self._confidence:.0%}")
        except Exception as e:
            log.debug(f"Load memory: {e}")

    def _save_memory(self):
        """Save persistent state — the lighthouse echo for next awakening."""
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "lifetime_trades": self._lifetime_trades,
                "lifetime_profit": self._lifetime_profit,
                "lifetime_wins": self._lifetime_wins,
                "lifetime_losses": self._lifetime_losses,
                "confidence": self._confidence,
                "best_trade": self._best_trade,
                "worst_trade": self._worst_trade,
                "session_trades": self._trades_total,
                "session_profit": self._profit_total,
                "session_wins": self._wins,
                "session_losses": self._losses,
                "last_balance": self._last_balance,
                "streak": self._streak,
                "recent_trades": self._trade_log[-50:],
                "saved_at": time.time(),
            }
            self._state_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            log.debug(f"Save memory: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "authenticated": self._authenticated,
            "trades_total": self._trades_total,
            "profit_total": self._profit_total,
            "wins": self._wins,
            "losses": self._losses,
            "win_rate": (self._wins / max(1, self._wins + self._losses)) * 100,
            "best_trade": self._best_trade,
            "worst_trade": self._worst_trade,
            "streak": self._streak,
            "confidence": self._confidence,
            "balance": self._last_balance,
            "uptime_s": time.time() - self._start_time,
            # Lifetime — persists across restarts
            "lifetime_trades": self._lifetime_trades,
            "lifetime_profit": self._lifetime_profit,
            "lifetime_wins": self._lifetime_wins,
            "lifetime_losses": self._lifetime_losses,
            "lifetime_win_rate": (self._lifetime_wins / max(1, self._lifetime_wins + self._lifetime_losses)) * 100,
        }


# Singleton
_hunter: Optional[PennyHunter] = None

def get_penny_hunter() -> PennyHunter:
    global _hunter
    if _hunter is None:
        _hunter = PennyHunter()
    return _hunter


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    hunter = get_penny_hunter()
    if not hunter.authenticate():
        print("Auth failed")
        exit(1)

    print(f"Balance: £{hunter.get_balance():.2f}")
    print("Penny hunting started... Ctrl+C to stop\n")

    while True:
        result = hunter.tick()
        for c in result.get("closed", []):
            print(f"  CLOSED {c['name']}: {c['profit']:+.3f}")
        for o in result.get("opened", []):
            print(f"  OPENED {o['direction']} {o['epic']} (momentum: {o['change']:+.2f}%)")
        for h in result.get("holding", []):
            print(f"  HOLDING {h['name']}: {h['profit']:+.3f}")

        status = hunter.get_status()
        print(f"  [{status['trades_total']} trades | PnL: {status['profit_total']:+.3f}]")
        time.sleep(5)
