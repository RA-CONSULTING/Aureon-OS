#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🎯🐺 AUREON LIVE MOMENTUM HUNTER 🐺🎯                                            ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                     ║
║                                                                                      ║
║     WIRES TOGETHER ALL AUREON SYSTEMS FOR LIVE ALPACA TRADING                        ║
║                                                                                      ║
║     COMPONENTS INTEGRATED:                                                           ║
║       👑 Queen Hive Mind - Central decision maker (Sero)                            ║
║       🐺 Wolf Scanner - Momentum sniper                                              ║
║       🦁 Lion Scanner - Multi-target hunter                                          ║
║       🐜 Ants Scanner - Small-profit forager                                         ║
║       🐦 Hummingbird - Micro-rotation pollinator                                     ║
║       🔮 Probability Nexus - 3-validation pipeline                                   ║
║       🦙 Scanner Bridge - Fee-aware execution with trailing stops                    ║
║       🦈 Orca Intelligence - Whale wake rider + hunting grounds                      ║
║       🌊 Ocean Scanner - 13,000+ symbol global scanner                               ║
║                                                                                      ║
║     THE HUNT:                                                                        ║
║       1. Animal scanners find momentum opportunities                                 ║
║       2. Probability Nexus validates with 3-pass pipeline                            ║
║       3. Queen decides on 4th pass (Batten Matrix)                                   ║
║       4. Execute with trailing stop protection                                       ║
║                                                                                      ║
║     Gary Leckey | January 2026 | All Systems United                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import sys
import os

# Windows UTF-8 fix (MANDATORY)
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import math
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

# Load local runtime credentials only when the file exists.  Importing this
# module from another working directory must remain inert and must not turn a
# missing credential file into an invented runtime state.
_env_path = Path('.env')
if _env_path.is_file():
    try:
        for line in _env_path.read_text(encoding='utf-8').splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())
    except OSError:
        pass

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# 🌍 SACRED CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
PHI = (1 + math.sqrt(5)) / 2  # 1.618 - Golden ratio
SCHUMANN_BASE = 7.83
LOVE_FREQUENCY = 528

# 👑 QUEEN'S SACRED 1.88% LAW - THE HUNT MUST PROFIT
QUEEN_MIN_COP = 1.0188              # Sacred constant: 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88         # Percentage form - no hunt below this
QUEEN_HUNTER_PROFIT_FREQ = 188.0    # Hz - Sacred frequency for profitable hunts


# ═══════════════════════════════════════════════════════════════════════════
# 📦 HUNTER RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════════════════
@dataclass
class HuntResult:
    """Result of a momentum hunt."""
    symbol: str
    side: str  # 'buy' or 'sell'
    
    # Scanner signals
    scanner_source: str  # 'wolf', 'lion', 'ants', 'hummingbird'
    momentum_pct: float
    net_pct: float
    volume: float
    
    # Probability Nexus validation
    nexus_direction: str = 'NO_DATA'
    nexus_probability: Optional[float] = None
    nexus_confidence: Optional[float] = None
    nexus_factors: Dict[str, Any] = field(default_factory=dict)
    
    # Queen decision
    queen_approved: bool = False
    queen_confidence: Optional[float] = None
    queen_reasoning: str = ""

    # Provenance chain
    truth_status: str = "no_data"
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    generated_values: bool = False
    nexus_truth_status: str = "no_data"
    nexus_source_id: Optional[str] = None
    nexus_source_timestamp: Optional[float] = None
    eligible_for_external_action: bool = False
    
    # Execution
    executed: bool = False
    execution_status: str = "not_submitted"
    order_id: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    final_pnl: Optional[float] = None
    
    def is_valid_opportunity(self, aggressive: bool = False) -> bool:
        """Check if this hunt result meets minimum criteria.
        
        Args:
            aggressive: If True, lower confidence threshold for growth mode (small portfolios)
        """
        # Confidence threshold: 0.2 for aggressive mode, 0.5 for normal
        conf_threshold = 0.2 if aggressive else 0.5
        
        # 3-pass validation (Batten Matrix)
        pass_1 = self.net_pct > 0  # Must be net positive after fees
        pass_2 = (
            self.nexus_confidence is not None
            and self.nexus_confidence > conf_threshold
        )
        pass_3 = (
            (self.side == 'buy' and self.nexus_direction == 'LONG') or
            (self.side == 'sell' and self.nexus_direction == 'SHORT')
        )
        try:
            source_timestamp = float(self.source_timestamp)
            received_at = float(self.received_at)
            nexus_source_timestamp = float(self.nexus_source_timestamp)
        except (TypeError, ValueError):
            return False
        now = time.time()
        provenance_ok = (
            self.truth_status in {"live", "real_derived"}
            and bool(self.source_id)
            and all(
                math.isfinite(value)
                for value in (source_timestamp, received_at, nexus_source_timestamp)
            )
            and source_timestamp > 0
            and received_at > 0
            and nexus_source_timestamp > 0
            and now - source_timestamp <= 2 * 60 * 60
            and source_timestamp - now <= 5 * 60
            and received_at - source_timestamp <= 2 * 60 * 60
            and self.generated_values is False
            and self.nexus_truth_status == "real_derived"
            and bool(self.nexus_source_id)
            and now - nexus_source_timestamp <= 5 * 60
            and nexus_source_timestamp - now <= 5 * 60
            and self.eligible_for_external_action is True
        )
        return pass_1 and pass_2 and pass_3 and provenance_ok


