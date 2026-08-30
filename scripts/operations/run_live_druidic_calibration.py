#!/usr/bin/env python3
"""Run the live, evidence-only four-seat Druidic calibration.

This command uses Ollama Cloud inference and local HNC/Auris producers.  It
cannot call an exchange or issue an economic permit.  It exits nonzero on any
HOLD and writes an atomic non-secret receipt only after four nodes validate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aureon.autonomous.aureon_agent_company_brain_fabric import (  # noqa: E402
    canonical_agent_company_brain_topology,
)
from aureon.autonomous.aureon_cloud_brain_composition import (  # noqa: E402
    build_material_truth_gated_cloud_thought_path,
)
from aureon.autonomous.aureon_internal_coding_workforce import (  # noqa: E402
    OllamaSwitchboardBrainResolver,
    provision_brain_bound_workforce,
)
from aureon.governance.live_workforce_calibration import (  # noqa: E402
    WorkforceCalibrationHold,
    bind_pinned_provider_moment_resolver,
    collect_live_workforce_auris_calibration,
    load_latest_active_provider_pair,
)
from aureon.governance.workforce_druid_resolver import (  # noqa: E402
    DEFAULT_WORKFORCE_DRUID_ROLES,
)
from aureon.ollama_config import ensure_ollama_runtime_config  # noqa: E402
from aureon.swarm.auris_node_receipts import (  # noqa: E402
    issue_auris_node_receipt,
    validate_auris_node_receipt,
)
from aureon.swarm.druidic_council import ACTIVE_THRESHOLD, REQUIRED_SEATS  # noqa: E402


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(encoded, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _target_topology():
    role_lanes, process_bindings = canonical_agent_company_brain_topology()
    roles = set(DEFAULT_WORKFORCE_DRUID_ROLES.values())
    selected_roles = {role: lane for role, lane in role_lanes.items() if role in roles}
    selected_processes = {
        process_id: binding
        for process_id, binding in process_bindings.items()
        if binding[1] in roles
    }
    if set(selected_roles) != roles or len(selected_processes) != 4:
        raise ValueError("exact_four_druid_brain_topology_unavailable")
    return selected_roles, selected_processes


def _observe_calibration_answer(event: Any) -> None:
    if not isinstance(event, dict):
        raise ValueError("calibration_decision_event_required")
    print(
        json.dumps(
            {
                "calibration_model_answer": str(event.get("output") or "")[:512],
                "prompt_digest": event.get("prompt_digest"),
                "stage": event.get("stage"),
                "subject_id": event.get("subject_id"),
            },
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
    )


def run(*, max_age_s: float, pair_wait_s: float) -> dict[str, Any]:
    os.environ["LIVE"] = "0"
    os.environ["DRY_RUN"] = "1"
    os.environ["AUREON_LLM_AUTO_BOOTSTRAP"] = "1"
    os.environ["AUREON_LLM_PREFER_NATIVE"] = "1"
    config = ensure_ollama_runtime_config(force=True, repo_root=ROOT)
    if not (
        config.get("cloud") is True
        and config.get("api_key_configured") is True
        and config.get("authorization_header_enabled") is True
    ):
        raise ValueError("authenticated_ollama_cloud_runtime_required")

    pinned_id = "aureon:pinned-live-council-provider-moment"
    node_resolver_id = "aureon:live-workforce-auris-nodes"
    pinned = bind_pinned_provider_moment_resolver(
        resolver_id=pinned_id,
        trusted_resolver_ids={pinned_id},
        max_age_s=max_age_s,
    )
    thought_path = build_material_truth_gated_cloud_thought_path(
        evidence_resolver=pinned,
        max_age_s=max_age_s,
    )
    initial_pair = load_latest_active_provider_pair(max_age_s=max_age_s)
    initial_available = True

    def pair_loader():
        nonlocal initial_available
        if initial_available:
            initial_available = False
            return initial_pair
        return load_latest_active_provider_pair(max_age_s=max_age_s)

    role_lanes, process_bindings = _target_topology()
    workforce = provision_brain_bound_workforce(
        role_brain_lanes=role_lanes,
        process_brain_bindings=process_bindings,
        resolver=OllamaSwitchboardBrainResolver(),
        thought_path=thought_path,
        agent_temperature=0.0,
        process_temperature=0.0,
        decision_observer=_observe_calibration_answer,
        response_stop_sequences=("\n",),
        agent_system_prompt_suffix=(
            "For every request, output exactly one complete line from ALLOWED EXACT "
            "RESPONSES. Do not use Markdown, emphasis, JSON, quotes, code fences, "
            "prefixes, suffixes, explanations, or extra punctuation. The first and "
            "last characters must be the first and last characters of the selected line."
        ),
    )
    report = workforce.report()
    if not (
        report.get("brain_fabric_ready") is True
        and report.get("agent_brain_count") == 4
        and report.get("process_brain_count") == 4
        and report.get("all_brains_hnc_routed") is True
        and report.get("provider_mode") == "ollama_cloud_primary"
        and report.get("truth_gate_enforced") is True
    ):
        raise ValueError("four_druid_cloud_brains_not_ready")

    calibration = collect_live_workforce_auris_calibration(
        workforce=workforce,
        evidence_resolver=pinned,
        auris_resolver_id=node_resolver_id,
        trusted_auris_resolver_ids={node_resolver_id},
        pair_loader=pair_loader,
        max_age_s=max_age_s,
        new_pair_wait_s=pair_wait_s,
    )
    now = time.time()
    nodes = [
        validate_auris_node_receipt(
            issue_auris_node_receipt(
                seat=seat,
                resolver=calibration.node_resolver,
                now=now,
                max_age_s=max_age_s,
            ),
            now=now,
            max_age_s=max_age_s,
        )
        for seat in REQUIRED_SEATS
    ]
    if any(node.get("data_status") != "live" for node in nodes):
        raise ValueError("four_live_auris_nodes_required")
    driver_count = sum(float(node["gamma"]) >= ACTIVE_THRESHOLD for node in nodes)
    council_ready = driver_count >= 2
    payload = {
        "schema": "aureon.live-druidic-calibration-operation.v1",
        "status": "complete" if council_ready else "hold",
        "reason": None if council_ready else "council_driver_quorum_unavailable",
        "provider_mode": "ollama_cloud_primary",
        "cloud_model_count": report["distinct_cloud_model_count"],
        "brain_count": report["agent_brain_count"] + report["process_brain_count"],
        "calibration_receipt": calibration.report,
        "auris_nodes": nodes,
        "node_driver_count": driver_count,
        "work_receipt_ids": [item.receipt_id for item in workforce.work_receipts],
        "thought_path_receipt_ids": [
            item["receipt_id"] for item in workforce.thought_path_receipts
        ],
        "action_eligible": False,
        "economic_mutation": False,
        "exchange_call_count": 0,
        "order_call_count": 0,
        "derived_at": time.time(),
    }
    receipt_id = calibration.report["receipt_id"].rsplit(":", 1)[-1]
    evidence_path = ROOT / "state" / f"druidic_live_calibration_{receipt_id}.json"
    latest_path = ROOT / "state" / "druidic_live_calibration_latest.json"
    _atomic_json(evidence_path, payload)
    _atomic_json(latest_path, payload)
    return {
        "status": payload["status"],
        "reason": payload["reason"],
        "calibration_receipt_id": calibration.report["receipt_id"],
        "evidence_path": str(evidence_path.relative_to(ROOT)).replace("\\", "/"),
        "node_count": len(nodes),
        "node_driver_count": driver_count,
        "node_gammas": {node["seat"]: node["gamma"] for node in nodes},
        "cloud_model_count": payload["cloud_model_count"],
        "cloud_request_count": len(workforce.work_receipts),
        "exchange_call_count": 0,
        "order_call_count": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-age-s", type=float, default=300.0)
    parser.add_argument("--pair-wait-s", type=float, default=45.0)
    args = parser.parse_args(argv)
    try:
        result = run(max_age_s=args.max_age_s, pair_wait_s=args.pair_wait_s)
    except WorkforceCalibrationHold as exc:
        report = dict(exc.report)
        receipt_id = str(report["receipt_id"]).rsplit(":", 1)[-1]
        evidence_path = ROOT / "state" / f"druidic_live_calibration_hold_{receipt_id}.json"
        latest_path = ROOT / "state" / "druidic_live_calibration_hold_latest.json"
        _atomic_json(evidence_path, report)
        _atomic_json(latest_path, report)
        result = {
            "status": "hold",
            "reason": report["reason"],
            "failure_type": type(exc).__name__,
            "calibration_receipt_id": report["receipt_id"],
            "negative_seats": report.get("negative_seats", []),
            "evidence_path": str(evidence_path.relative_to(ROOT)).replace("\\", "/"),
            "action_eligible": False,
            "economic_mutation": False,
            "exchange_call_count": 0,
            "order_call_count": 0,
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    except Exception as exc:  # noqa: BLE001 - terminal fail-closed receipt
        result = {
            "status": "hold",
            "reason": str(exc)[:500],
            "failure_type": type(exc).__name__,
            "action_eligible": False,
            "economic_mutation": False,
            "exchange_call_count": 0,
            "order_call_count": 0,
        }
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
