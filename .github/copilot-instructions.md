# Aureon repository safety instructions

The canonical release is on terminal `HOLD`. Do not suggest or execute direct
runtime, provider, exchange, balance, credential, listener, deployment,
installer, packaging, or live-data commands from this checkout.

Canonical operational entrypoints must enter
`scripts/bootstrap/protected_bootstrap_v05.py` through a fixed repository Python
with `-I -S -B`, or emit a non-mutating machine-readable HOLD receipt. A source
module, simulation, diagnostic, imported snapshot, test pass, or environment
flag cannot authorize operation.

Preserve imported/archive provenance and dirty user work. Keep credentials and
private runtime state out of source. Report missing data and unresolved gates
honestly. Production requires complete source coverage, native outer process
containment, externally anchored HNC evidence, signed packaging, and
authenticated provider read-back.
