#!/usr/bin/env python3
"""Remeasure go-live receipts 1–4 on a clean worktree.

Refuses a dirty worktree. Records HEAD, the published pin, and the tool
versions. Prints a summary table. go_live_clear stays false. The published
pin is read and not rewritten.

Receipt 1 runs ``python -m aureon.containment.cold_boot`` and writes
``reports/measured/native_process_containment.json``.
Receipt 2 runs ``scripts/validation/go_live_stage6.py``, which writes
``measured/go_live_stage6_provenance.json`` when the write completes.
Before that write, the tip must be an ancestor of the frozen head.
A tip that is not on main is refused. This command does not edit a tip field.
Receipt 3 checks ``refs/notes/aureon-hnc-head`` on HEAD. When the note is
absent, the command prints the git line that re-attaches the committed
sequence-1 DigiCert RFC 3161 token. That line runs only with
``--attach-note``. No new timestamp is requested. The notes ref is not pushed.
Receipt 4 uses the stage-6 census and ``measured/aureon_public_call_sweep.sh``.

The call sweep copies the checkout and refuses a dirty copy. It runs while
the worktree is still clean, with its file staged outside the checkout, so
receipt 1 can still record a clean tree. The sweep file is copied into
``measured/`` after that measurement.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_COMMIT_ID = set("0123456789abcdef")

PUBLISHED_PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
PRIOR_CONTAINMENT_HEAD = "c68a89d2a184d99582bb24310b91e024323a212c"
PRIOR_CONTAINMENT_PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
STALE_PROVENANCE_TIP = "b2b0310362597dc520114de86d8700c0c50758d5"
NOTE_NAME = "aureon-hnc-head"
NOTE_REF = "refs/notes/aureon-hnc-head"
TOKEN_REL = "evidence/output/hnc_head_anchor.tsr.b64"
RECORD_REL = "evidence/output/hnc_head_anchor.json"
PROVENANCE_REL = "measured/go_live_stage6_provenance.json"
CENSUS_REL = "measured/go_live_stage6_source_census.json"
CONTAINMENT_REL = "reports/measured/native_process_containment.json"
SWEEP_REL = "measured/aureon_public_call_sweep.json"
SWEEP_SCRIPT = "measured/aureon_public_call_sweep.sh"


def reattach_argv() -> list[str]:
    """Attach the committed token as a note. No push and no timestamp request."""

    argv = [
        "git",
        "notes",
        "--ref=aureon-hnc-head",
        "add",
        "-f",
        "-F",
        TOKEN_REL,
        "HEAD",
    ]
    if "push" in argv or any("timestamp.digicert.com" in part for part in argv):
        raise SystemExit(f"refusing to push {NOTE_REF}")
    return argv


def reattach_command_lines() -> list[str]:
    return [" ".join(reattach_argv())]


def repo_root_default() -> Path:
    return Path(__file__).resolve().parents[2]


def _run(
    argv: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True)


def porcelain(root: Path) -> str:
    done = _run(["git", "-C", str(root), "status", "--porcelain"], root)
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip()
        raise SystemExit(f"git status failed: {detail}")
    return done.stdout


def refuse_dirty(root: Path) -> str | None:
    """Return porcelain text when the worktree is dirty, else None."""

    text = porcelain(root)
    if text.strip():
        return text
    return None


def _git_text(root: Path, *args: str) -> str | None:
    done = _run(["git", "-C", str(root), *args], root)
    if done.returncode != 0:
        return None
    return done.stdout


def _git_bytes(root: Path, *args: str) -> bytes | None:
    done = subprocess.run(["git", "-C", str(root), *args], cwd=root, capture_output=True)
    if done.returncode != 0:
        return None
    return done.stdout


def commit_on_main(root: Path, tip: object) -> bool:
    """True when ``tip`` is an ancestor of the frozen head, including the head itself."""

    if not isinstance(tip, str) or len(tip) != 40 or any(ch not in _COMMIT_ID for ch in tip):
        return False
    done = _run(["git", "-C", str(root), "merge-base", "--is-ancestor", tip, "HEAD"], root)
    return done.returncode == 0


def tip_blocks_write(root: Path, tip: object) -> str | None:
    """Return a refusal when ``tip`` is not on main. Does not edit a file."""

    if commit_on_main(root, tip):
        return None
    shown = tip if isinstance(tip, str) else type(tip).__name__
    return f"tip {shown} is not on main. The tip field was not rewritten."


def read_stage6_tip(root: Path) -> str | None:
    """Read the TIP constant the stage-6 writer would record. Does not change it."""

    path = root / "scripts" / "validation" / "go_live_stage6.py"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith('TIP = "') and line.endswith('"') and len(line) == len('TIP = "') + 40 + 1:
            value = line[len('TIP = "') : -1]
            if len(value) == 40 and all(ch in _COMMIT_ID for ch in value):
                return value
    return None


def stage6_write_block(root: Path) -> str | None:
    """Refuse the stage-6 provenance and census write before it starts.

    The check reads the script's TIP constant and does not rewrite a tip field.
    """

    declared = read_stage6_tip(root)
    if declared is None:
        return (
            "refusing to write. scripts/validation/go_live_stage6.py has no TIP assignment. "
            "The tip field was not rewritten."
        )
    reason = tip_blocks_write(root, declared)
    if reason is None:
        return None
    cited: list[str] = []
    for rel in (PROVENANCE_REL, CENSUS_REL):
        payload = _load_json(root / rel)
        if isinstance(payload, dict) and "tip" in payload:
            cited.append(f"{rel} cites {payload.get('tip')}")
    suffix = (" " + "; ".join(cited)) if cited else ""
    return f"refusing to write. scripts/validation/go_live_stage6.py {reason}{suffix}"


def payload_tip_block(root: Path, payload: dict | None) -> str | None:
    """Refuse a receipt object that carries an unreachable tip. Does not edit it."""

    if not isinstance(payload, dict) or "tip" not in payload:
        return None
    return tip_blocks_write(root, payload.get("tip"))


def read_published_pin(root: Path) -> str:
    path = root / "mcp" / "aureon_public" / "guard_loader.py"
    marker = 'PINNED_COMMIT = "'
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(marker) and line.endswith('"'):
            value = line[len(marker) : -1]
            if len(value) == 40 and all(ch in "0123456789abcdef" for ch in value):
                return value
    raise SystemExit("PINNED_COMMIT is missing from mcp/aureon_public/guard_loader.py")


def _tool_line(argv: list[str]) -> str:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, check=False)
    except OSError as exc:
        return f"unavailable ({exc})"
    text = (done.stdout or done.stderr).strip()
    if done.returncode != 0 or not text:
        return "unavailable"
    return text.splitlines()[0]


def tool_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "git": _tool_line(["git", "--version"]),
        "unshare": _tool_line(["unshare", "--version"]),
        "openssl": _tool_line(["openssl", "version"]),
    }


def _one_line(text: str, limit: int = 900) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 3] + "..."


def _load_json(path: Path) -> dict | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def _child_env(root: Path, pythonpath: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = pythonpath
    env["AUREON_REMEASURE_ROOT"] = str(root)
    return env


def _row(
    receipt: int,
    name: str,
    verdict: str,
    detail: str,
    go_live_clear: object = False,
) -> dict[str, object]:
    if go_live_clear is True:
        return {
            "receipt": receipt,
            "name": name,
            "verdict": "refused",
            "detail": "child output set go_live_clear true. This command does not adopt it. " + detail,
            "go_live_clear": False,
        }
    return {
        "receipt": receipt,
        "name": name,
        "verdict": verdict,
        "detail": detail,
        "go_live_clear": False,
    }


def measure_containment(root: Path) -> dict[str, object]:
    tmp = Path(tempfile.mkdtemp(prefix="aureon-containment-"))
    json_path = tmp / "native_process_containment.json"
    md_path = tmp / "native_process_containment.md"
    done = _run(
        [
            sys.executable,
            "-m",
            "aureon.containment.cold_boot",
            "--receipt-json",
            str(json_path),
            "--receipt-md",
            str(md_path),
        ],
        root,
        _child_env(root, str(root)),
    )
    receipt = _load_json(json_path)
    block = payload_tip_block(root, receipt)
    if block is not None:
        shutil.rmtree(tmp, ignore_errors=True)
        return _row(1, "containment", "refused", block + " The containment receipt was not written.")
    if receipt is not None:
        dest_json = root / CONTAINMENT_REL
        dest_md = root / "reports" / "measured" / "native_process_containment.md"
        dest_json.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(json_path, dest_json)
        if md_path.is_file():
            shutil.copyfile(md_path, dest_md)
    shutil.rmtree(tmp, ignore_errors=True)
    if receipt is None:
        err = _one_line(done.stderr or done.stdout or "cold boot wrote no receipt")
        return _row(
            1,
            "containment",
            "fail",
            f"python -m aureon.containment.cold_boot exit {done.returncode}. {err}",
        )
    verdict = str(receipt.get("verdict") or "fail")
    dirty = receipt.get("worktree_dirty_at_measurement")
    detail = (
        f"prior measurement {PRIOR_CONTAINMENT_HEAD[:12]} dirty worktree pin {PRIOR_CONTAINMENT_PIN[:12]}. "
        f"this run git_head {receipt.get('git_head_at_measurement')} "
        f"worktree_dirty {dirty} pin {receipt.get('pin')} "
        f"allowed {receipt.get('allowed_at_default')} exit {done.returncode}."
    )
    if dirty is True:
        verdict = "fail"
        detail = "worktree was dirty at measurement. " + detail
    if verdict not in {"pass", "fail", "skip"}:
        verdict = "fail"
    return _row(1, "containment", verdict, detail)


def measure_provenance(
    root: Path,
    head: str,
) -> tuple[dict[str, object], subprocess.CompletedProcess[str]]:
    script = root / "scripts" / "validation" / "go_live_stage6.py"
    done = _run([sys.executable, str(script)], root, _child_env(root, str(root / "mcp")))
    payload = _load_json(root / PROVENANCE_REL)
    tip = None if payload is None else payload.get("tip")
    clear = None if payload is None else payload.get("go_live_clear")
    err = _one_line(done.stderr or done.stdout or "")
    if done.returncode != 0:
        shown_tip = tip if tip is not None else STALE_PROVENANCE_TIP
        detail = (
            f"scripts/validation/go_live_stage6.py exit {done.returncode}. "
            f"on-disk tip {shown_tip}. HEAD {head}. {err}"
        )
        return _row(2, "release provenance", "fail", detail, clear), done
    if tip != head:
        detail = (
            f"provenance tip {tip}. HEAD {head}. "
            f"The stage-6 script still binds tip {STALE_PROVENANCE_TIP}. decision HOLD."
        )
        return _row(2, "release provenance", "stale", detail, clear), done
    decision = None if payload is None else payload.get("decision")
    detail = f"wrote {PROVENANCE_REL}. tip {tip}. decision {decision}."
    verdict = "hold" if decision == "HOLD" and clear is False else "fail"
    return _row(2, "release provenance", verdict, detail, clear), done


def _committed_anchor(root: Path) -> dict | None:
    raw = _git_text(root, "show", f"HEAD:{RECORD_REL}")
    if raw is None:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def note_on_head(root: Path) -> bytes | None:
    return _git_bytes(root, "notes", "--ref", NOTE_NAME, "show", "HEAD")


def _sequence_one_token(root: Path) -> tuple[bytes | None, str | None]:
    record = _committed_anchor(root)
    if record is None:
        return None, f"{RECORD_REL} is not a committed object on HEAD"
    if record.get("sequence") != 1:
        return None, f"committed anchor sequence is {record.get('sequence')}, not 1"
    external = record.get("external")
    provider = external.get("provider") if isinstance(external, dict) else None
    kind = external.get("kind") if isinstance(external, dict) else None
    if kind != "rfc3161" or provider != "http://timestamp.digicert.com":
        return None, "committed anchor is not the DigiCert RFC 3161 sequence-1 token"
    blob = _git_bytes(root, "show", f"HEAD:{TOKEN_REL}")
    if blob is None:
        return None, f"{TOKEN_REL} is not committed on HEAD"
    work = root / TOKEN_REL
    if not work.is_file() or work.read_bytes() != blob:
        return None, "working tree token differs from the committed sequence-1 bytes"
    return blob, None


def measure_anchor(root: Path, attach: bool) -> dict[str, object]:
    token, problem = _sequence_one_token(root)
    commands = reattach_command_lines()
    shown = " ; ".join(commands)
    if problem is not None:
        return _row(
            3,
            "hnc head anchor",
            "fail",
            f"{problem}. No timestamp was requested. {NOTE_REF} was not pushed.",
        )
    assert token is not None
    note = note_on_head(root)
    if note == token:
        return _row(
            3,
            "hnc head anchor",
            "anchored",
            f"{NOTE_REF} is on HEAD and matches the committed sequence-1 DigiCert token.",
        )
    state = "differs from" if note is not None else "is not on"
    detail = (
        f"{NOTE_REF} {state} HEAD. "
        f"Re-attach the committed sequence-1 token without a new timestamp request: {shown}. "
        "This command does not push the notes ref."
    )
    print(detail)
    if not attach:
        print("Not run. Pass --attach-note to run that command locally.")
        return _row(3, "hnc head anchor", "absent", detail + " Not run.")
    print("Running locally because --attach-note was passed.")
    done = _run(reattach_argv(), root)
    if done.returncode != 0:
        err = _one_line(done.stderr or done.stdout or "git notes add failed")
        return _row(3, "hnc head anchor", "fail", f"git notes add exit {done.returncode}. {err}")
    if note_on_head(root) != token:
        return _row(3, "hnc head anchor", "fail", "git note on HEAD does not match the committed token bytes.")
    return _row(
        3,
        "hnc head anchor",
        "attached",
        f"{NOTE_REF} now points at HEAD with the sequence-1 token. The notes ref was not pushed.",
    )


def run_call_sweep(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the call sweep while ``root`` is clean. Write the JSON outside ``root``."""

    script = root / SWEEP_SCRIPT
    if not script.is_file():
        return subprocess.CompletedProcess(
            args=["bash", SWEEP_SCRIPT],
            returncode=127,
            stdout="",
            stderr=f"missing {SWEEP_SCRIPT}",
        )
    handle = tempfile.NamedTemporaryFile(prefix="aureon-call-sweep-", suffix=".json", delete=False)
    out_path = Path(handle.name)
    handle.close()
    env = os.environ.copy()
    env["OUT"] = str(out_path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    print(f"receipt 4: bash {SWEEP_SCRIPT}")
    done = _run(["bash", str(script)], root, env)
    done.out_path = out_path  # type: ignore[attr-defined]
    return done


def _place_sweep(root: Path, done: subprocess.CompletedProcess[str]) -> tuple[bool, str]:
    out_path = getattr(done, "out_path", None)
    if done.returncode != 0 or not isinstance(out_path, Path) or not out_path.is_file():
        err = _one_line(done.stderr or done.stdout or "call sweep wrote no file")
        if isinstance(out_path, Path):
            out_path.unlink(missing_ok=True)
        return False, f"call sweep exit {done.returncode}. {err}"
    block = payload_tip_block(root, _load_json(out_path))
    if block is not None:
        out_path.unlink(missing_ok=True)
        return False, block + " The call-sweep receipt was not written."
    target = root / SWEEP_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out_path, target)
    out_path.unlink(missing_ok=True)
    return True, f"call sweep exit 0. wrote {SWEEP_REL}."


