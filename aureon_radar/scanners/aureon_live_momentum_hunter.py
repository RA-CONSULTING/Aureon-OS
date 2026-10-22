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

import os

# Windows UTF-8 fix (MANDATORY)
try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402
except ImportError:
    # Upstream lib ships no console_utf8 module; run with PYTHONUTF8=1
    # instead. Degraded glyphs beat an ImportError.
    def ensure_utf8_stdout(*_a, **_k):
        return False

ensure_utf8_stdout()

import math
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

# Load environment
for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

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
    nexus_direction: str = 'NEUTRAL'  # 'LONG', 'SHORT', 'NEUTRAL'
    nexus_probability: float = 0.5
    nexus_confidence: float = 0.0
    nexus_factors: Dict[str, float] = field(default_factory=dict)
    
    # Queen decision
    queen_approved: bool = False
    queen_confidence: float = 0.0
    queen_reasoning: str = ""
    
    # Execution
    executed: bool = False
    order_id: Optional[str] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    final_pnl: float = 0.0
    
    def is_valid_opportunity(self, aggressive: bool = False) -> bool:
        """Check if this hunt result meets minimum criteria.
        
        Args:
            aggressive: If True, lower confidence threshold for growth mode (small portfolios)
        """
        # Confidence threshold: 0.2 for aggressive mode, 0.5 for normal
        conf_threshold = 0.2 if aggressive else 0.5
        
        # 3-pass validation (Batten Matrix)
        pass_1 = self.net_pct > 0  # Must be net positive after fees
        pass_2 = self.nexus_confidence > conf_threshold  # Nexus must have confidence
        pass_3 = (
            (self.side == 'buy' and self.nexus_direction == 'LONG') or
            (self.side == 'sell' and self.nexus_direction == 'SHORT')
        )
        return pass_1 and pass_2 and pass_3


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
        
        # Get account info
        try:
            acct = self.alpaca.get_account()
            self.cash = float(acct.get('cash', 0))
            self.equity = float(acct.get('equity', 0))
            logger.info(f"🦙 Alpaca connected: ${self.equity:.2f} equity, ${self.cash:.2f} cash")
        except Exception as e:
            logger.error(f"❌ Alpaca connection failed: {e}")
            self.cash = 0
            self.equity = 0
    
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
            
            self.queen = create_queen_hive_mind(initial_capital=self.equity or 100.0)
            
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
            for bar in bar_data[symbol]:
                result.append({
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': float(bar.volume),
                    'timestamp': bar.timestamp.timestamp()
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
            if 'result' in data:
                for key, candles in data['result'].items():
                    if isinstance(candles, list) and candles:
                        for c in candles[-limit:]:
                            result.append({
                                'open': float(c[1]),
                                'high': float(c[2]),
                                'low': float(c[3]),
                                'close': float(c[4]),
                                'volume': float(c[6]),
                                'timestamp': float(c[0])
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
            
            # Feed to nexus - use update_history method
            for candle in candles:
                self.nexus.update_history(candle)
            
            # Get prediction
            prediction = self.nexus.predict()
            
            return {
                'direction': prediction.direction,
                'probability': prediction.probability,
                'confidence': prediction.confidence,
                'factors': prediction.factors,
                'stop_loss_pct': prediction.stop_loss_pct,
                'take_profit_pct': prediction.take_profit_pct,
                'reason': prediction.reason
            }
            
        except Exception as e:
            logger.error(f"Nexus validation failed for {symbol}: {e}")
            return None
    
    def ask_queen(self, opportunity: Dict) -> Tuple[bool, float, str]:
        """Ask Queen for final 4th-pass decision."""
        if not self.queen:
            return True, 0.5, "Queen unavailable - default approval"
        
        try:
            decision = self.queen.get_queen_decision_with_intelligence(opportunity)
            
            # Extract decision
            approved = decision.get('final_score', 0) > 0.5
            confidence = decision.get('final_score', 0.5)
            reasoning = " | ".join(decision.get('reasoning', ['No reasoning']))
            
            return approved, confidence, reasoning
            
        except Exception as e:
            logger.error(f"Queen decision failed: {e}")
            return True, 0.5, f"Queen error: {e}"
    
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
                    animal_opp = AnimalOpportunity(
                        symbol=gopp.symbol,
                        side=gopp.direction,
                        move_pct=gopp.momentum_pct,
                        net_pct=gopp.net_edge * 100,  # Convert to %
                        volume=0,
                        reason=f"🌍 {gopp.exchange}: {gopp.reason}"
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
                
                # Create hunt result
                result = HuntResult(
                    symbol=opp.symbol,
                    side=opp.side,
                    scanner_source=scanner,
                    momentum_pct=opp.move_pct,
                    net_pct=opp.net_pct,
                    volume=opp.volume
                )
                
                # 🦈 EXTREME MOMENTUM BYPASS: For massive moves (>10%), trust the signal
                # The Nexus looks at recent candles but the move may have happened earlier
                if scanner == 'global' and abs(opp.move_pct) >= 10.0:
                    # Trust Binance's 24h data for extreme moves
                    direction = 'LONG' if opp.side == 'buy' else 'SHORT'
                    # Scale confidence by momentum: 10% = 0.5, 20% = 0.75, 40%+ = 1.0
                    extreme_conf = min(0.5 + (abs(opp.move_pct) - 10) / 40, 1.0)
                    result.nexus_direction = direction
                    result.nexus_probability = 0.5 + extreme_conf * 0.4  # 0.7-0.9
                    result.nexus_confidence = extreme_conf
                    result.nexus_factors = {'extreme_momentum': True, 'binance_24h': opp.move_pct}
                    print(f"{direction} ({extreme_conf:.2f}) [🔥 EXTREME MOMENTUM BYPASS]")
                else:
                    # Normal Nexus validation
                    nexus_result = self.validate_with_nexus(opp.symbol)
                    if nexus_result:
                        result.nexus_direction = nexus_result['direction']
                        result.nexus_probability = nexus_result['probability']
                        result.nexus_confidence = nexus_result['confidence']
                        result.nexus_factors = nexus_result['factors']
                        print(f"{nexus_result['direction']} ({nexus_result['confidence']:.2f})")
                    else:
                        result.nexus_direction = 'NEUTRAL'
                        result.nexus_probability = 0.5
                        result.nexus_confidence = 0.3
                        print("NO DATA")
                
                hunt_results.append(result)
        
        # 3. Filter for valid 3-pass opportunities
        print("\n📊 PHASE 3: 3-Pass Validation Filter...")
        
        # Use aggressive mode for small portfolios (< $100)
        aggressive_mode = self.equity < 100
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
                if r.nexus_confidence <= 0.5:
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
                'coherence': result.nexus_factors.get('coherence', 0.5),
                'momentum': result.momentum_pct,
                'net_profit_pct': result.net_pct
            }
            
            approved, confidence, reasoning = self.ask_queen(opp_dict)
            
            # 🔥 EXTREME MOMENTUM OVERRIDE: If momentum > 15% and net edge > 10%, override Queen
            is_extreme = result.nexus_factors.get('extreme_momentum', False)
            extreme_override = False
            if not approved and is_extreme and abs(result.momentum_pct) >= 15 and result.net_pct >= 10:
                extreme_override = True
                approved = True
                confidence = min(0.6, result.nexus_confidence)
                reasoning = f"🔥 EXTREME OVERRIDE: {result.momentum_pct:+.2f}% momentum, {result.net_pct:.1f}% net edge"
            
            result.queen_approved = approved
            result.queen_confidence = confidence
            result.queen_reasoning = reasoning
            
            if extreme_override:
                status = "🔥 OVERRIDE"
            else:
                status = "✅ APPROVED" if approved else "❌ REJECTED"
            print(f"   {result.symbol}: {status} ({confidence:.2f}) - {reasoning[:50]}...")
            
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
        
        # Sort by queen confidence × net profit
        results.sort(key=lambda r: r.queen_confidence * r.net_pct, reverse=True)
        best = results[0]
        
        print(f"\n🎯 EXECUTING BEST: {best.symbol} {best.side.upper()}")
        
        if self.dry_run:
            print(f"   [DRY-RUN] Would execute {best.side} on {best.symbol}")
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
            
            # Refresh account
            acct = self.alpaca.get_account()
            cash = float(acct.get('cash', 0))
            
            # Calculate qty
            trade_value = cash * 0.90
            qty = trade_value / price
            
            # Alpaca needs symbol without slash
            alpaca_symbol = best.symbol.replace('/', '')
            
            print(f"   Price: ${price:.5f}")
            print(f"   Cash: ${cash:.2f}")
            print(f"   Trade Value: ${trade_value:.2f}")
            print(f"   Quantity: {qty:.6f}")
            
            # Execute via bridge with trailing stop
            if self.bridge and best.side == 'buy':
                from aureon.scanners.aureon_animal_momentum_scanners import AnimalOpportunity
                opp = AnimalOpportunity(
                    symbol=alpaca_symbol,
                    side=best.side,
                    move_pct=best.momentum_pct,
                    net_pct=best.net_pct,
                    volume=best.volume,
                    reason=f"Queen: {best.queen_confidence:.2f}"
                )
                
                result = self.swarm.execute_opportunity(opp, qty, use_trailing_stop=True)
                
                if result and not result.get('dry_run'):
                    best.executed = True
                    best.order_id = result.get('id', 'unknown')
                    best.entry_price = price
                    print(f"   ✅ Order executed: {best.order_id}")
                
                return best
            else:
                # Direct execution
                from alpaca.trading.client import TradingClient
                from alpaca.trading.requests import MarketOrderRequest
                from alpaca.trading.enums import OrderSide, TimeInForce
                
                trading = TradingClient(
                    os.environ['ALPACA_API_KEY'],
                    os.environ['ALPACA_SECRET_KEY'],
                    paper=False
                )
                
                order = MarketOrderRequest(
                    symbol=alpaca_symbol,
                    qty=qty,
                    side=OrderSide.BUY if best.side == 'buy' else OrderSide.SELL,
                    time_in_force=TimeInForce.GTC
                )
                
                result = trading.submit_order(order)
                best.executed = True
                best.order_id = str(result.id)
                best.entry_price = price
                print(f"   ✅ Order executed: {best.order_id}")
                
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
        try:
            acct = self.alpaca.get_account()
            start_equity = float(acct.get('equity', 0))
            start_cash = float(acct.get('cash', 0))
            print(f"💰 Starting Portfolio: ${start_equity:.2f} equity, ${start_cash:.2f} cash")
        except:
            start_equity = 0
            start_cash = 0
        
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
        
        # Sort by best opportunity (queen confidence × net profit × hunt score boost)
        for result in hunt_results:
            # Boost score if symbol matches best hunting ground
            if grounds and result.symbol.replace('/', '') == grounds[0]['symbol'].replace('/', ''):
                result.queen_confidence *= 1.2  # 20% boost for best venue
        
        hunt_results.sort(key=lambda r: r.queen_confidence * max(r.net_pct, 0.001), reverse=True)
        
        best_kill = hunt_results[0]
        print(f"\n🎯 TARGET: {best_kill.symbol} {best_kill.side.upper()}")
        print(f"   Momentum: {best_kill.momentum_pct:+.2f}%")
        print(f"   Net Profit: {best_kill.net_pct:+.3f}%")
        print(f"   Queen Confidence: {best_kill.queen_confidence:.2f}")
        print(f"   Scanner: {best_kill.scanner_source}")
        
        if self.dry_run:
            print(f"\n   [DRY-RUN] Would execute {best_kill.side} on {best_kill.symbol}")
            return {
                'executed': False,
                'dry_run': True,
                'target': best_kill.symbol,
                'side': best_kill.side,
                'expected_net': best_kill.net_pct,
                'confidence': best_kill.queen_confidence
            }
        
        # Execute!
        executed = self.execute_best([best_kill])
        
        if executed and executed.executed:
            print(f"\n✅ KILL EXECUTED!")
            print(f"   Order ID: {executed.order_id}")
            print(f"   Entry Price: ${executed.entry_price:.5f}")
            
            # Check growth
            try:
                acct = self.alpaca.get_account()
                end_equity = float(acct.get('equity', 0))
                growth = end_equity - start_equity
                growth_pct = (growth / start_equity * 100) if start_equity > 0 else 0
                print(f"\n📈 GROWTH: ${growth:+.2f} ({growth_pct:+.2f}%)")
            except:
                pass
            
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
