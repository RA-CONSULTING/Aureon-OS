# Source archives

Build checksummed source archives for the public prerelease channel. The command uses `git archive` of `HEAD`. It writes a tar.gz, a zip, `release-channel.json`, and `SHA256SUMS`.

```bash
python packaging/release_channel.py check
python packaging/release_channel.py archive --dest dist/tip-channel
```

`dist/` is gitignored. The archives are not committed.

`check` prints the pin, the lineage tip, and receipts 1-5. It exits 0 when the orange badge is still HOLD, `PINNED_COMMIT` still matches `PUBLISHED_PIN` in `packaging/release_channel.py`, and `docs/releases/RELEASE_NOTES_tip.md` still says production go-live is not cleared. `PUBLISHED_PIN` is `bb04503119681adcf832f3c3e9b0cbf09fc7a938`. This file does not move the pin.

`publish` always exits non-zero. Go-live stays HOLD. Charlie, Buzz, and Spike PASS do not publish. The command waits for Gary's own yes. It does not call GitHub and does not create a tag.

To bind the filenames to a prerelease tag, the tag must already exist and must be `tip-` plus a lowercase hex prefix of `HEAD`:

```bash
python packaging/release_channel.py accept-tag "tip-$(git rev-parse --short=12 HEAD)"
python packaging/release_channel.py archive --dest dist/tip-channel --tag "tip-$(git rev-parse --short=12 HEAD)"
```

Verify:

```bash
cd dist/tip-channel
sha256sum -c SHA256SUMS
```

The manifest fields `go_live` is HOLD, `go_live_clear` is false, and `published`, `system_alive`, and `orders_placed` are false. `.github/workflows/source-archive-release.yml` uploads these files as Actions artifacts. It does not open a GitHub Release. The wait for Gary's own yes is in `docs/releases/PUBLIC_RELEASE_CHANNEL.md`.
