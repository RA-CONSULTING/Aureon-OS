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
below and do not clear go-live. Receipt 5 is a stage 10 HOLD skip. None of
these is inferred into a clear:

- native process containment with a zero-network default (receipt 1, measured;
  see below);
- exact target-source measurement and immutable release provenance (receipt 2,
  remeasured, HOLD);
- durable HNC evidence with an external monotonic head anchor (receipt 3,
  measured, HOLD);
- complete source-boundary census closure (receipt 4, remeasured, the pin
  tree is not closed, HOLD);
- authenticated deployment receipt and provider-side read-back (receipt 5,
  stage 10 skip, HOLD).

Until receipt 5 is a provider read-back, the correct outcome is `HOLD`, not
a partially configured listener. The stage 10 file is a skip. Upload and
read-back stay off without an explicit opt-in. The orange release-boundary
badge stays HOLD. `go_live_clear` stays false. This document does not say
the system is alive.

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
is strictly later. This receipt does not append a later head.

This receipt does not set `external_head_anchor_attested` on the local
intrusion ledger. That flag stays false. The system is not reported alive.
Live trading stays off. No order is placed.

Still HOLD. Receipt 1 is measured separately. Receipts 2 and 4 are
remeasured and do not clear. Receipt 5 is a skip:

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
Receipt 5 is a stage 10 skip and is not part of this stage. The census
does not close the pin tree: symbols in that tree are absent from
`docs/mcp/inventory.json` and were not added. That
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

## Receipt 5 — authenticated deployment (stage 10)

Receipt 5 is not complete. The measured file is a HOLD skip. Nothing was
published.

The runner is:

```bash
python scripts/validation/go_live_receipt5.py
python scripts/validation/go_live_receipt5.py --check
```

`--check` re-reads `reports/measured/go_live_receipt5_deployment.json` and
`reports/measured/go_live_receipt5_deployment.md` and probes this machine for
local auth files. It does not deploy and it does not read a provider back.
The JSON is the record. This paragraph is not the measurement.

At tip `9333bfbbeb8de54a4b42be05f9263e536da643a7` the probe found no Hugging
Face token and no Google Cloud credential. No deploy was attempted. No
provider API was called. The read-back digest is null. A localhost process
was not substituted for a provider.

Upload and provider read-back are off by default. A Hugging Face token does
not turn them on. Both stay off unless `AUREON_RECEIPT5_ALLOW_HF_UPLOAD=1`.
The runner does not send hardware identifiers or personal data. Before any
upload it reads the Space and refuses the upload when the Space is not
private, the hardware is not free `cpu-basic`, or the SDK is not `gradio`.
`create_repo(..., exist_ok=True)` does not change privacy, hardware, or SDK,
so it is not that check, and the runner does not send `space_hardware`.
A new Space stays private unless `AUREON_RECEIPT5_HF_PUBLIC=1`, and that
public opt-in does not relax the check on a Space that already exists.
Cloud Run upload and read-back stay off unless
`AUREON_RECEIPT5_ALLOW_CLOUD_RUN_DEPLOY=1` and a service, project, region,
and image are already set.

If an opted-in upload finishes and a later read fails, the receipt stays
incomplete and keeps a null digest. It records that the provider was called
and the upload happened. Those flags do not stay false after the upload.

The public pin recorded on this receipt is the published require-pin
`bb04503119681adcf832f3c3e9b0cbf09fc7a938` (`PINNED_COMMIT` in
`mcp/aureon_public/guard_loader.py` at this tip). This receipt does not move
it. `evidence/output/hnc_head_anchor.json` `public_require_pin` stays
`34864ff0547d2cff03e707414743a3b0cc8770b5`. That field is receipt 3. This
receipt does not rewrite it.

`go_live_clear` stays false. The orange release-boundary badge stays HOLD.
A later badge flip is stage 11 and a separate PR. This file does not report
the system alive. Official installers are unchanged. Receipts 1–4 were not
re-run here.

Live trading stays off. No order is placed. No tunnel is opened. MCP plan
stages 3 and 4 stay closed.

## Receipts 2, 3, 4, and 5 remain HOLD

Receipt 5 does not clear the release. Receipts 2 and 4 were remeasured and
do not supply a provider read-back. Receipt 3 is the DigiCert section above
and does not clear go-live. These stay open, and this change does not
re-judge them:

- exact target-source measurement and immutable release provenance (HOLD)
- durable HNC evidence with an external monotonic head anchor (HOLD)
- complete source-boundary census closure (HOLD)
- authenticated deployment receipt and provider-side read-back (skip only;
  see receipt 5)

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
