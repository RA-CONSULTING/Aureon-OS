# Remeasure go-live receipts 1–4

Go-live stays **HOLD**. `go_live_clear` stays false. This command does not
move the published pin `bb04503119681adcf832f3c3e9b0cbf09fc7a938`, does not
edit `docs/runbooks/GO_LIVE_HARDENING.md`, and does not edit
`reports/measured/baseline/`. It does not request a new RFC 3161 timestamp
and it does not push `refs/notes/aureon-hnc-head`.

The release head is not frozen. A trial run rewrites local receipt files.
Those files are not a release measurement until the head is frozen and the
run is committed on purpose.

`docs/runbooks/GO_LIVE_HARDENING.md` is the HOLD boundary. This file is only
the remeasure procedure.

## Command

```bash
make remeasure-go-live-receipts
```

```bash
PYTHONPATH=. python3 scripts/validation/remeasure_go_live_receipts.py
```

The worktree must be clean. `git status --porcelain` with any line, including
an untracked file, exits 2 and runs no measurement.

The summary records `HEAD`, the `PINNED_COMMIT` value read from
`mcp/aureon_public/guard_loader.py`, and the python, git, unshare, and
openssl versions. It then prints one row per receipt.

## What each receipt runs

| Receipt | Entry | File |
| --- | --- | --- |
| 1 containment | `python -m aureon.containment.cold_boot` | `reports/measured/native_process_containment.json` |
| 2 release provenance | `scripts/validation/go_live_stage6.py` | `measured/go_live_stage6_provenance.json` |
| 3 HNC head anchor | `refs/notes/aureon-hnc-head` on HEAD | committed `evidence/output/hnc_head_anchor.tsr.b64` |
| 4 census and call sweep | stage 6 census and `measured/aureon_public_call_sweep.sh` | `measured/go_live_stage6_source_census.json` and `measured/aureon_public_call_sweep.json` |

Receipt 1's committed record was measured at `c68a89d2` with a dirty worktree
and pin `34864ff0`. Receipt 2's committed provenance still names tip
`b2b03103`. The stage-6 script binds that tip. A run on a later HEAD reports
that fact in the table.

The call sweep copies the checkout and its own stamp refuses a dirty copy.
The runner starts that script while the worktree is still clean and points
`OUT` outside the checkout. Receipt 1 then records the clean tree. The sweep
JSON is copied to `measured/aureon_public_call_sweep.json` after that.

## Receipt 3

When `refs/notes/aureon-hnc-head` is already on HEAD and matches the
committed sequence-1 token, the verdict is `anchored`.

When it is not, the runner prints this command and does not run it:

```bash
git notes --ref=aureon-hnc-head add -f -F evidence/output/hnc_head_anchor.tsr.b64 HEAD
```

That line reads the committed DigiCert RFC 3161 token bytes for sequence 1.
It does not contact `http://timestamp.digicert.com`. Pass `--attach-note` to
run that same command in this checkout. Do not push the notes ref:

```bash
PYTHONPATH=. python3 scripts/validation/remeasure_go_live_receipts.py --attach-note
```

## Exit

`2` means the worktree was dirty and nothing was measured. `1` means the
table was printed and a receipt verdict is `fail` or `refused`. `0` means
every verdict is a measured hold, pass, skip, absent, stale, anchored, or
attached state. A passing containment row does not clear go-live.
