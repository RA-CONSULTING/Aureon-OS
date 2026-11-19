"""``python -m aureon.observer.benchmark`` — capture a real-data benchmark run.

Drives the live HNC daemon for a configurable duration against the real
fetchers (NOAA Kp, Schumann bridge, GDELT), records every kernel state,
every rock event, and a periodic PredictionBus consensus + Kelly gate
comparison, then writes a markdown + JSON report under
``docs/research/benchmarks/`` following the existing
``queen-benchmark-run*.md`` convention.

The benchmark is the unified-field signature: how the live observer
characterises the field over the run, what rocks emerge, how the
coherence_score evolves, and what the auto-wired downstream consumers
(probability bus, Kelly gate) say about the same window.

Three capture channels run in parallel:

  1. **Engine snapshots** — every COMPUTE_INTERVAL the daemon ticks, the
     observer's metrics_snapshot is recorded (regime, coherence, rocks,
     latest_field).

  2. **Rock events** — a ThoughtBus subscriber catches every
     ``harmonic.observer.rock`` envelope (formed / strengthened /
     weakened / vanished) with its full payload.

  3. **Periodic policy reads** — every PERIODIC_READ_INTERVAL the
     benchmark calls ``PredictionBus.run_predictions`` →
     ``get_consensus`` and computes
     ``AdaptivePrimeProfitGate.calculate_gates`` once with and once
     without observer_coherence so the report can show their delta.

The benchmark itself does not modify any production state; it's a
pure read-side observer of the observer. Re-runnable; each invocation
gets its own dated report file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aureon.core.lambda_reading import format_lambda, lambda_reading


def engine_lambda_trace(snaps: List[Any]) -> List[float]:
    """Measured Λ(t) points. A missing sample is dropped, not written as 0.0."""
    values: List[float] = []
    for snap in snaps:
        engine = snap.get("engine_state") if isinstance(snap, dict) else None
        if not isinstance(engine, dict) or "lambda_t" not in engine:
            continue
        number = lambda_reading(engine["lambda_t"])
        if number is None:
            continue
        values.append(number)
    return values


def measured_trace(snaps: List[Any], *path: str) -> List[float]:
    """Numeric points along ``path``. Missing and non-finite points are skipped.

    A measured ``0.0`` stays in the series. ``or 0.0`` is not used.
    """
    values: List[float] = []
    for snap in snaps:
        current: Any = snap
        present = True
        for key in path:
            if not isinstance(current, dict) or key not in current:
                present = False
                break
            current = current[key]
        if not present:
            continue
        number = lambda_reading(current)
        if number is None:
            continue
        values.append(number)
    return values

logger = logging.getLogger("aureon.observer.benchmark")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS_DIR = REPO_ROOT / "docs" / "research" / "benchmarks"

# Cadence of the periodic policy-read sampling — independent of the
# daemon's compute loop. Long enough that NOAA / GDELT have a chance
# to refresh between samples.
PERIODIC_READ_INTERVAL_S = 30.0


# ─── capture state ─────────────────────────────────────────────────

@dataclass
class _BenchCapture:
    """Mutable buffer the run loop appends into."""
    started_at: float = field(default_factory=time.time)
    engine_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    rock_events: List[Dict[str, Any]] = field(default_factory=list)
    periodic_reads: List[Dict[str, Any]] = field(default_factory=list)
    fetcher_errors: List[Dict[str, Any]] = field(default_factory=list)


# ─── orchestration ─────────────────────────────────────────────────

async def _engine_snapshot_loop(
    daemon, capture: _BenchCapture, interval_s: float, stop: asyncio.Event
) -> None:
    """Pull the observer's snapshot at a fixed cadence."""
    while not stop.is_set():
        if daemon._observer is not None:
            try:
                snap = daemon._observer.metrics_snapshot()
                # Trim rocks payloads to top-5 each scale to keep the
                # report file from ballooning.
                snap_compact = dict(snap)
                snap_compact["rocks_fast"] = snap.get("rocks_fast", [])[:5]
                snap_compact["rocks_slow"] = snap.get("rocks_slow", [])[:5]
                capture.engine_snapshots.append({
                    "ts": time.time(),
                    "snapshot": snap_compact,
                    "engine_state": dict(daemon._last_state_dict or {}),
                })
            except Exception as exc:
                logger.debug("snapshot pull failed: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
            return
        except asyncio.TimeoutError:
            pass


async def _periodic_read_loop(
    daemon, capture: _BenchCapture, stop: asyncio.Event
) -> None:
    """Sample PredictionBus consensus + Kelly readings (with/without observer)."""
    try:
        from aureon.autonomous.aureon_autonomy_hub import PredictionBus
        from aureon.utils.adaptive_prime_profit_gate import AdaptivePrimeProfitGate
    except Exception as exc:
        logger.warning("periodic-read deps unavailable: %s", exc)
        return

    bus = PredictionBus()       # auto-wires harmonic_observer (Stage B)
    gate = AdaptivePrimeProfitGate()
    SAMPLE_TRADE_VALUE = 100.0
    SAMPLE_EXCHANGE = "binance"

    while not stop.is_set():
        try:
            preds = bus.run_predictions({}, symbol="BTCUSD")
            consensus = bus.get_consensus(preds)
            obs_pred = preds.get("harmonic_observer")

            # Kelly: explicit None (today's behaviour) vs explicit
            # observer-driven (consult singleton's coherence_score).
            obs_coh = None
            if daemon._observer is not None:
                try:
                    obs_coh = float(daemon._observer.coherence_score())
                except Exception:
                    obs_coh = None
            gate_baseline = gate.calculate_gates(
                SAMPLE_EXCHANGE, SAMPLE_TRADE_VALUE,
                observer_coherence=False,    # explicit disable
                use_cache=False,
            )
            gate_observed = gate.calculate_gates(
                SAMPLE_EXCHANGE, SAMPLE_TRADE_VALUE,
                observer_coherence=obs_coh,  # explicit float or None
                use_cache=False,
            )

            capture.periodic_reads.append({
                "ts": time.time(),
                "n_predictors": len(preds),
                "predictor_directions": {n: p.direction for n, p in preds.items()},
                "predictor_strengths": {n: float(p.strength) for n, p in preds.items()},
                "consensus": {
                    "direction": consensus.direction,
                    "confidence": float(consensus.confidence),
                    "strength": float(consensus.strength),
                    "agreement_ratio": consensus.payload.get("agreement_ratio") if consensus.payload else None,
                },
                "harmonic_observer_signal": (
                    {
                        "direction": obs_pred.direction,
                        "confidence": float(obs_pred.confidence),
                        "strength": float(obs_pred.strength),
                        "n_aligned_rocks": (obs_pred.payload or {}).get("n_aligned_rocks"),
                        "regime": (obs_pred.payload or {}).get("regime"),
                    }
                    if obs_pred is not None else None
                ),
                "observer_coherence_used": obs_coh,
                "kelly_baseline_r_prime_buffer": float(gate_baseline.r_prime_buffer),
                "kelly_observed_r_prime_buffer": float(gate_observed.r_prime_buffer),
                "kelly_buffer_multiplier": float(gate_observed.observer_buffer_multiplier),
            })
        except Exception as exc:
            logger.debug("periodic read failed: %s", exc)

        try:
            await asyncio.wait_for(stop.wait(), timeout=PERIODIC_READ_INTERVAL_S)
            return
        except asyncio.TimeoutError:
            pass


def _wire_thoughtbus_capture(capture: _BenchCapture):
    """Subscribe to harmonic.observer.* and append to capture."""
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus
        bus = get_thought_bus()
    except Exception as exc:
        logger.warning("ThoughtBus capture unavailable: %s", exc)
        return None

    def _handler(thought):
        try:
            payload = getattr(thought, "payload", None) or {}
            capture.rock_events.append({
                "ts": getattr(thought, "ts", time.time()),
                "topic": getattr(thought, "topic", ""),
                "payload": dict(payload) if isinstance(payload, dict) else {"value": str(payload)},
            })
        except Exception:
            pass

    try:
        bus.subscribe("harmonic.observer.rock", _handler)
    except Exception as exc:
        logger.debug("subscribe failed: %s", exc)
        return None
    return _handler


# ─── aggregation ───────────────────────────────────────────────────

def _aggregate(capture: _BenchCapture, daemon) -> Dict[str, Any]:
    """Compute summary stats from the captured event log."""
    snaps = capture.engine_snapshots
    reads = capture.periodic_reads
    rock_events = capture.rock_events

    duration_s = (snaps[-1]["ts"] - capture.started_at) if snaps else 0.0
    if not snaps:
        return {
            "duration_s": duration_s,
            "engine_snapshots": 0,
            "rock_events": len(rock_events),
            "periodic_reads": len(reads),
            "n_rocks_final": 0,
            "regime_histogram": {},
        "coherence_mean": None,
        "coherence_min": None,
        "coherence_max": None,
            "rock_event_kinds": {},
            "predictor_consensus_directions": {},
            "kelly_buffer_multiplier_mean": 1.0,
            "fetchers": {},
        }

    # Regime histogram
    regimes = [s["snapshot"].get("regime", "UNKNOWN") for s in snaps]
    regime_hist = dict(Counter(regimes))

    # Coherence trace
    cohs = measured_trace(snaps, "snapshot", "coherence_score")

    # Rock event kinds
    event_kinds = Counter(
        e["payload"].get("event", "?") for e in rock_events if "payload" in e
    )

    # Predictor consensus direction distribution
    consensus_dirs = Counter(r["consensus"]["direction"] for r in reads if r.get("consensus"))

    # Kelly buffer-multiplier mean
    mults = [r["kelly_buffer_multiplier"] for r in reads
             if r.get("kelly_buffer_multiplier") is not None]
    mult_mean = (sum(mults) / len(mults)) if mults else 1.0

    # Fetcher status from daemon source state
    fetchers = {}
    if daemon is not None:
        fetchers = daemon.source_status

    # Final rock count
    last_snap = snaps[-1]["snapshot"]
    n_rocks_final = (
        len(last_snap.get("rocks_fast", [])) + len(last_snap.get("rocks_slow", []))
    )

    return {
        "duration_s": duration_s,
        "engine_snapshots": len(snaps),
        "rock_events": len(rock_events),
        "periodic_reads": len(reads),
        "n_rocks_final": n_rocks_final,
        "regime_histogram": regime_hist,
        "coherence_mean": (sum(cohs) / len(cohs)) if cohs else None,
        "coherence_min": min(cohs) if cohs else None,
        "coherence_max": max(cohs) if cohs else None,
        "rock_event_kinds": dict(event_kinds),
        "predictor_consensus_directions": dict(consensus_dirs),
        "kelly_buffer_multiplier_mean": mult_mean,
        "fetchers": fetchers,
    }


# ─── report writers ────────────────────────────────────────────────

_BENCH_HEADER = "# HNC Observer — Unified Field Benchmark"


def _stat_text(value: Any, spec: str) -> str:
    if value is None:
        return "no reading"
    return format(value, spec)


# ─── text sparkline ────────────────────────────────────────────────
# 8-level Unicode block characters; mapping a value's position in
# [vmin, vmax] to a glyph. Constant-width, no font dependency.
_SPARK_GLYPHS = " ▁▂▃▄▅▆▇█"


def _sparkline(values: List[float], width: Optional[int] = None) -> str:
    """Render ``values`` as a one-line block-character sparkline.

    Empty input returns an empty string. Constant series renders as
    a flat midline. ``width`` resamples to that many output columns
    (nearest-neighbour); None preserves the input length.
    """
    if not values:
        return ""
    vs = list(values)
    if width is not None and width > 0 and width != len(vs):
        # Nearest-neighbour resample.
        step = len(vs) / float(width)
        vs = [vs[min(int(i * step), len(vs) - 1)] for i in range(width)]
    vmin = min(vs)
    vmax = max(vs)
    span = vmax - vmin
    if span <= 0:
        # Flat — pick the middle glyph so it's visible.
        return _SPARK_GLYPHS[len(_SPARK_GLYPHS) // 2] * len(vs)
    out = []
    for v in vs:
        norm = (v - vmin) / span
        idx = int(round(norm * (len(_SPARK_GLYPHS) - 1)))
        idx = max(0, min(len(_SPARK_GLYPHS) - 1, idx))
        out.append(_SPARK_GLYPHS[idx])
    return "".join(out)


def _regime_timeline(snaps: List[Dict[str, Any]]) -> str:
    """Single-line timeline showing regime transitions across the run.

    Format: ``WARMING(4) → QUIET(14)`` — each regime with its
    consecutive sample count, transitions separated by → arrows.
    """
    if not snaps:
        return ""
    runs: List[Tuple[str, int]] = []
    cur = None
    n = 0
    for s in snaps:
        regime = s["snapshot"].get("regime", "?") or "?"
        if regime == cur:
            n += 1
        else:
            if cur is not None:
                runs.append((cur, n))
            cur = regime
            n = 1
    if cur is not None:
        runs.append((cur, n))
    return " → ".join(f"{r}({c})" for r, c in runs)


def _write_markdown(report_path: Path, agg: Dict[str, Any], capture: _BenchCapture,
                    params: Dict[str, Any], tag: str) -> None:
    started = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(capture.started_at))
    snaps = capture.engine_snapshots
    reads = capture.periodic_reads
    last_snap = snaps[-1]["snapshot"] if snaps else {}
    last_engine = snaps[-1]["engine_state"] if snaps else {}

    lines: List[str] = []
    add = lines.append
    add(_BENCH_HEADER)
    add("")
    add(f"- **Tag:** `{tag}`")
    add(f"- **Started:** {started}")
    add(f"- **Duration:** {agg['duration_s']:.1f} s")
    add(f"- **Engine snapshots:** {agg['engine_snapshots']}")
    add(f"- **Rock events on bus:** {agg['rock_events']}")
    add(f"- **Periodic policy reads:** {agg['periodic_reads']}")
    add("")
    add("## HNC parameters in effect")
    add("")
    add(f"| α | g | β | τ | Δt | fitted? |")
    add("|---|---|---|---|---|---|")
    fitted = "yes" if params.get("fitted_at") else "no (defaults)"
    add(f"| {params.get('alpha')} | {params.get('g')} | {params.get('beta')} | "
        f"{params.get('tau')} | {params.get('delta_t')} | {fitted} |")
    if params.get("r_squared"):
        add(f"")
        add(f"R² of last fit: **{params.get('r_squared'):.3f}** "
            f"(from {params.get('fitted_from')})")
    add("")
    add("## Field state at end of run")
    add("")
    if last_engine:
        add(f"- **Λ_full:** {format_lambda(last_engine.get('lambda_t'), '.6f')}")
        add(f"- **ψ (consciousness_psi):** {format_lambda(last_engine.get('consciousness_psi') if 'consciousness_psi' in last_engine else None)}")
        add(f"- **Level:** {last_engine.get('consciousness_level', 'n/a')}")
        add(f"- **Γ (coherence_gamma):** {format_lambda(last_engine.get('coherence_gamma') if 'coherence_gamma' in last_engine else None)}")
        add(f"- **Symbolic life score:** {format_lambda(last_engine.get('symbolic_life_score') if 'symbolic_life_score' in last_engine else None)}")
        add(f"- **Effective gain (α+β):** {last_engine.get('effective_gain', 0):.3f}")
    add("")
    add("## Observer signal")
    add("")
    add(f"- **Final regime:** {last_snap.get('regime', 'n/a')}")
    add(f"- **Coherence mean / min / max:** "
        f"{_stat_text(agg['coherence_mean'], '.3f')} / {_stat_text(agg['coherence_min'], '.3f')} / {_stat_text(agg['coherence_max'], '.3f')}")
    add(f"- **Active rocks at end:** {agg['n_rocks_final']}")
    add("")
    add("**Regime histogram (over snapshot samples):**")
    add("")
    add("| Regime | Samples |")
    add("|---|---|")
    for k, v in sorted(agg["regime_histogram"].items(), key=lambda kv: -kv[1]):
        add(f"| {k} | {v} |")
    add("")
    add("**Rock event kinds (over the run):**")
    add("")
    if agg["rock_event_kinds"]:
        add("| Event | Count |")
        add("|---|---|")
        for k, v in sorted(agg["rock_event_kinds"].items(), key=lambda kv: -kv[1]):
            add(f"| {k} | {v} |")
    else:
        add("*(no rock events emitted — observer needs numpy/scipy or more data)*")
    add("")
    add("## Time series")
    add("")
    # Coherence trace
    cohs = measured_trace(snaps, "snapshot", "coherence_score")
    if cohs:
        add(f"**Coherence score** ({min(cohs):.3f} → {max(cohs):.3f}, "
            f"mean {sum(cohs)/len(cohs):.3f}):")
        add("")
        add(f"```\n{_sparkline(cohs, width=min(len(cohs), 60))}\n```")
        add("")
    # Λ_full trace from engine_state
    lambdas = engine_lambda_trace(snaps)
    if lambdas:
        add(f"**Λ_full** ({min(lambdas):.3f} → {max(lambdas):.3f}):")
        add("")
        add(f"```\n{_sparkline(lambdas, width=min(len(lambdas), 60))}\n```")
        add("")
    else:
        add("**Λ_full:** no reading")
        add("")
    # ψ trace
    psis = measured_trace(snaps, "engine_state", "consciousness_psi")
    if psis:
        add(f"**ψ (consciousness)** ({min(psis):.3f} → {max(psis):.3f}):")
        add("")
        add(f"```\n{_sparkline(psis, width=min(len(psis), 60))}\n```")
        add("")
    # Symbolic life score
    sls = measured_trace(snaps, "engine_state", "symbolic_life_score")
    if sls:
        add(f"**Symbolic life score** ({min(sls):.3f} → {max(sls):.3f}):")
        add("")
        add(f"```\n{_sparkline(sls, width=min(len(sls), 60))}\n```")
        add("")
    # Regime transition timeline (text, not sparkline)
    timeline = _regime_timeline(snaps)
    if timeline:
        add(f"**Regime timeline:** {timeline}")
        add("")

    add("## Predictor consensus")
    add("")
    add(f"- **Periodic reads:** {agg['periodic_reads']}")
    if agg["predictor_consensus_directions"]:
        add("")
        add("**Consensus direction histogram:**")
        add("")
        add("| Direction | Reads |")
        add("|---|---|")
        for k, v in sorted(agg["predictor_consensus_directions"].items(),
                           key=lambda kv: -kv[1]):
            add(f"| {k} | {v} |")
    # Per-predictor breakdown — what every registered predictor said
    # at the LAST periodic read. Useful for "is X actually wired?"
    # debugging without needing to open the JSON.
    if reads:
        last = reads[-1]
        directions = last.get("predictor_directions") or {}
        strengths = last.get("predictor_strengths") or {}
        if directions:
            add("")
            add("**Per-predictor breakdown (last read):**")
            add("")
            add("| Predictor | Direction | Strength |")
            add("|---|---|---|")
            for name in sorted(directions.keys()):
                d = directions.get(name, "?")
                s = strengths.get(name, 0.0)
                add(f"| {name} | {d} | {s:+.3f} |")
    # Per-read consensus strength evolution
    cons_strengths = [
        float(r["consensus"].get("strength", 0.0))
        for r in reads if r.get("consensus")
    ]
    cons_confs = [
        float(r["consensus"].get("confidence", 0.0))
        for r in reads if r.get("consensus")
    ]
    if cons_strengths:
        add("")
        add(f"**Consensus strength** "
            f"({min(cons_strengths):+.3f} → {max(cons_strengths):+.3f}):")
        add("")
        add(f"```\n{_sparkline(cons_strengths, width=min(len(cons_strengths), 40))}\n```")
        add("")
    if cons_confs:
        add(f"**Consensus confidence** "
            f"({min(cons_confs):.3f} → {max(cons_confs):.3f}):")
        add("")
        add(f"```\n{_sparkline(cons_confs, width=min(len(cons_confs), 40))}\n```")
        add("")

    add("## Kelly gate coupling")
    add("")
    add(f"- **Mean buffer multiplier (observed/baseline):** "
        f"{agg['kelly_buffer_multiplier_mean']:.3f}")
    add("- A multiplier > 1.0 means the observer's coherence_score < 1.0 "
        "and the safety buffer was widened; 1.0 means no widening.")
    # Side-by-side baseline vs observed Kelly r_prime_buffer table
    if reads:
        add("")
        add("**Baseline vs observer-driven r_prime_buffer per read:**")
        add("")
        add("| t (s) | observer_coh | baseline | observed | mul | Δ (bps) |")
        add("|---|---|---|---|---|---|")
        t0 = capture.started_at
        for r in reads:
            coh = r.get("observer_coherence_used")
            coh_s = f"{coh:.3f}" if coh is not None else "—"
            base = r.get("kelly_baseline_r_prime_buffer", 0.0)
            obs = r.get("kelly_observed_r_prime_buffer", 0.0)
            mul = r.get("kelly_buffer_multiplier", 1.0)
            delta_bps = (obs - base) * 1e4   # fraction → basis points
            add(f"| {r['ts']-t0:.0f} | {coh_s} | "
                f"{base:.6f} | {obs:.6f} | {mul:.3f} | {delta_bps:+.2f} |")
        # Sparkline of the multiplier over time
        mults = [r.get("kelly_buffer_multiplier", 1.0) for r in reads]
        if mults:
            add("")
            add(f"**Multiplier trace** ({min(mults):.3f} → {max(mults):.3f}):")
            add("")
            add(f"```\n{_sparkline(mults, width=min(len(mults), 40))}\n```")
            add("")

    add("## Fetcher health")
    add("")
    if agg["fetchers"]:
        add("| Source | Interval (s) | Lag (s) | Errors | Has reading |")
        add("|---|---|---|---|---|")
        for name, fs in agg["fetchers"].items():
            lag = f"{fs['lag_s']:.1f}" if fs.get("lag_s") is not None else "—"
            add(f"| {name} | {fs.get('interval_s'):.0f} | {lag} | "
                f"{fs.get('error_count')} | {fs.get('has_reading')} |")
    else:
        add("*(no fetcher status available)*")
    add("")
    add("---")
    add("")
    add("*Generated by `aureon.observer.benchmark` — re-run any time with "
        "`python -m aureon.observer.benchmark`.*")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _write_json(json_path: Path, agg: Dict[str, Any], capture: _BenchCapture,
                params: Dict[str, Any], tag: str) -> None:
    payload = {
        "tag": tag,
        "started_at": capture.started_at,
        "params": params,
        "aggregates": agg,
        "engine_snapshots": capture.engine_snapshots,
        "rock_events": capture.rock_events,
        "periodic_reads": capture.periodic_reads,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str),
                          encoding="utf-8")


