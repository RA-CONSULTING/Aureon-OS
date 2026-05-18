from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_evolution_queue_autonomous_certification import (
    build_and_write_evolution_queue_autonomous_certification,
)


def _order(order_id: str, status: str, safety: str = "observation") -> dict:
    return {
        "id": order_id,
        "title": f"Wire {order_id}",
        "source_path": f"frontend/src/components/{order_id}.tsx",
        "target_screen": "overview",
        "priority": 50,
        "status": status,
        "safety_boundary": safety,
        "frontend_action": "Create a read-only blocker card in Overview before any interactive control."
        if status == "blocked_security_review"
        else "Create frontend/src/components/unified/TestStatusCard.tsx and mount it in Overview.",
        "data_contract": {
            "expected_topic": "organism.status",
            "safe_fields": ["status", "health", "blockers", "last_updated"],
            "secret_policy": "metadata_only_hide_values",
        },
        "acceptance_tests": [
            "Manifest exposes source path, target screen, safety boundary, and status.",
            "Unified frontend renders the work order without importing/executing the legacy system.",
            "Any missing/stale/fake data is displayed as a blocker instead of trusted.",
        ],
        "evidence": {"safety_class": safety},
    }


def _write_queue(root: Path, orders: list[dict]) -> None:
    public = root / "frontend" / "public" / "aureon_frontend_evolution_queue.json"
    docs = root / "docs" / "audits" / "aureon_frontend_evolution_queue.json"
    public.parent.mkdir(parents=True, exist_ok=True)
    docs.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "aureon-frontend-evolution-queue-v1",
        "status": "evolution_queue_ready_with_blockers",
        "generated_at": "2026-05-17T00:00:00+00:00",
        "summary": {"queue_count": len(orders)},
        "work_orders": orders,
    }
    public.write_text(json.dumps(payload), encoding="utf-8")
    docs.write_text(json.dumps(payload), encoding="utf-8")


def test_certifies_every_evolution_queue_item_with_safe_outcomes(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _order("ready_panel", "ready_for_frontend_adapter"),
            _order("trading_panel", "blocked_security_review", "live_trading_boundary"),
            _order("old_config", "archive_candidate"),
        ],
    )

    report = build_and_write_evolution_queue_autonomous_certification(root=tmp_path)

    assert report["status"] == "evolution_queue_autonomous_certified"
    assert report["ok"] is True
    assert report["summary"]["processed_count"] == 3
    assert report["summary"]["throughput_percent"] == 100
    assert report["summary"]["fake_pass_count"] == 0
    assert report["summary"]["manual_boundary_visible_count"] == 1
    assert {case["autonomous_outcome"] for case in report["cases"]} == {
        "read_only_adapter_certified",
        "read_only_blocker_card_certified",
        "archive_decision_certified",
    }
    assert (tmp_path / "state" / "aureon_evolution_queue_autonomous_certification_last_run.json").exists()
    assert (tmp_path / "docs" / "audits" / "aureon_evolution_queue_autonomous_certification.md").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_evolution_queue_autonomous_certification.json").exists()


def test_fake_pass_detection_blocks_missing_manifest_proof(tmp_path: Path) -> None:
    bad = _order("bad_panel", "ready_for_frontend_adapter")
    bad["source_path"] = ""
    _write_queue(tmp_path, [bad])

    report = build_and_write_evolution_queue_autonomous_certification(root=tmp_path)

    assert report["ok"] is False
    assert report["status"] == "evolution_queue_autonomous_certification_attention"
    assert report["summary"]["failed_count"] == 1
    assert report["summary"]["fake_pass_count"] == 1
    assert report["cases"][0]["handover_state"]["state"] == "blocked_by_failed_proof"


def test_certification_attaches_compact_state_to_coding_bridge(tmp_path: Path) -> None:
    bridge = tmp_path / "frontend" / "public" / "aureon_coding_organism_bridge.json"
    bridge.parent.mkdir(parents=True, exist_ok=True)
    bridge.write_text(json.dumps({"summary": {}}), encoding="utf-8")
    _write_queue(tmp_path, [_order("ready_panel", "ready_for_frontend_adapter")])

    build_and_write_evolution_queue_autonomous_certification(root=tmp_path)

    payload = json.loads(bridge.read_text(encoding="utf-8"))
    assert payload["evolution_queue_autonomous_certification"]["status"] == "evolution_queue_autonomous_certified"
    assert payload["summary"]["evolution_queue_certification_processed_count"] == 1
