# Go-live status: terminal HOLD

There is no supported live Aureon instance in the current release. Official
Docker, Compose, Supervisor, systemd, shell, package, desktop, and cloud routes
stop before target import or process start. The cloud manifests define zero
components and no secret bindings.

Do not expose listeners, inject credentials, enable trading, create tunnels, or
use direct module execution as a substitute for the missing release boundary.
Historical listener and environment guidance is withdrawn.

Go-live requires all of the following. Receipt 1 is measured (stage 7).
Receipts 2–5 are not, and none of them is inferred from a local test pass:

- native process containment with a zero-network default (receipt 1, measured;
  see below);
- exact target-source measurement and immutable release provenance (HOLD);
- durable HNC evidence with an external monotonic head anchor (HOLD);
- complete source-boundary census closure (HOLD);
- authenticated deployment receipt and provider-side read-back (HOLD).

Until receipts 2–5 exist, the correct outcome is `HOLD`, not a partially
configured listener. The orange release-boundary badge stays HOLD.

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
in-process. That guard is cited, not this measurement, and this stage does
not change it. The public pin stays
`34864ff0547d2cff03e707414743a3b0cc8770b5`. `AUREON_PUBLIC_REQUIRE_PIN` is
unchanged.

What an installer can start, once the other receipts exist, is this contained
process. Receipt 1 does not switch the official installers on. Docker,
Compose, Supervisor, systemd, shell, package, desktop, and cloud routes still
stop at the isolated bootstrap before target import. `scripts/linux/install-linux.sh`
still execs that bootstrap. No live instance is claimed.

## Receipts 2–5 remain HOLD

- exact target-source measurement and immutable release provenance
- durable HNC evidence with an external monotonic head anchor
- complete source-boundary census closure
- authenticated deployment receipt and provider-side read-back
