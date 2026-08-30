#!/usr/bin/env python3
"""
🧠🔥 AUREON REAL INTELLIGENCE ENGINE 🔥🧠
==========================================
REPLACES RANDOM SIMULATION WITH ACTUAL INTELLIGENCE SYSTEMS

This module connects:
1. Bot Profiler → Identifies Jane Street, Citadel, etc. by trading patterns
2. Whale Predictor → 3-pass validation for whale behavior prediction
3. Animal Momentum Scanners → Wolf, Lion, Ants, Hummingbird
4. Firm Pattern Recognition → Pattern-based firm attribution

All validated data flows to Queen for REAL trade decisions.

Gary Leckey & Tina Brown | January 2026 | REAL INTELLIGENCE
"""

import time
import json
import math
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Sacred constants
PHI = 1.618033988749895
SCHUMANN = 7.83
LOVE_FREQ = 528

# ═══════════════════════════════════════════════════════════════════════════════
# REAL INTELLIGENCE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

# Try importing real systems - fallback gracefully if unavailable
_BOT_PROFILER_AVAILABLE = False
_WHALE_PREDICTOR_AVAILABLE = False
_MOMENTUM_SCANNERS_AVAILABLE = False

try:
    from aureon.bots_intelligence.aureon_bot_intelligence_profiler import (
        TRADING_FIRM_SIGNATURES,
        BotIntelligenceProfiler,
    )
    _BOT_PROFILER_AVAILABLE = True
    _bot_profiler = None  # Will create instance when needed
    logger.info("✅ Bot Profiler LOADED - Real firm detection available")
except ImportError as e:
    logger.warning(f"⚠️ Bot Profiler not available: {e}")
    TRADING_FIRM_SIGNATURES = {}
    _bot_profiler = None

try:
    from aureon.analytics.aureon_whale_behavior_predictor import (
        WhaleBehaviorPredictor,
        default_predictor as _whale_predictor
    )
    _WHALE_PREDICTOR_AVAILABLE = True
    logger.info("✅ Whale Predictor LOADED - 3-pass validation available")
except ImportError as e:
    logger.warning(f"⚠️ Whale Predictor not available: {e}")
    _whale_predictor = None

try:
    from aureon.scanners.aureon_animal_momentum_scanners import (
        AlpacaSwarmOrchestrator,
        AlpacaLoneWolf,
        AlpacaLionHunt,
        AlpacaArmyAnts,
        AlpacaHummingbird,
        AnimalOpportunity
    )
    _MOMENTUM_SCANNERS_AVAILABLE = True
    logger.info("✅ Animal Momentum Scanners LOADED")
