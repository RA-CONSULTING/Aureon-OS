#!/usr/bin/env python3
"""
Publish the Antarctic research -> Seer/Lyra unity bridge evidence.

This is a context/evidence bridge, not a blocker audit.  It records what
was wired, which research assets were found, and how the research map flows
into Seer, Lyra, and the Probability Nexus.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from aureon.wisdom.antarctic_research_bridge import build_research_context

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = Path("state/aureon_antarctic_research_unity_bridge_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_antarctic_research_unity_bridge.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_antarctic_research_unity_bridge.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_antarctic_research_unity_bridge.json")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path)


def _exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


def _wiring_row(system: str, file_path: str, relationship: str) -> Dict[str, Any]:
    return {
        "system": system,
        "path": file_path,
        "present": _exists(file_path),
        "relationship": relationship,
        "authority": "context_signal_only",
    }


def build_report(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    ctx = build_research_context(root=root)
    manifest = ctx["shared_map"]["source_manifest"]
    sources = manifest.get("sources", [])
    visual_media = manifest.get("visual_media", [])

    wiring_rows = [
        _wiring_row(
            "Seer",
            "aureon/intelligence/aureon_seer_integration.py",
            "seer_get_vision attaches Antarctic star/rune research context",
        ),
        _wiring_row(
            "Lyra",
            "aureon/trading/aureon_lyra_integration.py",
            "lyra_get_resonance attaches Antarctic emotion/frequency research context",
        ),
        _wiring_row(
            "Probability Nexus",
            "aureon/bridges/aureon_probability_nexus.py",
            "nexus reads research context as a bounded confidence modifier",
        ),
        _wiring_row(
            "Research Bridge",
            "aureon/wisdom/antarctic_research_bridge.py",
            "machine-readable map for Seer stars and Lyra emotions",
        ),
    ]

    merge_checklist = [
        {
            "item": "Extract Antarctic research assets",
            "status": "available" if manifest.get("source_count", 0) else "needs_source_files",
            "relates_to": "source research corpus",
            "where_it_flows": "source_manifest",
        },
        {
            "item": "Map phi-graded sphere and 13-sign zodiac into Seer",
            "status": "wired",
            "relates_to": "Seer star/rune reading",
            "where_it_flows": "seer.antarctic_research",
        },
        {
            "item": "Map rune/Ogham emotional texture into Lyra",
            "status": "wired",
            "relates_to": "Lyra emotional resonance",
            "where_it_flows": "lyra.antarctic_research",
        },
        {
            "item": "Expose shared context to Probability Nexus",
            "status": "wired",
            "relates_to": "prediction confidence context",
            "where_it_flows": "research_score/research_modifier",
        },
        {
            "item": "Keep research context out of broker mutation authority",
            "status": "preserved",
            "relates_to": "live execution safety boundary",
            "where_it_flows": "execution_command=none",
        },
    ]

    report = {
        "schema_version": "aureon-antarctic-research-unity-bridge-v1",
        "status": "antarctic_research_context_wired",
        "mode": "context_signal_only",
        "summary": {
            "source_count": manifest.get("source_count", 0),
            "visual_media_count": len(visual_media),
            "seer_context_available": True,
            "lyra_context_available": True,
            "nexus_context_available": True,
            "no_new_blocker_gates": True,
            "execution_command_added": False,
        },
        "research_context": ctx,
        "wiring_rows": wiring_rows,
        "merge_checklist": merge_checklist,
        "source_paths": {
            "state": _rel(REPO_ROOT / DEFAULT_STATE_PATH),
            "audit_json": _rel(REPO_ROOT / DEFAULT_AUDIT_JSON),
            "audit_md": _rel(REPO_ROOT / DEFAULT_AUDIT_MD),
            "public_json": _rel(REPO_ROOT / DEFAULT_PUBLIC_JSON),
            "research_root": manifest.get("research_root"),
        },
    }
    return report


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Antarctic Research Unity Bridge",
        "",
        f"Status: `{report.get('status')}`",
        f"Mode: `{report.get('mode')}`",
        "",
        "This bridge wires the Antarctic/HNC research maps into Seer and Lyra as context signals only.",
        "It does not add buy/sell/close controls and does not create new blocker gates.",
        "",
        "## Summary",
    ]
    for key, value in report.get("summary", {}).items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(["", "## Wiring"])
    for row in report.get("wiring_rows", []):
        present = "present" if row.get("present") else "missing"
        lines.append(f"- {row['system']}: `{row['path']}` ({present}) - {row['relationship']}")

    lines.extend(["", "## Merge Checklist"])
    for row in report.get("merge_checklist", []):
        lines.append(
            f"- {row['item']}: `{row['status']}` -> {row['where_it_flows']}"
        )

    shared = report.get("research_context", {}).get("shared_map", {})
    lines.extend([
        "",
        "## Current Research Reading",
        f"- Zodiac: `{shared.get('zodiac_13_sign')}`",
        f"- Futhork: `{shared.get('younger_futhork', {}).get('name')}`",
        f"- Ogham: `{shared.get('ogham', {}).get('name')}`",
        f"- Phi alignment: `{shared.get('phi_alignment')}`",
        f"- Chamber wall: `{shared.get('chamber_wall', {}).get('wall')}`",
        "",
    ])
    return "\n".join(lines)


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    path.write_text(text, encoding="utf-8")
    return {"path": _rel(path), "bytes": len(text.encode("utf-8"))}


def _write_text(path: Path, text: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": _rel(path), "bytes": len(text.encode("utf-8"))}


def build_and_write_report(*, root: Optional[Path] = None) -> Dict[str, Any]:
    report = build_report(root=root)
    write_info = {
        "evidence_writes": [
            _write_json(REPO_ROOT / DEFAULT_STATE_PATH, report),
            _write_json(REPO_ROOT / DEFAULT_AUDIT_JSON, report),
            _write_text(REPO_ROOT / DEFAULT_AUDIT_MD, render_markdown(report)),
            _write_json(REPO_ROOT / DEFAULT_PUBLIC_JSON, report),
        ]
    }
    report["write_info"] = write_info
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(REPO_ROOT / rel, report)
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish Antarctic research unity bridge evidence.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = build_and_write_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(f"{report['status']} source_count={report['summary']['source_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