# ═══════════════════════════════════════════════════════════════════════════
# 🎯 LIVE MOMENTUM HUNTER
# ═══════════════════════════════════════════════════════════════════════════
class LiveMomentumHunter:
    """
    Unified hunter that wires all Aureon systems for live trading.
    
    The hunt process:
    1. Animal scanners (Wolf/Lion/Ants/Hummingbird) find momentum
    2. Probability Nexus validates each opportunity
    3. Queen makes final 4th-pass decision
    4. Execute via Scanner Bridge with trailing stops
    """
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.hunt_history: List[HuntResult] = []
        
        # Initialize components
        self._init_exchange_client()
        self._init_scanner_bridge()
        self._init_animal_swarm()
        self._init_probability_nexus()
        self._init_queen()
        self._init_orca()        # 🦈 Whale wake rider
        self._init_ocean()       # 🌊 Global ocean scanner
        self._init_hunting_grounds()  # 🎯 Venue scoring
        self._init_barter_matrix()    # 🫒 Multi-hop conversion paths
        self._init_global_hunter()    # 🦈🌍 Worldwide 3,000+ symbol scanner
        
        logger.info(f"🎯 LiveMomentumHunter initialized (dry_run={dry_run})")
    
    def _init_exchange_client(self):
        """Initialize Alpaca client."""
        from aureon.exchanges.alpaca_client import AlpacaClient
        self.alpaca = AlpacaClient()
        
        self.cash = None
        self.equity = None

        # Get account info.  Missing/malformed provider fields remain no-data;
        # zero is never substituted for an unavailable balance.
        try:
            acct = self.alpaca.get_account()
            if not isinstance(acct, dict) or acct.get('cash') is None or acct.get('equity') is None:
                raise ValueError("account receipt missing cash/equity")
            cash = float(acct['cash'])
            equity = float(acct['equity'])
            if not math.isfinite(cash) or not math.isfinite(equity) or cash < 0 or equity < 0:
                raise ValueError("account receipt contains invalid cash/equity")
            self.cash = cash
            self.equity = equity
            logger.info(f"🦙 Alpaca connected: ${self.equity:.2f} equity, ${self.cash:.2f} cash")
        except Exception as e:
            logger.error(f"❌ Alpaca connection failed: {e}")
    
    def _init_scanner_bridge(self):
        """Initialize fee-aware scanner bridge."""
        try:
            from aureon.bridges.aureon_alpaca_scanner_bridge import AlpacaScannerBridge
            from aureon.exchanges.alpaca_fee_tracker import AlpacaFeeTracker
            
            self.fee_tracker = AlpacaFeeTracker(self.alpaca)
            self.bridge = AlpacaScannerBridge(
                alpaca_client=self.alpaca,
                fee_tracker=self.fee_tracker,
                enable_sse=False,  # Start without SSE for stability
                enable_stocks=False
            )
            logger.info("🌉 Scanner Bridge initialized with fee tracking")
        except Exception as e:
            logger.error(f"❌ Scanner Bridge failed: {e}")
            self.bridge = None
    
    def _init_animal_swarm(self):
        """Initialize animal momentum scanners."""
        try:
            from aureon.scanners.aureon_animal_momentum_scanners import AlpacaSwarmOrchestrator
            
            self.swarm = AlpacaSwarmOrchestrator(self.alpaca, self.bridge)
            self.swarm.dry_run = self.dry_run
            logger.info("🐺🦁🐜🐦 Animal Swarm initialized (Wolf, Lion, Ants, Hummingbird)")
        except Exception as e:
            logger.error(f"❌ Animal Swarm failed: {e}")
            self.swarm = None
    
    def _init_probability_nexus(self):
        """Initialize probability prediction engine."""
        try:
            from aureon.bridges.aureon_probability_nexus import AureonProbabilityNexus
            
            self.nexus = AureonProbabilityNexus(exchange='alpaca')
            logger.info("🔮 Probability Nexus initialized (3-validation pipeline)")
        except Exception as e:
            logger.error(f"❌ Probability Nexus failed: {e}")
            self.nexus = None
    
    def _init_queen(self):
        """Initialize Queen Hive Mind."""
        try:
            from aureon.utils.aureon_queen_hive_mind import QueenHiveMind, create_queen_hive_mind
            
            if self.equity is None:
                raise RuntimeError("account equity unavailable; Queen capital cannot be evidenced")
            self.queen = create_queen_hive_mind(initial_capital=self.equity)
            
            # Wire components
            if self.nexus:
                self.queen.wire_probability_nexus(self.nexus)
            
            # Wire exchange clients
            self.queen.wire_exchange_clients({'alpaca': self.alpaca})
            
            logger.info("👑 Queen Sero initialized and wired to all systems")
        except Exception as e:
            logger.error(f"❌ Queen initialization failed: {e}")
            self.queen = None
    
    def _init_orca(self):
        """Initialize Orca Killer Whale Intelligence."""
        try:
            from aureon.bots_intelligence.aureon_orca_intelligence import OrcaKillerWhaleIntelligence
            
            self.orca = OrcaKillerWhaleIntelligence()
            
            # Wire Orca to Queen (chain of command)
            if self.queen:
                self.orca.wire_queen(self.queen)
            
            logger.info("🦈 Orca Intelligence initialized - whale wake rider ready")
        except Exception as e:
            logger.error(f"❌ Orca initialization failed: {e}")
            self.orca = None
    
    def _init_ocean(self):
        """Initialize Ocean Scanner for 13,000+ symbol scanning."""
        try:
            from aureon.scanners.aureon_ocean_scanner import OceanScanner
            
            # Pass exchange clients to ocean scanner
            exchanges = {}
            if self.alpaca:
                exchanges['alpaca'] = self.alpaca
            
            self.ocean = OceanScanner(exchanges=exchanges)
            logger.info("🌊 Ocean Scanner initialized - 13,000+ symbol universe ready")
        except Exception as e:
            logger.error(f"❌ Ocean Scanner initialization failed: {e}")
            self.ocean = None
    
    def _init_hunting_grounds(self):
        """Initialize Orca Hunting Grounds for venue scoring."""
        try:
            from aureon.bots.orca_hunting_grounds import OrcaHuntingGrounds
            
            self.hunting_grounds = OrcaHuntingGrounds()
            logger.info("🎯 Hunting Grounds initialized - venue scoring ready")
        except Exception as e:
            logger.error(f"❌ Hunting Grounds initialization failed: {e}")
            self.hunting_grounds = None
    
    def _init_barter_matrix(self):
        """Initialize Barter Matrix for multi-hop conversion paths."""
        try:
            from aureon.trading.aureon_barter_navigator import BarterNavigator
            
            self.barter = BarterNavigator()
            
            # Try to load from cache first
            if not self.barter.load_cache():
                logger.info("🫒 Barter cache empty - will build on first use")
            else:
                logger.info(f"🫒 Barter Matrix loaded - {len(self.barter.assets)} assets, {self.barter.total_edges} edges")
        except Exception as e:
            logger.error(f"❌ Barter Matrix failed: {e}")
            self.barter = None
    
    def _init_global_hunter(self):
        """Initialize Orca Global Hunter for 3,000+ symbol worldwide scanning."""
        try:
            from aureon.bots.orca_global_hunter import OrcaGlobalHunter
            
            self.global_hunter = OrcaGlobalHunter()
            logger.info("🦈🌍 Global Hunter initialized - 3,000+ symbols across all exchanges")
        except Exception as e:
            logger.error(f"❌ Global Hunter failed: {e}")
            self.global_hunter = None
    
    def _get_price_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch recent price history for a symbol."""
        try:
            # Check if this is a Kraken-only symbol (not on Alpaca)
            if hasattr(self, 'global_hunter') and self.global_hunter:
                alpaca_symbols = self.global_hunter.universes.get('alpaca_crypto', set())
                if symbol not in alpaca_symbols and symbol.replace('/', '') + '/USD' not in alpaca_symbols:
                    # Try Kraken API directly
                    kraken_data = self._get_kraken_ohlc(symbol, limit)
                    if kraken_data:
                        return kraken_data
            
            from alpaca.data.historical import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from datetime import datetime, timedelta
            
            # Use API keys for authenticated data access
            api_key = os.environ.get('ALPACA_API_KEY')
            api_secret = os.environ.get('ALPACA_SECRET_KEY')
            data_client = CryptoHistoricalDataClient(api_key=api_key, secret_key=api_secret)
            
            # Normalize symbol format
            # Convert USDC pairs to USD for data (e.g., AAVE/USDC -> AAVE/USD)
            if 'USDC' in symbol:
                symbol = symbol.replace('USDC', 'USD').replace('//', '/')
            
            # Ensure proper format
            if '/' not in symbol:
                symbol = symbol.replace('USD', '/USD')
            
            # Clean up any double slashes
            symbol = symbol.replace('//', '/')
            
            end = datetime.now()
            start = end - timedelta(hours=6)  # Last 6 hours of 1-min bars
            
            req = CryptoBarsRequest(
                symbol_or_symbols=[symbol],
                start=start,
                end=end,
                timeframe=TimeFrame.Minute
            )
            bars = data_client.get_crypto_bars(req)
            
            # Access data through the .data attribute (BarSet has dict-like data)
            bar_data = getattr(bars, 'data', {}) or {}
            
            if symbol not in bar_data:
                # Try without the slash
                alt_symbol = symbol.replace('/', '')
                if alt_symbol in bar_data:
                    symbol = alt_symbol
                else:
                    return []
            
            result = []
            received_at = time.time()
            for bar in bar_data[symbol]:
                source_timestamp = float(bar.timestamp.timestamp())
                result.append({
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': float(bar.volume),
                    'timestamp': source_timestamp,
                    'source_id': 'alpaca_crypto_bars_1m',
                    'source_timestamp': source_timestamp,
                    'received_at': received_at,
                    'truth_status': 'live',
                    'generated_values': False,
                })
            
            return result[-limit:]
            
        except Exception as e:
            logger.error(f"Failed to get price history for {symbol}: {e}")
            return []
    
    def _get_kraken_ohlc(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Fetch OHLC data directly from Kraken API."""
        import requests
        
        try:
            # Normalize symbol for Kraken (QTUM/USD -> QTUMUSD)
            kraken_pair = symbol.replace('/', '')
            
            # Kraken OHLC endpoint
            resp = requests.get(
                'https://api.kraken.com/0/public/OHLC',
                params={'pair': kraken_pair, 'interval': 1},  # 1-minute bars
                timeout=10
            )
            data = resp.json()
            
            if 'error' in data and data['error']:
                logger.debug(f"Kraken OHLC error: {data['error']}")
                return []
            
            result = []
            received_at = time.time()
            if 'result' in data:
                for key, candles in data['result'].items():
                    if isinstance(candles, list) and candles:
                        for c in candles[-limit:]:
                            source_timestamp = float(c[0])
                            result.append({
                                'open': float(c[1]),
                                'high': float(c[2]),
                                'low': float(c[3]),
                                'close': float(c[4]),
                                'volume': float(c[6]),
                                'timestamp': source_timestamp,
                                'source_id': 'kraken_public_ohlc_1m',
                                'source_timestamp': source_timestamp,
                                'received_at': received_at,
                                'truth_status': 'live',
                                'generated_values': False,
                            })
                        break
            
            if result:
                logger.info(f"🐙 Kraken OHLC: Got {len(result)} candles for {symbol}")
            
            return result
            
        except Exception as e:
            logger.debug(f"Kraken OHLC fetch error for {symbol}: {e}")
            return []
    
    def validate_with_nexus(self, symbol: str) -> Optional[Dict]:
        """Run probability nexus validation on a symbol."""
        if not self.nexus:
            return None
        
        try:
            # Get price history
            candles = self._get_price_history(symbol)
            if len(candles) < 30:
                logger.warning(f"Insufficient data for {symbol}: {len(candles)} candles")
                return None
            latest = candles[-1]
            source_timestamp = latest.get("source_timestamp", latest.get("timestamp"))
            source_id = latest.get("source_id")
            try:
                source_timestamp = float(source_timestamp)
            except (TypeError, ValueError):
                return None
            if (
                not source_id
                or not math.isfinite(source_timestamp)
                or source_timestamp <= 0
                or time.time() - source_timestamp > 5 * 60
                or source_timestamp - time.time() > 5 * 60
            ):
                return None
            for candle in candles:
                required = [
                    candle.get("open"),
                    candle.get("high"),
                    candle.get("low"),
                    candle.get("close"),
                    candle.get("volume"),
                    candle.get("timestamp"),
                ]
                try:
                    numbers = [float(value) for value in required]
                except (TypeError, ValueError):
                    return None
                if (
                    not all(math.isfinite(value) for value in numbers)
                    or min(numbers[:4]) <= 0
                    or numbers[4] < 0
                    or candle.get("truth_status") != "live"
                    or candle.get("source_id") != source_id
                    or candle.get("generated_values") is not False
                ):
                    return None
                candle_source_timestamp = candle.get("source_timestamp")
                try:
                    candle_source_timestamp = float(candle_source_timestamp)
                except (TypeError, ValueError):
                    return None
                if (
                    not math.isfinite(candle_source_timestamp)
                    or candle_source_timestamp <= 0
                    or abs(candle_source_timestamp - numbers[5]) > 1e-6
                ):
                    return None
            
            # Feed to nexus - use update_history method
            for candle in candles:
                self.nexus.update_history(candle)
            
            # Get prediction
            prediction = self.nexus.predict()
            probability = float(prediction.probability)
            confidence = float(prediction.confidence)
            if (
                not math.isfinite(probability)
                or not math.isfinite(confidence)
                or not 0 <= probability <= 1
                or not 0 <= confidence <= 1
                or prediction.direction not in {"LONG", "SHORT", "NEUTRAL"}
            ):
                return None
            
            return {
                'direction': prediction.direction,
                'probability': probability,
                'confidence': confidence,
                'factors': prediction.factors,
                'stop_loss_pct': prediction.stop_loss_pct,
                'take_profit_pct': prediction.take_profit_pct,
                'reason': prediction.reason,
                'truth_status': 'real_derived',
                'source_id': f"probability_nexus:{source_id}",
                'source_timestamp': source_timestamp,
                'generated_values': False,
            }
            
        except Exception as e:
            logger.error(f"Nexus validation failed for {symbol}: {e}")
            return None
    
    def ask_queen(self, opportunity: Dict) -> Tuple[bool, Optional[float], str]:
        """Ask Queen for final 4th-pass decision."""
        if not self.queen:
            return False, None, "NO_DATA: Queen unavailable"
        
        try:
            decision = self.queen.get_queen_decision_with_intelligence(opportunity)
            
            # Extract decision
            if not isinstance(decision, dict) or decision.get('final_score') is None:
                return False, None, "NO_DATA: Queen decision score missing"
            confidence = float(decision['final_score'])
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                return False, None, "NO_DATA: Queen decision score invalid"
            approved = confidence > 0.5
            reasons = decision.get('reasoning')
            reasoning = " | ".join(str(item) for item in reasons) if isinstance(reasons, list) and reasons else "reasoning_not_provided"
            
            return approved, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Queen decision failed: {e}")
            return False, None, f"NO_DATA: Queen decision failed: {e}"
    
    def hunt(self) -> List[HuntResult]:
        """
        Execute a full momentum hunt cycle.
        
        Returns list of validated opportunities ready for execution.
        """
        print("\n" + "=" * 70)
        print("🎯🐺 AUREON MOMENTUM HUNT STARTING 🐺🎯")
        print("=" * 70)
        
        # 0. GLOBAL SCAN - See the whole world first!
        global_opportunities = []
        if hasattr(self, 'global_hunter') and self.global_hunter:
            print("\n🦈🌍 PHASE 0: Global Exchange Scan (Kraken + Binance + Alpaca)...")
            try:
                global_opportunities = self.global_hunter.hunt_global()
                print(f"   Found {len(global_opportunities)} global momentum signals")
            except Exception as e:
                print(f"   ⚠️ Global scan error: {e}")
        
        if not self.swarm:
            print("❌ Animal Swarm not available!")
            return []
        
        # 1. Run animal scanners (focused Alpaca crypto scan)
        print("\n🔍 PHASE 1: Animal Scanners Running...")
        scan_results = self.swarm.run_once()
        
        total_opportunities = sum(len(v) for v in scan_results.values())
        print(f"   Found {total_opportunities} raw opportunities")
        
        for scanner, opps in scan_results.items():
            if opps:
                print(f"   {scanner.upper()}: {len(opps)} targets")
        
        # Merge global opportunities into scan results
        if global_opportunities:
            # Convert GlobalOpportunity to AnimalOpportunity format
            from aureon.scanners.aureon_animal_momentum_scanners import AnimalOpportunity
            global_as_animal = []
            for gopp in global_opportunities[:10]:  # Top 10 global
                try:
                    truth_status = getattr(gopp, 'truth_status', None)
                    source_id = getattr(gopp, 'source_id', None)
                    source_timestamp = getattr(gopp, 'source_timestamp', None)
                    received_at = getattr(gopp, 'received_at', None)
                    generated_values = getattr(gopp, 'generated_values', None)
                    eligible = getattr(gopp, 'eligible_for_external_action', None)
                    volume = getattr(gopp, 'volume', None)
                    numeric_values = [
                        float(source_timestamp),
                        float(received_at),
                        float(volume),
                        float(gopp.momentum_pct),
                        float(gopp.net_edge),
                    ]
                    if (
                        truth_status not in {'live', 'real_derived'}
                        or not source_id
                        or not all(math.isfinite(value) for value in numeric_values)
                        or time.time() - numeric_values[0] > 2 * 60 * 60
                        or numeric_values[0] - time.time() > 5 * 60
                        or generated_values is not False
                        or eligible is not True
                    ):
                        continue
                    animal_opp = AnimalOpportunity(
                        symbol=gopp.symbol,
                        side=gopp.direction,
                        move_pct=gopp.momentum_pct,
                        net_pct=gopp.net_edge * 100,  # Convert to %
                        volume=volume,
                        reason=f"🌍 {gopp.exchange}: {gopp.reason}",
                        truth_status=truth_status,
                        source_id=source_id,
                        source_timestamp=numeric_values[0],
                        received_at=numeric_values[1],
                        generated_values=False,
                        eligible_for_external_action=True,
                    )
                    global_as_animal.append(animal_opp)
                except Exception as e:
                    logger.debug(f"Global convert error: {e}")
            
            if global_as_animal:
                scan_results['global'] = global_as_animal
                total_opportunities += len(global_as_animal)
                print(f"   GLOBAL: {len(global_as_animal)} targets (from worldwide scan)")
        
        if total_opportunities == 0:
            print("\n😴 No momentum detected - market is flat worldwide")
            return []
        
        # 2. Validate each opportunity through Probability Nexus
        print("\n🔮 PHASE 2: Probability Nexus Validation...")
        hunt_results: List[HuntResult] = []
        
        for scanner, opps in scan_results.items():
            for opp in opps[:3]:  # Top 3 from each scanner
                print(f"   Validating {opp.symbol}...", end=" ")

                try:
                    source_timestamp = float(opp.source_timestamp)
                    received_at = float(opp.received_at)
                except (TypeError, ValueError):
                    print("NO DATA")
                    continue
                if (
                    opp.truth_status not in {'live', 'real_derived'}
                    or not opp.source_id
                    or not math.isfinite(source_timestamp)
                    or not math.isfinite(received_at)
                    or time.time() - source_timestamp > 2 * 60 * 60
                    or source_timestamp - time.time() > 5 * 60
                    or opp.generated_values is not False
                    or opp.eligible_for_external_action is not True
                ):
                    print("NO DATA")
                    continue
                
                # Create hunt result
                result = HuntResult(
                    symbol=opp.symbol,
                    side=opp.side,
                    scanner_source=scanner,
                    momentum_pct=opp.move_pct,
                    net_pct=opp.net_pct,
                    volume=opp.volume,
                    truth_status=opp.truth_status,
                    source_id=opp.source_id,
                    source_timestamp=source_timestamp,
                    received_at=received_at,
                    generated_values=False,
                )
                
                nexus_result = self.validate_with_nexus(opp.symbol)
                if nexus_result:
                    result.nexus_direction = nexus_result['direction']
                    result.nexus_probability = nexus_result['probability']
                    result.nexus_confidence = nexus_result['confidence']
                    result.nexus_factors = nexus_result['factors']
                    result.nexus_truth_status = nexus_result['truth_status']
                    result.nexus_source_id = nexus_result['source_id']
                    result.nexus_source_timestamp = nexus_result['source_timestamp']
                    result.eligible_for_external_action = True
                    print(f"{nexus_result['direction']} ({nexus_result['confidence']:.2f})")
                else:
                    print("NO DATA")
                
                hunt_results.append(result)
        
        # 3. Filter for valid 3-pass opportunities
        print("\n📊 PHASE 3: 3-Pass Validation Filter...")
        
        # Use aggressive mode for small portfolios (< $100)
        aggressive_mode = self.equity is not None and self.equity < 100
        if aggressive_mode:
            print("   🚀 AGGRESSIVE MODE: Small portfolio - confidence threshold 0.2")
        
        valid_results = [r for r in hunt_results if r.is_valid_opportunity(aggressive=aggressive_mode)]
        print(f"   {len(valid_results)}/{len(hunt_results)} passed 3-validation")
        
        if not valid_results:
            print("\n⚠️ No opportunities passed 3-validation")
            # Show why they failed
            for r in hunt_results[:5]:
                reasons = []
                if r.net_pct <= 0:
                    reasons.append(f"net={r.net_pct:.2f}%")
                if r.nexus_confidence is None:
                    reasons.append("conf=NO_DATA")
                elif r.nexus_confidence <= 0.5:
                    reasons.append(f"conf={r.nexus_confidence:.2f}")
                if not ((r.side == 'buy' and r.nexus_direction == 'LONG') or
                        (r.side == 'sell' and r.nexus_direction == 'SHORT')):
                    reasons.append(f"dir={r.side}!={r.nexus_direction}")
                print(f"   {r.symbol}: FAILED - {', '.join(reasons)}")
            return []
        
        # 4. Queen 4th-pass decision
        print("\n👑 PHASE 4: Queen's 4th-Pass Decision...")
        approved_results: List[HuntResult] = []
        
        for result in valid_results:
            opp_dict = {
                'symbol': result.symbol,
                'action': 'BUY' if result.side == 'buy' else 'SELL',
                'exchange': 'alpaca',
                'score': result.nexus_confidence,
                'momentum': result.momentum_pct,
                'net_profit_pct': result.net_pct
            }
            coherence = result.nexus_factors.get('coherence')
            try:
                coherence = float(coherence)
            except (TypeError, ValueError):
                coherence = None
            if coherence is not None and math.isfinite(coherence):
                opp_dict['coherence'] = coherence
            
            approved, confidence, reasoning = self.ask_queen(opp_dict)

            result.queen_approved = approved
            result.queen_confidence = confidence
            result.queen_reasoning = reasoning
            if not approved:
                result.eligible_for_external_action = False

            status = "✅ APPROVED" if approved else "❌ REJECTED"
            confidence_text = f"{confidence:.2f}" if confidence is not None else "NO DATA"
            print(f"   {result.symbol}: {status} ({confidence_text}) - {reasoning[:50]}...")
            
            if approved:
                approved_results.append(result)
        
        # Summary
        print("\n" + "=" * 70)
        print(f"🎯 HUNT COMPLETE: {len(approved_results)} opportunities approved")
        print("=" * 70)
        
        for r in approved_results:
            print(f"   🐺 {r.symbol} {r.side.upper()} | Mom: {r.momentum_pct:+.2f}% | Net: {r.net_pct:+.3f}% | Queen: {r.queen_confidence:.2f}")
        
        self.hunt_history.extend(approved_results)
        return approved_results
    
    def execute_best(self, results: List[HuntResult] = None) -> Optional[HuntResult]:
        """Execute the best opportunity from hunt results."""
        if results is None:
            results = self.hunt()
        
        if not results:
            print("❌ No opportunities to execute")
            return None
        
        aggressive_mode = self.equity is not None and self.equity < 100
        results = [
            result for result in results
            if result.queen_approved
            and result.queen_confidence is not None
            and result.is_valid_opportunity(aggressive=aggressive_mode)
        ]
        if not results:
            print("❌ No proven, Queen-approved opportunity to execute")
            return None

        # Sort only proven Queen decisions by confidence × provider-derived net edge.
        results.sort(key=lambda r: float(r.queen_confidence) * r.net_pct, reverse=True)
        best = results[0]
        
        print(f"\n🎯 EXECUTING BEST: {best.symbol} {best.side.upper()}")
        
        if self.dry_run:
            print(f"   [DRY-RUN] Would execute {best.side} on {best.symbol}")
            best.executed = False
            best.execution_status = "not_submitted"
            best.order_id = None
            best.entry_price = None
            return best
        
        # Calculate position size (use 90% of cash)
        try:
            # Get current quote
            from alpaca.data.historical import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoLatestQuoteRequest
            
            data_client = CryptoHistoricalDataClient()
            symbol_fmt = best.symbol if '/' in best.symbol else best.symbol.replace('USD', '/USD')
            
            req = CryptoLatestQuoteRequest(symbol_or_symbols=[symbol_fmt])
            quotes = data_client.get_crypto_latest_quote(req)
            quote = quotes[symbol_fmt]
            price = float(quote.ask_price) if best.side == 'buy' else float(quote.bid_price)
            if not math.isfinite(price) or price <= 0:
                raise ValueError("provider quote price is invalid")
            quote_timestamp = getattr(quote, 'timestamp', None)
            if hasattr(quote_timestamp, 'timestamp'):
                quote_timestamp = quote_timestamp.timestamp()
            quote_timestamp = float(quote_timestamp)
            now = time.time()
            if (
                not math.isfinite(quote_timestamp)
                or quote_timestamp <= 0
                or now - quote_timestamp > 60
                or quote_timestamp - now > 5 * 60
            ):
                raise ValueError("provider quote timestamp is missing or stale")
            
            # Refresh account
            acct = self.alpaca.get_account()
            if not isinstance(acct, dict) or acct.get('cash') is None:
                raise ValueError("account cash receipt unavailable")
            cash = float(acct['cash'])
            if not math.isfinite(cash) or cash <= 0:
                raise ValueError("account cash receipt is invalid or empty")
            
            # Calculate qty
            trade_value = cash * 0.90
            qty = trade_value / price
            
            # Alpaca needs symbol without slash
            alpaca_symbol = best.symbol.replace('/', '')
            
            print(f"   Price: ${price:.5f}")
            print(f"   Cash: ${cash:.2f}")
            print(f"   Trade Value: ${trade_value:.2f}")
            print(f"   Quantity: {qty:.6f}")
            
            # Every side uses the same receipted bridge path.  There is no
            # direct-order bypass around the provenance gate.
            if not self.bridge or not self.swarm:
                raise RuntimeError("scanner bridge execution path unavailable")
            from aureon.scanners.aureon_animal_momentum_scanners import AnimalOpportunity
            opp = AnimalOpportunity(
                symbol=alpaca_symbol,
                side=best.side,
                move_pct=best.momentum_pct,
                net_pct=best.net_pct,
                volume=best.volume,
                reason=f"Queen: {best.queen_confidence:.2f}",
                truth_status=best.truth_status,
                source_id=best.source_id,
                source_timestamp=best.source_timestamp,
                received_at=best.received_at,
                generated_values=False,
                eligible_for_external_action=True,
            )

            result = self.swarm.execute_opportunity(opp, qty, use_trailing_stop=True)
            if not isinstance(result, dict):
                best.execution_status = "submission_failed"
                return best

            provider_order_id = result.get('provider_order_id')
            if result.get('status') == 'submitted' and provider_order_id:
                best.executed = False
                best.execution_status = "submitted"
                best.order_id = str(provider_order_id)
                best.entry_price = None
                print(f"   ✅ Order submitted: {best.order_id}; fill reconciliation pending")
                return best

            best.executed = False
            best.execution_status = str(result.get('decision_status') or result.get('status') or 'submission_failed')
            best.order_id = None
            best.entry_price = None
            return best
                
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            print(f"   ❌ Execution failed: {e}")
            return None
    
    def run_continuous(self, interval_seconds: int = 60, max_cycles: int = None):
        """Run continuous hunting loop."""
        print("\n🐺 Starting continuous hunt mode...")
        print(f"   Interval: {interval_seconds}s")
        print(f"   Max cycles: {max_cycles or 'infinite'}")
        print("   Press Ctrl+C to stop\n")
        
        cycle = 0
        while max_cycles is None or cycle < max_cycles:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"🔄 HUNT CYCLE {cycle}")
            print(f"{'='*60}")
            
            try:
                results = self.hunt()
                
                if results and not self.dry_run:
                    self.execute_best(results)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Hunt stopped by user")
                break
            except Exception as e:
                logger.error(f"Hunt cycle error: {e}")
                print(f"❌ Error: {e}")
            
            if max_cycles is None or cycle < max_cycles:
                print(f"\n⏳ Sleeping {interval_seconds}s until next hunt...")
                time.sleep(interval_seconds)
        
        print(f"\n🏁 Hunt complete. {len(self.hunt_history)} opportunities found.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🦈🎯 ORCA HUNTING GROUNDS - WHERE TO FISH FOR FASTEST KILLS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def find_best_hunting_grounds(self) -> List[Dict]:
        """
        🦈 Find the BEST hunting grounds using Orca's venue intelligence.
        
        Score = (volatility - cost) × liquidity
        
        Returns venues sorted by hunt_score (best first).
        """
        if not self.hunting_grounds:
            print("❌ Hunting Grounds not available!")
            return []
        
        print("\n" + "=" * 70)
        print("🦈🎯 ORCA HUNTING GROUNDS SCAN 🎯🦈")
        print("=" * 70)
        print("   Score = (volatility - cost) × liquidity")
        print("   Higher = Better hunting (more profit potential)")
        print()
        
        all_grounds = []
        
        # Scan Alpaca
        alpaca_grounds = self.hunting_grounds.scan_alpaca()
        print(f"   🦙 Alpaca: {len(alpaca_grounds)} grounds")
        all_grounds.extend(alpaca_grounds)
        
        # Scan Kraken
        kraken_grounds = self.hunting_grounds.scan_kraken()
        print(f"   🦑 Kraken: {len(kraken_grounds)} grounds")
        all_grounds.extend(kraken_grounds)
        
        # Sort by hunt score
        all_grounds.sort(key=lambda g: g.hunt_score, reverse=True)
        
        print()
        print("🎯 TOP HUNTING GROUNDS (where kills are fastest):")
        print("-" * 70)
        print(f"{'Exchange':<10} {'Symbol':<12} {'Vol%':>7} {'Cost%':>7} {'Liq':>5} {'Score':>8}")
        print("-" * 70)
        
        for g in all_grounds[:10]:
            print(f"{g.exchange:<10} {g.symbol:<12} {g.volatility_1h*100:>6.2f}% {g.round_trip_cost*100:>6.3f}% {g.liquidity_score:>5.2f} {g.hunt_score:>8.4f}")
        
        print("-" * 70)
        print()
        
        # Convert to dicts for return
        results = []
        for g in all_grounds[:10]:
            results.append({
                'exchange': g.exchange,
                'symbol': g.symbol,
                'price': g.price,
                'volatility': g.volatility_1h,
                'cost': g.round_trip_cost,
                'liquidity': g.liquidity_score,
                'hunt_score': g.hunt_score,
                'expected_net': (g.volatility_1h - g.round_trip_cost) * 100  # Expected % after fees
            })
        
        return results
    
    def smart_hunt(self) -> List[HuntResult]:
        """
        🦈🎯 SMART HUNT - Uses Orca's hunting grounds intelligence.
        
        1. Find best venues with highest kill potential
        2. Focus animal scanners on those venues
        3. Validate with full pipeline
        4. Execute fastest kill
        """
        print("\n" + "=" * 70)
        print("🦈🎯 ORCA SMART HUNT - FINDING FASTEST KILLS 🎯🦈")
        print("=" * 70)
        
        # Step 1: Find best hunting grounds
        grounds = self.find_best_hunting_grounds()
        
        if not grounds:
            print("❌ No hunting grounds found!")
            return []
        
        # Get top ground
        best_ground = grounds[0]
        print(f"\n🎯 BEST VENUE: {best_ground['exchange'].upper()} {best_ground['symbol']}")
        print(f"   Hunt Score: {best_ground['hunt_score']:.4f}")
        print(f"   Expected Net: {best_ground['expected_net']:+.3f}% after fees")
        
        # If best ground is on Alpaca, use our animal scanners
        # Otherwise fall back to standard hunt
        if best_ground['exchange'] == 'alpaca':
            print(f"\n   🦙 Focusing hunt on {best_ground['symbol']}...")
            
            # Standard hunt will pick this up
            return self.hunt()
        else:
            print(f"\n   ⚠️ Best venue is on {best_ground['exchange']} - using standard hunt")
            return self.hunt()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🦈🔪 ORCA KILL CHAIN - THE FULL INTELLIGENCE STACK FOR GROWTH
    # ═══════════════════════════════════════════════════════════════════════════
    
    def orca_kill_chain(self) -> Optional[Dict]:
        """
        🦈🔪 THE COMPLETE ORCA KILL CHAIN 🔪🦈
        
        Wires together ALL systems for maximum growth:
        
        1. 🎯 HUNTING GROUNDS - Find best venues (volatility - cost) × liquidity
        2. 🫒 BARTER MATRIX - Find conversion paths if stuck assets exist
        3. 🌊 OCEAN SCANNER - Scan 13,000+ symbols globally
        4. 🐺🦁🐜🐦 ANIMAL SWARM - Detect real-time momentum
        5. 🔮 PROBABILITY NEXUS - 3-pass validation
        6. 👑 QUEEN - 4th pass final decision
        7. 💰 EXECUTE - Quick kill for growth!
        
        Returns the executed trade result or None.
        """
        print("\n" + "=" * 70)
        print("🦈🔪 ORCA KILL CHAIN - HUNTING FOR GROWTH 🔪🦈")
        print("=" * 70)
        print("   Wiring: Hunting Grounds → Barter Matrix → Ocean → Momentum → Queen")
        print()
        
        # Track portfolio for growth measurement
        start_equity = None
        start_cash = None
        try:
            acct = self.alpaca.get_account()
            if not isinstance(acct, dict) or acct.get('equity') is None or acct.get('cash') is None:
                raise ValueError("account receipt missing equity/cash")
            start_equity = float(acct['equity'])
            start_cash = float(acct['cash'])
            if (
                not math.isfinite(start_equity)
                or not math.isfinite(start_cash)
                or start_equity < 0
                or start_cash < 0
            ):
                raise ValueError("account receipt contains invalid equity/cash")
            print(f"💰 Starting Portfolio: ${start_equity:.2f} equity, ${start_cash:.2f} cash")
        except Exception as exc:
            logger.warning("Starting portfolio unavailable: %s", exc)
            print("💰 Starting Portfolio: NO DATA")
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: 🎯 HUNTING GROUNDS - Where to fish?
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "-" * 50)
        print("PHASE 1: 🎯 HUNTING GROUNDS SCAN")
        print("-" * 50)
        
        grounds = self.find_best_hunting_grounds() if self.hunting_grounds else []
        
        if grounds:
            best = grounds[0]
            print(f"\n🎯 BEST HUNTING GROUND: {best['exchange'].upper()} {best['symbol']}")
            print(f"   Score: {best['hunt_score']:.4f}")
            print(f"   Volatility: {best['volatility']*100:.2f}%")
            print(f"   Cost: {best['cost']*100:.3f}%")
            print(f"   Expected Net: {best['expected_net']:+.3f}%")
        else:
            print("   No hunting grounds available")
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2: 🫒 BARTER MATRIX - Any stuck assets to convert?
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "-" * 50)
        print("PHASE 2: 🫒 BARTER MATRIX CHECK")
        print("-" * 50)
        
        barter_opportunity = None
        if self.barter and self.barter.assets:
            # Check if we have stuck assets that need converting
            try:
                balances = self.alpaca.get_all_balances() if hasattr(self.alpaca, 'get_all_balances') else {}
                
                # Find any non-USD assets we're holding
                stuck_assets = []
                for asset, amount in balances.items():
                    if asset != 'USD' and float(amount) > 0.01:
                        # Check if there's a better path to USD
                        path = self.barter.find_path(asset, 'USD', max_hops=3)
                        if path and path.total_rate > 0:
                            stuck_assets.append({
                                'asset': asset,
                                'amount': float(amount),
                                'path': path,
                                'expected_usd': float(amount) * path.total_rate
                            })
                
                if stuck_assets:
                    print(f"   Found {len(stuck_assets)} assets with conversion paths")
                    for sa in stuck_assets[:3]:
                        print(f"   🫒 {sa['asset']}: {sa['amount']:.4f} → ${sa['expected_usd']:.2f} USD")
                        print(f"      Path: {sa['path'].describe()}")
                else:
                    print("   ✅ No stuck assets - portfolio is clean")
            except Exception as e:
                print(f"   ⚠️ Barter check error: {e}")
        else:
            print("   Barter Matrix not available")
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 3: 🐺🦁🐜🐦 MOMENTUM SCAN - What's moving NOW?
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "-" * 50)
        print("PHASE 3: 🐺🦁🐜🐦 MOMENTUM SCAN")
        print("-" * 50)
        
        # Run the full hunt (includes animal swarm + nexus + queen)
        hunt_results = self.hunt()
        
        if not hunt_results:
            print("\n😴 No momentum opportunities found - market may be flat")
            print("   Orca waits for the right moment to strike...")
            return None
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 4: 🔪 EXECUTE THE KILL
        # ═══════════════════════════════════════════════════════════════════
        print("\n" + "-" * 50)
        print("PHASE 4: 🔪 EXECUTING THE KILL")
        print("-" * 50)
        
        # Rank by observed Queen confidence and provider-derived net edge.  Venue
        # metadata may inform reporting, but it must not manufacture confidence.
        hunt_results = [
            result for result in hunt_results
            if result.queen_confidence is not None and result.queen_approved
        ]
        if not hunt_results:
            print("   No proven Queen-approved opportunity remains")
            return None
        hunt_results.sort(key=lambda r: float(r.queen_confidence) * r.net_pct, reverse=True)
        
        best_kill = hunt_results[0]
        print(f"\n🎯 TARGET: {best_kill.symbol} {best_kill.side.upper()}")
        print(f"   Momentum: {best_kill.momentum_pct:+.2f}%")
        print(f"   Net Profit: {best_kill.net_pct:+.3f}%")
        print(f"   Queen Confidence: {best_kill.queen_confidence:.2f}")
        print(f"   Scanner: {best_kill.scanner_source}")
        
        if self.dry_run:
            print(f"\n   [DRY-RUN] Would execute {best_kill.side} on {best_kill.symbol}")
            return {
                'status': 'not_submitted',
                'truth_status': 'dry_run',
                'decision_status': 'not_submitted',
                'executed': False,
                'dry_run': True,
                'provider_order_id': None,
                'filled_qty': None,
                'filled_avg_price': None,
                'eligible_for_learning': False,
                'generated_values': False,
                'target': best_kill.symbol,
                'side': best_kill.side,
                'expected_net': best_kill.net_pct,
                'confidence': best_kill.queen_confidence
            }
        
        # Execute!
        executed = self.execute_best([best_kill])
        
        if executed and executed.execution_status == 'submitted' and executed.order_id:
            print(f"\n✅ ORDER SUBMITTED; FILL RECONCILIATION PENDING")
            print(f"   Provider Order ID: {executed.order_id}")
            return {
                'status': 'submitted',
                'truth_status': 'live',
                'decision_status': 'submitted',
                'executed': False,
                'provider_order_id': executed.order_id,
                'symbol': executed.symbol,
                'side': executed.side,
                'filled_qty': None,
                'filled_avg_price': None,
                'actual_pnl': None,
                'eligible_for_learning': False,
                'generated_values': False,
                'expected_net': best_kill.net_pct,
                'confidence': best_kill.queen_confidence,
            }

        if executed and executed.executed:
            print(f"\n✅ KILL EXECUTED!")
            print(f"   Order ID: {executed.order_id}")
            print(f"   Entry Price: ${executed.entry_price:.5f}")
            
            # Check growth
            try:
                acct = self.alpaca.get_account()
                if start_equity is None or not isinstance(acct, dict) or acct.get('equity') is None:
                    raise ValueError("paired equity receipts unavailable")
                end_equity = float(acct['equity'])
                if not math.isfinite(end_equity) or end_equity < 0 or start_equity <= 0:
                    raise ValueError("paired equity receipt invalid")
                growth = end_equity - start_equity
                growth_pct = growth / start_equity * 100
                print(f"\n📈 GROWTH: ${growth:+.2f} ({growth_pct:+.2f}%)")
            except Exception as exc:
                logger.warning("Growth readback unavailable: %s", exc)
            
            return {
                'executed': True,
                'order_id': executed.order_id,
                'symbol': executed.symbol,
                'side': executed.side,
                'entry_price': executed.entry_price,
                'expected_net': best_kill.net_pct,
                'confidence': best_kill.queen_confidence
            }
        
        print("\n❌ Kill execution failed")
        return None
    
    def continuous_kill_chain(self, interval_seconds: int = 60, max_cycles: int = None):
        """
        🦈 Run continuous Orca Kill Chain hunting.
        
        This is the GROWTH MODE - continuously hunting for quick kills.
        """
        print("\n" + "=" * 70)
        print("🦈🔪 ORCA CONTINUOUS KILL CHAIN - GROWTH MODE 🔪🦈")
        print("=" * 70)
        print(f"   Interval: {interval_seconds}s between hunts")
        print(f"   Max cycles: {max_cycles or 'infinite'}")
        print("   Press Ctrl+C to stop")
        print()
        
        cycle = 0
        total_executed = 0
        total_profit = 0.0
        
        while max_cycles is None or cycle < max_cycles:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"🔄 KILL CHAIN CYCLE {cycle}")
            print(f"{'='*60}")
            
            try:
                result = self.orca_kill_chain()
                
                if result and result.get('executed'):
                    total_executed += 1
                    # Track profit when trade closes
                
            except KeyboardInterrupt:
                print("\n\n🛑 Kill chain stopped by user")
                break
            except Exception as e:
                logger.error(f"Kill chain error: {e}")
                print(f"❌ Error: {e}")
            
            print(f"\n📊 Session Stats: {total_executed} kills executed")
            
            if max_cycles is None or cycle < max_cycles:
                print(f"\n⏳ Sleeping {interval_seconds}s until next hunt...")
                time.sleep(interval_seconds)
        
        print(f"\n🏁 Kill chain complete. {total_executed} total kills.")