except ImportError as e:
    logger.warning(f"⚠️ Momentum Scanners not available: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BotProfile:
    """Identified bot with firm attribution"""
    symbol: str
    bot_type: str
    firm: str
    firm_animal: str
    confidence: float
    hft_frequency: int
    layering_score: float
    timing_ms: int
    estimated_capital: int
    known_strategies: List[str]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class WhalePrediction:
    """Predicted whale behavior with validation"""
    symbol: str
    action: str  # buy, sell, lean_buy, lean_sell, wait
    confidence: float
    time_horizon_minutes: int
    validators: Dict[str, float]  # p1, p2, p3, p4
    coherence: float
    lambda_stability: float
    validated: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class MomentumOpportunity:
    """Momentum-based trade opportunity"""
    symbol: str
    scanner_type: str  # wolf, lion, ants, hummingbird
    side: str
    move_pct: float
    net_pct: float
    volume: float
    reason: str
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class ValidatedIntelligence:
    """Combined intelligence for Queen decision-making"""
    symbol: str
    bot_profiles: List[BotProfile]
    whale_predictions: List[WhalePrediction]
    momentum_opportunities: List[MomentumOpportunity]
    composite_score: float
    recommended_action: str
    reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ═══════════════════════════════════════════════════════════════════════════════
# REAL BOT PROFILER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class RealBotProfiler:
    """Uses aureon_bot_intelligence_profiler for REAL firm identification"""
    
    def __init__(self):
        self.profiler = _bot_profiler if _BOT_PROFILER_AVAILABLE else None
        self.firm_signatures = TRADING_FIRM_SIGNATURES if _BOT_PROFILER_AVAILABLE else {}
        self.detected_count = 0
        
    def profile_trading_activity(self, symbol: str, trade_data: Dict) -> Optional[BotProfile]:
        """Analyze trading activity and identify firm patterns"""
        
        if not self.firm_signatures:
            return None
            
        # Extract features from trade data
        hft_freq = trade_data.get('hft_frequency', 0)
        order_consistency = trade_data.get('order_size_consistency', 0.5)
        latency = trade_data.get('latency_ms', 100)
        volume = trade_data.get('volume', 0)
        
        best_match = None
        best_score = 0.0
        
        for firm_id, firm_data in self.firm_signatures.items():
            patterns = firm_data.get('patterns', {})
            
            # Match HFT frequency range
            freq_range = patterns.get('hft_frequency', (0, 1000))
            freq_score = 1.0 if freq_range[0] <= hft_freq <= freq_range[1] else 0.3
            
            # Match order consistency
            expected_consistency = patterns.get('order_size_consistency', 0.5)
            consistency_diff = abs(order_consistency - expected_consistency)
            consistency_score = max(0, 1.0 - consistency_diff * 2)
            
            # Match latency profile
            latency_profile = patterns.get('latency_profile', 'medium')
            latency_score = 0.5
            if latency_profile == 'ultra_low' and latency < 20:
                latency_score = 1.0
            elif latency_profile == 'low' and latency < 50:
                latency_score = 0.9
            elif latency_profile == 'medium' and 50 <= latency < 150:
                latency_score = 0.8
            elif latency_profile == 'high' and latency >= 150:
                latency_score = 0.7
            
            # Composite score
            composite = (freq_score * 0.4 + consistency_score * 0.35 + latency_score * 0.25)
            
            if composite > best_score:
                best_score = composite
                best_match = (firm_id, firm_data)
        
        if best_match and best_score > 0.5:
            firm_id, firm_data = best_match
            self.detected_count += 1
            
            return BotProfile(
                symbol=symbol,
                bot_type=self._classify_bot_type(firm_data.get('known_strategies', [])),
                firm=firm_data.get('name', firm_id),
                firm_animal=firm_data.get('animal', '🤖'),
                confidence=best_score,
                hft_frequency=hft_freq,
                layering_score=trade_data.get('layering_score', 0),
                timing_ms=latency,
                estimated_capital=firm_data.get('estimated_capital', 0),
                known_strategies=firm_data.get('known_strategies', [])
            )
        
        return None
    
    def _classify_bot_type(self, strategies: List[str]) -> str:
        """Classify bot type based on strategies"""
        if 'hft' in strategies or 'market_making' in strategies:
            return 'HFT'
        elif 'arbitrage' in strategies:
            return 'ARBITRAGE'
        elif 'momentum' in strategies:
            return 'MOMENTUM'
        elif 'statistical_arbitrage' in strategies:
            return 'STAT_ARB'
        elif 'macro' in strategies:
            return 'MACRO'
        else:
            return 'QUANT'
    
    def scan_market_for_bots(self, prices: Dict, orderbook_data: Dict = None) -> List[BotProfile]:
        """Scan market data for bot activity"""
        detected_bots = []
        
        for symbol, price in prices.items():
            volume = self._get_volume(symbol, orderbook_data)
            if volume is None:
                continue
            trade_data = {
                'hft_frequency': self._estimate_hft_frequency(symbol, orderbook_data),
                'order_size_consistency': self._estimate_order_consistency(orderbook_data),
                'latency_ms': self._estimate_latency(orderbook_data),
                'volume': volume,
                'layering_score': self._detect_layering(orderbook_data)
            }
            
            profile = self.profile_trading_activity(symbol, trade_data)
            if profile:
                detected_bots.append(profile)
        
        return detected_bots
    
    def _estimate_hft_frequency(self, symbol: str, orderbook: Dict) -> int:
        """Estimate HFT frequency from orderbook updates"""
        if orderbook and symbol in orderbook:
            updates = orderbook[symbol].get('update_count', 0)
            return min(300, max(5, updates // 10))
        return 50  # Default
    
    def _estimate_order_consistency(self, orderbook: Dict) -> float:
        """Estimate order size consistency from real L2 orderbook entries.

        Returns a score in [0, 1] where 1 = highly consistent order sizes
        (algorithmic trading signature) and 0 = highly varied sizes (more
        retail-like). Computed as 1 / (1 + CV) where CV = stdev/mean of
        all order qty values across bids+asks for every symbol present.

        Returns 0.0 only when orderbook is empty / unparseable — in which
        case there's no real signal to surface.
        """
        if not orderbook:
            return 0.0
        try:
            qty_values: List[float] = []
            iterable = orderbook.values() if isinstance(orderbook, dict) else []
            for sym_book in iterable:
                if not isinstance(sym_book, dict):
                    continue
                for side in ("bids", "asks"):
                    rows = sym_book.get(side) or []
                    for row in rows:
                        try:
                            # Accept (price, qty), {'price','qty'}, or [price,qty]
                            if isinstance(row, dict):
                                q = float(row.get("qty") or row.get("size") or 0)
                            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                                q = float(row[1])
                            else:
                                continue
                        except (ValueError, TypeError):
                            continue
                        if q > 0:
                            qty_values.append(q)
            if len(qty_values) < 4:
                return 0.0   # Too few orders to compute meaningful CV
            mean = sum(qty_values) / len(qty_values)
            if mean <= 0:
                return 0.0
            var = sum((q - mean) ** 2 for q in qty_values) / len(qty_values)
            stdev = var ** 0.5
            cv = stdev / mean
            # Map CV → consistency. CV=0 → 1.0; CV=1 → 0.5; CV→∞ → 0.
            return max(0.0, min(1.0, 1.0 / (1.0 + cv)))
        except Exception as exc:
            logger.debug("_estimate_order_consistency unexpected error: %s", exc)
            return 0.0

    def _estimate_latency(self, orderbook: Dict) -> int:
        """Estimate effective WebSocket latency from per-symbol update timing.

        Real measurement requires exchange-side ack timestamps which the
        existing client interfaces don't currently expose. As a best-effort
        proxy, infer from the cadence of update events the orderbook
        records: tighter cadences imply lower latency. Returns latency in
        ms rounded to the nearest 5; returns -1 sentinel only when no
        timing data is present.
        """
        if not orderbook:
            return -1
        try:
            cadences: List[float] = []
            for sym_book in orderbook.values() if isinstance(orderbook, dict) else []:
                if not isinstance(sym_book, dict):
                    continue
                last_update = sym_book.get("last_update_ts") or sym_book.get("ts")
                prev_update = sym_book.get("prev_update_ts")
                if last_update and prev_update:
                    try:
                        delta = float(last_update) - float(prev_update)
                        if 0 < delta < 60:  # only sensible cadences
                            cadences.append(delta * 1000.0)
                    except (ValueError, TypeError):
                        continue
            if not cadences:
                return -1
            avg_ms = sum(cadences) / len(cadences)
            # Round to nearest 5 ms
            return int(round(avg_ms / 5.0) * 5)
        except Exception as exc:
            logger.debug("_estimate_latency unexpected error: %s", exc)
            return -1

    def _get_volume(self, symbol: str, orderbook: Dict) -> Optional[float]:
        """Return an observed finite volume, or None when it is absent."""
        if not isinstance(orderbook, dict):
            return None
        symbol_book = orderbook.get(symbol)
        if not isinstance(symbol_book, dict) or "volume" not in symbol_book:
            return None
        try:
            volume = float(symbol_book["volume"])
        except (TypeError, ValueError):
            return None
        return volume if math.isfinite(volume) and volume >= 0.0 else None

    def _detect_layering(self, orderbook: Dict) -> float:
        """Detect L2 orderbook layering (multi-level bid/ask wall stacking).

        Layering = placing multiple sizable orders behind the top of book
        to create false depth. Computed as: ratio of (qty in levels 2-N)
        to (qty at top of book). Higher ratio means more layering.

        Returns score in [0, 1] capped — 0 = no layering (all qty at top
        of book or no data), 1 = heavy layering (deeper levels carry far
        more qty than top).
        """
        if not orderbook:
            return 0.0
        try:
            scores: List[float] = []
            for sym_book in orderbook.values() if isinstance(orderbook, dict) else []:
                if not isinstance(sym_book, dict):
                    continue
                for side in ("bids", "asks"):
                    rows = sym_book.get(side) or []
                    if len(rows) < 3:
                        continue
                    qtys: List[float] = []
                    for row in rows:
                        try:
                            if isinstance(row, dict):
                                q = float(row.get("qty") or row.get("size") or 0)
                            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                                q = float(row[1])
                            else:
                                continue
                        except (ValueError, TypeError):
                            continue
                        if q > 0:
                            qtys.append(q)
                    if len(qtys) < 3:
                        continue
                    top_qty = qtys[0]
                    deeper_qty = sum(qtys[1:])
                    if top_qty <= 0:
                        continue
                    ratio = deeper_qty / top_qty
                    # Cap at 1.0 — beyond ratio=1 is heavy layering
                    scores.append(min(1.0, ratio / 4.0))
            if not scores:
                return 0.0
            return sum(scores) / len(scores)
        except Exception as exc:
            logger.debug("_detect_layering unexpected error: %s", exc)
            return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# REAL WHALE PREDICTOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class RealWhalePredictor:
    """Uses aureon_whale_behavior_predictor for 3-pass validated predictions"""
    
    def __init__(self):
        self.predictor = _whale_predictor
        self.predictions_made = 0
        self.validated_predictions = 0
        
    def predict_whale_behavior(self, symbol: str, whale_data: Dict = None) -> Optional[WhalePrediction]:
        """Run 3-pass validation and predict whale behavior"""
        
        if self.predictor:
            try:
                # Use real predictor with 4 validators (p1-p4)
                result = self.predictor.predict_next_move(symbol)
                
                if result:
                    self.predictions_made += 1
                    
                    # Check if validated (coherence > 0.618 golden ratio)
                    validated = result.get('coherence', 0) > 0.618
                    if validated:
                        self.validated_predictions += 1
                    
                    return WhalePrediction(
                        symbol=symbol,
                        action=result.get('action', 'wait'),
                        confidence=result.get('confidence', 0),
                        time_horizon_minutes=result.get('time_horizon_minutes', 30),
                        validators=result.get('validators', {}),
                        coherence=result.get('coherence', 0),
                        lambda_stability=result.get('lambda', 1.0),
                        validated=validated
                    )
            except Exception as e:
                logger.warning(f"Whale prediction error for {symbol}: {e}")
        
        # Fallback: basic pattern analysis
        return self._fallback_prediction(symbol, whale_data)
    
    def _fallback_prediction(self, symbol: str, whale_data: Dict) -> Optional[WhalePrediction]:
        """Fallback prediction without full predictor"""
        if not whale_data:
            return None
            
        side = whale_data.get('side', 'unknown')
        size = whale_data.get('size_usd', 0)
        
        # Simple heuristic
        confidence = min(0.7, size / 1000000)  # Higher size = higher confidence
        action = 'lean_buy' if side == 'BUY' else 'lean_sell' if side == 'SELL' else 'wait'
        
        return WhalePrediction(
            symbol=symbol,
            action=action,
            confidence=confidence,
            time_horizon_minutes=30,
            validators={'p1': 0.5, 'p2': 0.5, 'p3': 0.5, 'p4': 0.5},
            coherence=0.5,
            lambda_stability=0.8,
            validated=False
        )
    
    def bulk_predict(self, whale_alerts: List[Dict]) -> List[WhalePrediction]:
        """Run predictions for multiple whale alerts"""
        predictions = []
        
        for alert in whale_alerts:
            symbol = alert.get('symbol', '')
            if symbol:
                pred = self.predict_whale_behavior(symbol, alert)
                if pred:
                    predictions.append(pred)
        
        return predictions


# ═══════════════════════════════════════════════════════════════════════════════
# REAL MOMENTUM SCANNER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class RealMomentumScanner:
    """Uses aureon_animal_momentum_scanners for REAL momentum detection"""
    
    def __init__(self):
        self.orchestrator = None
        self.wolf = None
        self.lion = None
        self.ants = None
        self.hummingbird = None
        self._init_scanners()
        self.scan_count = 0
        
    def _init_scanners(self):
        """Initialize momentum scanners if available"""
        if not _MOMENTUM_SCANNERS_AVAILABLE:
            logger.warning("⚠️ Momentum scanners not available - using fallback")
            return
            
        try:
            from aureon.exchanges.alpaca_client import AlpacaClient
            from aureon.bridges.aureon_alpaca_scanner_bridge import AlpacaScannerBridge
            
            # Initialize Alpaca client
            alpaca = AlpacaClient()
            bridge = AlpacaScannerBridge(alpaca)
            
            # Initialize all animal scanners
            self.wolf = AlpacaLoneWolf(alpaca, bridge)
            self.lion = AlpacaLionHunt(alpaca, bridge)
            self.ants = AlpacaArmyAnts(alpaca, bridge)
            self.hummingbird = AlpacaHummingbird(alpaca, bridge)
            self.orchestrator = AlpacaSwarmOrchestrator(alpaca, bridge)
            
            logger.info("✅ All 4 animal scanners initialized (Wolf, Lion, Ants, Hummingbird)")
        except Exception as e:
            logger.warning(f"⚠️ Scanner initialization failed: {e}")
    
    def scan_all_momentum(self) -> Dict[str, List[MomentumOpportunity]]:
        """Run all momentum scanners and return opportunities"""
        results = {
            'wolf': [],
            'lion': [],
            'ants': [],
            'hummingbird': []
        }
        
        self.scan_count += 1
        
        if self.wolf:
            try:
                wolf_result = self.wolf.stalk()
                if wolf_result:
                    results['wolf'].append(self._convert_opportunity(wolf_result, 'wolf'))
            except Exception as e:
                logger.debug(f"Wolf scan error: {e}")
        
        if self.lion:
            try:
                lion_results = self.lion.hunt(limit=5)
                for opp in lion_results:
                    results['lion'].append(self._convert_opportunity(opp, 'lion'))
            except Exception as e:
                logger.debug(f"Lion scan error: {e}")
        
        if self.ants:
            try:
                ant_results = self.ants.forage(max_targets=10)
                for opp in ant_results:
                    results['ants'].append(self._convert_opportunity(opp, 'ants'))
            except Exception as e:
                logger.debug(f"Ants scan error: {e}")
        
        if self.hummingbird:
            try:
                hb_results = self.hummingbird.pollinate(limit=5)
                for opp in hb_results:
                    results['hummingbird'].append(self._convert_opportunity(opp, 'hummingbird'))
            except Exception as e:
                logger.debug(f"Hummingbird scan error: {e}")
        
        return results
    
    def _convert_opportunity(self, opp: Any, scanner_type: str) -> MomentumOpportunity:
        """Convert animal scanner opportunity to standard format"""
        if hasattr(opp, 'symbol'):
            return MomentumOpportunity(
                symbol=opp.symbol,
                scanner_type=scanner_type,
                side=opp.side,
                move_pct=opp.move_pct,
                net_pct=opp.net_pct,
                volume=opp.volume,
                reason=opp.reason,
                confidence=abs(opp.net_pct) / 2.0  # Higher net profit = higher confidence
            )
        else:
            # Dict format
            return MomentumOpportunity(
                symbol=opp.get('symbol', 'UNKNOWN'),
                scanner_type=scanner_type,
                side=opp.get('side', 'hold'),
                move_pct=opp.get('move_pct', 0),
                net_pct=opp.get('net_pct', 0),
                volume=opp.get('volume', 0),
                reason=opp.get('reason', ''),
                confidence=abs(opp.get('net_pct', 0)) / 2.0
            )


# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class RealIntelligenceEngine:
    """
    🧠 MASTER INTELLIGENCE ENGINE
    
    Combines all intelligence sources:
    - Bot Profiler (firm identification)
    - Whale Predictor (3-pass validation)
    - Momentum Scanners (Wolf, Lion, Ants, Hummingbird)
    
    Produces validated intelligence for Queen decisions.
    """
    
    def __init__(self):
        self.bot_profiler = RealBotProfiler()
        self.whale_predictor = RealWhalePredictor()
        self.momentum_scanner = RealMomentumScanner()
        
        self.intelligence_generated = 0
        self.validated_signals = 0
        
        logger.info("=" * 60)
        logger.info("🧠 REAL INTELLIGENCE ENGINE INITIALIZED")
        logger.info(f"   Bot Profiler: {'✅ ACTIVE' if _BOT_PROFILER_AVAILABLE else '⚠️ FALLBACK'}")
        logger.info(f"   Whale Predictor: {'✅ ACTIVE' if _WHALE_PREDICTOR_AVAILABLE else '⚠️ FALLBACK'}")
        logger.info(f"   Momentum Scanners: {'✅ ACTIVE' if _MOMENTUM_SCANNERS_AVAILABLE else '⚠️ FALLBACK'}")
        logger.info("=" * 60)
    
    def gather_all_intelligence(self, prices: Dict, orderbook_data: Dict = None) -> Dict[str, Any]:
        """
        Gather intelligence from all sources and return combined data.
        This replaces the random simulation in the live runner.
        """
        
        # 1. Bot Detection & Firm Profiling
        bot_profiles = self.bot_profiler.scan_market_for_bots(prices, orderbook_data)
        
        # 2. Momentum Scanning (all 4 animal scanners)
        momentum_data = self.momentum_scanner.scan_all_momentum()
        
        # 3. Whale Predictions (3-pass validated)
        # Create synthetic whale alerts from momentum data for prediction
        whale_alerts = []
        for scanner_type, opps in momentum_data.items():
            for opp in opps:
                if opp.confidence > 0.5:
                    whale_alerts.append({
                        'symbol': opp.symbol,
                        'side': opp.side.upper(),
                        'size_usd': opp.volume * 0.1  # Estimate
                    })
        
        whale_predictions = self.whale_predictor.bulk_predict(whale_alerts)
        
        # 4. Generate validated intelligence for each symbol
        validated_intelligence = []
        symbols_seen = set()
        
        # Collect all symbols from all sources
        for bp in bot_profiles:
            symbols_seen.add(bp.symbol)
        for wp in whale_predictions:
            symbols_seen.add(wp.symbol)
        for scanner_type, opps in momentum_data.items():
            for opp in opps:
                symbols_seen.add(opp.symbol)
        
        for symbol in symbols_seen:
            intel = self._generate_validated_intelligence(
                symbol, 
                [bp for bp in bot_profiles if bp.symbol == symbol],
                [wp for wp in whale_predictions if wp.symbol == symbol],
                {k: [o for o in v if o.symbol == symbol] for k, v in momentum_data.items()}
            )
            if intel:
                validated_intelligence.append(intel)
                self.intelligence_generated += 1
                if intel.composite_score > 0.618:  # Golden ratio threshold
                    self.validated_signals += 1
        
        return {
            'bot_profiles': [self._profile_to_dict(bp) for bp in bot_profiles],
            'whale_predictions': [self._prediction_to_dict(wp) for wp in whale_predictions],
            'momentum_opportunities': {k: [self._opp_to_dict(o) for o in v] for k, v in momentum_data.items()},
            'validated_intelligence': [self._intel_to_dict(vi) for vi in validated_intelligence],
            'stats': {
                'bots_detected': len(bot_profiles),
                'whales_predicted': len(whale_predictions),
                'validated_predictions': self.whale_predictor.validated_predictions,
                'momentum_opportunities': sum(len(v) for v in momentum_data.values()),
                'intelligence_generated': self.intelligence_generated,
                'validated_signals': self.validated_signals,
                'timestamp': datetime.utcnow().isoformat() + "Z"
            }
        }
    
    def _generate_validated_intelligence(
        self,
        symbol: str,
        bots: List[BotProfile],
        whales: List[WhalePrediction],
        momentum: Dict[str, List[MomentumOpportunity]]
    ) -> Optional[ValidatedIntelligence]:
        """Generate combined validated intelligence for a symbol"""
        
        # Calculate composite score from all sources
        scores = []
        actions = []
        reasoning_parts = []
        
        # Bot intelligence
        for bot in bots:
            scores.append(bot.confidence)
            reasoning_parts.append(f"{bot.firm_animal} {bot.firm} detected ({bot.bot_type})")
        
        # Whale predictions (weighted higher if validated)
        for whale in whales:
            weight = 1.5 if whale.validated else 1.0
            scores.append(whale.confidence * weight)
            actions.append(whale.action)
            if whale.validated:
                reasoning_parts.append(f"✓ Validated whale signal: {whale.action} (p1={whale.validators.get('p1', 0):.2f})")
        
        # Momentum opportunities
        for scanner_type, opps in momentum.items():
            for opp in opps:
                scores.append(opp.confidence)
                actions.append(opp.side)
                reasoning_parts.append(f"{scanner_type.upper()}: {opp.side} {opp.net_pct:.2f}%")
        
        if not scores:
            return None
        
        # Composite score (weighted average with golden ratio)
        composite = sum(scores) / len(scores) * PHI / 2
        composite = min(1.0, composite)
        
        # Determine recommended action
        buy_count = sum(1 for a in actions if a.lower() in ['buy', 'lean_buy'])
        sell_count = sum(1 for a in actions if a.lower() in ['sell', 'lean_sell'])
        
        if buy_count > sell_count * 1.5:
            recommended = 'BUY'
        elif sell_count > buy_count * 1.5:
            recommended = 'SELL'
        else:
            recommended = 'HOLD'
        
        return ValidatedIntelligence(
            symbol=symbol,
            bot_profiles=bots,
            whale_predictions=whales,
            momentum_opportunities=[o for opps in momentum.values() for o in opps],
            composite_score=composite,
            recommended_action=recommended,
            reasoning=" | ".join(reasoning_parts[:3]) if reasoning_parts else "Insufficient data"
        )
    
    def _profile_to_dict(self, bp: BotProfile) -> Dict:
        return {
            'symbol': bp.symbol,
            'bot_type': bp.bot_type,
            'firm': bp.firm,
            'firm_animal': bp.firm_animal,
            'confidence': bp.confidence,
            'hft_frequency': bp.hft_frequency,
            'layering_score': bp.layering_score,
            'timing_ms': bp.timing_ms,
            'estimated_capital': bp.estimated_capital,
            'known_strategies': bp.known_strategies,
            'timestamp': bp.timestamp
        }
    
    def _prediction_to_dict(self, wp: WhalePrediction) -> Dict:
        return {
            'symbol': wp.symbol,
            'action': wp.action,
            'confidence': wp.confidence,
            'time_horizon_minutes': wp.time_horizon_minutes,
            'validators': wp.validators,
            'coherence': wp.coherence,
            'lambda_stability': wp.lambda_stability,
            'validated': wp.validated,
            'timestamp': wp.timestamp
        }
    
    def _opp_to_dict(self, mo: MomentumOpportunity) -> Dict:
        return {
            'symbol': mo.symbol,
            'scanner_type': mo.scanner_type,
            'side': mo.side,
            'move_pct': mo.move_pct,
            'net_pct': mo.net_pct,
            'volume': mo.volume,
            'reason': mo.reason,
            'confidence': mo.confidence,
            'timestamp': mo.timestamp
        }
    
    def _intel_to_dict(self, vi: ValidatedIntelligence) -> Dict:
        return {
            'symbol': vi.symbol,
            'composite_score': vi.composite_score,
            'recommended_action': vi.recommended_action,
            'reasoning': vi.reasoning,
            'bot_count': len(vi.bot_profiles),
            'whale_count': len(vi.whale_predictions),
            'momentum_count': len(vi.momentum_opportunities),
            'timestamp': vi.timestamp
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL ENGINE INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_global_engine: Optional[RealIntelligenceEngine] = None

def get_intelligence_engine() -> RealIntelligenceEngine:
    """Get or create the global intelligence engine"""
    global _global_engine
    if _global_engine is None:
        _global_engine = RealIntelligenceEngine()
    return _global_engine
