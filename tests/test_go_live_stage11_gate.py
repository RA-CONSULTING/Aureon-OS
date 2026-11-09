"""Stage 11 installer gate: HOLD unless receipts 1-5 verify on this HEAD."""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "scripts" / "bootstrap" / "go_live_stage11_gate.py"
INSTALLER = ROOT / "scripts" / "linux" / "install-linux.sh"
MASTER = ROOT / "deploy" / "start_master_launcher.sh"
PRODUCTION = ROOT / "production" / "aureon.py"
README = ROOT / "README.md"
RUNBOOK = ROOT / "docs" / "runbooks" / "GO_LIVE_STAGE11_INSTALLER_GATE.md"
HARDENING = ROOT / "docs" / "runbooks" / "GO_LIVE_HARDENING.md"

_spec = importlib.util.spec_from_file_location("go_live_stage11_gate", GATE_PATH)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


class FakeGit:
    def __init__(
        self,
        head: str | None,
        note: bytes | None = None,
        blob: bytes | None = None,
        changes: dict[tuple[str, str], list[str] | None] | None = None,
    ) -> None:
        self._head = head
        self._note = note
        self._blob = blob
        self._changes = {} if changes is None else changes

    def head(self) -> str | None:
        return self._head

    def note(self) -> bytes | None:
        return self._note

    def head_blob(self, relative: str) -> bytes | None:
        assert relative == gate.TOKEN_REL
        return self._blob

    def changed_paths(self, tip: str, head: str) -> list[str] | None:
        return self._changes.get((tip, head))


PUBLISHED_PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
FIXTURE_PIN = "99" * 20


def _write(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_pin(tmp_path: Path, pin: str) -> None:
    path = tmp_path / gate.PIN_SOURCE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'PINNED_COMMIT = "{pin}"\n', encoding="utf-8")


def _provenance(head: str, pin: str = FIXTURE_PIN) -> dict:
    body = {
        "schema": "aureon.go-live.release-provenance.v1",
        "receipt": 2,
        "pin": pin,
        "tip": head,
        "aureon_trees_match": True,
        "inventory_blobs_match": True,
        "release_tree_sha256": "ab" * 32,
        "system_alive": False,
        "live_trading": False,
        "orders_placed": False,
    }
    body["digest"] = gate._sha256(gate._canonical(body))
    return body


def _clear_tree(
    tmp_path: Path,
    head: str,
    *,
    pin: str = FIXTURE_PIN,
    changes: dict[tuple[str, str], list[str] | None] | None = None,
) -> FakeGit:
    _write_pin(tmp_path, pin)
    source = tmp_path / "fixture" / "source.py"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"contained\n")
    token = b"\x30\x00"
    token_text = base64.b64encode(token).decode("ascii") + "\n"
    token_path = tmp_path / gate.TOKEN_REL
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token_text, encoding="ascii")
    anchor = gate._sha256(token)
    (tmp_path / "evidence" / "output" / "hnc_head_anchor.id").write_text(anchor + "\n", encoding="ascii")
    provenance = _provenance(head, pin)
    _write(
        tmp_path / "reports" / "measured" / "native_process_containment.json",
        {
            "schema": "aureon.measured.native-process-containment.v1",
            "receipt": 1,
            "pin": pin,
            "git_head_at_measurement": head,
            "worktree_dirty_at_measurement": False,
            "verdict": "pass",
            "allowed_at_default": "none",
            "cold_boot_argv_has_net": True,
            "cold_boot_argv": ["unshare", "--net", "python"],
            "market_data_fetched": False,
            "pin_changed": False,
            "orders_placed": False,
            "live_trading": False,
            "system_alive": False,
            "tags": {"system_alive": "not claimed"},
            "source_sha256": {"fixture/source.py": gate._sha256(b"contained\n")},
        },
    )
    _write(tmp_path / "measured" / "go_live_stage6_provenance.json", provenance)
    _write(
        tmp_path / "evidence" / "output" / "hnc_head_anchor.json",
        {
            "schema": "aureon.evidence.hnc-head-anchor.v1",
            "receipt": 3,
            "tag": "measured",
            "public_require_pin": pin,
            "hnc_identity_changed": False,
            "anchor_id": anchor,
            "system_alive": False,
            "live_trading": False,
            "orders_placed": False,
            "external": {"kind": "rfc3161", "provider_contacted_by_check": False},
        },
    )
    _write(
        tmp_path / "measured" / "go_live_stage6_source_census.json",
        {
            "schema": "aureon.go-live.source-boundary-census.v1",
            "receipt": 4,
            "pin": pin,
            "tip": head,
            "source_boundary_closed": True,
            "missing_from_source": [],
            "open_gaps": [],
            "provenance_digest": provenance["digest"],
            "system_alive": False,
            "live_trading": False,
            "orders_placed": False,
        },
    )
    _write(
        tmp_path / gate.RECEIPT5_REL,
        {
            "schema": gate.RECEIPT5_SCHEMA,
            "receipt": 5,
            "pin": pin,
            "git_head_at_measurement": head,
            "receipt_5_complete": True,
            "provider_readback_digest": "cd" * 32,
            "system_alive": False,
            "system_alive_claimed": False,
            "live_trading": False,
            "orders_placed": False,
            "go_live_clear": False,
        },
    )
    (tmp_path / "README.md").write_text(
        "![Release boundary: HOLD](https://img.shields.io/badge/release%20boundary-HOLD-orange.svg)\n",
        encoding="utf-8",
    )
    note = token_text.encode("ascii")
    return FakeGit(head, note=note, blob=note, changes=changes)


