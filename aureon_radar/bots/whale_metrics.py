"""
Whale Detection System Metrics

Comprehensive metrics and alerting for:
- Shape detections by subtype
- Shape outcome win rates  
- On-chain large transfer events
- Stargate correlations
- Whale pattern classifications
- Prediction accuracy

Uses the lightweight metrics.py infrastructure with Prometheus integration.
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

try:
    from aureon.utils.console_utf8 import ensure_utf8_stdout  # noqa: E402
except ImportError:  # aureon.utils.console_utf8 not present in this environment
    def ensure_utf8_stdout():
        import sys as _sys
        if _sys.platform == "win32":
            for _s in (_sys.stdout, _sys.stderr):
                try:
                    _s.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass

ensure_utf8_stdout()

import logging
from typing import Any, Dict, Optional
from aureon.core import metrics as _metrics_impl
from aureon.core.metrics import MetricCounter, MetricGauge

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 📊 WHALE SYSTEM METRICS
# ═══════════════════════════════════════════════════════════════

# Shape Detection Metrics
whale_shape_detected_total = MetricCounter(
    'whale_shape_detected_total',
    'Total whale shapes detected by subtype',
    labelnames=('subtype', 'symbol', 'exchange')
)

whale_shape_outcome_total = MetricCounter(
    'whale_shape_outcome_total',
    'Shape outcomes recorded (win/loss)',
    labelnames=('subtype', 'outcome')  # outcome = 'win' or 'loss'
)

whale_shape_win_rate = MetricGauge(
    'whale_shape_win_rate',
    'Win rate for each shape subtype (0-1)',
    labelnames=('subtype',)
)

whale_shape_profit_factor = MetricGauge(
    'whale_shape_profit_factor',
    'Profit factor for each shape subtype',
    labelnames=('subtype',)
)

# Pattern Classification Metrics
whale_pattern_classified_total = MetricCounter(
    'whale_pattern_classified_total',
    'Whale patterns classified by type',
    labelnames=('pattern_type', 'symbol')
)

whale_pattern_confidence = MetricGauge(
    'whale_pattern_confidence',
    'Current confidence for active whale patterns',
    labelnames=('symbol', 'pattern_type')
)

# Behavior Prediction Metrics
whale_prediction_emitted_total = MetricCounter(
    'whale_prediction_emitted_total',
    'Total whale behavior predictions emitted',
    labelnames=('action', 'symbol')  # action = buy/sell/wait/lean_buy/lean_sell
)

whale_prediction_confidence = MetricGauge(
    'whale_prediction_confidence',
    'Current prediction confidence',
    labelnames=('symbol', 'action')
)

whale_prediction_coherence = MetricGauge(
    'whale_prediction_coherence',
    'Batten Matrix coherence score (0-1)',
    labelnames=('symbol',)
)

whale_prediction_lambda_stability = MetricGauge(
    'whale_prediction_lambda_stability',
    'Lambda stability score (0-1)',
    labelnames=('symbol',)
)

# Orderbook Analysis Metrics
whale_wall_detected_total = MetricCounter(
    'whale_wall_detected_total',
    'Large orderbook walls detected',
    labelnames=('side', 'symbol', 'exchange')  # side = bid/ask
)

whale_layering_score = MetricGauge(
    'whale_layering_score',
    'Current layering score (0-1 = manipulation indicator)',
    labelnames=('symbol', 'exchange')
)

whale_depth_imbalance = MetricGauge(
    'whale_depth_imbalance',
    'Bid/ask depth imbalance (-1 to 1, positive = bid heavy)',
    labelnames=('symbol', 'exchange')
)

# On-chain Metrics
whale_onchain_transfer_total = MetricCounter(
    'whale_onchain_transfer_total',
    'Large on-chain transfers detected',
    labelnames=('direction', 'exchange_name', 'token_symbol')  # direction = deposit/withdrawal/whale/internal
)

whale_onchain_transfer_usd = MetricGauge(
    'whale_onchain_transfer_usd',
    'Last on-chain transfer USD value',
    labelnames=('direction', 'exchange_name', 'token_symbol')
)

whale_onchain_provider_requests = MetricCounter(
    'whale_onchain_provider_requests_total',
    'On-chain provider API requests',
    labelnames=('provider',)  # provider = etherscan/covalent/alchemy
)

whale_onchain_provider_errors = MetricCounter(
    'whale_onchain_provider_errors_total',
    'On-chain provider API errors',
    labelnames=('provider',)
)

# Stargate Correlation Metrics
whale_stargate_correlation_total = MetricCounter(
    'whale_stargate_correlation_total',
    'Stargate correlations emitted',
    labelnames=('symbol', 'source', 'node_info')  # source = stargate/quantum_mirror/stargate_computed
)

whale_stargate_coherence = MetricGauge(
    'whale_stargate_coherence',
    'Current stargate coherence for symbol (0-1)',
    labelnames=('symbol', 'node_id')
)

whale_quantum_mirror_coherence = MetricGauge(
    'whale_quantum_mirror_coherence',
    'Quantum mirror coherence score (0-1)',
    labelnames=('mirror_id',)
)

# Integration Metrics
whale_integration_cache_size = MetricGauge(
    'whale_integration_cache_size',
    'Number of symbols in whale prediction cache',
    labelnames=()
)

whale_integration_cache_hit = MetricCounter(
    'whale_integration_cache_hit_total',
    'Cache hits for whale predictions',
    labelnames=('symbol',)
)

whale_integration_cache_miss = MetricCounter(
    'whale_integration_cache_miss_total',
    'Cache misses for whale predictions',
    labelnames=('symbol',)
)

# Shape Registry Metrics
whale_shape_registry_patterns = MetricGauge(
    'whale_shape_registry_patterns_total',
    'Total patterns stored in shape registry',
    labelnames=()
)

whale_shape_registry_outcome_latency = MetricGauge(
    'whale_shape_registry_outcome_latency_seconds',
    'Time between shape detection and outcome recording',
    labelnames=('subtype',)
)


# ═══════════════════════════════════════════════════════════════
# 🚨 ALERT THRESHOLDS & HELPERS
# ═══════════════════════════════════════════════════════════════

ALERT_THRESHOLDS = {
    # Shape detection alerts
    'shape_manipulation_confidence': 0.8,  # High manipulation pattern
    'shape_grid_detection_rate': 5,        # Grid bots detected per minute
    
    # On-chain alerts
    'onchain_mega_whale_usd': 1_000_000,   # $1M+ transfer
    'onchain_exchange_flow_ratio': 3.0,    # Deposits 3x withdrawals (or vice versa)
    
    # Stargate alerts
    'stargate_coherence_spike': 0.9,       # Very high planetary alignment
    'stargate_coherence_collapse': 0.2,    # Planetary misalignment
    
    # Pattern alerts
    'whale_layering_critical': 0.85,       # Very high layering = manipulation
    'whale_wall_mega': 500_000,            # $500K+ wall
    
    # Prediction alerts
    'prediction_confidence_low': 0.3,      # Low confidence = avoid trade
    'prediction_coherence_low': 0.4,       # Validators disagree
}


def check_alert_conditions(metric_name: str, value: float, labels: Optional[Dict[str, str]] = None) -> Optional[str]:
    """
    Check if a metric value triggers an alert.
    
    Returns:
        Alert message string if triggered, None otherwise
    """
    labels = labels or {}
    
    # Shape manipulation alert
    if metric_name == 'whale_prediction_confidence':
        subtype = labels.get('subtype', '')
        if 'manipulation' in subtype and value > ALERT_THRESHOLDS['shape_manipulation_confidence']:
            return f"🚨 HIGH MANIPULATION PATTERN: {subtype} confidence={value:.2f} symbol={labels.get('symbol', 'unknown')}"
    
    # On-chain mega whale alert
    if metric_name == 'whale_onchain_transfer_usd':
        if value >= ALERT_THRESHOLDS['onchain_mega_whale_usd']:
            direction = labels.get('direction', 'unknown')
            exchange = labels.get('exchange_name', 'unknown')
            token = labels.get('token_symbol', 'unknown')
            return f"🐋 MEGA WHALE DETECTED: ${value:,.0f} {token} {direction} {exchange}"
    
    # Stargate coherence spike
    if metric_name == 'whale_stargate_coherence':
        if value >= ALERT_THRESHOLDS['stargate_coherence_spike']:
            symbol = labels.get('symbol', 'unknown')
            node = labels.get('node_id', 'unknown')
            return f"🌌 STARGATE ALIGNMENT SPIKE: {symbol} coherence={value:.3f} node={node}"
        elif value <= ALERT_THRESHOLDS['stargate_coherence_collapse']:
            symbol = labels.get('symbol', 'unknown')
            node = labels.get('node_id', 'unknown')
            return f"⚠️  STARGATE COHERENCE COLLAPSE: {symbol} coherence={value:.3f} node={node}"
    
    # Layering manipulation alert
    if metric_name == 'whale_layering_score':
        if value >= ALERT_THRESHOLDS['whale_layering_critical']:
            symbol = labels.get('symbol', 'unknown')
            exchange = labels.get('exchange', 'unknown')
            return f"🚩 CRITICAL LAYERING DETECTED: {symbol} on {exchange} score={value:.2f}"
    
    # Prediction quality alerts
    if metric_name == 'whale_prediction_coherence':
        if value <= ALERT_THRESHOLDS['prediction_coherence_low']:
            symbol = labels.get('symbol', 'unknown')
            return f"⚠️  LOW PREDICTION COHERENCE: {symbol} coherence={value:.2f} (validators disagree)"
    
    return None


def log_alert(alert_msg: str):
    """Log an alert message"""
    logger.warning(alert_msg)
    # TODO: Hook to external alerting system (PagerDuty, Slack, etc.)


def _matching_total(metric, **filters) -> float:
    """Sum all internal counter values whose labelset matches ``filters``.

    MetricCounter/MetricGauge.get() is exact-labelset only — a partial-label
    lookup such as get(subtype='grid') silently returns 0 after an increment
    recorded under ('grid', 'BTC/USD', 'kraken'). This helper matches on the
    subset instead so summaries aggregate correctly.
    """
    total = 0.0
    for (name, items), value in _metrics_impl._internal_counters.items():
        if name != metric.name:
            continue
        labels = dict(items)
        if all(labels.get(k) == str(v) for k, v in filters.items()):
            total += value
    return total


# ═══════════════════════════════════════════════════════════════
# 📈 METRICS REPORTING
# ═══════════════════════════════════════════════════════════════

def get_whale_system_summary() -> Dict[str, Any]:
    """
    Get summary of whale system health and performance.

    Returns:
        Dict with key metrics aggregated
    """
    return {
        'shapes_detected': {
            'grid': _matching_total(whale_shape_detected_total, subtype='grid'),
            'oscillator': _matching_total(whale_shape_detected_total, subtype='oscillator'),
            'spiral': _matching_total(whale_shape_detected_total, subtype='spiral'),
            'accumulation': _matching_total(whale_shape_detected_total, subtype='accumulation'),
            'distribution': _matching_total(whale_shape_detected_total, subtype='distribution'),
            'manipulation': _matching_total(whale_shape_detected_total, subtype='manipulation'),
        },
        'onchain_transfers': {
            'deposits': _matching_total(whale_onchain_transfer_total, direction='deposit'),
            'withdrawals': _matching_total(whale_onchain_transfer_total, direction='withdrawal'),
            'whale': _matching_total(whale_onchain_transfer_total, direction='whale'),
        },
        'predictions': {
            'buy': _matching_total(whale_prediction_emitted_total, action='buy'),
            'sell': _matching_total(whale_prediction_emitted_total, action='sell'),
            'wait': _matching_total(whale_prediction_emitted_total, action='wait'),
        },
        'stargate_correlations': _matching_total(whale_stargate_correlation_total),
        'cache_size': _matching_total(whale_integration_cache_size),
    }


if __name__ == '__main__':
    # Test metrics
    logging.basicConfig(level=logging.INFO)
    
    # Simulate some detections
    whale_shape_detected_total.inc(subtype='grid', symbol='BTC/USD', exchange='kraken')
    whale_shape_detected_total.inc(subtype='accumulation', symbol='ETH/USD', exchange='binance')
    
    whale_onchain_transfer_total.inc(direction='deposit', exchange_name='Binance', token_symbol='ETH')
    whale_onchain_transfer_usd.set(250000.0, direction='deposit', exchange_name='Binance', token_symbol='ETH')
    
    whale_stargate_coherence.set(0.92, symbol='BTC/USD', node_id='giza')
    
    # Check alerts
    alert = check_alert_conditions('whale_stargate_coherence', 0.92, {'symbol': 'BTC/USD', 'node_id': 'giza'})
    if alert:
        log_alert(alert)
    
    # Get summary
    summary = get_whale_system_summary()
    print("\n📊 Whale System Summary:")
    print(f"  Shapes detected: {summary['shapes_detected']}")
    print(f"  On-chain transfers: {summary['onchain_transfers']}")
    print(f"  Predictions: {summary['predictions']}")
    print(f"  Stargate correlations: {summary['stargate_correlations']}")
    print(f"  Cache size: {summary['cache_size']}")
