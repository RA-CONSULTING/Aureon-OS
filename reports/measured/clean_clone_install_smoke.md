# Clean clone, install.sh, guarded smoke

Measured local boot of the documented five-minute path. Live trading stayed off. This is a stack smoke. It is a local stamp. It is not an authenticated deployment receipt, and it does not report the system alive.

Verdict: **pass** on commit `7de64166bc532170a5a95a842e623a4b894cebd2`.
Public tip `bb04503119681adcf832f3c3e9b0cbf09fc7a938`: **fail** (measured, before the supervisor path fix).
Release boundary: **HOLD**. `go_live_clear`: **false**. Orange badge: unchanged.
Live trading: false. Orders placed: false. Exchange keys: unset. External LLM: false.

Machine: Ubuntu 24.04.5 LTS, Linux 6.12.94+ x86_64.
Python 3.12.3 (`/usr/bin/python3`). Node v22.23.4. npm 10.9.9.
Node binary: `/home/ubuntu/.nvm/versions/node/v22.23.4/bin/node`.

## Prerequisite

The image did not have Debian/Ubuntu `python3-venv`. The README quick start says to install it before `./install.sh`.

```bash
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip
```

Installed: `python3-venv 3.12.3-0ubuntu2.1`, `python3.12-venv 3.12.3-1ubuntu0.17` (measured).

## Commands

Public HEAD, measured with `git ls-remote origin HEAD`:

`bb04503119681adcf832f3c3e9b0cbf09fc7a938`

Pin commit `34864ff0547d2cff03e707414743a3b0cc8770b5` was fetched from `https://github.com/RA-CONSULTING/Aureon-OS.git`. `aureon/__init__.py` at that pin is blob `5141a6ed0a0e1ee1cf8861b73071029481df07bd` (measured).

The smoke shell was `env -i` with `HOME`, `USER`, `LANG`, `LC_ALL`, and a PATH that contained the Node binary above plus the system directories. No `.env` file was in the clone. Agent and GitHub credentials were not in that shell. `./install.sh` sets `AUREON_AUTONOMY_MODE=guarded` inside `scripts/plug_and_play.py`.

### 1. Depth-1 public clone — fail

```bash
git clone --depth 1 https://github.com/RA-CONSULTING/Aureon-OS.git
./install.sh --smoke
```

This is a narrower clone than the README's `git clone`. HEAD `bb045031`, tree `9ce6c0252d27617fb2a7775b7197537efa2388d7`. Shell exit **1**.

The MCP child exited 1. Its log: `ImportError: aureon is not an aureon module path`. `PinnedAureonFinder` asks git for `34864ff:aureon/__init__.py`. That commit is not in a depth-1 clone (measured).

A later `--depth 1 --bare` clone of the fix commit `7de64166` also lacks that pin (`git cat-file` exit 128). That check did not re-run `./install.sh --smoke`.

### 2. Full clone of the public tip — fail

```bash
git clone --no-local file:///agent/repos/Aureon-OS
# HEAD bb045031, same tree 9ce6c025 as the GitHub depth-1 clone
./install.sh --smoke
```

Pin `34864ff` is an ancestor of this HEAD, so a default full clone contains it. MCP, operator, frontend, HNC, and QGITA printed. Cognition returned HTTP 500 `{"error": "ModuleNotFoundError", "ok": false}`. The log ends with `SMOKE FAILED` and `cognition endpoint`. A shell exit code was not captured for this run.

Cause, measured by replaying the script path: `python scripts/plug_and_play.py` sets `sys.path[0]` to `scripts/`, and `import aureon` raises `ModuleNotFoundError: No module named 'aureon'`. `PYTHONPATH` is applied to the child processes. Assigning `os.environ["PYTHONPATH"]` does not rebuild this process's `sys.path`. `/api/cognition` imports `aureon` here.

### 3. Full clone after the path fix — pass

```bash
git clone --no-local file:///agent/repos/Aureon-OS
# HEAD 7de64166bc532170a5a95a842e623a4b894cebd2
./install.sh --smoke
```

Tree `5a3c7f3682addcdf80cc260b82dfbb91037945ba`. No `.venv`, no `frontend/node_modules`, no `.env` before the command. Shell exit **0**. Started `2026-11-05T20:47:16Z`, ended `2026-11-05T20:47:35Z`.

Nineteen seconds on this machine. The pip log says `Using cached` for the wheels, because an earlier run on this machine had already downloaded them. `npm ci` added 548 packages in 5s. This duration is a warm-cache measurement.

