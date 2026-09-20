"""Optional Torch/CUDA backend for batched AGPHA protein sequence signatures.

The pure-Python implementation in :mod:`harmonics` is the reference oracle.  This
module computes the same low-mode DFT construction in batches on a GPU and emits
records under a separately versioned algorithm identifier.  Torch remains optional
and is intentionally not added to Aureon's light core dependencies.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from .harmonics import (
    TARGET_BAND_HZ,
    _SEQUENCE_CHANNELS,
    _mode_to_tone,
    adjacent_bands,
    normalise_protein_sequence,
)
from .models import EvidenceRef, EvidenceState, HarmonicComponent, HarmonicLane, HarmonicMapping


@dataclass(frozen=True)
class ProteinSequenceInput:
    subject_id: str
    sequence: str
    evidence: tuple[EvidenceRef, ...] = ()


def torch_available() -> bool:
    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def cuda_available() -> bool:
    if not torch_available():
        return False
    import torch

    return bool(torch.cuda.is_available())


def _chunks(items: Sequence[ProteinSequenceInput], size: int) -> Iterable[Sequence[ProteinSequenceInput]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def batch_protein_sequence_signatures(
    records: Sequence[ProteinSequenceInput],
    *,
    device: str = "cuda",
    batch_size: int = 64,
    top_modes_per_channel: int = 4,
    max_dft_modes: int = 64,
    target_band_hz: tuple[float, float] = TARGET_BAND_HZ,
) -> list[HarmonicMapping]:
    """Compute variable-length protein DFT sketches in vectorised Torch batches.

    A masked Fourier matrix uses each sequence's own length, so padding does not
    alter its coefficients.  Ranking is performed on CPU with an explicit stable
    ``(-power, mode_index)`` key to keep tie behaviour deterministic.
    """

    if not torch_available():
        raise RuntimeError("Torch is required for the AGPHA GPU backend")
    if batch_size <= 0 or top_modes_per_channel <= 0 or max_dft_modes <= 0:
        raise ValueError("batch_size and mode counts must be positive")

    import torch

    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but torch.cuda.is_available() is false")

    prepared = [
        (record, normalise_protein_sequence(record.sequence))
        for record in records
    ]
    if not prepared:
        return []

    residue_index = {residue: index for index, residue in enumerate(sorted(_SEQUENCE_CHANNELS["hydropathy"]))}
    ordered_residues = [residue for residue, _ in sorted(residue_index.items(), key=lambda item: item[1])]
    channel_names = tuple(_SEQUENCE_CHANNELS)
    lookup = torch.tensor(
        [
            [_SEQUENCE_CHANNELS[channel][residue] for residue in ordered_residues]
            for channel in channel_names
        ],
        dtype=torch.float64,
        device=device,
    )

    results: list[HarmonicMapping] = []
    for group in _chunks(prepared, batch_size):
        lengths = [len(sequence) for _, sequence in group]
        max_length = max(lengths)
        encoded = torch.zeros((len(group), max_length), dtype=torch.long, device=device)
        mask = torch.zeros((len(group), max_length), dtype=torch.float64, device=device)
        for row, (_, sequence) in enumerate(group):
            encoded[row, : len(sequence)] = torch.tensor(
                [residue_index[residue] for residue in sequence],
                dtype=torch.long,
                device=device,
            )
            mask[row, : len(sequence)] = 1.0

        # B x C x L residue-property signal.
        signals = lookup[:, encoded].permute(1, 0, 2)
        lengths_tensor = torch.tensor(lengths, dtype=torch.float64, device=device)
        means = (signals * mask[:, None, :]).sum(dim=2) / lengths_tensor[:, None]
        centred = (signals - means[:, :, None]) * mask[:, None, :]
        energy = torch.sqrt((centred * centred).sum(dim=2)).clamp_min(1e-15)
        centred = centred / energy[:, :, None]

        positions = torch.arange(max_length, dtype=torch.float64, device=device)
        modes = torch.arange(1, max_dft_modes + 1, dtype=torch.float64, device=device)
        angles = -2.0 * math.pi * (
            modes[None, :, None] * positions[None, None, :] / lengths_tensor[:, None, None]
        )
        cos_matrix = torch.cos(angles) * mask[:, None, :]
        sin_matrix = torch.sin(angles) * mask[:, None, :]
        real = torch.einsum("bcl,bkl->bck", centred, cos_matrix)
        imag = torch.einsum("bcl,bkl->bck", centred, sin_matrix)
        power = (real.square() + imag.square()) / lengths_tensor[:, None, None]
        phase = torch.atan2(imag, real)

        valid_mode_counts = torch.tensor(
            [min(max_dft_modes, length // 2) for length in lengths],
            dtype=torch.long,
            device=device,
        )
        mode_numbers = torch.arange(1, max_dft_modes + 1, device=device)
        valid_modes = mode_numbers[None, :] <= valid_mode_counts[:, None]
        power = power * valid_modes[:, None, :]
        totals = power.sum(dim=2, keepdim=True).clamp_min(1e-30)
        power = power / totals

        power_cpu = power.detach().cpu().tolist()
        phase_cpu = phase.detach().cpu().tolist()
        for row, (record, sequence) in enumerate(group):
            components: list[HarmonicComponent] = []
            max_mode = max(1, min(max_dft_modes, len(sequence) // 2))
            for channel_index, channel_name in enumerate(channel_names):
                candidates = [
                    (mode_index, float(power_cpu[row][channel_index][mode_index - 1]), float(phase_cpu[row][channel_index][mode_index - 1]))
                    for mode_index in range(1, max_mode + 1)
                ]
                ranked = sorted(candidates, key=lambda item: (-item[1], item[0]))[:top_modes_per_channel]
                for mode_index, mode_power, mode_phase in ranked:
                    tone_hz = _mode_to_tone(mode_index, max_mode, target_band_hz)
                    components.append(
                        HarmonicComponent(
                            tone_hz=tone_hz,
                            source_coordinate=mode_index / len(sequence),
                            source_unit="cycles_per_residue",
                            amplitude=mode_power,
                            phase_radians=mode_phase,
                            channel=channel_name,
                            mode_index=mode_index,
                            adjacent_bands=adjacent_bands(tone_hz),
                        )
                    )
            components.sort(key=lambda item: (item.channel or "", item.mode_index or 0))
            sequence_digest = hashlib.sha256(sequence.encode("ascii")).hexdigest()
            mapping = HarmonicMapping(
                mapping_id=f"agpha:sequence-signature:{sequence_digest[:20]}",
                subject_id=record.subject_id,
                lane=HarmonicLane.SEQUENCE_SIGNATURE,
                algorithm="batched multi-channel amino-acid property DFT sketch",
                algorithm_version="agpha.sequence-dft.torch.v1",
                input_sha256=sequence_digest,
                evidence_state=EvidenceState.COMPUTED,
                physical_interpretation=False,
                components=tuple(components),
                source_evidence=record.evidence,
                notes=(
                    "Torch/CUDA implementation of the non-physical sequence fingerprint. "
                    "Display tones are mathematical index coordinates and carry no biological-effect claim."
                ),
            )
            errors = mapping.validate()
            if errors:
                raise ValueError("invalid GPU sequence signature: " + "; ".join(errors))
            results.append(mapping)
    return results
