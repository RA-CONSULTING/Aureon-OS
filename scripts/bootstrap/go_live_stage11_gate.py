#!/usr/bin/env python3
"""Stage 11 gate for release-boundary installers and the cloud master launcher.

Stdlib only. Run with ``python -I -S -B``. This file does not import Aureon,
does not write a go-live flag, does not edit the README badge, does not move
the public pin, and does not claim the system is alive.

``go_live_clear`` is computed. It is true only when receipts 1–5 all verify
against the current git HEAD. A receipt's recorded tip matches when it is
HEAD, or when the only paths that differ between that tip and HEAD are the
receipt and measured files in ``TIP_DELTA_ALLOWLIST``. Any other path fails
that receipt. A JSON flag, an environment variable, or a receipt that merely
says ``go_live_clear: true`` does not clear the gate.

The public pin is ``PINNED_COMMIT`` in ``mcp/aureon_public/guard_loader.py``.
This module does not hard-code a second pin and does not write that file.

When the computed flag is true, ``--launch-contained`` replaces this process
with ``python -m aureon.containment.cold_boot``. That is the contained
process named by receipt 1. It is not a trading launcher and it places no
order. While the flag is false, callers keep the isolated bootstrap and do
not import a target.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

SCHEMA = "aureon.go-live.stage11-installer-gate.v1"
PIN_SOURCE_REL = "mcp/aureon_public/guard_loader.py"
_PIN_LINE = re.compile(r'^PINNED_COMMIT = "([0-9a-f]{40})"$', re.MULTILINE)
NOTE_REF = "refs/notes/aureon-hnc-head"
NOTE_NAME = "aureon-hnc-head"
NEXT_NOTE_NAME = "aureon-hnc-head-next"
TOKEN_REL = "evidence/output/hnc_head_anchor.tsr.b64"
NEXT_TOKEN_REL = "evidence/output/hnc_head_next.tsr.b64"
# The commit that recorded these files is where the notes may live. HEAD is
# not required to carry them. A squash leaves the notes on that commit.
RECORDED_HNC_PATHS = (
    "evidence/output/hnc_head_anchor.json",
    "evidence/output/hnc_head_anchor.id",
    "evidence/output/hnc_head_anchor.tsr.b64",
    "evidence/output/hnc_head_next.json",
    "evidence/output/hnc_head_next.id",
    "evidence/output/hnc_head_next.tsr.b64",
)
NOTE_PAIRS = (
    (NOTE_NAME, TOKEN_REL),
    (NEXT_NOTE_NAME, NEXT_TOKEN_REL),
)
NOTE_REATTACH = (
    "the same token bytes must be re-attached on the frozen release head, "
    "with no new timestamp request"
)
# Receipts 2 and 4 name this tip. It is a pre-squash commit from the #253
# branch and is not on main. A clone of main fails closed. Do not rewrite it.
PRE_SQUASH_TIP = "b2b0310362597dc520114de86d8700c0c50758d5"
PRE_SQUASH_NOTE = "pre-squash commit from the #253 branch, not on main"
FLAG_FILE = "measured/go_live_clear.json"
SUPPORTED_MODULE = "aureon.containment.cold_boot"

# The runner on main writes this path. This module reads it and does not create it.
RECEIPT5_REL = "reports/measured/go_live_receipt5_deployment.json"
RECEIPT5_SCHEMA = "aureon.go-live.deployment-receipt.v1"

# A committed receipt names the tip it measured, which cannot be the commit
# that adds the receipt. Those paths, and only those paths, may differ between
# the recorded tip and HEAD. A code file, a runbook, or any other path fails.
TIP_DELTA_ALLOWLIST = frozenset(
    {
        "reports/measured/native_process_containment.json",
        "reports/measured/native_process_containment.md",
        "measured/go_live_stage6_provenance.json",
        "measured/go_live_stage6_source_census.json",
        "evidence/output/hnc_head_anchor.json",
        "evidence/output/hnc_head_anchor.id",
        "evidence/output/hnc_head_anchor.tsr.b64",
        "evidence/output/hnc_head_next.json",
        "evidence/output/hnc_head_next.id",
        "evidence/output/hnc_head_next.tsr.b64",
        "reports/measured/go_live_receipt5_deployment.json",
        "reports/measured/go_live_receipt5_deployment.md",
    }
)

RECEIPTS: tuple[dict[str, Any], ...] = (
    {
        "id": 1,
        "name": "native process containment with a zero-network default",
        "path": "reports/measured/native_process_containment.json",
        "schema": "aureon.measured.native-process-containment.v1",
        "tip_field": "git_head_at_measurement",
    },
    {
        "id": 2,
        "name": "exact target-source measurement and immutable release provenance",
        "path": "measured/go_live_stage6_provenance.json",
        "schema": "aureon.go-live.release-provenance.v1",
        "tip_field": "tip",
    },
    {
        "id": 3,
        "name": "durable HNC evidence with an external monotonic head anchor",
        "path": "evidence/output/hnc_head_anchor.json",
        "schema": "aureon.evidence.hnc-head-anchor.v1",
        "tip_field": "notes on the commit that recorded the HNC anchor files",
    },
    {
        "id": 4,
        "name": "complete source-boundary census closure",
        "path": "measured/go_live_stage6_source_census.json",
        "schema": "aureon.go-live.source-boundary-census.v1",
        "tip_field": "tip",
    },
    {
        "id": 5,
        "name": "authenticated deployment receipt and provider-side read-back",
        "path": RECEIPT5_REL,
        "schema": RECEIPT5_SCHEMA,
        "tip_field": "git_head_at_measurement",
    },
)

_BLOCKING_CENSUS_GAPS = frozenset({"post_pin_checkout_not_in_closure"})


def published_require_pin(root: Path) -> str | None:
    """Read the one published require-pin. A missing or unreadable source is None."""

    path = root / PIN_SOURCE_REL
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = _PIN_LINE.search(text)
    if match is None:
        return None
    return match.group(1)


def _repo_root() -> Path:
    script = Path(__file__).resolve()
    root = script.parents[2]
    expected = (root / "scripts" / "bootstrap" / "go_live_stage11_gate.py").resolve()
    if script != expected or not expected.is_file():
        raise ValueError("fixed_stage11_gate_path_invalid")
    return root


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex_n(value: object, size: int) -> bool:
    return isinstance(value, str) and len(value) == size and all(
        char in "0123456789abcdef" for char in value
    )


def _hex64(value: object) -> bool:
    return _hex_n(value, 64)


def _git_id(value: object) -> bool:
    return _hex_n(value, 40) or _hex_n(value, 64)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(body, dict):
        return None
    return body


class RealGit:
    """Read-only git lookups. A missing object is None, not a network fetch."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _out(self, args: list[str]) -> bytes | None:
        try:
            return subprocess.check_output(
                ["git", "-C", str(self.root), *args],
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            return None

    def head(self) -> str | None:
        raw = self._out(["rev-parse", "HEAD"])
        if raw is None:
            return None
        text = raw.decode("ascii", "replace").strip()
        if not _git_id(text):
            return None
        return text

    def note(self) -> bytes | None:
        return self._out(["notes", "--ref", NOTE_NAME, "show", "HEAD"])

    def head_blob(self, relative: str) -> bytes | None:
        return self._out(["show", f"HEAD:{relative}"])

    def changed_paths(self, tip: str, head: str) -> list[str] | None:
        """Paths that differ between two commits. None when either commit is missing."""

        if not _git_id(tip) or not _git_id(head):
            return None
        raw = self._out(["diff", "--name-only", "--no-renames", "-z", tip, head])
        if raw is None:
            return None
        paths: list[str] = []
        for part in raw.split(b"\0"):
            if not part:
                continue
            text = part.decode("utf-8", "replace")
            if text not in paths:
                paths.append(text)
        return paths

    def recorded_hnc_commit(self) -> str | None:
        """Latest HEAD commit that recorded the anchor files and hnc_head_next.*."""

        raw = self._out(["log", "-1", "--format=%H", "HEAD", "--", *RECORDED_HNC_PATHS])
        if raw is None:
            return None
        text = raw.decode("ascii", "replace").strip()
        if not _git_id(text):
            return None
        return text

    def is_ancestor(self, commit: str, head: str) -> bool | None:
        if not _git_id(commit) or not _git_id(head):
            return None
        try:
            subprocess.check_call(
                ["git", "-C", str(self.root), "merge-base", "--is-ancestor", commit, head],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as exc:
            if exc.returncode == 1:
                return False
            return None
        except OSError:
            return None
        return True

    def note_at(self, commit: str, name: str) -> bytes | None:
        if not _git_id(commit):
            return None
        return self._out(["notes", "--ref", name, "show", commit])

    def blob_at(self, commit: str, relative: str) -> bytes | None:
        if not _git_id(commit):
            return None
        return self._out(["show", f"{commit}:{relative}"])


def _unique(reasons: list[str]) -> list[str]:
    seen: list[str] = []
    for item in reasons:
        if item not in seen:
            seen.append(item)
    return seen


def _row(
    spec: dict[str, Any],
    *,
    present: bool,
    verified: bool,
    reasons: list[str],
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cleaned = _unique(reasons)
    return {
        "id": spec["id"],
        "name": spec["name"],
        "path": spec["path"],
        "schema": spec["schema"],
        "tip_field": spec["tip_field"],
        "present": present,
        "verified_on_tip": bool(verified) and not cleaned,
        "reasons": cleaned,
        "detail": detail or {},
    }


def _safety(
    body: dict[str, Any], reasons: list[str], *, pin_field: str, pin: str | None
) -> None:
    if body.get("system_alive") is True:
        reasons.append("system_alive_claimed")
    if body.get("live_trading") is True:
        reasons.append("live_trading_claimed")
    if body.get("orders_placed") is True:
        reasons.append("orders_placed_claimed")
    if not isinstance(pin, str) or body.get(pin_field) != pin:
        reasons.append("pin_mismatch")


def _require_identity(
    body: dict[str, Any], spec: dict[str, Any], reasons: list[str]
) -> None:
    if body.get("schema") != spec["schema"]:
        reasons.append("schema_mismatch")
    if body.get("receipt") != spec["id"]:
        reasons.append("receipt_number_mismatch")


def _tip_matches(
    body: dict[str, Any],
    field: str,
    head: str | None,
    reasons: list[str],
    git: Any,
    detail: dict[str, Any] | None = None,
) -> None:
    """Pass when the recorded tip is HEAD, or the delta is only receipt files."""

    recorded = body.get(field)
    if detail is not None:
        detail["recorded_tip"] = recorded
        if recorded == PRE_SQUASH_TIP and recorded != head:
            detail["tip_note"] = PRE_SQUASH_NOTE
    if head is None:
        reasons.append("head_unresolved")
        return
    if recorded == head:
        if detail is not None:
            detail["tip_diff"] = "head"
        return
    changed = _changed_paths(git, recorded, head)
    if changed is None:
        if detail is not None:
            detail["tip_diff"] = "unavailable"
        reasons.append("tip_is_not_head")
        return
    outside = [path for path in changed if path not in TIP_DELTA_ALLOWLIST]
    if outside:
        if detail is not None:
            detail["tip_diff"] = "outside_allowlist"
            detail["tip_outside_allowlist_count"] = len(outside)
        reasons.append("tip_is_not_head")
        return
    if detail is not None:
        detail["tip_diff"] = "allowlist"


def _changed_paths(git: Any, tip: object, head: str) -> list[str] | None:
    if not isinstance(tip, str):
        return None
    method = getattr(git, "changed_paths", None)
    if not callable(method):
        return None
    try:
        changed = method(tip, head)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        return None
    if not isinstance(changed, list) or not all(isinstance(item, str) for item in changed):
        return None
    return changed


def _check_receipt1(
    root: Path, spec: dict[str, Any], head: str | None, git: Any, pin: str | None
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    detail: dict[str, Any] = {}
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin", pin=pin)
    _tip_matches(body, "git_head_at_measurement", head, reasons, git, detail)
    if body.get("worktree_dirty_at_measurement") is not False:
        reasons.append("worktree_dirty_at_measurement")
    if body.get("verdict") != "pass":
        reasons.append("verdict_not_pass")
    if body.get("allowed_at_default") != "none":
        reasons.append("network_not_denied")
    argv = body.get("cold_boot_argv")
    if body.get("cold_boot_argv_has_net") is not True or not (
        isinstance(argv, list) and "--net" in argv
    ):
        reasons.append("zero_network_default_unproven")
    if body.get("market_data_fetched") is True or body.get("pin_changed") is True:
        reasons.append("measurement_bounds_broken")
    tags = body.get("tags")
    if not isinstance(tags, dict) or tags.get("system_alive") != "not claimed":
        reasons.append("system_alive_not_disclaimed")
    hashes = body.get("source_sha256")
    if not isinstance(hashes, dict) or not hashes:
        reasons.append("source_hash_mismatch")
    else:
        for relative, digest in hashes.items():
            if not isinstance(relative, str) or not _hex64(digest):
                reasons.append("source_hash_mismatch")
                break
            file_path = root / relative
            try:
                current = _sha256(file_path.read_bytes())
            except OSError:
                reasons.append("source_hash_mismatch")
                break
            if current != digest:
                reasons.append("source_hash_mismatch")
                break
    detail["recorded_head"] = body.get("git_head_at_measurement")
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail=detail,
    )


def _digest_ok(body: dict[str, Any]) -> bool:
    recorded = body.get("digest")
    if not _hex64(recorded):
        return False
    payload = {key: value for key, value in body.items() if key != "digest"}
    return _sha256(_canonical(payload)) == recorded


def _check_receipt2(
    root: Path, spec: dict[str, Any], head: str | None, git: Any, pin: str | None
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    detail: dict[str, Any] = {}
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin", pin=pin)
    _tip_matches(body, "tip", head, reasons, git, detail)
    if body.get("aureon_trees_match") is not True:
        reasons.append("target_tree_not_measured")
    if body.get("inventory_blobs_match") is not True:
        reasons.append("inventory_not_measured")
    if not _hex64(body.get("release_tree_sha256")):
        reasons.append("release_tree_sha256_missing")
    if not _digest_ok(body):
        reasons.append("digest_mismatch")
    detail["digest_ok"] = _digest_ok(body)
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail=detail,
    )


def _recorded_notes(git: Any, head: str | None, reasons: list[str], detail: dict[str, Any]) -> None:
    """Accept notes on the recording commit when it is an ancestor and bytes match."""

    method = getattr(git, "recorded_hnc_commit", None)
    recorded = method() if callable(method) else None
    detail["note_commit"] = recorded if isinstance(recorded, str) else None
    if head is None:
        reasons.append("head_unresolved")
        return
    if not isinstance(recorded, str) or not _git_id(recorded):
        reasons.append(NOTE_REATTACH)
        return
    ancestor_fn = getattr(git, "is_ancestor", None)
    ancestor = ancestor_fn(recorded, head) if callable(ancestor_fn) else None
    detail["note_commit_is_ancestor"] = ancestor is True
    if ancestor is not True:
        reasons.append("note_commit_not_ancestor")
        return
    saw_note = False
    mismatch = False
    for name, path in NOTE_PAIRS:
        note_fn = getattr(git, "note_at", None)
        blob_fn = getattr(git, "blob_at", None)
        note = note_fn(recorded, name) if callable(note_fn) else None
        blob = blob_fn(recorded, path) if callable(blob_fn) else None
        if isinstance(note, (bytes, bytearray)) and len(note) > 0:
            saw_note = True
        if not isinstance(note, (bytes, bytearray)) or not isinstance(blob, (bytes, bytearray)) or bytes(note) != bytes(blob):
            mismatch = True
    detail["notes_match"] = saw_note and not mismatch
    if not saw_note:
        reasons.append(NOTE_REATTACH)
        return
    if mismatch:
        reasons.append("note_bytes_mismatch")


def _check_receipt3(
    root: Path,
    spec: dict[str, Any],
    head: str | None,
    git: Any,
    pin: str | None,
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="public_require_pin", pin=pin)
    if head is None:
        reasons.append("head_unresolved")
    if body.get("tag") != "measured":
        reasons.append("not_measured")
    if body.get("hnc_identity_changed") is not False:
        reasons.append("hnc_identity_changed")
    external = body.get("external")
    if not isinstance(external, dict) or external.get("provider_contacted_by_check") is not False:
        reasons.append("timestamp_check_contacted_provider")
    if not isinstance(external, dict) or external.get("kind") != "rfc3161":
        reasons.append("external_timestamp_missing")
    anchor_id = body.get("anchor_id")
    token_path = root / TOKEN_REL
    try:
        token_text = token_path.read_text(encoding="ascii")
        token = base64.b64decode(token_text.strip(), validate=True)
    except (OSError, UnicodeError, ValueError):
        token = b""
        reasons.append("token_hash_mismatch")
    if token and _sha256(token) != anchor_id:
        reasons.append("token_hash_mismatch")
    id_path = root / "evidence" / "output" / "hnc_head_anchor.id"
    try:
        recorded_id = id_path.read_text(encoding="ascii").strip()
    except OSError:
        recorded_id = ""
    if recorded_id != anchor_id:
        reasons.append("anchor_id_file_mismatch")
    detail: dict[str, Any] = {"note_ref": NOTE_REF, "next_note_ref": f"refs/notes/{NEXT_NOTE_NAME}"}
    _recorded_notes(git, head, reasons, detail)
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail=detail,
    )


def _check_receipt4(
    root: Path,
    spec: dict[str, Any],
    head: str | None,
    provenance_digest: str | None,
    git: Any,
    pin: str | None,
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    detail: dict[str, Any] = {}
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin", pin=pin)
    _tip_matches(body, "tip", head, reasons, git, detail)
    if body.get("source_boundary_closed") is not True:
        reasons.append("source_boundary_not_closed")
    if body.get("missing_from_source") != []:
        reasons.append("census_missing_source")
    gaps = body.get("open_gaps")
    gap_ids: list[str] = []
    if isinstance(gaps, list):
        for gap in gaps:
            if isinstance(gap, dict) and isinstance(gap.get("id"), str):
                gap_ids.append(gap["id"])
    if _BLOCKING_CENSUS_GAPS.intersection(gap_ids):
        reasons.append("post_pin_checkout_not_in_closure")
    recorded = body.get("provenance_digest")
    if not _hex64(recorded):
        reasons.append("provenance_digest_missing")
    elif provenance_digest is not None and recorded != provenance_digest:
        reasons.append("provenance_digest_mismatch")
    detail["open_gap_ids"] = gap_ids
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail=detail,
    )


def _check_receipt5(
    root: Path, spec: dict[str, Any], head: str | None, git: Any, pin: str | None
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(
            spec,
            present=path.is_file(),
            verified=False,
            reasons=["artifact_absent"],
            detail={"created_by_this_gate": False},
        )
    reasons: list[str] = []
    detail: dict[str, Any] = {
        "created_by_this_gate": False,
        "receipt_5_complete": body.get("receipt_5_complete"),
        "provider_readback_digest_present": _hex64(body.get("provider_readback_digest")),
    }
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin", pin=pin)
    if body.get("system_alive_claimed") is True:
        reasons.append("system_alive_claimed")
    _tip_matches(body, "git_head_at_measurement", head, reasons, git, detail)
    if body.get("receipt_5_complete") is not True:
        reasons.append("receipt_5_incomplete")
    if not _hex64(body.get("provider_readback_digest")):
        reasons.append("provider_readback_digest_missing")
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail=detail,
    )


def evaluate(root: Path, git: Any | None = None) -> dict[str, Any]:
    """Return the stage 11 decision for ``root``. Does not write and does not launch."""

    client = git if git is not None else RealGit(root)
    head = client.head()
    pin = published_require_pin(root)
    specs = {item["id"]: item for item in RECEIPTS}
    receipt1 = _check_receipt1(root, specs[1], head, client, pin)
    receipt2 = _check_receipt2(root, specs[2], head, client, pin)
    provenance = _load_json(root / specs[2]["path"])
    provenance_digest = None
    if provenance is not None and _digest_ok(provenance):
        provenance_digest = provenance.get("digest")
    receipt3 = _check_receipt3(root, specs[3], head, client, pin)
    digest = provenance_digest if isinstance(provenance_digest, str) else None
    receipt4 = _check_receipt4(root, specs[4], head, digest, client, pin)
    receipt5 = _check_receipt5(root, specs[5], head, client, pin)
    rows = [receipt1, receipt2, receipt3, receipt4, receipt5]
    verified = [row["id"] for row in rows if row["verified_on_tip"] is True]
    go_live_clear = verified == [1, 2, 3, 4, 5]
    flag_path = root / FLAG_FILE
    flag_present = flag_path.is_file()
    readme = ""
    readme_path = root / "README.md"
    try:
        readme = readme_path.read_text(encoding="utf-8")
    except OSError:
        readme = ""
    readme_badge = "HOLD" if "release%20boundary-HOLD-orange" in readme else "other"
    return {
        "schema": SCHEMA,
        "head": head,
        "public_pin": pin,
        "pin_moved": False,
        "go_live_clear": go_live_clear,
        "decision": "CLEAR" if go_live_clear else "HOLD",
        "badge": "CLEAR" if go_live_clear else "HOLD",
        "readme_badge": readme_badge,
        "readme_edited": False,
        "badge_edit_required": bool(go_live_clear and readme_badge == "HOLD"),
        "system_alive": False,
        "live_trading": False,
        "orders_placed": False,
        "supported_module": SUPPORTED_MODULE,
        "supported_path_taken": False,
        "flag_file": {
            "path": FLAG_FILE,
            "present": flag_present,
            "honored": False,
            "reason": (
                "a boolean flag is not a receipt; go_live_clear is computed "
                "only when receipts 1-5 verify against this HEAD"
            ),
        },
        "verified_ids": verified,
        "receipts": rows,
    }


def supported_argv(executable: str | None = None) -> list[str]:
    """Argv for the contained cold boot. Not a trading command."""

    return [executable or sys.executable, "-m", SUPPORTED_MODULE]


def launch_contained(root: Path, git: Any | None = None, execv: Callable[..., None] | None = None) -> int:
    """Replace this process with the contained cold boot only when the gate is clear."""

    result = evaluate(root, git)
    if result["go_live_clear"] is not True:
        print(
            "stage 11 gate is HOLD; contained cold boot was not started",
            file=sys.stderr,
        )
        return 1
    if (
        result["system_alive"] is not False
        or result["live_trading"] is not False
        or result["orders_placed"] is not False
    ):
        print("stage 11 gate refused a live or trading launch", file=sys.stderr)
        return 1
    argv = supported_argv()
    os.chdir(root)
    (execv or os.execv)(argv[0], argv)
    return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 0 only when go_live_clear")
    parser.add_argument("--json", action="store_true", help="print the evaluation JSON")
    parser.add_argument(
        "--launch-contained",
        action="store_true",
        help="exec the contained cold boot only when the gate is clear",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.check and not args.json and not args.launch_contained:
        args.check = True
    try:
        root = _repo_root()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.launch_contained and not args.json and not args.check:
        return launch_contained(root)
    result = evaluate(root)
    if args.json or not args.check:
        print(json.dumps(result, sort_keys=True, indent=2))
    if args.launch_contained:
        return launch_contained(root)
    return 0 if result["go_live_clear"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
