# Aureon quick status

Operational quick-start instructions are intentionally disabled. The current
release decision is `HOLD`: full source protection, native process containment,
and externally anchored HNC evidence have not been attested.

For controlled validation, run the repository test suites and the isolated
protected bootstrap contracts. Do not copy credentials, start a listener,
activate an exchange client, or treat a local test pass as deployment approval.

Public environment postures — guarded offline, read-only market fetch, and
explicitly disabled live orders — are in [`PUBLIC_ENV.md`](PUBLIC_ENV.md).
`.env.example` uses placeholder names only. A real key never goes in that file.
