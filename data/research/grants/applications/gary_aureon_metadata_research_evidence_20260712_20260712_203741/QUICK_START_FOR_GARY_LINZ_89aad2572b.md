# flAmeBornLLC / LLM Academy - Clean Share Build

This package is a clean handoff build (no private API keys, no local user history/settings).

## 1) Install

```bash
cd flAmeBornLLC-LLM-Academy
npm install
npm --prefix desktop install
```

## 2) Configure keys (optional but recommended)

Create local `.env` in project root:

```bash
OPENROUTER_API_KEY=YOUR_KEY
OPENAI_API_KEY=YOUR_KEY
GEMINI_API_KEY=YOUR_KEY
GOOGLE_API_KEY=YOUR_KEY
HF_TOKEN=YOUR_KEY
XAI_API_KEY=YOUR_KEY
AUREON_API_KEY=
```

Notes:
- OpenRouter key works with free models (Gemma and other `:free` models listed in app).
- Keep `.env` private and never commit it.

## 3) Run desktop app

```bash
npm run desktop:start
```

## 4) Runtime + sandbox checks

```bash
curl -s http://127.0.0.1:7331/health
curl -s http://127.0.0.1:7331/api/sandbox/status
```

If Docker access fails in shell:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

## 5) Aureon note

Aureon bridge may be intermittent depending on local bridge process state.
Use app status cards and `/api/aureon/status` for quick verification.
