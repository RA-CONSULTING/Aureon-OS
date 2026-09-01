import json
from pathlib import Path

from aureon.autonomous.aureon_self_enhancement_lifecycle import (
    SCHEMA_VERSION,
    build_contract_plan,
    build_self_enhancement_lifecycle,
    derive_enhancement_intents,
    render_markdown,
    write_report,
)


def _seed_root(tmp_path: Path) -> Path:
    (tmp_path / "aureon").mkdir()
    (tmp_path / "scripts").mkdir()
    audits = tmp_path / "docs" / "audits"
    audits.mkdir(parents=True)
    (audits / "repo_wide_organization_audit.json").write_text(
        json.dumps(
            {
                "status": "organized_with_attention_items",
                "summary": {
                    "stage_count": 12,
                    "attention_counts": {
                        "runtime_state_outside_runtime_stage": 2,
                        "generated_output_inside_source_area": 1,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (audits / "mind_wiring_audit.json").write_text(
        json.dumps({"counts": {"wired": 10, "partial": 0, "broken": 0, "unknown": 0}}),
        encoding="utf-8",
    )
    (audits / "aureon_system_readiness_audit.json").write_text(
        json.dumps(
            {
                "status": "working_with_attention_items",
                "summary": {"status_counts": {"working": 3}, "real_orders_allowed": False},
                "proofs": [
                    {"id": "mind", "name": "Mind", "status": "working", "summary": "ok", "systems": ["Mind"]},
                    {
                        "id": "accounts",
                        "name": "Accounts",
                        "status": "working_with_attention",
                        "summary": "manual filing required",
                        "systems": ["AccountingContextBridge"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_derives_enhancement_intents_from_audit_attention():
    intents = derive_enhancement_intents(
        {"summary": {"attention_counts": {"runtime_state_outside_runtime_stage": 2}}},
        {"proofs": []},
        {"status": {"top_gaps": []}},
    )

    ids = {intent.id for intent in intents}
    assert "runtime_state_staging_policy" in ids
    assert "refresh_self_readiness_after_changes" in ids


def test_contract_plan_can_queue_in_temporary_state(tmp_path):
    root = _seed_root(tmp_path)
    intents = derive_enhancement_intents(
        {"summary": {"attention_counts": {"generated_output_inside_source_area": 1}}},
        {"proofs": []},
        {"status": {"top_gaps": []}},
    )

    plan = build_contract_plan(root, intents, queue_contracts=False)

    assert plan["queued_persistently"] is False
    assert plan["workflow_contract_count"] == 4
    assert plan["intent_work_order_count"] >= 1
    assert plan["status"]["contract_count"] >= 5


def test_build_self_enhancement_lifecycle_and_write_report(tmp_path):
    root = _seed_root(tmp_path)

    report = build_self_enhancement_lifecycle(root, write_state=False)

    assert report.schema_version == SCHEMA_VERSION
    assert report.summary["stage_count"] >= 5
    assert report.summary["enhancement_intent_count"] >= 2
    assert any(stage.id == "restart_apply" for stage in report.stages)
    assert report.restart_handoff.preflight_command.startswith(".venv/bin/python -I -S -B")
    assert "--target-id ignition" in report.restart_handoff.preflight_command
    assert report.restart_handoff.apply_command.startswith("HOLD:")

    markdown = render_markdown(report)
    assert "Aureon Self-Enhancement Lifecycle" in markdown
    assert "Enhancement Intents" in markdown

    md_path, json_path = write_report(report, tmp_path / "self.md", tmp_path / "self.json")
    assert md_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
