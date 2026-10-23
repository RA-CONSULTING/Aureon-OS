"""Bitcoin Lighthouse forensic analysis and forward projection.

This module provides a full pipeline:
1. Fetch hourly BTC market data (CoinGecko) with synthetic fallback.
2. Compute geometric "lighthouse" signatures over rolling windows.
3. Detect critical historical events and classify current regime.
4. Produce probabilistic forward projections via Monte Carlo simulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import requests
except ModuleNotFoundError:  # optional dependency
    requests = None


@dataclass
class LighthouseSignature:
    """Compact geometric state derived from a rolling return window."""

    curvature: float
    coherence: float
    dimension: float
    coordinates: np.ndarray
    velocity: np.ndarray


class LighthousePatternRecognition:
    """Lightweight geometric signature extraction model.

    The implementation uses delay embeddings + SVD-derived structure metrics.
    """

    def __init__(self, embedding_dim: int = 10, memory_length: int = 144):
        self.embedding_dim = embedding_dim
        self.memory_length = memory_length
        self.historical_signatures: List[LighthouseSignature] = []

    def _delay_embed(self, series: np.ndarray) -> np.ndarray:
        if len(series) < self.embedding_dim:
            pad = np.pad(series, (self.embedding_dim - len(series), 0), mode="edge")
            return pad.reshape(1, -1)

        rows = len(series) - self.embedding_dim + 1
        return np.vstack([series[i : i + self.embedding_dim] for i in range(rows)])

    @staticmethod
    def _safe_entropy(probabilities: np.ndarray) -> float:
        probs = probabilities[probabilities > 0]
        if len(probs) == 0:
            return 0.0
        return float(-(probs * np.log(probs)).sum())

    def extract_signature(self, window: np.ndarray, idx: int) -> LighthouseSignature:
        """Extract geometric signature from return window."""
        embed = self._delay_embed(window)
        centered = embed - embed.mean(axis=0, keepdims=True)

        try:
            _, singular_values, _ = np.linalg.svd(centered, full_matrices=False)
        except np.linalg.LinAlgError:
            singular_values = np.ones(min(centered.shape), dtype=float)

        variance = singular_values**2
        variance_ratio = variance / (variance.sum() + 1e-12)

        # Effective dimension from inverse participation ratio
        dimension = float(1.0 / (np.square(variance_ratio).sum() + 1e-12))

        # Curvature proxy: mean normalized second derivative magnitude
        if len(window) >= 3:
            second_diff = np.diff(window, n=2)
            curvature = float(np.mean(np.abs(second_diff)) / (np.std(window) + 1e-8))
        else:
            curvature = 0.0

        # Coherence proxy: low entropy / concentrated dynamics -> higher coherence
        hist_counts, _ = np.histogram(window, bins=20, density=True)
        probs = hist_counts / (hist_counts.sum() + 1e-12)
        entropy = self._safe_entropy(probs)
        max_entropy = np.log(20)
        coherence = float(np.clip(1 - entropy / (max_entropy + 1e-12), 0, 1))

        coordinates = centered[-1]
        if self.historical_signatures:
            prev = self.historical_signatures[-1].coordinates
            velocity = coordinates - prev
        else:
            velocity = np.zeros_like(coordinates)

        signature = LighthouseSignature(
            curvature=float(curvature),
            coherence=float(coherence),
            dimension=float(dimension),
            coordinates=coordinates,
            velocity=velocity,
        )
        self.historical_signatures.append(signature)
        return signature

    def predict_transition(self, signature: LighthouseSignature) -> Dict[str, float]:
        """Estimate transition probabilities from geometric features."""
        # logistic score: high curvature + low coherence + higher dimension => instability
        score = (
            1.6 * signature.curvature
            + 0.35 * signature.dimension
            + 1.5 * (1 - signature.coherence)
            - 2.2
        )
        transition_probability = float(1 / (1 + np.exp(-score)))

        if transition_probability >= 0.66:
            state = "critical"
        elif transition_probability >= 0.33:
            state = "elevated"
        else:
            state = "stable"

        return {
            "transition_probability": transition_probability,
            "risk_state": state,
        }


class BitcoinDataFetcher:
    """Fetch historical Bitcoin market data from CoinGecko."""

    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"

    def fetch_historical_data(self, days: int = 90) -> pd.DataFrame:
        endpoint = f"{self.base_url}/coins/bitcoin/market_chart"
        params = {"vs_currency": "usd", "days": days, "interval": "hourly"}

        if requests is None:
            print("requests not available.")
            if self._synthetic_allowed():
                print("AUREON_ALLOW_SYNTHETIC=1 — using tagged synthetic dataset.")
                return self._generate_synthetic_data(days)
            return self._empty_frame()

        try:
            response = requests.get(endpoint, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            prices = data.get("prices", [])
            volumes = data.get("total_volumes", [])
            market_caps = data.get("market_caps", [])

            min_len = min(len(prices), len(volumes), len(market_caps))
            if min_len == 0:
                raise ValueError("No market data returned from CoinGecko")

            df = pd.DataFrame(
                {
                    "timestamp": [prices[i][0] for i in range(min_len)],
                    "price": [prices[i][1] for i in range(min_len)],
                    "volume": [volumes[i][1] for i in range(min_len)],
                    "market_cap": [market_caps[i][1] for i in range(min_len)],
                }
            )
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df.set_index("datetime").sort_index()

        except Exception as exc:  # network/rate-limit fallback
            print(f"Error fetching data from CoinGecko: {exc}")
            binance_df = self._fetch_binance_hourly()
            if binance_df is not None and not binance_df.empty:
                print("Falling back to Binance public klines (BTCUSDT 1h).")
                return binance_df
            if self._synthetic_allowed():
                print("AUREON_ALLOW_SYNTHETIC=1 — using tagged synthetic dataset.")
                return self._generate_synthetic_data(days)
            return self._empty_frame()

    def _fetch_binance_hourly(self, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Real BTC hourly data from Binance public klines (no auth, throttled).

        Covers the most recent ``limit`` hours (~41 days at limit=1000, the
        API maximum). Returns None when unavailable or stale-only.
        """
        try:
            from analyzers import global_energy_data as ged
        except ImportError:  # standalone: run from inside analyzers/
            import global_energy_data as ged

        body = ged.fetch_binance_klines("BTCUSDT", interval="1h", limit=limit)
        if not body:
            return None
        try:
            df = pd.DataFrame(
                {
                    "timestamp": [float(k[0]) for k in body],
                    "price": [float(k[4]) for k in body],
                    "volume": [float(k[5]) for k in body],
                    "market_cap": [float("nan")] * len(body),
                }
            )
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df.set_index("datetime").sort_index()
        except (TypeError, ValueError, IndexError):
            return None

    def _generate_synthetic_data(self, days: int) -> pd.DataFrame:
        hours = days * 24
        timestamps = pd.date_range(end=datetime.now(), periods=hours, freq="h")

        rng = np.random.default_rng(42)
        price = [95000.0]
        drift = 0.0001

        for i in range(1, hours):
            if i % 500 == 0:
                drift = float(rng.choice([-0.001, 0.0005]))
            volatility = max(0.003, 0.015 * (1 + 0.3 * rng.standard_normal()))
            ret = drift + volatility * rng.standard_normal()
            price.append(max(1000.0, price[-1] * (1 + ret)))

        price_arr = np.array(price)
        df = pd.DataFrame(
            {
                "timestamp": timestamps.astype("int64") // 10**6,
                "price": price_arr,
                "volume": rng.uniform(20e9, 40e9, hours),
                "market_cap": price_arr * 19.5e6,
            },
            index=timestamps,
        )
        df.index.name = "datetime"
        df["provenance"] = "SYNTHETIC_OFFLINE_FALLBACK"
        return df

    @staticmethod
    def _synthetic_allowed() -> bool:
        # Synthetic data is opt-in only (data-freshness doctrine): it may never
        # silently enter the live pipeline. When disallowed the caller gets an
        # empty frame and the analysis skips — fail closed, no fake telemetry.
        return os.environ.get("AUREON_ALLOW_SYNTHETIC") == "1"

    def _empty_frame(self) -> pd.DataFrame:
        print("DATA FRESHINESS GATE: real market data unavailable and "
              "AUREON_ALLOW_SYNTHETIC is not set — failing closed (empty frame, "
              "no synthetic data entering the pipeline).")
        return pd.DataFrame()


