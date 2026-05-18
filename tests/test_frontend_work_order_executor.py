from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_frontend_work_order_executor import execute_frontend_work_orders


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fake_repo(root: Path) -> None:
    (root / "aureon").mkdir()
    (root / "scripts").mkdir()
    app = root / "frontend" / "src" / "App.tsx"
    app.parent.mkdir(parents=True, exist_ok=True)
    app.write_text(
        'import { AureonGeneratedOperationalConsole } from "@/components/generated/AureonGeneratedOperationalConsole";\n'
        "export default function App() {\n"
        "  return (\n"
        "    <main>\n"
        "        <AureonGeneratedOperationalConsole />\n"
        "    </main>\n"
        "  );\n"
        "}\n",
        encoding="utf-8",
    )
    _write_json(
        root / "docs" / "audits" / "aureon_frontend_evolution_queue.json",
        {
            "summary": {"queue_count": 3},
            "work_orders": [
                {
                    "id": "ready",
                    "title": "Wire Ready",
                    "source_path": "frontend/src/components/Ready.tsx",
                    "target_screen": "overview",
                    "status": "ready_for_frontend_adapter",
                    "safety_boundary": "Read-only.",
                    "data_contract": {
                        "expected_topic": "organism.status",
                        "safe_fields": ["status", "health"],
                        "secret_policy": "metadata_only_hide_values",
                    },
                    "acceptance_tests": ["manifest", "render", "blockers"],
                },
                {
                    "id": "blocked",
                    "title": "Wire Blocked",
                    "source_path": "frontend/src/components/Blocked.tsx",
                    "target_screen": "trading",
                    "status": "blocked_security_review",
                    "safety_boundary": "Read-only.",
                    "data_contract": {
                        "expected_topic": "trading.status",
                        "safe_fields": ["status", "blocked_reason"],
                        "secret_policy": "metadata_only_hide_values",
                    },
                    "acceptance_tests": ["manifest", "render", "blockers"],
                },
                {
                    "id": "archive",
                    "title": "Wire Archive",
                    "source_path": "frontend/eslint.config.js",
                    "target_screen": "overview",
                    "status": "archive_candidate",
                    "safety_boundary": "Read-only.",
                },
            ],
        },
    )


def test_execute_frontend_work_orders_generates_manifest_component_and_mount(tmp_path: Path) -> None:
    _fake_repo(tmp_path)

    result = execute_frontend_work_orders("Aureon do the work orders", root=tmp_path)
    app_text = (tmp_path / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")

    assert result["schema_version"] == "aureon-frontend-work-order-execution-v1"
    assert result["summary"]["executed_count"] == 3
    assert result["summary"]["moved_from_queue_count"] == 3
    assert result["summary"]["remaining_queue_count"] == 0
    assert result["summary"]["validated_count"] == 3
    assert result["summary"]["runtime_patch_count"] == 3
    assert result["summary"]["adapter_record_count"] == 1
    assert result["summary"]["blocker_card_count"] == 1
    assert result["summary"]["archive_decision_count"] == 1
    assert result["queue_movement"]["queue_drained"] is True
    assert result["validation_summary"]["failed_validation_count"] == 0
    assert result["runtime_patch_registry"]["summary"]["active_patch_count"] == 3
    assert result["implemented_code_evidence"]["status"] == "materialized_runtime_patch_code_ready"
    assert result["implemented_code_evidence"]["materialized_patch_count"] == 3
    assert result["executions"][0]["queue_state"] == "completed_validated"
    assert result["executions"][0]["runtime_patch"]["status"] == "active_runtime_patch"
    assert "QueenCodeArchitect.write_file" in result["authoring_path"]
    assert (tmp_path / "frontend" / "public" / "aureon_frontend_work_order_execution.json").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_frontend_runtime_patch_registry.json").exists()
    assert (tmp_path / "frontend" / "src" / "components" / "generated" / "AureonWorkOrderExecutionConsole.tsx").exists()
    materialized = tmp_path / "frontend" / "src" / "components" / "generated" / "aureonEvolutionRuntimePatches.ts"
    assert materialized.exists()
    assert "AUREON_EVOLUTION_RUNTIME_PATCHES" in materialized.read_text(encoding="utf-8")
    assert "AureonWorkOrderExecutionConsole" in app_text