def _restore_stage6_outputs(root: Path) -> None:
    """Put the stage-6 files back. This does not edit a tip field."""

    _run(
        [
            "git",
            "-C",
            str(root),
            "checkout",
            "--",
            PROVENANCE_REL,
            CENSUS_REL,
            "docs/runbooks/GO_LIVE_STAGE6_SOURCE_CENSUS.md",
        ],
        root,
    )


def measure_census(
    root: Path,
    stage6: subprocess.CompletedProcess[str] | None,
    sweep: subprocess.CompletedProcess[str],
    write_block: str | None = None,
) -> dict[str, object]:
    refused = write_block is not None
    if write_block is not None:
        census_detail = write_block
        census_clear: object = False
        census_ok = False
    else:
        assert stage6 is not None
        census = _load_json(root / CENSUS_REL)
        census_clear = None if census is None else census.get("go_live_clear")
        err = _one_line(stage6.stderr or stage6.stdout or "")
        block = payload_tip_block(root, census)
        if block is not None:
            _restore_stage6_outputs(root)
            census_detail = block
            census_ok = False
            refused = True
            census_clear = False
        elif stage6.returncode != 0:
            census_detail = f"census via scripts/validation/go_live_stage6.py exit {stage6.returncode}. {err}"
            census_ok = False
        else:
            closed = None if census is None else census.get("source_boundary_closed")
            decision = None if census is None else census.get("decision")
            census_detail = f"census wrote {CENSUS_REL}. source_boundary_closed {closed}. decision {decision}."
            census_ok = decision == "HOLD" and census_clear is False
    sweep_ok, sweep_detail = _place_sweep(root, sweep)
    if refused:
        verdict = "refused"
    elif census_ok and sweep_ok:
        verdict = "hold"
    else:
        verdict = "fail"
    return _row(4, "census and call sweep", verdict, census_detail + " " + sweep_detail, census_clear)


