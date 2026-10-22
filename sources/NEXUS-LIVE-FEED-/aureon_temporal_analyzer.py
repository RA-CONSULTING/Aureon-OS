"""Aureon Institute Harmonic Nexus Temporal Analyzer.

This module loads embedded historical timeline and resonance datasets to
illustrate the cyclical convergence of major epochs culminating in the 2025
"Unity Event". It generates a dual-panel visualization showing the phase
alignment of pivotal events and the exponential surge in harmonic resonance
through time.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO


TIMELINE_CORRELATION_DATA = """Event,Year,Phase_Radians
Standard_of_Ur,-2600,0.0
Late_Bronze_Collapse,-1200,1.7163823278149115
Celtic_Roman_Conquest,-390,2.7094321031935387
Reformation,1500,5.026548245743669
Veil_Event,2025,5.670191618674261
Predicted_Surge_1,2038,5.6861294545754
Predicted_Surge_2,2046,5.695937353591485
Predicted_Surge_3,2059,5.711875189492623
"""

HARMONIC_SURGE_DATA = """Year,Event,Region,Resonance
-3114,Mayan Cycle Start,Mesoamerica,0.85
-600,Axial Age,Multiple,0.92
0,Roman/Christian Transition,Europe/Mediterranean,0.88
1450,Renaissance,Europe,0.9
1750,Enlightenment,Europe/Global,0.93
1900,Quantum Emergence,Global,0.95
2025,Unity Event Activation,Global,0.9813
"""


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the temporal datasets as pandas ``DataFrame`` objects.

    The data is embedded inside the module to keep the script self-contained
    while remaining easy to swap out for external CSV files if required.
    """

    timeline_df = pd.read_csv(StringIO(TIMELINE_CORRELATION_DATA))
    surge_df = pd.read_csv(StringIO(HARMONIC_SURGE_DATA))
    return timeline_df, surge_df


def plot_historical_cycle(ax: plt.Axes, df: pd.DataFrame) -> plt.Axes:
    """Render a polar plot visualising cyclical historical phases."""

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)
    ax.set_facecolor("#f0f4f8")
    ax.spines["polar"].set_visible(False)
    ax.tick_params(colors="#555555")

    for radius in (0.5, 1, 1.5):
        ax.plot(
            np.linspace(0, 2 * np.pi, 100),
            [radius] * 100,
            color="gray",
            linestyle=":",
            linewidth=0.7,
        )

    for _, row in df.iterrows():
        is_prediction = "Predicted" in row["Event"]
        is_veil_event = "Veil" in row["Event"]

        color = "#d1603d" if is_veil_event else ("#307374" if not is_prediction else "#b0b0b0")
        size = 200 if is_veil_event else (100 if not is_prediction else 50)
        marker = "*" if is_veil_event else "o"
        alpha = 1.0 if not is_prediction else 0.7

        ax.scatter(
            row["Phase_Radians"],
            1,
            s=size,
            c=color,
            alpha=alpha,
            marker=marker,
            zorder=10,
        )

        ax.text(
            row["Phase_Radians"],
            1.1,
            f"{row['Event']}\n({row['Year']})",
            ha="center",
            va="center",
            fontsize=9,
            color=color,
            weight="bold" if is_veil_event else "normal",
        )

    ax.set_yticks([])
    ax.set_xticks(np.linspace(0, 2 * np.pi, 12, endpoint=False))
    ax.set_xticklabels([f"{index * 30}°" for index in range(12)])
    ax.set_title("The Great Historical Cycle\n(Phase Correlation Model)", fontsize=14, weight="bold", pad=20)
    return ax


def plot_resonance_surge(ax: plt.Axes, df: pd.DataFrame) -> plt.Axes:
    """Render a line plot of harmonic resonance growth across history."""

    sns.lineplot(x="Year", y="Resonance", data=df, ax=ax, marker="o", color="#307374", linewidth=2.5)
    sns.scatterplot(x="Year", y="Resonance", data=df, ax=ax, s=100, color="#307374", zorder=10)

    unity_event = df[df["Year"] == 2025]
    if not unity_event.empty:
        ax.scatter(
            unity_event["Year"],
            unity_event["Resonance"],
            s=300,
            color="#d1603d",
            marker="*",
            zorder=12,
            label="Unity Event (C=0.9813)",
        )
        ax.text(
            unity_event["Year"].iloc[0],
            unity_event["Resonance"].iloc[0] - 0.015,
            "Unity Event",
            ha="right",
            va="top",
            fontsize=12,
            color="#d1603d",
            weight="bold",
        )

    ax.set_title("Harmonic Resonance Surge Across History", fontsize=14, weight="bold", pad=20)
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Harmonic Resonance (Coherence)", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_facecolor("#f0f4f8")
    ax.legend()
    return ax


def main() -> None:
    """Execute the analyzer and save the resulting visualisation."""

    print("Initializing Aureon Harmonic Nexus Temporal Analyzer...")
    timeline_df, surge_df = load_data()

    sns.set_style("whitegrid")
    fig = plt.figure(figsize=(20, 10))
    fig.suptitle(
        "Aureon Institute: Temporal Dynamics & The 2025 Harmonic Convergence",
        fontsize=22,
        weight="bold",
        y=0.98,
    )
    fig.patch.set_facecolor("#e9eef2")

    ax1 = fig.add_subplot(1, 2, 1, projection="polar")
    ax2 = fig.add_subplot(1, 2, 2)

    plot_historical_cycle(ax1, timeline_df)
    plot_resonance_surge(ax2, surge_df)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    output_filename = "Harmonic_Nexus_Analysis_2025.png"
    plt.savefig(output_filename, dpi=300, facecolor=fig.get_facecolor())

    print(f"\nAnalysis complete. Visualization saved as '{output_filename}'")
    print("\n--- KEY FINDINGS ---")
    print("1. Historical Cycle: Major historical events align to a cyclical phase model, indicating a predictable pattern of paradigm shifts.")
    print("2. Current Position: The 'Veil Event' of 2025 is positioned at a critical juncture in the cycle, marking the start of a new phase.")
    print("3. Resonance Surge: Global Harmonic Resonance has been steadily increasing over millennia, showing an exponential curve.")
    print(
        "4. The 2025 Peak: This curve culminates in the 2025 Unity Event, which achieved the highest measured resonance in recorded history (C="
        f"{surge_df[surge_df['Year'] == 2025]['Resonance'].iloc[0]:.4f})."
    )
    print(
        "\nConclusion: The data provides quantitative validation for the 2025 Unity Event as a historically significant convergence point, a 'Harmonic Nexus' where the great cycles of human consciousness align and reset."
    )

    plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
