# Drive Search Verification

Checked: 2026-07-05

Connected account: `gaxlec@gmail.com`

## Working Folder

- Folder: Aureon Grant War Room - 2026-07-04
- URL: `https://drive.google.com/drive/folders/1UBtVIJku0Ax9PyH9D0Lt9q7WwB3zVHIr`

The folder currently contains the live Grant War Room spreadsheet, operating logs, master work index, repo archive index, and the five prepared email PDF packs for Invest NI, InterTradeIreland, academic validation, EIC Accelerator, and Next Wave.

## Verified Drive Archives

| File | Drive ID | Size | URL |
|---|---|---:|---|
| `AureonReposDriveBundle_SANITIZED_20260705.tar` | `1AHKGb82z4FDIE2pccAAmB0oTFrSxfGCm` | 1,527,144,960 | `https://drive.google.com/file/d/1AHKGb82z4FDIE2pccAAmB0oTFrSxfGCm/view?usp=drivesdk` |
| `AureonLocalGitHistoryBundles_RAW_20260705.tar` | `11oDMxnlewlJwXgpLPeKR5Bod4QdFdtBx` | 1,241,515,520 | `https://drive.google.com/file/d/11oDMxnlewlJwXgpLPeKR5Bod4QdFdtBx/view?usp=drivesdk` |
| `AureonGitHubMirrorBundles_ALLREFS_20260705.tar` | `19A5T5BSdS-hjeMWl3XyQY3ZlaUsfMYaT` | 366,811,648 | `https://drive.google.com/file/d/19A5T5BSdS-hjeMWl3XyQY3ZlaUsfMYaT/view?usp=drivesdk` |
| `Aureon_Work_Hub_20260705.tar` | `1tZFDPqnIjF0C1UeBHqMozkcRWvKcPJgG` | 646,486,016 | `https://drive.google.com/file/d/1tZFDPqnIjF0C1UeBHqMozkcRWvKcPJgG/view?usp=drivesdk` |
| `HUB_DRIVE_READBACK_20260705.json` | `1bB2DdBpPS-3EXJvBVN_FTw66XA4DgAnt` | 1,478 | `https://drive.google.com/file/d/1bB2DdBpPS-3EXJvBVN_FTw66XA4DgAnt/view?usp=drivesdk` |

## Search Terms Checked

- `Aureon`
- `HNC`
- `Druid`
- `Leckey`
- `EPAS`
- `AureonReposDriveBundle`
- `Aureon_Work_Hub`
- direct folder-child search for folder ID `1UBtVIJku0Ax9PyH9D0Lt9q7WwB3zVHIr`

The search surfaced the expected Grant War Room, HNC whitepapers/audits, EPAS/HNC related files, Atlantic substrate files, Source Oscillator paper, historical HNC/Aureon trading framework docs, poster HTML files, and the prepared email PDFs. It also surfaced personal/legal/banking files on identity-style searches; those remain excluded from grant/research use unless Gary approves the exact file and recipient.

## Upload Status

Read/search access works. Upload/create does not currently work through the Drive connector:

- Attempted upload: `LOCAL_AND_DRIVE_CONSOLIDATION_STATUS_20260705.md`
- Target folder: `1UBtVIJku0Ax9PyH9D0Lt9q7WwB3zVHIr`
- Result: `403 Forbidden`
- Error reason: `ACCESS_TOKEN_SCOPE_INSUFFICIENT`
- Google method blocked: `google.apps.drive.v3.DriveFiles.Create`

Until the Drive connector is reauthorized with create/upload scope, new local hub continuation files remain local and should be uploaded manually or after reauth.
