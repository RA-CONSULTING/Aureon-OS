#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         AUREON UNIFIED TRADING HUB — ALL SYSTEMS WIRED INTO ONE HIVE         ║
║                                                                              ║
║  Cloned from Aureon-OS: 139 trading systems integrated                     ║
║  Scanners: 18 | Bots: 32 | Analyzers: 41 | Harmonic: 36 | Planetary: 12   ║
║                                                                              ║
║  SIGNAL FUSION:                                                              ║
║    Every scanner → signal score (0-1)                                        ║
║    All scores → weighted fusion → unified direction/confidence               ║
║    Auto-hive executes when fusion score > threshold                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import math
import logging
import importlib.util
import inspect
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════
RADAR_DIR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")
SCANNERS_DIR = RADAR_DIR / "scanners"
BOTS_DIR = RADAR_DIR / "bots"
ANALYZERS_DIR = RADAR_DIR / "analyzers"
HARMONIC_DIR = RADAR_DIR / "harmonic"
PLANETARY_DIR = RADAR_DIR / "planetary"

# ═══════════════════════════════════════════════════════════════════════════════
# CONSOLE UTF-8 SHIM — aureon.utils.console_utf8 exists only in the external
# Aureon-OS checkout, not in workspace upstream (regular package: no namespace
# merge). Inject a verbatim copy so scanner/analyzer imports don't fail.
# ═══════════════════════════════════════════════════════════════════════════════
def _ensure_console_utf8() -> None:
    try:
        import aureon.utils.console_utf8  # noqa: F401
        return
    except Exception:
        pass
    shim_path = RADAR_DIR / "_console_utf8_shim.py"
    try:
        spec = importlib.util.spec_from_file_location(
            "aureon.utils.console_utf8", shim_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["aureon.utils.console_utf8"] = mod
    except Exception as e:
        logging.getLogger("AUREON_HUB").warning(
            f"console_utf8 shim injection failed (non-fatal): {e}")


_ensure_console_utf8()

# Import-time guard: several upstream modules open TCP/WebSocket connections at
# import (whale orderbooks, exchange feeds). A filtered host (e.g. FCA-blocked
# Binance) leaves those connects hanging for many minutes and stalls the whole
# hive. Modules that legitimately need long-lived sockets set their own
# timeouts after import.
import socket as _socket
_socket.setdefaulttimeout(30)


def _preempt_hivemind_deadlock() -> None:
    """probability_ultimate_intelligence builds the ENTIRE QueenHiveMind
    (take_full_control -> kraken rate-limited universe discovery) inside its
    constructor, called at ecosystem-wiring import time. On this host that
    deadlocks (zero-CPU lock cycle in the kraken token bucket) and stalls the
    hive indefinitely. Pre-empt: keep the real module, replace only the
    singleton constructor with a loudly-degraded version. Scanners that want
    the full matrix can construct it explicitly outside the hub."""
    try:
        import aureon.strategies.probability_ultimate_intelligence as _pui
    except Exception:
        return

    _real_get = _pui.get_ultimate_intelligence

    class _DegradedUltimateIntelligence:
        patterns: list = []
        accuracy: float = 0.0
        degraded_reason = ("QueenHiveMind import-time construction deadlocks on "
                           "this host (kraken rate-limiter/logging lock cycle)")

    def _degraded_get(*args, **kwargs):
        logging.getLogger("AUREON_HUB").warning(
            "probability_ultimate_intelligence DEGRADED: full QueenHiveMind "
            "construction skipped at hub load (import-time deadlock hazard)")
        return _DegradedUltimateIntelligence()

    _pui.get_ultimate_intelligence = _degraded_get


_preempt_hivemind_deadlock()


def _preempt_sonar_spam() -> None:
    """mycelium_whale_sonar.ensure_sonar constructs a WhaleSonar and spawns a
    WhaleSonarLoop thread on EVERY call. The fusion engine's attribute-scan
    probes every public callable per module per symbol per cycle, so any bot
    that imports ensure_sonar leaks an unbounded thread army (observed: 40+
    WhaleSonarLoop threads, 420MB, hub wedged mid-cycle). Pre-empt: replace
    the factory with a loudly-degraded version."""
    try:
        import aureon.core.mycelium_whale_sonar as _mws
    except Exception:
        return

    def _degraded_ensure_sonar(*args, **kwargs):
        logging.getLogger("AUREON_HUB").warning(
            "mycelium_whale_sonar DEGRADED: per-call WhaleSonar construction "
            "skipped at hub load (thread-spam hazard)")
        return None

    _mws.ensure_sonar = _degraded_ensure_sonar


_preempt_sonar_spam()

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(RADAR_DIR / "unified_hub.log")
    ],
    # The import-time pre-emptions above (console_utf8 shim, hivemind/sonar
    # guards) pull in aureon modules that configure the root logger BEFORE
    # this line runs — without force, basicConfig is a silent no-op and the
    # hub writes nothing to unified_hub.log (observed: zero log output from
    # a live run). force=True re-attaches these handlers to the root logger.
    force=True
)
for _h in logging.getLogger().handlers:
    # mark so _ensure_hub_logging() recognizes (and does not duplicate) them
    _h._unified_hub = True  # type: ignore[attr-defined]
