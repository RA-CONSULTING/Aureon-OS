# Native package build — HOLD

No Aureon executable may currently be built, started, distributed, or
registered for autostart from this checkout. The legacy launcher is a terminal
HOLD shim and the post-build helper refuses to select or execute a binary.

A future package requires a reviewed native outer protection boundary,
reproducible source measurements, signed artifacts, isolated credential
custody, revocation and rollback procedures, and independently verified runtime
receipts. Shipping a key file beside an executable is not an approved custody
model.
