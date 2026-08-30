#!/usr/bin/env python3
"""
Cross-Substrate Automated Response Monitor
============================================

Research protocol for measuring correlation between solar events
and automated system activity across financial, academic, and social
substrates.

Based on Leckey (2026) cross-substrate hypothesis:
  H1: Solar events (CME, X-flares) trigger synchronized increases
      in automated activity across multiple substrates, suggesting
      shared infrastructure responding to volatility/disruption signals.

Data Sources (all open/free):
  Solar:  NOAA SWPC (X-ray flux, Kp index, solar wind)
  Financial: CoinGlass (liquidations), Alternative.me (fear/greed)
  Infrastructure: Cloudflare Radar (DDoS reports)

Academic precedent:
  - Krivelyova & Robotti (2003): Geomagnetic storms vs stock returns
  - Kamstra et al. (2003): SAD and market behavior
  - Floros (2021): Solar activity vs Bitcoin volatility

Gary Leckey | February 2026
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import json
import logging
import math
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

import numpy as np

try:
    import requests
except ImportError:
    requests = None

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)

# ===========================================================================
# Constants
# ===========================================================================
PHI = (1 + math.sqrt(5)) / 2
SCHUMANN_BASE_HZ = 7.83
COLLECTION_INTERVAL_SECONDS = 3600  # Hourly snapshots
BASELINE_DAYS = 30
EVENT_RESPONSE_WINDOW_HOURS = 6
FLARE_THRESHOLD_FLUX = 5e-5  # M5.0 class


# ===========================================================================
# Data Structures
# ===========================================================================

@dataclass
class SolarSnapshot:
    """Solar conditions at a single timestamp."""
    timestamp: str
    xray_flux: float           # W/m^2 from GOES satellite
    kp_index: float            # 0-9 geomagnetic index
    solar_wind_speed: float    # km/s
    proton_density: float      # p/cm^3
    bz_component: float        # nT (negative = geo-effective)

    def is_storm(self) -> bool:
        return self.kp_index >= 5

    def is_flare(self) -> bool:
        return self.xray_flux >= FLARE_THRESHOLD_FLUX


@dataclass
class SubstrateSnapshot:
    """Activity metrics across substrates at a single timestamp."""
    timestamp: str

    # Financial substrate
    btc_liquidations_24h: float = 0.0
    fear_greed_index: float = 50.0
    btc_volatility_1h: float = 0.0

    # Infrastructure substrate
    dns_query_rate: float = 0.0
    ddos_events_24h: int = 0

    # Social substrate
    crypto_mentions_1h: int = 0
    new_token_launches_1h: int = 0


@dataclass
class CrossSubstrateEvent:
    """A detected solar event with measured substrate response."""
    event_type: str            # "flare", "cme", "storm"
    event_time: str
    solar_magnitude: float     # Flux or Kp
    baseline_activity: Dict[str, float] = field(default_factory=dict)
    response_activity: Dict[str, float] = field(default_factory=dict)
    percent_changes: Dict[str, float] = field(default_factory=dict)
    lag_hours: float = 0.0


# ===========================================================================
# Solar Data Fetcher (NOAA SWPC - free, no API key)
# ===========================================================================

class SolarDataFetcher:
    """Fetch real-time and historical solar data from NOAA SWPC."""

    XRAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json"
    KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    SOLAR_WIND_URL = "https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json"
    PROTON_URL = "https://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json"

    def fetch_current(self) -> Optional[SolarSnapshot]:
        """Fetch current solar conditions from NOAA."""
        if requests is None:
            logger.warning("requests library not available")
            return None

        try:
            xray_flux = self._fetch_xray_flux()
            kp_index = self._fetch_kp_index()
            wind_speed = self._fetch_solar_wind_speed()

            return SolarSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                xray_flux=xray_flux,
                kp_index=kp_index,
                solar_wind_speed=wind_speed,
                proton_density=0.0,
                bz_component=0.0,
            )
        except Exception as exc:
            logger.error(f"Solar data fetch failed: {exc}")
            return None

    def _fetch_xray_flux(self) -> float:
        resp = requests.get(self.XRAY_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data:
            return float(data[-1].get("flux", 1e-7))
        return 1e-7

    def _fetch_kp_index(self) -> float:
        resp = requests.get(self.KP_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if len(data) > 1:
            return float(data[-1][1])
        return 0.0

    def _fetch_solar_wind_speed(self) -> float:
        resp = requests.get(self.SOLAR_WIND_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "WindSpeed" in data:
            return float(data["WindSpeed"])
        return 400.0


# ===========================================================================
# Substrate Activity Fetcher
# ===========================================================================

class SubstrateActivityFetcher:
    """Fetch activity metrics from financial and social substrates."""

    FEAR_GREED_URL = "https://api.alternative.me/fng/"

    def fetch_current(self) -> SubstrateSnapshot:
        """Collect snapshot of all substrate activity."""
        snapshot = SubstrateSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        # Fear & Greed Index (free API)
        try:
            if requests is not None:
                resp = requests.get(self.FEAR_GREED_URL, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if "data" in data and len(data["data"]) > 0:
                        snapshot.fear_greed_index = float(data["data"][0]["value"])
        except Exception as exc:
            logger.warning(f"Fear/Greed fetch failed: {exc}")

        return snapshot


# ===========================================================================
# Cross-Substrate Monitor (the main engine)
# ===========================================================================

class CrossSubstrateMonitor:
    """
    Continuously collects solar + substrate data and detects correlations.

    Usage:
        monitor = CrossSubstrateMonitor()
        monitor.collect_snapshot()          # Run hourly
        events = monitor.detect_events()    # Check for solar events
        analysis = monitor.analyze_event(event)  # Measure response
    """

    def __init__(self, data_dir: str = "data/cross_substrate"):
        self.solar_fetcher = SolarDataFetcher()
        self.substrate_fetcher = SubstrateActivityFetcher()

        self.solar_history: deque = deque(maxlen=720)       # 30 days hourly
        self.substrate_history: deque = deque(maxlen=720)
        self.detected_events: List[CrossSubstrateEvent] = []

        self.data_dir = data_dir
        self._collection_count = 0

        logger.info("Cross-Substrate Monitor initialized")
        logger.info(f"  Baseline period: {BASELINE_DAYS} days")
        logger.info(f"  Collection interval: {COLLECTION_INTERVAL_SECONDS}s")
        logger.info(f"  Flare threshold: M5.0 ({FLARE_THRESHOLD_FLUX} W/m^2)")

    def collect_snapshot(self) -> Dict[str, Any]:
        """
        Collect one synchronized snapshot of solar + substrate data.
        Call this hourly for 30 days to build baseline.
        """
        solar = self.solar_fetcher.fetch_current()
        substrate = self.substrate_fetcher.fetch_current()

        if solar is not None:
            self.solar_history.append(asdict(solar))

        self.substrate_history.append(asdict(substrate))
        self._collection_count += 1

        combined = {
            "collection_number": self._collection_count,
            "solar": asdict(solar) if solar else None,
            "substrate": asdict(substrate),
        }

        if self._collection_count % 24 == 0:
            logger.info(
                f"Cross-substrate: {self._collection_count} snapshots collected "
                f"({self._collection_count / 24:.0f} days)"
            )

        return combined

    def detect_solar_events(self) -> List[CrossSubstrateEvent]:
        """
        Scan solar history for significant events (flares, storms).
        """
        events = []

        for snapshot in self.solar_history:
            flux = snapshot.get("xray_flux", 0)
            kp = snapshot.get("kp_index", 0)
            ts = snapshot.get("timestamp", "")

            if flux >= FLARE_THRESHOLD_FLUX:
                events.append(CrossSubstrateEvent(
                    event_type="flare",
                    event_time=ts,
                    solar_magnitude=flux,
                ))

            if kp >= 5:
                events.append(CrossSubstrateEvent(
                    event_type="storm",
                    event_time=ts,
                    solar_magnitude=kp,
                ))

        return events

    def analyze_event_response(
        self,
        event_time_str: str,
        baseline_hours: int = 24,
        response_hours: int = 6,
    ) -> Dict[str, float]:
        """
        Measure substrate activity change around a solar event.

        Compares baseline (24h before) vs response window (6h after).
        Returns percent change per metric.
        """
        if pd is None:
            logger.warning("pandas required for event analysis")
            return {}

        if not self.substrate_history:
            return {}

        df = pd.DataFrame(list(self.substrate_history))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()

        event_time = pd.Timestamp(event_time_str)

        # Baseline window
        baseline_start = event_time - pd.Timedelta(hours=baseline_hours)
        baseline_end = event_time - pd.Timedelta(hours=1)
        baseline = df.loc[baseline_start:baseline_end]

        # Response window
        response_start = event_time
        response_end = event_time + pd.Timedelta(hours=response_hours)
        response = df.loc[response_start:response_end]

        if baseline.empty or response.empty:
            return {}

        metrics = [
            "fear_greed_index",
            "btc_liquidations_24h",
            "btc_volatility_1h",
        ]

        changes = {}
        for metric in metrics:
            if metric not in df.columns:
                continue
            baseline_mean = baseline[metric].mean()
            response_mean = response[metric].mean()

            if baseline_mean > 0:
                pct_change = (response_mean - baseline_mean) / baseline_mean * 100
            else:
                pct_change = 0.0

            changes[metric] = round(pct_change, 2)

        return changes

    def get_collection_summary(self) -> Dict[str, Any]:
        """Return summary of collected data."""
        solar_storms = sum(
            1 for s in self.solar_history if s.get("kp_index", 0) >= 5
        )
        solar_flares = sum(
            1 for s in self.solar_history
            if s.get("xray_flux", 0) >= FLARE_THRESHOLD_FLUX
        )

        return {
            "total_snapshots": self._collection_count,
            "days_collected": round(self._collection_count / 24, 1),
            "solar_storms_detected": solar_storms,
            "solar_flares_detected": solar_flares,
            "target_snapshots": BASELINE_DAYS * 24,
            "completion_pct": round(
                self._collection_count / (BASELINE_DAYS * 24) * 100, 1
            ),
        }


# ===========================================================================
# Statistical Analysis Engine
# ===========================================================================

class CrossSubstrateAnalyzer:
    """
    Statistical analysis of solar-substrate correlations.

    Methods:
      - Cross-correlation analysis
      - Granger causality test
      - Principal Component Analysis (unified system test)
      - Falsification check
    """

    def __init__(self):
        self.results: Dict[str, Any] = {}

    def cross_correlation(
        self,
        solar_series: np.ndarray,
        substrate_series: np.ndarray,
        max_lag: int = 24,
    ) -> Dict[str, float]:
        """
        Compute cross-correlation between solar and substrate time series.

        Uses normalized cross-correlation at each lag.
        Returns peak correlation and the lag (in hours) at which it occurs.
        """
        n = len(solar_series)
        if n < max_lag + 10:
            return {"peak_correlation": 0.0, "peak_lag_hours": 0, "significant": False}

        # Normalize (z-score)
        s_std = solar_series.std()
        b_std = substrate_series.std()
        if s_std < 1e-12 or b_std < 1e-12:
            return {"peak_correlation": 0.0, "peak_lag_hours": 0, "significant": False}

        s_norm = (solar_series - solar_series.mean()) / s_std
        b_norm = (substrate_series - substrate_series.mean()) / b_std

        correlations = []
        for lag in range(-max_lag, max_lag + 1):
            if lag >= 0:
                corr = np.mean(s_norm[:n - lag] * b_norm[lag:])
            else:
                corr = np.mean(s_norm[-lag:] * b_norm[:n + lag])
            correlations.append((lag, corr))

        # Find peak
        peak_lag, peak_corr = max(correlations, key=lambda x: abs(x[1]))

        # Rough significance test (|r| > 2/sqrt(n))
        threshold = 2.0 / math.sqrt(n)
        significant = abs(peak_corr) > threshold

        return {
            "peak_correlation": round(float(peak_corr), 4),
            "peak_lag_hours": int(peak_lag),
            "significant": significant,
            "threshold": round(threshold, 4),
        }

    def granger_causality(
        self,
        cause_series: np.ndarray,
        effect_series: np.ndarray,
        max_lag: int = 24,
    ) -> Dict[str, Any]:
        """
        Test if cause_series Granger-causes effect_series.

        Uses simple F-test comparing:
          Restricted model:  y_t = a0 + sum(a_i * y_{t-i})
          Unrestricted model: y_t = a0 + sum(a_i * y_{t-i}) + sum(b_j * x_{t-j})

        Returns p-value and best lag.
        """
        n = len(cause_series)
        if n < max_lag + 20:
            return {"min_p_value": 1.0, "best_lag": 0, "significant": False}

        try:
            from scipy import stats as scipy_stats
        except ImportError:
            logger.warning("scipy required for Granger causality test")
            return {"min_p_value": 1.0, "best_lag": 0, "significant": False}

        best_p = 1.0
        best_lag = 1

        for lag in range(1, min(max_lag + 1, n // 3)):
            # Build lagged matrices
            y = effect_series[lag:]
            n_obs = len(y)

            # Restricted: only own lags
            X_r = np.column_stack([
                effect_series[lag - i - 1: n - i - 1] for i in range(lag)
            ])
            X_r = np.column_stack([np.ones(n_obs), X_r])

            # Unrestricted: own lags + cause lags
            X_u = np.column_stack([
                X_r,
                *[cause_series[lag - i - 1: n - i - 1] for i in range(lag)]
            ])

            try:
                # Fit restricted
                beta_r = np.linalg.lstsq(X_r, y, rcond=None)[0]
                resid_r = y - X_r @ beta_r
                ssr_r = float(np.sum(resid_r ** 2))

                # Fit unrestricted
                beta_u = np.linalg.lstsq(X_u, y, rcond=None)[0]
                resid_u = y - X_u @ beta_u
                ssr_u = float(np.sum(resid_u ** 2))

                # F-test
                df1 = lag
                df2 = n_obs - X_u.shape[1]
                if df2 <= 0 or ssr_u <= 0:
                    continue

                f_stat = ((ssr_r - ssr_u) / df1) / (ssr_u / df2)
                p_value = float(1 - scipy_stats.f.cdf(f_stat, df1, df2))

                if p_value < best_p:
                    best_p = p_value
                    best_lag = lag

            except (np.linalg.LinAlgError, ValueError):
                continue

        return {
            "min_p_value": round(best_p, 6),
            "best_lag_hours": best_lag,
            "significant": best_p < 0.05,
        }

    def pca_unified_system_test(
        self,
        activity_matrix: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Test if substrate activities are driven by a single factor.

        If PC1 explains >90% of variance, suggests unified driving system.
        If PC1 explains <50%, activities are independent.
        """
        if activity_matrix.shape[0] < 10 or activity_matrix.shape[1] < 2:
            return {"pc1_variance": 0.0, "unified": False, "n_effective_dims": 0}

        # Standardize columns
        means = activity_matrix.mean(axis=0)
        stds = activity_matrix.std(axis=0)
        stds[stds < 1e-12] = 1.0
        standardized = (activity_matrix - means) / stds

        # SVD-based PCA
        try:
            _, s, _ = np.linalg.svd(standardized, full_matrices=False)
        except np.linalg.LinAlgError:
            return {"pc1_variance": 0.0, "unified": False, "n_effective_dims": 0}

        variance = s ** 2
        total_var = variance.sum()
        if total_var < 1e-12:
            return {"pc1_variance": 0.0, "unified": False, "n_effective_dims": 0}

        explained = variance / total_var
        pc1_var = float(explained[0])

        # Effective dimensionality (inverse participation ratio)
        n_eff = float(1.0 / (np.sum(explained ** 2) + 1e-12))

        # Cumulative variance for 95% threshold
        cumvar = np.cumsum(explained)
        dims_95 = int(np.argmax(cumvar >= 0.95)) + 1

        return {
            "pc1_variance": round(pc1_var, 4),
            "unified": pc1_var > 0.90,
            "n_effective_dims": round(n_eff, 1),
            "dims_for_95pct": dims_95,
            "explained_variance": [round(float(v), 4) for v in explained[:5]],
        }

    def check_falsification(
        self,
        cross_corr_results: List[Dict],
        pca_result: Dict,
        granger_results: List[Dict],
    ) -> Dict[str, Any]:
        """
        Clear falsification criteria for the cross-substrate hypothesis.

        Hypothesis FALSIFIED if:
          1. Average |correlation| < 0.3 across 3+ events
          2. Lag times have std_dev > 12 hours (random, no consistent response)
          3. PCA PC1 variance < 50% (independent systems)
          4. No Granger causality significant at p < 0.05
        """
        falsified = False
        reasons = []

        # Check correlations
        significant_corrs = [
            r for r in cross_corr_results if r.get("significant", False)
        ]
        if len(cross_corr_results) >= 3:
            avg_corr = np.mean([abs(r["peak_correlation"]) for r in cross_corr_results])
            if avg_corr < 0.3:
                falsified = True
                reasons.append(f"Average |correlation| = {avg_corr:.3f} < 0.3")

        # Check lag consistency
        if len(cross_corr_results) >= 3:
            lags = [r["peak_lag_hours"] for r in cross_corr_results]
            lag_std = float(np.std(lags))
            if lag_std > 12:
                falsified = True
                reasons.append(f"Lag std_dev = {lag_std:.1f}h > 12h (random)")

        # Check PCA
        pc1 = pca_result.get("pc1_variance", 0)
        if pc1 < 0.5:
            falsified = True
            reasons.append(f"PC1 variance = {pc1:.1%} < 50% (independent systems)")

        # Check Granger causality
        any_granger = any(g.get("significant", False) for g in granger_results)
        if not any_granger and len(granger_results) > 0:
            falsified = True
            reasons.append("No Granger causality significant at p < 0.05")

        return {
            "falsified": falsified,
            "reasons": reasons,
            "significant_correlations": len(significant_corrs),
            "total_events_analyzed": len(cross_corr_results),
            "conclusion": (
                "HYPOTHESIS FALSIFIED" if falsified
                else "HYPOTHESIS SURVIVES (continue testing)"
            ),
        }


