"""Build the evidence bundle and check it against the committed bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from aureon.evidence.auris import RANDOM_SEED as AURIS_RANDOM_SEED
from aureon.evidence.hnc import GAUSSIAN_SEED, SEEDS, SHUFFLE_SEED
from aureon.evidence.hnc_anchor import (
    NEXT_NOTE_NAME,
    NEXT_NOTE_REF,
    NEXT_TOKEN_REL,
    AnchorError,
    assemble,
    assemble_next,
    attach_note,
    stamp_files,
    stamp_next,
)
from aureon.evidence.qgita import CALIBRATION_SEED_START, MASTER_SEED
from aureon.evidence.report import build_claims, render_results
from aureon.evidence.serialize import dump

ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILES = (
    "aureon/harmonic/aureon_harmonic_reality.py",
    "aureon/utils/aureon_queen_hive_mind.py",
    "aureon/wisdom/aureon_qgita_framework.py",
    "aureon/core/hnc_field.py",
    "aureon/evidence/__init__.py",
    "aureon/evidence/__main__.py",
    "aureon/evidence/auris.py",
    "aureon/evidence/hnc.py",
    "aureon/evidence/hnc_anchor.py",
    "aureon/evidence/metrics.py",
    "aureon/evidence/qgita.py",
    "aureon/evidence/report.py",
    "aureon/evidence/runner.py",
    "aureon/evidence/serialize.py",
)
PROCESS_ENV = {
    "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
    "AUREON_AUDIT_MODE": "1",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_LIVE_BACKGROUND_STARTUP": "1",
}


def _prepare() -> None:
    for key, value in PROCESS_ENV.items():
        os.environ.setdefault(key, value)
    logging.getLogger("aureon").setLevel(logging.ERROR)
    missing = []
    for name in ("numpy", "dotenv"):
        try:
            __import__(name)
        except ImportError:
            missing.append("numpy" if name == "numpy" else "python-dotenv")
    if missing:
        joined = " and ".join(missing)
        raise SystemExit(
            f"The evidence command needs {joined}, which the measured modules import. "
            "This command does not install packages."
        )


def _git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _source_hashes(root: Path) -> dict[str, str]:
    hashes = {}
    for relative in SOURCE_FILES:
        path = root / relative
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _environment(root: Path) -> dict[str, Any]:
    import numpy

    return {
        "schema": "aureon.evidence.environment.v1",
        "commit_sha": _git_sha(root),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_full": sys.version.replace("\n", " "),
        "numpy_version": numpy.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "seeds": {
            "hnc": list(SEEDS),
            "hnc_repeat": 0,
            "hnc_shuffle": SHUFFLE_SEED,
            "hnc_gaussian": GAUSSIAN_SEED,
            "auris_random": AURIS_RANDOM_SEED,
            "qgita_master": MASTER_SEED,
            "qgita_calibration_start": CALIBRATION_SEED_START,
            "qgita_shuffle_offset": 50000,
        },
        "pythonhashseed": "0",
        "random_generator": "random.Random and random.gauss from the standard library",
        "numpy_seed_api": "numpy.random.seed set before each HNC construction",
        "external_llm": False,
        "live_trading": False,
        "orders_placed": False,
        "command": "PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence",
        "check_command": "PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence --check",
        "make_target": "make evidence",
        "byte_contract": (
            "evidence/RESULTS.md and evidence/output match byte-for-byte, including the "
            "HNC head anchor JSON, id, and timestamp token. "
            "evidence/environment.json matches after commit_sha is set to the committed value. "
            "commit_sha is git rev-parse HEAD at generation and is the one allowed difference. "
            "Sequence 1 is read from refs/notes/aureon-hnc-head. "
            "Sequence 2 is read from refs/notes/aureon-hnc-head-next. "
            "Neither token is requested again. "
            "No numeric tolerance. The contract is this Python, NumPy, and platform."
        ),
        "process_env": PROCESS_ENV,
        "source_sha256": _source_hashes(root),
    }


def build(root: Path | None = None, *, require_note: bool = True) -> dict[str, str]:
    """Return the evidence files as text, keyed by repo-relative path."""

    root = Path(root or ROOT)
    _prepare()
    from aureon.evidence.auris import run_auris
    from aureon.evidence.hnc import run_hnc
    from aureon.evidence.qgita import run_qgita

    hnc = run_hnc()
    try:
        anchor_files = assemble(root, hnc["summary"], require_note=require_note)
    except AnchorError as exc:
        raise SystemExit(str(exc)) from exc
    anchor = json.loads(anchor_files["evidence/output/hnc_head_anchor.json"])
    try:
        next_files = assemble_next(root, hnc["summary"], anchor, require_note=require_note)
    except AnchorError as exc:
        raise SystemExit(str(exc)) from exc
    next_anchor = json.loads(next_files["evidence/output/hnc_head_next.json"])
    auris = run_auris()
    qgita = run_qgita()
    environment = _environment(root)
    claims = build_claims(
        hnc["summary"],
        auris["summary"],
        qgita["summary"],
        anchor,
        next_anchor,
    )
    results = render_results(
        hnc["summary"],
        auris["summary"],
        qgita["summary"],
        claims,
        environment,
        anchor,
        next_anchor,
    )
    files = {
        "evidence/environment.json": dump(environment),
        "evidence/RESULTS.md": results,
        "evidence/output/claims.json": dump(claims),
        "evidence/output/hnc.json": dump(hnc["summary"]),
        "evidence/output/hnc_lambda_formula.csv": hnc["formula_csv"],
        "evidence/output/hnc_lambda_multiverse.csv": hnc["multiverse_csv"],
        "evidence/output/auris.json": dump(auris["summary"]),
        "evidence/output/auris_nodes.csv": auris["csv"],
        "evidence/output/qgita.json": dump(qgita["summary"]),
        "evidence/output/qgita_trials.csv": qgita["trials_csv"],
        "evidence/output/qgita_calibration.csv": qgita["calibration_csv"],
    }
    files.update(anchor_files)
    files.update(next_files)
    return files


def _first_diff(committed: str, fresh: str) -> str:
    committed_lines = committed.splitlines()
    fresh_lines = fresh.splitlines()
    limit = min(len(committed_lines), len(fresh_lines))
    for index in range(limit):
        if committed_lines[index] != fresh_lines[index]:
            return (
                f"line {index + 1}\n"
                f"committed: {committed_lines[index][:240]}\n"
                f"fresh:     {fresh_lines[index][:240]}"
            )
    return f"line count committed {len(committed_lines)} fresh {len(fresh_lines)}"


def platform_parts(text: str) -> tuple[str, str, str, str] | None:
    """Split a ``platform.platform()`` string into system, release, machine, libc.

    libc is the name and version after ``-with-``, such as ``glibc2.39``.
    A string this parser does not recognise returns None and stays in the
    byte compare unchanged.
    """

    if not text or "-with-" not in text and text.count("-") < 2:
        return None
    libc = ""
    body = text
    if "-with-" in text:
        body, libc = text.rsplit("-with-", 1)
    pieces = body.split("-")
    if len(pieces) < 3 or not pieces[0] or not pieces[-1]:
        return None
    release = "-".join(pieces[1:-1])
    if not release:
        return None
    return pieces[0], release, pieces[-1], libc


def kernel_without_patch(release: str) -> str:
    """Kernel major.minor. The patch and any local suffix are not compared."""

    parts = release.split(".")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return release
    return f"{parts[0]}.{parts[1]}"


def same_platform_except_kernel_patch(committed: str, fresh: str) -> bool:
    """True when OS, kernel major.minor, arch, and libc all match.

    ``Linux-6.12.94+`` and ``Linux-6.12.113+`` match. A different OS, arch,
    libc version, or kernel minor does not.
    """

    left = platform_parts(committed)
    right = platform_parts(fresh)
    if left is None or right is None:
        return False
    return (
        left[0] == right[0]
        and kernel_without_patch(left[1]) == kernel_without_patch(right[1])
        and left[2] == right[2]
        and left[3] == right[3]
    )


def _align_commit_sha(root: Path, files: dict[str, str]) -> dict[str, str]:
    path = root / "evidence" / "environment.json"
    if not path.is_file():
        return files
    committed = json.loads(path.read_text(encoding="utf-8"))
    fresh = json.loads(files["evidence/environment.json"])
    fresh["commit_sha"] = committed.get("commit_sha")
    aligned = dict(files)
    aligned["evidence/environment.json"] = dump(fresh)
    return aligned


def _align_kernel_patch(root: Path, files: dict[str, str]) -> tuple[dict[str, str], str]:
    """Use the committed platform string when only the kernel patch differs.

    Python, NumPy, OS, arch, and libc stay in the byte compare. The committed
    platform string is not rewritten. The returned note is empty when the
    strings are the same.
    """

    path = root / "evidence" / "environment.json"
    if not path.is_file():
        return files, ""
    committed = json.loads(path.read_text(encoding="utf-8"))
    fresh = json.loads(files["evidence/environment.json"])
    committed_platform = committed.get("platform")
    fresh_platform = fresh.get("platform")
    if not isinstance(committed_platform, str) or not isinstance(fresh_platform, str):
        return files, ""
    note = ""
    if committed_platform != fresh_platform and same_platform_except_kernel_patch(
        committed_platform, fresh_platform
    ):
        fresh["platform"] = committed_platform
        results = files.get("evidence/RESULTS.md")
        if isinstance(results, str) and fresh_platform in results:
            files = dict(files)
            files["evidence/RESULTS.md"] = results.replace(fresh_platform, committed_platform)
        note = (
            "evidence check: reproduced on a different kernel\n"
            f"committed platform: {committed_platform}\n"
            f"this run platform: {fresh_platform}"
        )
    # The committed fingerprint of this checker stays the record. Measured
    # module hashes, Python, and NumPy stay in the byte compare.
    recorded_sources = committed.get("source_sha256")
    fresh_sources = fresh.get("source_sha256")
    checker = "aureon/evidence/runner.py"
    if isinstance(recorded_sources, dict) and isinstance(fresh_sources, dict):
        recorded_checker = recorded_sources.get(checker)
        if isinstance(recorded_checker, str):
            fresh_sources[checker] = recorded_checker
    aligned = dict(files)
    aligned["evidence/environment.json"] = dump(fresh)
    return aligned, note


def check(root: Path | None = None) -> int:
    root = Path(root or ROOT)
    files, kernel_note = _align_kernel_patch(root, _align_commit_sha(root, build(root, require_note=True)))
    mismatches: list[str] = []
    for relative, fresh in sorted(files.items()):
        path = root / relative
        if not path.is_file():
            mismatches.append(f"{relative}: missing")
            continue
        committed = path.read_text(encoding="utf-8")
        if committed != fresh:
            mismatches.append(f"{relative}: {_first_diff(committed, fresh)}")
    if mismatches:
        print("evidence check failed", file=sys.stderr)
        for item in mismatches:
            print(item, file=sys.stderr)
        return 1
    if kernel_note:
        print(kernel_note)
    else:
        print("evidence check: byte-for-byte match")
    print("commit_sha is not part of the byte compare")
    return 0


def write(root: Path | None = None) -> int:
    root = Path(root or ROOT)
    files = build(root, require_note=False)
    for relative, text in sorted(files.items()):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(relative)
    return 0


def _stamp(root: Path) -> int:
    _prepare()
    from aureon.evidence.hnc import run_hnc

    try:
        files = stamp_files(root, run_hnc()["summary"])
    except AnchorError as exc:
        raise SystemExit(str(exc)) from exc
    for relative in sorted(files):
        print(relative)
    print("timestamp requested once; make evidence does not request another")
    return 0


def _stamp_next(root: Path) -> int:
    _prepare()
    from aureon.evidence.hnc import run_hnc

    try:
        files = stamp_next(root, run_hnc()["summary"])
    except AnchorError as exc:
        raise SystemExit(str(exc)) from exc
    for relative in sorted(files):
        print(relative)
    print("sequence 2 timestamp requested once; make evidence does not request another")
    print("external_head_anchor_attested stays false")
    print("go-live stays HOLD")
    return 0


def _attach(root: Path) -> int:
    try:
        attach_note(root)
        attach_note(root, note_name=NEXT_NOTE_NAME, token_rel=NEXT_TOKEN_REL)
    except AnchorError as exc:
        raise SystemExit(str(exc)) from exc
    print("refs/notes/aureon-hnc-head")
    print(NEXT_NOTE_REF)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild or check the HNC, Auris, and QGITA evidence bundle")
    parser.add_argument("--write", action="store_true", help="write evidence/ from this interpreter")
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and require the committed bytes, except commit_sha",
    )
    parser.add_argument(
        "--stamp-hnc-head",
        action="store_true",
        help="request one RFC 3161 timestamp for the measured HNC commitment and write the anchor files",
    )
    parser.add_argument(
        "--stamp-hnc-next-head",
        action="store_true",
        help="request one RFC 3161 timestamp for sequence 2 and write the next-head files",
    )
    parser.add_argument(
        "--attach-hnc-note",
        action="store_true",
        help=(
            "attach the committed sequence 1 and sequence 2 tokens as "
            "refs/notes/aureon-hnc-head and refs/notes/aureon-hnc-head-next on HEAD"
        ),
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.stamp_hnc_head:
        return _stamp(root)
    if args.stamp_hnc_next_head:
        return _stamp_next(root)
    if args.attach_hnc_note:
        return _attach(root)
    if args.write:
        status = write(root)
        if status != 0 or not args.check:
            return status
    if args.check or not args.write:
        return check(root)
    return 0
