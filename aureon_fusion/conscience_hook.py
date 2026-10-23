"""⚖️ Conscience Hook — the fused runtime's 4th-pass veto.

Wraps sero_conscience_engine (lazy import from the workspace root) behind a
thin, import-safe API: evaluate(action_desc, context) -> dict verdict.

The engine module carries a hardcoded Linux-era path (/root/.openclaw/...)
for its own logs/state. This hook is the workspace-side authority: it
persists every verdict to the workspace sero_conscience/ logs
(decision_log.jsonl / veto_log.jsonl) and maintains the workspace
conscience_state.json tally, which is what awakening.py and
fusion_status.py report.

Import-safe: the engine is only imported inside functions.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .paths import WORKSPACE, SERO_CONSCIENCE
from . import events

DECISION_LOG = SERO_CONSCIENCE / "decision_log.jsonl"
VETO_LOG = SERO_CONSCIENCE / "veto_log.jsonl"
CONSCIENCE_STATE = SERO_CONSCIENCE / "conscience_state.json"

_ENGINE = None


def _load_engine():
    """Lazy-import sero_conscience_engine from the workspace root."""
    global _ENGINE
    if _ENGINE is None:
        if str(WORKSPACE) not in sys.path:
            sys.path.insert(0, str(WORKSPACE))
        import sero_conscience_engine as engine
        _ENGINE = engine
    return _ENGINE


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


_TALLY_KEYS = (
    "total_checks", "approved_count", "concerned_count", "veto_count",
    "teaching_count", "override_attempts",
    "last_veto_timestamp", "last_veto_reason",
)


def _default_state():
    """Schema-compatible with sero_conscience_engine.ConscienceState."""
    return {
        "total_checks": 0,
        "approved_count": 0,
        "concerned_count": 0,
        "veto_count": 0,
        "teaching_count": 0,
        "override_attempts": 0,
        "last_veto_timestamp": None,
        "last_veto_reason": None,
        "sls_history": [],
        "trust_in_self": 0.80,
    }


def tally() -> dict:
    """Workspace-side conscience tally (no engine import needed)."""
    state = _read_json(CONSCIENCE_STATE, {})
    return {k: state.get(k) for k in _TALLY_KEYS}


def _engine_logs_to_workspace(engine) -> bool:
    """True if the engine's own log dir already resolves inside the workspace
    (engine workstream rewired its paths) — then we must not double-log."""
    try:
        engine_dir = Path(engine.CONSCIENCE_DIR).resolve()
        return str(engine_dir).startswith(str(WORKSPACE.resolve()))
    except Exception:
        return False


def _persist_verdict(verdict: dict, engine=None):
    """Persist the verdict: logs (unless the engine already logs to the
    workspace) plus the workspace conscience_state.json tally, preserving
    the engine's exact state schema."""
    SERO_CONSCIENCE.mkdir(parents=True, exist_ok=True)
    if engine is None or not _engine_logs_to_workspace(engine):
        line = json.dumps(verdict, ensure_ascii=False)
        with open(DECISION_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        if verdict.get("verdict") == "VETO":
            with open(VETO_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    state = _read_json(CONSCIENCE_STATE, {})
    merged = _default_state()
    merged.update({k: v for k, v in state.items() if k in merged})
    merged["total_checks"] += 1
    v = verdict.get("verdict")
    if v == "APPROVED":
        merged["approved_count"] += 1
    elif v == "CONCERNED":
        merged["concerned_count"] += 1
    elif v == "VETO":
        merged["veto_count"] += 1
        merged["last_veto_timestamp"] = verdict.get("timestamp")
        merged["last_veto_reason"] = verdict.get("reasoning")
    elif v == "TEACHING_MOMENT":
        merged["teaching_count"] += 1
    if verdict.get("override_attempted"):
        merged["override_attempts"] += 1
    history = list(merged.get("sls_history") or [])
    history.append([verdict.get("timestamp"), verdict.get("sls_score", 0.5)])
    merged["sls_history"] = history[-100:]
    with open(CONSCIENCE_STATE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)


def evaluate(action_desc: str, context: dict = None) -> dict:
    """Run the conscience gate on a proposed action.

    Returns a dict: verdict, reasoning, conditions, scores, timestamp.
    The verdict is persisted to the workspace sero_conscience/ logs.
    """
    engine = _load_engine()
    conscience = engine.ConscienceEngine()
    check = conscience.evaluate(action_desc, context or {})
    verdict = check.to_dict()
    _persist_verdict(verdict, engine)
    events.publish_event(
        "conscience_hook", "conscience.verdict",
        {"verdict": verdict.get("verdict"),
         "action": (verdict.get("action_description") or "")[:120],
         "sls_score": verdict.get("sls_score"),
         "override_attempted": bool(verdict.get("override_attempted"))},
        priority=7 if verdict.get("verdict") == "VETO" else 5,
    )
    return verdict


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.conscience_hook [--action] \"describe the proposed action\"")
        print("       prints the conscience verdict (APPROVED | CONCERNED | VETO | TEACHING_MOMENT)")
        return 0
    # Accept both `--action <text>` (documented form) and a bare positional string.
    if argv[0] in ("--action", "-a"):
        argv = argv[1:]
    action = " ".join(argv)
    verdict = evaluate(action)
    print("=" * 72)
    print("⚖️  CONSCIENCE VERDICT")
    print("=" * 72)
    print(f"  Action    : {verdict['action_description']}")
    print(f"  Verdict   : {verdict['verdict']}")
    print(f"  Reasoning : {verdict['reasoning']}")
    if verdict.get("conditions"):
        print(f"  Conditions: {' | '.join(verdict['conditions'])}")
    print(f"  Purpose   : {verdict['purpose_alignment']:.3f}  "
          f"Risk: {verdict['risk_score']:.3f}  SLS: {verdict['sls_score']:.3f}")
    print(f"  Logged to : {DECISION_LOG}")
    print("=" * 72)
    return 0 if verdict["verdict"] in ("APPROVED", "CONCERNED", "TEACHING_MOMENT") else 1


if __name__ == "__main__":
    sys.exit(main())
