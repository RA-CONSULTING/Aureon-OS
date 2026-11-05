"""Measure the three parts of the internal brain on the code that already exists.

The Harmonic Nexus Core figure is ``HarmonicRealityField.step`` with the
multiverse extension off, which is the master-formula branch in that method.
The class default turns the extension on. ``project_to_3d`` uses 0 when no
residual is supplied, and three constructions of that default match, so the
extension is measured beside the formula branch.

Auris coherence is ``QueenHiveMind.get_auris_coherence``. When
``reports/measured/market_series.json`` is a loaded public pack, that call
receives the pack's volatility, momentum, volume, and spread. The same call
is repeated at each closed bar on the bars and spread prints known at that
bar's close. The next bar's close-to-close return is the outcome label.
This checkout has no filled order for the series, so the label is paper.
Trade readiness is then a measured pass or a measured fail. The release
boundary stays HOLD. When the pack is absent or HOLD, the omitted call is
no_data and trade readiness stays HOLD. A measured fail records why the
ready mark stayed off. The stored spread prints may all fall after the
labelled decision closes, so Deer has no reading and the call returns
no_data. A sweep of the existing node formulas may also never emit that
mark. Those facts are not a reason to lower the mark, to copy a later
spread print onto an earlier bar, or to clear the release boundary. A
zero-input probe still names any node that stays without a value when the
four market fields are present as 0.

The same coherence method is then called with the formula-path Λ(t) series.
The value is passed under the field names already used for that series:
``lambda``, ``lambda_t``, and ``lambda_current``. No conversion into
volatility, momentum, volume, or spread is added. If the returned coherence
does not change, the join stays HOLD.

QGITA is ``QGITAMarketAnalyzer`` constructed with its own defaults, then
``analyze``. The public pack is fed beside the derived column and the formula
series. FTCP and lighthouse counts are that call. Detection rate and
false-alarm rate stay a measured HOLD: the receipt names the missing
ingredient, an exogenous signal-present versus noise-only label on held-out
trials. A planted-impulse harness, when a test runs one, is tagged
synthetic_planted and is not written into these fields. The release boundary
stays HOLD.

The ready-to-trade mark is the status string ``get_auris_coherence`` already
returns. A paper long is that mark. It passes only when every such paper
long has a higher next close. Live trading stays off
(``AUREON_DISABLE_REAL_ORDERS=1``). These figures are not a claim that the
system is conscious or alive.
"""

from __future__ import annotations

import ast
import contextlib
import csv
import inspect
import io
import os
import textwrap
from pathlib import Path
from typing import Any

from aureon.evaluation.market_series import derive_fields, load_market_series, series_summary
from aureon.evaluation.qgita_rate_receipt import (
    DERIVED_EVENT_COLUMNS,
    RATES_HOLD_VERDICT,
    apply_rates_hold,
    rates_hold_receipt,
)

DERIVED_SERIES = "data/de440_timeseries.csv"
DERIVED_COLUMN = "Lambda"
DERIVED_COMMIT = "6fd1d9d8"
_METRIC_WINDOW = 100
_NOTE = (
    "These figures are the HNC master-formula path, Auris coherence, and the QGITA analyzer. "
    "They are not a claim that the system is conscious or alive."
)
_INPUTS = ("volatility", "momentum", "volume", "spread")
_READY = "Ready to trade"
_ORDERS_OFF = "AUREON_DISABLE_REAL_ORDERS=1"
# Names this repo already uses for HarmonicRealityField Λ(t). "Lambda" is the
# derived-column name and is not this series.
_LAMBDA_KEYS = ("lambda", "lambda_t", "lambda_current")


