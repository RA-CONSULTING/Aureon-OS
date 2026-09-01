# Metacognition architecture — source present, runtime HOLD

Aureon contains a metacognition monitor that can assess provenance-stamped HNC,
organism-consensus, prediction, Auris, Lighthouse, and action signals and feed a
bounded self-assessment back into the shared field. This is an implementation
description, not a verified production outcome.

The historical multi-daemon benchmark started HNC, organism, and operator
processes, opened a local listener, and wrote traces. That route is now a
terminal non-mutating `HOLD` receipt because the native outer process boundary
and complete source protection have not been attested. Historic reports and
in-process tests do not prove a currently protected live self-loop.

Offline unit and compliance tests may still validate pure source contracts.
Do not start the daemons or expose the read surface from this checkout. Current
release decision: `HOLD`.
