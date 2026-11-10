"""Disk hygiene for the self-repair loop (owner's call, 12:30 GMT).

The repair child runs every 30s; without housekeeping its pytest scratch, journal
dirs, held branches and append-only state logs fill the disk until the suite
crashes. This cleaner runs at the end of every cycle and right after a fix is
banked, and a disk guard cleans first and skips the suite when free space is low.

It only ever touches Aureon's OWN artifacts: her pytest base-temp dirs
(``aureon_self_repair_pytest_*``), her journal dirs (``aureon-pytest-journal-*``),
her ``aureon-self-repair/<ts>`` branches and her ``state/`` logs. It never touches
another agent's scratch (e.g. ``/tmp/spike277``), ``.env`` or any ``quarantine``
path, and it never drops data for cycles with banked fixes or the ledger, attempt
and diagnosis files — large logs are gzip-archived whole, then trimmed to a tail,
so nothing is lost.
"""

from __future__ import annotations

import gzip
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

BASETEMP_PREFIX = "aureon_self_repair_pytest_"
JOURNAL_PREFIX = "aureon-pytest-journal-"
BRANCH_PREFIX = "aureon-self-repair/"

# Never rotate these: they are the memory later cycles build on.
PROTECTED_LOGS = {"queen_repair_progress.jsonl", "queen_repair_attempts.jsonl",
                  "queen_repair_diagnosis.json"}
LOG_SIZE_CAP = 200 * 1024 * 1024       # rotate an append-only log past 200 MB
LOG_TAIL_BYTES = 20 * 1024 * 1024      # keep the most recent 20 MB live
JOURNAL_MAX_AGE_S = 3600               # journals older than 1h are stale
KEEP_RECENT_BRANCHES = 5
MIN_FREE_BYTES = 5 * 1024 * 1024 * 1024  # disk guard threshold (~5 GB)

# Any path containing one of these is off-limits, full stop.
_FORBIDDEN = ("spike277", "quarantine", ".env")


def free_bytes(path: str | Path = "/") -> int:
    try:
        st = os.statvfs(str(path))
    except OSError:
        return MIN_FREE_BYTES  # unknown -> do not trigger destructive action
    return st.f_bavail * st.f_frsize


def _ours(path: Path) -> bool:
    s = str(path)
    return not any(token in s for token in _FORBIDDEN)


def _in_use(path: Path) -> bool:
    """True if any live process has this path as cwd, in its cmdline, or open."""
    target = str(path)
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return False
    for pid in pids:
        base = f"/proc/{pid}"
        try:
            if os.readlink(f"{base}/cwd").startswith(target):
                return True
        except OSError:
            pass
        try:
            with open(f"{base}/cmdline", "rb") as handle:
                if target.encode() in handle.read():
                    return True
        except OSError:
            pass
        try:
            fd_dir = f"{base}/fd"
            for fd in os.listdir(fd_dir):
                try:
                    if os.readlink(f"{fd_dir}/{fd}").startswith(target):
                        return True
                except OSError:
                    pass
        except OSError:
            pass
    return False


def sweep_basetemps(keep: Path | None = None) -> list[str]:
    """Remove her pytest base-temp dirs that no live process is using (keep the given one)."""
    tmp = Path(tempfile.gettempdir())
    removed: list[str] = []
    keep_resolved = keep.resolve() if keep else None
    try:
        entries = list(tmp.glob(BASETEMP_PREFIX + "*"))
    except OSError:
        return removed
    for entry in entries:
        if not _ours(entry):
            continue
        try:
            if keep_resolved and entry.resolve() == keep_resolved:
                continue
        except OSError:
            continue
        if _in_use(entry):
            continue
        shutil.rmtree(entry, ignore_errors=True)
        removed.append(str(entry))
    return removed