def _optional_count(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _one_default_field() -> dict[str, Any]:
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    field = HarmonicRealityField()
    series: list[float] = []
    while len(series) < _METRIC_WINDOW:
        series.append(float(field.step()))
    history = list(field.translation_map.projection_history) if field.translation_map is not None else []
    noises = [float(row["noise"]) for row in history]
    return {
        "series": series,
        "coherence": float(field.coherence),
        "state": str(field.state.value),
        "lambda_last": series[-1],
        "boundedness": float(field.boundedness),
        "echo_strength": float(field.echo_strength),
        "noises_all_zero": bool(noises) and all(item == 0.0 for item in noises),
        "noise_samples": len(noises),
        "noise_level_attribute": None if field.translation_map is None else float(field.translation_map.noise_level),
    }


def _default_extension() -> dict[str, Any]:
    """Measure the class-default extension. The noise claim is checked here."""

    runs = [_one_default_field() for _ in range(3)]
    identical = all(item["series"] == runs[0]["series"] for item in runs)
    noises_zero = all(item["noises_all_zero"] for item in runs)
    first = runs[0]
    if identical and noises_zero:
        verdict = "measured"
        reason = (
            "project_to_3d sets noise to 0 when no observed residual is supplied. "
            "TranslationMap.noise_level is stored and is not read by that method. "
            "Three constructions of the default HarmonicRealityField returned the same series."
        )
    elif not identical:
        verdict = "HOLD"
        reason = "three constructions of the default HarmonicRealityField did not return the same series"
    else:
        verdict = "HOLD"
        reason = "project_to_3d recorded a non-zero noise on the default path"
    return {
        "verdict": verdict,
        "reason": reason,
        "enable_multiverse": True,
        "constructions": len(runs),
        "series_identical": identical,
        "recorded_noise_all_zero": noises_zero,
        "noise_level_attribute_unread": first["noise_level_attribute"],
        "steps": len(first["series"]),
        "state": first["state"] if identical else None,
        "coherence": first["coherence"] if identical else None,
        "lambda_last": first["lambda_last"] if identical else None,
        "boundedness": first["boundedness"] if identical else None,
        "echo_strength": first["echo_strength"] if identical else None,
        "series": first["series"] if identical else None,
    }


def _reader():
    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    return QueenHiveMind.__new__(QueenHiveMind)


def _run_hnc() -> dict[str, Any]:
    from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField

    field = HarmonicRealityField(enable_multiverse=False)
    series: list[float] = []
    while len(series) < _METRIC_WINDOW:
        series.append(float(field.step()))
    return {
        "source": "aureon.harmonic.aureon_harmonic_reality.HarmonicRealityField.step",
        "formula": "F_sub(t) + F_observer(t) + F_feedback(t)",
        "enable_multiverse": False,
        "why_multiverse_is_off": (
            "enable_multiverse=False is the master-formula branch already in step(). "
            "The class default turns the extension on. That extension is measured separately."
        ),
        "multiverse_extension": _default_extension(),
        "steps": len(series),
        "steps_are": "the history length HarmonicRealityField._update_metrics requires before it computes coherence",
        "parameters": {
            "alpha": float(field.observer.alpha),
            "beta": float(field.echo.beta),
            "tau": float(field.echo.tau),
            "g": float(field.observer.g),
            "delta_t": float(field.observer.delta_t),
            "sample_rate": float(field.sample_rate),
            "substrate_frequencies": [float(mode.frequency) for mode in field.substrate.modes],
        },
        "lambda_min": min(series),
        "lambda_max": max(series),
        "lambda_mean": sum(series) / len(series),
        "lambda_last": series[-1],
        "coherence": float(field.coherence),
        "boundedness": float(field.boundedness),
        "echo_strength": float(field.echo_strength),
        "echo_strength_is_correlation": False,
        "echo_figure": "CausalEcho.get_echo_magnitude_ratio, not a correlation",
        "state": str(field.state.value),
        "series": series,
        "dt": float(field.dt),
    }


def _texture(pack: dict[str, Any]) -> dict[str, float]:
    inputs = pack.get("auris_inputs") if isinstance(pack.get("auris_inputs"), dict) else {}
    texture: dict[str, float] = {}
    for key in _INPUTS:
        value = _optional_float(inputs.get(key))
        if value is not None and key in inputs:
            texture[key] = value
    return texture


def _spread_clock(pack: dict[str, Any]) -> str:
    field = (pack.get("fields") or {}).get("spread") if isinstance(pack.get("fields"), dict) else None
    if isinstance(field, dict) and field.get("value") is not None:
        return str(field.get("clock") or "latest public bid/ask print")
    return "not supplied, so a node that needs spread stays without a reading"


def _known_prints(prints: list[Any], decision_close: int) -> list[dict[str, Any]]:
    """Spread prints whose clock is at or before the decision close. Later prints stay out."""

    known: list[dict[str, Any]] = []
    for item in prints:
        if not isinstance(item, dict):
            continue
        stamp = item.get("time")
        if isinstance(stamp, bool) or stamp is None:
            continue
        try:
            unix = int(stamp)
        except (TypeError, ValueError):
            continue
        if unix <= decision_close:
            known.append(item)
    return known


def _paper_outcome(move: float) -> str:
    if move > 0.0:
        return "up"
    if move < 0.0:
        return "down"
    return "flat"


def _paper_labels(queen: Any, pack: dict[str, Any]) -> list[dict[str, Any]]:
    """One paper label per bar that has a later close.

    The decision texture is ``derive_fields`` on bars through the decision
    bar, plus spread prints at or before that bar's close. The label is the
    next close against this close. No order is sent.
    """

    bars = pack.get("bars") if isinstance(pack.get("bars"), list) else []
    prints = pack.get("spread_prints") if isinstance(pack.get("spread_prints"), list) else []
    interval = _optional_count(pack.get("interval_seconds")) or 3600
    labels: list[dict[str, Any]] = []
    for index in range(1, len(bars) - 1):
        decision = bars[index]
        nxt = bars[index + 1]
        window = bars[: index + 1]
        if not isinstance(decision, dict) or not isinstance(nxt, dict):
            continue
        close = _optional_float(decision.get("close"))
        nxt_close = _optional_float(nxt.get("close"))
        if close is None or close <= 0.0 or nxt_close is None or isinstance(decision.get("open_time"), bool):
            continue
        open_unix = _optional_count(decision.get("open_time"))
        if open_unix is None:
            continue
        decision_close = open_unix + interval
        derived = derive_fields(window, _known_prints(prints, decision_close))
        inputs = derived.get("auris_inputs") if isinstance(derived.get("auris_inputs"), dict) else {}
        texture: dict[str, float] = {}
        for key in _INPUTS:
            if key not in inputs:
                continue
            value = _optional_float(inputs.get(key))
            if value is not None:
                texture[key] = value
        coherence, status = queen.get_auris_coherence(texture)
        nodes = queen.read_auris_nodes(texture)
        missing = sorted(name for name, item in nodes.items() if item.get("value") is None)
        move = (nxt_close - close) / close
        clownfish = nodes.get("Clownfish") if isinstance(nodes.get("Clownfish"), dict) else {}
        owl = nodes.get("Owl") if isinstance(nodes.get("Owl"), dict) else {}
        labels.append(
            {
                "clownfish": str(clownfish.get("data_status") or "no_data"),
                "coherence": None if coherence is None else float(coherence),
                "coherence_status": status,
                "decision_close_unix": decision_close,
                "entered": bool(coherence is not None and isinstance(status, str) and _READY in status),
                "filled": False,
                "next_bar_return": move,
                "nodes_without_reading": missing,
                "open_time": open_unix,
                "outcome_kind": "paper",
                "owl": str(owl.get("data_status") or "no_data"),
                "paper_outcome": _paper_outcome(move),
                "return_evidence": "measured",
                "spread_known_at_decision": "spread" in texture,
            }
        )
    return labels


def _coherence_compare(test: ast.AST) -> tuple[str, float] | None:
    if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
        return None
    left = test.left
    if not isinstance(left, ast.Name) or left.id != "coherence":
        return None
    op = test.ops[0]
    if isinstance(op, ast.GtE):
        symbol = ">="
    elif isinstance(op, ast.Gt):
        symbol = ">"
    else:
        return None
    raw = test.comparators[0]
    if not isinstance(raw, ast.Constant) or isinstance(raw.value, bool):
        return None
    try:
        threshold = float(raw.value)
    except (TypeError, ValueError):
        return None
    return symbol, threshold


def _status_constant(body: list[ast.stmt]) -> str | None:
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and "COHERENCE" in node.value:
                return node.value
    return None


def _status_ladder(method: Any) -> dict[str, Any]:
    """Cited coherence compares in ``get_auris_coherence``, in source order."""

    tree = _method_tree(method)
    compares: list[dict[str, Any]] = []
    else_status = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        parsed = _coherence_compare(node.test)
        if parsed is None:
            continue
        symbol, threshold = parsed
        text = _status_constant(node.body)
        compares.append(
            {
                "op": symbol,
                "ready_mark": bool(text and _READY in text),
                "status": text,
                "threshold": threshold,
            }
        )
        orelse_is_if = len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)
        if node.orelse and not orelse_is_if:
            else_status = _status_constant(node.orelse)
    ready = next((item for item in compares if item["ready_mark"]), None)
    later_buried = False
    for index, item in enumerate(compares):
        if item["op"] != ">":
            continue
        for earlier in compares[:index]:
            if earlier["op"] == ">=" and earlier["threshold"] <= item["threshold"]:
                later_buried = True
    return {
        "compares": compares,
        "else_status": else_status,
        "evidence_tag": "cited",
        "later_compare_buried_under_a_lower_band": later_buried,
        "ready_mark": _READY,
        "ready_threshold": None if ready is None else ready["threshold"],
        "source": "aureon.utils.aureon_queen_hive_mind.QueenHiveMind.get_auris_coherence",
    }