def format_summary(context: dict[str, object], rows: list[dict[str, object]]) -> str:
    tools = context["tools"]
    assert isinstance(tools, dict)
    matches = "true" if context["published_pin"] == PUBLISHED_PIN else "false"
    lines = [
        f"HEAD: {context['head']}",
        f"published_pin: {context['published_pin']}",
        f"published_pin_matches_checkout: {matches}",
        "go_live_clear: false",
        "tools:",
    ]
    for name in ("python", "git", "unshare", "openssl"):
        lines.append(f"  {name}: {tools.get(name, 'unavailable')}")
    lines.extend(["", "| receipt | name | verdict | detail |", "| --- | --- | --- | --- |"])
    for row in rows:
        detail = _one_line(str(row["detail"]).replace("|", "/"))
        lines.append(f"| {row['receipt']} | {row['name']} | {row['verdict']} | {detail} |")
    lines.extend(
        [
            "",
            "go_live_clear stays false. This run does not clear go-live, does not move the published pin, "
            f"and does not push {NOTE_REF}.",
            "",
        ]
    )
    text = "\n".join(lines)
    if "go_live_clear: true" in text:
        raise SystemExit("summary refused to report go_live_clear true")
    return text


def _context(root: Path) -> dict[str, object]:
    head = _git_text(root, "rev-parse", "HEAD")
    if head is None or len(head.strip()) != 40:
        raise SystemExit("git rev-parse HEAD failed")
    return {
        "head": head.strip(),
        "published_pin": read_published_pin(root),
        "tools": tool_versions(),
    }


