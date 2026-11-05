# Go-live status: terminal HOLD

There is no supported live Aureon instance in the current release. Official
Docker, Compose, Supervisor, systemd, shell, package, desktop, and cloud routes
stop before target import or process start. The cloud manifests define zero
components and no secret bindings.

Do not expose listeners, inject credentials, enable trading, create tunnels, or
use direct module execution as a substitute for the missing release boundary.
Historical listener and environment guidance is withdrawn.

Go-live requires all of the following. Receipt 1 is measured (stage 7).
Receipt 3 is the DigiCert section below. Receipts 2 and 4 are remeasured
below and do not clear go-live. Receipt 5 is absent. None of these is
inferred into a clear:

- native process containment with a zero-network default (receipt 1, measured;
  see below);
- exact target-source measurement and immutable release provenance (receipt 2,
  remeasured, HOLD);
- durable HNC evidence with an external monotonic head anchor (receipt 3,
  measured, HOLD);
- complete source-boundary census closure (receipt 4, remeasured, the pin
  tree is not closed, HOLD);
- authenticated deployment receipt and provider-side read-back (receipt 5,
  absent, HOLD).

Until receipt 5 exists, the correct outcome is `HOLD`, not a partially
configured listener. The orange release-boundary badge stays HOLD.
`go_live_clear` stays false. This document does not say the system is alive.

## Receipt 3 — durable HNC evidence

Measured for this receipt only. Go-live is not clear.

The fixed-seed formula path in `aureon.evidence.hnc` is unchanged. Its series
sha256 matches the series recorded at public pin
`34864ff0547d2cff03e707414743a3b0cc8770b5` in
`evidence/output/hnc_head_anchor.json`. That record is receipt 3. This
receipt does not publish a new HNC identity. No market series is fetched.
The published require-pin is now
`bb04503119681adcf832f3c3e9b0cbf09fc7a938`. Receipt 3's record still names
`34864ff0547d2cff03e707414743a3b0cc8770b5`. This pin move does not append a
later head.

The measured commitment is covered by one RFC 3161 timestamp from
`http://timestamp.digicert.com`. The token bytes are the git note
`refs/notes/aureon-hnc-head` on the commit that records them. `make evidence`
reads that note, verifies the token locally against the system trust store,
and requires these bytes:

- `evidence/output/hnc_head_anchor.id` — the anchor id, SHA-256 of the token
- `evidence/output/hnc_head_anchor.json` — the measured record
- `evidence/output/hnc_head_anchor.tsr.b64` — the token

A working-tree edit does not move the note or the committed blob. Sequence 1
points at the genesis id. The timestamp authority's ordering flag is no, so
the monotonic rule is this chain: a later head must use the next sequence,
name this anchor id as `prev_anchor_id`, and carry a verified `gen_time` that
is strictly later. This receipt does not append a later head. The follow-on
below is that later head. It does not clear this HOLD.

This receipt does not set `external_head_anchor_attested` on the local
intrusion ledger. That flag stays false. The system is not reported alive.
Live trading stays off. No order is placed. `go_live_clear` stays false.

## Receipt 3 follow-on — next monotonic head

Measured. Sequence 2 only. Go-live is not clear. `go_live_clear` stays false.

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
against the system trust store. The authority's ordering flag is no. The
chain above is the monotonic rule.

The formula series sha256 is unchanged. This follow-on does not publish a
new HNC identity. The timestamp records historical public pin
`34864ff0547d2cff03e707414743a3b0cc8770b5`. The published require-pin is
`bb04503119681adcf832f3c3e9b0cbf09fc7a938`. This follow-on does not move it.
No market series is fetched.

`make evidence` reads sequence 2 from `refs/notes/aureon-hnc-head-next` on
HEAD and requires these bytes:

- `evidence/output/hnc_head_next.id` — SHA-256 of the sequence 2 token
- `evidence/output/hnc_head_next.json` — the measured record
- `evidence/output/hnc_head_next.tsr.b64` — the token

Fetch the note with `git fetch origin
refs/notes/aureon-hnc-head-next:refs/notes/aureon-hnc-head-next`. The check
does not contact the timestamp authority. A working-tree edit does not move
the note. The notes are attached to the commit that records these files:
`refs/notes/aureon-hnc-head` is the sequence 1 token, and
`refs/notes/aureon-hnc-head-next` is the sequence 2 token. The sequence 1
file in the tree is unchanged. A squash merge leaves both notes on the
pre-squash commit. Re-attach the same token bytes to the squash commit. Do
not request another timestamp to do that.

`external_head_anchor_attested` stays false. The system is not reported
alive. Live trading stays off. No order is placed. This follow-on is not
receipt 5 and does not produce an authenticated deployment receipt. The
go-live line for durable HNC evidence stays HOLD because the intrusion ledger
is not attested by this timestamp chain.

The stage-0 pack `reports/measured/baseline/` records published pin
`34864ff0547d2cff03e707414743a3b0cc8770b5` at checkout
`c68a89d2a184d99582bb24310b91e024323a212c`. That pack is historical. The
published require-pin is now `bb04503119681adcf832f3c3e9b0cbf09fc7a938`.
The pack is not rewritten.

