# Off-HOLD stage 0 baseline

This pack freezes the starting line. It records the HOLDs that are true at checkout `c68a89d2a184d99582bb24310b91e024323a212c`. It lifts none of them.

Do not edit this directory. A later stage adds a new directory under `reports/measured/` and cites these hashes. `reports/measured/index.json` and the other measured proof files are unchanged. SHA-256 hashes of the files in this pack, excluding the manifest itself, are in `MANIFEST.sha256`.

`docs/runbooks/GO_LIVE_HARDENING.md` is unchanged. Its outcome stays `HOLD`.

## Identity

| Item | Value |
| --- | --- |
| Stage-0 checkout | `c68a89d2a184d99582bb24310b91e024323a212c` |
| Checkout subject | Pin public MCP / Aureon tree to post-#232 main (#233) |
| Checkout tree | `5e3637100d03aabc6979f2479c1b40593907bb2c` |
| Published pin | `34864ff0547d2cff03e707414743a3b0cc8770b5` |
| Pin object | commit: Add fixed-seed HNC, Auris, and QGITA evidence runs (#232) |
| Pin is an ancestor of the checkout | true |
| `aureon/` tree at HEAD | `3ba0cab4a5e193b01943e5e6e0be25077ff759f6` |
| `aureon/` tree at the pin | `3ba0cab4a5e193b01943e5e6e0be25077ff759f6` |
| Trees equal, and equal to `PIN_AUREON_TREE` | true |
| `git diff --quiet 34864ff0 -- aureon` | exit 0 |

Checkout constants name `34864ff0`. That is `PINNED_COMMIT` in `mcp/aureon_public/guard_loader.py`, `COMMIT` in each Hugging Face Space `guard.py`, and the `aureon @ git+...@34864ff0` requirement in `mcp/aureon_public/requirements.txt`, `mcp/pyproject.toml`, and the four Space `requirements.txt` files.

Inside commit `34864ff0` those same constants still name the previous pin `ad9be6c3179bba140fb7e88d5733616046110da9`. Commit `c68a89d2` is the retarget onto `34864ff0`. This stage does not move the pin.

`GUARD_BLOB` is `cd1f3003005edfde18d286157f226dd19583d7b0`. It matches `huggingface/hnc-field/guard.py` at this checkout. The blob of that file inside the pin commit is `571e1ca2c55a06a8966a2bbd0621898c6f636a91`, because the pin commit's `COMMIT` string is still the previous pin. The loader checks the constant bytes. It is not a path lookup inside `PINNED_COMMIT`.

`INVENTORY_SHA256` is `4bc19ea9b5444a7b8a9abbd3fabf635d083bd25bea6c1b2d6eab2605b4f5716b` and matches `docs/mcp/inventory.json`.

`OPEN_PLAN_THROUGH` is 2.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `mcp/aureon_public/guard_loader.py` | line 23 | `9d6dbb167d1e26beda9f5c13a44044603defd2bb` | `63ab1288084187039019b17dfc47165dd4bfa16f9769f79d41281667e0dff7f0` |
| `huggingface/hnc-field/guard.py` | line 65 | `cd1f3003005edfde18d286157f226dd19583d7b0` | `088f1aa743731ede31606d532474687770d6840a5361fe9b474e4e80ca5fe562` |
| `huggingface/auris-coherence/guard.py` | line 65 | `bb89ccc6cb84be22ff7a3efe2ed8eb24a2b067c2` | `3676eb7fbe7370c57049ed82bf8a461fe72349c2335ece86a70e354c13388e44` |
| `huggingface/organism-replay/guard.py` | line 65 | `bb89ccc6cb84be22ff7a3efe2ed8eb24a2b067c2` | `3676eb7fbe7370c57049ed82bf8a461fe72349c2335ece86a70e354c13388e44` |
| `huggingface/qgita-snr/guard.py` | line 65 | `bb89ccc6cb84be22ff7a3efe2ed8eb24a2b067c2` | `3676eb7fbe7370c57049ed82bf8a461fe72349c2335ece86a70e354c13388e44` |
| `mcp/aureon_public/requirements.txt` | line 7 | `eea9722a87d8e891cbfb233d7d183ae347b2c604` | `044d7f047c3e515000a7f13c4eaf3a8689ebc4c4abd40edb57863a601bb8c752` |
| `mcp/pyproject.toml` | dependency pin | `fd52aae7d5d2af55e2f9ba74cbafece4c7fa760d` | `1d316abeac06e40aa84cf9e7019c6b9377785b274dcab62fd40b75c18b003a4c` |
| `huggingface/hnc-field/requirements.txt` | line 4 | `e61d4aa1e3d0078cc6b213f88dca47572bfe7cdd` | `15187b0e4ffb32c167332526b773df50f8a84f7c689dab5680f80c160bf2fbda` |
| `huggingface/auris-coherence/requirements.txt` | line 4 | `e61d4aa1e3d0078cc6b213f88dca47572bfe7cdd` | `15187b0e4ffb32c167332526b773df50f8a84f7c689dab5680f80c160bf2fbda` |
| `huggingface/organism-replay/requirements.txt` | line 4 | `e61d4aa1e3d0078cc6b213f88dca47572bfe7cdd` | `15187b0e4ffb32c167332526b773df50f8a84f7c689dab5680f80c160bf2fbda` |
| `huggingface/qgita-snr/requirements.txt` | line 4 | `e61d4aa1e3d0078cc6b213f88dca47572bfe7cdd` | `15187b0e4ffb32c167332526b773df50f8a84f7c689dab5680f80c160bf2fbda` |

## Harness

No live market series was fetched. Brain-proof read the committed file `data/de440_timeseries.csv` (git blob `485a6f7a0c31ab92d034c1b716913c7fff1da5a8`, SHA-256 `3434145487dabb65913a843f0f74106a2e4f893c0255d5927b052af764573312`). That file is the cited-unverified derived series already in the checkout.

Interpreter: Python `3.12.3` (`3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]`), NumPy `1.26.4`, platform `Linux-6.12.94+-x86_64-with-glibc2.39`. `python-dotenv` `1.2.4` was installed so `QueenHiveMind` could import. Those three environment fields match `evidence/environment.json`. The committed `commit_sha` in that file is `2def6909d4db323bd7650380bd5f2392023d6bc4` and is excluded from the byte compare.

### `make evidence`

Command: `PYTHONHASHSEED=0 PYTHONPATH=. python3 -m aureon.evidence --check` (the `make evidence` target).

Exit 0. Result: `evidence check: byte-for-byte match`. Float tails reproduced. The committed evidence bytes matched, including `evidence/RESULTS.md` and `evidence/output/`.

Stdout and stderr are `evidence_check.stdout.txt` and `evidence_check.stderr.txt`. An import print (`Harmonic Fusion: Timeline Oracle WIRED`) precedes the match line. Stderr has the penny-profit hardcoded-threshold warning. Neither is part of the byte contract.

`evidence/RESULTS.md` still says deployment HOLD is unchanged. The synthetic QGITA table in that file remains a labeled-impulse harness score. The unlabeled-series rate HOLD below stays HOLD.

### Brain-proof

Command, from the README five-minute quickstart:

```bash
AUREON_LLM_OFFLINE=1 AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 PYTHONPATH=. python3 -c "from aureon.evaluation.brain_proof import evaluate_brain, render_brain_markdown; print(render_brain_markdown(evaluate_brain()))"
```

Exit 0. `evaluate_brain` matched `reports/measured/brain.json`. The rendered markdown matched `reports/measured/brain.md`. Copies are `brain_proof.md`, `brain_proof.stdout.txt`, `brain_proof.stderr.txt`, and `brain_proof_summary.json`.

The run printed a wisdom-engine warning because `requests` is not installed. The JSON match still held.

Measured on this run, and still HOLD where the harness says HOLD:

- HNC formula path, multiverse off: state `coherent`, coherence `0.7739191103121901`, last Λ(t) `1.1030284973375342`, steps `100`.
- Auris coherence `None`, status `no_data`. Nodes without a reading: none.
- Trade readiness: **HOLD**.
- QGITA derived series and formula series: FTCP count `0`, lighthouse events `0`, detection rate **HOLD**, false-alarm rate null.
- Auris joined to Λ(t): **HOLD**.
- `live_trading` false, `orders_placed` false, `external_llm` false.

## HOLDs still true

### trade_readiness

**Status: HOLD.** Trade readiness is HOLD. No market series and no trade-outcome labels were supplied. Live trading stayed off.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `aureon/evaluation/brain_proof.py` | trade_readiness verdict HOLD, lines 193-196 | `89d874ebfe2fc8b8e73113b86fe6524b3ee71322` | `40fecd35b3322c34d0ec2a9c36cb243f2a80ea2e131ef93b9f899ea0e7e3cba8` |
| `mcp/aureon_public/layers.py` | HOLDS trade_readiness HOLD, lines 76-77 | `1abb7a7910faf8581981c4435775f8c7747bf558` | `618fc6b9994c6577a87a9811c98401c36ca6056ab2583b3b1204797cff6bcd26` |
| `mcp/aureon_public/README.md` | Trade readiness is HOLD, line 120 | `dc6d086304ba1961afd03d53557c1f58ff763f00` | `25bc17ad7f471733c169e2e80fa4c7756d42acd580a63735df9f4c850b49b2a8` |
| `reports/measured/brain.json` | auris.trade_readiness.verdict HOLD | `fbe0c3b668e07f7cf847d0a50b340902c3c69125` | `fafa3834b4c441af957f65c49540ba1880a1e879c589a30a2d0bbb7021383e0f` |
| `reports/measured/brain.md` | Trade readiness HOLD, line 9 | `a89803578ea74f1907eeacbc7d6f177388d40328` | `59331de231ed41b893dbc3214b8096214f071a1b5531f1bedd64b26f6b72d26b` |
| `reports/measured/index.json` | auris_trade_readiness HOLD, line 4 | `7e4fb403ea940c87effbeecf614fca5781a2db58` | `7481234933471ff44af7e20c1f6108d7c35a4d6806477dff5e1dd392eff9637c` |
| `reports/measured/auris_nodes.md` | Trade readiness HOLD, line 6 | `efa0dfac14112beaf4f70764df2701f454b6c95a` | `f4af0927b1e3e207148364ee0293ff2a9a7a926eba844c64cbd6f29786780f8e` |
| `tests/test_measured_proof.py` | asserts trade_readiness verdict HOLD, line 46 | `8ecf484dc2e2b9eb578333c260b9a02b66e1f7ca` | `5c24613cc46e03a99632341800d7dd4bfbb11f8c573a84e95a6679a5de68554d` |

### qgita_rates

**Status: HOLD.** QGITA detection rate and false-alarm rate are HOLD. The derived series and the formula series have no signal-in-noise labels, so the analyzer counts stay off those rates. The synthetic evidence table in evidence/RESULTS.md remains a labeled-impulse harness score. This unlabeled-series rate HOLD stays HOLD.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `aureon/evaluation/brain_proof.py` | rates_verdict HOLD, detection_rate and false_alarm_rate None, lines 285-291 | `89d874ebfe2fc8b8e73113b86fe6524b3ee71322` | `40fecd35b3322c34d0ec2a9c36cb243f2a80ea2e131ef93b9f899ea0e7e3cba8` |
| `mcp/aureon_public/layers.py` | qgita_detection_rate and qgita_false_alarm_rate HOLD, lines 79-80 | `1abb7a7910faf8581981c4435775f8c7747bf558` | `618fc6b9994c6577a87a9811c98401c36ca6056ab2583b3b1204797cff6bcd26` |
| `reports/measured/qgita_snr.md` | Detection rate HOLD on both series | `414171114e0cb630290b5b4ff24bc9da22f03470` | `5124e9c8d74814de339203c2a5087c4d13165364fd298e878b18683d20537122` |
| `reports/measured/qgita_snr.json` | rates_verdict HOLD on derived_series and on_hnc_series | `fb1b75799acff11886bd2da3355ac5d3a9856441` | `99c75fac8cbc12b4f775edcb5d7d9e0f458930b0a38e9c80cbded04f8f6fa43d` |
| `reports/measured/index.json` | qgita_derived_detection_rate null, qgita_derived_series HOLD, lines 30-33 | `7e4fb403ea940c87effbeecf614fca5781a2db58` | `7481234933471ff44af7e20c1f6108d7c35a4d6806477dff5e1dd392eff9637c` |
| `evidence/RESULTS.md` | claim not_claimed.alive_or_hold; Deployment HOLD is unchanged, lines 134-136 | `0239db0a285ac2e68b975310d2d4be217648950f` | `b6d0be7f7c3568338b6e5437cbce5847a3b2aef5bd493b592d1ca088602de4e1` |
| `evidence/output/claims.json` | not_claimed.alive_or_hold asserted false | `22d2858409096c64221efa61953654274374f28d` | `721889ac18a5b06d71d7d871c411e351fdcb7b2ab2b75f0f8546dccd838c0560` |

### auris_lambda_join

**Status: HOLD.** Auris is not joined to Lambda(t). No function in the repo passes Lambda(t) into get_auris_coherence.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `aureon/evaluation/brain_proof.py` | together.auris_joined_to_lambda verdict HOLD, lines 408-413 | `89d874ebfe2fc8b8e73113b86fe6524b3ee71322` | `40fecd35b3322c34d0ec2a9c36cb243f2a80ea2e131ef93b9f899ea0e7e3cba8` |
| `mcp/aureon_public/layers.py` | HOLDS auris_to_lambda HOLD, line 78 | `1abb7a7910faf8581981c4435775f8c7747bf558` | `618fc6b9994c6577a87a9811c98401c36ca6056ab2583b3b1204797cff6bcd26` |
| `mcp/aureon_public/README.md` | The Auris-to-Lambda link is HOLD, line 131 | `dc6d086304ba1961afd03d53557c1f58ff763f00` | `25bc17ad7f471733c169e2e80fa4c7756d42acd580a63735df9f4c850b49b2a8` |
| `reports/measured/brain.md` | Auris is not joined to Lambda(t) HOLD, line 12 | `a89803578ea74f1907eeacbc7d6f177388d40328` | `59331de231ed41b893dbc3214b8096214f071a1b5531f1bedd64b26f6b72d26b` |
| `reports/measured/brain.json` | together.auris_joined_to_lambda.verdict HOLD | `fbe0c3b668e07f7cf847d0a50b340902c3c69125` | `fafa3834b4c441af957f65c49540ba1880a1e879c589a30a2d0bbb7021383e0f` |
| `tests/test_measured_proof.py` | asserts auris_joined_to_lambda verdict HOLD, line 53 | `8ecf484dc2e2b9eb578333c260b9a02b66e1f7ca` | `5c24613cc46e03a99632341800d7dd4bfbb11f8c573a84e95a6679a5de68554d` |

### release_boundary

**Status: HOLD.** The release boundary is not production-ready. LocalDevelopmentReleaseBoundaryV02.production_ready is False. The OS-protection census limitation release-boundary-production-ready-false is still the recorded limit. Supported launchers stop at terminal HOLD. This stage does not change that outcome.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `aureon/plumber/release_boundary_v02.py` | production_ready False at lines 415, 529, 619, 626, and 1089 | `85393b07054772b15d73ac99b4e72bdd7ca38426` | `8691b938dc8df60e89c7360c90c24079eda259754a0ea36810cce925580e05f4` |
| `tests/test_os_protection_boundary_census.py` | certification limitation release-boundary-production-ready-false, line 232 | `2275f4cfe6d860e0b9df463e0b00b075857d5709` | `7cefc5de7a5ae769038e3c1c4d697cf89209aec14b60de0cfe53326fc83bce0d` |
| `docs/runbooks/GO_LIVE_HARDENING.md` | missing release boundary, line 9; outcome HOLD, lines 20-21 | `4bfaf97b6673dda1736c414e9d35637cf2f2b449` | `47c99c15e58ab1e1b8632c074ac689fb187ccd669b930077cfe244dbfdc73c25` |
| `README.md` | Release-boundary implementation stops at terminal HOLD, line 193 | `08184d4c63a5377380893c5e8442fe0c42f8ecda` | `8fb3bac853ba36d9d702a85bfff663d6e537e2744628dd60a52035a746264462` |

### mcp_stages_3_and_4_closed

**Status: HOLD.** Public MCP plan stages 3 and 4 stay closed. OPEN_PLAN_THROUGH is 2. Miner is stage 3. Queen, exchanges, and trading are stage 4. body_call refuses a later plan stage with 'plan stage N is not open'.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `mcp/aureon_public/body.py` | OPEN_PLAN_THROUGH = 2, line 35; refusal at lines 771-773 | `298eea74b276f3651327ec9c596ac69c4899a7d0` | `9d27f346708b56e849d27a3148422a69554a0f6510b943a9486da8e02b787e1e` |
| `mcp/aureon_public/README.md` | Stages 3 and 4 stay closed, lines 14-16 | `dc6d086304ba1961afd03d53557c1f58ff763f00` | `25bc17ad7f471733c169e2e80fa4c7756d42acd580a63735df9f4c850b49b2a8` |
| `mcp/aureon_public/coverage_plan.py` | STAGE_TITLE stages 3 and 4, lines 30-35; Stages 3 and 4 stay closed, line 481 | `44e22695f16e44c8ad4504055836ba707eec3cb8` | `d99f74a3dd044ddb3faddce7aba206f3b9c9363836b396a48e372c8f81b7c467` |
| `mcp/aureon_public/COVERAGE_PLAN.md` | Stages 3 and 4 stay closed, line 224 | `77b062bd2f114d691c1e2595fa6b639dcd4a08b6` | `7e4d75833b5c9bd78f127c781307d6443ce4b7d914298f2c6a17a35539ddab15` |
| `tests/test_aureon_body.py` | plan stage 4 is not open, lines 49 and 71 | `f837db6281dc208fc77e4ca17c61ac42e1b17d52` | `7f2bb675e27f775fc55707a152d1cab82be5a3941ffe26e72f19eca9296d3649` |

### go_live_receipts_missing

**Status: HOLD.** Go-live receipts are missing. GO_LIVE_HARDENING requires native containment, target-source measurement, immutable release provenance, durable HNC evidence with an external monotonic head anchor, source-boundary census closure, and an authenticated deployment receipt with provider-side read-back. None of those receipts is in this checkout. The correct outcome remains HOLD. The isolated bootstrap can emit a local HOLD receipt; that receipt is not an authenticated deployment receipt, and its durable HNC, external head anchor, and production_ready flags stay false.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `docs/runbooks/GO_LIVE_HARDENING.md` | required receipts and outcome HOLD, lines 1-21 | `4bfaf97b6673dda1736c414e9d35637cf2f2b449` | `47c99c15e58ab1e1b8632c074ac689fb187ccd669b930077cfe244dbfdc73c25` |
| `docs/runbooks/PREFLIGHT_CHECKLIST.md` | current preflight decision HOLD, lines 20-22 | `c39f5828dc71d3cac428dab9ce1cdfb645149cf9` | `216109957183c8853e57459ccc499871b34f5a6bad336f16120215b33f90d0c6` |
| `docs/deployment/OPERATOR_DEPLOY.md` | authenticated deployment receipt not claimed, lines 21-24 | `48abd2c6bbdfc8a064bd64b71ef67cd932f7e0f4` | `e93cae499c04b0084213c23e81205a3875031c2b76e49969278ae65e51b25f9f` |
| `scripts/bootstrap/protected_bootstrap_v05.py` | decision HOLD; durable_hnc_evidence_attested, external_head_anchor_attested, and production_ready false, lines 437-492 | `a1297eae7ad3820c88218781cc75319509c9b3df` | `23a556f2deb0e1b45689840779a714e4dc79ce286ec6a7c907bce75adc6102bd` |
| `README.md` | go-live runbooks superseded until provider-side read-back is proven, lines 306-308 | `08184d4c63a5377380893c5e8442fe0c42f8ecda` | `8fb3bac853ba36d9d702a85bfff663d6e537e2744628dd60a52035a746264462` |

## Also still HOLD

These are in the same public HOLD table and the measured index. This stage does not lift them.

### schumann_f0

**Status: null. HOLD.** schumann_f0 stays null. HOLD in the public layer table.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `mcp/aureon_public/layers.py` | schumann_f0 null. HOLD, line 81 | `1abb7a7910faf8581981c4435775f8c7747bf558` | `618fc6b9994c6577a87a9811c98401c36ca6056ab2583b3b1204797cff6bcd26` |
| `mcp/aureon_public/surfaces.py` | schumann_f0 null. HOLD, line 62 | `26585908bf17ccd038c3ea37d6e4ff8d04f7bd2b` | `9b015cc7bddb767a3496902c047be8d495751f896226a254bf84ad33d0f86793` |

### human_eval

**Status: not run. HOLD.** HumanEval was not run. The self-coder comparison stays HOLD. This stage did not call an external model.

| Path | Locator | Git blob | SHA-256 |
| --- | --- | --- | --- |
| `mcp/aureon_public/layers.py` | human_eval not run. HOLD, line 82 | `1abb7a7910faf8581981c4435775f8c7747bf558` | `618fc6b9994c6577a87a9811c98401c36ca6056ab2583b3b1204797cff6bcd26` |
| `reports/measured/self_coder.md` | Flagship comparison HOLD; HumanEval status not_attempted | `064b6e722d72923a569819d2275ee62134feea99` | `0aaec5eac3f49d6b4f89c1556561c8bd13094efe18024eeb656501a560a2e687` |
| `reports/measured/self_coder.json` | humaneval.status not_attempted; flagship_comparison.status HOLD | `e9edd0ef6df5801668dc921b46f9045e8d4a899e` | `9f22194b38ba48cd73ec77cc8d403b5e9048091abdbf5d34971c05df2c30d1a3` |
| `reports/measured/index.json` | self_coder_comparison HOLD; self_coder_humaneval_pct null, lines 37-38 | `7e4fb403ea940c87effbeecf614fca5781a2db58` | `7481234933471ff44af7e20c1f6108d7c35a4d6806477dff5e1dd392eff9637c` |

## Fingerprints for later stages

Hashes below are the files at checkout `c68a89d2` before this pack was added. A later stage proves it moved something by showing a different hash, or proves it did not by showing the same hash. `GO_LIVE_HARDENING.md` is in this list so a later diff can show this stage left it alone.

| Path | Git blob | SHA-256 |
| --- | --- | --- |
| `reports/measured/index.json` | `7e4fb403ea940c87effbeecf614fca5781a2db58` | `7481234933471ff44af7e20c1f6108d7c35a4d6806477dff5e1dd392eff9637c` |
| `reports/measured/brain.json` | `fbe0c3b668e07f7cf847d0a50b340902c3c69125` | `fafa3834b4c441af957f65c49540ba1880a1e879c589a30a2d0bbb7021383e0f` |
| `reports/measured/brain.md` | `a89803578ea74f1907eeacbc7d6f177388d40328` | `59331de231ed41b893dbc3214b8096214f071a1b5531f1bedd64b26f6b72d26b` |
| `reports/measured/auris_nodes.json` | `afd9baa0258aac549d2fbf46fdd1274cd5c9b416` | `e097736935e12f46aecaa595edba1eae5bb2b0dd056994b1343226a481f72720` |
| `reports/measured/auris_nodes.md` | `efa0dfac14112beaf4f70764df2701f454b6c95a` | `f4af0927b1e3e207148364ee0293ff2a9a7a926eba844c64cbd6f29786780f8e` |
| `reports/measured/qgita_snr.json` | `fb1b75799acff11886bd2da3355ac5d3a9856441` | `99c75fac8cbc12b4f775edcb5d7d9e0f458930b0a38e9c80cbded04f8f6fa43d` |
| `reports/measured/qgita_snr.md` | `414171114e0cb630290b5b4ff24bc9da22f03470` | `5124e9c8d74814de339203c2a5087c4d13165364fd298e878b18683d20537122` |
| `reports/measured/organism.json` | `68a1573e6603e163a41899db394a061717346709` | `398a0fe0a2d46c117b7de8d9fb593bd9d96b768749eae293fa0bc42ca742f8f6` |
| `reports/measured/organism.md` | `95be91bb33298f1887565d3a294c38609af4f4d6` | `dd1223118c51a37775a9c522350138aa5a4ae0d7f669b4b4537ac74ae3bf347f` |
| `reports/measured/self_coder.json` | `e9edd0ef6df5801668dc921b46f9045e8d4a899e` | `9f22194b38ba48cd73ec77cc8d403b5e9048091abdbf5d34971c05df2c30d1a3` |
| `reports/measured/self_coder.md` | `064b6e722d72923a569819d2275ee62134feea99` | `0aaec5eac3f49d6b4f89c1556561c8bd13094efe18024eeb656501a560a2e687` |
| `evidence/RESULTS.md` | `0239db0a285ac2e68b975310d2d4be217648950f` | `b6d0be7f7c3568338b6e5437cbce5847a3b2aef5bd493b592d1ca088602de4e1` |
| `evidence/environment.json` | `23c0f2166af9e9f0d4500ad332a4e30d52997e98` | `ed39490de053d1dfc9cf132adeecfd95211fb052f4a567f87cf37c6849507899` |
| `evidence/output/claims.json` | `22d2858409096c64221efa61953654274374f28d` | `721889ac18a5b06d71d7d871c411e351fdcb7b2ab2b75f0f8546dccd838c0560` |
| `docs/runbooks/GO_LIVE_HARDENING.md` | `4bfaf97b6673dda1736c414e9d35637cf2f2b449` | `47c99c15e58ab1e1b8632c074ac689fb187ccd669b930077cfe244dbfdc73c25` |
| `docs/runbooks/PREFLIGHT_CHECKLIST.md` | `c39f5828dc71d3cac428dab9ce1cdfb645149cf9` | `216109957183c8853e57459ccc499871b34f5a6bad336f16120215b33f90d0c6` |
| `aureon/plumber/release_boundary_v02.py` | `85393b07054772b15d73ac99b4e72bdd7ca38426` | `8691b938dc8df60e89c7360c90c24079eda259754a0ea36810cce925580e05f4` |
| `mcp/aureon_public/body.py` | `298eea74b276f3651327ec9c596ac69c4899a7d0` | `9d27f346708b56e849d27a3148422a69554a0f6510b943a9486da8e02b787e1e` |
| `mcp/aureon_public/layers.py` | `1abb7a7910faf8581981c4435775f8c7747bf558` | `618fc6b9994c6577a87a9811c98401c36ca6056ab2583b3b1204797cff6bcd26` |
| `mcp/aureon_public/guard_loader.py` | `9d6dbb167d1e26beda9f5c13a44044603defd2bb` | `63ab1288084187039019b17dfc47165dd4bfa16f9769f79d41281667e0dff7f0` |

## Stage boundary

This pack is the baseline only. It lifts nothing.

- The published pin remains `34864ff0547d2cff03e707414743a3b0cc8770b5` in `PINNED_COMMIT`, every guard `COMMIT`, and the public MCP requirements.
- Every HOLD listed above remains HOLD, including the badges in code, docs, and `reports/measured/index.json`.
- The `GO_LIVE_HARDENING.md` outcome remains `HOLD`.
- MCP plan stages 3 and 4 remain closed. `OPEN_PLAN_THROUGH` remains 2.
- `LocalDevelopmentReleaseBoundaryV02.production_ready` remains `False`.
- Live market series remain unfetched. Fetching them is stage 1.
- Authenticated deployment receipts and provider-side read-back remain absent.

Merge of this baseline waits on Charlie, Buzz, and Spike PASS, and on Gary's plain yes on the exact head in Lrya 1:1.
