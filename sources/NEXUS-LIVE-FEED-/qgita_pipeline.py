import numpy as np
import scipy.signal as sps
import scipy.interpolate as interp
import matplotlib.pyplot as plt
from sklearn.preprocessing import QuantileTransformer
from sklearn.cluster import DBSCAN

try:
    from joblib import Parallel, delayed  # noqa: F401
except ImportError:  # pragma: no cover
    Parallel = None  # type: ignore
    delayed = None  # type: ignore

phi = (1 + 5 ** 0.5) / 2.0
phi_inv = 1.0 / phi

FS = 200.0
T = 60.0
alpha = 1.0
epsilon = 0.04
theta_kappa = 10.0
segma_eps = 0.5
link_window = 0.2
lighthouse_thresh_sigma = 2.0
weights = np.array([1.0, 1.0, 1.0, 1.0, 1.0])


def make_synthetic_signal(num_channels=8, duration=T, fs=FS, event_t=21.0, seed=42):
    t = np.arange(0, duration, 1.0 / fs)
    rng = np.random.RandomState(seed)
    signal = rng.normal(scale=0.8, size=(num_channels, t.size))
    for channel in range(num_channels):
        signal[channel] += 0.3 * np.sin(2 * np.pi * (1.0 + 0.2 * channel) * t)
    idx = t >= event_t
    for channel in range(num_channels):
        signal[channel, idx] += 1.5 * np.sin(2 * np.pi * 3.0 * t[idx] + channel * 0.1)
        signal[channel, idx] += 0.2 * rng.normal(scale=0.3, size=idx.sum())
    center_idx = np.argmin(np.abs(t - event_t))
    for channel in range(num_channels):
        signal[channel, center_idx:center_idx + 5] += np.linspace(0, 3.0, 5)
    return t, signal


def fibonacci_sequence_up_to(n):
    sequence = [0, 1]
    while sequence[-1] < n:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence


def construct_local_fib_knots(center_t, base_dt, max_f=20, anchor_t0=0.0):
    sequence = fibonacci_sequence_up_to(max_f)
    taus = anchor_t0 + base_dt * np.array(sequence)
    idx = np.searchsorted(taus, center_t)
    if idx < 2 or idx + 1 >= len(taus):
        return None
    return taus[idx - 2:idx + 2]


def interp_signal(times, values):
    return interp.interp1d(times, values, kind="cubic", fill_value="extrapolate")


def curvature_nonuniform(x_minus, x0, x_plus, dt1, dt2):
    return (x_plus - 2 * x0 + x_minus) / (dt1 * dt2 + 1e-15)


def detect_ftcps(times, values, base_dt=1.0, tolerance=epsilon, threshold=theta_kappa):
    fib_sequence = fibonacci_sequence_up_to(int(np.ceil(times[-1] / base_dt) + 10))
    taus = base_dt * np.array(fib_sequence)
    taus = taus[(taus >= times[0]) & (taus <= times[-1])]
    interpolator = interp_signal(times, values)
    candidates = []
    for i in range(2, len(taus) - 1):
        tau_minus, tau_center, tau_plus = taus[i - 2], taus[i - 1], taus[i]
        dt1 = tau_center - tau_minus
        dt2 = tau_plus - tau_center
        ratio = dt2 / dt1
        if abs(ratio - phi_inv) > tolerance:
            continue
        x_minus = float(interpolator(tau_minus))
        x0 = float(interpolator(tau_center))
        x_plus = float(interpolator(tau_plus))
        kappa = curvature_nonuniform(x_minus, x0, x_plus, dt1, dt2)
        if abs(kappa) <= threshold:
            continue
        local_contrast = abs(x0 - x_minus) / 2.0
        fib_match = max(0.0, 1.0 - abs(ratio - phi_inv) / tolerance)
        g_eff = alpha * abs(kappa) * fib_match * local_contrast
        candidates.append({"t": tau_center, "kappa": kappa, "r": ratio, "G": g_eff})
    return candidates


def segma_cluster(candidates, eps_seconds=segma_eps):
    if not candidates:
        return []
    times = np.array([candidate["t"] for candidate in candidates]).reshape(-1, 1)
    clustering = DBSCAN(eps=eps_seconds, min_samples=1, metric="euclidean").fit(times)
    clusters = []
    for label in np.unique(clustering.labels_):
        idxs = np.where(clustering.labels_ == label)[0]
        best = max((candidates[idx] for idx in idxs), key=lambda candidate: candidate["G"])
        clusters.append(best)
    return sorted(clusters, key=lambda candidate: candidate["t"])


