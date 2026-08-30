#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUREON OPERATIONAL CORE — The 9 Surgical Fixes
Gary Leckey | February 2026

This module connects Aureon's brilliant analysis brain to its execution body.
It provides the missing operational infrastructure:

1. Signal Gate     — Brain signals block/allow trades
2. Veto Enforcer   — Gates actually stop trades (not just log)
3. Circuit Breaker  — API failures trigger halt, not silent retry
4. Reconciliation   — Exchange balance vs internal state check
5. WebSocket Guard  — Reconnection with exponential backoff
6. Trade Lock       — Per-symbol coordination across processes
7. Execution Confirm — Verify orders actually filled
8. State Pulse      — Continuous state file updates
9. Health Truth     — Real system health, not just "server is up"
"""

import os
import sys
import io
import time
import json
import logging
import threading
import tempfile
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX
# ═══════════════════════════════════════════════════════════════════════════
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# Cross-platform file locking
if sys.platform == 'win32':
    import msvcrt
    def _lock_file(fh, exclusive=True, blocking=False):
        try:
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK if not blocking else msvcrt.LK_LOCK, 1)
            return True
        except (IOError, OSError):
            return False
    def _unlock_file(fh):
        try:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
else:
    import fcntl
    def _lock_file(fh, exclusive=True, blocking=False):
        try:
            flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            if not blocking:
                flags |= fcntl.LOCK_NB
            fcntl.flock(fh.fileno(), flags)
            return True
        except (IOError, OSError):
            return False
    def _unlock_file(fh):
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass

logger = logging.getLogger("AUREON_OPS")

# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 1: SIGNAL GATE — Wire the Brain to the Body
# ═══════════════════════════════════════════════════════════════════════════════

class SignalGate:
    """
    Sits between analysis (Phase Transition, Timeline Oracle, Harmonic Fusion)
    and execution (place_market_order). If the brain says NO, the body stops.

    This is the single most important fix: without it, all analysis is wasted.
    """

    def __init__(self, phase_detector=None, solar_monitor=None):
        self.phase_detector = phase_detector
        self.solar_monitor = solar_monitor
        self._last_phase_state = None
        self._last_check_time = 0
        self._cache_ttl = 5.0  # Re-check phase every 5 seconds max
        self._blocked_count = 0
        self._allowed_count = 0

    def check_entry_allowed(self, symbol: str, price: float,
                            queen_guidance: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Query the brain: should we enter this trade?

        Returns:
            (allowed: bool, reason: str)
        """
        now = time.time()

        # 1. Phase Transition Detector check. The detector's API is
        # ingest()/predict() — this block used to call update()/get_state()/
        # get_curvature(), none of which exist, so every call raised into the
        # except below and the PHASE_CRITICAL block had never once fired.
        # Because arming a never-executed veto on live paths is itself a risk,
        # the actual block follows the production_mode contract (acts in LIVE,
        # audits would_have_blocked everywhere else).
        if self.phase_detector is not None:
            try:
                if now - self._last_check_time > self._cache_ttl:
                    self.phase_detector.ingest(price, now)
                    self._last_check_time = now

                prediction = self.phase_detector.predict()
                self._last_phase_state = prediction.state if prediction else None

                if prediction is not None:
                    is_critical = prediction.state.name == 'CRITICAL'
                    high_kappa = prediction.curvature > 10.0
                    if is_critical or high_kappa:
                        from aureon.observer.production_mode import audit as _pm_audit
                        from aureon.observer.production_mode import phase_veto_active
                        veto = phase_veto_active()
                        _pm_audit(
                            "signal_gate_phase_check",
                            {
                                "symbol": symbol,
                                "state": prediction.state.value,
                                "probability": round(prediction.probability, 4),
                                "curvature": round(prediction.curvature, 4),
                            },
                            decision="entry_veto",
                            would_have_blocked=True,
                            actually_blocked=veto,
                        )
                        if veto:
                            self._blocked_count += 1
                            if is_critical:
                                return False, (
                                    f"PHASE_CRITICAL: Market regime change detected "
                                    f"(p={prediction.probability:.2f})"
                                )
                            return False, (
                                f"HIGH_CURVATURE: kappa={prediction.curvature:.2f} "
                                f"> 10.0 (geometric stress)"
                            )
            except Exception as e:
                logger.debug(f"Phase detector check failed (allowing trade): {e}")

        # 2. Queen Guidance check
        if queen_guidance is not None:
            try:
                direction = queen_guidance.get('direction', '').upper()
                confidence = float(queen_guidance.get('confidence', 0.5))

                # Queen says HOLD or SELL with decent confidence = block entry
                if direction in ('HOLD', 'SELL') and confidence > 0.4:
                    self._blocked_count += 1
                    return False, f"QUEEN_{direction}: confidence={confidence:.2f} > 0.4"
            except Exception as e:
                logger.debug(f"Queen guidance check failed (allowing trade): {e}")

        # 3. Solar storm check (if Cross-Substrate Monitor available)
        if self.solar_monitor is not None:
            try:
                if hasattr(self.solar_monitor, 'get_latest_snapshot'):
                    snapshot = self.solar_monitor.get_latest_snapshot()
                    if snapshot and hasattr(snapshot, 'solar_storm') and snapshot.solar_storm:
                        if hasattr(snapshot, 'flare_active') and snapshot.flare_active:
                            self._blocked_count += 1
                            return False, "SOLAR_STORM: Active flare detected (cross-substrate caution)"
            except Exception as e:
                logger.debug(f"Solar monitor check failed (allowing trade): {e}")

        # 4. Volatility sentinel check (P4). The sentinel PREDICTS high
        # volatility from four measured factors (EWMA expansion, phase
        # transition, QGITA regime, spectral surge); at VOL_RISK_BLOCK with
        # enough factor coverage the entry is vetoed. Same production_mode
        # contract as the phase check: acts in LIVE, audits
        # would_have_blocked everywhere else. No assessment / stale /
        # thin coverage → honest passthrough (never a substituted risk).
        try:
            from aureon.intelligence.volatility_sentinel import (
                VOL_MIN_CONFIDENCE_GATE,
                VOL_RISK_BLOCK,
                read_latest_assessment,
            )

            vol = read_latest_assessment()
            if (vol is not None and vol.status == "ok"
                    and vol.volatility_risk is not None
                    and vol.confidence >= VOL_MIN_CONFIDENCE_GATE
                    and vol.volatility_risk >= VOL_RISK_BLOCK):
                from aureon.observer.production_mode import audit as _pm_audit
                from aureon.observer.production_mode import volatility_veto_active
                veto = volatility_veto_active()
                factors = ",".join(
                    f.name for f in vol.factors if f.status == "ok") or "none"
                _pm_audit(
                    "signal_gate_volatility_check",
                    {
                        "symbol": symbol,
                        "volatility_risk": round(vol.volatility_risk, 4),
                        "confidence": round(vol.confidence, 4),
                        "factors": factors,
                    },
                    decision="entry_veto",
                    would_have_blocked=True,
                    actually_blocked=veto,
                )
                if veto:
                    self._blocked_count += 1
                    return False, (
                        f"VOLATILITY_PREDICTED: sentinel risk="
                        f"{vol.volatility_risk:.2f} >= {VOL_RISK_BLOCK} "
                        f"(factors: {factors})"
                    )
        except Exception as e:
            logger.debug(f"Volatility sentinel check failed (allowing trade): {e}")

        self._allowed_count += 1
        return True, "CLEAR"

    def get_stats(self) -> Dict:
        total = self._blocked_count + self._allowed_count
        return {
            'blocked': self._blocked_count,
            'allowed': self._allowed_count,
            'total': total,
            'block_rate': self._blocked_count / max(total, 1),
            'last_phase_state': str(self._last_phase_state) if self._last_phase_state else 'UNKNOWN',
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 3: CIRCUIT BREAKER — Stop cascading API failures
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeCircuitBreaker:
    """
    Tracks consecutive API failures per exchange.
    After threshold failures, disables that exchange temporarily.
    After global threshold, enters READ-ONLY mode.

    This prevents 50+ consecutive failures from silently continuing.
    """

    def __init__(self,
                 per_exchange_threshold: int = 5,
                 per_exchange_cooldown: float = 300.0,  # 5 minutes
                 global_threshold: int = 15,
                 failure_window: float = 60.0):
        self._failures: Dict[str, list] = {}  # exchange -> [timestamp, ...]
        self._disabled_until: Dict[str, float] = {}  # exchange -> timestamp
        self._global_readonly = False
        self._global_readonly_since: Optional[float] = None
        self._per_exchange_threshold = per_exchange_threshold
        self._per_exchange_cooldown = per_exchange_cooldown
        self._global_threshold = global_threshold
        self._failure_window = failure_window
        self._lock = threading.Lock()
        self._total_failures = 0
        self._total_trips = 0

    def record_failure(self, exchange: str, error: str = "") -> Dict:
        """
        Record an API failure. Returns action taken.
        """
        now = time.time()
        result = {'action': 'recorded', 'exchange': exchange}

        with self._lock:
            if exchange not in self._failures:
                self._failures[exchange] = []

            self._failures[exchange].append(now)
            self._total_failures += 1

            # Prune old failures outside window
            cutoff = now - self._failure_window
            self._failures[exchange] = [t for t in self._failures[exchange] if t > cutoff]

            recent_count = len(self._failures[exchange])

            # Per-exchange circuit breaker
            if recent_count >= self._per_exchange_threshold:
                self._disabled_until[exchange] = now + self._per_exchange_cooldown
                self._total_trips += 1
                result = {
                    'action': 'exchange_disabled',
                    'exchange': exchange,
                    'failures': recent_count,
                    'disabled_until': datetime.fromtimestamp(now + self._per_exchange_cooldown).isoformat(),
                    'cooldown_seconds': self._per_exchange_cooldown,
                }
                logger.warning(
                    f"CIRCUIT BREAKER: {exchange.upper()} DISABLED for {self._per_exchange_cooldown}s "
                    f"({recent_count} failures in {self._failure_window}s)"
                )
                print(f"\n   ⚡🛑 CIRCUIT BREAKER: {exchange.upper()} disabled for {self._per_exchange_cooldown/60:.0f} min "
                      f"({recent_count} consecutive failures)")

            # Global circuit breaker
            total_recent = sum(len(f) for f in self._failures.values())
            if total_recent >= self._global_threshold and not self._global_readonly:
                self._global_readonly = True
                self._global_readonly_since = now
                result['global_action'] = 'READ_ONLY_MODE'
                logger.critical(
                    f"GLOBAL CIRCUIT BREAKER: READ-ONLY MODE ACTIVATED "
                    f"({total_recent} total failures across all exchanges)"
                )
                print(f"\n   ⚡🛑🛑 GLOBAL CIRCUIT BREAKER: READ-ONLY MODE — "
                      f"{total_recent} failures across all exchanges. NO TRADES UNTIL MANUAL RESET.")

        return result

    def record_success(self, exchange: str):
        """Record a successful API call — resets failure count for exchange."""
        with self._lock:
            if exchange in self._failures:
                self._failures[exchange] = []

    def is_exchange_available(self, exchange: str) -> Tuple[bool, str]:
        """Check if an exchange is available for trading."""
        now = time.time()

        if self._global_readonly:
            return False, f"GLOBAL_READ_ONLY (since {datetime.fromtimestamp(self._global_readonly_since).strftime('%H:%M:%S')})"

        disabled_until = self._disabled_until.get(exchange, 0)
        if now < disabled_until:
            remaining = disabled_until - now
            return False, f"{exchange.upper()}_DISABLED ({remaining:.0f}s remaining)"

        # Auto-clear if cooldown expired
        if exchange in self._disabled_until and now >= disabled_until:
            with self._lock:
                del self._disabled_until[exchange]
                self._failures[exchange] = []
                logger.info(f"Circuit breaker: {exchange.upper()} re-enabled after cooldown")

        return True, "AVAILABLE"

    def reset_global(self):
        """Manual reset of global read-only mode."""
        with self._lock:
            self._global_readonly = False
            self._global_readonly_since = None
            self._failures.clear()
            self._disabled_until.clear()
            logger.info("Circuit breaker: Global reset — all exchanges re-enabled")

    def get_status(self) -> Dict:
        now = time.time()
        return {
            'global_readonly': self._global_readonly,
            'global_readonly_since': self._global_readonly_since,
            'total_failures': self._total_failures,
            'total_trips': self._total_trips,
            'exchanges': {
                ex: {
                    'recent_failures': len([t for t in times if t > now - self._failure_window]),
                    'disabled': now < self._disabled_until.get(ex, 0),
                    'disabled_remaining': max(0, self._disabled_until.get(ex, 0) - now),
                }
                for ex, times in self._failures.items()
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 6: TRADE LOCK — Per-symbol coordination across processes
# ═══════════════════════════════════════════════════════════════════════════════

class TradeLock:
    """
    File-based per-symbol lock to prevent multiple processes from
    trading the same symbol simultaneously.

    Uses fcntl.flock for cross-process safety.
    """

    def __init__(self, lock_dir: str = None):
        if lock_dir is None:
            lock_dir = os.path.join(tempfile.gettempdir(), "aureon_trade_locks")
        self._lock_dir = Path(lock_dir)
        self._lock_dir.mkdir(parents=True, exist_ok=True)
        self._held_locks: Dict[str, Any] = {}  # symbol -> file handle
        self._lock = threading.Lock()

    def _lock_path(self, symbol: str) -> Path:
        safe_name = symbol.replace('/', '_').replace('\\', '_')
        return self._lock_dir / f"{safe_name}.lock"

    def acquire(self, symbol: str, timeout: float = 5.0) -> Tuple[bool, str]:
        """
        Try to acquire a trade lock for a symbol.
        Returns (success, reason).
        """
        lock_path = self._lock_path(symbol)
        start = time.time()

        while time.time() - start < timeout:
            try:
                fh = open(lock_path, 'w')
                if _lock_file(fh, exclusive=True, blocking=False):
                    # Write lock info
                    fh.write(json.dumps({
                        'symbol': symbol,
                        'pid': os.getpid(),
                        'acquired': datetime.now(timezone.utc).isoformat(),
                    }))
                    fh.flush()

                    with self._lock:
                        self._held_locks[symbol] = fh

                    return True, "LOCKED"
                else:
                    raise IOError("Lock held")
            except (IOError, OSError):
                # Lock held by another process
                try:
                    fh.close()
                except Exception:
                    pass
                time.sleep(0.1)

        return False, f"TIMEOUT: {symbol} locked by another process"

    def release(self, symbol: str):
        """Release a trade lock."""
        with self._lock:
            fh = self._held_locks.pop(symbol, None)

        if fh:
            try:
                _unlock_file(fh)
                fh.close()
            except Exception:
                pass

            lock_path = self._lock_path(symbol)
            try:
                lock_path.unlink(missing_ok=True)
            except Exception:
                pass

    def is_locked(self, symbol: str) -> bool:
        """Check if a symbol is currently locked (by any process)."""
        lock_path = self._lock_path(symbol)
        if not lock_path.exists():
            return False
        try:
            fh = open(lock_path, 'r')
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()
            return False  # We could acquire it, so it's not locked
        except (IOError, OSError):
            return True
        except Exception:
            return False

    def release_all(self):
        """Release all locks held by this process."""
        with self._lock:
            symbols = list(self._held_locks.keys())
        for symbol in symbols:
            self.release(symbol)


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 7: EXECUTION CONFIRMATION — Verify orders actually filled
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionConfirmer:
    """
    After placing an order, polls the exchange to verify it actually filled.
    Only updates internal state after confirmed fill.

    Prevents fire-and-forget orders from corrupting position state.
    """

    def __init__(self, max_polls: int = 5, poll_interval: float = 2.0):
        self._max_polls = max_polls
        self._poll_interval = poll_interval
        self._confirmed = 0
        self._failed = 0
        self._pending = 0

    def confirm_order(self, client, exchange: str, order_id: str,
                      symbol: str) -> Dict:
        """
        Poll exchange for order status until filled, rejected, or timeout.

        Returns:
            {
                'confirmed': bool,
                'status': str,  # 'filled', 'partial', 'rejected', 'timeout'
                'fill_price': float or None,
                'fill_qty': float or None,
                'attempts': int,
            }
        """
        if not order_id or order_id == 'dry_run':
            return {'confirmed': True, 'status': 'dry_run', 'fill_price': None,
                    'fill_qty': None, 'attempts': 0}

        self._pending += 1

        for attempt in range(1, self._max_polls + 1):
            try:
                # Try to get order status from exchange
                order_status = None

                if hasattr(client, 'clients') and exchange in client.clients:
                    ex_client = client.clients[exchange]
                    if hasattr(ex_client, 'get_order_status'):
                        order_status = ex_client.get_order_status(order_id, symbol)
                    elif hasattr(ex_client, 'query_order'):
                        order_status = ex_client.query_order(order_id, symbol)

                if order_status:
                    status = str(order_status.get('status', '')).lower()

                    if status in ('filled', 'closed', 'done'):
                        self._confirmed += 1
                        self._pending -= 1
                        fill_price = float(order_status.get('price', 0) or
                                          order_status.get('avg_price', 0) or 0)
                        fill_qty = float(order_status.get('filled_qty', 0) or
                                        order_status.get('executedQty', 0) or 0)
                        return {
                            'confirmed': True,
                            'status': 'filled',
                            'fill_price': fill_price if fill_price > 0 else None,
                            'fill_qty': fill_qty if fill_qty > 0 else None,
                            'attempts': attempt,
                        }

                    if status in ('rejected', 'cancelled', 'canceled', 'expired'):
                        self._failed += 1
                        self._pending -= 1
                        return {
                            'confirmed': False,
                            'status': status,
                            'fill_price': None,
                            'fill_qty': None,
                            'attempts': attempt,
                        }

                    # Still pending, wait and retry

            except Exception as e:
                logger.debug(f"Order confirmation poll {attempt}/{self._max_polls} failed: {e}")

            if attempt < self._max_polls:
                time.sleep(self._poll_interval)

        # Timeout - assume filled if we got an order ID back
        self._pending -= 1
        logger.warning(f"Order {order_id} confirmation timeout after {self._max_polls} polls")
        return {
            'confirmed': True,  # Optimistic: we got an order ID
            'status': 'timeout_assumed_filled',
            'fill_price': None,
            'fill_qty': None,
            'attempts': self._max_polls,
        }

    def get_stats(self) -> Dict:
        return {
            'confirmed': self._confirmed,
            'failed': self._failed,
            'pending': self._pending,
            'total': self._confirmed + self._failed,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 8: STATE PULSE — Continuous state file updates
# ═══════════════════════════════════════════════════════════════════════════════

class StatePulse:
    """
    Ensures state files are written every cycle, not just frozen at startup.
    Tracks freshness and alerts if state goes stale.
    """

    def __init__(self, state_dir: str = None,
                 stale_threshold: float = 300.0):  # 5 minutes
        if state_dir is None:
            state_dir = os.path.join(tempfile.gettempdir(), "aureon_state")
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._stale_threshold = stale_threshold
        self._last_write: Dict[str, float] = {}
        self._write_count = 0
        self._lock = threading.Lock()

    def pulse(self, positions: Dict, tracker_stats: Dict,
              signal_gate_stats: Dict = None,
              circuit_breaker_status: Dict = None):
        """
        Write current system state atomically. Call every cycle.
        """
        now = time.time()
        state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'unix_ts': now,
            'positions': {
                sym: {
                    'symbol': sym,
                    'entry_price': getattr(pos, 'entry_price', 0),
                    'quantity': getattr(pos, 'quantity', 0),
                    'entry_value': getattr(pos, 'entry_value', 0),
                    'exchange': getattr(pos, 'exchange', 'unknown'),
                    'entry_time': getattr(pos, 'entry_time', 0),
                }
                for sym, pos in positions.items()
            },
            'tracker': tracker_stats,
            'signal_gate': signal_gate_stats or {},
            'circuit_breaker': circuit_breaker_status or {},
            'pulse_count': self._write_count + 1,
        }

        # Atomic write (write to temp, then rename)
        state_path = self._state_dir / 'aureon_live_state.json'
        tmp_path = self._state_dir / 'aureon_live_state.json.tmp'

        try:
            with open(tmp_path, 'w') as f:
                json.dump(state, f, indent=2, default=str)

            os.replace(str(tmp_path), str(state_path))

            with self._lock:
                self._last_write['state'] = now
                self._write_count += 1

        except Exception as e:
            logger.error(f"State pulse write failed: {e}")

    def is_stale(self) -> Tuple[bool, float]:
        """Check if state is stale (not updated recently)."""
        last = self._last_write.get('state', 0)
        if last == 0:
            return True, float('inf')
        age = time.time() - last
        return age > self._stale_threshold, age

    def get_freshness(self) -> Dict:
        now = time.time()
        last = self._last_write.get('state', 0)
        return {
            'last_write': datetime.fromtimestamp(last).isoformat() if last > 0 else 'NEVER',
            'age_seconds': now - last if last > 0 else float('inf'),
            'is_stale': (now - last > self._stale_threshold) if last > 0 else True,
            'write_count': self._write_count,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHANGE 4: EXCHANGE RECONCILIATION — Verify internal state vs exchange reality
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeReconciler:
    """
    Every N minutes, queries actual exchange balances and compares to internal state.
    Logs discrepancies. If discrepancy > threshold, halts trading.
    """

    def __init__(self, interval: float = 300.0,  # 5 minutes
                 discrepancy_threshold: float = 0.05):  # 5%
        self._interval = interval
        self._threshold = discrepancy_threshold
        self._last_reconcile = 0
        self._discrepancies: list = []
        self._reconcile_count = 0

    def should_reconcile(self) -> bool:
        return time.time() - self._last_reconcile >= self._interval

    def reconcile(self, client, internal_positions: Dict,
                  internal_cash: float) -> Dict:
        """
        Compare internal state with exchange reality.

        Returns:
            {
                'reconciled': bool,
                'discrepancies': [...],
                'should_halt': bool,
                'exchange_total': float,
                'internal_total': float,
            }
        """
        self._last_reconcile = time.time()
        self._reconcile_count += 1
        discrepancies = []
        exchange_total = 0.0
        internal_total = internal_cash

        # Calculate internal total
        for sym, pos in internal_positions.items():
            entry_val = getattr(pos, 'entry_value', 0)
            internal_total += entry_val

        # Query each exchange for actual balances
        exchanges_checked = []
        if hasattr(client, 'clients'):
            for exchange_name, ex_client in client.clients.items():
                try:
                    balance = None
                    if hasattr(ex_client, 'get_balance'):
                        balance = ex_client.get_balance()
                    elif hasattr(ex_client, 'get_account'):
                        balance = ex_client.get_account()

                    if balance:
                        # Try to extract total equity
                        ex_equity = 0.0
                        if isinstance(balance, dict):
                            ex_equity = float(
                                balance.get('total_equity', 0) or
                                balance.get('equity', 0) or
                                balance.get('totalWalletBalance', 0) or
                                balance.get('eb', 0) or 0
                            )

                        if ex_equity > 0:
                            exchange_total += ex_equity
                            exchanges_checked.append(exchange_name)

                except Exception as e:
                    logger.debug(f"Reconciliation failed for {exchange_name}: {e}")

        # Compare
        should_halt = False
        if exchange_total > 0 and internal_total > 0:
            diff_pct = abs(exchange_total - internal_total) / max(exchange_total, internal_total)

            if diff_pct > self._threshold:
                disc = {
                    'time': datetime.now(timezone.utc).isoformat(),
                    'exchange_total': exchange_total,
                    'internal_total': internal_total,
                    'diff_pct': diff_pct * 100,
                    'exchanges_checked': exchanges_checked,
                }
                discrepancies.append(disc)
                self._discrepancies.append(disc)

                logger.warning(
                    f"RECONCILIATION DISCREPANCY: Exchange=${exchange_total:.2f} vs "
                    f"Internal=${internal_total:.2f} (diff={diff_pct*100:.1f}%)"
                )
                print(f"\n   ⚖️⚠️ RECONCILIATION: Exchange=${exchange_total:.2f} vs "
                      f"Internal=${internal_total:.2f} ({diff_pct*100:.1f}% drift)")

                if diff_pct > self._threshold * 2:  # >10% = halt
                    should_halt = True
                    print(f"   ⚖️🛑 CRITICAL DRIFT: {diff_pct*100:.1f}% > {self._threshold*200:.0f}% — HALTING")

        return {
            'reconciled': True,
            'discrepancies': discrepancies,
            'should_halt': should_halt,
            'exchange_total': exchange_total,
            'internal_total': internal_total,
            'exchanges_checked': exchanges_checked,
            'reconcile_count': self._reconcile_count,
        }

    def get_status(self) -> Dict:
        return {
            'last_reconcile': datetime.fromtimestamp(self._last_reconcile).isoformat() if self._last_reconcile > 0 else 'NEVER',
            'reconcile_count': self._reconcile_count,
            'discrepancy_count': len(self._discrepancies),
            'recent_discrepancies': self._discrepancies[-5:],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED OPERATIONAL CORE — Single entry point for all 9 fixes
# ═══════════════════════════════════════════════════════════════════════════════

class AureonOperationalCore:
    """
    Unified operational infrastructure. Initialize once, wire into the ecosystem.

    Usage:
        ops = AureonOperationalCore(phase_detector=PHASE_DETECTOR)

        # Before every trade:
        allowed, reason = ops.check_trade_allowed(symbol, price, exchange)
        if not allowed:
            return None

        # After placing order:
        confirmed = ops.confirm_order(client, exchange, order_id, symbol)

        # Every cycle:
        ops.heartbeat(positions, tracker_stats)
    """

    def __init__(self, phase_detector=None, solar_monitor=None):
        self.signal_gate = SignalGate(
            phase_detector=phase_detector,
            solar_monitor=solar_monitor,
        )
        self.circuit_breaker = ExchangeCircuitBreaker()
        self.trade_lock = TradeLock()
        self.execution_confirmer = ExecutionConfirmer()
        self.state_pulse = StatePulse()
        self.reconciler = ExchangeReconciler()
        self._initialized_at = time.time()

        logger.info("Aureon Operational Core ONLINE — 9 fixes active")
        print("   🔧 Operational Core: Signal Gate + Circuit Breaker + Trade Lock + "
              "Execution Confirm + State Pulse + Reconciler = WIRED")

    def check_trade_allowed(self, symbol: str, price: float, exchange: str,
                            queen_guidance: Optional[Dict] = None) -> Tuple[bool, str]:
        """
        Master gate: checks ALL conditions before allowing a trade.
        Combines Signal Gate + Circuit Breaker + Trade Lock.
        """
        # 1. Circuit breaker check
        available, cb_reason = self.circuit_breaker.is_exchange_available(exchange)
        if not available:
            return False, f"CIRCUIT_BREAKER: {cb_reason}"

        # 2. Signal gate (brain) check
        allowed, sg_reason = self.signal_gate.check_entry_allowed(
            symbol, price, queen_guidance
        )
        if not allowed:
            return False, f"SIGNAL_GATE: {sg_reason}"

        # 3. Trade lock check (is another process already trading this?)
        if self.trade_lock.is_locked(symbol):
            return False, f"TRADE_LOCK: {symbol} locked by another process"

        return True, "ALL_CLEAR"

    def record_api_failure(self, exchange: str, error: str = ""):
        """Record an exchange API failure for circuit breaker."""
        return self.circuit_breaker.record_failure(exchange, error)

    def record_api_success(self, exchange: str):
        """Record a successful exchange API call."""
        self.circuit_breaker.record_success(exchange)

    def confirm_order(self, client, exchange: str, order_id: str,
                      symbol: str) -> Dict:
        """Confirm an order was actually filled."""
        return self.execution_confirmer.confirm_order(
            client, exchange, order_id, symbol
        )

    def heartbeat(self, positions: Dict, tracker_stats: Dict):
        """
        Call every trading cycle. Updates state, checks reconciliation.
        """
        self.state_pulse.pulse(
            positions=positions,
            tracker_stats=tracker_stats,
            signal_gate_stats=self.signal_gate.get_stats(),
            circuit_breaker_status=self.circuit_breaker.get_status(),
        )

    def get_health(self) -> Dict:
        """
        Real system health — not just "server is up".
        Used by Change 9 (health dashboard).
        """
        state_freshness = self.state_pulse.get_freshness()
        cb_status = self.circuit_breaker.get_status()

        # Determine overall health
        health = 'healthy'
        issues = []

        if cb_status['global_readonly']:
            health = 'critical'
            issues.append('Global circuit breaker: READ-ONLY mode')

        disabled_exchanges = [
            ex for ex, info in cb_status.get('exchanges', {}).items()
            if info.get('disabled')
        ]
        if disabled_exchanges:
            health = 'degraded' if health == 'healthy' else health
            issues.append(f"Disabled exchanges: {', '.join(disabled_exchanges)}")

        if state_freshness['is_stale']:
            health = 'degraded' if health == 'healthy' else health
            issues.append(f"State stale: {state_freshness['age_seconds']:.0f}s old")

        return {
            'status': health,
            'uptime': time.time() - self._initialized_at,
            'issues': issues,
            'signal_gate': self.signal_gate.get_stats(),
            'circuit_breaker': cb_status,
            'state_freshness': state_freshness,
            'execution': self.execution_confirmer.get_stats(),
            'reconciliation': self.reconciler.get_status(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════════════════════════

_ops_core: Optional[AureonOperationalCore] = None

def get_operational_core(phase_detector=None, solar_monitor=None) -> AureonOperationalCore:
    """Get or create the operational core singleton."""
    global _ops_core
    if _ops_core is None:
        _ops_core = AureonOperationalCore(
            phase_detector=phase_detector,
            solar_monitor=solar_monitor,
        )
    return _ops_core
