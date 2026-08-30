# Aureon Website Operator

## Purpose

`aureon-website` is the control plane that lets Aureon OS improve its public
website without turning a model response into publication authority.

The operator composes the website tooling already in this repository:

- `tools/aureon_website_design_audit_v28.js`
- `tools/aureon_metadata_ethos_audit_v28.js`
- `tools/build-homepl-v28-narrow-release.ps1`
- `website/backup-homepl-ftps.ps1`
- `website/publish-homepl-ftps.ps1`
- `tools/aureon_homepl_manifest_readback.ps1`

It adds a single lifecycle, machine-readable receipts, source-snapshot binding,
performance budgets, claim/ethos checks, backup verification, owner approval,
rollback metadata and exact live read-back.

The public website remains static and read-only. This operator is not served
from the marketing domain and does not expose the Aureon API, credentials,
grant ledgers, trading state or client material.

## Operating model

```text
inventory -> live reconciliation -> audit -> work order -> staged candidate -> separate owner-controlled promotion -> fresh audit
                                                                                |
                                                                                v
live read-back <- explicit deploy <- owner gate <- backup <- release build
```

The loop separates three kinds of authority:

1. **Aureon OS may observe, analyse and propose.** Inventory, audit and work
   orders are read-only.
2. **Aureon OS may prepare local artefacts.** A passing, current audit can build
   a hash-manifested release. This does not authorise publication.
3. **The owner controls external state.** Deployment requires a verified remote
   backup, a short-lived approval bound to the exact package hash and an
   explicit `--execute`. The upload is not called complete until every manifest
   path is read back from the live HTTPS domain.

The operator never performs automatic rollback or deletion. A backup receipt
records which release paths existed previously and which are new. Restoring a
backup—or removing a newly introduced path—is a separate owner-reviewed
operation.

## First setup

Install the strict operator/development surface:

```powershell
python -m pip install -e '.[operator,dev]'
aureon-website capabilities
```

The default configuration is
`aureon/operator/website_operator.defaults.json`; its schemas are:

- `aureon/operator/website_operator.schema.json`
- `aureon/operator/website_operator_receipts.schema.json`

Config changes are product changes. Review them like code. In particular, do
not add credentials, arbitrary shell strings, destructive commands or a second
publishing route.

## The self-improvement cycle

### 1. Observe the source and capacity context

```powershell
aureon-website inventory
```

The receipt records the local tree hash, file/byte totals, extension mix,
largest files, website Git state and the dated Home.pl capacity observation.
It records only the presence of credential environment variables, never their
values.

The provider panel currently reports a Hosting Biznes Apache allocation with
37 GB for the web server and 1.11 GB used. That headroom is **not** a target.
The operator independently enforces:

- 50 MiB maximum public source tree
- 2,000 public files
- 2.5 MiB maximum uncompressed critical-page direct references
- 384 KiB per CSS/JavaScript file
- 2.5 MiB per PNG and 512 KiB per WebP/JPEG
- smaller budgets for fonts, SVG, HTML, JSON and XML

Those defaults allow a visually rich static site while protecting mobile
performance and deployment reviewability. Raising a budget requires measured
evidence and a reviewed config change; unused hosting capacity is not evidence.

### 1a. Reconcile the public production presentation before treating local source as a baseline

```powershell
aureon-website live-drift `
  --route / `
  --route /research/ `
  --route /funding/investor-deck/
