"""Generate Aureon's public capability registry from CAPABILITIES.md."""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DATE = "2026-07-13"
SOURCE_DOC = REPO_ROOT / "CAPABILITIES.md"
DOCS_NAVIGATION_INDEX = REPO_ROOT / "docs" / "repo_navigation_index.json"
DOCS_SYSTEM_INTEGRATION = REPO_ROOT / "docs" / "system_integration_map.json"
DOCS_MANIFEST = REPO_ROOT / "docs" / "capability_registry.json"
PUBLIC_MANIFEST = REPO_ROOT / "frontend" / "public" / "aureon_capability_registry.json"

RUNTIME_PREFIXES = ("http://", "https://", "/api/", "POST http://")
GENERATED_REF_PREFIXES = ("state/", "docs/audits/", "frontend/public/", "ws_cache/")
SYMBOL_SEARCH_ROOTS = ("aureon", "frontend/src", "scripts", "Kings_Accounting_Suite", "tests")
SYMBOL_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs"}

ACCESS_ROUTE_RULES = [
    ("accounting_filing_support", ("accounting", "hmrc", "filing", "statutory")),
    ("coding_skills", ("code", "coding", "desktop", "director", "llm", "skill", "handoff")),
    ("deployment", ("deploy", "production", "docker", "cloudflare", "digitalocean")),
    ("local_runtime", ("runtime", "supervision", "launcher", "supervisor", "recovery", "resilience", "wake-up")),
    ("operator_console", ("console", "frontend", "dashboard")),
    ("research_evidence", ("hnc", "auris", "research", "cognitive", "harmonic", "evidence", "data ocean")),
    ("saas_integration", ("saas", "security", "audit", "supabase", "frontend surfaces")),
    ("trading_readiness", ("exchange", "trading", "market", "kraken", "binance", "alpaca", "capital", "portfolio", "order")),
    ("validation", ("self-audit", "readiness", "validation", "capability matrix", "checklist")),
]


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


def markdown_section(markdown: str, heading: str) -> str:
    start = markdown.find(heading)
    if start == -1:
        return ""
    next_heading = markdown.find("\n## ", start + len(heading))
    return markdown[start:] if next_heading == -1 else markdown[start:next_heading]


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip().replace("\\|", "|") for cell in line.strip().strip("|").split("|")]


def parse_capability_table() -> list[dict]:
    section = markdown_section(SOURCE_DOC.read_text(encoding="utf-8"), "## Capability Table")
    rows: list[dict] = []
    for line in section.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = split_markdown_row(line)
        if len(cells) != 3 or cells[0] == "Capability":
            continue
        rows.append(
            {
                "label": cells[0],
                "description": cells[1],
                "surface_text": cells[2],
            }
        )
    return rows


