# Aureon OS tip prerelease

Lineage tip: `bb04503119681adcf832f3c3e9b0cbf09fc7a938` (stage 7, native zero-network cold boot).

These notes describe that lineage. The source-archive manifest records the commit that was archived. After this pull request lands on main, that commit still has `bb04503119681adcf832f3c3e9b0cbf09fc7a938` as an ancestor. License: MIT (`LICENSE`).

The release boundary stays HOLD. The orange release-boundary badge stays HOLD. production go-live is not cleared. Receipts 1-5 are not verified on this commit. The system is not claimed alive. No order is placed.

The published GitHub Release `V2.1` (2026-07-13) is still the Latest release. It has zero uploaded assets and the title "Aureon OS v2.1 — Production Platform & Investor-Ready". These notes are the later tip. They become public only after the clicks in [PUBLIC_RELEASE_CHANNEL.md](PUBLIC_RELEASE_CHANNEL.md).

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
| 1. Native process containment, zero-network default | `reports/measured/native_process_containment.json`. Verdict `pass`. `release_boundary` HOLD. `git_head_at_measurement` `c68a89d2a184d99582bb24310b91e024323a212c`. The stage 7 commit adds the file and is not a second measurement. `orders_placed` false. `live_trading` false. | Measured cold boot. Go-live clear: false. |
| 2. Exact target-source measurement and immutable release provenance | `measured/go_live_stage6_provenance.json`. `decision` HOLD. `go_live_clear` false. Tip named there is `c68a89d2a184d99582bb24310b91e024323a212c`. | HOLD |
| 3. Durable HNC evidence with an external monotonic head anchor | `evidence/output/hnc_head_anchor.json`. RFC 3161 token for the fixed-seed formula series. `go_live` HOLD. `go_live_clear` false. `system_alive` false. Public pin unchanged. `external_head_anchor_attested` on the intrusion ledger stays false. | HOLD |
| 4. Complete source-boundary census closure | `measured/go_live_stage6_source_census.json`. `decision` HOLD. `go_live_clear` false. Tip named there is `c68a89d2a184d99582bb24310b91e024323a212c`. Plan stages 3 and 4 stay closed. | HOLD |
| 5. Authenticated deployment receipt and provider-side read-back | No receipt file in this tree. | Absent. HOLD |

Receipts 1-5 are not verified on this commit. production go-live is not cleared. The system is not claimed alive.

## Pin

`PINNED_COMMIT` in `mcp/aureon_public/guard_loader.py` is `34864ff0547d2cff03e707414743a3b0cc8770b5` (`34864ff0`). This pull request does not move it. It stays `34864ff0547d2cff03e707414743a3b0cc8770b5` until a pin pull request lands.

## Archives

A prerelease tag of the form `tip-` plus the leading lowercase hex digits of the archived commit can attach a source tar.gz, a source zip, `SHA256SUMS`, and `release-channel.json`. The manifest records `published: false`, `go_live_clear` from the receipt check, and `system_alive: false`. The workflow opens a draft pre-release. It does not publish. The clicks are in [PUBLIC_RELEASE_CHANNEL.md](PUBLIC_RELEASE_CHANNEL.md). The build command is in [packaging/SOURCE_ARCHIVE.md](../../packaging/SOURCE_ARCHIVE.md).
