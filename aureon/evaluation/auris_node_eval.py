"""Auris coherence from the brain proof.

The earlier labelled hit-rate draw used thresholds that are not in
``read_auris_nodes``. That draw is not the measurement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def evaluate_auris_nodes(root: Path | None = None) -> dict[str, Any]:
    from aureon.evaluation.brain_proof import evaluate_brain

    return evaluate_brain(root)["auris"]


def render_auris_markdown(report: dict[str, Any]) -> str:
    held = ", ".join(report.get("hold_nodes") or []) or "none"
    series_nodes = report.get("market_nodes_without_reading")
    if series_nodes is None:
        series_line = "Window nodes without a reading: no series loaded."
    else:
        series_line = (
            "Window nodes without a reading: "
            + (", ".join(series_nodes) or "none")
            + ". That is one call on the whole pack and includes the latest spread print, "
            "even when that print is after the OHLC bars. "
            "Labelled bars are a separate clock: a spread print counts only at or before the decision close."
        )
    trade = report.get("trade_readiness") or {}
    lines = [
        "# Auris coherence",
        "",
        f"Source `{report.get('source')}`. {report.get('market_data_note', '')}",
        f"Coherence `{report.get('coherence')}`. Status `{report.get('coherence_status')}`.",
        f"Nodes without a reading when the four market fields are present as 0: {held}.",
        series_line,
        f"Trade readiness: **{trade.get('verdict')}**. {trade.get('reason', '')}",
        "This coherence is the method's return. It is not a hit rate. "
        "Paper labels, when present, are next-bar closes and are not fills.",
        "Release boundary stays HOLD. No order was sent. This is not a claim that the system is alive.",
        "",
    ]
    return "\n".join(lines)