# ===========================================================================
# ThoughtBus Integration
# ===========================================================================

def publish_solar_event_to_thoughtbus(event: CrossSubstrateEvent):
    """Publish detected solar event to Aureon ThoughtBus."""
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus, Thought
        bus = get_thought_bus()
        if bus is not None:
            # payload/meta are the real Thought fields — the old data=/confidence=
            # kwargs raised TypeError into the except below, so solar events had
            # never actually been published.
            bus.publish(Thought(
                source="cross_substrate_monitor",
                topic="solar.event.detected",
                payload={
                    "event_type": event.event_type,
                    "event_time": event.event_time,
                    "magnitude": event.solar_magnitude,
                    "percent_changes": event.percent_changes,
                },
                meta={"confidence": 0.7},
            ))
    except Exception:
        pass


# ===========================================================================
# Standalone execution
# ===========================================================================

def run_single_collection():
    """Run a single data collection cycle (for testing or cron)."""
    monitor = CrossSubstrateMonitor()
    snapshot = monitor.collect_snapshot()

    print("Cross-Substrate Snapshot:")
    print(json.dumps(snapshot, indent=2, default=str))

    summary = monitor.get_collection_summary()
    print(f"\nCollection Summary: {json.dumps(summary, indent=2)}")

    return snapshot


if __name__ == "__main__":
    run_single_collection()
