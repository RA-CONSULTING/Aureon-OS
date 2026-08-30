# Investor-copy repair contract

Use `aureon.operator.design_investor_copy_repair` only for one bounded
`DESIGN-COPY-NNN` task. The control does not choose the source: it binds the
canonical-local or verified-live-backup source already selected by the current
owner/reconciliation and v4 work-order evidence. It then proves the complete
selected tree against the v4 baseline and runs the current controlled
investor-copy rules against that exact source before issuing a source-bound
contract.

The contract binds:

- the immutable design-cycle receipt and exact task hash;
- the immutable v4 work order and selected source root, manifest and tree;
- one public route, one HTML path and its before SHA-256;
- the current policy identity, SHA-256 and freshness window;
- a privacy-minimised findings digest, rule histogram and counts;
- one route claim-capsule SHA-256 and the exact required claim identifiers;
- a required-concept-groups SHA-256 and sorted satisfied concept identifiers.

Before issue, every required concept on the exact policy route—blocker or
warning—must have at least one controlled policy alternative present in an
exact `permitted_wording` entry of the sealed claim capsule. This is required
because candidate acceptance is zero-blocker and zero-warning. Unsatisfied
concepts block creation. Only the digest and concept identifiers enter the
contract; policy alternatives and permitted wording do not.

Before persisting a work order, run
`preflight_investor_copy_repair_contract(...)` to verify the exact task,
policy route, HTML path and claim-capsule satisfiability without selecting or
reading a source tree. Run
`preflight_investor_copy_repair_work_order(...)` against the complete
in-memory v4 work order and its planned controlled path to prove the already
selected source is feasible. Both preflights are read-only and grant no
decision, staging, package, release or deployment authority.

Create the in-memory source-bound contract with
`create_investor_copy_repair_contract(...)`, then persist it with
`write_investor_copy_repair_contract(...)`. The writer accepts only a direct
JSON child of `artifacts/website-operator/copy-repairs/` and refuses overwrite.

For staged delivery, supply the design-cycle receipt and task id only as a
pair:

```powershell
python -m aureon.autonomous.aureon_public_website_design_runner `
  --repo-root . create `
  --goal "<one bounded copy repair>" `
  --route-id <audited-route-id> `
  --reconciliation <current-live-reconciliation.json> `
  --design-cycle-receipt <current-design-cycle.json> `
  --design-copy-task-id DESIGN-COPY-001 `
  --run-id <new-run-id>
```

Either omit both copy arguments for a generic route-bounded job or provide both
for the exact `DESIGN-COPY-NNN` job. The delivery receipt seals
`delivery_contract` as exactly
`{"kind":"route-bounded-design","copy_repair_required":false}` or
`{"kind":"investor-copy-repair","copy_repair_required":true}`. The latter
requires the immutable `investor_copy_repair` reference at every state; dropping
it, retaining it under the generic kind, or carrying copy-candidate evaluation
before validation fails closed. The staged worker receives only the exact task,
contract, route, policy-count digest, claim-control digest and acceptance
projection. It never receives the selected-source root, manifest path, before
copy, raw findings, credentials, package or deployment authority.

Before using a contract, call
`verify_investor_copy_repair_contract(...)` with the exact route claim capsule.
Any task, work-order, selected-source, policy, route, claim or freshness drift
blocks the contract.

After the v4 candidate has been staged and its one HTML file repaired, call
`evaluate_investor_copy_repair_candidate(...)` against the sealed candidate
website root. Acceptance requires:

- exactly the target HTML path changed;
- no file addition, removal, link, reparse point or hard link;
- a current policy replay against the complete candidate;
- zero blockers and zero warnings.

A passing evaluation is local evidence only. It grants no canonical mutation,
package, credential, release or deployment authority and must continue through
the existing claim-surface, browser, accessibility, visual, package, owner,
backup and live read-back gates.