# ─── runner ────────────────────────────────────────────────────────

async def _run(duration_s: float, snapshot_interval_s: float,
               capture: _BenchCapture):
    """Drive the daemon + capture loops for ``duration_s`` seconds."""
    from aureon.core.hnc_live_daemon import HNCLiveDaemon

    daemon = HNCLiveDaemon(attach_observer=True)
    _wire_thoughtbus_capture(capture)

    stop = asyncio.Event()
    snap_task = asyncio.create_task(
        _engine_snapshot_loop(daemon, capture, snapshot_interval_s, stop),
        name="bench:snap",
    )
    read_task = asyncio.create_task(
        _periodic_read_loop(daemon, capture, stop),
        name="bench:read",
    )
    daemon_task = asyncio.create_task(
        daemon.run(duration_s=duration_s),
        name="bench:daemon",
    )

    try:
        await daemon_task
    finally:
        stop.set()
        await asyncio.gather(snap_task, read_task, return_exceptions=True)
    return daemon


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aureon.observer.benchmark",
        description="Capture a real-data benchmark run and write a report.",
    )
    parser.add_argument("--duration", type=float, default=300.0,
                        help="Run duration in seconds (default 300 = 5 min).")
    parser.add_argument("--snapshot-interval", type=float, default=10.0,
                        help="Cadence of engine snapshot capture in seconds (default 10).")
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR,
                        help=f"Where to write reports (default {DEFAULT_REPORTS_DIR}).")
    parser.add_argument("--tag", type=str, default=None,
                        help="Run tag for the report filename. "
                             "Default: ISO-ish timestamp of the run start.")
    parser.add_argument("--json-only", action="store_true",
                        help="Only emit the .json file (skip the .md report).")
    parser.add_argument("--no-write", action="store_true",
                        help="Run the capture but DON'T write any report files. "
                             "Useful for smoke-testing.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=os.environ.get("AUREON_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    capture = _BenchCapture()
    tag = args.tag or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(capture.started_at))

    # Capture the params actually applied to the engine for this run.
    from aureon.core.hnc_params import load_params
    p = load_params()
    params = {
        "alpha": p.alpha, "g": p.g, "beta": p.beta, "tau": p.tau,
        "delta_t": p.delta_t, "fitted_at": p.fitted_at,
        "fitted_from": p.fitted_from, "r_squared": p.r_squared,
    }

    try:
        daemon = asyncio.run(_run(args.duration, args.snapshot_interval, capture))
    except KeyboardInterrupt:
        return 130

    agg = _aggregate(capture, daemon)

    if args.no_write:
        print(json.dumps({"tag": tag, "params": params, "aggregates": agg},
                          indent=2, sort_keys=True, default=str))
        return 0

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = args.reports_dir / f"observer-benchmark-{tag}.md"
    json_path = args.reports_dir / f"observer-benchmark-{tag}.json"

    _write_json(json_path, agg, capture, params, tag)
    if not args.json_only:
        _write_markdown(md_path, agg, capture, params, tag)

    print()
    print(f"Benchmark tag: {tag}")
    print(f"Duration:      {agg['duration_s']:.1f}s")
    print(f"Snapshots:     {agg['engine_snapshots']}")
    print(f"Rock events:   {agg['rock_events']}")
    print(f"Periodic rds:  {agg['periodic_reads']}")
    print(f"Final regime:  {capture.engine_snapshots[-1]['snapshot'].get('regime') if capture.engine_snapshots else 'n/a'}")
    print(f"Coherence avg: {_stat_text(agg['coherence_mean'], '.3f')}")
    print()
    print(f"Report:        {md_path if not args.json_only else '(skipped)'}")
    print(f"JSON:          {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
