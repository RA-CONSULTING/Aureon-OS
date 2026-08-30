# Owner Source Reconciliation Decision

Use this only after `aureon-website live-drift` reports
`live-drift-detected` and after a fresh Home.pl backup has been verified with
`aureon-website verify-backup`.

Its purpose is narrow: the owner may choose either the current **local**
canonical source or one exact **fresh verified live backup** as the baseline
for one future staged design candidate. It does not merge, promote, apply,
package, upload, publish, delete, access credentials, or mutate `website/`.
It is not the package-hash release approval required later in the Website
Operator flow.

Create the owner-supplied JSON below at
`artifacts/website-operator/owner-source-reconciliations/<decision>.json`.
Replace every placeholder with the exact hashes from the two existing receipts.
Set `expires_at` no more than four hours after `approved_at`.

## Retain the local canonical source (v1)

This existing contract is unchanged. The verified backup preserves the live
record, but the candidate is copied from `website/`.

```json
{
  "schema": "aureon.owner-source-reconciliation-decision.v1",
  "decision": "approved",
  "scope": "successor-staged-design-candidate",
  "source_selection": "retain-local-canonical-source",
  "reconciliation_receipt_sha256": "<EXACT LIVE-RECONCILIATION RECEIPT SHA256>",
  "reconciliation_selected_tree_sha256": "<EXACT SELECTED LOCAL TREE SHA256>",
  "backup_receipt_sha256": "<EXACT VERIFIED-BACKUP RECEIPT SHA256>",
  "backup_tree_sha256": "<EXACT VERIFIED-BACKUP TREE SHA256>",
  "approved_at": "<ISO-8601 WITH TIMEZONE>",
  "expires_at": "<ISO-8601 WITH TIMEZONE, MAXIMUM FOUR HOURS LATER>",
  "approved_by": "<OWNER NAME>",
  "note": "Local source is selected only for one staged candidate. The live production record is preserved by the verified backup.",
  "authority": {
    "scope": "owner-controlled local-source selection after observed public website drift",
    "canonical_website_mutation": "none by this decision or a design agent",
    "release_eligible": false,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "release_authority": "WebsiteOperator owner gate only"
  }
}
```

## Use the exact verified live backup (v2)

Use v2 only when the Website Operator `verified-backup` receipt contains all of
the following source evidence:

- `schema` is `aureon.website-operator.backup.v1`;
- `state` is `verified-backup`;
- `method` is `homepl-ftps` under the current exact-identity verifier;
- `source_assertion` is `Authenticated Home.pl document-root download`;
- `remote_root` is exactly `/`;
- an authenticated Home.pl owner-panel read-back identifies the exact
  non-secret host/account binding and maps that account to the intended domain;
  matching public bytes without this provider identity evidence remain
  ambiguous and fail closed;
- `backup_directory` is an absolute ordinary directory below the active
  repository's `artifacts/homepl-backups/` tree;
- `manifest` is an absolute ordinary single-link file below the repository's
  `artifacts/` tree and outside the downloaded document root;
- `manifest_sha256`, `tree_sha256`, `file_count`, and `total_bytes` bind the
  complete download.
- `ftp_host_id`, `ftp_host_sha256`, `ftp_account_sha256`, and
  `ftp_binding_sha256` bind the exact authenticated endpoint without recording
  the raw account;
- `preflight_receipt`, `root_mapping_receipt`, and `transfer_receipt` hashes
  bind the exact `/`, fresh public reconciliation, audited backup script and
  read-only source run;
- the authenticated root mapping matches public HTTPS `/index.html` byte count
  and SHA-256, transfer start and end observations match the same listing and
  root file, and the downloaded `index.html` matches those bytes;
- `complete_manifest_membership` and `ordinary_single_link_files_only` are
  true, while `remote_write_methods_used` and `credentials_recorded` are
  false.

The backup observation must be no more than four hours before approval.

```json
{
  "schema": "aureon.owner-source-reconciliation-decision.v2",
  "decision": "approved",
  "scope": "successor-staged-design-candidate",
  "source_selection": "use-verified-live-backup",
  "reconciliation_receipt_sha256": "<EXACT LIVE-RECONCILIATION RECEIPT SHA256>",
  "reconciliation_selected_tree_sha256": "<EXACT SELECTED LOCAL TREE SHA256>",
  "backup_receipt_sha256": "<EXACT VERIFIED-BACKUP RECEIPT SHA256>",
  "backup_tree_sha256": "<EXACT VERIFIED-BACKUP TREE SHA256>",
  "backup_directory": "<EXACT ABSOLUTE BACKUP DIRECTORY FROM RECEIPT>",
  "backup_manifest": "<EXACT ABSOLUTE MANIFEST PATH FROM RECEIPT>",
  "backup_manifest_sha256": "<EXACT BACKUP MANIFEST SHA256>",
  "approved_at": "<ISO-8601 WITH TIMEZONE>",
  "expires_at": "<ISO-8601 WITH TIMEZONE, MAXIMUM FOUR HOURS LATER>",
  "approved_by": "<OWNER NAME>",
  "note": "The exact fresh verified live backup is selected only for this staged candidate.",
  "authority": {
    "scope": "owner-controlled verified-live-backup source selection after observed public website drift",
    "canonical_website_mutation": "none by this decision or a design agent",
    "release_eligible": false,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "release_authority": "WebsiteOperator owner gate only"
  }
}
```

For v2, candidate control rechecks the exact decision and receipt hashes,
manifest bytes, every declared file byte count and SHA-256, complete directory
membership, Website Operator tree hash, remote root, expiry, and source
stability. All source, manifest, decision, receipt, and candidate paths must be
ordinary non-link/non-reparse paths; files must have one hard link. The work
order binds source kind, absolute source root, manifest, receipt tree and
candidate-baseline tree. Staging copies only those manifest-bound backup files
into `artifacts/website-candidates/`, then checks the source and candidate
trees again.

The selected document root is also an intake boundary. It may contain only the
supported public static file set plus the intentional public `.htaccess`.
Environment-file variants, private-key/container formats, SSH key names,
server executables, and files containing recognised private-key or API-key
patterns block the candidate before any bytes are copied. Findings report only
paths and pattern classes, never credential values.

Any mismatch blocks creation, staging, validation, or later current receipt
verification. There is no fallback to `website/`, a different backup, or a
guessed production baseline.
