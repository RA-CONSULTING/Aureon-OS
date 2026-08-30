# Website release authority

## State machine

`OBSERVED -> BRIEFED -> CANDIDATE_LOCAL -> VERIFIED_LOCAL | REJECTED | NEEDS_EVIDENCE -> BENCHMARKED -> PACKAGE_READY -> BACKUP_VERIFIED -> OWNER_APPROVED -> DEPLOYED_PENDING_READBACK -> VERIFIED_LIVE | LIVE_FAILED`

For autonomous V30+ candidates, design agents may move work only as far as a one-time lease-bound staged patch, source-bound staged-candidate validation and source-bound staged visual review. The broker accepts a data manifest through its built-in applier, not arbitrary agent code, and requires every declared test to pass. It also requires a hash-bound `claim_surface_manifest` for the exact staged route (an explicit empty list for no-copy work); every new static public text surface must match permitted capsule wording, its boundary, or a true non-claim. It cannot apply a candidate to the canonical website, package, or deploy it. The normal WebsiteOperator lifecycle may proceed only after a separate owner-controlled canonical promotion and the full current audit, visual, claims, investor-copy, research-refresh, package, backup and approval evidence.

An optional `aureon.operator.website_source_rationalisation` plan and its named-owner review-acknowledgement validation sit before `CANDIDATE_LOCAL` and do not advance this state machine. Production use is accepted only through the externally hash-checked isolated launcher, and the path-owned validation writer regenerates and replays its own receipt from the exact plan and decision. They bind only a read-only retained/omitted projection of the unchanged canonical tree, its fixed footprint projections, and an exact review acknowledgement valid for no more than four hours. The decision and validation both carry `staging_authority: none`; even a passing validation performs no stage and grants no source mutation or removal, candidate creation or mutation, package, release, credential, network, publishing, or deployment authority.

## Required sequence

1. Run WebsiteOperator inventory and full audit.
2. Run the Design Nexus cycle and objective browser/a11y/performance/claims suite. Require the exact `investor_copy_quality_current` hard gate, retain only its privacy-minimised hash/count binding, and keep the copy audit at no release authority. WebsiteOperator must rerun the exact binding before release packaging.
3. Build a reproducible ZIP whose manifest equals the complete runtime dependency closure.
4. Extract the ZIP locally and smoke-test it without relying on unverified production leftovers.
5. Create a fresh Home.pl `/` backup and verify its manifest and rollback coverage.
6. Bind owner approval to the exact ZIP SHA-256 with a short expiry.
7. Immediately before overwriting the public website, obtain action-time confirmation for the exact package and destination.
8. Deploy only the approved hash.
9. Read every manifest path back from the live HTTPS domain and verify canonical routes, required data/assets, TLS, console, and resource loading.
10. Report “live” only when the deployment receipt says verified live.

## Prohibited shortcuts

- Do not deploy a partial overlay whose omitted dependencies are merely assumed to exist.
- Do not equate `not-in-public-runtime-closure` with safe deletion, a complete staged source, candidate readiness, package readiness, or release readiness.
- Do not treat a passing manifest of incomplete files as rendered-site proof.
- Do not reuse an approval for a different package hash.
- Do not reset credentials, weaken tests, delete remote files, or perform automatic rollback.
- Do not store credentials in configuration, logs, manifests, receipts, or prompts.
- Do not convert local preview, prepared package, uploaded archive, or successful extraction into a live-publication claim.

## Failure handling

If upload succeeds but read-back fails:

- mark `LIVE_FAILED`;
- preserve the deployment and read-back receipts;
- do not claim publication complete;
- compare against the verified backup;
- ask the owner before any rollback or destructive cleanup.
