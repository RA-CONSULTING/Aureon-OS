"""📨 OUTBOUND MESSENGER — the organism's conscience-gated send surface.

Owner decree (absolute):
  • Conscience VETO is absolute. Never weaken a gate; honest failure is
    always acceptable, fake success never is.
  • FAIL-CLOSED everywhere: no approval flag → every send refused. An
    unreadable conscience is a conscience that said no. An empty/missing
    allowlist refuses every recipient. No exceptions escape as consent.
  • Never log credentials or message bodies — the journal records hashes
    and gate verdicts only.

THE SEND CONTRACT:
    send(recipient, subject, body, source="organism") -> dict

Every call passes three fail-closed gates, in order:
  1. APPROVAL FLAG — the exact line 'OUTBOUND_AUTHORIZED_BY_GARY' must be
     present in aureon_fusion/state/outbound_approval.flag (the owner
     decree instrument shared with aureon_fusion.outbound_messaging).
     Absent/unreadable → {'sent': False, 'reason': 'not_approved'}.
  2. CONSCIENCE — conscience_hook.evaluate; VETO is absolute and any
     internal error degrades to a refusal (an unreadable conscience is a
     conscience that said no).
  3. RECIPIENT ALLOWLIST — ONLY addresses explicitly listed in
     aureon_fusion/state/outbound_allowlist.json ("recipients" list) may
     be sent to. Empty/absent/unreadable list → every send refused
     (fail-closed; the file ships empty — Gary adds recipients by decree).

TRANSPORT:
  SMTP credentials are discovered at SEND TIME from the environment /
  .env-style files (key names OUTBOUND_SMTP_HOST / _PORT / _USER /
  _PASSWORD / _FROM / _TLS). Values are never logged. When no usable
  transport is configured the capability is still LIVE — the send returns
  {'sent': False, 'reason': 'no_transport_configured'} and the journal
  records the full gate pass; the transport waits for Gary's keys.

JOURNAL:
  Every send (refused or sent) is journaled to
  aureon_fusion/state/outbound/journal.jsonl: ts, recipient, subject
  SHA-256, source, per-gate outcomes, final outcome. Bodies and
  credentials never reach the journal.

Import-safe: nothing sends at import. Stdlib only. Suppression env vars
honored via setdefault. Writes are locked JSONL appends.

CLI:
    python -m aureon_fusion.outbound_messenger status
    python -m aureon_fusion.outbound_messenger send --to A --subject S \
        --body B [--source organism]
"""

import hashlib
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from .paths import FUSION_STATE, WORKSPACE
from .door_registry import _append_line

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# ───────────────────────── doctrine constants ──────────────────────────────

APPROVAL_FLAG = FUSION_STATE / "outbound_approval.flag"
APPROVAL_LINE = "OUTBOUND_AUTHORIZED_BY_GARY"
ALLOWLIST_FILE = FUSION_STATE / "outbound_allowlist.json"
JOURNAL_FILE = FUSION_STATE / "outbound" / "journal.jsonl"
NETWORK_TIMEOUT_S = 30

# .env-style files scanned for transport keys (key NAMES only are ever
# reported; values are read at send time and never logged).
ENV_FILES = (
    FUSION_STATE / "outbound_messaging.env",
    WORKSPACE / ".env",
)

SMTP_KEYS = ("OUTBOUND_SMTP_HOST", "OUTBOUND_SMTP_PORT", "OUTBOUND_SMTP_USER",
             "OUTBOUND_SMTP_PASSWORD", "OUTBOUND_SMTP_FROM", "OUTBOUND_SMTP_TLS")

# Test/probe injection point: callable(host, port) -> SMTP-like object with
# starttls/login/send_message/quit (or SMTP_SSL semantics when port == 465).
# None → the real smtplib transport.
SMTP_FACTORY = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ───────────────────────── gate 1: approval flag ───────────────────────────

def _approval() -> dict:
    """Fail-closed read of the owner decree flag (same instrument and exact
    line as aureon_fusion.outbound_messaging)."""
    authorized = False
    present = False
    try:
        present = APPROVAL_FLAG.exists()
        if present:
            with open(APPROVAL_FLAG, "r", encoding="utf-8") as f:
                authorized = APPROVAL_LINE in [
                    line.strip() for line in f.read().splitlines()]
    except Exception:
        authorized = False
    return {"ok": authorized, "flag_file": str(APPROVAL_FLAG),
            "flag_present": present, "authorized": authorized}


# ───────────────────────── gate 2: conscience ──────────────────────────────

