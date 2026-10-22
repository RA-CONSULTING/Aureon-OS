"""📊 Fusion Status — one-screen dashboard of the fused runtime.

Sections: organ registry liveness, capability gate summary (incl. the
capital pin), conscience tally, last heartbeat checks, and field state
(latest Schumann reading). Read-only and fast: no network, no process
spawns. Import-safe.
"""

import json
import sys
import time
from pathlib import Path

from .paths import WORKSPACE, HEARTBEAT_STATE
from .organ_registry import status_data as organ_status
from .capability_gate import status as gate_status
from .conscience_hook import tally as conscience_tally
from .heartbeat_exec import mind_snapshot


def _read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _age_str(epoch) -> str:
    if not epoch:
        return "never"
    delta = time.time() - float(epoch)
    if delta < 90:
        return f"{int(delta)}s ago"
    if delta < 5400:
        return f"{int(delta // 60)}m ago"
    return f"{delta / 3600:.1f}h ago"


def dashboard() -> str:
    W = 78
    lines = []
    lines.append("╔" + "═" * W + "╗")
    lines.append("║" + "📊 AUREON FUSION — RUNTIME STATUS".center(W) + "║")
    lines.append("╚" + "═" * W + "╝")

    # ── Organs ──
    lines.append("")
    lines.append("── 🫀 ORGANS ──")
    for name, info in organ_status().items():
        icon = "🟢" if info["state"] == "running" else "⚪"
        lines.append(f"  {icon} {name:<26} {info['state']:<8} "
                     f"pid={info['pid'] or '-':<7} mode={info['mode']}")

    # ── Capability gate ──
    gs = gate_status()
    lines.append("")
    lines.append("── 🚦 CAPABILITY GATE ──")
    lines.append(f"  gates: {gs['gates_total']} "
                 f"({', '.join(f'{k}={v}' for k, v in sorted(gs['by_status'].items()))})")
    pin = gs["capital_pin"]
    pin_icon = "🔒" if pin["effective_verdict"] == "HOLD" else "🔓"
    lines.append(f"  {pin_icon} capital pin: {pin['gate']} → {pin['effective_verdict']} "
                 f"(matrix={pin['matrix_status']}, release_authorized={pin['release_authorized']})")

    # ── Conscience ──
    t = conscience_tally()
    lines.append("")
    lines.append("── ⚖️  CONSCIENCE ──")
    lines.append(f"  checks={t.get('total_checks', 0)} approved={t.get('approved_count', 0)} "
                 f"concerned={t.get('concerned_count', 0)} vetoes={t.get('veto_count', 0)} "
                 f"teaching={t.get('teaching_count', 0)} overrides={t.get('override_attempts', 0)}")
    if t.get("last_veto_reason"):
        lines.append(f"  last veto: {str(t['last_veto_reason'])[:60]}")

    # ── Heartbeat ──
    hb = _read_json(HEARTBEAT_STATE, {}).get("lastChecks", {})
    lines.append("")
    lines.append("── 💓 LAST HEARTBEAT CHECKS ──")
    if hb:
        for name, epoch in sorted(hb.items(), key=lambda kv: -(kv[1] or 0)):
            lines.append(f"  {name:<22} {_age_str(epoch)}")
    else:
        lines.append("  [none yet — run python -m aureon_fusion.heartbeat_exec run]")

    # ── Field state ──
    field = _read_json(WORKSPACE / "schumann_state.json", {})
    lines.append("")
    lines.append("── 🌍 FIELD STATE (latest Schumann reading) ──")
    if field:
        lines.append(f"  {field.get('frequency_hz', '?')} Hz | activity {field.get('activity_index', '?')} "
                     f"({field.get('activity_label', '?')}) | Kp {field.get('kp_index', '?')} | "
                     f"flare {field.get('solar_flare_class', '?')} | geo {field.get('geomagnetic_status', '?')}")
        lines.append(f"  measured: {field.get('timestamp', '?')[:19]}  source: {field.get('source', '?')}")
        summary = (field.get("summary") or "").strip()
        if summary:
            lines.append(f"  summary : {summary[:W - 12]}")
    else:
        lines.append("  [no schumann_state.json found]")

    # ── Mind ──
    lines.append("")
    lines.append("── 👑 MIND ──")
    try:
        from .heartbeat_exec import _queen_mind_indexes
        snap = mind_snapshot()
        state = snap.get("state") or {}
        mp = snap.get("model_plane") or {}
        organ = snap.get("organ") or {}
        report = state.get("last_report") or {}
        ci, mi = _queen_mind_indexes(state)
        if ci is None and mi is None:
            lines.append("  consciousness/metacognition index: pending first cycle")
        else:
            ci_s = f"{ci}" if ci is not None else "?"
            mi_s = f"{mi}" if mi is not None else "?"
            lines.append(f"  consciousness index: {ci_s} | metacognition index: {mi_s}")
        tick = state.get("last_tick") or {}
        verdict = tick.get("action") or report.get("action")
        cycle = tick.get("cycle") or report.get("cycle")
        if verdict:
            vline = f"  last metacognitive verdict: {str(verdict)[:40]}"
            if cycle:
                vline += f" (cycle {cycle}"
                if report.get("persona"):
                    vline += f", persona {report['persona']}"
                vline += ")"
            lines.append(vline)
        lines.append("  reasoning: NATIVE (repo logic: hnc+auris+qgita+knowledge, no model plane)")
        ev = snap.get("queen_mind_event") or {}
        if ev.get("found") and ev.get("age_s") is not None:
            lines.append(f"  last queen.mind event: {_age_str(time.time() - ev['age_s'])}")
        else:
            lines.append("  last queen.mind event: none on the bus yet")
        ostate = organ.get("state")
        if ostate:
            oline = f"  organ queen_mind: {ostate}"
            if organ.get("pid"):
                oline += f" pid={organ['pid']}"
            if ostate == "dormant" and organ.get("dormant_reason"):
                oline += f" — {organ['dormant_reason']}"
            lines.append(oline)
        personas = snap.get("personas") or []
        if personas:
            roster = "; ".join(personas)
            lines.append(f"  personas: {roster[:W + 40]}")
        else:
            lines.append("  personas: [aureon_fusion/personas.json not present yet]")
    except Exception as e:
        lines.append(f"  ! mind block unavailable: {e}")

    lines.append("")
    lines.append("═" * (W + 2))
    return "\n".join(lines)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help", "help"):
        print("usage: python -m aureon_fusion.fusion_status")
        return 0
    print(dashboard())
    return 0


if __name__ == "__main__":
    sys.exit(main())