def linear_coherence(signal, fs=FS, window_sec=2.0):
    channels, samples = signal.shape
    window = int(window_sec * fs)
    step = max(1, window // 4)
    times = []
    coherence_values = []
    for start in range(0, samples - window + 1, step):
        window_slice = signal[:, start:start + window]
        pairwise = []
        for i in range(channels):
            for j in range(i + 1, channels):
                _, coherence_spectrum = sps.coherence(
                    window_slice[i], window_slice[j], fs=fs, nperseg=window // 2
                )
                pairwise.append(np.nanmean(coherence_spectrum))
        coherence_values.append(np.mean(pairwise) if pairwise else 0.0)
        times.append((start + window / 2) / fs)
    return np.array(times), np.array(coherence_values)


def phi_cross_scale_coherence(signal_channel, times, fs=FS, ratio=phi):
    scaled_times = times * ratio
    interpolator = interp_signal(times, signal_channel)
    t_min = max(times[0], scaled_times[0])
    t_max = min(times[-1], scaled_times[-1])
    mask = (times >= t_min) & (times <= t_max)
    if mask.sum() < 10:
        return np.zeros_like(times)
    x1 = signal_channel[mask]
    x2 = interpolator(scaled_times[mask])
    window = int(2.0 * fs)
    length = len(x1)
    correlation = np.zeros(length)
    for i in range(0, length - window + 1):
        segment_a = x1[i:i + window]
        segment_b = x2[i:i + window]
        if np.std(segment_a) < 1e-6 or np.std(segment_b) < 1e-6:
            correlation[i + window // 2] = 0.0
        else:
            correlation[i + window // 2] = np.corrcoef(segment_a, segment_b)[0, 1]
    result = np.zeros_like(times)
    mask_idx = np.where(mask)[0]
    result[mask_idx[:len(correlation)]] = correlation
    return result


def nonlinear_coherence(signal, fs=FS, window_sec=2.0):
    channels, samples = signal.shape
    window = int(window_sec * fs)
    step = max(1, window // 4)
    times = []
    mi_values = []
    bins = 32
    for start in range(0, samples - window + 1, step):
        window_slice = signal[:, start:start + window]
        metrics = []
        for i in range(channels):
            for j in range(i + 1, channels):
                x = window_slice[i]
                y = window_slice[j]
                hist, _, _ = np.histogram2d(x, y, bins=bins)
                p_xy = hist / (np.sum(hist) + 1e-12)
                p_x = p_xy.sum(axis=1)
                p_y = p_xy.sum(axis=0)
                mask = p_xy > 0
                mi = np.sum(
                    p_xy[mask]
                    * np.log(p_xy[mask] / (p_x[:, None][mask] * p_y[None, :][mask] + 1e-15) + 1e-15)
                )
                metrics.append(mi)
        mi_values.append(np.mean(metrics) if metrics else 0.0)
        times.append((start + window / 2) / fs)
    return np.array(times), np.array(mi_values)


def anomaly_pointer_q(signal_channel, times, fs=FS):
    size = len(times)
    window = int(1.0 * fs)
    prediction_error = np.zeros(size)
    for idx in range(window, size - 2):
        prediction_error[idx] = abs(signal_channel[idx] - signal_channel[idx - 1])
    b, a = sps.butter(2, 0.5 / (fs / 2), btype="high")
    high_pass = sps.filtfilt(b, a, prediction_error + 1e-12)
    return np.abs(high_pass)


def robust_norm(array):
    transformer = QuantileTransformer(n_quantiles=200, output_distribution="uniform")
    reshaped = array.reshape(-1, 1)
    try:
        scaled = transformer.fit_transform(reshaped).flatten()
    except Exception:
        scaled = (array - np.nanmin(array)) / (np.nanmax(array) - np.nanmin(array) + 1e-12)
    return scaled


def compute_lighthouse_metrics(times, signal, ftcp_candidates, metric_weights=weights):
    channels = signal.shape[0]
    times_lin, coherence_lin = linear_coherence(signal)
    times_nonlin, coherence_nonlin = nonlinear_coherence(signal)
    coherence_lin_full = np.interp(times, times_lin, coherence_lin, left=0.0, right=0.0)
    coherence_nonlin_full = np.interp(times, times_nonlin, coherence_nonlin, left=0.0, right=0.0)
    phi_coherence = []
    for channel in range(channels):
        phi_coherence.append(phi_cross_scale_coherence(signal[channel], times))
    phi_coherence_full = np.nanmean(np.vstack(phi_coherence), axis=0)
    g_series = np.zeros_like(times)
    for candidate in ftcp_candidates:
        idx = np.argmin(np.abs(times - candidate["t"]))
        g_series[idx] = candidate["G"]
    kernel = sps.gaussian(51, std=7)
    g_eff_full = sps.convolve(g_series, kernel / kernel.sum(), mode="same") if np.any(g_series) else g_series
    q_full = anomaly_pointer_q(signal[0], times)
    metric_arrays = [
        robust_norm(np.nan_to_num(coherence_lin_full)),
        robust_norm(np.nan_to_num(coherence_nonlin_full)),
        robust_norm(np.nan_to_num(np.abs(phi_coherence_full))),
        robust_norm(np.nan_to_num(g_eff_full)),
        robust_norm(np.nan_to_num(q_full)),
    ]
    eps_small = 1e-6
    stacked = np.vstack([metric + eps_small for metric in metric_arrays])
    numerator = np.prod(stacked ** metric_weights.reshape(-1, 1), axis=0)
    lighthouse = numerator ** (1.0 / np.sum(metric_weights))
    return {
        "t": times,
        "C_lin": metric_arrays[0],
        "C_nonlin": metric_arrays[1],
        "C_phi": metric_arrays[2],
        "G_eff": metric_arrays[3],
        "Q": metric_arrays[4],
        "L": lighthouse,
    }


def detect_lhes(lighthouse, times, segma_candidates, k_sigma=lighthouse_thresh_sigma, window=link_window):
    mean = np.nanmean(lighthouse)
    std = np.nanstd(lighthouse) + 1e-12
    threshold = mean + k_sigma * std
    peaks, _ = sps.find_peaks(lighthouse, height=threshold, distance=int(0.1 * FS))
    lhes = []
    for peak in peaks:
        time_peak = times[peak]
        linked = None
        for candidate in segma_candidates:
            if abs(candidate["t"] - time_peak) <= window:
                linked = candidate
                break
        if linked is not None:
            lhes.append({"t": time_peak, "L": lighthouse[peak], "linked_ftcp": linked})
    return lhes, threshold


def run_ablation(metrics_dict, segma_candidates, times):
    base_l = metrics_dict["L"]
    base_lhes, _ = detect_lhes(base_l, times, segma_candidates)
    results = {
        "baseline": {
            "nLHE": len(base_lhes),
            "meanL": np.mean([lhe["L"] for lhe in base_lhes]) if base_lhes else 0.0,
        }
    }
    metric_names = ["C_lin", "C_nonlin", "C_phi", "G_eff", "Q"]
    eps_small = 1e-6
    weights_arr = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    for idx, name in enumerate(metric_names):
        metrics_stack = np.vstack([
            metrics_dict["C_lin"],
            metrics_dict["C_nonlin"],
            metrics_dict["C_phi"],
            metrics_dict["G_eff"],
            metrics_dict["Q"],
        ])
        metrics_stack[idx, :] = eps_small
        numerator = np.prod((metrics_stack + eps_small) ** weights_arr.reshape(-1, 1), axis=0)
        lighthouse = numerator ** (1.0 / weights_arr.sum())
        lhes, _ = detect_lhes(lighthouse, times, segma_candidates)
        results[name] = {
            "nLHE": len(lhes),
            "meanL": np.mean([lhe["L"] for lhe in lhes]) if lhes else 0.0,
        }
    return results


def run_pipeline():
    times, signal = make_synthetic_signal()
    energy = np.sqrt(np.mean(signal ** 2, axis=0))
    candidates = detect_ftcps(times, energy)
    print(f"FTCP raw count: {len(candidates)}")
    segmas = segma_cluster(candidates)
    print(f"Segma clusters (after grouping): {len(segmas)}")
    metrics = compute_lighthouse_metrics(times, signal, segmas)
    lhes, threshold = detect_lhes(metrics["L"], times, segmas)
    print(f"LHEs found: {len(lhes)} threshold: {threshold:.4f}")
    for lhe in lhes:
        print(
            " LHE at t={:.3f}s, L={:.4f}, linked FTCP t={:.3f}".format(
                lhe["t"], lhe["L"], lhe["linked_ftcp"]["t"]
            )
        )
    ablation_results = run_ablation(metrics, segmas, times)
    print("Ablation results (nLHE):")
    for key, value in ablation_results.items():
        print(f" {key}: {value['nLHE']} meanL: {value['meanL']:.4f}")
    fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
    axs[0].plot(times, energy, label="Energy (envelope)")
    axs[0].set_title("Energy Envelope & FTCPs")
    axs[0].plot(
        [candidate["t"] for candidate in candidates],
        [
            energy[np.argmin(np.abs(times - candidate["t"]))]
            for candidate in candidates
        ],
        "r.",
        label="FTCPs",
    )
    for segma in segmas:
        axs[0].plot(
            segma["t"],
            energy[np.argmin(np.abs(times - segma["t"]))],
            "ko",
            markersize=8,
            label="Segma",
        )
    axs[0].legend()
    axs[1].plot(times, metrics["C_lin"], label="C_lin")
    axs[1].plot(times, metrics["C_nonlin"], label="C_nonlin")
    axs[1].legend()
    axs[2].plot(times, metrics["C_phi"], label="C_phi")
    axs[2].plot(times, metrics["G_eff"], label="G_eff")
    axs[2].legend()
    axs[3].plot(times, metrics["Q"], label="Q")
    axs[3].legend()
    axs[4].plot(times, metrics["L"], label="L(t)")
    axs[4].axhline(threshold, color="r", linestyle="--", label="threshold")
    axs[4].plot([lhe["t"] for lhe in lhes], [lhe["L"] for lhe in lhes], "k*", markersize=10, label="LHEs")
    axs[4].legend()
    axs[-1].set_xlabel("Time (s)")
    plt.tight_layout()
    plt.savefig("qgita_run_output.png", dpi=150)
    print("Saved figure qgita_run_output.png")
    return {
        "t": times,
        "sig": signal,
        "candidates": candidates,
        "segmas": segmas,
        "metrics": metrics,
        "LHEs": lhes,
        "ablation": ablation_results,
    }


if __name__ == "__main__":
    run_pipeline()