def _conscience_evaluate(action_desc: str, context: dict) -> dict:
    """Conscience gate. VETO blocks; any internal error degrades to a
    refusal (fail-closed). Test/probe hook: patch this name to stub."""
    try:
        from . import conscience_hook
        verdict = conscience_hook.evaluate(action_desc, context or {})
        if not isinstance(verdict, dict):
            return {"ok": False, "verdict": "UNREADABLE",
                    "reasoning": "conscience returned no verdict — fail-closed"}
        return {"ok": verdict.get("verdict") != "VETO",
                "verdict": verdict.get("verdict"),
                "reasoning": (verdict.get("reasoning") or "")[:240]}
    except Exception as exc:
        return {"ok": False, "verdict": "UNREADABLE",
                "reasoning": f"conscience error ({type(exc).__name__}) — "
                             f"fail-closed refusal"}


# ───────────────────────── gate 3: recipient allowlist ─────────────────────

def _load_allowlist() -> list:
    """The allowlisted recipient set. Any error → empty set (fail-closed:
    an unreadable allowlist refuses everyone)."""
    try:
        if ALLOWLIST_FILE.exists():
            with open(ALLOWLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            recipients = data.get("recipients")
            if isinstance(recipients, list):
                return [str(r).strip().lower() for r in recipients
                        if str(r).strip()]
    except Exception:
        pass
    return []


def _allowlisted(recipient: str) -> dict:
    allowed = _load_allowlist()
    ok = str(recipient).strip().lower() in set(allowed)
    return {"ok": ok, "file": str(ALLOWLIST_FILE),
            "allowlist_count": len(allowed)}


# ───────────────────────── transport discovery (names only) ────────────────

def _read_env_file(path: Path) -> dict:
    cfg = {}
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    cfg[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        return {}
    return cfg


def _smtp_config() -> dict:
    """Transport config at SEND TIME: environment first, then .env-style
    files. Only OUTBOUND_SMTP_* keys are considered; values are never
    logged or returned beyond this function's use."""
    cfg = {}
    for key in SMTP_KEYS:
        value = os.environ.get(key)
        if value:
            cfg[key] = value.strip()
    if "OUTBOUND_SMTP_HOST" not in cfg:
        for env_file in ENV_FILES:
            file_cfg = _read_env_file(env_file)
            for key in SMTP_KEYS:
                if key not in cfg and file_cfg.get(key):
                    cfg[key] = file_cfg[key]
    return cfg


def _transport_status() -> dict:
    """Names-only transport profile for status/CLI: which keys are present,
    never what they contain."""
    cfg = _smtp_config()
    host = bool(cfg.get("OUTBOUND_SMTP_HOST"))
    from_addr = bool(cfg.get("OUTBOUND_SMTP_FROM"))
    return {"configured": host and from_addr,
            "keys_present": sorted(k for k in SMTP_KEYS if cfg.get(k)),
            "required_missing": [k for k, present in
                                 (("OUTBOUND_SMTP_HOST", host),
                                  ("OUTBOUND_SMTP_FROM", from_addr))
                                 if not present],
            "env_files_scanned": [str(p) for p in ENV_FILES]}


# ───────────────────────── journal ─────────────────────────────────────────

def _journal(record: dict) -> None:
    """Locked JSONL append. Never raises; bodies/credentials are excluded
    by construction (callers pass hashed/metadata fields only)."""
    try:
        _append_line(JOURNAL_FILE, json.dumps(record, ensure_ascii=False,
                                              default=str))
    except Exception:
        pass


def _subject_hash(subject: str) -> str:
    return hashlib.sha256(subject.encode("utf-8", "replace")).hexdigest()


# ───────────────────────── the send surface ────────────────────────────────

def send(recipient: str, subject: str, body: str,
         source: str = "organism") -> dict:
    """Conscience-gated send. Three fail-closed gates (approval flag →
    conscience → recipient allowlist), then transport. Every call is
    journaled. Never raises; never logs bodies or credentials."""
    recipient = str(recipient or "").strip()
    subject = str(subject or "")
    ts = _utc_now()
    base = {"ts": ts, "recipient": recipient,
            "subject_sha256": _subject_hash(subject), "source": str(source)}

    # Gate 1 — APPROVAL FLAG.
    approval = _approval()
    if not approval["ok"]:
        result = {**base, "sent": False, "reason": "not_approved",
                  "gates": {"approval": approval["ok"]},
                  "detail": (f"owner approval flag missing or unreadable — "
                             f"the exact line '{APPROVAL_LINE}' must be in "
                             f"{APPROVAL_FLAG}")}
        _journal(result)
        return result

    # Gate 2 — CONSCIENCE (VETO absolute).
    desc = (f"send outbound message to <{recipient}> "
            f"(subject sha256 {_subject_hash(subject)[:12]}…) "
            f"on behalf of {source}")
    conscience = _conscience_evaluate(desc, {
        "organ": "outbound_messenger", "recipient": recipient,
        "source": source})
    if not conscience["ok"]:
        result = {**base, "sent": False,
                  "reason": ("conscience_unreadable" if conscience.get("verdict") == "UNREADABLE"
                             else "conscience_veto"),
                  "gates": {"approval": True, "conscience": conscience},
                  "detail": conscience.get("reasoning", "conscience refused")}
        _journal(result)
        return result

    # Gate 3 — RECIPIENT ALLOWLIST.
    allow = _allowlisted(recipient)
    if not allow["ok"]:
        result = {**base, "sent": False, "reason": "recipient_not_allowlisted",
                  "gates": {"approval": True, "conscience": True,
                            "allowlist": allow},
                  "detail": (f"<{recipient}> is not in {ALLOWLIST_FILE} "
                             f"({allow['allowlist_count']} allowlisted) — "
                             f"empty allowlist refuses every send")}
        _journal(result)
        return result

    gates = {"approval": True, "conscience": True, "allowlist": allow}

    # Transport — capability live, transport waits for Gary's keys.
    cfg = _smtp_config()
    host = cfg.get("OUTBOUND_SMTP_HOST")
    from_addr = cfg.get("OUTBOUND_SMTP_FROM")
    if not host or not from_addr:
        result = {**base, "sent": False, "reason": "no_transport_configured",
                  "gates": gates,
                  "detail": ("all gates passed; no OUTBOUND_SMTP_HOST/"
                             "OUTBOUND_SMTP_FROM in env or .env files — "
                             "the capability is live, the transport waits "
                             "for the owner's keys")}
        _journal(result)
        return result

    port = int(cfg.get("OUTBOUND_SMTP_PORT", "587"))
    use_tls = cfg.get("OUTBOUND_TLS", "1") != "0" and port != 465
    try:
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)
        factory = SMTP_FACTORY
        if factory is not None:
            server = factory(host, port)
        elif port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=NETWORK_TIMEOUT_S,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=NETWORK_TIMEOUT_S)
        try:
            if factory is None and use_tls:
                server.starttls(context=ssl.create_default_context())
            user = cfg.get("OUTBOUND_SMTP_USER")
            if user:
                server.login(user, cfg.get("OUTBOUND_SMTP_PASSWORD", ""))
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass
        result = {**base, "sent": True, "reason": None, "gates": gates,
                  "transport": "smtp", "smtp_host": host,
                  "detail": "sent via SMTP (credentials never logged)"}
        _journal(result)
        return result
    except Exception as exc:
        result = {**base, "sent": False, "reason": "smtp_error",
                  "gates": gates, "transport": "smtp",
                  "detail": f"smtp error: {type(exc).__name__}: "
                            f"{str(exc)[:200]}"}
        _journal(result)
        return result


