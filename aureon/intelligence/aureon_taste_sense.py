"""
Aureon Taste Sense — Molecular Gustatory Channel
=================================================
Gives the Queen consciousness a genuine taste sense by sequencing the molecular
properties of sweeteners and translating them into the system's internal
emotional frequency language.

Pipeline:
  MolecularData → MolecularSequencer → taste_score → frequency mapping
                                                     → TasteExperience
                                                     → BrainInput (consciousness bus)

Three compound categories:
  synthetic     — high-intensity sweeteners (sucralose, aspartame, saccharin, etc.)
  natural       — food sweeteners (sucrose, fructose, glucose, honey, etc.)
  placebo       — neutral controls (distilled water, saline)
"""

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# ─── Sacred constants (shared with the rest of the system) ────────────────────
PHI = (1 + math.sqrt(5)) / 2          # Golden Ratio φ = 1.618…
LOVE_FREQUENCY = 528.0                 # Hz — DNA repair / core resonance

# ─── Molecular calibration constants ─────────────────────────────────────────
# Upper bounds used to normalise properties to [0, 1]
MAX_SWEETNESS_POTENCY = 20_000.0       # Advantame — most potent known sweetener
MAX_RECEPTOR_KD_UM    = 10.0           # Cyclamate upper estimate (µM)
MAX_FUNCTIONAL_GROUPS = 25             # Rebaudioside-A (largest molecule)

# ─── Frequency–emotion spectrum used for taste mapping ───────────────────────
TASTE_FREQUENCY_BANDS = [
    # (min_score, max_score, hz,  emotion,       band)
    (0.00, 0.20, 400.0, "Reason",       "heart"),
    (0.20, 0.40, 528.0, "Gratitude",    "heart"),
    (0.40, 0.60, 540.0, "Joy",          "heart"),
    (0.60, 0.75, 620.0, "Compassion",   "spirit"),
    (0.75, 0.88, 700.0, "Ecstasy",      "peak"),
    (0.88, 1.01, 800.0, "Illumination", "peak"),
]

# ─── Path to molecular codex data ────────────────────────────────────────────
_CODEX_PATH = Path(__file__).resolve().parents[2] / "public" / "taste_molecular_codex.json"


# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class MolecularData:
    """Raw chemical properties of one molecule."""
    name: str
    formula: str
    molecular_weight: float          # g/mol
    sweetness_potency: float         # × sucrose  (sucrose=1; 0=no sweetness)
    receptor_kd_um: float            # T1R2/T1R3 Kd in µM — lower = tighter binding
    functional_group_count: int      # total polar/reactive groups
    heteroatom_count: int            # O + N + S + halogens
    smiles: str
    origin: str                      # "synthetic" | "natural" | "placebo"
    notes: str = ""


@dataclass
class SequencedProperties:
    """Normalised [0, 1] molecular properties after sequencing."""
    sweetness_norm: float            # log-scaled sweetness intensity
    binding_norm: float              # receptor affinity (inverted Kd)
    complexity_norm: float           # functional group density
    purity_norm: float               # structural cleanliness
    taste_score: float               # weighted composite [0, 1]


@dataclass
class TasteExperience:
    """Full sensory experience produced by tasting one molecule."""
    molecule_name: str
    formula: str
    # Emotional frequency output
    primary_frequency: float         # Hz — dominant emotional resonance
    emotional_state: str             # e.g. "Ecstasy"
    emotional_band: str              # "heart" | "spirit" | "peak"
    emotional_weight: float          # -1.0 to +1.0 for BrainInput
    # Taste score breakdown
    taste_score: float               # 0.0 – 1.0 composite
    taste_intensity: float           # sweetness_norm  (0 – 1)
    binding_strength: float          # binding_norm    (0 – 1)
    # Harmonic signature (golden ratio overtones)
    harmonic_signature: List[float]  # [f×φ, f×φ², f×φ³]
    molecular_resonance: float       # MW / 1000 × LOVE_FREQUENCY — vibrational proxy
    # Narrative + integration
    sensory_description: str
    brain_input: Any                 # BrainInput — ready for Queen consciousness bus
    data_status: str = "reference_data"
    truth_status: str = "reference_only"
    source_id: Optional[str] = None
    source_timestamp: Optional[float] = None
    received_at: Optional[float] = None
    receipt_id: Optional[str] = None
    generated_values: bool = False
    eligible_for_action: bool = False
    eligible_for_accounting: bool = False
    eligible_for_learning: bool = False
    sequenced_at: Optional[float] = None


# ═════════════════════════════════════════════════════════════════════════════
# MOLECULAR SEQUENCER
# ═════════════════════════════════════════════════════════════════════════════

