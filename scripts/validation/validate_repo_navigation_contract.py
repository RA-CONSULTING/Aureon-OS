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
DOCS_NAVIGATION_INDEX = REPO_ROOT / "docs" / "repo_navigation_index.json"
PUBLIC_REPO_SITEMAP = REPO_ROOT / "frontend" / "public" / "aureon_repo_sitemap.json"
PUBLIC_ACCESS_MAP = REPO_ROOT / "frontend" / "public" / "aureon_end_user_access_map.json"
PUBLIC_NAVIGATION_INDEX = REPO_ROOT / "frontend" / "public" / "aureon_repo_navigation_index.json"
SUPABASE_CONFIG = REPO_ROOT / "supabase" / "config.toml"

REQUIRED_PATHS = [
    "README.md",
    "docs/REPO_SITEMAP.md",
    "docs/END_USER_ACCESS_MAP.md",
    "docs/SAAS_INTEGRATION_READINESS.md",
    "docs/INDEX.md",
    "docs/investor/README.md",
    "docs/investor/TERMINOLOGY.md",
    "docs/repo_sitemap.json",
    "docs/end_user_access_map.json",
    "docs/repo_navigation_index.json",
    "frontend/src/components/RepoNavigationPanel.tsx",
    "frontend/public/aureon_repo_sitemap.json",
    "frontend/public/aureon_end_user_access_map.json",
    "frontend/public/aureon_repo_navigation_index.json",
    "scripts/validation/generate_repo_navigation_index.py",
]

MARKDOWN_FILES = [
    "README.md",
    "docs/INDEX.md",
    "docs/REPO_SITEMAP.md",
    "docs/END_USER_ACCESS_MAP.md",
    "docs/SAAS_INTEGRATION_READINESS.md",
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
    docs_navigation_index = load_json(DOCS_NAVIGATION_INDEX)
    public_repo = load_json(PUBLIC_REPO_SITEMAP)
    public_access = load_json(PUBLIC_ACCESS_MAP)
    public_navigation_index = load_json(PUBLIC_NAVIGATION_INDEX)

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
    expect(docs_navigation_index == public_navigation_index, failures, "repo navigation index docs/public mirrors differ")
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

    supabase_counts = parse_supabase_auth_counts()
    expect(
        docs_repo.get("saas_readiness", {}).get("supabase_auth_counts") == supabase_counts,
        failures,
        "repo sitemap Supabase auth counts differ from supabase/config.toml",
    )

    for label, manifest in (
        ("frontend/public/aureon_repo_sitemap.json", public_repo),
        ("frontend/public/aureon_end_user_access_map.json", public_access),
        ("frontend/public/aureon_repo_navigation_index.json", public_navigation_index),
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
    print(f"OK repo_navigation_index_entries={len(navigation_entries)}")
    print(f"OK supabase_auth_counts={supabase_counts}")
    print("OK public navigation manifests contain no credential-like values")
    print("OK key Markdown links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
