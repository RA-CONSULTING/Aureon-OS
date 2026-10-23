"""📤 OUTBOUND MESSAGING — the organism's outbound rail (SMTP email + webhook).

Owner decree (absolute):
  • Conscience VETO is absolute. Never weaken a gate; honest failure is
    always acceptable, fake success never is.
  • She is sovereign: this module BUILDS the rail and keeps the switch OFF.
    The first live send requires the owner's explicit decree (see below) and
    still passes the full gate trio at send time.
  • FAIL-CLOSED everywhere: no approval flag → no send path, ever. An
    unreadable conscience is a conscience that said no. A missing/unreadable
    HNC state is incoherence. No exceptions escape as consent.

THE LIVE-SEND SWITCH (owner decree required to energize):
  1. Gary writes the exact line
        OUTBOUND_AUTHORIZED_BY_GARY
     to aureon_fusion/state/outbound_approval.flag
  2. Gary re-vouches the 'outbound_messaging' census door in person so its
     locked_reason is cleared and she can mint a key (master_key gate trio
     still applies at mint/open).
  Until BOTH hold, every send_* call refuses honestly ('not_approved').

THE GATE TRIO — checked on EVERY send (including dry-run):
  1. CONSCIENCE   (conscience_hook.evaluate — VETO absolute; any internal
                   error degrades to a block)
  2. HNC COHERENCE (coherence_gamma ≥ 0.25 from state/hnc_core_state.json —
                    below/absent → held_incoherent, never fabricated)
  3. AUTHORIZATION (capability_gate.check('external_communication:send_messages')
                    — matrix row is ELEVATE; a refusal blocks)

CREDENTIALS:
  • Never hardcoded, never logged. Read at SEND TIME only from the .env-style
    file aureon_fusion/state/outbound_messaging.env (KEY=VALUE lines).
  • Recognized keys: OUTBOUND_SMTP_HOST / _PORT / _USER / _PASSWORD /
    _FROM / _TLS, OUTBOUND_WEBHOOK_URL / _TOKEN. Secret-shaped values are
    redacted from every record this module writes.
  • The ledger (state/outbound/ledger.jsonl) records metadata only:
    channel, recipients, subject, gate verdicts, result. Never bodies,
    never credentials.

Import-safe: nothing sends at import. Suppression env vars honored via
setdefault. All writes tmp+replace or locked JSONL appends.

CLI:
    python -m aureon_fusion.outbound_messaging status
    python -m aureon_fusion.outbound_messaging send-email --to a@b.c \
        --subject "..." [--body-file draft.txt] [--dry]
    python -m aureon_fusion.outbound_messaging send-webhook [--url URL] \
        [--payload-file p.json] [--dry]
"""

import json
import os
import smtplib
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from .paths import FUSION_STATE
from . import events

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
os.environ.setdefault("AUREON_AUDIT_MODE", "1")

# ───────────────────────── doctrine constants ──────────────────────────────

APPROVAL_FLAG = FUSION_STATE / "outbound_approval.flag"
APPROVAL_LINE = "OUTBOUND_AUTHORIZED_BY_GARY"
CONFIG_FILE = FUSION_STATE / "outbound_messaging.env"
LEDGER_FILE = FUSION_STATE / "outbound" / "ledger.jsonl"
HNC_STATE_FILE = FUSION_STATE / "hnc_core_state.json"
DOMAIN_ACTION = "external_communication:send_messages"
COHERENCE_THRESHOLD = 0.25
NETWORK_TIMEOUT_S = 30

_SECRET_MARKERS = ("password", "secret", "token", "api_key", "apikey", "credential")

# ───────────────────────── small utilities ─────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _append_line(path: Path, line: str) -> None:
    """Locked JSONL append via the door-registry helper (sidecar lock,
    per-pid sidecar fallback — inter-process safe on Windows)."""
    try:
        from .door_registry import _append_line as _door_append
        _door_append(path, line)
    except Exception:
        # Never lose the record, never raise across a gate.
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path.with_name(f"{path.name}.pid{os.getpid()}"),
                      "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass


