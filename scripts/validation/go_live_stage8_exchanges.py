#!/usr/bin/env python3
"""Stage 8 exchanges read-surface sweep.

The child process is the measurement. It does not import aureon.exchanges,
does not place an order, and does not keep planted key values in the record.
``--write`` needs a clean tree so the stamp names that parent commit.
``--check`` runs the child again and compares the sweep. It does not publish.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MCP = ROOT / "mcp"
RECORD = ROOT / "measured" / "go_live_stage8_exchanges.json"
MARKDOWN = ROOT / "docs" / "runbooks" / "GO_LIVE_STAGE8_EXCHANGES.md"
STAMP_KEYS = ("aureon_tree", "code_commit", "code_commit_note", "pin_aureon_tree")


def _child_env() -> dict[str, str]:
    from aureon_public.exchanges_surface import PLANTED_SECRETS

    env = {
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(MCP),
    }
    env.update(PLANTED_SECRETS)
    return env


def run_child() -> dict:
    from aureon_public.exchanges_surface import PLANTED_SECRETS

    completed = subprocess.run(
        [sys.executable, "-m", "aureon_public.exchanges_surface", "--guarded-sweep"],
        cwd=str(ROOT),
        env=_child_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "exchanges sweep child failed " f"({completed.returncode}): {completed.stderr.strip()}"
        )
    for secret in PLANTED_SECRETS.values():
        if secret in completed.stdout or secret in completed.stderr:
            raise SystemExit("exchanges sweep leaked a planted secret")
    loaded = json.loads(completed.stdout)
    if not isinstance(loaded, dict):
        raise SystemExit("exchanges sweep did not return an object")
    return loaded


def render_markdown(record: dict) -> str:
    guard = record["guard"]
    return "\n".join(
        [
            "# Stage 8 exchanges read surface",
            "",
            "Decision: **HOLD**. Live orders: **refused**. Read-gated: yes.",
            "Go-live is not clear. This page does not publish a Space.",
            "",
            f"Pin: `{record['pin']}`. Pin moved: no. Badge: unchanged.",
            f"Rows: {record['rows']}. Called: {record['called']}. Reachable: {record['reachable']}.",
            f"Imports performed: {record['imports_performed']}. Key leak: {str(record['key_leak']).lower()}.",
            f"Sockets: {len(guard['sockets'])}. Processes: {len(guard['processes'])}. "
            f"Writes: {len(guard['writes'])}.",
            f"Entries sha256: `{record['entries_sha256']}`.",
            "",
            "`OPEN_PLAN_THROUGH` is 2. `ENABLED_THROUGH` is 6. " "Plan stages 3 and 4 stay closed.",
            "The protocol session and the call sweep were not repeated.",
            "",
            "Reproduce:",
            "",
            "```bash",
            "env PYTHONPATH=mcp python3 scripts/validation/go_live_stage8_exchanges.py --check",
            "```",
            "",
        ]
    )


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _ancestor(commit: str) -> bool:
    if len(commit) != 40:
        return False
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", commit, "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0 and commit != _git("rev-parse", "HEAD")


def code_commit_is_accepted(recorded: dict, ancestor: Callable[[str], bool]) -> bool:
    """Accept the measured commit, or the main commit the receipt says carries it.

    A squash can leave ``code_commit`` off the history. The receipt then names
    ``carried_on_main`` and says the sweep was not remeasured. The check reads
    those fields. It does not special-case a commit hash.
    """

    code_commit = str(recorded.get("code_commit") or "")
    if ancestor(code_commit):
        return True
    carried = str(recorded.get("carried_on_main") or "")
    note = str(recorded.get("code_commit_note") or "")
    if not carried or carried == code_commit or not ancestor(carried):
        return False
    return "does not remeasure" in note and code_commit in note and carried in note


def check() -> None:
    from aureon_public.exchanges_surface import sweep_ok

    if not RECORD.is_file():
        raise SystemExit(f"missing {RECORD}")
    recorded = json.loads(RECORD.read_text(encoding="utf-8"))
    reason = sweep_ok(recorded)
    if reason:
        raise SystemExit(f"recorded exchanges sweep refused: {reason}")
    fresh = run_child()
    fresh_reason = sweep_ok(fresh)
    if fresh_reason:
        raise SystemExit(f"fresh exchanges sweep refused: {fresh_reason}")
    for key in ("entries_sha256", "guard", "catalog", "execute_probe", "rows", "pin"):
        if recorded.get(key) != fresh.get(key):
            raise SystemExit(f"exchanges sweep drift: {key}")
    from aureon_public.guard_loader import PINNED_COMMIT

    if recorded.get("pin") != PINNED_COMMIT:
        raise SystemExit("pin moved")
    if not code_commit_is_accepted(recorded, _ancestor):
        raise SystemExit("code_commit is not a parent of HEAD")
    markdown = MARKDOWN.read_text(encoding="utf-8")
    if recorded["entries_sha256"] not in markdown:
        raise SystemExit("runbook is missing the entries digest")
    if "HOLD" not in markdown or "refused" not in markdown:
        raise SystemExit("runbook dropped the gate")
    badge = (ROOT / "README.md").read_text(encoding="utf-8")
    if "release%20boundary-HOLD-orange" not in badge:
        raise SystemExit("orange badge changed")
    print(f"ok {recorded['entries_sha256']}")


def write() -> None:
    sys.path.insert(0, str(MCP))
    from aureon_public.exchanges_surface import sweep_ok
    from aureon_public.measurement_stamp import measurement_stamp

    fresh = run_child()
    reason = sweep_ok(fresh)
    if reason:
        raise SystemExit(f"exchanges sweep refused: {reason}")
    record = {**fresh, **measurement_stamp()}
    from aureon_public.guard_loader import PINNED_COMMIT

    if record["pin"] != PINNED_COMMIT:
        raise SystemExit("stamp pin does not match the public pin")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MARKDOWN.write_text(render_markdown(record), encoding="utf-8")
    print(RECORD)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="go-live-stage8-exchanges")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.check == args.write:
        raise SystemExit("pass one of --check or --write")
    sys.path.insert(0, str(MCP))
    if args.write:
        write()
        return
    check()


if __name__ == "__main__":
    main()
