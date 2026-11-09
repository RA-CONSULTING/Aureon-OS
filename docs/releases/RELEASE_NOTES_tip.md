# Aureon OS tip prerelease

Lineage tip: `08f04936088689e29b7995d89530b21b425c35f9`. That commit keeps the four safety lines and go-live HOLD. Its ancestor `29fab7f21fc93da40224566dd8f34faacb3d74d4` pins the public require-pin to `bb04503119681adcf832f3c3e9b0cbf09fc7a938` and remeasures go-live receipts 2 and 4. Go-live stays HOLD.

These notes describe that tip. The source-archive manifest records the commit that was archived. After this pull request lands on main, that commit still has `08f04936088689e29b7995d89530b21b425c35f9` as an ancestor. License: MIT (`LICENSE`).

The release boundary stays HOLD. The orange release-boundary badge stays HOLD. Go-live stays HOLD. production go-live is not cleared. Receipts 1-5 are not verified on this commit. The system is not claimed alive. No order is placed.

The published GitHub Release `V2.1` (2026-07-13) is still the Latest release and has zero uploaded assets. These notes do not carry that release's title. They stay a draft until Gary's own yes, which is described in [PUBLIC_RELEASE_CHANNEL.md](PUBLIC_RELEASE_CHANNEL.md). Charlie, Buzz, and Spike PASS do not publish.

## What a stranger can run today

Python 3.11 or newer, Node.js 20 or newer, and a checkout with exchange keys left unset.

```bash
git clone https://github.com/RA-CONSULTING/Aureon-OS.git
cd Aureon-OS
./install.sh --smoke
```

`./install.sh` is that same local stack without the smoke stop. It does not read `.env`. `AUREON_AUTONOMY_MODE=guarded` is set by the plug-and-play boot, so live trading stays off. `AUREON_LLM_OFFLINE=1` keeps the operator on the offline adapter. `.github/workflows/plug-and-play.yml` runs `./install.sh --smoke` from a clean checkout. This pull request did not re-run that smoke. The README keeps an earlier banner; a later run prints its own process ids.

The README five-minute quickstart installs the operator extra, runs the offline operator, connectome, and quickstart tests, and prints the committed brain-proof report. That path does not start Docker and does not read exchange keys.

`python -m aureon.containment.cold_boot` is the stage 7 measurement command. The committed record is `reports/measured/native_process_containment.json`. It is a cold-boot measurement. It is not the installer, and it does not start the official Docker, Compose, Supervisor, systemd, shell, package, desktop, or cloud routes.

`scripts/launch/aureon-master.sh` and `production/install.sh` are outside this stranger path. They follow the public autonomy default: a complete exchange key group in `.env` makes that boot live.

## Supported deploy

Supported deploy stays on HOLD. Official Docker, Compose, Supervisor, systemd, shell, package, desktop, and cloud routes stop before target import or process start. `scripts/linux/install-linux.sh` still execs `scripts/bootstrap/protected_bootstrap_v05.py`. The appliance profile and `packaging/pyinstaller_build.md` stay on terminal HOLD. Receipt 1 does not switch those routes on.

| Receipt | Record on this tree | Go-live |
| --- | --- | --- |
| 1. Native process containment, zero-network default | `reports/measured/native_process_containment.json`. Verdict `pass`. `release_boundary` HOLD. `git_head_at_measurement` `c68a89d2a184d99582bb24310b91e024323a212c`. The record still names pin `34864ff0547d2cff03e707414743a3b0cc8770b5`. The pin move does not rewrite it. `orders_placed` false. `live_trading` false. | Measured cold boot. Go-live clear: false. |
| 2. Exact target-source measurement and immutable release provenance | `measured/go_live_stage6_provenance.json`. `decision` HOLD. `go_live_clear` false. Pin `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. Tip named there is `b2b0310362597dc520114de86d8700c0c50758d5`. | HOLD |
| 3. Durable HNC evidence with an external monotonic head anchor | `evidence/output/hnc_head_anchor.json`. RFC 3161 token for the fixed-seed formula series. `go_live` HOLD. `go_live_clear` false. `system_alive` false. The record still names `34864ff0547d2cff03e707414743a3b0cc8770b5`. `external_head_anchor_attested` on the intrusion ledger stays false. | HOLD |
| 4. Complete source-boundary census closure | `measured/go_live_stage6_source_census.json`. `decision` HOLD. `go_live_clear` false. Pin `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. Tip named there is `b2b0310362597dc520114de86d8700c0c50758d5`. The pin tree is not closed. Plan stages 3 and 4 stay closed. | HOLD |
| 5. Authenticated deployment receipt and provider-side read-back | No receipt file in this tree. | Absent. HOLD |

Receipts 1-5 are not verified on this commit. production go-live is not cleared. The system is not claimed alive.

Stage 8 is `measured/go_live_stage8_exchanges.json`. Decision HOLD. `go_live_clear` false. Pin unchanged. It reads the exchanges catalog and does not place an order. It does not clear go-live.

## Pin

`PINNED_COMMIT` in `mcp/aureon_public/guard_loader.py` is `bb04503119681adcf832f3c3e9b0cbf09fc7a938` (`bb045031`). The pin pull request landed in `29fab7f21fc93da40224566dd8f34faacb3d74d4`. This pull request does not move the pin.

## Archives

`workflow_dispatch` on `.github/workflows/source-archive-release.yml` can build a source tar.gz, a source zip, `SHA256SUMS`, and `release-channel.json` as Actions artifacts. The manifest records `go_live` HOLD, `go_live_clear` false, `published` false, and `system_alive` false. The workflow does not open a GitHub Release and does not create a tag. Publish waits for Gary's own yes even after Charlie, Buzz, and Spike PASS. The steps are in [PUBLIC_RELEASE_CHANNEL.md](PUBLIC_RELEASE_CHANNEL.md). The build command is in [packaging/SOURCE_ARCHIVE.md](../../packaging/SOURCE_ARCHIVE.md).