```

This is a read-only HTTPS observation. It compares selected local HTML routes
with the visible public presentation (title, description, canonical,
normalised visible text, CTA/form targets and key image/accessibility labels)
and writes an append-only receipt below
`artifacts/website-operator/`.

`live-surface-semantically-aligned` says only that the selected public routes
present the same semantic content as the local files at that moment. It does
not approve a candidate, a package, a backup or a deployment.

`live-drift-detected` means the public site and local tree are distinct
production records. Preserve both. Obtain a fresh verified Home.pl backup and
record an explicit owner-scoped source-reconciliation decision before using
either one as the baseline for a successor candidate or release discussion.
The command never fetches hosting credentials, copies public content into the
repository, overwrites production, promotes a candidate or invokes a publisher.

`live-observation-incomplete` means the public observation could not safely be
made (for example, a network error, unexpected response, or cross-origin
redirect). Repair the observation path first; it is not safe to infer
alignment.

### 1b. Use one minimized Research-route capture as an investigative hint

When a source-bound Research candidate fails its initial performance gate and
the existing trace leaves the source-level explanation unresolved, capture at
most one minimized, non-gating, self-hosted, analysis-only observation against
the unchanged staged tree. Do not repeat it to seek a different temporal
correlation or a lower performance observation:

```powershell
aureon-website research-attribution `
  --source-root artifacts/website-candidates/<run-id>/website
```

The resulting receipt and minimized trace remain below
`artifacts/website-operator/research-hydration-attribution/`. It uses browser
runtime resource, mutation and resize observations to record timing proximity
between known research render events and document-root layout windows. It is an
investigative hint only: it cannot prove causation; it is not a performance
gate, performance-budget result, or owner-work-order evidence; it cannot
satisfy candidate-control, source-reconciliation, or owner-decision
requirements; and it cannot change a performance threshold, create a
candidate, promote canonical source, package, access credentials or deploy. It
may identify a hypothesis for a separately scoped investigation, but cannot
itself justify or set the scope or acceptance proof of a fresh exact-path work
order. See
[`RESEARCH_ROUTE_LAYOUT_ATTRIBUTION.md`](RESEARCH_ROUTE_LAYOUT_ATTRIBUTION.md)
for interpretation.

### 1c. Resolve observed drift before an autonomous candidate is even staged

When the receipt reports `live-drift-detected`, the coding system must stop.
It cannot select either source or start a candidate by itself.
The owner first obtains a fresh verified Home.pl backup, then supplies a
four-hour owner decision using
[`OWNER_SOURCE_RECONCILIATION_DECISION.md`](OWNER_SOURCE_RECONCILIATION_DECISION.md).
That decision is retained below
`artifacts/website-operator/owner-source-reconciliations/` and binds the exact
reconciliation receipt and backup tree. The unchanged v1 decision retains
`website/` as candidate source; the stricter v2 decision selects the exact
manifest-bound verified backup below `artifacts/homepl-backups/` as candidate
source. V2 also rejects non-public/server-only paths and recognised credential
patterns before staging. Neither mutates `website/`, grants package approval,
or grants deployment approval.

Once the evidence is current, create a staged-only candidate order:

```powershell
aureon-website candidate-work-order `
  --goal "<one bounded website objective>" `
  --allow <exact-website-relative-file> `
  --route <affected-public-route> `
  --reconciliation-receipt artifacts/website-operator/<live-reconciliation>.json `
  --owner-source-decision artifacts/website-operator/owner-source-reconciliations/<decision>.json `
  --backup-receipt artifacts/website-operator/<verified-backup>.json `
  --run-id <lowercase-run-id>
```

For a `live-surface-semantically-aligned` receipt, omit the owner-decision and
backup arguments. Every order remains artifact-only, staged-only and unable to
promote, package or deploy.

### 2. Audit metadata, ethos, claims, static behaviour and motion

```powershell
aureon-website audit
```

The audit covers all HTML and applies the strict gate to the configured
critical routes. It checks:

- title, description, canonical, viewport, language, social metadata and H1
- local references, duplicate IDs, alt text and accessible interaction names
- HTTPS-only external references and no autoplay media
- a shared `prefers-reduced-motion` policy
- claim/evidence inputs, including the sector-blade register
- required evidence, research, human-authority and boundary signals
- prohibited unbounded commercial/autonomy claims
- public secret patterns and blocked credential-like files
- total, per-file and direct-reference performance/media budgets
- JavaScript syntax and the current V29 design-system audit

An audit receipt with `state: blocked` is useful evidence, not failure theatre.
It cannot be used to build a release.

### 3. Run the Design Nexus cycle and give Aureon a bounded work order

```powershell
aureon-website design-cycle --goal "<bounded design objective>"

