"""Source registry for AGPHA open-data acquisition.

This module describes *where* an acquisition worker may obtain evidence.  It does
not perform network calls.  Every downloaded release must be frozen as an immutable
snapshot with retrieval time, provider terms/licence, checksums, and query receipts
before compute shards may consume it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Final

SOURCE_REGISTRY_VERSION: Final[str] = "agpha.source-registry.v1"


class SourceLayer(str, Enum):
    TAXONOMY = "taxonomy"
    GENOME = "genome"
    TRANSCRIPTOME = "transcriptome"
    PROTEIN = "protein"
    PROTEOMICS = "proteomics"
    STRUCTURE = "structure"
    METABOLITE_OCCURRENCE = "metabolite_occurrence"
    CHEMICAL_IDENTITY = "chemical_identity"
    SPECTRUM = "spectrum"
    LITERATURE = "literature"


class AdapterState(str, Enum):
    EXISTING = "existing"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    provider: str
    layers: tuple[SourceLayer, ...]
    homepage: str
    access_mode: str
    primary_identifiers: tuple[str, ...]
    adapter_state: AdapterState
    snapshot_required: bool = True
    capture_licence_at_ingest: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["layers"] = [item.value for item in self.layers]
        payload["adapter_state"] = self.adapter_state.value
        return payload


DEFAULT_SOURCES: Final[tuple[SourceSpec, ...]] = (
    SourceSpec(
        source_id="wfo_plant_list",
        provider="World Flora Online Plant List",
        layers=(SourceLayer.TAXONOMY,),
        homepage="https://list.worldfloraonline.org/",
        access_mode="versioned release/API; prefer a local release snapshot for global matching",
        primary_identifiers=("wfo_id", "accepted_name", "synonym"),
        adapter_state=AdapterState.PHASE_1,
        notes="Primary global plant-name spine; retain the release identifier and CC0 declaration with every snapshot.",
    ),
    SourceSpec(
        source_id="ncbi_taxonomy",
        provider="NCBI Taxonomy / NCBI Datasets",
        layers=(SourceLayer.TAXONOMY,),
        homepage="https://www.ncbi.nlm.nih.gov/datasets/taxonomy/",
        access_mode="NCBI Datasets v2 CLI/API data package",
        primary_identifiers=("ncbitaxon", "scientific_name"),
        adapter_state=AdapterState.PHASE_1,
        notes="Sequence-linked taxonomic crosswalk; use ncbitaxon:<id> identifiers and archive dataset_catalog/checksums.",
    ),
    SourceSpec(
        source_id="ncbi_datasets",
        provider="NCBI Datasets / RefSeq / GenBank",
        layers=(SourceLayer.GENOME, SourceLayer.TRANSCRIPTOME, SourceLayer.PROTEIN),
        homepage="https://www.ncbi.nlm.nih.gov/datasets/",
        access_mode="NCBI Datasets v2 CLI/API; accession-first downloads",
        primary_identifiers=("assembly_accession", "gene_id", "protein_accession", "bioproject"),
        adapter_state=AdapterState.PHASE_1,
        notes="Use dehydrated packages for large releases where practical; never infer an absent assembly from an unrun query.",
    ),
    SourceSpec(
        source_id="uniprot",
        provider="UniProt",
        layers=(SourceLayer.PROTEIN,),
        homepage="https://www.uniprot.org/",
        access_mode="UniProt REST API / release downloads",
        primary_identifiers=("uniprot_accession", "proteome_id", "ncbitaxon"),
        adapter_state=AdapterState.PHASE_1,
        notes="Keep reviewed and unreviewed records distinguishable; preserve source-database cross-references.",
    ),
    SourceSpec(
        source_id="pride",
        provider="PRIDE Archive / ProteomeXchange",
        layers=(SourceLayer.PROTEOMICS,),
        homepage="https://www.ebi.ac.uk/pride/",
        access_mode="PRIDE Archive API and project file downloads",
        primary_identifiers=("px_accession", "project_accession", "usi"),
        adapter_state=AdapterState.PHASE_2,
        notes="Experimental peptide/protein observations; retain sample, tissue, protocol, and identification FDR metadata.",
    ),
    SourceSpec(
        source_id="rcsb_pdb",
        provider="RCSB Protein Data Bank",
        layers=(SourceLayer.STRUCTURE,),
        homepage="https://www.rcsb.org/",
        access_mode="RCSB Search/Data APIs and versioned coordinate files",
        primary_identifiers=("pdb_id", "entity_id", "uniprot_accession"),
        adapter_state=AdapterState.PHASE_2,
        notes="Experimental structures only; retain method, resolution, entity mapping, and biological assembly context.",
    ),
    SourceSpec(
        source_id="alphafold_db",
        provider="AlphaFold Protein Structure Database",
        layers=(SourceLayer.STRUCTURE,),
        homepage="https://alphafold.ebi.ac.uk/",
        access_mode="bulk/API predicted-structure records",
        primary_identifiers=("uniprot_accession", "model_version"),
        adapter_state=AdapterState.PHASE_2,
        notes="Predicted structures are computed evidence; retain pLDDT/PAE and model version before normal-mode work.",
    ),
    SourceSpec(
        source_id="lotus",
        provider="LOTUS natural-products occurrence knowledgebase",
        layers=(SourceLayer.METABOLITE_OCCURRENCE, SourceLayer.LITERATURE),
        homepage="https://lotus.naturalproducts.net/",
        access_mode="versioned open data release",
        primary_identifiers=("taxon", "inchikey", "reference"),
        adapter_state=AdapterState.PHASE_1,
        notes="Plant-to-natural-product occurrence candidates; evidence remains occurrence/source linked, not quantitative abundance.",
    ),
    SourceSpec(
        source_id="pubchem",
        provider="PubChem",
        layers=(SourceLayer.CHEMICAL_IDENTITY,),
        homepage="https://pubchem.ncbi.nlm.nih.gov/",
        access_mode="PUG REST / bulk files",
        primary_identifiers=("pubchem_cid", "inchikey", "canonical_smiles"),
        adapter_state=AdapterState.PHASE_1,
        notes="Chemical identity and cross-references; taxon occurrence must come from a separate evidence source.",
    ),
    SourceSpec(
        source_id="chebi",
        provider="ChEBI",
        layers=(SourceLayer.CHEMICAL_IDENTITY,),
        homepage="https://www.ebi.ac.uk/chebi/",
        access_mode="web services / release files",
        primary_identifiers=("chebi_id", "inchikey"),
        adapter_state=AdapterState.PHASE_2,
        notes="Ontology and curated chemical identity; retain release and ontology relationships.",
    ),
    SourceSpec(
        source_id="metabolights",
        provider="MetaboLights",
        layers=(SourceLayer.METABOLITE_OCCURRENCE, SourceLayer.SPECTRUM),
        homepage="https://www.ebi.ac.uk/metabolights/",
        access_mode="MetaboLights API and study files",
        primary_identifiers=("mtb_lsid", "study_accession", "assay_file"),
        adapter_state=AdapterState.PHASE_2,
        notes="Study-level metabolomics; preserve organism, plant part, condition, platform, and raw/processed distinction.",
    ),
    SourceSpec(
        source_id="massbank",
        provider="MassBank",
        layers=(SourceLayer.SPECTRUM,),
        homepage="https://massbank.eu/MassBank/",
        access_mode="versioned record repository / API",
        primary_identifiers=("massbank_accession", "inchikey"),
        adapter_state=AdapterState.PHASE_2,
        notes="Experimental mass spectra; these are not directly interchangeable with IR/Raman vibrational peaks.",
    ),
    SourceSpec(
        source_id="nist_webbook",
        provider="NIST Chemistry WebBook / Coblentz Society collection",
        layers=(SourceLayer.SPECTRUM,),
        homepage="https://webbook.nist.gov/chemistry/",
        access_mode="JCAMP-DX download",
        primary_identifiers=("nist_webbook_id", "cas_rn"),
        adapter_state=AdapterState.EXISTING,
        notes="Existing Aureon fetcher handles a small phenolic IR panel; AGPHA generalises discovery and identity resolution.",
    ),
    SourceSpec(
        source_id="europe_pmc",
        provider="Europe PMC",
        layers=(SourceLayer.LITERATURE,),
        homepage="https://europepmc.org/",
        access_mode="REST API / open-access full-text subset",
        primary_identifiers=("pmid", "pmcid", "doi"),
        adapter_state=AdapterState.PHASE_2,
        notes="Literature evidence extraction; every extracted relation must retain exact citation and evidence span/receipt.",
    ),
)


def source_registry() -> dict[str, SourceSpec]:
    return {source.source_id: source for source in DEFAULT_SOURCES}


def source_registry_payload() -> dict[str, object]:
    return {
        "schema_version": SOURCE_REGISTRY_VERSION,
        "sources": [source.to_dict() for source in DEFAULT_SOURCES],
    }
