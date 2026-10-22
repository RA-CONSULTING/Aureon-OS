# Token Flow Guide

Classroom Mode is designed to prevent token explosion.

## Main Chat

The main provider request keeps its existing payload:

```text
role prompt + current user message
```

## Mirrored Context

After the assistant reply, Classroom Mode sends a compact mirrored event:

```text
user message + assistant reply + provider metadata + enabled observers
```

## Context Limits

Backend truncation is controlled by observation depth:

- `shallow`: about 900 characters
- `standard`: about 1800 characters
- `deep`: about 3200 characters

The split favors assistant output slightly because reflections usually depend on both the request and the response.

## Current Token Accounting

The current system estimates token use locally with:

```text
estimated_tokens = ceil(characters / 4)
```

This is intentionally conservative enough for dashboard analytics, but not a billing-grade tokenizer.

## Future Upgrades

- Provider-specific tokenizers
- Observer call budgets per hour
- Backpressure when provider quotas are low
- Embedding queue with deduplication
- Durable token ledger in D1 or SQLite