def runner_exit(rows: list[dict[str, object]]) -> int:
    if any(row["verdict"] in {"fail", "refused"} for row in rows):
        return 1
    return 0


def _measure_clean(root: Path, attach_note: bool) -> tuple[dict[str, object], list[dict[str, object]]]:
    context = _context(root)
    head = str(context["head"])
    print(f"HEAD {head}")
    print(f"published pin {context['published_pin']}")
    if context["published_pin"] != PUBLISHED_PIN:
        print(
            "published pin in mcp/aureon_public/guard_loader.py differs from "
            f"{PUBLISHED_PIN}. This command does not edit that file."
        )
    print("receipt 4 call sweep snapshots the clean tree before receipt 1 writes")
    sweep = run_call_sweep(root)
    if porcelain(root).strip():
        out_path = getattr(sweep, "out_path", None)
        if isinstance(out_path, Path):
            out_path.unlink(missing_ok=True)
        raise SystemExit("call sweep dirtied the worktree before receipt 1. Receipt 1 was not measured.")
    print("receipt 1: python -m aureon.containment.cold_boot")
    containment = measure_containment(root)
    write_block = stage6_write_block(root)
    if write_block is not None:
        print(write_block)
        provenance = _row(2, "release provenance", "refused", write_block)
        stage6 = None
    else:
        print("receipt 2: python3 scripts/validation/go_live_stage6.py")
        provenance, stage6 = measure_provenance(root, head)
        written = payload_tip_block(root, _load_json(root / PROVENANCE_REL))
        if written is not None:
            _restore_stage6_outputs(root)
            provenance = _row(2, "release provenance", "refused", written)
            stage6 = None
            write_block = written
    print("receipt 3: refs/notes/aureon-hnc-head")
    anchor = measure_anchor(root, attach_note)
    print("receipt 4: census from stage 6 and the call-sweep script")
    census = measure_census(root, stage6, sweep, write_block)
    return context, [containment, provenance, anchor, census]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="checkout to measure")
    parser.add_argument(
        "--attach-note",
        action="store_true",
        help="locally re-attach the committed sequence-1 DigiCert token as a git note on HEAD",
    )
    args = parser.parse_args(argv)
    root = (args.root or repo_root_default()).resolve()
    dirty = refuse_dirty(root)
    if dirty is not None:
        print("refusing dirty worktree. Commit or stash before remeasuring receipts 1-4.\n" + dirty)
        return 2
    try:
        context, rows = _measure_clean(root, args.attach_note)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code)
            return 1
        raise
    sys.stdout.write(format_summary(context, rows))
    code = runner_exit(rows)
    print(f"runner_exit: {code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
