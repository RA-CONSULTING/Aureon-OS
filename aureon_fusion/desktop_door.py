"""Desktop door — Fusion-native, dry-run default.

Not a shell tool. Cortex must never register execute_shell.
Actions are cards: propose → conscience + gate → dry-run or armed write
inside an allowlisted jail. Destructive verbs are refused in code.

Import-safe.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import FUSION_STATE, WORKSPACE

RECEIPT_DIR = FUSION_STATE / "desktop"
JAIL_ROOTS = (
    WORKSPACE,
    FUSION_STATE,
    Path(__file__).resolve().parent / "knowledge",
)

ALLOWED_INTENTS = frozenset({"read_file", "list_dir", "write_file", "verify"})
FORBIDDEN_HINTS = (
    "rm -rf",
    "format ",
    "del /s",
    "execute_live_trades",
    "place_order",
    "wire ",
    "hmrc",
    "send email",
    "post tweet",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jail(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    for root in JAIL_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue
    raise PermissionError(f"path escapes desktop jail: {resolved}")


def _sha_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def propose(intent: str, args: dict) -> dict[str, Any]:
    card = {
        "id": hashlib.sha256(f"{intent}:{args}:{_utc()}".encode()).hexdigest()[:12],
        "intent": intent,
        "args": args or {},
        "mode": "dry_run",
        "ts": _utc(),
        "precondition": {},
        "expected": {},
        "observed": {},
        "verdict": "proposed",
        "veto": None,
    }
    return card


def _prefilter(intent: str, args: dict) -> str | None:
    blob = f"{intent} {json.dumps(args, default=str)}".lower()
    if intent not in ALLOWED_INTENTS:
        return f"intent not on allowlist: {intent}"
    for hint in FORBIDDEN_HINTS:
        if hint in blob:
            return f"forbidden pattern: {hint}"
    return None


def _observe_read(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    if path.is_dir():
        names = sorted(p.name for p in path.iterdir())[:80]
        return {"exists": True, "dir": True, "entries": names, "n": len(names)}
    data = path.read_text(encoding="utf-8", errors="replace")
    return {
        "exists": True,
        "dir": False,
        "bytes": path.stat().st_size,
        "sha256": _sha_file(path),
        "preview": data[:800],
    }


def execute(card: dict, *, armed: bool = False) -> dict:
    """Dry-run unless armed=True AND gate+conscience already passed by caller."""
    intent = card.get("intent")
    args = dict(card.get("args") or {})
    blocked = _prefilter(str(intent), args)
    if blocked:
        card["verdict"] = "vetoed"
        card["veto"] = blocked
        card["mode"] = "blocked"
        return card

    raw_path = args.get("path") or args.get("target")
    if not raw_path:
        card["verdict"] = "fail"
        card["veto"] = "missing path"
        return card

    try:
        target = _jail(Path(str(raw_path)))
    except PermissionError as exc:
        card["verdict"] = "vetoed"
        card["veto"] = str(exc)
        return card

    card["mode"] = "armed" if armed else "dry_run"
    card["precondition"] = {
        "path": str(target),
        "existed": target.exists(),
        "sha256": _sha_file(target) if target.is_file() else None,
    }

    if intent == "list_dir":
        path = target if target.is_dir() else target.parent
        card["observed"] = _observe_read(path)
        card["verdict"] = "pass"
        return _persist(card)

    if intent == "read_file":
        card["observed"] = _observe_read(target)
        card["verdict"] = "pass" if card["observed"].get("exists") else "fail"
        return _persist(card)

    if intent == "verify":
        card["observed"] = _observe_read(target)
        expect = args.get("sha256")
        if expect and card["observed"].get("sha256") != expect:
            card["verdict"] = "fail"
        else:
            card["verdict"] = "pass"
        return _persist(card)

    if intent == "write_file":
        content = str(args.get("content", ""))
        card["expected"] = {"exists": True, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
        if not armed:
            card["observed"] = {
                "would_write": str(target),
                "bytes": len(content.encode("utf-8")),
                "host_mutated": False,
            }
            card["verdict"] = "pass"
            return _persist(card)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".fusion-tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(target)
        card["observed"] = _observe_read(target)
        card["verdict"] = "pass" if card["observed"].get("sha256") == card["expected"]["sha256"] else "fail"
        return _persist(card)

    card["verdict"] = "fail"
    card["veto"] = "unhandled intent"
    return _persist(card)


def _persist(card: dict) -> dict:
    try:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        path = RECEIPT_DIR / f"{card.get('id', 'card')}.json"
        path.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
        card["receipt"] = str(path)
    except Exception:
        pass
    try:
        from . import events

        events.publish_event(
            "desktop_door",
            "desktop.card",
            {
                "id": card.get("id"),
                "intent": card.get("intent"),
                "mode": card.get("mode"),
                "verdict": card.get("verdict"),
            },
            priority=5 if card.get("verdict") == "pass" else 7,
        )
    except Exception:
        pass
    return card


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.desktop_door propose|dry-write|read <path> [content]")
        print("  propose <intent> <path>")
        print("  read <path>")
        print("  dry-write <path> <text>     host bytes unchanged")
        return 0
    verb = argv[0]
    if verb == "read" and len(argv) >= 2:
        card = propose("read_file", {"path": argv[1]})
        print(json.dumps(execute(card, armed=False), indent=2, ensure_ascii=False))
        return 0
    if verb == "dry-write" and len(argv) >= 3:
        card = propose("write_file", {"path": argv[1], "content": " ".join(argv[2:])})
        print(json.dumps(execute(card, armed=False), indent=2, ensure_ascii=False))
        return 0
    if verb == "propose" and len(argv) >= 3:
        print(json.dumps(propose(argv[1], {"path": argv[2]}), indent=2, ensure_ascii=False))
        return 0
    print("bad args", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
