# Keys to rotate before merge

Public `main` still contains live credentials. This file names every one that a full-history scan found: provider, type, file, and commit. It does not contain values, email addresses, or token bodies.

Rotate every row at the provider before merging. This pull request does not rewrite history and does not force-push. Rewriting history is Gary's decision.

## How the history was scanned

Two gitleaks 8.28.0 runs, both with `--redact`:

- `gitleaks detect --source . --redact` walked commits reachable from HEAD. It reported 2719 commits scanned, about 1.35 GB, and 277 leaks.
- `gitleaks detect --source . --redact --log-opts=--all` reported the same 277 leaks. The finding set was identical.

`git rev-list --all` counts 3394 commits. Gitleaks reported 2719. The named commits `beed16ecdf66`, `4b772995bdca`, and `d4f1fe121911` are in the leak set and are ancestors of `origin/main`.

Gitleaks records the commit that introduced a secret in a diff. A later commit that still contains the same `.env` line is not a new leak. A separate walk opened `.env` and `.env1.txt` at every commit that contains those paths and grouped identical values. That walk is the commit list in the environment tables below. Twenty-four of those commits are ancestors of `origin/main` (`dcf1d1dd`). Two commits are in this public repository but are not ancestors of `origin/main`:

- `7caba2103a72` is on `origin/edit/edt-53830782-0ccb-4b2c-b81e-6dff91440566`.
- `ddad512e3916` repeats the Quackers Binance pairs and is on several `origin/edit/*` branches, not on `origin/main`.

The current tree no longer contains `.env` or `.env1.txt`. Hardcoded copies that remain in the tree were replaced with the literal placeholder `REDACTED` before this branch. The live values are still reachable in history.

## Environment credentials

Every row below was a non-placeholder assignment in `.env` or `.env1.txt`. A generation is one distinct value. Rotate every generation, including ones that were later replaced.

### Alpaca

Three API key generations and three matching secret generations. Token lengths 26 and 44.

| Generation | Type | Name | File | Commits |
| --- | --- | --- | --- | --- |
| 1 | api_key | `ALPACA_API_KEY` | `.env`, `.env1.txt` | `.env1.txt`: `0078a66b33dd`, `2a137922cd4c`, `4b772995bdca`, `68af627c999d`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `d4f1fe121911`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`. `.env`: `2a137922cd4c`, `4b772995bdca`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07` |
| 2 | api_key | `ALPACA_API_KEY` | `.env` | `496d05fb0601`, `7c5c80f0f88e`, `a5f646c857a9` |
| 3 | api_key | `ALPACA_API_KEY` | `.env` | `518ce8ec0b92`, `5770ef5ddca0` |
| 1 | api_secret | `ALPACA_SECRET_KEY` | `.env`, `.env1.txt` | same commits as Alpaca key generation 1 |
| 2 | api_secret | `ALPACA_SECRET_KEY` | `.env` | `496d05fb0601`, `7c5c80f0f88e`, `a5f646c857a9` |
| 3 | api_secret | `ALPACA_SECRET_KEY` | `.env` | `518ce8ec0b92`, `5770ef5ddca0` |

### Binance

Two key generations in the env files. Generation 1's secret is `BINANCE_API_SECRET`. Generation 2 does not use that name: its secret is `BINANCE_SECRET`, and it is not the same value as generation 1. Both are 64-character tokens.

