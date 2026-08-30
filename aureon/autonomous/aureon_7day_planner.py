#!/usr/bin/env python3
"""
📅🔮 AUREON 7-DAY PLANNER - PREDICT & VALIDATE 🔮📅
═══════════════════════════════════════════════════════════════════════════════

Plans 7 days in advance using trained probability matrix data.
After each conversion, validates predictions and adapts the model.

FEATURES:
├─ 7-day forecast using hourly/daily edge patterns
├─ Per-symbol optimal windows based on historical patterns
├─ Post-conversion validation (was prediction correct?)
├─ Adaptive learning: updates weights based on accuracy
└─ Timeline confidence scoring

Gary Leckey & GitHub Copilot | January 2026
"Plan the Future, Learn from the Past"
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════════
# 📊 DATA STRUCTURES
# ════════════════════════════════════════════════════════════════════════════════

@dataclass
class PredictedWindow:
    """A predicted optimal trading window."""
    start_time: datetime
    end_time: datetime
    symbol: str
    expected_edge: float  # Expected % edge
    confidence: float  # 0-1 confidence score
    reasons: List[str] = field(default_factory=list)

    # Post-validation fields (filled after conversion)
    actual_result: Optional[float] = None  # Actual % change
    was_correct: Optional[bool] = None
    validated_at: Optional[datetime] = None


@dataclass
class DayPlan:
    """Plan for a single day."""
    date: datetime
    windows: List[PredictedWindow] = field(default_factory=list)
    daily_edge: float = 0.0
    day_of_week: int = 0
    is_optimal_day: bool = False
    is_avoid_day: bool = False


@dataclass
class WeekPlan:
    """Full 7-day plan."""
    created_at: datetime
    days: List[DayPlan] = field(default_factory=list)
    best_windows: List[PredictedWindow] = field(default_factory=list)
    total_predicted_edge: float = 0.0


@dataclass
class ValidationResult:
    """Result of validating a prediction."""
    window: PredictedWindow
    predicted_edge: float
    actual_edge: float
    error_pct: float  # How far off were we
    direction_correct: bool  # Did we get direction right?
    timing_score: float  # How good was the timing (0-1)


# ════════════════════════════════════════════════════════════════════════════════
# 🧠 7-DAY PLANNER CLASS
# ════════════════════════════════════════════════════════════════════════════════

class Aureon7DayPlanner:
    """
    Plans 7 days of optimal trading windows and validates predictions.
    """

    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        # Load trained probability matrix
        self.matrix = self._load_matrix()

        # Load validation history
        self.validation_history = self._load_validation_history()

        # Adaptive weights (learn from validation)
        self.adaptive_weights = self._load_adaptive_weights()

        # Current 7-day plan
        self.current_plan: Optional[WeekPlan] = None

        # Pending validations (conversions waiting to be validated)
        self.pending_validations: List[Dict] = []

        print("📅🔮 Aureon 7-Day Planner initialized")
        if self.matrix:
            print(f"   📊 Matrix loaded: {self.matrix.get('total_symbols', 0)} symbols, {self.matrix.get('total_candles', 0)} candles")

    def _load_matrix(self) -> Dict:
        """Load trained probability matrix."""
        matrix_path = os.path.join(self.base_path, 'trained_probability_matrix.json')
        try:
            if os.path.exists(matrix_path):
                with open(matrix_path, 'r') as f:
                    matrix = json.load(f)
                if not isinstance(matrix, dict):
                    raise ValueError('trained probability matrix must be a JSON object')
                matrix['_provenance'] = {
                    'truth_status': 'real_derived',
                    'source_id': os.path.abspath(matrix_path),
                    'source_timestamp': datetime.fromtimestamp(
                        os.path.getmtime(matrix_path), timezone.utc
                    ).isoformat(),
                    'generated_values': False,
                }
                return matrix
        except Exception as e:
            logger.error(f"Failed to load matrix: {e}")
        return {}

    def _load_validation_history(self) -> List[Dict]:
        """Load validation history."""
        history_path = os.path.join(self.base_path, '7day_validation_history.json')
        try:
            if os.path.exists(history_path):
                with open(history_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load validation history: {e}")
        return []

    def _save_validation_history(self):
        """Save validation history."""
        history_path = os.path.join(self.base_path, '7day_validation_history.json')
        try:
            # Keep last 1000 validations
            history_to_save = self.validation_history[-1000:]
            with open(history_path, 'w') as f:
                json.dump(history_to_save, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save validation history: {e}")

    def _load_adaptive_weights(self) -> Dict:
        """Load adaptive weights that adjust based on validation accuracy."""
        weights_path = os.path.join(self.base_path, '7day_adaptive_weights.json')
        try:
            if os.path.exists(weights_path):
                with open(weights_path, 'r') as f:
                    weights = json.load(f)
                if not isinstance(weights, dict):
                    raise ValueError('adaptive weights must be a JSON object')
                if int(weights.get('validation_count') or 0) <= 0:
                    weights['accuracy_7d'] = None
                    weights['accuracy_30d'] = None
                return weights
        except Exception as e:
            logger.error(f"Failed to load adaptive weights: {e}")

        # Default weights
        return {
            'hourly_weight': 1.0,
            'daily_weight': 1.0,
            'symbol_weight': 1.0,
            'correlation_weight': 1.0,
            'momentum_weight': 1.0,
            'validation_count': 0,
            'accuracy_7d': None,
            'accuracy_30d': None,
            'last_updated': None
        }

    def _save_adaptive_weights(self):
        """Save adaptive weights."""
        weights_path = os.path.join(self.base_path, '7day_adaptive_weights.json')
        try:
            self.adaptive_weights['last_updated'] = datetime.now().isoformat()
            with open(weights_path, 'w') as f:
                json.dump(self.adaptive_weights, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save adaptive weights: {e}")

    # ════════════════════════════════════════════════════════════════════════════
    # 📅 7-DAY PLANNING
    # ════════════════════════════════════════════════════════════════════════════

    def plan_7_days(self, symbols: List[str] = None) -> WeekPlan:
        """
        Create a 7-day plan of optimal trading windows.

        Args:
            symbols: List of symbols to plan for (None = use all from matrix)

        Returns:
            WeekPlan with predicted optimal windows for each day
        """
        now = datetime.now()

        # Default to top symbols if none specified
        if not symbols:
            symbols = self._get_top_symbols(limit=20)

        plan = WeekPlan(
            created_at=now,
            days=[],
            best_windows=[],
            total_predicted_edge=0.0
        )

        # Plan each of the next 7 days
        for day_offset in range(7):
            target_date = now + timedelta(days=day_offset)
            day_plan = self._plan_single_day(target_date, symbols)
            plan.days.append(day_plan)
            plan.total_predicted_edge += day_plan.daily_edge

        # Find best windows across the week
        all_windows = []
        for day in plan.days:
            all_windows.extend(day.windows)

        # Sort by expected edge * confidence
        all_windows.sort(key=lambda w: w.expected_edge * w.confidence, reverse=True)
        plan.best_windows = all_windows[:10]  # Top 10 windows

        self.current_plan = plan
        self._save_current_plan()

        return plan

    def _plan_single_day(self, target_date: datetime, symbols: List[str]) -> DayPlan:
        """Plan a single day."""
        dow = target_date.weekday()

        # Get daily edge from matrix
        daily_edge_data = self.matrix.get('daily_edge', {}).get(str(dow), {})
        daily_edge = daily_edge_data.get('edge', 0)

        # Check if optimal/avoid day
        optimal_days = self.matrix.get('optimal_conditions', {}).get('days', [])
        avoid_days = self.matrix.get('avoid_conditions', {}).get('days', [])

        day_plan = DayPlan(
            date=target_date,
            windows=[],
            daily_edge=daily_edge * self.adaptive_weights['daily_weight'],
            day_of_week=dow,
            is_optimal_day=dow in optimal_days,
            is_avoid_day=dow in avoid_days
        )

        # Find optimal windows for each symbol
        for symbol in symbols:
            windows = self._find_optimal_windows(target_date, symbol)
            day_plan.windows.extend(windows)

        # Sort windows by expected edge
        day_plan.windows.sort(key=lambda w: w.expected_edge * w.confidence, reverse=True)

        return day_plan

    def _find_optimal_windows(self, target_date: datetime, symbol: str) -> List[PredictedWindow]:
        """Find optimal trading windows for a symbol on a given day."""
        windows = []

        # Get symbol patterns
        symbol_patterns = self.matrix.get('symbol_patterns', {}).get(symbol, {})
        symbol_hourly = symbol_patterns.get('hourly_edge', {})

        # Get global hourly patterns
        global_hourly = self.matrix.get('hourly_edge', {})

        # Check each hour
        for hour in range(24):
            # Global edge for this hour
            global_edge_data = global_hourly.get(str(hour), {})
            global_edge = global_edge_data.get('edge', 0) * self.adaptive_weights['hourly_weight']
            global_conf = global_edge_data.get('confidence', 0)

            # Symbol-specific edge
            symbol_edge_data = symbol_hourly.get(str(hour), {})
            symbol_edge = symbol_edge_data.get('edge', 0) * self.adaptive_weights['symbol_weight']
            symbol_conf = symbol_edge_data.get('confidence', 0)

            # Combined edge (weighted average)
            if symbol_conf > 0:
                combined_edge = (global_edge * 0.6 + symbol_edge * 0.4)
                combined_conf = (global_conf * 0.6 + symbol_conf * 0.4)
            else:
                combined_edge = global_edge
                combined_conf = global_conf

            # Only create window if edge is significant
            if combined_edge > 1.0 and combined_conf > 0.3:  # >1% edge with 30%+ confidence
                reasons = []
                if global_edge > 2.0:
                    reasons.append(f"global_optimal_hour({hour})")
                if symbol_edge > 2.0:
                    reasons.append(f"symbol_optimal_hour({hour})")

                window = PredictedWindow(
                    start_time=target_date.replace(hour=hour, minute=0, second=0, microsecond=0),
                    end_time=target_date.replace(hour=hour, minute=59, second=59, microsecond=0),
                    symbol=symbol,
                    expected_edge=combined_edge,
                    confidence=combined_conf,
                    reasons=reasons
                )
                windows.append(window)

        return windows

    def _get_top_symbols(self, limit: int = 20) -> List[str]:
        """Get top symbols by sample count from matrix."""
        symbol_patterns = self.matrix.get('symbol_patterns', {})

        # Sort by sample count
        sorted_symbols = sorted(
            symbol_patterns.items(),
            key=lambda x: x[1].get('total_samples', 0),
            reverse=True
        )

        return [s[0] for s in sorted_symbols[:limit]]

    def _save_current_plan(self):
        """Save current plan to disk."""
        plan_path = os.path.join(self.base_path, '7day_current_plan.json')
        try:
            if self.current_plan:
                plan_dict = {
                    'created_at': self.current_plan.created_at.isoformat(),
                    'total_predicted_edge': self.current_plan.total_predicted_edge,
                    'days': [],
                    'best_windows': []
                }

                for day in self.current_plan.days:
                    day_dict = {
                        'date': day.date.isoformat(),
                        'daily_edge': day.daily_edge,
                        'day_of_week': day.day_of_week,
                        'is_optimal_day': day.is_optimal_day,
                        'is_avoid_day': day.is_avoid_day,
                        'windows': [self._window_to_dict(w) for w in day.windows[:5]]  # Top 5 per day
                    }
                    plan_dict['days'].append(day_dict)

                for window in self.current_plan.best_windows:
                    plan_dict['best_windows'].append(self._window_to_dict(window))

                with open(plan_path, 'w') as f:
                    json.dump(plan_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save plan: {e}")

    def _window_to_dict(self, window: PredictedWindow) -> Dict:
        """Convert window to dict for JSON."""
        return {
            'start_time': window.start_time.isoformat(),
            'end_time': window.end_time.isoformat(),
            'symbol': window.symbol,
            'expected_edge': window.expected_edge,
            'confidence': window.confidence,
            'reasons': window.reasons,
            'actual_result': window.actual_result,
            'was_correct': window.was_correct,
            'validated_at': window.validated_at.isoformat() if window.validated_at else None
        }

    # ════════════════════════════════════════════════════════════════════════════
    # ✅ POST-CONVERSION VALIDATION
    # ════════════════════════════════════════════════════════════════════════════

    def record_conversion(self, symbol: str, entry_price: float, entry_time: datetime = None,
                          predicted_edge: float = None) -> str:
        """
        Record a conversion for later validation.

        Args:
            symbol: The symbol that was converted
            entry_price: Price at conversion
            entry_time: When conversion happened (default: now)
            predicted_edge: What edge we predicted (if known)

        Returns:
            validation_id for tracking
        """
        if entry_time is None:
            entry_time = datetime.now()

        validation_id = f"{symbol}_{entry_time.strftime('%Y%m%d_%H%M%S')}"

        # Find matching prediction from current plan
        matching_prediction = self._find_matching_prediction(symbol, entry_time)

        self.pending_validations.append({
            'validation_id': validation_id,
            'symbol': symbol,
            'entry_price': entry_price,
            'entry_time': entry_time.isoformat(),
            'predicted_edge': predicted_edge or (matching_prediction.expected_edge if matching_prediction else 0),
            'predicted_confidence': matching_prediction.confidence if matching_prediction else 0.5,
            'hour': entry_time.hour,
            'day_of_week': entry_time.weekday(),
            'status': 'pending'
        })

        self._save_pending_validations()

        logger.info(f"📝 Recorded conversion {validation_id} for validation")
        return validation_id

    def _find_matching_prediction(self, symbol: str, entry_time: datetime) -> Optional[PredictedWindow]:
        """Find a prediction that matches this conversion."""
        if not self.current_plan:
            return None

        for day in self.current_plan.days:
            for window in day.windows:
                if window.symbol == symbol:
                    if window.start_time <= entry_time <= window.end_time:
                        return window

        return None

    def validate_conversion(self, validation_id: str = None, symbol: str = None,
                           exit_price: float = None, exit_time: datetime = None) -> Optional[ValidationResult]:
        """
        Validate a conversion after it completes.

        Args:
            validation_id: ID from record_conversion (or find by symbol)
            symbol: Symbol to validate (if no validation_id)
            exit_price: Price at exit
            exit_time: When exit happened (default: now)

        Returns:
            ValidationResult with accuracy metrics
        """
        if exit_time is None:
            exit_time = datetime.now()

        # Find pending validation
        pending = None
        for v in self.pending_validations:
            if validation_id and v['validation_id'] == validation_id:
                pending = v
                break
            elif symbol and v['symbol'] == symbol and v['status'] == 'pending':
                pending = v
                break

        if not pending:
            logger.warning(f"No pending validation found for {validation_id or symbol}")
            return None

        # Calculate actual result
        entry_price = pending['entry_price']
        actual_edge = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        predicted_edge = pending['predicted_edge']

        # Determine if prediction was correct
        direction_correct = (predicted_edge >= 0 and actual_edge >= 0) or (predicted_edge < 0 and actual_edge < 0)
        error_pct = abs(actual_edge - predicted_edge)

        # Timing score: how close were we to predicted edge
        if abs(predicted_edge) > 0:
            timing_score = max(0, 1 - (error_pct / abs(predicted_edge)))
        else:
            timing_score = 0.5

        # Create validation result
        result = ValidationResult(
            window=PredictedWindow(
                start_time=datetime.fromisoformat(pending['entry_time']),
                end_time=exit_time,
                symbol=pending['symbol'],
                expected_edge=predicted_edge,
                confidence=pending['predicted_confidence'],
                actual_result=actual_edge,
                was_correct=direction_correct,
                validated_at=exit_time
            ),
            predicted_edge=predicted_edge,
            actual_edge=actual_edge,
            error_pct=error_pct,
            direction_correct=direction_correct,
            timing_score=timing_score
        )

        # Update pending validation
        pending['status'] = 'validated'
        pending['exit_price'] = exit_price
        pending['exit_time'] = exit_time.isoformat()
        pending['actual_edge'] = actual_edge
        pending['direction_correct'] = direction_correct
        pending['timing_score'] = timing_score

        # Add to validation history
        self.validation_history.append(pending)
        self._save_validation_history()
        self._save_pending_validations()

        # 🧠 ADAPTIVE LEARNING: Update weights based on result
        self._adapt_from_validation(result)

        logger.info(f"✅ Validated {pending['symbol']}: predicted={predicted_edge:.2f}%, actual={actual_edge:.2f}%, correct={direction_correct}")

        return result

    def _adapt_from_validation(self, result: ValidationResult):
        """
        Adapt weights based on validation result.
        This is the key learning loop!
        """
        # Learning rate
        lr = 0.05

        # If prediction was correct, increase relevant weights slightly
        if result.direction_correct:
            # Boost hourly weight if hourly pattern was strong
            hour = result.window.start_time.hour
            hourly_edge = self.matrix.get('hourly_edge', {}).get(str(hour), {}).get('edge', 0)
            if abs(hourly_edge) > 2.0:
                self.adaptive_weights['hourly_weight'] = min(1.5, self.adaptive_weights['hourly_weight'] + lr)

            # Boost symbol weight if symbol pattern matched
            if result.timing_score > 0.7:
                self.adaptive_weights['symbol_weight'] = min(1.5, self.adaptive_weights['symbol_weight'] + lr)
        else:
            # Decrease weights slightly if wrong
            self.adaptive_weights['hourly_weight'] = max(0.5, self.adaptive_weights['hourly_weight'] - lr)
            self.adaptive_weights['symbol_weight'] = max(0.5, self.adaptive_weights['symbol_weight'] - lr)

        # Update accuracy metrics
        self.adaptive_weights['validation_count'] = self.adaptive_weights.get('validation_count', 0) + 1

        # Calculate rolling accuracy
        recent_validations = self.validation_history[-100:]  # Last 100
        if recent_validations:
            correct_count = sum(1 for v in recent_validations if v.get('direction_correct', False))
            self.adaptive_weights['accuracy_7d'] = correct_count / len(recent_validations)

        self._save_adaptive_weights()

        logger.info(f"🧠 Adapted weights: hourly={self.adaptive_weights['hourly_weight']:.2f}, "
                   f"symbol={self.adaptive_weights['symbol_weight']:.2f}, "
                   f"accuracy={self.adaptive_weights['accuracy_7d']:.1%}")

    def _save_pending_validations(self):
        """Save pending validations."""
        pending_path = os.path.join(self.base_path, '7day_pending_validations.json')
        try:
            with open(pending_path, 'w') as f:
                json.dump(self.pending_validations, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save pending validations: {e}")

    # ════════════════════════════════════════════════════════════════════════════
    # 🔮 QUERY METHODS
    # ════════════════════════════════════════════════════════════════════════════

    def get_current_recommendation(self, symbol: str = None) -> Dict:
        """
        Get trading recommendation for right now.

        Returns:
            Dict with recommendation, confidence, and reasons
        """
        now = datetime.now()
        hour = now.hour
        dow = now.weekday()

        if not self.matrix:
            return {
                'timestamp': now.isoformat(),
                'action': 'NO_DATA',
                'confidence': None,
                'symbol': symbol,
                'model_accuracy': None,
                'truth_status': 'no_data',
                'source_id': None,
                'source_timestamp': None,
                'generated_values': False,
                'reason': 'MISSING_TRAINED_PROBABILITY_MATRIX',
                'reasons': ['MISSING_TRAINED_PROBABILITY_MATRIX'],
            }

        # Get global patterns
        hourly_record = self.matrix.get('hourly_edge', {}).get(str(hour), {})
        daily_record = self.matrix.get('daily_edge', {}).get(str(dow), {})
        missing = []
        if not isinstance(hourly_record, dict) or hourly_record.get('edge') is None:
            missing.append(f'hourly_edge:{hour}')
        if not isinstance(daily_record, dict) or daily_record.get('edge') is None:
            missing.append(f'daily_edge:{dow}')

        symbol_record = None
        if symbol:
            symbol_record = (
                self.matrix.get('symbol_patterns', {})
                .get(symbol, {})
                .get('hourly_edge', {})
                .get(str(hour), {})
            )
            if not isinstance(symbol_record, dict) or symbol_record.get('edge') is None:
                missing.append(f'symbol_hourly_edge:{symbol}:{hour}')

        if missing:
            provenance = self.matrix.get('_provenance', {})
            return {
                'timestamp': now.isoformat(),
                'action': 'NO_DATA',
                'confidence': None,
                'symbol': symbol,
                'model_accuracy': (
                    self.adaptive_weights.get('accuracy_7d')
                    if self.adaptive_weights.get('validation_count', 0) > 0
                    else None
                ),
                'truth_status': 'no_data',
                'source_id': provenance.get('source_id'),
                'source_timestamp': provenance.get('source_timestamp'),
                'generated_values': False,
                'reason': 'MISSING_MATRIX_OBSERVATIONS',
                'missing_observations': missing,
                'reasons': [f'MISSING_MATRIX_OBSERVATIONS: {item}' for item in missing],
            }

        hourly_edge = float(hourly_record['edge'])
        daily_edge = float(daily_record['edge'])

        # Apply adaptive weights
        weighted_hourly = hourly_edge * self.adaptive_weights['hourly_weight']
        weighted_daily = daily_edge * self.adaptive_weights['daily_weight']

        # Get symbol-specific if provided
        symbol_edge = 0.0
        if symbol:
            symbol_edge = float(symbol_record['edge']) * self.adaptive_weights['symbol_weight']

        # Combined score
        total_edge = weighted_hourly + weighted_daily * 0.5 + symbol_edge * 0.5

        # Recommendation
        if total_edge > 3.0:
            action = 'STRONG_BUY'
            confidence = min(0.95, 0.7 + total_edge / 20)
        elif total_edge > 1.5:
            action = 'BUY'
            confidence = min(0.85, 0.6 + total_edge / 20)
        elif total_edge > 0:
            action = 'HOLD'
            confidence = 0.5
        elif total_edge > -1.5:
            action = 'HOLD'
            confidence = 0.5
        elif total_edge > -3.0:
            action = 'AVOID'
            confidence = min(0.85, 0.6 + abs(total_edge) / 20)
        else:
            action = 'STRONG_AVOID'
            confidence = min(0.95, 0.7 + abs(total_edge) / 20)

        provenance = self.matrix.get('_provenance', {})
        return {
            'timestamp': now.isoformat(),
            'action': action,
            'confidence': confidence,
            'hour': hour,
            'day_of_week': dow,
            'hourly_edge': weighted_hourly,
            'daily_edge': weighted_daily,
            'symbol_edge': symbol_edge,
            'total_edge': total_edge,
            'symbol': symbol,
            'model_accuracy': (
                self.adaptive_weights.get('accuracy_7d')
                if self.adaptive_weights.get('validation_count', 0) > 0
                else None
            ),
            'truth_status': 'real_derived',
            'source_id': provenance.get('source_id'),
            'source_timestamp': provenance.get('source_timestamp'),
            'generated_values': False,
            'reasons': self._build_reasons(hour, dow, hourly_edge, daily_edge, symbol_edge)
        }

    def _build_reasons(self, hour: int, dow: int, hourly_edge: float, daily_edge: float, symbol_edge: float) -> List[str]:
        """Build list of reasons for recommendation."""
        reasons = []

        if hourly_edge > 2.0:
            reasons.append(f"optimal_hour({hour}): +{hourly_edge:.1f}% edge")
        elif hourly_edge < -2.0:
            reasons.append(f"avoid_hour({hour}): {hourly_edge:.1f}% edge")

        if daily_edge > 1.0:
            reasons.append(f"optimal_day: +{daily_edge:.1f}% edge")
        elif daily_edge < -1.0:
            reasons.append(f"weak_day: {daily_edge:.1f}% edge")

        if symbol_edge > 2.0:
            reasons.append(f"symbol_bullish: +{symbol_edge:.1f}%")
        elif symbol_edge < -2.0:
            reasons.append(f"symbol_bearish: {symbol_edge:.1f}%")

        return reasons

    def get_next_optimal_window(self, symbol: str = None, within_hours: int = 24) -> Optional[Dict]:
        """
        Get the next optimal trading window.

        Args:
            symbol: Specific symbol (or None for any)
            within_hours: Look within this many hours

        Returns:
            Dict with window details or None
        """
        if not self.current_plan:
            self.plan_7_days()

        now = datetime.now()
        cutoff = now + timedelta(hours=within_hours)

        for day in self.current_plan.days:
            for window in day.windows:
                if window.start_time > now and window.start_time < cutoff:
                    if symbol is None or window.symbol == symbol:
                        return {
                            'symbol': window.symbol,
                            'start_time': window.start_time.isoformat(),
                            'end_time': window.end_time.isoformat(),
                            'expected_edge': window.expected_edge,
                            'confidence': window.confidence,
                            'reasons': window.reasons,
                            'hours_until': (window.start_time - now).total_seconds() / 3600
                        }

        return None

    def get_week_summary(self) -> Dict:
        """Get summary of the 7-day plan."""
        if not self.current_plan:
            self.plan_7_days()

        summary = {
            'created_at': self.current_plan.created_at.isoformat(),
            'total_predicted_edge': self.current_plan.total_predicted_edge,
            'adaptive_weights': self.adaptive_weights,
            'days': []
        }

        for day in self.current_plan.days:
            day_summary = {
                'date': day.date.strftime('%Y-%m-%d (%A)'),
                'daily_edge': day.daily_edge,
                'is_optimal': day.is_optimal_day,
                'is_avoid': day.is_avoid_day,
                'top_windows': len(day.windows),
                'best_window': None
            }

            if day.windows:
                best = day.windows[0]
                day_summary['best_window'] = {
                    'symbol': best.symbol,
                    'hour': best.start_time.hour,
                    'edge': best.expected_edge,
                    'confidence': best.confidence
                }

            summary['days'].append(day_summary)

        # Top 5 windows overall
        summary['top_5_windows'] = []
        for window in self.current_plan.best_windows[:5]:
            summary['top_5_windows'].append({
                'symbol': window.symbol,
                'datetime': window.start_time.strftime('%Y-%m-%d %H:00'),
                'edge': window.expected_edge,
                'confidence': window.confidence
            })

        return summary

    def get_validation_stats(self) -> Dict:
        """Get validation statistics."""
        if not self.validation_history:
            return {
                'total_validations': 0,
                'accuracy': None,
                'avg_error_pct': None,
                'avg_timing_score': None,
                'truth_status': 'no_data',
                'generated_values': False,
                'reason': 'NO_VALIDATION_RECEIPTS',
            }

        direction_receipts = [
            value
            for value in self.validation_history
            if isinstance(value.get('direction_correct'), bool)
        ]
        total = len(direction_receipts)
        correct = sum(1 for value in direction_receipts if value['direction_correct'])

        errors = [
            float(value['actual_edge']) - float(value['predicted_edge'])
            for value in self.validation_history
            if value.get('actual_edge') is not None and value.get('predicted_edge') is not None
        ]
        avg_error = sum(abs(error) for error in errors) / len(errors) if errors else None

        timing_scores = [
            float(value['timing_score'])
            for value in self.validation_history
            if value.get('timing_score') is not None
        ]
        avg_timing = sum(timing_scores) / len(timing_scores) if timing_scores else None

        return {
            'total_validations': total,
            'accuracy': correct / total if total > 0 else None,
            'correct_predictions': correct,
            'avg_error_pct': avg_error,
            'avg_timing_score': avg_timing,
            'adaptive_weights': self.adaptive_weights,
            'truth_status': 'real_derived' if total > 0 else 'no_data',
            'generated_values': False,
            'reason': None if total > 0 else 'NO_COMPLETE_VALIDATION_RECEIPTS',
        }


# ════════════════════════════════════════════════════════════════════════════════
# 🔌 LABYRINTH INTEGRATION
# ════════════════════════════════════════════════════════════════════════════════

def get_planner_score(symbol: str) -> Tuple[Optional[float], str]:
    """
    Get score from 7-day planner for use in labyrinth.

    Returns:
        (score 0-1, reason string)
    """
    try:
        planner = Aureon7DayPlanner()
        rec = planner.get_current_recommendation(symbol)
        if rec.get('truth_status') == 'no_data':
            return None, str(rec.get('reason') or 'planner_no_data')

        # Convert action to score
        action_scores = {
            'STRONG_BUY': 0.90,
            'BUY': 0.75,
            'HOLD': 0.50,
            'AVOID': 0.30,
            'STRONG_AVOID': 0.15
        }

        score = action_scores.get(rec['action'])
        if score is None:
            return None, f'unknown_planner_action:{rec.get("action")}'
        confidence = rec['confidence']

        # Weight only by measured validation accuracy. With no validation
        # receipt, preserve the real-derived planner score without inventing a
        # neutral 50% accuracy.
        accuracy = rec.get('model_accuracy')
        weighted_score = (
            score * (0.5 + float(accuracy) * 0.5)
            if accuracy is not None
            else score
        )

        reason = f"7day_{rec['action'].lower()}({rec['total_edge']:.1f}%)"

        return weighted_score, reason
    except Exception as e:
        logger.error(f"7-day planner error: {e}")
        return None, 'planner_error'


def record_labyrinth_conversion(symbol: str, entry_price: float) -> str:
    """Record a conversion from labyrinth for validation."""
    try:
        planner = Aureon7DayPlanner()
        return planner.record_conversion(symbol, entry_price)
    except Exception as e:
        logger.error(f"Failed to record conversion: {e}")
        return ""


def validate_labyrinth_conversion(symbol: str, exit_price: float) -> Optional[Dict]:
    """Validate a completed conversion from labyrinth."""
    try:
        planner = Aureon7DayPlanner()
        result = planner.validate_conversion(symbol=symbol, exit_price=exit_price)
        if result:
            return {
                'predicted_edge': result.predicted_edge,
                'actual_edge': result.actual_edge,
                'direction_correct': result.direction_correct,
                'timing_score': result.timing_score
            }
    except Exception as e:
        logger.error(f"Failed to validate conversion: {e}")
    return None


# ════════════════════════════════════════════════════════════════════════════════
# 🚀 MAIN
# ════════════════════════════════════════════════════════════════════════════════

def main():
    """Run 7-day planner demo."""
    print("\n" + "=" * 70)
    print("📅🔮 AUREON 7-DAY PLANNER - PREDICT & VALIDATE 🔮📅")
    print("=" * 70 + "\n")

    planner = Aureon7DayPlanner()

    # Create 7-day plan
    print("📅 Creating 7-day plan...")
    plan = planner.plan_7_days(['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK'])

    # Show summary
    summary = planner.get_week_summary()

    print(f"\n📊 WEEK SUMMARY (Total predicted edge: {summary['total_predicted_edge']:.2f}%)")
    print("-" * 70)

    for day in summary['days']:
        status = "🟢 OPTIMAL" if day['is_optimal'] else ("🔴 AVOID" if day['is_avoid'] else "🟡")
        best = day['best_window']
        if best:
            print(f"  {day['date']}: {day['daily_edge']:+.2f}% {status}")
            print(f"    └─ Best: {best['symbol']} @ {best['hour']:02d}:00 ({best['edge']:+.2f}% edge, {best['confidence']:.0%} conf)")
        else:
            print(f"  {day['date']}: {day['daily_edge']:+.2f}% {status}")

    print("\n🏆 TOP 5 WINDOWS THIS WEEK:")
    print("-" * 70)
    for i, window in enumerate(summary['top_5_windows'], 1):
        print(f"  {i}. {window['symbol']} @ {window['datetime']}: {window['edge']:+.2f}% edge ({window['confidence']:.0%} conf)")

    # Current recommendation
    print("\n🔮 CURRENT RECOMMENDATION:")
    print("-" * 70)
    rec = planner.get_current_recommendation('BTC')
    print(f"  Action: {rec['action']} (confidence: {rec['confidence']:.0%})")
    print(f"  Hour {rec['hour']} edge: {rec['hourly_edge']:+.2f}%")
    print(f"  Day edge: {rec['daily_edge']:+.2f}%")
    print(f"  Total edge: {rec['total_edge']:+.2f}%")
    if rec['reasons']:
        print(f"  Reasons: {', '.join(rec['reasons'])}")

    # Next optimal window
    print("\n⏰ NEXT OPTIMAL WINDOW (24h):")
    print("-" * 70)
    next_window = planner.get_next_optimal_window(within_hours=24)
    if next_window:
        print(f"  Symbol: {next_window['symbol']}")
        print(f"  Time: {next_window['start_time']}")
        print(f"  Expected edge: {next_window['expected_edge']:+.2f}%")
        print(f"  Hours until: {next_window['hours_until']:.1f}h")
    else:
        print("  No optimal windows found in next 24h")

    # Validation stats
    print("\n📊 VALIDATION STATS:")
    print("-" * 70)
    stats = planner.get_validation_stats()
    print(f"  Total validations: {stats['total_validations']}")
    print(f"  Accuracy: {stats['accuracy']:.1%}")
    print(f"  Avg error: {stats['avg_error_pct']:.2f}%")
    print(f"  Avg timing score: {stats['avg_timing_score']:.2%}")

    # Adaptive weights
    print("\n🧠 ADAPTIVE WEIGHTS:")
    print("-" * 70)
    weights = stats['adaptive_weights']
    print(f"  Hourly weight: {weights['hourly_weight']:.2f}")
    print(f"  Daily weight: {weights['daily_weight']:.2f}")
    print(f"  Symbol weight: {weights['symbol_weight']:.2f}")
    print(f"  Model accuracy (7d): {weights['accuracy_7d']:.1%}")

    print("\n" + "=" * 70)
    print("✅ 7-DAY PLAN COMPLETE!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
