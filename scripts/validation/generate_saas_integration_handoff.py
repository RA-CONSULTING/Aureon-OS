"""Generate Aureon's SaaS integration handoff manifest."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"

DOCS_REPO_SITEMAP = REPO_ROOT / "docs" / "repo_sitemap.json"
DOCS_READINESS = REPO_ROOT / "docs" / "repo_navigation_readiness.json"
DOCS_CAPABILITY_ACCESS_MATRIX = REPO_ROOT / "docs" / "capability_access_matrix.json"
DOCS_SYSTEM_INTEGRATION = REPO_ROOT / "docs" / "system_integration_map.json"
DOCS_SAAS_MANIFEST = REPO_ROOT / "docs" / "saas_integration_manifest.json"
DOCS_SUPABASE_HARDENING = REPO_ROOT / "docs" / "supabase_hardening_manifest.json"
PUBLIC_REPO_SITEMAP = REPO_ROOT / "frontend" / "public" / "aureon_repo_sitemap.json"

DOCS_HANDOFF = REPO_ROOT / "docs" / "saas_integration_handoff.json"
PUBLIC_HANDOFF = REPO_ROOT / "frontend" / "public" / "aureon_saas_integration_handoff.json"


def git_file_count() -> int:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True)
    return len([path for path in result.stdout.split(b"\0") if path])


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def public_assets(public_sitemap: dict) -> list[dict]:
    assets: list[dict] = []
    direct_keys = {
        "repo_sitemap": "Public sitemap and top-level front doors",
        "end_user_access_map": "Task-based capability access routes",
        "capability_access_matrix": "Capability-to-route/system matrix",
        "capability_registry": "Current capability registry",
        "navigation_index": "File-level navigation index",
        "organization_tree": "Directory hierarchy",
        "repo_navigation_readiness": "Navigation/readiness gate rollup",
        "repo_navigation_completion_audit": "Requirement-level completion audit",
        "system_integration_map": "System-to-capability integration map",
        "saas_integration_manifest": "SaaS deploy/env/auth contract",
        "supabase_hardening_manifest": "Supabase hardening and auth review",
    }
    for asset_id, purpose in direct_keys.items():
        path = public_sitemap.get(asset_id)
        if path:
            assets.append({"id": asset_id, "path": path, "purpose": purpose})

    for path in public_sitemap.get("autonomous_frontend_manifests", []):
        assets.append(
            {
                "id": Path(path).stem,
                "path": path,
                "purpose": "Autonomous frontend operational manifest",
            }
        )
    return assets


def env_group_counts(saas_manifest: dict) -> dict[str, int]:
    return {
        group: len(names)
        for group, names in saas_manifest.get("environment", {}).get("groups", {}).items()
    }


def integration_steps(public_asset_count: int) -> list[dict]:
    return [
        {
            "id": "mount_frontend",
            "label": "Mount the browser console",
            "action": "Serve the React/Vite frontend and keep the #repo-map route available.",
            "evidence": ["frontend/", "frontend/src/components/RepoNavigationPanel.tsx"],
            "gate": "npm run build and browser smoke test must pass before external deployment.",
        },
        {
            "id": "publish_public_manifests",
            "label": "Publish public navigation manifests",
            "action": f"Expose the {public_asset_count} public manifest assets from frontend/public without requiring repo traversal.",
            "evidence": ["frontend/public/", "docs/repo_navigation_readiness.json"],
            "gate": "Public manifests must remain secret-free and mirror docs contracts.",
        },
        {
            "id": "configure_environment_names",
            "label": "Configure environment variables",
            "action": "Create target-platform variables from the manifest names and store values only in the platform secret store.",
            "evidence": ["docs/saas_integration_manifest.json", ".env.example", "deploy/env.example", "app.yaml"],
            "gate": "Do not commit real environment values.",
        },
        {
            "id": "connect_supabase",
            "label": "Connect Supabase auth, functions, and migrations",
            "action": "Use the Supabase config, migrations, and hardening manifest to wire the hosted data plane.",
            "evidence": ["supabase/config.toml", "supabase/functions/", "supabase/migrations/", "docs/supabase_hardening_manifest.json"],
            "gate": "Production blockers must remain zero; advisory routes need explicit review before hosted launch.",
        },
        {
            "id": "bind_runtime_boundary",
            "label": "Bind the operator-controlled runtime boundary",
            "action": "Keep live trading, filing, payment, warehouse mutation, and desktop routes behind operator approval.",
            "evidence": ["RUNNING.md", "docs/END_USER_ACCESS_MAP.md", "docs/system_integration_map.json"],
            "gate": "Sensitive mutation routes require credentials, dry-run/live mode checks, and operator approval.",
        },
        {
            "id": "verify_release",
            "label": "Verify the release contract",
            "action": "Run navigation validation, frontend build, and deployment smoke checks before publishing.",
            "evidence": ["scripts/validation/validate_repo_navigation_contract.py", "docs/repo_navigation_readiness.json"],
            "gate": "Readiness status must be pass with zero failed gates.",
        },
    ]


def build_manifest() -> dict:
    repo_sitemap = load_json(DOCS_REPO_SITEMAP)
    public_sitemap = load_json(PUBLIC_REPO_SITEMAP)
    readiness = load_json(DOCS_READINESS)
    capability_matrix = load_json(DOCS_CAPABILITY_ACCESS_MATRIX)
    system_map = load_json(DOCS_SYSTEM_INTEGRATION)
    saas_manifest = load_json(DOCS_SAAS_MANIFEST)
    hardening = load_json(DOCS_SUPABASE_HARDENING)

    assets = public_assets(public_sitemap)
    steps = integration_steps(len(assets))
    readiness_summary = readiness.get("summary", {})
    hardening_summary = hardening.get("summary", {})
    advisory_count = hardening_summary.get("public_medium_risk_count", 0) + hardening_summary.get("jwt_review_required_count", 0)
    failed_gate_count = readiness_summary.get("failed_gate_count", 0)
    production_blocker_count = hardening_summary.get("production_blocker_count", 0)
    if failed_gate_count or production_blocker_count:
        handoff_status = "blocked"
    elif advisory_count:
        handoff_status = "ready_with_advisory_review"
    else:
        handoff_status = "ready"

    return {
        "name": "Aureon SaaS Integration Handoff",
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_saas_integration_handoff.py",
        "docs_mirror": "docs/saas_integration_handoff.json",
        "frontend_public_mirror": "frontend/public/aureon_saas_integration_handoff.json",
        "source_documents": [
            "docs/repo_sitemap.json",
            "docs/repo_navigation_readiness.json",
            "docs/capability_access_matrix.json",
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
            "handoff_status": handoff_status,
            "readiness_status": readiness_summary.get("readiness_status"),
            "tracked_file_count": git_file_count(),
            "public_manifest_count": len(assets),
            "integration_step_count": len(steps),
            "deployment_surface_count": len(saas_manifest.get("deployment_surfaces", [])),
            "environment_variable_name_count": saas_manifest.get("environment", {}).get("variable_count"),
            "environment_sensitive_name_count": saas_manifest.get("environment", {}).get("sensitive_variable_count"),
            "current_capability_count": capability_matrix.get("summary", {}).get("capability_count"),
            "routed_capability_count": capability_matrix.get("summary", {}).get("routed_capability_count"),
            "system_mapped_capability_count": system_map.get("summary", {}).get("mapped_capability_count"),
            "unmapped_capability_count": system_map.get("summary", {}).get("unmapped_capability_count"),
            "supabase_function_count": hardening_summary.get("function_count"),
            "supabase_verify_jwt_true": hardening_summary.get("verify_jwt_true"),
            "supabase_verify_jwt_false": hardening_summary.get("verify_jwt_false"),
            "supabase_production_blocker_count": production_blocker_count,
            "supabase_public_medium_risk_count": hardening_summary.get("public_medium_risk_count"),
            "supabase_jwt_review_required_count": hardening_summary.get("jwt_review_required_count"),
            "advisory_review_item_count": advisory_count,
        },
        "canonical_shape": saas_manifest.get("canonical_shape"),
        "public_assets": assets,
        "deployment_surfaces": saas_manifest.get("deployment_surfaces", []),
        "environment": {
            "source_files": saas_manifest.get("environment", {}).get("source_files", []),
            "variable_group_counts": env_group_counts(saas_manifest),
            "variables_by_group": {
                group: sorted(names)
                for group, names in saas_manifest.get("environment", {}).get("groups", {}).items()
            },
            "values_policy": "names only; values stay in platform secret stores and never in this manifest",
        },
        "auth_and_hardening": {
            "production_status": hardening.get("production_status"),
            "summary": hardening_summary,
            "public_medium_risk_routes": hardening.get("public_medium_risk_routes", []),
            "jwt_review_required_routes": hardening.get("jwt_review_required_routes", []),
            "production_gates": hardening.get("production_gates", []),
        },
        "navigation_contract": {
            "readiness_summary": readiness_summary,
            "capability_matrix_summary": capability_matrix.get("summary", {}),
            "system_integration_summary": system_map.get("summary", {}),
            "repo_sitemap": repo_sitemap.get("docs_mirror", "docs/repo_sitemap.json"),
            "frontend_navigation_tab": "#repo-map",
        },
        "integration_steps": steps,
        "remaining_advisories": [
            gate
            for gate in readiness.get("gates", [])
            if isinstance(gate, dict) and gate.get("status") == "warn"
        ],
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    manifest = build_manifest()
    write_json(DOCS_HANDOFF, manifest)
    write_json(PUBLIC_HANDOFF, manifest)
    print(f"Wrote {DOCS_HANDOFF.relative_to(REPO_ROOT)}")
    print(f"Wrote {PUBLIC_HANDOFF.relative_to(REPO_ROOT)}")
    print(
        "Handoff "
        f"{manifest['summary']['handoff_status']} with "
        f"{manifest['summary']['advisory_review_item_count']} advisory review items"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
