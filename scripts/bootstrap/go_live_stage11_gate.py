#!/usr/bin/env python3
"""Stage 11 gate for release-boundary installers and the cloud master launcher.

Stdlib only. Run with ``python -I -S -B``. This file does not import Aureon,
does not write a go-live flag, does not edit the README badge, does not move
the public pin, and does not claim the system is alive.

``go_live_clear`` is computed. It is true only when receipts 1–5 all verify
on the current git HEAD. A JSON flag, an environment variable, or a receipt
that merely says ``go_live_clear: true`` does not clear the gate.

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
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

PUBLIC_PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
SCHEMA = "aureon.go-live.stage11-installer-gate.v1"
NOTE_REF = "refs/notes/aureon-hnc-head"
NOTE_NAME = "aureon-hnc-head"
TOKEN_REL = "evidence/output/hnc_head_anchor.tsr.b64"
FLAG_FILE = "measured/go_live_clear.json"
SUPPORTED_MODULE = "aureon.containment.cold_boot"

# Receipt 5 has no artifact on this tip. This is the path a later measurement
# must use. This module does not create that file.
RECEIPT5_REL = "measured/go_live_receipt5_authenticated_deployment.json"

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
        "tip_field": "refs/notes/aureon-hnc-head on HEAD",
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
        "schema": "aureon.go-live.authenticated-deployment-receipt.v1",
        "tip_field": "tip",
    },
)

_BLOCKING_CENSUS_GAPS = frozenset({"post_pin_checkout_not_in_closure"})
_REJECTED_PROVIDERS = frozenset(
    {"", "local", "localhost", "bootstrap", "isolated", "self", "unspecified"}
)


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


def _safety(body: dict[str, Any], reasons: list[str], *, pin_field: str) -> None:
    if body.get("system_alive") is True:
        reasons.append("system_alive_claimed")
    if body.get("live_trading") is True:
        reasons.append("live_trading_claimed")
    if body.get("orders_placed") is True:
        reasons.append("orders_placed_claimed")
    if body.get(pin_field) != PUBLIC_PIN:
        reasons.append("pin_mismatch")


def _require_identity(
    body: dict[str, Any], spec: dict[str, Any], reasons: list[str]
) -> None:
    if body.get("schema") != spec["schema"]:
        reasons.append("schema_mismatch")
    if body.get("receipt") != spec["id"]:
        reasons.append("receipt_number_mismatch")


def _tip_matches(body: dict[str, Any], field: str, head: str | None, reasons: list[str]) -> None:
    if head is None:
        reasons.append("head_unresolved")
        return
    if body.get(field) != head:
        reasons.append("tip_is_not_head")


def _check_receipt1(
    root: Path, spec: dict[str, Any], head: str | None
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin")
    _tip_matches(body, "git_head_at_measurement", head, reasons)
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
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail={"recorded_head": body.get("git_head_at_measurement")},
    )


def _digest_ok(body: dict[str, Any]) -> bool:
    recorded = body.get("digest")
    if not _hex64(recorded):
        return False
    payload = {key: value for key, value in body.items() if key != "digest"}
    return _sha256(_canonical(payload)) == recorded


def _check_receipt2(
    root: Path, spec: dict[str, Any], head: str | None
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin")
    _tip_matches(body, "tip", head, reasons)
    if body.get("aureon_trees_match") is not True:
        reasons.append("target_tree_not_measured")
    if body.get("inventory_blobs_match") is not True:
        reasons.append("inventory_not_measured")
    if not _hex64(body.get("release_tree_sha256")):
        reasons.append("release_tree_sha256_missing")
    if not _digest_ok(body):
        reasons.append("digest_mismatch")
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail={"recorded_tip": body.get("tip"), "digest_ok": _digest_ok(body)},
    )


def _check_receipt3(
    root: Path,
    spec: dict[str, Any],
    head: str | None,
    note: bytes | None,
    blob: bytes | None,
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="public_require_pin")
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
    if note is None or blob is None:
        reasons.append("note_missing_on_head")
    elif note != blob:
        reasons.append("note_differs_from_blob")
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail={
            "note_ref": NOTE_REF,
            "note_on_head": note is not None and blob is not None and note == blob,
        },
    )


def _check_receipt4(
    root: Path, spec: dict[str, Any], head: str | None, provenance_digest: str | None
) -> dict[str, Any]:
    path = root / spec["path"]
    body = _load_json(path)
    if body is None:
        return _row(spec, present=path.is_file(), verified=False, reasons=["artifact_absent"])
    reasons: list[str] = []
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin")
    _tip_matches(body, "tip", head, reasons)
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
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail={"recorded_tip": body.get("tip"), "open_gap_ids": gap_ids},
    )


def _check_receipt5(
    root: Path, spec: dict[str, Any], head: str | None
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
    _require_identity(body, spec, reasons)
    _safety(body, reasons, pin_field="pin")
    _tip_matches(body, "tip", head, reasons)
    if body.get("authenticated") is not True:
        reasons.append("not_authenticated")
    if body.get("provider_side_readback") is not True:
        reasons.append("provider_readback_missing")
    provider = body.get("provider")
    if not isinstance(provider, str) or provider.strip().casefold() in _REJECTED_PROVIDERS:
        reasons.append("provider_not_authenticated")
    if not _hex64(body.get("readback_body_sha256")):
        reasons.append("provider_readback_missing")
    deployment_id = body.get("deployment_id")
    if not isinstance(deployment_id, str) or not deployment_id.strip():
        reasons.append("deployment_id_missing")
    if body.get("isolated_bootstrap_receipt_is_not_this") is not True:
        reasons.append("bootstrap_receipt_is_not_deployment_receipt")
    if body.get("system_alive") is not False:
        reasons.append("system_alive_claimed")
    return _row(
        spec,
        present=True,
        verified=True,
        reasons=reasons,
        detail={"created_by_this_gate": False},
    )


def evaluate(root: Path, git: Any | None = None) -> dict[str, Any]:
    """Return the stage 11 decision for ``root``. Does not write and does not launch."""

    client = git if git is not None else RealGit(root)
    head = client.head()
    note = client.note()
    blob = client.head_blob(TOKEN_REL)
    specs = {item["id"]: item for item in RECEIPTS}
    receipt1 = _check_receipt1(root, specs[1], head)
    receipt2 = _check_receipt2(root, specs[2], head)
    provenance = _load_json(root / specs[2]["path"])
    provenance_digest = None
    if provenance is not None and _digest_ok(provenance):
        provenance_digest = provenance.get("digest")
    receipt3 = _check_receipt3(root, specs[3], head, note, blob)
    digest = provenance_digest if isinstance(provenance_digest, str) else None
    receipt4 = _check_receipt4(root, specs[4], head, digest)
    receipt5 = _check_receipt5(root, specs[5], head)
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
        "public_pin": PUBLIC_PIN,
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
                "only when receipts 1-5 verify on this HEAD"
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
