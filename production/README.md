# Aureon production release status

Production installation, desktop packaging, container launch, release upload,
port exposure, and live-trading setup are on terminal **HOLD**.

The four checked-in installer entrypoints now execute only the isolated,
fixed-target bootstrap for `production-supervisor`. They do not download an
executable, build or start a container, create a shortcut, expose a port, read
exchange credentials, or claim a dashboard is running. The Windows release
workflow likewise performs only a HOLD-receipt audit and has no artifact or
release upload permission.

Expected result: non-zero exit with a registered receipt containing
`process_start_authorized: false`. A production release requires a reviewed
artifact identity, signed provenance, native process containment, external HNC
head anchoring, and provider-side deployment read-back; none is asserted here.
