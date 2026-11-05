"""External monotonic head for the measured HNC evidence.

The formula path is the fixed-seed ``HarmonicRealityField`` run already in
``aureon.evidence.hnc``. This module does not fetch a market series and does
not place an order.

The head is an RFC 3161 timestamp over that measured commitment. ``make
evidence`` reads the token from the git note ``refs/notes/aureon-hnc-head``
and requires the committed bytes to match. A working-tree edit does not move
the note or the committed blob. The public require-pin stays
``34864ff0547d2cff03e707414743a3b0cc8770b5`` unless a measured series hash
differs, and this module refuses to stamp that case.

Go-live stays HOLD. The record does not say the system is alive.
"""

from __future__ import annotations

import base64
import hashlib
import re
import subprocess
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.evidence.serialize import dump

PUBLIC_PIN = "34864ff0547d2cff03e707414743a3b0cc8770b5"
# Series sha256 of the formula path in evidence/output/hnc.json at that pin.
PIN_FORMULA_SERIES_SHA256 = "0a69c024c3a7b849857314ef710f11439eb13a30cd7c45f05429becea574f5c2"
# SHA-256 of the RFC 3161 token bytes recorded for this head. Not a new HNC identity.
EXPECTED_ANCHOR_ID = "548596463d7b4dddeeba274562b212960f879baf475ee135c7d2fd3468f58e11"

NOTE_NAME = "aureon-hnc-head"
NOTE_REF = "refs/notes/aureon-hnc-head"
TSA_URL = "http://timestamp.digicert.com"
TOKEN_REL = "evidence/output/hnc_head_anchor.tsr.b64"
RECORD_REL = "evidence/output/hnc_head_anchor.json"
ID_REL = "evidence/output/hnc_head_anchor.id"
GENESIS = "aureon.evidence.hnc-head-anchor.genesis.v1"
SCHEMA = "aureon.evidence.hnc-head-anchor.v1"
COMMITMENT_SCHEMA = "aureon.evidence.hnc-measurement-commitment.v1"

_STAMP_RE = re.compile(
    r"Time stamp: ([A-Z][a-z]{2})\s+(\d{1,2}) (\d{2}:\d{2}:\d{2}) (\d{4}) GMT"
)
_SERIAL_RE = re.compile(r"Serial number: 0x([0-9A-Fa-f]+)")
_POLICY_RE = re.compile(r"Policy OID: (\d+(?:\.\d+)+)")
_ORDER_RE = re.compile(r"Ordering: (yes|no)")
_HEX_LINE_RE = re.compile(
    r"^\s+[0-9a-fA-F]{4} - ([0-9a-fA-F]{2}(?:[ -][0-9a-fA-F]{2})*)"
)
_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


class AnchorError(RuntimeError):
    """The head anchor does not verify."""


def genesis_id() -> str:
    return hashlib.sha256(GENESIS.encode("utf-8")).hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(prefix + payload).hexdigest()


def canonical_token_text(token: bytes) -> str:
    return base64.b64encode(token).decode("ascii") + "\n"


def decode_token_text(text: str) -> bytes:
    if text != text.strip() + "\n":
        raise AnchorError("token text is not a single canonical base64 line")
    try:
        token = base64.b64decode(text.strip(), validate=True)
    except ValueError as exc:
        raise AnchorError("token text is not base64") from exc
    if canonical_token_text(token) != text:
        raise AnchorError("token text is not canonical base64")
    return token


def measurement_commitment(hnc_summary: dict[str, Any]) -> dict[str, Any]:
    """Bytes the timestamp covers. Measured fields only. No clock, no commit."""

    formula = hnc_summary["formula"]
    multiverse = hnc_summary["multiverse"]
    formula_sha = str(formula["sha256"])
    return {
        "schema": COMMITMENT_SCHEMA,
        "tag": "measured",
        "public_require_pin": PUBLIC_PIN,
        "hnc_identity_changed": formula_sha != PIN_FORMULA_SERIES_SHA256,
        "formula_series_sha256": formula_sha,
        "formula_seed": int(formula["series_reference_seed"]),
        "formula_steps": int(formula["steps"]),
        "formula_source": str(formula["source"]),
        "multiverse_series_sha256": str(multiverse["sha256"]),
        "sequence": 1,
        "prev_anchor_id": genesis_id(),
        "genesis": GENESIS,
        "live_trading": False,
        "orders_placed": False,
        "system_alive": False,
        "go_live": "HOLD",
        "go_live_clear": False,
        "market_series": False,
    }


