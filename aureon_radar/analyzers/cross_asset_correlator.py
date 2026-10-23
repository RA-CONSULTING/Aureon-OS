"""
Cross-Asset Correlation Engine
==============================
Tracks relationships between crypto, forex, indices, and commodities.

Core insight: markets don't move in isolation.
  - When BTC pumps → altcoins follow (lag: 60-240s)
  - When NAS100 runs → tech stocks follow (lag: 30-60s)
  - When Gold spikes → risk-off: indices dip, crypto softens
  - When oil dumps → USDCAD drops → commodity currencies follow
  - When EURUSD moves → GBPUSD, AUDUSD follow (DXY cascade)

This engine:
  1. Groups every scanned symbol into a category (crypto/forex/index/commodity/stock)
  2. Detects the current market regime (RISK_ON / RISK_OFF / NEUTRAL)
  3. Finds PRE-SIGNAL opportunities: leader has moved but correlated follower hasn't yet
  4. Returns MarketOpportunity-compatible dicts for injection into the scan pipeline
"""

import time
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
#  Asset → category mapping  (all uppercase, no slashes/dashes)
# ─────────────────────────────────────────────────────────────────────────────
ASSET_CATEGORIES: Dict[str, str] = {
    # ── Crypto ───────────────────────────────────────────────────────────────
    'BTC': 'crypto',    'BTCUSD': 'crypto',    'BTCUSDT': 'crypto',   'XBTUSD': 'crypto',
    'ETH': 'crypto',    'ETHUSD': 'crypto',    'ETHUSDT': 'crypto',
    'SOL': 'crypto',    'SOLUSD': 'crypto',    'SOLUSDT': 'crypto',
    'AVAX': 'crypto',   'AVAXUSD': 'crypto',   'AVAXUSDT': 'crypto',
    'LINK': 'crypto',   'LINKUSD': 'crypto',   'LINKUSDT': 'crypto',
    'DOT': 'crypto',    'DOTUSD': 'crypto',    'DOTUSDT': 'crypto',
    'MATIC': 'crypto',  'MATICUSD': 'crypto',  'MATICUSDT': 'crypto',
    'XLM': 'crypto',    'XLMUSD': 'crypto',    'XLMUSDT': 'crypto',
    'ADA': 'crypto',    'ADAUSD': 'crypto',    'ADAUSDT': 'crypto',
    'DOGE': 'crypto',   'DOGEUSD': 'crypto',   'DOGEUSDT': 'crypto',
    'XRP': 'crypto',    'XRPUSD': 'crypto',    'XRPUSDT': 'crypto',
    'LTC': 'crypto',    'LTCUSD': 'crypto',    'LTCUSDT': 'crypto',
    'UNI': 'crypto',    'UNIUSD': 'crypto',    'UNIUSDT': 'crypto',
    'AAVE': 'crypto',   'AAVEUSD': 'crypto',   'AAVEUSDT': 'crypto',
    'ATOM': 'crypto',   'ATOMUSD': 'crypto',
    'NEAR': 'crypto',   'NEARUSD': 'crypto',
    'APT': 'crypto',    'APTUSD': 'crypto',
    'ARB': 'crypto',    'ARBUSD': 'crypto',
    'OP': 'crypto',     'OPUSD': 'crypto',
    # ── Forex ────────────────────────────────────────────────────────────────
    'EURUSD': 'forex',  'GBPUSD': 'forex',  'USDJPY': 'forex',
    'AUDUSD': 'forex',  'USDCAD': 'forex',  'NZDUSD': 'forex',
    'USDCHF': 'forex',  'EURGBP': 'forex',  'EURJPY': 'forex',
    'GBPJPY': 'forex',  'AUDJPY': 'forex',  'EURCHF': 'forex',
    # ── Indices ──────────────────────────────────────────────────────────────
    'US500': 'index',   'US30': 'index',    'NAS100': 'index',
    'UK100': 'index',   'GER40': 'index',   'FRA40': 'index',
    'SPX': 'index',     'NDX': 'index',     'DJI': 'index',
    'VIX': 'index',
    # ── Commodities ──────────────────────────────────────────────────────────
    'GOLD': 'commodity',    'SILVER': 'commodity',
    'OILCRUDE': 'commodity', 'OIL_CRUDE': 'commodity',
    'NATURALGAS': 'commodity', 'NATURAL_GAS': 'commodity',
    'XAUUSD': 'commodity',  'XAGUSD': 'commodity',
    'WTI': 'commodity',     'BRENT': 'commodity',
    'COPPER': 'commodity',
    # ── Stocks ───────────────────────────────────────────────────────────────
    'AAPL': 'stock',  'MSFT': 'stock',  'GOOGL': 'stock',
    'AMZN': 'stock',  'TSLA': 'stock',  'NVDA': 'stock',
    'META': 'stock',  'NFLX': 'stock',  'AMD': 'stock',
}

