"""⚒️ FORGE ONCE — one bounded capability-forge cycle, fail-closed.

Owner decree (2026-09-05): "give her full control of her coding systems" —
the organism may open the capability_forge door itself (internal intent +
the master_key gate trio at mint time). This module is the thin wrapper the
door's subprocess-oneshot command runs.

Upstream entry point (read from aureon/autonomous/aureon_capability_forge.py):
    build_and_write_capability_forge(prompt, *, root=None,
                                     provider_policy="local_only_v1",
                                     approval_gate="after_apply") -> report
One call = one bounded cycle. The forge is template-based deterministic
generation — no local model plane (Ollama) is required:
  • provider_policy is pinned "local_only_v1" and the report carries
    external_api_calls: [] (no paid/cloud calls in v1);
  • the only model-adjacent path (SafeCodeControl proposal expression
    context via the voice core) is wrapped upstream in try/except and
    degrades to a warning when the voice core is unavailable.

Evidence writes land UNDER THE WORKSPACE ROOT (state/, docs/audits/,
frontend/public/) — the upstream repo itself is never written.

Import-safe: nothing upstream is imported at module import; suppression env
honored via setdefault. CLI prints exactly one JSON result line and exits
0 on success / 1 on failure.
"""

import argparse
import json
import os
import sys

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

from .paths import WORKSPACE

# Default prompt: a small, safe, organism-flavored local skill request —
# routes through the adaptive-skill-capsule path (no interactive app, no
# full-stack spawn) and exercises the forge's full local quality gate.
_DEFAULT_PROMPT = (
    "a small local Python utility skill that watches the organism's coding "
    "door journal and summarizes recent door activity in plain text"
)


def run_once(prompt: str | None = None, root=None) -> dict:
    """One bounded forge cycle. Fail-closed: any exception → ok=False."""
    try:
        from .paths import AUREON_UPSTREAM
        if str(AUREON_UPSTREAM) not in sys.path:
            sys.path.insert(0, str(AUREON_UPSTREAM))
        from aureon.autonomous.aureon_capability_forge import (
            build_and_write_capability_forge,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "items": 0,
                "error": f"forge import failed: {type(exc).__name__}"}
    try:
        report = build_and_write_capability_forge(
            prompt or _DEFAULT_PROMPT,
            root=root or WORKSPACE,
            provider_policy="local_only_v1",
            approval_gate="after_apply",
        )
    except Exception as exc:  # noqa: BLE001 - one honest failure line, never raise
        return {"ok": False, "items": 0,
                "error": f"forge cycle failed: {type(exc).__name__}"}
    if not isinstance(report, dict):
        return {"ok": False, "items": 0,
                "error": f"forge returned unexpected {type(report).__name__}"}
    output_files = report.get("output_files")
    items = len(output_files) if isinstance(output_files, list) else 0
    return {"ok": bool(report.get("ok")), "items": items,
            "task_family": report.get("task_family"),
            "build_id": report.get("build_id"),
            "status": report.get("status"),
            "error": None if report.get("ok") else str(report.get("status"))}


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(
        description="Run ONE bounded local capability-forge cycle (fail-closed).")
    parser.add_argument("--prompt", "-p", default="",
                        help="Forge prompt/job (default: internal sovereign micro-prompt).")
    parser.add_argument("--root", default="",
                        help="Evidence root (default: the workspace; upstream is never written).")
    args = parser.parse_args(argv)
    root = None
    if args.root:
        from pathlib import Path
        root = Path(args.root).resolve()
    result = run_once(prompt=args.prompt.strip() or None, root=root)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
