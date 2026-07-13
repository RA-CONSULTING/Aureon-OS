"""Generate the end-user access matrix for every current Aureon capability."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"
DOCS_ACCESS_MAP = REPO_ROOT / "docs" / "end_user_access_map.json"
DOCS_CAPABILITY_REGISTRY = REPO_ROOT / "docs" / "capability_registry.json"
DOCS_SYSTEM_INTEGRATION = REPO_ROOT / "docs" / "system_integration_map.json"
DOCS_MATRIX = REPO_ROOT / "docs" / "capability_access_matrix.json"
PUBLIC_MATRIX = REPO_ROOT / "frontend" / "public" / "aureon_capability_access_matrix.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def route_lookup(access_map: dict) -> dict[str, dict]:
    return {route["id"]: route for route in access_map.get("capabilities", []) if isinstance(route, dict) and route.get("id")}


def system_lookup(system_map: dict) -> dict[str, dict]:
    return {system["path"]: system for system in system_map.get("systems", []) if isinstance(system, dict) and system.get("path")}


def route_payload(route: dict) -> dict:
    return {
        "id": route.get("id", ""),
        "label": route.get("label", ""),
        "user_action": route.get("user_action", ""),
        "primary_docs": route.get("primary_docs", []),
        "related_systems": route.get("related_systems", []),
        "runtime_or_api_surface": route.get("runtime_or_api_surface", []),
        "safety_gate": route.get("safety_gate", ""),
    }


def system_payload(path: str, system: dict | None) -> dict:
    if not system:
        return {
            "path": path,
            "category": "root" if path == "root/" else "unmapped",
            "readiness_status": "mapped_with_review_gate",
            "access_mode": "repo path and generated navigation",
            "entrypoints": [path.rstrip("/")] if path == "root/" else [],
            "public_artifacts": [],
            "validation_refs": [],
            "safety_gate": "review before exposing as a hosted or mutable surface",
        }
    return {
        "path": system.get("path", path),
        "category": system.get("category", ""),
        "readiness_status": system.get("readiness_status", ""),
        "access_mode": system.get("access_mode", ""),
        "entrypoints": system.get("entrypoints", []),
        "public_artifacts": system.get("public_artifacts", []),
        "validation_refs": system.get("validation_refs", []),
        "safety_gate": system.get("safety_gate", ""),
    }


def readiness_for(capability: dict, routes: list[dict], systems: list[dict]) -> str:
    if capability.get("unresolved_refs"):
        return "needs_surface_review"
    route_ids = {route.get("id") for route in routes}
    if {"trading_readiness", "accounting_filing_support", "coding_skills"}.intersection(route_ids):
        return "operator_controlled_accessible"
    if any(system.get("readiness_status") == "integration_ready_with_production_gates" for system in systems):
        return "integration_ready_with_production_gates"
    if capability.get("public_artifacts"):
        return "public_manifest_accessible"
    return "mapped_for_end_user_navigation"


def build_matrix() -> dict:
    access_map = load_json(DOCS_ACCESS_MAP)
    capability_registry = load_json(DOCS_CAPABILITY_REGISTRY)
    system_map = load_json(DOCS_SYSTEM_INTEGRATION)
    routes_by_id = route_lookup(access_map)
    systems_by_path = system_lookup(system_map)

    rows = []
    routed_capability_count = 0
    system_bound_capability_count = 0
    public_artifact_capability_count = 0
    unresolved_capability_count = 0
    route_binding_count = 0

    for capability in capability_registry.get("capabilities", []):
        route_ids = capability.get("access_route_ids", [])
        routes = [route_payload(routes_by_id[route_id]) for route_id in route_ids if route_id in routes_by_id]
        systems = [system_payload(path, systems_by_path.get(path)) for path in capability.get("system_paths", [])]
        start_points = unique(
            [
                *[doc for route in routes for doc in route.get("primary_docs", [])],
                *capability.get("public_artifacts", []),
                *capability.get("resolved_paths", [])[:4],
            ]
        )
        runtime_surfaces = unique(
            [
                *capability.get("runtime_refs", []),
                *[surface for route in routes for surface in route.get("runtime_or_api_surface", [])],
            ]
        )

        if routes:
            routed_capability_count += 1
            route_binding_count += len(routes)
        if systems:
            system_bound_capability_count += 1
        if capability.get("public_artifacts"):
            public_artifact_capability_count += 1
        if capability.get("unresolved_refs"):
            unresolved_capability_count += 1

        rows.append(
            {
                "id": capability.get("id", ""),
                "label": capability.get("label", ""),
                "description": capability.get("description", ""),
                "readiness_status": readiness_for(capability, routes, systems),
                "access_routes": routes,
                "related_systems": systems,
                "end_user_start_points": start_points,
                "runtime_or_api_surfaces": runtime_surfaces,
                "implementation_surfaces": {
                    "resolved_paths": capability.get("resolved_paths", []),
                    "runtime_refs": capability.get("runtime_refs", []),
                    "generated_refs": capability.get("generated_refs", []),
                    "code_symbol_refs": capability.get("code_symbol_refs", []),
                    "unresolved_refs": capability.get("unresolved_refs", []),
                    "public_artifacts": capability.get("public_artifacts", []),
                },
                "safety_gates": unique(
                    [
                        *[route.get("safety_gate", "") for route in routes],
                        *[system.get("safety_gate", "") for system in systems],
                    ]
                ),
            }
        )

    return {
        "name": "Aureon Capability Access Matrix",
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_capability_access_matrix.py",
        "docs_mirror": "docs/capability_access_matrix.json",
        "frontend_public_mirror": "frontend/public/aureon_capability_access_matrix.json",
        "source_documents": [
            "docs/end_user_access_map.json",
            "docs/capability_registry.json",
            "docs/system_integration_map.json",
        ],
        "public_contract": {
            "contains_file_contents": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "capability_count": len(rows),
            "routed_capability_count": routed_capability_count,
            "system_bound_capability_count": system_bound_capability_count,
            "public_artifact_capability_count": public_artifact_capability_count,
            "unresolved_capability_count": unresolved_capability_count,
            "route_binding_count": route_binding_count,
            "access_route_count": len(routes_by_id),
        },
        "capabilities": rows,
        "frontend_navigation_tab": "#repo-map",
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    matrix = build_matrix()
    write_json(DOCS_MATRIX, matrix)
    write_json(PUBLIC_MATRIX, matrix)
    print(f"Wrote {DOCS_MATRIX.relative_to(REPO_ROOT)}")
    print(f"Wrote {PUBLIC_MATRIX.relative_to(REPO_ROOT)}")
    print(
        "Mapped "
        f"{matrix['summary']['routed_capability_count']} routed capabilities "
        f"across {matrix['summary']['route_binding_count']} route bindings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
