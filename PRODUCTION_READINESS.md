# Production readiness

Live trading is never armed by the system. Evidence gates are never loosened. Those rules are enforced in the writer, the sandbox repair, and the self-coder before a patch is applied.

## Self-repair fail-safe

| Control | Effect |
|---|---|
| `AUREON_SELF_REPAIR_ENABLE` unset | Self-repair stays disabled |
| `state/self_repair_config.json` missing, unreadable, or `"enabled"` not `true` | Self-repair stops (`missing_config` or `self_repair_disabled`) |
| `AUREON_SELF_REPAIR_KILL=1` | Self-repair stops, even when enable and the config are set |
| Protected path or pattern | The write or patch is not applied. The review log flags it for human review |

Both the enable flag and the config file are required. Either one on its own does not start a repair.

## Denylist

Checked by `aureon/autonomous/self_repair_guard.py` before Queen writes, before sandbox edits, before `git apply` in `aureon/autonomous/aureon_internal_self_coder.py`, and before the coherence-gate director backs up or applies a diff.

- `AUREON_LIVE_TRADING` and other live or real-money flags
- evidence gates and HOLD/RELEASE logic
- position sizing
- `.env` and credential files

`AUREON_CODE_AUTO_APPROVE=1` does not mark those proposals approved and does not apply them.

## Where this was run

```
cd aureon-os-upstream && PYTHONPATH=. python3 -m pytest tests/test_sandbox_self_repair.py tests/test_protected_patch_denylist.py tests/test_safe_code_control.py tests/test_orca_windows_stdio.py -q --tb=line
................                                                         [100%]
16 passed
```

The market-data WebSocket notes remain in `aureon-os-upstream/docs/runbooks/PRODUCTION_READINESS.md` and `aureon-trading/docs/runbooks/PRODUCTION_READINESS.md`. They are not a switch for live trading.

## Twelve production layers

Checked 22 Oct 2026 from this workspace. PROVEN means a command in this environment passed. BLOCKED means the layer is not faked. Live trading stays off. `may_act` stays false. The HOLD gate and the self-repair denylist were not changed.

| Layer | Status | Proof or reason |
|---|---|---|
| Frontend | BLOCKED | `frontend_vite` did not start: the organ requires a local HTTP profile that is not present. `aureon-os-upstream/.github/workflows/frontend-ci.yml` exists and was not executed here. |
| APIs | PROVEN | `python3 -m pytest tests/test_fusion_http.py -q --tb=line` covers `/healthz`, bearer auth, and the disarmed status page. |
| DB/storage | PROVEN | Faculty state is the local store. `python3 -m aureon_fusion.fleet_launcher --check` reads `aureon_fusion/state/flight_health.json`. Hosted Postgres is not provisioned. |
| Auth | PROVEN | `tests/test_fusion_http.py` refuses a start without `AUREON_FUSION_API_TOKEN` and rejects a missing bearer token. |
| Hosting/deploy | BLOCKED | Needs Gary to choose and pay for a host. This environment does not deploy. |
| Cloud | BLOCKED | Needs Gary to choose a cloud project and credentials. No project is configured here. |
| CI/CD | PROVEN | `.github/workflows/fusion-ci.yml` pins `AUREON_LIVE_TRADING=0`. `.github/workflows/windows-contract.yml` runs the Windows voice and release contract on `windows-latest`. |
| Security/RLS | PROVEN | `tests/test_production_layers.py` finds `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY` in `aureon-os-upstream/supabase/migrations`. A live database has not enforced them. |
| Rate limiting | PROVEN | `aureon_fusion.http_service.allow` returns false after the configured limit. The HTTP suite returns 429. |
| Caching/CDN | PROVEN | `cached_status` serves a hit inside the TTL. A public CDN is not configured; that part is not claimed. |
| Load balancing/scaling | BLOCKED | `/healthz` is the probe a balancer would use, and no balancer or scaler is provisioned. Needs Gary to choose and pay for a host. |
| Error tracking/logs | PROVEN | Flight-recorder health and `tests/test_fusion_http.py` record errors locally and do not call a webhook. No third-party tracker is configured. |

Faculty launcher: `python3 -m aureon_fusion.fleet_launcher --check`. It exits 2 when `AUREON_LIVE_TRADING` is set or `aureon_fusion/state/capital_release.flag` exists. The unity supervisor in tmux session `unity-supervisor` is the process manager that keeps the paper-mode organs alive.

Exchange tests that arm a live executor are marked `live` and are excluded unless pytest is run with `-m live`. They are not part of the default suite. Voice and release contract tests also run on the Windows CI job.

## Gary-leckey/aureon-trading

That public MIT fork of Aureon OS was compared with parent `main` before anything was copied. Its `main` is already contained in the parent. The Windows stdout fix from `fix/windows-closed-stdout-orca` (`6b149e9eca`) was applied to the two current Orca entrypoints because they still wrapped `sys.stdout.buffer`. Branches that instruct `scripts/aureon_ignition.py --live`, add a personal payment URL, or rename the tree into `1_substrate/` were not applied. Live trading stays off. The denylist was not changed. `Gary-leckey/King-Skill-Extended-Cognition-Architecture-for-Scientific-LLM-Agents` and `Gary-leckey/Taorice` were not merged. See `MERGE_PLAN.md`.
