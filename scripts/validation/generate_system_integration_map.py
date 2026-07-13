"""Generate Aureon's repo-wide system integration map."""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"
DOCS_REPO_SITEMAP = REPO_ROOT / "docs" / "repo_sitemap.json"
DOCS_ACCESS_MAP = REPO_ROOT / "docs" / "end_user_access_map.json"
DOCS_CAPABILITY_REGISTRY = REPO_ROOT / "docs" / "capability_registry.json"
DOCS_NAVIGATION_INDEX = REPO_ROOT / "docs" / "repo_navigation_index.json"
DOCS_SAAS_MANIFEST = REPO_ROOT / "docs" / "saas_integration_manifest.json"
DOCS_HARDENING_MANIFEST = REPO_ROOT / "docs" / "supabase_hardening_manifest.json"
DOCS_MANIFEST = REPO_ROOT / "docs" / "system_integration_map.json"
PUBLIC_MANIFEST = REPO_ROOT / "frontend" / "public" / "aureon_system_integration_map.json"

PUBLIC_ARTIFACT_PREFIXES = ("frontend/public/", "public/")
VALIDATION_PREFIXES = ("tests/", "scripts/validation/", "VERIFICATION AND VALIDATION/")
ENTRYPOINT_KINDS = {
    "markdown",
    "json",
    "config",
    "python",
    "typescript",
    "typescript-react",
    "javascript",
    "javascript-react",
    "windows-command",
    "powershell",
    "shell",
    "sql",
}


SYSTEM_OVERRIDES = {
    ".github/": {
        "integration_role": "repository automation and CI metadata",
        "safety_gate": "keep repository automation scoped and review dependency/security alerts",
        "access_mode": "GitHub repository metadata",
    },
    "api/": {
        "integration_role": "hosted API route surface",
        "safety_gate": "confirm auth, CORS, and payload validation before public exposure",
        "access_mode": "hosted/serverless API",
    },
    "aureon/": {
        "integration_role": "core local runtime and domain automation package",
        "safety_gate": "live mutation routes require operator review, credentials, and dry-run/live gates",
        "access_mode": "local runtime and internal package",
    },
    "data/": {
        "integration_role": "evidence, research, grant, and dataset store",
        "safety_gate": "redact private evidence before public disclosure",
        "access_mode": "public-safe evidence or controlled local files",
    },
    "docs/": {
        "integration_role": "primary reading, diligence, runbook, and generated-map system",
        "safety_gate": "keep claims evidence-backed and generated maps current",
        "access_mode": "public documentation",
    },
    "frontend/": {
        "integration_role": "React/Vite user console and public manifest surface",
        "safety_gate": "build and render-check public manifests before publishing",
        "access_mode": "browser application",
    },
    "Kings_Accounting_Suite/": {
        "integration_role": "accounting, filing-support, and statutory-pack tooling",
        "safety_gate": "filing and payment stay manual unless separately authorized",
        "access_mode": "local operator workflow",
    },
    "scripts/": {
        "integration_role": "operator diagnostics, reports, launch helpers, and validators",
        "safety_gate": "run focused validation before relying on generated artifacts",
        "access_mode": "local maintainer tooling",
    },
    "supabase/": {
        "integration_role": "SaaS backend, Edge Functions, auth settings, and migrations",
        "safety_gate": "resolve public Edge Function hardening blockers before hosted production",
        "access_mode": "hosted Supabase backend",
    },
    "tests/": {
        "integration_role": "regression, contract, and behavior verification",
        "safety_gate": "checks must cover the claimed capability or integration surface",
        "access_mode": "local or CI validation",
    },
}


def git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_path(path: str) -> str:
    return path if path.endswith("/") else f"{path}/"


