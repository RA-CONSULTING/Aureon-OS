"""Aureon Global Plant Harmonic Atlas (AGPHA).

AGPHA turns open, provenance-bearing plant evidence into immutable species shards.
It extends the existing phenolic-fingerprint path without conflating measured
spectral frequencies, computed structural modes, and sequence-derived signatures.
"""

from .harmonics import (
    PHI,
    PHI_INV_9,
    adjacent_bands,
    physical_frequency_hz,
    protein_sequence_signature,
    spectral_peak_to_mapping,
)
from .models import (
    ClaimCeiling,
    EvidenceRef,
    EvidenceState,
    HarmonicLane,
    HarmonicMapping,
    KnowledgeGap,
    MoleculeRecord,
    Observation,
    ProteinRecord,
    SpeciesShard,
    SpectralPeak,
    TaxonIdentity,
    inventory_summary,
    load_species_shard,
    write_species_shard,
)
from .sharding import AtlasRunManifest, build_run_manifest, load_run_manifest, partition_taxa
from .source_snapshot import (
    QueryReceipt,
    QueryStatus,
    SnapshotFile,
    SourceSnapshotManifest,
    load_source_snapshot,
    verify_source_snapshot,
    write_source_snapshot,
)

__all__ = [
    "PHI",
    "PHI_INV_9",
    "ClaimCeiling",
    "EvidenceRef",
    "EvidenceState",
    "HarmonicLane",
    "HarmonicMapping",
    "KnowledgeGap",
    "MoleculeRecord",
    "Observation",
    "ProteinRecord",
    "SpeciesShard",
    "SpectralPeak",
    "TaxonIdentity",
    "AtlasRunManifest",
    "QueryReceipt",
    "QueryStatus",
    "SnapshotFile",
    "SourceSnapshotManifest",
    "adjacent_bands",
    "physical_frequency_hz",
    "protein_sequence_signature",
    "spectral_peak_to_mapping",
    "inventory_summary",
    "load_species_shard",
    "write_species_shard",
    "build_run_manifest",
    "load_run_manifest",
    "partition_taxa",
    "load_source_snapshot",
    "verify_source_snapshot",
    "write_source_snapshot",
]
