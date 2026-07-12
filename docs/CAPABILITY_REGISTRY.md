# Aureon Capability Registry

Current tracked snapshot: 2026-07-13.

This registry turns the public capability table in [`../CAPABILITIES.md`](../CAPABILITIES.md)
into a machine-readable navigation contract. It connects each current capability
to surface references, resolved repo paths, runtime/API references, generated
artifact references, code-symbol references, related systems, public artifacts,
and broad end-user access routes.

Machine-readable registry:
[`capability_registry.json`](capability_registry.json), mirrored to
[`../frontend/public/aureon_capability_registry.json`](../frontend/public/aureon_capability_registry.json).

Generate and validate from repo root:

```text
python scripts/validation/generate_repo_navigation_index.py
python scripts/validation/generate_system_integration_map.py
python scripts/validation/generate_capability_registry.py
python scripts/validation/validate_repo_navigation_contract.py
```

## How To Use It

1. Use [`CAPABILITIES.md`](../CAPABILITIES.md) for the human-readable capability
   descriptions.
2. Use `capability_registry.json` when a UI, SaaS shell, or integrator needs to
   filter capabilities by system, source path, public artifact, generated
   artifact, runtime interface, code symbol, or broad access route.
3. Use [`SYSTEM_INTEGRATION_MAP.md`](SYSTEM_INTEGRATION_MAP.md) to move from a
   capability to its owning top-level systems and safety gates.
4. Use [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md) and
   [`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md) before hosted
   production exposure.

## Public Contract

The generated registry contains capability labels, summaries, path references,
runtime/API names, generated artifact names, code-symbol names, route IDs, and
counts only. It does not contain source file contents, credentials, environment
values, private runtime state, customer data, or local evidence exports.

## Resolution Rules

- Exact tracked paths are linked directly.
- Directory references are kept as directory entrypoints.
- Command-form references such as `file.py --flag` resolve to the underlying
  tracked file while preserving the command reference.
- Bare filenames are resolved against tracked file basenames where possible.
- Runtime URLs and `/api/*` references stay as runtime references.
- Expected generated artifacts under `state/`, `docs/audits/`,
  `frontend/public/`, and `ws_cache/` are classified separately from missing
  files.
- Code-symbol references are searched against tracked source roots and linked to
  matching source files where possible.
- Unresolved references remain visible so they can be reviewed instead of being
  silently dropped.
