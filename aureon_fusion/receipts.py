"""🧾 RECEIPTS & AUDIT — the fusion's plumber crypto/contract layer.

Thin fusion layer over the upstream plumber modules
(aureon-os-upstream/aureon/plumber/{crypto,receipts,audit,schema,quorum}.py),
imported lazily and ONLY with the suppression env vars set first
(AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1, AUREON_AUDIT_MODE=1) and sys.path
pinned to the upstream repo root. Upstream launchers are never run.

Responsibilities:
  • ed25519 sign/verify for fusion events (key generated ONCE into the fusion
    state dir; private key never leaves that file, never printed).
  • optional canonical receipt attached to published thoughtbus envelopes
    (events.publish_event → receipts.attach_to_envelope; enabled by
    AUREON_FUSION_EVENT_SIGNING=1, degrade-silent otherwise).
  • `filter <file>` CLI — the external-output filter: refuses anything
    destined to leave the machine that carries secret-bearing keys
    (plumber audit.assert_public_summary_safe) or secret-like values
    (high-entropy token/password/API-key patterns).
  • SQLiteRuntimeIntrusionLedgerV04 instantiated as the fusion audit ledger
    (fusion state dir), wrapped by log_intrusion(event) — called from
    capability_gate refusals and organ_registry prune/stop events.
    Audit hooks must never raise: they degrade to None.
  • bot_army_catalog.json → state/bot_army_catalog_snapshot.json read-only
    snapshot + data-source registration note.

Import-safe: no upstream import, no key generation, no ledger open at import.

CLI:
  python -m aureon_fusion.receipts --help
  python -m aureon_fusion.receipts status
  python -m aureon_fusion.receipts filter <file>     (exit 1 = unsafe)
  python -m aureon_fusion.receipts verify <file>     (verify a signed event)
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from .paths import AUREON_UPSTREAM, FUSION_STATE

# ───────────────────────── doctrine: upstream import guard ─────────────────
# These MUST be set before ANY aureon import; setdefault keeps an explicit
# external choice intact.
os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

SIGNING_ENABLED_ENV = "AUREON_FUSION_EVENT_SIGNING"

KEY_FILE = FUSION_STATE / "receipts_ed25519.key"          # hex private key
PUBLIC_KEY_FILE = FUSION_STATE / "receipts_ed25519.pub"   # hex public key
LEDGER_HNC_KEY_FILE = FUSION_STATE / "intrusion_ledger_hnc.key"
LEDGER_PATH = FUSION_STATE / "intrusion_ledger.sqlite3"
LEDGER_ID = "aureon-fusion-runtime"
SNAPSHOT_FILE = FUSION_STATE / "bot_army_catalog_snapshot.json"
DATA_SOURCES_FILE = FUSION_STATE / "data_sources.json"
UPSTREAM_CATALOG = AUREON_UPSTREAM / "bot_army_catalog.json"

EVENT_SIGNATURE_DOMAIN = "aureon.fusion.event.signature.v0"
RECEIPT_DOMAIN = "aureon.fusion.receipt.v0"

_plumber = None       # upstream plumber modules, lazy
_signing_key = None   # Ed25519PrivateKey, lazy
_ledger = None        # SQLiteRuntimeIntrusionLedgerV04, lazy

# Secret-like value heuristics for the external-output filter. Keys are
# descriptive only; patterns never capture or echo the secret itself.
_SECRET_VALUE_PATTERNS = (
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("generic_assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)"
        r"[\w\s\"']{0,12}[:=]\s*[\"']?([A-Za-z0-9_\-+/=.]{16,})[\"']?")),
)


def _ensure_upstream_importable() -> None:
    """Pin the upstream repo root onto sys.path (idempotent)."""
    root = str(AUREON_UPSTREAM)
    if root not in sys.path:
        sys.path.insert(0, root)


def _plumber_modules():
    """Lazily import the upstream plumber crypto/contract modules.

    Only ever reached with the suppression env vars set (above) and the
    upstream root pinned on sys.path. Never raises intentionally — callers
    treat None as 'plumber unavailable, degrade'."""
    global _plumber
    if _plumber is None:
        try:
            _ensure_upstream_importable()
            from aureon.plumber import audit as plumber_audit
            from aureon.plumber import crypto as plumber_crypto
            from aureon.plumber import receipts as plumber_receipts
            from aureon.plumber import schema as plumber_schema
            from aureon.plumber import quorum as plumber_quorum
            _plumber = {
                "audit": plumber_audit,
                "crypto": plumber_crypto,
                "receipts": plumber_receipts,
                "schema": plumber_schema,
                "quorum": plumber_quorum,
            }
        except Exception:
            _plumber = {}
    return _plumber or None


def _import_error():
    try:
        _ensure_upstream_importable()
        import aureon.plumber.crypto  # noqa: F401
        return None
    except Exception as exc:
        return exc


def _chmod_owner_only(path: Path) -> None:
    """chmod 0600-equivalent best effort (POSIX); on Windows this is a
    no-op — the ACL note belongs in the operator report instead."""
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


# ───────────────────────── signing key custody ─────────────────────────────

def get_signing_key():
    """Load-or-generate the fusion ed25519 signing key (once per machine).

    The private key lives only in KEY_FILE (owner-only ACL intended;
    chmod 0600 on POSIX). It is never printed, never copied elsewhere."""
    global _signing_key
    if _signing_key is not None:
        return _signing_key
    crypto = (_plumber_modules() or {}).get("crypto")
    if crypto is None:
        return None
    try:
        if KEY_FILE.exists():
            raw = KEY_FILE.read_text(encoding="utf-8").strip()
            _signing_key = crypto.load_ed25519_private_key(raw)
            return _signing_key
        _signing_key = crypto.generate_ed25519_private_key()
        FUSION_STATE.mkdir(parents=True, exist_ok=True)
        tmp = KEY_FILE.with_suffix(".tmp")
        tmp.write_text(_signing_key.private_bytes_raw().hex() + "\n",
                       encoding="utf-8")
        _chmod_owner_only(tmp)
        os.replace(tmp, KEY_FILE)
        PUBLIC_KEY_FILE.write_text(
            crypto.ed25519_public_key_hex(_signing_key) + "\n", encoding="utf-8")
        return _signing_key
    except Exception:
        _signing_key = None
        return None


def public_key_hex() -> str:
    key = get_signing_key()
    crypto = (_plumber_modules() or {}).get("crypto")
    if key is None or crypto is None:
        return ""
    try:
        return crypto.ed25519_public_key_hex(key)
    except Exception:
        return ""


# ───────────────────────── sign / verify fusion events ─────────────────────

def sign_event(source: str, topic: str, payload: dict) -> dict:
    """Sign a fusion event; returns the canonical signed-event dict.

    Canonical receipt = {"receipt_hash", "signature", "signer_public_key",
    "signed_at"} — receipt_hash binds signer + source + topic + payload.
    Returns a plain unsigned-shape dict with receipt=None when plumbing or
    key custody is unavailable (degrade, never raise)."""
    event = {
        "schema": "aureon.fusion.event.v1",
        "source": str(source),
        "topic": str(topic),
        "payload": payload or {},
    }
    crypto = (_plumber_modules() or {}).get("crypto")
    key = get_signing_key()
    if crypto is None or key is None:
        event["receipt"] = None
        return event
    receipt_values = {
        "schema": "aureon.fusion.receipt.v1",
        "source": event["source"],
        "topic": event["topic"],
        "payload_commitment": crypto.domain_hash(
            "aureon.fusion.event.payload.v1", event["payload"]),
        "signer_public_key": crypto.ed25519_public_key_hex(key),
    }
    receipt_hash = crypto.domain_hash(RECEIPT_DOMAIN, receipt_values)
    signature = crypto.sign_ed25519(
        key, {"receipt_hash": receipt_hash}, domain=EVENT_SIGNATURE_DOMAIN)
    event["receipt"] = {
        **receipt_values,
        "receipt_hash": receipt_hash,
        "signature": signature,
    }
    return event


def verify_event(event: dict) -> bool:
    """Verify a signed event dict produced by sign_event().

    False on any structural or signature problem — never raises."""
    try:
        crypto = (_plumber_modules() or {}).get("crypto")
        if crypto is None:
            return False
        receipt = event.get("receipt")
        if not isinstance(receipt, dict):
            return False
        receipt_values = {
            "schema": receipt["schema"],
            "source": event["source"],
            "topic": event["topic"],
            "payload_commitment": crypto.domain_hash(
                "aureon.fusion.event.payload.v1", event.get("payload") or {}),
            "signer_public_key": receipt["signer_public_key"],
        }
        if crypto.domain_hash(RECEIPT_DOMAIN, receipt_values) != receipt["receipt_hash"]:
            return False
        return bool(crypto.verify_ed25519(
            receipt["signer_public_key"],
            {"receipt_hash": receipt["receipt_hash"]},
            receipt["signature"],
            domain=EVENT_SIGNATURE_DOMAIN,
        ))
    except Exception:
        return False


def attach_to_envelope(envelope) -> None:
    """Optionally attach an ed25519 signature + canonical receipt to a
    published thoughtbus envelope, IN PLACE. Enabled only when
    AUREON_FUSION_EVENT_SIGNING=1. Degrades silently — an organ that
    cannot sign must never die because of it."""
    if os.environ.get(SIGNING_ENABLED_ENV, "").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    try:
        if envelope is None:
            return
        payload = getattr(envelope, "payload", None)
        if payload is None and isinstance(envelope, dict):
            payload = envelope.get("payload")
        if not isinstance(payload, dict):
            return
        source = getattr(envelope, "source", None) or (envelope.get("source") if isinstance(envelope, dict) else None)
        topic = getattr(envelope, "topic", None) or (envelope.get("topic") if isinstance(envelope, dict) else None)
        signed = sign_event(str(source), str(topic), payload)
        receipt = signed.get("receipt")
        if receipt is None:
            return
        if isinstance(envelope, dict):
            envelope["receipt"] = receipt
        else:
            setattr(envelope, "receipt", receipt)
    except Exception:
        return


# ───────────────────────── external-output filter ──────────────────────────

def scan_for_secrets(value) -> list:
    """Return a list of findings (code, path) for secret-bearing content.

    Layer 1: upstream plumber audit.assert_public_summary_safe (forbidden
    key names). Layer 2: secret-like VALUE patterns (tokens, keys, blocks).
    Values are never echoed — findings carry the pattern code and JSON path
    only."""
    findings = []
    try:
        modules = _plumber_modules()
        if modules:
            modules["audit"].assert_public_summary_safe(value)
    except Exception as exc:
        findings.append(("forbidden_key_name", "$", str(exc)))

    def walk(item, path):
        if isinstance(item, dict):
            for key, nested in item.items():
                walk(nested, f"{path}.{key}")
        elif isinstance(item, (list, tuple)):
            for index, nested in enumerate(item):
                walk(nested, f"{path}[{index}]")
        elif isinstance(item, str):
            for code, pattern in _SECRET_VALUE_PATTERNS:
                if pattern.search(item):
                    findings.append((code, path, ""))

    try:
        walk(value, "$")
    except Exception as exc:
        findings.append(("scan_error", "$", str(exc)))
    return findings


def filter_file(path) -> dict:
    """External-output gate for a JSON file. Returns a report dict with
    'safe' (bool) and 'findings'. Non-JSON input is treated as text and
    scanned line-wise. Never raises."""
    path = Path(path)
    report = {"file": str(path), "safe": True, "findings": [],
              "sha256": None, "bytes": 0}
    try:
        raw = path.read_bytes()
        report["bytes"] = len(raw)
        report["sha256"] = hashlib.sha256(raw).hexdigest()
    except OSError as exc:
        report["safe"] = False
        report["findings"].append(("unreadable", "$", str(exc)))
        return report
    try:
        value = json.loads(raw.decode("utf-8"))
    except Exception:
        value = raw.decode("utf-8", errors="replace")
    findings = scan_for_secrets(value)
    if findings:
        report["safe"] = False
        report["findings"] = [
            {"code": code, "path": p, "detail": detail}
            for code, p, detail in findings
        ]
    return report


# ───────────────────────── intrusion audit ledger ──────────────────────────

def _ledger_hnc_key_provider():
    """Key material provider for the ledger's HNC quarantine wrapping.
    Generated once into fusion state (never printed); wiped from memory by
    the ledger itself on close."""
    try:
        if LEDGER_HNC_KEY_FILE.exists():
            return LEDGER_HNC_KEY_FILE.read_text(encoding="utf-8").strip()
        import secrets
        material = secrets.token_hex(32)
        tmp = LEDGER_HNC_KEY_FILE.with_suffix(".tmp")
        tmp.write_text(material + "\n", encoding="utf-8")
        _chmod_owner_only(tmp)
        os.replace(tmp, LEDGER_HNC_KEY_FILE)
        return material
    except Exception:
        return None


def get_ledger():
    """Lazily open (or reopen) the fusion intrusion ledger. None on any
    failure — audit plumbing must never take an organ down."""
    global _ledger
    try:
        if _ledger is not None:
            return _ledger
        _ensure_upstream_importable()
        from aureon.plumber.runtime_intrusion_ledger_v04 import (
            SQLiteRuntimeIntrusionLedgerV04,
        )
        FUSION_STATE.mkdir(parents=True, exist_ok=True)
        _ledger = SQLiteRuntimeIntrusionLedgerV04(
            LEDGER_PATH,
            ledger_id=LEDGER_ID,
            quarantine_hnc_key_provider=_ledger_hnc_key_provider,
        )
        return _ledger
    except Exception:
        _ledger = None
        return None


# The upstream ledger is a SEALED contract: append_violation authenticates
# the quarantine packet against the runtime-guard's exact census — source_id
# must be "aureon:runtime-guard-v04", ingress_kind "runtime-effect-violation",
# reason_code "runtime_effect_not_magic_star_released", and the caller_aad
# event_name must be one of the guard's supported rule events. Fusion audit
# events are therefore mapped onto the nearest guard event; the fusion-level
# semantic (which organ, which gate, why) is carried ONLY as a sha256
# resource_commitment — no raw detail strings ever reach the ledger.
_FUSION_TO_GUARD_EVENT = {
    "organ_registry.stop": "os.kill",
    "organ_registry.prune": "os.kill",
    "organ_registry.prune_failure": "os.kill",
    "capability_gate.refusal": "open",
}
_RUNTIME_INTRUSION_REASON = "runtime_effect_not_magic_star_released"
_RUNTIME_INTRUSION_PURPOSE = "aureon.plumber.runtime-intrusion-quarantine.v04"
_SEQ_FILE = FUSION_STATE / "intrusion_ledger_seq.json"
_SEQ_LOCK_FILE = FUSION_STATE / "intrusion_ledger_seq.json.lock"


def _acquire_seq_lock(timeout_s: float = 10.0):
    """Advisory inter-process lock for the recorder-sequence RMW (msvcrt
    locking on Windows / flock elsewhere — same pattern as upstream
    aureon_lambda_engine._acquire_advisory_lock). Returns the handle or
    None on conflict; caller must pass it to _release_seq_lock."""
    deadline = time.monotonic() + timeout_s
    while True:
        handle = None
        try:
            handle = open(_SEQ_LOCK_FILE, "a+b")
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\x00")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),
                            fcntl.LOCK_EX | fcntl.LOCK_NB)  # noqa: F821
            return handle
        except (ImportError, OSError):
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.05)


def _release_seq_lock(handle) -> None:
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)  # noqa: F821
    except (ImportError, OSError):
        pass
    finally:
        try:
            handle.close()
        except OSError:
            pass


def _next_recorder_sequence() -> int:
    """Bounded monotonic recorder sequence (1..4096 per the upstream
    contract), persisted so each process picks a fresh slot. The
    read-modify-write runs under an advisory lock with a per-pid unique tmp
    file + os.replace: two concurrent log_intrusion callers must never draw
    the same sequence. On lock conflict the counter is NOT advanced and the
    current on-disk value is returned (fail-closed: the ledger append still
    records an event, but sequences are never duplicated)."""
    handle = _acquire_seq_lock()
    if handle is None:
        try:
            if _SEQ_FILE.exists():
                return int(json.loads(
                    _SEQ_FILE.read_text(encoding="utf-8")).get("seq", 0))
        except Exception:
            pass
        return 0
    try:
        seq = 0
        try:
            if _SEQ_FILE.exists():
                seq = int(json.loads(_SEQ_FILE.read_text(encoding="utf-8")).get("seq", 0))
        except Exception:
            seq = 0
        seq = (seq % 4096) + 1
        tmp = _SEQ_FILE.with_name(
            f"{_SEQ_FILE.name}.tmp.{os.getpid()}.{time.time_ns()}")
        try:
            tmp.write_text(json.dumps({"seq": seq}), encoding="utf-8")
            last = None
            for attempt in range(20):
                try:
                    os.replace(tmp, _SEQ_FILE)
                    last = None
                    break
                except OSError as exc:
                    last = exc
                    if attempt < 19:
                        time.sleep(0.05)
            if last is not None:
                raise last
        except OSError:
            pass
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
        return seq
    finally:
        _release_seq_lock(handle)


def log_intrusion(event: dict) -> dict:
    """Append one intrusion/audit event to the ledger.

    Thin wrapper over the sealed upstream contract: the fusion event is
    mapped to the runtime guard's violation census, quarantine-wrapped
    through the upstream OS protection boundary (encrypted HNC packet, no
    plaintext or raw arguments persisted — fusion detail is reduced to a
    sha256 commitment), and appended via the ledger's own append_violation
    (hash-chained, read-back verified). Returns the entry receipt dict, or
    None on any failure — NEVER raises."""
    try:
        _ensure_upstream_importable()
        from aureon.plumber.os_protection import (
            LocalOSProtectionBoundary,
            QuarantinedHNC,
        )
        from aureon.plumber.crypto import canonical_json_bytes
        ledger = get_ledger()
        if ledger is None:
            return None
        fusion_event = str(event.get("event") or event.get("event_name")
                           or "fusion.audit")
        reason = str(event.get("reason") or "unspecified")
        detail = {k: (str(v) if not isinstance(v, (str, int, bool)) else v)
                  for k, v in (event.get("detail") or {}).items()
                  if isinstance(v, (str, int, bool))}
        guard_event = _FUSION_TO_GUARD_EVENT.get(fusion_event, "open")
        resource_commitment = hashlib.sha256(canonical_json_bytes({
            "fusion_event": fusion_event,
            "reason": reason,
            "detail": detail,
        })).hexdigest()
        caller_aad = {
            "event_name": guard_event,
            "resource_commitment": resource_commitment,
            "reason_code": _RUNTIME_INTRUSION_REASON,
        }
        content = canonical_json_bytes({
            "schema": "aureon.plumber.runtime-intrusion.v04",
            "sequence": _next_recorder_sequence(),
            "event_name": guard_event,
            "resource_commitment": resource_commitment,
            "reason_code": _RUNTIME_INTRUSION_REASON,
            "raw_arguments_retained": False,
            "audit_event_origin_attested": False,
            "effect_attempt_attested": False,
            "resource_commitment_confidentiality_attested": False,
            "resource_commitments_keyed": False,
            "action_eligible": False,
            "economic_eligible": False,
            "production_ready": False,
        })
        boundary = LocalOSProtectionBoundary(
            boundary_id="aureon-fusion-intrusion-boundary",
            master_key_provider=_ledger_hnc_key_provider,
            max_ingress_bytes=max(1024, min(len(content), 4 * 1024 * 1024)),
            trusted_now=lambda: datetime.now(UTC),
        )
        boundary._durable_evidence_ledger_instance_commitment = str(
            ledger.preflight()["ledger_instance_commitment"])
        outcome = boundary.admit_external(
            content,
            source_id="aureon:runtime-guard-v04",
            ingress_kind="runtime-effect-violation",
            purpose=_RUNTIME_INTRUSION_PURPOSE,
            operator_aad=caller_aad,
        )
        if not isinstance(outcome, QuarantinedHNC):
            return None
        packet = dict(boundary._quarantine_packets[outcome.admission_id])
        metadata = {
            "schema": "aureon.plumber.os-durable-quarantine-evidence.v04",
            "intrusion_id": outcome.admission_id,
            "content_sha256": outcome.content_sha256,
            "source_id_sha256": hashlib.sha256(
                outcome.source_id.encode("utf-8")).hexdigest(),
            "ingress_kind_sha256": hashlib.sha256(
                outcome.ingress_kind.encode("utf-8")).hexdigest(),
            "denial_code_count": len(outcome.denial_codes),
            "raw_arguments_retained": False,
            "plaintext_retained": False,
            "action_eligible": False,
            "economic_eligible": False,
            "production_ready": False,
        }
        return ledger.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=metadata,
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    except Exception:
        return None


def ledger_summary() -> dict:
    ledger = get_ledger()
    if ledger is None:
        return {"ready": False}
    try:
        summary = ledger.preflight()
        return {
            "ready": bool(summary.get("ready")),
            "path": str(LEDGER_PATH),
            "entry_count": summary.get("entry_count"),
            "violation_count": summary.get("violation_count"),
            "max_violation_entries": summary.get("max_violation_entries"),
            "ledger_instance_commitment": summary.get("ledger_instance_commitment"),
        }
    except Exception:
        return {"ready": False}


# ───────────────────────── bot army catalog snapshot ───────────────────────

def ensure_catalog_snapshot() -> dict:
    """One-time read-only snapshot of the upstream bot_army_catalog.json
    into fusion state. The upstream file is NEVER written. Registers the
    snapshot in state/data_sources.json (additive). Returns a note dict."""
    note = {
        "name": "bot_army_catalog_snapshot",
        "source": str(UPSTREAM_CATALOG),
        "snapshot": str(SNAPSHOT_FILE),
        "mode": "read-only snapshot",
        "registered_at": None,
        "sha256": None,
        "bytes": 0,
    }
    try:
        if not SNAPSHOT_FILE.exists():
            raw = UPSTREAM_CATALOG.read_bytes()
            tmp = SNAPSHOT_FILE.with_suffix(".tmp")
            tmp.write_bytes(raw)
            os.replace(tmp, SNAPSHOT_FILE)
        raw = SNAPSHOT_FILE.read_bytes()
        note["sha256"] = hashlib.sha256(raw).hexdigest()
        note["bytes"] = len(raw)
        _register_data_source(note)
    except Exception as exc:
        note["error"] = str(exc)
    return note


def _register_data_source(note: dict) -> None:
    """Additive registration into state/data_sources.json."""
    entry = {
        "name": note["name"],
        "source": note["source"],
        "snapshot": note["snapshot"],
        "mode": note["mode"],
        "sha256": note.get("sha256"),
        "registered_by": "aureon_fusion.receipts",
    }
    data = {}
    try:
        if DATA_SOURCES_FILE.exists():
            data = json.loads(DATA_SOURCES_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    sources = data.get("sources")
    if not isinstance(sources, list):
        sources = []
    sources = [s for s in sources
               if not (isinstance(s, dict) and s.get("name") == entry["name"])]
    sources.append(entry)
    data["sources"] = sources
    tmp = DATA_SOURCES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    os.replace(tmp, DATA_SOURCES_FILE)


def data_source_notes() -> list:
    try:
        if DATA_SOURCES_FILE.exists():
            data = json.loads(DATA_SOURCES_FILE.read_text(encoding="utf-8"))
            sources = data.get("sources")
            if isinstance(sources, list):
                return [s for s in sources if isinstance(s, dict)]
    except Exception:
        pass
    return []


# ───────────────────────── CLI ─────────────────────────────────────────────

def _cmd_status() -> int:
    print("═" * 72)
    print("🧾 RECEIPTS & AUDIT — status")
    print("═" * 72)
    err = _import_error()
    if err is None:
        print(f"  upstream plumber import : OK (suppression env vars set)")
    else:
        print(f"  upstream plumber import : UNAVAILABLE ({type(err).__name__}: {err})")
    print(f"  signing key             : {KEY_FILE} (present={KEY_FILE.exists()})")
    print(f"  public key              : {public_key_hex() or '(unavailable)'}")
    print(f"  event signing (bus)     : {SIGNING_ENABLED_ENV}="
          f"{os.environ.get(SIGNING_ENABLED_ENV, '0')}")
    summary = ledger_summary()
    if summary.get("ready"):
        print(f"  intrusion ledger        : {summary['path']}")
        print(f"    entries={summary['entry_count']} "
              f"violations={summary['violation_count']} "
              f"capacity={summary['max_violation_entries']}")
    else:
        print(f"  intrusion ledger        : not ready ({LEDGER_PATH})")
    note = ensure_catalog_snapshot()
    print(f"  catalog snapshot        : {note.get('snapshot')} "
          f"({note.get('bytes', 0)} bytes, sha256={str(note.get('sha256'))[:16]}…)")
    sources = data_source_notes()
    print(f"  data source notes       : {len(sources)} registered")
    for s in sources:
        print(f"    - {s.get('name')}: {s.get('snapshot')}")
    print("═" * 72)
    return 0 if err is None else 1


def _cmd_filter(path) -> int:
    report = filter_file(path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["safe"]:
        print("FILTER: SAFE — no secret-bearing content detected.")
        return 0
    print(f"FILTER: REFUSED — {len(report['findings'])} finding(s); "
          "this content must not leave the machine.", file=sys.stderr)
    return 1


def _cmd_verify(path) -> int:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"verify: cannot read JSON: {exc}", file=sys.stderr)
        return 2
    ok = verify_event(value)
    print(f"verify: {'VALID signature' if ok else 'INVALID or missing signature'} "
          f"({path})")
    return 0 if ok else 1


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.receipts <verb>")
        print("  status          key custody, ledger, snapshot, data sources")
        print("  filter <file>   external-output leak gate (exit 1 = refused)")
        print("  verify <file>   verify a signed event JSON file")
        print(f"  env {SIGNING_ENABLED_ENV}=1 enables bus envelope signing")
        return 0
    verb = argv[0]
    if verb == "status":
        return _cmd_status()
    if verb == "filter":
        if len(argv) < 2:
            print("usage: filter <file>", file=sys.stderr)
            return 2
        return _cmd_filter(argv[1])
    if verb == "verify":
        if len(argv) < 2:
            print("usage: verify <file>", file=sys.stderr)
            return 2
        return _cmd_verify(argv[1])
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
