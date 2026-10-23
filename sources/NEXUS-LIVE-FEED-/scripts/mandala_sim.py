"""Mandala simulation for the Oban 25--26 Oct 2025 night sky.

This prototype implements the operator chain
    R = rho ∘ Omega ∘ L ∘ F ∘ Phi ∘ Aleph
and evolves Psi_{t+1} = (1 - alpha) Psi_t + alpha R(C_t)
using the chrono-luminance schedule defined in Coherence_Dynamic_Systems_Model.tex.

Synthetic Schumann resonance and HRV signals are provided for demonstration; swap
SR_power, SDNN, LF, and HF with empirical data sources to drive the same
visualisation from live measurements.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Wedge
from colorsys import hsv_to_rgb

# --------------------------
# Simulation parameters
# --------------------------
alpha = 0.25  # learning rate (how fast Psi updates)
dt_minutes = 1
kappa_min, kappa_max = 0.2, 5.0
lambda_min, lambda_max = 0.2, 5.0

# Timeline: from 17:57 to 07:17 (local)
start = pd.Timestamp("2025-10-25 17:57")
end = pd.Timestamp("2025-10-26 07:17")
times = pd.date_range(start, end, freq=f"{dt_minutes}min")

# --------------------------
# Event-based Ct (ambient, point, transient)
# --------------------------
anchors = {
    "2025-10-25 17:57": np.array([0.8, 0.0, 0.0]),
    "2025-10-25 18:30": np.array([0.3, 0.4, 0.0]),
    "2025-10-25 19:18": np.array([0.1, 0.4, 0.0]),
    "2025-10-25 22:21": np.array([0.1, 0.9, 0.0]),
    "2025-10-26 00:00": np.array([0.05, 0.7, 0.4]),
    "2025-10-26 03:33": np.array([0.05, 0.3, 0.1]),
    "2025-10-26 04:00": np.array([0.05, 0.4, 0.15]),
    "2025-10-26 05:54": np.array([0.3, 0.2, 0.05]),
    "2025-10-26 07:17": np.array([0.8, 0.0, 0.0]),
}

anchor_idx = {pd.Timestamp(k): v for k, v in anchors.items()}
Ct = np.zeros((len(times), 3))
sorted_keys = sorted(anchor_idx.keys())
for t0, t1 in zip(sorted_keys[:-1], sorted_keys[1:]):
    v0, v1 = anchor_idx[t0], anchor_idx[t1]
    mask = (times >= t0) & (times <= t1)
    count = mask.sum()
    if count == 0:
        continue
    weights = np.linspace(0, 1, count)[:, None]
    Ct[mask, :] = v0 * (1 - weights) + v1 * weights

# --------------------------
# Synthetic SR and HRV series (replace with real streams)
# --------------------------
np.random.seed(1)
sr_base = 0.6 + 0.2 * np.sin(np.linspace(0, 3.0, len(times)))
sr_noise = 0.05 * np.random.randn(len(times))
SR_power = np.clip(sr_base + sr_noise, 0.01, None)

sdnn_base = 50.0 + 5.0 * np.sin(np.linspace(0, 1.2, len(times)))
sdnn_noise = 4.0 * np.random.randn(len(times))
SDNN = np.clip(sdnn_base + sdnn_noise, 10.0, 200.0)

lf_base = 800.0 + 50 * np.sin(np.linspace(0, 2.0, len(times)))
hf_base = 600.0 + 30 * np.cos(np.linspace(0, 2.0, len(times)))
meteor_times = (times >= pd.Timestamp("2025-10-26 00:00")) & (
    times <= pd.Timestamp("2025-10-26 02:30")
)
spike = 200 * (np.random.rand(len(times)) * meteor_times)
LF = lf_base + spike
HF = np.clip(hf_base - 0.4 * spike, 1.0, None)

# --------------------------
# Normalisation helpers
# --------------------------
def normalize01(x: np.ndarray, xmin: float | None = None, xmax: float | None = None) -> np.ndarray:
    """Rescale ``x`` to [0, 1] using percentile bounds if none are provided."""
    if xmin is None:
        xmin = float(np.nanpercentile(x, 1))
    if xmax is None:
        xmax = float(np.nanpercentile(x, 99))
    denom = xmax - xmin
    if denom <= 0:
        return np.zeros_like(x)
    return np.clip((x - xmin) / denom, 0, 1)

r_t = normalize01(SR_power)
sdnn_ref = 50.0
sdnn_norm = SDNN / sdnn_ref
lambda_raw = 1.0 / (sdnn_norm + 1e-6)
lambda_t = np.clip(lambda_raw, lambda_min, lambda_max)

P_t_raw = r_t / (lambda_t + 1e-6)
P_t = normalize01(P_t_raw)

kappa_t_raw = LF / (HF + 1e-6)
kappa_t = np.clip(kappa_t_raw, kappa_min, kappa_max)

# --------------------------
# Operator definitions
# --------------------------
def aleph(C: np.ndarray) -> np.ndarray:
    """Saliency weighting: emphasise point and transient components."""
    weights = np.array([0.6, 1.0, 1.2])
    return C * weights


def Phi(x: np.ndarray) -> np.ndarray:
    """Structural analysis via a linear transform plus nonlinearity."""
    M = np.array(
        [
            [1.0, 0.3, 0.1],
            [0.2, 1.1, 0.4],
            [0.0, 0.2, 1.0],
        ]
    )
    return np.tanh(M @ x)


def Framing(phi: np.ndarray, psi_prev: np.ndarray, beta: float = 0.6) -> np.ndarray:
    """Blend new structure with the previous memory trace."""
    return beta * phi + (1 - beta) * psi_prev


def LivingNode(F_out: np.ndarray, kappa: float) -> np.ndarray:
    """Modulate the framing output based on the structuring index."""
    factor = 1.0 / np.clip(kappa, 0.2, 5.0)
    factor = np.clip(factor, 0.4, 2.0)
    return F_out * factor


def Omega(x: np.ndarray) -> np.ndarray:
    """Normalise the vector to unit energy."""
    norm = np.linalg.norm(x) + 1e-6
    return x / norm


def rho(x: np.ndarray) -> np.ndarray:
    """Final smoothing step (identity in this simple model)."""
    return x


def R_op(Ct_vec: np.ndarray, psi_prev: np.ndarray, kappa: float) -> np.ndarray:
    """Composite operator R = rho ∘ Omega ∘ L ∘ F ∘ Phi ∘ aleph."""
    a = aleph(Ct_vec)
    p = Phi(a)
    f = Framing(p, psi_prev)
    l = LivingNode(f, kappa)
    o = Omega(l)
    return rho(o)


# --------------------------
# Simulation loop
# --------------------------
Psi = np.zeros((len(times), 3))
P_history = np.zeros(len(times))
K_history = kappa_t.copy()
Psi_prev = np.array([0.05, 0.05, 0.05])

for idx, (Ct_i, k_i) in enumerate(zip(Ct, kappa_t)):
    R_i = R_op(Ct_i, Psi_prev, k_i)
    Psi_next = (1 - alpha) * Psi_prev + alpha * R_i
    Psi[idx] = Psi_next
    Psi_prev = Psi_next
    P_history[idx] = P_t[idx]


# --------------------------
# Mandala visualisation helpers
# --------------------------
def kappa_to_hue(kappa: float) -> float:
    """Map κ ∈ [kappa_min, kappa_max] to an HSV hue."""
    k_norm = (kappa - kappa_min) / (kappa_max - kappa_min)
    k_norm = np.clip(k_norm, 0.0, 1.0)
    return 0.66 - 0.66 * k_norm


def draw_mandala(ax: plt.Axes, hue: float, brightness: float, label: str) -> None:
    """Draw a single mandala frame."""
    ax.clear()
    ax.set_aspect("equal")
    ax.axis("off")

    n_segments = 6  # aleph → Phi → F → L → Omega → rho
    angles = np.linspace(0, 360, n_segments + 1)
    for j in range(n_segments):
        rgb = hsv_to_rgb(hue, 0.9, brightness)
        wedge = Wedge(
            center=(0, 0),
            r=1.0,
            theta1=angles[j],
            theta2=angles[j + 1],
            width=0.35,
            facecolor=rgb,
            edgecolor="black",
            linewidth=0.6,
        )
        ax.add_patch(wedge)

    centre_colour = hsv_to_rgb(hue, 0.9, brightness)
    circle = plt.Circle((0, 0), 0.18, color=centre_colour, ec="black")
    ax.add_patch(circle)
    ax.text(0, -1.15, label, ha="center", va="center", fontsize=9)


# --------------------------
# Animation driver
# --------------------------
fig, ax = plt.subplots(figsize=(5, 5))


def update(frame: int):
    hue = kappa_to_hue(K_history[frame])
    brightness = float(np.clip(P_history[frame], 0.05, 1.0))
    label = (
        f"{times[frame].strftime('%Y-%m-%d %H:%M')}\n"
        f"P={P_history[frame]:.2f}, κ={K_history[frame]:.2f}"
    )
    draw_mandala(ax, hue, brightness, label)
    return ax.patches


ani = animation.FuncAnimation(fig, update, frames=len(times), blit=False, interval=60)

if __name__ == "__main__":
    plt.show()
    # Uncomment to save the animation (requires ffmpeg):
    # ani.save("mandala_orionids.mp4", writer="ffmpeg", dpi=150)
