# Security Policy

The full security policy lives at [`docs/SECURITY.md`](docs/SECURITY.md).

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue for a
vulnerability. Use GitHub's private [Security Advisories](https://github.com/RA-CONSULTING/aureon-trading/security/advisories/new)
for this repository, or contact R&A Consulting and Brokerage Services Ltd via
[aureonzorzatechnologies.pl](https://aureonzorzatechnologies.pl).

## Secrets

Never commit credentials. This repository uses `.env` files (gitignored) and,
in production, environment variables / a secrets manager. If you believe a
secret was ever committed, treat it as compromised and rotate it immediately.

`.env.example` uses placeholder names only. Secret lines there are blank, or
an obvious placeholder name in a vendored template. A real key value never
goes in that file. A fresh blank-key copy ships `AUREON_DISABLE_REAL_ORDERS`
and `AUREON_DRY_RUN`. Those flags are not a lock: a full+keyed master boot
overrides them. Exchange keys in `.env` make that boot live. A complete key
group in the inherited shell or in `aureon_radar/.env` does the same when the
root `.env` is blank. See [`docs/PUBLIC_ENV.md`](docs/PUBLIC_ENV.md).
