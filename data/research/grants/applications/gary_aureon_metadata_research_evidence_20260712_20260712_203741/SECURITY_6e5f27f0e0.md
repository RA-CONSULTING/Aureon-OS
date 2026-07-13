# Security Model

## Explicit non-goals

This project does not implement:
- hidden persistence
- malware-like behavior
- privilege escalation bypasses
- hidden backdoors
- silent root execution

## Host execution rules

Host terminal commands are guarded by runtime safety checks:
- destructive root-level commands are blocked
- `sudo` and `su` are copy-only
- package and repository mutations require approval

## Browser boundary

The browser is only:
- UI
- renderer
- approval surface
- WebSocket client

The browser is not a root shell.

## Local runtime boundary

The companion runtime:
- binds to `127.0.0.1` by default
- only allows local requests by default
- only accepts remote origins when explicitly configured

## Sandbox execution

Docker sandbox mode:
- runs isolated per session
- mounts session workspace only
- applies CPU/RAM limits
- avoids direct host root exposure