| Generation | Type | Name | File | Commits |
| --- | --- | --- | --- | --- |
| 1 | api_key | `BINANCE_API_KEY` | `.env`, `.env1.txt` | `.env1.txt`: `0078a66b33dd`, `2a137922cd4c`, `4b772995bdca`, `68af627c999d`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `d4f1fe121911`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`. `.env`: `2a137922cd4c`, `44e4e79456bf`, `496d05fb0601`, `4b772995bdca`, `518ce8ec0b92`, `5770ef5ddca0`, `5f95f0a8a459`, `7c5c80f0f88e`, `8f1d72563825`, `a4cd64757ec5`, `a5a88685713b`, `a5f646c857a9`, `b6b5b7213f37`, `beed16ecdf66`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07` |
| 1 | api_secret | `BINANCE_API_SECRET` | `.env`, `.env1.txt` | same commits as Binance key generation 1 |
| 2 | api_key | `BINANCE_API_KEY` | `.env` | `38a779f17a38`, `921b68e42e11` on `origin/main`; `7caba2103a72` is not on `origin/main` |
| 2 | api_secret | `BINANCE_SECRET` | `.env` | `38a779f17a38`, `921b68e42e11` on `origin/main`; `7caba2103a72` is not on `origin/main` |

Five further distinct key/secret pairs were hardcoded at `5f95f0a8a459` (on `origin/main`). One of the five is Binance generation 1 above. The other four appear only in the shell scripts.

| Type | Name | File | Commit |
| --- | --- | --- | --- |
| api_key, api_secret | `BINANCE_API_KEY`, `BINANCE_API_SECRET` (five pairs) | `run_multi_bot.sh`, `run_specialized_army.sh` | `5f95f0a8a459` |
| api_key, api_secret | `BINANCE_API_KEY`, `BINANCE_API_SECRET` (two of those five pairs) | `run_safe_2bots.sh` | `5f95f0a8a459` |
| api_key, api_secret | `WORKING_KEY`, `WORKING_SECRET` (generation 1) | `aureon_infinite.py` | `5f95f0a8a459` |
| api_key, api_secret | `API_KEY`, `API_SECRET` (generation 1) | `aureon_live_trader.py`, `aureon_omega_btc.py`, `aureon_omega_live.py`, `aureon_piano.py`, `aureon_multiverse.py` | `5f95f0a8a459` |
| api_key, api_secret | same generation-1 pair | `aureon/trading/aureon_infinite.py`, `aureon/trading/aureon_piano.py`, `aureon/trading/aureon_omega_btc.py`, `aureon/trading/aureon_live_trader.py`, `aureon/trading/aureon_omega_live.py`, `aureon/simulation/aureon_multiverse.py` | `4ea3e68a23b9`, `18fe19d78a75` |
| api_key, api_secret | same generation-1 pair | `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_infinite.py`, `aureon_piano.py`, `aureon_omega_btc.py`, `aureon_live_trader.py`, `aureon_omega_live.py`, and `aureon/simulation/aureon_multiverse.py` under that snapshot | `6c8f225bb7d6`, `b9c2c9da4da1` |

Two more distinct pairs, neither equal to generation 1 or generation 2, are in the Quackers docs. Shorter example lines in those files (lengths 22 and 25) are placeholders and are not listed here.

| Type | Name | File | Commit |
| --- | --- | --- | --- |
| api_key, api_secret | `BINANCE_API_KEY`, `BINANCE_API_SECRET` | `Aueron-Trading-Quantum-Quackers-War-Ready-Version--alert-autofix-gl1/LIVE_DEPLOYMENT_STATUS.md`, `Aueron-Trading-Quantum-Quackers-War-Ready-Version--alert-autofix-gl1/docs/LIVE_MONEY_GUIDE.md` | `60e006d9d796` on `origin/main`. Repeated at `ddad512e3916`, which is not on `origin/main` |
| api_key, api_secret | `BINANCE_API_KEY`, `BINANCE_API_SECRET` | `Aueron-Trading-Quantum-Quackers-War-Ready-Version--alert-autofix-gl1/docs/SYSTEM_STATUS.md` | `60e006d9d796` on `origin/main`. Repeated at `ddad512e3916`, which is not on `origin/main` |

### Capital.com

The account identifier is an email address. The address is not written here. `CAPITAL_EMAIL` at `38a779f17a38` is that same identifier.

