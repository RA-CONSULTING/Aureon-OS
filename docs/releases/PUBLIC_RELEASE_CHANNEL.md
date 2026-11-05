# Public release channel

This channel prepares source archives for the tip lineage. It publishes nothing by itself.

Current lineage tip these notes were written against: `bb04503119681adcf832f3c3e9b0cbf09fc7a938`.

| Fact | Value |
| --- | --- |
| Release boundary | HOLD |
| Orange badge | `release boundary-HOLD-orange` in `README.md` |
| Published pin | `34864ff0547d2cff03e707414743a3b0cc8770b5` |
| Pin move in this change | none |
| production go-live | not cleared |
| System | not claimed alive |
| Orders | none placed |
| Stranger command | `./install.sh` and `./install.sh --smoke` |
| Latest GitHub Release today | `V2.1`, published 2026-07-13, zero uploaded assets |

Receipts 1-5 are not verified on this commit. The records are listed in [RELEASE_NOTES_tip.md](RELEASE_NOTES_tip.md).

## What the workflow does

`.github/workflows/source-archive-release.yml` runs in two cases.

- **Run workflow** (`workflow_dispatch`) on a commit that contains this file. The job runs `python packaging/release_channel.py check` and `archive`. It uploads the tar.gz, zip, `SHA256SUMS`, and `release-channel.json` as the Actions artifact `aureon-os-tip-channel`. It does not create a tag and does not open a GitHub Release.
- **Push a tag** named `tip-` plus 7 to 40 lowercase hex digits. Those digits must be a prefix of the tagged commit. The same job builds the archives and then runs `gh release create` with `--draft` and `--prerelease`. The draft title is `Aureon OS <tag> — prerelease, release boundary HOLD`. The body is `docs/releases/RELEASE_NOTES_tip.md`.

The workflow has no step that clears the draft flag, marks the release as latest, or creates a `v*` / `V*` tag. `python packaging/release_channel.py publish` refuses while the five receipts are unverified, and it never calls GitHub.

`contents: write` on that job is there so the draft upload can run. The other workflows keep `contents: read`.

## What Gary clicks to publish

1. Read this pull request. Mark it ready for review when the notes still say HOLD, and merge it. This repository's agent does not merge.
2. Check out the merge commit on `main`. Leave `PINNED_COMMIT` at `34864ff0547d2cff03e707414743a3b0cc8770b5` unless a separate pin pull request has already landed.
3. Create an annotated tag whose name is `tip-` plus at least the first 7 lowercase hex digits of that merge commit, and nothing else:

   ```bash
   SHORT=$(git rev-parse --short=12 HEAD)
   git tag -a "tip-${SHORT}" -m "Aureon OS tip prerelease. Release boundary HOLD. Not a production go-live."
   git push origin "tip-${SHORT}"
   ```

   Do not push `V2.2`, `v2.2.0`, or any tag whose name says production or go-live.
4. Wait for the Actions run **Source archive draft prerelease**. Confirm it uploaded `Aureon-OS-tip-<hex>.tar.gz`, `Aureon-OS-tip-<hex>.zip`, `SHA256SUMS`, and `release-channel.json`, and that it opened a draft.
5. Open the draft: GitHub → Releases → the draft titled `Aureon OS tip-… — prerelease, release boundary HOLD`.
6. Read the notes and `release-channel.json`. Confirm `release_boundary` is HOLD, `go_live_clear` is false, `system_alive` is false, `orders_placed` is false, `live_trading` is false, and `pin` is `34864ff0547d2cff03e707414743a3b0cc8770b5`.
7. Click **Publish release**. Leave **Set as a pre-release** checked.
8. Leave **Set as the latest release** unchecked to keep `V2.1` in the Latest slot. Check it only when this HOLD prerelease should replace that July 2026 Latest marker. That checkbox does not clear the orange badge and does not mean the system is alive.

If the draft step fails on token permissions, download the Actions artifact from the same run and create the draft in the GitHub release form by hand. Upload the four files. Use the same title and the committed notes. Then do steps 6–8.

`python packaging/release_channel.py publish` stays a local refusal until receipts 1-5 are verified on the commit being tagged. If a later commit makes that check succeed, this workflow stops before `gh release create`. A go-live release is a different change. This channel will not create it.