class BitcoinLighthouseForensics:
    """Complete Lighthouse geometric analysis for Bitcoin."""

    def __init__(self, data: pd.DataFrame):
        self.data = data.copy()
        self.lighthouse = LighthousePatternRecognition(embedding_dim=10, memory_length=144)

        self.data["returns"] = np.log(self.data["price"] / self.data["price"].shift(1))
        self.data["volatility"] = self.data["returns"].rolling(24).std()

        self.signatures: List[Dict] = []
        self.predictions: List[Dict] = []
        self.sig_df: Optional[pd.DataFrame] = None
        self.pred_df: Optional[pd.DataFrame] = None

    def run_complete_analysis(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        print("🔍 LIGHTHOUSE FORENSIC ANALYSIS")
        print("=" * 60)

        returns = self.data["returns"].dropna().values
        index = self.data["returns"].dropna().index
        window_size = self.lighthouse.memory_length

        for i in range(window_size, len(returns)):
            window = returns[i - window_size : i]
            timestamp = index[i]

            signature = self.lighthouse.extract_signature(window, i)
            self.signatures.append(
                {
                    "timestamp": timestamp,
                    "curvature": signature.curvature,
                    "coherence": signature.coherence,
                    "dimension": signature.dimension,
                    "coordinates": signature.coordinates,
                    "velocity_norm": float(np.linalg.norm(signature.velocity)),
                }
            )

            prediction = self.lighthouse.predict_transition(signature)
            self.predictions.append({"timestamp": timestamp, **prediction})

        self.sig_df = pd.DataFrame(self.signatures)
        self.pred_df = pd.DataFrame(self.predictions)

        print(f"✓ Analyzed {len(self.signatures)} windows")
        print(f"✓ Generated {len(self.predictions)} predictions")

        return self.sig_df, self.pred_df

    def identify_critical_events(self) -> pd.DataFrame:
        if self.sig_df is None or self.sig_df.empty or "curvature" not in self.sig_df.columns:
            print("\n🚨 CRITICAL EVENTS DETECTED: 0 (insufficient data windows)")
            return pd.DataFrame()
        critical_threshold = self.sig_df["curvature"].quantile(0.95)
        critical_events = self.sig_df[self.sig_df["curvature"] > critical_threshold]

        print(f"\n🚨 CRITICAL EVENTS DETECTED: {len(critical_events)}")
        print("=" * 60)

        for _, event in critical_events.iterrows():
            timestamp = event["timestamp"]
            if timestamp not in self.data.index:
                continue

            price_at_event = float(self.data.loc[timestamp, "price"])
            pos = self.data.index.get_loc(timestamp)
            future_pos = pos + 24

            if future_pos < len(self.data):
                future_price = float(self.data.iloc[future_pos]["price"])
                pct_change = (future_price - price_at_event) / price_at_event * 100

                print(f"\n📍 {timestamp}")
                print(f"   Price: ${price_at_event:,.0f}")
                print(f"   Curvature: {event['curvature']:.4f}")
                print(f"   Coherence: {event['coherence']:.4f}")
                print(f"   24h later: {pct_change:+.2f}%")

        return critical_events

    def analyze_current_regime(self) -> str:
        if self.sig_df is None or self.sig_df.empty or "curvature" not in self.sig_df.columns:
            print("\n📊 CURRENT REGIME: UNDETERMINED (insufficient data windows)")
            return "UNDETERMINED"
        recent = self.sig_df.tail(24)
        avg_curvature = float(recent["curvature"].mean())
        avg_coherence = float(recent["coherence"].mean())
        trend_coherence = float(recent["coherence"].iloc[-1] - recent["coherence"].iloc[0])

        print("\n📊 CURRENT REGIME (Last 24h)")
        print("=" * 60)
        print(f"Average Curvature: {avg_curvature:.4f}")
        print(f"Average Coherence: {avg_coherence:.4f}")
        print(f"Coherence Trend: {trend_coherence:+.4f}")

        if avg_coherence > 0.7 and avg_curvature < 1.0:
            regime = "STABLE (High Coherence, Low Curvature)"
        elif avg_coherence > 0.7 and avg_curvature > 2.0:
            regime = "PRE-TRANSITION (High Coherence, High Curvature)"
        elif avg_coherence < 0.5 and avg_curvature > 2.0:
            regime = "CRITICAL (Low Coherence, High Curvature)"
        elif avg_coherence < 0.5 and avg_curvature < 1.0:
            regime = "CHAOTIC (Low Coherence, Low Curvature)"
        else:
            regime = "TRANSITIONAL"

        print(f"Regime Classification: {regime}")
        return regime

    def visualize_forensics(self) -> plt.Figure:
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(self.data.index, self.data["price"], "b-", linewidth=1, alpha=0.7)

        critical_threshold = self.sig_df["curvature"].quantile(0.95)
        critical = self.sig_df[self.sig_df["curvature"] > critical_threshold]
        for ts in critical["timestamp"]:
            if ts in self.data.index:
                price = self.data.loc[ts, "price"]
                ax1.axvline(ts, color="red", alpha=0.3, linewidth=2)
                ax1.scatter(ts, price, color="red", s=80, zorder=5)

        ax1.set_ylabel("BTC Price ($)", fontsize=12, fontweight="bold")
        ax1.set_title("Bitcoin Price with Critical Events (Red = High Curvature)", fontsize=14, fontweight="bold")
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(gs[1, 0])
        ax2.plot(self.sig_df["timestamp"], self.sig_df["curvature"], "r-", linewidth=1.5)
        ax2.axhline(2.0, color="orange", linestyle="--", label="Warning Threshold")
        ax2.set_ylabel("Curvature κ", fontsize=11, fontweight="bold")
        ax2.set_title("Phase Space Curvature", fontsize=12, fontweight="bold")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(self.sig_df["timestamp"], self.sig_df["coherence"], "g-", linewidth=1.5)
        ax3.axhline(0.7, color="green", linestyle="--", label="Safe Threshold")
        ax3.set_ylabel("Coherence Γ", fontsize=11, fontweight="bold")
        ax3.set_title("System Coherence", fontsize=12, fontweight="bold")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        ax4 = fig.add_subplot(gs[2, 0])
        ax4.plot(self.sig_df["timestamp"], self.sig_df["dimension"], "purple", linewidth=1.5)
        ax4.set_ylabel("Intrinsic Dimension", fontsize=11, fontweight="bold")
        ax4.set_title("Attractor Dimensionality", fontsize=12, fontweight="bold")
        ax4.grid(True, alpha=0.3)

        ax5 = fig.add_subplot(gs[2, 1])
        ax5.plot(self.pred_df["timestamp"], self.pred_df["transition_probability"], "orange", linewidth=1.5)
        ax5.axhline(0.66, color="red", linestyle="--", label="Critical")
        ax5.axhline(0.33, color="gold", linestyle="--", label="Elevated")
        ax5.set_ylabel("Transition Probability", fontsize=11, fontweight="bold")
        ax5.set_title("Phase Transition Forecast", fontsize=12, fontweight="bold")
        ax5.legend()
        ax5.grid(True, alpha=0.3)

        ax6 = fig.add_subplot(gs[3, :])
        scatter = ax6.scatter(
            self.sig_df["coherence"],
            self.sig_df["curvature"],
            c=np.arange(len(self.sig_df)),
            cmap="viridis",
            alpha=0.6,
            s=20,
        )
        ax6.axhline(2.0, color="red", linestyle="--", alpha=0.5)
        ax6.axvline(0.7, color="green", linestyle="--", alpha=0.5)
        ax6.set_xlabel("Coherence Γ", fontsize=11, fontweight="bold")
        ax6.set_ylabel("Curvature κ", fontsize=11, fontweight="bold")
        ax6.set_title("Phase Space Portrait (Color = Time →)", fontsize=12, fontweight="bold")
        ax6.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax6, label="Time Index")

        plt.suptitle("LIGHTHOUSE FORENSIC ANALYSIS - Bitcoin 3-Month Review", fontsize=16, fontweight="bold", y=0.995)
        return fig


