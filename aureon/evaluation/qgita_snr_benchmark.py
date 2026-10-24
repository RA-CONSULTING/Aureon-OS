"""QGITA analyzer output from the brain proof.

Detection rate stays HOLD unless the series itself carries signal-in-noise
labels. The planted-spike false-alarm target was not the detector's definition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def evaluate_qgita_snr(root: Path | None = None) -> dict[str, Any]:
    from aureon.evaluation.brain_proof import evaluate_brain

    return evaluate_brain(root)["qgita"]


def render_qgita_markdown(report: dict[str, Any]) -> str:
    public = report.get("public_series") or {}
    on_lambda = report.get("on_hnc_series") or {}
    lines = [
        "# QGITA analyzer",
        "",
        f"Source `{public.get('source')}`. Detector defaults are the ones the analyzer constructed.",
        (
            f"Ephemeris series: FTCP count `{public.get('ftcp_count')}`, "
            f"lighthouse events `{public.get('lhe_count')}`. "
            f"Detection rate **{public.get('rates_verdict')}**. {public.get('rates_reason', public.get('reason', ''))} "
            f"Clock: {public.get('timestamps', '')}"
        ),
        (
            f"Formula series: FTCP count `{on_lambda.get('ftcp_count')}`, "
            f"lighthouse events `{on_lambda.get('lhe_count')}`. "
            f"Detection rate **{on_lambda.get('rates_verdict')}**. "
            f"Clock: {on_lambda.get('timestamps', '')}"
        ),
        "",
    ]
    return "\n".join(lines)
