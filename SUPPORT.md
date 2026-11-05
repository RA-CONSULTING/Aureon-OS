# Support

Aureon OS is public source under the [MIT License](LICENSE). The release boundary is **HOLD**. This page says where to ask, and what that ask does not include.

There is no service level. No response time, uptime target, or fix commitment is offered. A reply, if one comes, is voluntary.

## How to get help

- **Questions** about the public tree: [GitHub Discussions](https://github.com/RA-CONSULTING/Aureon-OS/discussions).
- **Defects** you can reproduce from this checkout: [GitHub Issues](https://github.com/RA-CONSULTING/Aureon-OS/issues). Use the bug report template. Name the command you ran and what you saw. Do not paste secrets, credentials, or private data.
- **Code changes**: [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **Vulnerabilities**: [`SECURITY.md`](SECURITY.md). Report them privately. Do not open a public issue or discussion.

Behaviour in those spaces follows [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## While the release boundary is HOLD

The orange release-boundary badge stays HOLD. A green test, a local boot, or a measured receipt does not lift it. Go-live status is [`docs/runbooks/GO_LIVE_HARDENING.md`](docs/runbooks/GO_LIVE_HARDENING.md). Deployment notes are under [`docs/deployment/`](docs/deployment/).

**Supported**

- Voluntary questions and reproducible defect reports about the current public source, through Discussions and Issues above.

**Not supported**

- A production, hosted, or go-live runtime. Official deploy routes stay at terminal HOLD. There is no supported public listener.
- Live trading, order handling, or exchange operations.
- Public MCP stages 3 and 4. They stay closed. See [`mcp/aureon_public/README.md`](mcp/aureon_public/README.md).
- Treating the local path in the [README](README.md) (`./install.sh`, the five-minute quickstart) as a supported release. That path is documentation for inspecting this checkout with exchange keys unset and live trading off. It is not a support contract.
- Older notes in `docs/`, `aureon-trading/docs/`, and `imports/`. The README is the current front door. Those notes may repeat figures that have been withdrawn.
- Any promise that a report will be read, answered, or fixed.

## Contact

The public face is **Aureon Zorza Technologies**, the trading name of **R&A Consulting and Brokerage Services Ltd** (Belfast, Northern Ireland). Company facts are in [`COMPANY.md`](COMPANY.md). The website is [aureonzorzatechnologies.pl](https://aureonzorzatechnologies.pl).

Writing to that site, or opening a Discussion or Issue, does not create a support contract.

Nothing in this repository is financial, legal, tax, or regulatory advice, and nothing here is an offer of securities or a promise of returns.
