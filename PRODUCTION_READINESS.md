# Production readiness

Live trading is never armed by the system. Evidence gates are never loosened. Those rules are enforced in the writer, the sandbox repair, and the self-coder before a patch is applied.

## Self-repair fail-safe

| Control | Effect |
|---|---|
| `AUREON_SELF_REPAIR_ENABLE` unset | Self-repair stays disabled |
| `state/self_repair_config.json` missing, unreadable, or `"enabled"` not `true` | Self-repair stops (`missing_config` or `self_repair_disabled`) |
| `AUREON_SELF_REPAIR_KILL=1` | Self-repair stops, even when enable and the config are set |
| Protected path or pattern | The write or patch is not applied. The review log flags it for human review |

Both the enable flag and the config file are required. Either one on its own does not start a repair.

## Denylist

Checked by `aureon/autonomous/self_repair_guard.py` before Queen writes, before sandbox edits, before `git apply` in `aureon/autonomous/aureon_internal_self_coder.py`, and before the coherence-gate director backs up or applies a diff.

- `AUREON_LIVE_TRADING` and other live or real-money flags
- evidence gates and HOLD/RELEASE logic
- position sizing
- `.env` and credential files

`AUREON_CODE_AUTO_APPROVE=1` does not mark those proposals approved and does not apply them.

## Where this was run

```
cd aureon-os-upstream && PYTHONPATH=. python3 -m pytest tests/test_sandbox_self_repair.py tests/test_protected_patch_denylist.py tests/test_safe_code_control.py tests/test_orca_windows_stdio.py -q --tb=line
................                                                         [100%]
16 passed
```

The market-data WebSocket notes remain in `aureon-os-upstream/docs/runbooks/PRODUCTION_READINESS.md` and `aureon-trading/docs/runbooks/PRODUCTION_READINESS.md`. They are not a switch for live trading.

## Gary-leckey/aureon-trading

That public MIT fork of Aureon OS was compared with parent `main` before anything was copied. Its `main` is already contained in the parent. The Windows stdout fix from `fix/windows-closed-stdout-orca` (`6b149e9eca`) was applied to the two current Orca entrypoints because they still wrapped `sys.stdout.buffer`. Branches that instruct `scripts/aureon_ignition.py --live`, add a personal payment URL, or rename the tree into `1_substrate/` were not applied. Live trading stays off. The denylist was not changed. `Gary-leckey/King-Skill-Extended-Cognition-Architecture-for-Scientific-LLM-Agents` and `Gary-leckey/Taorice` were not merged. See `MERGE_PLAN.md`.
