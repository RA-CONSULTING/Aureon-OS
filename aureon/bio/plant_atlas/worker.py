"""Offline AGPHA shard worker for staged Eigenbot/Isambard-AI runs.

Compute nodes consume immutable local input bundles.  They do not query live data
providers.  Acquisition, licensing capture, and checksum verification happen in a
separate staging phase so every emitted species shard can be reproduced.
"""

from __future__ import annotations

import hashlib
import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .harmonics import protein_sequence_signature, spectral_peak_to_mapping
from .models import (
    ClaimCeiling,
    EvidenceRef,
    EvidenceState,
    KnowledgeGap,
    MoleculeRecord,
    Observation,
    ProteinRecord,
    SpeciesShard,
    SpectralPeak,
    TaxonIdentity,
    write_species_shard,
)
from .sharding import AtlasRunManifest

INPUT_BUNDLE_VERSION = "agpha.input-bundle.v1"
RECEIPT_VERSION = "agpha.shard-receipt.v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evidence(data: Mapping[str, Any]) -> EvidenceRef:
    return EvidenceRef(
        provider=str(data["provider"]),
        record_id=str(data["record_id"]),
        state=EvidenceState(data["state"]),
        source_uri=data.get("source_uri"),
        licence=data.get("licence"),
        retrieved_at=data.get("retrieved_at"),
        checksum_sha256=data.get("checksum_sha256"),
        notes=data.get("notes"),
    )