def test_this_tip_stays_hold_and_does_not_flip_the_badge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUREON_GO_LIVE_CLEAR", "1")
    monkeypatch.setenv("GO_LIVE_CLEAR", "true")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    result = gate.evaluate(ROOT)
    assert result["head"] == head
    assert result["go_live_clear"] is False
    assert result["decision"] == "HOLD"
    assert result["badge"] == "HOLD"
    assert result["readme_badge"] == "HOLD"
    assert result["readme_edited"] is False
    assert result["badge_edit_required"] is False
    assert result["system_alive"] is False
    assert result["live_trading"] is False
    assert result["orders_placed"] is False
    assert result["pin_moved"] is False
    assert result["public_pin"] == gate.published_require_pin(ROOT)
    assert result["public_pin"] == PUBLISHED_PIN
    assert "34864ff0547d2cff03e707414743a3b0cc8770b5" not in GATE_PATH.read_text(encoding="utf-8")
    assert PUBLISHED_PIN not in GATE_PATH.read_text(encoding="utf-8")
    assert result["supported_path_taken"] is False
    assert result["flag_file"]["honored"] is False
    by_id = {row["id"]: row for row in result["receipts"]}
    assert by_id[1]["verified_on_tip"] is False
    assert by_id[1]["detail"]["recorded_head"] == "c68a89d2a184d99582bb24310b91e024323a212c"
    assert by_id[1]["detail"]["recorded_head"] != head
    assert by_id[1]["detail"]["tip_diff"] == "outside_allowlist"
    assert "pin_mismatch" in by_id[1]["reasons"]
    assert "tip_is_not_head" in by_id[1]["reasons"]
    assert "worktree_dirty_at_measurement" in by_id[1]["reasons"]
    assert by_id[2]["verified_on_tip"] is False
    assert by_id[2]["detail"]["digest_ok"] is True
    assert "pin_mismatch" not in by_id[2]["reasons"]
    assert "tip_is_not_head" in by_id[2]["reasons"]
    assert by_id[3]["verified_on_tip"] is False
    assert "pin_mismatch" in by_id[3]["reasons"]
    assert "note_missing_on_head" in by_id[3]["reasons"]
    assert by_id[4]["verified_on_tip"] is False
    assert "pin_mismatch" not in by_id[4]["reasons"]
    assert "tip_is_not_head" in by_id[4]["reasons"]
    assert "source_boundary_not_closed" in by_id[4]["reasons"]
    assert by_id[5]["present"] is True
    assert by_id[5]["path"] == "reports/measured/go_live_receipt5_deployment.json"
    assert by_id[5]["schema"] == "aureon.go-live.deployment-receipt.v1"
    assert by_id[5]["verified_on_tip"] is False
    assert "receipt_5_incomplete" in by_id[5]["reasons"]
    assert "provider_readback_digest_missing" in by_id[5]["reasons"]
    assert "tip_is_not_head" in by_id[5]["reasons"]
    assert by_id[5]["detail"]["created_by_this_gate"] is False
    assert by_id[5]["detail"]["receipt_5_complete"] is False
    assert (ROOT / gate.RECEIPT5_REL).is_file()
    assert "release%20boundary-HOLD-orange" in README.read_text(encoding="utf-8")


