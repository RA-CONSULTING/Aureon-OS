"""Run the NAIC 2026 state-support prototype against synthetic companies."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aureon.operator.grounded_action import GroundedActionGate  # noqa: E402
from aureon.operator.state_support_agent import (  # noqa: E402
    StateSupportEligibilityAgent,
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    load(temporary)
    temporary.replace(path)


def render_markdown(run: dict) -> str:
    lines = [
        "# Aureon State Support Eligibility Agent - Demonstration",
        "",
        f"Evaluated at: `{run['evaluated_at']}`",
        "",
        "This demonstration uses synthetic companies and a dated public-rule snapshot. "
        "Every provider remains the final authority; no application is submitted.",
        "",
    ]
    for portfolio in run["portfolios"]:
        lines.extend([f"## {portfolio['profile_id']}", ""])
        for route in portfolio["route_results"]:
            lines.append(
                f"- **{route['name']}**: `{route['decision']}` "
                f"(readiness {route['readiness_score']:.0%})"
            )
            if route["missing_evidence"]:
                lines.append("  Evidence gaps: " + "; ".join(route["missing_evidence"]))
            if route["failed_eligibility"]:
                lines.append(
                    "  Direct-route failures: " + "; ".join(route["failed_eligibility"])
                )
        lines.append("")
    lines.extend(
        [
            "## Control Boundary",
            "",
            "- Emails sent: 0",
            "- Forms submitted: 0",
            "- Portal mutations: 0",
            "- Applications submitted: 0",
            "- Human approval is required before any external action.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()

    rule_snapshot = load(args.rules)
    profiles = load(args.profiles)
    gate = GroundedActionGate(source="state_support_agent", enable_llm=False)

    def ground(action: str, params: dict):
        return gate.ground(action, params).to_dict()

    agent = StateSupportEligibilityAgent(rule_snapshot["routes"], grounder=ground)
    as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
    portfolios = [
        agent.evaluate_portfolio(
            profile,
            as_of=as_of,
            source_snapshot=rule_snapshot,
        )
        for profile in profiles["profiles"]
    ]
    run = {
        "schema_version": "aureon.naic2026-state-support-demo.v1",
        "evaluated_at": as_of.isoformat(),
        "rules_path": str(args.rules),
        "profiles_path": str(args.profiles),
        "portfolios": portfolios,
        "external_actions": {
            "emails_sent": 0,
            "forms_submitted": 0,
            "portal_mutations": 0,
            "applications_submitted": 0,
        },
    }
    write_json_atomic(args.output, run)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(run), encoding="utf-8")
    print(
        json.dumps(
            {
                "profiles": len(portfolios),
                "routes_per_profile": len(rule_snapshot["routes"]),
                "output": str(args.output),
                "external_actions": run["external_actions"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
