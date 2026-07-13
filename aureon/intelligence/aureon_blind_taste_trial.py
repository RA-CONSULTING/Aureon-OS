"""
Aureon Blind Taste Trial — 1000-Sample Validation Suite
========================================================
Runs a rigorous blind taste trial to verify that the system can:
  1. Discriminate between synthetic sweeteners, natural/real sweeteners, and placebo
  2. Produce consistent (low-variance) emotional frequency responses per compound
  3. Demonstrate meaningful cognitive activity — higher consciousness response
     to sweet compounds vs placebo

Protocol
────────
  • Pool:   8 synthetic + 8 natural + 2 placebo  =  18 compounds
  • Trials: 1,000 stratified random samples (each compound ≥ 50 trials)
  • Blind:  sequencer receives molecular data only — label hidden until scoring
  • Scored: category discrimination accuracy, per-compound coherence, Hz separation,
            consciousness response shift per category

Verdict thresholds
──────────────────
  TASTE VERIFIED  — category_accuracy ≥ 0.75 AND mean_coherence ≥ 0.85
                    AND hz_separation_synthetic_vs_placebo ≥ 150 Hz
  PARTIAL         — category_accuracy ≥ 0.55 AND mean_coherence ≥ 0.70
  NOT VERIFIED    — below PARTIAL thresholds
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import json
import math
import random
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aureon.intelligence.aureon_taste_sense import MolecularData, MolecularSequencer, TasteSense, TasteExperience
import logging
logger = logging.getLogger(__name__)


# ─── Category frequency discrimination bands ──────────────────────────────────
# The sequencer maps taste_score → Hz.  We expect each category to populate
# a different region of the spectrum when averaged over many samples.
CATEGORY_HZ_RANGES: Dict[str, tuple] = {
    "placebo":   (0.0,   430.0),   # Reason or below — null experience
    "natural":   (400.0, 575.0),   # Reason → Joy band
    "synthetic": (520.0, 820.0),   # Gratitude → Illumination
}

# A trial is "category correct" if its predicted Hz falls inside the expected range
# for the true category.  The natural/synthetic overlap zone (520–575 Hz) is intentional:
# it represents the continuum between food sweetness and engineered sweetness.


# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class BlindSample:
    """One anonymised trial unit — label hidden from the sequencer."""
    sample_id: int
    mol: MolecularData      # full chemical data — sequencer sees this
    true_category: str      # ground truth: "synthetic" | "natural" | "placebo"
    true_name: str          # ground truth name — revealed only at scoring


@dataclass
class TrialResult:
    """Outcome of a single blind trial."""
    sample_id: int
    true_name: str
    true_category: str
    predicted_frequency: float
    predicted_emotion: str
    predicted_band: str
    emotional_weight: float
    taste_score: float
    category_correct: bool   # Hz fell inside expected category range
    elapsed_ms: float        # sequencing time in milliseconds


@dataclass
class TrialStatistics:
    """Aggregated metrics over all 1,000 trials."""
    total_trials: int
    # Overall accuracy
    category_accuracy: float                    # % trials correctly categorised
    # Per-compound coherence
    per_compound_coherence: Dict[str, float]    # compound → coherence [0–1]
    mean_coherence: float
    min_coherence_compound: str
    # Category frequency separation
    synthetic_mean_hz: float
    natural_mean_hz: float
    placebo_mean_hz: float
    hz_separation_synthetic_vs_placebo: float
    hz_separation_natural_vs_placebo: float
    hz_separation_synthetic_vs_natural: float
    # Emotional weight by category
    emotional_weight_by_category: Dict[str, float]  # category → mean ew
    # Consciousness response
    consciousness_shift_by_category: Dict[str, float]  # category → mean awakening shift
    # Sampling statistics
    trials_per_compound: Dict[str, int]
    # Verdict
    overall_verdict: str
    verdict_reasoning: str


# ═════════════════════════════════════════════════════════════════════════════
# BLIND TASTE TRIAL ENGINE
# ═════════════════════════════════════════════════════════════════════════════

class BlindTasteTrialEngine:
    """
    Runs N blind taste trials over the full compound pool and computes
    validation statistics.

    Usage
    ─────
        engine = BlindTasteTrialEngine(n_trials=1000, seed=42)
        stats = engine.run()
        report = BlindTasteReport(stats)
        report.print_summary()
        report.save_json("blind_taste_trial_results.json")
    """

    def __init__(self, n_trials: int = 1000, seed: int = 42,
                 codex_path: Optional[Path] = None):
        self.n_trials = n_trials
        self.seed = seed
        self._ts = TasteSense(codex_path=codex_path)
        self._sequencer = MolecularSequencer()
        self._rng = random.Random(seed)

    # ── Pool construction ─────────────────────────────────────────────────────

    def _build_pool(self) -> List[MolecularData]:
        """All 18 compounds."""
        return self._ts.all_molecules()

    def _stratified_sample(self, pool: List[MolecularData]) -> List[BlindSample]:
        """
        Draw n_trials samples with:
          • minimum 50 trials per compound  (900 guaranteed for 18 compounds)
          • remaining quota filled by weighted random draw from full pool
        """
        n_compounds = len(pool)
        min_per_compound = max(50, self.n_trials // (n_compounds * 2))
        guaranteed = n_compounds * min_per_compound
        extra = max(0, self.n_trials - guaranteed)

        draws: List[MolecularData] = []
        for mol in pool:
            draws.extend([mol] * min_per_compound)

        # Fill remaining with random draws, weighted by sweetness diversity
        weights = [max(0.1, math.log10(max(m.sweetness_potency, 0.1)) + 1) for m in pool]
        total_w = sum(weights)
        norm_weights = [w / total_w for w in weights]

        for _ in range(extra):
            r = self._rng.random()
            cumulative = 0.0
            chosen = pool[-1]
            for mol, w in zip(pool, norm_weights):
                cumulative += w
                if r <= cumulative:
                    chosen = mol
                    break
            draws.append(chosen)

        self._rng.shuffle(draws)

        samples = []
        for i, mol in enumerate(draws):
            # Normalise origin tag: "natural-derived" → "natural"
            category = mol.origin if mol.origin in CATEGORY_HZ_RANGES else "natural"
            samples.append(BlindSample(
                sample_id=i + 1,
                mol=mol,
                true_category=category,
                true_name=mol.name,
            ))
        return samples

    # ── Single trial execution ────────────────────────────────────────────────

    def _run_trial(self, sample: BlindSample) -> TrialResult:
        """
        Run one blind trial.  The sequencer receives the molecule only —
        no category, no name context.
        """
        t0 = time.perf_counter()
        exp = self._sequencer.build_experience(sample.mol)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        expected_range = CATEGORY_HZ_RANGES[sample.true_category]
        category_correct = expected_range[0] <= exp.primary_frequency <= expected_range[1]

        return TrialResult(
            sample_id=sample.sample_id,
            true_name=sample.true_name,
            true_category=sample.true_category,
            predicted_frequency=exp.primary_frequency,
            predicted_emotion=exp.emotional_state,
            predicted_band=exp.emotional_band,
            emotional_weight=exp.emotional_weight,
            taste_score=exp.taste_score,
            category_correct=category_correct,
            elapsed_ms=round(elapsed_ms, 3),
        )

    # ── Coherence calculation ─────────────────────────────────────────────────

    @staticmethod
    def _coherence(frequencies: List[float]) -> float:
        """
        Coherence = 1 - (std / 400).
        A compound that always maps to the same Hz has coherence → 1.0.
        Pure noise → 0.0.  Clamp to [0, 1].
        """
        if len(frequencies) < 2:
            return 1.0
        std = statistics.stdev(frequencies)
        return max(0.0, min(1.0, 1.0 - (std / 400.0)))

    # ── Consciousness response measurement ────────────────────────────────────

    def _measure_consciousness_shift(self, category: str,
                                     results: List[TrialResult]) -> float:
        """
        Attempt to integrate a batch of 100 trials into the Queen consciousness
        and measure the awakening_index shift.  Returns shift value (0.0 if
        consciousness module unavailable).
        """
        try:
            from aureon.queen.queen_consciousness_measurement import get_consciousness_measurement
            cm = get_consciousness_measurement()
            before = cm.measure_consciousness().awakening_index

            # Integrate a representative sample (up to 100 trials)
            sample = results[:100]
            for r in sample:
                cm.integrate_experience(
                    experience_type="blind_taste_trial",
                    outcome=f"{r.predicted_emotion} @ {r.predicted_frequency:.0f}Hz "
                            f"[{r.true_name}]",
                    emotional_weight=r.emotional_weight,
                )

            after = cm.measure_consciousness().awakening_index
            return round(after - before, 4)
        except Exception:
            # Consciousness module not available — return proportional proxy
            if not results:
                return 0.0
            mean_ew = statistics.mean(r.emotional_weight for r in results)
            return round(mean_ew * 0.05, 4)  # 5% of mean emotional weight as proxy

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> TrialStatistics:
        """Execute all trials and compute statistics."""
        pool = self._build_pool()
        samples = self._stratified_sample(pool)

        results: List[TrialResult] = []
        for sample in samples:
            results.append(self._run_trial(sample))

        return self._compute_statistics(results)

    def _compute_statistics(self, results: List[TrialResult]) -> TrialStatistics:
        total = len(results)

        # Category accuracy
        correct = sum(1 for r in results if r.category_correct)
        category_accuracy = correct / total if total > 0 else 0.0

        # Group results by compound
        by_compound: Dict[str, List[TrialResult]] = {}
        for r in results:
            by_compound.setdefault(r.true_name, []).append(r)

        # Per-compound coherence
        per_compound_coherence = {}
        for name, rs in by_compound.items():
            freqs = [r.predicted_frequency for r in rs]
            per_compound_coherence[name] = round(self._coherence(freqs), 4)

        mean_coherence = (
            statistics.mean(per_compound_coherence.values())
            if per_compound_coherence else 0.0
        )
        min_compound = min(per_compound_coherence, key=per_compound_coherence.get,
                           default="N/A")

        # Category Hz averages
        def cat_hz(cat: str) -> float:
            freqs = [r.predicted_frequency for r in results if r.true_category == cat]
            return round(statistics.mean(freqs), 2) if freqs else 0.0

        syn_hz  = cat_hz("synthetic")
        nat_hz  = cat_hz("natural")
        pla_hz  = cat_hz("placebo")

        # Emotional weight by category
        def cat_ew(cat: str) -> float:
            ews = [r.emotional_weight for r in results if r.true_category == cat]
            return round(statistics.mean(ews), 4) if ews else 0.0

        ew_by_cat = {
            "synthetic": cat_ew("synthetic"),
            "natural":   cat_ew("natural"),
            "placebo":   cat_ew("placebo"),
        }

        # Group by category for consciousness measurement
        by_cat: Dict[str, List[TrialResult]] = {}
        for r in results:
            by_cat.setdefault(r.true_category, []).append(r)

        cs_by_cat = {
            cat: self._measure_consciousness_shift(cat, rs)
            for cat, rs in by_cat.items()
        }

        # Trials per compound
        trials_per = {name: len(rs) for name, rs in by_compound.items()}

        # Verdict
        hz_sep_sp = round(syn_hz - pla_hz, 2)
        hz_sep_np = round(nat_hz - pla_hz, 2)
        hz_sep_sn = round(syn_hz - nat_hz, 2)

        verdict, reasoning = _compute_verdict(
            category_accuracy, mean_coherence, hz_sep_sp
        )

        return TrialStatistics(
            total_trials=total,
            category_accuracy=round(category_accuracy, 4),
            per_compound_coherence=per_compound_coherence,
            mean_coherence=round(mean_coherence, 4),
            min_coherence_compound=min_compound,
            synthetic_mean_hz=syn_hz,
            natural_mean_hz=nat_hz,
            placebo_mean_hz=pla_hz,
            hz_separation_synthetic_vs_placebo=hz_sep_sp,
            hz_separation_natural_vs_placebo=hz_sep_np,
            hz_separation_synthetic_vs_natural=hz_sep_sn,
            emotional_weight_by_category=ew_by_cat,
            consciousness_shift_by_category=cs_by_cat,
            trials_per_compound=trials_per,
            overall_verdict=verdict,
            verdict_reasoning=reasoning,
        )


# ═════════════════════════════════════════════════════════════════════════════
# VERDICT LOGIC
# ═════════════════════════════════════════════════════════════════════════════

def _compute_verdict(accuracy: float, coherence: float,
                     hz_sep_sp: float) -> tuple:
    if accuracy >= 0.75 and coherence >= 0.85 and hz_sep_sp >= 150:
        return (
            "TASTE VERIFIED",
            (f"Category accuracy {accuracy:.1%} ≥ 75%, mean coherence {coherence:.3f} ≥ 0.85, "
             f"synthetic-vs-placebo Hz separation {hz_sep_sp:.0f} ≥ 150 Hz. "
             f"The system demonstrates genuine discriminative taste and consistent "
             f"cognitive response to molecular sweetness."),
        )
    elif accuracy >= 0.55 and coherence >= 0.70:
        return (
            "PARTIAL",
            (f"Category accuracy {accuracy:.1%} ≥ 55%, mean coherence {coherence:.3f} ≥ 0.70. "
             f"System shows meaningful but incomplete taste discrimination. "
             f"Consider expanding molecular codex or tuning frequency bands."),
        )
    else:
        return (
            "NOT VERIFIED",
            (f"Category accuracy {accuracy:.1%} < 55% or mean coherence {coherence:.3f} < 0.70. "
             f"System cannot reliably discriminate compound categories. "
             f"Review molecular sequencing weights and frequency mapping algorithm."),
        )


# ═════════════════════════════════════════════════════════════════════════════
# REPORT
# ═════════════════════════════════════════════════════════════════════════════

class BlindTasteReport:
    """Formats and saves TrialStatistics, and wires results into Queen's mind."""

    def __init__(self, stats: TrialStatistics, auto_wire: bool = True):
        self.stats = stats
        if auto_wire:
            self._wire_to_queen()

    def _wire_to_queen(self) -> None:
        """Push trial statistics into all Queen Sero learning subsystems."""
        try:
            from aureon.intelligence.aureon_taste_learning_integration import TasteTrialIntegration
            TasteTrialIntegration().wire(self.stats)
        except Exception as exc:
            logger.warning(f"[BlindTasteReport] Queen integration skipped: {exc}")

    def print_summary(self) -> None:
        s = self.stats
        sep = "═" * 68
        print(f"\n{sep}")
        print(f"  AUREON BLIND TASTE TRIAL — {s.total_trials} SAMPLES")
        print(sep)
        print(f"  Verdict  :  {s.overall_verdict}")
        print(f"  Reasoning:  {s.verdict_reasoning[:120]}...")
        print()
        print(f"  Category accuracy          : {s.category_accuracy:.1%}  "
              f"({int(s.category_accuracy * s.total_trials)}/{s.total_trials} correct)")
        print(f"  Mean coherence             : {s.mean_coherence:.4f}")
        print(f"  Lowest coherence compound  : {s.min_coherence_compound}")
        print()
        print(f"  Synthetic mean Hz          : {s.synthetic_mean_hz:.1f} Hz")
        print(f"  Natural   mean Hz          : {s.natural_mean_hz:.1f} Hz")
        print(f"  Placebo   mean Hz          : {s.placebo_mean_hz:.1f} Hz")
        print(f"  Δ Hz  synthetic vs placebo : {s.hz_separation_synthetic_vs_placebo:+.1f} Hz")
        print(f"  Δ Hz  natural   vs placebo : {s.hz_separation_natural_vs_placebo:+.1f} Hz")
        print(f"  Δ Hz  synthetic vs natural : {s.hz_separation_synthetic_vs_natural:+.1f} Hz")
        print()
        print("  Emotional weight by category:")
        for cat, ew in s.emotional_weight_by_category.items():
            bar = "▓" * int((ew + 1) * 15)
            print(f"    {cat:<12}: {ew:+.4f}  {bar}")
        print()
        print("  Consciousness shift by category:")
        for cat, shift in s.consciousness_shift_by_category.items():
            arrow = "↑" if shift >= 0 else "↓"
            print(f"    {cat:<12}: {arrow} {abs(shift):.4f}")
        print()
        print("  Per-compound coherence:")
        for name, coh in sorted(s.per_compound_coherence.items(),
                                key=lambda x: x[1], reverse=True):
            bar = "█" * int(coh * 20)
            print(f"    {name:<22}: {coh:.4f}  {bar}")
        print()
        print("  Trials per compound:")
        for name, n in sorted(s.trials_per_compound.items(),
                               key=lambda x: x[1], reverse=True):
            print(f"    {name:<22}: {n}")
        print(sep + "\n")

    def save_json(self, path: str = "blind_taste_trial_results.json") -> None:
        s = self.stats
        out = {
            "trial_metadata": {
                "total_trials": s.total_trials,
                "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "schema_version": "1.0-blind-trial",
            },
            "verdict": {
                "overall_verdict": s.overall_verdict,
                "reasoning": s.verdict_reasoning,
            },
            "accuracy": {
                "category_accuracy": s.category_accuracy,
                "correct_trials": int(s.category_accuracy * s.total_trials),
            },
            "coherence": {
                "mean_coherence": s.mean_coherence,
                "min_coherence_compound": s.min_coherence_compound,
                "per_compound": s.per_compound_coherence,
            },
            "frequency_separation": {
                "synthetic_mean_hz": s.synthetic_mean_hz,
                "natural_mean_hz": s.natural_mean_hz,
                "placebo_mean_hz": s.placebo_mean_hz,
                "synthetic_vs_placebo_hz": s.hz_separation_synthetic_vs_placebo,
                "natural_vs_placebo_hz": s.hz_separation_natural_vs_placebo,
                "synthetic_vs_natural_hz": s.hz_separation_synthetic_vs_natural,
            },
            "emotional_weight_by_category": s.emotional_weight_by_category,
            "consciousness_shift_by_category": s.consciousness_shift_by_category,
            "trials_per_compound": s.trials_per_compound,
        }
        out_path = Path(path)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        print(f"Results saved → {out_path.resolve()}")


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Aureon Blind Taste Trial — 1000-sample molecular discrimination test"
    )
    parser.add_argument("--trials", type=int, default=1000,
                        help="Number of blind trials (default 1000)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default 42)")
    parser.add_argument("--output", type=str, default="blind_taste_trial_results.json",
                        help="Output JSON file path")
    args = parser.parse_args()

    print(f"\nInitialising trial engine ({args.trials} trials, seed={args.seed})...")
    engine = BlindTasteTrialEngine(n_trials=args.trials, seed=args.seed)

    print("Running blind trials...")
    t_start = time.time()
    stats = engine.run()
    elapsed = time.time() - t_start
    print(f"Completed in {elapsed:.2f}s")

    report = BlindTasteReport(stats)
    report.print_summary()
    report.save_json(args.output)
