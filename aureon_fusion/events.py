"""📡 Event Spine — the organism's shared nervous system.

Thin fusion layer over the workspace sero_thoughtbus (event envelopes) and
sero_chirp (high-urgency signals) substrates, both lazy-imported from the
workspace root via sys.path.

  publish_event(source, topic, payload, priority=5)  → ThoughtBus envelope
  chirp(source, signal_type, urgency, payload)       → ChirpBus signal
  publish(source, topic, payload, priority=5)        → alias of publish_event
                                                     (returns the envelope
                                                      dict; None on degrade)

Both degrade to silent no-ops if a substrate module fails to import or
publish — an organ that cannot speak must never die because of it.

CLI:
  python -m aureon_fusion.events tail [N]          last N bus events (default 20)
  python -m aureon_fusion.events tail --chirps [N] last N chirp signals

Import-safe: no side effects at import time.
"""

import json
import sys
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from .paths import WORKSPACE, SERO_THOUGHTBUS, SERO_CHIRP

BUS_LOG = SERO_THOUGHTBUS / "thought_bus.jsonl"
CHIRP_LOG = SERO_CHIRP / "chirp_log.jsonl"

_BUS = None
_CHIRP_BUS = None


def _bus():
    """Lazy ThoughtBus instance (module lives at the workspace root).

    Wires receipts.attach_to_envelope as the bus's pre_log_signer so the
    ed25519 receipt is attached BEFORE the envelope is appended to the log
    (sign-then-append; the logged record is verifiable via
    `python -m aureon_fusion.receipts verify <file>`). Signing stays gated
    on AUREON_FUSION_EVENT_SIGNING inside attach_to_envelope."""
    global _BUS
    if _BUS is None:
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        import sero_thoughtbus
        _BUS = sero_thoughtbus.ThoughtBus()
        try:
            from . import receipts as _receipts
            sero_thoughtbus.ThoughtBus.pre_log_signer = _receipts.attach_to_envelope
        except Exception:
            pass
    return _BUS


def _chirpbus():
    """Lazy ChirpBus instance (module lives at the workspace root)."""
    global _CHIRP_BUS
    if _CHIRP_BUS is None:
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        import sero_chirp
        _CHIRP_BUS = sero_chirp.ChirpBus()
    return _CHIRP_BUS


_PRIORITY_LABELS = ((8, "critical"), (6, "high"), (4, "normal"), (0, "low"))


def _priority_label(priority) -> str:
    """Map an integer priority (1-10) to the bus's string labels."""
    try:
        p = int(priority)
    except (TypeError, ValueError):
        return str(priority)
    for floor, label in _PRIORITY_LABELS:
        if p >= floor:
            return label
    return "normal"


def publish_event(source: str, topic: str, payload: dict, priority: int = 5):
    """Publish an event envelope to the ThoughtBus. Never raises.

    When AUREON_FUSION_EVENT_SIGNING=1 the envelope is additionally
    attested by the receipts organ (ed25519 signature + canonical
    receipt, attached in place). Signing failure degrades silently."""
    try:
        envelope = _bus().publish(source, topic, payload or {},
                                  priority=_priority_label(priority))
    except Exception:
        return None
    try:
        if envelope is not None:
            from . import receipts
            receipts.attach_to_envelope(envelope)
    except Exception:
        pass
    return envelope


def chirp(source: str, signal_type: str, urgency, payload: dict):
    """Emit a high-priority ChirpBus signal. Never raises."""
    try:
        return _chirpbus().chirp(source, signal_type, int(urgency), payload or {})
    except Exception:
        return None


def publish(source: str, topic: str, payload: dict, priority=5):
    """Backward-compatible alias of publish_event returning the envelope
    as a plain dict (or None on degrade)."""
    env = publish_event(source, topic, payload, priority=priority)
    if env is None:
        return None
    to_dict = getattr(env, "to_dict", None)
    return to_dict() if callable(to_dict) else env


def emit_radar_signal(source: str, topic: str, symbol: str, score: float,
                      extra: dict = None, priority: int = 5) -> dict:
    """Emit a radar event that includes the source_id and timestamp the
    flight recorder needs.

    Returns the envelope dict, or None if the bus is degraded.
    """
    payload = {
        "symbol": symbol,
        "score": float(score),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_id": f"{source}-{symbol}-{uuid.uuid4().hex[:8]}",
    }
    if extra:
        payload.update(extra)
    return publish(source, topic, payload, priority=priority)


# ───────────────────────────── tail CLI ────────────────────────────────────

def _tail_lines(path: Path, n: int):
    """Last n non-empty lines of a jsonl file (memory-bounded read)."""
    out = deque(maxlen=max(1, n))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(line)
    except OSError:
        pass
    return list(out)


def _fmt_bus(rec: dict) -> str:
    ts = str(rec.get("timestamp", "?"))[:19]
    payload = json.dumps(rec.get("payload"), ensure_ascii=False, default=str)
    return (f"[{ts}] {rec.get('source', '?'):<18} {rec.get('topic', '?'):<28} "
            f"({rec.get('priority', '?')}) {payload[:110]}")


def _fmt_chirp(rec: dict) -> str:
    ts = str(rec.get("timestamp", "?"))[:19]
    payload = json.dumps(rec.get("payload"), ensure_ascii=False, default=str)
    return (f"[{ts}] !{rec.get('urgency', '?')} {rec.get('source', '?'):<18} "
            f"{rec.get('signal_type', '?')} {payload[:110]}")


def _tail(argv) -> int:
    chirps = "--chirps" in argv
    argv = [a for a in argv if a != "--chirps"]
    n = 20
    if argv:
        try:
            n = max(1, int(argv[0]))
        except ValueError:
            print(f"usage: tail [N] [--chirps]  (N must be an integer, got '{argv[0]}')",
                  file=sys.stderr)
            return 2
    log = CHIRP_LOG if chirps else BUS_LOG
    title = "CHIRP SIGNALS" if chirps else "THOUGHTBUS EVENTS"
    print("=" * 100)
    print(f"EVENT TAIL -- {title} (last {n})  <- {log}")
    print("=" * 100)
    if not log.exists():
        print(f"  [no log yet: {log}]")
        return 0
    formatter = _fmt_chirp if chirps else _fmt_bus
    count = 0
    for line in _tail_lines(log, n):
        try:
            rec = json.loads(line)
        except Exception:
            continue
        print(formatter(rec))
        count += 1
    if not count:
        print("  [log is empty]")
    print("=" * 100)
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.events tail [N] [--chirps]")
        print("       tail          last N ThoughtBus events (default 20)")
        print("       tail --chirps last N ChirpBus signals")
        return 0
    if argv[0] == "tail":
        return _tail(argv[1:])
    print(f"unknown verb: {argv[0]} (expected tail)", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