logger = logging.getLogger('UNIFIED_HUB')

_HUB_FILE_HANDLER: Optional[logging.FileHandler] = None


def _ensure_hub_logging() -> None:
    """Re-attach the hub's stdout+file handlers if a module wiped them.

    Load-bearing module imports (aureon ecosystem wiring) reconfigure the
    root logger DURING load_all, after this module's basicConfig ran — the
    observed effect was a hub that cycled silently: no 'UNIFIED CYCLE' or
    'FUSED SIGNAL' lines in unified_hub.log or the suite log. Called from
    initialize() and the top of every run_cycle; idempotent and cheap.

    Double-logging guard (suite log grew to ~400MB, every line written
    twice): aureon.utils.aureon_miner WIPES root.handlers at import (win32
    branch) and installs its own stdout handler. Once this function
    re-attached the hub handlers, the root logger carried TWO stdout
    handlers, so every record reached the suite log twice, in two formats
    (observed: ~1.17M duplicate pairs). The guards below drop any stdout
    handler that is not the hub's own, on the root logger and on any
    module logger that still propagates to root, so exactly one handler
    chain writes each record. FileHandlers are never touched.
    """
    global _HUB_FILE_HANDLER
    root = logging.getLogger()

    # Stray root stdout handlers (e.g. aureon_miner's import-time UTF8
    # handler) — remove; the hub's marked handlers below are the one chain.
    for _h in root.handlers[:]:
        if (isinstance(_h, logging.StreamHandler)
                and not isinstance(_h, logging.FileHandler)
                and not getattr(_h, '_unified_hub', False)):
            root.removeHandler(_h)
            _h.close()

    # Module loggers that attached their own stdout handler AND kept
    # propagate=True emit every record twice (own handler + root chain).
    # Where propagation is on, the root chain already carries the record.
    # propagate=False loggers are left alone: their handler is the record's
    # only output path, so removing it would lose messages.
    for _lg in list(logging.Logger.manager.loggerDict.values()):
        if not isinstance(_lg, logging.Logger) or not _lg.propagate:
            continue
        for _h in _lg.handlers[:]:
            if (isinstance(_h, logging.StreamHandler)
                    and not isinstance(_h, logging.FileHandler)):
                _lg.removeHandler(_h)
                _h.close()

    need_stream = not any(
        isinstance(h, logging.StreamHandler)
        and getattr(h, '_unified_hub', False) for h in root.handlers)
    need_file = not any(
        isinstance(h, logging.FileHandler)
        and getattr(h, '_unified_hub', False) for h in root.handlers)
    if need_stream:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'))
        sh._unified_hub = True  # type: ignore[attr-defined]
        root.addHandler(sh)
    if need_file:
        if _HUB_FILE_HANDLER is None or _HUB_FILE_HANDLER.stream is None:
            _HUB_FILE_HANDLER = logging.FileHandler(RADAR_DIR / "unified_hub.log")
            _HUB_FILE_HANDLER.setFormatter(logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'))
            _HUB_FILE_HANDLER._unified_hub = True  # type: ignore[attr-defined]
        root.addHandler(_HUB_FILE_HANDLER)
    root.setLevel(logging.INFO)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class UnifiedSignal:
    timestamp: str
    symbol: str
    direction: str  # LONG, SHORT, NEUTRAL
    confidence: float  # 0.0-1.0
    sources: Dict[str, float]  # source_name: score
    fusion_score: float
    planetary_bias: float
    harmonic_resonance: float
    orderbook_pressure: float
    momentum_score: float
    bot_score: float = 0.0
    
    def to_dict(self):
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# DYNAMIC MODULE LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class AureonModuleLoader:
    """Dynamically loads Aureon OS trading modules."""
    
    def __init__(self):
        self.modules = {}
        self.scanner_instances = {}
        
    # Hard deadline for the whole import phase. Tunable via env var so a
    # resource-constrained host can be given more headroom without editing
    # code; the default 180s safety bound is preserved.
    _LOAD_DEADLINE_SEC = float(
        os.environ.get("AUREON_HUB_LOAD_DEADLINE_SEC", 180))

    def load_all(self):
        """Load all modules with a hard deadline.

        Several upstream modules construct heavy systems at import time
        (the probability-intelligence chain builds the whole QueenHiveMind and
        can stall for many minutes on exchange rate limiters). A module that
        hasn't finished by the deadline is skipped for this cycle but keeps
        loading on a daemon thread — late arrivals still join the hive.
        """
        import threading
        done = threading.Event()

        def _load():
            try:
                self._load_all_inner()
            except Exception as e:
                logging.getLogger("AUREON_HUB").warning(
                    f"Module loading aborted: {e}")
            finally:
                done.set()

        # Re-attach hub handlers before the loader thread starts: upstream
        # modules reconfigure the root logger during import, so the load
        # progress and final summary must be written to unified_hub.log.
        _ensure_hub_logging()
        t = threading.Thread(target=_load, daemon=True, name="module-loader")
        t.start()
        deadline = self._LOAD_DEADLINE_SEC
        if not done.wait(timeout=deadline):
            logging.getLogger("AUREON_HUB").warning(
                f"Module loading incomplete after {deadline:.0f}s: "
                f"{len(self.modules)} systems aboard; proceeding with the "
                f"available hive")
        return self.modules

    def _load_all_inner(self):
        """Load all available scanner/analyzer modules."""
        counts = {"harmonic": 0, "planetary": 0, "scanner": 0,
                  "bot": 0, "analyzer": 0}

        # Load harmonic + planetary FIRST: the 180s deadline below used to
        # starve them every cycle (heavy scanner/bot imports consumed the
        # whole window, so harmonic:/planetary: always loaded zero modules).
        for f in HARMONIC_DIR.glob("*.py"):
            if f.name.startswith("__"):
                continue
            try:
                mod = self._load_module(f, category="harmonic")
                self.modules[f"harmonic:{f.stem}"] = mod
                counts["harmonic"] += 1
                logger.info(f"Loaded harmonic: {f.stem}")
            except Exception as e:
                logger.warning(f"Failed to load harmonic:{f.stem}: {e}")

        for f in PLANETARY_DIR.glob("*.py"):
            if f.name.startswith("__"):
                continue
            try:
                mod = self._load_module(f, category="planetary")
                self.modules[f"planetary:{f.stem}"] = mod
                counts["planetary"] += 1
                logger.info(f"Loaded planetary: {f.stem}")
            except Exception as e:
                logger.warning(f"Failed to load planetary:{f.stem}: {e}")

        # Load scanners
        for f in SCANNERS_DIR.glob("*.py"):
            if f.name.startswith("__"):
                continue
            try:
                mod = self._load_module(f, category="scanner")
                self.modules[f"scanner:{f.stem}"] = mod
                counts["scanner"] += 1
                logger.info(f"Loaded scanner: {f.stem}")
            except Exception as e:
                logger.warning(f"Failed to load scanner:{f.stem}: {e}")

        # Load bots (executors/traders) — BOTS_DIR was defined but never
        # globbed, leaving ~32 systems permanently off the hive.
        # Skip the ORCA live monitor: it is a position-monitoring child
        # process, not a signal source, and probing it submits real orders.
        _SKIP_BOTS = {"orca_live_monitor"}
        for f in BOTS_DIR.glob("*.py"):
            if f.name.startswith("__") or f.stem in _SKIP_BOTS:
                continue
            try:
                mod = self._load_module(f, category="bot")
                self.modules[f"bot:{f.stem}"] = mod
                counts["bot"] += 1
                logger.info(f"Loaded bot: {f.stem}")
            except Exception as e:
                logger.warning(f"Failed to load bot:{f.stem}: {e}")

        # Load analyzers
        for f in ANALYZERS_DIR.glob("*.py"):
            if f.name.startswith("__"):
                continue
            try:
                mod = self._load_module(f, category="analyzer")
                self.modules[f"analyzer:{f.stem}"] = mod
                counts["analyzer"] += 1
                logger.info(f"Loaded analyzer: {f.stem}")
            except Exception as e:
                logger.warning(f"Failed to load analyzer:{f.stem}: {e}")

        # Harmonic + planetary are loaded FIRST in this method (deadline-starve
        # fix) — the old tail loops were removed.

        # Re-attach hub handlers one last time before the summary: the last
        # analyzer imports may have wiped the root logger again.
        _ensure_hub_logging()
        summary = " | ".join(
            f"{k}:{v}" for k, v in counts.items())
        logger.info(f"Total modules loaded: {len(self.modules)} ({summary})")
        return self.modules
    
    def _load_module(self, path: Path, category: str = "aureon_radar"):
        # Use a unique sys.modules key so duplicate stems across categories
        # (e.g. harmonic/aureon_market_energy_field.py and
        # planetary/aureon_market_energy_field.py) do not overwrite each other.
        unique_name = f"aureon_radar.{category}.{path.stem}"
        spec = importlib.util.spec_from_file_location(unique_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = mod
        spec.loader.exec_module(mod)
        return mod

# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL FUSION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class SignalFusionEngine:
    """
    Fuses signals from ALL Aureon systems into a unified trading decision.
    
    Weighting (sum = 1.00):
    - Scanners: 0.24 (momentum, movers, ocean wave)
    - Analyzers: 0.20 (orderbook, whale, waveform)
    - Harmonic: 0.20 (resonance, coherence)
    - Planetary: 0.16 (planetary bands)
    - Bots: 0.20 (reclaimer, turbo, sniper modes)

    The 0.20 bot weight is the documented share from the original fusion
    spec; the other four weights are the old values scaled uniformly by 0.8
    (30:25:25:20 → 24:20:20:16) so the ratio between them is preserved and
    the total stays 1.00.
    """

    def __init__(self, modules: Dict):
        self.modules = modules
        self.weights = {
            "scanner": 0.50,
            "analyzer": 0.15,
            "harmonic": 0.15,
            "planetary": 0.10,
            "bot": 0.10
        }
        self.history = []
        # Modules that exceeded the extraction deadline once are parked from
        # fusion permanently (their own threads keep running) — a blocking
        # callable must never stall every cycle.
        self.blocking_modules = set()
        self._blocking_logged = set()
        # cached class instances for _probe_module_classes (per module)
        self._probe_instances: Dict[str, list] = {}

    _EXTRACTION_TIMEOUT_SEC = 5.0

    # CLI entry points that must never be probed as signal functions — they
    # are loops, not extractors (bug-hunt: whale_agent.main parked the hub
    # forever inside `while True: time.sleep(1)`).
    _NEVER_CALL = frozenset({
        'main', 'run', 'start', 'stop', 'run_forever', 'run_forever_ssl',
        'main_loop', 'cli', 'entrypoint', 'launch', 'serve', 'listen', 'loop',
        'execute', 'fire', 'go', 'begin', 'boot', 'start_all', 'monitor',
        'watch', 'poll', 'spin', 'work', 'process',
        'ensure_sonar',  # per-call WhaleSonar thread spawn (thread-spam leak)
        # ORCA live monitor: must never be probed as a signal extractor;
        # calling any of these with (symbol, price) starts a position loop
        # or submits orders inside the hub process.
        'monitor_and_trade', 'run_all_test_orders', 'run_test_order',
        'run_balance_price_check', 'submit_exit_order', 'get_all_positions',
    })
        
    def scan_all(self, symbol: str, price: float) -> UnifiedSignal:
        """Run ALL systems and fuse their signals."""
        sources = {}
        
        # Run each module and extract signals
        for name, mod in self.modules.items():
            if name in self.blocking_modules:
                continue
            try:
                score = self._extract_with_timeout(name, mod, symbol, price)
                if score is not None:
                    # Contract enforcement: every source speaks [-1, 1].
                    # Bug-hunt 2026-09-06: a harmonic module among the
                    # newly-loaded 37 returned raw unbounded magnitudes
                    # (harm=35877 on OIL_CRUDE -> fusion 7175 -> bogus conf
                    # 1.0 signals firing the shadow arm). Anything outside
                    # the contract is clamped, never trusted.
                    sources[name] = max(-1.0, min(1.0, float(score)))
            except TimeoutError:
                self.blocking_modules.add(name)
                if name not in self._blocking_logged:
                    self._blocking_logged.add(name)
                    logger.warning(
                        f"{name} exceeded the {self._EXTRACTION_TIMEOUT_SEC:.0f}s extraction "
                        f"deadline — parked from signal fusion (its own threads keep running)")
            except Exception as e:
                logger.debug(f"{name} failed for {symbol}: {e}")
        
        # Calculate category scores
        scanner_scores = [v for k, v in sources.items() if k.startswith("scanner:")]
        analyzer_scores = [v for k, v in sources.items() if k.startswith("analyzer:")]
        harmonic_scores = [v for k, v in sources.items() if k.startswith("harmonic:")]
        planetary_scores = [v for k, v in sources.items() if k.startswith("planetary:")]
        bot_scores = [v for k, v in sources.items() if k.startswith("bot:")]

        # Owner decree 2026-09-07: use the strongest scanner signal rather than
        # the average, so a high-confidence volatility target is not diluted by
        # other scanners that have no view on the same symbol.
        avg_scanner = max(scanner_scores, key=abs) if scanner_scores else 0
        avg_analyzer = sum(analyzer_scores) / len(analyzer_scores) if analyzer_scores else 0
        avg_harmonic = sum(harmonic_scores) / len(harmonic_scores) if harmonic_scores else 0
        avg_planetary = sum(planetary_scores) / len(planetary_scores) if planetary_scores else 0
        avg_bot = sum(bot_scores) / len(bot_scores) if bot_scores else 0

        # Fusion score (weighted) — bots folded in at their documented 0.20
        # share; every loaded category contributes.
        fusion = (
            avg_scanner * self.weights["scanner"] +
            avg_analyzer * self.weights["analyzer"] +
            avg_harmonic * self.weights["harmonic"] +
            avg_planetary * self.weights["planetary"] +
            avg_bot * self.weights["bot"]
        )
        
        # Determine direction from net score
        if fusion > 0.2:
            direction = "LONG"
            confidence = min(fusion, 1.0)
        elif fusion < -0.2:
            direction = "SHORT"
            confidence = min(abs(fusion), 1.0)
        else:
            direction = "NEUTRAL"
            confidence = 0.0
        
        signal = UnifiedSignal(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            sources=sources,
            fusion_score=fusion,
            planetary_bias=avg_planetary,
            harmonic_resonance=avg_harmonic,
            orderbook_pressure=avg_analyzer,
            momentum_score=avg_scanner,
            bot_score=avg_bot
        )
        
        self.history.append(signal)
        return signal
    
    def _extract_with_timeout(self, name: str, mod, symbol: str, price: float) -> Optional[float]:
        """Run _extract_signal on a daemon thread with a hard deadline.

        A module callable that blocks forever (e.g. a CLI `main` probed by
        the attribute-scan fallback) must not stall the cycle; the daemon
        thread is abandoned and the module is parked by the caller.
        """
        import threading
        box: Dict[str, object] = {}

        def _work():
            try:
                box["score"] = self._extract_signal(mod, symbol, price)
            except Exception as e:  # surfaced as a normal per-module failure
                box["err"] = e

        t = threading.Thread(target=_work, daemon=True,
                             name=f"extract-{name.split(':', 1)[-1]}")
        t.start()
        t.join(self._EXTRACTION_TIMEOUT_SEC)
        if t.is_alive():
            raise TimeoutError(f"{name} extraction exceeded "
                               f"{self._EXTRACTION_TIMEOUT_SEC:.0f}s")
        if "err" in box:
            raise box["err"]
        return box.get("score")

    def _extract_signal(self, mod, symbol: str, price: float) -> Optional[float]:
        """Extract a signal score (-1 to 1) from a module."""
        # Try common method names
        for method_name in ['scan', 'analyze', 'signal', 'evaluate', 'score', 'predict']:
            if hasattr(mod, method_name):
                method = getattr(mod, method_name)
                try:
                    result = method(symbol, price)
                    # Bug-hunt 2026-09-07: some modules expose async scan()
                    # coroutines. Calling them without awaiting triggers a
                    # RuntimeWarning and leaves the coroutine unawaited.
                    if inspect.iscoroutine(result):
                        result.close()
                        continue
                    score = self._coerce_score(result)
                    if score is not None:
                        return score
                except:
                    pass

        # Class-based systems: this clone's modules mostly define scanner /
        # analyzer CLASSES (e.g. MoversShakersScanner.scan()), not module-
        # level functions — probing only the module surface always returned
        # None, so fusion was 0.000 for every symbol. Instantiate probe-able
        # classes (guarded by the same 5s deadline + parking) and ask them.
        score = self._probe_module_classes(mod, symbol, price)
        if score is not None:
            return score

        # Try to find any callable that returns a number
        for attr_name in dir(mod):
            if attr_name.startswith('_') or attr_name in self._NEVER_CALL:
                continue
            attr = getattr(mod, attr_name)
            # Bug-hunt 2026-09-07: skip CLASSES — calling a class with
            # (symbol, price) constructs it with garbage args (e.g.
            # WhaleOrderbookAnalyzer("BTCUSD", 80165.17) → poll_symbols=float
            # → 'float' object is not iterable every cycle, plus a fresh
            # exchange-client leak per cycle). Classes are probed separately,
            # guarded, in _probe_module_classes.
            if inspect.isclass(attr):
                continue
            if callable(attr) and attr_name not in ['scan_all', 'load_all']:
                try:
                    result = attr(symbol, price)
                    if inspect.iscoroutine(result):
                        result.close()
                        continue
                    if isinstance(result, (int, float)) \
                            and not isinstance(result, bool):
                        return float(result)
                except:
                    pass

        return None

    _PROBE_METHODS = ('scan', 'analyze', 'signal', 'evaluate', 'score', 'predict')

    # Class constructors containing these tokens are never instantiated by
    # the probe: on an ARMED radar with a released capital gate, a probe
    # must never touch a live order-firing surface.
    _INIT_RISK_TOKENS = ('place_order', 'create_order', 'execute_order',
                         'submit_order', 'orders.create', 'create_market_order',
                         'place_market', 'fire_order', 'send_order')

    @staticmethod
    def _coerce_score(result) -> Optional[float]:
        """Map a probe result to a signal score, or None if it isn't one."""
        import inspect
        if inspect.iscoroutine(result) or isinstance(result, bool):
            return None
        if isinstance(result, (int, float)):
            return float(result)
        if isinstance(result, dict):
            if 'score' in result:
                try:
                    return float(result['score'])
                except (TypeError, ValueError):
                    return None
            d = result.get('direction')
            try:
                conf = float(result.get('confidence', 0.5))
            except (TypeError, ValueError):
                conf = 0.5
            if d in ['LONG', 'BUY', 'UP']:
                return conf
            if d in ['SHORT', 'SELL', 'DOWN']:
                return -conf
        return None

    def _probe_module_classes(self, mod, symbol: str, price: float) -> Optional[float]:
        """Instantiate module-defined classes that expose a probe method and
        ask them for a score. Instances are cached per module so stateful
        scanners keep their history across cycles. Everything runs inside
        the caller's 5s extraction deadline; a class that stalls gets the
        whole module parked, exactly like a stalling function.
        """
        import inspect
        mod_key = getattr(mod, '__name__', str(id(mod)))
        instances = self._probe_instances.get(mod_key)
        if instances is None:
            instances = []
            for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
                if cls.__module__ != mod_key:
                    continue  # imported class, not defined by this module
                if not any(callable(getattr(cls, m, None)) for m in self._PROBE_METHODS):
                    continue
                try:
                    init_src = inspect.getsource(cls.__init__)
                except (TypeError, OSError):
                    init_src = ''
                if any(tok in init_src for tok in self._INIT_RISK_TOKENS):
                    continue
                try:
                    instances.append(cls())
                except Exception:
                    continue
            self._probe_instances[mod_key] = instances

        for inst in instances:
            for m in self._PROBE_METHODS:
                meth = getattr(inst, m, None)
                if not callable(meth) or inspect.iscoroutinefunction(meth):
                    continue
                for args in ((symbol, price), (symbol,), (price,), ()):
                    try:
                        result = meth(*args)
                    except TypeError:
                        continue  # wrong arity — try a narrower call
                    except Exception:
                        break     # method itself failed — next method
                    score = self._coerce_score(result)
                    if score is not None:
                        return score
                    break  # ran fine but produced no score — next method
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW TRADING ARM
# ═══════════════════════════════════════════════════════════════════════════════

class ShadowArm:
    """Shadow-trading actuator for the hub's promoted fused signals.

    Lazy-loads shadow_{kraken,binance,alpaca}.py from exchange_adapters/ by
    file path (same technique as AureonModuleLoader._load_module, so no
    sys.path dependence). Fully inert — at debug level only — when the shadow
    modules are absent, fail to import, or throw at call time: the hub loop
    must never break because an arm is broken.

    Routing: a promoted signal (confidence >= _PROMOTE_CONF, direction not
    NEUTRAL) whose symbol contains BTC/ETH/AAPL is offered as a small fixed
    shadow order to every mapped venue with signal_source="hub_fusion".
    FX/metal/oil symbols (EURUSD/GBPUSD/USDJPY/GOLD/...) match nothing and
    are silently skipped. Every venue call is individually try/except-wrapped;
    refusals are logged at debug.

    Expectancy gate (Gary's decree): before each venue propose_signal call,
    exchange_adapters/expectancy_gate.py check() must approve the edge —
    the confidence-scaled expected move must clear 1.25x the venue's real
    round-trip cost (per-venue VENUE_FEES from shadow_executor, not the
    upstream flat 0.2%). Refused venues are skipped (debug log with reason +
    margin); a gate error skips the venue too (fail-closed) and can never
    break dispatch. The gate applies to the shadow arm here; the venue
    wrappers' live_place paths enforce it independently, fail-closed.
    """

    _PROMOTE_CONF = 0.55

    # symbol substring -> {venue: (venue_symbol, fixed_qty)}
    _ASSET_MAP = {
        "BTC":  {"kraken": ("XBTUSD", 0.001), "binance": ("BTCUSDT", 0.001),
                 "alpaca": ("BTC/USD", 0.001)},
        "ETH":  {"kraken": ("ETHUSD", 0.01),  "binance": ("ETHUSDT", 0.01),
                 "alpaca": ("ETH/USD", 0.01)},
        "AAPL": {"alpaca": ("AAPL", 1)},
    }
    _VENUES = ("kraken", "binance", "alpaca")

    def __init__(self):
        self._venues: Dict[str, object] = {}
        self._import_attempted = False
        self._gate_mod: Optional[object] = None
        self._gate_attempted = False

    def _load_gate(self) -> Optional[object]:
        """Load expectancy_gate.py by path, once. None => gate inert."""
        if self._gate_attempted:
            return self._gate_mod
        self._gate_attempted = True
        path = RADAR_DIR / "exchange_adapters" / "expectancy_gate.py"
        try:
            spec = importlib.util.spec_from_file_location(
                "aureon_expectancy_gate", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._gate_mod = mod
            logger.info("shadow arm: expectancy gate online "
                        "(1.25x round-trip cost, per-venue fees)")
        except Exception as e:
            logger.debug(f"shadow arm: expectancy_gate unavailable ({e}) — inert")
        return self._gate_mod

    def _gate_price(self, mod: object, venue_symbol: str) -> Optional[float]:
        """Fresh quote for the gate's information fields, best-effort only.

        Uses the venue wrapper's own _quote_fn when it exposes one; the gate
        decision itself is confidence-based and does not depend on this.
        """
        quote_fn = getattr(mod, "_quote_fn", None)
        if not callable(quote_fn):
            return None
        try:
            quote = quote_fn(str(venue_symbol))
            if not isinstance(quote, dict):
                return None
            for key in ("last", "mid", "bid", "ask", "price"):
                try:
                    value = float(quote.get(key))
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value) and value > 0:
                    return value
        except Exception:
            return None
        return None

    def _load_venues(self) -> Dict[str, object]:
        """Import shadow venue modules once; empty dict if none load."""
        if self._import_attempted:
            return self._venues
        self._import_attempted = True
        for name in self._VENUES:
            path = RADAR_DIR / "exchange_adapters" / f"shadow_{name}.py"
            try:
                spec = importlib.util.spec_from_file_location(
                    f"aureon_shadow_{name}", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                self._venues[name] = mod
            except Exception as e:
                logger.debug(f"shadow arm: shadow_{name} unavailable ({e}) — inert")
        if self._venues:
            logger.info(f"Shadow arm online: {', '.join(sorted(self._venues))}")
        return self._venues

    def dispatch(self, signal: "UnifiedSignal") -> None:
        """Offer one promoted fused signal to the mapped shadow venues."""
        try:
            if signal.direction == "NEUTRAL" or signal.confidence < self._PROMOTE_CONF:
                return
            sym = (signal.symbol or "").upper()
            if not sym:
                return
            venues = self._load_venues()
            if not venues:
                return
            side = "BUY" if signal.direction == "LONG" else "SELL"
            gate = self._load_gate()
            for key, routes in self._ASSET_MAP.items():
                if key not in sym:
                    continue
                for venue, (venue_symbol, qty) in routes.items():
                    mod = venues.get(venue)
                    if mod is None:
                        continue
                    if gate is not None:
                        # Expectancy gate (Gary's decree): skip the venue when
                        # the expected move doesn't clear 1.25x round-trip
                        # cost. Fail-closed: a gate error skips the venue but
                        # never breaks dispatch.
                        try:
                            gate_price = (getattr(signal, "price", None) or
                                          self._gate_price(mod, venue_symbol))
                            verdict = gate.check(
                                venue=venue, symbol=venue_symbol, side=side,
                                qty=qty, price=gate_price,
                                confidence=float(signal.confidence))
                            if not verdict.get("allowed"):
                                logger.debug(
                                    f"shadow arm: {venue} {venue_symbol} gated "
                                    f"({verdict.get('reason')}) "
                                    f"margin={verdict.get('margin_pct')} "
                                    f"floor={verdict.get('capture_floor_pct')} "
                                    f"{verdict.get('detail') or ''}")
                                continue
                        except Exception as e:
                            logger.debug(
                                f"shadow arm: expectancy gate error for {venue} "
                                f"({e}) — skipping venue (fail-closed)")
                            continue
                    try:
                        result = mod.propose_signal(
                            venue_symbol, side, qty,
                            signal_source="hub_fusion",
                            signal_confidence=float(signal.confidence),
                        )
                        self._log_result(venue, venue_symbol, result)
                    except Exception as e:
                        logger.debug(
                            f"shadow arm: {venue} propose_signal({venue_symbol}) "
                            f"failed: {e}")
                return  # one asset class per symbol
        except Exception as e:
            logger.debug(f"shadow arm dispatch failed (non-fatal): {e}")

    def _log_result(self, venue: str, symbol: str, result: object) -> None:
        """Refusals at debug; anything else noteworthy at info."""
        try:
            if not isinstance(result, dict):
                return
            event = result.get("event") or result.get("status")
            if not event:
                return
            if str(event).startswith("refused"):
                logger.debug(f"shadow arm: {venue} {symbol} refused ({event})")
            else:
                logger.info(f"shadow arm: {venue} {symbol} -> {event}")
        except Exception:
            pass

    def mark_all(self) -> None:
        """Stops/TPs + mark-to-market for open shadow positions, once per cycle."""
        try:
            venues = self._load_venues()
            for name, mod in venues.items():
                try:
                    mod.mark_all()
                except Exception as e:
                    logger.debug(f"shadow arm: {name} mark_all failed: {e}")
        except Exception as e:
            logger.debug(f"shadow arm mark_all failed (non-fatal): {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED HUB MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedTradingHub:
    """
    The master hub that runs ALL Aureon trading systems.
    Outputs fused signals to the Phi-Radar for auto-hive execution.
    """
    
    def __init__(self):
        self.loader = AureonModuleLoader()
        self.fusion = None
        self.shadow = ShadowArm()
        # BTC/ETH added 2026-09-06: the shadow arm trades these on the
        # kraken/alpaca/binance venues; FX/metals remain for the Capital path.
        self.symbols = ["BTCUSD", "ETHUSD", "USDJPY", "US100", "EURUSD", "GBPUSD", "GOLD", "SILVER", "OIL_CRUDE", "AAPL", "TSLA", "NVDA", "NATURALGAS"]
        self.running = False
        
    def initialize(self):
        """Load all modules and initialize fusion engine."""
        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info("║     🐝 AUREON UNIFIED TRADING HUB INITIALIZING 🐝            ║")
        logger.info("║                                                              ║")
        logger.info("║  Cloning ALL systems from Aureon-OS...                       ║")
        logger.info("╚══════════════════════════════════════════════════════════════╝")
        
        # Signal coercion patch: object-returning harmonic/planetary modules
        # silently scored 0 before this adapter existed (fail-closed → numeric).
        try:
            import sys as _sys
            if str(RADAR_DIR.parent) not in _sys.path:
                _sys.path.insert(0, str(RADAR_DIR.parent))
            import aureon_fusion.signal_adapters as _signal_adapters
            _signal_adapters.install_coercion_patch(engine_class=SignalFusionEngine)
        except Exception as e:
            logger.warning(f"signal coercion patch unavailable, using hub-native "
                           f"coercion only: {e}")
        modules = self.loader.load_all()
        self.fusion = SignalFusionEngine(modules)
        _ensure_hub_logging()  # module imports may have re-rooted logging
        
        logger.info(f"✅ Unified Hub ready. {len(modules)} systems online.")
        
    def run_cycle(self):
        """Run one complete scan cycle across all symbols and systems."""
        _ensure_hub_logging()  # module imports re-root logging mid-load
        logger.info(f"--- UNIFIED CYCLE @ {datetime.now(timezone.utc).isoformat()} ---")

        cycle_signals: List[UnifiedSignal] = []
        for symbol in self.symbols:
            # Real feed only — hardcoded placeholder prices were feeding
            # synthetic signals into the radar pipeline (bug-hunt #6).
            price = self._get_price(symbol)
            if price is None:
                logger.debug(f"{symbol}: no real price available — skipping (no synthetic signals)")
                continue
            
            # Run ALL systems and fuse
            signal = self.fusion.scan_all(symbol, price)
            cycle_signals.append(signal)

            # Log the fused signal
            if signal.confidence > 0.2:
                logger.info(
                    f"🎯 FUSED SIGNAL: {signal.symbol} {signal.direction} "
                    f"confidence={signal.confidence:.2f} fusion={signal.fusion_score:.3f} "
                    f"[mom={signal.momentum_score:.2f} harm={signal.harmonic_resonance:.2f} "
                    f"ob={signal.orderbook_pressure:.2f} planet={signal.planetary_bias:.2f} "
                    f"bots={signal.bot_score:.2f}]"
                )

                # Write to signal log for Phi-Radar to pick up
                self._write_fused_signal(signal)

                # Shadow arm: offer the promoted signal to the mapped shadow
                # venues (fixed small qty, source hub_fusion). Inert and
                # exception-proof when shadow modules are absent/broken.
                self.shadow.dispatch(signal)
            else:
                logger.debug(f"{symbol}: NEUTRAL (conf={signal.confidence:.2f})")

        # One compact honest line per cycle: the real fusion values, so the
        # pipeline's behaviour is visible even when nothing crosses the
        # conf>0.3 promotion threshold.
        if cycle_signals:
            parts = " ".join(f"{s.symbol}={s.fusion_score:+.3f}" for s in cycle_signals)
            best = max(cycle_signals, key=lambda s: s.confidence)
            logger.info(
                f"FUSION SUMMARY: {parts} | best: {best.symbol} "
                f"{best.direction} conf={best.confidence:.2f} "
                f"(promote threshold conf>0.2)")

        # Shadow arm upkeep: stops/TPs + MTM for open shadow positions.
        # Runs once per cycle regardless of which symbols scanned; inert
        # (debug-only) when the shadow modules are not importable.
        self.shadow.mark_all()
    
    def _get_price(self, symbol: str) -> Optional[float]:
        """Real market price via aureon_price_feed.

        Bug-hunt #6: this used to return HARDCODED constants, so every fused
        signal written to fused_signals.jsonl was anchored to a fictional
        price. Returns None when the feed cannot provide a quote — callers
        skip the symbol instead of emitting synthetic signals.
        """
        try:
            from aureon_price_feed import get_price
            price = get_price(symbol)
            if price and price > 0:
                return float(price)
        except Exception as e:
            logger.debug(f"Price feed unavailable for {symbol}: {e}")
        return None
    
    def _write_fused_signal(self, signal: UnifiedSignal):
        """Write fused signal to log for Phi-Radar consumption."""
        log_file = RADAR_DIR / "fused_signals.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(signal.to_dict()) + '\n')

        # Emit a flight-recorder event on the organism's shared event spine.
        try:
            from aureon_fusion import events as _events
            _events.emit_radar_signal(
                source="unified_hub",
                topic="radar.fused_signal",
                symbol=signal.symbol,
                score=signal.confidence,
                extra={
                    "direction": signal.direction,
                    "fusion_score": float(signal.fusion_score),
                    "signal_timestamp": signal.timestamp,
                },
                priority=5,
            )
        except Exception as e:
            logger.debug(f"radar.fused_signal event emit failed: {e}")
    
    def run_continuous(self, interval: int = 60):
        """Run continuous scanning."""
        self.running = True
        self.initialize()
        
        logger.info("╔══════════════════════════════════════════════════════════════╗")
        logger.info("║     🐝 UNIFIED HUB RUNNING — ALL SYSTEMS ACTIVE 🐝           ║")
        logger.info("║                                                              ║")
        logger.info("║  135 Aureon systems fused into one signal pipeline           ║")
        logger.info("║  Auto-hive executes when fusion confidence > threshold       ║")
        logger.info("╚══════════════════════════════════════════════════════════════╝")
        
        while self.running:
            self.run_cycle()
            time.sleep(interval)
    
    def stop(self):
        self.running = False

# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    hub = UnifiedTradingHub()
    try:
        hub.run_continuous()
    except KeyboardInterrupt:
        hub.stop()
        print("\nUnified Hub halted.")

if __name__ == "__main__":
    main()
