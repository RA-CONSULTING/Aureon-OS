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
| 3 HNC head anchor | `refs/notes/aureon-hnc-head` and `refs/notes/aureon-hnc-head-next` on the recording commit named by the evidence records | committed `evidence/output/hnc_head_anchor.tsr.b64` and `evidence/output/hnc_head_next.tsr.b64` |
| 4 census and call sweep | stage 6 census and `measured/aureon_public_call_sweep.sh` | `measured/go_live_stage6_source_census.json` and `measured/aureon_public_call_sweep.json` |

Receipt 1's committed record was measured at `c68a89d2` with a dirty worktree
and pin `34864ff0`. Receipts 2 and 4 still cite tip `b2b03103`. That commit
is on the old #253 branch. It is not an ancestor of main. Before writing,
the runner checks that the tip is an ancestor of the frozen head. The
refusal says the tip is not an ancestor of the frozen head (not on main).
The tip field is not rewritten. When no tip value could be read, the row
says `none read`.

Containment is measured into a folder outside the committed paths. The
committed `reports/measured/native_process_containment.json` and `.md` are
replaced only when that measurement's verdict is `pass` and the worktree
was clean. A `fail` or a dirty-tree result leaves those files byte-identical.

The call sweep writes outside the checkout. If receipt 4 is refused, that
staged file is discarded and `measured/aureon_public_call_sweep.json` stays
byte-identical.

## Receipt 3

The runner looks for the commit that recorded `hnc_head_next.*` together
with the HNC anchor files. When that commit is an ancestor of HEAD and the
notes `refs/notes/aureon-hnc-head` and `refs/notes/aureon-hnc-head-next` on
that commit match the committed token files byte for byte, the verdict is
`anchored` and the detail is `anchored on <short sha>`. Those notes are on
`9b666838` in this history. `python -m aureon.evidence --check` reads each
note from the commit that recorded its own evidence record
(`evidence/output/hnc_head_anchor.json` for sequence 1,
`evidence/output/hnc_head_next.json` for sequence 2), using the `note_ref`
named in that record. It does not read the note from HEAD and does not fall
back to HEAD when the note is missing or the bytes differ. A re-attach is
offered only when no such commit exists.

A shallow clone fails closed, so CI needs the full history (`fetch-depth: 0`) and the notes fetch (`refs/notes/aureon-hnc-head` and `refs/notes/aureon-hnc-head-next`).

Editing `hnc_head_anchor.json` or `hnc_head_next.json` moves the recording commit, so the check fails until the notes are re-attached at the new commit.

The offered commands do not use `-f` and do not request a new timestamp:

```bash
git notes --ref=aureon-hnc-head add -F evidence/output/hnc_head_anchor.tsr.b64 HEAD
git notes --ref=aureon-hnc-head-next add -F evidence/output/hnc_head_next.tsr.b64 HEAD
```

`--attach-note` runs those commands only for a ref that has no note. If a
different note is already there, the runner stops with a plain message and
leaves that note alone. Do not push either notes ref.

## Exit

Exit 0 means the receipts were measured: every row is `pass`, `anchored`,
or `attached`. It does not mean go-live is clear. `go_live_clear` stays false.

Exit 3 is a HOLD-type verdict: `stale`, `hold`, `absent`, or `skip`. This
matches `publish`. Exit 1 is `fail` or `refused`. Exit 2 means the worktree
was dirty and nothing was measured.

## HOLD note — published-pin move to 0646146c (box/65-of-65, 2026-11-10)

The published require-pin was moved from `bb04503119681adcf832f3c3e9b0cbf09fc7a938`
to `0646146c53e59dbcab41363a613d5651c9c9d50f` on the box/65-of-65 line so the
pinned finder accepts the tree the trader and repair loop actually run. This is
a require-pin retarget only. It is not a badge flip, a release, or a publish.
`go_live_clear` stays false and the orange HOLD badge is unchanged.

Receipt 1 (containment) was remeasured on this line and passes; its committed
record stays frozen at its measurement-time head `c68a89d2`.

Receipts 2, 3, 4, and 5 stay HOLD and are **not** moved to the new pin on this
line:

- Receipts 2 and 4 (release provenance, source census / call sweep) are frozen
  to the main head `b2b0310362597dc520114de86d8700c0c50758d5`. The go_live_stage6
  measure refuses any tip that is not an ancestor of that frozen head, and
  box/65-of-65 (`0646146c`) is on a divergent line, so these cannot be remeasured
  here. They will catch up when the move lands on main.
- Receipt 3 (HNC head anchor, DigiCert sequence 2) needs the timestamp notes
  re-attached, which requires the external DigiCert timestamp service. Left HOLD.
- Receipt 5 (deployment) stays bound to its prior measurement head.

No receipt values were fabricated. The three receipt tests tied to the above
(stage6 receipt 2/4 provenance, the receipt 5 schema-pin check, and the HNC-head
sequence-2 check) are left red and honest until the main-line move and DigiCert
re-attach complete.
