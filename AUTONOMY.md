# Autonomy mode

Aureon has one switch, `AUREON_AUTONOMY_MODE`.

| Mode | Who gets it | What self-repair and the self-coder may change |
|---|---|---|
| `full` | Public default. Every local run with the variable unset | Any repo path except credential material. Live flags, the gate, `may_act`, position sizing, and the trading modules included. Auto-approve is on. A patch commits after its own tests pass |
| `guarded` | Opt-in. `AUREON_AUTONOMY_MODE=guarded` or `state/autonomy_mode.json` with `{"mode": "guarded"}` | Not live flags, not the HOLD/RELEASE gate, not `may_act`, not position sizing, not credential files |

`full` is the default in code. A missing state file is full. An unknown explicit environment value stays guarded. An explicit environment value wins over the file.

This is a different switch from `AUREON_AUTONOMY` (the pursuit loop) and from `AUREON_SELF_REPAIR_ENABLE` (which still has to be set, with `state/self_repair_config.json`, before a repair run starts). The launcher does not enable repair and does not invent a goal.

## Trading

The master launcher (`scripts/launch/aureon-master.sh`) boots the organism in full mode.

Trading is live when the person running it has put their own exchange keys in `.env` (Kraken, Binance, Alpaca, or Capital.com: the whole group for that venue). The health report then says `trading_mode=live (exchange keys present)`.

With no complete key group, every child stays in paper/public-data mode and the report says `trading_mode=paper/public-data (no exchange keys)`. Key presence is the switch. The launcher does not place an order by itself, and it does not create `capital_release.flag`.

Explicit `AUREON_AUTONOMY_MODE=guarded` puts the self-coding denylist back and keeps that boot on the paper profile.

## What stays

Credentials are read from `.env` or the OS keychain. They are never written into the repo, into a patch, or into a log. `.env`, key files, and assignments such as `API_SECRET=<value>` are refused in full mode too.

`AUREON_SELF_REPAIR_KILL` and `state/SELF_REPAIR_KILL` do not stop self-writes or order dispatch. The launcher does not write `state/autonomy_audit.jsonl`. A self-patch whose tests fail stays applied. A patch whose tests pass still commits on the current branch. Nothing is pushed.

`--stop` and `--status` on the master launcher are process control. They are not a trading or self-coding stop.

## Risks

Full mode means Aureon can change the code that decides whether money moves, can approve those edits itself, and can commit them when the tests it ran came back clean. A patch whose tests fail stays in the working tree. A bad patch that still passes its own tests stays committed. When exchange keys are in `.env`, a venue can lose money. There is no kill switch and no autonomy audit of the fill.

## Where it lives

- `aureon/autonomous/autonomy_mode.py` — mode, runtime authority, key presence
- `aureon/launch/master.py` — boot profile, paper without keys, live with keys, `--stop` and `--status`
- `aureon/autonomous/self_repair_guard.py` — denylist, open when the mode is full
- `aureon/autonomous/aureon_internal_self_coder.py` — a failed patch stays applied; full mode commits after tests pass
- `aureon/queen/unity_exchange_brain.py` — dispatch is not stopped by a kill file
