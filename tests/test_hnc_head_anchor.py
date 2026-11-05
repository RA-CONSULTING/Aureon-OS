"""Receipt 3: the measured HNC head is a git note, not a working-tree file."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from aureon.evidence.hnc_anchor import (
    EXPECTED_ANCHOR_ID,
    GENESIS,
    NOTE_REF,
    PIN_FORMULA_SERIES_SHA256,
    PUBLIC_PIN,
    TOKEN_REL,
    AnchorError,
    attach_note,
    canonical_token_text,
    commitment_bytes,
    decode_token_text,
    genesis_id,
    git_blob_sha1,
    load_token_text,
    measurement_commitment,
    parse_timestamp_text,
    validate_chain,
    verify_timestamp,
)

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "evidence" / "output" / "hnc_head_anchor.json"
TOKEN = ROOT / TOKEN_REL
OPEN_SSL_TEXT = """
Status info:
Status: Granted.
Status description: unspecified
Failure info: unspecified

TST info:
Version: 1
Policy OID: 2.16.840.1.114412.7.1
Hash Algorithm: sha256
Message data:
    0000 - aa bb cc dd ee ff 00 11-22 33 44 55 66 77 88 99   ................
    0010 - ab cd ef 01 23 45 67 89-9a bc de f0 12 34 56 78   ....#Eg......4Vx
Serial number: 0xAB
Time stamp: Nov  5 19:32:26 2026 GMT
Accuracy: unspecified
Ordering: no
Nonce: 0x01
TSA: unspecified
Extensions:
"""


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_genesis_id_is_the_named_string() -> None:
    assert genesis_id() == hashlib.sha256(GENESIS.encode("utf-8")).hexdigest()
    assert len(genesis_id()) == 64


def test_timestamp_text_parser_reads_the_external_clock() -> None:
    parsed = parse_timestamp_text(OPEN_SSL_TEXT)
    assert parsed["gen_time"] == "2026-11-05T19:32:26Z"
    assert parsed["serial_hex"] == "ab"
    assert parsed["policy_oid"] == "2.16.840.1.114412.7.1"
    assert parsed["tsa_ordering"] is False
    assert parsed["imprint_sha256"] == "aabbccddeeff00112233445566778899abcdef01234567899abcdef012345678"


def test_chain_rejects_a_rollback() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    validate_chain(record)
    rolled = json.loads(RECORD.read_text(encoding="utf-8"))
    rolled["sequence"] = 0
    with pytest.raises(AnchorError):
        validate_chain(rolled)
    rolled["sequence"] = 2
    with pytest.raises(AnchorError):
        validate_chain(rolled)
    later = json.loads(RECORD.read_text(encoding="utf-8"))
    later["sequence"] = 2
    later["prev_anchor_id"] = record["anchor_id"]
    later["anchor_id"] = "b" * 64
    later["external"] = dict(record["external"])
    later["external"]["gen_time"] = "2020-01-01T00:00:00Z"
    with pytest.raises(AnchorError):
        validate_chain(later, record)
    later["external"]["gen_time"] = "2099-01-01T00:00:00Z"
    validate_chain(later, record)


def test_public_pin_and_hold_are_unchanged() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    guard = (ROOT / "mcp/aureon_public/guard_loader.py").read_text(encoding="utf-8")
    space = (ROOT / "huggingface/hnc-field/guard.py").read_text(encoding="utf-8")
    assert f'PINNED_COMMIT = "{PUBLIC_PIN}"' in guard
    assert f'COMMIT = "{PUBLIC_PIN}"' in space
    assert record["public_require_pin"] == PUBLIC_PIN
    assert record["hnc_identity_changed"] is False
    assert record["measurement"]["formula_series_sha256"] == PIN_FORMULA_SERIES_SHA256
    assert record["measurement"]["hnc_identity_changed"] is False
    assert record["system_alive"] is False
    assert record["live_trading"] is False
    assert record["orders_placed"] is False
    assert record["go_live"] == "HOLD"
    assert record["go_live_clear"] is False
    assert record["market_series"] is False
    assert record["tag"] == "measured"
    assert record["anchor_id"] == EXPECTED_ANCHOR_ID
    assert (ROOT / "evidence/output/hnc_head_anchor.id").read_text(encoding="utf-8") == record["anchor_id"] + "\n"
    assert record["note_ref"] == NOTE_REF


def test_committed_token_verifies_over_the_measured_commitment() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    token = decode_token_text(TOKEN.read_text(encoding="utf-8"))
    assert hashlib.sha256(token).hexdigest() == record["anchor_id"]
    parsed = verify_timestamp(token, commitment_bytes(record["measurement"]))
    assert parsed["gen_time"] == record["external"]["gen_time"]
    assert parsed["serial_hex"] == record["external"]["serial_hex"]
    assert parsed["imprint_sha256"] == record["measurement_sha256"]
    mutated = dict(record["measurement"])
    mutated["formula_series_sha256"] = "0" * 64
    with pytest.raises(AnchorError):
        verify_timestamp(token, commitment_bytes(mutated))


def test_working_tree_edit_does_not_move_the_note(tmp_path: Path) -> None:
    token_text = TOKEN.read_text(encoding="utf-8")
    target = tmp_path / TOKEN_REL
    target.parent.mkdir(parents=True)
    target.write_text(token_text, encoding="utf-8")
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "cursoragent@cursor.com")
    _git(tmp_path, "config", "user.name", "Cursor Agent")
    _git(tmp_path, "add", TOKEN_REL)
    _git(tmp_path, "commit", "-m", "anchor token")
    attach_note(tmp_path)
    target.write_text(canonical_token_text(b"\x30\x00"), encoding="utf-8")
    assert load_token_text(tmp_path, require_note=True) == token_text
    note = subprocess.check_output(
        ["git", "notes", "--ref", "aureon-hnc-head", "show", "HEAD"],
        cwd=tmp_path,
    )
    assert note.decode("ascii") == token_text
    assert git_blob_sha1(token_text.encode("ascii")) == subprocess.check_output(
        ["git", "hash-object", "--stdin"],
        input=token_text.encode("ascii"),
        cwd=tmp_path,
    ).decode("ascii").strip()


def test_commitment_from_the_recorded_summary_matches_the_token() -> None:
    summary = json.loads((ROOT / "evidence/output/hnc.json").read_text(encoding="utf-8"))
    commitment = measurement_commitment(summary)
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert commitment == record["measurement"]
    assert commitment["market_series"] is False
    assert commitment["system_alive"] is False
