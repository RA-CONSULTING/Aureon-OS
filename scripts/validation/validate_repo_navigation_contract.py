"""Validate Aureon's repo navigation and SaaS-access contract."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[2]

DOCS_REPO_SITEMAP = REPO_ROOT / "docs" / "repo_sitemap.json"
DOCS_ACCESS_MAP = REPO_ROOT / "docs" / "end_user_access_map.json"
DOCS_CAPABILITY_REGISTRY = REPO_ROOT / "docs" / "capability_registry.json"
DOCS_NAVIGATION_INDEX = REPO_ROOT / "docs" / "repo_navigation_index.json"
DOCS_SYSTEM_INTEGRATION = REPO_ROOT / "docs" / "system_integration_map.json"
DOCS_SAAS_MANIFEST = REPO_ROOT / "docs" / "saas_integration_manifest.json"
DOCS_SUPABASE_HARDENING = REPO_ROOT / "docs" / "supabase_hardening_manifest.json"
PUBLIC_REPO_SITEMAP = REPO_ROOT / "frontend" / "public" / "aureon_repo_sitemap.json"
PUBLIC_ACCESS_MAP = REPO_ROOT / "frontend" / "public" / "aureon_end_user_access_map.json"
PUBLIC_CAPABILITY_REGISTRY = REPO_ROOT / "frontend" / "public" / "aureon_capability_registry.json"
PUBLIC_NAVIGATION_INDEX = REPO_ROOT / "frontend" / "public" / "aureon_repo_navigation_index.json"
PUBLIC_SYSTEM_INTEGRATION = REPO_ROOT / "frontend" / "public" / "aureon_system_integration_map.json"
PUBLIC_SAAS_MANIFEST = REPO_ROOT / "frontend" / "public" / "aureon_saas_integration_manifest.json"
PUBLIC_SUPABASE_HARDENING = REPO_ROOT / "frontend" / "public" / "aureon_supabase_hardening_manifest.json"
SUPABASE_CONFIG = REPO_ROOT / "supabase" / "config.toml"
ENV_SOURCES = [".env.example", "deploy/env.example", "app.yaml"]

REQUIRED_PATHS = [
    "README.md",
    "docs/REPO_SITEMAP.md",
    "docs/END_USER_ACCESS_MAP.md",
    "docs/CAPABILITY_REGISTRY.md",
    "docs/SAAS_INTEGRATION_READINESS.md",
    "docs/SYSTEM_INTEGRATION_MAP.md",
    "docs/INDEX.md",
    "docs/investor/README.md",
    "docs/investor/TERMINOLOGY.md",
    "docs/repo_sitemap.json",
    "docs/end_user_access_map.json",
    "docs/capability_registry.json",
    "docs/repo_navigation_index.json",
    "docs/system_integration_map.json",
    "docs/saas_integration_manifest.json",
    "docs/SUPABASE_HARDENING_REVIEW.md",
    "docs/supabase_hardening_manifest.json",
    "frontend/src/components/RepoNavigationPanel.tsx",
    "frontend/public/aureon_repo_sitemap.json",
    "frontend/public/aureon_end_user_access_map.json",
    "frontend/public/aureon_capability_registry.json",
    "frontend/public/aureon_repo_navigation_index.json",
    "frontend/public/aureon_system_integration_map.json",
    "frontend/public/aureon_saas_integration_manifest.json",
    "frontend/public/aureon_supabase_hardening_manifest.json",
    "scripts/validation/generate_repo_navigation_index.py",
    "scripts/validation/generate_capability_registry.py",
    "scripts/validation/generate_system_integration_map.py",
    "scripts/validation/generate_saas_integration_manifest.py",
    "scripts/validation/generate_supabase_hardening_manifest.py",
]

MARKDOWN_FILES = [
    "README.md",
    "docs/INDEX.md",
    "docs/REPO_SITEMAP.md",
    "docs/END_USER_ACCESS_MAP.md",
    "docs/CAPABILITY_REGISTRY.md",
    "docs/SYSTEM_INTEGRATION_MAP.md",
    "docs/SAAS_INTEGRATION_READINESS.md",
    "docs/SUPABASE_HARDENING_REVIEW.md",
    "docs/investor/README.md",
    "docs/investor/TERMINOLOGY.md",
]

SECRET_VALUE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"pk_[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
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


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def git_file_count(path_prefix: str | None = None) -> int:
    args = ["ls-files", "-z"]
    if path_prefix:
        args.extend(["--", path_prefix])
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return len([path for path in result.stdout.split(b"\0") if path])


def parse_supabase_auth_counts() -> dict[str, int]:
    counts = {"verify_jwt_true": 0, "verify_jwt_false": 0}
    current_function = None
    section_re = re.compile(r"^\s*\[functions\.([^\]]+)\]\s*$")
    verify_re = re.compile(r"^\s*verify_jwt\s*=\s*(true|false)\s*(?:#.*)?$")

    for raw_line in SUPABASE_CONFIG.read_text(encoding="utf-8").splitlines():
        section_match = section_re.match(raw_line)
        if section_match:
            current_function = section_match.group(1)
            continue

        verify_match = verify_re.match(raw_line)
        if current_function and verify_match:
            key = f"verify_jwt_{verify_match.group(1)}"
            counts[key] += 1

    return counts


def parse_env_variable_names() -> set[str]:
    names: set[str] = set()
    assignment_re = re.compile(r"^\s*([A-Z][A-Z0-9_]+)\s*=")
    app_key_re = re.compile(r"^\s*-\s*key:\s*([A-Z][A-Z0-9_]+)\s*$")

    for rel_path in ENV_SOURCES:
        path = REPO_ROOT / rel_path
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            assignment_match = assignment_re.match(raw_line)
            if assignment_match:
                names.add(assignment_match.group(1))
                continue
            app_key_match = app_key_re.match(raw_line)
            if app_key_match:
                names.add(app_key_match.group(1))

    return names


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


def collect_json_secret_findings(value: object, path: str = "$") -> list[str]:
    findings: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            lower_key = key.lower()
            if any(marker in lower_key for marker in ("password", "secret", "token", "api_key", "apikey", "private_key")):
                if isinstance(child, str) and child.strip().lower() not in {"", "false", "none", "null", "redacted", "[redacted]"}:
                    findings.append(f"{child_path} contains a credential-like key with a string value")
                elif child not in (False, None) and not isinstance(child, (dict, list)):
                    findings.append(f"{child_path} contains a credential-like key with a non-empty value")
            findings.extend(collect_json_secret_findings(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(collect_json_secret_findings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                findings.append(f"{path} contains a credential-like value")

    return findings


def markdown_link_targets(markdown: str) -> list[str]:
    pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    return [match.group(1).strip() for match in pattern.finditer(markdown)]


def is_external_or_anchor(target: str) -> bool:
    lowered = target.lower()
    return (
        not target
        or lowered.startswith(("http://", "https://", "mailto:", "javascript:"))
        or target.startswith("#")
    )


def normalize_markdown_target(target: str) -> str:
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split("#", 1)[0].strip()
    if " " in target and not target.endswith("/"):
        first, *_ = target.split()
        target = first
    return unquote(target)


def collect_broken_markdown_links() -> list[str]:
    broken: list[str] = []
    for rel_path in MARKDOWN_FILES:
        markdown_path = REPO_ROOT / rel_path
        if not markdown_path.exists():
            broken.append(f"{rel_path} is missing")
            continue

        for raw_target in markdown_link_targets(markdown_path.read_text(encoding="utf-8")):
            if is_external_or_anchor(raw_target):
                continue
            target = normalize_markdown_target(raw_target)
            if not target:
                continue
            candidate = (markdown_path.parent / target).resolve()
            if not str(candidate).startswith(str(REPO_ROOT.resolve())):
                broken.append(f"{rel_path} links outside repo: {raw_target}")
            elif not candidate.exists():
                broken.append(f"{rel_path} has broken link: {raw_target}")

    return broken


def expect(condition: bool, failures: list[str], message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    docs_repo = load_json(DOCS_REPO_SITEMAP)
    docs_access = load_json(DOCS_ACCESS_MAP)
    docs_capability_registry = load_json(DOCS_CAPABILITY_REGISTRY)
    docs_navigation_index = load_json(DOCS_NAVIGATION_INDEX)
    docs_system_integration = load_json(DOCS_SYSTEM_INTEGRATION)
    docs_saas_manifest = load_json(DOCS_SAAS_MANIFEST)
    docs_supabase_hardening = load_json(DOCS_SUPABASE_HARDENING)
    public_repo = load_json(PUBLIC_REPO_SITEMAP)
    public_access = load_json(PUBLIC_ACCESS_MAP)
    public_capability_registry = load_json(PUBLIC_CAPABILITY_REGISTRY)
    public_navigation_index = load_json(PUBLIC_NAVIGATION_INDEX)
    public_system_integration = load_json(PUBLIC_SYSTEM_INTEGRATION)
    public_saas_manifest = load_json(PUBLIC_SAAS_MANIFEST)
    public_supabase_hardening = load_json(PUBLIC_SUPABASE_HARDENING)

    for rel_path in REQUIRED_PATHS:
        expect((REPO_ROOT / rel_path).exists(), failures, f"required path missing: {rel_path}")

    tracked_total = git_file_count()
    expect(docs_repo.get("tracked_file_count") == tracked_total, failures, "docs/repo_sitemap.json tracked_file_count is stale")
    expect(public_repo.get("tracked_file_count") == tracked_total, failures, "frontend public sitemap tracked_file_count is stale")
    expect(docs_navigation_index.get("tracked_file_count") == tracked_total, failures, "docs repo navigation index tracked_file_count is stale")
    expect(public_navigation_index.get("tracked_file_count") == tracked_total, failures, "frontend repo navigation index tracked_file_count is stale")

    systems = {entry["path"]: entry["files"] for entry in docs_repo.get("top_level_systems", [])}
    for path, recorded_count in systems.items():
        actual_count = git_file_count(path)
        expect(recorded_count == actual_count, failures, f"top_level_systems count is stale for {path}: {recorded_count} != {actual_count}")

    docs_capabilities = docs_access.get("capabilities", [])
    public_capabilities = public_access.get("capabilities", [])
    expect(len(docs_capabilities) == 13, failures, "docs access map capability count changed from 13")
    expect(len(public_capabilities) == len(docs_capabilities), failures, "public access map capability count differs from docs access map")
    expect(
        docs_repo.get("end_user_access", {}).get("capability_count") == len(docs_capabilities),
        failures,
        "repo sitemap end_user_access.capability_count is stale",
    )
    expect(
        docs_repo.get("end_user_access", {}).get("frontend_navigation_tab") == "#repo-map",
        failures,
        "repo sitemap does not expose the frontend navigation tab",
    )
    expect(
        public_repo.get("frontend_navigation_tab") == "#repo-map",
        failures,
        "frontend public sitemap does not expose #repo-map",
    )
    expect(
        docs_repo.get("end_user_access", {}).get("capability_registry") == "docs/capability_registry.json",
        failures,
        "repo sitemap does not expose the docs capability registry",
    )
    expect(
        docs_repo.get("end_user_access", {}).get("frontend_public_capability_registry")
        == "frontend/public/aureon_capability_registry.json",
        failures,
        "repo sitemap does not expose the public capability registry",
    )
    expect(
        public_repo.get("capability_registry") == "frontend/public/aureon_capability_registry.json",
        failures,
        "frontend public sitemap does not expose the capability registry",
    )
    expect(
        docs_repo.get("end_user_access", {}).get("repo_navigation_index") == "docs/repo_navigation_index.json",
        failures,
        "repo sitemap does not expose the docs repo navigation index",
    )
    expect(
        docs_repo.get("end_user_access", {}).get("frontend_public_navigation_index") == "frontend/public/aureon_repo_navigation_index.json",
        failures,
        "repo sitemap does not expose the public repo navigation index",
    )
    expect(
        public_repo.get("navigation_index") == "frontend/public/aureon_repo_navigation_index.json",
        failures,
        "frontend public sitemap does not expose the repo navigation index",
    )
    expect(
        docs_repo.get("end_user_access", {}).get("system_integration_map") == "docs/system_integration_map.json",
        failures,
        "repo sitemap does not expose the docs system integration map",
    )
    expect(
        docs_repo.get("end_user_access", {}).get("frontend_public_system_integration_map")
        == "frontend/public/aureon_system_integration_map.json",
        failures,
        "repo sitemap does not expose the public system integration map",
    )
    expect(
        public_repo.get("system_integration_map") == "frontend/public/aureon_system_integration_map.json",
        failures,
        "frontend public sitemap does not expose the system integration map",
    )
    expect(
        docs_repo.get("saas_readiness", {}).get("machine_readable") == "docs/saas_integration_manifest.json",
        failures,
        "repo sitemap does not expose the docs SaaS integration manifest",
    )
    expect(
        docs_repo.get("saas_readiness", {}).get("frontend_public_mirror") == "frontend/public/aureon_saas_integration_manifest.json",
        failures,
        "repo sitemap does not expose the public SaaS integration manifest",
    )
    expect(
        public_repo.get("saas_integration_manifest") == "frontend/public/aureon_saas_integration_manifest.json",
        failures,
        "frontend public sitemap does not expose the SaaS integration manifest",
    )
    expect(
        docs_repo.get("saas_readiness", {}).get("supabase_hardening_manifest") == "docs/supabase_hardening_manifest.json",
        failures,
        "repo sitemap does not expose the docs Supabase hardening manifest",
    )
    expect(
        docs_repo.get("saas_readiness", {}).get("frontend_public_supabase_hardening_manifest")
        == "frontend/public/aureon_supabase_hardening_manifest.json",
        failures,
        "repo sitemap does not expose the public Supabase hardening manifest",
    )
    expect(
        public_repo.get("supabase_hardening_manifest") == "frontend/public/aureon_supabase_hardening_manifest.json",
        failures,
        "frontend public sitemap does not expose the Supabase hardening manifest",
    )
    expect(docs_capability_registry == public_capability_registry, failures, "capability registry docs/public mirrors differ")
    expect(docs_navigation_index == public_navigation_index, failures, "repo navigation index docs/public mirrors differ")
    expect(docs_system_integration == public_system_integration, failures, "system integration map docs/public mirrors differ")
    capability_registry_rows = docs_capability_registry.get("capabilities", []) if isinstance(docs_capability_registry, dict) else []
    expected_capability_rows = parse_capabilities_table_count()
    registry_summary = docs_capability_registry.get("summary", {}) if isinstance(docs_capability_registry, dict) else {}
    registry_resolved_count = sum(len(row.get("resolved_paths", [])) for row in capability_registry_rows if isinstance(row, dict))
    registry_runtime_count = sum(len(row.get("runtime_refs", [])) for row in capability_registry_rows if isinstance(row, dict))
    registry_generated_count = sum(len(row.get("generated_refs", [])) for row in capability_registry_rows if isinstance(row, dict))
    registry_command_count = sum(len(row.get("command_refs", [])) for row in capability_registry_rows if isinstance(row, dict))
    registry_symbol_count = sum(len(row.get("code_symbol_refs", [])) for row in capability_registry_rows if isinstance(row, dict))
    registry_unresolved_count = sum(len(row.get("unresolved_refs", [])) for row in capability_registry_rows if isinstance(row, dict))
    expect(
        registry_summary.get("tracked_file_count") == tracked_total,
        failures,
        "capability registry tracked_file_count is stale",
    )
    expect(
        registry_summary.get("capability_count") == expected_capability_rows,
        failures,
        "capability registry capability_count differs from CAPABILITIES.md",
    )
    expect(
        len(capability_registry_rows) == expected_capability_rows,
        failures,
        "capability registry row count differs from CAPABILITIES.md",
    )
    expect(
        registry_summary.get("runtime_surface_ref_count") == registry_runtime_count,
        failures,
        "capability registry runtime_surface_ref_count differs from rows",
    )
    expect(
        registry_summary.get("generated_artifact_ref_count") == registry_generated_count,
        failures,
        "capability registry generated_artifact_ref_count differs from rows",
    )
    expect(
        registry_summary.get("command_surface_ref_count") == registry_command_count,
        failures,
        "capability registry command_surface_ref_count differs from rows",
    )
    expect(
        registry_summary.get("code_symbol_ref_count") == registry_symbol_count,
        failures,
        "capability registry code_symbol_ref_count differs from rows",
    )
    expect(
        registry_summary.get("unresolved_surface_ref_count") == registry_unresolved_count,
        failures,
        "capability registry unresolved_surface_ref_count differs from rows",
    )
    expect(
        registry_summary.get("resolved_surface_ref_count", 0) <= registry_resolved_count,
        failures,
        "capability registry resolved_surface_ref_count exceeds row path count",
    )
    expect(
        docs_capability_registry.get("public_contract", {}).get("contains_file_contents") is False,
        failures,
        "capability registry public contract must not contain file contents",
    )
    expect(
        docs_capability_registry.get("public_contract", {}).get("contains_secrets") is False,
        failures,
        "capability registry public contract must not contain secrets",
    )
    navigation_entries = docs_navigation_index.get("entries", [])
    expect(len(navigation_entries) == tracked_total, failures, "repo navigation index entry count differs from git ls-files")
    expect(docs_navigation_index.get("entry_count") == tracked_total, failures, "repo navigation index entry_count is stale")
    entry_paths = [entry.get("path") for entry in navigation_entries if isinstance(entry, dict)]
    expect(len(set(entry_paths)) == tracked_total, failures, "repo navigation index paths are missing or duplicated")
    expect(
        docs_navigation_index.get("public_contract", {}).get("contains_file_contents") is False,
        failures,
        "repo navigation index public contract must not contain file contents",
    )
    system_rows = docs_system_integration.get("systems", []) if isinstance(docs_system_integration, dict) else []
    system_paths = {entry.get("path") for entry in system_rows if isinstance(entry, dict)}
    sitemap_paths = {entry.get("path") for entry in docs_repo.get("top_level_systems", []) if isinstance(entry, dict)}
    expect(
        docs_system_integration.get("summary", {}).get("tracked_file_count") == tracked_total,
        failures,
        "system integration map tracked_file_count is stale",
    )
    expect(
        docs_system_integration.get("summary", {}).get("system_count") == len(docs_repo.get("top_level_systems", [])),
        failures,
        "system integration map system_count differs from repo sitemap",
    )
    expect(
        docs_system_integration.get("summary", {}).get("capability_count") == len(docs_capabilities),
        failures,
        "system integration map capability_count differs from access map",
    )
    expect(system_paths == sitemap_paths, failures, "system integration map does not cover every top-level system")
    expect(
        docs_system_integration.get("public_contract", {}).get("contains_file_contents") is False,
        failures,
        "system integration map public contract must not contain file contents",
    )
    expect(
        docs_system_integration.get("public_contract", {}).get("contains_secrets") is False,
        failures,
        "system integration map public contract must not contain secrets",
    )

    supabase_counts = parse_supabase_auth_counts()
    expect(
        docs_repo.get("saas_readiness", {}).get("supabase_auth_counts") == supabase_counts,
        failures,
        "repo sitemap Supabase auth counts differ from supabase/config.toml",
    )
    expect(docs_saas_manifest == public_saas_manifest, failures, "SaaS integration manifest docs/public mirrors differ")
    expect(docs_supabase_hardening == public_supabase_hardening, failures, "Supabase hardening manifest docs/public mirrors differ")
    env_names = parse_env_variable_names()
    expect(
        docs_saas_manifest.get("environment", {}).get("variable_count") == len(env_names),
        failures,
        "SaaS integration manifest env variable count differs from env sources",
    )
    expect(
        docs_saas_manifest.get("supabase", {}).get("verify_jwt_true") == supabase_counts["verify_jwt_true"],
        failures,
        "SaaS integration manifest verify_jwt_true differs from supabase/config.toml",
    )
    expect(
        docs_saas_manifest.get("supabase", {}).get("verify_jwt_false") == supabase_counts["verify_jwt_false"],
        failures,
        "SaaS integration manifest verify_jwt_false differs from supabase/config.toml",
    )
    expect(
        docs_saas_manifest.get("public_contract", {}).get("contains_env_values") is False,
        failures,
        "SaaS integration manifest public contract must not contain env values",
    )
    hardening_summary = docs_supabase_hardening.get("summary", {}) if isinstance(docs_supabase_hardening, dict) else {}
    public_high_risk_routes = docs_supabase_hardening.get("public_high_risk_routes", []) if isinstance(docs_supabase_hardening, dict) else []
    expect(
        hardening_summary.get("function_count") == supabase_counts["verify_jwt_true"] + supabase_counts["verify_jwt_false"],
        failures,
        "Supabase hardening manifest function_count differs from supabase/config.toml",
    )
    expect(
        hardening_summary.get("verify_jwt_true") == supabase_counts["verify_jwt_true"],
        failures,
        "Supabase hardening manifest verify_jwt_true differs from supabase/config.toml",
    )
    expect(
        hardening_summary.get("verify_jwt_false") == supabase_counts["verify_jwt_false"],
        failures,
        "Supabase hardening manifest verify_jwt_false differs from supabase/config.toml",
    )
    expect(
        hardening_summary.get("public_high_risk_count") == len(public_high_risk_routes),
        failures,
        "Supabase hardening manifest public_high_risk_count is stale",
    )
    expect(
        hardening_summary.get("production_blocker_count") == len(public_high_risk_routes),
        failures,
        "Supabase hardening manifest production_blocker_count is stale",
    )
    expect(
        docs_supabase_hardening.get("public_contract", {}).get("contains_file_contents") is False,
        failures,
        "Supabase hardening manifest public contract must not contain file contents",
    )
    expect(
        docs_supabase_hardening.get("public_contract", {}).get("contains_secrets") is False,
        failures,
        "Supabase hardening manifest public contract must not contain secrets",
    )

    for label, manifest in (
        ("frontend/public/aureon_repo_sitemap.json", public_repo),
        ("frontend/public/aureon_end_user_access_map.json", public_access),
        ("frontend/public/aureon_capability_registry.json", public_capability_registry),
        ("frontend/public/aureon_repo_navigation_index.json", public_navigation_index),
        ("frontend/public/aureon_system_integration_map.json", public_system_integration),
        ("frontend/public/aureon_saas_integration_manifest.json", public_saas_manifest),
        ("frontend/public/aureon_supabase_hardening_manifest.json", public_supabase_hardening),
    ):
        for finding in collect_json_secret_findings(manifest):
            failures.append(f"{label}: {finding}")

    failures.extend(collect_broken_markdown_links())

    if failures:
        print("Navigation contract validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"OK tracked_file_count={tracked_total}")
    print(f"OK capability_count={len(docs_capabilities)}")
    print(f"OK current_capability_registry_count={len(capability_registry_rows)}")
    print(f"OK repo_navigation_index_entries={len(navigation_entries)}")
    print(f"OK system_integration_systems={len(system_rows)}")
    print(f"OK saas_env_variable_count={len(env_names)}")
    print(f"OK supabase_auth_counts={supabase_counts}")
    print(f"OK supabase_hardening_public_blockers={len(public_high_risk_routes)}")
    print("OK public navigation manifests contain no credential-like values")
    print("OK key Markdown links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
