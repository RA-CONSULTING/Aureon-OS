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
Receipt 3 reports ``anchored on <short sha>`` when the commit that recorded
the HNC anchor files and ``hnc_head_next.*`` is an ancestor of HEAD and both
notes match those committed token files. A re-attach is offered only when no
such commit exists. ``--attach-note`` adds a note only where none exists.
Receipt 4 uses the stage-6 census and ``measured/aureon_public_call_sweep.sh``.
A refused receipt 4 discards the staged sweep and leaves the committed sweep
file byte-identical.

The call sweep copies the checkout and refuses a dirty copy. It runs while
the worktree is still clean, with its file staged outside the checkout.
Containment is written outside the committed paths and copied over
``reports/measured/native_process_containment.*`` only on ``pass``.
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

PUBLISHED_PIN = "0646146c53e59dbcab41363a613d5651c9c9d50f"
PRIOR_CONTAINMENT_HEAD = "c68a89d2a184d99582bb24310b91e024323a212c"
PRIOR_CONTAINMENT_PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
NOTE_NAME = "aureon-hnc-head"
NOTE_REF = "refs/notes/aureon-hnc-head"
NEXT_NOTE_NAME = "aureon-hnc-head-next"
NEXT_NOTE_REF = "refs/notes/aureon-hnc-head-next"
TOKEN_REL = "evidence/output/hnc_head_anchor.tsr.b64"
NEXT_TOKEN_REL = "evidence/output/hnc_head_next.tsr.b64"
RECORD_REL = "evidence/output/hnc_head_anchor.json"
RECORDED_ANCHOR_PATHS = (
    "evidence/output/hnc_head_anchor.tsr.b64",
    "evidence/output/hnc_head_anchor.json",
    "evidence/output/hnc_head_anchor.id",
    "evidence/output/hnc_head_next.tsr.b64",
    "evidence/output/hnc_head_next.json",
    "evidence/output/hnc_head_next.id",
)
NOTE_PAIRS = (
    (NOTE_NAME, TOKEN_REL),
    (NEXT_NOTE_NAME, NEXT_TOKEN_REL),
)
PROVENANCE_REL = "measured/go_live_stage6_provenance.json"
CENSUS_REL = "measured/go_live_stage6_source_census.json"
CONTAINMENT_REL = "reports/measured/native_process_containment.json"
CONTAINMENT_MD = "reports/measured/native_process_containment.md"
SWEEP_REL = "measured/aureon_public_call_sweep.json"
SWEEP_SCRIPT = "measured/aureon_public_call_sweep.sh"


def reattach_argv(note_name: str, token_rel: str) -> list[str]:
    """Add a note only. No ``-f``, so an existing note is left alone."""

    return ["git", "notes", f"--ref={note_name}", "add", "-F", token_rel, "HEAD"]


def reattach_command_lines() -> list[str]:
    return [" ".join(reattach_argv(name, rel)) for name, rel in NOTE_PAIRS]


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
    return (
        f"tip {shown} is not an ancestor of the frozen head (not on main). "
        "The tip field was not rewritten."
    )


def tip_text(value: object) -> str:
    """A tip string that was actually read, or ``none read``."""

    if isinstance(value, str) and value.strip():
        return value.strip()
    return "none read"


def describe_tip(disk_tip: object, script_tip: object) -> str:
    """Prefer the tip read from a receipt file, then the script TIP."""

    if isinstance(disk_tip, str) and disk_tip.strip():
        return disk_tip.strip()
    return tip_text(script_tip)


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
            cited.append(f"{rel} cites {tip_text(payload.get('tip'))}")
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
        install_containment_receipt(root, receipt, json_path, md_path)
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


def install_containment_receipt(
    root: Path,
    receipt: dict,
    json_path: Path,
    md_path: Path,
) -> bool:
    """Copy a containment receipt onto the committed paths only on a clean pass."""

    if str(receipt.get("verdict")) != "pass":
        return False
    if receipt.get("worktree_dirty_at_measurement") is True:
        return False
    dest_json = root / CONTAINMENT_REL
    dest_md = root / CONTAINMENT_MD
    dest_json.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(json_path, dest_json)
    if md_path.is_file():
        shutil.copyfile(md_path, dest_md)
    return True


def provenance_failure_detail(
    root: Path,
    head: str,
    payload: dict | None,
    returncode: int,
    err: str,
) -> str:
    disk = payload.get("tip") if isinstance(payload, dict) else None
    shown = describe_tip(disk, read_stage6_tip(root))
    return (
        f"scripts/validation/go_live_stage6.py exit {returncode}. "
        f"tip {shown}. HEAD {head}. {err}"
    )


