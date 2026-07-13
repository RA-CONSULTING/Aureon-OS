"""Generate Aureon's repo-wide directory organization tree from git metadata."""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"
DOCS_REPO_SITEMAP = REPO_ROOT / "docs" / "repo_sitemap.json"
DOCS_ACCESS_MAP = REPO_ROOT / "docs" / "end_user_access_map.json"
DOCS_TREE = REPO_ROOT / "docs" / "repo_organization_tree.json"
PUBLIC_TREE = REPO_ROOT / "frontend" / "public" / "aureon_repo_organization_tree.json"

ROOT_CATEGORY_RULES = {
    ".github": ("repo automation", "GitHub workflow and repository metadata"),
    "api": ("integration", "API route surface"),
    "archive": ("archive", "Historical bundles and backups"),
    "aureon": ("runtime", "Main Python runtime and subsystem package"),
    "aureon_launcher": ("runtime", "Launcher support"),
    "cli": ("operator tooling", "Command-line helpers"),
    "daemon_codes": ("runtime", "Background automation code"),
    "data": ("evidence", "Research, grants, datasets, and copied evidence"),
    "deploy": ("deployment", "Deployment scripts and service configs"),
    "docs": ("documentation", "Documentation, runbooks, research, architecture, and navigation"),
    "flameborn": ("product surface", "Companion UI/runtime material"),
    "frontend": ("product surface", "React/Vite console and public artifacts"),
    "functions": ("integration", "Serverless function surface"),
    "imports": ("provenance", "Imported historical/source bundles"),
    "integrations": ("integration", "External integration support"),
    "Kings_Accounting_Suite": ("back office", "Accounting, filing-support, and statutory-pack tooling"),
    "netlify": ("deployment", "Netlify deploy/function surface"),
    "packaging": ("release", "Package and build helpers"),
    "production": ("deployment", "Production install and runtime assets"),
    "public": ("product surface", "Public static assets"),
    "scripts": ("operator tooling", "Diagnostics, runners, reports, validation scripts"),
    "server": ("integration", "Node/server bridge surface"),
    "skills": ("extensions", "Local skill registries and interactions"),
    "supabase": ("saas backend", "Supabase config, migrations, and functions"),
    "templates": ("product surface", "UI and report templates"),
    "tests": ("validation", "Regression and validation tests"),
    "tools": ("maintenance", "Focused utility scripts"),
    "VERIFICATION AND VALIDATION": ("validation", "Formal validation documents"),
    "wisdom_data": ("research", "Specialist research/context data"),
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


def top_level_for(path: str) -> str:
    return path.split("/", 1)[0]


def category_for(path: str) -> tuple[str, str]:
    top_level = top_level_for(path.rstrip("/"))
    return ROOT_CATEGORY_RULES.get(top_level, ("uncategorized", "Tracked repository path"))


def zone_for(path: str, zones: list[dict]) -> str:
    normalized_path = path.rstrip("/")
    for zone in zones:
        for prefix in zone.get("paths", []):
            normalized_prefix = str(prefix).rstrip("/")
            if normalized_path == normalized_prefix or normalized_path.startswith(f"{normalized_prefix}/"):
                return str(zone.get("id", "unmapped"))
    return "root"


def capability_map(access_map: dict) -> dict[str, list[str]]:
    lookup: dict[str, list[str]] = defaultdict(list)
    for capability in access_map.get("capabilities", []):
        capability_id = str(capability.get("id", "")).strip()
        if not capability_id:
            continue
        for field in ("primary_docs", "related_systems"):
            for prefix in capability.get(field, []):
                lookup[str(prefix)].append(capability_id)
    return lookup


def capabilities_for(path: str, lookup: dict[str, list[str]]) -> list[str]:
    capability_ids: set[str] = set()
    normalized_path = path.rstrip("/")
    for prefix, ids in lookup.items():
        normalized_prefix = prefix.rstrip("/")
        if normalized_path == normalized_prefix or normalized_path.startswith(f"{normalized_prefix}/"):
            capability_ids.update(ids)
    return sorted(capability_ids)


def directory_prefixes(path: str) -> list[str]:
    parts = path.split("/")[:-1]
    return ["/".join(parts[:index]) + "/" for index in range(1, len(parts) + 1)]


def parent_for(directory: str) -> str:
    parts = directory.rstrip("/").split("/")
    if len(parts) <= 1:
        return ""
    return "/".join(parts[:-1]) + "/"


def name_for(directory: str) -> str:
    return directory.rstrip("/").split("/")[-1]


def build_tree() -> dict:
    repo_sitemap = load_json(DOCS_REPO_SITEMAP)
    access_map = load_json(DOCS_ACCESS_MAP)
    public_sitemap = load_json(REPO_ROOT / "frontend" / "public" / "aureon_repo_sitemap.json")
    tracked_paths = git_ls_files()
    zones = public_sitemap.get("zones", [])
    lookup = capability_map(access_map)

    file_counts: Counter[str] = Counter()
    direct_file_counts: Counter[str] = Counter()
    direct_file_samples: dict[str, list[str]] = defaultdict(list)
    children: dict[str, set[str]] = defaultdict(set)
    root_files: list[str] = []

    for path in tracked_paths:
        prefixes = directory_prefixes(path)
        if not prefixes:
            root_files.append(path)
            continue
        for prefix in prefixes:
            file_counts[prefix] += 1
        parent = prefixes[-1]
        direct_file_counts[parent] += 1
        if len(direct_file_samples[parent]) < 12:
            direct_file_samples[parent].append(path)
        for prefix in prefixes:
            children[parent_for(prefix)].add(prefix)

    directories = []
    category_counts: Counter[str] = Counter()
    zone_counts: Counter[str] = Counter()
    max_depth = 0

    for directory in sorted(file_counts, key=lambda item: item.lower()):
        category, role = category_for(directory)
        zone_id = zone_for(directory, zones)
        depth = directory.rstrip("/").count("/") + 1
        max_depth = max(max_depth, depth)
        category_counts[category] += 1
        zone_counts[zone_id] += 1
        directories.append(
            {
                "path": directory,
                "name": name_for(directory),
                "parent": parent_for(directory),
                "depth": depth,
                "category": category,
                "role": role,
                "zone_id": zone_id,
                "capability_ids": capabilities_for(directory, lookup),
                "file_count": file_counts[directory],
                "direct_file_count": direct_file_counts[directory],
                "child_directory_count": len(children.get(directory, set())),
                "child_directories": sorted(children.get(directory, set()), key=lambda item: item.lower()),
                "direct_file_samples": direct_file_samples.get(directory, []),
            }
        )

    top_level = [entry for entry in directories if entry["depth"] == 1]

    return {
        "name": "Aureon Repo Organization Tree",
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "source": "git ls-files",
        "generated_by": "scripts/validation/generate_repo_organization_tree.py",
        "docs_mirror": "docs/repo_organization_tree.json",
        "frontend_public_mirror": "frontend/public/aureon_repo_organization_tree.json",
        "tracked_file_count": len(tracked_paths),
        "directory_count": len(directories),
        "root_file_count": len(root_files),
        "max_depth": max_depth,
        "public_contract": {
            "paths_only": True,
            "contains_file_contents": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "top_level_directory_count": len(top_level),
            "root_file_count": len(root_files),
            "category_counts": dict(sorted(category_counts.items())),
            "zone_counts": dict(sorted(zone_counts.items())),
        },
        "root_files": sorted(root_files, key=lambda item: item.lower()),
        "top_level": top_level,
        "directories": directories,
        "frontend_navigation_tab": "#repo-map",
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    tree = build_tree()
    write_json(DOCS_TREE, tree)
    write_json(PUBLIC_TREE, tree)
    print(f"Wrote {DOCS_TREE.relative_to(REPO_ROOT)}")
    print(f"Wrote {PUBLIC_TREE.relative_to(REPO_ROOT)}")
    print(f"Mapped {tree['directory_count']} directories across {tree['tracked_file_count']} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
