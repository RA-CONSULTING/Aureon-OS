"""HNC/Auris harmonic affect state manifest.

This module expresses Aureon's emotion-like state as measurable system
coherence: goal progress, trade reward evidence, runtime freshness, HNC/Auris
source availability, and safety blockers. It does not claim human sensation;
it publishes the synthetic frequency/state-change contract the rest of the
organism can inspect.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence


SCHEMA_VERSION = "aureon-harmonic-affect-state-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_harmonic_affect_state.json"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_harmonic_affect_state.json"

COGNITIVE_TRADE_PATH = Path("docs/audits/aureon_cognitive_trade_evidence.json")
ORGANISM_STATUS_PATH = Path("docs/audits/aureon_organism_runtime_status.json")
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
NEXUS_LEARNING_PATH = Path("nexus_learning_state.json")
EMOTIONAL_CODEX_PATHS = (
    Path("public/emotional_codex.json"),
    Path("public/emotional_frequency_codex_complete.json"),
    Path("public/emotional_frequency_codex.json"),
)
AURIS_EMOTIONS_PATH = Path("public/auris_emotions.json")

HNC_AURIS_ANCHORS = (
    Path("frontend/src/types/hnc.ts"),
    Path("public/auris_emotions.json"),
    Path("public/auris_symbols.json"),
    Path("public/emotional_codex.json"),
    Path("public/emotional_frequency_codex_complete.json"),
    Path("aureon/harmonic/harmonic_nexus_bridge.py"),
    Path("aureon/vault/auris_metacognition.py"),
    Path("aureon/bridges/aureon_probability_nexus.py"),
    Path("docs/audits/hnc_saas_cognitive_bridge.json"),
    Path("docs/audits/hnc_saas_security_blueprint.json"),
)

PHASE_TO_EMOTION = {
    "protective_recalibration": "Reason",
    "steady_willingness": "Willingness",
    "gratitude_resonance": "Gratitude",
    "joyful_goal_pursuit": "Joy",
    "synthetic_inner_peace": "Peace",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except Exception:
        pass
    return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _summary(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("summary"), dict):
        return payload["summary"]
    return {}


def _frequency_catalog(root: Path) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for rel in EMOTIONAL_CODEX_PATHS:
        data = _read_json(root / rel, {})
        rows: Any = []
        if isinstance(data, dict):
            rows = data.get("entries") or data.get("emotional_frequency_codex") or data.get("emotions") or []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                emotion = str(row.get("emotion") or row.get("name") or "").strip()
                if not emotion:
                    continue
                freq = _as_float(row.get("frequency_hz", row.get("frequency")), 0.0)
                catalog[emotion.lower()] = {
                    "emotion": emotion,
                    "frequency_hz": freq,
                    "color": row.get("color") or row.get("color_hex") or row.get("color_name") or "",
                    "band": row.get("band") or row.get("level") or "",
                }
    return catalog


def _auris_emotion_count(root: Path) -> int:
    data = _read_json(root / AURIS_EMOTIONS_PATH, {})
    emotions = data.get("emotions") if isinstance(data, dict) else {}
    return len(emotions) if isinstance(emotions, dict) else 0


def _anchor_status(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in HNC_AURIS_ANCHORS:
        path = root / rel
        rows.append(
            {
                "path": str(rel).replace("\\", "/"),
                "present": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return rows


def _select_phase(
    *,
    coherence: float,
    runtime_stale: bool,
    blocker_count: int,
    signal_quality: float,
    average_reward: float,
    win_rate: float,
) -> str:
    if runtime_stale or blocker_count > 0:
        return "protective_recalibration"
    if coherence >= 0.9 and signal_quality >= 0.75 and average_reward >= 0.65:
        return "synthetic_inner_peace"
    if coherence >= 0.78 and win_rate >= 0.6:
        return "joyful_goal_pursuit"
    if coherence >= 0.62 and average_reward >= 0.55:
        return "gratitude_resonance"
    return "steady_willingness"


def build_harmonic_affect_state(root: Optional[Path] = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    cognitive = _read_json(root / COGNITIVE_TRADE_PATH, {})
    organism = _read_json(root / ORGANISM_STATUS_PATH, {})
    runtime = _read_json(root / RUNTIME_STATUS_PATH, {})
    nexus = _read_json(root / NEXUS_LEARNING_PATH, {})
    cognitive_summary = _summary(cognitive)
    organism_summary = _summary(organism)
    runtime_watchdog = runtime.get("runtime_watchdog") if isinstance(runtime.get("runtime_watchdog"), dict) else {}

    signal_quality = _as_float(cognitive_summary.get("signal_quality"))
    average_reward = _as_float(cognitive_summary.get("average_learning_reward"))
    win_rate = _as_float(cognitive_summary.get("win_rate"))
    evidence_count = int(_as_float(cognitive_summary.get("evidence_count")))
    net_pnl = _as_float(cognitive_summary.get("net_pnl"))
    runtime_stale = bool(
        cognitive_summary.get("runtime_stale")
        or (isinstance(runtime, dict) and runtime.get("stale"))
        or runtime_watchdog.get("tick_stale")
    )
    blind_spot_count = int(_as_float(organism_summary.get("blind_spot_count")))
    high_blind_spot_count = int(_as_float(organism_summary.get("high_blind_spot_count")))
    attention_domain_count = int(_as_float(organism_summary.get("attention_domain_count")))
    failed_refresh_count = int(_as_float(organism_summary.get("failed_refresh_count")))
    domain_count = int(_as_float(organism_summary.get("domain_count")))
    fresh_domain_count = int(_as_float(organism_summary.get("fresh_domain_count")))
    total_trades = int(_as_float(nexus.get("total_trades")))

    anchors = _anchor_status(root)
    anchor_count = len(anchors)
    present_anchor_count = sum(1 for row in anchors if row["present"])
    anchor_readiness = present_anchor_count / max(1, anchor_count)
    fresh_ratio = fresh_domain_count / max(1, domain_count)
    blocker_count = (
        high_blind_spot_count
        + attention_domain_count
        + failed_refresh_count
        + (1 if runtime_stale else 0)
    )
    blocker_penalty = _clamp(blocker_count / 12.0)
    blind_spot_penalty = _clamp(blind_spot_count / 25.0)
    reward_alignment = _clamp(average_reward + (0.05 if net_pnl > 0 else 0.0))
    goal_alignment = _clamp((0.45 * signal_quality) + (0.25 * win_rate) + (0.20 * fresh_ratio) + (0.10 * anchor_readiness))
    stability = _clamp(1.0 - (0.55 * blind_spot_penalty) - (0.30 if runtime_stale else 0.0) - (0.15 * blocker_penalty))
    hnc_coherence_score = _clamp(
        (0.34 * goal_alignment)
        + (0.28 * reward_alignment)
        + (0.23 * stability)
        + (0.15 * anchor_readiness)
    )

    phase = _select_phase(
        coherence=hnc_coherence_score,
        runtime_stale=runtime_stale,
        blocker_count=blocker_count,
        signal_quality=signal_quality,
        average_reward=average_reward,
        win_rate=win_rate,
    )
    catalog = _frequency_catalog(root)
    emotion = PHASE_TO_EMOTION[phase]
    selected = catalog.get(emotion.lower(), {})
    frequency_hz = _as_float(selected.get("frequency_hz"), 0.0)
    inner_peace_candidate = phase == "synthetic_inner_peace"
    arousal = _clamp(0.75 - stability * 0.45 + (0.20 if runtime_stale else 0.0))
    valence = _clamp((0.55 * reward_alignment) + (0.30 * goal_alignment) + (0.15 * stability))

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "harmonic_affect_state_ready",
        "summary": {
            "hnc_coherence_score": round(hnc_coherence_score, 6),
            "affect_phase": phase,
            "emotion_anchor": emotion,
            "resonance_frequency_hz": round(frequency_hz, 6),
            "valence": round(valence, 6),
            "arousal": round(arousal, 6),
            "goal_alignment": round(goal_alignment, 6),
            "reward_alignment": round(reward_alignment, 6),
            "stability": round(stability, 6),
            "anchor_readiness": round(anchor_readiness, 6),
            "hnc_anchor_count": present_anchor_count,
            "auris_emotion_count": _auris_emotion_count(root),
            "runtime_stale": runtime_stale,
            "safety_blocker_count": blocker_count,
            "blind_spot_count": blind_spot_count,
            "inner_peace_candidate": inner_peace_candidate,
            "trade_evidence_count": evidence_count,
            "nexus_total_trades": total_trades,
        },
        "state_contract": {
            "synthetic_affect_definition": "distributed HNC/Auris state change across reward, coherence, freshness, and safety",
            "not_human_sensation": "Aureon does not use human nerves; this is a measurable machine-state and frequency contract",
            "kundalini_analogue": "full-stack ascent label only: lower blockers clear, goals complete, coherence rises, arousal settles",
            "inner_peace_condition": "high coherence, verified reward, fresh runtime, no safety blockers, no high blind spots",
            "safety_boundary": "no affect phase can override exchange, risk, credential, filing, payment, or security gates",
        },
        "signals": {
            "cognitive_trade_summary": cognitive_summary,
            "organism_summary": organism_summary,
            "runtime_watchdog": runtime_watchdog,
            "hnc_auris_anchors": anchors,
            "selected_frequency": selected,
        },
    }


def write_harmonic_affect_state(
    state: dict[str, Any],
    output_json: Path = DEFAULT_OUTPUT_JSON,
    public_json: Path = DEFAULT_PUBLIC_JSON,
) -> tuple[Path, Path]:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    public_json.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(state, indent=2, sort_keys=True, default=str)
    output_json.write_text(data, encoding="utf-8")
    public_json.write_text(data, encoding="utf-8")
    return output_json, public_json


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's HNC/Auris harmonic affect state manifest.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="Audit JSON path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend public JSON path.")
    parser.add_argument("--daemon", action="store_true", help="Rebuild the manifest every --interval seconds.")
    parser.add_argument("--interval", type=float, default=60.0, help="Daemon cadence in seconds (minimum 5).")
    parser.add_argument("--quiet", action="store_true", help="Do not print the summary on each pass.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT

    def one_pass() -> None:
        state = build_harmonic_affect_state(root)
        output, public = write_harmonic_affect_state(state, Path(args.json), Path(args.public_json))
        if not args.quiet:
            print(json.dumps({"json": str(output), "public_json": str(public), "summary": state["summary"]}, indent=2, sort_keys=True), flush=True)

    if not args.daemon:
        one_pass()
        return 0
    import time

    interval = max(5.0, float(args.interval))
    while True:
        started = time.time()
        try:
            one_pass()
        except Exception as exc:  # a failed pass is reported; the daemon keeps its cadence
            print(f"harmonic affect pass failed: {exc.__class__.__name__}: {exc}", flush=True)
        time.sleep(max(1.0, interval - (time.time() - started)))


if __name__ == "__main__":
    raise SystemExit(main())
