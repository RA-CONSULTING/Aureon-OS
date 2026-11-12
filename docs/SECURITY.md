# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Main    | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability, please do NOT open a public issue.

Instead, please report it privately:
1. Use GitHub's private [Security Advisories](https://github.com/RA-CONSULTING/Aureon-OS/security/advisories/new) for this repository.
2. Or email [gary@aureonzorzatechnologies.com](mailto:gary@aureonzorzatechnologies.com).

We will acknowledge your report within 48 hours and provide an estimated timeline for a fix.

## API Keys and Secrets

- **NEVER** commit API keys, secrets, or credentials to the repository.
- Use `.env` files (which are git-ignored) for local development.
- `.env.example` uses placeholder names only. A real key value never goes in that file. The copied disable and dry-run flags are not a lock: a full+keyed master boot overrides them. Exchange keys in `.env` make that boot live. A complete key group in the inherited shell or in `aureon_radar/.env` does the same when the root `.env` is blank. See [`PUBLIC_ENV.md`](PUBLIC_ENV.md).
- If you accidentally commit a key, revoke it immediately.

## Model-written benchmark code

`aureon.autonomous.self_coder_benchmark` runs model-written Python. That
child is not a kernel sandbox. It starts only inside `unshare` (a new user,
pid, and net namespace) from an environment that never held the keys. Inside
that namespace, home and the workspace are covered with a tmpfs when that
mount works. The opt-in path does not mount over the parent namespace. If
`unshare` is missing, the probe fails, or a remembered `unshare` later
disappears, the harness does not claim a namespace and does not run the
model code unless `AUREON_BENCH_ALLOW_UNSANDBOXED=1`. That opt-in is
unsandboxed: a same-user child can read `/proc/PID/environ` and can open a
raw socket. A failed probe is not cached. Run this harness only on a
machine with no secrets.

## Trading Risks

This software executes financial transactions.
- Always use **Testnet** or **Dry-Run** modes first.
- Set strict risk limits (e.g., `BINANCE_RISK_MAX_ORDER_USDT`).
- We are not responsible for financial losses due to software bugs or misconfiguration.
