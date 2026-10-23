# Aureon Brain Integration

This app integrates Aureon safely as a separate brain provider, not as a full repository merge.

## Current Integration Level

Implemented in flAmeBornLLC / LLM Academy:

- `Aureon Brain` provider in the model/provider menu.
- `Aureon Queen Observer` preset in Classroom Mode.
- Local filesystem vault logging for local Node runs.
- Cloudflare Worker-safe status mode when no remote Aureon bridge is configured.
- Optional remote bridge call using `AUREON_API_BASE_URL`.
- Safe default: no autonomous trading, no Queen execute actions, no external filesystem access from Cloudflare.

## Gary's Three Requested Integrations

### 1. Obsidian Bridge

Local Node mode writes chat turns to:

```text
logs/aureon-vault/daily/YYYY-MM-DD.md
logs/aureon-vault/sessions/YYYY-MM-DD.jsonl
```

This mirrors the Obsidian filesystem-vault idea from Aureon without requiring the Obsidian app to be running.

Cloudflare mode cannot write local files. For production Obsidian memory, Gary needs to expose an Aureon bridge endpoint and the Worker will call it.

### 2. Ollama Fallback

The app is prepared to call Aureon's backend as:

```text
POST ${AUREON_API_BASE_URL}${AUREON_CHAT_PATH}
```

Default path:

```text
/api/message
```

The actual Ollama fallback should live behind Gary's Aureon backend, using Aureon's `OpenMultiAgent`, `OllamaBridge`, and `OllamaLLMAdapter`.

### 3. Queen / Meta-Cognitive Layer

The app currently treats Queen as a controlled observer/provider layer:

- Main provider: `Aureon Brain`
- Classroom observer: `Aureon Queen Observer`
- Safe default: observer/status only
- Explicitly not enabled: autonomous execution, trading, self-modification, real-world actions

## Environment Variables

Local Node or Cloudflare Worker secrets:

```bash
AUREON_API_BASE_URL=http://127.0.0.1:5000
AUREON_CHAT_PATH=/api/message
AUREON_API_KEY=optional-token-if-gary-requires-it
```

Local Node only:

```bash
AUREON_VAULT_PATH=/home/l/CodexPROsSparrow/logs/aureon-vault
```

## Expected Remote Request Shape

The app sends:

```json
{
  "text": "user message",
  "message": "user message",
  "voice": "queen",
  "model": "aureon-brain",
  "provider": "aureon",
  "rolePrompt": "system prompt",
  "context": {
    "app": "flAmeBornLLC LLM Academy",
    "mode": "aureon-brain",
    "classroom": "observer-compatible"
  }
}
```

## Accepted Response Shapes

Any of these text fields will work:

```json
{ "reply": "..." }
{ "response": "..." }
{ "text": "..." }
{ "message": "..." }
{ "message": { "content": "..." } }
{ "statement": { "text": "..." } }
{ "result": { "text": "..." } }
```

## Recommended Next Step

Ask Gary to run or expose a minimal bridge around Aureon's vault UI / OpenMultiAgent:

```text
GET  /api/status
POST /api/message
GET  /api/queen/status
GET  /api/queen/memory
```

Then set `AUREON_API_BASE_URL` in Cloudflare secrets and the app will use Aureon as a real brain provider.

## Confirmed Existing Aureon Phi Bridge

Gary's repo already contains the bridge we need:

```text
aureon/vault/ui/server.py
scripts/runners/run_vault_ui.py
aureon/harmonic/phi_bridge.py
aureon/harmonic/phi_bridge_mesh.py
```

Confirmed endpoints in the existing Aureon Vault UI / Phi Bridge server:

```text
GET  /api/status
POST /api/message
GET  /api/message/<job_id>
GET  /api/health
GET  /api/bridge/info
GET  /api/bridge/state
POST /api/bridge/sync
POST /api/bridge/cards
GET  /api/bridge/mesh/info
GET  /api/queen/status
GET  /api/queen/memory
```

The correct local Aureon base URL after starting the vault UI is:

```text
http://127.0.0.1:5566
```

The flAmeBorn adapter now sends:

```json
{
  "text": "user message",
  "message": "user message",
  "voice": "queen",
  "fast": true,
  "peer_id": "flameborn-academy",
  "model": "aureon-brain",
  "provider": "aureon"
}
```

It reads Aureon responses from:

```text
utterance.response.text
```

and also supports the generic fallback response shapes listed above.

## Local Startup Script

Use this script to run Gary's Aureon Phi Bridge and our app together:

```bash
bash scripts/start_aureon_brain_local.sh
```

This starts:

```text
Aureon Phi Bridge: http://127.0.0.1:5566
flAmeBorn app:      http://127.0.0.1:4173
```

The script uses safe local defaults:

```text
AUREON_VOICE_BACKEND=local
AUREON_LLM_OFFLINE=0
AUREON_LLM_BASE_URL=https://openrouter.ai/api/v1
AUREON_LLM_MODEL=qwen/qwen-2.5-7b-instruct
--no-signals
--no-ollama
```

If `OPENROUTER_API_KEY` is loaded in the shell, the launcher passes it to Aureon as `AUREON_LLM_API_KEY`.

This avoids live trading and heavy local services while testing Gary's human-facing Vault Voice path. `AUREON_VOICE_BACKEND=brain` is intentionally avoided for chat because it uses Aureon's market/trading `AureonBrainAdapter` and can return trading JSON instead of human conversation.

Model/voice options in the app:

```text
aureon-queen     -> voice: queen
aureon-council   -> voice: council
aureon-architect -> voice: architect
aureon-lover     -> voice: lover
aureon-vault     -> voice: vault
aureon-miner     -> voice: miner
aureon-scout     -> voice: scout
```

Confirmed deeper Aureon layers in Gary's repo:

```text
aureon/vault/voice/vault_voice.py
aureon/vault/voice/self_dialogue.py
aureon/vault/voice/thought_stream_loop.py
aureon/vault/voice/meta_cognition_observer.py
aureon/queen/queen_sentience_integration.py
aureon/queen/queen_metacognition.py
aureon/queen/queen_authentic_voice.py
aureon/queen/queen_inhouse_ai_bridge.py
```

## Cloud Limitation

Cloudflare Workers cannot call `127.0.0.1` on the user's PC. For public cloud use, Gary's Aureon bridge must be hosted at a reachable HTTPS URL, then configured as:

```bash
AUREON_API_BASE_URL=https://gary-aureon-bridge.example
AUREON_CHAT_PATH=/api/message
```
