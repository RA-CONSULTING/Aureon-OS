---
pretty_name: Aureon Isambard Archive
license: other
tags:
  - aureon
  - hnc
  - isambard
  - research-archive
---

# Aureon Isambard Archive

Preservation of approved content from `/projects/u6vs/hnc-organism/` that is not assigned to the canonical model, training-data, or run repositories. Files retain their source-relative layout beneath `hnc-organism/`.

The archive includes HNC campaign evidence, raw streams, manifests, cluster-source snapshots, research records, and operational artifacts found in the source tree. Its purpose is traceability: the consolidated Aureon OS release and the Aureon 7B candidate can be connected back to the environment that produced them.

## Related release components

- Canonical model: [GaryLeckey/aureon-7b](https://huggingface.co/GaryLeckey/aureon-7b)
- Training inputs: [GaryLeckey/aureon-isambard-data](https://huggingface.co/datasets/GaryLeckey/aureon-isambard-data)
- Runs and evaluations: [GaryLeckey/aureon-isambard-runs](https://huggingface.co/datasets/GaryLeckey/aureon-isambard-runs)
- Consolidated source: [RA-CONSULTING/Aureon-OS](https://github.com/RA-CONSULTING/Aureon-OS)
- Public demonstration: [GaryLeckey/aureon-os](https://huggingface.co/spaces/GaryLeckey/aureon-os)

## Evidence and limitations

Historical logs, cancelled jobs, partial outputs, alternate experiments, and source snapshots are preserved as historical records, not promoted to successful results. Quantitative HNC claims remain tied to their original evidence and reproduction paths in the source repository. The archive itself is not independent validation of those claims.

The transfer does not silently discard material. Its public inventory records relative path, size, SHA-256, category, destination, and provenance. Blocked items appear in an explicit report with reasons. Credentials, private keys, session material, sensitive personal data, and material without redistribution permission are never approved for public upload.

Aureon-authored material retains its existing license. Third-party snapshots and evidence retain their own terms; `license: other` denotes mixed provenance and grants no additional rights. Exact revisions, transferred totals, verification results, and unresolved blockers belong in the final signed release manifest after the real release paths pass.
