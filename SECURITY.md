# Security Policy

The full security policy lives at [`docs/SECURITY.md`](docs/SECURITY.md).

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue for a
vulnerability. Use GitHub's private [Security Advisories](https://github.com/RA-CONSULTING/aureon-os/security/advisories/new)
for this repository, or contact R&A Consulting and Brokerage Services Ltd via
[aureonzorzatechnologies.pl](https://aureonzorzatechnologies.pl).

## Secrets

Never commit credentials. This repository uses `.env` files (gitignored) and,
in production, environment variables / a secrets manager. If you believe a
secret was ever committed, treat it as compromised and rotate it immediately.
