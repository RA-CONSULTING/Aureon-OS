import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Tuple

import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt

from aureon.analytics.lighthouse_metrics import LighthouseMetricsEngine


MAX_SOURCE_AGE_SECONDS = 3600.0
FUTURE_SKEW_SECONDS = 5.0


def _finite_positive(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _timestamp_seconds(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = None
    if number is not None and math.isfinite(number):
        if number > 100_000_000_000:
            number /= 1000.0
        return number if number > 0 else None
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _proven_receipt_meta(meta: Any) -> bool:
    return bool(
        isinstance(meta, Mapping)
        and meta.get("truth_status") == "real_observed"
        and meta.get("generated_values") is False
        and meta.get("eligible_for_analysis") is True
        and meta.get("source_ids")
        and meta.get("receipt_ids")
    )


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
        self.metrics_engine = LighthouseMetricsEngine(
            restoration_freq=self.RESTORATION_FREQ,
            distortion_freq=self.DISTORTION_FREQ,
        )

    def generate_market_data(self, n_points=1000, mode="mixed"):
        """Retired generated-data entry point retained for compatibility."""
        raise RuntimeError(
            "no_data: generated Lighthouse market series are retired; "
            "load a provider-observed log price series"
        )

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
        max_age_seconds: float = MAX_SOURCE_AGE_SECONDS,
        received_at: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray, dict]:
        """Load a regular series of fresh JSONL provider-price receipts."""
        if resample_seconds is not None:
            raise ValueError("no_data: interpolated/resampled prices are not accepted")
        now = time.time() if received_at is None else float(received_at)
        observations = []
        rejected_rows = 0
        with open(log_path, "r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    rejected_rows += 1
                    continue
                if not isinstance(row, Mapping):
                    rejected_rows += 1
                    continue
                asset_code = str(row.get("asset") or row.get("symbol") or "").strip().upper()
                if not asset_code or (asset and asset_code != asset.upper()):
                    continue
                if row.get("truth_status") != "real_observed" or row.get("generated_values") is not False:
                    rejected_rows += 1
                    continue
                source_id = str(row.get("source_id") or "").strip()
                receipt_id = str(row.get("receipt_id") or "").strip()
                source_timestamp = _timestamp_seconds(row.get("source_timestamp"))
                row_received_at = _timestamp_seconds(row.get("received_at"))
                price = _finite_positive(row.get("price"))
                if not source_id or not receipt_id or source_timestamp is None or row_received_at is None or price is None:
                    rejected_rows += 1
                    continue
                age = now - source_timestamp
                if age < -FUTURE_SKEW_SECONDS or age > max_age_seconds:
                    rejected_rows += 1
                    continue
                if row_received_at < source_timestamp - FUTURE_SKEW_SECONDS or row_received_at > now + FUTURE_SKEW_SECONDS:
                    rejected_rows += 1
                    continue
                observations.append(
                    (source_timestamp, price, asset_code, source_id, receipt_id)
                )

        observations.sort(key=lambda item: item[0])
        if limit is not None and limit > 0:
            observations = observations[-limit:]
        if len(observations) < 8:
            raise ValueError("no_data: at least eight fresh provider receipts are required")

        assets = {item[2] for item in observations}
        if len(assets) != 1:
            raise ValueError("no_data: a Lighthouse price series must contain exactly one asset")
        absolute_timestamps = np.array([item[0] for item in observations], dtype=float)
        if np.any(np.diff(absolute_timestamps) <= 0):
            raise ValueError("no_data: provider source timestamps must be strictly increasing")
        diffs = np.diff(absolute_timestamps)
        step = float(np.median(diffs))
        if step <= 0 or np.max(np.abs(diffs - step)) > step * 0.10:
            raise ValueError("no_data: provider observations are not regularly sampled")

        timestamps = absolute_timestamps - absolute_timestamps[0]
        prices = np.array([item[1] for item in observations], dtype=float)
        meta = {
            "asset": next(iter(assets)),
            "points": len(observations),
            "source": str(log_path),
            "step_seconds": step,
            "start_source_timestamp": float(absolute_timestamps[0]),
            "source_timestamp": float(absolute_timestamps[-1]),
            "received_at": now,
            "source_ids": sorted({item[3] for item in observations}),
            "receipt_ids": [item[4] for item in observations],
            "truth_status": "real_observed",
            "generated_values": False,
            "eligible_for_analysis": True,
            "eligible_for_action": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "rejected_rows": rejected_rows,
        }
        return timestamps, prices, meta

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
    parser.add_argument("--source", choices=["log"], default="log", help="Observed data source")
    parser.add_argument("--log-path", type=str, required=True, help="Path to provider-observed trading log")
    parser.add_argument("--asset", type=str, help="Asset symbol to filter within the log (default: all)")
    parser.add_argument("--resample", type=float, help="Resample step in seconds for log data")
    parser.add_argument("--limit", type=int, help="Limit number of log entries (latest N)")
    parser.add_argument("--delay", type=int, help="Custom delay for phase-space reconstruction")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analyzer = LighthouseFinancialAnalyzer()

    if args.source == "log":
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