def sweep_journals(max_age_s: int = JOURNAL_MAX_AGE_S) -> list[str]:
    """Remove stale journal dirs older than max_age_s that no live process is using."""
    tmp = Path(tempfile.gettempdir())
    removed: list[str] = []
    now = time.time()
    try:
        entries = list(tmp.glob(JOURNAL_PREFIX + "*"))
    except OSError:
        return removed
    for entry in entries:
        if not _ours(entry):
            continue
        try:
            if now - entry.stat().st_mtime < max_age_s:
                continue
        except OSError:
            continue
        if _in_use(entry):
            continue
        if entry.is_dir():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            try:
                entry.unlink()
            except OSError:
                continue
        removed.append(str(entry))
    return removed


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=60)


def prune_branches(root: Path, keep_recent: int = KEEP_RECENT_BRANCHES) -> list[str]:
    """Delete held, no-fix self-repair branches; keep ones with a banked fix and the last few."""
    if not (root / ".git").exists():
        return []
    current = (_git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
    listing = _git(root, "for-each-ref", "--sort=-committerdate",
                   "--format=%(refname:short)%09%(contents:subject)",
                   f"refs/heads/{BRANCH_PREFIX}")
    deleted: list[str] = []
    rows = [line for line in (listing.stdout or "").splitlines() if line.strip()]
    for index, line in enumerate(rows):
        name, _, subject = line.partition("\t")
        if index < keep_recent or name == current:
            continue
        if subject.startswith("self-repair"):  # a banked fix lives here; keep it
            continue
        if _git(root, "branch", "-D", name).returncode == 0:
            deleted.append(name)
    return deleted


def rotate_logs(root: Path, cap: int = LOG_SIZE_CAP, tail: int = LOG_TAIL_BYTES) -> list[str]:
    """Archive an oversized append-only state log whole to .gz, then trim it to a recent tail.

    Nothing is dropped: the gzip holds the complete file, so cycles with banked fixes keep
    their entries. The ledger, attempts and diagnosis files are never rotated.
    """
    state = root / "state"
    if not state.is_dir():
        return []
    rotated: list[str] = []
    candidates = list(state.glob("*.jsonl")) + list(state.glob("*.log"))
    for log in candidates:
        if log.name in PROTECTED_LOGS or not _ours(log):
            continue
        try:
            size = log.stat().st_size
        except OSError:
            continue
        if size <= cap:
            continue
        archive = state / f"{log.name}.{int(time.time())}.gz"
        try:
            with log.open("rb") as src, gzip.open(archive, "wb") as dst:
                shutil.copyfileobj(src, dst)
            with log.open("rb") as handle:
                handle.seek(max(0, size - tail))
                if size > tail:
                    handle.readline()  # align to a line boundary
                keep = handle.read()
            tmp = log.with_name(log.name + ".tmp")
            tmp.write_bytes(keep)
            os.replace(tmp, log)
            rotated.append(str(archive))
        except OSError:
            continue
    return rotated


def clean_cycle(root: Path, *, keep_basetemp: Path | None = None) -> dict[str, Any]:
    """End-of-cycle (and post-bank) housekeeping. Never raises into the repair loop."""
    summary: dict[str, Any] = {"basetemps": [], "journals": [], "branches": [], "logs": []}
    try:
        summary["basetemps"] = sweep_basetemps(keep=keep_basetemp)
    except Exception:
        pass
    try:
        summary["journals"] = sweep_journals()
    except Exception:
        pass
    try:
        summary["branches"] = prune_branches(root)
    except Exception:
        pass
    try:
        summary["logs"] = rotate_logs(root)
    except Exception:
        pass
    summary["free_bytes"] = free_bytes(root)
    return summary


def ensure_space(root: Path, min_free: int = MIN_FREE_BYTES) -> dict[str, Any]:
    """Disk guard: if free space is low, clean first. Returns {'ok', 'free_bytes', 'cleaned'}."""
    before = free_bytes(root)
    if before >= min_free:
        return {"ok": True, "free_bytes": before, "cleaned": None}
    cleaned = clean_cycle(root)
    after = free_bytes(root)
    return {"ok": after >= min_free, "free_bytes": after, "cleaned": cleaned}