aureon-website work-order --audit-receipt <audit.json>
```

The design cycle is release-eligible only when the complete configured external
suite ran, every hard gate passed, and there are zero open audit warnings or
errors. `--skip-external` is a diagnostic-only mode: its receipt is useful for
repair work but can never verify the candidate or authorise packaging. Enforced
stop control halts the work order after five iterations, two no-progress
iterations, a repeated blocker, missing claim evidence, or a critical veto.

The cycle runs the bounded investor-copy policy as the exact
`investor_copy_quality_current` hard gate. Static traction, research, operating,
finance or dated-snapshot figures and missing required concepts therefore block
the Design Nexus cycle even when the general website audit is otherwise clean.
The receipt retains only a privacy-minimised policy, route, source-hash,
finding-hash and aggregate-count binding for this control; it does not copy
public page text or raw findings into worker context. The copy audit has no
release authority. Release building must rerun the exact binding before release
packaging and requires the policy, route and finding hashes to remain unchanged.

For an exact `DESIGN-COPY-NNN` repair, the staged-delivery path first performs
the read-only task/policy/claim preflight, then the selected-source feasibility
preflight against the in-memory one-HTML v4 work order. Only then may it persist
the work order and short-lived source-bound contract. The candidate must pass
both the existing candidate control and the contract's exact current
investor-copy re-audit before any browser gate. Protocol availability is not a
current contract, copy readiness, source choice, candidate, package, release,
or deployment authority. See
[`INVESTOR_COPY_REPAIR_CONTRACT.md`](INVESTOR_COPY_REPAIR_CONTRACT.md).

If that repair needs the exact governed claim/register extension, the installed
investor-copy governance protocol exposes read-only decision verification and
full shadow simulation. Broad system access, a 24-hour operating window,
deployment approval, or conversational consent is not the required decision.
Canonical application remains blocked unless the named owner separately
supplies a fresh immutable decision bound to the module's current exact
proposal and validation and the caller explicitly selects apply. Even then,
the transaction is limited to the three declared governance files. It cannot
edit the copy policy or `website/`, create a candidate or package, approve a
release, access credentials or network, or deploy. See
[`INVESTOR_COPY_GOVERNANCE_APPLICATION.md`](INVESTOR_COPY_GOVERNANCE_APPLICATION.md).

The legacy work order is a diagnostic task list, not canonical-write authority.
For autonomous V30+ implementation, issue a separate reconciled v4 candidate work order
with an exact file allow-list. The runner may copy the current site only to
artifacts/website-candidates/<run-id>/website/, where the control records the
complete baseline, current live-surface evidence, per-file before/after hashes,
claim-impact declarations, editorial-binary policy, secret scan and
remote-origin diff. A worker may later submit only the broker-sealed text
delta. A drifted live record also requires the fresh verified backup and owner
source decision above. Neither runner nor worker can apply the candidate to
`website/`, package it or deploy it.

HTML, JavaScript, JSON and SVG rendering changes remain material
claim-impact declarations. A staged claim-register refresh is required only
when a changed material path is already one of that register's bound source
paths. A changed unbound material path must preserve the register byte-for-byte
and must not add a synthetic source binding. Any legitimate bound-source
refresh must retain the exact existing source and public-route scope. This
register rule is separate from the claim-surface manifest: every new rendered
surface still needs its independent route-capsule, boundary or non-claim
classification.

Candidate validation first creates exactly one immutable local provenance
sidecar at
`artifacts/website-candidates/<run-id>/candidate-validation-input.v1.json`
through the shared handle-bound `secure_immutable_artifact` writer. The
fixed-path sidecar binds the exact work order, local validation instant,
claim-impact declarations, and required claim-surface context and manifest.
It includes a canonical payload self-hash. An existing byte-identical sidecar
may be replayed, but it is never overwritten; changed immutable inputs require
a successor candidate.

The candidate receipt binds the sidecar's exact path, raw file SHA-256,
canonical JSON SHA-256, and payload self-hash. Verification resolves exactly
one contained filesystem link, reloads and re-hashes the sidecar, and derives
the replay instant, declarations, and claim-surface inputs only from that
sidecar. Receipt-supplied `validated_at` or claim context is never a replay
input. Runtime validation and the public schema also fix every nested field and
JSON type in the work-order and candidate bindings, change rows, claim wrapper,
17 ordered checks, and exact next gate. Duplicate JSON keys, non-finite
numbers, boolean/integer substitutions, extra nested fields, appended checks,
changed gates, or worker-supplied authority markers therefore block.

The sidecar is local provenance only. It is not a trusted wall-clock
attestation, operating-system isolation, input-origin attestation, or
canonical, package, release, credential, or deployment authority. A same-user
process with equivalent filesystem authority remains inside the residual
local trust boundary.

After a separate owner-controlled canonical promotion, rerun the complete
current audit, claim control, visual evidence, package, backup, owner approval
and live read-back sequence. This is the controlled self-building loop: the
model proposes and stages; objective controls and accountable humans decide
whether a result can advance.

### 3a. Prepare v4 candidate assets before any text-worker lease

Rights clearance and candidate asset readiness are separate facts.
`candidate_use_rights_ready` reports only that the provenance audit has an
exact, current, allowlisted named-owner-reviewer per-asset rights capsule. It does not show that
bytes were imported into a candidate. Because the capability registry is
global and has no candidate receipt, it must report
`candidate_asset_ready: false`. Only the staged-delivery runner may record the
candidate-specific `candidate-assets-ready` state.

An explicit owner rights choice may be recorded without editing that
manifest. Place one strict request beneath
`artifacts/website-operator/editorial-rights-requests/` with exactly these
fields:

```json
{
  "schema": "aureon.editorial-asset-rights-decision-preparation-request.v1",
  "asset_ids": ["<exact-asset-id-1>", "<exact-asset-id-2>"],
  "asset_scopes": {
    "<exact-asset-id-1>": "<CURRENT-UPPERCASE-ASSET-SCOPE-SHA256>",
    "<exact-asset-id-2>": "<CURRENT-UPPERCASE-ASSET-SCOPE-SHA256>"
  },
  "boundary_acknowledgement": "editorial-only; not evidence, validation, facilities, measured data or tested hardware",
  "decision": "approved",
  "decided_by": "<allowlisted named owner-reviewer>",
  "decided_at": "<ISO-8601 decision time>",
  "manifest_sha256": "<CURRENT-CANONICAL-MANIFEST-FILE-SHA256>",
  "rights_basis": "<controlled-rights-basis>",
  "usage_scope": "bound-routes-destinations-copy-and-variants-only"
}
```

The controlled rights bases are
`copyright-owner-authorisation`, `documented-provider-use-rights`, and
`licensed-for-bound-public-use`. Do not substitute a delivery message,
design preference or free-form explanation.
Use the current canonical manifest file hash and the current audit's
per-asset `rights.asset_scope_sha256` values only after the named reviewer has
reviewed the corresponding variants, routes, destinations, alt text, caption,
credit and representation boundary. The preparation command is a verifier,
not a worksheet generator, and must not auto-populate the human request.

Then run:

```powershell
python -m aureon.operator.design_editorial_asset_provenance `
  --repo-root . `
  --prepare-rights-request artifacts/website-operator/editorial-rights-requests/<request>.json