def test_a_boolean_flag_file_cannot_clear_the_gate(tmp_path: Path) -> None:
    flag = tmp_path / gate.FLAG_FILE
    flag.parent.mkdir(parents=True)
    flag.write_text('{"go_live_clear": true}\n', encoding="utf-8")
    result = gate.evaluate(tmp_path, FakeGit("a" * 40))
    assert result["go_live_clear"] is False
    assert result["flag_file"]["present"] is True
    assert result["flag_file"]["honored"] is False
    assert result["receipts"][-1]["reasons"] == ["artifact_absent"]


def test_clear_fixture_computes_go_live_clear_without_editing_the_badge(tmp_path: Path) -> None:
    head = "ab" * 20
    client = _clear_tree(tmp_path, head)
    (tmp_path / gate.FLAG_FILE).write_text('{"go_live_clear": false}\n', encoding="utf-8")
    result = gate.evaluate(tmp_path, client)
    assert result["verified_ids"] == [1, 2, 3, 4, 5]
    assert result["go_live_clear"] is True
    assert result["decision"] == "CLEAR"
    assert result["badge"] == "CLEAR"
    assert result["readme_badge"] == "HOLD"
    assert result["readme_edited"] is False
    assert result["badge_edit_required"] is True
    assert result["system_alive"] is False
    assert result["live_trading"] is False
    assert "HOLD-orange" in (tmp_path / "README.md").read_text(encoding="utf-8")
    assert result["flag_file"]["honored"] is False


def test_receipt5_claiming_alive_does_not_verify(tmp_path: Path) -> None:
    head = "cd" * 20
    client = _clear_tree(tmp_path, head)
    path = tmp_path / gate.RECEIPT5_REL
    body = json.loads(path.read_text(encoding="utf-8"))
    body["system_alive"] = True
    body["go_live_clear"] = True
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    result = gate.evaluate(tmp_path, client)
    row = result["receipts"][-1]
    assert row["verified_on_tip"] is False
    assert "system_alive_claimed" in row["reasons"]
    assert result["go_live_clear"] is False
    assert result["system_alive"] is False


def test_parent_measurement_is_not_this_tip(tmp_path: Path) -> None:
    head = "ef" * 20
    client = _clear_tree(tmp_path, head)
    path = tmp_path / "reports" / "measured" / "native_process_containment.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    body["git_head_at_measurement"] = "12" * 20
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    result = gate.evaluate(tmp_path, client)
    row = next(item for item in result["receipts"] if item["id"] == 1)
    assert row["verified_on_tip"] is False
    assert row["detail"]["tip_diff"] == "unavailable"
    assert "tip_is_not_head" in row["reasons"]
    assert result["go_live_clear"] is False


def _retip_provenance(tmp_path: Path, head: str, recorded: str) -> None:
    path = tmp_path / "measured" / "go_live_stage6_provenance.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    body["tip"] = recorded
    body["digest"] = gate._sha256(gate._canonical({key: value for key, value in body.items() if key != "digest"}))
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    census = tmp_path / "measured" / "go_live_stage6_source_census.json"
    census_body = json.loads(census.read_text(encoding="utf-8"))
    census_body["provenance_digest"] = body["digest"]
    census.write_text(json.dumps(census_body) + "\n", encoding="utf-8")


def test_tip_passes_when_it_is_head(tmp_path: Path) -> None:
    head = "ab" * 20
    client = _clear_tree(tmp_path, head)
    reasons: list[str] = []
    gate._tip_matches({"tip": head}, "tip", head, reasons, client)
    assert reasons == []
    result = gate.evaluate(tmp_path, client)
    assert result["go_live_clear"] is True
    assert all(row["detail"].get("tip_diff") == "head" for row in result["receipts"] if row["id"] != 3)


