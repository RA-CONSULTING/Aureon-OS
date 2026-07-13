# Aureon Local and Drive Consolidation Status

Created: 2026-07-05

Purpose: working status for consolidating Aureon/Gary Leckey research, local downloads, local repo state, and Drive-published repo archives into one operating hub.

## Operating Hub

- Local hub: `C:\Users\user\Aureon_Work_Hub_20260705`
- Main local corpus: `01_LOCAL_RESEARCH_CORPUS`
- New delta imports: `06_LOCAL_DELTA_IMPORTS_20260705`
- Grant working packs: `04_GRANT_WORKING_PACKS`
- Sensitive exclusion index: `05_SENSITIVE_EXCLUDED_INDEX`

## Current Coverage

- Original local research corpus: 3,219 files, about 640.6 MB.
- New delta import: 806 files, 78,862,137 bytes.
- Total imported/collated local working files now represented in hub folders: 4,025 files, about 719.5 MB, excluding referenced large private runtime state.
- Existing sensitive/accounting exclusion manifest remains active and is not grant-safe by default.
- Updated local upload-ready archive: `C:\Users\user\outputs\Aureon_Work_Hub_20260705_WITH_DELTA.tar`.
- Final archive byte size and SHA-256 are recorded in the external sidecar manifest next to the archive so the archive does not contain its own changing checksum.

## New Delta Import Collections

See `LOCAL_DELTA_IMPORTED_MANIFEST_20260705.csv` and `LOCAL_DELTA_IMPORTED_SUMMARY_20260705.csv`.

| Collection | Count | Bytes | Treatment |
|---|---:|---:|---|
| `kimi_openclaw_workspace_research` | 783 | 55,965,587 | Copied into `06_LOCAL_DELTA_IMPORTS_20260705` |
| `openclaw_grant_research_downloads` | 14 | 11,638,355 | Copied into `06_LOCAL_DELTA_IMPORTS_20260705` |
| `project_rainbow_archive_delta` | 1 | 10,799,890 | Copied into `06_LOCAL_DELTA_IMPORTS_20260705` |
| `aureonresearch_validation_delta` | 1 | 222,105 | Copied into `06_LOCAL_DELTA_IMPORTS_20260705` |
| `project_rainbow_validation_delta` | 1 | 222,105 | Copied into `06_LOCAL_DELTA_IMPORTS_20260705` |
| `claude_project_memory_notes` | 5 | 12,064 | Copied into `06_LOCAL_DELTA_IMPORTS_20260705` |
| `repo_drive_bundle_metadata_delta` | 1 | 2,031 | Copied into `06_LOCAL_DELTA_IMPORTS_20260705` |

## Repo Archive Coverage

The raw local repo working trees produced more than 100,000 keyword matches. They were not duplicated file-by-file into the delta import because they are already covered by verified Drive/local archive work:

- Sanitized repo/source Drive archive: `AureonReposDriveBundle_SANITIZED_20260705.tar`
- Raw local Git history Drive archive: `AureonLocalGitHistoryBundles_RAW_20260705.tar`
- Public GitHub mirror Drive archive: `AureonGitHubMirrorBundles_ALLREFS_20260705.tar`
- Repo index: `03_REPO_ARCHIVE_INDEX\REPO_ARCHIVE_INDEX_20260705.md`

Use the sanitized archive for grant/partner work. Treat raw Git history as private backup because Git history can preserve secrets or deleted sensitive material.

## Drive Upload Gap

The original `Aureon_Work_Hub_20260705.tar` is already in Drive, but it predates the continuation-pass delta import. The updated local archive with delta is ready for upload, but Drive upload/create is currently blocked by Google OAuth scope:

- Blocked method: `google.apps.drive.v3.DriveFiles.Create`
- Error: `ACCESS_TOKEN_SCOPE_INSUFFICIENT`
- Reupload target: Aureon Grant War Room folder `1UBtVIJku0Ax9PyH9D0Lt9q7WwB3zVHIr`

## Private Large Runtime State

The following large local-state file was indexed, hashed, and left in place instead of copied into grant-working folders:

- `C:\Users\user\project-rainbow\state\aureon_repo_singularity_vault_packet.json`
- Size: 747,488,746 bytes
- SHA-256: `96C9BAD70D6BD67A791A50C0972AD8CBF3FE2E64ECC8E03E12E8AD8B6A3292EB`
- Index: `LOCAL_STATE_LARGE_REFERENCE_20260705.csv`

Reason: the file contains repeated `secret_policy` and accounting labels. It may be important private runtime evidence, but it is not safe for grants, email, or partner packs without exact action-time approval.

## Practical Working Rule

Use the hub as the default source of truth:

1. For grant writing, start with `04_GRANT_WORKING_PACKS`.
2. For research evidence, use `01_LOCAL_RESEARCH_CORPUS`, `06_LOCAL_DELTA_IMPORTS_20260705`, and the source manifests.
3. For repo evidence, cite the sanitized repo archive and the public GitHub mirror archive.
4. For private finance/accounting/runtime state, use only the exclusion and large-reference indexes until Gary approves a specific file for a specific recipient or portal.

## Active Application Materials

- `04_GRANT_WORKING_PACKS\ACTIVE_APPLICATION_FIELD_PACKS_20260705.md`: funder-facing draft text for Invest NI, InterTradeIreland, Next Wave, and EIC.
- `04_GRANT_WORKING_PACKS\ACTIVE_APPLICATION_FIELD_PACKS_20260705.json`: machine-readable version for the Aureon operator workflow.
- `04_GRANT_WORKING_PACKS\SELF_UPDATE_DRAFT_NO_SUBMISSION_20260705.eml`: internal self-update draft; not sent.
- `00_INDEXES\GRANT_WAR_ROOM_SHEET_UPDATE_PENDING_REAUTH_20260705.md`: exact Sheet rows to add after Drive/Sheets write scope is reauthorized.
