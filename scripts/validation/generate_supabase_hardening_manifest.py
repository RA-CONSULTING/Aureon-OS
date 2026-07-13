"""Generate a public Supabase endpoint hardening manifest from config."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"
SUPABASE_CONFIG = REPO_ROOT / "supabase" / "config.toml"
DOCS_MANIFEST = REPO_ROOT / "docs" / "supabase_hardening_manifest.json"
PUBLIC_MANIFEST = REPO_ROOT / "frontend" / "public" / "aureon_supabase_hardening_manifest.json"

LOW_PUBLIC_PREFIXES = ("fetch-", "backend-health-check", "aureon-chat", "interpret-frequency")
MUTATION_TERMS = ("force", "confirm", "execute", "trade", "topup", "deduct", "update", "create", "backfill")
INGEST_TERMS = ("ingest", "sync", "poll")
SENSITIVE_STATE_TERMS = ("terminal", "brain", "credential", "balance", "position", "pnl", "connection")


def parse_supabase_functions() -> list[dict]:
    functions: list[dict] = []
    current = ""
    section_re = re.compile(r"^\s*\[functions\.([^\]]+)\]\s*$")
    verify_re = re.compile(r"^\s*verify_jwt\s*=\s*(true|false)\s*(?:#.*)?$")

    for line in SUPABASE_CONFIG.read_text(encoding="utf-8").splitlines():
        section_match = section_re.match(line)
        if section_match:
            current = section_match.group(1)
            continue

        verify_match = verify_re.match(line)
        if current and verify_match:
            verify_jwt = verify_match.group(1) == "true"
            functions.append(classify_function(current, verify_jwt))

    return functions


def classify_function(name: str, verify_jwt: bool) -> dict:
    function_path = f"supabase/functions/{name}/index.ts"
    has_source = (REPO_ROOT / function_path).exists()
    terms = {
        "mutation": any(term in name for term in MUTATION_TERMS),
        "ingest": any(term in name for term in INGEST_TERMS),
        "sensitive_state": any(term in name for term in SENSITIVE_STATE_TERMS),
    }

    if verify_jwt:
        risk = "medium" if terms["mutation"] or terms["sensitive_state"] else "low"
        status = "jwt_gated_review_required" if risk == "medium" else "jwt_gated"
        required_controls = ["role checks", "payload schema validation", "rate limits", "redacted logs"] if risk == "medium" else ["payload schema validation", "redacted logs"]
    elif name.startswith(LOW_PUBLIC_PREFIXES) and not terms["mutation"] and not terms["sensitive_state"]:
        risk = "low"
        status = "public_read_candidate"
        required_controls = ["prove anonymous-safe response", "rate limits", "CORS allowlist", "redacted logs"]
    elif terms["mutation"] or terms["sensitive_state"]:
        risk = "high"
        status = "must_gate_before_production"
        required_controls = ["enable JWT or service-role validation", "role checks", "payload schema validation", "rate limits", "replay protection", "redacted logs"]
    else:
        risk = "medium"
        status = "public_review_required"
        required_controls = ["prove anonymous-safe response", "payload schema validation", "rate limits", "CORS allowlist", "redacted logs"]

    return {
        "name": name,
        "path": function_path,
        "source_present": has_source,
        "verify_jwt": verify_jwt,
        "auth_mode": "jwt_required" if verify_jwt else "public_edge",
        "risk": risk,
        "status": status,
        "signals": terms,
        "required_controls": required_controls,
    }


def build_manifest() -> dict:
    functions = parse_supabase_functions()
    public_functions = [item for item in functions if not item["verify_jwt"]]
    high_risk_public = [item for item in public_functions if item["risk"] == "high"]
    medium_risk_public = [item for item in public_functions if item["risk"] == "medium"]
    jwt_review = [item for item in functions if item["verify_jwt"] and item["status"] == "jwt_gated_review_required"]

    return {
        "name": "Aureon Supabase Hardening Manifest",
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_supabase_hardening_manifest.py",
        "docs_mirror": "docs/supabase_hardening_manifest.json",
        "frontend_public_mirror": "frontend/public/aureon_supabase_hardening_manifest.json",
        "source_documents": ["supabase/config.toml", "docs/SAAS_INTEGRATION_READINESS.md"],
        "public_contract": {
            "contains_file_contents": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "function_count": len(functions),
            "verify_jwt_true": sum(1 for item in functions if item["verify_jwt"]),
            "verify_jwt_false": len(public_functions),
            "public_high_risk_count": len(high_risk_public),
            "public_medium_risk_count": len(medium_risk_public),
            "jwt_review_required_count": len(jwt_review),
            "production_blocker_count": len(high_risk_public),
        },
        "production_status": "blocked_until_public_high_risk_routes_are_gated" if high_risk_public else "public_routes_reviewed",
        "public_high_risk_routes": [item["name"] for item in high_risk_public],
        "public_medium_risk_routes": [item["name"] for item in medium_risk_public],
        "jwt_review_required_routes": [item["name"] for item in jwt_review],
        "production_gates": [
            "keep high-risk mutation and sensitive-state routes JWT gated",
            "prove remaining public routes are anonymous-safe",
            "add role checks for JWT-gated mutation routes",
            "add payload schema validation for all hosted functions",
            "define CORS allowlist, rate limits, replay protection, and redacted logging",
        ],
        "functions": functions,
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
        "Classified "
        f"{manifest['summary']['function_count']} functions; "
        f"{manifest['summary']['production_blocker_count']} public high-risk routes block production"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