```

The preparation command never infers approval. It requires an explicit
`approved` or `rejected` value, an allowlisted named reviewer, one controlled
rights basis, a non-future decision time, the current canonical manifest file
hash, exact mapped asset IDs, the matching current scope hash for every and
only every requested asset, and the exact controlled usage and representation
boundary text. These are human-acknowledged request fields: the preparation
command verifies and copies them but must not derive or insert them. It
re-audits each scope, rejects stale manifest or scope bindings, duplicate,
abbreviated or unknown IDs, and writes one immutable decision file per asset
under `docs/research/editorial-assets/rights-decisions/`. A multi-asset request
is preflighted as one all-or-none batch; it does not turn the decisions into
one collection-wide record.

The companion artifact is a privacy-minimised
`manifest-binding-proposal-only` receipt. Neither it nor the decision files
edit `data/website_operator/editorial_asset_provenance.v1.json`, `website/`,
asset bytes, a candidate or a release package. The global policy remains
`not-cleared`, and `candidate_use_rights_ready` remains false until a separate
controlled manifest change binds each exact decision and a fresh provenance
audit emits its per-asset capsule. The preparation command has no candidate,
package, release, credential, network or deployment authority.

For a v4 order that declares WebP targets, the sequence is fixed:

1. The runner stages a pristine full candidate tree and records
   `candidate-staged`.
2. Before any text-worker context or broker lease is issued, trusted
   orchestration invokes the content-addressed importer for the complete exact
   WebP batch declared by the work order.
3. The importer persists its immutable receipt inside that candidate. The
   runner replays the receipt against current bytes, work order, provenance,
   routes and rights, then records `candidate-assets-ready`.
4. Only after that runner transition may the broker issue the sealed text
   contract. The public website worker has no binary read, write, copy, or
   import authority, cannot call the importer and cannot create or assert
   `candidate-assets-ready`.
5. After the declared text patch, final candidate validation performs a
   structural surface replay from the current staged bytes. Separately
   controlled text deltas may remain, but the binary projection must equal the
   source-bound baseline plus the exact importer receipt. Undeclared, missing,
   unbound, remote, embedded-media, or otherwise binary-smuggled asset
   references fail closed.

A text-only order skips steps 2 and 3, remains `candidate-staged` until
validation, and must never be labelled `candidate-assets-ready`. Do not trust
a worker-supplied “assets ready” assertion. Rights capsules, importer receipts,
asset-ready states, structural replay and candidate validation are local
evidence with no release authority: none can mutate canonical `website/`,
promote, package, access credentials, publish or deploy.

The runner exposes the controlled transition as:

```powershell
python -m aureon.autonomous.aureon_public_website_design_runner `
  --repo-root . import-assets --run-id <run-id>
```

