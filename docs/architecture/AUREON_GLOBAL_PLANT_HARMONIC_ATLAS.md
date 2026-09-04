# Aureon Global Plant Harmonic Atlas (AGPHA)

**Status:** v1 foundation / execution contract  
**System:** Aureon OS / Harmonic Nexus Core  
**Compute target:** Isambard-AI through the project's internal Eigenbot worker role  
**Scientific boundary:** inventory, mathematical representation, physical spectral transformation, and preclinical hypothesis generation only

## 1. Purpose

AGPHA is the species-scale extension of Aureon's existing phenolic fingerprint and HNC BioMolecule packet work. Its target is an evidence-bearing library for every plant species for which open data can be lawfully acquired. Each species shard answers, without compression:

1. Which plant is this, according to a frozen taxonomic release?
2. Which genomes, transcripts, proteins, structures, metabolites, spectra, and publications are directly known?
3. Which records are computed or inferred rather than directly observed?
4. Which harmonic transform was applied, under which algorithm version?
5. Which layers are absent, conflicting, negative, or not yet queried?

The atlas is not a table of frequencies stripped from their provenance. It is a versioned knowledge graph expressed as immutable species shards, with every emitted tone attached to its source object, evidence state, transform lane, and checksum.

## 2. What already exists in Aureon OS

AGPHA extends rather than replaces the current repository path:

```text
open spectral evidence
        |
        v
fetcher.py                      NIST/Coblentz JCAMP-DX acquisition
        |
        v
connector.py                    heterogeneous normalisation + hard provenance gate
        |
        v
phenolic_fingerprint.py         spectral coordinate -> physical frequency -> octave fold
        |                       Test A clustering + Test B phi alignment + controls
        +-------------------+
                            |
                            v
blueprints.py                   plant/molecule graph + coherence nodes + adjacent bands
                            |
                            v
aureon/cognition/
phenolic_bridge.py              ThoughtBus + compact cognitive trace
```

The inherited transform remains the reference physical-frequency lane. For a wavenumber \(\tilde\nu\) in cm\(^{-1}\):

\[
f_{physical}=\tilde\nu\,(0.0299792458\;\mathrm{THz\,cm})\,10^{12}
\]

The modulation coordinate is:

\[
f_{mod}=\frac{f_{physical}}{2^n}
\]

where \(n\in[20,60]\) is selected to place the result nearest the geometric centre of the fixed 1000–2000 Hz HNC modulation band. AGPHA keeps this exact rule so existing HNC biomolecule peaks map to the same modulation coordinates.

Each centre can carry two explicitly labelled adjacent fields:

\[
f_{\pm1\%}=f(1\pm0.01)
\]

\[
f_{\pm\phi^{-9}}=f(1\pm\phi^{-9})
\]

These are derived packet coordinates. They do not, by themselves, establish a biological effect.

## 3. The non-negotiable separation of harmonic lanes

AGPHA does not collapse unlike evidence into one frequency column.

| Lane | Input | Interpretation | Evidence rule |
|---|---|---|---|
| `spectral_measured` | Experimental IR, Raman, UV-visible or other supported spectral coordinate | Physical source frequency, octave-folded into the display/modulation band | Requires `measured_direct` |
| `spectral_computed` | Calculated spectral coordinate | Theoretical physical model output | Requires `computed` |
| `structure_normal_mode` | Structure-based normal-mode calculation | Computed structural-mode candidate | Must retain method, model and confidence |
| `sequence_signature` | Amino-acid sequence | Deterministic mathematical fingerprint | Always non-physical |
| `ortholog_inferred` | Nearest supported ortholog | Prioritisation candidate only | Always non-physical and explicitly inferred |
| `legacy_hnc_packet` | Existing governed HNC packet | Preserved reference object | Never silently reclassified as a measured spectrum |

A sequence signature is not a vibrational spectrum. It is an indexable representation that allows the system to cluster proteins, identify conserved patterns, prioritise expensive structure calculations, and compare like with like. Cross-lane distance is refused in code.

## 4. Sequence-signature transform

For each canonical amino-acid sequence, AGPHA builds three residue-property channels:

- Kyte-Doolittle hydropathy;
- average residue mass;
- nominal side-chain charge near neutral pH.

For channel \(c\), the centred, energy-normalised sequence \(x_c(j)\) is projected through a low-mode discrete Fourier transform:

\[
X_c(k)=\sum_{j=0}^{N-1}x_c(j)e^{-2\pi i k j/N}
\]

The retained coordinate is \(k/N\) cycles per residue. Normalised power and phase remain attached. For visual indexing only, mode \(k\) is mapped monotonically into the 1000–2000 Hz display band:

\[
f_{display}(k)=1000\left(\frac{2000}{1000}\right)^{k/K}
\]

where \(K=\min(64,\lfloor N/2\rfloor)\). The resulting mapping is hard-coded as `physical_interpretation=false`.

The pure-Python implementation is the deterministic reference oracle. The Torch backend performs the same masked batched DFT on CUDA for Isambard-AI and has a separate algorithm version, `agpha.sequence-dft.torch.v1`.

## 5. Species shard contract

The canonical object is `agpha.species-shard.v1`. Each shard contains:

```text
species shard
├── taxon identity
│   ├── accepted name, rank, family, genus, synonyms
│   └── WFO / NCBITaxon / provider identifiers
├── source evidence
├── proteins
│   ├── accession, gene/name, sequence digest and length
│   ├── reviewed/unreviewed status
│   └── structure cross-references
├── molecules
│   ├── chemical identifiers
│   ├── occurrence evidence
│   └── plant-part/phase only when sourced
├── spectral peaks
│   └── method, unit, value, assignment, phase and source
├── harmonic mappings
│   ├── lane and algorithm version
│   ├── input digest
│   ├── physical/non-physical flag
│   └── components and adjacent fields
├── observations
│   └── positive, negative or conflicting findings with boundaries
├── knowledge gaps
│   └── no-data, not-queried, negative or conflicting states
└── claim ceiling + boundary statement
```

Serialization is canonicalised and SHA-256-addressable. The schema is accompanied by runtime validation and a public JSON Schema under `docs/schemas/`.

## 6. Evidence state machine

AGPHA uses evidence states rather than a single confidence score:

- `measured_direct` — direct experimental measurement;
- `curated_direct` — direct curated identity, occurrence or sequence record;
- `computed` — generated by a named computational method;
- `inferred_ortholog` — transferred from a related sequence and never presented as direct;
- `negative_result` — a source explicitly reports failure, absence or a stop condition;
- `no_data` — the defined query was run and returned no qualifying evidence;
- `query_not_run` — acquisition has not yet covered the defined scope;
- `conflicting` — sources materially disagree.

The distinction between `no_data` and `query_not_run` is load-bearing. Unknown must not be converted into absence.

No mapping may emit components from `negative_result`, `no_data`, `query_not_run`, or `conflicting` evidence. Measured and computed spectral lanes have stricter lane-specific gates.

## 7. Source acquisition plan

The source registry in `aureon/bio/plant_atlas/source_registry.py` defines the initial acquisition surface. Network acquisition is separated from compute. Isambard workers consume frozen local snapshots only.

| Layer | Primary source | Role |
|---|---|---|
| Global taxonomy | World Flora Online Plant List | Accepted-name and synonym spine; freeze a release and its CC0 declaration |
| Sequence-linked taxonomy | NCBI Taxonomy / Datasets | NCBITaxon crosswalk and sequence package anchor |
| Genomes/transcripts/proteins | NCBI Datasets, RefSeq, GenBank | Accession-pinned sequence packages and checksums |
| Protein curation | UniProt | Reviewed/unreviewed proteins, proteome IDs and cross-references |
| Experimental proteomics | PRIDE / ProteomeXchange | Tissue/sample-linked peptide and protein observations |
| Experimental structures | RCSB PDB | Method-bearing coordinate evidence |
| Predicted structures | AlphaFold DB | Computed structures with pLDDT/PAE and model version |
| Natural-product occurrence | LOTUS | Taxon-to-compound literature-linked candidates |
| Chemical identity | PubChem and ChEBI | CID/InChIKey/SMILES and ontology crosswalks |
| Metabolomics | MetaboLights | Study, plant part, condition and assay context |
| Spectra | NIST WebBook, MassBank and study files | Experimental spectra; modality is preserved |
| Literature | Europe PMC/open full text | Citation-retaining evidence extraction |

Every acquisition snapshot must contain:

- release or query identifier;
- provider and retrieval timestamp;
- applicable licence/terms captured at ingest;
- source checksums and file inventory;
- query receipts, including zero-result queries;
- identifier crosswalk receipts;
- a snapshot-level manifest digest.

The source snapshot is serialised as `agpha.source-snapshot.v1`; `verify-snapshot` recomputes file sizes and SHA-256 digests before compute. The compute manifest enforces `network_policy=staged_snapshot_only`; a compute shard does not contact public APIs.

## 8. Planetary build sequence

### Stage 0 — freeze the operating contract

Pin `agpha.species-shard.v1`, `agpha.run-manifest.v1`, algorithm versions, source registry version, claim ceilings, and the pilot acceptance tests.

