"""QGITA Space. Events are the adapter return. Detection rate stays HOLD."""

from __future__ import annotations

import csv
import json
import os

import guard
import gradio as gr

SERIES = guard.SPACE_DIR / "data" / "de440_timeseries.csv"
REPLAY = guard.SPACE_DIR / "replay" / "qgita_snr.json"
COLUMN = "Lambda"
HOLD = (
    "Trade readiness: HOLD. "
    "Auris joined to Lambda: HOLD. "
    "QGITA detection rate: HOLD. "
    "Schumann f0: null. HOLD."
)
LINK = (
    "https://github.com/RA-CONSULTING/Aureon-OS/blob/"
    f"{guard.COMMIT}/reports/measured/qgita_snr.json"
)


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _load_series() -> tuple[list[float], str]:
    if not SERIES.is_file():
        return [], "unavailable"
    values: list[float] = []
    with SERIES.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or COLUMN not in reader.fieldnames:
            return [], "unavailable"
        for row in reader:
            try:
                values.append(float(row[COLUMN]))
            except (TypeError, ValueError):
                continue
    if len(values) < 3:
        return [], "unavailable"
    return values, "loaded"


def _user_series(text: str) -> list[float] | None:
    if _blank(text):
        return None
    values: list[float] = []
    for line in str(text).splitlines():
        piece = line.strip()
        if not piece:
            continue
        try:
            number = float(piece)
        except ValueError:
            return None
        if number != number or number in (float("inf"), float("-inf")):
            return None
        values.append(number)
    if len(values) < 3:
        return None
    return values


def _record(item: object, kind: str) -> dict:
    if kind == "ftcp":
        return {
            "adapter": "QGITAMarketAnalyzer.analyze",
            "kind": "FTCP",
            "timestamp": float(item.timestamp),
            "knot_index": int(item.knot_index),
            "curvature": float(item.curvature),
            "is_valid": bool(item.is_valid),
        }
    return {
        "adapter": "QGITAMarketAnalyzer.analyze",
        "kind": "lighthouse",
        "timestamp": float(item.timestamp),
        "event_type": str(item.event_type.value),
        "lighthouse_intensity": float(item.lighthouse_intensity),
    }


def _run_adapter(values: list[float]) -> dict:
    from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer

    analyzer = QGITAMarketAnalyzer()
    for index, value in enumerate(values):
        analyzer.feed_price(float(value), timestamp=float(index))
    raw = analyzer.analyze()
    stage1 = raw.get("stage1") if isinstance(raw.get("stage1"), dict) else {}
    stage2 = raw.get("stage2") if isinstance(raw.get("stage2"), dict) else {}
    valid = list(stage1.get("valid_ftcps") or [])
    events = list(stage2.get("lighthouse_events") or [])
    return {
        "status": raw.get("status", guard.UNAVAILABLE),
        "ftcp_count": stage1.get("ftcp_count"),
        "lhe_count": stage2.get("lhe_count"),
        "ftcps": [_record(item, "ftcp") for item in valid],
        "lighthouse_events": [_record(item, "lhe") for item in events],
        "samples_fed": len(values),
    }


def _committed() -> dict | None:
    if not REPLAY.is_file():
        return None
    loaded = json.loads(REPLAY.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def run(mode: str, user_text: str) -> str:
    lines = [
        f"Licence: {guard.LICENCE}",
        "QGITA events below come from the adapter QGITAMarketAnalyzer.analyze.",
        "They are the adapter return, not a detection rate.",
        HOLD,
        "This Space makes no track-record, return, or performance claim.",
        "The analyzer's signals object is not shown.",
        guard.REFUSAL,
        f"Committed file: {LINK}",
    ]
    if mode == "bundled replay":
        values, status = _load_series()
        lines.append(
            "Replay label: committed derived series data/de440_timeseries.csv column Lambda."
        )
        lines.append(
            "The committed file tags that series cited-unverified and says it is not public market data."
        )
        if status != "loaded":
            lines.append("Bundled series: unavailable")
            values = []
        else:
            lines.append(f"Samples in the file: {len(values)}")
            lines.append("Clock: sample index, the same clock as the committed run.")
    else:
        parsed = _user_series(user_text)
        if parsed is None:
            lines.append("User series: unavailable")
            values = []
        else:
            values = parsed
            lines.append("Label: inferred. Adapter run on the pasted series. Not the committed replay.")
            lines.append("Clock: sample index.")
    if not values:
        lines.append("Adapter FTCP count: unavailable")
        lines.append("Adapter lighthouse count: unavailable")
        lines.append("Adapter events: unavailable")
    else:
        result = _run_adapter(values)
        lines.append(f"Adapter status: {guard.show(result['status'])}")
        lines.append(f"Adapter FTCP count: {guard.show(result['ftcp_count'])} (inferred, this call).")
        lines.append(
            f"Adapter lighthouse count: {guard.show(result['lhe_count'])} (inferred, this call)."
        )
        if result["ftcps"]:
            lines.append("Adapter FTCP events:")
            for row in result["ftcps"]:
                lines.append("  " + json.dumps(row, sort_keys=True))
        else:
            lines.append("Adapter FTCP events: none returned.")
        if result["lighthouse_events"]:
            lines.append("Adapter lighthouse events:")
            for row in result["lighthouse_events"]:
                lines.append("  " + json.dumps(row, sort_keys=True))
        else:
            lines.append("Adapter lighthouse events: none returned.")
    committed = _committed()
    derived = committed.get("derived_series") if isinstance(committed, dict) else None
    if isinstance(derived, dict):
        lines.append(
            "Committed adapter FTCP count: "
            f"{guard.show(derived.get('ftcp_count'))} (cited, reports/measured/qgita_snr.json)."
        )
        lines.append(
            "Committed adapter lighthouse count: "
            f"{guard.show(derived.get('lhe_count'))} (cited)."
        )
        lines.append(f"Committed detection rate: {guard.show(derived.get('rates_verdict'))}.")
    else:
        lines.append("Committed QGITA record: unavailable")
    lines.append("Detection rate: HOLD. False-alarm rate: HOLD.")
    return "\n".join(f"- {line}" if not line.startswith("  ") else line for line in lines)


def example() -> str:
    return run("bundled replay", "")


with gr.Blocks(title="QGITA adapter") as demo:
    gr.Markdown(
        f"""# QGITA adapter

Licence: **{guard.LICENCE}** (same as the Aureon OS `LICENSE`).

Detections are the return of the QGITA adapter `QGITAMarketAnalyzer.analyze`.
Detection rate and false-alarm rate stay HOLD. Schumann f0 stays null.

{HOLD}

This Space makes no track-record, return, or performance claim.
"""
    )
    mode = gr.Radio(["bundled replay", "user series"], value="bundled replay", label="Source")
    user_text = gr.Textbox(label="One number per line", lines=6)
    output = gr.Markdown()
    gr.Button("Run").click(run, [mode, user_text], output)


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=int(os.environ.get("PORT", "7860")),
        share=False,
    )