def _window_matches_else(coherence: float | None, ladder: dict[str, Any]) -> bool | None:
    if coherence is None:
        return None
    for item in ladder["compares"]:
        threshold = float(item["threshold"])
        if item["op"] == ">=" and coherence >= threshold:
            return False
        if item["op"] == ">" and coherence > threshold:
            return False
    return True


def _label_spread_clock(pack: dict[str, Any], labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Where the stored bid/ask prints sit relative to the labelled decision closes."""

    prints = pack.get("spread_prints") if isinstance(pack.get("spread_prints"), list) else []
    times: list[int] = []
    for item in prints:
        if not isinstance(item, dict):
            continue
        stamp = _optional_count(item.get("time"))
        if stamp is not None:
            times.append(stamp)
    closes = [int(row["decision_close_unix"]) for row in labels if _optional_count(row.get("decision_close_unix")) is not None]
    last_close = max(closes) if closes else None
    first_print = min(times) if times else None
    gap = None if first_print is None or last_close is None else first_print - last_close
    usable = 0 if last_close is None else sum(1 for stamp in times if stamp <= last_close)
    known = sum(1 for row in labels if row.get("spread_known_at_decision") is True)
    return {
        "evidence_tag": "measured",
        "first_print_minus_last_labelled_close_seconds": gap,
        "first_print_unix": first_print,
        "labels_with_spread_known": known,
        "last_labelled_decision_close_unix": last_close,
        "prints": len(times),
        "prints_at_or_before_last_labelled_close": usable,
    }


def _call_coherence(queen: Any, texture: dict[str, float]) -> tuple[float | None, str]:
    coherence, status = queen.get_auris_coherence(texture)
    if coherence is None:
        return None, str(status)
    return float(coherence), str(status)


def _consider(
    best: dict[str, Any] | None,
    coherence: float | None,
    status: str,
    texture: dict[str, float],
) -> dict[str, Any] | None:
    if coherence is None:
        return best
    if best is None or coherence > float(best["coherence"]):
        return {"coherence": coherence, "inputs": dict(texture), "status": status}
    return best


def _formula_ceiling(queen: Any) -> dict[str, Any]:
    """Highest coherence the existing formulas returned on a stated sweep.

    The corner is volatility 0, volume 1, spread 1. In ``_auris_role_value``,
    for volatility at or above 0, volume in [0, 1], and spread in [0, 1],
    Tiger, Hummingbird, and Panda do not rise as volatility rises, Falcon and
    CargoShip do not rise as volume falls, and Deer does not rise as spread
    falls.     Momentum is swept from -2 to 4 so the positive side, where Owl adds
    its bonus, covers a full repeat after Falcon has clamped. This is not
    a new threshold and it is not a trade.
    """

    calls = 0
    ready_marks = 0
    best: dict[str, Any] | None = None
    for step in range(-2000, 4001):
        texture = {"momentum": step / 1000, "spread": 1.0, "volatility": 0.0, "volume": 1.0}
        coherence, status = _call_coherence(queen, texture)
        calls += 1
        if _READY in status:
            ready_marks += 1
        best = _consider(best, coherence, status, texture)
    sweep_highest = None if best is None else float(best["coherence"])
    probes = 0
    probe_highest = None
    if best is not None:
        momentum = float(best["inputs"]["momentum"])
        for shift in (-4.0, -2.0, 2.0, 4.0):
            texture = {"momentum": momentum + shift, "spread": 1.0, "volatility": 0.0, "volume": 1.0}
            coherence, status = _call_coherence(queen, texture)
            calls += 1
            probes += 1
            if _READY in status:
                ready_marks += 1
            if coherence is not None and (probe_highest is None or coherence > probe_highest):
                probe_highest = coherence
            best = _consider(best, coherence, status, texture)
    corner_highest = sweep_highest
    grid_best: dict[str, Any] | None = None
    grid_calls = 0
    for volatility in (0.0, 0.3, 1.0):
        for volume in (0.0, 1.0):
            for spread in (0.0, 1.0):
                for step in range(-40, 41):
                    texture = {
                        "momentum": step / 20,
                        "spread": spread,
                        "volatility": volatility,
                        "volume": volume,
                    }
                    coherence, status = _call_coherence(queen, texture)
                    calls += 1
                    grid_calls += 1
                    if _READY in status:
                        ready_marks += 1
                    grid_best = _consider(grid_best, coherence, status, texture)
                    best = _consider(best, coherence, status, texture)
    highest = None if best is None else float(best["coherence"])
    grid_highest = None if grid_best is None else float(grid_best["coherence"])
    return {
        "calls": calls,
        "confirmation_grid_calls": grid_calls,
        "confirmation_grid_exceeded_corner": bool(
            grid_highest is not None and corner_highest is not None and grid_highest > corner_highest
        ),
        "confirmation_grid_highest_coherence": grid_highest,
        "domain": (
            "momentum from -2 to 4 by 0.001 at volatility 0, volume 1, spread 1; "
            "plus that argmax shifted by -4, -2, 2, and 4; "
            "plus a confirmation grid of volatility in {0, 0.3, 1}, volume in {0, 1}, "
            "spread in {0, 1}, momentum from -2 to 2 by 0.05. "
            "Negative volatility is not in this sweep. derive_fields does not emit it"
        ),
        "period_note": (
            "cited from _auris_role_value: once abs(momentum) is at least 1, Falcon is clamped at 1, "
            "and the sine and cosine terms repeat every 2. "
            "The sweep covers a full repeat of that pair on the positive side, where Owl adds its bonus"
        ),
        "period_note_evidence_tag": "cited",
        "momentum_sweep_highest_coherence": sweep_highest,
        "evidence_tag": "measured",
        "highest_coherence": highest,
        "highest_inputs": None if best is None else best["inputs"],
        "highest_status": None if best is None else best["status"],
        "period_probes": probes,
        "period_probe_highest_coherence": probe_highest,
        "ready_mark": _READY,
        "ready_marks": ready_marks,
    }


def _clock_sentence(clock: dict[str, Any]) -> str:
    prints = int(clock["prints"])
    usable = int(clock["prints_at_or_before_last_labelled_close"])
    known = int(clock["labels_with_spread_known"])
    gap = clock["first_print_minus_last_labelled_close_seconds"]
    if prints == 0:
        return "the pack has no spread prints, so Deer has no spread at any labelled decision close"
    if usable == 0 and isinstance(gap, int) and gap > 0:
        return (
            "spread prints at or before a labelled decision close: 0; "
            f"first spread print is {gap} seconds after the last labelled decision close"
        )
    return (
        f"spread prints at or before the last labelled decision close: {usable}; "
        f"labels with spread known at the decision: {known}"
    )


def _diagnosis(
    labels: list[dict[str, Any]],
    *,
    window_coherence: float | None,
    window_status: str,
    clock: dict[str, Any],
    ceiling: dict[str, Any],
    ladder: dict[str, Any],
) -> dict[str, Any]:
    numeric = sum(1 for row in labels if row.get("coherence") is not None)
    no_data = sum(1 for row in labels if row.get("coherence_status") == "no_data")
    matched_else = _window_matches_else(window_coherence, ladder)
    ready_threshold = ladder.get("ready_threshold")
    below_ready = (
        ceiling["ready_marks"] == 0
        and ready_threshold is not None
        and ceiling["highest_coherence"] is not None
        and float(ceiling["highest_coherence"]) < float(ready_threshold)
    )
    if window_coherence is None:
        window_sentence = f"window call status: {window_status}; the window call has no numeric coherence"
    elif _READY in window_status:
        window_sentence = (
            f"window call status: {window_status}; "
            f"window coherence {window_coherence} contains the ready mark"
        )
    else:
        window_sentence = (
            f"window call status: {window_status}; "
            f"window coherence {window_coherence} does not contain the ready mark"
        )
    order_bits = [
        f"coherence {item['op']} {item['threshold']}"
        + (" (ready mark)" if item["ready_mark"] else "")
        for item in ladder["compares"]
    ]
    if matched_else is True:
        order_sentence = (
            "cited status compares in order: "
            + ", ".join(order_bits)
            + "; the window coherence matches none of them, so the final else is the branch that ran"
        )
    elif matched_else is False:
        order_sentence = (
            "cited status compares in order: "
            + ", ".join(order_bits)
            + "; the window coherence matches an earlier branch"
        )
    else:
        order_sentence = "cited status compares in order: " + ", ".join(order_bits)
    if ladder.get("later_compare_buried_under_a_lower_band") and matched_else is True:
        order_sentence += (
            "; a later compare sits under a lower band and does not run, "
            "and this window figure is below that lower band, so the order is not what keeps this window off the ready mark"
        )
    if int(clock["prints_at_or_before_last_labelled_close"]) == 0:
        next_stage = (
            "next stage needs a public bid/ask history whose print times are at or before the labelled decision closes, "
            "so Deer can be scored on those bars without using a later print"
        )
    else:
        next_stage = (
            "spread prints already overlap at least one labelled decision close, "
            "so the missing piece is not the spread clock"
        )
    if below_ready:
        next_stage += (
            "; the ready mark stays off on this sweep of the existing formulas, "
            "including volatility 0, volume 1, and spread 1"
        )
    next_stage += (
        "; this stage does not change the node formulas or the ready mark, "
        "does not copy a later spread print onto an earlier bar, and does not invent outcome labels"
    )
    summary = (
        f"{_clock_sentence(clock)}; "
        f"labelled bars with a numeric coherence: {numeric}; "
        f"labelled bars returned no_data: {no_data}; "
        f"{window_sentence}; "
        f"formula sweep highest coherence {ceiling['highest_coherence']}; "
        f"ready marks {ceiling['ready_marks']} of {ceiling['calls']}; "
        f"{order_sentence}; "
        f"{next_stage}"
    )
    return {
        "evidence_tag": "measured",
        "formula_ceiling": ceiling,
        "labelled_bars_no_data": no_data,
        "labelled_bars_with_coherence": numeric,
        "live_trading": False,
        "next_stage": next_stage,
        "orders_placed": False,
        "ready_mark_below_sweep": below_ready,
        "spread_clock": clock,
        "status_ladder": ladder,
        "summary": summary,
        "window_matches_final_else": matched_else,
    }


def _trade_readiness(
    pack: dict[str, Any],
    labels: list[dict[str, Any]] | None,
    *,
    queen: Any,
    window_coherence: float | None,
    window_status: str,
) -> dict[str, Any]:
    """Score paper labels with the method's own ready-to-trade status."""

    base = {
        "entries": 0,
        "entries_not_higher": 0,
        "entries_with_higher_close": 0,
        "evidence_tag": "no_data",
        "filled_outcomes": 0,
        "filled_outcome_note": "this checkout has no filled order outcome for this series",
        "live_trading": False,
        "orders_placed": False,
        "outcome_labels": "missing",
        "paper_labels": 0,
        "real_orders": _ORDERS_OFF,
        "release_boundary": "HOLD",
    }
    if labels is None:
        base["reason"] = "no market series and no trade-outcome labels"
        base["verdict"] = "HOLD"
        return base
    if not labels:
        window = pack.get("time_range") if isinstance(pack.get("time_range"), dict) else {}
        base["reason"] = (
            f"market series loaded from {pack.get('key_group')} {pack.get('symbol')} "
            f"{window.get('start')} to {window.get('end')}; "
            "a next-bar paper label could not be formed; filled outcomes: 0; "
            "release boundary stays HOLD"
        )
        base["verdict"] = "HOLD"
        return base
    entries = [row for row in labels if row.get("entered")]
    higher = sum(1 for row in entries if row.get("paper_outcome") == "up")
    not_higher = len(entries) - higher
    clownfish_reading = sum(1 for row in labels if row.get("clownfish") == "reading")
    owl_reading = sum(1 for row in labels if row.get("owl") == "reading")
    held = sorted({name for row in labels for name in row.get("nodes_without_reading") or []})
    held_text = ", ".join(held) if held else "none"
    if entries and higher == len(entries):
        verdict = "pass"
        because = "measured pass: every paper long the method marked ready to trade had a higher next close"
    elif not entries:
        verdict = "fail"
        because = "measured fail: get_auris_coherence did not mark any labelled bar ready to trade"
    else:
        verdict = "fail"
        because = (
            "measured fail: a paper long the method marked ready to trade "
            "did not have a higher next close"
        )
    diagnosis = _diagnosis(
        labels,
        window_coherence=window_coherence,
        window_status=window_status,
        clock=_label_spread_clock(pack, labels),
        ceiling=_formula_ceiling(queen),
        ladder=_status_ladder(type(queen).get_auris_coherence),
    )
    reason = (
        f"paper trade-outcome labels: {len(labels)} next-bar close-to-close returns "
        f"from {pack.get('key_group')} {pack.get('symbol')}; "
        "the prices are measured and the outcomes are paper; "
        "filled outcomes: 0; "
        f"Clownfish readings {clownfish_reading} of {len(labels)}; "
        f"Owl readings {owl_reading} of {len(labels)}; "
        f"nodes without a reading on a labelled bar: {held_text}; "
        f"ready-to-trade paper entries: {len(entries)}; "
        f"entries with a higher next close: {higher}; "
        f"entries without a higher next close: {not_higher}; "
        "a spread print is used only when its time is at or before the decision close; "
        f"{diagnosis['summary']}; "
        f"{because}; "
        "release boundary stays HOLD"
    )
    return {
        "clownfish_readings": clownfish_reading,
        "diagnosis": diagnosis,
        "entries": len(entries),
        "entries_not_higher": not_higher,
        "entries_with_higher_close": higher,
        "evidence_tag": "measured",
        "filled_outcomes": 0,
        "filled_outcome_note": (
            "this checkout has no filled order outcome for this series; the labels are paper"
        ),
        "label_clock": (
            "decision at the close of bar i uses bars through i and spread prints at or before that close; "
            "the paper label is the next close against this close"
        ),
        "labels": labels,
        "live_trading": False,
        "nodes_without_reading_on_a_label": held,
        "orders_placed": False,
        "outcome_labels": "paper",
        "owl_readings": owl_reading,
        "paper_labels": len(labels),
        "real_orders": _ORDERS_OFF,
        "reason": reason,
        "release_boundary": "HOLD",
        "verdict": verdict,
    }


def _run_auris(pack: dict[str, Any]) -> dict[str, Any]:
    queen = _reader()
    omitted_coherence, omitted_status = queen.get_auris_coherence(None)
    zeros = dict.fromkeys(_INPUTS, 0.0)
    probed = queen.read_auris_nodes(zeros)
    hold = sorted(name for name, item in probed.items() if item.get("value") is None)
    loaded = pack.get("verdict") == "loaded"
    texture = _texture(pack) if loaded else {}
    if loaded:
        coherence, status = queen.get_auris_coherence(texture)
        raw_nodes = queen.read_auris_nodes(texture)
        nodes = _plain(raw_nodes)
        missing = sorted(name for name, item in raw_nodes.items() if item.get("value") is None)
        window = pack.get("time_range") if isinstance(pack.get("time_range"), dict) else {}
        market_note = (
            f"Loaded {pack.get('bar_count')} closed {pack.get('interval')} bars of {pack.get('symbol')} "
            f"from {pack.get('key_group')} ({pack.get('source')}), "
            f"{window.get('start')} to {window.get('end')}. "
            f"Spread input clock: {_spread_clock(pack)}. "
            "The four inputs are the measured window statistics in the pack. "
            "Key material was not read. No order was sent."
        )
        market_data: dict[str, float] | None = texture
        trade = _trade_readiness(
            pack,
            _paper_labels(queen, pack),
            queen=queen,
            window_coherence=None if coherence is None else float(coherence),
            window_status=str(status),
        )
    else:
        coherence, status = omitted_coherence, omitted_status
        nodes = None
        missing = None
        market_data = None
        market_note = "no market series was supplied, so the omitted call is no_data"
        trade = _trade_readiness(
            pack,
            None,
            queen=queen,
            window_coherence=None if coherence is None else float(coherence),
            window_status=str(status),
        )
    return {
        "source": "aureon.utils.aureon_queen_hive_mind.QueenHiveMind.get_auris_coherence",
        "market_data": market_data,
        "market_data_note": market_note,
        "status": status,
        "nodes": nodes,
        "coherence": None if coherence is None else float(coherence),
        "coherence_status": status,
        "coherence_evidence": "measured" if loaded and coherence is not None else "no_data",
        "market_nodes_without_reading": missing,
        "omitted_call": {
            "coherence": None if omitted_coherence is None else float(omitted_coherence),
            "market_data": None,
            "note": "get_auris_coherence(None) remains no_data. It is not the loaded series.",
            "status": omitted_status,
        },
        "zero_input_probe": {
            "inputs": zeros,
            "note": "clamp-bound probe of the existing formulas, not a market reading; node values are not published",
            "nodes_without_reading": hold,
        },
        "hold_nodes": hold,
        "hold_reason": (
            "these nodes have no value when volatility, momentum, volume, and spread are all present as 0"
            if hold
            else "every node returned a value when volatility, momentum, volume, and spread are present as 0"
        ),
        "live_trading": False,
        "orders_placed": False,
        "trade_readiness": trade,
    }


def _ftcp_record(item: Any) -> dict[str, Any]:
    return {
        "timestamp": float(item.timestamp),
        "knot_index": int(item.knot_index),
        "curvature": float(item.curvature),
        "interval_ratio": float(item.interval_ratio),
        "phi_match": float(item.phi_match),
        "g_eff": float(item.g_eff),
        "local_contrast": float(item.local_contrast),
        "is_valid": bool(item.is_valid),
    }


def _lhe_record(item: Any) -> dict[str, Any]:
    return {
        "timestamp": float(item.timestamp),
        "lighthouse_intensity": float(item.lighthouse_intensity),
        "c_linear": float(item.c_linear),
        "c_nonlinear": float(item.c_nonlinear),
        "c_phi": float(item.c_phi),
        "g_eff": float(item.g_eff),
        "q_anomaly": float(item.q_anomaly),
        "confidence": float(item.confidence),
        "event_type": str(item.event_type.value),
    }


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return float(value)
    item = getattr(value, "item", None)
    if callable(item):
        return _plain(item())
    return str(value)


def _run_qgita(values: list[float], times: list[float], series_name: str) -> dict[str, Any]:
    from aureon.wisdom.aureon_qgita_framework import QGITAMarketAnalyzer

    analyzer = QGITAMarketAnalyzer()
    for stamp, value in zip(times, values, strict=True):
        analyzer.feed_price(float(value), timestamp=float(stamp))
    raw = analyzer.analyze()
    stage1 = raw.get("stage1") if isinstance(raw.get("stage1"), dict) else {}
    stage2 = raw.get("stage2") if isinstance(raw.get("stage2"), dict) else {}
    valid = list(stage1.get("valid_ftcps") or [])
    events = list(stage2.get("lighthouse_events") or [])
    coherence = None if raw.get("coherence") is None else _plain(raw.get("coherence"))
    statistics = None if raw.get("statistics") is None else _plain(raw.get("statistics"))
    plain_signals = None if raw.get("signals") is None else _plain(raw.get("signals"))
    regime = None if raw.get("regime") is None else _plain(raw.get("regime"))
    return {
        "source": "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze",
        "series": series_name,
        "detector": {
            "epsilon": float(analyzer.ftcp_detector.epsilon),
            "theta": float(analyzer.ftcp_detector.theta),
            "alpha": float(analyzer.ftcp_detector.alpha),
            "adaptive_threshold": bool(analyzer.ftcp_detector.adaptive_threshold),
        },
        "lighthouse_threshold_sigma": float(analyzer.lighthouse.threshold_sigma),
        "samples_fed": len(values),
        "samples_analyzed": None if not isinstance(statistics, dict) else statistics.get("total_samples"),
        "signal_note": "the direction is the analyzer's return. It is not an order and it has no outcome label",
        "buffer_note": "QGITAMarketAnalyzer keeps a 1000-sample buffer; analyze sees that tail",
        "status": raw.get("status"),
        "ftcp_count": _optional_count(stage1.get("ftcp_count")),
        "valid_ftcps": [_ftcp_record(item) for item in valid],
        "max_g_eff": _optional_float(stage1.get("max_g_eff")),
        "lhe_count": _optional_count(stage2.get("lhe_count")),
        "lighthouse_events": [_lhe_record(item) for item in events],
        "lighthouse_intensity": _plain(stage2.get("current_lighthouse_intensity")),
        "detection_threshold": _plain(stage2.get("detection_threshold")),
        "coherence": coherence,
        "regime": regime,
        "signals": plain_signals,
        "statistics": statistics,
        "detection_rate": None,
        "false_alarm_rate": None,
        "rates_verdict": "HOLD",
        "rates_reason": (
            "this series has no signal-in-noise labels in the repo, "
            "so the analyzer counts are not a detection rate or a false-alarm rate"
        ),
        "orders_placed": False,
    }


def _market_qgita(pack: dict[str, Any]) -> dict[str, Any]:
    source = "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze"
    if pack.get("verdict") != "loaded":
        return {
            "source": source,
            "series": "reports/measured/market_series.json",
            "series_class": "public-market",
            "evidence_tag": "hold",
            "key_group": pack.get("key_group"),
            "verdict": "HOLD",
            "reason": pack.get("reason") or "no market series was loaded",
            "detection_rate": None,
            "false_alarm_rate": None,
            "rates_verdict": "HOLD",
            "orders_placed": False,
            "authenticated": False,
        }
    bars = pack.get("bars") if isinstance(pack.get("bars"), list) else []
    values = [float(bar["close"]) for bar in bars]
    times = [float(bar["open_time"]) for bar in bars]
    window = pack.get("time_range") if isinstance(pack.get("time_range"), dict) else {}
    record = _run_qgita(values, times, str(pack.get("symbol") or "market_series"))
    record["series_class"] = "public-market"
    record["evidence_tag"] = "measured"
    record["key_group"] = pack.get("key_group")
    record["authenticated"] = False
    record["time_range"] = window
    record["timestamps"] = "venue bar open time in unix seconds; price is the bar close"
    record["provenance"] = (
        f"{pack.get('source')} {pack.get('symbol')} {pack.get('interval')} "
        f"key-group {pack.get('key_group')}. "
        f"{window.get('start')} to {window.get('end')}. "
        "Prices are bar closes. Timestamps are venue bar open times. No order was sent."
    )
    field_names: list[str] = []
    for bar in bars:
        if isinstance(bar, dict):
            field_names.extend(str(key) for key in bar)
    apply_rates_hold(
        record,
        rates_hold_receipt(
            samples=len(values),
            field_names=field_names,
            series_kind="public-market",
            paper_outcomes_are_not_signal_labels=True,
        ),
    )
    return record


def _load_lambda(root: Path) -> dict[str, Any]:
    path = root / DERIVED_SERIES
    if not path.is_file():
        return {
            "verdict": "HOLD",
            "path": DERIVED_SERIES,
            "reason": "the derived series is not in this checkout",
            "values": [],
        }
    values: list[float] = []
    first_dt = ""
    last_dt = ""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        if DERIVED_COLUMN not in fieldnames:
            return {
                "verdict": "HOLD",
                "path": DERIVED_SERIES,
                "reason": f"column {DERIVED_COLUMN} is missing",
                "values": [],
            }
        event_positive_counts = {
            name: 0 for name in DERIVED_EVENT_COLUMNS if name in fieldnames
        }
        for row in reader:
            stamp = str(row.get("datetime") or "")
            try:
                values.append(float(row[DERIVED_COLUMN]))
            except (TypeError, ValueError):
                continue
            for name in event_positive_counts:
                if str(row.get(name) or "").strip() in {"1", "1.0"}:
                    event_positive_counts[name] += 1
            if stamp and not first_dt:
                first_dt = stamp
            if stamp:
                last_dt = stamp
    if len(values) < 3:
        return {
            "verdict": "HOLD",
            "path": DERIVED_SERIES,
            "reason": "the column has fewer than three numeric samples",
            "values": values,
        }
    return {
        "verdict": "loaded",
        "path": DERIVED_SERIES,
        "column": DERIVED_COLUMN,
        "values": values,
        "rows": len(values),
        "datetime_first": first_dt,
        "datetime_last": last_dt,
        "field_names": fieldnames,
        "event_positive_counts": event_positive_counts,
    }


def _method_tree(method: Any) -> ast.AST:
    return ast.parse(textwrap.dedent(inspect.getsource(method)))


def _tree_names_lambda(tree: ast.AST) -> bool:
    needles = set(_LAMBDA_KEYS)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in needles:
            return True
        if isinstance(node, ast.Attribute) and node.attr in needles:
            return True
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in needles:
            return True
    return False


def _cited_auris_input_keys(tree: ast.AST) -> list[str]:
    """String keys ``_auris_role_value`` passes to ``_auris_input``. Cited from that method."""

    keys: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else None
        if name != "_auris_input":
            continue
        arg = node.args[1]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            keys.append(arg.value)
    return sorted(set(keys))


def _coherence_call(queen: Any, market: dict[str, float] | None) -> dict[str, Any]:
    coherence, status = queen.get_auris_coherence(market)
    return {
        "coherence": None if coherence is None else float(coherence),
        "evidence_tag": "measured",
        "status": status,
    }


def _join_auris_to_lambda(series: list[float], texture: dict[str, float] | None) -> dict[str, Any]:
    """Pass formula-path Λ(t) into ``get_auris_coherence`` and record what that call returns.

    The market-texture formulas already in ``_auris_role_value`` are not changed.
    A lambda key the method does not read leaves the coherence figure where it was.
    """

    from aureon.utils.aureon_queen_hive_mind import QueenHiveMind

    queen = _reader()
    omitted = _coherence_call(queen, None)
    role_tree = _method_tree(QueenHiveMind._auris_role_value)
    coherence_tree = _method_tree(QueenHiveMind.get_auris_coherence)
    keys_read = _cited_auris_input_keys(role_tree)
    role_names_lambda = _tree_names_lambda(role_tree)
    names_lambda = _tree_names_lambda(coherence_tree)
    values = [float(item) for item in series]
    lambda_last = values[-1]
    only_lambda = {
        key: _coherence_call(queen, {key: lambda_last})
        for key in _LAMBDA_KEYS
    }
    only_matches_omitted = all(
        item["coherence"] is None and item["status"] == omitted["status"]
        for item in only_lambda.values()
    )
    supplied = dict(texture or {})
    texture_call = _coherence_call(queen, supplied) if supplied else None
    matches_texture = True
    compared = 0
    if texture_call is not None:
        base_coherence = texture_call["coherence"]
        base_status = texture_call["status"]
        for value in values:
            for key in _LAMBDA_KEYS:
                market = dict(supplied)
                market[key] = value
                coherence, status = queen.get_auris_coherence(market)
                coherence = None if coherence is None else float(coherence)
                compared += 1
                if coherence != base_coherence or status != base_status:
                    matches_texture = False
    lambda_keys_are_read = any(key in keys_read for key in _LAMBDA_KEYS)
    consumed = (
        names_lambda
        or role_names_lambda
        or lambda_keys_are_read
        or not only_matches_omitted
        or not matches_texture
    )
    measurement = {
        "calls_compared_with_texture": compared,
        "evidence_tag": "measured",
        "keys_passed": list(_LAMBDA_KEYS),
        "lambda_last": lambda_last,
        "lambda_max": max(values),
        "lambda_min": min(values),
        "lambda_source": "aureon.harmonic.aureon_harmonic_reality.HarmonicRealityField.step",
        "live_trading": False,
        "only_lambda": only_lambda,
        "only_lambda_matches_omitted_call": only_matches_omitted,
        "omitted_call": omitted,
        "orders_placed": False,
        "samples": len(values),
        "texture_call": texture_call,
        "texture_with_lambda_matches_texture": matches_texture if texture_call is not None else None,
    }
    cited = {
        "auris_role_value_names_lambda": role_names_lambda,
        "evidence_tag": "cited",
        "get_auris_coherence_names_lambda": names_lambda,
        "keys_read_by_auris_role_value": keys_read,
        "source": (
            "aureon.utils.aureon_queen_hive_mind.QueenHiveMind._auris_role_value "
            "and QueenHiveMind.get_auris_coherence"
        ),
    }
    if consumed:
        verdict = "HOLD"
        reason = (
            "HarmonicRealityField.step Λ(t) was passed into get_auris_coherence "
            "and the reading changed, or the method names that field. "
            "This path does not add a formula, so that change is not claimed as a join. "
            "No order was placed. Go-live stays HOLD."
        )
        evidence_tag = "measured"
    else:
        verdict = "HOLD"
        texture_text = (
            f"Beside the loaded market texture, coherence stayed {texture_call['coherence']} "
            f"with status {texture_call['status']!r} for all {len(values)} formula-series samples "
            f"under those keys ({compared} calls)."
            if texture_call is not None
            else "No market texture was loaded, so the beside-texture comparison was not run."
        )
        reason = (
            "HarmonicRealityField.step Λ(t) was passed into get_auris_coherence "
            f"under the keys {', '.join(_LAMBDA_KEYS)}. "
            f"Each only-lambda call returned coherence null and status {omitted['status']!r}, "
            "the same as get_auris_coherence(None). "
            f"{texture_text} "
            f"Cited from _auris_role_value, the keys read are {', '.join(keys_read)}. "
            "Neither _auris_role_value nor get_auris_coherence names lambda. "
            "On this formula series the coherence figure was unchanged by those keys. "
            "No formula was added. No order was placed. Go-live stays HOLD."
        )
        evidence_tag = "inferred"
    return {
        "cited": cited,
        "evidence_tag": evidence_tag,
        "go_live": "HOLD",
        "measurement": measurement,
        "reason": reason,
        "verdict": verdict,
    }


def evaluate_brain(root: Path | None = None) -> dict[str, Any]:
    """Run the HNC formula, Auris coherence, and the QGITA analyzer.

    Importing the measured modules prints relay banners. Those lines are not
    part of the measurement, so they are kept off the returned report's stdout.
    """

    with contextlib.redirect_stdout(io.StringIO()):
        return _evaluate_brain(root)


def _evaluate_brain(root: Path | None = None) -> dict[str, Any]:
    root = Path(root or Path.cwd())
    previous_orders = os.environ.get("AUREON_DISABLE_REAL_ORDERS")
    os.environ["AUREON_DISABLE_REAL_ORDERS"] = "1"
    try:
        return _evaluate_brain_body(root)
    finally:
        if previous_orders is None:
            os.environ.pop("AUREON_DISABLE_REAL_ORDERS", None)
        else:
            os.environ["AUREON_DISABLE_REAL_ORDERS"] = previous_orders


def _evaluate_brain_body(root: Path) -> dict[str, Any]:
    pack = load_market_series(root)
    hnc = _run_hnc()
    auris = _run_auris(pack)
    loaded = _load_lambda(root)
    provenance = (
        f"{DERIVED_SERIES} column {DERIVED_COLUMN} is a precomputed derived series. "
        "This checkout has no generator for the column. It is not public market data."
    )
    if loaded["verdict"] != "loaded":
        derived = {
            "source": "aureon.wisdom.aureon_qgita_framework.QGITAMarketAnalyzer.analyze",
            "series": DERIVED_SERIES,
            "series_class": "derived",
            "evidence_tag": "cited-unverified",
            "provenance": provenance,
            "committed_in": DERIVED_COMMIT,
            "verdict": "HOLD",
            "reason": loaded["reason"],
            "detection_rate": None,
            "false_alarm_rate": None,
            "rates_verdict": "HOLD",
        }
    else:
        values = loaded["values"]
        derived = _run_qgita(values, [float(index) for index in range(len(values))], DERIVED_SERIES)
        derived["column"] = DERIVED_COLUMN
        derived["series_class"] = "derived"
        derived["evidence_tag"] = "cited-unverified"
        derived["provenance"] = (
            f"{provenance} {loaded['rows']} numeric rows, "
            f"{loaded['datetime_first']} to {loaded['datetime_last']}, committed in {DERIVED_COMMIT}."
        )
        derived["committed_in"] = DERIVED_COMMIT
        derived["datetime_first"] = loaded["datetime_first"]
        derived["datetime_last"] = loaded["datetime_last"]
        derived["timestamps"] = (
            "sample index. analyze_price_stream uses range(len(prices)) when no timestamps are passed"
        )
        apply_rates_hold(
            derived,
            rates_hold_receipt(
                samples=len(values),
                field_names=list(loaded.get("field_names") or []),
                series_kind="derived",
                rejected_event_columns=dict(loaded.get("event_positive_counts") or {}),
            ),
        )
    hnc_values = list(hnc["series"])
    on_lambda = _run_qgita(
        hnc_values,
        [index * float(hnc["dt"]) for index in range(len(hnc_values))],
        "hnc_lambda_series",
    )
    on_lambda["timestamps"] = "step index times HarmonicRealityField.dt"
    apply_rates_hold(
        on_lambda,
        rates_hold_receipt(
            samples=len(hnc_values),
            field_names=[],
            series_kind="formula",
        ),
    )
    return {
        "schema": "aureon.brain-proof.v1",
        "live_trading": False,
        "orders_placed": False,
        "external_llm": False,
        "cognition": "internal",
        "note": _NOTE,
        "hnc": hnc,
        "market_series": series_summary(pack),
        "auris": auris,
        "qgita": {
            "derived_series": derived,
            "on_hnc_series": on_lambda,
            "on_market_series": _market_qgita(pack),
        },
        "together": {
            "qgita_on_the_formula_series": RATES_HOLD_VERDICT,
            "auris_joined_to_lambda": _join_auris_to_lambda(
                hnc_values,
                auris.get("market_data") if isinstance(auris.get("market_data"), dict) else None,
            ),
        },
    }


def _rate_line(block: dict[str, Any]) -> str:
    receipt = block.get("rates_receipt") if isinstance(block.get("rates_receipt"), dict) else {}
    ingredient = receipt.get("missing_ingredient")
    if ingredient:
        return f"Detection rate **{block.get('rates_verdict')}**. Missing ingredient: {ingredient}."
    return f"Detection rate **{block.get('rates_verdict')}**."


def render_brain_markdown(report: dict[str, Any]) -> str:
    hnc = report["hnc"]
    auris = report["auris"]
    public = report["qgita"]["derived_series"]
    on_lambda = report["qgita"]["on_hnc_series"]
    on_market = report["qgita"].get("on_market_series") or {}
    series_nodes = auris.get("market_nodes_without_reading")
    series_text = "no series loaded" if series_nodes is None else (", ".join(series_nodes) or "none")
    lines = [
        "# HNC, Auris coherence, and QGITA",
        "",
        report["note"],
        "",
        "No outside model was called. Live trading stayed off. No order was placed.",
        (
            f"HNC formula path, multiverse off: state `{hnc['state']}`, "
            f"coherence `{hnc['coherence']}`, last Λ(t) `{hnc['lambda_last']}`, "
            f"steps `{hnc['steps']}`."
        ),
        f"Multiverse extension: **{hnc['multiverse_extension']['verdict']}**. {hnc['multiverse_extension']['reason']}",
        (
            f"Auris coherence `{auris['coherence']}` with status `{auris['coherence_status']}`. "
            f"Zero-input nodes without a reading: {', '.join(auris['hold_nodes']) or 'none'}. "
            f"Window nodes without a reading: {series_text}. "
            "The window is one call on the whole pack and includes the latest spread print, "
            "even when that print is after the OHLC bars. "
            "Labelled bars are a separate clock: a spread print counts only at or before the decision close."
        ),
        f"Trade readiness: **{auris['trade_readiness']['verdict']}**. {auris['trade_readiness']['reason']}",
        (
            f"QGITA on the derived series `{public.get('series')}` ({public.get('evidence_tag')}): "
            f"status `{public.get('status', public.get('verdict'))}`, "
            f"FTCP count `{public.get('ftcp_count')}`, lighthouse events `{public.get('lhe_count')}`. "
            f"{_rate_line(public)} "
            f"Clock: {public.get('timestamps', '')}"
        ),
        (
            f"QGITA on the formula series: FTCP count `{on_lambda.get('ftcp_count')}`, "
            f"lighthouse events `{on_lambda.get('lhe_count')}`. "
            f"{_rate_line(on_lambda)} "
            f"Clock: {on_lambda.get('timestamps', '')}"
        ),
        (
            f"QGITA on the public series `{on_market.get('series')}` ({on_market.get('evidence_tag')}, "
            f"key group `{on_market.get('key_group')}`): "
            f"status `{on_market.get('status', on_market.get('verdict'))}`, "
            f"FTCP count `{on_market.get('ftcp_count')}`, lighthouse events `{on_market.get('lhe_count')}`. "
            f"{_rate_line(on_market)} "
            f"Clock: {on_market.get('timestamps', '')}"
        ),
        (
            "Auris joined to Λ(t): **"
            f"{report['together']['auris_joined_to_lambda']['verdict']}**. "
            f"{report['together']['auris_joined_to_lambda']['reason']}"
        ),
        "",
    ]
    return "\n".join(lines)
