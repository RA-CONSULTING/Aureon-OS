"""Build a merge checklist for the staged AUREON MURGE package.

The ZIP is treated as an incoming subsystem bundle.  This audit does not copy
or overwrite production files; it publishes a merge map so the organism can
track what belongs where before any integration work touches live trading code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORTS_DIR = REPO_ROOT / "imports"
SOURCE_ZIP_CANDIDATES = [
    REPO_ROOT / "AUREON MURGE REQUIRED.zip",
    REPO_ROOT / "imports" / "AUREON MURGE REQUIRED.zip",
]

OUTPUT_FILES = [
    REPO_ROOT / "state" / "aureon_murge_merge_checklist_last_run.json",
    REPO_ROOT / "docs" / "audits" / "aureon_murge_merge_checklist.json",
    REPO_ROOT / "docs" / "audits" / "aureon_murge_merge_checklist.md",
    REPO_ROOT / "frontend" / "public" / "aureon_murge_merge_checklist.json",
]

COLLISION_PATHS = {"README.md", ".gitignore", "docs/SECURITY.md"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _latest_staging_dir() -> Optional[Path]:
    candidates = [
        p
        for p in IMPORTS_DIR.glob("aureon_murge_required_*")
        if p.is_dir()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _source_zip() -> Optional[Path]:
    for path in SOURCE_ZIP_CANDIDATES:
        if path.exists():
            return path
    return None


def _track_for(rel_path: str) -> Dict[str, str]:
    if rel_path in {"server.mjs", "index.html", "style.css", "package.json", "package-lock.json"}:
        return {
            "track_id": "web_app_provider_shell",
            "target_area": "isolated Node web/provider bridge",
            "recommended_target": "integrations/aureon_murge/web_app/",
            "relates_to": "Aureon brain provider, classroom observer UI, local vault memory, provider routing",
        }
    if rel_path.startswith("runtime/"):
        return {
            "track_id": "local_companion_runtime",
            "target_area": "local runtime and sandbox execution bridge",
            "recommended_target": "integrations/aureon_murge/runtime/",
            "relates_to": "terminal bridge, Docker sandbox, localhost runtime API, PTY/WebSocket execution",
        }
    if rel_path.startswith("desktop/"):
        return {
            "track_id": "desktop_runtime_shell",
            "target_area": "desktop experiment shell",
            "recommended_target": "integrations/aureon_murge/desktop/",
            "relates_to": "Electron runtime manager, local desktop controls, smoke checks",
        }
    if rel_path.startswith("workers/") or rel_path == "wrangler.jsonc":
        return {
            "track_id": "cloudflare_worker_surface",
            "target_area": "Cloudflare worker deployment surface",
            "recommended_target": "deploy/cloudflare/aureon_murge_worker/",
            "relates_to": "worker provider proxy, classroom memory, remote Aureon bridge, static asset delivery",
        }
    if rel_path.startswith("scripts/"):
        return {
            "track_id": "operator_scripts",
            "target_area": "operator scripts and setup commands",
            "recommended_target": "scripts/aureon_murge/",
            "relates_to": "health checks, Cloudflare setup, sandbox runtime setup, Aureon local brain launcher",
        }
    if rel_path.startswith("docs/") or rel_path.endswith(".md"):
        return {
            "track_id": "documentation_and_runbooks",
            "target_area": "documentation import lane",
            "recommended_target": "docs/imported/aureon_murge/",
            "relates_to": "architecture, environment, security, storage, desktop rollout, memory pipeline",
        }
    if rel_path.startswith("shared/") or rel_path.startswith("frontend/"):
        return {
            "track_id": "shared_frontend_contracts",
            "target_area": "shared contracts and frontend notes",
            "recommended_target": "frontend/src/aureon_murge_contracts/",
            "relates_to": "future TypeScript contracts, frontend migration notes, UI model alignment",
        }
    return {
        "track_id": "miscellaneous_assets",
        "target_area": "manual review",
        "recommended_target": "imports/aureon_murge_required_review/",
        "relates_to": "unclassified incoming asset",
    }


def _merge_action(rel_path: str, exists: bool, same_hash: bool, track_id: str) -> str:
    if exists and same_hash:
        return "already_present_no_action"
    if exists:
        return "collision_review_required"
    if track_id in {"web_app_provider_shell", "local_companion_runtime", "desktop_runtime_shell", "cloudflare_worker_surface"}:
        return "stage_as_isolated_subsystem_then_adapter"
    if track_id == "operator_scripts":
        return "import_to_script_namespace_then_shellcheck_or_windows_adapter"
    if track_id == "documentation_and_runbooks":
        return "import_docs_then_distill_into_current_runbooks"
    return "stage_then_review"


def _file_rows(staging_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in sorted(p for p in staging_dir.rglob("*") if p.is_file()):
        rel_path = _rel(path, staging_dir)
        target = REPO_ROOT / rel_path
        exists = target.exists()
        incoming_hash = _sha256(path)
        target_hash = _sha256(target) if exists and target.is_file() else ""
        same_hash = bool(exists and incoming_hash == target_hash)
        track = _track_for(rel_path)
        rows.append(
            {
                "path": rel_path,
                "size_bytes": path.stat().st_size,
                "track_id": track["track_id"],
                "target_area": track["target_area"],
                "recommended_target": track["recommended_target"],
                "relates_to": track["relates_to"],
                "exists_in_repo": exists,
                "same_hash": same_hash,
                "collision": exists and not same_hash,
                "collision_reason": "incoming file differs from current repo path" if exists and not same_hash else "",
                "merge_action": _merge_action(rel_path, exists, same_hash, track["track_id"]),
                "incoming_sha256": incoming_hash,
                "repo_sha256": target_hash,
            }
        )
    return rows


def _track_rows(file_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in file_rows:
        track_id = str(row["track_id"])
        item = grouped.setdefault(
            track_id,
            {
                "track_id": track_id,
                "target_area": row["target_area"],
                "recommended_target": row["recommended_target"],
                "relates_to": row["relates_to"],
                "file_count": 0,
                "collision_count": 0,
                "sample_files": [],
            },
        )
        item["file_count"] += 1
        if row.get("collision"):
            item["collision_count"] += 1
        if len(item["sample_files"]) < 8:
            item["sample_files"].append(row["path"])

    priority = {
        "documentation_and_runbooks": "P0",
        "local_companion_runtime": "P0",
        "web_app_provider_shell": "P1",
        "operator_scripts": "P1",
        "cloudflare_worker_surface": "P2",
        "desktop_runtime_shell": "P2",
        "shared_frontend_contracts": "P2",
        "miscellaneous_assets": "P3",
    }
    actions = {
        "documentation_and_runbooks": "Import into docs/imported first; only then update README/RUNNING/SECURITY with distilled Aureon-specific notes.",
        "local_companion_runtime": "Mount as a separate localhost runtime candidate and compare against existing terminal-state/ThoughtBus runtime before enabling any execution route.",
        "web_app_provider_shell": "Do not overwrite current frontend/root server. Extract provider and observer concepts into adapters or a separate local service.",
        "operator_scripts": "Move into scripts/aureon_murge and convert Linux-only bash paths/env assumptions for this Windows repo before use.",
        "cloudflare_worker_surface": "Keep deployment code isolated until secrets, wrangler config, and route authority are reviewed.",
        "desktop_runtime_shell": "Keep Electron shell experimental until it can launch the current Aureon runtime without bypassing gates.",
        "shared_frontend_contracts": "Use as future contracts/reference only until TypeScript models are mapped to current frontend data shapes.",
        "miscellaneous_assets": "Manual inspect before merge.",
    }
    rows = []
    for track_id, item in sorted(grouped.items(), key=lambda kv: (priority.get(kv[0], "P9"), kv[0])):
        item["priority"] = priority.get(track_id, "P3")
        item["required_action"] = actions.get(track_id, "Manual review before merge.")
        item["status"] = "blocked_by_collision_review" if item["collision_count"] else "ready_for_staged_import"
        rows.append(item)
    return rows


def _checklist(track_rows: Iterable[Dict[str, Any]], collision_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tasks: List[Dict[str, Any]] = [
        {
            "id": "murge-001",
            "status": "done",
            "task": "Extract ZIP to isolated imports staging directory.",
            "acceptance": "No archive path traversal; no production files overwritten.",
        },
        {
            "id": "murge-002",
            "status": "done",
            "task": "Inventory files, hashes, collisions, and subsystem ownership.",
            "acceptance": "Every file has a track_id, target area, relation, and recommended target.",
        },
        {
            "id": "murge-003",
            "status": "pending",
            "task": "Resolve direct path collisions.",
            "acceptance": "README.md, .gitignore, and docs/SECURITY.md are manually merged rather than overwritten.",
        },
        {
            "id": "murge-004",
            "status": "pending",
            "task": "Create isolated integration namespaces.",
            "acceptance": "Runtime, desktop, worker, web app, scripts, and docs land under dedicated Aureon MURGE paths first.",
        },
        {
            "id": "murge-005",
            "status": "pending",
            "task": "Wire safe runtime concepts into current Aureon organism.",
            "acceptance": "Terminal/sandbox/provider ideas are exposed through current runtime gates, ThoughtBus, and audit artifacts.",
        },
        {
            "id": "murge-006",
            "status": "pending",
            "task": "Verify syntax and platform compatibility.",
            "acceptance": "Node files, Python scripts, shell scripts, and frontend integration pass checks on this Windows workspace.",
        },
        {
            "id": "murge-007",
            "status": "pending",
            "task": "Update public UI evidence if a subsystem is promoted.",
            "acceptance": "Trading/Live Ops panels show new subsystem health without adding hidden mutation controls.",
        },
    ]
    if any(row.get("collision") for row in collision_rows):
        tasks.append(
            {
                "id": "murge-008",
                "status": "blocked",
                "task": "Prevent direct overwrite of colliding root files.",
                "acceptance": "Collisions stay blocked until reviewed and manually reconciled.",
            }
        )
    for track in track_rows:
        tasks.append(
            {
                "id": f"track-{track['track_id']}",
                "status": "pending" if track["status"] == "ready_for_staged_import" else "blocked",
                "task": f"Merge track {track['track_id']} into {track['recommended_target']}",
                "acceptance": track["required_action"],
            }
        )
    return tasks


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Aureon MURGE Merge Checklist",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Source zip: `{report['source_zip'] or 'not found'}`",
        f"- Staging directory: `{report['staging_dir']}`",
        f"- Files: `{report['summary']['file_count']}`",
        f"- Tracks: `{report['summary']['track_count']}`",
        f"- Collisions: `{report['summary']['collision_count']}`",
        f"- Status: `{report['status']}`",
        "",
        "## Merge Tracks",
        "",
    ]
    for row in report["merge_tracks"]:
        lines.extend(
            [
                f"### {row['priority']} {row['track_id']}",
                f"- Target area: {row['target_area']}",
                f"- Recommended target: `{row['recommended_target']}`",
                f"- Relates to: {row['relates_to']}",
                f"- Files: `{row['file_count']}`; collisions: `{row['collision_count']}`",
                f"- Required action: {row['required_action']}",
                f"- Sample files: {', '.join(f'`{p}`' for p in row['sample_files'])}",
                "",
            ]
        )
    lines.extend(["## Direct Collisions", ""])
    if report["collision_rows"]:
        for row in report["collision_rows"]:
            lines.append(f"- `{row['path']}` -> {row['merge_action']} ({row['collision_reason']})")
    else:
        lines.append("- No direct path collisions.")
    lines.extend(["", "## Checklist", ""])
    for task in report["merge_checklist"]:
        lines.append(f"- [{task['status']}] `{task['id']}` {task['task']} Acceptance: {task['acceptance']}")
    lines.extend(["", "## Rule", "", "Do not overwrite live Aureon runtime, trading, security, or README files from this package until the collision and adapter tracks are explicitly cleared."])
    return "\n".join(lines) + "\n"


def build_report(staging_dir: Optional[Path] = None) -> Dict[str, Any]:
    staging = staging_dir or _latest_staging_dir()
    if not staging or not staging.exists():
        return {
            "schema_version": "aureon-murge-merge-checklist-v1",
            "status": "murge_staging_missing",
            "generated_at": _utc_now(),
            "source_zip": str(_source_zip() or ""),
            "staging_dir": "",
            "summary": {"file_count": 0, "track_count": 0, "collision_count": 0},
            "merge_tracks": [],
            "file_rows": [],
            "collision_rows": [],
            "merge_checklist": [],
            "manual_boundaries": ["no production file overwrite", "no runtime activation", "no credential read"],
        }

    files = _file_rows(staging)
    tracks = _track_rows(files)
    collisions = [row for row in files if row.get("collision")]
    checklist = _checklist(tracks, collisions)
    status = "murge_merge_collision_review_required" if collisions else "murge_merge_staged_ready"
    return {
        "schema_version": "aureon-murge-merge-checklist-v1",
        "status": status,
        "generated_at": _utc_now(),
        "source_zip": str(_source_zip() or ""),
        "staging_dir": str(staging),
        "summary": {
            "file_count": len(files),
            "track_count": len(tracks),
            "collision_count": len(collisions),
            "ready_track_count": sum(1 for row in tracks if row.get("status") == "ready_for_staged_import"),
            "blocked_track_count": sum(1 for row in tracks if row.get("status") != "ready_for_staged_import"),
            "checklist_count": len(checklist),
        },
        "merge_tracks": tracks,
        "file_rows": files,
        "collision_rows": collisions,
        "merge_checklist": checklist,
        "manual_boundaries": [
            "no production file overwrite from ZIP",
            "no runtime or desktop service activation from checklist generation",
            "no credential read or secret migration",
            "Linux/bash scripts require Windows compatibility review before use",
            "Cloudflare worker routes remain isolated until secrets and deployment authority are reviewed",
        ],
        "output_files": [str(path) for path in OUTPUT_FILES],
    }


def write_report(report: Dict[str, Any]) -> Dict[str, Any]:
    writes: List[Dict[str, Any]] = []
    for path in OUTPUT_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".md":
            content = _markdown(report)
            path.write_text(content, encoding="utf-8")
            size = len(content.encode("utf-8"))
        else:
            content = json.dumps(report, indent=2, sort_keys=True)
            path.write_text(content + "\n", encoding="utf-8")
            size = len((content + "\n").encode("utf-8"))
        writes.append({"path": str(path), "bytes": size})
    return {"evidence_writes": writes}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Aureon MURGE merge checklist artifacts.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    parser.add_argument("--staging-dir", default="", help="Explicit extracted staging directory.")
    args = parser.parse_args(argv)
    staging_dir = Path(args.staging_dir) if args.staging_dir else None
    report = build_report(staging_dir)
    report["write_info"] = write_report(report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") != "murge_staging_missing" else 1


if __name__ == "__main__":
    raise SystemExit(main())
