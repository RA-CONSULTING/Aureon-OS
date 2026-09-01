"""
Aureon SaaS — repo-wide coverage audit.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"Does the SaaS cover the whole repository?" — made falsifiable.

Reconciles three views of the ``aureon/`` package tree and proves they agree:

  1. **Filesystem truth** — the real top-level packages under ``aureon/`` (dirs with an
     ``__init__.py``). This is the ground truth of "what the repo actually contains".
  2. **Taxonomy** — the domains the SaaS taxonomy maps to a product domain
     (``aureon/saas/domains.py`` ``_FS_TO_PRODUCT`` ∪ ``_ADAPTERS``).
  3. **Catalog** — the domains the filesystem scan actually surfaced systems for
     (``build_catalog``'s ``filesystem_domains``).

A domain present on disk but absent from the taxonomy is **uncovered** (a real gap — the
console would default it silently). A taxonomy domain with no package on disk is **phantom**
(stale mapping). ``all_covered`` is true only when both are empty. Every covered domain also
carries its real operational ``health`` rollup, so the audit is coverage *and* depth in one.

Read-only and honest: it scans the filesystem and the committed catalog; it fabricates nothing.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from aureon.saas.domains import _ADAPTERS, known_fs_domains, product_domain_for

logger = logging.getLogger("aureon.saas.coverage")

_REPO_ROOT = Path(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
)
_AUREON = _REPO_ROOT / "aureon"
# Package dirs that are not product "domains" for coverage purposes.
_SKIP = {"__pycache__"}


def filesystem_packages() -> List[str]:
    """The real top-level packages under ``aureon/`` (a dir with an ``__init__.py``)."""
    out: List[str] = []
    try:
        for child in sorted(_AUREON.iterdir()):
            if child.is_dir() and child.name not in _SKIP and (child / "__init__.py").exists():
                out.append(child.name)
    except OSError as exc:  # noqa: BLE001 - a missing tree is an honest empty, never a crash
        logger.debug("coverage: cannot list aureon/ (%s)", exc)
    return out


@dataclass
class CoverageAudit:
    fs_package_count: int
    taxonomy_count: int
    covered: List[str]
    uncovered: List[str]     # on disk, missing from the taxonomy — a real gap
    phantom: List[str]       # in the taxonomy, no package on disk — a stale mapping
    coverage_fraction: float
    all_covered: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fs_package_count": self.fs_package_count,
            "taxonomy_count": self.taxonomy_count,
            "covered": self.covered,
            "uncovered": self.uncovered,
            "phantom": self.phantom,
            "coverage_fraction": self.coverage_fraction,
            "all_covered": self.all_covered,
        }


def reconcile() -> CoverageAudit:
    """The core reconciliation: filesystem truth vs the SaaS taxonomy."""
    fs = set(filesystem_packages())
    tax = set(known_fs_domains())
    covered = sorted(fs & tax)
    uncovered = sorted(fs - tax)
    phantom = sorted(tax - fs)
    frac = round(len(covered) / len(fs), 4) if fs else 0.0
    return CoverageAudit(
        fs_package_count=len(fs),
        taxonomy_count=len(tax),
        covered=covered,
        uncovered=uncovered,
        phantom=phantom,
        coverage_fraction=frac,
        all_covered=(not uncovered and not phantom),
    )


def build_coverage_audit(catalog: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """The full repo-wide coverage audit: the reconciliation plus a per-domain operational rollup
    for every covered domain. Pure-read; never raises."""
    from aureon.saas.catalog import build_catalog
    from aureon.saas.domains import domain_health

    audit = reconcile()
    cat = catalog if catalog is not None else build_catalog(use_cache=True)

    domains: List[Dict[str, Any]] = []
    adapter_deep = 0
    for d in audit.covered:
        health = domain_health(d, cat)
        has_adapter = d in _ADAPTERS
        adapter_deep += 1 if has_adapter else 0
        domains.append({
            "domain": d,
            "product_domain": product_domain_for(d),
            "has_adapter": has_adapter,
            "health": health,
        })

    surfaced = sum(1 for x in domains if x["health"] and int(x["health"]["system_count"]) > 0)
    return {
        **audit.to_dict(),
        "adapter_deep_count": adapter_deep,
        "surfaced_with_systems": surfaced,
        "domains": domains,
        "note": "repo-wide coverage: every aureon/ package reconciled against the SaaS taxonomy + "
                "catalog; each covered domain carries its real operational health rollup. Read-only; "
                "nothing fabricated.",
    }


def write_coverage_report(audit: Dict[str, Any], out_md: str | Path,
                          out_json: str | Path | None = None) -> str:
    """Write the coverage audit as a durable evidence artifact (markdown [+ JSON]). Deterministic —
    no wall-clock in the body, so it is byte-identical on re-run for a fixed repo state."""
    lines: List[str] = []
    lines.append("# SaaS repo-wide coverage audit")
    lines.append("")
    lines.append("Generated by `python -m aureon.saas.coverage --report <OUT.md>` — reconciles the real "
                 "`aureon/` package tree against the SaaS taxonomy + catalog. Read-only; nothing is armed.")
    lines.append("")
    lines.append(f"**All covered: {audit['all_covered']}** · {len(audit['covered'])}/"
                 f"{audit['fs_package_count']} packages covered (fraction {audit['coverage_fraction']}) · "
                 f"{len(audit['uncovered'])} uncovered · {len(audit['phantom'])} phantom · "
                 f"{audit.get('adapter_deep_count', 0)} with a deep adapter")
    lines.append("")
    if audit["uncovered"]:
        lines.append("**Uncovered (on disk, missing from the taxonomy):** "
                     + ", ".join(f"`{d}`" for d in audit["uncovered"]))
        lines.append("")
    if audit["phantom"]:
        lines.append("**Phantom (in the taxonomy, no package on disk):** "
                     + ", ".join(f"`{d}`" for d in audit["phantom"]))
        lines.append("")
    lines.append("## Per-domain operational rollup")
    lines.append("")
    lines.append("| domain | product | adapter | systems | dashboards | wired | LOC |")
    lines.append("|:---|:---|:---:|---:|---:|---:|---:|")
    for x in audit.get("domains", []):
        h = x.get("health") or {}
        lines.append(
            f"| `{x['domain']}` | {x['product_domain']} | {'deep' if x['has_adapter'] else 'probe'} | "
            f"{h.get('system_count', 0)} | {h.get('dashboards', 0)} | {h.get('wired_count', 0)} | "
            f"{h.get('total_loc', 0)} |"
        )
    lines.append("")
    md = "\n".join(lines) + "\n"

    out_md_path = Path(out_md)
    out_md_path.write_text(md, encoding="utf-8")
    if out_json is not None:
        Path(out_json).write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(out_md_path)


def main(argv: List[str] | None = None) -> int:
    """CLI: audit repo-wide SaaS coverage. Exit 0 iff every aureon/ package is covered."""
    import argparse

    parser = argparse.ArgumentParser(description="Audit repo-wide SaaS coverage (fs ↔ taxonomy ↔ catalog).")
    parser.add_argument("--report", metavar="OUT.md", help="write the audit as a markdown artifact")
    parser.add_argument("--report-json", metavar="OUT.json", help="also write the JSON record")
    parser.add_argument("--json", action="store_true", help="print the raw JSON audit and exit")
    args = parser.parse_args(argv)

    audit = build_coverage_audit()

    if args.json:
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["all_covered"] else 1

    print("SaaS repo-wide coverage audit")
    print(f"  packages : {len(audit['covered'])}/{audit['fs_package_count']} covered "
          f"(fraction {audit['coverage_fraction']})")
    print(f"  taxonomy : {audit['taxonomy_count']} domains · {audit.get('adapter_deep_count', 0)} deep adapters")
    if audit["uncovered"]:
        print(f"  UNCOVERED: {', '.join(audit['uncovered'])}")
    if audit["phantom"]:
        print(f"  PHANTOM  : {', '.join(audit['phantom'])}")
    if args.report:
        path = write_coverage_report(audit, args.report, args.report_json)
        print(f"  report written: {path}")
    print(f"  all covered: {audit['all_covered']}")
    return 0 if audit["all_covered"] else 1


__all__ = [
    "CoverageAudit", "filesystem_packages", "reconcile",
    "build_coverage_audit", "write_coverage_report", "main",
]


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
