"""Reference harmonic transforms for AGPHA.

There are deliberately separate lanes:

* spectral peaks -> physical frequency -> octave-folded modulation tone;
* computed normal modes -> the same physical-frequency transform, but labelled computed;
* protein sequences -> a deterministic DFT signature over residue-property channels.

The sequence lane is a mathematical fingerprint only.  It is useful for indexing,
nearest-neighbour search, and prioritising expensive structural calculations; it is
not a claim that a protein physically oscillates at the emitted modulation tones.
"""

from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Final, Iterable, Mapping, Sequence

from .models import (
    AdjacentBand,
    EvidenceRef,
    EvidenceState,
    HarmonicComponent,
    HarmonicLane,
    HarmonicMapping,
    SpectralPeak,
)

PHI: Final[float] = 1.618033988749895
PHI_INV_9: Final[float] = PHI ** -9
CM1_TO_THZ: Final[float] = 0.0299792458
NM_TO_THZ_NUMERATOR: Final[float] = 299_792.458
THZ_TO_HZ: Final[float] = 1.0e12
TARGET_BAND_HZ: Final[tuple[float, float]] = (1000.0, 2000.0)
OCTAVE_SEARCH_RANGE: Final[tuple[int, int]] = (20, 60)
NARROW_DELTA: Final[float] = 0.01

