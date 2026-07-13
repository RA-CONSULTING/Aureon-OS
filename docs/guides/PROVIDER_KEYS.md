# 🔑 Provider API keys — bring your own key for every model

Aureon's operator switchboard fans a prompt across whichever LLMs you've enabled.
The **Providers** page (UI → *Cognition & LLM → Providers*) lets you paste each
provider's API key, test it, pick a model, and turn the line on — no file editing,
no restart.

Supported providers (all optional, all key-gated):

| Provider | Kind | Get a key |
|---|---|---|
| OpenAI (ChatGPT) | native | platform.openai.com/api-keys |
| Anthropic (Claude) | native | console.anthropic.com/settings/keys |
| xAI (Grok) | native | console.x.ai |
| Google (Gemini) | native | aistudio.google.com/apikey |
| Ollama (local or cloud) | self-hosted | ollama.com/settings/keys (cloud) — blank for local |
| DeepSeek · Mistral · Groq · OpenRouter · Perplexity | OpenAI-compatible | each provider's key page (linked in the UI) |

## How it works

```
Providers UI  →  POST /api/providers/<id>  →  encrypted keystore  →  os.environ  →  switchboard rebuild
```

1. You paste a key (and optionally a model / base URL) and hit **Save**.
2. It's written to an **encrypted keystore** on the server — `~/.aureon/provider_keys.json.enc`,
   sealed with Fernet (key file `~/.aureon/provider_keys.key`, mode 0600). Never committed.
3. The operator injects the stored values into the process environment
   (`keystore.apply_to_env()`) and **rebuilds the switchboard live** — the new line
   is usable immediately, no restart.
4. **Test** (`POST /api/providers/<id>/test`) does one real round-trip against the
   provider with your key and reports latency or the exact error.

The keystore is the control plane: a key set here overrides the same variable in
`.env`. Disable a provider and its key is removed from the environment (the line
drops out) but kept in the store so you can re-enable it. **Clear** forgets it.

## What you see vs. what's stored

- The API returns keys **masked** (`••••1234`, last four only) — the full key is
  never sent back to the browser or written to logs.
- `GET /api/providers` lists every provider with `{model, base_url, has_key,
  key_masked, key_source: keystore|env|none, enabled, live}`.

## Security

- Keys are **encrypted at rest** and git-ignored (`.aureon/`, `provider_keys.*`).
- Nothing logs a full key; the test endpoint never persists.
- The write/test/delete endpoints live under `/api/*`, so they are covered by the
  operator's bearer gate. **For any shared or public deployment, set
  `AUREON_OPERATOR_API_KEY`** so only holders of that token can change keys. When
  the gate is on, the console must send `Authorization: Bearer <key>` (the default
  self-hosted posture leaves it open on a trusted box).
- This is **instance-owned**: one key set for the running Aureon, used for everyone
  it serves. Per-user "bring your own key" is a future phase.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/providers` | list providers + masked status |
| POST | `/api/providers/<id>` | set `{api_key?, base_url?, model?, enabled?}` → persist + rebuild |
| POST | `/api/providers/<id>/test` | real round-trip test (does not persist) |
| DELETE | `/api/providers/<id>` | forget the key + unset its env |

Prefer files? The same keys work as environment variables / `.env` entries — see
`.env.example`. The UI just makes it encrypted, testable, and hot-reloaded.