Do not run `context` for an asset-bearing candidate before the persisted
`candidate-assets-ready` receipt verifies. For text-only work, `context` is
allowed from the verified `candidate-staged` state.

### 3b. Bind every new public text surface before a staged candidate can validate

For autonomous delivery, a refreshed claim-impact hash alone is insufficient:
the worker or broker must provide `claim_surface_manifest`, including `[]` for
an exact no-copy change. The staged candidate validator recomputes static
public text surfaces from the canonical baseline and the candidate's exact
changed paths. Every new surface needs one hash-bound classification that is
either exact permitted route wording, its exact route boundary, or a genuine
non-claim. It rejects dynamically generated copy that cannot be safely audited
and unsupported company, customer, adoption, validation, partnership, funding
or commercial assertions disguised as non-claims.

Use the dedicated
[`DESIGN_CANDIDATE_CLAIM_SURFACE.md`](DESIGN_CANDIDATE_CLAIM_SURFACE.md)
runbook. This evidence remains staged and local: a pass neither promotes the
canonical tree nor authorises a release, backup, package, credentials, upload
or live-publication claim.

### 3c. Bind staged visual evidence before an owner considers promotion

For a material V30+ candidate, capture the browser matrix from the staged tree
only. The candidate runner refuses a remote `--base-url` and has no canonical
write, package, credential, promotion or deployment capability:

