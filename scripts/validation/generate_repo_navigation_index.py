"""Generate Aureon's repo-wide public navigation index from git metadata."""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"
DOCS_REPO_SITEMAP = REPO_ROOT / "docs" / "repo_sitemap.json"
DOCS_ACCESS_MAP = REPO_ROOT / "docs" / "end_user_access_map.json"
DOCS_INDEX = REPO_ROOT / "docs" / "repo_navigation_index.json"
PUBLIC_INDEX = REPO_ROOT / "frontend" / "public" / "aureon_repo_navigation_index.json"


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

ROOT_FILE_RULES = [
    (("README.md", "INDEX.md", "RUNNING.md", "QUICK_START.md", "CAPABILITIES.md", "SYSTEM_OVERVIEW.md", "DATA_FLOW.md"), "documentation", "Root documentation and orientation"),
    (("Dockerfile", "docker-compose.yml", "docker-compose.autonomous.yml", "app.yaml", "Procfile", "runtime.txt", "supervisord.conf"), "deployment", "Root deployment or process configuration"),
    (("requirements.txt", "package.json", "package-lock.json", "eslint.config.js"), "release", "Root dependency or build configuration"),
]

EXTENSION_KIND_RULES = {
    ".md": "markdown",
    ".mdx": "markdown",
    ".json": "json",
    ".toml": "config",
    ".yaml": "config",
    ".yml": "config",
    ".ini": "config",
    ".env": "config",
    ".txt": "text",
    ".csv": "data",
    ".tsv": "data",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript-react",
    ".js": "javascript",
    ".jsx": "javascript-react",
    ".css": "css",
    ".html": "html",
    ".cmd": "windows-command",
    ".ps1": "powershell",
    ".sh": "shell",
    ".sql": "sql",
    ".pdf": "pdf",
    ".docx": "word-document",
    ".xlsx": "spreadsheet",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".svg": "image",
    ".zip": "archive",
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


def category_for(path: str, top_level: str) -> tuple[str, str]:
    if "/" in path:
        return ROOT_CATEGORY_RULES.get(top_level, ("uncategorized", "Tracked repository path"))

    for names, category, role in ROOT_FILE_RULES:
        if path in names:
            return category, role

    extension = Path(path).suffix.lower()
    if extension in {".md", ".txt", ".pdf", ".docx"}:
        return "documentation", "Root document or evidence artifact"
    if extension in {".py", ".cmd", ".ps1", ".sh"}:
        return "operator tooling", "Root script or launcher"
    if extension in {".json", ".yaml", ".yml", ".toml"}:
        return "configuration", "Root configuration or manifest"
    if extension in {".zip"}:
        return "archive", "Root archive artifact"
    return "root artifact", "Tracked root-level artifact"


def kind_for(path: str) -> str:
    name = Path(path).name
    if "." not in name:
        return "file"
    return EXTENSION_KIND_RULES.get(Path(path).suffix.lower(), "file")


def zone_for(path: str, zones: list[dict]) -> str:
    for zone in zones:
        for prefix in zone.get("paths", []):
            normalized = prefix.rstrip("/")
            if path == normalized or path.startswith(f"{normalized}/"):
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
    for prefix, ids in lookup.items():
        normalized = prefix.rstrip("/")
        if path == normalized or path.startswith(f"{normalized}/"):
            capability_ids.update(ids)
    return sorted(capability_ids)


def build_index() -> dict:
    repo_sitemap = load_json(DOCS_REPO_SITEMAP)
    access_map = load_json(DOCS_ACCESS_MAP)
    tracked_paths = git_ls_files()
    zones = repo_sitemap.get("end_user_access", {})
    public_sitemap = load_json(REPO_ROOT / "frontend" / "public" / "aureon_repo_sitemap.json")
    zone_rows = public_sitemap.get("zones", [])
    capability_lookup = capability_map(access_map)

    entries = []
    category_counts: Counter[str] = Counter()
    top_level_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    zone_counts: Counter[str] = Counter()
    capability_counts: Counter[str] = Counter()

    for path in tracked_paths:
        top_level = top_level_for(path)
        category, role = category_for(path, top_level)
        extension = Path(path).suffix.lower() or "[none]"
        kind = kind_for(path)
        zone_id = zone_for(path, zone_rows)
        capability_ids = capabilities_for(path, capability_lookup)

        entry = {
            "path": path,
            "top_level": top_level,
            "zone_id": zone_id,
            "category": category,
            "role": role,
            "kind": kind,
            "extension": extension,
            "capability_ids": capability_ids,
        }
        entries.append(entry)
        category_counts[category] += 1
        top_level_counts[top_level] += 1
        extension_counts[extension] += 1
        zone_counts[zone_id] += 1
        for capability_id in capability_ids:
            capability_counts[capability_id] += 1

    top_level_summary = [
        {
            "path": f"{top_level}/" if any(item.startswith(f"{top_level}/") for item in tracked_paths) else top_level,
            "files": count,
            "category": category_for(f"{top_level}/__placeholder__", top_level)[0] if top_level in ROOT_CATEGORY_RULES else category_for(top_level, top_level)[0],
        }
        for top_level, count in sorted(top_level_counts.items(), key=lambda item: item[0].lower())
    ]

    return {
        "name": "Aureon Repo Navigation Index",
        "snapshot_date": SNAPSHOT_DATE,
        "source": "git ls-files",
        "generated_by": "scripts/validation/generate_repo_navigation_index.py",
        "docs_mirror": "docs/repo_navigation_index.json",
        "frontend_public_mirror": "frontend/public/aureon_repo_navigation_index.json",
        "tracked_file_count": len(tracked_paths),
        "entry_count": len(entries),
        "public_contract": {
            "paths_only": True,
            "contains_file_contents": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "top_level_count": len(top_level_counts),
            "category_counts": dict(sorted(category_counts.items())),
            "zone_counts": dict(sorted(zone_counts.items())),
            "capability_counts": dict(sorted(capability_counts.items())),
            "extension_counts": dict(sorted(extension_counts.items())),
        },
        "top_level": top_level_summary,
        "entries": entries,
        "sitemap_document": repo_sitemap.get("end_user_access", {}).get("document", "docs/END_USER_ACCESS_MAP.md"),
        "frontend_navigation_tab": zones.get("frontend_navigation_tab", "#repo-map"),
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    index = build_index()
    write_json(DOCS_INDEX, index)
    write_json(PUBLIC_INDEX, index)
    print(f"Wrote {DOCS_INDEX.relative_to(REPO_ROOT)}")
    print(f"Wrote {PUBLIC_INDEX.relative_to(REPO_ROOT)}")
    print(f"Indexed {index['entry_count']} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