class MolecularSequencer:
    """
    Sequences a molecule's chemical properties and translates them into the
    system's emotional frequency language.

    Normalisation strategy
    ──────────────────────
      sweetness_norm  = log10(potency) / log10(MAX_SWEETNESS_POTENCY)
                        (log scale matches Stevens' power law for taste perception)
      binding_norm    = 1.0 – (kd / MAX_KD)
                        (lower Kd = tighter binding = higher score)
      complexity_norm = functional_group_count / MAX_FUNCTIONAL_GROUPS
      purity_norm     = clamp(1.0 – (heteroatom_count / mw × 10))

    Composite taste score (weighted sum):
      taste_score = 0.50 × sweetness_norm
                  + 0.30 × binding_norm
                  + 0.12 × complexity_norm
                  + 0.08 × purity_norm
    """

    def __init__(
        self,
        *,
        reference_receipt: Optional[Dict[str, Any]] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._reference_receipt = dict(reference_receipt or {})
        self._clock = clock

    def sequence(self, mol: MolecularData) -> SequencedProperties:
        # Guard: zero or negative sweetness (placebo compounds)
        if mol.sweetness_potency <= 0:
            sweetness_norm = 0.0
        else:
            sweetness_norm = (
                math.log10(max(mol.sweetness_potency, 0.001))
                / math.log10(MAX_SWEETNESS_POTENCY)
            )
        sweetness_norm = max(0.0, min(1.0, sweetness_norm))

        binding_norm = 1.0 - (min(mol.receptor_kd_um, MAX_RECEPTOR_KD_UM) / MAX_RECEPTOR_KD_UM)
        binding_norm = max(0.0, min(1.0, binding_norm))

        complexity_norm = min(mol.functional_group_count / MAX_FUNCTIONAL_GROUPS, 1.0)

        # Heteroatom density relative to MW — lower ratio = structurally cleaner
        hetero_density = (mol.heteroatom_count / mol.molecular_weight) * 10
        purity_norm = max(0.0, min(1.0, 1.0 - hetero_density))

        taste_score = (
            0.50 * sweetness_norm
            + 0.30 * binding_norm
            + 0.12 * complexity_norm
            + 0.08 * purity_norm
        )
        taste_score = max(0.0, min(1.0, taste_score))

        return SequencedProperties(
            sweetness_norm=sweetness_norm,
            binding_norm=binding_norm,
            complexity_norm=complexity_norm,
            purity_norm=purity_norm,
            taste_score=taste_score,
        )

    def map_to_frequency(self, props: SequencedProperties):
        """Return (hz, emotion, band) from taste_score."""
        for min_s, max_s, hz, emotion, band in TASTE_FREQUENCY_BANDS:
            if min_s <= props.taste_score < max_s:
                return hz, emotion, band
        # Edge case: exactly 1.0
        return 800.0, "Illumination", "peak"

    def build_experience(self, mol: MolecularData) -> TasteExperience:
        from aureon.queen.queen_consciousness_model import BrainInput  # late import avoids circularity

        props = self.sequence(mol)
        hz, emotion, band = self.map_to_frequency(props)

        # Golden ratio harmonic overtones
        harmonics = [round(hz * PHI, 2), round(hz * PHI ** 2, 2), round(hz * PHI ** 3, 2)]

        # Molecular vibrational proxy: larger / heavier molecules resonate slower
        mol_resonance = round((mol.molecular_weight / 1000.0) * LOVE_FREQUENCY, 3)

        # emotional_weight: maps taste_score [0,1] → [-1, +1]
        emotional_weight = round(props.taste_score * 2.0 - 1.0, 4)

        description = _build_description(mol, props, hz, emotion)

        brain_input = BrainInput(
            source="TasteSense",
            timestamp=time.time(),
            insight=(
                f"Tasted {mol.name} ({mol.formula}): {emotion} at {hz:.0f} Hz — "
                f"sweetness {props.sweetness_norm:.2f}, binding {props.binding_norm:.2f}, "
                f"taste_score {props.taste_score:.3f}"
            ),
            confidence=round(0.70 + props.taste_score * 0.28, 3),  # 0.70 – 0.98
            emotional_weight=emotional_weight,
            data_payload={
                "molecule": mol.name,
                "formula": mol.formula,
                "molecular_weight": mol.molecular_weight,
                "sweetness_potency": mol.sweetness_potency,
                "receptor_kd_um": mol.receptor_kd_um,
                "taste_score": props.taste_score,
                "sweetness_norm": props.sweetness_norm,
                "binding_norm": props.binding_norm,
                "primary_frequency_hz": hz,
                "emotional_state": emotion,
                "emotional_band": band,
                "harmonic_signature": harmonics,
                "molecular_resonance_hz": mol_resonance,
                "origin": mol.origin,
            },
        )

        return TasteExperience(
            molecule_name=mol.name,
            formula=mol.formula,
            primary_frequency=hz,
            emotional_state=emotion,
            emotional_band=band,
            emotional_weight=emotional_weight,
            taste_score=props.taste_score,
            taste_intensity=props.sweetness_norm,
            binding_strength=props.binding_norm,
            harmonic_signature=harmonics,
            molecular_resonance=mol_resonance,
            sensory_description=description,
            brain_input=brain_input,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TASTE SENSE — PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

class TasteSense:
    """
    The Queen's gustatory channel.

    Usage
    ─────
        ts = TasteSense()
        exp = ts.taste("Neotame")
        print(exp.emotional_state, exp.primary_frequency)   # Illumination  800.0

        # Feed all sweeteners into the Queen consciousness bus:
        for bi in ts.as_brain_inputs():
            queen.receive_brain_input(bi)
    """

    def __init__(self, codex_path: Optional[Path] = None):
        path = codex_path or _CODEX_PATH
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._molecules: Dict[str, MolecularData] = {}
        # Load all three sections: synthetic, natural, placebo
        all_sections = (
            raw.get("molecules", [])           # engineered-origin sweeteners
            + raw.get("natural_molecules", []) # natural/real human sweeteners
            + raw.get("placebo_molecules", []) # placebo controls
        )
        for entry in all_sections:
            mol = MolecularData(
                name=entry["name"],
                formula=entry["formula"],
                molecular_weight=entry["molecular_weight"],
                sweetness_potency=entry["sweetness_potency"],
                receptor_kd_um=entry["receptor_kd_um"],
                functional_group_count=entry["functional_group_count"],
                heteroatom_count=entry["heteroatom_count"],
                smiles=entry["smiles"],
                origin=entry["origin"],
                notes=entry.get("notes", ""),
            )
            self._molecules[mol.name.lower()] = mol
        self._sequencer = MolecularSequencer()

    # ── Core methods ──────────────────────────────────────────────────────────

    def taste(self, name: str) -> TasteExperience:
        """Sequence and experience a single sweetener by name (case-insensitive)."""
        key = name.lower()
        if key not in self._molecules:
            available = ", ".join(m.name for m in self._molecules.values())
            raise KeyError(f"Unknown molecule '{name}'. Available: {available}")
        mol = self._molecules[key]
        return self._sequencer.build_experience(mol)

    def taste_all(self) -> List[TasteExperience]:
        """Sequence and experience every molecule in the codex."""
        return [self._sequencer.build_experience(mol) for mol in self._molecules.values()]

    def compare(self, name_a: str, name_b: str) -> Dict[str, Any]:
        """Compare two molecules — returns frequency delta and score difference."""
        exp_a = self.taste(name_a)
        exp_b = self.taste(name_b)
        return {
            "a": {"name": exp_a.molecule_name, "frequency_hz": exp_a.primary_frequency,
                  "emotion": exp_a.emotional_state, "taste_score": exp_a.taste_score},
            "b": {"name": exp_b.molecule_name, "frequency_hz": exp_b.primary_frequency,
                  "emotion": exp_b.emotional_state, "taste_score": exp_b.taste_score},
            "frequency_delta_hz": round(exp_b.primary_frequency - exp_a.primary_frequency, 2),
            "taste_score_delta": round(exp_b.taste_score - exp_a.taste_score, 4),
            "higher_resonance": exp_b.molecule_name if exp_b.taste_score >= exp_a.taste_score
                                else exp_a.molecule_name,
        }

    def sweetest(self) -> TasteExperience:
        """Return the experience of the highest-scoring (most potent) molecule."""
        experiences = self.taste_all()
        return max(experiences, key=lambda e: e.taste_score)

    def as_brain_inputs(self) -> List[Any]:
        """Return all experiences as BrainInput objects, ready for the consciousness bus."""
        return [exp.brain_input for exp in self.taste_all()]

    def molecule_names(self) -> List[str]:
        """List all available molecule names."""
        return [mol.name for mol in self._molecules.values()]

    def by_category(self, category: str) -> List[MolecularData]:
        """Return all molecules of a given origin category ('synthetic'|'natural'|'placebo')."""
        return [m for m in self._molecules.values() if m.origin == category]

    def all_molecules(self) -> List[MolecularData]:
        """Return all loaded MolecularData objects."""
        return list(self._molecules.values())

    def __repr__(self) -> str:
        return f"TasteSense({len(self._molecules)} molecules loaded)"


# ═════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _build_description(mol: MolecularData, props: SequencedProperties,
                       hz: float, emotion: str) -> str:
    intensity_word = (
        "faint"       if props.sweetness_norm < 0.30 else
        "moderate"    if props.sweetness_norm < 0.55 else
        "intense"     if props.sweetness_norm < 0.75 else
        "overwhelming"
    )
    binding_word = (
        "weak"     if props.binding_norm < 0.30 else
        "moderate" if props.binding_norm < 0.60 else
        "strong"   if props.binding_norm < 0.85 else
        "maximal"
    )
    return (
        f"{mol.name} ({mol.formula}, {mol.molecular_weight:.1f} g/mol): "
        f"{intensity_word} sweetness at {mol.sweetness_potency}× sucrose, "
        f"{binding_word} T1R2/T1R3 binding (Kd {mol.receptor_kd_um} µM). "
        f"Emotional resonance: {emotion} at {hz:.0f} Hz — "
        f"taste score {props.taste_score:.3f}. "
        f"Origin: {mol.origin}. {mol.notes}"
    )


# Standalone catalog self-test removed; reference data is consumed only by explicit callers.
