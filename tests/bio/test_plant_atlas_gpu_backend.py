from __future__ import annotations

import pytest

from aureon.bio.plant_atlas.gpu_backend import (
    ProteinSequenceInput,
    batch_protein_sequence_signatures,
    torch_available,
)
from aureon.bio.plant_atlas.harmonics import protein_sequence_signature


@pytest.mark.skipif(not torch_available(), reason="optional torch backend not installed")
def test_torch_cpu_backend_matches_reference_oracle() -> None:
    sequence = "MSTNPKPQRKTKRNTNRRPQDVKFPGGGQIVGGVYLLPRRGACDEFGHIKLMNPQRSTVWY"
    reference = protein_sequence_signature("protein:test", sequence)
    accelerated = batch_protein_sequence_signatures(
        [ProteinSequenceInput(subject_id="protein:test", sequence=sequence)],
        device="cpu",
    )[0]

    assert accelerated.physical_interpretation is False
    assert accelerated.input_sha256 == reference.input_sha256
    assert len(accelerated.components) == len(reference.components)
    for expected, actual in zip(reference.components, accelerated.components):
        assert actual.channel == expected.channel
        assert actual.mode_index == expected.mode_index
        assert actual.source_coordinate == pytest.approx(expected.source_coordinate, abs=1e-15)
        assert actual.tone_hz == pytest.approx(expected.tone_hz, abs=1e-12)
        assert actual.amplitude == pytest.approx(expected.amplitude, abs=1e-12)
        assert actual.phase_radians == pytest.approx(expected.phase_radians, abs=1e-12)