def commitment_bytes(commitment: dict[str, Any]) -> bytes:
    return dump(commitment).encode("utf-8")


def _ca_file() -> str:
    for path in (
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/cert.pem",
    ):
        if Path(path).is_file():
            return path
    raise AnchorError("system CA bundle was not found; the timestamp token is not verified")


def _openssl_env() -> dict[str, str]:
    import os

    env = os.environ.copy()
    env["LC_ALL"] = "C"
    return env


def request_timestamp(data: bytes) -> bytes:
    """Ask the timestamp authority for a token over ``data``. Not used by check."""

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "data.bin"
        query = Path(tmp) / "query.tsq"
        raw.write_bytes(data)
        proc = subprocess.run(
            ["openssl", "ts", "-query", "-data", str(raw), "-sha256", "-cert", "-out", str(query)],
            capture_output=True,
            env=_openssl_env(),
        )
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", "replace").strip()
            raise AnchorError(f"openssl ts -query failed: {detail}")
        query_bytes = query.read_bytes()
    request = urllib.request.Request(
        TSA_URL,
        data=query_bytes,
        headers={"Content-Type": "application/timestamp-query"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except OSError as exc:
        raise AnchorError(f"timestamp authority request failed: {exc}") from exc
    if not body.startswith(b"\x30"):
        raise AnchorError("timestamp authority did not return a DER TimeStampResp")
    return body


def parse_timestamp_text(text: str) -> dict[str, Any]:
    if "Status: Granted." not in text:
        raise AnchorError("timestamp token was not granted")
    stamp = _STAMP_RE.search(text)
    serial = _SERIAL_RE.search(text)
    policy = _POLICY_RE.search(text)
    ordering = _ORDER_RE.search(text)
    if stamp is None or serial is None or policy is None or ordering is None:
        raise AnchorError("timestamp token text is missing genTime, serial, policy, or ordering")
    month = _MONTHS.get(stamp.group(1))
    if month is None:
        raise AnchorError("timestamp month is not an English abbreviation")
    day = int(stamp.group(2))
    clock = stamp.group(3)
    year = int(stamp.group(4))
    gen = datetime.strptime(f"{year:04d}-{month:02d}-{day:02d}T{clock}", "%Y-%m-%dT%H:%M:%S")
    gen = gen.replace(tzinfo=UTC)
    imprint = _imprint_hex(text)
    return {
        "gen_time": gen.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "serial_hex": serial.group(1).lower(),
        "policy_oid": policy.group(1),
        "tsa_ordering": ordering.group(1) == "yes",
        "imprint_sha256": imprint,
    }


def _imprint_hex(text: str) -> str:
    chunks: list[str] = []
    capture = False
    for line in text.splitlines():
        if line.startswith("Message data:"):
            capture = True
            continue
        if not capture:
            continue
        match = _HEX_LINE_RE.match(line)
        if match is None:
            break
        chunks.append(match.group(1).replace("-", "").replace(" ", ""))
    imprint = "".join(chunks).lower()
    if len(imprint) != 64:
        raise AnchorError("timestamp imprint is not a sha256 hex string")
    return imprint


def verify_timestamp(token: bytes, data: bytes) -> dict[str, Any]:
    """Verify ``token`` against ``data`` with the system trust store. No network."""

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        token_path = folder / "token.tsr"
        data_path = folder / "data.bin"
        token_path.write_bytes(token)
        data_path.write_bytes(data)
        verified = subprocess.run(
            [
                "openssl",
                "ts",
                "-verify",
                "-in",
                str(token_path),
                "-data",
                str(data_path),
                "-CAfile",
                _ca_file(),
            ],
            capture_output=True,
            env=_openssl_env(),
        )
        if verified.returncode != 0:
            detail = verified.stderr.decode("utf-8", "replace").strip()
            raise AnchorError(f"timestamp verification failed: {detail}")
        printed = subprocess.run(
            ["openssl", "ts", "-reply", "-in", str(token_path), "-text"],
            capture_output=True,
            env=_openssl_env(),
        )
    if printed.returncode != 0:
        detail = printed.stderr.decode("utf-8", "replace").strip()
        raise AnchorError(f"openssl ts -reply failed: {detail}")
    parsed = parse_timestamp_text(printed.stdout.decode("utf-8"))
    digest = hashlib.sha256(data).hexdigest()
    if parsed["imprint_sha256"] != digest:
        raise AnchorError("timestamp imprint does not match the measured commitment")
    parsed["verification"] = "openssl ts -verify"
    parsed["ca"] = "system trust store"
    return parsed


def _git_bytes(root: Path, args: list[str]) -> bytes | None:
    try:
        return subprocess.check_output(args, cwd=root, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def read_note(root: Path) -> bytes | None:
    return _git_bytes(root, ["git", "notes", "--ref", NOTE_NAME, "show", "HEAD"])


def read_head_blob(root: Path) -> bytes | None:
    return _git_bytes(root, ["git", "show", f"HEAD:{TOKEN_REL}"])


def load_token_text(root: Path, *, require_note: bool) -> str:
    """Return the canonical token text from the note or the committed blob.

    The working tree is used only when neither git object exists, so a local
    edit cannot replace a note that is already attached.
    """

    note = read_note(root)
    head = read_head_blob(root)
    if note is not None and head is not None and note != head:
        raise AnchorError("git note and committed HNC head token differ")
    if require_note and note is None:
        raise AnchorError(
            f"missing {NOTE_REF} on HEAD. "
            f"Fetch it with: git fetch origin {NOTE_REF}:{NOTE_REF}"
        )
    if note is not None:
        raw = note
    elif head is not None:
        raw = head
    else:
        path = root / TOKEN_REL
        if not path.is_file():
            raise AnchorError(
                "HNC head token is not in git. "
                "Stamp it, commit the bytes, and attach the git note. "
                "make evidence does not request a new timestamp."
            )
        raw = path.read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise AnchorError("HNC head token text is not ASCII") from exc
    decode_token_text(text)
    return text


def parse_gen_time(value: str) -> datetime:
    if not value.endswith("Z"):
        raise AnchorError("gen_time is not UTC")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise AnchorError("gen_time is not YYYY-MM-DDTHH:MM:SSZ") from exc
    return parsed.replace(tzinfo=UTC)


def validate_chain(record: dict[str, Any], previous: dict[str, Any] | None = None) -> None:
    """Accept sequence 1 at genesis, or a later head with a strictly later clock."""

    sequence = record.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise AnchorError("head sequence is not a positive integer")
    prev = record.get("prev_anchor_id")
    anchor_id = record.get("anchor_id")
    if not isinstance(anchor_id, str) or len(anchor_id) != 64:
        raise AnchorError("anchor_id is not a sha256 hex string")
    gen_time = parse_gen_time(str(record["external"]["gen_time"]))
    if sequence == 1:
        if previous is not None:
            raise AnchorError("sequence 1 has no previous head")
        if prev != genesis_id():
            raise AnchorError("sequence 1 does not point at the genesis id")
        return
    if previous is None:
        raise AnchorError("a later head needs the previous measured record")
    if sequence != int(previous["sequence"]) + 1:
        raise AnchorError("head sequence is not the previous sequence plus one")
    if prev != previous["anchor_id"]:
        raise AnchorError("prev_anchor_id is not the previous anchor id")
    if anchor_id == previous["anchor_id"]:
        raise AnchorError("anchor id is reused")
    previous_time = parse_gen_time(str(previous["external"]["gen_time"]))
    if gen_time <= previous_time:
        raise AnchorError("gen_time is not strictly later than the previous head")


def anchor_record(
    hnc_summary: dict[str, Any],
    token: bytes,
    parsed: dict[str, Any],
    token_text: str,
) -> dict[str, Any]:
    commitment = measurement_commitment(hnc_summary)
    if commitment["hnc_identity_changed"]:
        raise AnchorError(
            "Measured formula series sha256 differs from the public pin evidence "
            f"{PIN_FORMULA_SERIES_SHA256}. This receipt will not move "
            f"AUREON_PUBLIC_REQUIRE_PIN ({PUBLIC_PIN}). "
            "Refusing to record a new HNC identity."
        )
    anchor_id = hashlib.sha256(token).hexdigest()
    if EXPECTED_ANCHOR_ID and anchor_id != EXPECTED_ANCHOR_ID:
        raise AnchorError(
            "timestamp token does not match the recorded HNC head anchor id "
            f"{EXPECTED_ANCHOR_ID}"
        )
    measured = hashlib.sha256(commitment_bytes(commitment)).hexdigest()
    record = {
        "schema": SCHEMA,
        "receipt": 3,
        "receipt_name": "durable HNC evidence with an external monotonic head anchor",
        "tag": "measured",
        "go_live": "HOLD",
        "go_live_clear": False,
        "system_alive": False,
        "live_trading": False,
        "orders_placed": False,
        "external_llm": False,
        "market_series": False,
        "public_require_pin": PUBLIC_PIN,
        "hnc_identity_changed": False,
        "hnc_identity_note": (
            "The measured formula series sha256 matches the series recorded at the "
            "public pin. This receipt does not publish a new HNC identity and does "
            "not move AUREON_PUBLIC_REQUIRE_PIN."
        ),
        "sequence": 1,
        "prev_anchor_id": genesis_id(),
        "genesis": GENESIS,
        "anchor_id": anchor_id,
        "note_ref": NOTE_REF,
        "note_git_blob": git_blob_sha1(token_text.encode("ascii")),
        "measurement_sha256": measured,
        "measurement": commitment,
        "external": {
            "kind": "rfc3161",
            "provider": TSA_URL,
            "provider_contacted_by_check": False,
            "policy_oid": parsed["policy_oid"],
            "hash_algorithm": "sha256",
            "gen_time": parsed["gen_time"],
            "serial_hex": parsed["serial_hex"],
            "tsa_ordering": parsed["tsa_ordering"],
            "imprint_sha256": parsed["imprint_sha256"],
            "token_sha256": anchor_id,
            "verification": parsed["verification"],
            "ca": parsed["ca"],
        },
        "binding": {
            "token_source": f"{NOTE_REF} on HEAD, equal to the committed blob {TOKEN_REL}",
            "working_tree_is_not_the_source": True,
            "monotonic_rule": (
                "Sequence 1 points at the genesis id. A later head is a new timestamp "
                "whose sequence is one greater, whose prev_anchor_id is this anchor_id, "
                "and whose verified gen_time is strictly later. The timestamp authority "
                "reports ordering no, so this chain is the monotonic rule. This receipt "
                "does not append a later head. A working-tree edit does not move the git note."
            ),
        },
    }
    validate_chain(record)
    return record


def id_text(record: dict[str, Any]) -> str:
    return str(record["anchor_id"]) + "\n"


def assemble(root: Path, hnc_summary: dict[str, Any], *, require_note: bool) -> dict[str, str]:
    """Verify the external token and return the evidence files as text."""

    text = load_token_text(root, require_note=require_note)
    token = decode_token_text(text)
    commitment = commitment_bytes(measurement_commitment(hnc_summary))
    parsed = verify_timestamp(token, commitment)
    record = anchor_record(hnc_summary, token, parsed, text)
    blob = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=text.encode("ascii"),
        capture_output=True,
        cwd=root,
        check=False,
    )
    if blob.returncode != 0 or blob.stdout.decode("ascii").strip() != record["note_git_blob"]:
        raise AnchorError("git hash-object of the token text does not match note_git_blob")
    if EXPECTED_ANCHOR_ID == "":
        raise AnchorError("EXPECTED_ANCHOR_ID is empty; the measured head has not been recorded")
    return {
        TOKEN_REL: text,
        RECORD_REL: dump(record),
        ID_REL: id_text(record),
    }


def stamp_files(root: Path, hnc_summary: dict[str, Any]) -> dict[str, str]:
    """Request one timestamp and return the files. Check does not call this."""

    commitment = measurement_commitment(hnc_summary)
    if commitment["hnc_identity_changed"]:
        raise AnchorError(
            "Measured formula series sha256 differs from the public pin evidence. "
            f"Refusing to stamp a new HNC identity. Pin stays {PUBLIC_PIN}."
        )
    data = commitment_bytes(commitment)
    token = request_timestamp(data)
    text = canonical_token_text(token)
    parsed = verify_timestamp(token, data)
    record = anchor_record(hnc_summary, token, parsed, text)
    files = {
        TOKEN_REL: text,
        RECORD_REL: dump(record),
        ID_REL: id_text(record),
    }
    for relative, contents in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    return files


def attach_note(root: Path) -> None:
    """Attach the committed token to HEAD. Refuses a dirty working-tree copy."""

    path = root / TOKEN_REL
    head = read_head_blob(root)
    if head is None:
        raise AnchorError(f"{TOKEN_REL} is not committed on HEAD")
    work = path.read_bytes()
    if work != head:
        raise AnchorError("working tree token differs from HEAD; the note was not moved")
    proc = subprocess.run(
        ["git", "notes", "--ref", NOTE_NAME, "add", "-f", "-F", str(path), "HEAD"],
        cwd=root,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        raise AnchorError(f"git notes add failed: {detail}")
    note = read_note(root)
    if note != head:
        raise AnchorError("git note does not match the committed token")