# ─────────────────────────────────────────────────────────────────────────────
#  Symbol aliases → canonical name used in the correlation graph
# ─────────────────────────────────────────────────────────────────────────────
_ALIASES: Dict[str, str] = {
    'XBTUSD': 'BTC',  'BTCUSD': 'BTC',  'BTCUSDT': 'BTC',  'BTCEUR': 'BTC',
    'ETHUSD': 'ETH',  'ETHUSDT': 'ETH',
    'SOLUSD': 'SOL',  'SOLUSDT': 'SOL',
    'AVAXUSD': 'AVAX', 'AVAXUSDT': 'AVAX',
    'LINKUSD': 'LINK', 'LINKUSDT': 'LINK',
    'DOTUSD': 'DOT',  'DOTUSDT': 'DOT',
    'MATICUSD': 'MATIC', 'MATICUSDT': 'MATIC',
    'XLMUSD': 'XLM',  'XLMUSDT': 'XLM',
    'ADAUSD': 'ADA',  'ADAUSDT': 'ADA',
    'DOGEUSD': 'DOGE', 'DOGEUSDT': 'DOGE',
    'XRPUSD': 'XRP',  'XRPUSDT': 'XRP',
    'LTCUSD': 'LTC',  'LTCUSDT': 'LTC',
    'UNIUSD': 'UNI',  'UNIUSDT': 'UNI',
    'AAVEUSD': 'AAVE', 'AAVEUSDT': 'AAVE',
    'ATOMUSD': 'ATOM', 'NEARUSD': 'NEAR',
    'APTUSD': 'APT',  'ARBUSD': 'ARB', 'OPUSD': 'OP',
    'XAUUSD': 'GOLD', 'XAGUSD': 'SILVER',
    'OILCRUDE': 'OIL_CRUDE',
}

# ─────────────────────────────────────────────────────────────────────────────
#  Fallback: which exchange to route a pre-signal to (if not in live scan)
# ─────────────────────────────────────────────────────────────────────────────
_EXCHANGE_FALLBACK: Dict[str, Tuple[str, str]] = {
    # canonical → (exchange, symbol_on_that_exchange)
    'BTC':   ('kraken',  'BTC/USD'),   'ETH':  ('kraken', 'ETH/USD'),
    'SOL':   ('kraken',  'SOL/USD'),   'AVAX': ('kraken', 'AVAX/USD'),
    'LINK':  ('kraken',  'LINK/USD'),  'DOT':  ('kraken', 'DOT/USD'),
    'MATIC': ('alpaca',  'MATICUSD'),  'XLM':  ('kraken', 'XLM/USD'),
    'ADA':   ('kraken',  'ADA/USD'),   'DOGE': ('alpaca', 'DOGEUSD'),
    'XRP':   ('kraken',  'XRP/USD'),   'LTC':  ('kraken', 'LTC/USD'),
    'UNI':   ('alpaca',  'UNIUSD'),    'AAVE': ('alpaca', 'AAVEUSD'),
    'ATOM':  ('alpaca',  'ATOMUSD'),
    'EURUSD': ('capital', 'EURUSD'),   'GBPUSD': ('capital', 'GBPUSD'),
    'USDJPY': ('capital', 'USDJPY'),   'AUDUSD': ('capital', 'AUDUSD'),
    'USDCAD': ('capital', 'USDCAD'),   'NZDUSD': ('capital', 'NZDUSD'),
    'US500': ('capital', 'US500'),     'US30':   ('capital', 'US30'),
    'NAS100':('capital', 'NAS100'),    'UK100':  ('capital', 'UK100'),
    'GER40': ('capital', 'GER40'),
    'GOLD':  ('capital', 'GOLD'),      'SILVER': ('capital', 'SILVER'),
    'OIL_CRUDE': ('capital', 'OIL_CRUDE'), 'NATURAL_GAS': ('capital', 'NATURAL_GAS'),
    'AAPL':  ('capital', 'AAPL'),      'MSFT':   ('capital', 'MSFT'),
    'TSLA':  ('capital', 'TSLA'),      'NVDA':   ('capital', 'NVDA'),
    'GOOGL': ('capital', 'GOOGL'),     'AMZN':   ('capital', 'AMZN'),
    'META':  ('capital', 'META'),      'NFLX':   ('capital', 'NFLX'),
}

