# Capability report

Commands below were run in this workspace on 22 October 2026. A result is recorded only after that run.

## Self-repair

| | |
|---|---|
| Where | `aureon_fusion/repair.py`, `aureon-os-upstream/aureon/autonomous/aureon_sandbox_self_repair.py`, guard in `aureon-os-upstream/aureon/autonomous/self_repair_guard.py`, writer in `aureon-os-upstream/aureon/queen/queen_code_architect.py` |
| Command | `python -m aureon_fusion.repair --root /tmp/plug-demo` |
| Result | **pass** |

Self-repair stays disabled unless `AUREON_SELF_REPAIR_ENABLE=1` and the project has `state/self_repair_config.json` with `{"enabled": true}`. `AUREON_SELF_REPAIR_KILL=1` or a missing config stops it.

The denylist is checked before a write or a patch is applied. Refused attempts are flagged `human_review` and are not written. The denylist covers `AUREON_LIVE_TRADING` and other live or real-money flags, evidence-gate and HOLD/RELEASE logic, position sizing, and `.env` or credential files. `AUREON_CODE_AUTO_APPROVE=1` does not approve or apply those paths.

The repair that ran here is an off-by-one in a pure utility: `band_offset` returned `1` and the test required `0`. The test file was not edited. A desk module whose tests wanted `position_qty` changed from `0` to `1` and `evidence_gate` changed from `HOLD` to `RELEASE` was not modified. That run returned `human_review`.

```
cd aureon-os-upstream && PYTHONPATH=. python3 -m pytest tests/test_sandbox_self_repair.py tests/test_protected_patch_denylist.py tests/test_safe_code_control.py -q --tb=line
...............                                                          [100%]
15 passed
```

`aureon/autonomous/aureon_internal_self_coder.py` still applies an approved patch only after the denylist check. With `AUREON_CODE_AUTO_APPROVE=1`, a patch that sets `AUREON_LIVE_TRADING`, writes `.env`, flips HOLD to RELEASE, or changes `position_qty` returns `protected_denylist` before `git apply`. A patch that changes `band_offset` from `return 1` to `return 0` still applies. The senior release review still raises `release_review_entrypoint_disabled_proposal_only` until a durable proposal vault exists.

## Fusion status and gates

| Capability | Where | Command | Result |
|---|---|---|---|
| Fusion status, live trading off | `aureon_fusion` | `python3 -m aureon_fusion` | **pass**, exit 0, `live_trading: false`, `may_act: false` |
| Layer join, synthetic evidence rejected | `aureon-os-upstream/aureon/organism/repository_layers.py` | `python3 -m pytest tests/test_fusion_join.py tests/test_public_field.py tests/test_fusion_http.py organism/test_public_market.py -q` | **pass**, 16 passed |
| Plant atlas and repository layers | `aureon-os-upstream` | `PYTHONPATH=. python3 -m pytest tests/test_repository_layers.py tests/bio/test_plant_atlas_*.py -q` | **pass**, 16 passed, 2 skipped (GPU backend needs torch) |
| Exchange rate limiter | `aureon-os-upstream/aureon/core/rate_limiter.py` | `PYTHONPATH=. python3 -m pytest tests/test_rate_limiter.py -q` | **pass**, 2 passed |
| Organ registry | `aureon_fusion/organ_registry.py` | `SERO_WORKSPACE=/workspace python3 -m aureon_fusion.organ_registry status` | **pass**, exit 0, organs stopped, capital pin DENY |
| Fusion HTTP auth, rate limit, health, error sink | `aureon_fusion/http_service.py` | included in the 16 tests above | **pass** |

## Gary-leckey/aureon-trading

The public fork's `main` is 45 commits behind `RA-CONSULTING/Aureon-OS` and has no commit of its own. The one fix still missing from the newest Orca files was `6b149e9eca`: stop wrapping `sys.stdout.buffer` on Windows. That change is in `aureon-os-upstream/aureon/bots/orca_complete_kill_cycle.py` and `aureon_radar/bots/orca_complete_kill_cycle.py`. The April documentation branch that points operators at `scripts/aureon_ignition.py --live` was not applied. Current ignition still returns HOLD. The protected-path denylist was not changed.

```
cd aureon-os-upstream && PYTHONPATH=. python3 -m pytest tests/test_sandbox_self_repair.py tests/test_protected_patch_denylist.py tests/test_safe_code_control.py tests/test_orca_windows_stdio.py -q --tb=line
................                                                         [100%]
16 passed
```

## Not runnable here

| Surface | Command | Result |
|---|---|---|
| Vite frontend | `npm run dev` in `aureon-os-upstream/frontend` | **exit 2**. `package.json` routes `dev`, `preview`, and `trade:real` through `npm run unavailable`. |
| Nexus server on this Node | `node --check sources/NEXUS-LIVE-FEED-/src/server.js` | **fail**. The file uses `import ... assert { type: 'json' }`, which Node 22.23.4 rejects. |
| Docker image | `docker build` | **not runnable**. `docker` is not installed on this machine. `Dockerfile` and `docker-compose.yml` are in the repo root. |
| Private source repos | GitHub API | **not retrieved**. `skaila-journey-platform`, `aureon-founder-mirror`, `aureon-quantum-bloom`, and `Aueron-Trading-Quantum-Quackers-War-Ready-Version-` returned HTTP 404 for this credential. The in-tree Quackers strategy module is still present. |
