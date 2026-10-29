"""Auris coherence Space. Four meanings stay separate. No orders."""

from __future__ import annotations

import json
import os

import guard
import gradio as gr

DATA = guard.SPACE_DIR / "data" / "kraken_ohlc_BTCUSD_1440m.json"
FIELDS = ("volatility", "momentum", "volume", "spread")
LINK = (
    "https://github.com/RA-CONSULTING/Aureon-OS/blob/"
    f"{guard.COMMIT}/data/historical/kraken_ohlc_BTCUSD_1440m.json"
)
HOLD = (
    "Trade readiness: HOLD. "
    "Auris joined to Lambda: HOLD. "
    "QGITA detection rate: HOLD. "
    "Schumann f0: null. HOLD."
)


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _load() -> dict | None:
    if not DATA.is_file():
        return None
    loaded = json.loads(DATA.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def _queen():
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    return QueenHiveMind.__new__(QueenHiveMind)


def _texture(market: dict) -> tuple[dict, list[str]]:
    supplied = {}
    lines = []
    for key in FIELDS:
        if key not in market:
            lines.append(f"Input {key}: unavailable")
            continue
        number = _number(market.get(key))
        if number is None:
            lines.append(f"Input {key}: unavailable")
            continue
        supplied[key] = number
        lines.append(f"Input {key}: {number}")
    return supplied, lines


def _evaluate(market: dict | None, label: str) -> list[str]:
    lines = [
        "1. Conjecture: the five symbolic-life markers in LambdaEngine. "
        "This Space does not call that function. HOLD.",
        "2. Nine nodes: QueenHiveMind.read_auris_nodes.",
        "3. Persona: the Queen persona on QueenHiveMind. This Space does not score it.",
        "4. Coherence evaluator: QueenHiveMind.get_auris_coherence.",
        label,
    ]
    if market is None:
        lines.append("Nine nodes: unavailable")
        lines.append("Coherence evaluator: unavailable")
        return lines
    supplied, texture_lines = _texture(market)
    lines.extend(texture_lines)
    if not supplied:
        lines.append("Nine nodes: unavailable")
        lines.append("Coherence evaluator: unavailable")
        return lines
    queen = _queen()
    nodes = queen.read_auris_nodes(supplied)
    coherence, status = queen.get_auris_coherence(supplied)
    lines.append(
        "Nine nodes (inferred, this call). A missing field is not filled. "
        "A node value is the function return, including its own clamp:"
    )
    for name in sorted(nodes):
        row = nodes[name]
        value = row.get("value")
        shown = guard.UNAVAILABLE if value is None else value
        lines.append(
            f"  {name}: value {shown}; data_status {row.get('data_status')}"
        )
    if coherence is None:
        lines.append("Coherence evaluator: unavailable")
        lines.append(f"Evaluator status: {status}")
    else:
        lines.append(f"Coherence evaluator: {coherence}")
        lines.append(f"Evaluator status string: {status}")
        lines.append("Label: inferred. This is the evaluator return, not a track record.")
    lines.append(
        "Committed run with no market series: coherence unavailable, trade readiness HOLD. "
        f"Link: https://github.com/RA-CONSULTING/Aureon-OS/blob/{guard.COMMIT}/reports/measured/auris_nodes.json"
    )
    return lines


def run(mode: str, index_text: str, volatility: str, momentum: str, volume: str, spread: str) -> str:
    lines = [
        f"Licence: {guard.LICENCE}",
        HOLD,
        "This Space makes no track-record, return, or performance claim.",
        "No order path is reachable. Trading modules are hard-disabled.",
        "Replay label: public historical candles, recorded, not a performance series.",
    ]
    if mode == "bundled replay":
        loaded = _load()
        candles = loaded.get("candles") if isinstance(loaded, dict) else None
        if not isinstance(candles, list) or not candles:
            lines.append("Bundled replay: unavailable")
            body = _evaluate(None, "Replay: unavailable")
        else:
            if _blank(index_text):
                chosen = len(candles) - 1
                index_label = "last candle in the file"
            else:
                try:
                    chosen = int(str(index_text).strip())
                except ValueError:
                    chosen = None
                index_label = f"index {index_text}"
            if chosen is None or chosen < 0 or chosen >= len(candles) or not isinstance(candles[chosen], dict):
                lines.append("Bundled replay: unavailable. The candle index is missing.")
                body = _evaluate(None, "Replay: unavailable")
            else:
                candle = candles[chosen]
                provenance = loaded.get("provenance") if isinstance(loaded.get("provenance"), dict) else {}
                lines.append(f"Replay file: data/historical/kraken_ohlc_BTCUSD_1440m.json ({index_label}).")
                lines.append(f"Link: {LINK}")
                lines.append(f"Source note: {provenance.get('source', guard.UNAVAILABLE)}")
                lines.append(f"Candle timestamp: {guard.show(candle.get('ts'))}")
                for key in ("open", "high", "low", "close", "volume"):
                    lines.append(f"Candle {key}: {guard.show(candle.get(key))}")
                market = {}
                if _number(candle.get("volume")) is not None:
                    market["volume"] = _number(candle.get("volume"))
                lines.append(
                    "volatility, momentum, and spread are not columns in this file, so they are not filled in."
                )
                body = _evaluate(market, "Label on the candle: replay of recorded public market data. cited.")
    else:
        market = {}
        boxes = {
            "volatility": volatility,
            "momentum": momentum,
            "volume": volume,
            "spread": spread,
        }
        missing = False
        for key, raw in boxes.items():
            if _blank(raw):
                missing = True
                continue
            number = _number(raw)
            if number is None:
                missing = True
                continue
            market[key] = number
        if missing:
            lines.append("User texture: a field is missing, so that field is omitted.")
        body = _evaluate(market, "Label: inferred from the fields that were typed. Missing fields stay unavailable.")
    lines.extend(body)
    return "\n".join(f"- {line}" if not line.startswith("  ") else line for line in lines)


def example() -> str:
    return run("bundled replay", "", "", "", "", "")


with gr.Blocks(title="Auris coherence") as demo:
    gr.Markdown(
        f"""# Auris coherence

Licence: **{guard.LICENCE}** (same as the Aureon OS `LICENSE`).

Four meanings, kept apart:

1. **Conjecture** — symbolic-life markers in `LambdaEngine`. Not this Space.
2. **Nine nodes** — `read_auris_nodes`.
3. **Persona** — the Queen persona on `QueenHiveMind`. Not scored here.
4. **Coherence evaluator** — `get_auris_coherence`.

{HOLD}

This Space makes no track-record, return, or performance claim.
A missing field is unavailable. Nothing is filled with zero.
"""
    )
    mode = gr.Radio(["bundled replay", "user inputs"], value="bundled replay", label="Source")
    index_text = gr.Textbox(label="Candle index (empty uses the last recorded candle)")
    with gr.Row():
        volatility = gr.Textbox(label="volatility")
        momentum = gr.Textbox(label="momentum")
        volume = gr.Textbox(label="volume")
        spread = gr.Textbox(label="spread")
    output = gr.Markdown()
    gr.Button("Run").click(
        run,
        [mode, index_text, volatility, momentum, volume, spread],
        output,
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=int(os.environ.get("PORT", "7860")),
        share=False,
    )
