# Aureon System Integration Map

Current tracked snapshot: 2026-07-13.

This map is the bridge between the repo-wide sitemap and a SaaS integration
view. It answers the practical question: which systems exist, what capabilities
they support, which entry points matter, which public artifacts the frontend can
read, and which safety gate applies before a system is exposed to end users.

Machine-readable map: [`system_integration_map.json`](system_integration_map.json),
mirrored to
[`../frontend/public/aureon_system_integration_map.json`](../frontend/public/aureon_system_integration_map.json).

Generate and validate from repo root:

```text
python scripts/validation/generate_repo_navigation_index.py
python scripts/validation/generate_capability_registry.py
python scripts/validation/generate_system_integration_map.py
python scripts/validation/validate_repo_navigation_contract.py
```

## How To Use It

1. Start with [`REPO_SITEMAP.md`](REPO_SITEMAP.md) for the top-level structure.
2. Use [`END_USER_ACCESS_MAP.md`](END_USER_ACCESS_MAP.md) for task-based routes.
3. Use `system_integration_map.json` to bind each repo system to current
   implementation capabilities from [`CAPABILITIES.md`](../CAPABILITIES.md),
   access routes, entrypoints, public artifacts, validation references, and
   safety gates.
4. Use [`SAAS_INTEGRATION_READINESS.md`](SAAS_INTEGRATION_READINESS.md) for env,
   deployment, and auth boundaries.
5. Use [`SUPABASE_HARDENING_REVIEW.md`](SUPABASE_HARDENING_REVIEW.md) before
   exposing hosted Supabase functions.

## Public Contract

The generated system integration map contains paths, labels, counts,
implementation capability IDs, access-route IDs, safety gates, and readiness
statuses only. It does not contain source contents, credentials, environment
values, private runtime state, customer data, or local evidence exports.

## Coverage

The current generated map covers:

| Contract Item | Current Value |
|---|---:|
| Top-level systems | 29 |
| Current implementation capabilities | 29 |
| Mapped implementation capabilities | 29 |
| Unmapped implementation capabilities | 0 |
| System-capability links | 198 |
| Access routes | 13 |
| Mapped access routes | 13 |

In each system row, `capability_ids` are concrete capability registry IDs from
[`capability_registry.json`](capability_registry.json). `access_route_ids` are
the broader end-user routes from
[`end_user_access_map.json`](end_user_access_map.json). Keeping both fields
separate lets investors and integrators see both the product capability and the
user-facing path to reach it.

## Readiness Terms

| Status | Meaning |
|---|---|
| `mapped_for_end_user_navigation` | Public or local navigation surface is mapped and safe to expose as metadata. |
| `integration_ready_with_production_gates` | The system is a SaaS/deploy surface, but production gates still apply. |
| `operator_controlled_before_saas_exposure` | The system is useful, but live or sensitive workflows must stay under operator control. |
| `preserved_for_audit_not_current_product_surface` | The system is retained for provenance and should not be treated as current product copy. |
| `mapped_with_review_gate` | The system is mapped, but requires review before hosted or mutable use. |

## Validation Contract

The validator checks that the docs and frontend public mirrors are identical,
that the map covers every top-level system in `docs/repo_sitemap.json`, that
every current capability registry ID is mapped to at least one system, that
the tracked count matches `git ls-files`, and that the public mirror is
secret-free.
