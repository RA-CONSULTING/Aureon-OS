# How Aureon OS is reviewed and kept safe

This page is for people downloading Aureon OS. It describes the review practice, the tests, how secrets are handled, and the live-trading safety controls that exist in this repository. A control-by-control map is in [`CONTROLS_MATRIX.md`](CONTROLS_MATRIX.md).

The practices below are **aligned with** SOC 2 Trust Services Criteria and ISO/IEC 27001:2022 Annex A themes. This project has not had a formal audit, and this page is not an attestation.

Go-live stays **HOLD**. This checkout is research-stage software. There is a live trading route if exchange keys are present; that is described honestly below.

## How changes are reviewed

The team's current practice is:

- one small pull request at a time
- three reviewer PASSes at the exact commit being merged
- a squash merge onto `main`

The PASS reviewers are AI review agents run by the maintainer, not human reviewers. Gary Leckey, the maintainer, is the only human with merge and publish authority.

That practice is how changes are meant to land, and it has had exceptions. It is not enforced by branch protection: GitHub branch protection is not enabled on `main` at the time of writing, so the platform itself does not require a pull request, those reviews, or a green CI check before a push. Merges have occasionally landed with fewer than three PASSes at the merged commit (for example #324, #242 and #245). [`CODEOWNERS`](../CODEOWNERS) names `@RA-CONSULTING` as the default owner; it is not enforced by a protection rule. The contribution notes in [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`docs/CONTRIBUTING.md`](CONTRIBUTING.md) are the files to read next, and some of that text is still due an update.

## Tests

The repository has a large pytest suite covering isolation, rate limits, the live-trading gate, self-repair, operator and SaaS surfaces, and other contracts.

CI is defined in 21 workflows under [`.github/workflows/`](../.github/workflows/). The ones most relevant here:

- [`.github/workflows/main_ci.yml`](../.github/workflows/main_ci.yml) — compile the package and run an offline product-surface pytest suite on push and pull request to `main`
- [`.github/workflows/operator-ci.yml`](../.github/workflows/operator-ci.yml) — ruff, mypy, and the strict-tier tests for `aureon/operator`, `aureon/saas`, and the connectome
- [`.github/workflows/plug-and-play.yml`](../.github/workflows/plug-and-play.yml) — a clean-checkout guarded smoke (`./install.sh --smoke`)
- [`.github/workflows/gitleaks.yml`](../.github/workflows/gitleaks.yml) — gitleaks 8.28.0 on the tree being merged (`gitleaks detect --no-git --redact`)
- [`.github/workflows/plumber-contract.yml`](../.github/workflows/plumber-contract.yml) — Plumber contract jobs

Because `main` is not branch-protected, these workflows can be bypassed by a direct push. They are real checks when they run; they are not a required gate on every change.

## Secret handling

New credentials must not be committed. That rule is written in [`SECURITY.md`](../SECURITY.md) and [`docs/PUBLIC_ENV.md`](PUBLIC_ENV.md).

- [`.env.example`](../.env.example) ships placeholder names only. Secret lines there are blank, or an obvious placeholder in a vendored template. A real key value does not go in that file.
- [`.gitignore`](../.gitignore) ignores `.env*` and keeps `.env.example` and `.env.sample` committable.
- [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) runs gitleaks 8.28.0 on staged files. [`.gitleaks.toml`](../.gitleaks.toml) is the config.
- GitHub secret scanning and push protection are enabled on this repository.

Children launched through [`aureon/core/aureon_baton_link.py`](../aureon/core/aureon_baton_link.py), [`aureon/launch/session_scope.py`](../aureon/launch/session_scope.py), sandbox self-repair ([`aureon/autonomous/aureon_sandbox_self_repair.py`](../aureon/autonomous/aureon_sandbox_self_repair.py)), and [`aureon/autonomous/queen_benchmark_gate.py`](../aureon/autonomous/queen_benchmark_gate.py) go through `isolated_child_env` in `session_scope`. That helper strips credential-like names (`strip_credentials`), drops arming switches and the live-profile names, and forces the off values in `FORCED_OFF` (`disarm`). Those forced values include `AUREON_LIVE_TRADING=0`, `AUREON_AUTONOMY_MODE=guarded`, `AUREON_ACTIVATE_ON_IMPORT=0`, and the paper, testnet, or demo values each exchange reader parses. `SIMULATION_MODE` and `DEMO_MODE` are dropped rather than forced on. Repair and gate children also set `AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1` and drop `AUREON_QUEEN_REPAIR_ROOT` in `aureon_baton_link`. Other launch sites are still open: [`aureon/autonomous/aureon_repo_self_repair.py`](../aureon/autonomous/aureon_repo_self_repair.py) (line 197) and [`aureon/briefing/assemble.py`](../aureon/briefing/assemble.py) (line 416) pass their own `env=` without going through `isolated_child_env`, and [`aureon/autonomous/aureon_internal_self_coder.py`](../aureon/autonomous/aureon_internal_self_coder.py) passes no `env`. Tests for the isolated path include [`tests/test_isolated_child_env_hardening.py`](../tests/test_isolated_child_env_hardening.py), [`tests/test_self_repair_session_isolation.py`](../tests/test_self_repair_session_isolation.py), and [`tests/test_baton_link_isolated_repair.py`](../tests/test_baton_link_isolated_repair.py).

Imported historical trees are quarantined: they are not on the canonical runtime path. See [`imports/README_QUARANTINED.md`](../imports/README_QUARANTINED.md). Denied Plumber material is recorded as metadata-only quarantine records in [`aureon/plumber/quarantine.py`](../aureon/plumber/quarantine.py).

## Live-trading safety controls that exist

These controls are in the tree. They are not a promise that live trading cannot happen.

- **Child environment isolation (partial).** Children launched through `aureon_baton_link`, `session_scope`, sandbox self-repair, and `queen_benchmark_gate` go through `session_scope.isolated_child_env`, as above. Other launch sites are still open: `aureon/autonomous/aureon_repo_self_repair.py:197` and `aureon/briefing/assemble.py:416` pass their own `env=` without going through it, and `aureon/autonomous/aureon_internal_self_coder.py` passes no `env`.
- **Capital.com shared pacer.** [`aureon/exchanges/capital_shared_state.py`](../aureon/exchanges/capital_shared_state.py) shares one session, login spacing, request window, and 429 backoff across processes on the same box. Order requests are refused if the shared lock cannot be taken or written. The Phi-Radar client in [`aureon_radar/capital_client.py`](../aureon_radar/capital_client.py) uses the same shared state. Tests: [`tests/test_capital_rate_limit_shared_session.py`](../tests/test_capital_rate_limit_shared_session.py), [`tests/test_radar_capital_shared_pacing.py`](../tests/test_radar_capital_shared_pacing.py). Rate-limit background is in [`docs/runbooks/PRODUCTION_RATE_LIMITING.md`](runbooks/PRODUCTION_RATE_LIMITING.md).
- **Launcher session teardown.** `kill_session` in [`aureon/launch/session_scope.py`](../aureon/launch/session_scope.py) stops the recorded launcher scope (systemd unit, cgroup, and pid tree). That is process teardown for a launcher session. It is not a global trading stop. Test: [`tests/test_launcher_session_scope_kill.py`](../tests/test_launcher_session_scope_kill.py).
- **Guarded mode.** `AUREON_AUTONOMY_MODE=guarded` (or `state/autonomy_mode.json` with `{"mode": "guarded"}`) turns on the self-coding denylist and is the mode used by `./install.sh --smoke`. The public default, when the variable is unset, is `full`. See [`AUTONOMY.md`](../AUTONOMY.md) and [`aureon/autonomous/autonomy_mode.py`](../aureon/autonomous/autonomy_mode.py).
- **Go-live HOLD.** The release-boundary badge on the [root README](../README.md) is HOLD. [`docs/runbooks/GO_LIVE_HARDENING.md`](runbooks/GO_LIVE_HARDENING.md) records go-live as terminal HOLD. The guarded smoke leaves live trading off for that run and does not read `.env`.

The same README and [`docs/PUBLIC_ENV.md`](PUBLIC_ENV.md) are also explicit about the live route: the master launcher ([`scripts/launch/aureon-master.sh`](../scripts/launch/aureon-master.sh)) overrides the disable and dry-run flags when autonomy is full and a complete exchange key group is present in `.env`, the inherited shell, or `aureon_radar/.env`. Exchange keys in `.env` make that boot live. Those flags are not a lock.

## Known limits

**There is no global kill switch.** [`AUTONOMY.md`](../AUTONOMY.md) states this directly:

> When exchange keys are in `.env`, a venue can lose money. There is no kill switch. Order attempts are written to the autonomy audit, and secret values stay redacted.

The same file says `AUREON_SELF_REPAIR_KILL` and `state/SELF_REPAIR_KILL` do not stop self-writes or order dispatch. In code, `kill_switch_engaged()` in [`aureon/autonomous/autonomy_mode.py`](../aureon/autonomous/autonomy_mode.py) is retired and always returns false. `--stop` and `--status` on the master launcher are process control, not a trading or self-coding stop.

**Old credentials remain in public git history.** [`ROTATE_KEYS.md`](../ROTATE_KEYS.md) is the inventory. It says public `main` still contains live credentials in history; a full-history gitleaks scan reported 277 leaks; the current tree no longer contains `.env` or `.env1.txt`; hardcoded copies that remain in the tree were replaced with the literal placeholder `REDACTED`; the live values are still reachable in history; history was not rewritten; and rotation is not a merge blocker. It asks that every named generation be rotated, including ones that were later replaced. This page does not add a rotation-complete claim beyond that file.

**No formal audit has been done.** This organisation has not completed a SOC 2 attestation or an ISO/IEC 27001:2022 management-system audit.

## Reporting a vulnerability

Please report security issues privately. Use GitHub's private [Security Advisories](https://github.com/RA-CONSULTING/Aureon-OS/security/advisories/new) for this repository, or email [gary@aureonzorzatechnologies.com](mailto:gary@aureonzorzatechnologies.com). See [`SECURITY.md`](../SECURITY.md).
