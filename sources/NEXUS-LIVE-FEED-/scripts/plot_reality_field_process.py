"""Generate visualization for the Reality Field process tree simulation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_process_payload(base_path: Path) -> dict:
    data_path = base_path / "data" / "reality_field_process.json"
    if not data_path.exists():
        raise FileNotFoundError(
            "Process tree data not found. Run scripts/runRealityFieldProcess.js first."
        )
    with data_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def render_process_visualization(payload: dict, output_path: Path, fmt: str) -> None:
    telemetry = payload.get("telemetry", {})
    series = telemetry.get("series", {})
    time = series.get("time", [])
    coherence = series.get("coherence", [])
    phase = series.get("phase", [])
    reality_field = series.get("realityField", [])

    if not time or not coherence or not phase:
        raise ValueError("Incomplete telemetry in process payload.")

    simulation = payload.get("simulation", {})
    unity_step = simulation.get("unityEventStep")
    unity_time = time[unity_step] if unity_step is not None and unity_step < len(time) else None

    plt.style.use("dark_background")
    fig, ax_coherence = plt.subplots(figsize=(10, 6))

    coherence_line, = ax_coherence.plot(
        time,
        coherence,
        color="#3dd5f3",
        linewidth=2.5,
        label="Coherence (C)",
    )
    ax_coherence.set_xlabel("Time (simulation units)")
    ax_coherence.set_ylabel("Coherence (C)", color="#3dd5f3")
    ax_coherence.tick_params(axis="y", colors="#3dd5f3")
    ax_coherence.set_ylim(0.8, 1.01)

    ax_phase = ax_coherence.twinx()
    phase_line, = ax_phase.plot(
        time,
        phase,
        color="#ff5fd2",
        linestyle="--",
        linewidth=2,
        label="Phase Spread (θ)",
    )
    ax_phase.set_ylabel("Phase Spread θ (rad)", color="#ff5fd2")
    ax_phase.tick_params(axis="y", colors="#ff5fd2")
    ax_phase.set_ylim(0, max(0.2, max(phase) * 1.1))

    if reality_field:
        ax_reality = ax_coherence.twinx()
        ax_reality.spines["right"].set_position(("axes", 1.12))
        reality_line, = ax_reality.plot(
            time,
            reality_field,
            color="#f7c948",
            linewidth=1.8,
            label="Reality Field R(t)",
        )
        ax_reality.set_ylabel("Reality Field R(t)", color="#f7c948")
        ax_reality.tick_params(axis="y", colors="#f7c948")
    else:
        reality_line = None

    if unity_time is not None:
        ax_coherence.axvline(
            unity_time,
            color="#ffd700",
            linestyle="-.",
            linewidth=1.6,
        )
        metrics = simulation.get("metrics", {})
        coherence_star = metrics.get("unityEventCoherence")
        phase_star = metrics.get("unityEventPhase")
        annotation = (
            f"Unity Event\nC={coherence_star:.3f}, θ={phase_star:.3f} rad"
            if coherence_star is not None and phase_star is not None
            else "Unity Event"
        )
        ax_coherence.text(
            unity_time,
            max(coherence) - 0.03,
            annotation,
            color="#ffd700",
            ha="left",
            va="top",
            fontsize=10,
        )

    title_lines = [
        "Reality Field Process Tree: Unity Event Synthesis",
    ]
    love_estimate = simulation.get("metrics", {}).get("loveConstantEstimate")
    if love_estimate is not None:
        title_lines.append(f"Λₗ Estimate: {love_estimate:.2f}")
    ax_coherence.set_title(" — ".join(title_lines))

    handles = [coherence_line, phase_line]
    if reality_line is not None:
        handles.append(reality_line)
    ax_coherence.legend(handles=handles, loc="lower right")

    ax_coherence.grid(alpha=0.2, linestyle=":")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_kwargs = {"format": fmt}
    if fmt.lower() in {"png", "jpg", "jpeg"}:
        save_kwargs["dpi"] = 200
    fig.savefig(output_path, **save_kwargs)
    plt.close(fig)


def parse_args(base_path: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the Reality Field process visualization."
    )
    default_output = base_path / "docs" / "images" / "reality_field_process.svg"
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=(
            "Target file for the visualization. Relative paths are resolved "
            "from the repository root."
        ),
    )
    parser.add_argument(
        "--format",
        choices={"svg", "png", "pdf"},
        help=(
            "Explicit output format. Defaults to the file extension or SVG "
            "when omitted."
        ),
    )
    return parser.parse_args()


def main() -> None:
    base_path = Path(__file__).resolve().parent.parent
    args = parse_args(base_path)
    payload = load_process_payload(base_path)

    output_path = args.output
    if not output_path.is_absolute():
        output_path = base_path / output_path

    fmt = args.format
    if fmt is None:
        suffix = output_path.suffix.lower()
        fmt = suffix[1:] if suffix else "svg"
        if not suffix:
            output_path = output_path.with_suffix(".svg")

    render_process_visualization(payload, output_path, fmt)
    print(f"Visualization saved to {output_path} ({fmt.upper()})")


if __name__ == "__main__":
    main()
