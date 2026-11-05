# Public release channel

This channel keeps draft release notes and a draft workflow. It publishes nothing.

Current lineage tip these notes were written against: `bb04503119681adcf832f3c3e9b0cbf09fc7a938`.

| Fact | Value |
| --- | --- |
| Go-live | HOLD |
| Release boundary | HOLD |
| Orange badge | `release boundary-HOLD-orange` in `README.md` |
| Published pin | `34864ff0547d2cff03e707414743a3b0cc8770b5` |
| Pin move in this change | none |
| production go-live | not cleared |
| System | not claimed alive |
| Orders | none placed |
| Stranger command | `./install.sh` and `./install.sh --smoke` |
| Latest GitHub Release today | `V2.1`, published 2026-07-13, zero uploaded assets |

Receipts 1-5 are not verified on this commit. The records are listed in [RELEASE_NOTES_tip.md](RELEASE_NOTES_tip.md). Go-live stays HOLD.

## What the workflow does

`.github/workflows/source-archive-release.yml` runs only from **Run workflow** (`workflow_dispatch`).

The archive job runs `python packaging/release_channel.py check` and `archive`. It uploads the tar.gz, zip, `SHA256SUMS`, and `release-channel.json` as the Actions artifact `aureon-os-tip-channel`.

The publish job then runs `python packaging/release_channel.py publish`. That command exits 3. Charlie, Buzz, and Spike PASS do not publish. The job stops there and waits for Gary's own yes. It does not call the GitHub Releases API. It does not create a tag. Permissions stay `contents: read`.

## What Gary still has to do

1. Read this pull request. The notes and the README show go-live as HOLD. Merge is his decision. This pull request is not merged here.
2. Leave `PINNED_COMMIT` at `34864ff0547d2cff03e707414743a3b0cc8770b5` unless a separate pin pull request has already landed.
3. Do not create a production tag (`V2.2`, `v2.2.0`, or any tag whose name says production or go-live). This workflow will not create one.
4. Optional: Actions → **Source archive draft** → **Run workflow**. Download `aureon-os-tip-channel` if he wants the checksummed archives. That run's publish job is red on purpose. The red job means publish is still waiting.
5. Charlie PASS, Buzz PASS, and Spike PASS are not a publish. After those three, publish still waits for Gary's own yes on the exact head.
6. A GitHub Release, including a draft release, is his own later action in the GitHub UI. This workflow will not open it. If he does that later, the notes he pastes are `docs/releases/RELEASE_NOTES_tip.md`, go-live stays HOLD, and he does not mark the release as a production go-live.

`python packaging/release_channel.py publish` is the local form of that wait. It does not accept a flag that publishes.
