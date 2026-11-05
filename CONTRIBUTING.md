# Contributing to Aureon

The full contribution guide lives at [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md).

## Quick start

```bash
pip install -e '.[operator,dev]'          # install with dev toolchain
AUREON_LLM_OFFLINE=1 pytest tests/test_operator_*.py tests/test_saas_*.py tests/test_connectome.py -q
ruff check aureon/operator/ aureon/saas/   # strict-tier lint
mypy aureon/operator/ aureon/saas/         # strict-tier types
```

## Ground rules

- The **strict tier** (`aureon/operator`, `aureon/saas`, the connectome) must stay
  ruff-clean, mypy-clean, and tests-green — CI gates on it.
- The wider tree is on an informational lint ratchet — see
  [`docs/runbooks/PRODUCTION_GRADE.md`](docs/runbooks/PRODUCTION_GRADE.md).
- Preserve the creator's voice in research/synthesis docs; keep quantitative claims
  pre-registered and falsifiable (see [`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md)).
- Never commit secrets. See [`SECURITY.md`](SECURITY.md).
- Questions and conversation belong in [GitHub Discussions](https://github.com/RA-CONSULTING/Aureon-OS/discussions). Read [`docs/COMMUNITY.md`](docs/COMMUNITY.md) first. The release boundary stays HOLD.

By contributing you agree your contributions are licensed under the repository's
[MIT License](LICENSE).
