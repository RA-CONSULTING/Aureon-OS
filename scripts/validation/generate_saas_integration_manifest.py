"""Generate Aureon's public SaaS integration manifest from repo config."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"
DOCS_MANIFEST = REPO_ROOT / "docs" / "saas_integration_manifest.json"
PUBLIC_MANIFEST = REPO_ROOT / "frontend" / "public" / "aureon_saas_integration_manifest.json"
SUPABASE_CONFIG = REPO_ROOT / "supabase" / "config.toml"

ENV_SOURCES = [
    ".env.example",
    "deploy/env.example",
    "app.yaml",
]

DEPLOYMENT_SURFACES = [
    {"id": "frontend_app", "label": "Frontend app", "paths": ["frontend/package.json", "frontend/src/", "frontend/public/"], "mode": "hosted browser surface"},
    {"id": "supabase_backend", "label": "Supabase backend", "paths": ["supabase/config.toml", "supabase/functions/", "supabase/migrations/"], "mode": "hosted auth, functions, and data plane"},
    {"id": "digitalocean_app", "label": "DigitalOcean App Platform", "paths": ["app.yaml", "deploy/"], "mode": "containerized production app spec"},
    {"id": "local_operator", "label": "Local Windows operator", "paths": ["AUREON_PRODUCTION_LIVE.cmd", "AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1", "RUNNING.md"], "mode": "operator-controlled local runtime"},
    {"id": "serverless_routes", "label": "Serverless routes", "paths": ["api/", "functions/", "netlify/"], "mode": "hosted edge/serverless routes"},
    {"id": "node_bridge", "label": "Node/server bridge", "paths": ["server/"], "mode": "optional backend bridge"},
    {"id": "docker_package", "label": "Docker and production package", "paths": ["Dockerfile", "docker-compose.yml", "production/"], "mode": "container/release package"},
]

PRODUCTION_GATES = [
    "choose one canonical hosted target",
    "store secrets in target secret store",
    "review public Supabase functions",
    "define CORS, rate limits, payload limits, logging, and redaction",
    "decide generated artifact persistence policy",
    "keep sensitive mutation routes operator-controlled",
    "run local and deployment smoke checks",
]

PUBLIC_ENDPOINT_REVIEW_TERMS = (
    "force",
    "confirm",
    "poll",
    "trade",
    "test",
    "ingest",
    "terminal",
    "brain",
    "credential",
    "connect",
)


def read_text(rel_path: str) -> str:
    path = REPO_ROOT / rel_path
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def classify_env_var(name: str) -> str:
    if name.startswith("VITE_SUPABASE_"):
        return "Supabase frontend"
    if name.startswith("SUPABASE_"):
        return "Supabase runtime"
    if any(part in name for part in ("API_KEY", "API_SECRET", "SECRET_KEY", "PASSWORD", "IDENTIFIER")):
        return "Exchange credentials"
    if any(part in name for part in ("DRY_RUN", "PAPER", "DEMO", "TESTNET", "LIVE", "REAL_DATA_ONLY", "SIMULATION", "MOCK")):
        return "Exchange mode flags"
    if name.startswith("ENABLE_") or name == "STARTING_CAPITAL":
        return "Feature enablement"
    if name in {"PORT", "MODE"} or name.startswith("PYTHON") or name.startswith("AUREON_") or name.endswith("_PATH") or name.endswith("_URL"):
        return "Runtime/platform"
    if name.endswith("_KEY"):
        return "Optional data providers"
    return "Runtime/platform"


def is_secret_like(name: str) -> bool:
    return any(marker in name for marker in ("SECRET", "PASSWORD", "API_KEY", "TOKEN", "PRIVATE", "IDENTIFIER"))


def parse_env_assignment_sources() -> dict[str, dict]:
    variables: dict[str, dict] = {}
    assignment_re = re.compile(r"^\s*([A-Z][A-Z0-9_]+)\s*=")
    app_key_re = re.compile(r"^\s*-\s*key:\s*([A-Z][A-Z0-9_]+)\s*$")
    app_attr_re = re.compile(r"^\s+(scope|type|value):\s*(.+?)\s*$")

    for rel_path in ENV_SOURCES:
        lines = read_text(rel_path).splitlines()
        current_app_key = ""
        for line in lines:
            key_match = app_key_re.match(line)
            if key_match:
                current_app_key = key_match.group(1)
                entry = variables.setdefault(
                    current_app_key,
                    {
                        "name": current_app_key,
                        "group": classify_env_var(current_app_key),
                        "sources": [],
                        "scopes": [],
                        "sensitive_like": is_secret_like(current_app_key),
                        "platform_sensitive_store": False,
                    },
                )
                if rel_path not in entry["sources"]:
                    entry["sources"].append(rel_path)
                continue

            attr_match = app_attr_re.match(line)
            if current_app_key and attr_match and rel_path == "app.yaml":
                attr, value = attr_match.groups()
                entry = variables[current_app_key]
                if attr == "scope" and value not in entry["scopes"]:
                    entry["scopes"].append(value)
                if attr == "type" and value.strip().upper() == "SECRET":
                    entry["platform_sensitive_store"] = True
                    entry["sensitive_like"] = True
                continue

            assign_match = assignment_re.match(line)
            if assign_match:
                name = assign_match.group(1)
                entry = variables.setdefault(
                    name,
                    {
                        "name": name,
                        "group": classify_env_var(name),
                        "sources": [],
                        "scopes": [],
                        "sensitive_like": is_secret_like(name),
                        "platform_sensitive_store": False,
                    },
                )
                if rel_path not in entry["sources"]:
                    entry["sources"].append(rel_path)

    return variables


def parse_supabase_functions() -> list[dict]:
    functions: list[dict] = []
    current = ""
    section_re = re.compile(r"^\s*\[functions\.([^\]]+)\]\s*$")
    verify_re = re.compile(r"^\s*verify_jwt\s*=\s*(true|false)\s*(?:#.*)?$")

    for line in read_text("supabase/config.toml").splitlines():
        section_match = section_re.match(line)
        if section_match:
            current = section_match.group(1)
            continue
        verify_match = verify_re.match(line)
        if current and verify_match:
            verify_jwt = verify_match.group(1) == "true"
            public_review_required = (not verify_jwt) and any(term in current for term in PUBLIC_ENDPOINT_REVIEW_TERMS)
            functions.append(
                {
                    "name": current,
                    "verify_jwt": verify_jwt,
                    "auth_mode": "jwt_required" if verify_jwt else "public_edge",
                    "public_review_required": public_review_required,
                }
            )
    return functions


def build_manifest() -> dict:
    variables = parse_env_assignment_sources()
    functions = parse_supabase_functions()
    grouped_variables: dict[str, list[str]] = defaultdict(list)
    for name, entry in variables.items():
        grouped_variables[entry["group"]].append(name)

    public_functions = [item for item in functions if not item["verify_jwt"]]
    review_required = [item["name"] for item in public_functions if item["public_review_required"]]
    sensitive_like = [entry for entry in variables.values() if entry["sensitive_like"]]

    return {
        "name": "Aureon SaaS Integration Manifest",
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_saas_integration_manifest.py",
        "docs_mirror": "docs/saas_integration_manifest.json",
        "frontend_public_mirror": "frontend/public/aureon_saas_integration_manifest.json",
        "source_documents": ["docs/SAAS_INTEGRATION_READINESS.md", *ENV_SOURCES, "supabase/config.toml"],
        "public_contract": {
            "contains_env_values": False,
            "contains_file_contents": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "canonical_shape": "local-first SaaS integration with hosted browser/Supabase surfaces and operator-controlled sensitive mutation routes",
        "deployment_surfaces": [
            {
                **surface,
                "tracked": all((REPO_ROOT / path.rstrip("/")).exists() for path in surface["paths"]),
            }
            for surface in DEPLOYMENT_SURFACES
        ],
        "environment": {
            "source_files": ENV_SOURCES,
            "variable_count": len(variables),
            "sensitive_variable_count": len(sensitive_like),
            "groups": {group: sorted(names) for group, names in sorted(grouped_variables.items())},
            "variables": sorted(variables.values(), key=lambda item: item["name"]),
        },
        "supabase": {
            "config": "supabase/config.toml",
            "function_count": len(functions),
            "verify_jwt_true": sum(1 for item in functions if item["verify_jwt"]),
            "verify_jwt_false": len(public_functions),
            "public_endpoint_review_required_count": len(review_required),
            "public_endpoint_review_required": review_required,
            "functions": functions,
        },
        "production_gates": PRODUCTION_GATES,
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
        "Captured "
        f"{manifest['environment']['variable_count']} env variable names and "
        f"{manifest['supabase']['function_count']} Supabase functions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