# ═══════════════════════════════════════════════════════════════════════════
# 🚀 QUICK RUN FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def quick_scan():
    """Quick scan - find opportunities without executing."""
    hunter = LiveMomentumHunter(dry_run=False)
    return hunter.hunt()


def quick_hunt():
    """Quick hunt - find and execute best opportunity."""
    hunter = LiveMomentumHunter(dry_run=False)
    results = hunter.hunt()
    if results:
        return hunter.execute_best(results)
    return None


def continuous_hunt(interval: int = 60):
    """Run continuous hunting."""
    hunter = LiveMomentumHunter(dry_run=False)
    hunter.run_continuous(interval_seconds=interval)


def smart_scan():
    """🦈 Smart scan - use Orca's hunting grounds to find best venues."""
    hunter = LiveMomentumHunter(dry_run=False)
    return hunter.smart_hunt()


def find_hunting_grounds():
    """🎯 Show the best hunting grounds across all exchanges."""
    hunter = LiveMomentumHunter(dry_run=False)
    return hunter.find_best_hunting_grounds()


def orca_kill():
    """🦈🔪 Run the full Orca Kill Chain for GROWTH."""
    hunter = LiveMomentumHunter(dry_run=False)
    return hunter.orca_kill_chain()


def orca_kill_dry():
    """🦈 Run Orca Kill Chain in dry-run mode (no real trades)."""
    hunter = LiveMomentumHunter(dry_run=False)
    return hunter.orca_kill_chain()


def orca_growth_mode(interval: int = 60):
    """🦈📈 Run continuous Orca Kill Chain for portfolio GROWTH."""
    hunter = LiveMomentumHunter(dry_run=False)
    hunter.continuous_kill_chain(interval_seconds=interval)


# ═══════════════════════════════════════════════════════════════════════════
# 🎮 MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='🎯 Aureon Live Momentum Hunter')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no real trades)')
    parser.add_argument('--execute', action='store_true', help='Execute best opportunity')
    parser.add_argument('--continuous', action='store_true', help='Run continuous hunting')
    parser.add_argument('--interval', type=int, default=60, help='Interval between hunts (seconds)')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s'
    )
    
    # Suppress noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('alpaca').setLevel(logging.WARNING)
    
    hunter = LiveMomentumHunter(dry_run=args.dry_run or not args.execute)
    
    if args.continuous:
        hunter.run_continuous(interval_seconds=args.interval)
    else:
        results = hunter.hunt()
        
        if results and args.execute and not args.dry_run:
            hunter.execute_best(results)


if __name__ == '__main__':
    main()