def provenance_stale_detail(root: Path, head: str, payload: dict | None) -> str:
    disk = payload.get("tip") if isinstance(payload, dict) else None
    shown = describe_tip(disk, read_stage6_tip(root))
    return f"provenance tip {shown}. HEAD {head}. decision HOLD."


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
        detail = provenance_failure_detail(root, head, payload, done.returncode, err)
        return _row(2, "release provenance", "fail", detail, clear), done
    if tip != head:
        detail = provenance_stale_detail(root, head, payload)
        return _row(2, "release provenance", "stale", detail, clear), done
    decision = None if payload is None else payload.get("decision")
    detail = f"wrote {PROVENANCE_REL}. tip {tip}. decision {decision}."
    verdict = "hold" if decision == "HOLD" and clear is False else "fail"
    return _row(2, "release provenance", verdict, detail, clear), done


def short_sha(sha: str) -> str:
    return sha[:12]


def _blob_exists(root: Path, spec: str) -> bool:
    done = _run(["git", "-C", str(root), "cat-file", "-e", spec], root)
    return done.returncode == 0


def recording_commit(root: Path) -> str | None:
    """Commit that added ``hnc_head_next`` while the anchor files are in that tree."""

    raw = _git_text(
        root,
        "log",
        "--diff-filter=A",
        "--format=%H",
        "--",
        NEXT_TOKEN_REL,
    )
    if raw is None:
        return None
    for sha in raw.splitlines():
        sha = sha.strip()
        if not commit_on_main(root, sha):
            continue
        if all(_blob_exists(root, f"{sha}:{path}") for path in RECORDED_ANCHOR_PATHS):
            return sha
    return None


def _note_bytes(root: Path, note_name: str, commit: str) -> bytes | None:
    return _git_bytes(root, "notes", "--ref", note_name, "show", commit)


def anchored_recording(root: Path) -> str | None:
    """Ancestor whose notes match the committed token files byte for byte."""

    sha = recording_commit(root)
    if sha is None:
        return None
    for name, rel in NOTE_PAIRS:
        note = _note_bytes(root, name, sha)
        committed = _git_bytes(root, "show", f"{sha}:{rel}")
        head = _git_bytes(root, "show", f"HEAD:{rel}")
        if note is None or committed is None or note != committed:
            return None
        if head is not None and note != head:
            return None
    return sha


def _attach_missing_notes(root: Path) -> dict[str, object]:
    """Add a note only where none exists. A different note stops the attach."""

    for name, rel in NOTE_PAIRS:
        token = _git_bytes(root, "show", f"HEAD:{rel}")
        if token is None:
            return _row(
                3,
                "hnc head anchor",
                "fail",
                f"{rel} is not committed on HEAD. No note was added.",
            )
        existing = _note_bytes(root, name, "HEAD")
        if existing is not None and existing != token:
            return _row(
                3,
                "hnc head anchor",
                "fail",
                f"A different note already exists on refs/notes/{name}. It was left alone.",
            )
    for name, rel in NOTE_PAIRS:
        token = _git_bytes(root, "show", f"HEAD:{rel}")
        existing = _note_bytes(root, name, "HEAD")
        if existing is not None:
            continue
        done = _run(reattach_argv(name, rel), root)
        if done.returncode != 0:
            err = _one_line(done.stderr or done.stdout or "git notes add failed")
            return _row(3, "hnc head anchor", "fail", f"git notes add exit {done.returncode}. {err}")
        if _note_bytes(root, name, "HEAD") != token:
            return _row(
                3,
                "hnc head anchor",
                "fail",
                "git note does not match the committed token. The notes ref was not pushed.",
            )
    return _row(
        3,
        "hnc head anchor",
        "attached",
        "Notes were added where none existed. The notes ref was not pushed.",
    )


def measure_anchor(root: Path, attach: bool) -> dict[str, object]:
    sha = anchored_recording(root)
    if sha is not None:
        return _row(3, "hnc head anchor", "anchored", f"anchored on {short_sha(sha)}")
    shown = " ; ".join(reattach_command_lines())
    if not attach:
        detail = (
            "No ancestor has notes that match the committed HNC token files. "
            f"Re-attach without -f and without a new timestamp request: {shown}. "
            "This command does not push the notes ref. Not run."
        )
        print(detail)
        print("Not run. Pass --attach-note to run that command locally.")
        return _row(3, "hnc head anchor", "absent", detail)
    print("Running locally because --attach-note was passed.")
    return _attach_missing_notes(root)


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


def _place_sweep(
    root: Path,
    done: subprocess.CompletedProcess[str],
    keep: bool = True,
) -> tuple[bool, str]:
    out_path = getattr(done, "out_path", None)
    if not keep:
        if isinstance(out_path, Path):
            out_path.unlink(missing_ok=True)
        return False, f"staged call sweep discarded. {SWEEP_REL} was not written."
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
    sweep_ok, sweep_detail = _place_sweep(root, sweep, keep=not refused)
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
    """0 only when every row was measured. HOLD-type rows exit 3, like publish."""

    verdicts = [str(row["verdict"]) for row in rows]
    if any(verdict in {"fail", "refused"} for verdict in verdicts):
        return 1
    if any(verdict in {"stale", "hold", "absent", "skip"} for verdict in verdicts):
        return 3
    if verdicts and all(verdict in {"pass", "anchored", "attached"} for verdict in verdicts):
        return 0
    return 1


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
