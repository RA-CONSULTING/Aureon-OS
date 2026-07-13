# Local Runtime Setup

## Start

```bash
cd /home/l/CodexPROsSparrow
npm run runtime:start
```

Default bind:
- `127.0.0.1:7331`

## Verify

```bash
curl -s http://127.0.0.1:7331/health
curl -s http://127.0.0.1:7331/api/runtime/info
curl -s http://127.0.0.1:7331/api/terminal/status
```

## Trusted origin configuration

For a deployed web app later:

```bash
export FLAMEBORN_RUNTIME_TRUSTED_ORIGINS="https://your-cloudflare-app.example"
npm run runtime:start
```

## Notes

- The current frontend defaults to runtime origin `http://127.0.0.1:7331`
- This can be overridden later without changing the core safety model
