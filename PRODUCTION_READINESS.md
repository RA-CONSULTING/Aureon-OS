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

Checked 22 Oct 2026. PROVEN means the self-hosted stack shows the layer. Hosting is the end user's choice: any machine that can run `make up` or `make compose`. No cloud project and no provider credential is required. Live trading stays off. `may_act` stays false. The HOLD gate and the self-repair denylist were not changed.

Deploy:

```
make up
```

That path does not use Docker. It applies the Postgres RLS scripts, starts Redis, two API replicas, the local HTTP frontend, nginx, and the error sink.

```
make compose
python3 scripts/selfhost_smoke.py
```

`make compose` builds `deploy/selfhost/docker-compose.yml`. The operator steps are in `deploy/selfhost/README.md`. The smoke test is `.github/workflows/selfhost-ci.yml`. The loopback bearer token is `local-selfhost-token`. It is not a provider key.

| Layer | Status | Proof or reason |
|---|---|---|
| Frontend | PROVEN | self-hosted `aureon/operator/local_http_profile.py` serves `frontend/index.html`. `scripts/selfhost_smoke.py` requires HTTP 200 from `/` and `/app/`. |
| APIs | PROVEN | self-hosted `aureon_fusion.http_service` behind nginx. `tests/test_fusion_http.py` and `scripts/selfhost_smoke.py` cover `/healthz`. |
| DB/storage | PROVEN | self-hosted Postgres. `scripts/selfhost_smoke.py` reads `relrowsecurity` on `schumann_resonance_data` after the init scripts. |
| Auth | PROVEN | self-hosted bearer check. `tests/test_fusion_http.py` and `scripts/selfhost_smoke.py` require `AUREON_FUSION_API_TOKEN` and reject a missing bearer token. |
| Hosting/deploy | PROVEN | self-hosted. Hosting is the end user's choice. `make up` and `make compose` are the deploy. `scripts/selfhost_smoke.py` requires `"hosting": "self-hosted"`. |
| Cloud | PROVEN | self-hosted. No cloud project is required. The same compose file is the cloud-shaped run, proven by `.github/workflows/selfhost-ci.yml`. |
| CI/CD | PROVEN | self-hosted `.github/workflows/selfhost-ci.yml` brings up compose and runs `scripts/selfhost_smoke.py`. `.github/workflows/fusion-ci.yml` pins `AUREON_LIVE_TRADING=0`. `.github/workflows/windows-contract.yml` runs the Windows contract on `windows-latest`. |
| Security/RLS | PROVEN | self-hosted. `supabase/migrations/20260811210525_lock_down_legacy_public_tables.sql` is applied to a live Postgres. `scripts/selfhost_smoke.py` checks `ENABLE ROW LEVEL SECURITY` is on, `deny_direct_client_access` exists, `anon` cannot read, and `service_role` can. |
| Rate limiting | PROVEN | self-hosted nginx `limit_req` plus `aureon_fusion.http_service.allow`. `tests/test_fusion_http.py` expects 429. `scripts/selfhost_smoke.py` expects nginx 429. |
| Caching/CDN | PROVEN | self-hosted Redis. `cached_status` returns `cache_layer=redis`. `scripts/selfhost_smoke.py` reads the Redis key. A public CDN is not claimed. |
| Load balancing/scaling | PROVEN | self-hosted nginx round-robin across `api_a` and `api_b`, both with health checks and `restart: unless-stopped`. `scripts/selfhost_smoke.py` requires both replica ids. |
| Error tracking/logs | PROVEN | self-hosted JSON logs and `deploy/selfhost/error_sink.py`. `tests/test_fusion_http.py` records a local exception. `scripts/selfhost_smoke.py` requires the sink to store `fusion_error_sink_test`. |

Faculty launcher: `python3 -m aureon_fusion.fleet_launcher --check`. It exits 2 when `AUREON_LIVE_TRADING` is set or `aureon_fusion/state/capital_release.flag` exists. The unity supervisor in tmux session `unity-supervisor` is the process manager that keeps the paper-mode organs alive.

Exchange tests that arm a live executor are marked `live` and are excluded unless pytest is run with `-m live`. They are not part of the default suite. Voice and release contract tests also run on the Windows CI job.

## Gary-leckey/aureon-trading

That public MIT fork of Aureon OS was compared with parent `main` before anything was copied. Its `main` is already contained in the parent. The Windows stdout fix from `fix/windows-closed-stdout-orca` (`6b149e9eca`) was applied to the two current Orca entrypoints because they still wrapped `sys.stdout.buffer`. Branches that instruct `scripts/aureon_ignition.py --live`, add a personal payment URL, or rename the tree into `1_substrate/` were not applied. Live trading stays off. The denylist was not changed. `Gary-leckey/King-Skill-Extended-Cognition-Architecture-for-Scientific-LLM-Agents` and `Gary-leckey/Taorice` were not merged. See `MERGE_PLAN.md`.
