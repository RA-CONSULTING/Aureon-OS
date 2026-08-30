from __future__ import annotations

import base64
import hashlib
import json
import sys
import types
import zlib
from pathlib import Path

from pytest import MonkeyPatch

from aureon.autonomous.aureon_agent_company_builder import (
    SCHEMA_VERSION,
    build_agent_company_bill_list,
    build_and_write_agent_company_bill_list,
)
from aureon.autonomous.aureon_coding_organism_bridge import submit_coding_prompt
from aureon.core.goal_execution_engine import GoalExecutionEngine


def _seed_repo(root: Path) -> None:
    for path in [
        "aureon/autonomous",
        "aureon/core",
        "aureon/exchanges",
        "aureon/vault/voice",
        "aureon/queen",
        "aureon/code_architect",
        "frontend/src/components/generated",
        "frontend/public",
        "docs/audits",
        "tests",
        "state",
        "logs",
        ".obsidian",
        "Kings_Accounting_Suite/tools",
    ]:
        (root / path).mkdir(parents=True, exist_ok=True)
    for file_path in [
        "aureon/core/goal_execution_engine.py",
        "aureon/core/organism_contracts.py",
        "aureon/autonomous/aureon_goal_capability_map.py",
        "aureon/autonomous/aureon_local_task_queue.py",
        "aureon/autonomous/aureon_safe_code_control.py",
        "aureon/autonomous/aureon_coding_organism_bridge.py",
        "aureon/autonomous/aureon_trading_intelligence_checklist.py",
        "aureon/autonomous/aureon_data_ocean.py",
        "aureon/autonomous/aureon_global_financial_coverage_map.py",
        "aureon/autonomous/aureon_coding_agent_skill_base.py",
        "aureon/autonomous/aureon_safe_desktop_control.py",
        "aureon/autonomous/aureon_frontend_unification_plan.py",
        "aureon/autonomous/aureon_frontend_evolution_queue.py",
        "aureon/autonomous/hnc_saas_security_architect.py",
        "aureon/autonomous/hnc_authorized_attack_lab.py",
        "aureon/exchanges/unified_market_trader.py",
        "aureon/exchanges/kraken_asset_registry.py",
        "aureon/queen/queen_code_architect.py",
        "aureon/queen/accounting_context_bridge.py",
        "aureon/code_architect/architect.py",
        "Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py",
        "frontend/src/App.tsx",
        "frontend/package.json",
        "README.md",
        "RUNNING.md",
        "QUICK_START.md",
        "CAPABILITIES.md",
    ]:
        target = root / file_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# seeded\n", encoding="utf-8")


