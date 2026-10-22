# Twelve layers

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
PYTHONPATH=. python3 -m pytest tests/test_sandbox_self_repair.py tests/test_protected_patch_denylist.py tests/test_safe_code_control.py tests/test_orca_windows_stdio.py -q --tb=line
```

That command is from the repository root. There is no separate upstream checkout directory in this tree.

The market-data WebSocket notes remain in `docs/runbooks/PRODUCTION_READINESS.md` and `aureon-trading/docs/runbooks/PRODUCTION_READINESS.md`. They are not a switch for live trading.

## Twelve layers

Checked 22 Oct 2026. Nothing is PROVEN without a green CI run. GitHub Actions on `c90d087f` did not start: every Actions job failed in about two seconds because the account is locked due to a billing issue. Local smoke is not that green run.

The four jobs that have to finish green on the hosted runner are `fusion tests` (Aureon Fusion CI), `compile + offline test suite` (Aureon CI, Python 3.12), `Supabase functions and RLS policy contract`, and `Frontend typecheck, lint, build, and E2E`. Their commands pass on this machine. A hosted run ID is linked in the list below only after that job finishes green.

Green hosted run IDs:

- none yet

Secret rotation is not a merge blocker. `ROTATE_KEYS.md` is still the inventory (provider, type, file, commit, never the value). Gitleaks still guards new commits, in the pre-commit hook and in the tree scan. History is not rewritten from this branch.

Hosting is the end user's choice: any machine that can run `make up` or `make compose`. No cloud project and no provider credential is required. Live trading stays off. `may_act` stays false. The HOLD gate and the self-repair denylist were not changed.

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

| Layer | Status | What exists, and why it is not PROVEN |
|---|---|---|
| Frontend | local-only | `aureon/operator/local_http_profile.py` can serve `frontend/index.html`. No green CI run. |
| APIs | local-only | `aureon_fusion.http_service` answers `/healthz` on a machine that runs the stack. No green CI run. |
| DB/storage | local-only | Compose and `make up` can start Postgres. No green CI run. |
| Auth | local-only | The fusion service rejects a missing bearer token when it is run locally. No green CI run. |
| Hosting/deploy | local-only | `make up` and `make compose` are the deploy. Hosting is the end user's choice. No green CI run. |
| Cloud | local-only | No cloud project is required. The compose file is not a green CI run. |
| CI/CD | missing | Workflow files exist, including `.github/workflows/selfhost-ci.yml`. The runners did not start. |
| Security/RLS | policy text only | The SQL is `supabase/migrations/20260811210525_lock_down_legacy_public_tables.sql` plus the earlier `ENABLE ROW LEVEL SECURITY` migrations under `supabase/migrations/`. It still has to be enforced and tested against a live Postgres in the compose stack on a green CI run. |
| Rate limiting | local-only | nginx `limit_req` and `aureon_fusion.http_service.allow` exist. No green CI run. |
| Caching/CDN | local-only | Redis caching exists in the local stack. A public CDN is not claimed. No green CI run. |
| Load balancing/scaling | local-only | nginx is configured for `api_a` and `api_b`. No green CI run. |
| Error tracking/logs | local-only | JSON logs and `deploy/selfhost/error_sink.py` exist. No green CI run. |

Faculty launcher: `python3 -m aureon_fusion.fleet_launcher --check`. It exits 2 when `AUREON_LIVE_TRADING` is set or `aureon_fusion/state/capital_release.flag` exists. The unity supervisor in tmux session `unity-supervisor` is the process manager that keeps the paper-mode organs alive.

Exchange tests that arm a live executor are marked `live` and are excluded unless pytest is run with `-m live`. They are not part of the default suite. Every `live` and `windows` marker states its reason (`tests/test_quarantined_marker_reasons.py`). The optional plant-atlas GPU test is skipped with the reason `optional torch backend not installed`. Voice and release contract tests also run on the Windows CI job.

## Gary-leckey/aureon-trading

That public MIT fork of Aureon OS was compared with parent `main` before anything was copied. Its `main` is already contained in the parent. The Windows stdout fix from `fix/windows-closed-stdout-orca` (`6b149e9eca`) was applied to the two current Orca entrypoints because they still wrapped `sys.stdout.buffer`. Branches that instruct `scripts/aureon_ignition.py --live`, add a personal payment URL, or rename the tree into `1_substrate/` were not applied. Live trading stays off. The denylist was not changed. `Gary-leckey/King-Skill-Extended-Cognition-Architecture-for-Scientific-LLM-Agents` and `Gary-leckey/Taorice` were not merged. See `MERGE_PLAN.md`.
