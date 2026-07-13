# Grant War Room Sheet Update Pending Reauth

Prepared: 2026-07-05

Target sheet: `https://docs.google.com/spreadsheets/d/1Nk5TwzX0PJcAlhoi9V0zOLEKsVN127roApdMjXNtgdM/edit`

Status: pending. Connector read/search works, but spreadsheet write failed with `ACCESS_TOKEN_SCOPE_INSUFFICIENT`. Reapply these rows after Google Drive/Sheets reauthorization with create/write scope.

## Evidence Register Rows

| Evidence type | Source name | Path or URL | Source type | What it supports | Use notes |
|---|---|---|---|---|---|
| Local corpus consolidation | LOCAL_DELTA_IMPORTED_MANIFEST_20260705.csv | C:/Users/user/Aureon_Work_Hub_20260705/00_INDEXES/LOCAL_DELTA_IMPORTED_MANIFEST_20260705.csv | Local hub index | 806 additional non-sensitive files imported from `.kimi_openclaw`, `.openclaw`, Claude memory notes, validation docs, and project-rainbow archive delta. | Use for grant evidence discovery and source traceability; do not attach raw private state or accounting files. |
| Drive/readback verification | DRIVE_SEARCH_VERIFICATION_20260705.md | C:/Users/user/Aureon_Work_Hub_20260705/02_DRIVE_SOURCE_INDEX/DRIVE_SEARCH_VERIFICATION_20260705.md | Local hub index | Live Drive readback for Grant War Room folder, uploaded archives, repo bundles, HNC/EPAS research files, and email PDF packs. | Confirms read/search access; upload/create remains blocked by DriveFiles.Create OAuth scope. |
| Grant data room archive | Aureon_Work_Hub_20260705_WITH_DELTA.tar | C:/Users/user/outputs/Aureon_Work_Hub_20260705_WITH_DELTA.tar | Local archive pending Drive upload | Single upload-ready archive of the consolidated hub including the continuation delta import and active field packs. | Final byte size and SHA-256 are in external sidecar `C:/Users/user/outputs/Aureon_Work_Hub_20260705_WITH_DELTA_MANIFEST.json`; upload after Drive reauth. |

## Source Register Rows

| Source | URL | Use |
|---|---|---|
| Drive Search Verification 20260705 | C:/Users/user/Aureon_Work_Hub_20260705/02_DRIVE_SOURCE_INDEX/DRIVE_SEARCH_VERIFICATION_20260705.md | Local verification record for `gaxlec@gmail.com` Drive search/readback, Grant War Room contents, repo archives, and upload-scope blocker. |
| Updated local hub archive with delta | C:/Users/user/outputs/Aureon_Work_Hub_20260705_WITH_DELTA.tar | Upload-ready archive that supersedes the older Drive hub archive once Drive create/upload scope is available. |
| Existing Drive hub archive | https://drive.google.com/file/d/1tZFDPqnIjF0C1UeBHqMozkcRWvKcPJgG/view?usp=drivesdk | Existing Drive upload of the pre-delta hub archive; keep as historical readback until WITH_DELTA archive is uploaded. |

## Application Tracker Rows

| ID | Application / task | Status | Priority | Owner | Target date | Blockers / dependencies | Next action |
|---|---|---|---|---|---|---|---|
| AUR-GRANT-013 | Upload updated hub archive with delta | Blocked | P0 | Gary + Codex | 2026-07-05 | Drive connector can read/search but cannot create/upload files; DriveFiles.Create returns ACCESS_TOKEN_SCOPE_INSUFFICIENT. | Reauthorize Google Drive connector with create/upload scope, then upload `C:/Users/user/outputs/Aureon_Work_Hub_20260705_WITH_DELTA.tar` and its manifest to the Grant War Room folder. |
| AUR-GRANT-014 | Grant-ready application field pack buildout | In progress | P0 | Codex | 2026-07-05 | Needs funder-specific text packs for Invest NI, InterTradeIreland, Next Wave, and EIC without unsupported claims. | Generate local field packs from the hub and map evidence attachments to each application route. |

## Comms Log Rows

| Date | Audience | Subject | Message / note | Status |
|---|---|---|---|---|
| 2026-07-05 | Internal | Delta consolidation complete | Imported 806 additional non-sensitive files into the local Aureon Work Hub, indexed the private large runtime state instead of copying it, verified Drive readback for repo/hub archives, and created an updated upload-ready hub archive with delta. | Logged |
| 2026-07-05 | Internal | Drive upload still blocked | Attempt to upload `LOCAL_AND_DRIVE_CONSOLIDATION_STATUS_20260705.md` failed with 403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT` on DriveFiles.Create. Search/read access works; create/upload scope must be reauthorized. | Action required |

## Validation Checklist Row

| Area | Check | Current status | Owner | Next validation action |
|---|---|---|---|---|
| Data room consolidation | Delta import and Drive archive readback recorded | Partial | Codex | Upload updated WITH_DELTA archive to Drive after connector reauthorization; keep sensitive/private state excluded unless explicitly approved. |
