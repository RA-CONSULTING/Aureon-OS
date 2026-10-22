from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt

from aureon.analytics.lighthouse_metrics import LighthouseMetricsEngine


class LighthouseFinancialAnalyzer:
    """Visual toolkit for exploring the Lighthouse Protocol metaphors."""

    def __init__(self, random_state=None):
        """
        Initializes the Lighthouse Protocol Analyzer.
        CONSTANTS based on 'Harmonic Reality Framework':
        - RESTORATION_FREQ: 528 Hz (The 'Love' Signal - Signal of Truth)
        - DISTORTION_FREQ: 440 Hz (The 'Mars' Distortion - Signal of Ego)
        - INTERFERENCE_RATIO: 0.833 (Threshold for Dissonance)
        """
        self.RESTORATION_FREQ = 528
        self.DISTORTION_FREQ = 440
        self.INTERFERENCE_RATIO = self.DISTORTION_FREQ / self.RESTORATION_FREQ
        self.cmap = plt.get_cmap("turbo")
        self.rng = np.random.default_rng(random_state)
        self.metrics_engine = LighthouseMetricsEngine(
            restoration_freq=self.RESTORATION_FREQ,
            distortion_freq=self.DISTORTION_FREQ,
        )

    def generate_market_data(self, n_points=1000, mode="mixed"):
        """
        Simulates a 'Financial Ego System' time series.
        Generates a signal that transitions from:
        1. Lighthouse State (Stable, Harmonic)
        2. Ego State (Chaotic, High-Frequency Noise)
        """
        t = np.linspace(0, 10, n_points)

        if mode == "stable":
            signal = np.sin(2 * np.pi * 1.0 * t) * 100 + 200
        elif mode == "chaos":
            r = 3.9
            x = np.empty(n_points)
            x[0] = 0.5
            for i in range(1, n_points):
                x[i] = r * x[i - 1] * (1 - x[i - 1])
            signal = x * 100 + 150
        else:
            carrier = np.linspace(200, 400, n_points)
            harmony = np.sin(2 * np.pi * 0.5 * t) * 20
            noise_amp = np.linspace(0, 50, n_points) * self.rng.normal(0, 1, n_points)
            signal = carrier + harmony + noise_amp

        return t, signal

    def phase_space_reconstruction(self, data, delay=10):
        """TOOL I: PHASE SPACE RECONSTRUCTION."""
        if delay <= 0 or delay >= len(data):
            raise ValueError("delay must be > 0 and less than data length")
        x = data[:-delay]
        y = data[delay:]
        return x, y

    def bifurcation_map(self, r_min=2.5, r_max=4.0, n_points=1000, transient=900):
        """TOOL II: BIFURCATION DIAGRAM."""
        r_values = np.linspace(r_min, r_max, n_points)
        x = np.full(n_points, 0.5)
        bifurcation_data = []

        for i in range(transient + 100):
            x = r_values * x * (1 - x)
            if i >= transient:
                bifurcation_data.append(x.copy())

        return r_values, np.array(bifurcation_data)

    def load_log_price_series(
        self,
        log_path: Path,
        asset: Optional[str] = None,
        resample_seconds: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray, dict]:
        pattern = re.compile(
            r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(?P<msec>\d+) .*?Kelly Calc: (?P<asset>[A-Z0-9]+).*?Price: \$(?P<price>[0-9.]+)"
        )
        timestamps = []
        prices = []
        assets = []

        with open(log_path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                match = pattern.search(line)
                if not match:
                    continue
                asset_code = match.group("asset")
                if asset and asset_code != asset:
                    continue
                ts_raw = f"{match.group('ts')}.{match.group('msec')}"
                try:
                    ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    continue
                price = float(match.group("price"))
                timestamps.append(ts)
                prices.append(price)
                assets.append(asset_code)

        if not timestamps:
            raise ValueError("No matching price entries found in log.")

        if limit is not None and limit > 0:
            timestamps = timestamps[-limit:]
            prices = prices[-limit:]
            assets = assets[-limit:]

        unix_seconds = np.array([(ts - timestamps[0]).total_seconds() for ts in timestamps])
        sorted_idx = np.argsort(unix_seconds)
        unix_seconds = unix_seconds[sorted_idx]
        prices = np.array(prices)[sorted_idx]
        assets = np.array(assets)[sorted_idx]

        unique_mask = np.concatenate(([True], np.diff(unix_seconds) > 0))
        unix_seconds = unix_seconds[unique_mask]
        prices = prices[unique_mask]
        assets = assets[unique_mask]

        if len(unix_seconds) < 3:
            raise ValueError("Not enough data points after filtering to construct a series.")

        diffs = np.diff(unix_seconds)
        positive_diffs = diffs[diffs > 0]
        if positive_diffs.size == 0:
            raise ValueError("Timestamps are not strictly increasing; cannot compute sampling rate.")

        step = resample_seconds or float(np.median(positive_diffs))
        if step <= 0:
            step = float(np.mean(positive_diffs))
        if step <= 0:
            step = 1.0

        target_grid = np.arange(0, unix_seconds[-1] + step, step)
        resampled_prices = np.interp(target_grid, unix_seconds, prices)

        meta = {
            "asset": asset if asset else "MULTI",
            "points": len(resampled_prices),
            "source": str(log_path),
            "step_seconds": step,
            "start": timestamps[0].isoformat(),
            "end": timestamps[-1].isoformat(),
        }

        return target_grid, resampled_prices, meta

    def run_dashboard(
        self,
        mode: str = "mixed",
        price_data: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
        source_label: str = "Synthetic",
        phase_delay: Optional[int] = None,
    ):
        """Generates the Visual Dashboard combining all 3 tools."""
        if price_data is None:
            timestamps, price_data = self.generate_market_data(mode=mode)
            source_label = f"Synthetic ({mode})"
        else:
            if timestamps is None:
                timestamps = np.arange(len(price_data))

        price_data = np.asarray(price_data)
        timestamps = np.asarray(timestamps)

        if phase_delay is None:
            inferred_delay = max(1, int(len(price_data) * 0.03))
            phase_delay = min(inferred_delay, max(len(price_data) // 4, 1))
        phase_delay = max(1, min(phase_delay, len(price_data) - 1))

        metrics = self.metrics_engine.analyze_series(timestamps, price_data)
        freqs = metrics["freqs"]
        psd = metrics["psd"]
        sampling_rate = metrics["sampling_rate"]
        coherence_score = metrics["coherence_score"]
        gamma_ratio = metrics["gamma_ratio"]
        distortion_ratio = metrics["distortion_index"]
        maker_bias = metrics["maker_bias"]
        emotion = metrics["emotion"]
        emotion_color = metrics["emotion_color"]

        fig = plt.figure(figsize=(15, 10))
        fig.suptitle(
            f"LIGHTHOUSE PROTOCOL: FINANCIAL EGO SYSTEM MAP\nSource: {source_label}",
            fontsize=16,
            fontweight="bold",
        )
        gs = gridspec.GridSpec(2, 2, height_ratios=[1, 1])

        ax1 = fig.add_subplot(gs[0, 0])
        x_lag, y_lag = self.phase_space_reconstruction(price_data, delay=phase_delay)
        colors = self.cmap(np.linspace(0, 1, len(x_lag))) if len(x_lag) else "grey"
        ax1.scatter(x_lag, y_lag, s=1, c=colors, alpha=0.6)
        ax1.set_title("1. PHASE SPACE (Attractor Geometry)")
        ax1.set_xlabel("Value (t)")
        ax1.set_ylabel(f"Value (t + {phase_delay})")
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(gs[0, 1])
        r_vals, bif_data = self.bifurcation_map()
        r_grid = np.repeat(r_vals[np.newaxis, :], bif_data.shape[0], axis=0)
        ax2.scatter(r_grid.flatten(), bif_data.flatten(), s=0.1, color="black", alpha=0.4)
        chaos_onset = 3.56995
        threshold_r = r_vals[0] + (r_vals[-1] - r_vals[0]) * self.INTERFERENCE_RATIO
        ax2.axvline(x=chaos_onset, color="red", linestyle="--", label="Chaos Onset")
        ax2.axvline(x=threshold_r, color="purple", linestyle=":", label="Interference Ratio")
        ax2.text(chaos_onset + 0.01, 0.1, "EGO COLLAPSE", color="red", rotation=90, va="bottom")
        ax2.set_title("2. BIFURCATION (Stability Horizon)")
        ax2.set_xlabel("Market Hype Parameter (r)")
        ax2.set_ylabel("Equilibrium Price")
        ax2.legend(loc="upper left")

        ax3 = fig.add_subplot(gs[1, :])
        psd_norm = 10 * np.log10(psd + 1e-10)
        ax3.plot(freqs, psd_norm, color="black", lw=1)
        ax3.fill_between(freqs, psd_norm, color="skyblue", alpha=0.3)

        nyquist = sampling_rate / 2.0
        ax3.axvspan(0, 0.1 * nyquist, color="green", alpha=0.2, label="Lighthouse Low Band")
        distortion_center = self.INTERFERENCE_RATIO * nyquist
        distortion_half_width = 0.08 * nyquist
        ax3.axvspan(
            max(distortion_center - distortion_half_width, 0),
            min(distortion_center + distortion_half_width, nyquist),
            color="red",
            alpha=0.15,
            label="Distortion Band",
        )
        ax3.axvspan(0.6 * nyquist, nyquist, color="purple", alpha=0.1, label="Gamma Surge")

        ax3.text(0.02, 0.9, f"COHERENCE SCORE: {coherence_score:.2f}", transform=ax3.transAxes, fontsize=12, fontweight="bold")
        ax3.text(0.02, 0.83, f"CURRENT STATE: {emotion}", transform=ax3.transAxes, fontsize=13, color=emotion_color, fontweight="bold")
        ax3.text(0.35, 0.9, f"GAMMA RATIO: {gamma_ratio:.2f}", transform=ax3.transAxes, fontsize=12, color="purple", fontweight="bold")
        ax3.text(0.35, 0.83, f"MAKER BIAS: {maker_bias:.2f}", transform=ax3.transAxes, fontsize=12, color="black")
        ax3.text(0.65, 0.83, f"DISTORTION INDEX: {distortion_ratio:.2f}", transform=ax3.transAxes, fontsize=12, color="red")

        ax3.set_title("3. SPECTRAL ANALYSIS (Signal vs Noise)")
        ax3.set_xlabel("Frequency (Hz)")
        ax3.set_ylabel("Power Density (dB)")
        ax3.legend(loc="upper right")

        plt.tight_layout()
        plt.show()

        print("\n--- Lighthouse Metrics ---")
        print(f"Source: {source_label}")
        print(f"Sampling Rate (Hz): {sampling_rate:.3f}")
        print(f"Coherence Score: {coherence_score:.3f}")
        print(f"Gamma Power Ratio: {gamma_ratio:.3f}")
        print(f"Maker Bias: {maker_bias:.3f}")
        print(f"Distortion Index: {distortion_ratio:.3f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lighthouse Protocol Financial Analyzer")
    parser.add_argument("--source", choices=["synthetic", "log"], default="synthetic", help="Data source to drive the dashboard")
    parser.add_argument("--mode", choices=["mixed", "stable", "chaos"], default="mixed", help="Synthetic data regime when --source=synthetic")
    parser.add_argument("--log-path", type=str, help="Path to trading log file when --source=log")
    parser.add_argument("--asset", type=str, help="Asset symbol to filter within the log (default: all)")
    parser.add_argument("--resample", type=float, help="Resample step in seconds for log data")
    parser.add_argument("--limit", type=int, help="Limit number of log entries (latest N)")
    parser.add_argument("--delay", type=int, help="Custom delay for phase-space reconstruction")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for synthetic noise generation")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analyzer = LighthouseFinancialAnalyzer(random_state=args.seed)

    if args.source == "log":
        if not args.log_path:
            raise SystemExit("--log-path is required when --source=log")
        grid, prices, meta = analyzer.load_log_price_series(
            Path(args.log_path),
            asset=args.asset,
            resample_seconds=args.resample,
            limit=args.limit,
        )
        label = f"Log {meta['asset']} ({Path(args.log_path).name})"
        analyzer.run_dashboard(
            price_data=prices,
            timestamps=grid,
            source_label=label,
            phase_delay=args.delay,
        )
    else:
        analyzer.run_dashboard(mode=args.mode, phase_delay=args.delay)
