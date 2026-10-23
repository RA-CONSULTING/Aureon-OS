"""Reproducible self-coder benchmark harness.

The offline fixture always runs. SWE-bench and LiveCodeBench are recorded as
not executed unless their datasets are present on disk and the operator sets
``AUREON_SELF_CODER_BENCH_RUN=1`` with an API key. Published Kimi K2.5 figures
are a reference named by the operator. They are not this process's score.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable

from aureon.autonomous.aureon_internal_self_coder import openai_compatible_model_endpoint

PUBLISHED_KIMI_K2_5 = {
    "model": "Kimi K2.5",
    "swe_bench_verified_pct": 76.8,
    "livecodebench_v6_pct": 85.0,
    "source": "published score named by the operator; not a measurement from this harness",
}

FixtureFn = Callable[..., int]


def _add(a: int, b: int) -> int:
    return a + b


def _third(n: int) -> int:
    return n // 3


def _even(n: int) -> int:
    return int(n % 2 == 0)


_OFFLINE_FIXTURE: tuple[dict[str, Any], ...] = (
    {"id": "add", "fn": _add, "cases": [((1, 2), 3), ((0, 0), 0)]},
    {"id": "third", "fn": _third, "cases": [((9,), 3), ((2,), 0)]},
    {"id": "even", "fn": _even, "cases": [((4,), 1), ((5,), 0)]},
)


def _score_fixture() -> dict[str, Any]:
    passed = 0
    total = 0
    failures: list[str] = []
    for item in _OFFLINE_FIXTURE:
        function = item["fn"]
        for args, expected in item["cases"]:
            total += 1
            try:
                got = function(*args)
            except Exception as exc:
                failures.append(f"{item['id']}: {exc.__class__.__name__}")
                continue
            if got == expected:
                passed += 1
            else:
                failures.append(item["id"])
    return {
        "suite": "offline-fixture",
        "executed": True,
        "passed": passed,
        "total": total,
        "ok": passed == total and total > 0,
        "failures": failures,
        "model_attempted": False,
    }


def _dataset_present(root: Path, name: str) -> bool:
    return (root / "data" / "benchmarks" / name).is_dir()


def run_harness(root: Path | None = None) -> dict[str, Any]:
    """Score the offline fixture and say why the public benches were not run."""

    root = Path(root or Path.cwd())
    endpoint = openai_compatible_model_endpoint()
    run_remote = os.environ.get("AUREON_SELF_CODER_BENCH_RUN", "").strip() in {"1", "true", "yes"}
    key_ready = endpoint["api_key_configured"] is True
    swe_present = _dataset_present(root, "swebench")
    live_present = _dataset_present(root, "livecodebench")
    remote_reason = "AUREON_SELF_CODER_BENCH_RUN is unset and the bench datasets are not in this checkout"
    if run_remote and not key_ready:
        remote_reason = "AUREON_SELF_CODER_API_KEY is unset"
    elif run_remote and key_ready and not (swe_present or live_present):
        remote_reason = "bench datasets are not in this checkout"
    elif run_remote and key_ready:
        remote_reason = "dataset present but this harness does not download or score the full public sets in-process"
    fixture = _score_fixture()
    return {
        "schema": "aureon.self-coder-benchmark.v0",
        "endpoint": endpoint,
        "offline_fixture": fixture,
        "swe_bench": {
            "suite": "SWE-bench Lite or Verified",
            "executed": False,
            "dataset_present": swe_present,
            "reason": remote_reason,
        },
        "livecodebench": {
            "suite": "LiveCodeBench",
            "executed": False,
            "dataset_present": live_present,
            "reason": remote_reason,
        },
        "published_reference": PUBLISHED_KIMI_K2_5,
        "measured_swe_bench_verified_pct": None,
        "measured_livecodebench_v6_pct": None,
        "live_trading": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the offline self-coder benchmark fixture")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    report = run_harness(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["offline_fixture"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
