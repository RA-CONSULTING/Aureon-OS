"""
Unified Signal Engine
=====================
Links every signal source into ONE score per asset and ONE top pick per group.

Signal sources integrated:
  1. Live price momentum (change_pct × volume from exchange scan)
  2. Cross-asset regime (RISK_ON / RISK_OFF / NEUTRAL from cross_asset_correlator)
  3. Category-level average moves (crypto avg, forex avg, etc.)
  4. Correlation pre-signals (_correlation_signal flag + remaining_pct)
  5. Market Harp resonance ripples (confidence boosts from market_harp.tick())
  6. News/geopolitical sentiment per category (from news_signal RSS)
  7. Macro score: Fear & Greed + BTC dominance (from macro_intelligence)

Output:
  UnifiedSignal  — per asset: direction + confidence + composite score + sources
  GroupSignal    — per category: bias + top picks ranked within group

The engine is deliberately read-only: it doesn't fetch any external data itself,
it just aggregates what scan_entire_market already discovered.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────────────────────

# How much each source can shift the final score (weights must sum to 1.0)
WEIGHT_MOMENTUM     = 0.30   # live price change × volume (exchange scan)
WEIGHT_HARP         = 0.20   # Market Harp resonance boost
WEIGHT_REGIME       = 0.15   # cross-asset regime alignment
WEIGHT_NEWS         = 0.20   # news/geopolitical sentiment
WEIGHT_MACRO        = 0.10   # Fear & Greed + macro score
WEIGHT_CORRELATION  = 0.05   # pre-signal boost (correlation engine)

# Minimum confidence to emit a BUY or SELL direction (otherwise NEUTRAL)
BUY_THRESHOLD  = 0.55
SELL_THRESHOLD = 0.45   # unified score < this → SELL signal

# Category → regime alignment (RISK_ON boosts these, RISK_OFF hurts them)
RISK_ON_CATEGORIES  = {'crypto', 'index', 'stock'}
RISK_OFF_CATEGORIES = {'commodity', 'forex'}   # safe-haven / defensive

# Group bias labels
BIAS_LABELS = {
    (0.80, 1.01): 'STRONG_BUY',
    (0.60, 0.80): 'BUY',
    (0.45, 0.60): 'MILD_BUY',
    (0.40, 0.45): 'NEUTRAL',
    (0.25, 0.40): 'MILD_SELL',
    (0.00, 0.25): 'SELL',
}


def _bias_label(score: float) -> str:
    for (lo, hi), label in BIAS_LABELS.items():
        if lo <= score < hi:
            return label
    return 'NEUTRAL'


# ─────────────────────────────────────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class UnifiedSignal:
    """Full per-asset aggregated signal."""
    symbol:         str
    exchange:       str
    category:       str
    price:          float
    change_pct:     float

    direction:      str     # BUY / SELL / NEUTRAL
    confidence:     float   # 0.0 → 1.0
    raw_score:      float   # composite before clamping (can be > 1)

    sources:        List[str]           # which signals contributed
    score_breakdown: Dict[str, float]   # source → contribution

    # Rank within category (1 = strongest in group)
    group_rank:     int = 0

    # Original momentum_score from scan (for comparison)
    original_momentum: float = 0.0

    # Boost multiplier to apply to momentum_score in the pipeline
    @property
    def pipeline_boost(self) -> float:
        """Multiplier to apply to the opportunity's momentum_score."""
        if self.confidence >= 0.80:
            return 1.6
        elif self.confidence >= 0.65:
            return 1.35
        elif self.confidence >= 0.55:
            return 1.15
        elif self.confidence <= 0.35:
            return 0.75    # dampen weak/sell signals
        return 1.0

    def one_line(self) -> str:
        src = ', '.join(self.sources[:4])
        return (f"{self.symbol:12s} [{self.exchange:7s}] {self.category:9s} "
                f"{self.direction:7s} conf={self.confidence:.0%}  "
                f"chg={self.change_pct:+.2f}%  sources=[{src}]")


@dataclass
class GroupSignal:
    """Aggregated signal for a whole asset category."""
    category:       str
    bias:           str             # STRONG_BUY / BUY / NEUTRAL / SELL / STRONG_SELL
    confidence:     float           # avg confidence of top assets in group
    regime_note:    str             # how the regime affects this category
    news_note:      str             # what news says about this category
    top_picks:      List[UnifiedSignal] = field(default_factory=list)

    def summary(self) -> str:
        picks = ', '.join(f"{p.symbol}({p.confidence:.0%})" for p in self.top_picks[:3])
        return (f"  {self.category.upper():10s}  {self.bias:12s}  "
                f"conf={self.confidence:.0%}  "
                f"picks=[{picks}]")