class LighthouseForwardProjection:
    """Generate probabilistic forward projections from forensic signatures."""

    def __init__(self, forensics: BitcoinLighthouseForensics):
        if not forensics.lighthouse.historical_signatures:
            raise ValueError("Run forensic analysis before projection")

        self.forensics = forensics
        self.current_signature = forensics.lighthouse.historical_signatures[-1]
        self.current_price = float(forensics.data["price"].iloc[-1])

    def monte_carlo_projection(self, n_simulations: int = 10_000, horizon_hours: int = 168) -> Dict:
        print("\n🎲 MONTE CARLO FORWARD PROJECTION")
        print("=" * 60)
        print(f"Simulations: {n_simulations:,}")
        print(f"Horizon: {horizon_hours}h ({horizon_hours // 24} days)")
        print(f"Starting Price: ${self.current_price:,.2f}")

        curvature = self.current_signature.curvature
        coherence = self.current_signature.coherence
        velocity = float(np.linalg.norm(self.current_signature.velocity))

        print("\nCurrent Geometric State:")
        print(f"  Curvature: {curvature:.4f}")
        print(f"  Coherence: {coherence:.4f}")
        print(f"  Velocity: {velocity:.4f}")

        hist_vol = float(self.forensics.data["returns"].dropna().std() * np.sqrt(24 * 365))
        vol_multiplier = (1 + curvature) * (2 - coherence)
        adjusted_vol = max(0.01, hist_vol * vol_multiplier)

        print("\nVolatility Estimate:")
        print(f"  Historical: {hist_vol:.2%}")
        print(f"  Geometry-Adjusted: {adjusted_vol:.2%}")

        drift_estimate = velocity * 0.0001
        dt = 1 / (24 * 365)

        paths = np.zeros((n_simulations, horizon_hours), dtype=float)
        paths[:, 0] = self.current_price

        rng = np.random.default_rng(123)
        shocks = rng.standard_normal(size=(n_simulations, horizon_hours - 1)) * np.sqrt(dt)

        drift_term = (drift_estimate - 0.5 * adjusted_vol**2) * dt
        for t in range(1, horizon_hours):
            paths[:, t] = paths[:, t - 1] * np.exp(drift_term + adjusted_vol * shocks[:, t - 1])

        percentiles = {
            "p05": float(np.percentile(paths[:, -1], 5)),
            "p25": float(np.percentile(paths[:, -1], 25)),
            "p50": float(np.percentile(paths[:, -1], 50)),
            "p75": float(np.percentile(paths[:, -1], 75)),
            "p95": float(np.percentile(paths[:, -1], 95)),
        }

        print(f"\n📈 PRICE FORECAST ({horizon_hours // 24} days)")
        print("=" * 60)
        for pct, price in percentiles.items():
            change = (price - self.current_price) / self.current_price * 100
            print(f"{pct.upper()}: ${price:,.2f} ({change:+.2f}%)")

        prob_up_10 = float((paths[:, -1] > self.current_price * 1.10).mean())
        prob_down_10 = float((paths[:, -1] < self.current_price * 0.90).mean())
        prob_up_20 = float((paths[:, -1] > self.current_price * 1.20).mean())
        prob_down_20 = float((paths[:, -1] < self.current_price * 0.80).mean())

        print("\n🎯 EVENT PROBABILITIES")
        print("=" * 60)
        print(f"+10%: {prob_up_10:.1%}")
        print(f"-10%: {prob_down_10:.1%}")
        print(f"+20%: {prob_up_20:.1%}")
        print(f"-20%: {prob_down_20:.1%}")

        return {
            "paths": paths,
            "percentiles": percentiles,
            "probabilities": {
                "up_10pct": prob_up_10,
                "down_10pct": prob_down_10,
                "up_20pct": prob_up_20,
                "down_20pct": prob_down_20,
            },
            "parameters": {
                "drift": float(drift_estimate),
                "volatility": float(adjusted_vol),
                "curvature": float(curvature),
                "coherence": float(coherence),
            },
        }

    def visualize_projection(self, projection_results: Dict) -> plt.Figure:
        paths = projection_results["paths"]
        percentiles = projection_results["percentiles"]

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        ax1, ax2, ax3, ax4 = axes.flatten()

        n_display = min(1000, len(paths))
        time_axis = np.arange(paths.shape[1])
        for i in range(n_display):
            ax1.plot(time_axis, paths[i], alpha=0.01, color="blue")

        p50_path = np.median(paths, axis=0)
        p05_path = np.percentile(paths, 5, axis=0)
        p95_path = np.percentile(paths, 95, axis=0)
        ax1.plot(time_axis, p50_path, "r-", linewidth=2, label="Median")
        ax1.fill_between(time_axis, p05_path, p95_path, alpha=0.3, color="orange", label="90% CI")
        ax1.set_xlabel("Hours Ahead")
        ax1.set_ylabel("BTC Price ($)")
        ax1.set_title("Monte Carlo Price Paths", fontweight="bold")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        final_prices = paths[:, -1]
        ax2.hist(final_prices, bins=80, density=True, alpha=0.7, color="skyblue", edgecolor="black")
        for pct_name, pct_value in percentiles.items():
            ax2.axvline(pct_value, color="red", linestyle="--", alpha=0.7)
            ax2.text(pct_value, ax2.get_ylim()[1] * 0.85, pct_name.upper(), rotation=90, fontsize=8)
        ax2.set_xlabel("Final Price ($)")
        ax2.set_ylabel("Probability Density")
        ax2.set_title("Price Distribution (End of Horizon)", fontweight="bold")
        ax2.grid(True, alpha=0.3)

        returns = (final_prices / self.current_price - 1) * 100
        ax3.hist(returns, bins=80, density=True, alpha=0.7, color="lightgreen", edgecolor="black")
        ax3.axvline(0, color="black", linestyle="-", linewidth=2)
        ax3.set_xlabel("Return (%)")
        ax3.set_ylabel("Probability Density")
        ax3.set_title("Return Distribution", fontweight="bold")
        ax3.grid(True, alpha=0.3)

        sorted_returns = np.sort(returns)
        cumulative = np.arange(1, len(sorted_returns) + 1) / len(sorted_returns)
        ax4.plot(sorted_returns, cumulative, linewidth=2)
        ax4.axvline(0, color="black", linestyle="--")
        ax4.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
        ax4.set_xlabel("Return (%)")
        ax4.set_ylabel("Cumulative Probability")
        ax4.set_title("Cumulative Distribution Function", fontweight="bold")
        ax4.grid(True, alpha=0.3)

        plt.suptitle("LIGHTHOUSE FORWARD PROJECTION - Probabilistic Forecast", fontsize=16, fontweight="bold")
        plt.tight_layout()
        return fig


