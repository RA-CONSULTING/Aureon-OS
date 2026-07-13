# Flameborn Full Capability Stress Audit

- Status: `flameborn_full_capability_attention`
- Generated: `2026-05-21T08:33:43.432553+00:00`
- Required rows passed: `9/14`
- Blockers: `4`
- Attention: `2`
- No trading gate bypass: `False`

## Status Rows
- `web_health`: pass - health_passed
- `runtime_health`: blocker - runtime_unavailable
- `desktop_ready`: pass - desktop_ready
- `supervisor_connected`: pass - supervisor_connected
- `phi_status`: pass - phi_connected
- `phi_chat_response`: attention - chat_unavailable
- `terminal_guard`: pass - terminal_guard_passed
- `sandbox_guard`: pass - sandbox_guard_passed
- `websocket_origin_guard`: pass - websocket_origin_guard_passed
- `provider_api_boundary`: pass - provider_api_guarded_off
- `cloudflare_boundary`: pass - cloudflare_guarded_off
- `npm_audit_state`: blocker - npm_audit_attention
- `live_trade_gate_visibility`: blocker - live_trade_gate_visibility_missing
- `no_trading_gate_bypass`: blocker - trading_gate_bypass_risk
- `thoughtbus_mycelium_visibility`: attention - organism_receipt_attention

## Blockers
- `runtime_health_unavailable`
- `npm_audit_high_critical_or_missing`
- `live_trade_gate_visibility_missing`
- `trading_gate_bypass_risk`

## Boundaries
- full capability stress audit observes local services only
- no service start or restart is performed by the audit
- no terminal or sandbox command execution
- no credential read, migration, or reveal
- no Cloudflare deploy
- no order, close, cancel, credential, or broker mutation
- live trading gates are reported, not changed