def _load_input_bundle(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input bundle must contain a JSON object")
    if payload.get("schema_version") != INPUT_BUNDLE_VERSION:
        raise ValueError(f"unsupported input bundle schema {payload.get('schema_version')!r}")
    return payload


def build_species_from_bundle(
    bundle: Mapping[str, Any],
    *,
    snapshot_id: str,
    enabled_lanes: set[str],
) -> SpeciesShard:
    taxon_data = bundle["taxon"]
    taxon = TaxonIdentity(
        accepted_name=str(taxon_data["accepted_name"]),
        rank=str(taxon_data.get("rank", "species")),
        family=taxon_data.get("family"),
        genus=taxon_data.get("genus"),
        identifiers=dict(taxon_data.get("identifiers", {})),
        synonyms=tuple(taxon_data.get("synonyms", [])),
    )

    proteins: list[ProteinRecord] = []
    mappings = []
    gaps: list[KnowledgeGap] = []
    sequence_inputs: list[tuple[str, str, tuple[EvidenceRef, ...]]] = []
    for item in bundle.get("proteins", []):
        evidence = tuple(_evidence(ref) for ref in item.get("evidence", []))
        sequence = item.get("sequence")
        sequence_digest: str | None = None
        sequence_length: int | None = None
        if sequence:
            compact = "".join(str(sequence).split()).upper().replace("*", "")
            sequence_digest = hashlib.sha256(compact.encode("ascii")).hexdigest()
            sequence_length = len(compact)
        protein = ProteinRecord(
            protein_id=str(item["protein_id"]),
            accession=item.get("accession"),
            name=item.get("name"),
            sequence_sha256=sequence_digest,
            sequence_length=sequence_length,
            evidence=evidence,
            gene=item.get("gene"),
            reviewed=item.get("reviewed"),
            structure_ids=tuple(item.get("structure_ids", [])),
            notes=item.get("notes"),
        )
        proteins.append(protein)
        if "sequence_signature" in enabled_lanes:
            if sequence:
                sequence_inputs.append((protein.protein_id, str(sequence), evidence))
            else:
                gaps.append(
                    KnowledgeGap(
                        gap_id=f"gap:protein-sequence:{protein.protein_id}",
                        layer="protein_sequence",
                        state=EvidenceState.NO_DATA,
                        query_scope=protein.accession or protein.protein_id,
                        reason="protein record exists but no amino-acid sequence was present in the frozen input bundle",
                        next_action="retrieve an accession-pinned sequence into a new source snapshot",
                    )
                )

    if sequence_inputs:
        backend = os.environ.get("AGPHA_SEQUENCE_BACKEND", "reference").strip().lower()
        if backend == "torch":
            from .gpu_backend import ProteinSequenceInput, batch_protein_sequence_signatures

            mappings.extend(
                batch_protein_sequence_signatures(
                    [
                        ProteinSequenceInput(subject_id=subject_id, sequence=sequence, evidence=evidence)
                        for subject_id, sequence, evidence in sequence_inputs
                    ],
                    device=os.environ.get("AGPHA_TORCH_DEVICE", "cuda"),
                    batch_size=int(os.environ.get("AGPHA_SEQUENCE_BATCH_SIZE", "64")),
                )
            )
        elif backend == "reference":
            mappings.extend(
                protein_sequence_signature(subject_id, sequence, evidence=evidence)
                for subject_id, sequence, evidence in sequence_inputs
            )
        else:
            raise ValueError("AGPHA_SEQUENCE_BACKEND must be 'reference' or 'torch'")

    molecules = tuple(
        MoleculeRecord(
            molecule_id=str(item["molecule_id"]),
            name=str(item["name"]),
            identifiers=dict(item.get("identifiers", {})),
            evidence=tuple(_evidence(ref) for ref in item.get("evidence", [])),
            plant_parts=tuple(item.get("plant_parts", [])),
            phases=tuple(item.get("phases", [])),
            notes=item.get("notes"),
        )
        for item in bundle.get("molecules", [])
    )

    peaks: list[SpectralPeak] = []
    for item in bundle.get("spectral_peaks", []):
        peak = SpectralPeak(
            peak_id=str(item["peak_id"]),
            subject_id=str(item["subject_id"]),
            value=float(item["value"]),
            unit=str(item["unit"]),
            method=str(item["method"]),
            evidence=_evidence(item["evidence"]),
            relative_intensity=item.get("relative_intensity"),
            assignment=item.get("assignment"),
            phase=item.get("phase"),
        )
        peaks.append(peak)
        if peak.evidence.state == EvidenceState.MEASURED_DIRECT and "spectral_measured" in enabled_lanes:
            mappings.append(spectral_peak_to_mapping(peak))
        elif peak.evidence.state == EvidenceState.COMPUTED and "spectral_computed" in enabled_lanes:
            mappings.append(spectral_peak_to_mapping(peak))

    observations = tuple(
        Observation(
            observation_id=str(item["observation_id"]),
            statement=str(item["statement"]),
            evidence_state=EvidenceState(item["evidence_state"]),
            evidence=tuple(_evidence(ref) for ref in item.get("evidence", [])),
            interpretation_boundary=str(item["interpretation_boundary"]),
        )
        for item in bundle.get("observations", [])
    )
    gaps.extend(
        KnowledgeGap(
            gap_id=str(item["gap_id"]),
            layer=str(item["layer"]),
            state=EvidenceState(item["state"]),
            query_scope=str(item["query_scope"]),
            reason=str(item["reason"]),
            next_action=item.get("next_action"),
        )
        for item in bundle.get("gaps", [])
    )

    shard_id = str(bundle.get("shard_id") or _default_shard_id(taxon))
    shard = SpeciesShard(
        shard_id=shard_id,
        taxon=taxon,
        snapshot_id=snapshot_id,
        claim_ceiling=ClaimCeiling(bundle.get("claim_ceiling", "inventory_only")),
        boundary_statement=str(
            bundle.get(
                "boundary_statement",
                "Inventory and derived harmonic representations only; no therapeutic, diagnostic, or biological-effect claim.",
            )
        ),
        evidence=tuple(_evidence(ref) for ref in bundle.get("evidence", [])),
        proteins=tuple(proteins),
        molecules=molecules,
        spectral_peaks=tuple(peaks),
        harmonic_mappings=tuple(mappings),
        observations=observations,
        gaps=tuple(gaps),
        metadata=dict(bundle.get("metadata", {})),
    )
    return shard.require_valid()


def _default_shard_id(taxon: TaxonIdentity) -> str:
    if "ncbitaxon" in taxon.identifiers:
        return f"agpha:species:ncbitaxon:{taxon.identifiers['ncbitaxon']}"
    digest = hashlib.sha256(taxon.accepted_name.encode("utf-8")).hexdigest()[:20]
    return f"agpha:species:name:{digest}"


def run_manifest_shard(
    manifest: AtlasRunManifest,
    shard_index: int,
    *,
    source_snapshot_root: str | Path | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    """Process one manifest assignment and return a checksum-bearing receipt."""

    manifest.require_valid()
    assignment = manifest.shard(shard_index)
    source_root = Path(source_snapshot_root or manifest.source_snapshot_root)
    target_root = Path(output_root or manifest.output_root)
    species_dir = target_root / "species"
    receipt_dir = target_root / "receipts"
    species_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)

    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_VERSION,
        "run_id": manifest.run_id,
        "snapshot_id": manifest.snapshot_id,
        "manifest_sha256": manifest.content_sha256(),
        "shard_index": shard_index,
        "assignment_sha256": assignment.assignment_sha256,
        "started_at": _utc_now(),
        "network_policy": manifest.network_policy,
        "items": [],
        "completed": 0,
        "failed": 0,
    }
    enabled_lanes = set(manifest.lanes)
    for work in assignment.items:
        input_path = source_root / work.input_relpath
        item_receipt: dict[str, Any] = {
            "taxon_key": work.taxon_key,
            "input_relpath": work.input_relpath,
            "status": "failed",
        }
        try:
            if not input_path.is_file():
                raise FileNotFoundError(f"input bundle not found: {input_path}")
            actual_input_sha256 = _sha256_file(input_path)
            item_receipt["input_sha256"] = actual_input_sha256
            if work.input_sha256 is not None and actual_input_sha256 != work.input_sha256.lower():
                raise ValueError(
                    f"input bundle checksum mismatch for {work.taxon_key}: "
                    f"expected {work.input_sha256}, got {actual_input_sha256}"
                )
            if manifest.require_source_checksums and work.input_sha256 is None:
                raise ValueError(f"manifest requires an input checksum for {work.taxon_key}")
            bundle = _load_input_bundle(input_path)
            bundle_key = str(bundle.get("taxon_key", ""))
            if bundle_key and bundle_key != work.taxon_key:
                raise ValueError(
                    f"input bundle taxon_key {bundle_key!r} does not match manifest {work.taxon_key!r}"
                )
            species = build_species_from_bundle(
                bundle,
                snapshot_id=manifest.snapshot_id,
                enabled_lanes=enabled_lanes,
            )
            output_name = hashlib.sha256(work.taxon_key.encode("utf-8")).hexdigest()[:24] + ".json"
            output_path = species_dir / output_name
            write_species_shard(species, output_path)
            item_receipt.update(
                {
                    "status": "complete",
                    "species_shard_id": species.shard_id,
                    "output_relpath": str(output_path.relative_to(target_root)),
                    "output_sha256": _sha256_file(output_path),
                    "species_content_sha256": species.content_sha256(),
                    "proteins": len(species.proteins),
                    "molecules": len(species.molecules),
                    "spectral_peaks": len(species.spectral_peaks),
                    "harmonic_mappings": len(species.harmonic_mappings),
                    "gaps": len(species.gaps),
                }
            )
            receipt["completed"] += 1
        except Exception as exc:  # receipt captures failure; caller decides whether to resubmit
            item_receipt["error_type"] = type(exc).__name__
            item_receipt["error"] = str(exc)
            item_receipt["traceback"] = traceback.format_exc(limit=8)
            receipt["failed"] += 1
        receipt["items"].append(item_receipt)

    receipt["finished_at"] = _utc_now()
    receipt["status"] = "complete" if receipt["failed"] == 0 else "partial_failure"
    receipt_path = receipt_dir / f"shard-{shard_index:05d}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    receipt["receipt_path"] = str(receipt_path)
    receipt["receipt_sha256"] = _sha256_file(receipt_path)
    return receipt
