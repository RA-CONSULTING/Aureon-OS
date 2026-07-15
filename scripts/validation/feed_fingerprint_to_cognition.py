#!/usr/bin/env python3
"""Feed a phenolic-fingerprint run into the cognition layer and make sense of it.

Runs the experimental analysis via the repo's own systems (`connector`), feeds
the result into the cognitive / meta-cognitive layer through
`aureon.cognition.phenolic_bridge.emit_to_cognition` (ThoughtBus + bus_trace),
reads the emitted thoughts back, and prints the sense-making summary with ✅/❌
lines. This is the "feed in → make sense of the patterns" demonstration.

Run: ``python scripts/validation/feed_fingerprint_to_cognition.py``
     (optionally ``--include-computed``).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import connector  # noqa: E402
from aureon.cognition import phenolic_bridge as bridge  # noqa: E402
from aureon.core.aureon_thought_bus import ThoughtBus  # noqa: E402

DATA = REPO_ROOT / "data" / "spectra"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _sources(include_computed: bool) -> list[str]:
    srcs = [
        FIXTURES / "weed_phenolic_spectral_map_codex.csv",
        DATA / "nist_ir_peaks.csv",
        DATA / "curated_open_access_peaks.csv",
    ]
    if include_computed:
        srcs.append(DATA / "computed_xtb_peaks.csv")
    return [str(s) for s in srcs if s.exists()]


def main(argv: list[str] | None = None) -> int:
    """Run analysis, feed cognition, verify emission, print the sense-making report."""
    parser = argparse.ArgumentParser(description="Feed phenolic fingerprints into cognition.")
    parser.add_argument("--include-computed", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--nulls", type=int, default=500)
    args = parser.parse_args(argv)

    result = connector.run_analysis(_sources(args.include_computed), nulls=args.nulls, seed=args.seed)

    # Isolated bus so the demonstration is self-contained and capturable.
    bus = ThoughtBus(persist_path=str(Path(tempfile.mkdtemp()) / "phenolic_thoughts.jsonl"))
    received: list[str] = []
    bus.subscribe("phenolic.*", lambda t: received.append(t.topic))

    summary = bridge.emit_to_cognition(result.to_dict(), bus=bus)

    print("Phenolic → cognition")
    print(f"  {summary['headline']}")
    print(f"  separable: {summary['separable'] or '(none)'}")
    print(f"  clustering-significant: {summary['clustering_significant'] or '(none)'}")
    print(f"  provenance: {summary['provenance_counts']}")

    n_run = received.count(bridge.RUN_TOPIC)
    n_compound = received.count(bridge.COMPOUND_TOPIC)
    ok_bus = n_run == 1 and n_compound == len(result.compounds)
    print(f"  {'✅' if ok_bus else '❌'} ThoughtBus received "
          f"{n_run}× run + {n_compound}× compound (expected {len(result.compounds)})")

    from aureon.core.bus_trace import read_trace_latest

    tr = read_trace_latest(bridge.TRACE_NAME)
    ok_trace = bool(tr) and "separable_fraction" in tr
    print(f"  {'✅' if ok_trace else '❌'} bus_trace signal '{bridge.TRACE_NAME}' written: {tr}")

    return 0 if (ok_bus and ok_trace) else 1


if __name__ == "__main__":
    raise SystemExit(main())
