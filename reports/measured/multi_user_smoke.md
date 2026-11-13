# Contained multi-user smoke — stage 9

This boots the tenant boundary that already lives in `aureon.operator` inside the stage-7 contained launcher. It is not a supported public runtime, not a listener, and not a go-live receipt.

Verdict: **pass**.
Release boundary: **HOLD**. Orange badge: unchanged. `go_live_clear`: False.
Public pin: `ac9fa3151b63bd4143dc1aa434ec79b382406b7e` (changed by this stage: False). Containment module pin: `bb04503119681adcf832f3c3e9b0cbf09fc7a938` (same as public pin: False).
Live trading: false. Orders placed: false. Market data fetched: false. Listener bound: false.

## Cold boot

```bash
python -m aureon.containment.multi_user_smoke
```

Command included `unshare --net`: **True** (measured).
Parent net namespace `net:[4026532600]`, child `net:[4026532951]` (measured).
Contained TCP 1.1.1.1:443 ok=False errno=101 error=ENETUNREACH bytes_read=0 (measured).
Boot entry: `create_app` with the local test ingress seam. `operator_server.main` was not called. `production_ready` on that seam is false.

## Tenant boundary

Per-user encrypted stores: tenant A 100 bytes, tenant B 268 bytes. Plaintext key in the store file: False (measured). Cross-tenant key visible: False (measured). Tenant key in `os.environ`: False (measured).
Request-scoped engines: keyed A `tenant_no_key`=None, keyless B `tenant_no_key`=True, keyed B `tenant_no_key`=None, A after revoke `tenant_no_key`=True, B after A's revoke `tenant_no_key`=None (measured).
Default-deny sample: [{"method": "GET", "mounted": true, "path": "/api/pulse", "secret_in_body": false, "status": 403}, {"method": "GET", "mounted": true, "path": "/api/switchboard", "secret_in_body": false, "status": 403}, {"method": "GET", "mounted": true, "path": "/api/terminal-state", "secret_in_body": false, "status": 403}, {"method": "GET", "mounted": true, "path": "/api/env-credentials", "secret_in_body": false, "status": 403}, {"method": "GET", "mounted": true, "path": "/api/trades", "secret_in_body": false, "status": 403}, {"method": "GET", "mounted": true, "path": "/api/action/status", "secret_in_body": false, "status": 403}, {"method": "POST", "mounted": true, "path": "/api/billing/charge-fee", "secret_in_body": false, "status": 403}] (measured).
Admin `GET /api/pulse` status: 200 (measured). Tenant `GET /api/me` status: 200 (measured).

## Shared memory

No universal shared-memory-leak claim. Each surface below was read or is named as unread. A canary is found or absent only on a surface whose found map is present.

Thought-bus deque items scanned: 1. Control canary found: True. Other canaries: {"canary_operator": false, "canary_prompt_a": false, "canary_prompt_a_revoked": false, "canary_prompt_b": false, "canary_prompt_b_absent": false, "canary_prompt_b_still": false, "canary_signer": false, "canary_tenant_a": false, "canary_tenant_b": false}.
`thoughts.jsonl` bytes: 343. Truncated: False. Control canary found: True. Other canaries: {"canary_operator": false, "canary_prompt_a": false, "canary_prompt_a_revoked": false, "canary_prompt_b": false, "canary_prompt_b_absent": false, "canary_prompt_b_still": false, "canary_signer": false, "canary_tenant_a": false, "canary_tenant_b": false}.
`os.environ` names scanned: 17. Canaries found: {"canary_operator": true, "canary_prompt_a": false, "canary_prompt_a_revoked": false, "canary_prompt_b": false, "canary_prompt_b_absent": false, "canary_prompt_b_still": false, "canary_signer": true, "canary_tenant_a": false, "canary_tenant_b": false}. The signer and operator canaries are supposed to be in the child environment. They are a leak only if they show up on the bus, the JSONL file, or a new shared-memory segment.
New `/dev/shm` names: ['aureon_chirp_bus']. Bytes scanned: 4116. Pre-existing names: 0 (not read). Canaries in new segments: {"canary_operator": false, "canary_prompt_a": false, "canary_prompt_a_revoked": false, "canary_prompt_b": false, "canary_prompt_b_absent": false, "canary_prompt_b_still": false, "canary_signer": false, "canary_tenant_a": false, "canary_tenant_b": false}.
Thought-bus subscriber count before tenant calls: 1. After: 4. Before: [{"count": 1, "handlers": ["subscribe_membrane_topic.<locals>._on_membrane"], "topic": "bio.mcp_membrane.run"}]. After: [{"count": 1, "handlers": ["Connectome.Connectome._on_baton"], "topic": "baton.link"}, {"count": 1, "handlers": ["subscribe_membrane_topic.<locals>._on_membrane"], "topic": "bio.mcp_membrane.run"}, {"count": 0, "handlers": [], "topic": "symbolic.life.pulse"}, {"count": 1, "handlers": ["_on_predicted"], "topic": "whale.behavior.predicted"}, {"count": 1, "handlers": ["_on_shape"], "topic": "whale.shape.detected"}]. A count change is not, by itself, a prompt leak.
Not scored. The child handled the prompts, so those bytes exist in that process. That is not the shared thought bus.

## Still HOLD

- Receipt 2: exact target-source measurement and immutable release provenance — HOLD
- Receipt 3: durable HNC evidence with an external monotonic head anchor — HOLD
- Receipt 4: complete source-boundary census closure — HOLD
- Receipt 5: authenticated deployment receipt and provider-side read-back — HOLD

Started from `c68a89d2a184d99582bb24310b91e024323a212c`. Git HEAD at measurement: `9d254c9ed8b0b9fdd3b3d15e455f067a8189fc29`.
The child boots create_app with the local test ingress seam. operator_server.main is not called and no listener is bound. source_sha256 binds this stage's sources. git_head_at_measurement is HEAD when the command ran. The UTC stamps are this machine's clock, not receipt 3. go_live_clear stays false. aureon/operator/keystore.py is not listed in unchanged_sha256. This stage does not modify that file.