def run_analysis(days: int = 90, simulations: int = 5_000, horizon_hours: int = 168) -> Dict:
    """Headless, plot-free Lighthouse pipeline summary for the battle-view.

    Uses the same real CoinGecko data path as run_complete_lighthouse_analysis
    (synthetic remains opt-in via AUREON_ALLOW_SYNTHETIC, tagged). Returns a
    JSON-safe dict; fail-closed (ok=False, fields=None) when no real data.
    """
    import time as _time

    fetcher = BitcoinDataFetcher()
    df = fetcher.fetch_historical_data(days=days)
    if df is None or df.empty:
        return {
            "ok": False,
            "ts": _time.time(),
            "regime": None,
            "current_price": None,
            "signature": None,
            "critical_events": None,
            "projection": None,
            "error": "no_real_market_data",
        }

    forensics = BitcoinLighthouseForensics(df)
    forensics.run_complete_analysis()
    critical_events = forensics.identify_critical_events()
    regime = forensics.analyze_current_regime()

    projector = LighthouseForwardProjection(forensics)
    projection = projector.monte_carlo_projection(
        n_simulations=simulations, horizon_hours=horizon_hours
    )

    current_sig = forensics.lighthouse.historical_signatures[-1]
    return {
        "ok": True,
        "ts": _time.time(),
        "data_points": int(len(df)),
        "date_range": [str(df.index[0]), str(df.index[-1])],
        "regime": regime,
        "current_price": float(forensics.data["price"].iloc[-1]),
        "signature": {
            "curvature": float(current_sig.curvature),
            "coherence": float(current_sig.coherence),
            "dimension": float(current_sig.dimension),
            "velocity_norm": float(np.linalg.norm(current_sig.velocity)),
        },
        "critical_events": int(len(critical_events)),
        "projection": {
            "horizon_hours": horizon_hours,
            "percentiles": projection["percentiles"],
            "probabilities": projection["probabilities"],
            "parameters": projection["parameters"],
        },
        "error": None,
    }


