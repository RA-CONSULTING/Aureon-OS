#!/usr/bin/env python3
"""
capital_hft_stress.py — Flight test + stress test for Capital.com HFT on volatile assets.

Two phases:
  FLIGHT  (90s)  — current default config, observe what the engine naturally does
  STRESS  (180s) — HFT overrides: faster scan, tighter timing, volatile-only universe

Goal injected: "Capitalize on volatility — enter and exit fast in any direction."

Output: capital_hft_benchmark.log  +  live console stream.
"""

import os, sys, io, time, json, threading
from pathlib import Path

# ── UTF-8 stdout for Windows ──────────────────────────────────────────────────
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

os.environ["PYTHONIOENCODING"]           = "utf-8"
os.environ["AUREON_LLM_PROBE_TIMEOUT_S"] = "3"
os.environ["AUREON_LLM_HEALTH_TIMEOUT_S"]= "2"

HERE      = Path(__file__).parent
LOG_PATH  = HERE / "capital_hft_benchmark.log"
SYS_PATH  = str(HERE)
if SYS_PATH not in sys.path:
    sys.path.insert(0, SYS_PATH)

# ── HFT Universe — volatile assets only ──────────────────────────────────────
#  sl_pct  — initial hard stop, wide enough to survive entry noise
#  tp_pct  — take-profit target; trail_activation_pct — trail only once profit
#            reaches this level (position breathes, then the river flows)
#  trail_activation_pct — % profit required before trailing stop engages
HFT_UNIVERSE = {
    # Forex — initial SL wide enough for 15-20 pip noise; trail after 0.08%; exit at 60s if still losing
    "EURUSD":     {"class": "forex",     "tp_pct": 0.30, "sl_pct": 0.18, "trail_activation_pct": 0.08, "cognitive_timeout_s": 60, "size": 0.01, "max_spread_pct": 0.08, "momentum_threshold": 0.015},
    "GBPUSD":     {"class": "forex",     "tp_pct": 0.30, "sl_pct": 0.18, "trail_activation_pct": 0.08, "cognitive_timeout_s": 60, "size": 0.01, "max_spread_pct": 0.10, "momentum_threshold": 0.015},
    "USDJPY":     {"class": "forex",     "tp_pct": 0.30, "sl_pct": 0.18, "trail_activation_pct": 0.08, "cognitive_timeout_s": 60, "size": 0.01, "max_spread_pct": 0.07, "momentum_threshold": 0.015},
    "GBPJPY":     {"class": "forex",     "tp_pct": 0.40, "sl_pct": 0.22, "trail_activation_pct": 0.10, "cognitive_timeout_s": 60, "size": 0.01, "max_spread_pct": 0.12, "momentum_threshold": 0.02},
    "USDCHF":     {"class": "forex",     "tp_pct": 0.30, "sl_pct": 0.18, "trail_activation_pct": 0.08, "cognitive_timeout_s": 60, "size": 0.01, "max_spread_pct": 0.09, "momentum_threshold": 0.015},
    # Indices — trail after 0.15% to survive entry pullback; 90s timeout
    "US500":      {"class": "index",     "tp_pct": 0.65, "sl_pct": 0.30, "trail_activation_pct": 0.15, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.06, "momentum_threshold": 0.025},
    "US30":       {"class": "index",     "tp_pct": 0.65, "sl_pct": 0.30, "trail_activation_pct": 0.15, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.06, "momentum_threshold": 0.025},
    "USTECH":     {"class": "index",     "tp_pct": 0.70, "sl_pct": 0.33, "trail_activation_pct": 0.18, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.07, "momentum_threshold": 0.03},
    "US100":      {"class": "index",     "tp_pct": 0.70, "sl_pct": 0.33, "trail_activation_pct": 0.18, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.07, "momentum_threshold": 0.03},
    "UK100":      {"class": "index",     "tp_pct": 0.65, "sl_pct": 0.30, "trail_activation_pct": 0.15, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.06, "momentum_threshold": 0.025},
    "DE40":       {"class": "index",     "tp_pct": 0.65, "sl_pct": 0.30, "trail_activation_pct": 0.15, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.07, "momentum_threshold": 0.025},
    # Commodities — wide SL to survive volatility spikes; 90s timeout
    "GOLD":       {"class": "commodity", "tp_pct": 0.65, "sl_pct": 0.38, "trail_activation_pct": 0.18, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.10, "momentum_threshold": 0.025},
    "SILVER":     {"class": "commodity", "tp_pct": 0.70, "sl_pct": 0.40, "trail_activation_pct": 0.20, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.20, "momentum_threshold": 0.03},
    "OIL_CRUDE":  {"class": "commodity", "tp_pct": 0.65, "sl_pct": 0.38, "trail_activation_pct": 0.18, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.12, "momentum_threshold": 0.03},
    "NATURALGAS": {"class": "commodity", "tp_pct": 0.90, "sl_pct": 0.55, "trail_activation_pct": 0.25, "cognitive_timeout_s": 90, "size": 0.01, "max_spread_pct": 0.30, "momentum_threshold": 0.04},
    # Volatile stocks — trail after 0.25% to ride the full move; 120s timeout
    "TSLA":       {"class": "stock",     "tp_pct": 1.20, "sl_pct": 0.55, "trail_activation_pct": 0.25, "cognitive_timeout_s": 120, "size": 0.01, "max_spread_pct": 0.25, "momentum_threshold": 0.04},
    "NVDA":       {"class": "stock",     "tp_pct": 1.20, "sl_pct": 0.55, "trail_activation_pct": 0.25, "cognitive_timeout_s": 120, "size": 0.01, "max_spread_pct": 0.25, "momentum_threshold": 0.04},
    "AAPL":       {"class": "stock",     "tp_pct": 1.10, "sl_pct": 0.50, "trail_activation_pct": 0.22, "cognitive_timeout_s": 120, "size": 0.01, "max_spread_pct": 0.18, "momentum_threshold": 0.04},
    "AMZN":       {"class": "stock",     "tp_pct": 1.10, "sl_pct": 0.50, "trail_activation_pct": 0.22, "cognitive_timeout_s": 120, "size": 0.01, "max_spread_pct": 0.18, "momentum_threshold": 0.04},
    "META":       {"class": "stock",     "tp_pct": 1.20, "sl_pct": 0.55, "trail_activation_pct": 0.25, "cognitive_timeout_s": 120, "size": 0.01, "max_spread_pct": 0.22, "momentum_threshold": 0.04},
    "MSFT":       {"class": "stock",     "tp_pct": 1.10, "sl_pct": 0.50, "trail_activation_pct": 0.22, "cognitive_timeout_s": 120, "size": 0.01, "max_spread_pct": 0.18, "momentum_threshold": 0.04},
}

