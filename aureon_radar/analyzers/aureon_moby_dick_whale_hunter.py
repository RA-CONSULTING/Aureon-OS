#!/usr/bin/env python3
"""
🐋⚔️ AUREON MOBY DICK WHALE HUNTER ⚔️🐋
==========================================

CAPTAIN AHAB'S LEGENDARY WHALE HUNTING STRATEGIES
Applied to Market Whales and Algorithmic Traders

From Herman Melville's Moby-Dick (1851):

"He piled upon the whale's white hump the sum of all the general rage
and hate felt by his whole race from Adam down; and then, as if his
chest had been a mortar, he burst his hot heart's shell upon it."

KEY STRATEGIES FROM MOBY DICK:

1. **THE GAM SYSTEM** (Chapter encounters with 9 ships)
   - Information gathering from other "ships" (exchanges)
   - Each encounter reveals whale behavior patterns
   - Track which exchanges have seen the whale (Citadel, Jane Street, etc.)

2. **FEDALLAH'S PROPHECIES** (Predictive patterns)
   - "Neither hearse nor coffin can be thine" → Whale movement prediction
   - Pattern recognition BEFORE the whale surfaces
   - Three prophecies = three validation passes before 4th execution

3. **THE DOUBLOON** (Reward system / profit targeting)
   - Ahab nails a gold doubloon to the mast
   - First to spot Moby Dick wins the prize
   - Our system: First to detect accumulation pattern wins the trade

4. **THE THREE HARPOONS** (Triple validation)
   - Queequeg, Tashtego, Daggoo = Three independent validators
   - All three must hit before the kill shot
   - Maps to: Batten Matrix 3-pass validation system

5. **THE WHITE WHALE TRACKING** (Seasonal/pattern-based prediction)
   - Moby Dick follows feeding grounds in predictable patterns
   - Chart his course based on previous sightings
   - Predict NEXT appearance before it happens

6. **THE PEQUOD'S CREW DIVERSITY** (Multi-source intelligence)
   - Global crew from all nations = multi-exchange scanning
   - Each brings unique whale knowledge
   - Integration of diverse intelligence streams

7. **STUBB'S HUMOR** (Don't let fear control you)
   - Stay calm during whale encounters
   - Confidence despite danger
   - Don't panic-sell when whales move

8. **STARBUCK'S REASON** (Risk management)
   - "I came here to hunt whales, not my commander's vengeance"
   - Know when to walk away
   - Profit vs. obsession balance

9. **PIP'S MADNESS** (What happens when you're left alone)
   - Don't get separated from the fleet
   - Stay connected to market intelligence
   - Isolation = death

10. **THE FINAL CHASE** (Three-day pursuit pattern)
    - Day 1: First sighting, boat destroyed
    - Day 2: Second encounter, ivory leg lost
    - Day 3: Final confrontation
    - Our system: Three accumulation signals → 4th confirmation → Execute

Gary Leckey | January 2026 | "Call me Ishmael"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import math
import sys
import time
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque, defaultdict

# UTF-8 fix — aureon.utils.console_utf8 is absent from the upstream package;
# fall back to the repo shim, then to an inline no-op reconfigure.
try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402
except ImportError:  # pragma: no cover - environment dependent
    try:
        from _console_utf8_shim import ensure_utf8_stdout  # noqa: E402
    except ImportError:
        def ensure_utf8_stdout(*_a, **_k):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

logger = logging.getLogger(__name__)

PHI = (1 + math.sqrt(5)) / 2  # 1.618

# 👑 QUEEN'S SACRED 1.88% LAW - THE HUNT SERVES THE QUEEN
QUEEN_MIN_COP = 1.0188              # Sacred constant: 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88         # Percentage form - no whale hunt below this
QUEEN_WHALE_PROFIT_FREQ = 188.0     # Hz - Sacred frequency for profitable whale hunts


@dataclass
class GamEncounter:
    """Encounter with another 'ship' (exchange) about whale sightings."""
    exchange: str
    timestamp: float
    symbol: str
    whale_class: str  # "ACCUMULATION_BOT", "MM_SPOOF", "HFT_ALGO"
    frequency: float  # Hz
    activities: int
    confidence: float  # 0-1
    

@dataclass
class WhalePrediction:
    """Prediction of WHERE and WHEN the whale will surface next."""
    symbol: str
    predicted_time: float  # Unix timestamp
    predicted_side: str  # 'buy' or 'sell'
    confidence: float  # 0-1
    pattern_type: str  # "seasonal_feeding", "accumulation_cycle", "spoofing_pattern"
    validation_count: int  # How many "harpoons" have hit (0-3)
    ready_for_execution: bool  # 4th pass ready?
    reasoning: str
    

@dataclass
class WhaleTrackingState:
    """Persistent state of whale tracking across exchanges."""
    symbol: str
    last_sightings: List[GamEncounter] = field(default_factory=list)
    pattern_history: List[Dict] = field(default_factory=list)
    predicted_next_appearance: Optional[WhalePrediction] = None
    harpoon_hits: int = 0  # 0-3 validations
    

class MobyDickWhaleHunter:
    """
    🐋⚔️ CAPTAIN AHAB'S WHALE HUNTING SYSTEM ⚔️🐋
    
    "I'll chase him round Good Hope, and round the Horn, and round the Norway Maelstrom,
    and round perdition's flames before I give him up."
    
    PREDICTIVE WHALE TRACKING:
    - Learns from past whale movements (Gam encounters)
    - Predicts NEXT appearance BEFORE it happens
    - Uses 3-harpoon validation (Batten Matrix)
    - Executes on 4th confirmation (like Queen Hive)
    """
    
    def __init__(self):
        self.tracking_state: Dict[str, WhaleTrackingState] = {}
        self.gam_log: List[GamEncounter] = []  # All encounters logged
        self.doubloon_mounted = True  # Reward system active
        
        # Prophecy constants (Fedallah's predictions)
        self.prophecy_window = 3600  # Predict 1 hour ahead
        self.min_gams_for_prediction = 3  # Need 3 sightings to predict
        self.harpoon_confidence_threshold = 0.618  # φ⁻¹
        
        logger.info("🐋 Moby Dick Whale Hunter initialized - 'Call me Ishmael'")
        
    def log_gam_encounter(self, encounter: GamEncounter) -> None:
        """
        Log an encounter with another 'ship' about whale activity.
        
        Like Ahab meeting the Jeroboam, Rachel, Delight - each encounter
        adds to his knowledge of where Moby Dick was last seen.
        """
        self.gam_log.append(encounter)
        
        # Update tracking state
        if encounter.symbol not in self.tracking_state:
            self.tracking_state[encounter.symbol] = WhaleTrackingState(symbol=encounter.symbol)
            
        state = self.tracking_state[encounter.symbol]
        state.last_sightings.append(encounter)
        
        # Keep only recent sightings (last 24 hours)
        cutoff = time.time() - 86400
        state.last_sightings = [s for s in state.last_sightings if s.timestamp > cutoff]
        
        logger.info(f"🐋 GAM: {encounter.exchange} reported {encounter.whale_class} on {encounter.symbol} "
                   f"({encounter.frequency:.2f}Hz, {encounter.activities} activities)")
        
    def predict_next_whale_appearance(self, symbol: str) -> Optional[WhalePrediction]:
        """
        🔮 FEDALLAH'S PROPHECY 🔮
        
        Predict WHERE and WHEN the whale will surface next.
        
        "Ere the Pequod's weedy hull rolls side by side with the barnacled
        craft of the whale, shall ye see the White Whale ere ye die."
        
        Uses pattern analysis of past sightings to forecast future movements.
        """
        if symbol not in self.tracking_state:
            return None
            
        state = self.tracking_state[symbol]
        
        if len(state.last_sightings) < self.min_gams_for_prediction:
            return None  # Not enough intelligence yet
            
        # Analyze sighting pattern
        recent = state.last_sightings[-5:]  # Last 5 sightings
        
        # Pattern 1: ACCUMULATION CYCLE (repeated buy signals)
        accumulation_count = sum(1 for s in recent if "ACCUMULATION" in s.whale_class)
        
        # Pattern 2: MM_SPOOF FREQUENCY (market maker spoofing rhythm)
        spoof_freqs = [s.frequency for s in recent if "MM_SPOOF" in s.whale_class]
        
        # Pattern 3: HFT_ALGO TIMING (high-frequency trader patterns)
        hft_intervals = []
        hft_sightings = [s for s in recent if "HFT_ALGO" in s.whale_class]
        for i in range(1, len(hft_sightings)):
            interval = hft_sightings[i].timestamp - hft_sightings[i-1].timestamp
            hft_intervals.append(interval)
            
        # Make prediction based on dominant pattern
        prediction = None
        
        if accumulation_count >= 3:
            # ACCUMULATION pattern detected
            avg_interval = sum(recent[i].timestamp - recent[i-1].timestamp 
                             for i in range(1, len(recent))) / (len(recent) - 1)
            predicted_time = recent[-1].timestamp + avg_interval
            
            prediction = WhalePrediction(
                symbol=symbol,
                predicted_time=predicted_time,
                predicted_side='buy',  # Accumulation = buying
                confidence=0.75,
                pattern_type="accumulation_cycle",
                validation_count=1,  # First harpoon hit
                ready_for_execution=False,
                reasoning=f"Detected {accumulation_count} accumulation signals in last 5 gams"
            )
            
        elif spoof_freqs and len(spoof_freqs) >= 2:
            # MM_SPOOF frequency pattern
            avg_freq = sum(spoof_freqs) / len(spoof_freqs)
            period = 1.0 / avg_freq if avg_freq > 0 else 60
            predicted_time = recent[-1].timestamp + period
            
            prediction = WhalePrediction(
                symbol=symbol,
                predicted_time=predicted_time,
                predicted_side='sell',  # Spoofing often precedes selling
                confidence=0.70,
                pattern_type="spoofing_pattern",
                validation_count=1,
                ready_for_execution=False,
                reasoning=f"MM spoofing detected at {avg_freq:.2f}Hz - predicting next spoof"
            )
            
        elif hft_intervals:
            # HFT_ALGO timing pattern
            avg_interval = sum(hft_intervals) / len(hft_intervals)
            predicted_time = recent[-1].timestamp + avg_interval
            
            prediction = WhalePrediction(
                symbol=symbol,
                predicted_time=predicted_time,
                predicted_side='buy',  # HFT algos often accumulate
                confidence=0.68,
                pattern_type="hft_rhythm",
                validation_count=1,
                ready_for_execution=False,
                reasoning=f"HFT rhythm detected: {avg_interval:.1f}s intervals"
            )
            
        if prediction:
            state.predicted_next_appearance = prediction
            logger.info(f"🔮 PROPHECY: {symbol} whale predicted to surface at "
                       f"{datetime.fromtimestamp(prediction.predicted_time)} "
                       f"(confidence: {prediction.confidence:.0%})")
            
        return prediction
        
    def validate_harpoon(self, symbol: str, observed_data: Dict) -> bool:
        """
        🎯 HARPOON VALIDATION 🎯
        
        Queequeg throws his harpoon, Tashtego throws his, Daggoo throws his.
        Three independent validators must HIT before Ahab gives the kill order.
        
        Returns True if this validation increases the harpoon hit count.
        """
        if symbol not in self.tracking_state:
            return False
            
        state = self.tracking_state[symbol]
        pred = state.predicted_next_appearance
        
        if not pred:
            return False
            
        # Check if observed data matches prediction
        time_diff = abs(observed_data.get('timestamp', 0) - pred.predicted_time)
        side_match = observed_data.get('side') == pred.predicted_side
        
        # Time window: within 5 minutes (300 seconds)
        if time_diff < 300 and side_match:
            state.harpoon_hits += 1
            pred.validation_count = state.harpoon_hits
            
            logger.info(f"🎯 HARPOON HIT #{state.harpoon_hits} on {symbol}! "
                       f"Time diff: {time_diff:.0f}s")
            
            # Check if ready for 4th pass (execution)
            if state.harpoon_hits >= 3 and pred.confidence > self.harpoon_confidence_threshold:
                pred.ready_for_execution = True
                logger.warning(f"⚔️ THREE HARPOONS HIT! {symbol} ready for FINAL CHASE (4th pass)")
                
            return True
            
        return False
        
    def get_execution_ready_predictions(self) -> List[WhalePrediction]:
        """
        ⚔️ THE FINAL CHASE ⚔️
        
        "To the last I grapple with thee; from hell's heart I stab at thee;
        for hate's sake I spit my last breath at thee."
        
        Returns all predictions that have 3 harpoon hits and are ready for
        the 4th pass (execution).
        """
        ready = []
        for state in self.tracking_state.values():
            pred = state.predicted_next_appearance
            if pred and pred.ready_for_execution:
                ready.append(pred)
                
        return ready
        
    def claim_doubloon(self, symbol: str, profit_usd: float) -> Dict:
        """
        💰 CLAIM THE DOUBLOON 💰

        "Whosoever of ye raises me a white-headed whale with a wrinkled brow
        and a crooked jaw... he shall have this gold ounce, my boys!"

        Award the doubloon to the system that successfully predicted and profited.
        """
        return {
            'symbol': symbol,
            'profit_usd': profit_usd,
            'timestamp': time.time(),
            'captain': 'Ahab',
            'message': f"💰 DOUBLOON CLAIMED! ${profit_usd:.2f} profit on {symbol}"
        }

    # ── Persistence (real cross-run tracking state) ─────────────────────

    @staticmethod
    def _state_path() -> Path:
        # aureon_radar/state/moby_dick_whale_tracking.json
        return Path(__file__).resolve().parent.parent / "state" / "moby_dick_whale_tracking.json"

    def save_state(self) -> None:
        """Persist sightings + predictions so tracking survives restarts."""
        path = self._state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "ts": time.time(),
                "tracking_state": {
                    sym: {
                        "last_sightings": [asdict(s) for s in st.last_sightings],
                        "harpoon_hits": st.harpoon_hits,
                        "predicted_next_appearance": (
                            asdict(st.predicted_next_appearance)
                            if st.predicted_next_appearance else None
                        ),
                    }
                    for sym, st in self.tracking_state.items()
                },
                "gam_log_tail": [asdict(g) for g in self.gam_log[-200:]],
            }
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Moby Dick state save failed: {e}")

    def load_state(self) -> bool:
        """Load persisted tracking state. Returns True when state was restored."""
        path = self._state_path()
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for sym, st_data in (data.get("tracking_state") or {}).items():
                st = WhaleTrackingState(symbol=sym)
                st.last_sightings = [
                    GamEncounter(**s) for s in st_data.get("last_sightings", [])
                ]
                st.harpoon_hits = int(st_data.get("harpoon_hits", 0))
                pred = st_data.get("predicted_next_appearance")
                st.predicted_next_appearance = WhalePrediction(**pred) if pred else None
                self.tracking_state[sym] = st
            self.gam_log = [GamEncounter(**g) for g in data.get("gam_log_tail", [])]
            return True
        except Exception as e:
            logger.debug(f"Moby Dick state load failed: {e}")
            return False

    # ── Real-data analysis entry point ──────────────────────────────────

    def ingest_sighting(self, exchange: str, symbol: str, whale_class: str,
                        frequency: float, activities: int, confidence: float,
                        timestamp: Optional[float] = None) -> None:
        """Ingest ONE real whale sighting (from scanner state / signal logs)."""
        self.log_gam_encounter(GamEncounter(
            exchange=exchange,
            timestamp=timestamp if timestamp is not None else time.time(),
            symbol=symbol,
            whale_class=whale_class,
            frequency=float(frequency),
            activities=int(activities),
            confidence=float(confidence),
        ))

    def run_analysis(self, max_predictions: int = 10) -> Dict[str, Any]:
        """One analysis pass over REAL sightings only.

        Sightings come from:
          - persisted tracking state (state/moby_dick_whale_tracking.json)
          - bot_shape_scanner_state.json (Bot Shape Scanner output, if present)
          - crypto_signals.jsonl scanner output (if present)

        No sightings -> fail-closed: ok=False, predictions=None, error set.
        Predictions are only ever derived from logged real sightings.
        """
        loaded = self.load_state()
        ingested = 0

        radar_root = Path(__file__).resolve().parent.parent

        # 1) Bot Shape Scanner state (another organ writes this)
        scanner_state_path = radar_root / "bot_shape_scanner_state.json"
        if scanner_state_path.exists():
            try:
                state = json.loads(scanner_state_path.read_text(encoding="utf-8"))
                for symbol, symbol_data in state.items():
                    if not isinstance(symbol_data, dict):
                        continue
                    advanced = symbol_data.get("advanced_classification", {})
                    bot_class = advanced.get("class", "UNKNOWN")
                    frequency = float(advanced.get("frequency", 0.0) or 0.0)
                    if bot_class == "UNKNOWN":
                        continue
                    self.ingest_sighting(
                        "binance", symbol, bot_class, frequency,
                        int(symbol_data.get("activity_count", 0) or 0),
                        float(symbol_data.get("confidence", 0.0) or 0.0),
                    )
                    ingested += 1
            except Exception as e:
                logger.debug(f"bot scanner state ingest failed: {e}")

        # 2) crypto_signals.jsonl — real correlation signals from the radar
        signals_path = radar_root / "crypto_signals.jsonl"
        if signals_path.exists():
            try:
                lines = signals_path.read_text(encoding="utf-8", errors="replace").splitlines()
                cutoff = time.time() - 86400  # last 24h only
                for line in lines[-500:]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    try:
                        ts = datetime.fromisoformat(
                            str(rec.get("timestamp", "")).replace("Z", "+00:00")
                        ).timestamp()
                    except ValueError:
                        continue
                    if ts < cutoff:
                        continue
                    direction = str(rec.get("direction", "")).upper()
                    whale_class = "ACCUMULATION_SIGNAL" if direction == "LONG" else "DISTRIBUTION_SIGNAL"
                    self.ingest_sighting(
                        str(rec.get("source", "radar")),
                        str(rec.get("symbol", "UNKNOWN")),
                        whale_class,
                        0.0,
                        1,
                        float(rec.get("confidence", 0.0) or 0.0),
                        timestamp=ts,
                    )
                    ingested += 1
            except Exception as e:
                logger.debug(f"crypto_signals ingest failed: {e}")

        if not self.tracking_state and not loaded and ingested == 0:
            return {
                "ok": False,
                "ts": time.time(),
                "sightings_ingested": 0,
                "predictions": None,
                "execution_ready": None,
                "error": "no_real_sightings_available",
            }

        predictions = []
        for symbol in list(self.tracking_state):
            pred = self.predict_next_whale_appearance(symbol)
            if pred:
                predictions.append(asdict(pred))

        predictions.sort(key=lambda p: p["confidence"], reverse=True)
        predictions = predictions[:max_predictions]
        ready = self.get_execution_ready_predictions()

        self.save_state()

        return {
            "ok": True,
            "ts": time.time(),
            "sightings_ingested": ingested,
            "tracked_symbols": len(self.tracking_state),
            "predictions": predictions,
            "execution_ready": len(ready),
            "error": None,
        }


# Singleton instance
_moby_dick_hunter = None

def get_moby_dick_hunter() -> MobyDickWhaleHunter:
    """Get the singleton Moby Dick whale hunter instance."""
    global _moby_dick_hunter
    if _moby_dick_hunter is None:
        _moby_dick_hunter = MobyDickWhaleHunter()
    return _moby_dick_hunter


if __name__ == '__main__':
    ensure_utf8_stdout()
    print("🐋⚔️ MOBY DICK WHALE HUNTER - Real-Data Analysis ⚔️🐋")
    print("=" * 60)

    hunter = get_moby_dick_hunter()
    result = hunter.run_analysis()

    if not result.get("ok"):
        print(f"⛔ FAIL-CLOSED: {result.get('error')} — no fabricated sightings substituted.")
        sys.exit(2)

    print(f"📊 Sightings ingested this pass: {result['sightings_ingested']}")
    print(f"📊 Tracked symbols: {result['tracked_symbols']}")
    print(f"📊 Execution-ready predictions: {result['execution_ready']}")

    if result["predictions"]:
        print("\n🔮 PROPHECIES (from real sightings):")
        for pred in result["predictions"]:
            print(f"\n  {pred['symbol']}: {pred['reasoning']}")
            print(f"    Predicted time: {datetime.fromtimestamp(pred['predicted_time'])}")
            print(f"    Confidence: {pred['confidence']:.0%} | Harpoons: {pred['validation_count']}/3")
    else:
        print("\n🔮 No prophecies yet — not enough real sightings to predict.")

    print("\n⚔️ AWAITING THE FINAL CHASE...")
