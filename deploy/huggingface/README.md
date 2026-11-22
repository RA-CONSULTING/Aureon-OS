---
title: Aureon OS / HNC
emoji: 🌀
colorFrom: indigo
colorTo: yellow
sdk: docker
app_port: 7860
suggested_hardware: l40s
license: mit
short_description: Aureon OS, HNC evidence, and the canonical Aureon 7B own-model demo
models:
  - GaryLeckey/aureon-7b
---

# Aureon OS / Harmonic Nexus Core

*The gods do not speak in words. They speak in ratios.*

This is the public, paper-only Aureon OS console and HNC evidence deployment. It uses the canonical **Aureon 7B** checkpoint through Aureon's own loopback model server. It does not borrow a hosted chat model and does not substitute a synthetic completion when Aureon is unavailable.

- Source: [RA-CONSULTING/Aureon-OS](https://github.com/RA-CONSULTING/Aureon-OS)
- Model and evaluation: [GaryLeckey/aureon-7b](https://huggingface.co/GaryLeckey/aureon-7b)
- Isambard data: [GaryLeckey/aureon-isambard-data](https://huggingface.co/datasets/GaryLeckey/aureon-isambard-data)
- Isambard runs: [GaryLeckey/aureon-isambard-runs](https://huggingface.co/datasets/GaryLeckey/aureon-isambard-runs)
- Remaining archive: [GaryLeckey/aureon-isambard-archive](https://huggingface.co/datasets/GaryLeckey/aureon-isambard-archive)

## Explore

- `/` and `/app/` serve the rebuilt Aureon console.
- `/hnc/` is the accessible evidence view.
- `/api/demo/status` reports the exact own-model route and public safety checks.
- `/api/hnc/status` reads the current HNC organ and canonical field state.
- `/api/hnc/replay` compares a fresh rerun with the committed HNC record, with multiverse off and on.
- `/api/hnc/organism-replay` labels recorded circulation separately from the seed `20261024` synthetic fault block.
- `/healthz` is process liveness only. `/readyz` is strict aggregate readiness and remains `503` until the operator, exact model revision, weight identity, CUDA startup generation, and public posture all pass.

### Bounded own-model generation

`POST /api/demo/generate` accepts only JSON with `prompt` and optional `max_tokens`. Prompts are limited to 4,096 characters, completions to 64 tokens, and generation is deterministic (`temperature=0`). Requests are rate-limited and concurrency-bounded. There are no tools, streaming, exchange calls, or provider fallbacks on this route.

```bash
curl -sS https://garyleckey-aureon-os.hf.space/api/demo/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Return one short JSON object with an ok field.","max_tokens":32}'
```

Responses identify `provider_mode=aureon_own_model`, `model=aureon-7b-v65k`, actual token usage, finish reason, and the HNC gear receipt. Prompt and completion bodies are not logged by the demo service.

## Honest capability and safety boundary

The model was trained from random initialization and then received 1,578 SFT steps. The existing 1,125-row evaluation measured a **46.24% parse rate**, symbol recall **0.2411196294744682**, and overall line F1 **0.035554558485818205**. These are capability limitations, not production-readiness claims. Read the model card and evaluation receipt before relying on an output.

**Live trading is off. No real orders are placed.** Exchange and provider credentials are removed from the public runtime. Approval files from an earlier process are not honored. Generic operator, Fusion, credential, terminal-state, provider, connection, approval, switchboard, pulse, fleet, and MCP routes are not public. Possession of an internal bearer does not unlock a public mutation.

The target runtime is one Nvidia L40S with 48 GB GPU memory, 62 GB RAM, and 380 GB disk. Hardware selection alone is not a validation result. The release manifest records the actual image, model revision, hardware, smoke receipt, browser checks, and performance measurements after those checks run.

## Immutable model loading

The container requires `AUREON_MODEL_REVISION` to be the full lowercase commit of `GaryLeckey/aureon-7b`. Startup downloads only that revision's allowlisted files, checks the preparation receipt, independently hashes `model.safetensors`, loads bf16 on CUDA, and completes a real greedy generation before opening the internal model port.

Canonical weight identity:

- File: `model.safetensors`
- Size: `13,990,806,664` bytes
- SHA-256: `48487f800623474ab99371d71b369694cae64f8ebc4ef038019c7e60da3d45bb`

The tokenizer's source `model_max_length=4096` is preserved. The server bound is 8,192 positions; this is not a claim of tested long-context quality.

Deployment and verification instructions live in [`deploy/huggingface/PUBLISH.md`](https://github.com/RA-CONSULTING/Aureon-OS/blob/main/deploy/huggingface/PUBLISH.md).