Still HOLD. Receipt 1 is measured separately. Receipts 2 and 4 are
remeasured and do not clear. Receipt 5 is absent:

- exact target-source measurement and immutable release provenance
- complete source-boundary census closure
- authenticated deployment receipt and provider-side read-back

## Stage 6 artifacts

Receipt 2 is `measured/go_live_stage6_provenance.json`. Receipt 4 is
`measured/go_live_stage6_source_census.json` and
`docs/runbooks/GO_LIVE_STAGE6_SOURCE_CENSUS.md`. They measure pin
`bb04503119681adcf832f3c3e9b0cbf09fc7a938` and tip
`b2b0310362597dc520114de86d8700c0c50758d5`. Pin `bb045031` is the prior main
tip. Tip `b2b03103` retargets the published require-pin onto that commit and
does not change the `aureon/` bytes the digest measures. They do not clear
go-live. `go_live_clear` is false. Receipt 3 is the DigiCert section above
and is not part of this stage. Receipt 1 is measured at
`reports/measured/native_process_containment.json` and is not rewritten here.
Receipt 5 is absent. The census does not close the pin tree: symbols in that
tree are absent from `docs/mcp/inventory.json` and were not added. That
includes `aureon/evidence/hnc_anchor.py` and
`aureon/evaluation/market_series.py`. `http_get` stays unlisted so evaluation
is not moved to plan stage 4. Plan stages 3 and 4 stay closed. Reachable
stays the prior sweep's 69. Decision remains `HOLD`.

Operator contract names are not injected by go-live: `AUREON_OPERATOR_ENV`,
`AUREON_OPERATOR_API_KEY`, `AUREON_OPERATOR_RATE_RPS`,
`AUREON_OPERATOR_RATE_BURST`, `AUREON_OPERATOR_MAX_BODY`,
`AUREON_OPERATOR_TRUSTED_PROXY_CIDRS`, `AUREON_OPERATOR_HTTP_PROCESSES`,
`AUREON_OPERATOR_REPLICAS`.

## Receipt 1 — native process containment (stage 7)

Receipt 1 is measured. The cold boot is:

```bash
python -m aureon.containment.cold_boot
```

That command starts a new process with `unshare` (user, mount, pid, and net
namespaces). The default includes `--net`. Outbound network is not configured.
The measured record is `reports/measured/native_process_containment.json`, with
the same facts in `reports/measured/native_process_containment.md`. Read that
record for the cold-boot argv, the errno evidence, what remains allowed, and
the gaps. This paragraph is not the measurement.

An explicit allow path is `authorize_network_allow` in
`aureon.containment.native`. The cold boot does not call it for the contained
default. An environment variable cannot select it. A grant omits `--net` and
shares the parent network namespace. That path is audited. The receipt's
allow-path probe does not connect; it only compares namespace ids.

The public MCP sweep describes the same zero-network outcome inside one
interpreter: `mcp/aureon_public/sweep_guard.py` replaces `socket.socket`
in-process. That guard is cited, not this measurement. Stage 7 did not
change the guard or the pin. The measured receipt still names
`34864ff0547d2cff03e707414743a3b0cc8770b5` and `pin_changed: false`.
The published require-pin is now
`bb04503119681adcf832f3c3e9b0cbf09fc7a938`. This section does not re-run
the cold boot and does not rewrite
`reports/measured/native_process_containment.json`.

What an installer can start, once the other receipts exist, is this contained
process. Receipt 1 does not switch the official installers on. Docker,
Compose, Supervisor, systemd, shell, package, desktop, and cloud routes still
stop at the isolated bootstrap before target import. `scripts/linux/install-linux.sh`
still execs that bootstrap. No live instance is claimed.

## Receipts 2, 3, 4, and 5 remain HOLD

Go-live stays HOLD until receipt 5 exists: an authenticated deployment
receipt and provider-side read-back. Receipts 2 and 4 were remeasured and
do not supply that receipt. Receipt 3 is the DigiCert section above and
does not clear go-live. `go_live_clear` is false. The orange badge stays
HOLD.

- exact target-source measurement and immutable release provenance (HOLD)
- durable HNC evidence with an external monotonic head anchor (HOLD)
- complete source-boundary census closure (HOLD)
- authenticated deployment receipt and provider-side read-back (absent)

## Stage 8 — exchanges read surface

This slice measures the public exchanges catalog. It does not clear go-live.

`exchanges_gate` and `exchanges_surface` are on `aureon-public`. They read
`docs/mcp/inventory.json` for package `exchanges`. They do not import
`aureon.exchanges`. They do not place an order. They do not read keys.
The decision is HOLD. An environment variable cannot select EXECUTE.
Live orders on this surface stay refused when `AUREON_DISABLE_REAL_ORDERS`
is unset and when it is set to `0`.

The measured record is `measured/go_live_stage8_exchanges.json`.
`docs/runbooks/GO_LIVE_STAGE8_EXCHANGES.md` names the same facts.
This slice does not change `PINNED_COMMIT`. The orange release-boundary
badge stays HOLD. This slice does not publish a Space and does not repeat
the protocol or call-sweep records. `OPEN_PLAN_THROUGH` stays 2.
`ENABLED_THROUGH` stays 6. Exchanges reachable stays 0.
Plan stages 3 and 4 stay closed.
