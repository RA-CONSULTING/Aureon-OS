"""Phenolic fingerprint → cognition bridge.

Feeds a phenolic-fingerprint :class:`AnalysisResult` (as its ``to_dict()`` dict)
into Aureon's cognitive / meta-cognitive layer using the repo's blessed pattern
(the one `aureon/analytics/aureon_lighthouse.py` uses): publish ``Thought``
envelopes on the ThoughtBus and mirror a compact signal to a ``bus_trace`` that
the metacognition monitor / Queen can sense.

Decoupled by design: it consumes a plain dict (no numpy, no ``connector`` import)
and has no import-time side effects, so it is safe to live in the cognition
package and be called explicitly after an analysis run.

Topics published:
* ``phenolic.fingerprint.run``       — one per analysis, payload carries the
  pattern summary + run metadata.
* ``phenolic.fingerprint.compound``  — one per compound (test_A/test_B p-values,
  separable flag, peak count, provenance/DOIs).

Trace signal: ``phenolic_fingerprint`` (separable fraction, counts, validity).
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from aureon.core.aureon_thought_bus import Thought, get_thought_bus
from aureon.core.bus_trace import append_trace

__all__ = [
    "RUN_TOPIC",
    "COMPOUND_TOPIC",
    "TRACE_NAME",
    "summarize_patterns",
    "emit_to_cognition",
]

SOURCE: str = "phenolic_fingerprint"
RUN_TOPIC: str = "phenolic.fingerprint.run"
COMPOUND_TOPIC: str = "phenolic.fingerprint.compound"
TRACE_NAME: str = "phenolic_fingerprint"


def _provenance(sources: list[str]) -> str:
    """Classify a compound's provenance from its source strings."""
    tags = {"computed" if "COMPUTED" in str(s) else "experimental" for s in sources}
    if not tags:
        return "experimental"
    return "mixed" if len(tags) > 1 else next(iter(tags))


def summarize_patterns(analysis: dict[str, Any]) -> dict[str, Any]:
    """Distil an :class:`AnalysisResult` dict into a cognition-ready pattern summary.

    This is the "make sense of the patterns" layer: what is separable, what merely
    clusters, how confident the provenance is, and whether the controls validate
    the run. Reads only the dict produced by ``AnalysisResult.to_dict()``.
    """
    compounds: dict[str, Any] = analysis.get("compounds", {}) or {}
    alpha = float(analysis.get("alpha", 0.05) or 0.05)
    n = len(compounds)

    separable = sorted(name for name, c in compounds.items() if c.get("separable"))
    clustering = sorted(
        name for name, c in compounds.items()
        if c.get("test_A_p") is not None and c["test_A_p"] < alpha
    )
    provenance_counts: dict[str, int] = {}
    for c in compounds.values():
        tag = _provenance(c.get("sources", []) or [])
        provenance_counts[tag] = provenance_counts.get(tag, 0) + 1

    controls = analysis.get("controls", {}) or {}
    controls_pass = bool(controls) and all(c.get("passed") for c in controls.values())

    return {
        "valid": bool(analysis.get("valid")),
        "controls_pass": controls_pass,
        "alpha": alpha,
        "n_compounds": n,
        "separable": separable,
        "separable_fraction": (len(separable) / n) if n else 0.0,
        "clustering_significant": clustering,
        "provenance_counts": provenance_counts,
        "headline": (
            f"{len(separable)}/{n} separable · "
            f"{len(clustering)}/{n} clustering-significant · "
            f"controls {'PASS' if controls_pass else 'FAIL'}"
        ),
    }


def emit_to_cognition(
    analysis: dict[str, Any],
    *,
    bus: Any | None = None,
    trace: bool = True,
) -> dict[str, Any]:
    """Publish the analysis to the ThoughtBus + mirror a trace; return the summary.

    ``analysis`` is ``AnalysisResult.to_dict()``. Bus failures are swallowed (the
    cognition emission must never crash an analysis run), matching the repo's
    "a throwing bus does not raise" contract. Returns :func:`summarize_patterns`.
    """
    summary = summarize_patterns(analysis)
    bus = bus if bus is not None else get_thought_bus()
    trace_id = uuid.uuid4().hex

    try:
        bus.publish(
            Thought(
                source=SOURCE,
                topic=RUN_TOPIC,
                trace_id=trace_id,
                payload={
                    "summary": summary,
                    "valid": bool(analysis.get("valid")),
                    "source_path": analysis.get("source_path"),
                    "formats": analysis.get("formats"),
                    "reason": analysis.get("reason"),
                },
            )
        )
        for name, comp in (analysis.get("compounds", {}) or {}).items():
            bus.publish(
                Thought(
                    source=SOURCE,
                    topic=COMPOUND_TOPIC,
                    trace_id=trace_id,
                    payload={"compound": name, "provenance": _provenance(comp.get("sources", []) or []), **comp},
                )
            )
    except Exception:  # noqa: BLE001 - emission is best-effort, never fatal
        pass

    if trace:
        try:
            append_trace(
                TRACE_NAME,
                {
                    "separable_fraction": summary["separable_fraction"],
                    "n_separable": len(summary["separable"]),
                    "n_clustering_significant": len(summary["clustering_significant"]),
                    "n_compounds": summary["n_compounds"],
                    "valid": summary["valid"],
                    "controls_pass": summary["controls_pass"],
                    "_ts": time.time(),
                },
            )
        except Exception:  # noqa: BLE001 - trace mirror is best-effort
            pass

    return summary
