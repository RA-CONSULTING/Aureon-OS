"""``python -m aureon.observer.historical_backtest`` — replay decades of
real geomagnetic Kp data through the HNC engine + HarmonicObserver and
emit a report.

The repo ships ``data/Kp_ap_Ap_SN_F107_since_1932.txt`` from the GFZ
Helmholtz Centre — daily rows with 8 three-hourly Kp samples each, a
continuous record back to 1932. This module loads a configurable
window, maps each Kp into a SubsystemReading exactly the way the live
daemon does, ticks the LambdaEngine, feeds the resulting state into
the HarmonicObserver, and aggregates the regime / coherence / rocks /
predictor-direction distribution over the entire window.

What's tested:

  * **Engine behaviour against historical reality.** Λ_full and ψ
    evolution against decades of real space weather, not synthetic
    sinusoids.
  * **Observer narrow-band signal.** Coherence_score and rock
    detection over real Kp swings — including the storm periods
    that any field-coupled model has to handle.
  * **Decision divergence.** For every periodic snapshot, the report
    records what the per-symbol observer predictor would have voted
    (BULLISH / BEARISH / NEUTRAL) — the same Brain-6 vote
    queen_gated_buy now reads.

What's intentionally NOT tested here (separate module, separate run):

  * Actual P&L. That requires per-symbol price history aligned to
    the same timestamps and is not in scope for this backtest.
  * The full multi-brain gate. The 5 existing brains require live
    services; this module exercises the observer + engine layer
    only, which is the addition Stage L wired in.

Output:
  docs/research/benchmarks/historical-backtest-<tag>.md   (human report)
  docs/research/benchmarks/historical-backtest-<tag>.json (full series)
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from aureon.core.lambda_reading import format_lambda, lambda_reading


def snapshot_lambda_trace(snaps: List[Any]) -> List[float]:
    """Measured Λ(t) from replay snapshots. Missing points are not 0.0."""
    values: List[float] = []
    for snap in snaps:
        if not isinstance(snap, dict) or "lambda_t" not in snap:
            continue
        number = lambda_reading(snap["lambda_t"])
        if number is None:
            continue
        values.append(number)
    return values


def snapshot_lambda_cell(snap: Any) -> str:
    if not isinstance(snap, dict) or "lambda_t" not in snap:
        return "no reading"
    return format_lambda(snap["lambda_t"], ".3f")

logger = logging.getLogger("aureon.observer.historical_backtest")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KP_PATH = REPO_ROOT / "data" / "Kp_ap_Ap_SN_F107_since_1932.txt"
DEFAULT_REPORTS_DIR = REPO_ROOT / "docs" / "research" / "benchmarks"

# Match the live daemon's mapping: Kp 0 (very quiet) → high coherence
# input value (1.0); Kp 9 (severe storm) → low input value (0.0).
def _map_kp_to_value(kp: float) -> float:
    return max(0.0, min(1.0, 1.0 - float(kp) / 9.0))


def _kp_category(kp: float) -> str:
    if kp < 2.0:
        return "Quiet"
    if kp < 4.0:
        return "Unsettled"
    if kp < 5.0:
        return "Active"
    if kp < 7.0:
        return "Storm"
    return "Severe"


# ─── parser ────────────────────────────────────────────────────────

@dataclass
class KpSample:
    year: int
    month: int
    day: int
    slot: int        # 1..8 (3-hour bucket within the day)
    kp: float


def parse_kp_file(path: Path,
                  start_year: int = 2024,
                  end_year: int = 9999,
                  max_samples: Optional[int] = None) -> List[KpSample]:
    """Parse the GFZ Kp file. Skips comment lines (start with '#').

    Each data row has 8 Kp values (3-hour buckets) for one day. We
    flatten to one sample per 3-hour bucket so a 365-day window yields
    2,920 samples.
    """
    if not path.exists():
        raise FileNotFoundError(f"Kp file not found: {path}")
    out: List[KpSample] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 15:
                continue
            try:
                yr = int(parts[0])
                mo = int(parts[1])
                dy = int(parts[2])
            except (ValueError, IndexError):
                continue
            if yr < start_year:
                continue
            if yr > end_year:
                break
            # Kp1..Kp8 are columns 7..14 (0-indexed)
            try:
                kps = [float(parts[7 + i]) for i in range(8)]
            except (ValueError, IndexError):
                continue
            for slot, kp in enumerate(kps, start=1):
                out.append(KpSample(year=yr, month=mo, day=dy, slot=slot, kp=kp))
                if max_samples is not None and len(out) >= max_samples:
                    return out
    return out


# ─── replay ────────────────────────────────────────────────────────

@dataclass
class _ReplayCapture:
    samples_processed: int = 0
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    rock_events: List[Dict[str, Any]] = field(default_factory=list)
    direction_distribution: Counter = field(default_factory=Counter)
    regime_distribution: Counter = field(default_factory=Counter)
    kp_category_distribution: Counter = field(default_factory=Counter)
    # Stage X — Vote 7 decision-flow tally:
    vote7_outcome_distribution: Counter = field(default_factory=Counter)
    # Per-Kp-category veto/vote/neutral counts (nested: kp_cat → outcome → n)
    vote7_by_kp_category: Dict[str, Counter] = field(default_factory=dict)


def _classify_vote7(consensus_direction: str,
                    consensus_confidence: float,
                    consensus_strength: float) -> str:
    """Mirror the buy-side Vote 7 rule from queen_gated_buy.

    Returns one of:
      'BULLISH_VOTE'      consensus BULLISH, conf ≥ 0.4 → +1 vote
      'BEARISH_VETO'      consensus BEARISH, conf ≥ 0.6, strength ≤ -0.3 → veto
      'NEUTRAL_NO_VOTE'   anything else (NEUTRAL, weak BEARISH,
                          low-conf BULLISH) → 0 vote, no veto
    """
    if consensus_direction == "BULLISH" and consensus_confidence >= 0.4:
        return "BULLISH_VOTE"
    if (consensus_direction == "BEARISH"
            and consensus_confidence >= 0.6
            and consensus_strength <= -0.3):
        return "BEARISH_VETO"
    return "NEUTRAL_NO_VOTE"


def run_replay(
    samples: List[KpSample],
    snapshot_every: int = 100,
    fast_window_minutes: float = 360.0,
    slow_window_minutes: float = 20160.0,
) -> Tuple[_ReplayCapture, Dict[str, Any]]:
    """Replay ``samples`` through LambdaEngine + HarmonicObserver + Vote 7.

    Each Kp is treated as one tick. Per snapshot we now also evaluate
    the buy-side Vote 7 gate (PredictionBus.run_predictions →
    get_consensus → classify_vote7) so the report shows historical
    decision flow: how many bullish votes, how many bearish vetoes,
    how many neutrals — total and broken down by Kp category.
    """
    from aureon.core.aureon_lambda_engine import LambdaEngine, SubsystemReading
    from aureon.observer import HarmonicObserver
    from aureon.observer.predictor import make_predictor
    from aureon.observer.wave_predictor import WavePredictor
    from aureon.autonomous.aureon_autonomy_hub import PredictionBus

    # Reset singletons so a stale observer / wave predictor from a
    # previous run can't bleed in; the new ones auto-claim.
    import aureon.observer as _obs_mod
    import aureon.observer.wave_predictor as _wp_mod
    _obs_mod._observer_singleton = None
    _wp_mod._singleton = None

    engine = LambdaEngine()
    observer = HarmonicObserver(
        fast_window_minutes=fast_window_minutes,
        slow_window_minutes=slow_window_minutes,
        publish_to_bus=False,  # backtest never touches the live bus
    )
    wave = WavePredictor(history_length=120, observer=observer)
    predict = make_predictor(observer)
    # PredictionBus auto-wires harmonic_observer + wave_predictor
    # against the singletons we just constructed (Stages B + Q).
    bus = PredictionBus()
    capture = _ReplayCapture()

    state = None
    for sample in samples:
        # Map Kp → SubsystemReading (mirror live daemon's _map_space_weather).
        reading = SubsystemReading(
            name="space_weather",
            value=_map_kp_to_value(sample.kp),
            confidence=0.9,
            state=_kp_category(sample.kp),
        )
        # Engine step.
        state = engine.step([reading])
        # Feed the engine state into both observer + wave predictor so
        # the bus consensus has real, evolving inputs.
        try:
            observer.ingest_state(state)
        except Exception:
            pass
        try:
            wave.ingest_state(state)
        except Exception:
            pass
        capture.samples_processed += 1
        capture.kp_category_distribution[_kp_category(sample.kp)] += 1

        # Periodic snapshot.
        if capture.samples_processed % snapshot_every == 0:
            snap = observer.metrics_snapshot()
            sig = predict({}, "BTCUSD")

            # Stage X: run the bus consensus + classify Vote 7 outcome.
            try:
                preds = bus.run_predictions({}, "BTCUSD")
                consensus = bus.get_consensus(preds)
                cons_dir = consensus.direction
                cons_conf = float(consensus.confidence)
                cons_str = float(consensus.strength)
                vote7_outcome = _classify_vote7(cons_dir, cons_conf, cons_str)
                # Per-predictor breakdown for audit.
                predictor_breakdown = {
                    n: {
                        "direction": p.direction,
                        "confidence": float(p.confidence),
                        "strength": float(p.strength),
                    }
                    for n, p in (preds or {}).items()
                }
            except Exception:
                cons_dir, cons_conf, cons_str = None, 0.0, 0.0
                vote7_outcome = "NEUTRAL_NO_VOTE"
                predictor_breakdown = {}

            kp_cat = _kp_category(sample.kp)
            capture.regime_distribution[snap.get("regime", "?")] += 1
            capture.direction_distribution[sig.direction] += 1
            capture.vote7_outcome_distribution[vote7_outcome] += 1
            capture.vote7_by_kp_category.setdefault(kp_cat, Counter())[vote7_outcome] += 1
            capture.snapshots.append({
                "sample_index": capture.samples_processed,
                "date": f"{sample.year:04d}-{sample.month:02d}-{sample.day:02d}",
                "kp": sample.kp,
                "kp_category": kp_cat,
                "lambda_t": state.lambda_t,
                "consciousness_psi": state.consciousness_psi,
                "consciousness_level": state.consciousness_level,
                "coherence_gamma": state.coherence_gamma,
                "symbolic_life_score": state.symbolic_life_score,
                "regime": snap.get("regime"),
                "coherence_score": snap.get("coherence_score"),
                "n_rocks_fast": len(snap.get("rocks_fast") or []),
                "n_rocks_slow": len(snap.get("rocks_slow") or []),
                "predictor": {
                    "direction": sig.direction,
                    "confidence": sig.confidence,
                    "strength": sig.strength,
                },
                "consensus": {
                    "direction": cons_dir,
                    "confidence": cons_conf,
                    "strength": cons_str,
                },
                "vote7_outcome": vote7_outcome,
                "predictor_breakdown": predictor_breakdown,
            })

    aggregates = {
        "samples": capture.samples_processed,
        "snapshots": len(capture.snapshots),
        "regime_distribution": dict(capture.regime_distribution),
        "direction_distribution": dict(capture.direction_distribution),
        "kp_category_distribution": dict(capture.kp_category_distribution),
        "vote7_outcome_distribution": dict(capture.vote7_outcome_distribution),
        "vote7_by_kp_category": {
            cat: dict(counts) for cat, counts in capture.vote7_by_kp_category.items()
        },
        "rock_events_total": observer._n_events_emitted,
        "active_rocks_at_end": len(observer.current_rocks()),
        "final_state": {
            "lambda_t": state.lambda_t if samples else None,
            "consciousness_psi": state.consciousness_psi if samples else None,
            "consciousness_level": state.consciousness_level if samples else None,
            "regime": observer.regime() if samples else None,
            "coherence_score": observer.coherence_score() if samples else None,
        },
    }
    return capture, aggregates


# ─── sparkline helpers (reused style from benchmark.py) ────────────

_SPARK_GLYPHS = " ▁▂▃▄▅▆▇█"


def _sparkline(values: List[float], width: Optional[int] = 60) -> str:
    if not values:
        return ""
    vs = list(values)
    if width is not None and width > 0 and width != len(vs):
        step = len(vs) / float(width)
        vs = [vs[min(int(i * step), len(vs) - 1)] for i in range(width)]
    vmin, vmax = min(vs), max(vs)
    span = vmax - vmin
    if span <= 0:
        return _SPARK_GLYPHS[len(_SPARK_GLYPHS) // 2] * len(vs)
    out = []
    for v in vs:
        idx = int(round((v - vmin) / span * (len(_SPARK_GLYPHS) - 1)))
        idx = max(0, min(len(_SPARK_GLYPHS) - 1, idx))
        out.append(_SPARK_GLYPHS[idx])
    return "".join(out)


# ─── report writers ────────────────────────────────────────────────

def _write_markdown(path: Path, capture: _ReplayCapture, agg: Dict[str, Any],
                    tag: str, window_label: str, kp_path: Path) -> None:
    snaps = capture.snapshots
    lines: List[str] = []
    add = lines.append

    add("# HNC Observer — Historical Backtest")
    add("")
    add(f"- **Tag:** `{tag}`")
    add(f"- **Window:** {window_label}")
    add(f"- **Source:** `{kp_path.relative_to(REPO_ROOT) if kp_path.is_relative_to(REPO_ROOT) else kp_path}`")
    add(f"- **Samples replayed:** {agg['samples']}")
    add(f"- **Snapshots taken:** {agg['snapshots']}")
    add(f"- **Rock events emitted:** {agg['rock_events_total']}")
    add(f"- **Active rocks at end:** {agg['active_rocks_at_end']}")
    add("")

    final = agg.get("final_state") or {}
    add("## Final field state")
    add("")
    if final.get("lambda_t") is not None:
        add(f"- **Λ_full:** {final['lambda_t']:.6f}")
        add(f"- **ψ:** {final['consciousness_psi']:.4f} ({final['consciousness_level']})")
        add(f"- **Regime:** {final['regime']}")
        add(f"- **Coherence score:** {final['coherence_score']:.4f}")
    add("")

    add("## Kp distribution (input)")
    add("")
    add("| Category | Samples | Pct |")
    add("|---|---|---|")
    total = agg["samples"] or 1
    for cat in ("Quiet", "Unsettled", "Active", "Storm", "Severe"):
        n = agg["kp_category_distribution"].get(cat, 0)
        add(f"| {cat} | {n} | {100.0 * n / total:.1f}% |")
    add("")

    add("## Regime distribution (over snapshots)")
    add("")
    add("| Regime | Snapshots |")
    add("|---|---|")
    for k, v in sorted(agg["regime_distribution"].items(), key=lambda kv: -kv[1]):
        add(f"| {k} | {v} |")
    add("")

    add("## Predictor direction distribution (over snapshots)")
    add("")
    add("| Direction | Snapshots |")
    add("|---|---|")
    for k, v in sorted(agg["direction_distribution"].items(), key=lambda kv: -kv[1]):
        add(f"| {k} | {v} |")
    add("")

    # Stage X: Vote 7 decision-flow tables.
    add("## Vote 7 decision flow (queen_gated_buy gate evaluation)")
    add("")
    add("Each periodic snapshot is evaluated against the buy-side Vote 7 "
        "logic: consensus BULLISH ≥40% conf adds +1 vote; consensus "
        "BEARISH ≥60% conf with strength ≤−0.3 vetoes the trade outright; "
        "everything else is neutral / no vote.")
    add("")

    v7 = agg.get("vote7_outcome_distribution") or {}
    total_snaps = max(1, sum(v7.values()))
    if v7:
        add("**Outcome distribution:**")
        add("")
        add("| Outcome | Count | % |")
        add("|---|---|---|")
        for outcome in ("BULLISH_VOTE", "BEARISH_VETO", "NEUTRAL_NO_VOTE"):
            n = v7.get(outcome, 0)
            add(f"| {outcome} | {n} | {100.0 * n / total_snaps:.1f}% |")
        add("")

    v7_kp = agg.get("vote7_by_kp_category") or {}
    if v7_kp:
        add("**Outcome by Kp category** "
            "(does narrow-band fire harder during storms?):")
        add("")
        add("| Kp category | Snapshots | Bullish votes | Bearish vetos | Neutral | Veto rate |")
        add("|---|---|---|---|---|---|")
        for cat in ("Quiet", "Unsettled", "Active", "Storm", "Severe"):
            cat_data = v7_kp.get(cat) or {}
            n_total = sum(cat_data.values())
            if n_total == 0:
                continue
            n_bull = cat_data.get("BULLISH_VOTE", 0)
            n_veto = cat_data.get("BEARISH_VETO", 0)
            n_neut = cat_data.get("NEUTRAL_NO_VOTE", 0)
            veto_pct = 100.0 * n_veto / n_total
            add(f"| {cat} | {n_total} | {n_bull} | {n_veto} | "
                f"{n_neut} | {veto_pct:.1f}% |")
        add("")

    # Consensus signal traces — show the underlying movement even when
    # the Vote 7 threshold isn't crossed. The threshold gates DECISION;
    # the trace gates UNDERSTANDING.
    cons_dirs = [str((s.get("consensus") or {}).get("direction") or "?") for s in snaps]
    cons_confs = [float((s.get("consensus") or {}).get("confidence") or 0.0) for s in snaps]
    cons_strs = [float((s.get("consensus") or {}).get("strength") or 0.0) for s in snaps]
    if cons_strs:
        add("**Consensus signal trace** (raw, pre-threshold):")
        add("")
        add(f"- Direction histogram: " +
            ", ".join(f"{d}: {cons_dirs.count(d)}"
                      for d in sorted(set(cons_dirs))))
        add(f"- Strength range: {min(cons_strs):+.4f} → {max(cons_strs):+.4f} "
            f"(mean {sum(cons_strs)/len(cons_strs):+.4f})")
        add(f"- Confidence range: {min(cons_confs):.4f} → {max(cons_confs):.4f} "
            f"(mean {sum(cons_confs)/len(cons_confs):.4f})")
        add("")
        add(f"**Strength sparkline** ({min(cons_strs):+.3f} → {max(cons_strs):+.3f}):")
        add(f"```\n{_sparkline(cons_strs)}\n```")
        add("")
        add(f"**Confidence sparkline** ({min(cons_confs):.3f} → {max(cons_confs):.3f}):")
        add(f"```\n{_sparkline(cons_confs)}\n```")
        add("")
        add(f"_Vote 7 fires when direction == BULLISH and confidence ≥ 0.40 "
            f"(or direction == BEARISH and confidence ≥ 0.60 with strength ≤ −0.30). "
            f"A consistent below-threshold bullish trace is itself a finding: "
            f"the consensus signal is non-zero, just gated by the harmonic field's "
            f"coherence floor (no rocks → coherence_gate at 0.25 → confidence squashed)._ ")
        add("")

    if snaps:
        kps = [float(s.get("kp") or 0.0) for s in snaps]
        lambdas = snapshot_lambda_trace(snaps)
        psis = [float(s.get("consciousness_psi") or 0.0) for s in snaps]
        cohs = [float(s.get("coherence_score") or 0.0) for s in snaps]
        sls = [float(s.get("symbolic_life_score") or 0.0) for s in snaps]

        add("## Time series (snapshot-aligned sparklines)")
        add("")
        add(f"**Kp input** ({min(kps):.2f} → {max(kps):.2f}):")
        add(f"```\n{_sparkline(kps)}\n```")
        add("")
        if lambdas:
            add(f"**Λ_full** ({min(lambdas):.3f} → {max(lambdas):.3f}):")
            add(f"```\n{_sparkline(lambdas)}\n```")
        else:
            add("**Λ_full:** no reading")
        add("")
        add(f"**ψ (consciousness)** ({min(psis):.3f} → {max(psis):.3f}):")
        add(f"```\n{_sparkline(psis)}\n```")
        add("")
        add(f"**Coherence score** ({min(cohs):.3f} → {max(cohs):.3f}):")
        add(f"```\n{_sparkline(cohs)}\n```")
        add("")
        add(f"**Symbolic life score** ({min(sls):.3f} → {max(sls):.3f}):")
        add(f"```\n{_sparkline(sls)}\n```")
        add("")

        add("## Recent snapshots (last 12)")
        add("")
        add("| Date | Kp | Λ_full | ψ | Level | Regime | Coherence | Pred dir |")
        add("|---|---|---|---|---|---|---|---|")
        for s in snaps[-12:]:
            add(f"| {s['date']} | {s['kp']:.2f} | {snapshot_lambda_cell(s)} | "
                f"{s['consciousness_psi']:.3f} | {s['consciousness_level']} | "
                f"{s['regime']} | {s['coherence_score']:.3f} | "
                f"{s['predictor']['direction']} |")
        add("")

    add("---")
    add("")
    add("*Generated by `aureon.observer.historical_backtest`. "
        "Re-run any time with `python -m aureon.observer.historical_backtest`.*")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_json(path: Path, capture: _ReplayCapture, agg: Dict[str, Any],
                tag: str) -> None:
    payload = {
        "tag": tag,
        "aggregates": agg,
        "snapshots": capture.snapshots,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str),
                     encoding="utf-8")


# ─── CLI ───────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aureon.observer.historical_backtest",
        description="Replay historical Kp data through HNC + observer.",
    )
    parser.add_argument("--kp-path", type=Path, default=DEFAULT_KP_PATH,
                        help=f"Kp data file (default {DEFAULT_KP_PATH}).")
    parser.add_argument("--start-year", type=int, default=2024,
                        help="First year of data to replay (default 2024).")
    parser.add_argument("--end-year", type=int, default=9999,
                        help="Last year of data to replay (default 9999 = end of file).")
    parser.add_argument("--max-samples", type=int, default=None,
                        help="Stop after N samples (8 per day). Default: all in range.")
    parser.add_argument("--snapshot-every", type=int, default=100,
                        help="Take an observer snapshot every N samples (default 100).")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR,
                        help=f"Where to write reports (default {DEFAULT_REPORTS_DIR}).")
    parser.add_argument("--tag", type=str, default=None,
                        help="Tag for the report filename. Default: yearrange-timestamp.")
    parser.add_argument("--no-write", action="store_true",
                        help="Run replay but skip report files; print summary.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    logger.info("loading Kp samples from %s (years %d..%d)",
                args.kp_path, args.start_year, args.end_year)
    samples = parse_kp_file(
        args.kp_path,
        start_year=args.start_year,
        end_year=args.end_year,
        max_samples=args.max_samples,
    )
    if not samples:
        print(f"error: no samples in window {args.start_year}..{args.end_year}",
              file=sys.stderr)
        return 3
    logger.info("loaded %d samples — replaying", len(samples))

    capture, aggregates = run_replay(samples, snapshot_every=args.snapshot_every)
    window_label = f"{samples[0].year}-{samples[0].month:02d}-{samples[0].day:02d} → " \
                   f"{samples[-1].year}-{samples[-1].month:02d}-{samples[-1].day:02d} " \
                   f"({aggregates['samples']} samples)"

    tag = args.tag or f"{samples[0].year}-{samples[-1].year}-" \
                       f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"

    if args.no_write:
        print(json.dumps({"tag": tag, "window": window_label,
                          "aggregates": aggregates}, indent=2, sort_keys=True,
                         default=str))
        return 0

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = args.reports_dir / f"historical-backtest-{tag}.md"
    json_path = args.reports_dir / f"historical-backtest-{tag}.json"

    _write_json(json_path, capture, aggregates, tag)
    _write_markdown(md_path, capture, aggregates, tag, window_label, args.kp_path)

    print()
    print(f"Tag:                {tag}")
    print(f"Window:             {window_label}")
    print(f"Samples:            {aggregates['samples']}")
    print(f"Snapshots:          {aggregates['snapshots']}")
    print(f"Rock events:        {aggregates['rock_events_total']}")
    print(f"Active rocks:       {aggregates['active_rocks_at_end']}")
    print(f"Final regime:       {aggregates.get('final_state', {}).get('regime')}")
    print(f"Final ψ:            {aggregates.get('final_state', {}).get('consciousness_psi'):.4f}")
    print(f"Coherence:          {aggregates.get('final_state', {}).get('coherence_score'):.4f}")
    print()
    print(f"Report:             {md_path}")
    print(f"JSON:               {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
