from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from aureon.autonomous.aureon_capability_forge import REPO_ROOT
from aureon.autonomous.aureon_frontend_evolution_queue import (
    DEFAULT_OUTPUT_JSON as DEFAULT_EVOLUTION_JSON,
    DEFAULT_PUBLIC_JSON as DEFAULT_EVOLUTION_PUBLIC_JSON,
    build_frontend_evolution_queue,
    write_queue,
)


SCHEMA_VERSION = "aureon-evolution-queue-autonomous-certification-v1"
DEFAULT_STATE_PATH = Path("state/aureon_evolution_queue_autonomous_certification_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_evolution_queue_autonomous_certification.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_evolution_queue_autonomous_certification.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_evolution_queue_autonomous_certification.json")
CODING_BRIDGE_EVIDENCE_PATHS = [
    Path("state/aureon_coding_organism_last_run.json"),
    Path("docs/audits/aureon_coding_organism_bridge.json"),
    Path("frontend/public/aureon_coding_organism_bridge.json"),
]

MANUAL_BOUNDARY_SAFETY = {
    "live_trading_boundary",
    "payment_or_kyc_boundary",
    "credential_or_auth_boundary",
    "admin_or_tenant_boundary",
}


def _default_root() -> Path:
    return REPO_ROOT


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rooted(root: Path, rel: Path) -> Path:
    return rel if rel.is_absolute() else root / rel


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}
    return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _write_text(path: Path, text: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _load_or_build_queue(root: Path) -> Dict[str, Any]:
    queue = _read_json(_rooted(root, DEFAULT_EVOLUTION_PUBLIC_JSON)) or _read_json(_rooted(root, DEFAULT_EVOLUTION_JSON))
    if queue.get("work_orders"):
        return queue
    built = build_frontend_evolution_queue(root).to_dict()
    write_queue(
        build_frontend_evolution_queue(root),
        markdown_path=_rooted(root, Path("docs/audits/aureon_frontend_evolution_queue.md")),
        json_path=_rooted(root, DEFAULT_EVOLUTION_JSON),
        public_json_path=_rooted(root, DEFAULT_EVOLUTION_PUBLIC_JSON),
        vault_path=_rooted(root, Path(".obsidian/Aureon Self Understanding/aureon_frontend_evolution_queue.md")),
    )
    return built


def _outcome_for(order: Dict[str, Any]) -> Dict[str, Any]:
    status = str(order.get("status") or "")
    safety = str(order.get("safety_boundary") or order.get("evidence", {}).get("safety_class") or "")
    if status == "blocked_security_review":
        return {
            "outcome": "read_only_blocker_card_certified",
            "bucket": "manual_boundary_visible",
            "handover_state": "boundary_visible",
            "description": "Unsafe interactive authority is not mounted; a read-only blocker card is the autonomous output.",
        }
    if status == "needs_safe_status_adapter":
        return {
            "outcome": "safe_status_adapter_certified",
            "bucket": "safe_status_adapter",
            "handover_state": "safe_status_visible",
            "description": "Credential/auth/admin state may be shown as metadata only through a safe status adapter.",
        }
    if status == "link_generated_output":
        return {
            "outcome": "evidence_link_certified",
            "bucket": "evidence_link",
            "handover_state": "evidence_link_visible",
            "description": "Generated accounting or document output is represented as an evidence link, not executed.",
        }
    if status == "archive_candidate":
        return {
            "outcome": "archive_decision_certified",
            "bucket": "archive_decision",
            "handover_state": "archive_decision_visible",
            "description": "Low-value support file is classified for archive/supporting status instead of a dashboard panel.",
        }
    if status == "ready_for_frontend_adapter":
        return {
            "outcome": "read_only_adapter_certified",
            "bucket": "read_only_adapter",
            "handover_state": "adapter_ready",
            "description": "A read-only adapter can be generated and mounted without importing legacy controls.",
        }
    if safety in MANUAL_BOUNDARY_SAFETY:
        return {
            "outcome": "manual_boundary_status_certified",
            "bucket": "manual_boundary_visible",
            "handover_state": "boundary_visible",
            "description": "Manual authority boundary is visible and does not block safe queue throughput.",
        }
    return {
        "outcome": "watch_only_certified",
        "bucket": "watch_only",
        "handover_state": "watch_record_visible",
        "description": "Work order is retained as watch-only evidence.",
    }


def _proof(order: Dict[str, Any], outcome: Dict[str, Any]) -> List[Dict[str, Any]]:
    data_contract = order.get("data_contract") if isinstance(order.get("data_contract"), dict) else {}
    acceptance_tests = order.get("acceptance_tests") if isinstance(order.get("acceptance_tests"), list) else []
    source_path = str(order.get("source_path") or "")
    target_screen = str(order.get("target_screen") or "")
    frontend_action = str(order.get("frontend_action") or "")
    status = str(order.get("status") or "")
    safety = str(order.get("safety_boundary") or order.get("evidence", {}).get("safety_class") or "")
    return [
        {
            "id": "manifest_contract_present",
            "ok": bool(order.get("id") and source_path and target_screen and status),
            "evidence": f"{source_path} -> {target_screen} ({status})",
        },
        {
            "id": "safe_data_contract_declared",
            "ok": bool(data_contract.get("safe_fields") and data_contract.get("secret_policy") == "metadata_only_hide_values"),
            "evidence": data_contract.get("expected_topic") or "missing",
        },
        {
            "id": "legacy_execution_not_required",
            "ok": True,
            "evidence": "certification reads manifest evidence only; no legacy dashboard import or execution",
        },
        {
            "id": "boundary_handled",
            "ok": (
                outcome["bucket"] != "manual_boundary_visible"
                or "read-only" in frontend_action.lower()
                or "status adapter" in frontend_action.lower()
                or safety in MANUAL_BOUNDARY_SAFETY
            ),
            "evidence": frontend_action or outcome["description"],
        },
        {
            "id": "acceptance_tests_present",
            "ok": len(acceptance_tests) >= 3,
            "evidence": f"{len(acceptance_tests)} acceptance test(s)",
        },
    ]


def _certify_order(order: Dict[str, Any], queue_source: str) -> Dict[str, Any]:
    outcome = _outcome_for(order)
    proof = _proof(order, outcome)
    passed = all(item["ok"] for item in proof)
    fake_pass = outcome["handover_state"] and not passed
    return {
        "id": order.get("id"),
        "title": order.get("title"),
        "source_path": order.get("source_path"),
        "target_screen": order.get("target_screen"),
        "priority": order.get("priority"),
        "input_status": order.get("status"),
        "safety_boundary": order.get("safety_boundary") or order.get("evidence", {}).get("safety_class"),
        "autonomous_outcome": outcome["outcome"],
        "outcome_bucket": outcome["bucket"],
        "description": outcome["description"],
        "proof_checklist": proof,
        "ok": passed and not fake_pass,
        "fake_pass": bool(fake_pass),
        "handover_state": {
            "state": outcome["handover_state"] if passed else "blocked_by_failed_proof",
            "ready": passed and not fake_pass,
            "manual_boundary_visible": outcome["bucket"] == "manual_boundary_visible",
        },
        "actual_artifacts": {
            "queue_source": queue_source,
            "public_evidence": "/aureon_evolution_queue_autonomous_certification.json",
            "source_path": order.get("source_path"),
        },
        "repair_attempts": [],
        "failure_reason": "" if passed else ", ".join(item["id"] for item in proof if not item["ok"]),
    }


def _attach_to_coding_bridge(root: Path, compact: Dict[str, Any]) -> List[Dict[str, Any]]:
    writes: List[Dict[str, Any]] = []
    for rel in CODING_BRIDGE_EVIDENCE_PATHS:
        path = _rooted(root, rel)
        payload = _read_json(path)
        if not payload:
            continue
        payload["evolution_queue_autonomous_certification"] = compact
        summary = payload.setdefault("summary", {})
        if isinstance(summary, dict):
            compact_summary = compact.get("summary") or {}
            summary["evolution_queue_certification_status"] = compact.get("status")
            summary["evolution_queue_certification_processed_count"] = compact_summary.get("processed_count")
            summary["evolution_queue_certification_queue_count"] = compact_summary.get("queue_count")
        writes.append(_write_json(path, payload))
    return writes


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon Evolution Queue Autonomous Certification",
        "",
        f"- status: {report.get('status')}",
        f"- processed: {summary.get('processed_count')}/{summary.get('queue_count')}",
        f"- throughput: {summary.get('throughput_percent')}%",
        f"- safe autonomous outcomes: {summary.get('safe_autonomous_outcome_count')}",
        f"- manual boundaries visible: {summary.get('manual_boundary_visible_count')}",
        f"- failed: {summary.get('failed_count')}",
        f"- fake passes: {summary.get('fake_pass_count')}",
        "",
        "## Outcome Buckets",
    ]
    for key, value in sorted((summary.get("outcome_buckets") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## First Cases"])
    for case in report.get("cases", [])[:20]:
        lines.append(
            f"- {case.get('id')}: {case.get('autonomous_outcome')} -> {case.get('handover_state', {}).get('state')}"
        )
    return "\n".join(lines) + "\n"


def build_and_write_evolution_queue_autonomous_certification(
    *,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    generated_at = _utc_now()
    queue = _load_or_build_queue(root)
    orders = [order for order in queue.get("work_orders", []) if isinstance(order, dict)]
    queue_source = str(DEFAULT_EVOLUTION_PUBLIC_JSON)
    cases = [_certify_order(order, queue_source) for order in orders]
    buckets = Counter(case.get("outcome_bucket") for case in cases)
    failures = [case for case in cases if not case.get("ok")]
    fake_passes = [case for case in cases if case.get("fake_pass")]
    processed_count = len(cases)
    queue_count = int((queue.get("summary") or {}).get("queue_count") or len(orders))
    throughput_percent = round((processed_count / queue_count) * 100, 2) if queue_count else 0.0
    certified = bool(queue_count and processed_count == queue_count and not failures and not fake_passes)
    status = (
        "evolution_queue_584_autonomous_certified"
        if certified and queue_count == 584
        else "evolution_queue_autonomous_certified"
        if certified
        else "evolution_queue_autonomous_certification_attention"
    )
    summary = {
        "queue_count": queue_count,
        "processed_count": processed_count,
        "throughput_percent": throughput_percent,
        "safe_autonomous_outcome_count": len([case for case in cases if case.get("ok")]),
        "manual_boundary_visible_count": buckets.get("manual_boundary_visible", 0),
        "read_only_adapter_count": buckets.get("read_only_adapter", 0),
        "blocker_card_count": len([case for case in cases if case.get("autonomous_outcome") == "read_only_blocker_card_certified"]),
        "safe_status_adapter_count": buckets.get("safe_status_adapter", 0),
        "evidence_link_count": buckets.get("evidence_link", 0),
        "archive_decision_count": buckets.get("archive_decision", 0),
        "watch_only_count": buckets.get("watch_only", 0),
        "failed_count": len(failures),
        "fake_pass_count": len(fake_passes),
        "outcome_buckets": dict(buckets),
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": status,
        "ok": certified,
        "repo_root": str(root),
        "source_queue": {
            "status": queue.get("status"),
            "generated_at": queue.get("generated_at"),
            "summary": queue.get("summary", {}),
            "public_json": str(DEFAULT_EVOLUTION_PUBLIC_JSON),
        },
        "certification_contract": {
            "mode": "full_safe_local_autonomy",
            "claim": "Every evolution work order receives an autonomous safe outcome or a visible true-boundary state.",
            "no_legacy_execution": True,
            "no_external_mutation": True,
            "manual_authority_boundaries": sorted(MANUAL_BOUNDARY_SAFETY),
            "fake_pass_policy": "handover_ready is blocked when proof is missing",
        },
        "summary": summary,
        "cases": cases,
        "failures": failures[:20],
        "fake_passes": fake_passes[:20],
        "output_files": [
            str(DEFAULT_STATE_PATH),
            str(DEFAULT_AUDIT_JSON),
            str(DEFAULT_AUDIT_MD),
            str(DEFAULT_PUBLIC_JSON),
        ],
    }
    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    compact = {
        "schema_version": SCHEMA_VERSION,
        "status": report["status"],
        "ok": report["ok"],
        "generated_at": report["generated_at"],
        "summary": report["summary"],
        "sample_cases": cases[:8],
    }
    report["write_info"] = {
        "evidence_writes": writes,
        "coding_bridge_evidence_writes": _attach_to_coding_bridge(root, compact),
    }
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Certify Aureon's full frontend evolution queue autonomous throughput.")
    parser.add_argument("--root", default="", help="Repository root. Defaults to current Aureon repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else None
    report = build_and_write_evolution_queue_autonomous_certification(root=root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        summary = report.get("summary", {})
        print(
            f"{report.get('status')}: processed={summary.get('processed_count')}/"
            f"{summary.get('queue_count')} fake_passes={summary.get('fake_pass_count')} "
            f"failed={summary.get('failed_count')}"
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
