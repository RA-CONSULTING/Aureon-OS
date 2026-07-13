"""Generate Aureon's repo navigation completion audit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"

DOCS_AUDIT = REPO_ROOT / "docs" / "repo_navigation_completion_audit.json"
PUBLIC_AUDIT = REPO_ROOT / "frontend" / "public" / "aureon_repo_navigation_completion_audit.json"

DOCS_REPO_SITEMAP = REPO_ROOT / "docs" / "repo_sitemap.json"
PUBLIC_REPO_SITEMAP = REPO_ROOT / "frontend" / "public" / "aureon_repo_sitemap.json"
DOCS_NAVIGATION_INDEX = REPO_ROOT / "docs" / "repo_navigation_index.json"
DOCS_ORGANIZATION_TREE = REPO_ROOT / "docs" / "repo_organization_tree.json"
DOCS_ACCESS_MAP = REPO_ROOT / "docs" / "end_user_access_map.json"
DOCS_CAPABILITY_ACCESS_MATRIX = REPO_ROOT / "docs" / "capability_access_matrix.json"
DOCS_CAPABILITY_REGISTRY = REPO_ROOT / "docs" / "capability_registry.json"
DOCS_SYSTEM_INTEGRATION = REPO_ROOT / "docs" / "system_integration_map.json"
DOCS_READINESS = REPO_ROOT / "docs" / "repo_navigation_readiness.json"
DOCS_SAAS_MANIFEST = REPO_ROOT / "docs" / "saas_integration_manifest.json"
DOCS_HANDOFF = REPO_ROOT / "docs" / "saas_integration_handoff.json"
DOCS_HARDENING = REPO_ROOT / "docs" / "supabase_hardening_manifest.json"


def git_file_count() -> int:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True)
    return len([path for path in result.stdout.split(b"\0") if path])


def git_directory_count() -> int:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True)
    directories: set[str] = set()
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        parts = raw_path.decode("utf-8", errors="replace").split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]) + "/")
    return len(directories)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evidence_item(
    requirement_id: str,
    label: str,
    passed: bool,
    actual: object,
    expected: object,
    evidence: list[str],
) -> dict:
    return {
        "id": requirement_id,
        "label": label,
        "status": "complete" if passed else "incomplete",
        "actual": actual,
        "expected": expected,
        "evidence": evidence,
    }


def build_audit() -> dict:
    tracked_total = git_file_count()
    directory_total = git_directory_count()

    repo_sitemap = load_json(DOCS_REPO_SITEMAP)
    public_sitemap = load_json(PUBLIC_REPO_SITEMAP)
    navigation_index = load_json(DOCS_NAVIGATION_INDEX)
    organization_tree = load_json(DOCS_ORGANIZATION_TREE)
    access_map = load_json(DOCS_ACCESS_MAP)
    capability_matrix = load_json(DOCS_CAPABILITY_ACCESS_MATRIX)
    capability_registry = load_json(DOCS_CAPABILITY_REGISTRY)
    system_map = load_json(DOCS_SYSTEM_INTEGRATION)
    readiness = load_json(DOCS_READINESS)
    saas_manifest = load_json(DOCS_SAAS_MANIFEST)
    handoff = load_json(DOCS_HANDOFF)
    hardening = load_json(DOCS_HARDENING)

    matrix_summary = capability_matrix.get("summary", {})
    registry_summary = capability_registry.get("summary", {})
    system_summary = system_map.get("summary", {})
    readiness_summary = readiness.get("summary", {})
    handoff_summary = handoff.get("summary", {})
    hardening_summary = hardening.get("summary", {})
    saas_environment = saas_manifest.get("environment", {})

    current_capability_count = registry_summary.get("capability_count", 0)
    public_asset_count = len(handoff.get("public_assets", []))

    requirements = [
        evidence_item(
            "full_repo_file_navigation",
            "Every tracked repo file is represented in the navigation index",
            navigation_index.get("entry_count") == tracked_total
            and navigation_index.get("tracked_file_count") == tracked_total,
            {
                "entry_count": navigation_index.get("entry_count"),
                "tracked_file_count": navigation_index.get("tracked_file_count"),
                "git_ls_files_count": tracked_total,
            },
            {"entry_count": tracked_total, "tracked_file_count": tracked_total},
            ["docs/repo_navigation_index.json", "frontend/public/aureon_repo_navigation_index.json", "git ls-files"],
        ),
        evidence_item(
            "organizational_structure",
            "Tracked directories are categorized into an organization tree",
            organization_tree.get("directory_count") == directory_total
            and organization_tree.get("summary", {}).get("top_level_directory_count", 0) > 0,
            {
                "directory_count": organization_tree.get("directory_count"),
                "git_directory_count": directory_total,
                "top_level_directory_count": organization_tree.get("summary", {}).get("top_level_directory_count"),
                "max_depth": organization_tree.get("max_depth"),
            },
            {"directory_count": directory_total},
            ["docs/repo_organization_tree.json", "frontend/public/aureon_repo_organization_tree.json", "git ls-files"],
        ),
        evidence_item(
            "all_current_capabilities_accessible",
            "Every current capability is routed to end-user start points and safety gates",
            matrix_summary.get("capability_count") == current_capability_count
            and matrix_summary.get("routed_capability_count") == current_capability_count
            and matrix_summary.get("unresolved_capability_count") == 0,
            matrix_summary,
            {
                "capability_count": current_capability_count,
                "routed_capability_count": current_capability_count,
                "unresolved_capability_count": 0,
            },
            ["CAPABILITIES.md", "docs/capability_registry.json", "docs/capability_access_matrix.json"],
        ),
        evidence_item(
            "related_systems_mapped",
            "All current capabilities are bound to related systems",
            system_summary.get("mapped_capability_count") == current_capability_count
            and system_summary.get("unmapped_capability_count") == 0
            and system_summary.get("system_count", 0) > 0,
            system_summary,
            {
                "mapped_capability_count": current_capability_count,
                "unmapped_capability_count": 0,
            },
            ["docs/system_integration_map.json", "frontend/public/aureon_system_integration_map.json"],
        ),
        evidence_item(
            "end_user_surface_available",
            "End users can browse the public repo map and access contracts without repo traversal",
            public_asset_count >= 14
            and public_sitemap.get("frontend_navigation_tab") == "#repo-map"
            and len(access_map.get("capabilities", [])) == readiness_summary.get("access_route_count"),
            {
                "frontend_navigation_tab": public_sitemap.get("frontend_navigation_tab"),
                "public_manifest_count": public_asset_count,
                "access_route_count": len(access_map.get("capabilities", [])),
            },
            {"frontend_navigation_tab": "#repo-map", "public_manifest_count": ">=14"},
            [
                "frontend/src/components/RepoNavigationPanel.tsx",
                "frontend/public/aureon_repo_sitemap.json",
                "docs/END_USER_ACCESS_MAP.md",
            ],
        ),
        evidence_item(
            "saas_integration_ready",
            "SaaS deploy surfaces, env names, Supabase auth posture, and handoff steps are documented",
            handoff_summary.get("handoff_status") in {"ready", "ready_with_advisory_review"}
            and handoff_summary.get("deployment_surface_count", 0) >= 7
            and saas_environment.get("variable_count", 0) > 0
            and handoff_summary.get("integration_step_count", 0) >= 6,
            {
                "handoff_status": handoff_summary.get("handoff_status"),
                "deployment_surface_count": handoff_summary.get("deployment_surface_count"),
                "environment_variable_name_count": saas_environment.get("variable_count"),
                "integration_step_count": handoff_summary.get("integration_step_count"),
            },
            {
                "handoff_status": "ready or ready_with_advisory_review",
                "deployment_surface_count": ">=7",
                "integration_step_count": ">=6",
            },
            ["docs/saas_integration_handoff.json", "docs/saas_integration_manifest.json"],
        ),
        evidence_item(
            "production_blockers_cleared",
            "SaaS readiness has no failed navigation gates or Supabase production blockers",
            readiness_summary.get("readiness_status") == "pass"
            and readiness_summary.get("failed_gate_count") == 0
            and hardening_summary.get("production_blocker_count") == 0,
            {
                "readiness_status": readiness_summary.get("readiness_status"),
                "failed_gate_count": readiness_summary.get("failed_gate_count"),
                "supabase_production_blocker_count": hardening_summary.get("production_blocker_count"),
            },
            {"readiness_status": "pass", "failed_gate_count": 0, "supabase_production_blocker_count": 0},
            ["docs/repo_navigation_readiness.json", "docs/supabase_hardening_manifest.json"],
        ),
        evidence_item(
            "public_contract_clean",
            "Public manifests expose paths, labels, and counts without secrets or private runtime data",
            not any(
                bool(handoff.get("public_contract", {}).get(key))
                for key in (
                    "contains_file_contents",
                    "contains_env_values",
                    "contains_secrets",
                    "contains_private_runtime_state",
                    "contains_customer_data",
                )
            ),
            handoff.get("public_contract", {}),
            {
                "contains_file_contents": False,
                "contains_env_values": False,
                "contains_secrets": False,
                "contains_private_runtime_state": False,
                "contains_customer_data": False,
            },
            ["docs/saas_integration_handoff.json", "scripts/validation/validate_repo_navigation_contract.py"],
        ),
    ]

    incomplete = [item for item in requirements if item["status"] != "complete"]
    completion_status = "complete" if not incomplete else "incomplete"
    return {
        "name": "Aureon Repo Navigation Completion Audit",
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_repo_navigation_completion_audit.py",
        "docs_mirror": "docs/repo_navigation_completion_audit.json",
        "frontend_public_mirror": "frontend/public/aureon_repo_navigation_completion_audit.json",
        "objective": "Full repo-wide sitemap and organizational structure for navigating the entire repo, all capabilities, related systems, and SaaS integration readiness.",
        "public_contract": {
            "contains_file_contents": False,
            "contains_env_values": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "completion_status": completion_status,
            "requirement_count": len(requirements),
            "complete_requirement_count": len(requirements) - len(incomplete),
            "incomplete_requirement_count": len(incomplete),
            "tracked_file_count": tracked_total,
            "directory_count": organization_tree.get("directory_count"),
            "current_capability_count": current_capability_count,
            "routed_capability_count": matrix_summary.get("routed_capability_count"),
            "system_mapped_capability_count": system_summary.get("mapped_capability_count"),
            "unmapped_capability_count": system_summary.get("unmapped_capability_count"),
            "public_manifest_count": public_asset_count,
            "readiness_status": readiness_summary.get("readiness_status"),
            "supabase_production_blocker_count": hardening_summary.get("production_blocker_count"),
            "handoff_status": handoff_summary.get("handoff_status"),
        },
        "source_documents": [
            "docs/repo_sitemap.json",
            "docs/repo_navigation_index.json",
            "docs/repo_organization_tree.json",
            "docs/end_user_access_map.json",
            "docs/capability_access_matrix.json",
            "docs/capability_registry.json",
            "docs/system_integration_map.json",
            "docs/repo_navigation_readiness.json",
            "docs/saas_integration_manifest.json",
            "docs/saas_integration_handoff.json",
            "docs/supabase_hardening_manifest.json",
        ],
        "requirements": requirements,
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    audit = build_audit()
    write_json(DOCS_AUDIT, audit)
    write_json(PUBLIC_AUDIT, audit)
    print(f"Wrote {DOCS_AUDIT.relative_to(REPO_ROOT)}")
    print(f"Wrote {PUBLIC_AUDIT.relative_to(REPO_ROOT)}")
    print(
        "Completion audit "
        f"{audit['summary']['completion_status']} "
        f"({audit['summary']['complete_requirement_count']}/"
        f"{audit['summary']['requirement_count']} requirements)"
    )
    return 0 if audit["summary"]["completion_status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