def test_tip_passes_when_only_receipt_files_differ(tmp_path: Path) -> None:
    head = "cd" * 20
    recorded = "12" * 20
    changed = [
        "reports/measured/native_process_containment.json",
        "reports/measured/native_process_containment.md",
        "measured/go_live_stage6_provenance.json",
        "reports/measured/go_live_receipt5_deployment.json",
        "reports/measured/go_live_receipt5_deployment.md",
    ]
    assert set(changed) <= gate.TIP_DELTA_ALLOWLIST
    client = _clear_tree(tmp_path, head, changes={(recorded, head): changed})
    _retip_provenance(tmp_path, head, recorded)
    result = gate.evaluate(tmp_path, client)
    row = next(item for item in result["receipts"] if item["id"] == 2)
    assert row["detail"]["tip_diff"] == "allowlist"
    assert row["verified_on_tip"] is True
    assert result["go_live_clear"] is True


def test_tip_fails_when_a_non_receipt_path_differs(tmp_path: Path) -> None:
    head = "ef" * 20
    recorded = "34" * 20
    client = _clear_tree(
        tmp_path,
        head,
        changes={(recorded, head): ["docs/runbooks/GO_LIVE_HARDENING.md"]},
    )
    _retip_provenance(tmp_path, head, recorded)
    result = gate.evaluate(tmp_path, client)
    row = next(item for item in result["receipts"] if item["id"] == 2)
    assert row["verified_on_tip"] is False
    assert row["detail"]["tip_diff"] == "outside_allowlist"
    assert "tip_is_not_head" in row["reasons"]
    assert result["go_live_clear"] is False


def test_tip_fails_when_a_code_file_changed_after_the_tip(tmp_path: Path) -> None:
    head = "11" * 20
    recorded = "22" * 20
    changed = [
        "measured/go_live_stage6_provenance.json",
        "aureon/containment/cold_boot.py",
    ]
    assert "aureon/containment/cold_boot.py" not in gate.TIP_DELTA_ALLOWLIST
    client = _clear_tree(tmp_path, head, changes={(recorded, head): changed})
    _retip_provenance(tmp_path, head, recorded)
    result = gate.evaluate(tmp_path, client)
    row = next(item for item in result["receipts"] if item["id"] == 2)
    assert row["verified_on_tip"] is False
    assert row["detail"]["tip_outside_allowlist_count"] == 1
    assert "tip_is_not_head" in row["reasons"]
    assert result["go_live_clear"] is False


def test_receipt5_fixture_in_a_temp_dir_requires_digest_complete_and_tip(tmp_path: Path) -> None:
    head = "56" * 20
    client = _clear_tree(tmp_path, head)
    result = gate.evaluate(tmp_path, client)
    row = next(item for item in result["receipts"] if item["id"] == 5)
    assert row["path"] == gate.RECEIPT5_REL
    assert row["schema"] == gate.RECEIPT5_SCHEMA
    assert row["verified_on_tip"] is True
    assert row["detail"]["provider_readback_digest_present"] is True

    path = tmp_path / gate.RECEIPT5_REL
    body = json.loads(path.read_text(encoding="utf-8"))
    body["provider_readback_digest"] = None
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    null_digest = gate.evaluate(tmp_path, client)
    null_row = next(item for item in null_digest["receipts"] if item["id"] == 5)
    assert null_row["verified_on_tip"] is False
    assert "provider_readback_digest_missing" in null_row["reasons"]
    assert null_digest["go_live_clear"] is False

    body["provider_readback_digest"] = "cd" * 32
    body["receipt_5_complete"] = False
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    incomplete = gate.evaluate(tmp_path, client)
    incomplete_row = next(item for item in incomplete["receipts"] if item["id"] == 5)
    assert incomplete_row["verified_on_tip"] is False
    assert "receipt_5_incomplete" in incomplete_row["reasons"]

    body["receipt_5_complete"] = True
    body["git_head_at_measurement"] = "78" * 20
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    moved = gate.evaluate(tmp_path, client)
    moved_row = next(item for item in moved["receipts"] if item["id"] == 5)
    assert moved_row["verified_on_tip"] is False
    assert "tip_is_not_head" in moved_row["reasons"]


def test_receipt_paths_are_on_the_tip_allowlist() -> None:
    for spec in gate.RECEIPTS:
        assert spec["path"] in gate.TIP_DELTA_ALLOWLIST
    assert "aureon/containment/cold_boot.py" not in gate.TIP_DELTA_ALLOWLIST
    assert "docs/runbooks/GO_LIVE_HARDENING.md" not in gate.TIP_DELTA_ALLOWLIST
    assert "scripts/bootstrap/go_live_stage11_gate.py" not in gate.TIP_DELTA_ALLOWLIST


