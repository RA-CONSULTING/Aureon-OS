# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Main    | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability, please do NOT open a public issue.

Instead, please report it responsibly:
1. Email the maintainers (if a contact is listed in the repo profile).
2. Or use GitHub's "Report a vulnerability" feature if enabled.

We will acknowledge your report within 48 hours and provide an estimated timeline for a fix.

## API Keys and Secrets

- **NEVER** commit API keys, secrets, or credentials to the repository.
- Use `.env` files (which are git-ignored) for local development.
- If you accidentally commit a key, revoke it immediately.

## Model-written benchmark code

`aureon.autonomous.self_coder_benchmark` runs model-written Python. That
child is not a kernel sandbox. On Linux it is started with `unshare` in a
new user, pid, and net namespace, from an environment that never held the
keys, when that command works. The host filesystem is still visible to the
same user. Without `unshare`, the child only gets a scrubbed environment
and a Python socket stub. That stub can be bypassed, and a same-user child
can read `/proc/<pid>/environ`. Run this harness only on a machine with no
secrets.

## Trading Risks

This software executes financial transactions.
- Always use **Testnet** or **Dry-Run** modes first.
- Set strict risk limits (e.g., `BINANCE_RISK_MAX_ORDER_USDT`).
- We are not responsible for financial losses due to software bugs or misconfiguration.