def _redact(obj):
    """Recursively mask secret-shaped values. Key names are preserved so a
    record can honestly say WHICH config was present without ever carrying
    the secret itself."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(m in str(k).lower() for m in _SECRET_MARKERS):
                out[k] = ("<redacted:%d chars>" % len(str(v))) if v else None
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_redact(v) for v in obj]
    return obj


def _record(entry: dict) -> None:
    """Append a redacted metadata record to the outbound ledger. Never
    raises; bodies and credentials never reach the ledger."""
    try:
        safe = _redact(entry)
        safe.pop("body", None)
        safe.pop("payload", None)
        _append_line(LEDGER_FILE, json.dumps(safe, ensure_ascii=False,
                                             default=str))
    except Exception:
        pass


def _publish(topic: str, payload: dict, priority: int = 5) -> None:
    try:
        events.publish_event("outbound_messaging", topic,
                             _redact(payload), priority=priority)
    except Exception:
        pass


# ───────────────────────── approval & config ───────────────────────────────

def approval_status() -> dict:
    """Honest state of the live-send switch. Reads the flag file only —
    never the config secrets."""
    authorized = False
    try:
        if APPROVAL_FLAG.exists():
            with open(APPROVAL_FLAG, "r", encoding="utf-8") as f:
                authorized = APPROVAL_LINE in [
                    line.strip() for line in f.read().splitlines()]
    except Exception:
        authorized = False
    return {"flag_file": str(APPROVAL_FLAG), "flag_present": APPROVAL_FLAG.exists(),
            "authorized": authorized}


def _load_config() -> dict:
    """Parse the .env-style config file. Called at SEND TIME only. Returns
    {} when absent/unreadable — a missing config is a block, never a crash."""
    cfg = {}
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    cfg[key.strip()] = value.strip().strip('"').strip("'")
    except Exception:
        return {}
    return cfg


def _config_profile(cfg: dict) -> dict:
    """Names-only profile of the config: which keys are present, never what
    they contain (secret-shaped values are length-masked)."""
    return {"config_file": str(CONFIG_FILE),
            "config_present": bool(cfg),
            "keys": sorted(cfg.keys()),
            "private_keys_present": sorted(
                k for k in cfg if any(m in k.lower() for m in _SECRET_MARKERS)
                and cfg[k])}


# ───────────────────────── the gate trio ───────────────────────────────────

def coherence_gamma():
    """Γ from the live HNC state, or None when unreadable (fail-closed)."""
    data = _read_json(HNC_STATE_FILE, None)
    if isinstance(data, dict):
        gamma = data.get("coherence_gamma")
        if isinstance(gamma, (int, float)):
            return float(gamma)
    return None


def _conscience_check(action_desc: str, context: dict) -> dict:
    """Conscience gate. VETO blocks; an internal error degrades to a block
    (an unreadable conscience is a conscience that said no)."""
    try:
        from . import conscience_hook
        verdict = conscience_hook.evaluate(action_desc, context or {})
        return {"ok": verdict.get("verdict") != "VETO",
                "verdict": verdict.get("verdict"),
                "reasoning": (verdict.get("reasoning") or "")[:300]}
    except Exception as exc:
        return {"ok": False, "verdict": "UNREADABLE",
                "reasoning": f"conscience error ({type(exc).__name__}) — "
                             f"fail-closed block"}


def _capability_check() -> dict:
    try:
        from . import capability_gate
        verdict = capability_gate.check(DOMAIN_ACTION)
        return {"ok": bool(verdict.get("allowed")),
                "verdict": verdict.get("verdict"),
                "level": verdict.get("level"),
                "reason": (verdict.get("reason") or "")[:300]}
    except Exception as exc:
        return {"ok": False, "verdict": "ERROR",
                "reason": f"capability gate error ({type(exc).__name__}) — "
                          f"fail-closed block"}


def run_gate_trio(action_desc: str, context: dict | None = None) -> dict:
    """All three gates, evaluated honestly, in decree order. 'ok' is True
    only when every gate passes. Never raises."""
    conscience = _conscience_check(action_desc, context or {})
    gamma = coherence_gamma()
    coherence = {"ok": gamma is not None and gamma >= COHERENCE_THRESHOLD,
                 "gamma": gamma, "threshold": COHERENCE_THRESHOLD}
    capability = _capability_check()
    ok = bool(conscience["ok"] and coherence["ok"] and capability["ok"])
    return {"ok": ok, "conscience": conscience, "coherence": coherence,
            "capability": capability}


# ───────────────────────── send paths (fail-closed) ────────────────────────

def _preflight(channel: str, action_desc: str, context: dict,
               dry_run: bool) -> dict:
    """Common fail-closed ladder: approval flag → gate trio → config.
    Returns {'ok': True, 'config': cfg} or a blocked result. Never raises."""
    approval = approval_status()
    if not approval["authorized"]:
        result = {"ok": False, "blocked_by": "not_approved", "channel": channel,
                  "dry_run": dry_run, "approval": approval,
                  "detail": (f"live send is not approved — the exact line "
                             f"'{APPROVAL_LINE}' must be written to "
                             f"{APPROVAL_FLAG} by the owner. Rail built, "
                             f"switch off.")}
        _record({**result, "ts": _utc_now()})
        _publish("outbound.blocked", result, priority=6)
        return result
    trio = run_gate_trio(action_desc, context)
    if not trio["ok"]:
        result = {"ok": False, "blocked_by": "gate_trio", "channel": channel,
                  "dry_run": dry_run, "approval": approval, "trio": trio,
                  "detail": "gate trio refused: " + "; ".join(
                      g for g in ("conscience", "coherence", "capability")
                      if not trio[g]["ok"])}
        _record({**result, "ts": _utc_now()})
        _publish("outbound.blocked", result, priority=7)
        return result
    cfg = _load_config()
    return {"ok": True, "channel": channel, "dry_run": dry_run,
            "approval": approval, "trio": trio, "config": cfg}


def send_email(to: str, subject: str, body: str, dry_run: bool = False,
               context: dict | None = None) -> dict:
    """SMTP email behind approval flag + gate trio. dry_run=True runs every
    gate and the config check with zero network. Never raises."""
    desc = f"send outbound email to <{to}> subject '{subject[:80]}'"
    pre = _preflight("email", desc, context or {"to": to}, dry_run)
    if not pre["ok"]:
        return pre
    cfg = pre["config"]
    host = cfg.get("OUTBOUND_SMTP_HOST")
    from_addr = cfg.get("OUTBOUND_SMTP_FROM")
    if not host or not from_addr:
        return {"ok": False, "blocked_by": "config_incomplete",
                "channel": "email", "dry_run": dry_run,
                "detail": ("OUTBOUND_SMTP_HOST and OUTBOUND_SMTP_FROM are "
                           "required in " + str(CONFIG_FILE)),
                "config": _config_profile(cfg)}
    port = int(cfg.get("OUTBOUND_SMTP_PORT", "587"))
    use_tls = cfg.get("OUTBOUND_TLS", "1") != "0" and port != 465
    if dry_run:
        result = {"ok": True, "channel": "email", "dry_run": True,
                  "would_send": True, "to": to, "subject": subject,
                  "config": _config_profile(cfg),
                  "detail": "dry-run: all gates passed; no network touched"}
        _record({**result, "ts": _utc_now(), "trio_ok": pre["trio"]["ok"]})
        return result
    try:
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=NETWORK_TIMEOUT_S,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=NETWORK_TIMEOUT_S)
        try:
            if use_tls:
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
        result = {"ok": True, "channel": "email", "dry_run": False,
                  "to": to, "subject": subject,
                  "config": _config_profile(cfg),
                  "detail": "sent via SMTP (credentials never logged)"}
        _record({**result, "ts": _utc_now(), "trio_ok": pre["trio"]["ok"]})
        _publish("outbound.sent", result, priority=6)
        return result
    except Exception as exc:
        result = {"ok": False, "channel": "email", "dry_run": False,
                  "to": to, "subject": subject,
                  "detail": f"smtp error: {type(exc).__name__}: "
                            f"{str(exc)[:200]}"}
        _record({**result, "ts": _utc_now()})
        _publish("outbound.failed", result, priority=6)
        return result


def post_webhook(payload: dict, url: str | None = None,
                 dry_run: bool = False, context: dict | None = None) -> dict:
    """Generic JSON webhook post behind approval flag + gate trio. URL comes
    from the argument or OUTBOUND_WEBHOOK_URL config (config at send time).
    dry_run=True runs every gate with zero network. Never raises."""
    desc = "post outbound webhook payload (%d bytes)" % len(
        json.dumps(payload, default=str))
    pre = _preflight("webhook", desc, context or {}, dry_run)
    if not pre["ok"]:
        return pre
    cfg = pre["config"]
    target = url or cfg.get("OUTBOUND_WEBHOOK_URL")
    if not target or not target.startswith(("https://", "http://")):
        return {"ok": False, "blocked_by": "config_incomplete",
                "channel": "webhook", "dry_run": dry_run,
                "detail": ("a webhook URL (--url or OUTBOUND_WEBHOOK_URL, "
                           "http/https only) is required"),
                "config": _config_profile(cfg)}
    token = cfg.get("OUTBOUND_WEBHOOK_TOKEN")
    if dry_run:
        result = {"ok": True, "channel": "webhook", "dry_run": True,
                  "would_send": True, "url_host": target.split("/")[2],
                  "config": _config_profile(cfg),
                  "detail": "dry-run: all gates passed; no network touched"}
        _record({**result, "ts": _utc_now(), "trio_ok": pre["trio"]["ok"]})
        return result
    try:
        data = json.dumps(payload, default=str).encode("utf-8")
        req = urllib.request.Request(
            target, data=data, method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": "aureon-outbound/1.0"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_S) as resp:
            status = resp.status
        result = {"ok": 200 <= status < 300, "channel": "webhook",
                  "dry_run": False, "url_host": target.split("/")[2],
                  "http_status": status,
                  "config": _config_profile(cfg),
                  "detail": f"webhook POST returned HTTP {status}"}
        _record({**result, "ts": _utc_now(), "trio_ok": pre["trio"]["ok"]})
        _publish("outbound.sent" if result["ok"] else "outbound.failed",
                 result, priority=6)
        return result
    except Exception as exc:
        result = {"ok": False, "channel": "webhook", "dry_run": False,
                  "url_host": target.split("/")[2],
                  "detail": f"webhook error: {type(exc).__name__}: "
                            f"{str(exc)[:200]}"}
        _record({**result, "ts": _utc_now()})
        _publish("outbound.failed", result, priority=6)
        return result


# ───────────────────────── readiness (door mechanics) ──────────────────────

def readiness() -> dict:
    """What the door activator reports: the rail's honest standing. Never
    sends; never reads secret values (names + length masks only)."""
    approval = approval_status()
    cfg = _config_profile(_load_config())
    gamma = coherence_gamma()
    return {"module": "aureon_fusion.outbound_messaging",
            "approval": approval, "config": cfg,
            "gamma": gamma, "gamma_threshold": COHERENCE_THRESHOLD,
            "domain_action": DOMAIN_ACTION,
            "armed": bool(approval["authorized"]),
            "detail": ("rail built, switch OFF — owner decree required: "
                       f"write '{APPROVAL_LINE}' to {APPROVAL_FLAG} and "
                       "re-vouch the outbound_messaging door")}


# ───────────────────────── CLI ─────────────────────────────────────────────

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
        print("usage: python -m aureon_fusion.outbound_messaging "
              "status|send-email|send-webhook|readiness")
        print("  status      approval flag, config profile (names only), Γ, "
              "capability verdict — no secrets")
        print("  readiness   the door-activator view of the rail")
        print("  send-email --to A --subject S [--body-file F] [--body B] "
              "[--dry]")
        print("  send-webhook [--url U] [--payload-file F] [--dry]")
        print("ALL sends are fail-closed without the owner approval flag; "
              "--dry runs the full gate trio with zero network.")
        return 0
    verb, rest = argv[0], argv[1:]
    dry = "--dry" in rest
    rest = [a for a in rest if a != "--dry"]

    def _opt(flag):
        if flag in rest:
            i = rest.index(flag)
            if i + 1 < len(rest):
                return rest[i + 1]
        return None

    if verb == "status":
        from . import capability_gate
        cap = capability_gate.check(DOMAIN_ACTION)
        _print_json({"approval": approval_status(),
                     "config": _config_profile(_load_config()),
                     "coherence_gamma": coherence_gamma(),
                     "capability": {"verdict": cap.get("verdict"),
                                    "allowed": cap.get("allowed"),
                                    "level": cap.get("level"),
                                    "domain_action": DOMAIN_ACTION},
                     "ledger": str(LEDGER_FILE)})
        return 0
    if verb == "readiness":
        _print_json(readiness())
        return 0
    if verb == "send-email":
        to = _opt("--to")
        subject = _opt("--subject")
        if not to or not subject:
            print("usage: send-email --to A --subject S [--body-file F] "
                  "[--body B] [--dry]", file=sys.stderr)
            return 2
        body = _opt("--body") or ""
        body_file = _opt("--body-file")
        if body_file:
            try:
                body = Path(body_file).read_text(encoding="utf-8")
            except Exception as exc:
                print(f"cannot read body file: {type(exc).__name__}",
                      file=sys.stderr)
                return 2
        result = send_email(to, subject, body, dry_run=dry)
        _print_json(_redact(result))
        return 0 if result.get("ok") else 1
    if verb == "send-webhook":
        payload = {}
        payload_file = _opt("--payload-file")
        if payload_file:
            try:
                payload = json.loads(Path(payload_file).read_text(
                    encoding="utf-8"))
            except Exception as exc:
                print(f"cannot read payload file: {type(exc).__name__}",
                      file=sys.stderr)
                return 2
        result = post_webhook(payload, url=_opt("--url"), dry_run=dry)
        _print_json(_redact(result))
        return 0 if result.get("ok") else 1
    print(f"unknown verb: {verb}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
