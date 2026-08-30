import json

from aureon.autonomous.aureon_system_readiness_audit import (
    AureonSystemReadinessAudit,
    CapabilityProof,
    probe_capability_growth_loop,
    probe_contract_stack,
    probe_goal_routing,
    probe_hnc_saas_security,
    probe_ignition,
    probe_repo_organization,
    probe_saas_product_inventory,
    probe_trading_brain,
    render_markdown,
    write_report,
)


def test_dirty_repo_is_attention_not_a_blocked_capability(tmp_path):
    audits = tmp_path / "docs" / "audits"
    audits.mkdir(parents=True)
    (audits / "repo_wide_organization_audit.json").write_text(
        json.dumps(
            {
                "summary": {
                    "recorded_files": 42,
                    "stage_count": 5,
                    "unstaged_file_count": 7,
                    "attention_counts": {"unstaged_path": 7},
                },
                "contract_surfaces": [{"id": "aureon", "status": "present"}],
            }
        ),
        encoding="utf-8",
    )

    proof = probe_repo_organization(tmp_path)

    assert proof.status == "working_with_attention"
    assert "Preserve existing local work" in proof.next_action


def test_missing_internal_audit_becomes_repair_work_not_a_hard_block(tmp_path):
    proof = probe_ignition(tmp_path)

    assert proof.status == "repair_pending"
    assert "--audit-only" in proof.next_action


def test_trading_readiness_probe_is_simulated_and_blocks_real_orders():
    proof = probe_trading_brain()

    assert proof.status == "working_safe_simulation"
    assert proof.evidence["real_orders_allowed"] is False
    assert proof.evidence["size_plan"]["approved"] is True
    assert proof.evidence["margin_decision"]["approved"] is True
    assert "does not call Kraken" in proof.safety_boundary


def test_contract_stack_probe_builds_goal_task_job_work_order():
    proof = probe_contract_stack()

    assert proof.status == "working"
    assert proof.evidence["status"]["contract_count"] == 4
    assert "organism.contract.goal.created" in proof.evidence["topics"]
    assert "work_order" in proof.evidence["workflow_contract_types"]


def test_goal_routing_probe_uses_full_route_list(tmp_path):
    proof = probe_goal_routing(tmp_path)

    assert proof.status in {"working", "working_with_attention"}
    assert "safe_research_corpus" in proof.evidence["routes"]
    assert "hnc_saas_security_architect" in proof.evidence["routes"]
    assert "saas_product_inventory" in proof.evidence["routes"]
    assert proof.evidence["missing_required_routes"] == []


def test_hnc_saas_security_probe_builds_blueprint_without_deployment(tmp_path):
    (tmp_path / "aureon" / "core").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "aureon" / "core" / "hnc_gateway.py").write_text("class HNCGateway: pass\n", encoding="utf-8")

    proof = probe_hnc_saas_security(tmp_path)

    assert proof.status in {"working_with_attention", "working"}
    assert proof.evidence["summary"]["control_count"] >= 12
    assert proof.evidence["summary"]["unhackable_internal_goal_active"] is True
    assert proof.evidence["summary"]["authorized_self_attack_required"] is True
    assert proof.evidence["unhackable_pursuit_loop"]
    assert "no third-party attack" in proof.safety_boundary


def test_saas_product_inventory_probe_counts_frontend_and_backend(tmp_path):
    (tmp_path / "aureon").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "frontend" / "src" / "components").mkdir(parents=True)
    (tmp_path / "frontend" / "src" / "App.tsx").write_text(
        "import { Panel } from './components/Panel'; export default function App(){return <Panel/>}",
        encoding="utf-8",
    )
    (tmp_path / "frontend" / "src" / "main.tsx").write_text("import App from './App';", encoding="utf-8")
    (tmp_path / "frontend" / "src" / "components" / "Panel.tsx").write_text(
        "export function Panel(){return null}",
        encoding="utf-8",
    )
    (tmp_path / "supabase" / "functions" / "status").mkdir(parents=True)
    (tmp_path / "supabase" / "functions" / "status" / "index.ts").write_text(
        "Deno.serve(() => new Response('{}'))",
        encoding="utf-8",
    )

    proof = probe_saas_product_inventory(tmp_path)

    assert proof.status in {"working", "working_with_attention"}
    assert proof.evidence["inventory_summary"]["surface_count"] >= 4
    assert "overview" in proof.evidence["screen_ids"]


def test_capability_growth_probe_scores_domains_without_external_mutation(tmp_path):
    audits = tmp_path / "docs" / "audits"
    audits.mkdir(parents=True)
    (tmp_path / "aureon").mkdir()
    (tmp_path / "scripts").mkdir()
    (audits / "aureon_repo_self_catalog.json").write_text(
        json.dumps({"status": "catalog_complete", "summary": {"cataloged_file_count": 3, "truncated": False}}),
        encoding="utf-8",
    )
    (audits / "mind_wiring_audit.json").write_text(
        json.dumps({"counts": {"wired": 3, "partial": 0, "broken": 0, "unknown": 0}}),
        encoding="utf-8",
    )
    (audits / "aureon_system_readiness_audit.json").write_text(
        json.dumps(
            {
                "proofs": [
                    {"id": "repo_organization", "status": "working", "summary": "ok"},
                    {"id": "goal_routing", "status": "working", "summary": "ok"},
                    {"id": "trading_brain", "status": "working_safe_simulation", "summary": "sim"},
                    {"id": "accounting_brain", "status": "working_with_attention", "summary": "review"},
                    {"id": "research_vault", "status": "working", "summary": "ok"},
                    {"id": "hnc_saas_security", "status": "working_with_attention", "summary": "queued"},
                    {"id": "llm_capability", "status": "working", "summary": "ok"},
                    {"id": "operator_surfaces", "status": "working", "summary": "ok"},
                    {"id": "ignition", "status": "working", "summary": "ok"},
                ]
            }
        ),
        encoding="utf-8",
    )

    proof = probe_capability_growth_loop(tmp_path)

    assert proof.status in {"working", "working_with_attention"}
    assert proof.evidence["latest_iteration"]["domain_count"] >= 10
    assert "does not run live orders" in proof.safety_boundary


def test_readiness_report_render_and_write(tmp_path):
    report = AureonSystemReadinessAudit(
        schema_version="aureon-system-readiness-audit-v1",
        generated_at="2026-05-11T00:00:00+00:00",
        repo_root=str(tmp_path),
        status="working_as_designed_safe_mode",
        proofs=[
            CapabilityProof(
                id="demo",
                name="Demo Capability",
                status="working",
                summary="Demo summary.",
                systems=["DemoSystem"],
                evidence={"ok": True},
                safety_boundary="Read-only.",
                next_action="Keep covered.",
            )
        ],
        safety={"AUREON_AUDIT_MODE": "1", "real_orders_allowed": False},
        summary={"proof_count": 1},
        notes=["No external mutation."],
    )

    markdown = render_markdown(report)
    assert "Aureon System Readiness Audit" in markdown
    assert "Demo Capability" in markdown

    md_path, json_path = write_report(report, tmp_path / "readiness.md", tmp_path / "readiness.json")
    assert md_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["status"] == "working_as_designed_safe_mode"
    assert data["proofs"][0]["id"] == "demo"
