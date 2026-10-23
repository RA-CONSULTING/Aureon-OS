# Classroom Mode Architecture

Classroom Mode turns CodexPROsSparrow into a multi-agent observation layer around the main chat.

It does not train foundation models. It mirrors conversation context into observer agents that analyze, summarize, and build session memory.

## Runtime Shape

Main flow:

```text
User -> Main Chat Provider -> Assistant Reply
                         -> Context Stream Bus
                         -> Observer Agents Pool
                         -> Session Memory + Analytics
```

## Components

- Main chat: the visible conversation with the primary model.
- Classroom sidebar: UI for enabling observation, adding observers, and viewing stream state.
- Observer agents: silent analyzers that receive mirrored context after the main reply.
- Context stream: compact event log of mirrored turns.
- Memory pipeline: session summaries, coding patterns, workflow traces, and inconsistency notes.
- Replay endpoint: exposes recent session events and reflections.

## Backend Endpoints

- `POST /api/chat`: primary chat call.
- `POST /api/classroom/observe`: mirrored context ingestion and observer processing.
- `GET /api/classroom/state`: current memory and analytics.
- `GET /api/classroom/replay`: recent events, reflections, and memory.

## Deployment Notes

Local Node stores memory in `logs/classroom-memory.json`.

Cloudflare Worker keeps memory in runtime memory. For durable cloud memory, add KV, D1, or R2 later.