def run_complete_lighthouse_analysis(
    days: int = 90,
    simulations: int = 10_000,
    horizon_hours: int = 168,
    show_plots: bool = False,
    save_prefix: str = "bitcoin_lighthouse",
):
    """Execute full pipeline: data -> forensics -> projection."""
    print("\n" + "=" * 60)
    print("BITCOIN LIGHTHOUSE ANALYSIS - COMPLETE PIPELINE")
    print("=" * 60)

    print("\n[1/4] Fetching Bitcoin data...")
    fetcher = BitcoinDataFetcher()
    df = fetcher.fetch_historical_data(days=days)
    if df.empty:
        print("✗ No real market data available and synthetic fallback is gated "
              "(AUREON_ALLOW_SYNTHETIC not set). Skipping analysis — no synthetic "
              "data will enter the pipeline.")
        return None, None
    print(f"✓ Retrieved {len(df)} hourly observations")
    print(f"  Date range: {df.index[0]} to {df.index[-1]}")
    print(f"  Price range: ${df['price'].min():,.0f} - ${df['price'].max():,.0f}")

    print("\n[2/4] Running geometric forensics...")
    forensics = BitcoinLighthouseForensics(df)
    forensics.run_complete_analysis()

    print("\n[3/4] Identifying critical events...")
    critical_events = forensics.identify_critical_events()
    regime = forensics.analyze_current_regime()

    print("\n[4/4] Generating forward projections...")
    projector = LighthouseForwardProjection(forensics)
    projection = projector.monte_carlo_projection(
        n_simulations=simulations,
        horizon_hours=horizon_hours,
    )

    print("\n📊 Generating visualizations...")
    fig1 = forensics.visualize_forensics()
    fig2 = projector.visualize_projection(projection)

    forensic_path = f"{save_prefix}_forensics.png"
    projection_path = f"{save_prefix}_projection.png"
    fig1.savefig(forensic_path, dpi=150)
    fig2.savefig(projection_path, dpi=150)
    print(f"Saved: {forensic_path}")
    print(f"Saved: {projection_path}")

    if show_plots:
        plt.show()
    else:
        plt.close(fig1)
        plt.close(fig2)

    return {
        "forensics": forensics,
        "projector": projector,
        "projection": projection,
        "critical_events": critical_events,
        "regime": regime,
        "artifacts": [forensic_path, projection_path],
    }


if __name__ == "__main__":
    run_complete_lighthouse_analysis()