# ── Phase configs ──────────────────────────────────────────────────────────────
PHASES = {
    "FLIGHT": {
        "duration_s":               90,
        "tick_interval_s":          8.0,   # Standard cadence
        "CAPITAL_PRICE_TTL_SECS":   "30",  # Cache prices 30s — in-mem cache makes subsequent ticks instant
        "CAPITAL_TICKER_MEM_TTL":   "30",  # In-memory per-symbol cache TTL
        "CAPITAL_MARKET_CACHE_TTL": "86400",  # Accept day-old market catalogue — it barely changes
        "CAPITAL_SCAN_INTERVAL_SECS": "8",
        "CAPITAL_MONITOR_INTERVAL_SECS": "2",
        "CAPITAL_MAX_POSITIONS":    "4",
        "CAPITAL_SHADOW_MIN_VALIDATE_SECS": "3",
        "CAPITAL_REJECTION_COOLDOWN_SECS": "60",
        "CAPITAL_SLOT_FILL_INTERVAL_SECS": "8",
        # Disable continuous 1s background refresh — it fires 20 req/s and triggers 429
        "CAPITAL_LIVE_REFRESH_ENABLED": "false",
        # 10 workers: 20 symbols in 2 rounds × ~5s = ~10s cold fetch (down from 7 rounds × 8s = 56s)
        "CAPITAL_TICKER_WORKERS": "10",
        "description": "Default config — all intel overlays active (Timeline Oracle + Harmonic Fusion + self-confidence)",
    },
    "STRESS": {
        "duration_s":               180,
        "tick_interval_s":          3.0,   # 3x faster
        "CAPITAL_PRICE_TTL_SECS":   "25",  # Cold-fetch every 25s; in-mem cache makes 8+ intermediate ticks instant
        "CAPITAL_TICKER_MEM_TTL":   "25",  # In-memory per-symbol cache TTL
        "CAPITAL_SCAN_INTERVAL_SECS": "3", # Scan every 3s
        "CAPITAL_MONITOR_INTERVAL_SECS": "1",
        "CAPITAL_MAX_POSITIONS":    "6",   # More concurrent positions
        "CAPITAL_SHADOW_MIN_VALIDATE_SECS": "1",  # Shadow validates in 1s
        "CAPITAL_REJECTION_COOLDOWN_SECS": "20",   # Re-try rejected symbols faster
        "CAPITAL_SLOT_FILL_INTERVAL_SECS": "3",
        "CAPITAL_LIVE_REFRESH_ENABLED": "false",
        "CAPITAL_TICKER_WORKERS": "10",   # 10 workers — same as FLIGHT
        "CAPITAL_MARKET_CACHE_TTL": "86400",  # Accept day-old market catalogue
        "description": "HFT mode — 3s tick, 6 positions, shadow validates in 1s, all intel active",
    },
}

