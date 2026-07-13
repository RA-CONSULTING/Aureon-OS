# Observer System Guide

Observers silently watch the conversation stream. They do not write into the main chat unless a future explicit setting enables it.

## Default Observers

- Logic Auditor: detects contradictions, failed routes, quota risks, and weak assumptions.
- Code Pattern Miner: extracts implementation patterns, API flows, deploy steps, and file-level workflows.
- Memory Curator: creates compact memory summaries from each turn.
- Workflow Tracker: follows active user goals and repeated operational patterns.

## Observer State

Each observer tracks:

- model name
- role
- activity state
- estimated token usage
- memory item count
- latest reflection
- last run time

## Routing Rules

The frontend mirrors context only when Classroom Mode is enabled.

The backend truncates mirrored context based on observation depth:

- `shallow`: low context, fastest
- `standard`: balanced default
- `deep`: larger context, higher token budget

## Safety Rules

- Observers remain silent by default.
- Observers run after the main response.
- Observers receive truncated context.
- Observer count is capped by backend routing.
- The system stores reflections, not raw full-history transcripts.
