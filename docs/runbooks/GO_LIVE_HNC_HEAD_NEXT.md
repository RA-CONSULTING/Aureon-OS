# Receipt 3 follow-on — next monotonic head

Measured. Sequence 2 only. Go-live is not clear. `go_live_clear` stays false.
This note is not in `docs/runbooks/GO_LIVE_HARDENING.md`. That file matches
main. This note does not publish anything and does not report the system alive.

On tip `bb04503119681adcf832f3c3e9b0cbf09fc7a938`, `git notes --ref
aureon-hnc-head show HEAD` had no note. The origin notes ref annotates
`7d26871ff007ec6c84be657297827fc813fe7428`, which is not an object in this
history. The note bytes match the committed sequence 1 token. This follow-on
does not rewrite that tip and does not request a replacement for the sequence
1 timestamp.

Sequence 2 uses the next sequence, `prev_anchor_id`
`548596463d7b4dddeeba274562b212960f879baf475ee135c7d2fd3468f58e11`, and a
DigiCert `gen_time` of `2026-11-05T20:44:49Z`. Sequence 1 is
`2026-11-05T19:40:18Z`. The later time was taken from `openssl ts -verify`
against the system trust store. The authority's ordering flag is no.

The formula series sha256 is unchanged. This follow-on does not publish a
new HNC identity. The timestamp records historical public pin
`34864ff0547d2cff03e707414743a3b0cc8770b5`. The published require-pin is
`bb04503119681adcf832f3c3e9b0cbf09fc7a938`. This follow-on does not move it.
No market series is fetched.

`make evidence` reads sequence 2 from `refs/notes/aureon-hnc-head-next` on
the commit that recorded `evidence/output/hnc_head_next.json`, and sequence
1 from `refs/notes/aureon-hnc-head` on the commit that recorded
`evidence/output/hnc_head_anchor.json`. Each evidence record names its own
`note_ref`. The check does not read either note from HEAD. A missing note
or different bytes on that recording commit fails the check. It requires
these bytes:

- `evidence/output/hnc_head_next.id` — SHA-256 of the sequence 2 token
- `evidence/output/hnc_head_next.json` — the measured record
- `evidence/output/hnc_head_next.tsr.b64` — the token

Fetch the note with `git fetch origin
refs/notes/aureon-hnc-head-next:refs/notes/aureon-hnc-head-next`. The check
does not contact the timestamp authority. A working-tree edit does not move
the note. The notes are attached to the commit that records these files:
`refs/notes/aureon-hnc-head` is the sequence 1 token, and
`refs/notes/aureon-hnc-head-next` is the sequence 2 token. In this history
both records were last recorded on `9b666838`, and both notes are on that
commit. A note that exists only on a later HEAD is not used. The sequence 1
file in the tree is unchanged. A squash merge leaves both notes on the
pre-squash commit. Re-attach the same token bytes to the squash commit. Do
not request another timestamp to do that.

`external_head_anchor_attested` stays false. The system is not reported
alive. Live trading stays off. No order is placed. This follow-on is not
receipt 5 and does not produce an authenticated deployment receipt. The
go-live line for durable HNC evidence stays HOLD because the intrusion ledger
is not attested by this timestamp chain.

## Historical stage-0 pin

The frozen pack `reports/measured/baseline/` records published pin
`34864ff0547d2cff03e707414743a3b0cc8770b5` at checkout
`c68a89d2a184d99582bb24310b91e024323a212c`. That pin is historical. The
published require-pin is now `bb04503119681adcf832f3c3e9b0cbf09fc7a938`.
The pack says not to edit that directory, so this note is not written there.
The stage 7 receipt still names `34864ff0547d2cff03e707414743a3b0cc8770b5`.
That receipt is not rewritten.

The stage 6 census tip stays `b2b0310362597dc520114de86d8700c0c50758d5`.
The unlisted-symbol count in that census is a scan of a later checkout.
The census decision stays HOLD. `source_boundary_closed` stays false.
`go_live_clear` stays false.
