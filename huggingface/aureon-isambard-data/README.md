---
pretty_name: Aureon Isambard Data
license: other
tags:
  - aureon
  - hnc
  - isambard
  - training-data
---

# Aureon Isambard Data

Direct, checksum-tracked preservation of the approved training inputs used by the Aureon Isambard work. This is one component of the consolidated Aureon release, not a blanket relicensing of upstream datasets.

## Source mapping

| Isambard source | Repository destination |
| --- | --- |
| `/projects/u6vs/pretrain/` | `pretrain/` |
| `/projects/u6vs/hnc-organism/training/sft/` | `training/sft/` |
| `/projects/u6vs/hnc-organism/training/aureon_tokenizer.json` | `training/aureon_tokenizer.json` |
| `/projects/u6vs/hnc-organism/training/aureon_tokenizer.report.json` | `training/aureon_tokenizer.report.json` |

The tokenizer report records a 65,536-token vocabulary, a passing round-trip check, and approximately 4.057 characters per token on its Python holdout. Historical handoff estimates described roughly 562 GB of source corpus and 505 GB of token shards. Those are not current measured totals; the inventory and reconciliation manifests are authoritative when published.

## Provenance and licensing

This repository has mixed provenance. `license: other` does not grant rights that an upstream source did not grant. Source revisions, original per-row fields, attribution, and transformation records must remain attached to their corresponding files.

| Source | Observed terms | Publication rule |
| --- | --- | --- |
| [FineWeb](https://huggingface.co/datasets/HuggingFaceFW/fineweb) and [FineWeb-Edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) | ODC-BY 1.0; source cards also reference Common Crawl terms | Preserve attribution, source notices, and revisions. See [ODC-BY 1.0](https://opendatacommons.org/licenses/by/1-0/) and [Common Crawl terms](https://commoncrawl.org/terms-of-use). |
| [SmolLM-Corpus](https://huggingface.co/datasets/HuggingFaceTB/smollm-corpus) | ODC-BY; its `python-edu` files are metadata, with content obtained separately from Software Heritage and subject to The Stack v2 terms | Preserve the upstream metadata and The Stack provenance. Metadata availability alone does not clear separately downloaded source text. |
| [CodeParrot Clean](https://huggingface.co/datasets/codeparrot/codeparrot-clean) | The card describes per-row license fields but does not declare one simple repository-wide license | Do not infer a blanket license. Raw mirrors remain blocked until the applicable per-file terms and redistribution scope are reviewed. |
| [The Stack dedup](https://huggingface.co/datasets/bigcode/the-stack-dedup) | Gated upstream source; its public card was not available as license evidence during review | Blocked by default. Never bypass access controls or treat a downloadable mirror as permission. |
| Aureon-generated SFT and tokenizer artifacts | Release provenance is recorded per artifact | Publish only after source, privacy, and transformation checks pass. |

Derived token shards are not automatically cleared by the license on a script or tokenizer. Their source lineage must be retained and any unresolved source batch must be named in the blocked report.

## Integrity and exclusions

The transfer inventory records relative path, byte size, SHA-256, category, destination, and provenance for every regular file. Uploads resume from on-disk state on Isambard and are reconciled against Hub revisions and object hashes. No archive data is staged on the release PC.

Credentials, private keys, session material, sensitive personal data, and material without redistribution permission are excluded and reported. A blocked item is not silently dropped from accounting. Final release verification requires all blockers to be resolved; an explicitly acknowledged partial upload is only a migration checkpoint, not the completed release.

Canonical model: [GaryLeckey/aureon-7b](https://huggingface.co/GaryLeckey/aureon-7b). Source: [RA-CONSULTING/Aureon-OS](https://github.com/RA-CONSULTING/Aureon-OS). Public demonstration: [GaryLeckey/aureon-os](https://huggingface.co/spaces/GaryLeckey/aureon-os). Exact revisions will be linked in the final release manifest after validation.
