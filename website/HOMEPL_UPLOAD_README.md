# Publish Aureon to Home.pl

This static website belongs to **R&A Consulting and Brokerage Services Ltd**
(company no. **NI696693**), trading as **Aureon Zorza Technologies**. Gary
Anthony Leckey retains the final owner/CEO veto. Never publish a personal
mailbox, credentials, private correspondence, internal financial records, or
unreviewed claims.

The canonical automated release sequence is:

`audit -> commit-bound build -> fresh served-root backup -> non-pruning FTPS upload -> exact read-back`

An upload, provider success message, local preview, or GitHub push does not by
itself prove publication.

## Canonical release commands

From the repository root:

```powershell
python -m scripts.website.audit_site --root website
$sourceCommit = (git rev-parse HEAD).Trim()
python -m scripts.website.build_package `
  --root website `
  --out artifacts/website-releases `
  --source-commit $sourceCommit
```

The build refuses a malformed commit, a commit different from checked-out
`HEAD`, or tracked/untracked `website/` changes not represented by that commit.
It creates a deterministic ZIP, an external companion checksum, and
`website_package/HOMEPL_FILE_HASHES.json`. The hash manifest records the size
and SHA-256 of every other package file and excludes only itself to avoid
recursive self-hashing; its own hash is in the companion checksum file.

## Fresh backup gate

Before any remote write:

1. Map the authenticated account to the current public Home.pl served root.
2. Do not assume `/` or `/public_html`; use the exact current provider mapping.
3. Create a fresh recursive backup with a non-zero manifest.
4. Retain the `aureon.homepl-backup-transfer.v1` completion receipt.

[`backup-homepl-ftps.ps1`](backup-homepl-ftps.ps1) is the audited read-only
backup tool. It has strict preflight and served-root bindings. If those bindings
do not match the current provider state, stop and treat Home.pl's provider
backup control as a named human host gate. Do not weaken the check, guess a
credential/root, or fabricate a receipt.

## One FTPS environment contract

The canonical Python deployer and Home.pl PowerShell tools use these names:

| Variable | Required | Meaning |
|---|---:|---|
| `HOMEPL_FTPS_HOST` | yes | FTPS hostname only |
| `HOMEPL_FTPS_USER` | yes | approved FTPS account |
| `HOMEPL_FTPS_PASSWORD` | yes | process-only password; never logged or committed |
| `HOMEPL_FTPS_REMOTE_ROOT` | yes | exact authenticated served root |
| `HOMEPL_FTPS_PORT` | yes | exact authenticated port; never inferred |
| `HOMEPL_FTPS_MODE` | yes | exactly `explicit` or `implicit` |
| `HOMEPL_FTPS_CERT_THUMBPRINT` | PowerShell only | optional certificate pin |

Retained Home.pl configuration evidence points to implicit FTPS on port 990.
The Python uploader currently implements explicit FTPS only and fails closed on
an implicit live run before opening a socket. Until an implicit connector is
implemented and authenticated, use the Home.pl provider route as the named host
gate. Do not guess port 21 or silently change protocol.

Preview the exact plan with no network operation:

```powershell
python -m scripts.website.ftp_deploy `
  --package artifacts/website-releases/website_package `
  --dry-run
```

After a verified fresh backup, the live command additionally names its exact
transfer receipt:

```powershell
python -m scripts.website.ftp_deploy `
  --package artifacts/website-releases/website_package `
  --backup-receipt C:\absolute\path\to\backup-transfer.json
```

The deployer verifies the local package first. It also checks that the backup
receipt names the audited `backup-homepl-ftps.ps1` producer, binds that script's
hash, and carries a sorted `Path,Bytes,Sha256` manifest matching the exact
downloaded backup directory, counts, byte total, root and freshness. A
hand-authored receipt cannot stand in for rollback evidence. The deployer then
creates/overwrites only listed release files. It never deletes remote files;
`--prune` is always refused.

## Mandatory read-back

Capture all served package paths from the authenticated root or public domain
into an isolated directory, then run the offline comparison:

```powershell
python -m scripts.website.readback `
  --package artifacts/website-releases/website_package `
  --readback-dir C:\absolute\path\to\captured-served-root
```

The exact directory comparison checks the remote hash manifest itself, every
manifest record by byte length and SHA-256, and rejects any unexpected file in
the captured served-root mirror. That prevents a mixed July-era/V45 file set
from passing after a non-pruning upload.

The programmatic HTTP comparison checks every expected V45 path already
captured, but cannot discover an unknown stale URL that was not requested. It is
expected-path evidence, not exact served-root inventory proof. Neither helper
opens a network connection or records a body, URL, header, cookie, account, or
credential. TLS/cache checks, critical route rendering, claim lint,
accessibility, visual regression, and Core Web Vitals remain separate required
evidence before publication can be called complete.

## Manual Home.pl alternative

WebFTP ZIP upload/unzip is a host-gate alternative, not a second build or
verification stack. It must use the exact audited ZIP, exact served root, fresh
backup, and the same `HOMEPL_FILE_HASHES.json` read-back. The legacy
[`publish-homepl-ftps.ps1`](publish-homepl-ftps.ps1) CSV flow and retired
[`build-homepl-package.ps1`](build-homepl-package.ps1) are not the canonical V45
automated path and must not be mixed with the new manifest.

Do not change DNS, SSL assignment, domain ownership, pre-existing FTP accounts,
or unrelated provider settings as part of a normal website-file release.

## Current publication boundary

The last recorded V28 attempt was incomplete. V45 remains a local candidate
until a fresh served-root backup, exact upload, full per-file public read-back,
and the remaining browser/claim/vitals gates all pass.
