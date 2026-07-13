# Aureon Repo Drive Bundle - 2026-07-05

This bundle preserves Aureon repo/source material for Drive publication.

## Included

- `local_source_snapshots/`
  - Sanitized local working-tree source snapshots for:
    - `aureon-trading`
    - `aureon-trading-clean`
    - `aureon-trading-github-latest-20260701`
    - `aureon-trading-integrated-main-20260508`
    - `aureon-trading-latest`
    - `aureon-trading\loveavblr`
    - `project-rainbow`
    - supporting Aureon content folders: `AureonResearch`, `AureonObsidianVault`, `substack_posts`, `aureon-json-backup`, `aureon-update-preservation-20260508`
- `github_mirror_bundles/`
  - Fresh all-ref GitHub mirror bundles from `RA-CONSULTING`:
    - `RA-CONSULTING/aureon-trading`
    - `RA-CONSULTING/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-`
    - `RA-CONSULTING/NEXUS-LIVE-FEED-`
- `metadata/`
  - Local repo inventory, GitHub repo metadata, bundle verification results, and source snapshot verification.

## Sanitization

The local source snapshots intentionally exclude runtime/generated bulk and obvious secret-file patterns:

- Git internals, virtualenvs, dependency/build/cache folders.
- `logs`, `state`, `.claude`, `queen_backups`, and similar runtime folders.
- `*.jsonl`, embedded `*.zip`, `*.bsp`, compiled/cache/log files.
- `.env*`, `.kraken_nonce`, key/certificate patterns, and common credentials/secrets/token JSON patterns.

The generated local Git bundles in `C:\Users\user\outputs\aureon_repo_drive_20260705\local_git_bundles` were verified locally, but are not included in this upload bundle because full Git history can carry secret material that path-level source sanitization cannot remove.

## Restore Notes

Restore a GitHub mirror bundle with:

```powershell
git clone <bundle-file> <target-folder>
```

Extract a local source snapshot with:

```powershell
tar -xzf <snapshot-file> -C <target-folder>
```

The local source snapshots are intended for grant/evidence preservation and working-source recovery, not for restoring excluded runtime logs or secrets.