| Generation | Type | Name | File | Commits |
| --- | --- | --- | --- | --- |
| 1 | api_key | `CAPITAL_API_KEY` | `.env`, `.env1.txt` | `.env1.txt`: `0078a66b33dd`, `2a137922cd4c`, `4b772995bdca`, `68af627c999d`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `d4f1fe121911`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`. `.env`: `2a137922cd4c`, `496d05fb0601`, `4b772995bdca`, `518ce8ec0b92`, `5770ef5ddca0`, `7c5c80f0f88e`, `8f1d72563825`, `a5a88685713b`, `a5f646c857a9`, `b6b5b7213f37`, `beed16ecdf66`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07` |
| 2 | api_key | `CAPITAL_API_KEY` | `.env` | `38a779f17a38`, `921b68e42e11` on `origin/main`; `7caba2103a72` is not on `origin/main` |
| 1 | password | `CAPITAL_PASSWORD` | `.env`, `.env1.txt` | same commits as Capital key generation 1 |
| 2 | password | `CAPITAL_PASSWORD` | `.env` | `38a779f17a38`, `921b68e42e11` on `origin/main`; `7caba2103a72` is not on `origin/main` |
| 1 | account identifier | `CAPITAL_IDENTIFIER` | `.env`, `.env1.txt` | same commits as Capital key generation 1 |
| 1 | account identifier | `CAPITAL_EMAIL` | `.env` | `38a779f17a38` |

### CoinAPI

One key. Token length 36.

| Type | Name | File | Commits |
| --- | --- | --- | --- |
| api_key | `COINAPI_KEY` | `.env`, `.env1.txt` | `.env1.txt`: `0078a66b33dd`, `2a137922cd4c`, `4b772995bdca`, `68af627c999d`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `d4f1fe121911`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`. `.env`: `2a137922cd4c`, `4b772995bdca`, `7c5c80f0f88e`, `8f1d72563825`, `a5a88685713b`, `a5f646c857a9`, `b6b5b7213f37`, `beed16ecdf66`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07` |

### Kraken

Four API key generations and four matching secret generations. `4b772995bdca` ("Update Kraken API keys to new credentials") is generation 4, not a deletion. Lengths 56 and 88. Gitleaks rule `kraken-access-token` fired on `.env` and `.env1.txt`.

