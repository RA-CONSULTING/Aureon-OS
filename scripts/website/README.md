# Aureon website release tooling

This directory is the single automated release stack for the static site in
[`website/`](../../website/):

`audit -> commit-bound build -> fresh backup gate -> non-pruning FTPS upload -> exact read-back`

An upload is not publication proof. The release is complete only when the
read-back comparison passes for the exact package.

## 1. Audit

```powershell
python -m scripts.website.audit_site --root website
```

The deterministic audit fails on broken internal links/assets, invalid JSON or
JSON-LD, sitemap/canonical drift, and the static accessibility/SEO contracts it
implements. It is not a substitute for the separate claim, browser, a11y, or
Core Web Vitals gates.

## 2. Build an exact release

The source commit is mandatory. In a Git worktree it must equal checked-out
`HEAD`, and the bounded `website/` tree must be clean. An uncommitted public file
cannot be described as belonging to a commit.

```powershell
$sourceCommit = (git rev-parse HEAD).Trim()
python -m scripts.website.build_package `
  --root website `
  --out artifacts/website-releases `
  --source-commit $sourceCommit
```

The build writes:

- `website_package/` with `index.html` at its root;
- `website_package/HOMEPL_PACKAGE_MANIFEST.txt`, which names the exact source
  commit and package contract;
- `website_package/HOMEPL_FILE_HASHES.json`, a sorted SHA-256 record for every
  other package file, including the summary manifest;
- `aureon-zorza-website.zip`, produced with deterministic ordering and
  timestamps; and
- `aureon-zorza-website.zip.sha256.txt`, the external companion containing the
  ZIP hash and the hash of `HOMEPL_FILE_HASHES.json`.

`HOMEPL_FILE_HASHES.json` intentionally excludes itself to avoid recursive
self-hashing. Its own SHA-256 is in the external companion.

For byte-identical reproduction, also pass the same `--created-at` value. A
standalone test fixture outside Git can build with an explicit valid commit, but
the manifest labels that binding `declared-only-isolated-source`; a real
repository build is labelled `verified-git-head-clean-site`.

## 3. Create and verify a fresh backup

Before any remote write, map the authenticated Home.pl served root and create a
fresh recursive backup with a non-zero manifest. The audited backup tool is
[`website/backup-homepl-ftps.ps1`](../../website/backup-homepl-ftps.ps1). It
emits an `aureon.homepl-backup-transfer.v1` receipt only after a complete,
read-only transfer and manifest verification.

Do not assume that the root is `/` or `/public_html`. The exact current provider
mapping controls. If the existing backup tool's strict root/preflight contract
does not match the current provider mapping, stop and use the Home.pl provider
backup as a named human host gate; do not weaken the mapping check or fabricate
a receipt.

## 4. Plan and deploy without pruning

The Python deployer and the audited PowerShell tools use one environment-name
contract:

| Variable | Required | Meaning |
|---|---:|---|
| `HOMEPL_FTPS_HOST` | yes | FTPS hostname only |
| `HOMEPL_FTPS_USER` | yes | temporary or approved FTPS account |
| `HOMEPL_FTPS_PASSWORD` | yes | process-only secret; never logged |
| `HOMEPL_FTPS_REMOTE_ROOT` | yes | exact authenticated served root |
| `HOMEPL_FTPS_PORT` | yes | exact authenticated port; never inferred from mode |
| `HOMEPL_FTPS_MODE` | yes | exactly `explicit` or `implicit` |
| `HOMEPL_FTPS_CERT_THUMBPRINT` | PowerShell only | optional pinned certificate thumbprint |

Retained Home.pl configuration evidence points to implicit FTPS on port 990.
The Python uploader currently implements only explicit FTPS and therefore
refuses an implicit live run before opening a socket. Until an implicit
connector is implemented and authenticated, use the Home.pl provider route as
the named host gate. Do not silently substitute explicit port 21.

Dry-run still requires the target binding and process-only credentials because
it prints the exact authenticated-account plan, but it performs no network
operation:

```powershell
python -m scripts.website.ftp_deploy `
  --package artifacts/website-releases/website_package `
  --dry-run
```

A live upload additionally requires the fresh backup transfer receipt:

```powershell
python -m scripts.website.ftp_deploy `
  --package artifacts/website-releases/website_package `
  --backup-receipt C:\absolute\path\to\backup-transfer.json
```

The deployer verifies the local package against its per-file manifest before
opening a connection. It also verifies that the backup receipt was produced by
the checked `website/backup-homepl-ftps.ps1`, that its deterministic CSV
`Path,Bytes,Sha256` manifest matches the exact downloaded directory, and that
its counts, byte totals, root and freshness agree. A hand-authored receipt or a
manifest detached from the backed-up files is refused. The deployer
creates/overwrites package files only. Pruning and remote deletion are disabled;
`--prune` is always refused.

## 5. Compare exact read-back

Capture the served-root files through the authenticated operator or fetch the
public paths into an isolated directory, then compare without credentials or
network access:

```powershell
python -m scripts.website.readback `
  --package artifacts/website-releases/website_package `
  --readback-dir C:\absolute\path\to\captured-served-root
```

The directory helper verifies `HOMEPL_FILE_HASHES.json` itself, every listed file
by size and SHA-256, and the absence of unexpected files in the downloaded
served-root mirror. This exact-mirror rule prevents a mixed release from passing
when non-pruning upload leaves stale public files.

`compare_http_observations()` verifies every expected package path from already
captured status/body objects. It cannot discover an unknown stale URL that was
not requested, so it is expected-path evidence, not proof of an exact served-root
file set. Reports never contain bodies, URLs, headers, cookies, or credentials.

TLS, cache headers, public route rendering, visual regression, accessibility,
claim lint, and Core Web Vitals remain separate mandatory release evidence.

## Manual provider alternatives

Home.pl WebFTP ZIP upload/unzip is a manual host-gate alternative, not a second
release stack. It must use the exact audited ZIP, the same fresh backup gate,
the exact served root, and the same per-file read-back comparison. The legacy
`website/publish-homepl-ftps.ps1` CSV flow and
`website/build-homepl-package.ps1` are not the canonical V45 automated path.
Do not mix their legacy manifests with `HOMEPL_FILE_HASHES.json`.

## Focused verification

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -m pytest -p no:cacheprovider tests/test_website_tooling.py -q
python -m ruff check scripts/website tests/test_website_tooling.py
python -m mypy --strict scripts/website/build_package.py scripts/website/ftp_deploy.py scripts/website/readback.py
```
