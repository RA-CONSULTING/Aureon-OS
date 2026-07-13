# Aureon Repo Archives - Verified 2026-07-05

Status: published and verified in Google Drive on 2026-07-05.

Drive folder: https://drive.google.com/drive/folders/1UBtVIJku0Ax9PyH9D0Lt9q7WwB3zVHIr

## Uploaded Archive Set

1. Raw local Git history bundles
   - File: AureonLocalGitHistoryBundles_RAW_20260705.tar
   - Drive: https://drive.google.com/file/d/11oDMxnlewlJwXgpLPeKR5Bod4QdFdtBx/view?usp=drivesdk
   - Size: 1241515520 bytes
   - SHA-256: 99E332CE7E1CDBEBF9FA3128052913402C08F5F97FD96888B23FD1E19810E9F1
   - Contains: five verified local all-ref Git bundles.

2. Fresh GitHub mirror all-ref bundles
   - File: AureonGitHubMirrorBundles_ALLREFS_20260705.tar
   - Drive: https://drive.google.com/file/d/19A5T5BSdS-hjeMWl3XyQY3ZlaUsfMYaT/view?usp=drivesdk
   - Size: 366811648 bytes
   - SHA-256: 061BD20D27779451FC8E6C04EDCB875D55F720508BB324201BA4A7770C6697A7
   - Contains: RA-CONSULTING/aureon-trading, RA-CONSULTING/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-, RA-CONSULTING/NEXUS-LIVE-FEED-.

3. Sanitized local source snapshots and repo evidence bundle
   - File: AureonReposDriveBundle_SANITIZED_20260705.tar
   - Drive: https://drive.google.com/file/d/1AHKGb82z4FDIE2pccAAmB0oTFrSxfGCm/view?usp=drivesdk
   - Size: 1527144960 bytes
   - SHA-256: CDA331A830559F6D46D16DBDB91E2BA0F9EEE676FEB4FC4E6DCF1EEB7162BDAC
   - Contains: sanitized local source snapshots, GitHub mirror bundles, metadata, and restore README.

## Raw Local Git Histories Covered

- aureon-trading
- aureon-trading-clean
- aureon-trading-github-latest-20260701
- aureon-trading-integrated-main-20260508
- aureon-trading-latest

## Local Source Snapshots Without Raw Git Bundle

- aureon-trading-loveavblr (skipped_no_verified_head)
- project-rainbow (skipped_no_verified_head)

## Public GitHub Repositories Covered

- RA-CONSULTING/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-
- RA-CONSULTING/aureon-trading
- RA-CONSULTING/NEXUS-LIVE-FEED-

## Restore

Extract an archive:

```powershell
tar -xf AureonLocalGitHistoryBundles_RAW_20260705.tar
```

Restore a Git bundle:

```powershell
git clone .\local_git_bundles\aureon-trading_local_allrefs_20260705.bundle .\aureon-trading-restored
```

Use the sanitized source bundle for grant/evidence review. Use the RAW local history archive only when full local refs/history are needed.