| Generation | Type | Name | File | Commits |
| --- | --- | --- | --- | --- |
| 1 | api_key | `KRAKEN_API_KEY` | `.env`, `.env1.txt` | `.env1.txt`: `0078a66b33dd`, `2a137922cd4c`, `4b772995bdca`, `68af627c999d`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`. `.env`: `2a137922cd4c`, `496d05fb0601`, `7c5c80f0f88e`, `8f1d72563825`, `a5f646c857a9`, `beed16ecdf66`, `e1468b4b1818`, `f82d07b77d07` |
| 2 | api_key | `KRAKEN_API_KEY` | `.env1.txt` | `d4f1fe121911` |
| 3 | api_key | `KRAKEN_API_KEY` | `.env` | `44e4e79456bf`, `518ce8ec0b92`, `5770ef5ddca0`, `5f95f0a8a459` |
| 4 | api_key | `KRAKEN_API_KEY` | `.env` | `4b772995bdca`, `a5a88685713b`, `b6b5b7213f37`, `ddca19b0c98c` |
| 1 | api_secret | `KRAKEN_API_SECRET` | `.env`, `.env1.txt` | same commits as Kraken key generation 1 |
| 2 | api_secret | `KRAKEN_API_SECRET` | `.env1.txt` | `d4f1fe121911` |
| 3 | api_secret | `KRAKEN_API_SECRET` | `.env` | `44e4e79456bf`, `518ce8ec0b92`, `5770ef5ddca0`, `5f95f0a8a459` |
| 4 | api_secret | `KRAKEN_API_SECRET` | `.env` | `4b772995bdca`, `a5a88685713b`, `b6b5b7213f37`, `ddca19b0c98c` |

### Agent

All on `origin/main`, `.env` only.

| Type | Name | Commits |
| --- | --- | --- |
| api_key | `AUREON_AGENT_KEY` | `2a137922cd4c`, `4b772995bdca`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `ddca19b0c98c`, `e1468b4b1818` |
| identifier | `AUREON_AGENT_ID` | same commits |
| endpoint | `AUREON_AGENT_ENDPOINT` | same commits |
| identifier | `AUREON_CHATBOT_ID` | same commits |

### Supabase

One publishable JWT, role `anon`, not `service_role`. The same JWT is hardcoded in three source files. The project URL and project id are identifiers for that project, not a second key.

| Type | Name | File | Commits |
| --- | --- | --- | --- |
| publishable JWT, role anon | `VITE_SUPABASE_PUBLISHABLE_KEY` | `.env`, `.env1.txt` | `.env1.txt`: `0078a66b33dd`, `2a137922cd4c`, `4b772995bdca`, `68af627c999d`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `d4f1fe121911`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`. `.env`: `2a137922cd4c`, `34e3d8ec291e`, `38a779f17a38`, `44e4e79456bf`, `496d05fb0601`, `4b772995bdca`, `5770ef5ddca0`, `7c5c80f0f88e`, `8f1d72563825`, `a4cd64757ec5`, `a5a88685713b`, `a5f646c857a9`, `afa9cf75cfc9`, `b6b5b7213f37`, `beed16ecdf66`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`, plus `7caba2103a72` and `921b68e42e11` |
| publishable JWT, role anon | client fallback | `src/integrations/supabase/client.ts` | `054b948547f3` |
| publishable JWT, role anon | client fallback | `src/lib/supabase.ts` | `bacbf950741f`, and the same file at `60e006d9d796` (repeated at `ddad512e3916`, not on `origin/main`) |
| publishable JWT, role anon | client fallback | `src/core/smokeTestPhaseValidator.ts` | `5dd587c6dacd` |
| publishable JWT, role anon | client fallback, removed from the tree on this branch | `frontend/src/integrations/supabase/client.ts`, `frontend/src/core/smokeTestPhaseValidator.ts` | the same JWT as the rows above; the fallback in the current tree is now empty |
| endpoint | `VITE_SUPABASE_URL` | `.env`, `.env1.txt` | same commits as the env JWT |
| identifier | `VITE_SUPABASE_PROJECT_ID` | `.env`, `.env1.txt` | same commits as the env JWT |

### Mining worker

One worker name (letters, digits, and a single dot). It is an account identifier, not an API secret.

| Type | Name | File | Commits |
| --- | --- | --- | --- |
| mining worker identifier | `MINING_WORKER` | `.env`, `.env1.txt` | `.env1.txt`: `0078a66b33dd`, `2a137922cd4c`, `4b772995bdca`, `68af627c999d`, `8f1d72563825`, `a5a88685713b`, `b6b5b7213f37`, `beed16ecdf66`, `d4f1fe121911`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07`. `.env`: `2a137922cd4c`, `4b772995bdca`, `8f1d72563825`, `a5a88685713b`, `a5f646c857a9`, `b6b5b7213f37`, `beed16ecdf66`, `ddca19b0c98c`, `e1468b4b1818`, `f82d07b77d07` |

## Hardcoded credentials outside the env files

### World News API key

One hex key, length 32, default for `WORLD_NEWS_API_KEY`. On `origin/main`.

| File | Commits |
| --- | --- |
| `aureon_news_feed.py` | `d65ce831db8c` |
| `aureon_unified_ecosystem.py` | `81b40cd0d1e5`, `d65ce831db8c` |
| `aureon/data_feeds/aureon_news_feed.py` | `4ea3e68a23b9`, `18fe19d78a75` |
| `aureon/trading/aureon_unified_ecosystem.py` | `19ff07559c56`, `cdb8af76f357`, `9418a91053ce`, `721f124d3d2f`, `4ea3e68a23b9`, `18fe19d78a75` |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/data_feeds/aureon_news_feed.py` | `6c8f225bb7d6`, `b9c2c9da4da1` |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_unified_ecosystem.py` | `6c8f225bb7d6`, `b9c2c9da4da1` |

