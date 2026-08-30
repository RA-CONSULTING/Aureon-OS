from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from aureon.autonomous.aureon_unified_self_evolution_loop import (
    build_and_write_unified_self_evolution_loop,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class _QuestioningHarness:
    def run_cycle(self, **kwargs):
        assert kwargs["include_audit"] is False
        assert kwargs["include_self_scan"] is False
        assert kwargs["augment_questions"] is False
        assert "never close introspection or repair" in kwargs["questions"][0]
        return SimpleNamespace(
            cycle_id="selfq-test",
            answer_source="ollama",
            summary="Repair the highest-ranked internal pathway.",
            answers=[{"question": "q", "answer": "a", "evidence": ["catalog"]}],
            next_actions=[],
            errors=[],
            note_path="autonomy/test.md",
        )


class _SwarmHarness:
    def run(self, objective, flow):
        assert objective == "repair the backend"
        assert flow["internal_blocking"] if "internal_blocking" in flow else True
        return {
            "status": "hnc_phi_swarm_synthesized",
            "ok": True,
            "synthesis": {"answer": {"consensus": "repair canonical contract bus"}},
            "summary": {
                "recruited_worker_count": 3,
                "successful_worker_count": 3,
                "distinct_worker_models": 3,
                "api_call_count": 4,
                "research_packet_count": 3,
                "internal_blocking": False,
                "credential_values_exposed": False,
            },
        }


def test_unified_evolution_keeps_all_internal_capabilities_alive_in_dark_field(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "docs/audits/aureon_system_readiness_audit.json",
        {
            "proofs": [
                {
                    "id": "repo_organization",
                    "status": "blocked_or_missing",
                    "next_action": "Reconcile organization evidence.",
                    "safety_boundary": "read only",
                }
            ]
        },
    )

    report = build_and_write_unified_self_evolution_loop(
        root=tmp_path,
        prompt="repair the backend",
        field_inputs={
            "gamma": None,
            "advisory_open": None,
            "lighthouse_severity": None,
            "auris_confidence": None,
            "beta": 1.0,
            "sources": {},
        },
        cognitive_bridge_report={"ok": True, "status": "ollama_cognitive_bridge_ready", "summary": {}},
        self_questioning=_QuestioningHarness(),
        run_swarm=True,
        phi_swarm=_SwarmHarness(),
    )

    assert report["ok"] is True
    assert report["status"] == "unified_self_evolution_reasoned"
    assert report["internal_blocking"] is False
    assert report["coherence_flow"]["flow"] == "observe"
    assert all(report["coherence_flow"]["capabilities"].values())
    assert report["autonomous_work_orders"][0]["blocking"] is False
    assert report["summary"]["phi_swarm_distinct_models"] == 3
    assert report["phi_swarm"]["synthesis"]["answer"]["consensus"] == "repair canonical contract bus"
    assert (tmp_path / "state/aureon_unified_self_evolution_last_run.json").exists()
    assert (tmp_path / "docs/audits/aureon_unified_self_evolution_loop.md").exists()
    assert (tmp_path / "frontend/public/aureon_unified_self_evolution_loop.json").exists()


def test_low_coherence_redirects_to_repair_without_a_hard_block(tmp_path: Path) -> None:
    report = build_and_write_unified_self_evolution_loop(
        root=tmp_path,
        run_ollama=False,
        field_inputs={
            "gamma": 0.08,
            "advisory_open": False,
            "lighthouse_severity": "critical",
            "auris_confidence": 0.1,
            "beta": 1.2,
            "sources": {},
        },
        cognitive_bridge_report={"ok": False, "status": "offline", "summary": {}},
    )

    assert report["status"] == "unified_self_evolution_observed"
    assert report["internal_blocking"] is False
    assert report["coherence_flow"]["flow"] == "repair"
    assert report["coherence_flow"]["patch_batch_limit"] == 1
    assert "rollback" in report["coherence_flow"]["required_test_layers"]
