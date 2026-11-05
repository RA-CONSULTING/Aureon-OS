# Go-live status: terminal HOLD

There is no supported live Aureon instance in the current release. Official
Docker, Compose, Supervisor, systemd, shell, package, desktop, and cloud routes
stop before target import or process start. The cloud manifests define zero
components and no secret bindings.

Do not expose listeners, inject credentials, enable trading, create tunnels, or
use direct module execution as a substitute for the missing release boundary.
Historical listener and environment guidance is withdrawn.

Go-live requires all of the following, none inferred from a local test pass:

- native process containment with a zero-network default;
- exact target-source measurement and immutable release provenance;
- durable HNC evidence with an external monotonic head anchor;
- complete source-boundary census closure;
- authenticated deployment receipt and provider-side read-back.

Until those receipts exist, the correct outcome is `HOLD`, not a partially
configured listener.

## Receipt 3 — durable HNC evidence

Measured for this receipt only. Go-live is not clear.

The fixed-seed formula path in `aureon.evidence.hnc` is unchanged. Its series
sha256 matches the series recorded at public pin
`34864ff0547d2cff03e707414743a3b0cc8770b5`. This receipt does not publish a new
HNC identity and does not move `AUREON_PUBLIC_REQUIRE_PIN`. No market series
is fetched.

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
is strictly later. This receipt does not append a later head.

This receipt does not set `external_head_anchor_attested` on the local
intrusion ledger. That flag stays false. The system is not reported alive.
Live trading stays off. No order is placed.

Still HOLD, with no receipt from this change:

- native process containment with a zero-network default
- exact target-source measurement and immutable release provenance
- complete source-boundary census closure
- authenticated deployment receipt and provider-side read-back

## Stage 6 artifacts

Receipt 2 is `measured/go_live_stage6_provenance.json`. Receipt 4 is
`measured/go_live_stage6_source_census.json` and
`docs/runbooks/GO_LIVE_STAGE6_SOURCE_CENSUS.md`. They measure pin
`34864ff0547d2cff03e707414743a3b0cc8770b5` and tip
`c68a89d2a184d99582bb24310b91e024323a212c`. They do not clear go-live.
Receipt 3 is the DigiCert section above and is not part of this stage.
Receipts 1 and 5 are absent. The census closes the pin tree. This checkout
also has `aureon/evidence/hnc_anchor.py` and
`aureon/evaluation/market_series.py`. Those paths are named in the census
and are not added to the inventory. Plan stages 3 and 4 stay closed.
Decision remains `HOLD`.

Operator contract names are not injected by go-live: `AUREON_OPERATOR_ENV`,
`AUREON_OPERATOR_API_KEY`, `AUREON_OPERATOR_RATE_RPS`,
`AUREON_OPERATOR_RATE_BURST`, `AUREON_OPERATOR_MAX_BODY`,
`AUREON_OPERATOR_TRUSTED_PROXY_CIDRS`, `AUREON_OPERATOR_HTTP_PROCESSES`,
`AUREON_OPERATOR_REPLICAS`.
