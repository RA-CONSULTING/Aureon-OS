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
- worker env secrets for provider API keys as needed during deploy

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