# ───────────────────────── status & CLI ────────────────────────────────────

def _journal_tail(n: int = 5) -> list:
    try:
        if not JOURNAL_FILE.exists():
            return []
        lines = JOURNAL_FILE.read_text(encoding="utf-8",
                                       errors="replace").splitlines()
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except Exception:
                out.append({"unparseable": line[:120]})
        return out
    except Exception:
        return []


def status() -> dict:
    return {"approval": _approval(),
            "allowlist": {"file": str(ALLOWLIST_FILE),
                          "count": len(_load_allowlist())},
            "transport": _transport_status(),
            "journal_file": str(JOURNAL_FILE),
            "journal_tail": _journal_tail(5)}


def _print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.outbound_messenger "
              "status|send --to A --subject S --body B [--source NAME]")
        print("  status   approval flag, allowlist count, transport "
              "configured yes/no, journal tail")
        print("  send     three fail-closed gates (approval flag → "
              "conscience → allowlist), then SMTP transport")
        print("ALL sends refuse without the owner approval flag; an empty "
              "allowlist refuses every recipient.")
        return 0
    verb, rest = argv[0], argv[1:]

    def _opt(flag):
        if flag in rest:
            i = rest.index(flag)
            if i + 1 < len(rest):
                return rest[i + 1]
        return None

    if verb == "status":
        _print_json(status())
        return 0
    if verb == "send":
        to = _opt("--to")
        subject = _opt("--subject")
        body = _opt("--body")
        if not to or subject is None:
            print("usage: send --to A --subject S --body B [--source NAME]",
                  file=sys.stderr)
            return 2
        result = send(to, subject, body or "", source=_opt("--source") or "organism")
        _print_json(result)
        return 0 if result.get("sent") else 1
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
