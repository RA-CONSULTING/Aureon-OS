#!/usr/bin/env python3
"""Stage 6 go-live receipts 2 and 4.

Receipt 2 is an exact content measurement of the pinned release tree, bound
to pin bb045031 and tip b2b03103. Receipt 4 compares the public inventory
with an AST scan of the paths in that pin tree. Symbols in the pin tree that
are absent from the inventory stay unlisted. Neither receipt calls Aureon,
places an order, or publishes a new reachable count.

The sweep files under measured/aureon_public_*.json stay as they are. They
name an older pin. This script reads them and does not rewrite them.
Receipt 1 at reports/measured/native_process_containment.json stays as measured.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
TIP = "b2b0310362597dc520114de86d8700c0c50758d5"
PROVENANCE_SCHEMA = "aureon.go-live.release-provenance.v1"
CENSUS_SCHEMA = "aureon.go-live.source-boundary-census.v1"
TREE_SCHEMA = "aureon.go-live.release-tree.v1"
PROVENANCE_PATH = Path("measured/go_live_stage6_provenance.json")
CENSUS_PATH = Path("measured/go_live_stage6_source_census.json")
CENSUS_MARKDOWN = Path("docs/runbooks/GO_LIVE_STAGE6_SOURCE_CENSUS.md")
SWEEP_PATH = Path("measured/aureon_public_call_sweep.json")
COMPARE_FIELDS = ("package", "server", "form", "safety", "stage", "required", "async")
# Checkout paths that are not in the pin tree. At pin bb045031 the previous
# exclusions (market_series, hnc_anchor, containment, qgita_series_rates) are
# inside the pin. They are scanned and left out of the inventory. Listing
# market_series.http_get would mark evaluation as a live public fetch and move
# that package from plan stage 2 to plan stage 4, which changes the reachable
# count. This stage does not do that.
# Files added after pin bb045031. They stay out of the inventory.
POST_PIN_CHECKOUT_PATHS = (
    "aureon/containment/_multi_user_child.py",
    "aureon/containment/multi_user_smoke.py",
)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


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


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _cat_blobs(blobs: list[str]) -> dict[str, bytes]:
    if not blobs:
        return {}
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "--batch"],
        input="".join(f"{blob}\n" for blob in blobs).encode("ascii"),
        capture_output=True,
        check=True,
    )
    out = proc.stdout
    found: dict[str, bytes] = {}
    cursor = 0
    for blob in blobs:
        newline = out.index(b"\n", cursor)
        header = out[cursor:newline].decode("ascii")
        cursor = newline + 1
        name, kind, size_text = header.split(" ")
        if name != blob or kind != "blob":
            raise RuntimeError(f"unexpected cat-file header: {header}")
        size = int(size_text)
        data = out[cursor : cursor + size]
        cursor += size
        if out[cursor : cursor + 1] != b"\n":
            raise RuntimeError("cat-file batch is missing the trailing newline")
        cursor += 1
        if _git_blob_sha1(data) != blob:
            raise RuntimeError(f"blob bytes do not match {blob}")
        found[blob] = data
    if cursor != len(out):
        raise RuntimeError("cat-file batch has trailing bytes")
    return found


def _ls_tree(commit: str, prefix: str) -> list[tuple[str, str]]:
    raw = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-tree", "-r", "-z", commit, prefix]
    )
    rows: list[tuple[str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        _mode, kind, blob = meta.decode("ascii").split(" ")
        if kind != "blob":
            raise RuntimeError(f"{path.decode()} is not a blob")
        rows.append((path.decode("utf-8"), blob))
    rows.sort(key=lambda item: item[0].encode("utf-8"))
    return rows


def _measure_prefix(commit: str, prefix: str) -> tuple[str, list[dict[str, object]], int]:
    listing = _ls_tree(commit, prefix)
    blobs = _cat_blobs([blob for _path, blob in listing])
    files: list[dict[str, object]] = []
    total = 0
    for path, blob in listing:
        data = blobs[blob]
        size = len(data)
        total += size
        files.append(
            {
                "git_blob": blob,
                "path": path,
                "sha256": _sha256(data),
                "size": size,
            }
        )
    digest = hashlib.sha256()
    digest.update((TREE_SCHEMA + "\n").encode("ascii"))
    digest.update(prefix.encode("utf-8") + b"\n")
    for item in files:
        digest.update(
            _canonical(
                {
                    "path": item["path"],
                    "sha256": item["sha256"],
                    "size": item["size"],
                }
            )
        )
    return digest.hexdigest(), files, total


def _diff_raw(left: str, right: str, prefix: str | None = None) -> list[dict[str, str]]:
    command = ["git", "-C", str(ROOT), "diff", "--raw", "--abbrev=40", "-z", left, right]
    if prefix:
        command.extend(["--", prefix])
    raw = subprocess.check_output(command)
    parts = [part for part in raw.split(b"\0") if part]
    rows: list[dict[str, str]] = []
    index = 0
    while index < len(parts):
        meta = parts[index]
        index += 1
        if index >= len(parts):
            raise RuntimeError("diff record is missing its path")
        path = parts[index]
        index += 1
        fields = meta.decode("ascii").split(" ")
        if len(fields) != 5:
            raise RuntimeError(f"unexpected diff record: {meta.decode('ascii')}")
        old_blob, new_blob, status = fields[2], fields[3], fields[4]
        if len(old_blob) != 40 or len(new_blob) != 40:
            raise RuntimeError("diff blob id is not 40 hex characters")
        item = {
            "new_blob": new_blob,
            "old_blob": old_blob,
            "path": path.decode("utf-8"),
            "status": status,
        }
        if status.startswith(("R", "C")):
            if index >= len(parts):
                raise RuntimeError("rename record is missing the new path")
            item["new_path"] = parts[index].decode("utf-8")
            index += 1
        rows.append(item)
    rows.sort(key=lambda item: item["path"].encode("utf-8"))
    return rows


def _public_texts(path: str, commit: str) -> dict[str, str]:
    text = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
        text=True,
    )
    tree = ast.parse(text)
    lines = text.splitlines()
    found: dict[str, str] = {}

    def take(node: ast.AST, name: str) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not name.startswith("_"):
            found[name] = "\n".join(lines[node.lineno - 1 : node.end_lineno])

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    take(item, f"{node.name}.{item.name}")
        else:
            take(node, getattr(node, "name", ""))
    return found


def _brain_proof_note(measured_tree_commit: str) -> str:
    path = "aureon/evaluation/brain_proof.py"
    old_blob = _git("rev-parse", f"{measured_tree_commit}:{path}")
    new_blob = _git("rev-parse", f"{PIN}:{path}")
    old_public = _public_texts(path, measured_tree_commit)
    new_public = _public_texts(path, PIN)
    changed = sorted(
        name for name in set(old_public) & set(new_public) if old_public[name] != new_public[name]
    )
    added = sorted(set(new_public) - set(old_public))
    removed = sorted(set(old_public) - set(new_public))
    return (
        f"`{path}` blob at the measured aureon tree is `{old_blob}` and at pin "
        f"`{PIN}` is `{new_blob}`. Public function source text added: {added or 'none'}. "
        f"Removed: {removed or 'none'}. Changed: {changed or 'none'}. "
        "`render_brain_markdown` is one of those public functions. "
        "This stage did not call it and did not call `evaluate_brain`."
    )


def _sweep_identity() -> dict[str, object]:
    loaded = json.loads((ROOT / SWEEP_PATH).read_text(encoding="utf-8"))
    return {
        "aureon_tree": loaded.get("aureon_tree"),
        "code_commit": loaded.get("code_commit"),
        "path": SWEEP_PATH.as_posix(),
        "pin": loaded.get("pin"),
        "pin_aureon_tree": loaded.get("pin_aureon_tree"),
        "repeated_at_pin": False,
    }


def build_provenance() -> dict[str, object]:
    pin_tree = _git("rev-parse", f"{PIN}^{{tree}}")
    tip_tree = _git("rev-parse", f"{TIP}^{{tree}}")
    pin_aureon = _git("rev-parse", f"{PIN}:aureon")
    tip_aureon = _git("rev-parse", f"{TIP}:aureon")
    pin_umt = _git("rev-parse", f"{PIN}:unified_margin_trader")
    tip_umt = _git("rev-parse", f"{TIP}:unified_margin_trader")
    release_digest, release_files, release_bytes = _measure_prefix(PIN, "aureon")
    if pin_aureon == tip_aureon:
        tip_digest = release_digest
        tip_bytes = release_bytes
        tip_file_count = len(release_files)
    else:
        tip_digest, tip_files, tip_bytes = _measure_prefix(TIP, "aureon")
        tip_file_count = len(tip_files)
    umt_digest, umt_files, umt_bytes = _measure_prefix(PIN, "unified_margin_trader")
    pin_inventory_blob = _git("rev-parse", f"{PIN}:docs/mcp/inventory.json")
    tip_inventory_blob = _git("rev-parse", f"{TIP}:docs/mcp/inventory.json")
    inventory_bytes = _cat_blobs([pin_inventory_blob])[pin_inventory_blob]
    pin_move = _diff_raw(PIN, TIP)
    sweep = _sweep_identity()
    measured_commit = str(sweep["pin"])
    aureon_delta = _diff_raw(measured_commit, PIN, "aureon")
    payload: dict[str, object] = {
        "aureon_delta_since_measured_pin": aureon_delta,
        "aureon_trees_match": pin_aureon == tip_aureon and release_digest == tip_digest,
        "decision": "HOLD",
        "go_live_clear": False,
        "inventory_blobs_match": pin_inventory_blob == tip_inventory_blob,
        "lineage_note": (
            f"Pin {PIN} is the prior main tip. "
            f"Tip {TIP} is the commit that retargets published require-pin "
            "strings onto that pin. The commit that adds this digest is not "
            "the pin and is not that tip. The digest binds the pin and tip "
            "git objects, not the working tree. The previous receipt named pin "
            "34864ff0547d2cff03e707414743a3b0cc8770b5 and tip "
            "c68a89d2a184d99582bb24310b91e024323a212c."
        ),
        "receipt_1_measured": True,
        "receipt_1_path": "reports/measured/native_process_containment.json",
        "receipt_5_state": "absent",
        "measured_call_sweep": sweep,
        "pin": PIN,
        "pin_aureon_tree": pin_aureon,
        "pin_commit_tree": pin_tree,
        "pin_inventory_git_blob": pin_inventory_blob,
        "pin_inventory_sha256": _sha256(inventory_bytes),
        "pin_move_delta": pin_move,
        "pin_move_touches_aureon": any(
            item["path"].startswith("aureon/") or item.get("new_path", "").startswith("aureon/")
            for item in pin_move
        ),
        "pin_move_touches_inventory": any(
            item["path"] == "docs/mcp/inventory.json" for item in pin_move
        ),
        "pin_unified_margin_trader_tree": pin_umt,
        "receipt": 2,
        "receipts_not_in_this_stage": [1, 3, 5],
        "release_tree_file_count": len(release_files),
        "release_tree_files": release_files,
        "release_tree_git_tree": pin_aureon,
        "release_tree_prefix": "aureon",
        "release_tree_sha256": release_digest,
        "release_tree_total_bytes": release_bytes,
        "schema": PROVENANCE_SCHEMA,
        "tip": TIP,
        "tip_aureon_file_count": tip_file_count,
        "tip_aureon_total_bytes": tip_bytes,
        "tip_aureon_tree": tip_aureon,
        "tip_commit_tree": tip_tree,
        "tip_inventory_git_blob": tip_inventory_blob,
        "tip_release_tree_sha256": tip_digest,
        "tip_unified_margin_trader_tree": tip_umt,
        "unified_margin_trader_file_count": len(umt_files),
        "unified_margin_trader_files": umt_files,
        "unified_margin_trader_sha256": umt_digest,
        "unified_margin_trader_total_bytes": umt_bytes,
    }
    payload["digest"] = _sha256(_canonical({key: value for key, value in payload.items() if key != "digest"}))
    return payload


def _row_key(row: dict) -> tuple[str, str, str]:
    return (str(row["module"]), str(row["symbol"]), str(row["kind"]))


def _load_json_blob(commit: str, path: str) -> list[dict]:
    blob = _git("rev-parse", f"{commit}:{path}")
    data = _cat_blobs([blob])[blob]
    loaded = json.loads(data)
    if not isinstance(loaded, list):
        raise RuntimeError(f"{path} at {commit} is not a list")
    return loaded


def _key_token(module: str, symbol: str) -> str | None:
    sys.path.insert(0, str(ROOT / "mcp"))
    from aureon_public.inventory_scan import KEY_RE

    path = ROOT / "aureon" / module
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines()
    leaf = symbol.split(".")[-1]

    def span(node: ast.AST) -> str:
        return "\n".join(lines[node.lineno - 1 : node.end_lineno])

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == leaf and "." not in symbol:
            match = KEY_RE.search(node.name + "\n" + span(node))
            return None if match is None else match.group(0)
        if isinstance(node, ast.ClassDef) and symbol.startswith(node.name + "."):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == leaf:
                    match = KEY_RE.search(item.name + "\n" + span(item))
                    return None if match is None else match.group(0)
    return None


def _pin_blob_paths() -> set[str]:
    return {path for path, _blob in _ls_tree(PIN, "aureon")} | {
        path for path, _blob in _ls_tree(PIN, "unified_margin_trader")
    }


def _row_path(module: str) -> str:
    if module.startswith("unified_margin_trader/"):
        return module
    return f"aureon/{module}"


def _checkout_paths_outside_pin(pin_paths: set[str]) -> list[str]:
    found: list[str] = []
    for prefix in ("aureon", "unified_margin_trader"):
        root = ROOT / prefix
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel not in pin_paths:
                found.append(rel)
    found.sort()
    return found


def build_census(provenance: dict[str, object]) -> dict[str, object]:
    sys.path.insert(0, str(ROOT / "mcp"))
    from aureon_public.body import ENABLED_THROUGH, OPEN_PLAN_THROUGH, _public_entry_refusal
    from aureon_public.coverage_plan import safety_category, stage_for
    from aureon_public.inventory_scan import scan

    if OPEN_PLAN_THROUGH != 2:
        raise SystemExit(
            f"OPEN_PLAN_THROUGH is {OPEN_PLAN_THROUGH}; stage 6 must not open plan stages 3 and 4"
        )
    pin_paths = _pin_blob_paths()
    outside = _checkout_paths_outside_pin(pin_paths)
    if outside != list(POST_PIN_CHECKOUT_PATHS):
        raise SystemExit(
            "checkout paths outside the pin tree changed; stage 6 does not fold them "
            "into the inventory: " + ", ".join(outside)
        )
    scanned = [
        row for row in scan(ROOT) if _row_path(str(row["module"])) in pin_paths
    ]
    inventory_path = ROOT / "docs" / "mcp" / "inventory.json"
    inventory_bytes = inventory_path.read_bytes()
    inventory = json.loads(inventory_bytes)
    pin_inventory = _load_json_blob(PIN, "docs/mcp/inventory.json")
    scan_index = {_row_key(row): row for row in scanned}
    inv_index = {_row_key(row): row for row in inventory}
    pin_index = {_row_key(row): row for row in pin_inventory}
    unlisted = sorted(set(scan_index) - set(inv_index))
    missing = sorted(set(inv_index) - set(scan_index))
    drift = []
    for key in sorted(set(scan_index) & set(inv_index)):
        left = scan_index[key]
        right = inv_index[key]
        changed = [field for field in COMPARE_FIELDS if left.get(field) != right.get(field)]
        if changed:
            drift.append({"fields": changed, "key": list(key)})
    added_keys = sorted(set(inv_index) - set(pin_index))
    removed_since_pin = sorted(set(pin_index) - set(inv_index))
    by_package: dict[str, list[dict]] = {}
    for row in inventory:
        by_package.setdefault(str(row["package"]), []).append(row)
    plan_stage: dict[str, int] = {}
    for package, rows in by_package.items():
        categories = {safety_category(str(row["safety"])) for row in rows}
        plan_stage[package] = stage_for(package, categories)
    added_public: list[dict[str, object]] = []
    added_other: list[dict[str, object]] = []
    for key in added_keys:
        row = inv_index[key]
        item: dict[str, object] = {
            "full_body_stage": row["stage"],
            "kind": row["kind"],
            "module": row["module"],
            "package": row["package"],
            "plan_stage": plan_stage[str(row["package"])],
            "safety": row["safety"],
            "server": row["server"],
            "symbol": row["symbol"],
        }
        if row["module"] == "evidence/report.py" and row["symbol"] == "render_results":
            item["key_pattern_match"] = _key_token(str(row["module"]), str(row["symbol"]))
        if row["server"] == "public" and row["kind"] in {"function", "method"}:
            reason = _public_entry_refusal(row)
            if not reason:
                raise SystemExit(
                    "new public entry point would be reachable without a new sweep: "
                    f"{row['module']} {row['symbol']}"
                )
            item["refusal"] = reason
            added_public.append(item)
        else:
            added_other.append(item)
    sweep = provenance["measured_call_sweep"]
    assert isinstance(sweep, dict)
    evidence_key = _key_token("evidence/report.py", "render_results")
    if evidence_key != "dotenv":
        raise SystemExit(f"evidence key pattern match is {evidence_key!r}, expected dotenv")
    delta = provenance["aureon_delta_since_measured_pin"]
    assert isinstance(delta, list)
    modified = [str(item["path"]) for item in delta if isinstance(item, dict) and item.get("status") != "A"]
    gaps = [
        {
            "id": "sweep_not_repeated",
            "text": (
                "The call sweep was not repeated at pin "
                f"{PIN}. {SWEEP_PATH.as_posix()} still names pin {sweep.get('pin')} "
                f"and aureon tree {sweep.get('aureon_tree')}. "
                "Reachable and tested figures in COVERAGE_PLAN.md are that record "
                "plus public_entry_refusal. This stage does not publish a new reachable count."
            ),
        },
        {
            "id": "brain_proof_blob",
            "text": _brain_proof_note(str(sweep.get("pin"))),
        },
        {
            "id": "plan_stages_3_and_4_closed",
            "text": (
                f"OPEN_PLAN_THROUGH stays {OPEN_PLAN_THROUGH}. "
                "The read gate opens two entry points: miner MinerAIInsight.to_dict "
                "and queen compute_zpe_ground. Exchange body_call stays refused. "
                f"Full-body ENABLED_THROUGH is {ENABLED_THROUGH}. "
                "That full-body number is not the read gate. "
                f"{len(added_public)} public entry points added since the pin inventory "
                "are refused. evidence is plan stage "
                f"{plan_stage.get('evidence')} because render_results matches the scanner "
                "key pattern. Harmonic stays plan stage "
                f"{plan_stage.get('harmonic')}. Exchanges stay plan stage "
                f"{plan_stage.get('exchanges')}. Exchange rows stay operator. "
                "The matched token in "
                "`render_results` is `dotenv`, from the letters inside `python-dotenv`."
            ),
        },
        {
            "id": "changed_blobs_not_recalled",
            "text": (
                "These existing files differ in git blob between the measured aureon tree "
                "and the pin. The census compares symbol names and scanner fields. "
                "It does not re-call them: " + ", ".join(f"`{path}`" for path in modified) + "."
            ),
        },
        {
            "id": "receipt_5_absent",
            "text": (
                "Receipt 1 is measured at reports/measured/native_process_containment.json. "
                "This stage does not rewrite that record. Receipts 2 and 4 are this "
                "remeasurement. Receipt 3 is the DigiCert head anchor in "
                "docs/runbooks/GO_LIVE_HARDENING.md. This stage does not append a "
                "later head, does not set external_head_anchor_attested, and does "
                "not report the system alive. Receipt 5, an authenticated deployment "
                "receipt and provider-side read-back, is absent. Decision remains HOLD. "
                "go_live_clear is false."
            ),
        },
        {
            "id": "pin_inventory_predates_closure",
            "text": (
                f"Inventory sha256 at pin {PIN} is {provenance['pin_inventory_sha256']}. "
                f"The closure inventory sha256 is {_sha256(inventory_bytes)}. "
                + (
                    f"Tip {TIP} did not change the inventory blob. "
                    if provenance["inventory_blobs_match"]
                    else f"Tip {TIP} changed the inventory blob. "
                )
                + (
                    "No inventory rows were added since the pin inventory. "
                    if not added_keys
                    else (
                        f"{len(added_keys)} inventory rows differ from the pin inventory. "
                    )
                )
                + (
                    "The pin aureon tree matches the tip aureon tree."
                    if provenance["aureon_trees_match"]
                    else "The pin aureon tree does not match the tip aureon tree."
                )
            ),
        },
        {
            "id": "pin_tree_symbols_outside_inventory",
            "text": (
                f"{len(unlisted)} symbols are in the pin aureon tree and are not in "
                "docs/mcp/inventory.json. They were not added. "
                f"The symbol count is a scan of this checkout, which is later than tip {TIP}. "
                "The tip field stays that commit and is not a claim that these counts were measured there. "
                "`evaluation/market_series.py` `http_get` is a live public fetch. "
                "Listing that row would move the evaluation package from plan stage 2 "
                "to plan stage 4 and would change the reachable count. Reachable stays "
                "the prior sweep's 69. Plan stages 3 and 4 stay closed. The unlisted paths are "
                + ", ".join(f"`{path}`" for path in sorted({_row_path(key[0]) for key in unlisted}))
                + "."
            ),
        },
    ]
    payload: dict[str, object] = {
        "added_other_symbols": added_other,
        "added_public_entry_points": added_public,
        "added_since_pin_inventory": len(added_keys),
        "coverage_plan_open_through": OPEN_PLAN_THROUGH,
        "coverage_plan_stages_3_and_4_open": False,
        "decision": "HOLD",
        "field_drift": drift,
        "full_body_enabled_through": ENABLED_THROUGH,
        "go_live_clear": False,
        "inventory_sha256": _sha256(inventory_bytes),
        "inventory_symbol_count": len(inventory),
        "missing_from_source": [list(key) for key in missing],
        "open_gaps": gaps,
        "pin": PIN,
        "pin_aureon_tree": provenance["pin_aureon_tree"],
        "pin_inventory_sha256": provenance["pin_inventory_sha256"],
        "post_pin_checkout_paths": list(POST_PIN_CHECKOUT_PATHS),
        "provenance_digest": provenance["digest"],
        "provenance_path": PROVENANCE_PATH.as_posix(),
        "reachable_count": None,
        "receipt": 4,
        "removed_since_pin_inventory": [list(key) for key in removed_since_pin],
        "scan_symbol_count": len(scanned),
        "schema": CENSUS_SCHEMA,
        "source_boundary_closed": not unlisted and not missing and not drift,
        "tip": TIP,
        "tip_aureon_tree": provenance["tip_aureon_tree"],
        "unlisted_in_inventory": [list(key) for key in unlisted],
    }
    return payload


def render_markdown(census: dict[str, object], provenance: dict[str, object]) -> str:
    gaps = census["open_gaps"]
    assert isinstance(gaps, list)
    added_public = census["added_public_entry_points"]
    added_other = census["added_other_symbols"]
    assert isinstance(added_public, list)
    assert isinstance(added_other, list)
    lines = [
        "# Stage 6 source-boundary census",
        "",
        "Receipt 4 of the go-live list. Decision: `HOLD`. This is not a go-live clear.",
        "",
        f"Provenance digest: `{provenance['digest']}`",
        f"Path: `{PROVENANCE_PATH.as_posix()}`",
        "",
        "## Lineage",
        "",
        f"Pin `{PIN}` aureon tree `{provenance['pin_aureon_tree']}`.",
        f"Tip `{TIP}` aureon tree `{provenance['tip_aureon_tree']}`.",
        f"Those aureon trees match: `{str(provenance['aureon_trees_match']).lower()}`.",
        f"Release-tree content sha256: `{provenance['release_tree_sha256']}`.",
        f"Files: {provenance['release_tree_file_count']}. Bytes: {provenance['release_tree_total_bytes']}.",
        f"Pin-move paths: {len(provenance['pin_move_delta'])}.",
        f"Pin-move touches aureon: `{str(provenance['pin_move_touches_aureon']).lower()}`.",
        f"Pin-move touches inventory.json: `{str(provenance['pin_move_touches_inventory']).lower()}`.",
        "",
        "The pin-move commit updates published pin strings and the tests that name them. "
        "It does not change the aureon bytes this digest measures.",
        "",
        "## Closure",
        "",
        f"Scan symbols: {census['scan_symbol_count']}. Inventory symbols: {census['inventory_symbol_count']}.",
        f"Unlisted in the inventory: {len(census['unlisted_in_inventory'])}.",
        f"Inventory rows missing from source: {len(census['missing_from_source'])}.",
        f"Field drift on shared keys: {len(census['field_drift'])}.",
        f"Source boundary closed: `{str(census['source_boundary_closed']).lower()}`.",
        f"Symbols added since the inventory blob at the pin: {census['added_since_pin_inventory']}.",
        f"Removed since that blob: {len(census['removed_since_pin_inventory'])}.",
        "",
        "A public entry point is a public function or method. A module or class is listed and is not an entry point. "
        "`reachable_count` in the census file is null. This stage does not invent one.",
        "",
        "### Public entry points added since the pin inventory",
        "",
        "| Module | Symbol | Plan stage | Refusal |",
        "| --- | --- | ---: | --- |",
    ]
    for item in added_public:
        assert isinstance(item, dict)
        lines.append(
            f"| `{item['module']}` | `{item['symbol']}` | {item['plan_stage']} | {item['refusal']} |"
        )
    lines.extend(
        [
            "",
            "### Other symbols added since the pin inventory",
            "",
            "| Module | Symbol | Kind | Server | Full-body stage |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    for item in added_other:
        assert isinstance(item, dict)
        lines.append(
            f"| `{item['module']}` | `{item['symbol']}` | {item['kind']} | {item['server']} | {item['full_body_stage']} |"
        )
    lines.extend(["", "## Open gaps", ""])
    for gap in gaps:
        assert isinstance(gap, dict)
        lines.append(f"- `{gap['id']}`. {gap['text']}")
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "env -u PYTHONPATH PYTHONPATH=mcp python3.12 scripts/validation/go_live_stage6.py --check",
            "```",
            "",
            "The check reads git objects for the pin and the tip, scans the checkout files that exist at the pin, and compares these files. "
            "Paths added after the pin stay out of the inventory. "
            "It does not import a trading package and it does not start a listener.",
            "",
        ]
    )
    return "\n".join(lines)


def _dump(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _load(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit(f"{path} is not an object")
    return loaded


def check() -> None:
    provenance = build_provenance()
    census = build_census(provenance)
    markdown = render_markdown(census, provenance)
    stored_provenance = _load(ROOT / PROVENANCE_PATH)
    stored_census = _load(ROOT / CENSUS_PATH)
    stored_markdown = (ROOT / CENSUS_MARKDOWN).read_text(encoding="utf-8")
    if stored_provenance != provenance:
        raise SystemExit("provenance digest file does not match the pin and tip")
    if stored_census != census:
        raise SystemExit("source-boundary census file does not match the scan")
    if stored_markdown != markdown:
        raise SystemExit("census markdown does not match the census file")
    digest = provenance.pop("digest")
    if _sha256(_canonical(provenance)) != digest:
        raise SystemExit("provenance digest does not match its payload")


def write() -> None:
    provenance = build_provenance()
    census = build_census(provenance)
    _dump(ROOT / PROVENANCE_PATH, provenance)
    _dump(ROOT / CENSUS_PATH, census)
    (ROOT / CENSUS_MARKDOWN).write_text(render_markdown(census, provenance), encoding="utf-8")
    print(provenance["digest"])
    print(CENSUS_PATH)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        check()
        return
    if args.write or not args.check:
        write()


if __name__ == "__main__":
    main()