```powershell
node tools/aureon_candidate_visual_review_v1.js `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json `
  --reviewer "<named technical reviewer>"
```

It writes a visual QA receipt, screenshots, a **deliberately unreviewed**
pixel-review template, and a capture receipt below that candidate's
`visual-review/` directory. A named reviewer must inspect and complete a copy
of that template. A separate human-visual-acceptance JSON receipt must then
bind the exact candidate receipt, visual receipt and completed manual review.

Verify the full local evidence chain without changing `website/`:

```powershell
aureon-website candidate-visual-review `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json `
  --capture-receipt artifacts/website-candidates/<run-id>/visual-review/<capture>.json `
  --manual-review artifacts/website-candidates/<run-id>/visual-review/<completed-manual-review>.json `
  --human-acceptance artifacts/website-candidates/<run-id>/visual-review/<human-acceptance>.json
```

A pass is `prepromotion-visual-review-passed`, with release, package and
deployment authority all still `none`. It demonstrates that a particular
staged candidate was tested and visually reviewed. It is not the V28 canonical
release gate and cannot be passed to `build`; after any owner-controlled
promotion, repeat the fresh canonical V28 audit/manual/composite sequence.

### 3d. Record a reusable pattern without changing a skill automatically

Once the exact staged candidate and visual review pass, the Design Learning
Ledger can record a bounded proposal for a future Design Suite skill update.
The manifest must name only candidate paths that actually changed, existing
regression-test paths, a current refresh deadline and an existing Markdown
target inside the Design Suite:

```powershell
aureon-website candidate-learning `
  --candidate-receipt artifacts/website-candidates/<run-id>/candidate.v1.json `
  --visual-review artifacts/website-candidates/<run-id>/visual-review/prepromotion-visual-review.v1.json `
  --learning-manifest artifacts/website-candidates/<run-id>/feedback/<pattern>.manifest.v1.json
```

The resulting record is append-only evidence below the same candidate root.
It revalidates candidate scope, browser evidence, manual pixel review and
human acceptance. It always has `release_eligible: false`, `package_authority:
none`, `deployment_authority: none` and `promotion.applied: false`; a
human-reviewed repository change is still required before a skill source can
change.

### 4. Build a narrow, verified release

```powershell
aureon-website build `
  --audit-receipt <passing-audit.json> `
  --design-cycle-receipt <passing-current-design-cycle.json> `
  --human-visual-accepted `
  --human-visual-accepted-by "<reviewer name>" `
  --output-directory "$env:USERPROFILE\Documents\Aureon-Releases"
```

The acceptance flag records an explicit human visual decision for the exact
source tree and design-cycle run; it is not deployment approval. The build
stops if the website changed after either receipt, if a receipt is stale, or if
any finding remains open. It then calls the audited narrow-release builder for V29 and
independently verifies:

- every required production path is present
- no path escapes the site root
- no blocked credential-like filename or extension is selected
- source bytes, CSV manifest hashes and ZIP entries agree exactly
- the package and manifest are bound to the passing audit, design cycle, and
  source-bound visual acceptance

The result is `prepared-not-deployed`.

### 5. Back up the actual Home.pl document root

The exact automated path is read-only FTPS. It never invokes
`publish-homepl-ftps.ps1`; that separate script contains upload methods and is
outside this step.

First obtain an authenticated Home.pl owner-panel read-back that binds the
exact non-secret FTPS hostname and account identifier to the intended domain
and `/` document root. A matching homepage on an unverified account can be an
exact copy, so public bytes alone are not provider identity. If that
owner-panel evidence is absent, stale, or ambiguous, the backup action remains
blocked even when `index.html` matches.

Create a fresh public HTTPS reconciliation for `/`, then create a unique
output and an immutable preflight within 15 minutes. The preflight receives the
exact non-secret host and account identifier but never reads a password and
stores only the account hash:

```powershell
$backupStamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$backupDirectory = Join-Path `
  (Resolve-Path 'artifacts/homepl-backups').Path `
  "homepl-live-$backupStamp"
$preflightReceipt = Join-Path `
  (Resolve-Path 'artifacts/website-operator').Path `
  "$backupStamp-homepl-backup-preflight.json"

python -m aureon.operator.website_operator `
  --repo-root (Get-Location).Path `
  backup-preflight `
  --output-directory $backupDirectory `
  --ftp-host $env:HOMEPL_FTPS_HOST `
  --ftp-account $env:HOMEPL_FTPS_USER `
  --live-reconciliation-receipt <fresh-live-reconciliation.json> `
  --output $preflightReceipt
```

Read the new receipt and stop unless `state` is
`ready-for-explicit-backup`. It binds:

- the ordinary single-link backup script and its SHA-256;
- the canonical `host:port`, host SHA-256, account SHA-256 and combined
  host/account binding, without recording the raw account;
- the exact `/` remote root;
- one absent output directory below `artifacts/homepl-backups/`;
- one absent adjacent CSV manifest, authenticated root-mapping receipt and
  transfer receipt;
- one fresh public HTTPS root fingerprint and its immutable reconciliation
  receipt;
- remote methods limited to directory listing, file-size observation, and
  file download.

An older preflight that lacks any of those fields, including the 2026-07-30
preflight produced before identity/root-continuity hardening, is diagnostic
history and is rejected. A changed script, host, account, public
reconciliation, output, or receipt path requires a new preflight.

At action time, provide `HOMEPL_FTPS_HOST`, `HOMEPL_FTPS_USER`, and
`HOMEPL_FTPS_PASSWORD` only in the current process environment. Never place
them in a command, receipt, log, `.env`, Drive file, or repository file. First
perform an authenticated no-transfer listing:

```powershell
& '.\website\backup-homepl-ftps.ps1' `
  -FtpHost $env:HOMEPL_FTPS_HOST `
  -FtpUser $env:HOMEPL_FTPS_USER `
  -RemoteRoot '/' `
  -OutputDirectory $backupDirectory `
  -PreflightReceipt $preflightReceipt `
  -ReadPasswordFromStandardInput `
  -ListOnly
```

The listing checks the configured immediate root entries and downloads
`/index.html` into memory. It must match the fresh public HTTPS byte count and
SHA-256 exactly. Only then does the tool create the adjacent immutable
`$backupDirectory-root-mapping.json`. This receipt binds the exact host,
account hash, preflight, script, public reconciliation, root listing digest and
homepage bytes. It is valid for at most 15 minutes. Do not fall back to
`/public_html`. If `/` cannot be proven to be the served document root, stop
and obtain a new owner-controlled hosting mapping before any backup or upload.

Run the complete read-only transfer only after that mapping passes. The
launcher locks the exact repository script, preflight, root-mapping receipt and
public reconciliation against replacement from validation through child exit,
and reads the temporary password only after every non-secret binding has
passed:

```powershell
& '.\tools\start-homepl-ftps-backup.ps1' `
  -BackupScript (Resolve-Path '.\website\backup-homepl-ftps.ps1').Path `
  -FtpHost $env:HOMEPL_FTPS_HOST `
  -FtpUser $env:HOMEPL_FTPS_USER `
  -RemoteRoot '/' `
  -OutputDirectory $backupDirectory `
  -PreflightReceipt $preflightReceipt `
  -StandardOutputPath "$backupDirectory-stdout.log" `
  -StandardErrorPath "$backupDirectory-stderr.log"
```

The tool downloads into a unique `.partial-*` staging directory. It publishes
the final directory, adjacent manifest, and adjacent transfer receipt only
after the complete download is locally hashed. It refuses existing
destinations, non-`/` roots, unsafe or colliding remote names, path aliases,
unbounded recursion, excessive file/byte counts, and any preflight/script
drift. Immediately before and after the tree download it re-lists `/` and
re-downloads `/index.html`; both observations must equal the authenticated
mapping, and the downloaded `backup/index.html` must have the same bytes. It
uses no FTP write method. If it fails, do not treat or rename a retained
partial directory as a backup; use a new timestamp, owner-panel read-back,
public reconciliation and preflight for a retry.

