# SWOT Analysis: Setup Wizard, Launcher, and Dashboard System

## Strengths
- **Secure defaults with optional dev mode**: Configuration is encrypted with Fernet by default while still providing a plaintext dev override, balancing safety and flexibility for local testing.【F:cli/config_manager.py†L9-L78】
- **Guided onboarding and validation**: The setup wizard walks users through exchange selection, credential entry, and performs a lightweight connectivity probe before saving settings, reducing misconfiguration risk.【F:cli/setup_wizard.py†L14-L78】
- **Unified control surface**: A single launcher ensures config creation, can register OS auto-start hints, spins up the trading loop, and opens the dashboard for monitoring.【F:cli/launcher.py†L14-L116】
- **Observable runtime with local UI**: The dashboard exposes start/stop controls plus real-time P&L, positions, and logs via both HTML and JSON status endpoints, improving transparency for local runs.【F:cli/dashboard.py†L5-L74】

## Weaknesses
- **Mocked trading logic**: The runtime uses randomized price jitter and synthetic positions, so it does not reflect live exchange behavior or risk controls yet.【F:cli/trading_runtime.py†L11-L55】
- **Limited credential verification**: Connectivity checks only hit public endpoints; API key/secret validity isn’t truly confirmed, leaving room for runtime failures later.【F:cli/setup_wizard.py†L36-L47】
- **Basic persistence**: Config and key files live beside the codebase without rotation or backup guidance, which may not meet stricter operational standards.【F:cli/config_manager.py†L9-L78】

## Opportunities
- **Pluggable exchange adapters**: Replace the mock runtime with modular clients per exchange, enabling real trade placement and richer telemetry surfaced in the dashboard.【F:cli/trading_runtime.py†L11-L55】【F:cli/dashboard.py†L5-L74】
- **Stronger security posture**: Introduce hardware-backed key storage or OS keychain integration and allow per-environment config segregation to harden secrets handling.【F:cli/config_manager.py†L9-L78】
- **Operational automation**: Extend auto-start to create first-class services (systemd/launchd) and add health checks or alerting endpoints for supervised deployments.【F:cli/launcher.py†L71-L116】
- **User experience enhancements**: Expand the wizard with validation of trading pairs, rate-limit warnings, and clearer defaults, while enhancing the dashboard with charts and historical P&L.【F:cli/setup_wizard.py†L14-L92】【F:cli/dashboard.py†L5-L74】

## Threats
- **User error and misconfiguration**: Without strict validation or safe defaults (e.g., minimum balance checks), users could enable live mode with incorrect sizing or credentials, leading to failed or unintended trades.【F:cli/setup_wizard.py†L49-L78】【F:cli/trading_runtime.py†L11-L55】
- **Local attack surface**: Storing keys locally and opening a dashboard server, even on localhost, could be exploited on compromised machines or when ports are exposed inadvertently.【F:cli/config_manager.py†L9-L78】【F:cli/dashboard.py†L5-L74】
- **Packaging drift**: The PyInstaller flow may omit new dependencies or platform-specific hardening (e.g., code signing), risking broken or untrusted distributables over time.【F:packaging/pyinstaller_build.md†L1-L34】【F:packaging/post_build_smoke_test.py†L1-L33】