def test_agent_company_builder_creates_ceo_to_cleaner_registry(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_agent_company_bill_list(root=tmp_path, goal="create company of agents")

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["company_name"] == "Aureon Agent Company"
    assert report["summary"]["department_count"] >= 7
    assert report["summary"]["role_count"] >= 30
    assert report["summary"]["agent_count"] == report["summary"]["role_count"]
    assert report["summary"]["ceo_to_cleaner_coverage"] is True
    titles = {role["title"] for role in report["roles"]}
    assert {"CEO Goal Steward", "Log Janitor", "Stale State Cleaner"}.issubset(titles)
    assert all(role["existing_surfaces"] or role["work_orders"] for role in report["roles"])
    assert all(agent["metadata"]["registry_only_v1"] is True for agent in report["agents"])
    assert report["summary"]["roles_with_day_plan_count"] == report["summary"]["role_count"]
    assert report["summary"]["roles_with_whole_organism_access_count"] == report["summary"]["role_count"]
    assert report["summary"]["not_one_trick_role_count"] == report["summary"]["role_count"]
    assert report["summary"]["daily_operating_loop_ready"] is True
    assert report["summary"]["mycelium_ethos"] == "mycelium_network_organisation"
    assert report["summary"]["mycelium_doctrine_ready"] is True
    assert report["summary"]["bio_cosmic_ethos"] == "bio_cosmic_living_system_organisation"
    assert report["summary"]["bio_cosmic_doctrine_ready"] is True
    assert report["mycelium_organisation_doctrine"]["ethos"] == "mycelium_network_organisation"
    assert len(report["mycelium_organisation_doctrine"]["metaphor_map"]) >= 5
    assert any(
        item["mycelium_part"] == "fruiting_bodies"
        and "temporary recruited agents" in item["aureon_part"]
        for item in report["mycelium_organisation_doctrine"]["metaphor_map"]
    )
    assert report["bio_cosmic_organisation_doctrine"]["ethos"] == "bio_cosmic_living_system_organisation"
    scales = {item["scale"] for item in report["bio_cosmic_organisation_doctrine"]["scale_ladder"]}
    assert {"cell", "ant_colony", "stars_and_constellations"}.issubset(scales)
    assert report["summary"]["agency_model"] == "prompt_as_client_job_agency"
    assert report["summary"]["agency_workforce_role_count"] >= 5
    assert report["summary"]["roles_with_workforce_lifecycle_count"] == report["summary"]["role_count"]
    assert report["summary"]["subcontractor_eligible_role_count"] > 0
    assert report["summary"]["temporary_staff_retirement_policy_ready"] is True
    assert report["summary"]["memory_phonebook_ready"] is True
    assert report["summary"]["sha256_memory_entry_count"] == report["summary"]["role_count"]
    assert report["summary"]["zlib_memory_archive_ready"] is True
    assert report["workforce_memory_phonebook"]["summary"]["entry_count"] == report["summary"]["role_count"]
    assert report["workforce_memory_phonebook"]["summary"]["sha256_addressed"] is True
    assert report["workforce_memory_phonebook"]["summary"]["zlib_compressed"] is True
    assert "_bundle_payloads" not in report["workforce_memory_phonebook"]
    assert report["completion_report"]["did_attach_mycelium_organisation_doctrine"] is True
    assert report["completion_report"]["did_attach_bio_cosmic_organisation_doctrine"] is True


def test_agent_company_roles_have_day_jobs_and_whole_organism_access(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_agent_company_bill_list(root=tmp_path, goal="make every worker know the day job")

    policy = report["whole_organism_access_policy"]
    assert policy["access_model"] == "whole_organism_with_role_authority"
    assert "GoalExecutionEngine" in policy["universal_surfaces"]
    assert "bypass live trading runtime gates" in policy["blocked_actions"]
    assert len(report["daily_operating_loop"]) >= 6
    for role in report["roles"]:
        assert len(role["day_to_day"]) >= 6
        assert len(role["standing_checks"]) >= 5
        assert len(role["escalation_rules"]) >= 5
        assert len(role["cross_training"]) >= 4
        assert role["whole_organism_access"]["access_model"] == "whole_organism_with_role_authority"
        assert "GoalExecutionEngine" in role["whole_organism_access"]["allowed_surfaces"]
        assert role["whole_organism_access"]["authority_boundary_ids"]
        assert "who/what/where/when/how/act" in role["whole_organism_access"]["evidence_rule"]
        assert role["workforce_lifecycle"]["agency_model"] == "prompt_as_client_job_agency"
        assert role["workforce_lifecycle"]["hire_when"]
        assert role["workforce_lifecycle"]["retire_when"]


def test_agent_company_compares_big_market_ai_systems(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_agent_company_bill_list(root=tmp_path, goal="market ai capability expansion hiring plan")

    providers = {item["provider"] for item in report["capability_market_comparison"]}
    assert {
        "OpenAI",
        "Anthropic",
        "Google",
        "Microsoft",
        "GitHub",
        "Replit",
        "Cursor",
        "Cognition",
    }.issubset(providers)
    assert report["summary"]["market_ai_system_count"] >= 8
    assert report["completion_report"]["did_compare_market_ai_systems"] is True
    assert all(item["hired_temporary_workers"] for item in report["capability_market_comparison"])
    assert all("authority_boundary" in item["next_work_order"] for item in report["capability_market_comparison"])


def test_agent_company_recruits_workers_from_scope_and_internal_search(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_agent_company_bill_list(
        root=tmp_path,
        goal="Client needs an online-search coding agent crew with browser smoke tests, work orders, proof, and release handover.",
    )
    recruitment = report["recruitment_engine"]

    assert recruitment["status"] == "recruitment_ready"
    assert recruitment["summary"]["recruited_worker_count"] >= 6
    assert recruitment["summary"]["agent_blueprint_count"] == recruitment["summary"]["recruited_worker_count"]
    assert recruitment["summary"]["internal_search_count"] >= 3
    assert recruitment["summary"]["internal_hit_count"] > 0
    titles = {worker["title"] for worker in recruitment["recruited_workers"]}
    assert {"Skill Headhunter", "Subcontractor Crew Builder", "Test Pilot"}.issubset(titles)
    assert all(blueprint["scope_contract"]["client_goal"] for blueprint in recruitment["agent_blueprints"])
    assert report["completion_report"]["did_build_recruitment_engine"] is True
    assert report["completion_report"]["did_build_agent_blueprints"] is True


def test_agent_company_has_bounded_public_website_design_studio(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_agent_company_bill_list(
        root=tmp_path,
        goal=(
            "Research competitors and redesign the public website with serious brand, "
            "graphics, motion, evidence-led writing, accessibility and release QA."
        ),
    )

    roles = {role["title"]: role for role in report["roles"]}
    expected = {
        "Website Design Director",
        "Competitor Research Scout",
        "Brand and Design-System Lead",
        "Technical Editorial Writer",
        "Claims and Evidence Editor",
        "Motion Designer",
        "Visual Asset Director",
        "Accessibility and Performance QA",
        "Design Release QA",
    }
    assert expected.issubset(roles)
    assert all(roles[title]["department"] == "public_design" for title in expected)
    assert roles["Design Release QA"]["authority_level"] == "no_deploy_owner_gate_required"
    assert roles["Claims and Evidence Editor"]["authority_level"] == "claims_veto_no_deploy"
    recruited = {
        worker["title"]
        for worker in report["recruitment_engine"]["recruited_workers"]
    }
    assert {
        "Website Design Director",
        "Claims and Evidence Editor",
        "Motion Designer",
        "Accessibility and Performance QA",
        "Design Release QA",
    }.issubset(recruited)


def test_agent_company_online_recruitment_search_uses_agent_core_when_requested(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_repo(tmp_path)

    class FakeAgentCore:
        def web_search(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
            return [{"title": "Official agent docs", "url": "https://example.test/docs", "snippet": query[:60]}]

    fake_module = types.ModuleType("aureon.autonomous.aureon_agent_core")
    fake_module.__dict__["AureonAgentCore"] = FakeAgentCore
    monkeypatch.setitem(sys.modules, "aureon.autonomous.aureon_agent_core", fake_module)

    report = build_agent_company_bill_list(
        root=tmp_path,
        goal="go online search agent roles and recruit workers",
        online=True,
        online_limit=2,
    )
    online = report["recruitment_engine"]["online_skill_searches"]

    assert online["enabled"] is True
    assert online["status"] == "search_complete"
    assert len(online["searches"]) == 2
    assert all(search["result_count"] == 1 for search in online["searches"])
    assert report["summary"]["online_recruitment_search_enabled"] is True
    assert report["summary"]["online_recruitment_search_count"] == 2
    assert report["completion_report"]["did_run_online_skill_search_when_requested"] is True


def test_agent_company_models_prompts_as_client_jobs_and_temp_crews(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_agent_company_bill_list(root=tmp_path, goal="make prompt agency subcontractor flow")

    titles = {role["title"] for role in report["roles"]}
    assert {
        "Client Brief Broker",
        "Skill Headhunter",
        "Subcontractor Crew Builder",
        "Client Acceptance Officer",
        "Workforce Retirement Clerk",
    }.issubset(titles)
    lifecycle_steps = {step["step"] for step in report["prompt_client_job_lifecycle"]}
    assert {
        "client_intake",
        "skill_market_scan",
        "crew_selection",
        "job_delivery",
        "client_acceptance",
        "retire_or_retain",
    }.issubset(lifecycle_steps)
    assert report["subcontractor_retirement_policy"]["retire_means"].startswith("mark temporary role packs inactive")
    assert "delete generated throwaway artifacts" in report["subcontractor_retirement_policy"]["delete_means"]
    assert len(report["labor_market_skill_source_types"]) >= 5


def test_agent_company_builder_preserves_authority_boundaries_and_secret_safety(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_agent_company_bill_list(root=tmp_path)
    raw = json.dumps(report, sort_keys=True)

    assert report["summary"]["existing_gates_preserved"] is True
    boundary_ids = {item["id"] for item in report["authority_boundaries"]}
    assert {
        "live_trading_runtime_gated",
        "credentials_hidden",
        "filing_payment_manual",
        "cleaner_reports_first",
    }.issubset(boundary_ids)
    assert "API_SECRET" not in raw
    assert "BEGIN PRIVATE" not in raw
    assert "Government Gateway" not in raw


def test_agent_company_builder_writes_reports(tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    report = build_and_write_agent_company_bill_list(root=tmp_path, goal="write agent company")

    assert report["write_info"]["all_ok"] is True
    assert (tmp_path / "state/aureon_agent_company_last_run.json").exists()
    assert (tmp_path / "docs/audits/aureon_agent_company_bill_list.json").exists()
    assert (tmp_path / "docs/audits/aureon_agent_company_bill_list.md").exists()
    assert (tmp_path / "frontend/public/aureon_agent_company_bill_list.json").exists()
    public = json.loads((tmp_path / "frontend/public/aureon_agent_company_bill_list.json").read_text(encoding="utf-8"))
    assert public["completion_report"]["self_validation_result"] == "passing"
    assert public["completion_report"]["did_attach_day_to_day_duties"] is True
    assert public["completion_report"]["did_attach_whole_organism_access"] is True
    assert public["completion_report"]["did_attach_agency_prompt_job_model"] is True
    assert public["completion_report"]["did_attach_hire_retire_lifecycle"] is True
    assert public["completion_report"]["did_build_sha256_zlib_memory_phonebook"] is True
    phonebook_path = tmp_path / "state/aureon_agent_company_memory_phonebook.json"
    assert phonebook_path.exists()
    phonebook = json.loads(phonebook_path.read_text(encoding="utf-8"))
    assert phonebook["summary"]["entry_count"] == public["summary"]["role_count"]
    first_entry = phonebook["entries"][0]
    bundle_path = Path(first_entry["bundle_path"])
    assert bundle_path.exists()
    compressed = base64.b64decode(bundle_path.read_text(encoding="ascii"))
    assert hashlib.sha256(compressed).hexdigest() == first_entry["sha256_compressed_payload"]
    raw = zlib.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest() == first_entry["sha256_raw_payload"]
    payload = json.loads(raw.decode("utf-8"))
    assert payload["role_id"] == first_entry["role_id"]
    assert payload["rehydration_contract"]["restore_as"] == "temporary_crew_candidate"


def test_goal_engine_routes_agent_company_builder(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    plan = GoalExecutionEngine().submit_goal(
        "Aureon must create the company of agents org chart, capability bill list, "
        "roles from CEO to cleaner, work orders, and tests."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "agent_company_builder"
    assert plan.steps[0].validation_result["valid"] is True
    evidence = json.loads((tmp_path / "state/aureon_agent_company_last_run.json").read_text(encoding="utf-8"))
    assert evidence["completion_report"]["did_include_ceo_to_cleaner_roles"] is True
    assert evidence["completion_report"]["daily_operating_loop_ready"] is True


def test_goal_engine_marks_agent_company_online_recruitment_requests(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine._decompose_goal(
        "Aureon must create an agent company and go online with internet search capabilities "
        "to recruit roles, skill sets, work orders, and tests."
    )

    assert plan.steps[0].intent == "agent_company_builder"
    assert plan.steps[0].params["online"] is True


def test_coding_organism_journal_includes_agent_company_report(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = submit_coding_prompt(
        "Aureon must create the company of agents org chart, capability bill list, "
        "roles from CEO to cleaner, work orders, and tests.",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
    )

    assert result["summary"]["agent_company_report_created"] is True
    assert result["agent_company_report"]["schema_version"] == SCHEMA_VERSION
    assert result["agent_company_report"]["summary"]["daily_operating_loop_ready"] is True
    stage_ids = {stage["id"] for stage in result["work_journal"]["stages"]}
    assert "agent_company_bill_list" in stage_ids


def test_market_ai_expansion_prompt_routes_to_agent_company_before_work_journal(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    _seed_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = submit_coding_prompt(
        "Aureon coding organism must run a market AI capability expansion client job: "
        "compare OpenAI Codex, Anthropic Claude Code, Gemini/Jules, Microsoft Agent Framework, "
        "GitHub Copilot, Replit, Cursor, and Devin; hire temporary workers; map work orders; "
        "publish proof and client handover.",
        source="test",
        run_tests=False,
        include_desktop=False,
        scope_approved=True,
        scope_answers={
            "goal": "Compare market AI coding-agent capability patterns with Aureon.",
            "deliverables": "Agent-company report, market comparison, worker hires, work orders, proof.",
            "target_system": "Aureon agent company and coding organism reports.",
            "constraints": "Preserve authority boundaries and do not expose secrets.",
            "acceptance": "Agent-company report is created and includes direct market AI systems.",
        },
        root=tmp_path,
    )

    assert result["summary"]["agent_company_report_created"] is True
    assert result["agent_company_report"]["summary"]["market_ai_system_count"] >= 8
    stage_ids = {stage["id"] for stage in result["work_journal"]["stages"]}
    assert "agent_company_bill_list" in stage_ids
