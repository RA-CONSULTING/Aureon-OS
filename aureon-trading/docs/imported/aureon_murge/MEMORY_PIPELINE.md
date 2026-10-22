# Memory Pipeline

The memory pipeline creates session-level context artifacts from the mirrored stream.

## Memory Types

- summaries: compact turn-level context
- patterns: implementation and integration patterns
- inconsistencies: contradictions, failed assumptions, and broken paths
- workflows: user goals and operational sequences
- reflections: observer-specific analysis notes

## Local Storage

Node runtime persists memory to:

```text
logs/classroom-memory.json
```

This file is intentionally under `logs/` and should not be committed.

## Cloud Storage

Cloudflare Worker runtime currently uses in-memory state. This keeps the deployment simple and free-friendly.

For durable cloud memory, use one of these later:

- KV: simple session state and small memory objects
- D1: structured replay, analytics, and observer events
- R2: larger archives and exported conversation bundles

## Replay

Replay data is available from:

```text
GET /api/classroom/replay
```

Replay returns recent mirrored events, reflections, and memory groups. It is meant for analysis and debugging, not full transcript reconstruction.
