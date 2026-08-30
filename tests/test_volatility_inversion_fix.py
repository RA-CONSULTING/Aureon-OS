"""P4 inversion regression: volatility no longer LOOSENS the entry-coherence formula.

The old E-term rewarded raw (high−low) range, so violent chop raised coherence
toward the entry threshold. The fix scales energy by directional structure
(|net change| / range). These tests prove the formula-level contract:

  * tighten-only — for identical inputs the new coherence is ≤ the old value
    (old formula reimplemented here as the reference), across a grid;
  * churn punished — wide range with no net direction scores strictly lower;
  * clean moves keep their energy — when |change| ≥ range the structure factor
    is 1 and the value is unchanged to the digit;
  * benchmark invariants — the sentinel benchmark's pinned regression
    (all regimes detected while live, calm FPR ≤ 20%, deterministic).
"""

from __future__ import annotations

import math

import pytest

from aureon.trading.aureon_unified_ecosystem import MultiExchangeOrchestrator


def _old_coherence(change: float, volume: float, ticker: dict, asset_class: str) -> float:
    """The pre-P4 formula, verbatim — the regression reference."""
    high = ticker.get('high', ticker.get('price', 1))
    low = ticker.get('low', ticker.get('price', 1))
    volatility = ((high - low) / low * 100) if low > 0 else 0
    if asset_class == 'forex':
        S = min(1.0, volume / 50.0)
        O = min(1.0, abs(change) / 0.3)
        E = min(1.0, volatility / 0.5)
        Lambda = (S + O + E) / 3.0
        return 1 / (1 + math.exp(-6 * (Lambda - 0.35)))
    elif asset_class == 'indices':
        S = min(1.0, volume / 50.0)
        O = min(1.0, abs(change) / 1.0)
        E = min(1.0, volatility / 2.0)
        Lambda = (S + O + E) / 3.0
        return 1 / (1 + math.exp(-6 * (Lambda - 0.35)))
    else:
        S = min(1.0, volume / 50000.0)
        O = min(1.0, abs(change) / 15.0)
        E = min(1.0, volatility / 25.0)
        Lambda = (S + O + E) / 3.0
        return 1 / (1 + math.exp(-5 * (Lambda - 0.5)))


def _new_coherence(change: float, volume: float, ticker: dict, asset_class: str) -> float:
    # The method reads only its arguments — drive it unbound on a bare instance.
    host = object.__new__(MultiExchangeOrchestrator)
    return MultiExchangeOrchestrator._calculate_coherence(host, change, volume, ticker, asset_class)


def _ticker(price: float, spread_pct: float) -> dict:
    half = price * spread_pct / 200.0
    return {"price": price, "high": price + half, "low": price - half}


GRID = [
    (change, volume, spread, asset_class)
    for change in (-12.0, -3.0, -0.5, 0.0, 0.5, 3.0, 12.0)
    for volume in (10.0, 5_000.0, 100_000.0)
    for spread in (0.1, 2.0, 10.0, 30.0)
    for asset_class in ("crypto", "forex", "indices")
]


def test_new_formula_never_exceeds_old_across_grid():
    for change, volume, spread, asset_class in GRID:
        t = _ticker(100.0, spread)
        new = _new_coherence(change, volume, t, asset_class)
        old = _old_coherence(change, volume, t, asset_class)
        assert new <= old + 1e-12, (
            f"tighten-only violated at change={change} volume={volume} "
            f"spread={spread}% class={asset_class}: new={new} > old={old}"
        )


def test_churn_scores_strictly_lower_than_before():
    """Wide range, zero net direction — the exact inversion case: the old formula
    rewarded it, the new one must strictly discount it."""
    t = _ticker(100.0, 20.0)  # 20% intraday sweep
    new = _new_coherence(0.0, 100_000.0, t, "crypto")
    old = _old_coherence(0.0, 100_000.0, t, "crypto")
    assert new < old


def test_directional_move_keeps_full_energy():
    """|change| ≥ range traversed → structure = 1 → identical to the old formula."""
    t = _ticker(100.0, 2.0)
    new = _new_coherence(5.0, 100_000.0, t, "crypto")  # 5% net move > 2% range
    old = _old_coherence(5.0, 100_000.0, t, "crypto")
    assert new == pytest.approx(old, abs=1e-12)


def test_zero_range_is_zero_energy_both_ways():
    t = {"price": 100.0, "high": 100.0, "low": 100.0}
    assert _new_coherence(0.0, 100.0, t, "crypto") == pytest.approx(
        _old_coherence(0.0, 100.0, t, "crypto"))


# ── sentinel benchmark pinned regression ────────────────────────────────────


def test_benchmark_canonical_regimes_detected_and_calm_fpr_bounded():
    from aureon.analytics.volatility_sentinel_benchmark import compute_benchmark

    report = compute_benchmark()
    assert report.all_detected, (
        f"every pinned regime must be flagged while still live: {report.regimes}"
    )
    assert report.min_protected_samples is not None
    assert report.min_protected_samples >= 0, "lead must be >= 0 (never post-hoc)"
    assert report.fpr_calm <= 0.20
    assert report.calm_assessments > 0


def test_benchmark_is_deterministic():
    from aureon.analytics.volatility_sentinel_benchmark import compute_benchmark

    assert compute_benchmark().to_dict() == compute_benchmark().to_dict()
