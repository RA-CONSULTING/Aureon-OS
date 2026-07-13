"""Generate Aureon's repo navigation and SaaS-readiness audit manifest."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"

DOCS_REPO_SITEMAP = REPO_ROOT / "docs" / "repo_sitemap.json"
DOCS_ACCESS_MAP = REPO_ROOT / "docs" / "end_user_access_map.json"
DOCS_CAPABILITY_ACCESS_MATRIX = REPO_ROOT / "docs" / "capability_access_matrix.json"
DOCS_CAPABILITY_REGISTRY = REPO_ROOT / "docs" / "capability_registry.json"
DOCS_NAVIGATION_INDEX = REPO_ROOT / "docs" / "repo_navigation_index.json"
DOCS_ORGANIZATION_TREE = REPO_ROOT / "docs" / "repo_organization_tree.json"
DOCS_SYSTEM_INTEGRATION = REPO_ROOT / "docs" / "system_integration_map.json"
DOCS_SAAS_MANIFEST = REPO_ROOT / "docs" / "saas_integration_manifest.json"
DOCS_SUPABASE_HARDENING = REPO_ROOT / "docs" / "supabase_hardening_manifest.json"
DOCS_READINESS = REPO_ROOT / "docs" / "repo_navigation_readiness.json"

PUBLIC_REPO_SITEMAP = REPO_ROOT / "frontend" / "public" / "aureon_repo_sitemap.json"
PUBLIC_ACCESS_MAP = REPO_ROOT / "frontend" / "public" / "aureon_end_user_access_map.json"
PUBLIC_CAPABILITY_ACCESS_MATRIX = REPO_ROOT / "frontend" / "public" / "aureon_capability_access_matrix.json"
PUBLIC_CAPABILITY_REGISTRY = REPO_ROOT / "frontend" / "public" / "aureon_capability_registry.json"
PUBLIC_NAVIGATION_INDEX = REPO_ROOT / "frontend" / "public" / "aureon_repo_navigation_index.json"
PUBLIC_ORGANIZATION_TREE = REPO_ROOT / "frontend" / "public" / "aureon_repo_organization_tree.json"
PUBLIC_SYSTEM_INTEGRATION = REPO_ROOT / "frontend" / "public" / "aureon_system_integration_map.json"
PUBLIC_SAAS_MANIFEST = REPO_ROOT / "frontend" / "public" / "aureon_saas_integration_manifest.json"
PUBLIC_SUPABASE_HARDENING = REPO_ROOT / "frontend" / "public" / "aureon_supabase_hardening_manifest.json"
PUBLIC_READINESS = REPO_ROOT / "frontend" / "public" / "aureon_repo_navigation_readiness.json"

MIRROR_PAIRS = [
    (DOCS_ACCESS_MAP, PUBLIC_ACCESS_MAP, "end_user_access_map"),
    (DOCS_CAPABILITY_ACCESS_MATRIX, PUBLIC_CAPABILITY_ACCESS_MATRIX, "capability_access_matrix"),
    (DOCS_CAPABILITY_REGISTRY, PUBLIC_CAPABILITY_REGISTRY, "capability_registry"),
    (DOCS_NAVIGATION_INDEX, PUBLIC_NAVIGATION_INDEX, "repo_navigation_index"),
    (DOCS_ORGANIZATION_TREE, PUBLIC_ORGANIZATION_TREE, "repo_organization_tree"),
    (DOCS_SYSTEM_INTEGRATION, PUBLIC_SYSTEM_INTEGRATION, "system_integration_map"),
    (DOCS_SAAS_MANIFEST, PUBLIC_SAAS_MANIFEST, "saas_integration_manifest"),
    (DOCS_SUPABASE_HARDENING, PUBLIC_SUPABASE_HARDENING, "supabase_hardening_manifest"),
]


def run_git(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def git_file_count() -> int:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True)
    return len([path for path in result.stdout.split(b"\0") if path])


def git_directory_count() -> int:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True)
    directories: set[str] = set()
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8", errors="replace")
        parts = path.split("/")[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]) + "/")
    return len(directories)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_capabilities_table_count() -> int:
    source = REPO_ROOT / "CAPABILITIES.md"
    markdown = source.read_text(encoding="utf-8")
    start = markdown.find("## Capability Table")
    if start == -1:
        return 0
    end = markdown.find("\n## ", start + len("## Capability Table"))
    section = markdown[start:] if end == -1 else markdown[start:end]
    count = 0
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("|") and not line.startswith("|---") and not line.startswith("| Capability "):
            count += 1
    return count


def gate(gates: list[dict], gate_id: str, label: str, passed: bool, actual: object, expected: object, evidence: list[str], severity: str = "critical") -> None:
    gates.append(
        {
            "id": gate_id,
            "label": label,
            "status": "pass" if passed else "fail",
            "severity": severity,
            "actual": actual,
            "expected": expected,
            "evidence": evidence,
        }
    )


def warning(gates: list[dict], gate_id: str, label: str, actual: object, expected: object, evidence: list[str]) -> None:
    gates.append(
        {
            "id": gate_id,
            "label": label,
            "status": "warn",
            "severity": "advisory",
            "actual": actual,
            "expected": expected,
            "evidence": evidence,
        }
    )


def public_contract_is_clean(manifest: dict) -> bool:
    contract = manifest.get("public_contract", {})
    return not any(
        bool(contract.get(key))
        for key in (
            "contains_file_contents",
            "contains_env_values",
            "contains_secrets",
            "contains_private_runtime_state",
            "contains_customer_data",
        )
    )


def build_manifest() -> dict:
    tracked_total = git_file_count()
    directory_total = git_directory_count()
    capability_table_count = parse_capabilities_table_count()

    repo_sitemap = load_json(DOCS_REPO_SITEMAP)
    public_sitemap = load_json(PUBLIC_REPO_SITEMAP)
    access_map = load_json(DOCS_ACCESS_MAP)
    capability_matrix = load_json(DOCS_CAPABILITY_ACCESS_MATRIX)
    capability_registry = load_json(DOCS_CAPABILITY_REGISTRY)
    navigation_index = load_json(DOCS_NAVIGATION_INDEX)
    organization_tree = load_json(DOCS_ORGANIZATION_TREE)
    system_integration = load_json(DOCS_SYSTEM_INTEGRATION)
    saas_manifest = load_json(DOCS_SAAS_MANIFEST)
    hardening_manifest = load_json(DOCS_SUPABASE_HARDENING)

    registry_rows = capability_registry.get("capabilities", [])
    matrix_rows = capability_matrix.get("capabilities", [])
    system_rows = system_integration.get("systems", [])
    registry_count = len(registry_rows)
    access_route_count = len(access_map.get("capabilities", []))

    gates: list[dict] = []
    gate(
        gates,
        "repo_sitemap_tracked_files",
        "Repo sitemap tracked-file count is current",
        repo_sitemap.get("tracked_file_count") == tracked_total and public_sitemap.get("tracked_file_count") == tracked_total,
        {"docs": repo_sitemap.get("tracked_file_count"), "public": public_sitemap.get("tracked_file_count")},
        tracked_total,
        ["docs/repo_sitemap.json", "frontend/public/aureon_repo_sitemap.json", "git ls-files"],
    )
    gate(
        gates,
        "repo_navigation_index_complete",
        "File-level navigation index covers every tracked file",
        navigation_index.get("entry_count") == tracked_total and navigation_index.get("tracked_file_count") == tracked_total,
        {"entry_count": navigation_index.get("entry_count"), "tracked_file_count": navigation_index.get("tracked_file_count")},
        tracked_total,
        ["docs/repo_navigation_index.json", "git ls-files"],
    )
    gate(
        gates,
        "repo_organization_tree_complete",
        "Directory organization tree covers every tracked directory",
        organization_tree.get("directory_count") == directory_total,
        organization_tree.get("directory_count"),
        directory_total,
        ["docs/repo_organization_tree.json", "git ls-files"],
    )
    gate(
        gates,
        "capability_registry_current",
        "Capability registry matches CAPABILITIES.md",
        registry_count == capability_table_count and capability_registry.get("summary", {}).get("capability_count") == capability_table_count,
        {"registry_rows": registry_count, "summary_count": capability_registry.get("summary", {}).get("capability_count")},
        capability_table_count,
        ["CAPABILITIES.md", "docs/capability_registry.json"],
    )
    gate(
        gates,
        "capability_access_matrix_complete",
        "Every current capability has routes, start points, related systems, and safety gates",
        len(matrix_rows) == registry_count
        and capability_matrix.get("summary", {}).get("routed_capability_count") == registry_count
        and capability_matrix.get("summary", {}).get("system_bound_capability_count") == registry_count
        and capability_matrix.get("summary", {}).get("unresolved_capability_count") == 0,
        capability_matrix.get("summary", {}),
        {
            "capability_count": registry_count,
            "routed_capability_count": registry_count,
            "system_bound_capability_count": registry_count,
            "unresolved_capability_count": 0,
        },
        ["docs/capability_access_matrix.json", "docs/capability_registry.json"],
    )
    gate(
        gates,
        "system_integration_complete",
        "Every current capability is mapped to at least one related system",
        system_integration.get("summary", {}).get("mapped_capability_count") == registry_count
        and system_integration.get("summary", {}).get("unmapped_capability_count") == 0
        and not system_integration.get("unmapped_capability_ids"),
        system_integration.get("summary", {}),
        {"mapped_capability_count": registry_count, "unmapped_capability_count": 0},
        ["docs/system_integration_map.json", "docs/capability_registry.json"],
    )
    gate(
        gates,
        "access_routes_available",
        "End-user access routes are available and mirrored",
        access_route_count > 0 and repo_sitemap.get("end_user_access", {}).get("capability_count") == access_route_count,
        {"access_route_count": access_route_count, "sitemap_capability_count": repo_sitemap.get("end_user_access", {}).get("capability_count")},
        access_route_count,
        ["docs/end_user_access_map.json", "docs/repo_sitemap.json"],
    )
    gate(
        gates,
        "saas_manifest_available",
        "SaaS integration manifest exposes deploy surfaces and env names without values",
        saas_manifest.get("environment", {}).get("variable_count", 0) > 0
        and len(saas_manifest.get("deployment_surfaces", [])) > 0
        and public_contract_is_clean(saas_manifest),
        {
            "variable_count": saas_manifest.get("environment", {}).get("variable_count"),
            "deployment_surface_count": len(saas_manifest.get("deployment_surfaces", [])),
            "public_contract_clean": public_contract_is_clean(saas_manifest),
        },
        {"variable_count": ">0", "deployment_surface_count": ">0", "public_contract_clean": True},
        ["docs/saas_integration_manifest.json"],
    )
    gate(
        gates,
        "supabase_hardening_no_blockers",
        "Supabase hardening manifest has no production blockers",
        hardening_manifest.get("summary", {}).get("production_blocker_count") == 0,
        hardening_manifest.get("summary", {}).get("production_blocker_count"),
        0,
        ["docs/supabase_hardening_manifest.json", "supabase/config.toml"],
    )
    gate(
        gates,
        "public_contracts_clean",
        "Public navigation manifests do not claim to contain secrets or private runtime data",
        all(public_contract_is_clean(load_json(path)) for path in [
            DOCS_CAPABILITY_ACCESS_MATRIX,
            DOCS_CAPABILITY_REGISTRY,
            DOCS_NAVIGATION_INDEX,
            DOCS_ORGANIZATION_TREE,
            DOCS_SYSTEM_INTEGRATION,
            DOCS_SAAS_MANIFEST,
            DOCS_SUPABASE_HARDENING,
        ]),
        True,
        True,
        [
            "docs/capability_access_matrix.json",
            "docs/capability_registry.json",
            "docs/repo_navigation_index.json",
            "docs/repo_organization_tree.json",
            "docs/system_integration_map.json",
            "docs/saas_integration_manifest.json",
            "docs/supabase_hardening_manifest.json",
        ],
    )

    for docs_path, public_path, label in MIRROR_PAIRS:
        gate(
            gates,
            f"{label}_mirror_match",
            f"{label} docs/public mirrors match",
            load_json(docs_path) == load_json(public_path),
            True,
            True,
            [str(docs_path.relative_to(REPO_ROOT)), str(public_path.relative_to(REPO_ROOT))],
        )

    public_medium = hardening_manifest.get("summary", {}).get("public_medium_risk_count", 0)
    jwt_review = hardening_manifest.get("summary", {}).get("jwt_review_required_count", 0)
    if public_medium or jwt_review:
        warning(
            gates,
            "supabase_public_review_queue",
            "Supabase public/JWT review queue remains for production hardening",
            {"public_medium_risk_count": public_medium, "jwt_review_required_count": jwt_review},
            {"public_medium_risk_count": 0, "jwt_review_required_count": 0},
            ["docs/supabase_hardening_manifest.json"],
        )

    failed_critical = [item for item in gates if item["status"] == "fail" and item["severity"] == "critical"]
    failed = [item for item in gates if item["status"] == "fail"]
    warnings = [item for item in gates if item["status"] == "warn"]
    passed = [item for item in gates if item["status"] == "pass"]

    readiness_status = "pass" if not failed_critical else "fail"

    return {
        "name": "Aureon Repo Navigation Readiness Audit",
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_repo_navigation_readiness.py",
        "docs_mirror": "docs/repo_navigation_readiness.json",
        "frontend_public_mirror": "frontend/public/aureon_repo_navigation_readiness.json",
        "source_documents": [
            "docs/repo_sitemap.json",
            "docs/end_user_access_map.json",
            "docs/capability_access_matrix.json",
            "docs/capability_registry.json",
            "docs/repo_navigation_index.json",
            "docs/repo_organization_tree.json",
            "docs/system_integration_map.json",
            "docs/saas_integration_manifest.json",
            "docs/supabase_hardening_manifest.json",
        ],
        "public_contract": {
            "contains_file_contents": False,
            "contains_env_values": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "readiness_status": readiness_status,
            "tracked_file_count": tracked_total,
            "directory_count": directory_total,
            "top_level_system_count": len(system_rows),
            "access_route_count": access_route_count,
            "current_capability_count": registry_count,
            "routed_capability_count": capability_matrix.get("summary", {}).get("routed_capability_count"),
            "system_mapped_capability_count": system_integration.get("summary", {}).get("mapped_capability_count"),
            "unmapped_capability_count": system_integration.get("summary", {}).get("unmapped_capability_count"),
            "saas_deployment_surface_count": len(saas_manifest.get("deployment_surfaces", [])),
            "supabase_production_blocker_count": hardening_manifest.get("summary", {}).get("production_blocker_count"),
            "gate_count": len(gates),
            "passed_gate_count": len(passed),
            "failed_gate_count": len(failed),
            "warning_gate_count": len(warnings),
        },
        "coverage": {
            "repo_structure": {
                "tracked_file_count": tracked_total,
                "navigation_index_entries": navigation_index.get("entry_count"),
                "directory_count": directory_total,
                "organization_tree_directories": organization_tree.get("directory_count"),
            },
            "capabilities": {
                "current_capability_count": registry_count,
                "routed_capability_count": capability_matrix.get("summary", {}).get("routed_capability_count"),
                "system_bound_capability_count": capability_matrix.get("summary", {}).get("system_bound_capability_count"),
                "system_mapped_capability_count": system_integration.get("summary", {}).get("mapped_capability_count"),
                "unmapped_capability_ids": system_integration.get("unmapped_capability_ids", []),
            },
            "saas": {
                "deployment_surface_count": len(saas_manifest.get("deployment_surfaces", [])),
                "environment_variable_name_count": saas_manifest.get("environment", {}).get("variable_count"),
                "supabase_function_count": hardening_manifest.get("summary", {}).get("function_count"),
                "supabase_production_blocker_count": hardening_manifest.get("summary", {}).get("production_blocker_count"),
            },
        },
        "gates": gates,
        "frontend_navigation_tab": "#repo-map",
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    manifest = build_manifest()
    write_json(DOCS_READINESS, manifest)
    write_json(PUBLIC_READINESS, manifest)
    print(f"Wrote {DOCS_READINESS.relative_to(REPO_ROOT)}")
    print(f"Wrote {PUBLIC_READINESS.relative_to(REPO_ROOT)}")
    print(
        "Readiness "
        f"{manifest['summary']['readiness_status']} with "
        f"{manifest['summary']['failed_gate_count']} failed gates and "
        f"{manifest['summary']['warning_gate_count']} warnings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
