# Stage 11 installer gate

The orange release-boundary badge stays HOLD. `go_live_clear` is not stored as
a true flag in this checkout. The system is not claimed alive. The public pin is not moved. No order is placed.

`scripts/bootstrap/go_live_stage11_gate.py` is the check. It imports only the
Python standard library. It does not import Aureon on the HOLD path. Run it
with `python -I -S -B`. `--check` prints nothing and exits 0 only when the
computed flag is true. `--json` prints the evaluation. `--launch-contained`
re-evaluates and, only when that evaluation is clear, replaces the process
with `python -m aureon.containment.cold_boot`. That command is the contained
process from receipt 1. It is not a trading launcher.

An environment variable cannot set the flag. `measured/go_live_clear.json` is
not read as authority. If that file exists, the gate reports it and does not
honor it. A receipt whose own `go_live_clear` field is true does not clear
the gate by itself.

## Who calls the gate

These three routes ask the gate, then keep the isolated bootstrap when the
gate is not clear. The bootstrap exec remains the last step. They do not
import a target while the decision is HOLD.

- `scripts/linux/install-linux.sh` — target `linux-supervisor`
- `deploy/start_master_launcher.sh` — target `master-launcher`
- `production/aureon.py` — target `production-supervisor`

`deploy/start_master_launcher.sh` looks for the gate at
`/app/scripts/bootstrap/go_live_stage11_gate.py`. The container image still
copies only the isolated bootstrap, so a stock image skips the gate and stays
on terminal HOLD. Docker, Compose, Supervisor, systemd, and the other shell
routes that exec the isolated bootstrap directly are unchanged.

`production/install.sh` and `scripts/launch/aureon-master.sh` are the local
canonical boot. They are not this release-boundary path. This stage does not
switch them on or off and does not treat them as go-live.

## Exact checklist

`verified_on_tip` requires the recorded tip to be the current `git rev-parse HEAD`
(40 or 64 hex characters). A parent commit is not this tip. Every receipt must
name public pin `34864ff0547d2cff03e707414743a3b0cc8770b5`. `system_alive: true`,
`live_trading: true`, or `orders_placed: true` fails that receipt. The gate's
own `system_alive`, `live_trading`, and `orders_placed` fields stay false.

`go_live_clear` is true only when receipts 1, 2, 3, 4, and 5 are all
`verified_on_tip`. The README badge is not edited by the gate. When the
computed flag is true and the README still says HOLD, `badge_edit_required`
is true and a later change may update the badge. This checkout does not.

1. **native process containment with a zero-network default.** Path
   `reports/measured/native_process_containment.json`. Schema
   `aureon.measured.native-process-containment.v1`. Receipt number 1.
   `git_head_at_measurement` equals HEAD. `worktree_dirty_at_measurement` is
   false. `verdict` is `pass`. `allowed_at_default` is `none`.
   `cold_boot_argv` contains `--net` and `cold_boot_argv_has_net` is true.
   `market_data_fetched` and `pin_changed` are not true. `tags.system_alive`
   is `not claimed`. Every `source_sha256` entry matches the current file.

2. **exact target-source measurement and immutable release provenance.** Path
   `measured/go_live_stage6_provenance.json`. Schema
   `aureon.go-live.release-provenance.v1`. Receipt number 2. `tip` equals
   HEAD. `aureon_trees_match` and `inventory_blobs_match` are true.
   `release_tree_sha256` is 64 hex characters. `digest` is the SHA-256 of the
   canonical JSON object with the `digest` key removed, including the trailing
   newline used by `scripts/validation/go_live_stage6.py`.

3. **durable HNC evidence with an external monotonic head anchor.** Path
   `evidence/output/hnc_head_anchor.json`. Schema
   `aureon.evidence.hnc-head-anchor.v1`. Receipt number 3. `tag` is
   `measured`. `hnc_identity_changed` is false. `external.kind` is `rfc3161`
   and `external.provider_contacted_by_check` is false. The gate does not
   contact the timestamp authority. `anchor_id` equals the SHA-256 of the
   decoded token in `evidence/output/hnc_head_anchor.tsr.b64` and
   `evidence/output/hnc_head_anchor.id`. `refs/notes/aureon-hnc-head` on HEAD
   exists and equals `HEAD:evidence/output/hnc_head_anchor.tsr.b64`. The gate
   does not fetch that note.

4. **complete source-boundary census closure.** Path
   `measured/go_live_stage6_source_census.json`. Schema
   `aureon.go-live.source-boundary-census.v1`. Receipt number 4. `tip` equals
   HEAD. `source_boundary_closed` is true. `missing_from_source` is an empty
   list. `open_gaps` does not include `post_pin_checkout_not_in_closure`.
   `provenance_digest` matches receipt 2 when receipt 2's digest verifies.

5. **authenticated deployment receipt and provider-side read-back.** Path
   `measured/go_live_receipt5_authenticated_deployment.json`. Schema
   `aureon.go-live.authenticated-deployment-receipt.v1`. Receipt number 5.
   `tip` equals HEAD. `authenticated` is true. `provider_side_readback` is
   true. `provider` is a non-empty name other than local, localhost,
   bootstrap, isolated, self, or unspecified. `readback_body_sha256` is 64
   hex characters. `deployment_id` is a non-empty string.
   `isolated_bootstrap_receipt_is_not_this` is true. `system_alive` is false.
   The isolated bootstrap's local HOLD receipt is not this receipt. On this
   tip the artifact is absent. This stage does not create it.

## This checkout

The receipt artifacts are the ones from stage 7 tip
`bb04503119681adcf832f3c3e9b0cbf09fc7a938`. This change does not replace
them. The gate compares them with the checked-out HEAD, so they also fail
on any descendant commit that leaves them in place. Receipt 1's measurement
head is `c68a89d2a184d99582bb24310b91e024323a212c` and the worktree was dirty
at measurement. Receipts 2 and 4 record that same older tip, and receipt 4
still names `post_pin_checkout_not_in_closure`. Receipt 3's git note is not
on `bb045031` (the published note is on `7d26871ff007ec6c84be657297827fc813fe7428`,
which is not this history). Receipt 5's artifact is absent. `go_live_clear`
is false. The badge stays HOLD. Pin re-publish is not this change.
