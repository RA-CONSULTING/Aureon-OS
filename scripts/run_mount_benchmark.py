"""
Run the mount integration benchmark: drive OpenAI-shaped probes through the
`/v1/chat/completions` mount and record whether an external flagship / AGI model
integrates smoothly — valid chat.completion shape, boundary refusals, both engines,
intact `aureon` provenance. Writes a JSON + markdown artifact to
docs/research/benchmarks/ and exits non-zero if any critical check fails (so it is
a real signal, not decoration).

    AUREON_LLM_OFFLINE=1 python -m scripts.run_mount_benchmark
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("AUREON_LLM_OFFLINE", "1")
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aureon.operator.mount_benchmark import run_mount_benchmark  # noqa: E402

_MARK = {True: "✅", False: "❌"}


def _write_artifacts(report: dict) -> list[str]:
    out_dir = _REPO_ROOT / "docs" / "research" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "mount_integration_benchmark.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    s = report["summary"]
    m = report["metrics"]
    imap = report["integration_map"]
    lines = [
        "# Aureon — Mount Integration Benchmark",
        "",
        "> *\"We're not reinventing the wheel — we're drawing the map so AGI systems "
        "integrate smoothly.\"*",
        "",
        f"**Status:** {'✅ pass' if s['status'] == 'pass' else '❌ fail'} · "
        f"critical {s['critical_passed']}/{s['critical_total']} · "
        f"informational {s['informational_passed']}/{s['informational_total']} · "
        f"{s['check_count']} checks",
        "",
        "Every probe is a real OpenAI `chat.completions` request driven through the "
        "live `/v1/chat/completions` mount — exactly what a flagship / AGI model gets "
        "when it points its `base_url` at Aureon. Offline; latency is cold-start "
        "dominated (the first grounding probe builds the repo index).",
        "",
        "## Integration guarantees",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Probes | {m['probes']} |",
        f"| Valid OpenAI shape | {m['shape_valid_rate'] * 100:.0f}% |",
        f"| Boundary prompts blocked (content_filter) | {m['boundary_blocked_rate'] * 100:.0f}% |",
        f"| Both engines reachable | {'yes' if m['both_engines'] else 'no'} ({', '.join(m['engines_exercised'])}) |",
        f"| Grounded probes grounded | {m['grounded_rate'] * 100:.0f}% |",
        f"| Mean latency | {m['mean_latency_ms']} ms |",
        f"| Max latency (cold index) | {m['max_latency_ms']} ms |",
        "",
        "## The integration map (what an AGI system reads to plug in)",
        "",
        "```json",
        json.dumps(imap, indent=2),
        "```",
        "",
        "## Probes",
        "",
        "| Probe | Kind | Engine | finish_reason | blocked | grounded | stages | latency (ms) |",
        "|-------|------|--------|---------------|---------|----------|--------|--------------|",
    ]
    for r in report["probes"]:
        lines.append(
            f"| {r['id']} | {r['kind']} | {r.get('engine')} | {r.get('finish_reason')} | "
            f"{r.get('blocked')} | {r.get('grounded')} | {r.get('n_stages')} | {r.get('latency_ms')} |"
        )
    lines += ["", "## Checks", "", "| Check | Tier | Result | Detail |",
              "|-------|------|--------|--------|"]
    for c in report["checks"]:
        tier = "critical" if c["critical"] else "info"
        mark = _MARK[c["ok"]] if c["ok"] else (_MARK[False] if c["critical"] else "⚠️")
        lines.append(f"| {c['check']} | {tier} | {mark} | {c['detail']} |")
    md_path = out_dir / "mount_integration_benchmark.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [str(json_path), str(md_path)]


def main() -> int:
    report = run_mount_benchmark()
    paths = _write_artifacts(report)

    print("═" * 74)
    print("AUREON MOUNT INTEGRATION BENCHMARK — a map for AGI systems to plug in")
    print("═" * 74)
    m = report["metrics"]
    print(f"  probes={m['probes']} shape_valid={m['shape_valid_rate']} "
          f"boundary_blocked={m['boundary_blocked_rate']} engines={m['engines_exercised']} "
          f"grounded={m['grounded_rate']} mean_latency_ms={m['mean_latency_ms']}")
    print("─" * 74)
    for c in report["checks"]:
        mark = "✅ PASS" if c["ok"] else ("❌ FAIL" if c["critical"] else "⚠️  WARN")
        print(f"  {mark}  {c['check']:26} {c['detail']}")
    s = report["summary"]
    print("─" * 74)
    print(f"  {s['status'].upper()} · critical {s['critical_passed']}/{s['critical_total']} · "
          f"informational {s['informational_passed']}/{s['informational_total']}")
    for p in paths:
        print(f"  artifact: {p}")
    return 0 if s["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