# ─────────────────────────────────────────────────────────────────────────────
#  Correlation graph: (leader, follower, strength, typical_lag_seconds)
#    strength > 0 → positive correlation (same direction)
#    strength < 0 → inverse (opposite direction)
# ─────────────────────────────────────────────────────────────────────────────
CORRELATION_EDGES: List[Tuple[str, str, float, int]] = [
    # ── BTC → altcoin cascade ─────────────────────────────────────────────
    ('BTC',   'ETH',    0.92,  60),
    ('BTC',   'SOL',    0.85, 120),
    ('BTC',   'AVAX',   0.82, 180),
    ('BTC',   'LINK',   0.78, 180),
    ('BTC',   'DOT',    0.80, 180),
    ('BTC',   'MATIC',  0.75, 240),
    ('BTC',   'XLM',    0.70, 240),
    ('BTC',   'ADA',    0.72, 180),
    ('BTC',   'DOGE',   0.65, 240),
    ('BTC',   'XRP',    0.68, 180),
    ('BTC',   'LTC',    0.75, 120),
    ('BTC',   'ATOM',   0.73, 180),
    # ── ETH → DeFi tokens ────────────────────────────────────────────────
    ('ETH',   'LINK',   0.82, 120),
    ('ETH',   'MATIC',  0.80, 120),
    ('ETH',   'AVAX',   0.75, 120),
    ('ETH',   'UNI',    0.82, 120),
    ('ETH',   'AAVE',   0.78, 120),
    # ── US Indices (near-simultaneous) ───────────────────────────────────
    ('NAS100', 'US500', 0.88,  30),
    ('NAS100', 'US30',  0.82,  30),
    ('US500',  'US30',  0.85,  30),
    # ── Indices → Tech Stocks ────────────────────────────────────────────
    ('NAS100', 'AAPL',  0.80,  60),
    ('NAS100', 'MSFT',  0.82,  60),
    ('NAS100', 'GOOGL', 0.79,  60),
    ('NAS100', 'NVDA',  0.76,  60),
    ('NAS100', 'META',  0.74,  60),
    ('NAS100', 'TSLA',  0.70,  60),
    ('NAS100', 'AMZN',  0.78,  60),
    ('NAS100', 'NFLX',  0.68,  60),
    ('US500',  'AAPL',  0.75,  60),
    ('US500',  'MSFT',  0.77,  60),
    # ── Gold → Silver (commodity pair) ───────────────────────────────────
    ('GOLD',   'SILVER', 0.85,  60),
    # ── Gold risk-off: indices dip when gold spikes ───────────────────────
    ('GOLD',   'US500', -0.45, 120),
    ('GOLD',   'NAS100',-0.40, 120),
    # ── Oil correlations ─────────────────────────────────────────────────
    ('OIL_CRUDE', 'NATURAL_GAS', 0.60, 120),
    # ── Forex DXY cascade: EURUSD leads ──────────────────────────────────
    ('EURUSD', 'GBPUSD', 0.78,  60),
    ('EURUSD', 'AUDUSD', 0.70,  60),
    ('EURUSD', 'NZDUSD', 0.68,  60),
    # ── USD strength → crypto weakens (macro risk-off) ───────────────────
    ('USDJPY', 'BTC',   -0.35, 180),
    # ── Risk-on: indices up → crypto loosely follows ─────────────────────
    ('NAS100', 'BTC',    0.45, 240),
    ('US500',  'BTC',    0.40, 300),
    ('NAS100', 'ETH',    0.42, 240),
    # ── Oil → USDCAD inverse (oil up → CAD up → USDCAD down) ─────────────
    ('OIL_CRUDE', 'USDCAD', -0.55, 120),
]


