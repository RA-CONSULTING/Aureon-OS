# Autonomy mode

Aureon has one owner-controlled switch, `AUREON_AUTONOMY_MODE`.

| Mode | Who gets it | What self-repair and the self-coder may change |
|---|---|---|
| `guarded` | Public default. Every clone. | Not live flags, not the HOLD/RELEASE gate, not `may_act`, not position sizing, not credential files |
| `full` | The owner, in local state only | Any repo path except credential material. Live flags, the gate, `may_act`, position sizing, and the trading modules included |

`guarded` is the default in code. Nothing in this repository sets `full`. A person who clones the repo is not handed an unguarded live trader.

This is a different switch from `AUREON_AUTONOMY` (the pursuit loop) and from `AUREON_SELF_REPAIR_ENABLE` (which still has to be set, with `state/self_repair_config.json`, before a repair run starts).

## Turning full mode on

Gary does this on his machine. It is not committed.

Either export it from the shell or from an untracked `.env`:

```bash
AUREON_AUTONOMY_MODE=full
```

Or write the untracked file `state/autonomy_mode.json` (the `state/` directory is gitignored):

```json
{"mode": "full"}
```

An explicit environment value wins. `guarded`, an unknown value, a missing file, and an unreadable file all stay guarded. The pytest suite pins `guarded` when the variable is unset, so a local mode file does not flip the guarded tests. Exporting `full` in the environment is the owner's choice and is left as exported.

In full mode:

- Self-repair and the self-coder may edit any path, including live flags, the HOLD/RELEASE gate, `may_act`, position sizing, and the trading modules.
- `AUREON_CODE_AUTO_APPROVE=1` applies to those protected changes too. Credential paths still stay on human review.
- A self-generated patch commits on the current branch after its own tests pass. The commit is local. Nothing is pushed.
- The system may set its own live-trading flag and `may_act` through `set_runtime_authority`. That writes `state/autonomy_runtime.json` and the process environment. It does not place an order.

The census live-arming refusal is quiet in full mode. That is the owner accepting the unguarded-mutation inventory. Guarded mode still refuses to arm while those entries remain.

## What stays, in both modes

These are off switches and records, not a denylist of topics.

- `AUREON_SELF_REPAIR_KILL=1`, or the file `state/SELF_REPAIR_KILL`, stops self-writes and order dispatch. Remove the variable and the file to let the owner mode work again.
- `state/autonomy_audit.jsonl` is append-only. Every self-change and every order attempt is a line. The log is not rewritten. Secret values are redacted and omitted.
- A self-patch that makes its test command fail is rolled back with `git apply -R`.
- Credentials are read from `.env` or the OS keychain. They are never written into the repo, into a patch, or into the audit log. `.env`, key files, and assignments such as `API_SECRET=<value>` are refused in full mode too.

## Risks

Full mode means Aureon can change the code that decides whether money moves, can set `AUREON_LIVE_TRADING` and `may_act` itself, and can commit those edits when the tests it ran came back clean. A bad patch that still passes its own tests stays committed. A venue that is actually armed can lose money. The kill switch stops the next write and the next order; it does not unwind a fill that already happened. The audit log is the record of what the system changed and what it tried to send.

The public default does none of this. Gary turns full mode on. This tree does not.

## Where it lives

- `aureon/autonomous/autonomy_mode.py` — mode, kill switch, audit, runtime authority
- `aureon/autonomous/self_repair_guard.py` — denylist, open only when the mode is full and the kill switch is off
- `aureon/autonomous/aureon_internal_self_coder.py` — rollback, and auto-merge in full mode
- `aureon/queen/unity_exchange_brain.py` — kill switch before dispatch, and an audit line for every order attempt
