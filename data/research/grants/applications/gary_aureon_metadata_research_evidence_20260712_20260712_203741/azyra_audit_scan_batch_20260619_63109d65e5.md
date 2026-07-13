# Azyra Audit Scan Batch - Public Capability Note

This public note documents the scan-to-batch capability without exposing customer files, local paths, stock codes, counts, or live operational evidence.

## Capability

Aureon can turn warehouse audit scans into a controlled Azyra-ready workbook by:

- rendering scan pages into review images,
- running OCR/transcription passes,
- validating stock codes against the stock master,
- grouping quantities by stock/UOM/location,
- separating ready rows from held rows,
- producing a human-readable workbook,
- and creating a batch-ready upload sheet only from rows that pass validation.

## Public-Safe Outputs

The public repository should only describe the output types:

- OCR control workbook,
- batch-ready aggregate CSV,
- review-hold register,
- rendered scan/contact-sheet evidence,
- summary JSON,
- and human-readable workbook previews.

Do not commit the customer's source scan PDF, decoded stock rows, local evidence paths, customer stock codes, warehouse locations, or live upload evidence.

## Batch Gate

Rows are eligible for upload only when:

- the visual/OCR decode is clear,
- the stock master validates the stock code,
- the location and quantity are reviewable,
- the row is not duplicated or contradicted,
- and the batch route/schema has been confirmed inside Azyra.

Held rows remain outside the upload file until separately resolved.

## Guardrail

Do not repurpose the current-balance adjustment runner for scan-count upload work. Audit-scan work is a stock-count/import package, not a decrease/increase adjustment batch.
