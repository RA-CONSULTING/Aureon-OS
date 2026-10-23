# Merge plan

Standing rules for every source: keep the newest working copy when two trees contain the same module, do not import secrets or credential files, leave live trading off, and leave the protected-path denylist in place. The denylist is `aureon/autonomous/self_repair_guard.py`. It refuses live-trading flags, evidence-gate and HOLD/RELEASE edits, position-sizing edits, and `.env` or credential writes before a patch is applied.

## Already in this tree

| Source | Where it sits | Licence noted here |
|---|---|---|
| RA-CONSULTING/Aureon-OS snapshot | `aureon-os-upstream/` | MIT, Copyright (c) 2025 R&A Consulting |
| RA-CONSULTING/Aureon-Trading--Project-Sero workspace | repository root, `aureon_fusion/`, `aureon_radar/`, `unified_margin_trader/` | This private staging tree |
| NEXUS-LIVE-FEED- | `sources/NEXUS-LIVE-FEED-/` | See that tree's own licence file |
| AUREON-QUANTUM-TRADING-SYSTEM-AQTS- | `sources/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-/` | See that tree's own licence file |
| Local trading material | `aureon-trading/` | Project Sero trading, frontend, and deploy files. This directory is not the Gary-leckey fork |

Paths kept out of the import are listed in `sources/EXCLUDED_FROM_MERGE.txt` (logs, git-lfs pointers, research documents, and secret-bearing scripts).

## Gary-leckey/aureon-trading

Public fork of `RA-CONSULTING/Aureon-OS`. Description: Samuel Harmonic Trading Entity. Homepage: https://trading.aureoninstitute.co.uk/. Licence: MIT. GitHub size about 408,188 KB. Default branch `main` last pushed 27 August 2026, 06:01 Europe/London. Parent `main` was last pushed 18 October 2026, 08:52 Europe/London, at `dcf1d1dd0d`. Gary's `main` is `f5fb1916c0` ("Unify Aureon governance and full-stack runtime", 14 August 2026).

Compare of parent `main` with Gary's `main`: ahead 0, behind 45. Every commit on his `main` is already in the parent. A search of the fork for author name Gary, Leckey, or login Gary-leckey returned no commits. The fork's unique commits are on side branches and are authored by Aureon Bot, Claude, or The Quantum Frequency.

| Branch | Versus parent `main` | Decision |
|---|---|---|
| `main` | ahead 0, behind 45 | Already in upstream. Nothing to copy. |
| `fix/binance-ld-earn-pricing` | ahead 0, behind 1373 | Already in upstream. |
| `fix/prod-unify-and-windows-stdio` | ahead 0, behind 1375 | Already in upstream. |
| `fix/windows-kraken-nonce-lock` | ahead 0, behind 1301 | Already in upstream. |
| `claude/add-margin-trading-jPgFK` | ahead 0, behind 1164 | Already in upstream. |
| `fix/windows-closed-stdout-orca` | ahead 1, behind 1374. Commit `6b149e9eca` by The Quantum Frequency, 11 February 2026. One file: `orca_complete_kill_cycle.py` | The newest Orca files still wrapped `sys.stdout.buffer` with `codecs.getwriter`, which is the closed-file bug this commit fixes. The module already routes `print` through `_safe_print`, so those three call-site edits were not repeated. The `__main__` reconfigure fix was applied to `aureon-os-upstream/aureon/bots/orca_complete_kill_cycle.py` and `aureon_radar/bots/orca_complete_kill_cycle.py`. It does not arm trading. |
| `claude/docs-final` | ahead 3, behind 574. Aureon Bot, 28 April 2026. Eight files | Not applied. `aureon/trading/aureon_live.py` in the current tree already imports `get_binance_client`. The current `INDEX.md`, `CAPABILITIES.md`, `docs/QUICK_START.md`, and `docs/LIVE_TRADING_RUNBOOK.md` are the newer HOLD texts. The fork's runbook and quick start tell the operator to run `scripts/aureon_ignition.py --live`, including for mainnet. Current `scripts/aureon_ignition.py` returns HOLD and submits no order. `.github/FUNDING.yml` on that branch names `github: Gary-leckey` and a personal SumUp payment URL. That payment URL was not copied. |
| `claude/organize-system-new-files-a9jLN` | ahead 1, behind 1094. Moves into the package that later history already has (`aureon/wisdom/civilizational_dna.py`, `aureon/wisdom/maeshowe_seer_decode.py`, `aureon/intelligence/aureon_seer.py`, `public/geometric_glyph.html`, `public/geometric_glyph_animated.html`) | Newest paths kept. The April rename was not replayed. |
| `claude/organize-code-structure-h6Yi1` | ahead 14, behind 1094. Compare listed 300 files, the API cap, almost all renames into `1_substrate/` of loose JSON, caches, and learning-state dumps | Not applied. That layout is 1,094 commits behind the parent, and replaying it would replace the current `aureon/` package with an abandoned directory of runtime dumps. |

