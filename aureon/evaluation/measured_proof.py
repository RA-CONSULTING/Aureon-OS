"""Write the measured-proof bundle. Numbers come from these functions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from aureon.evaluation.auris_node_eval import render_auris_markdown
from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown
from aureon.evaluation.organism_proof import evaluate_organism, render_organism_markdown
from aureon.evaluation.qgita_snr_benchmark import render_qgita_markdown


def _dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def dataset_solution_smoke(root: Path, limit: int = 5) -> dict[str, Any]:
    """Execute the dataset's own HumanEval solutions. Not a model score."""

    from aureon.autonomous.self_coder_benchmark import (
        BenchmarkChildRefused,
        _humaneval_path,
        _load_jsonl,
        _run_python,
        humaneval_reference_program,
        humaneval_tests,
    )

    path = _humaneval_path(root)
    if path is None:
        return {
            "verdict": "HOLD",
            "counts_as_model_score": False,
            "reason": "HumanEval jsonl is not in this checkout",
            "passed": None,
            "total": 0,
            "results": [],
        }
    rows = _load_jsonl(path)[:limit]
    results: list[dict[str, Any]] = []
    passed = 0
    for row in rows:
        try:
            ok = _run_python(humaneval_reference_program(row), humaneval_tests(row))
        except BenchmarkChildRefused as exc:
            return {
                "verdict": "HOLD",
                "counts_as_model_score": False,
                "reason": str(exc),
                "passed": passed,
                "total": len(rows),
                "results": results,
            }
        results.append({"task_id": row.get("task_id"), "dataset_solution_passed": bool(ok)})
        if ok:
            passed += 1
    return {
        "verdict": "measured",
        "counts_as_model_score": False,
        "reason": "the dataset's own solutions ran in the harness; this is not a model score",
        "dataset": str(path),
        "limit": limit,
        "passed": passed,
        "total": len(rows),
        "results": results,
    }


def self_coder_report(root: Path) -> dict[str, Any]:
    from aureon.autonomous.self_coder_benchmark import run_harness

    report = run_harness(root)
    report["dataset_solution_smoke"] = dataset_solution_smoke(root, limit=5)
    report["live_trading"] = False
    return report


def render_self_coder_markdown(report: dict[str, Any]) -> str:
    comparison = report.get("flagship_comparison") or {}
    humaneval = report.get("humaneval") or {}
    smoke = report.get("dataset_solution_smoke") or {}
    lines = [
        "# Self-coding benchmark",
        "",
        "The system under test is the internal Auris, QGITA, and self-coder path. "
        "An outside model is off unless `AUREON_SELF_CODER_ALLOW_EXTERNAL=1`, and that opt-in is not Aureon's brain.",
        f"Outside provider called: `{report.get('external_provider', {}).get('called')}`.",
        f"Flagship comparison: **{comparison.get('status', 'HOLD')}**. {comparison.get('reason', '')}",
        f"This run HumanEval: `{comparison.get('this_run_humaneval_pct')}`.",
        (
            f"HumanEval passed `{humaneval.get('passed')}` of `{humaneval.get('rows')}`; "
            f"attempted `{humaneval.get('attempted')}`; not attempted `{humaneval.get('not_attempted')}`. "
            f"{humaneval.get('reason', '')}"
        ),
        f"This run SWE-bench: `{comparison.get('this_run_swe_bench_pct')}`.",
        f"This run LiveCodeBench: `{comparison.get('this_run_livecodebench_pct')}`.",
        "Published Kimi figures in `published_reference` are not this run.",
        f"HumanEval rows on disk: `{humaneval.get('rows')}`. Status `{humaneval.get('status')}`.",
        (
            "Dataset-solution smoke "
            f"({smoke.get('passed')}/{smoke.get('total')}): **{smoke.get('verdict')}**. "
            f"{smoke.get('reason', '')}"
        ),
        "",
    ]
    return "\n".join(lines)


def write_bundle(root: Path, out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    brain = evaluate_brain(root)
    auris = brain["auris"]
    qgita = brain["qgita"]
    coder = self_coder_report(root)
    organism = evaluate_organism()
    (out / "brain.json").write_text(_dump(brain), encoding="utf-8")
    (out / "brain.md").write_text(render_brain_markdown(brain), encoding="utf-8")
    (out / "auris_nodes.json").write_text(_dump(auris), encoding="utf-8")
    (out / "auris_nodes.md").write_text(render_auris_markdown(auris), encoding="utf-8")
    (out / "qgita_snr.json").write_text(_dump(qgita), encoding="utf-8")
    (out / "qgita_snr.md").write_text(render_qgita_markdown(qgita), encoding="utf-8")
    (out / "self_coder.json").write_text(_dump(coder), encoding="utf-8")
    (out / "self_coder.md").write_text(render_self_coder_markdown(coder), encoding="utf-8")
    (out / "organism.json").write_text(_dump(organism), encoding="utf-8")
    (out / "organism.md").write_text(render_organism_markdown(organism), encoding="utf-8")
    fault = organism["self_model"]["fault"]
    prediction = organism["self_model"]["prediction"]
    index = {
        "schema": "aureon.measured-proof.v1",
        "live_trading": False,
        "files": [
            "auris_nodes.json",
            "brain.json",
            "organism.json",
            "qgita_snr.json",
            "self_coder.json",
        ],
        "auris_coherence": auris["coherence"],
        "auris_hold_nodes": auris["hold_nodes"],
        "auris_trade_readiness": auris["trade_readiness"]["verdict"],
        "hnc_coherence": brain["hnc"]["coherence"],
        "hnc_lambda_last": brain["hnc"]["lambda_last"],
        "hnc_multiverse_extension": brain["hnc"]["multiverse_extension"]["verdict"],
        "hnc_state": brain["hnc"]["state"],
        "qgita_on_hnc_detection_rate": qgita["on_hnc_series"]["detection_rate"],
        "qgita_on_hnc_ftcp_count": qgita["on_hnc_series"]["ftcp_count"],
        "qgita_public_detection_rate": qgita["public_series"]["detection_rate"],
        "qgita_public_ftcp_count": qgita["public_series"].get("ftcp_count"),
        "qgita_public_series": qgita["public_series"]["rates_verdict"],
        "self_coder_comparison": coder["flagship_comparison"]["status"],
        "self_coder_humaneval_pct": coder["flagship_comparison"]["this_run_humaneval_pct"],
        "dataset_solution_smoke": coder["dataset_solution_smoke"]["verdict"],
        "organism_connectivity_verdict": organism["connectivity"]["verdict"],
        "organism_connectivity_score": organism["connectivity"]["score"],
        "organism_isolated": organism["connectivity"]["isolated"],
        "organism_self_prediction_accuracy": prediction["accuracy"],
        "organism_self_prediction_baseline_accuracy": prediction["baseline_accuracy"],
        "organism_fault_detection_rate": fault["detection_rate"],
        "organism_fault_false_alarm_rate": fault["false_alarm_rate"],
        "organism_fault_baseline_detection_rate": fault["baseline_detection_rate"],
        "organism_fault_baseline_false_alarm_rate": fault["baseline_false_alarm_rate"],
    }
    (out / "index.json").write_text(_dump(index), encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the measured-proof bundle and write its raw output")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("reports/measured"))
    args = parser.parse_args(argv)
    index = write_bundle(args.root.resolve(), args.out.resolve())
    print(_dump(index), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
