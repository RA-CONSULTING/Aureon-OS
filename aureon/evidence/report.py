"""RESULTS.md and the tagged claim list. Wording follows the numbers."""

from __future__ import annotations

from typing import Any


def with_ci(point: Any, interval: Any) -> str:
    if not isinstance(interval, list) or len(interval) != 2:
        return fmt(point)
    return f"{fmt(point)} [{fmt(interval[0])}, {fmt(interval[1])}]"


def fmt(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(value, ".6g")
    return str(value)


def _claim(claim_id: str, tag: str, statement: str, *, asserted: bool = True) -> dict[str, Any]:
    return {
        "id": claim_id,
        "tag": tag,
        "asserted": asserted,
        "statement": statement.replace("|", "/"),
    }


def build_claims(hnc: dict[str, Any], auris: dict[str, Any], qgita: dict[str, Any]) -> list[dict[str, Any]]:
    formula = hnc["formula"]
    multiverse = hnc["multiverse"]
    baselines = formula["baselines"]
    claims: list[dict[str, Any]] = []

    claims.append(
        _claim(
            "hnc.formula.window",
            "measured",
            (
                f"HarmonicRealityField.step with enable_multiverse false, {formula['steps']} steps, "
                f"seed {formula['series_reference_seed']}: state {formula['state']}, "
                f"coherence {fmt(formula['coherence'])}, boundedness {fmt(formula['boundedness'])}, "
                f"echo magnitude ratio {fmt(formula['echo_magnitude_ratio'])}, "
                f"sample rate {fmt(formula['sample_rate'])}, "
                f"lambda min {fmt(formula['series_min'])}, max {fmt(formula['series_max'])}, "
                f"finite {fmt(formula['finite'])}."
            ),
        )
    )
    seed_same = formula["max_abs_diff_across_seeds"] == 0.0 and formula["repeat_max_abs_diff"] == 0.0
    claims.append(
        _claim(
            "hnc.formula.seeds",
            "inferred",
            (
                "The formula-path series is unchanged across the recorded seeds and a repeat of seed "
                f"{formula['repeat_seed']}."
                if seed_same
                else (
                    "The formula-path series changed across seeds or on a repeat. "
                    f"max_abs_diff_across_seeds {fmt(formula['max_abs_diff_across_seeds'])}, "
                    f"repeat_max_abs_diff {fmt(formula['repeat_max_abs_diff'])}."
                )
            ),
        )
    )
    coherence = formula["coherence"]
    shuffled = baselines["shuffled_coherence"]
    gaussian = baselines["gaussian_coherence"]
    zero = baselines["zero_coherence"]
    if coherence > shuffled and coherence > gaussian:
        coherence_text = (
            "Formula-path coherence is higher than the shuffled-series baseline and the unit-Gaussian baseline "
            "under HarmonicRealityField._calculate_coherence."
        )
    elif coherence > shuffled:
        coherence_text = (
            "Formula-path coherence is higher than the shuffled-series baseline and is not higher than "
            "the unit-Gaussian baseline."
        )
    else:
        coherence_text = "Formula-path coherence is not higher than the shuffled-series baseline."
    claims.append(
        _claim(
            "hnc.formula.coherence_baselines",
            "inferred",
            (
                f"{coherence_text} Measured coherence {fmt(coherence)}, shuffled {fmt(shuffled)}, "
                f"gaussian {fmt(gaussian)}, zeros {fmt(zero)}."
            ),
        )
    )
    claims.append(
        _claim(
            "hnc.formula.echo_magnitude_ratio",
            "measured",
            (
                "The published echo figure is CausalEcho.get_echo_magnitude_ratio, also stored as "
                "get_echo_strength. It is min(1, abs(current*delayed) / (abs(current)*abs(delayed) + 1e-10)). "
                f"This run measured {format(formula['echo_magnitude_ratio'], '.12g')}. "
                "It is not a correlation."
            ),
        )
    )
    above = formula["modes_at_or_above_nyquist"]
    if above:
        nyquist_text = (
            f"{len(above)} substrate modes are at or above the Nyquist rate "
            f"{fmt(formula['nyquist_hz'])} Hz for sample rate {fmt(formula['sample_rate'])}: "
            f"{', '.join(fmt(freq) for freq in above)}."
        )
    else:
        nyquist_text = (
            f"Every substrate mode is strictly below the Nyquist rate {fmt(formula['nyquist_hz'])} Hz. "
            f"The rate used is {fmt(formula['sample_rate'])} Hz"
            f" (requested {fmt(formula['sample_rate_requested'])}). "
            "That rate is floor(2 * highest mode) + 1 when the request would not already clear Nyquist."
        )
    claims.append(_claim("hnc.formula.nyquist", "measured", nyquist_text))
    multi_same = (
        multiverse["max_abs_diff_across_seeds"] == 0.0 and multiverse["repeat_max_abs_diff"] == 0.0
    )
    claims.append(
        _claim(
            "hnc.multiverse.seeds",
            "inferred",
            (
                "The class-default multiverse path is unchanged across the recorded seeds and a repeat."
                if multi_same
                else (
                    "The multiverse path changed across seeds or on a repeat. "
                    f"max_abs_diff_across_seeds {fmt(multiverse['max_abs_diff_across_seeds'])}, "
                    f"repeat_max_abs_diff {fmt(multiverse['repeat_max_abs_diff'])}."
                )
            ),
        )
    )
    claims.append(
        _claim(
            "hnc.multiverse.versus_formula",
            "measured",
            (
                "Maximum absolute difference between the seed-0 formula series and the seed-0 multiverse series "
                f"is {fmt(formula['multiverse_max_abs_diff'])}. Multiverse coherence {fmt(multiverse['coherence'])}, "
                f"state {multiverse['state']}."
            ),
        )
    )

    claims.append(
        _claim(
            "auris.dependency",
            "measured",
            (
                f"Input-guard checks {auris['dependency_mismatches']} mismatches "
                f"out of {auris['dependency_checks']} node readings."
            ),
        )
    )
    withheld = (
        auris["numeric_coherence_cases"] == 0
        and auris["coherence_status_matches_null"] == auris["coherence_status_cases"]
    )
    claims.append(
        _claim(
            "auris.coherence_versus_null",
            "inferred",
            (
                "get_auris_coherence returned no number, and the same status as the null input, on every "
                f"synthetic case ({auris['coherence_status_matches_null']} of {auris['coherence_status_cases']}). "
                "These inputs are not separated from the null baseline by the coherence figure."
                if withheld
                else (
                    f"Numeric coherence was returned on {auris['numeric_coherence_cases']} cases. "
                    f"Status matched the null input on {auris['coherence_status_matches_null']} "
                    f"of {auris['coherence_status_cases']} cases."
                )
            ),
        )
    )
    missing = ", ".join(auris["nodes_without_any_reading"]) or "none"
    claims.append(
        _claim(
            "auris.nodes_without_readings",
            "measured",
            (
                f"Nodes with no numeric reading on any case: {missing}. "
                f"Cases with a numeric coherence: {auris['numeric_coherence_cases']} of {auris['cases']}. "
                "get_auris_coherence still returns no_data when any required input is missing."
            ),
        )
    )
    shuffle_gap = auris["median_distance_from_key_shuffle"]
    zero_gap = auris["median_distance_from_zero_input"]
    if shuffle_gap is not None and shuffle_gap > 0.0:
        shuffle_text = (
            "Moving the seeded random inputs onto different keys changed node outputs "
            f"(median distance {fmt(shuffle_gap)}). The readings are key-sensitive on these cases."
        )
    else:
        shuffle_text = (
            f"The key shuffle median distance is {fmt(shuffle_gap)}. "
            "A zero distance would mean the node vector ignored which key held which number."
        )
    claims.append(
        _claim(
            "auris.baselines",
            "inferred",
            (
                f"{shuffle_text} Median distance from the all-zero input on the same random cases "
                f"is {fmt(zero_gap)}."
            ),
        )
    )

    cells = qgita["cells"]
    ftcp_sep = [cell for cell in cells if _recall_above_fpr(cell["ftcp"])]
    ftcp_below = [cell for cell in cells if _recall_below_fpr(cell["ftcp"])]
    lhe_sep = [cell for cell in cells if _recall_above_fpr(cell["lhe"])]
    g_beats = [
        cell
        for cell in cells
        if cell["auroc"]["max_g_eff"]["auroc"] is not None
        and cell["auroc"]["energy"]["auroc"] is not None
        and cell["auroc"]["max_g_eff"]["auroc"] > cell["auroc"]["energy"]["auroc"]
    ]
    claims.append(
        _claim(
            "qgita.gates_versus_null",
            "inferred",
            (
                f"FTCP recall exceeded the FTCP false-alarm rate in {len(ftcp_sep)} of {len(cells)} cells "
                f"({_cell_names(ftcp_sep) or 'none'}). "
                f"FTCP recall was below that false-alarm rate in {len(ftcp_below)} of {len(cells)} cells "
                f"({_cell_names(ftcp_below) or 'none'}). "
                f"LHE recall exceeded the LHE false-alarm rate in {len(lhe_sep)} of {len(cells)} cells "
                f"({_cell_names(lhe_sep) or 'none'}). "
                "FTCP and lighthouse calls use thresholds fit on a separate null calibration set at a 5 percent "
                "tail of max_g_eff and lighthouse intensity. "
                "A one-trial gap is not a significance test. Wilson 95 percent intervals are in the table."
            ),
        )
    )
    claims.append(
        _claim(
            "qgita.geff_versus_energy",
            "inferred",
            (
                f"max_g_eff AUROC exceeded the location-unknown energy detector AUROC in {len(g_beats)} "
                f"of {len(cells)} cells ({_cell_names(g_beats) or 'none'}). "
                "Higher scores were ranked as the injected class and were not flipped."
            ),
        )
    )
    def _max_recall(placement: str) -> Any:
        group = [cell for cell in cells if cell["placement"] == placement]
        return max(cell["ftcp"]["recall"] for cell in group)

    def _min_energy(placement: str) -> Any:
        group = [cell for cell in cells if cell["placement"] == placement]
        return min(cell["auroc"]["energy"]["auroc"] for cell in group)

    claims.append(
        _claim(
            "qgita.placement",
            "measured",
            (
                f"Maximum FTCP recall on the tight knot was {fmt(_max_recall('tight_lattice'))}. "
                f"Maximum FTCP recall on the mid knot was {fmt(_max_recall('mid_lattice'))}. "
                f"Maximum FTCP recall off the lattice was {fmt(_max_recall('off_lattice'))}. "
                f"Minimum energy-detector AUROC off the lattice was {fmt(_min_energy('off_lattice'))}."
            ),
        )
    )
    claims.append(
        _claim(
            "not_claimed.alive_or_hold",
            "speculative",
            (
                "Nothing measured here says that HNC, Auris, or QGITA is alive, conscious, or validated, "
                "and nothing here lifts deployment HOLD. Reading a coherence label or an AUROC as that "
                "decision would be speculative."
            ),
            asserted=False,
        )
    )
    tags = {claim["tag"] for claim in claims}
    if tags - {"measured", "inferred", "speculative"}:
        raise RuntimeError(f"unexpected claim tags: {tags}")
    return claims


def _recall_above_fpr(block: dict[str, Any]) -> bool:
    recall = block["recall"]
    false_alarm = block["false_alarm_rate"]
    return recall is not None and false_alarm is not None and recall > false_alarm


def _recall_below_fpr(block: dict[str, Any]) -> bool:
    recall = block["recall"]
    false_alarm = block["false_alarm_rate"]
    return recall is not None and false_alarm is not None and recall < false_alarm


def _cell_names(cells: list[dict[str, Any]]) -> str:
    return ", ".join(f"{cell['placement']} {cell['snr_db']} dB" for cell in cells)


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(fmt(value) for value in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def render_results(
    hnc: dict[str, Any],
    auris: dict[str, Any],
    qgita: dict[str, Any],
    claims: list[dict[str, Any]],
    environment: dict[str, Any],
) -> str:
    formula = hnc["formula"]
    multiverse = hnc["multiverse"]
    baselines = formula["baselines"]
    seeds = environment["seeds"]
    lines = [
        "# Evidence results",
        "",
        "This file is written by `python -m aureon.evidence`. "
        "Floats here use Python `format(x, \".6g\")`. Full values are in `evidence/output/`.",
        "",
        "The run calls `HarmonicRealityField.step`, `QueenHiveMind.get_auris_coherence`, "
        "`QueenHiveMind.read_auris_nodes`, and `QGITAMarketAnalyzer.analyze`. "
        "It does not call an external model. It does not place an order. "
        "It does not say the system is alive.",
        "",
        "## Reproduce",
        "",
        "```",
        "make evidence",
        "```",
        "",
        "That target runs `PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence --check`. "
        "The check rebuilds every committed output and requires the bytes to match. "
        "`evidence/environment.json` is included, except the field `commit_sha`, which is "
        "`git rev-parse HEAD` at run time and is allowed to differ. "
        "There is no numeric tolerance. The match is for the Python, NumPy, and platform recorded below.",
        "",
        "Dependencies used by the imported implementations: NumPy, and `python-dotenv` because "
        "`QueenHiveMind` imports it. This command does not install packages and does not call a network API.",
        "",
        "## Recorded environment",
        "",
        _table(
            ["item", "value"],
            [
                ["Python", environment["python_version"]],
                ["NumPy", environment["numpy_version"]],
                ["platform", environment["platform"]],
                ["HNC seeds", ", ".join(str(seed) for seed in seeds["hnc"])],
                ["HNC shuffle and Gaussian seed", str(seeds["hnc_shuffle"])],
                ["Auris random seed", str(seeds["auris_random"])],
                ["QGITA master seed", str(seeds["qgita_master"])],
                ["QGITA calibration seed start", str(seeds["qgita_calibration_start"])],
                ["PYTHONHASHSEED", environment["pythonhashseed"]],
            ],
        ),
        "",
        "## Harness definitions",
        "",
        "These belong to the harness. They are not formulas of the three systems.",
        "",
        "- HNC baselines pass a zero series, a shuffled copy of Λ(t), and unit Gaussian noise through "
        "`HarmonicRealityField._calculate_coherence`.",
        "- Auris ground truth is the input guard transcribed from `_auris_role_value` and `_auris_input`. "
        "Numeric node values are the function's own outputs.",
        "- Auris baselines are the null call, the all-zero input, and the same numbers moved onto different keys.",
        "- QGITA signal: one-sample impulse of amplitude A added to unit-variance Gaussian noise. "
        "`snr_db = 20 * log10(A)`.",
        "- QGITA calls compare `max_g_eff` and lighthouse intensity with thresholds fit on calibration "
        "nulls at a 5% tail. The analyzer's constructor defaults are unchanged. "
        "Rate intervals are Wilson 95%. AUROC intervals are Hanley-McNeil.",
        "- Energy baseline: maximum squared sample, location unknown. "
        "Oracle baseline: squared sample at the known injection index. "
        "Their call threshold is fit on separate null draws so about 5% of those draws lie strictly above it.",
        "- AUROC is Mann-Whitney with ties counted as one half. Higher scores rank as the injected class. "
        "Scores are not flipped when the ranking runs the other way.",
        "",
        "## HNC",
        "",
        _table(
            [
                "path",
                "coherence",
                "boundedness",
                "echo magnitude ratio",
                "state",
                "min",
                "max",
                "finite",
                "seed diff",
                "repeat diff",
                "shuffled coherence",
                "gaussian coherence",
                "zero coherence",
            ],
            [
                [
                    "formula",
                    formula["coherence"],
                    formula["boundedness"],
                    formula["echo_magnitude_ratio"],
                    formula["state"],
                    formula["series_min"],
                    formula["series_max"],
                    formula["finite"],
                    formula["max_abs_diff_across_seeds"],
                    formula["repeat_max_abs_diff"],
                    baselines["shuffled_coherence"],
                    baselines["gaussian_coherence"],
                    baselines["zero_coherence"],
                ],
                [
                    "multiverse",
                    multiverse["coherence"],
                    multiverse["boundedness"],
                    multiverse["echo_magnitude_ratio"],
                    multiverse["state"],
                    multiverse["series_min"],
                    multiverse["series_max"],
                    multiverse["finite"],
                    multiverse["max_abs_diff_across_seeds"],
                    multiverse["repeat_max_abs_diff"],
                    None,
                    None,
                    None,
                ],
            ],
        ),
        "",
        f"Formula versus multiverse, maximum absolute difference: {fmt(formula['multiverse_max_abs_diff'])}.",
        (
            "The echo figure is the magnitude ratio from CausalEcho.get_echo_magnitude_ratio. "
            f"JSON value {formula['echo_magnitude_ratio']!r}. It is not a correlation. "
            f"Sample rate {fmt(formula['sample_rate'])} Hz, requested {fmt(formula['sample_rate_requested'])} Hz."
        ),
        "",
        "## Auris",
        "",
        _table(
            ["quantity", "value"],
            [
                ["cases", auris["cases"]],
                ["dependency mismatches", f"{auris['dependency_mismatches']} / {auris['dependency_checks']}"],
                ["cases with a numeric coherence", auris["numeric_coherence_cases"]],
                [
                    "cases whose coherence status matches the null input",
                    f"{auris['coherence_status_matches_null']} / {auris['coherence_status_cases']}",
                ],
                ["null coherence status", auris["null_coherence_status"]],
                ["nodes with no reading on any case", ", ".join(auris["nodes_without_any_reading"]) or "none"],
                ["median distance from the zero input", auris["median_distance_from_zero_input"]],
                ["median distance from the key shuffle", auris["median_distance_from_key_shuffle"]],
            ],
        ),
        "",
        _table(
            ["node", "role", "readings", "missing", "value on zeros", "value on ones"],
            [
                [
                    node["node"],
                    node["role"],
                    node["readings"],
                    node["missing"],
                    node["value_on_zeros"],
                    node["value_on_ones"],
                ]
                for node in auris["nodes"]
            ],
        ),
        "",
        "## QGITA",
        "",
        "Brackets are 95% intervals. Precision is null when a detector made no positive calls. "
        f"Evaluation trials per class: {qgita['cells'][0]['signal_trials']}. "
        f"Calibration nulls: {qgita['calibration']['trials']}.",
        "",
        _table(
            [
                "placement",
                "snr_db",
                "amplitude",
                "ftcp recall",
                "ftcp FPR",
                "lhe recall",
                "lhe FPR",
                "g_eff AUROC",
                "energy AUROC",
                "oracle AUROC",
            ],
            [
                [
                    cell["placement"],
                    cell["snr_db"],
                    cell["amplitude"],
                    with_ci(cell["ftcp"]["recall"], cell["ftcp"]["recall_ci95"]),
                    with_ci(cell["ftcp"]["false_alarm_rate"], cell["ftcp"]["false_alarm_ci95"]),
                    with_ci(cell["lhe"]["recall"], cell["lhe"]["recall_ci95"]),
                    with_ci(cell["lhe"]["false_alarm_rate"], cell["lhe"]["false_alarm_ci95"]),
                    with_ci(cell["auroc"]["max_g_eff"]["auroc"], cell["auroc"]["max_g_eff"]["ci95"]),
                    with_ci(cell["auroc"]["energy"]["auroc"], cell["auroc"]["energy"]["ci95"]),
                    with_ci(cell["auroc"]["oracle"]["auroc"], cell["auroc"]["oracle"]["ci95"]),
                ]
                for cell in qgita["cells"]
            ],
        ),
        "",
        (
            "FTCP max_g_eff threshold "
            f"{fmt(qgita['calibration']['ftcp_max_g_eff_threshold'])}, "
            "calibration false-alarm rate "
            f"{fmt(qgita['calibration']['ftcp_calibration_false_alarm_rate'])}. "
            "Lighthouse intensity threshold "
            f"{fmt(qgita['calibration']['lighthouse_intensity_threshold'])}, "
            "calibration false-alarm rate "
            f"{fmt(qgita['calibration']['lighthouse_calibration_false_alarm_rate'])}. "
            "Energy threshold "
            f"{fmt(qgita['calibration']['energy_threshold'])}. "
            "Oracle threshold "
            f"{fmt(qgita['calibration']['oracle_threshold'])}."
        ),
        "",
        "## Claims",
        "",
        "Measured: a figure this run computed. "
        "Inferred: a comparison or a reading of the implementation that the figure supports. "
        "Speculative: recorded so it is explicit, and not asserted as a result.",
        "",
        _table(
            ["id", "tag", "asserted", "statement"],
            [[claim["id"], claim["tag"], claim["asserted"], claim["statement"]] for claim in claims],
        ),
        "",
        "Deployment HOLD is unchanged by this run.",
        "",
    ]
    return "\n".join(lines)