def capability_id(label: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return cleaned or "capability"


def surface_refs(surface_text: str) -> list[str]:
    refs = re.findall(r"`([^`]+)`", surface_text)
    cleaned: list[str] = []
    for ref in refs:
        for part in ref.split(","):
            value = part.strip()
            if value and value not in cleaned:
                cleaned.append(value)
    return cleaned


def normalize_ref(ref: str) -> str:
    normalized = ref.split("#", 1)[0].strip().lstrip("/")
    if " " in normalized:
        command_target = normalized.split()[0].strip()
        if "/" in command_target and Path(command_target).suffix:
            return command_target.lstrip("/")
    return normalized


def is_generated_ref(ref: str) -> bool:
    normalized = normalize_ref(ref)
    return normalized.startswith(GENERATED_REF_PREFIXES)


def is_symbol_like(ref: str) -> bool:
    normalized = ref.strip()
    if "/" in normalized or normalized.startswith((".", "-")):
        return False
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", normalized))


def symbol_terms(ref: str) -> list[str]:
    normalized = ref.strip()
    terms = [normalized]
    if "." in normalized:
        terms.append(normalized.rsplit(".", 1)[-1])
    return [term for index, term in enumerate(terms) if term and term not in terms[:index]]


def find_symbol_paths(ref: str, tracked_paths: set[str]) -> list[str]:
    if not is_symbol_like(ref):
        return []

    matches: list[str] = []
    for term in symbol_terms(ref):
        result = subprocess.run(
            ["git", "grep", "-l", term, "--", *SYMBOL_SEARCH_ROOTS],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode not in (0, 1):
            continue
        for raw_path in result.stdout.splitlines():
            path = raw_path.strip().replace("\\", "/")
            if path not in tracked_paths:
                continue
            if Path(path).suffix not in SYMBOL_SOURCE_EXTENSIONS:
                continue
            if path not in matches:
                matches.append(path)

    def priority(path: str) -> tuple[int, str]:
        if path.startswith("aureon/"):
            return (0, path)
        if path.startswith("frontend/src/"):
            return (1, path)
        if path.startswith("scripts/"):
            return (2, path)
        if path.startswith("Kings_Accounting_Suite/"):
            return (3, path)
        if path.startswith("tests/"):
            return (4, path)
        return (5, path)

    return sorted(matches, key=priority)[:8]


def resolve_ref(ref: str, tracked_paths: list[str], basename_lookup: dict[str, list[str]]) -> tuple[list[str], bool, bool, bool]:
    if ref.startswith(RUNTIME_PREFIXES) or ref.startswith("/api/") or ref.startswith("POST "):
        return [], True, False, False

    normalized = normalize_ref(ref)
    if not normalized:
        return [], True, False, False

    if is_generated_ref(ref):
        return [], False, True, False

    if normalized in tracked_paths:
        return [normalized], False, False, False

    if normalized.endswith("/") and any(path.startswith(normalized) for path in tracked_paths):
        return [normalized], False, False, False

    basename = Path(normalized).name
    matches = basename_lookup.get(basename, [])
    if matches:
        return matches[:8], False, False, False

    if "/" not in normalized:
        partial = [path for path in tracked_paths if Path(path).stem == normalized or normalized in Path(path).stem]
        if partial:
            return partial[:8], False, False, False

    return [], False, False, is_symbol_like(ref)


def access_routes_for(label: str, description: str, refs: list[str]) -> list[str]:
    haystack = " ".join([label, description, *refs]).lower()
    route_ids = [route_id for route_id, terms in ACCESS_ROUTE_RULES if any(term in haystack for term in terms)]
    return sorted(set(route_ids)) or ["repo_navigation"]


def system_paths_for(paths: list[str], system_paths: set[str]) -> list[str]:
    systems: set[str] = set()
    for path in paths:
        if "/" not in path:
            systems.add("root/")
            continue
        top = path.split("/", 1)[0] + "/"
        if top in system_paths:
            systems.add(top)
    return sorted(systems)


def build_manifest() -> dict:
    tracked_paths = git_ls_files()
    tracked_set = set(tracked_paths)
    basename_lookup: dict[str, list[str]] = {}
    for path in tracked_paths:
        basename_lookup.setdefault(Path(path).name, []).append(path)

    navigation_index = load_json(DOCS_NAVIGATION_INDEX)
    system_map = load_json(DOCS_SYSTEM_INTEGRATION)
    system_paths = {system["path"] for system in system_map.get("systems", [])}
    capabilities = []
    resolved_ref_count = 0
    runtime_ref_count = 0
    generated_ref_count = 0
    command_ref_count = 0
    code_symbol_ref_count = 0
    unresolved_ref_count = 0
    route_counts: Counter[str] = Counter()
    system_counts: Counter[str] = Counter()

    for row in parse_capability_table():
        refs = surface_refs(row["surface_text"])
        resolved_paths: list[str] = []
        runtime_refs: list[str] = []
        generated_refs: list[str] = []
        command_refs: list[str] = []
        code_symbol_refs: list[dict] = []
        unresolved_refs: list[str] = []

        for ref in refs:
            matches, is_runtime, is_generated, may_be_symbol = resolve_ref(ref, tracked_paths, basename_lookup)
            if is_runtime:
                runtime_refs.append(ref)
                runtime_ref_count += 1
            elif is_generated:
                generated_refs.append(ref)
                generated_ref_count += 1
            elif matches:
                resolved_paths.extend(path for path in matches if path not in resolved_paths)
                resolved_ref_count += 1
                if normalize_ref(ref) != ref.split("#", 1)[0].strip().lstrip("/"):
                    command_refs.append(ref)
                    command_ref_count += 1
            elif may_be_symbol:
                symbol_paths = find_symbol_paths(ref, tracked_set)
                if symbol_paths:
                    code_symbol_refs.append({"ref": ref, "paths": symbol_paths})
                    code_symbol_ref_count += 1
                    for path in symbol_paths:
                        if path not in resolved_paths:
                            resolved_paths.append(path)
                    resolved_ref_count += 1
                else:
                    unresolved_refs.append(ref)
                    unresolved_ref_count += 1
            else:
                unresolved_refs.append(ref)
                unresolved_ref_count += 1

        systems = system_paths_for(resolved_paths, system_paths)
        routes = access_routes_for(row["label"], row["description"], refs)
        for route in routes:
            route_counts[route] += 1
        for system in systems:
            system_counts[system] += 1

        capabilities.append(
            {
                "id": capability_id(row["label"]),
                "label": row["label"],
                "description": row["description"],
                "source_document": "CAPABILITIES.md",
                "surface_refs": refs,
                "resolved_paths": resolved_paths[:20],
                "runtime_refs": runtime_refs,
                "generated_refs": generated_refs,
                "command_refs": command_refs,
                "code_symbol_refs": code_symbol_refs,
                "unresolved_refs": unresolved_refs,
                "system_paths": systems,
                "access_route_ids": routes,
                "public_artifacts": [
                    path
                    for path in [*resolved_paths, *generated_refs]
                    if path.startswith("frontend/public/") or path.startswith("docs/audits/")
                ],
            }
        )

    return {
        "name": "Aureon Capability Registry",
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/validation/generate_capability_registry.py",
        "docs_mirror": "docs/capability_registry.json",
        "frontend_public_mirror": "frontend/public/aureon_capability_registry.json",
        "source_documents": [
            "CAPABILITIES.md",
            "docs/repo_navigation_index.json",
            "docs/system_integration_map.json",
        ],
        "public_contract": {
            "contains_file_contents": False,
            "contains_secrets": False,
            "contains_private_runtime_state": False,
            "contains_customer_data": False,
        },
        "summary": {
            "tracked_file_count": len(tracked_set),
            "capability_count": len(capabilities),
            "resolved_surface_ref_count": resolved_ref_count,
            "runtime_surface_ref_count": runtime_ref_count,
            "generated_artifact_ref_count": generated_ref_count,
            "command_surface_ref_count": command_ref_count,
            "code_symbol_ref_count": code_symbol_ref_count,
            "unresolved_surface_ref_count": unresolved_ref_count,
            "access_route_count": len(route_counts),
            "system_count": len(system_counts),
            "navigation_index_entries": navigation_index.get("entry_count", 0),
        },
        "access_route_counts": dict(sorted(route_counts.items())),
        "system_counts": dict(sorted(system_counts.items())),
        "capabilities": capabilities,
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
        "Registered "
        f"{manifest['summary']['capability_count']} capabilities with "
        f"{manifest['summary']['resolved_surface_ref_count']} resolved surface refs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
