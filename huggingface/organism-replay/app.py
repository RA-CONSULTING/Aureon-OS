"""Organism dashboard on the committed replay only. No synthetic telemetry is added."""

from __future__ import annotations

import json
import os

import guard
import gradio as gr

REPLAY = guard.SPACE_DIR / "replay" / "organism.json"
LINK = (
    "https://github.com/RA-CONSULTING/Aureon-OS/blob/"
    f"{guard.COMMIT}/reports/measured/organism.json"
)
HOLD = (
    "Trade readiness: HOLD. "
    "Auris joined to Lambda: HOLD. "
    "QGITA detection rate: HOLD. "
    "Schumann f0: null. HOLD."
)
ICS = (
    "ics.body.state",
    "ics.mind.state",
    "ics.source.state",
    "ics.soul.state",
    "ics.hnc.state",
    "ics.monologue",
)


def _load() -> dict | None:
    if not REPLAY.is_file():
        return None
    loaded = json.loads(REPLAY.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def _dashboard_topics() -> list[str]:
    from aureon.core.aureon_thought_bus import ThoughtBus
    from aureon.core.cognitive_dashboard import CognitiveDashboard

    bus = ThoughtBus(persist_path=None)
    CognitiveDashboard(thought_bus=bus)
    lines = []
    for topic in ICS:
        found = bus.recall(topic, limit=1)
        if found:
            lines.append(f"Dashboard topic {topic}: present in the replay")
        else:
            lines.append(f"Dashboard topic {topic}: unavailable")
    return lines


def run() -> str:
    lines = [
        f"Licence: {guard.LICENCE}",
        "Replay label: recorded circulation replay. This Space does not start a seat and does not inject faults.",
        f"Link: {LINK}",
        HOLD,
        "This Space makes no track-record, return, or performance claim.",
        guard.REFUSAL,
    ]
    record = _load()
    if record is None:
        lines.append("Replay file: unavailable")
        return "\n".join(f"- {line}" for line in lines)
    connectivity = record.get("connectivity") if isinstance(record.get("connectivity"), dict) else {}
    lines.append(
        "Connectivity verdict: "
        f"{guard.show(connectivity.get('verdict'))} (cited, reports/measured/organism.json)."
    )
    lines.append(f"Connectivity score: {guard.show(connectivity.get('score'))} (cited).")
    lines.append(f"Roster: {guard.show(connectivity.get('roster'))} (cited).")
    lines.append(f"Connected: {guard.show(connectivity.get('connected'))} (cited).")
    isolated = connectivity.get("isolated")
    lines.append(
        "Isolated seats: "
        + (guard.UNAVAILABLE if isolated is None else (", ".join(isolated) if isolated else "none"))
    )
    lines.append(f"HTTP seat bound: {guard.show(connectivity.get('http_seat_bound'))} (cited).")
    seats = connectivity.get("seats") if isinstance(connectivity.get("seats"), dict) else {}
    if not seats:
        lines.append("Seat table: unavailable")
    else:
        lines.append("Seat table from the replay:")
        for name in sorted(seats):
            seat = seats[name] if isinstance(seats[name], dict) else {}
            lines.append(
                "  "
                + name
                + f" published {guard.show(seat.get('published'))}"
                + f", consumed {guard.show(seat.get('consumed'))}"
                + f", loop {guard.show(seat.get('last_loop'))}"
            )
    prediction = {}
    self_model = record.get("self_model") if isinstance(record.get("self_model"), dict) else {}
    if isinstance(self_model.get("prediction"), dict):
        prediction = self_model["prediction"]
    lines.append(
        "Self-prediction accuracy on the replay pulses: "
        f"{guard.show(prediction.get('accuracy'))} (cited)."
    )
    lines.append(
        "Persistence baseline on the same pulses: "
        f"{guard.show(prediction.get('baseline_accuracy'))} (cited)."
    )
    lines.extend(_dashboard_topics())
    lines.append(
        "The cognitive dashboard has no ics.* rows in this replay, so those panels stay unavailable."
    )
    fault = self_model.get("fault") if isinstance(self_model.get("fault"), dict) else {}
    measured = "\n".join(f"- {line}" if not line.startswith("  ") else line for line in lines)
    synthetic = "\n".join(
        [
            "## Seeded synthetic input, seed 20261024, not telemetry",
            "",
            f"- Origin: {guard.show(fault.get('origin'))}.",
            f"- Seed: {guard.show(fault.get('seed'))}.",
            (
                "- Detection rate in the file, not a telemetry figure: "
                f"{guard.show(fault.get('detection_rate'))}."
            ),
            (
                "- False-alarm rate in the file, not a telemetry figure: "
                f"{guard.show(fault.get('false_alarm_rate'))}."
            ),
            "- These faults were injected by the harness.",
            "- A claim that they are recorded seat faults is HOLD.",
        ]
    )
    return measured + "\n\n" + synthetic


def example() -> str:
    return run()


with gr.Blocks(title="Organism replay") as demo:
    gr.Markdown(
        f"""# Organism replay

Licence: **{guard.LICENCE}** (same as the Aureon OS `LICENSE`).

Dashboard of the committed circulation replay only.
The cognitive-dashboard topics that are absent from the file stay unavailable.

## Seeded synthetic input, seed 20261024, not telemetry

That block is below the measured figures. It is not part of the cited list.

{HOLD}

This Space makes no track-record, return, or performance claim.
"""
    )
    output = gr.Markdown()
    gr.Button("Load replay").click(run, None, output)


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=int(os.environ.get("PORT", "7860")),
        share=False,
    )
