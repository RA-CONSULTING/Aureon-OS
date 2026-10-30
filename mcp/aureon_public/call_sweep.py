"""Call every body_call-reachable entry point with no arguments.

Each call uses the public worker. Sockets are blocked and logged in that
worker. Fake NEXUS and Sero checkouts sit beside the repo. An entry point is
refused when the call opens a connection or loads queen, miner, swarm_motion,
inhouse_ai, ollama_config, or an HTTP client.

    bash measured/aureon_public_call_sweep.sh
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _tested_stage1_tools() -> set[tuple[str, str]]:
    return {
        ("alignment/harmonic_resonance.py", "compute_signal_consensus"),
        ("alignment/harmonic_resonance.py", "consonance_score"),
        ("alignment/harmonic_resonance.py", "analyse_frequency_harmony"),
        ("alignment/harmonic_resonance.py", "compute_phase_coherence"),
        ("alignment/harmonic_resonance.py", "derive_phase"),
        ("alignment/harmonic_resonance.py", "geometric_mean"),
        ("alignment/harmonic_resonance.py", "full_harmonic_analysis"),
        ("alignment/harmonic_resonance.py", "HarmonicAnalysis.to_dict"),
        ("alignment/pillar_alignment.py", "AlignmentCycleResult.to_dict"),
        ("alignment/pillar_alignment.py", "get_pillar_alignment"),
        ("alignment/unified_directive.py", "MasterDirective.to_dict"),
        ("generated/research_cinema/harmonic_nexus_score_model.py", "build_default_inputs"),
        ("generated/research_cinema/harmonic_nexus_score_model.py", "HarmonicNexusScoreInputs.normalized"),
        ("generated/research_cinema/harmonic_nexus_score_model.py", "harmonic_nexus_score"),
        ("generated/research_cinema/harmonic_nexus_score_model.py", "score_breakdown"),
        ("swarm/druidic_council.py", "voice_for_gamma"),
        ("swarm/fleadh.py", "steer_flow"),
        ("swarm/druidic_council.py", "build_seat_receipt"),
        ("swarm/agent.py", "SwarmAgent.substrate"),
        ("swarm/agent.py", "SwarmAgent.to_dict"),
        ("swarm/agent.py", "SwarmAgent.propose"),
        ("swarm/coherence.py", "ClusterCoherence.gamma"),
        ("swarm/coherence.py", "ClusterCoherence.to_dict"),
        ("swarm/memory_bus.py", "CausalEchoBus.echo"),
        ("swarm/memory_bus.py", "CausalEchoBus.to_dict"),
        ("swarm/steering.py", "SteeringField.steer"),
        ("swarm/druidic_council.py", "SeatReceipt.to_dict"),
        ("swarm/druidic_council.py", "CouncilReceipt.to_dict"),
        ("swarm/queen_gate.py", "Actualization.to_dict"),
    }


def reachable_entries() -> list[dict[str, Any]]:
    """Entry points body_call will run while the call-sweep gate is open."""

    import aureon_public.body as body_module

    body_module.enable_sweep_measurement()
    from aureon_public.body import _inventory, _plan_stage, public_entry_refusal

    seen: set[tuple[str, str]] = set()
    found = []
    rows, _index = _inventory()
    for row in rows:
        if row["server"] != "public" or row["kind"] not in {"function", "method"}:
            continue
        key = (str(row["module"]), str(row["symbol"]))
        if key in seen:
            continue
        seen.add(key)
        if public_entry_refusal(row) is not None:
            continue
        found.append(
            {
                "module": key[0],
                "package": str(row["package"]),
                "plan_stage": _plan_stage(str(row["package"])),
                "symbol": key[1],
            }
        )
    return found


def child_main(module: str, symbol: str) -> None:
    import aureon_public.body as body_module

    body_module.enable_sweep_measurement()
    text = body_module.body_call(module, symbol)
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        body = {"status": "unavailable", "reason": "result was not JSON"}
    report = body_module.last_sweep_report or {}
    json.dump(
        {
            "bad": list(report.get("modules") or []),
            "called": body.get("called") is True,
            "reason": body.get("reason"),
            "socket": list(report.get("sockets") or []),
            "status": body.get("status"),
        },
        sys.stdout,
    )


def _one(module: str, symbol: str, timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "aureon_public.call_sweep",
            "--module",
            module,
            "--symbol",
            symbol,
        ],
        cwd=os.environ.get("TMPDIR") or "/tmp",
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env={key: value for key, value in os.environ.items() if key != "AUREON_PUBLIC_SWEEP"},
    )
    if not completed.stdout.strip():
        return {
            "bad": [],
            "called": False,
            "error": f"sweep exited {completed.returncode}",
            "socket": [],
            "status": "unavailable",
        }
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "bad": [],
            "called": False,
            "error": "sweep result was not JSON",
            "socket": [],
            "status": "unavailable",
        }
    return payload if isinstance(payload, dict) else {}


def build_record(timeout: float) -> dict[str, Any]:
    from aureon_public.guard_loader import PINNED_COMMIT, aureon_source
    from aureon_public.sweep_layout import layout_record

    source = aureon_source()
    tested = _tested_stage1_tools()
    entries = []
    for row in reachable_entries():
        print(f"{row['module']} {row['symbol']}", file=sys.stderr)
        payload = _one(row["module"], row["symbol"], timeout)
        bad = [str(item) for item in payload.get("bad") or []]
        sockets = [str(item) for item in payload.get("socket") or []]
        key = (row["module"], row["symbol"])
        entries.append(
            {
                "bad": bad,
                "called": payload.get("called") is True,
                "error": payload.get("error"),
                "module": row["module"],
                "package": row["package"],
                "plan_stage": row["plan_stage"],
                "reason": payload.get("reason"),
                "refused": bool(bad or sockets),
                "socket": sockets,
                "status": payload.get("status"),
                "symbol": row["symbol"],
                "tested_stage1_tool": key in tested,
            }
        )
    return {
        "aureon_source": source,
        "entries": entries,
        "layout": layout_record(),
        "pin": PINNED_COMMIT,
        "sockets": "blocked",
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aureon-public-call-sweep")
    parser.add_argument("--module")
    parser.add_argument("--symbol")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    if args.module or args.symbol:
        if not args.module or not args.symbol:
            raise SystemExit("module and symbol are both required")
        child_main(args.module, args.symbol)
        return
    record = build_record(args.timeout)
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        sys.stdout.write(text)
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
