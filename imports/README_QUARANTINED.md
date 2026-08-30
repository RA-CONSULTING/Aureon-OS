# Imported source quarantine

Everything below `imports/` is preserved historical or provenance material. It
is not part of the canonical Aureon runtime, packaging input, Python import
path, deployment source, or launcher navigation.

In particular,
`Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/` is a complete,
runnable historical checkout. Its Dockerfiles, Compose files, provider clients,
launchers, scripts, configuration, and dependency declarations are retained as
evidence only. Do not run them from the canonical checkout, install their
dependencies into a canonical environment, add the snapshot to `PYTHONPATH` or
`sys.path`, use it as a working directory, or copy it into a deployment image.

The repository-root `.dockerignore` excludes both `imports/` and `archive/`.
Canonical launchers remain under `scripts/launchers/`; root deployment and
package controls must resolve only to current root-owned paths. Documentation,
inventories, and audit evidence may name quarantined material, but an executable
runtime surface may not select it.

Any future reactivation requires a separate, explicit review and migration into
current root-owned modules. Inspection of the preserved source should be
offline and isolated from production credentials, provider sessions, and
canonical state. This packaging quarantine does not certify the imported code
as safe and does not by itself reclassify its economic-mutation sites.
