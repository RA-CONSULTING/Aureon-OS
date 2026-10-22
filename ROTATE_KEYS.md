# Keys to rotate before merge

A secrets scan of this snapshot found live credentials. They were removed from the tree. This file records the file and the type only. It does not contain the values.

Some of these values were already on the public `main` branch, so they are still in that branch's history. This pull request deletes them from the files going forward. It does not rewrite history, and it does not merge itself. Rotate the credentials at the provider before merging. Treat the copies that were already public as exposed.

## Must rotate

One exchange API key and one exchange API secret (the same pair) were hardcoded in these files. Both are base64 strings, 64 characters. They were already on public `main`, including the vendored Kimi snapshot.

| File | Type |
| --- | --- |
| `aureon/trading/aureon_infinite.py` | exchange_api_key, exchange_api_secret |
| `aureon/trading/aureon_piano.py` | exchange_api_key, exchange_api_secret |
| `aureon/trading/aureon_omega_btc.py` | exchange_api_key, exchange_api_secret |
| `aureon/trading/aureon_live_trader.py` | exchange_api_key, exchange_api_secret |
| `aureon/trading/aureon_omega_live.py` | exchange_api_key, exchange_api_secret |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_infinite.py` | exchange_api_key, exchange_api_secret |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_piano.py` | exchange_api_key, exchange_api_secret |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_omega_btc.py` | exchange_api_key, exchange_api_secret |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_live_trader.py` | exchange_api_key, exchange_api_secret |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_omega_live.py` | exchange_api_key, exchange_api_secret |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/simulation/aureon_multiverse.py` | exchange_api_key, exchange_api_secret |

One World News API key (hex, 32 characters) was a hardcoded default. It was already on public `main`.

| File | Type |
| --- | --- |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/data_feeds/aureon_news_feed.py` | world_news_api_key |
| `imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon/trading/aureon_unified_ecosystem.py` | world_news_api_key |

One broadcast pre-shared key (token, 33 characters) was hardcoded. The `daemon_codes` copies were already on public `main`. The `aureon_radar` copies are the same value, added with this snapshot.

| File | Type |
| --- | --- |
| `aureon_radar/_radar_recovery.py` | pre_shared_key |
| `aureon_radar/aureon_phi_radar.py` | pre_shared_key |
| `daemon_codes/openclaw_daemons/autonomous_liberation_engine.py` | pre_shared_key |
| `daemon_codes/openclaw_daemons/coherence_broadcast.py` | pre_shared_key |
| `daemon_codes/openclaw_daemons/planetary_broadcast_encoder.py` | pre_shared_key |
| `daemon_codes/openclaw_daemons/schumann_broadcast_injection.py` | pre_shared_key |
| `daemon_codes/openclaw_daemons/sero_master_orchestrator.py` | pre_shared_key |
| `daemon_codes/openclaw_daemons/ultimate_daemon_lineage.py` | pre_shared_key |

Provider-side rotations before merge: the exchange key, the exchange secret, the World News API key, and the broadcast pre-shared key.

## Reviewed and left in place

Gitleaks reported other hits. Inspection showed they are not credentials, so they were not removed and do not need rotation:

- Python type annotations named `private_key` or `key` (Ed25519 types in the plumber).
- `idempotency_key` fields in grant-evidence JSON.
- Placeholder `BINANCE_API_KEY` / `BINANCE_API_SECRET` examples in the DigitalOcean quickstarts.
- The Supabase client fallback in `frontend/src/integrations/supabase/client.ts` and `frontend/src/core/smokeTestPhaseValidator.ts`. The JWT role is `anon` (the public client key), not `service_role`.
- Test fixtures: approval tokens shaped like `token_urlsafe`, synthetic PEM blocks, HNC known-answer vectors, dummy Kraken probe keys, and worker-secret test environment values.
- UI field names and website `releaseKey` build identifiers.
- Resonance identifiers in `sources/NEXUS-LIVE-FEED-/` (canonical labels for that feed, not wallet keys).

No `.env` file was added. The tree only has `.env.example` and `.env.sample`. No wallet private key and no non-fixture private-key block was found. Live trading stays off. The self-repair denylist is intact.

Scan: `gitleaks detect --no-git` over the snapshot, plus a manual search for key assignments, token prefixes, `.env` files, wallet keys, and private-key blocks.
