"""
Benchmark coverage — "how much of Aureon OS is pinned?" made falsifiable.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The end goal is a full 100% benchmark of the Aureon OS. This module is the
measuring instrument for that march: it reconciles the COMMITTED Tier-A
benchmark report (``tests/benchmarks/report.json`` — every row names the
module it pins) against the real filesystem (every top-level package under
``aureon/`` and every ``.py`` module inside it) and reports, with nothing
invented:

  - which domains carry at least one Tier-A pin (covered),
  - which domains carry NONE (uncovered — the gap list is the roadmap),
  - how many unique modules are pinned, out of how many exist.

The **ratchet** makes progress one-way: a committed baseline
(``docs/BENCHMARK_COVERAGE.json``) records the covered-domain set and the
pinned-module count; a later derivation may only grow both. Any regression is
named (which domain fell out, which count went down) — never smoothed over.

Honest by construction: everything is derived from the committed report and
the disk. A missing report is an honest empty coverage with the blocker
named, never a guessed number. A stale or superseded report is never promoted
to a current measurement, even if its historical rows all say ``passed``.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("aureon.analytics.benchmark_coverage")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPORT = _REPO_ROOT / "tests" / "benchmarks" / "report.json"
_BASELINE = _REPO_ROOT / "docs" / "BENCHMARK_COVERAGE.json"
_SKIP = {"__pycache__"}


def _fs_domains(repo_root: Path) -> Dict[str, int]:
    """Real top-level packages under ``aureon/`` → recursive ``.py`` module count."""
    out: Dict[str, int] = {}
    aureon = repo_root / "aureon"
    try:
        for child in sorted(aureon.iterdir()):
            if child.is_dir() and child.name not in _SKIP and (child / "__init__.py").exists():
                out[child.name] = sum(1 for p in child.rglob("*.py")
                                      if "__pycache__" not in p.parts)
    except OSError as exc:  # noqa: BLE001 — a missing tree is an honest empty, never a crash
        logger.debug("benchmark_coverage: cannot list aureon/ (%s)", exc)
    return out


def _domain_of(module: str) -> str | None:
    """``aureon/<domain>/...`` → domain; anything else → None (outside the package)."""
    parts = module.split("/")
    if len(parts) >= 3 and parts[0] == "aureon":
        return parts[1]
    return None


@dataclass
class BenchmarkCoverage:
    status: str                    # "measured" | "stale_superseded" | "honest_unavailable"
    blocker: str = ""
    benchmarks: int = 0
    all_rows_passed: bool = False
    pinned_modules: List[str] = field(default_factory=list)   # unique, sorted
    missing_modules: List[str] = field(default_factory=list)  # named in report, absent on disk
    domains: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    outside_aureon: List[str] = field(default_factory=list)   # pins outside aureon/ (e.g. scripts/)
    covered_domains: List[str] = field(default_factory=list)
    uncovered_domains: List[str] = field(default_factory=list)
    domain_coverage_fraction: float | None = None
    total_modules: int = 0
    module_pin_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status, "blocker": self.blocker,
            "benchmarks": self.benchmarks, "all_rows_passed": self.all_rows_passed,
            "pinned_modules": self.pinned_modules,
            "missing_modules": self.missing_modules,
            "domains": self.domains, "outside_aureon": self.outside_aureon,
            "covered_domains": self.covered_domains,
            "uncovered_domains": self.uncovered_domains,
            "domain_coverage_fraction": self.domain_coverage_fraction,
            "total_modules": self.total_modules,
            "module_pin_count": self.module_pin_count,
        }


def build_coverage(repo_root: Path | None = None,
                   report_path: Path | None = None) -> BenchmarkCoverage:
    """Derive the coverage map from the committed Tier-A report + the disk."""
    root = Path(repo_root) if repo_root else _REPO_ROOT
    rp = Path(report_path) if report_path else (root / "tests" / "benchmarks" / "report.json")
    try:
        report = json.loads(rp.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return BenchmarkCoverage(status="honest_unavailable",
                                 blocker=f"committed report unreadable: {exc}")
    if not isinstance(report, dict):
        return BenchmarkCoverage(
            status="honest_unavailable",
            blocker="committed report must contain a JSON object",
        )
    report_status = report.get("report_status")
    production_ready = report.get("production_ready")
    current_effect_claim = report.get("current_effect_claim")
    if not (
        report_status == "CURRENT"
        and production_ready is True
        and current_effect_claim is True
    ):
        return BenchmarkCoverage(
            status="stale_superseded",
            blocker=(
                "committed report is not current release evidence: "
                f"report_status={report_status!r}, "
                f"production_ready={production_ready is True}, "
                f"current_effect_claim={current_effect_claim is True}"
            ),
        )
    rows = report.get("tier_a", [])
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return BenchmarkCoverage(
            status="honest_unavailable",
            blocker="current report tier_a must be a list of objects",
        )
    if not rows:
        return BenchmarkCoverage(status="honest_unavailable",
                                 blocker="committed report carries no tier_a rows")

    mods = sorted({str(r.get("module", "")) for r in rows if r.get("module")})
    missing = [m for m in mods if not (root / m).exists()]
    fs = _fs_domains(root)

    domains: Dict[str, Dict[str, Any]] = {}
    for d, count in fs.items():
        pinned = sorted(m for m in mods if _domain_of(m) == d)
        domains[d] = {"modules": count, "pinned": pinned, "covered": bool(pinned)}
    outside = sorted(m for m in mods if _domain_of(m) is None)

    covered = sorted(d for d, v in domains.items() if v["covered"])
    uncovered = sorted(d for d, v in domains.items() if not v["covered"])
    return BenchmarkCoverage(
        status="measured",
        benchmarks=len(rows),
        all_rows_passed=all(bool(r.get("passed")) for r in rows),
        pinned_modules=mods,
        missing_modules=missing,
        domains=domains,
        outside_aureon=outside,
        covered_domains=covered,
        uncovered_domains=uncovered,
        domain_coverage_fraction=(round(len(covered) / len(fs), 4) if fs else None),
        total_modules=sum(fs.values()),
        module_pin_count=len(mods),
    )


def ratchet_check(live: BenchmarkCoverage,
                  baseline: Dict[str, Any] | None) -> Dict[str, Any]:
    """One-way progress: live coverage may only GROW relative to the baseline.

    Regressions are NAMED — which domain fell out of coverage, which count went
    down. No baseline yet → ratchet passes trivially (first measurement seeds it).
    """
    if not baseline:
        return {"ok": True, "regressions": [], "note": "no baseline — first measurement seeds it"}
    regressions: List[str] = []
    base_covered = set(baseline.get("covered_domains", []))
    lost = sorted(base_covered - set(live.covered_domains))
    if lost:
        regressions.append(f"domains fell out of coverage: {lost}")
    base_pins = int(baseline.get("module_pin_count", 0))
    if live.module_pin_count < base_pins:
        regressions.append(
            f"pinned-module count fell: {live.module_pin_count} < baseline {base_pins}")
    base_benchmarks = int(baseline.get("benchmarks", 0))
    if live.benchmarks < base_benchmarks:
        regressions.append(
            f"benchmark count fell: {live.benchmarks} < baseline {base_benchmarks}")
    return {"ok": not regressions, "regressions": regressions, "note": ""}


def load_baseline(path: Path | None = None) -> Dict[str, Any] | None:
    p = Path(path) if path else _BASELINE
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_coverage(cov: BenchmarkCoverage, out_md: Path, out_json: Path) -> None:
    out_json.write_text(json.dumps(cov.to_dict(), indent=2), encoding="utf-8")
    lines = [
        "# Benchmark coverage — the march to 100%", "",
        "> Derived from the committed Tier-A report + the filesystem. Nothing invented;",
        "> the uncovered list is the roadmap, the ratchet makes progress one-way.", "",
        f"- Status: **{cov.status}**",
        *([f"- Blocker: {cov.blocker}"] if cov.blocker else []),
        f"- Tier-A benchmarks: **{cov.benchmarks}** (all passed: {cov.all_rows_passed})",
        f"- Unique modules pinned: **{cov.module_pin_count}** of {cov.total_modules} on disk",
        f"- Domain coverage: **{len(cov.covered_domains)}/{len(cov.domains)}**"
        f" ({cov.domain_coverage_fraction})", "",
        "## Per-domain", "",
        "| Domain | Modules | Pinned | Covered |", "|---|---|---|---|",
    ]
    for d, v in sorted(cov.domains.items()):
        lines.append(f"| {d} | {v['modules']} | {len(v['pinned'])} | "
                     f"{'yes' if v['covered'] else '**no**'} |")
    if cov.outside_aureon:
        lines += ["", "## Pins outside `aureon/`", ""]
        lines += [f"- `{m}`" for m in cov.outside_aureon]
    lines += ["", "## Uncovered domains (the roadmap)", ""]
    lines += [f"- `{d}` — {cov.domains[d]['modules']} modules, zero pins"
              for d in cov.uncovered_domains] or ["(none — 100% domain coverage)"]
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=_REPO_ROOT / "docs" / "BENCHMARK_COVERAGE.md")
    args = ap.parse_args(argv)
    cov = build_coverage()
    ratchet = ratchet_check(cov, load_baseline())
    write_coverage(cov, args.out, args.out.with_suffix(".json"))
    print(f"benchmarks={cov.benchmarks} pinned_modules={cov.module_pin_count}"
          f"/{cov.total_modules} domains={len(cov.covered_domains)}/{len(cov.domains)}"
          f" ratchet_ok={ratchet['ok']}")
    for r in ratchet["regressions"]:
        print(f"REGRESSION: {r}")
    return 0 if (cov.status == "measured" and ratchet["ok"]) else 1


__all__ = ["BenchmarkCoverage", "build_coverage", "ratchet_check",
           "load_baseline", "write_coverage", "main"]

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
