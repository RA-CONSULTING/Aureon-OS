"""Aureon MURGE unity bridge.

This audit promotes the extracted MURGE package from "found files" into an
explicit Aureon unity map: docs, runtime, desktop, workers, scripts, and web
provider shell are all tracked as organism reach surfaces.  It still avoids
blind activation; a surface is unified only when staged in an isolated namespace
and mapped to an adapter path.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]

CHECKLIST_PUBLIC = REPO_ROOT / "frontend" / "public" / "aureon_murge_merge_checklist.json"
OUTPUT_FILES = [
    REPO_ROOT / "state" / "aureon_murge_unity_bridge_last_run.json",
    REPO_ROOT / "docs" / "audits" / "aureon_murge_unity_bridge.json",
    REPO_ROOT / "docs" / "audits" / "aureon_murge_unity_bridge.md",
    REPO_ROOT / "frontend" / "public" / "aureon_murge_unity_bridge.json",
]


TRACKS = [
    {
        "track_id": "documentation_and_runbooks",
        "priority": "P0",
        "target": "docs/imported/aureon_murge",
        "required_files": ["README.md", "AUREON_BRAIN_INTEGRATION.md", "docs/SECURITY.md"],
        "organism_relation": "Aureon public face, operator memory, security/runbook continuity",
        "adapter": "docs/runbook_distillation + frontend evidence freshness",
    },
    {
        "track_id": "local_companion_runtime",
        "priority": "P0",
        "target": "integrations/aureon_murge/runtime",
        "required_files": ["server.mjs", "Dockerfile"],
        "organism_relation": "local terminal/sandbox reach, execution runtime, PTY/WebSocket bridge",
        "adapter": "runtime bridge must report into terminal-state, ThoughtBus, and Live Signal Fabric before activation",
    },
    {
        "track_id": "web_app_provider_shell",
        "priority": "P1",
        "target": "integrations/aureon_murge/web_app",
        "required_files": ["server.mjs", "index.html", "style.css", "package.json"],
        "organism_relation": "Aureon face/provider UI, classroom observer, vault memory bridge",
        "adapter": "extract provider/observer concepts into current React console or run as separate local service",
    },
    {
        "track_id": "operator_scripts",
        "priority": "P1",
        "target": "scripts/aureon_murge",
        "required_files": ["aureon_cli.mjs", "start_aureon_brain_local.sh", "world_data_bridge.py"],
        "organism_relation": "operator bootstraps, health checks, cloud/runtime setup",
        "adapter": "convert Linux scripts to Windows-safe launchers and register safe checks only",
    },
    {
        "track_id": "shared_frontend_contracts",
        "priority": "P2",
        "target": "integrations/aureon_murge/shared",
        "required_files": ["README.md"],
        "organism_relation": "shared contracts, frontend migration notes, UI model alignment",
        "adapter": "map contracts into current TypeScript data shapes before importing",
    },
    {
        "track_id": "cloudflare_worker_surface",
        "priority": "P2",
        "target": "deploy/cloudflare/aureon_murge_worker",
        "required_files": ["index.mjs", "wrangler.jsonc"],
        "organism_relation": "extended web reach, worker proxy, remote observer memory",
        "adapter": "deploy only after wrangler source-of-truth, assets routing, and secrets review",
    },
    {
        "track_id": "desktop_runtime_shell",
        "priority": "P2",
        "target": "integrations/aureon_murge/desktop",
        "required_files": ["main.cjs", "preload.cjs", "runtime-manager.cjs", "package.json"],
        "organism_relation": "desktop face and local runtime manager",
        "adapter": "Electron shell must pass security checklist and call existing runtime gates",
    },
]


ONLINE_REQUIREMENTS = [
    {
        "surface": "express_local_server",
        "source": "https://expressjs.com/en/advanced/best-practice-security.html",
        "requirement": "Production Express surfaces require dependency hygiene, TLS when external, input validation, reduced fingerprinting, secure cookies, and brute-force protection.",
        "unity_gate": "local-only or reverse-proxy gated before exposure",
    },
    {
        "surface": "electron_desktop_shell",
        "source": "https://www.electronjs.org/docs/latest/tutorial/security",
        "requirement": "Electron security checklist must be applied before trusting renderer/Node integration or remote content.",
        "unity_gate": "desktop shell remains experimental until context isolation and command boundaries are verified",
    },
    {
        "surface": "cloudflare_worker",
        "source": "https://developers.cloudflare.com/workers/wrangler/configuration/",
        "requirement": "Wrangler config should be treated as source of truth for Worker configuration and static asset routing.",
        "unity_gate": "worker stays isolated until wrangler assets/secrets/routes are reviewed",
    },
    {
        "surface": "docker_sandbox_runtime",
        "source": "https://docs.docker.com/engine/security/",
        "requirement": "Docker runtime should use least privilege; remove capabilities except those explicitly required.",
        "unity_gate": "sandbox bridge cannot bypass current Aureon runtime safety gates",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _track_row(track: Dict[str, Any]) -> Dict[str, Any]:
    root = REPO_ROOT / str(track["target"])
    missing = [name for name in track["required_files"] if not (root / name).exists()]
    file_count = _count_files(root)
    staged = root.exists() and not missing and file_count > 0
    return {
        **track,
        "path": str(root),
        "file_count": file_count,
        "required_file_count": len(track["required_files"]),
        "missing_files": missing,
        "staged": staged,
        "status": "unity_staged" if staged else "unity_missing_required_files",
        "next_action": "wire_adapter_and_stress_test" if staged else "copy_or_recover_required_files_from_staging",
    }


def _collision_rows(checklist: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = checklist.get("collision_rows")
    return rows if isinstance(rows, list) else []


def _adapter_rows(track_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mapping = {
        "documentation_and_runbooks": ["docs/audits", "frontend/public", "operator brief"],
        "local_companion_runtime": ["terminal-state", "runtime observer", "ThoughtBus", "Live Signal Fabric"],
        "web_app_provider_shell": ["Aureon console", "vault voice", "observer/classroom panel"],
        "operator_scripts": ["wake launcher", "health checks", "capability switchboard"],
        "shared_frontend_contracts": ["frontend data models", "provider contracts", "console adapters"],
        "cloudflare_worker_surface": ["deploy/cloudflare", "remote worker bridge", "provider proxy"],
        "desktop_runtime_shell": ["desktop app", "runtime manager", "local host controls"],
    }
    rows: List[Dict[str, Any]] = []
    for row in track_rows:
        surfaces = mapping.get(str(row["track_id"]), [])
        rows.append(
            {
                "track_id": row["track_id"],
                "status": "adapter_ready_to_design" if row["staged"] else "adapter_blocked_missing_files",
                "target_surfaces": surfaces,
                "adapter": row["adapter"],
                "organism_relation": row["organism_relation"],
                "next_action": row["next_action"],
            }
        )
    return rows


def build_unity_bridge() -> Dict[str, Any]:
    checklist = _read_json(CHECKLIST_PUBLIC)
    if not _collision_rows(checklist):
        # A missing/empty published checklist is NOT evidence of zero collisions —
        # rebuild the merge map live from the staged MURGE package so collisions
        # stay visible instead of failing open to "nothing to review".
        try:
            from aureon.autonomous.aureon_murge_merge_checklist import build_report

            live = build_report()
            if isinstance(live, dict) and _collision_rows(live):
                checklist = live
        except Exception:  # noqa: BLE001 — no staging package → keep the (empty) artifact view
            pass
    track_rows = [_track_row(track) for track in TRACKS]
    collisions = _collision_rows(checklist)
    staged_count = sum(1 for row in track_rows if row["staged"])
    missing_count = len(track_rows) - staged_count
    collision_count = len(collisions)
    adapter_rows = _adapter_rows(track_rows)
    blockers: List[str] = []
    if missing_count:
        blockers.append("unity_track_missing_files")
    if collision_count:
        blockers.append("collision_review_required")
    if any(row["track_id"] == "operator_scripts" for row in track_rows):
        blockers.append("windows_shell_compatibility_review_required")
    status = "aureon_unity_staged_collision_review" if blockers else "aureon_unity_wired_ready_for_adapters"
    return {
        "schema_version": "aureon-murge-unity-bridge-v1",
        "status": status,
        "generated_at": _utc_now(),
        "mode": "unity_staged_no_blind_activation",
        "summary": {
            "track_count": len(track_rows),
            "staged_track_count": staged_count,
            "missing_track_count": missing_count,
            "adapter_row_count": len(adapter_rows),
            "collision_count": collision_count,
            "online_requirement_count": len(ONLINE_REQUIREMENTS),
            "unity_ready": not blockers,
            "hidden_activation": False,
        },
        "unity_track_rows": track_rows,
        "organism_adapter_rows": adapter_rows,
        "collision_rows": collisions,
        "online_requirement_baseline": ONLINE_REQUIREMENTS,
        "next_unity_actions": [
            {
                "id": "unity-001",
                "priority": "P0",
                "action": "Resolve README, .gitignore, and docs/SECURITY.md collisions by distilling, not overwriting.",
            },
            {
                "id": "unity-002",
                "priority": "P0",
                "action": "Design the local companion runtime adapter so terminal/sandbox events report to terminal-state, ThoughtBus, and Live Signal Fabric.",
            },
            {
                "id": "unity-003",
                "priority": "P1",
                "action": "Extract the Aureon brain/provider and observer UI ideas into the current React console as a face/reach panel.",
            },
            {
                "id": "unity-004",
                "priority": "P1",
                "action": "Convert Linux-only scripts into Windows-safe operator commands before running them.",
            },
            {
                "id": "unity-005",
                "priority": "P2",
                "action": "Keep Cloudflare and desktop surfaces isolated until route, secret, and Electron security gates pass.",
            },
            {
                "id": "unity-006",
                "priority": "P2",
                "action": "Map shared/frontend contract notes into current TypeScript models before importing them into live panels.",
            },
        ],
        "blockers": blockers,
        "manual_boundaries": [
            "unity means staged and visible to the organism, not blind overwrite",
            "no hidden runtime activation",
            "no credential migration",
            "no trading gate bypass",
            "all new execution surfaces must report through current safety gates before use",
        ],
        "source_paths": {
            "merge_checklist": "frontend/public/aureon_murge_merge_checklist.json",
            "docs": "docs/imported/aureon_murge",
            "runtime": "integrations/aureon_murge/runtime",
            "desktop": "integrations/aureon_murge/desktop",
            "web_app": "integrations/aureon_murge/web_app",
            "worker": "deploy/cloudflare/aureon_murge_worker",
            "scripts": "scripts/aureon_murge",
            "shared": "integrations/aureon_murge/shared",
        },
        "output_files": [str(path) for path in OUTPUT_FILES],
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Aureon MURGE Unity Bridge",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Status: `{report['status']}`",
        f"- Staged tracks: `{report['summary']['staged_track_count']}/{report['summary']['track_count']}`",
        f"- Collisions: `{report['summary']['collision_count']}`",
        "",
        "## Unity Tracks",
        "",
    ]
    for row in report["unity_track_rows"]:
        lines.extend(
            [
                f"### {row['priority']} {row['track_id']}",
                f"- Status: `{row['status']}`",
                f"- Path: `{row['path']}`",
                f"- Files: `{row['file_count']}`",
                f"- Relates to: {row['organism_relation']}",
                f"- Adapter: {row['adapter']}",
                f"- Next: {row['next_action']}",
                "",
            ]
        )
    lines.extend(["## Next Unity Actions", ""])
    for row in report["next_unity_actions"]:
        lines.append(f"- `{row['priority']}` `{row['id']}` {row['action']}")
    lines.extend(["", "## Online Requirement Baseline", ""])
    for row in report["online_requirement_baseline"]:
        lines.append(f"- `{row['surface']}`: {row['requirement']} Source: {row['source']}")
    if report["blockers"]:
        lines.extend(["", "## Blockers", ""])
        for blocker in report["blockers"]:
            lines.append(f"- `{blocker}`")
    return "\n".join(lines) + "\n"


def write_unity_bridge(report: Dict[str, Any]) -> Dict[str, Any]:
    writes: List[Dict[str, Any]] = []
    for path in OUTPUT_FILES:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".md":
            content = _markdown(report)
            path.write_text(content, encoding="utf-8")
            size = len(content.encode("utf-8"))
        else:
            content = json.dumps(report, indent=2, sort_keys=True) + "\n"
            path.write_text(content, encoding="utf-8")
            size = len(content.encode("utf-8"))
        writes.append({"path": str(path), "bytes": size})
    return {"evidence_writes": writes}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Publish Aureon MURGE unity bridge evidence.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_unity_bridge()
    report["write_info"] = write_unity_bridge(report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