# ── Logging ───────────────────────────────────────────────────────────────────
_log_lock = threading.Lock()
_logfh = None

def log(line: str, prefix: str = ""):
    ts  = time.strftime("%H:%M:%S")
    msg = f"[{ts}] {prefix:<8} {line}"
    with _log_lock:
        print(msg, flush=True)
        if _logfh:
            _logfh.write(msg + "\n")
            _logfh.flush()

def separator(char="─", label=""):
    line = char * 60
    if label:
        pad = (56 - len(label)) // 2
        line = char * pad + f" {label} " + char * (56 - pad - len(label))
    log(line)


def _force_close_all(trader, reason: str, timeout_s: float = 12) -> None:
    """Close all open positions with a hard timeout so a slow API never hangs the benchmark."""
    import threading
    result_box: list = []

    def _do_close():
        try:
            import aureon.exchanges.capital_cfd_trader as _cdt
            _cdt.CFD_FLAGS["profit_only_closes"] = False
            closed = trader._deadman_close_all(reason)
            result_box.append(closed)
        except Exception as e:
            result_box.append(e)

    t = threading.Thread(target=_do_close, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if not t.is_alive():
        result = result_box[0] if result_box else []
        if isinstance(result, Exception):
            log(f"Close failed: {result} — continuing", prefix="WARN")
        elif result:
            log(f"Closed {len(result)} positions: {[r.get('symbol','?') for r in result]}", prefix="INIT")
        else:
            log("No open positions to close.", prefix="INIT")
    else:
        log(f"Close timed out after {timeout_s}s — skipping, continuing anyway", prefix="WARN")
        # Clear local position list so the benchmark starts fresh even if exchange has stale state
        trader.positions = []


# ── Benchmark state ───────────────────────────────────────────────────────────
class BenchmarkStats:
    def __init__(self, phase: str):
        self.phase       = phase
        self.ticks       = 0
        self.tick_times  = []
        self.trades_opened = 0
        self.trades_closed = 0
        self.symbols_seen: set = set()
        self.top_scored: list  = []
        self.rejections: dict  = {}
        self.start       = time.time()

    def add_tick(self, elapsed_s: float, closed: list, candidates: list):
        self.ticks += 1
        self.tick_times.append(elapsed_s)
        self.trades_closed += len(closed)
        for c in candidates:
            self.symbols_seen.add(c.get("symbol", "?"))
            if float(c.get("score", 0) or 0) > 0:
                self.top_scored.append({
                    "ts":     time.strftime("%H:%M:%S"),
                    "symbol": c.get("symbol"),
                    "dir":    c.get("direction"),
                    "score":  round(float(c.get("score", 0) or 0), 3),
                    "change": round(float(c.get("change_pct", 0) or 0), 3),
                    "spread": round(float(c.get("spread_pct", 0) or 0), 4),
                    "reason": c.get("reject_reason") or c.get("hft_reason") or "",
                })
        self.top_scored = sorted(self.top_scored, key=lambda x: -x["score"])[:20]

    def report(self):
        elapsed = time.time() - self.start
        avg_tick = sum(self.tick_times) / len(self.tick_times) if self.tick_times else 0
        tpm = self.ticks / (elapsed / 60) if elapsed > 0 else 0
        separator("=", f"PHASE {self.phase} RESULTS")
        log(f"Duration:        {elapsed:.0f}s")
        log(f"Total ticks:     {self.ticks}  ({tpm:.1f}/min)")
        log(f"Avg tick time:   {avg_tick*1000:.0f}ms")
        log(f"Symbols scanned: {len(self.symbols_seen)}  {sorted(self.symbols_seen)}")
        log(f"Trades opened:   {self.trades_opened}")
        log(f"Trades closed:   {self.trades_closed}")
        separator()
        if self.top_scored:
            log("TOP SCORING CANDIDATES (highest opportunity signals seen):")
            for item in self.top_scored[:10]:
                log(f"  {item['ts']} {item['symbol']:<12} {item['dir']:<5} "
                    f"score={item['score']:.3f}  move={item['change']:+.3f}%  "
                    f"spread={item['spread']:.4f}%  {item['reason']}")
        else:
            log("No positive-score candidates — all rejected at gate.")
        separator("=")


# ── Phase runner ──────────────────────────────────────────────────────────────
def run_phase(trader, phase_name: str, cfg: dict, universe: dict) -> BenchmarkStats:
    # Patch universe on the running trader instance
    from aureon.exchanges.capital_cfd_trader import CAPITAL_UNIVERSE as _CU
    _CU.clear()
    _CU.update(universe)
    # Also patch the module-level dict the trader reads at scan time
    try:
        import aureon.exchanges.capital_cfd_trader as _cdt_mod
        _cdt_mod.CAPITAL_UNIVERSE.clear()
        _cdt_mod.CAPITAL_UNIVERSE.update(universe)
    except Exception:
        pass

    stats   = BenchmarkStats(phase_name)
    end     = time.time() + cfg["duration_s"]
    tick_iv = cfg["tick_interval_s"]

    separator("─", f"PHASE {phase_name} START — {cfg['description']}")
    log(f"Universe: {len(universe)} symbols — tick every {tick_iv}s — {cfg['duration_s']}s window")

    tick_num = 0
    while time.time() < end:
        tick_num += 1
        t0 = time.time()
        try:
            closed = trader.tick()
        except Exception as exc:
            log(f"tick() error: {exc}", prefix="ERROR")
            closed = []
        elapsed = time.time() - t0

        candidates = list(getattr(trader, "_latest_candidate_snapshot", []) or [])
        stats.add_tick(elapsed, closed, candidates)
        stats.trades_opened = len(getattr(trader, "positions", []))

        # Diagnostics: prices + rate-limit state + change_pct sample
        try:
            prices_dict = getattr(trader, "_prices", {}) or {}
            n_priced = sum(1 for v in prices_dict.values() if float(v.get("price", 0) or 0) > 0)
            n_total  = len(prices_dict)
            rl_until = float(getattr(getattr(trader, "client", None), "_rate_limit_until", 0) or 0)
            rl_left  = max(0.0, rl_until - time.time())
            univ_sz  = len(list((getattr(trader, "_active_universe", lambda: {})()).keys()))
            # Sample change_pct values to diagnose scoring gate
            chg_samples = {k: round(float(v.get("change_pct", 0) or 0), 5)
                           for k, v in list(prices_dict.items())[:6] if float(v.get("price", 0) or 0) > 0}
            log(f"  DIAG: prices={n_priced}/{n_total} universe={univ_sz} rate_limit_remaining={rl_left:.0f}s", prefix="DIAG")
            log(f"  DIAG: change_pct_sample={chg_samples}", prefix="DIAG")
        except Exception as de:
            log(f"  DIAG error: {de}", prefix="DIAG")

        # Real-time tick summary
        n_pos    = len(getattr(trader, "positions", []))
        n_shadow = len(getattr(trader, "shadow_trades", []))
        top      = max(candidates, key=lambda c: float(c.get("score", 0) or 0), default=None) if candidates else None
        top_str  = ""
        if top and float(top.get("score", 0) or 0) > 0:
            top_str = (f"  BEST: {top.get('symbol')} {top.get('direction')} "
                       f"score={float(top.get('score',0)):.3f} "
                       f"move={float(top.get('change_pct',0)):+.3f}%")

        log(f"tick#{tick_num:03d}  {elapsed*1000:.0f}ms  pos={n_pos}  shadows={n_shadow}  "
            f"candidates={len(candidates)}{top_str}",
            prefix=phase_name[:6])

        for rec in closed:
            sym    = rec.get("symbol", "?")
            pnl    = float(rec.get("pnl_gbp", 0.0) or 0.0)
            reason = rec.get("close_reason") or rec.get("reason") or "?"
            log(f"  CLOSED {sym}  P&L={pnl:+.4f} GBP  reason={reason}", prefix="TRADE")

        # Position state: show TP/SL vs current price so we can see the wave being ridden
        for pos in getattr(trader, "positions", []):
            cp   = float(getattr(pos, "current_price", 0) or 0)
            ep   = float(getattr(pos, "entry_price", 0) or 0)
            tp   = float(getattr(pos, "tp_price", 0) or 0)
            sl   = float(getattr(pos, "sl_price", 0) or 0)
            pnl_pct = ((cp - ep) / ep * 100 if ep > 0 and getattr(pos, "direction", "") == "BUY"
                       else (ep - cp) / ep * 100 if ep > 0 else 0)
            log(f"  POS {getattr(pos,'symbol','?'):<12} {getattr(pos,'direction','?'):<5} "
                f"entry={ep:.5g}  now={cp:.5g}  tp={tp:.5g}  sl={sl:.5g}  pnl={pnl_pct:+.3f}%",
                prefix="MON")

        # Decision transparency: log every scored candidate
        for c in sorted(candidates, key=lambda x: -float(x.get("score", 0) or 0))[:5]:
            sym  = c.get("symbol", "?")
            scr  = float(c.get("score", 0) or 0)
            why  = c.get("reject_reason") or c.get("hft_reason") or c.get("intel_reason") or ""
            chg  = float(c.get("change_pct", 0) or 0)
            sprd = float(c.get("spread_pct", 0) or 0)
            tl   = float(c.get("timeline_bonus", 0) or 0)
            fu   = float(c.get("fusion_bonus", 0) or 0)
            cf   = float(c.get("self_confidence_boost", 1.0) or 1.0)
            wf   = float(c.get("wave_factor", 1.0) or 1.0)
            rf   = float(c.get("range_factor", 1.0) or 1.0)
            om   = float(c.get("onset_mag", 0.0) or 0.0)
            intel_str = (f"  tl={tl:+.2f} fu={fu:+.2f} cf_x{cf:.2f}"
                         if (tl or fu or cf != 1.0) else "")
            wave_str  = f"  wf={wf:.2f}" if wf < 0.95 else ""
            range_str = f"  rf={rf:.2f}" if rf < 0.95 else ""
            onset_str = f"  om={om:+.3f}%" if om != chg else ""   # only show if different from total move
            if abs(scr) > 0.001 or why:
                log(f"    {sym:<12} {c.get('direction','?'):<5} "
                    f"score={scr:.4f}  move={chg:+.3f}%  spread={sprd:.4f}%{onset_str}{wave_str}{range_str}{intel_str}  {why}",
                    prefix="SCAN")

        remaining = tick_iv - (time.time() - t0)
        if remaining > 0:
            time.sleep(remaining)

    stats.report()
    return stats


# ── GOAL injection ────────────────────────────────────────────────────────────
def inject_hft_goal():
    """Write the HFT goal into the GoalExecutionEngine if reachable."""
    try:
        from aureon.core.goal_execution_engine import GoalExecutionEngine
        gee = GoalExecutionEngine()
        gee.submit_goal(
            "Capitalize on Capital.com volatility — scan all instruments, "
            "enter fast in any direction on momentum, exit at target. "
            "Maximize trade frequency and P&L turn rate."
        )
        log("HFT goal injected into GoalExecutionEngine.", prefix="GOAL")
    except Exception as e:
        log(f"Goal injection skipped ({e}) — organism will use its own goals.", prefix="GOAL")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    global _logfh
    _logfh = open(LOG_PATH, "w", encoding="utf-8")

    separator("=", "CAPITAL HFT STRESS TEST")
    log(f"Session: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Log:     {LOG_PATH}")
    separator()

    inject_hft_goal()

    # ── Apply FLIGHT env vars ─────────────────────────────────────────────
    os.environ.pop("CAPITAL_SKIP_INTEL_OVERLAYS", None)   # never inherit stale skip flag
    for k, v in PHASES["FLIGHT"].items():
        if k.startswith("CAPITAL_"):
            os.environ[k] = v

    log("Importing CapitalCFDTrader...", prefix="INIT")
    try:
        from aureon.exchanges.capital_cfd_trader import CapitalCFDTrader, CAPITAL_UNIVERSE
    except Exception as e:
        log(f"Import failed: {e}", prefix="FATAL")
        _logfh.close()
        return

    log("Instantiating trader...", prefix="INIT")
    try:
        trader = CapitalCFDTrader()
    except Exception as e:
        log(f"Trader init failed: {e}", prefix="FATAL")
        _logfh.close()
        return

    # Disable components that make blocking network calls outside the Capital.com tick path
    trader.system_hub_registry = None
    trader.orchestrator = None
    trader.unified_registry = None
    log("Mind-map scan + orchestrator + unified registry disabled for HFT mode.", prefix="INIT")

    # Monitoring fixes: live prices + wave riding for both phases
    import aureon.exchanges.capital_cfd_trader as _cdt_monitor
    _cdt_monitor.CFD_FLAGS["profit_only_closes"] = False  # close at TP/SL regardless of P&L sign
    _cdt_monitor.CFD_FLAGS["trailing_stop"]      = True   # trail SL when in profit — ride the wave
    log("Monitoring: profit_only_closes=OFF, trailing_stop=ON (wave riding active).", prefix="INIT")

    # Warm up — first tick establishes Capital.com session (no position opening)
    log("Warming up (first tick — establishes session + fetches prices)...", prefix="INIT")
    try:
        import aureon.exchanges.capital_cfd_trader as _cdt_warmup
        _orig_fsf = _cdt_warmup.CAPITAL_FORCE_SLOT_FILL
        _cdt_warmup.CAPITAL_FORCE_SLOT_FILL = False   # price fetch + sync only
        try:
            trader.tick()
        finally:
            _cdt_warmup.CAPITAL_FORCE_SLOT_FILL = _orig_fsf
        log("Warm-up complete.", prefix="INIT")
    except Exception as e:
        log(f"Warm-up tick failed: {e} — continuing anyway", prefix="WARN")

    # ─── PRE-FLIGHT: Close any stale positions left from prior sessions ───
    log("Closing any pre-existing positions before FLIGHT...", prefix="INIT")
    _force_close_all(trader, "BENCHMARK_CLEANUP", timeout_s=12)

    # ─── PHASE 1: FLIGHT TEST ──────────────────────────────────────────────
    # Standard universe (already in CAPITAL_UNIVERSE from module)
    from aureon.exchanges.capital_cfd_trader import CAPITAL_UNIVERSE as STD_UNIVERSE
    std_copy = dict(STD_UNIVERSE)
    flight_stats = run_phase(trader, "FLIGHT", PHASES["FLIGHT"], std_copy)

    # ─── INTER-PHASE CLEANUP: Close FLIGHT positions so STRESS starts clean ──
    log("Closing FLIGHT positions before STRESS...", prefix="INIT")
    _force_close_all(trader, "FLIGHT_TO_STRESS", timeout_s=12)
    trader.shadow_trades = []
    log("Shadow trades cleared.", prefix="INIT")

    # ─── PHASE 2: STRESS TEST ─────────────────────────────────────────────
    # Apply HFT env overrides
    for k, v in PHASES["STRESS"].items():
        if k.startswith("CAPITAL_"):
            os.environ[k] = v

    # Patch module-level constants — they are frozen at import time from FLIGHT env.
    # Must update directly; os.environ changes after import have no effect on them.
    import aureon.exchanges.capital_cfd_trader as _cdt_mod
    _cdt_mod.CAPITAL_SLOT_FILL_INTERVAL_SECS   = float(PHASES["STRESS"]["CAPITAL_SLOT_FILL_INTERVAL_SECS"])
    _cdt_mod.CAPITAL_SHADOW_MIN_VALIDATE_SECS  = float(PHASES["STRESS"]["CAPITAL_SHADOW_MIN_VALIDATE_SECS"])
    _cdt_mod.CAPITAL_REJECTION_COOLDOWN_SECS   = float(PHASES["STRESS"]["CAPITAL_REJECTION_COOLDOWN_SECS"])
    _cdt_mod.CFD_CONFIG["scan_interval_secs"]   = float(PHASES["STRESS"]["CAPITAL_SCAN_INTERVAL_SECS"])
    _cdt_mod.CFD_CONFIG["monitor_interval"]     = float(PHASES["STRESS"]["CAPITAL_MONITOR_INTERVAL_SECS"])
    _cdt_mod.CFD_CONFIG["max_positions"]        = float(PHASES["STRESS"]["CAPITAL_MAX_POSITIONS"])
    # HFT mode: close positions at TP/SL even if in loss — required for full cycle turnover
    _cdt_mod.CFD_FLAGS["profit_only_closes"]    = False
    # Enable all local intel scoring: Timeline Oracle + Harmonic Fusion + self-confidence multiplier
    _cdt_mod.CAPITAL_SKIP_INTEL_OVERLAYS        = False
    # Patch the class constant on the live instance so shadow promotion uses correct window
    trader.SHADOW_MIN_VALIDATE = float(PHASES["STRESS"]["CAPITAL_SHADOW_MIN_VALIDATE_SECS"])

    # Reset scan/monitor/slot-fill timers so new intervals take effect immediately
    trader._last_scan    = 0.0
    trader._last_monitor = 0.0
    trader._last_slot_fill_attempt = {"BUY": 0.0, "SELL": 0.0}
    log("STRESS module constants patched + timers reset.", prefix="INIT")

    stress_stats = run_phase(trader, "STRESS", PHASES["STRESS"], HFT_UNIVERSE)

    # ─── FINAL SUMMARY ────────────────────────────────────────────────────
    separator("=", "BENCHMARK SUMMARY")
    for stats in [flight_stats, stress_stats]:
        tpm = stats.ticks / (PHASES[stats.phase]["duration_s"] / 60)
        avg = sum(stats.tick_times) / len(stats.tick_times) if stats.tick_times else 0
        log(f"{stats.phase:<8}  ticks={stats.ticks}  ticks/min={tpm:.1f}  "
            f"avg_tick={avg*1000:.0f}ms  symbols={len(stats.symbols_seen)}  "
            f"trades={stats.trades_opened}  closed={stats.trades_closed}")
    separator("=")

    # Save JSON summary
    summary = {
        "session_start": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phases": {
            p.phase: {
                "ticks": p.ticks,
                "avg_tick_ms": round(sum(p.tick_times)/len(p.tick_times)*1000 if p.tick_times else 0, 1),
                "trades_opened": p.trades_opened,
                "trades_closed": p.trades_closed,
                "symbols": sorted(p.symbols_seen),
                "top_signals": p.top_scored[:5],
            }
            for p in [flight_stats, stress_stats]
        }
    }
    json_path = HERE / "capital_hft_benchmark.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    log(f"JSON summary: {json_path}")
    _logfh.close()


if __name__ == "__main__":
    main()
