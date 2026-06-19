# Azyra Audit Scan Batch - 2026-06-19

This note records the controlled batch package built from:

`C:\Users\Gary.Leckey\OneDrive - SFG Forwarding Ltd\Desktop\audit scans 1st batch.pdf`

The batch workbook and evidence are held locally under:

`C:\Users\Gary.Leckey\OneDrive - SFG Forwarding Ltd\Documents\sfg azrya intergrations\outputs\aureon_goal_contract_dispatcher\audit_scans_1st_batch_20260619`

## Built Outputs

- Control workbook: `Azyra_Audit_Scans_1st_Batch_OCR_Control.xlsx`
- Batch-ready aggregate CSV: `azyra_batch_ready_aggregate.csv`
- Summary JSON: `audit_scan_batch_summary.json`
- Rendered scan evidence: `rendered_pages`, `upright_pages_final`, and `contact_sheets_final`
- Workbook previews: `workbook_previews`

## Batch Counts

- Decoded scan rows: `428`
- Ready source rows: `283`
- Batch-ready aggregate rows: `277`
- Held review rows: `140`
- Excluded rows: `5`
- Pending rows: `0`
- Ready quantity total: `725`
- Held quantity total: `419`

Rows are only included in the `Azyra_Batch_File` workbook sheet when the visual/OCR decode, master-code validation, and batch status are ready. Held rows remain outside the upload file.

## Live Status

Status: `prepared_not_posted`

The live Azyra stock-count upload has not been submitted. Aureon restored Azyra to the WMS menu and captured evidence, but RemoteApp menu activation did not open `Stock Checks Monitor` or known WMS menu items from the automation route. The batch upload route/schema must still be confirmed inside Azyra before any live stock mutation is made.

## Guardrail

Do not repurpose the current-balance adjustment runner for this batch. This audit is a stock-count upload package, not a decrease/increase adjustment batch.