def test_pin_mismatch_fails_closed(tmp_path: Path) -> None:
    head = "11" * 20
    client = _clear_tree(tmp_path, head)
    path = tmp_path / "measured" / "go_live_stage6_provenance.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    body["pin"] = "22" * 20
    body["digest"] = gate._sha256(gate._canonical({k: v for k, v in body.items() if k != "digest"}))
    path.write_text(json.dumps(body) + "\n", encoding="utf-8")
    result = gate.evaluate(tmp_path, client)
    row = next(item for item in result["receipts"] if item["id"] == 2)
    assert "pin_mismatch" in row["reasons"]
    assert result["go_live_clear"] is False
    assert result["pin_moved"] is False


def test_launch_stays_on_hold_for_this_tip() -> None:
    called: list[list[str]] = []

    def _execv(executable: str, argv: list[str]) -> None:
        called.append([executable, *argv])

    code = gate.launch_contained(ROOT, execv=_execv)
    assert code == 1
    assert called == []


def test_launch_execs_only_the_contained_cold_boot(tmp_path: Path) -> None:
    head = "33" * 20
    client = _clear_tree(tmp_path, head)
    called: list[list[str]] = []
    previous = Path.cwd()

    def _execv(executable: str, argv: list[str]) -> None:
        called.append(list(argv))

    try:
        code = gate.launch_contained(tmp_path, client, execv=_execv)
    finally:
        os.chdir(previous)
    assert code == 1
    assert called == [[gate.supported_argv()[0], "-m", "aureon.containment.cold_boot"]]


def test_check_cli_is_silent_and_hold() -> None:
    done = subprocess.run(
        ["/usr/bin/python3", "-I", "-S", "-B", str(GATE_PATH), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1
    assert done.stdout == ""
    source = GATE_PATH.read_text(encoding="utf-8")
    assert "import aureon" not in source
    assert "from aureon" not in source


def test_linux_installer_still_emits_the_isolated_hold() -> None:
    done = subprocess.run(
        ["bash", str(INSTALLER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1
    receipt = json.loads(done.stdout)
    assert receipt["decision"] == "HOLD"
    assert receipt["target_id"] == "linux-supervisor"
    assert receipt["target_imported"] is False
    assert receipt["target_called"] is False
    assert receipt["child_process_started"] is False
    assert receipt["production_ready"] is False
    assert "stage 11 gate is HOLD" not in done.stdout


def test_release_scripts_keep_the_hold_exec_last() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    master = MASTER.read_text(encoding="utf-8")
    production = PRODUCTION.read_text(encoding="utf-8")
    assert "go_live_stage11_gate.py" in installer
    assert "go_live_stage11_gate.py" in master
    assert "go_live_stage11_gate.py" in production
    assert "aureon.containment" not in installer
    assert "aureon.containment" not in master
    assert "-m aureon." not in installer
    assert "-m aureon." not in master
    assert "-m aureon." not in production
    assert installer.rstrip().endswith('--target-id linux-supervisor')
    assert master.rstrip().endswith("--target-id master-launcher")
    assert "protected_bootstrap_v05.py" in installer
    assert "protected_bootstrap_v05.py" in master
    assert '"production-supervisor"' in production
    for path in (INSTALLER, MASTER):
        parsed = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        assert parsed.returncode == 0, parsed.stderr


def test_runbook_lists_the_same_receipt_paths() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    hardening = HARDENING.read_text(encoding="utf-8")
    assert (
        "Receipts 2–5 remain HOLD" in hardening
        or "Receipts 2, 3, 4, and 5 remain HOLD" in hardening
    )
    assert "go_live_clear" in text
    assert "HOLD-orange" in text or "badge stays HOLD" in text
    assert "not claimed alive" in text
    assert "pin is not moved" in text
    for spec in gate.RECEIPTS:
        assert spec["path"] in text
        assert spec["name"] in text
        assert spec["schema"] in text
    assert gate.RECEIPT5_REL in text
    assert "provider_readback_digest" in text
    assert "receipt_5_complete" in text
    assert "TIP_DELTA_ALLOWLIST" in text or "allowlist" in text
    assert "guard_loader.py" in text
    assert "artifact is absent" not in text