def path_matches(path: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/")
    return path == normalized or path.startswith(f"{normalized}/")


def capability_lookup(access_map: dict) -> dict[str, set[str]]:
    lookup: dict[str, set[str]] = defaultdict(set)
    for capability in access_map.get("capabilities", []):
        capability_id = str(capability.get("id", ""))
        for field in ("primary_docs", "related_systems", "runtime_or_api_surface"):
            for target in capability.get(field, []):
                if not isinstance(target, str) or target.startswith(("http://", "https://", "#", "/")):
                    continue
                lookup[target].add(capability_id)
    return lookup


def top_level_system_for_path(path: str, system_paths: set[str]) -> str | None:
    normalized = path.strip().lstrip("/")
    if not normalized or normalized.startswith(("http://", "https://", "#")):
        return None
    if normalized.endswith("/") and normalized in system_paths:
        return normalized
    if "/" not in normalized:
        return None
    top_level = normalized.split("/", 1)[0] + "/"
    return top_level if top_level in system_paths else None


def capability_system_lookup(capability_registry: dict, access_map: dict, system_paths: set[str]) -> dict[str, set[str]]:
    lookup: dict[str, set[str]] = defaultdict(set)
    routes_by_id = {
        route["id"]: route
        for route in access_map.get("capabilities", [])
        if isinstance(route, dict) and route.get("id")
    }

    for capability in capability_registry.get("capabilities", []):
        if not isinstance(capability, dict) or not capability.get("id"):
            continue
        capability_id = str(capability["id"])
        candidate_paths: list[str] = []
        candidate_paths.extend(capability.get("system_paths", []))
        candidate_paths.extend(capability.get("resolved_paths", []))
        candidate_paths.extend(capability.get("generated_refs", []))
        candidate_paths.extend(capability.get("public_artifacts", []))
        for route_id in capability.get("access_route_ids", []):
            route = routes_by_id.get(route_id)
            if not route:
                continue
            candidate_paths.extend(route.get("primary_docs", []))
            candidate_paths.extend(route.get("related_systems", []))

        for candidate in candidate_paths:
            if not isinstance(candidate, str):
                continue
            system_path = top_level_system_for_path(candidate, system_paths)
            if system_path:
                lookup[system_path].add(capability_id)

    return lookup


def access_routes_for_system(system_path: str, lookup: dict[str, set[str]], entries: list[dict]) -> list[str]:
    ids: set[str] = set()
    for prefix, capability_ids in lookup.items():
        if path_matches(prefix, system_path) or path_matches(system_path, prefix):
            ids.update(capability_ids)
    for entry in entries:
        if path_matches(entry.get("path", ""), system_path):
            ids.update(entry.get("capability_ids", []))
    return sorted(ids)


def pick_entrypoints(system_path: str, entries: list[dict]) -> list[str]:
    candidates: list[str] = []
    for entry in entries:
        path = entry.get("path", "")
        if not path_matches(path, system_path):
            continue
        if entry.get("kind") in ENTRYPOINT_KINDS:
            name = Path(path).name.lower()
            if name in {"readme.md", "index.md"} or path.count("/") <= 2:
                candidates.append(path)
    return candidates[:12]


def pick_public_artifacts(system_path: str, entries: list[dict]) -> list[str]:
    artifacts = [
        entry.get("path", "")
        for entry in entries
        if path_matches(entry.get("path", ""), system_path)
        and entry.get("path", "").startswith(PUBLIC_ARTIFACT_PREFIXES)
        and entry.get("kind") in {"json", "markdown", "html", "image"}
    ]
    return artifacts[:15]


def pick_validation_refs(system_path: str, entries: list[dict], capability_ids: list[str]) -> list[str]:
    refs: list[str] = []
    for entry in entries:
        path = entry.get("path", "")
        if not path.startswith(VALIDATION_PREFIXES):
            continue
        entry_capabilities = set(entry.get("capability_ids", []))
        if path_matches(path, system_path) or entry_capabilities.intersection(capability_ids):
            refs.append(path)
    return refs[:12]


def readiness_for(system_path: str, category: str) -> str:
    if system_path in {"frontend/", "docs/", "data/", "scripts/", "tests/"}:
        return "mapped_for_end_user_navigation"
    if system_path in {"supabase/", "api/", "server/", "functions/", "netlify/", "deploy/", "production/"}:
        return "integration_ready_with_production_gates"
    if category in {"archive", "provenance"}:
        return "preserved_for_audit_not_current_product_surface"
    if category in {"runtime", "back office"}:
        return "operator_controlled_before_saas_exposure"
    return "mapped_with_review_gate"


def build_manifest() -> dict:
    repo_sitemap = load_json(DOCS_REPO_SITEMAP)
    access_map = load_json(DOCS_ACCESS_MAP)
    capability_registry = load_json(DOCS_CAPABILITY_REGISTRY)
    navigation_index = load_json(DOCS_NAVIGATION_INDEX)
    saas_manifest = load_json(DOCS_SAAS_MANIFEST)
    hardening_manifest = load_json(DOCS_HARDENING_MANIFEST)
    tracked_paths = git_ls_files()
    entries = navigation_index.get("entries", [])
    access_lookup = capability_lookup(access_map)
    system_paths = {normalize_path(system["path"]) for system in repo_sitemap.get("top_level_systems", [])}
    implementation_lookup = capability_system_lookup(capability_registry, access_map, system_paths)

    capability_counts = Counter()
    access_route_counts = Counter()
    systems = []
    for system in repo_sitemap.get("top_level_systems", []):
        system_path = normalize_path(system["path"])
        category = system.get("category", "uncategorized")
        override = SYSTEM_OVERRIDES.get(system_path, {})
        access_route_ids = access_routes_for_system(system_path, access_lookup, entries)
        capability_ids = sorted(implementation_lookup.get(system_path, set()))
        for capability_id in capability_ids:
            capability_counts[capability_id] += 1
        for route_id in access_route_ids:
            access_route_counts[route_id] += 1

        systems.append(
            {
                "path": system_path,
                "category": category,
                "tracked_files": system.get("files", 0),
                "role": system.get("role", ""),
                "integration_role": override.get("integration_role", system.get("role", "")),
                "access_mode": override.get("access_mode", "repo path and generated navigation"),
                "readiness_status": readiness_for(system_path, category),
                "capability_ids": capability_ids,
                "access_route_ids": access_route_ids,
                "entrypoints": pick_entrypoints(system_path, entries),
                "public_artifacts": pick_public_artifacts(system_path, entries),
                "validation_refs": pick_validation_refs(system_path, entries, [*capability_ids, *access_route_ids]),
                "safety_gate": override.get("safety_gate", "review before exposing as a hosted or mutable surface"),
            }
        )

    registry_capability_ids = sorted(
        str(capability.get("id", ""))
        for capability in capability_registry.get("capabilities", [])
        if isinstance(capability, dict) and capability.get("id")
    )
    unmapped_capability_ids = sorted(set(registry_capability_ids) - set(capability_counts))

    return {
        "name": "Aureon System Integration Map",
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_system_integration_map.py",
        "docs_mirror": "docs/system_integration_map.json",
        "frontend_public_mirror": "frontend/public/aureon_system_integration_map.json",
        "source_documents": [
            "docs/repo_sitemap.json",
            "docs/end_user_access_map.json",
            "docs/capability_registry.json",
            "docs/repo_navigation_index.json",
            "docs/saas_integration_manifest.json",
            "docs/supabase_hardening_manifest.json",
        ],
        "public_contract": {
            "contains_file_contents": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "tracked_file_count": len(tracked_paths),
            "system_count": len(systems),
            "capability_count": len(registry_capability_ids),
            "mapped_capability_count": len(capability_counts),
            "unmapped_capability_count": len(unmapped_capability_ids),
            "capability_system_binding_count": sum(capability_counts.values()),
            "access_route_count": len(access_map.get("capabilities", [])),
            "mapped_access_route_count": len(access_route_counts),
            "access_route_system_binding_count": sum(access_route_counts.values()),
            "saas_deployment_surface_count": len(saas_manifest.get("deployment_surfaces", [])),
            "supabase_public_blocker_count": hardening_manifest.get("summary", {}).get("production_blocker_count", 0),
        },
        "systems": systems,
        "capability_system_counts": dict(sorted(capability_counts.items())),
        "access_route_system_counts": dict(sorted(access_route_counts.items())),
        "unmapped_capability_ids": unmapped_capability_ids,
        "integration_sequence": [
            "start with README.md, docs/REPO_SITEMAP.md, and docs/END_USER_ACCESS_MAP.md",
            "use docs/system_integration_map.json to bind systems to capabilities and gates",
            "use docs/repo_navigation_index.json for file-level lookup",
            "use docs/saas_integration_manifest.json for deployment/env/auth surfaces",
            "use docs/supabase_hardening_manifest.json before hosted Supabase production",
            "run scripts/validation/validate_repo_navigation_contract.py before publishing navigation changes",
        ],
        "frontend_navigation_tab": "#repo-map",
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    manifest = build_manifest()
    write_json(DOCS_MANIFEST, manifest)
    write_json(PUBLIC_MANIFEST, manifest)
    print(f"Wrote {DOCS_MANIFEST.relative_to(REPO_ROOT)}")
    print(f"Wrote {PUBLIC_MANIFEST.relative_to(REPO_ROOT)}")
    print(
        "Mapped "
        f"{manifest['summary']['system_count']} systems across "
        f"{manifest['summary']['mapped_capability_count']} capability bindings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