```text
{"autonomy_mode": "guarded", "banner": "aureon-plug", "exchange_keys": "unset", "external_llm": false, "live_trading": false, "ok": true, ...}
SMOKE healthz 200 autonomy_mode=guarded exchange_keys=unset external_llm=false live_trading=false ok=true
SMOKE operator 200 providers offline
SMOKE readyz 200 ready=true
SMOKE frontend 200 aureon_os=True
SMOKE mcp_initialize {"name": "aureon-public", "version": "1.30.0"}
SMOKE mcp_tools auris_coherence hnc_reality_step qgita_analyze
SMOKE hnc {"coherence": 0.7739191103121901, "enable_multiverse": false, "status": "inferred"}
SMOKE qgita {"detection_rate": "HOLD", "false_alarm_rate": "HOLD", "ftcp_count": 0, "status": "complete"}
SMOKE cognition live_trading=false orders_placed=false trade_readiness.verdict=fail release_boundary=HOLD
SMOKE cognition qgita derived_rates_verdict=HOLD on_hnc_rates_verdict=HOLD
SMOKE cognition auris_joined_to_lambda.verdict=HOLD go_live=HOLD
SMOKE PASSED
```

The full lines are in `reports/measured/clean_clone_install_smoke.json`. Log sha256 `6465c3a293c1ad093f929b7f059eb66782daf5b3dd89652ab1b01ed3e66d9830`. Process ids in the banner are from this run: operator 4700, mcp 4701, frontend 4702.

After `SMOKE PASSED`, CPython printed `resource_tracker: There appear to be 1 leaked shared_memory objects to clean up at shutdown`. The shell exit stayed 0.

`git status --porcelain` was empty. The smoke did not change the pin, the release-boundary module, or the go-live files.

## Fix

`scripts/plug_and_play.py` now calls `ensure_checkout_importable()` so the supervisor puts the checkout and `mcp/` on `sys.path` before `evaluate_brain`. Child `PYTHONPATH` is unchanged. `AUREON_LIVE_TRADING` stays `0`. `AUREON_AUTONOMY_MODE` stays `guarded`.

`scripts/plug_and_play.py` sha256 at measurement: `074958ec277ae9cbd88dc3a3f0faa635d71f41431d8d36f4208e71dce8667497`.

`pytest tests/test_plug_and_play_static.py tests/test_credential_bootstrap.py` passed on the plug virtualenv.

## Still HOLD

- `LocalDevelopmentReleaseBoundaryV02` still has four `"production_ready": False` literals. File sha256 `8691b938dc8df60e89c7360c90c24079eda259754a0ea36810cce925580e05f4`, unchanged by the smoke.
- README badge remains release-boundary HOLD.
- `go_live_clear` is false in `evidence/output/hnc_head_anchor.json` (top level and `measurement.go_live_clear`), `measured/go_live_stage6_provenance.json`, and `measured/go_live_stage6_source_census.json`. `aureon/evidence/hnc_anchor.py` still has two `"go_live_clear": False` literals. Those four file hashes were unchanged by the smoke. The hashes in the JSON are the measured tree. See the rebase note for the two stage-6 files that `29fab7f2` replaced.
- Trade readiness inside the cognition report is **fail** on 166 paper labels, and that report's release boundary is **HOLD**. QGITA rates are **HOLD**. Auris joined to Λ(t) is **HOLD**. The smoke gate accepts that report. The gate does not promote it.
- Receipts 2, 3, 4, and 5 stay HOLD. This file is a local install smoke. The clock is this machine's UTC.

Started from `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. Git HEAD at the passing measurement: `7de64166bc532170a5a95a842e623a4b894cebd2`. The commit that adds this file is not a second measurement.

## Rebase onto 29fab7f2

This branch was rebased onto `29fab7f21fc93da40224566dd8f34faacb3d74d4`. The path fix replayed as `799f1a4d98699a5590140f69b4d6483f27b2b5fe`. The original receipt replayed as `3703529745775003969f1132dc1b7ff800e1053e`. `scripts/plug_and_play.py` is the same bytes as the measurement (`074958ec277ae9cbd88dc3a3f0faa635d71f41431d8d36f4208e71dce8667497`).

No `./install.sh --smoke` was run on `29fab7f2` or on the replayed commits. `git_head_at_measurement` stays `7de64166bc532170a5a95a842e623a4b894cebd2`.

`29fab7f2` sets `PINNED_COMMIT` to `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. The smoke measured pin `34864ff0547d2cff03e707414743a3b0cc8770b5`. The depth-1 failure in this receipt is that earlier pin.

`29fab7f2` replaces the two stage-6 files. On this worktree, read after the rebase and not by a new smoke:

- `measured/go_live_stage6_provenance.json` sha256 `33adba393aec6047e2dcc8cf90e5ad3984aa158355b5205c65f2f1109c7b4d94`, `go_live_clear` false
- `measured/go_live_stage6_source_census.json` sha256 `2bc09488106c4a6a4d1fd231dc27ff8baab12c597a1f17b1dacf249eea8cc4f4`, `go_live_clear` false

`evidence/output/hnc_head_anchor.json`, `aureon/evidence/hnc_anchor.py`, and `aureon/plumber/release_boundary_v02.py` still match the measurement hashes. `production_ready` stays false. Release boundary stays **HOLD**. `go_live_clear` stays false.
