# Self-repair

A developer points Aureon at a Python project. Aureon runs that project's pytest suite, repairs a proved implementation bug, runs the tests again, and commits the repair on a local branch. Nothing is pushed.

```bash
AUREON_SELF_REPAIR_ENABLE=1 python -m aureon_fusion.repair --root /path/to/project
```

The project also needs `state/self_repair_config.json` containing `{"enabled": true}`. The command exits 0 when the tests pass after the repair, or when they already passed.

Self-repair stays disabled unless both of those are set. `AUREON_SELF_REPAIR_KILL=1` stops it even then. A missing or unreadable config stops it too.

## What it repairs

In one run it can repair several failures, as long as each one is proved by the tests and is outside the denylist:

- an off-by-one in a pure utility (`return 1` against `assert band_offset() == 0`)
- a function that returns the wrong constant
- a two-argument function that uses the wrong operator (`return a - b` against `assert add(2, 3) == 5`)
- a `NameError` whose missing name is one character away from exactly one name in that file

It edits implementation files only. Test files are left as they are. After the suite passes, the change is committed on `aureon-self-repair/<timestamp>`. A line is appended to `state/self_repair_review_log.jsonl`.

## What it refuses

The denylist is checked before a write or a patch is applied. A refused change is not written. The review log records `human_review_required` and the reason. It does not record secret values.

- live or real-money flags, including `AUREON_LIVE_TRADING`, `CONFIRM_LIVE_TRADING`, `testnet: false`, and `PAPER_MODE=false`
- any change to evidence-gate or HOLD/RELEASE logic, including `may_act`, `action_eligible`, and `economic_mutation`
- any change to position sizing (`position_qty`, `position_size`, and the same family)
- creating or modifying `.env` and credential files

`AUREON_CODE_AUTO_APPROVE=1` does not cover those paths. An auto-approved proposal that touches them stays `pending_human_review`, and `_apply_approved_patch` returns before `git apply`.

A repair that would make a test pass by flipping HOLD to RELEASE, or by changing a position size, is rejected and flagged for human review.
