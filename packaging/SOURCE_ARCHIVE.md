# Source archives

Build checksummed source archives for the public prerelease channel. The command uses `git archive` of `HEAD`. It writes a tar.gz, a zip, `release-channel.json`, and `SHA256SUMS`.

```bash
python packaging/release_channel.py check
python packaging/release_channel.py archive --dest dist/tip-channel
```

`dist/` is gitignored. The archives are not committed.

`check` prints the pin, the lineage tip, and receipts 1-5. It exits 0 when the orange badge is still HOLD, `PINNED_COMMIT` still matches `PUBLISHED_PIN` in `packaging/release_channel.py`, and `docs/releases/RELEASE_NOTES_tip.md` still says production go-live is not cleared. A pin pull request updates both the constant in `mcp/aureon_public/guard_loader.py` and `PUBLISHED_PIN` here. This file does not move the pin.

`publish` exits non-zero on this tree. It does not call GitHub and does not create a tag.

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

The manifest fields `published`, `system_alive`, and `orders_placed` are false. `go_live_clear` is false while any of receipts 1-5 is unverified on `HEAD`. The GitHub draft step that uploads these files is `.github/workflows/source-archive-release.yml`. The clicks that make a draft public are in `docs/releases/PUBLIC_RELEASE_CHANNEL.md`.