### Broadcast pre-shared key

One token, length 33. Commit `aaf20132c028` is on `origin/main`. The same value is the `PSK` assignment, and it also appears inside `ultimate_daemon_lineage.py`.

| File | Commit |
| --- | --- |
| `daemon_codes/openclaw_daemons/autonomous_liberation_engine.py` | `aaf20132c028` |
| `daemon_codes/openclaw_daemons/coherence_broadcast.py` | `aaf20132c028` |
| `daemon_codes/openclaw_daemons/planetary_broadcast_encoder.py` | `aaf20132c028` |
| `daemon_codes/openclaw_daemons/schumann_broadcast_injection.py` | `aaf20132c028` |
| `daemon_codes/openclaw_daemons/sero_master_orchestrator.py` | `aaf20132c028` |
| `daemon_codes/openclaw_daemons/ultimate_daemon_lineage.py` | `aaf20132c028` |

`aureon_radar/aureon_phi_radar.py` and `aureon_radar/_radar_recovery.py` contain the literal placeholder `REDACTED` in the only commit that added them. They are not a second live value.

## Reviewed, not a live credential

Gitleaks also reported these. They were inspected and left in place:

- `AUREON_AURIS_MAX_PER_MIN` is a one-digit rate in `.env`, except `e1468b4b1818`, where the value is a 28-character config string. It is not a provider key.
- Python type annotations named `private_key` in `aureon/plumber/crypto.py`, `packet.py`, `quorum.py`, `receipts.py` at `5b207dde3d24`, and the plumber tests beside them.
- Placeholder `BINANCE_API_KEY` / `BINANCE_API_SECRET` examples in `QUICKSTART_DIGITALOCEAN.md` (`bd4b00461518`), the Kimi copy of that quickstart (`6c8f225bb7d6`, `b9c2c9da4da1`), and the grant-folder copies (`b4bfe6375679`).
- `idempotency_key` fields and similar ids in the grant-folder JSON and CSV at `b4bfe6375679`.
- Test fixtures and synthetic tokens: `tests/approval/test_reply.py`, `tests/fixtures/hnc_legacy_v1_known_answers.json`, `tests/test_action_authority.py`, `tests/test_credential_bootstrap.py`, `tests/test_hnc_scorm_coherence.py`, `tests/test_kraken_economic_transport_guard.py`, `tests/test_operator_connections.py`, `tests/test_operator_providers_keys.py`, `tests/test_operator_tenant_security.py`, `tests/cloudflare_workers_deploy_preflight_contract.test.mjs`.
- Dummy Kraken probe material in `aureon_radar/_kraken_adapter_probe.py` (`1f1f54f545c5`).
- Resonance identifiers in `sources/NEXUS-LIVE-FEED-/` (`1f1f54f545c5`).
- UI and website build identifiers: `src/components/warroom/HarmonicWaveform6DStatus.tsx` (`cbf3826ba3f1`), `tools/aureon_website_design_audit_v27.js`, `tools/refresh_website_shell_v27.js` (`af9aace9cd8b`).
- A census string in `scripts/validation/audit_economic_mutation_boundaries.py` (`f5fb1916c07a`).

The loopback bearer `local-selfhost-token` and the compose Postgres password `local_only` are local throwaways. They are not in this inventory.

## Guards added on this branch

History was not rewritten.

- `.gitignore` ignores `.env*`, and keeps `.env.example` and `.env.sample` committable.
- `.pre-commit-config.yaml` runs gitleaks 8.28.0 on staged content (`pre-commit install`).
- `.github/workflows/gitleaks.yml` scans the tree being merged with `gitleaks detect --no-git --redact --config .gitleaks.toml`. `.gitleaks.toml` allowlists only the reviewed non-credentials in the section above. It does not allowlist these keys. A full-history job cannot go green while these commits are still reachable. That job does not rewrite history.