Normalise and verify the completed backup:

```powershell
python -m aureon.operator.website_operator `
  --repo-root (Get-Location).Path `
  verify-backup `
  --backup-directory $backupDirectory `
  --manifest "$backupDirectory-manifest.csv" `
  --preflight-receipt $preflightReceipt `
  --transfer-receipt "$backupDirectory-transfer.json" `
  --method homepl-ftps `
  --package-receipt <package-receipt.json>
```

The command rejects stale or future transfer times, any unmanifested or
missing file, links/reparse points, hard-linked aliases, off-boundary paths,
changed provenance, byte/hash differences, or a transfer that used remote
write methods. It also requires start/end root continuity and proves that the
downloaded `index.html` is the exact mapped public file. It re-hashes the
complete tree and records rollback coverage. A preflight, root-mapping or
transfer receipt alone is never accepted as backup proof. The current
exact-identity verifier accepts only `homepl-ftps`; historical WebFTP notes do
not satisfy this gate.

### 6. Create a short-lived owner approval

The Website Operator deliberately has no command that self-approves a release.
The owner supplies an external receipt conforming to the receipt schema:

```json
{
  "schema": "aureon.website-operator.owner-approval.v1",
  "decision": "approved",
  "scope": "static-website-release",
  "package_sha256": "<EXACT 64-CHARACTER PACKAGE SHA256>",
  "approved_at": "2026-07-26T10:40:00+01:00",
  "expires_at": "2026-07-26T12:40:00+01:00",
  "approved_by": "<OWNER NAME>",
  "note": "Approved only for this reviewed static-site package."
}
```

Approval is valid for no more than four hours and must match the exact package.

### 7. Gate, verify and explicitly deploy

```powershell
aureon-website gate `
  --audit-receipt <audit.json> `
  --package-receipt <package.json> `
  --backup-receipt <backup.json> `
  --approval-receipt <owner-approval.json>
```

Running `deploy` without `--execute` invokes the existing publisher in
verification-only mode:

```powershell
aureon-website deploy `
  --gate-receipt <deployment-gate.json> `
  --confirm-package-sha256 <EXACT SHA256>
```

Only the explicit action-time command may upload:

```powershell
aureon-website deploy `
  --gate-receipt <deployment-gate.json> `
  --confirm-package-sha256 <EXACT SHA256> `
  --execute
```

The explicit deploy requires `HOMEPL_FTPS_HOST`, `HOMEPL_FTPS_USER` and
`HOMEPL_FTPS_PASSWORD` in the current process. Values are neither printed nor
stored. After upload, the operator immediately runs the manifest read-back
against `https://aureonzorzatechnologies.pl/`. The final deployment state is
`deployed-and-verified-live` only when every path matches exactly or after
permitted text newline normalisation.

## Adding tools safely

The tool belt is configuration-driven, but not open-ended at runtime:

- audit commands are argument arrays checked into source control
- packaging, backup, publish and read-back point to reviewed repository tools
- no prompt can inject a shell string
- a new tool must declare whether it reads, mutates local source or changes
  external state
- any external-state tool must preserve the backup, approval, hash and
  read-back gates

This is how Aureon gains more design capability without gaining silent
publication authority.

## Verification

```powershell
python -m ruff check aureon/operator/website_operator.py
python -m mypy aureon/operator/website_operator.py
python -m pytest tests/test_website_operator.py -q
python -m aureon.operator.website_operator capabilities
python -m aureon.operator.website_operator inventory
python -m aureon.operator.website_operator audit
```

Receipts are written under `artifacts/website-operator/` by default. They are
runtime evidence, not source and not deployment authority by themselves.
