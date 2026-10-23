# Twelve layers

The public default is full mode (`AUREON_AUTONOMY_MODE` unset). Trading is live when the operator's own exchange keys are in `.env`. `AUREON_AUTONOMY_MODE=guarded` puts the denylist back. That switch is documented in `AUTONOMY.md`.

## Self-repair fail-safe

| Control | Effect |
|---|---|
| `AUREON_SELF_REPAIR_ENABLE` unset | Self-repair stays disabled |
| `state/self_repair_config.json` missing, unreadable, or `"enabled"` not `true` | Self-repair stops (`missing_config` or `self_repair_disabled`) |
| `AUREON_SELF_REPAIR_KILL=1` or `state/SELF_REPAIR_KILL` | Ignored. Neither one stops self-repair or order dispatch |
| Protected path or pattern, guarded mode | The write or patch is not applied. The review log flags it for human review |
| `AUREON_AUTONOMY_MODE=full` in local state only | Live flags, the HOLD/RELEASE gate, `may_act`, and position sizing may be edited. Credentials stay refused |

Both the enable flag and the config file are required. Either one on its own does not start a repair.

## Denylist

Checked by `aureon/autonomous/self_repair_guard.py` before Queen writes, before sandbox edits, before `git apply` in `aureon/autonomous/aureon_internal_self_coder.py`, and before the coherence-gate director backs up or applies a diff.

- `AUREON_LIVE_TRADING` and other live or real-money flags
- evidence gates and HOLD/RELEASE logic
- position sizing
- `.env` and credential files

In guarded mode, `AUREON_CODE_AUTO_APPROVE=1` does not mark those proposals approved and does not apply them. In full mode it does, except for credential material. A self-patch whose tests fail stays applied.

## Where this was run

```
PYTHONPATH=. python3 -m pytest tests/test_sandbox_self_repair.py tests/test_protected_patch_denylist.py tests/test_safe_code_control.py tests/test_orca_windows_stdio.py -q --tb=line
```

That command is from the repository root. There is no separate upstream checkout directory in this tree.

The market-data WebSocket notes remain in `docs/runbooks/PRODUCTION_READINESS.md` and `aureon-trading/docs/runbooks/PRODUCTION_READINESS.md`. They are not a switch for live trading.

## Twelve layers

Checked 22 Oct 2026. Nothing is PROVEN without a green CI run. GitHub Actions on `c90d087f` did not start: every Actions job failed in about two seconds because the account is locked due to a billing issue. Local smoke is not that green run.

The four jobs that have to finish green on the hosted runner are `fusion tests` (Aureon Fusion CI), `compile + offline test suite (3.12)` (Aureon CI), `Supabase functions and RLS policy contract`, and `Frontend typecheck, lint, build, and E2E`. The same frontend specs also sit in Frontend CI as `strict tier (build · shell lint · smoke E2E)`. Those commands pass on this machine: fusion pytest (one skip, reason `optional torch backend not installed`), `compileall` plus the offline product suite, the four Supabase contract tests with `--disable-socket`, and the frontend typecheck, lint, build, and 19 Playwright specs. A hosted run ID is added under "Green hosted run IDs" only after that job finishes green. The RLS contract is still policy text: a green copy of it would not be a live Postgres apply.

Green hosted run IDs:

- none. On `b563282c` the hosted jobs failed in about two seconds and are not green. The annotation on each is: "The job was not started because your account is locked due to a billing issue."
  - `fusion tests`: run [39870227758](https://github.com/RA-CONSULTING/Aureon-OS/actions/runs/39870227758), job 120142518451
  - `compile + offline test suite (3.12)`: run [39870227765](https://github.com/RA-CONSULTING/Aureon-OS/actions/runs/39870227765), job 120142518498
  - `Supabase functions and RLS policy contract`: run [39870228056](https://github.com/RA-CONSULTING/Aureon-OS/actions/runs/39870228056), job 120142519768
  - `Frontend typecheck, lint, build, and E2E`: run [39870228056](https://github.com/RA-CONSULTING/Aureon-OS/actions/runs/39870228056), job 120142519784
  - `strict tier (build · shell lint · smoke E2E)`: run [39870227838](https://github.com/RA-CONSULTING/Aureon-OS/actions/runs/39870227838), job 120142518804

Secret rotation is not a merge blocker. `ROTATE_KEYS.md` is still the inventory (provider, type, file, commit, never the value). Gitleaks still guards new commits, in the pre-commit hook and in the tree scan. History is not rewritten from this branch.

Hosting is the end user's choice: any machine that can run `make up` or `make compose`. No cloud project and no provider credential is required. The public default stays guarded: live trading stays off and `may_act` stays false until the owner sets `AUREON_AUTONOMY_MODE=full` in local state. See `AUTONOMY.md`.

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

Ten of the twelve layers are local-only. CI/CD is missing. Security/RLS is policy text only.

The economic-mutation census still lists live-capable unguarded blockers in `scripts/validation/economic_mutation_allowlist.json`. Every live-capable-unguarded-blocker entry is an inventory classification, not a guard. These entries are safe only while live trading is off. Each one must get a structural guard before live trading can ever be armed. Setting `AUREON_LIVE_TRADING` or `AUREON_FUSION_ARM_LIVE`, or creating `aureon_fusion/state/capital_release.flag`, while any of those entries remain fails the gate `unguarded_economic_mutations_block_live_trading`.

Faculty launcher: `python3 -m aureon_fusion.fleet_launcher --check`. It exits 2 when `AUREON_LIVE_TRADING` is set or `aureon_fusion/state/capital_release.flag` exists. The unity supervisor in tmux session `unity-supervisor` is the process manager that keeps the paper-mode organs alive.

Exchange tests that arm a live executor are marked `live` and are excluded unless pytest is run with `-m live`. They are not part of the default suite. Every `live` and `windows` marker states its reason (`tests/test_quarantined_marker_reasons.py`). The optional plant-atlas GPU test is skipped with the reason `optional torch backend not installed`. Voice and release contract tests also run on the Windows CI job.

## Gary-leckey/aureon-trading

That public MIT fork of Aureon OS was compared with parent `main` before anything was copied. Its `main` is already contained in the parent. The Windows stdout fix from `fix/windows-closed-stdout-orca` (`6b149e9eca`) was applied to the two current Orca entrypoints because they still wrapped `sys.stdout.buffer`. Branches that instruct `scripts/aureon_ignition.py --live`, add a personal payment URL, or rename the tree into `1_substrate/` were not applied. Live trading stays off. The denylist was not changed. `Gary-leckey/King-Skill-Extended-Cognition-Architecture-for-Scientific-LLM-Agents` and `Gary-leckey/Taorice` were not merged. See `MERGE_PLAN.md`.
