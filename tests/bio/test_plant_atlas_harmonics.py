from __future__ import annotations

import pytest

from aureon.bio.plant_atlas.harmonics import (
    PHI_INV_9,
    adjacent_bands,
    harmonic_distance,
    protein_sequence_signature,
    spectral_peak_to_mapping,
)
from aureon.bio.plant_atlas.models import EvidenceRef, EvidenceState, SpectralPeak


def _measured_peak(value: float = 1603.0) -> SpectralPeak:
    return SpectralPeak(
        peak_id=f"peak:{value}",
        subject_id="molecule:chlorogenic-acid",
        value=value,
        unit="cm^-1",
        method="Raman",
        evidence=EvidenceRef(
            provider="test",
            record_id="doi:test",
            state=EvidenceState.MEASURED_DIRECT,
        ),
    )


def test_existing_hnc_peak_maps_to_same_modulation_region() -> None:
    mapping = spectral_peak_to_mapping(_measured_peak())

    assert mapping.selected_octaves == 35
    assert mapping.components[0].tone_hz == pytest.approx(1398.60, abs=0.1)
    assert mapping.physical_interpretation is True


def test_adjacent_bands_include_narrow_and_phi_inverse_nine() -> None:
    bands = adjacent_bands(1400.0)

    assert {band.label for band in bands} == {
        "narrow_pm_1_percent",
        "geometric_pm_phi_inv_9",
    }
    geometric = next(band for band in bands if band.label == "geometric_pm_phi_inv_9")
    assert geometric.delta_fraction == pytest.approx(PHI_INV_9)
    assert geometric.lower_hz == pytest.approx(1400.0 * (1.0 - PHI_INV_9))


def test_sequence_signature_is_deterministic_and_nonphysical() -> None:
    sequence = "MSTNPKPQRKTKRNTNRRPQDVKFPGGGQIVGGVYLLPRRG"
    first = protein_sequence_signature("protein:test", sequence)
    second = protein_sequence_signature("protein:test", sequence)

    assert first == second
    assert first.physical_interpretation is False
    assert first.input_sha256 == second.input_sha256
    assert len(first.components) == 12
    assert {component.channel for component in first.components} == {
        "hydropathy",
        "residue_mass",
        "nominal_charge",
    }


def test_cross_lane_distance_is_refused() -> None:
    sequence = protein_sequence_signature("protein:test", "ACDEFGHIKLMNPQRSTVWY")
    measured = spectral_peak_to_mapping(_measured_peak())

    with pytest.raises(ValueError, match="cannot compare harmonic lanes"):
        harmonic_distance(sequence, measured)