No `.env`, credential file, or live-trading flag from the fork was written. The protected-path denylist was not edited.

## Not merged

These two repositories were not cloned and none of their files were copied.

`Gary-leckey/King-Skill-Extended-Cognition-Architecture-for-Scientific-LLM-Agents` is a fork of `Agnuxo1/King-Skill-Extended-Cognition-Architecture-for-Scientific-LLM-Agents`. GitHub reports no licence. Last pushed 11 April 2026. This tree does not import it, submodule it, or pin it. It stays an external program. Aureon OS does not call it. A later experiment could shell out to a checkout the operator supplies, but this tree cannot vendor the source while it has no licence.

`Gary-leckey/Taorice` is a fork of `lindseyhhorton-ui/Taorice` ("Myth Tech for Flamecare"). Last pushed 1 March 2026. This tree does not import it, submodule it, or pin it. It stays an external program. Aureon OS does not call it. A later surface could depend on a released package the operator chooses. It is not part of this merge.

## Public snapshot for RA-CONSULTING/Aureon-OS

The pull request is one commit on top of public `main`. The private repository's git history is not in that commit. Public `main` stays the base because it is the newer OS tree (about 13,676 files versus 10,105 in the nested `aureon-os-upstream` snapshot). The nested snapshot is not copied over it.

Added from the unified workspace, after dropping personal data, job-hunt files, private PDFs and office papers, `.env` files, nested `.git` directories, and the bulky Nexus reel:

- `aureon_fusion/`, `aureon_radar/`, `aureon-trading/`, `unified_margin_trader/`, `organism/`
- `sources/NEXUS-LIVE-FEED-/` and `sources/AUREON-QUANTUM-TRADING-SYSTEM-AQTS-/`
- the self-repair denylist and the tests that lock it
- the Windows Orca text-stream fix on the current Orca entrypoints

Left out of the snapshot: `R&A_CONSULTING_Package/` (outreach, grants, target lists), `kimi-group-chat/`, `research/`, `zenodo_papers/`, `academia_downloads/`, `substack_output/`, `full-workspace-backup/`, and `*.pdf`, `*.docx`, `*.pptx`. Public `main` already contains research PDFs under `Antarctic research/`. This snapshot does not add those, and it does not delete files that were already public.

`sources/Aureon-Trading--Project-Sero/organism/public_market.py` is the read-only market adapter the OS composer already calls. It is the same file as `organism/public_market.py`.

The fusion organs are the working runtime for the pieces that do not run when they still point at a nested `aureon-os-upstream` checkout or a personal Windows profile. `aureon_fusion/paths.py` is the spine: if `aureon-os-upstream/aureon` exists it stays the import root (private workspace); otherwise this repository is the OS (public tree). The read-only write fence still applies only to a directory named `aureon-os-upstream`. Live trading stays off. The self-repair denylist is unchanged.

Credentials found by the scan were removed from the tree. The file and type of each one are in `ROTATE_KEYS.md`. Rotate those before merge. The values are not in this plan. Live trading stays off, and the self-repair denylist is unchanged.