### Stage 1 — build the plant spine

Freeze a World Flora Online release. Create one taxon key per accepted species. Preserve synonyms and the exact release identifier. No proteins or molecules are required to create an inventory-only species shard.

### Stage 2 — create identifier crosswalks

Resolve WFO names to NCBITaxon and provider-specific identifiers. Ambiguous and conflicting matches become explicit gap records; they are not auto-merged.

### Stage 3 — ingest direct evidence

Attach direct genome, transcript, protein, structure, metabolite occurrence, spectrum and literature records. Sequence bytes stay in the frozen input snapshot; public atlas shards retain accession, length and digest unless a distribution licence permits more.

### Stage 4 — map measured spectra

Apply the inherited physical-frequency conversion and octave rule. Preserve modality, method, phase, source and intensity. Run existing controls before any statistical-structure verdict is accepted.

### Stage 5 — compute protein sequence signatures

Run the deterministic reference implementation on the pilot set. Confirm byte-stable results against the Torch backend. Then execute batched GPU shards on Isambard-AI.

### Stage 6 — compute structural candidates

For proteins with experimental or confidence-qualified predicted structures, calculate normal-mode candidates under a separately versioned method. Do not merge these with sequence signatures or measured spectra.

### Stage 7 — add ortholog expansion

Where direct species evidence is absent, attach a separately labelled ortholog candidate with source species, alignment method, identity/coverage, orthology method and uncertainty. Inference is a search-prioritisation layer, not an observation.

### Stage 8 — construct governed HNC packets

Packets may be assembled only from lane-compatible mappings whose evidence gates pass. Every packet records its constituent mappings, transform versions, carrier assumptions, controls, and claim ceiling.

### Stage 9 — falsification and external validation

Use random-frequency, carrier-only, molecule-only, signal-only and assay-positive controls appropriate to the hypothesis. A packet that fails its pre-registered stop rule remains in the atlas as negative evidence rather than being deleted.

## 9. Eigenbot and Isambard-AI execution model

`Eigenbot` is the internal name for the orchestration role. The awarded Bristol system is Isambard-AI. AGPHA gives that role a reproducible contract:

```text
frozen source snapshot
        |
        v
agpha.run-manifest.v1
        |
        +-- deterministic SHA-256 taxon partition
        +-- one taxon appears in exactly one shard
        +-- source/output roots
        +-- enabled lanes and algorithm versions
        |
        v
Slurm job array: one task = one manifest shard
        |
        v
Torch/CUDA batched sequence mapping + physical spectral mapping
        |
        v
species JSON + per-task receipt + SHA-256 digests
```

Isambard-AI uses Arm/aarch64 GH200 nodes. Container images and compiled dependencies must support aarch64. The supplied `scripts/isambard/agpha_torch.def` is the starting runtime, and `plant_atlas_array.sbatch` requests one GPU per task. The array concurrency cap is intentionally conservative and should be raised only after the calibration tranche.

### Storage discipline

- immutable input snapshot and durable results: `$PROJECTDIR`;
- SIF images, temporary checkpoints and intermediate files: `$SCRATCHDIR`;
- never treat either location as archival backup;
- copy receipts, manifests, final shards and checksums off-system;
- do not rely on scratch content beyond the documented retention window.

### Compute gates for the 20,000 GPU-hour award

The award should not be released as one uncontrolled global run.

| Gate | Maximum initial use | Exit condition |
|---|---:|---|
| G0 — environment proof | 20 GPU-hours | aarch64 container, one-GPU job, receipt and checksum round trip pass |
| G1 — reference equivalence and throughput | additional 180 GPU-hours | Torch agrees with the reference within declared tolerances; throughput/memory curves recorded |
| G2 — first taxonomic tranche | up to 2,000 GPU-hours total | no duplicate/lost taxa; failure rate and source coverage audited |
| G3 — scaled expansion | released in measured tranches | each tranche reconciles input count, output count, receipts, cost and evidence states |
| Reserve | retained until final quarter | failed-shard reruns, method comparison, external reproduction |

A 20,000 GPU-hour Isambard-AI allocation corresponds to 5,000 full node-hours because a node contains four GPUs. Accounting is based on allocated GPU fractions, so short, fully utilised one-GPU tasks are preferable to CPU-heavy jobs that merely reserve a GPU.

## 10. Pilot shards

### `Prunus spinosa` — Blackthorn

The Blackthorn pilot is deliberately negative-evidence aware. It preserves the existing research stop conditions and does **not** emit a harmonic packet merely because a species name or candidate chemistry exists. Current state:

- taxonomy anchored to `ncbitaxon:114937`;
- research findings retained as negative/insufficient observations;
- missing direct molecular spectra and protein layers represented as gaps;
- `harmonic_packet_status=withheld`;
- no therapeutic, clinical, diagnostic or administration route.

This is an integrity test: the planetary atlas must be capable of saying **do not advance**.

### `Taraxacum officinale` — dandelion

The dandelion pilot preserves the existing HNC packet as a legacy governed object and separately maps measured compound spectral peaks through the physical lane. Current state:

- taxonomy anchored to `ncbitaxon:50225`;
- chlorogenic acid, luteolin and chicoric acid records;
- source-linked spectral records where present;
- existing 13-tone HNC packet retained as `legacy_hnc_packet` and marked non-physical as an aggregate reference;
- experiment remains unperformed and the claim ceiling remains preclinical.

## 11. Input bundle and worker contract

Acquisition produces one `agpha.input-bundle.v1` JSON per taxon under a content-addressed relative path. An input bundle may contain source sequences because it lives in the controlled snapshot. The emitted public species shard stores only sequence digest and length alongside the derived signature.

Verify the frozen source snapshot before making compute work:

```bash
python -m aureon.bio.plant_atlas verify-snapshot \
  --manifest "$PROJECTDIR/agpha/snapshots/2026-09-04/source-snapshot.json" \
  --root "$PROJECTDIR/agpha/snapshots/2026-09-04"
```

Create a manifest:

```bash
python -m aureon.bio.plant_atlas make-manifest \
  --taxa taxa.txt \
  --run-id agpha-wfo-snapshot-001 \
  --snapshot-id wfo-ncbi-uniprot-2026-09-04 \
  --created-at 2026-09-04T13:00:00Z \
  --source-root "$PROJECTDIR/agpha/snapshots/2026-09-04" \
  --output-root "$PROJECTDIR/agpha/runs/agpha-wfo-snapshot-001" \
  --shards 256 \
  --output "$PROJECTDIR/agpha/manifests/agpha-wfo-snapshot-001.json"
```

Build the aarch64-compatible runtime on Isambard-AI:

```bash
apptainer build --fakeroot "$SCRATCHDIR/agpha-torch.sif" \
  scripts/isambard/agpha_torch.def
```

Submit the array:

```bash
export AGPHA_REPO="$PROJECTDIR/Aureon-OS"
export AGPHA_MANIFEST="$PROJECTDIR/agpha/manifests/agpha-wfo-snapshot-001.json"
export AGPHA_CONTAINER="$SCRATCHDIR/agpha-torch.sif"
export AGPHA_SOURCE_ROOT="$PROJECTDIR/agpha/snapshots/2026-09-04"
export AGPHA_OUTPUT_ROOT="$PROJECTDIR/agpha/runs/agpha-wfo-snapshot-001"

sbatch --array=0-255%32 scripts/isambard/plant_atlas_array.sbatch
```

Validate output locally or on a login node without running compute:

```bash
python -m aureon.bio.plant_atlas validate-shard \
  "$AGPHA_OUTPUT_ROOT/species"

python -m aureon.bio.plant_atlas inventory \
  "$AGPHA_OUTPUT_ROOT/species"
```

## 12. Acceptance criteria

A planetary tranche is complete only when:

- every input taxon appears exactly once in the manifest;
- every task emits a receipt, including failed and empty shards;
- completed + failed equals assigned for every task;
- every output checksum verifies;
- all species shards validate against runtime rules and JSON Schema;
- every harmonic mapping names one lane and one algorithm version;
- no sequence or ortholog mapping is marked physical;
- negative results and zero-result queries remain visible;
- no missing layer is silently converted into a positive candidate;
- inventory totals reconcile to the taxon spine snapshot;
- manifests, receipts, source ledgers and final shards are copied to durable external storage.

## 13. Immediate implementation boundary

This v1 foundation implements:

- evidence-first species shard model and parser;
- measured/computed spectral conversion compatible with the current HNC engine;
- deterministic protein sequence signatures;
- Torch/CUDA batched sequence backend;
- adjacent field generation;
- source registry;
- deterministic run manifests and taxon sharding;
- offline worker and checksum-bearing receipts;
- Blackthorn and dandelion pilot shards;
- Isambard-AI Apptainer/Slurm entry points;
- tests enforcing lane separation, negative-evidence preservation and reproducibility.

It does not claim that every plant has already been ingested, that sequence signatures are measured molecular vibrations, or that any packet has demonstrated biological efficacy. The next implementation tranche is the release-pinned WFO/NCBI/UniProt acquisition and crosswalk layer feeding this contract.
