# Environment Variables Snapshot

Date: 2026-05-14

This file documents variable names and responsibilities only.
It does not include secret values.

## Web/server provider variables

- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `HF_TOKEN`
- `HUGGINGFACE_API_KEY`
- `OLLAMA_API_KEY`
- `AUREON_EXTERNAL_LLM_FALLBACK`
- `AUREON_LLM_BASE_URL`
- `AUREON_LLM_MODEL`
- `AUREON_OLLAMA_REASONING_EFFORT`
- `AUREON_API_BASE_URL`
- `AUREON_API_KEY`
- `AUREON_CHAT_PATH`
- `AUREON_VAULT_PATH`
- `GARY_AUREON_ROOT`

## Web/server execution variables

- `TERMINAL_ALLOW_REMOTE`
- `TERMINAL_TRUSTED_ORIGINS`
- `SANDBOX_TERMINAL_ENABLED`
- `SANDBOX_IMAGE`
- `SANDBOX_WORKSPACE_ROOT`
- `SANDBOX_LOG_DIR`
- `SANDBOX_MEMORY_BYTES`
- `SANDBOX_NANO_CPUS`
- `SANDBOX_COMMAND_TIMEOUT_MS`
- `LOCAL_AUREON_CLI_ENABLED`

## Companion runtime variables

- `FLAMEBORN_RUNTIME_HOST`
- `FLAMEBORN_RUNTIME_PORT`
- `FLAMEBORN_RUNTIME_ALLOW_REMOTE`
- `FLAMEBORN_RUNTIME_TRUSTED_ORIGINS`
- `DOCKER_SOCKET`
- `SANDBOX_IMAGE`
- `SANDBOX_WORKSPACE_ROOT`
- `SANDBOX_LOG_DIR`
- `SANDBOX_MEMORY_BYTES`
- `SANDBOX_NANO_CPUS`
- `SANDBOX_COMMAND_TIMEOUT_MS`

## Cloudflare / workers

- `CLOUDFLARE_API_TOKEN`
- `OLLAMA_API_KEY` must be stored as a Worker secret, never a plain `vars` value
- the non-secret Ollama routing variables above may be Worker environment variables
- other provider API keys remain optional; Ollama is the final external fallback

## Supabase Edge Functions

- store `OLLAMA_API_KEY` in Supabase project secrets
- set `AUREON_EXTERNAL_LLM_FALLBACK=ollama`
- set `AUREON_LLM_BASE_URL=https://ollama.com/v1`
- set `AUREON_LLM_MODEL` to the approved cloud model
- set `AUREON_OLLAMA_REASONING_EFFORT=none` for short structured calls
- never expose these values through a `VITE_` variable; the browser calls the
  authenticated `auris-classify` Edge Function instead

## Local Aureon launcher

- `AUREON_DIR`
- `AUREON_PORT`
- `AUREON_OBSIDIAN_VAULT_PATH`
- `AUREON_PYTHON`
- `AUREON_VOICE_BACKEND`
- `AUREON_LLM_OFFLINE`
- `AUREON_LLM_BASE_URL`
- `AUREON_LLM_MODEL`
- `AUREON_LLM_API_KEY`
- `OPENROUTER_API_KEY`

## Environment separation for migration

Recommended separation going forward:

### WEB_ENV
- Cloudflare worker deploy secrets
- browser-safe and worker-safe provider routing config
- web deployment settings

### DESKTOP_ENV
- local runtime config
- desktop OAuth redirect settings
- local Docker/runtime paths
- local-only host execution settings