@dataclass
class UnifiedBundle:
    """Complete output of one engine.process() call."""
    signals:        List[UnifiedSignal]              # all assets, sorted by confidence
    groups:         Dict[str, GroupSignal]            # one per category
    top_per_group:  Dict[str, Optional[UnifiedSignal]] # single best per category
    regime:         str
    geo_risk:       str                              # NORMAL / ELEVATED / HIGH / EXTREME
    summary_lines:  List[str]                        # human-readable dashboard


# ─────────────────────────────────────────────────────────────────────────────
#  Engine
# ─────────────────────────────────────────────────────────────────────────────

class UnifiedSignalEngine:
    """
    Aggregates all signal layers into unified per-asset scores and group rankings.

    Designed to be called once per scan cycle with whatever data is available —
    any missing source simply contributes zero to the score.
    """

    def __init__(self) -> None:
        self._last_bundle: Optional[UnifiedBundle] = None

    def process(
        self,
        opportunities: list,                        # List[MarketOpportunity]
        regime:             str   = 'NEUTRAL',       # from cross_asset_correlator
        category_moves:     Dict[str, float] = None, # {category: avg_change_pct}
        harp_boosts:        Dict[str, float] = None, # {symbol: confidence} from MarketHarp.tick()
        news_sentiment:     Dict[str, float] = None, # {category: -1..+1} from news_signal
        macro_score:        float = 0.0,             # -2..+2 from macro_intelligence
        fear_greed:         int   = 50,              # 0-100 fear & greed index
        geo_risk_level:     str   = 'NORMAL',
    ) -> UnifiedBundle:
        """
        Run all opportunities through the unified signal pipeline.

        Returns UnifiedBundle with per-asset signals and per-group rankings.
        """
        category_moves  = category_moves  or {}
        harp_boosts     = harp_boosts     or {}
        news_sentiment  = news_sentiment  or {}

        # ── Normalise macro score to 0..1 (macro_intelligence gives -2..+2) ──
        macro_norm = (macro_score + 2.0) / 4.0   # maps -2..+2 → 0..0.5..1.0

        # ── Fear & Greed: 0-100 → 0..1 (>50 = greedy = risk-on = bullish) ──
        fg_norm = fear_greed / 100.0

        # ── Combined macro signal ─────────────────────────────────────────────
        macro_combined = (macro_norm * 0.6 + fg_norm * 0.4)   # 0..1

        # ── Regime multiplier per category ───────────────────────────────────
        def regime_mult(category: str) -> float:
            """How much the current regime boosts/hurts this category."""
            if regime in ('RISK_ON', 'MILD_RISK_ON'):
                factor = 1.0 if regime == 'MILD_RISK_ON' else 0.8
                if category in RISK_ON_CATEGORIES:
                    return 0.5 + factor * 0.25   # up to +0.25 bonus
                elif category in RISK_OFF_CATEGORIES:
                    return 0.5 - factor * 0.15   # slight penalty
            elif regime in ('RISK_OFF', 'MILD_RISK_OFF'):
                factor = 1.0 if regime == 'MILD_RISK_OFF' else 0.8
                if category in RISK_OFF_CATEGORIES:
                    return 0.5 + factor * 0.20   # safe-haven benefits
                elif category in RISK_ON_CATEGORIES:
                    return 0.5 - factor * 0.15   # risk assets hurt
            return 0.50   # neutral

        # ── Process each opportunity ─────────────────────────────────────────
        unified_signals: List[UnifiedSignal] = []

        for opp in opportunities:
            cat = self._get_category(opp)
            symbol = opp.symbol

            sources:    List[str]          = []
            breakdown:  Dict[str, float]   = {}

            # 1. Momentum from exchange scan (change_pct normalised to 0..1)
            #    change_pct: 0% = 0.5 neutral, positive = above 0.5, negative = below
            raw_chg = float(getattr(opp, 'change_pct', 0.0))
            momentum_norm = min(1.0, max(0.0, 0.5 + raw_chg / 10.0))
            m_contrib = WEIGHT_MOMENTUM * momentum_norm
            breakdown['momentum'] = m_contrib
            if abs(raw_chg) >= 0.05:
                sources.append(f"momentum({raw_chg:+.2f}%)")

            # 2. Market Harp ripple boost
            harp_conf = 0.5   # neutral default
            harp_raw  = self._find_harp_boost(symbol, harp_boosts)
            if harp_raw > 0:
                harp_conf = min(1.0, 0.5 + harp_raw * 0.5)   # 0..1 with 0.5 floor
                sources.append(f"harp({harp_raw:.2f})")
            h_contrib = WEIGHT_HARP * harp_conf
            breakdown['harp'] = h_contrib

            # 3. Regime alignment
            reg_score = regime_mult(cat)
            r_contrib = WEIGHT_REGIME * reg_score
            breakdown['regime'] = r_contrib
            if abs(reg_score - 0.5) >= 0.1:
                direction_word = 'aligned' if reg_score > 0.5 else 'against'
                sources.append(f"regime_{direction_word}({regime})")

            # 4. News sentiment for this category
            news_cat   = news_sentiment.get(cat, 0.0)
            news_norm  = min(1.0, max(0.0, 0.5 + news_cat * 0.5))   # -1..+1 → 0..1
            n_contrib  = WEIGHT_NEWS * news_norm
            breakdown['news'] = n_contrib
            if abs(news_cat) >= 0.15:
                sources.append(f"news({news_cat:+.2f})")

            # 5. Macro (global fear/greed + macro_intelligence score)
            mac_contrib = WEIGHT_MACRO * macro_combined
            breakdown['macro'] = mac_contrib
            if abs(macro_combined - 0.5) >= 0.1:
                sources.append(f"macro({macro_combined:.2f})")

            # 6. Correlation pre-signal boost
            corr_contrib = 0.0
            if getattr(opp, '_correlation_signal', False):
                remaining = abs(getattr(opp, '_correlation_remaining', 0.0))
                corr_str  = getattr(opp, '_correlation_strength', 0.5)
                corr_norm = min(1.0, 0.5 + remaining * corr_str * 2.0)
                corr_contrib = WEIGHT_CORRELATION * corr_norm
                leader = getattr(opp, '_correlation_leader', '?')
                sources.append(f"presignal({leader}→{remaining:.2f}%)")
            breakdown['correlation'] = corr_contrib

            # ── Composite score ──────────────────────────────────────────────
            raw_score  = sum(breakdown.values())
            confidence = min(1.0, max(0.0, raw_score))

            if confidence >= BUY_THRESHOLD:
                direction = 'BUY'
            elif confidence <= SELL_THRESHOLD:
                direction = 'SELL'
            else:
                direction = 'NEUTRAL'

            unified_signals.append(UnifiedSignal(
                symbol=symbol,
                exchange=opp.exchange,
                category=cat,
                price=float(getattr(opp, 'price', 0.0)),
                change_pct=raw_chg,
                direction=direction,
                confidence=confidence,
                raw_score=raw_score,
                sources=sources,
                score_breakdown=breakdown,
                original_momentum=float(getattr(opp, 'momentum_score', 0.0)),
            ))

        # ── Sort overall by confidence desc ──────────────────────────────────
        unified_signals.sort(key=lambda s: s.confidence, reverse=True)

        # ── Group signals by category ─────────────────────────────────────────
        by_cat: Dict[str, List[UnifiedSignal]] = defaultdict(list)
        for sig in unified_signals:
            by_cat[sig.category].append(sig)

        groups: Dict[str, GroupSignal] = {}
        top_per_group: Dict[str, Optional[UnifiedSignal]] = {}

        for cat, cat_signals in by_cat.items():
            # Rank within group (1 = highest confidence in group)
            for rank, sig in enumerate(cat_signals, 1):
                sig.group_rank = rank

            # Group bias = average confidence of top 3 in category
            top3 = cat_signals[:3]
            avg_conf = sum(s.confidence for s in top3) / len(top3) if top3 else 0.5
            bias = _bias_label(avg_conf)

            # Regime note
            reg_score = regime_mult(cat)
            if reg_score > 0.6:
                regime_note = f"{regime} → FAVOURS {cat.upper()}"
            elif reg_score < 0.4:
                regime_note = f"{regime} → HEADWIND for {cat.upper()}"
            else:
                regime_note = f"{regime} → NEUTRAL for {cat.upper()}"

            # News note
            news_cat = news_sentiment.get(cat, 0.0)
            if news_cat >= 0.3:
                news_note = f"News BULLISH ({news_cat:+.2f})"
            elif news_cat <= -0.3:
                news_note = f"News BEARISH ({news_cat:+.2f})"
            else:
                news_note = f"News NEUTRAL ({news_cat:+.2f})"

            group_sig = GroupSignal(
                category=cat,
                bias=bias,
                confidence=avg_conf,
                regime_note=regime_note,
                news_note=news_note,
                top_picks=cat_signals[:5],
            )
            groups[cat] = group_sig
            top_per_group[cat] = cat_signals[0] if cat_signals else None

        # ── Build summary lines for logging ──────────────────────────────────
        summary_lines = self._build_summary(
            groups, top_per_group, regime, geo_risk_level, fear_greed, macro_score
        )

        bundle = UnifiedBundle(
            signals=unified_signals,
            groups=groups,
            top_per_group=top_per_group,
            regime=regime,
            geo_risk=geo_risk_level,
            summary_lines=summary_lines,
        )
        self._last_bundle = bundle
        return bundle

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_category(self, opp) -> str:
        """Infer category from the opportunity's exchange or symbol."""
        # If cross_asset_correlator already tagged it, trust that
        if hasattr(opp, '_category'):
            return opp._category

        exchange = getattr(opp, 'exchange', '')
        symbol   = getattr(opp, 'symbol', '').upper().replace('/', '')

        if exchange == 'capital':
            # Capital.com symbols tell us the category
            FOREX_SYMS  = {'EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','NZDUSD','USDCHF','EURGBP'}
            INDEX_SYMS  = {'US500','US30','NAS100','UK100','GER40','FRA40','DE40','JP225'}
            COMMOD_SYMS = {'GOLD','SILVER','OILCRUDE','OIL_CRUDE','NATURALGAS','NATURAL_GAS','XAUUSD','XAGUSD'}
            STOCK_SYMS  = {'AAPL','MSFT','GOOGL','AMZN','TSLA','NVDA','META','NFLX','AMD'}
            if symbol in FOREX_SYMS:   return 'forex'
            if symbol in INDEX_SYMS:   return 'index'
            if symbol in COMMOD_SYMS:  return 'commodity'
            if symbol in STOCK_SYMS:   return 'stock'

        # Crypto exchanges
        if exchange in ('kraken', 'alpaca', 'binance'):
            return 'crypto'

        # Try cross_asset_correlator categories if available
        try:
            from aureon.analytics.cross_asset_correlator import ASSET_CATEGORIES, _norm
            cat = ASSET_CATEGORIES.get(symbol, ASSET_CATEGORIES.get(_norm(symbol), ''))
            if cat:
                return cat
        except ImportError:
            pass

        return 'crypto'   # safe default for unknown

    def _find_harp_boost(self, symbol: str, harp_boosts: Dict[str, float]) -> float:
        """Look up harp boost for a symbol, trying various name forms."""
        if not harp_boosts:
            return 0.0
        sym_variants = [
            symbol,
            symbol.upper(),
            symbol.replace('/', '').upper(),
            symbol.replace('/USD', '').upper(),
            symbol.replace('USD', '').upper(),
        ]
        for v in sym_variants:
            if v in harp_boosts:
                return harp_boosts[v]
        return 0.0

    def _build_summary(
        self,
        groups:         Dict[str, GroupSignal],
        top_per_group:  Dict[str, Optional[UnifiedSignal]],
        regime:         str,
        geo_risk:       str,
        fear_greed:     int,
        macro_score:    float,
    ) -> List[str]:
        lines = [
            "╔══════════════════════════════════════════════════════════════════╗",
            f"║  UNIFIED SIGNAL DASHBOARD                                        ║",
            f"║  Regime: {regime:<18s}  GeoRisk: {geo_risk:<10s}  F&G: {fear_greed:3d}/100  ║",
            "╠══════════════════════════════════════════════════════════════════╣",
        ]

        cat_order = ['crypto', 'index', 'forex', 'commodity', 'stock']
        for cat in cat_order:
            grp = groups.get(cat)
            if not grp:
                continue
            top = top_per_group.get(cat)
            top_str = f"{top.symbol}@{top.exchange}({top.confidence:.0%})" if top else "—"
            lines.append(
                f"║  {cat.upper():9s}  {grp.bias:12s}  conf={grp.confidence:.0%}"
                f"  TOP={top_str:<28s}║"
            )
            lines.append(f"║    {grp.regime_note:<62s}║")
            lines.append(f"║    {grp.news_note:<62s}║")
            if grp.top_picks:
                picks_str = '  '.join(
                    f"{p.symbol}({p.direction[0]}:{p.confidence:.0%})"
                    for p in grp.top_picks[:4]
                )
                lines.append(f"║    Ranked: {picks_str:<56s}║")
            lines.append("║" + "─" * 66 + "║")

        lines.append("╚══════════════════════════════════════════════════════════════════╝")
        return lines

    @property
    def last_bundle(self) -> Optional[UnifiedBundle]:
        return self._last_bundle
