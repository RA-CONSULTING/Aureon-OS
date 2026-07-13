# Aureon Frontend Unification Plan

- Generated: `2026-05-15T18:32:02.336938+00:00`
- Repo: `C:\Users\user\aureon-trading-integrated-main-20260508`
- Status: `unification_plan_ready_with_security_blockers`

## Summary

- `screen_count`: `7`
- `migration_action_count`: `5`
- `missing_screen_capability_count`: `2`
- `source_surface_count`: `870`
- `security_blocker_count`: `2`
- `frontend_surface_count`: `676`
- `supabase_function_count`: `101`

## Canonical Screens

| Screen | Sources | Backend | Missing | Safety |
| --- | ---: | ---: | --- | --- |
| `Overview` | 247 | 4 | none | observation |
| `Trading` | 412 | 20 | none | live orders remain behind runtime trading gates |
| `Accounting` | 633 | 6 | none | Companies House filing; HMRC submission; tax or penalty payment |
| `Research` | 124 | 5 | none | observation |
| `SaaS Security` | 263 | 20 | Security blockers must be fixed before production promotion. | production deployment approval; third-party authorization scope signoff; 2 security blocker surface(s) visible in inventory. |
| `Self-Improvement` | 6 | 0 | none | code apply/restart approval when required |
| `Admin` | 242 | 20 | Security blockers must be fixed before production promotion. | credential entry; payment approval; official filing approval; 2 security blocker surface(s) visible in inventory. |

## Migration Actions

| Priority | Action | Reason |
| ---: | --- | --- |
| 1 | `fix_security_blockers` fix_before_production | Security blocker surfaces cannot be hidden by the new shell. |
| 2 | `build_unified_shell` canonicalize | Create one observation shell with the seven canonical screens. |
| 3 | `triage_orphaned_frontend` migrate_keep_or_archive | Important frontend surfaces exist but are not reachable from the current app entrypoint. |
| 4 | `triage_backend_functions` link_or_archive | Backend functions exist without a confirmed frontend caller. |
| 5 | `legacy_dashboard_transition` embed_migrate_or_keep_link | Legacy dashboards stay available until their useful panels are migrated. |

## Duplicate Groups

- `accounting_outputs`: `73` surfaces
- `auth_and_credentials`: `17` surfaces
- `dashboards`: `46` surfaces
- `trading_controls`: `48` surfaces

## Safety Contract

- `human_observes_aureon_works`: `True`
- `live_trading_requires_existing_runtime_gates`: `True`
- `official_filing_and_payments_manual_only`: `True`
- `credentials_status_visible_secret_values_hidden`: `True`
- `security_blockers_visible`: `True`
- `legacy_dashboards_preserved_until_migrated`: `True`

## Notes

- The unified frontend is an observation and command surface; Aureon remains the worker.
- Old dashboards are not removed in this pass; they are linked, embedded, or migrated after inventory proof.
- Manual-only actions stay visible and explicit instead of being automated silently.