def _norm(sym: str) -> str:
    """Normalise a symbol to canonical form (strip separators, uppercase, apply aliases)."""
    s = sym.upper().replace('/', '').replace('-', '').replace('_', '').replace(' ', '')
    return _ALIASES.get(s, s)


@dataclass
class PreSignal:
    """A pre-signal: follower asset that hasn't caught up with its leader yet."""
    leader: str
    follower: str
    follower_exchange: str
    follower_symbol: str        # exact symbol to use on that exchange
    leader_move_pct: float
    expected_move_pct: float    # what follower should do based on correlation
    already_moved_pct: float    # how much follower has already moved
    remaining_pct: float        # remaining expected move = expected - already
    correlation: float          # 0–1 strength
    lag_seconds: int
    category: str
    regime: str


class CrossAssetCorrelator:
    """
    Cross-asset correlation and pre-signal engine.

    Feed it the symbols + change_pct from every market scan, and it will:
      - Tell you the current market regime (RISK_ON / RISK_OFF / NEUTRAL)
      - Show category-level moves (crypto avg, forex avg, indices avg, etc.)
      - Return pre-signals: follower assets that haven't caught up to their leaders
    """

    # Tuning knobs
    LEADER_MIN_MOVE     = 0.35   # leader must have moved ≥ 0.35% to trigger
    FOLLOWER_MAX_MOVE   = 0.25   # follower must be lagging (moved ≤ 0.25% so far)
    MIN_CORR_STRENGTH   = 0.60   # ignore weak correlations
    MIN_REMAINING       = 0.15   # remaining expected move must be ≥ 0.15%
    MAX_PRESIGNALS      = 10     # cap added to opportunity list

    def __init__(self) -> None:
        # Rolling history: canonical_symbol → deque of (timestamp, change_pct)
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._last_update: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def update_batch(self, symbol_to_change: Dict[str, float]) -> None:
        """Ingest the latest change_pct for every scanned symbol."""
        ts = time.time()
        for sym, chg in symbol_to_change.items():
            self.history[_norm(sym)].append((ts, float(chg)))
        self._last_update = ts

    def get_category(self, symbol: str) -> str:
        s = symbol.upper().replace('/', '').replace('-', '')
        return ASSET_CATEGORIES.get(s, ASSET_CATEGORIES.get(_norm(symbol), 'unknown'))

    def get_category_moves(self, symbol_to_change: Dict[str, float]) -> Dict[str, float]:
        """Average change_pct per asset category from the current scan batch."""
        buckets: Dict[str, List[float]] = defaultdict(list)
        for sym, chg in symbol_to_change.items():
            cat = self.get_category(sym)
            if cat != 'unknown':
                buckets[cat].append(chg)
        return {cat: sum(v) / len(v) for cat, v in buckets.items() if v}

    def get_regime(self, symbol_to_change: Dict[str, float]) -> str:
        """
        Classify the current macro regime from cross-category moves.
        RISK_ON       — indices/crypto up, gold down
        RISK_OFF      — gold up, indices/crypto down
        MILD_RISK_ON  — mild positive drift
        MILD_RISK_OFF — mild negative drift
        NEUTRAL       — mixed / flat
        """
        cat = self.get_category_moves(symbol_to_change)
        crypto  = cat.get('crypto',    0.0)
        idx     = cat.get('index',     0.0)
        gold    = cat.get('commodity', 0.0)
        forex   = cat.get('forex',     0.0)   # EUR/GBP leads = USD weakness = risk-on

        risk_on  = 0
        risk_off = 0

        if idx     >  0.30: risk_on  += 2
        if idx     < -0.30: risk_off += 2
        if crypto  >  0.50: risk_on  += 1
        if crypto  < -0.50: risk_off += 1
        if gold    >  0.30: risk_off += 1   # safe-haven bid
        if gold    < -0.30: risk_on  += 1
        if forex   >  0.20: risk_on  += 1   # USD weakness
        if forex   < -0.20: risk_off += 1

        if   risk_on  >= 3: return 'RISK_ON'
        elif risk_off >= 3: return 'RISK_OFF'
        elif risk_on  >  risk_off: return 'MILD_RISK_ON'
        elif risk_off >  risk_on:  return 'MILD_RISK_OFF'
        return 'NEUTRAL'

    def get_pre_signals(
        self,
        symbol_to_change:  Dict[str, float],
        symbol_to_price:   Dict[str, float],
        symbol_to_exchange: Dict[str, str],
        existing_symbols:  set,
    ) -> List[PreSignal]:
        """
        Find follower assets where:
          1. The correlated leader has already moved significantly
          2. The follower hasn't caught up yet
          3. There's still meaningful remaining upside/downside to capture

        Returns list sorted by |remaining_pct| descending (biggest opportunity first).
        """
        # Build normalised lookup
        canon_change: Dict[str, float] = {_norm(s): v for s, v in symbol_to_change.items()}
        regime = self.get_regime(symbol_to_change)
        signals: List[PreSignal] = []
        seen_followers: set = set()

        for leader, follower, strength, lag in CORRELATION_EDGES:
            leader_chg = canon_change.get(leader)
            if leader_chg is None:
                continue
            if abs(leader_chg) < self.LEADER_MIN_MOVE:
                continue
            if abs(strength) < self.MIN_CORR_STRENGTH:
                continue

            follower_chg   = canon_change.get(follower, 0.0)
            expected_move  = leader_chg * strength         # signed
            remaining      = expected_move - follower_chg  # how much is left

            # Follower must be genuinely lagging (not already over-shot)
            if abs(remaining) < self.MIN_REMAINING:
                continue
            if abs(follower_chg) > abs(expected_move) * 1.3:
                continue   # already ran past the expected move

            # Deduplicate: only best signal per follower
            if follower in seen_followers:
                continue
            seen_followers.add(follower)

            # Find exchange + symbol for follower
            ex, sym = self._find_follower(follower, symbol_to_exchange)
            if not ex or not sym:
                continue

            # Skip if already in live scan results
            if sym in existing_symbols or follower in existing_symbols:
                continue

            price = symbol_to_price.get(sym, symbol_to_price.get(follower, 0.0))

            signals.append(PreSignal(
                leader=leader,
                follower=follower,
                follower_exchange=ex,
                follower_symbol=sym,
                leader_move_pct=leader_chg,
                expected_move_pct=expected_move,
                already_moved_pct=follower_chg,
                remaining_pct=remaining,
                correlation=abs(strength),
                lag_seconds=lag,
                category=self.get_category(follower),
                regime=regime,
            ))

        signals.sort(key=lambda s: abs(s.remaining_pct), reverse=True)
        return signals[:self.MAX_PRESIGNALS]

    def format_category_table(self, symbol_to_change: Dict[str, float]) -> str:
        """Return a formatted multi-line string of category moves + regime."""
        cat   = self.get_category_moves(symbol_to_change)
        regime = self.get_regime(symbol_to_change)
        lines = [f"  CROSS-ASSET REGIME: {regime}"]
        order = ['crypto', 'index', 'forex', 'commodity', 'stock']
        for c in order:
            if c not in cat:
                continue
            m  = cat[c]
            arrow = '↑' if m > 0.1 else '↓' if m < -0.1 else '→'
            bar_len = min(20, int(abs(m) * 5))
            bar = ('█' * bar_len) if m > 0 else ('░' * bar_len)
            lines.append(f"     {c.upper():10s}  {m:+6.2f}% {arrow}  {bar}")
        return '\n'.join(lines)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _find_follower(
        self,
        canonical: str,
        symbol_to_exchange: Dict[str, str],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return (exchange, symbol) for a canonical asset name."""
        # 1. Look in live scan results first
        for sym, ex in symbol_to_exchange.items():
            if _norm(sym) == canonical:
                return ex, sym
        # 2. Static fallback
        if canonical in _EXCHANGE_FALLBACK:
            ex, sym = _EXCHANGE_FALLBACK[canonical]
            return ex, sym
        return None, None


# ─────────────────────────────────────────────────────────────────────────────
#  LIVE ANALYSIS ENTRY POINT (real public data only, fail-closed)
# ─────────────────────────────────────────────────────────────────────────────

def run_analysis(
    crypto_changes: Optional[Dict[str, Dict[str, float]]] = None,
    yahoo_changes: Optional[Dict[str, Optional[Dict[str, float]]]] = None,
) -> Dict:
    """Run the correlator on REAL market data.

    Fetches (throttled, via aureon_fusion.api_communion):
      - Binance public 24h tickers  -> crypto change_pct per liquid base asset
      - Yahoo Finance chart         -> forex / index / commodity / stock change_pct

    Args:
        crypto_changes: optional pre-fetched ``binance_tickers_to_changes``
            result (the aggregator passes its own batch to avoid duplicate calls).
        yahoo_changes: optional pre-fetched {symbol: {change_pct, price}|None}.

    Returns a JSON-safe dict. On total data failure returns
    ``{"ok": False, "regime": None, ..., "error": "..."}`` — never fabricated.
    Pre-signals are model inference from measured leader moves + static
    correlation priors, and are labeled as such.
    """
    import time as _time

    try:
        from analyzers import global_energy_data as ged
    except ImportError:  # standalone: run from inside analyzers/
        import global_energy_data as ged

    if crypto_changes is None:
        tickers = ged.fetch_binance_24h_tickers()
        crypto_changes = ged.binance_tickers_to_changes(tickers) if tickers else None

    if yahoo_changes is None:
        yahoo_changes = {}
        for sym in list(ged.YAHOO_MAP):
            yahoo_changes[sym] = ged.fetch_yahoo_change_pct(sym)

    symbol_to_change: Dict[str, float] = {}
    symbol_to_price: Dict[str, float] = {}
    symbol_to_exchange: Dict[str, str] = {}
    source_counts = {"crypto": 0, "yahoo": 0, "yahoo_failed": 0}

    if crypto_changes:
        for base, d in crypto_changes.items():
            symbol_to_change[base] = float(d["change_pct"])
            symbol_to_price[base] = float(d["price"])
            symbol_to_exchange[base] = "binance"
            source_counts["crypto"] += 1

    for sym, snap in (yahoo_changes or {}).items():
        if snap is None:
            source_counts["yahoo_failed"] += 1
            continue
        symbol_to_change[sym] = float(snap["change_pct"])
        symbol_to_price[sym] = float(snap["price"])
        symbol_to_exchange[sym] = "yahoo"
        source_counts["yahoo"] += 1

    if not symbol_to_change:
        return {
            "ok": False,
            "ts": _time.time(),
            "regime": None,
            "category_moves": None,
            "pre_signals": None,
            "symbol_count": 0,
            "source_counts": source_counts,
            "error": "no_live_market_data",
        }

    corr = CrossAssetCorrelator()
    corr.update_batch(symbol_to_change)
    regime = corr.get_regime(symbol_to_change)
    category_moves = corr.get_category_moves(symbol_to_change)
    pre_signals = corr.get_pre_signals(
        symbol_to_change, symbol_to_price, symbol_to_exchange, existing_symbols=set()
    )

    return {
        "ok": True,
        "ts": _time.time(),
        "regime": regime,
        "category_moves": category_moves,
        "pre_signals": [
            {
                "leader": s.leader,
                "follower": s.follower,
                "follower_exchange": s.follower_exchange,
                "follower_symbol": s.follower_symbol,
                "leader_move_pct": round(s.leader_move_pct, 4),
                "expected_move_pct": round(s.expected_move_pct, 4),
                "already_moved_pct": round(s.already_moved_pct, 4),
                "remaining_pct": round(s.remaining_pct, 4),
                "correlation": round(s.correlation, 4),
                "lag_seconds": s.lag_seconds,
                "category": s.category,
                "regime": s.regime,
                "inference": "correlation_prior",  # model inference, not measurement
            }
            for s in pre_signals
        ],
        "symbol_count": len(symbol_to_change),
        "source_counts": source_counts,
        "error": None,
    }