# Kyte-Doolittle hydropathy, average residue mass, and a simple nominal side-chain
# charge at near-neutral pH.  These are input channels to a mathematical sequence
# signature, not a molecular-dynamics force field.
_HYDROPATHY: Final[Mapping[str, float]] = {
    "A": 1.8, "C": 2.5, "D": -3.5, "E": -3.5, "F": 2.8,
    "G": -0.4, "H": -3.2, "I": 4.5, "K": -3.9, "L": 3.8,
    "M": 1.9, "N": -3.5, "P": -1.6, "Q": -3.5, "R": -4.5,
    "S": -0.8, "T": -0.7, "V": 4.2, "W": -0.9, "Y": -1.3,
    "X": 0.0,
}
_RESIDUE_MASS: Final[Mapping[str, float]] = {
    "A": 71.0788, "C": 103.1388, "D": 115.0886, "E": 129.1155, "F": 147.1766,
    "G": 57.0519, "H": 137.1411, "I": 113.1594, "K": 128.1741, "L": 113.1594,
    "M": 131.1926, "N": 114.1038, "P": 97.1167, "Q": 128.1307, "R": 156.1875,
    "S": 87.0782, "T": 101.1051, "V": 99.1326, "W": 186.2132, "Y": 163.1760,
    "X": 111.0,
}
_CHARGE: Final[Mapping[str, float]] = {
    **{aa: 0.0 for aa in _HYDROPATHY},
    "D": -1.0,
    "E": -1.0,
    "K": 1.0,
    "R": 1.0,
    "H": 0.1,
}
_SEQUENCE_CHANNELS: Final[Mapping[str, Mapping[str, float]]] = {
    "hydropathy": _HYDROPATHY,
    "residue_mass": _RESIDUE_MASS,
    "nominal_charge": _CHARGE,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_digest(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(text.encode("utf-8"))


def adjacent_bands(
    center_hz: float,
    *,
    narrow_delta: float = NARROW_DELTA,
    geometric_delta: float = PHI_INV_9,
) -> tuple[AdjacentBand, ...]:
    """Return the packet's narrow and phi^-9 adjacent sidebands."""

    if not math.isfinite(center_hz) or center_hz <= 0:
        raise ValueError("center_hz must be finite and positive")
    bands = (
        AdjacentBand(
            label="narrow_pm_1_percent",
            lower_hz=center_hz * (1.0 - narrow_delta),
            center_hz=center_hz,
            upper_hz=center_hz * (1.0 + narrow_delta),
            delta_fraction=narrow_delta,
        ),
        AdjacentBand(
            label="geometric_pm_phi_inv_9",
            lower_hz=center_hz * (1.0 - geometric_delta),
            center_hz=center_hz,
            upper_hz=center_hz * (1.0 + geometric_delta),
            delta_fraction=geometric_delta,
        ),
    )
    for band in bands:
        errors = band.validate()
        if errors:
            raise ValueError("invalid adjacent band: " + "; ".join(errors))
    return bands


def physical_frequency_hz(value: float, unit: str) -> float:
    """Convert a measured or computed spectral coordinate to physical hertz."""

    if not math.isfinite(value) or value <= 0:
        raise ValueError("spectral value must be finite and positive")
    if unit == "cm^-1":
        return value * CM1_TO_THZ * THZ_TO_HZ
    if unit == "nm":
        return (NM_TO_THZ_NUMERATOR / value) * THZ_TO_HZ
    if unit == "THz":
        return value * THZ_TO_HZ
    if unit == "Hz":
        return value
    raise ValueError(f"unsupported spectral unit {unit!r}")


def select_octaves(
    frequency_hz: float,
    *,
    target_band_hz: tuple[float, float] = TARGET_BAND_HZ,
    search_range: tuple[int, int] = OCTAVE_SEARCH_RANGE,
) -> int:
    """Choose the octave divisor nearest the geometric centre of the target band.

    This mirrors the existing ``phenolic_fingerprint.py`` / HNC biomolecule packet
    selection rule so an existing spectral peak maps to the same modulation tone.
    """

    if not math.isfinite(frequency_hz) or frequency_hz <= 0:
        raise ValueError("frequency_hz must be finite and positive")
    low, high = target_band_hz
    if not 0 < low < high:
        raise ValueError("target band must satisfy 0 < low < high")
    start, stop = search_range
    if start < 0 or stop < start:
        raise ValueError("invalid octave search range")
    centre = math.sqrt(low * high)
    best_n = start
    best_score = float("inf")
    for n in range(start, stop + 1):
        folded = frequency_hz / (2**n)
        if low <= folded <= high:
            score = abs(math.log(folded / centre))
        else:
            distance = min(abs(math.log(folded / low)), abs(math.log(folded / high)))
            score = 10.0 + distance
        if score < best_score:
            best_n = n
            best_score = score
    return best_n


def spectral_peak_to_mapping(
    peak: SpectralPeak,
    *,
    lane: HarmonicLane | None = None,
    algorithm_version: str = "agpha.spectral-octave.v1",
) -> HarmonicMapping:
    """Convert one spectral peak into an evidence-labelled harmonic mapping."""

    peak_errors = peak.validate()
    if peak_errors:
        raise ValueError("invalid spectral peak: " + "; ".join(peak_errors))

    inferred_lane = lane
    if inferred_lane is None:
        if peak.evidence.state == EvidenceState.MEASURED_DIRECT:
            inferred_lane = HarmonicLane.SPECTRAL_MEASURED
        elif peak.evidence.state == EvidenceState.COMPUTED:
            inferred_lane = HarmonicLane.SPECTRAL_COMPUTED
        else:
            raise ValueError(
                "spectral lane must be explicit unless evidence is measured_direct or computed"
            )
    if inferred_lane not in {
        HarmonicLane.SPECTRAL_MEASURED,
        HarmonicLane.SPECTRAL_COMPUTED,
        HarmonicLane.STRUCTURE_NORMAL_MODE,
    }:
        raise ValueError(f"lane {inferred_lane.value} is not a physical spectral lane")

    physical_hz = physical_frequency_hz(peak.value, peak.unit)
    octaves = select_octaves(physical_hz)
    tone_hz = physical_hz / (2**octaves)
    payload = {
        "peak_id": peak.peak_id,
        "subject_id": peak.subject_id,
        "value": peak.value,
        "unit": peak.unit,
        "method": peak.method,
        "source": peak.evidence.record_id,
        "lane": inferred_lane.value,
    }
    input_digest = _canonical_digest(payload)
    mapping = HarmonicMapping(
        mapping_id=f"agpha:harmonic:{input_digest[:20]}",
        subject_id=peak.subject_id,
        lane=inferred_lane,
        algorithm="physical-frequency octave folding",
        algorithm_version=algorithm_version,
        input_sha256=input_digest,
        evidence_state=peak.evidence.state,
        physical_interpretation=True,
        selected_octaves=octaves,
        components=(
            HarmonicComponent(
                tone_hz=tone_hz,
                source_coordinate=peak.value,
                source_unit=peak.unit,
                amplitude=(
                    float(peak.relative_intensity)
                    if isinstance(peak.relative_intensity, (int, float))
                    else None
                ),
                adjacent_bands=adjacent_bands(tone_hz),
            ),
        ),
        source_evidence=(peak.evidence,),
        notes=(
            "Physical frequency derived from a spectral coordinate, then octave-folded into the "
            "HNC modulation band. The folded tone does not itself establish biological efficacy."
        ),
    )
    errors = mapping.validate()
    if errors:
        raise ValueError("invalid spectral mapping: " + "; ".join(errors))
    return mapping


def normalise_protein_sequence(sequence: str) -> str:
    """Return an uppercase canonical sequence, allowing X for unknown residues."""

    normalised = "".join(sequence.split()).upper().replace("*", "")
    if len(normalised) < 7:
        raise ValueError("protein sequence must contain at least 7 residues")
    invalid = sorted(set(normalised) - set(_HYDROPATHY))
    if invalid:
        raise ValueError(f"protein sequence contains unsupported residues: {''.join(invalid)}")
    return normalised


def _centre(values: Sequence[float]) -> list[float]:
    mean = sum(values) / len(values)
    centred = [value - mean for value in values]
    energy = math.sqrt(sum(value * value for value in centred))
    if energy == 0:
        return [0.0 for _ in centred]
    return [value / energy for value in centred]


def _dft_modes(values: Sequence[float], max_modes: int) -> list[tuple[int, float, float]]:
    """Return ``(mode_index, power, phase)`` for the low-frequency DFT sketch."""

    n = len(values)
    stop = min(max_modes, n // 2)
    if stop < 1:
        return []
    centred = _centre(values)
    modes: list[tuple[int, float, float]] = []
    for k in range(1, stop + 1):
        coefficient = sum(
            value * cmath.exp(-2j * math.pi * k * index / n)
            for index, value in enumerate(centred)
        )
        power = float((coefficient.real**2 + coefficient.imag**2) / n)
        phase = float(cmath.phase(coefficient))
        modes.append((k, power, phase))
    total = sum(power for _, power, _ in modes)
    if total > 0:
        return [(k, power / total, phase) for k, power, phase in modes]
    return modes


def _mode_to_tone(mode_index: int, max_mode: int, target_band_hz: tuple[float, float]) -> float:
    low, high = target_band_hz
    fraction = mode_index / max_mode
    return low * ((high / low) ** fraction)


def protein_sequence_signature(
    subject_id: str,
    sequence: str,
    *,
    top_modes_per_channel: int = 4,
    max_dft_modes: int = 64,
    target_band_hz: tuple[float, float] = TARGET_BAND_HZ,
    evidence: Iterable[EvidenceRef] = (),
) -> HarmonicMapping:
    """Build a deterministic, explicitly non-physical protein harmonic signature.

    Each amino-acid sequence is projected into hydropathy, residue-mass, and nominal
    charge signals.  A low-frequency DFT sketch is computed for each channel; the
    strongest modes are mapped monotonically into the HNC display band.  The original
    mode coordinate (cycles per residue), power, phase, channel, and algorithm version
    remain attached, so no information is silently promoted to physical vibration.
    """

    if not subject_id.strip():
        raise ValueError("subject_id is required")
    if top_modes_per_channel <= 0 or max_dft_modes <= 0:
        raise ValueError("mode counts must be positive")
    low, high = target_band_hz
    if not 0 < low < high:
        raise ValueError("target band must satisfy 0 < low < high")

    normalised = normalise_protein_sequence(sequence)
    sequence_digest = sha256_bytes(normalised.encode("ascii"))
    components: list[HarmonicComponent] = []
    for channel_name, scale in _SEQUENCE_CHANNELS.items():
        values = [scale[residue] for residue in normalised]
        modes = _dft_modes(values, max_dft_modes)
        ranked = sorted(modes, key=lambda row: (-row[1], row[0]))[:top_modes_per_channel]
        for mode_index, power, phase in ranked:
            tone_hz = _mode_to_tone(mode_index, max(1, min(max_dft_modes, len(normalised) // 2)), target_band_hz)
            components.append(
                HarmonicComponent(
                    tone_hz=tone_hz,
                    source_coordinate=mode_index / len(normalised),
                    source_unit="cycles_per_residue",
                    amplitude=power,
                    phase_radians=phase,
                    channel=channel_name,
                    mode_index=mode_index,
                    adjacent_bands=adjacent_bands(tone_hz),
                )
            )
    components.sort(key=lambda item: (item.channel or "", item.mode_index or 0))
    mapping = HarmonicMapping(
        mapping_id=f"agpha:sequence-signature:{sequence_digest[:20]}",
        subject_id=subject_id,
        lane=HarmonicLane.SEQUENCE_SIGNATURE,
        algorithm="multi-channel amino-acid property DFT sketch",
        algorithm_version="agpha.sequence-dft.v1",
        input_sha256=sequence_digest,
        evidence_state=EvidenceState.COMPUTED,
        physical_interpretation=False,
        components=tuple(components),
        source_evidence=tuple(evidence),
        notes=(
            "Deterministic mathematical fingerprint over residue-property sequences. "
            "The display tones and adjacent bands are index coordinates, not measured protein vibrations, "
            "and carry no biological-effect claim."
        ),
    )
    errors = mapping.validate()
    if errors:
        raise ValueError("invalid sequence signature: " + "; ".join(errors))
    return mapping


def harmonic_distance(left: HarmonicMapping, right: HarmonicMapping) -> float:
    """Lane-safe RMS distance between two mappings after sorted tone alignment.

    Cross-lane comparison is refused because a mathematical sequence signature is not
    commensurate with a measured vibrational spectrum.
    """

    if left.lane != right.lane:
        raise ValueError(f"cannot compare harmonic lanes {left.lane.value} and {right.lane.value}")
    a = sorted(component.tone_hz for component in left.components)
    b = sorted(component.tone_hz for component in right.components)
    if len(a) != len(b):
        raise ValueError("harmonic mappings must contain the same number of components")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))
