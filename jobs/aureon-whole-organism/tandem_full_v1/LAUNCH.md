# Tandem full-wave launch record

This launcher uses the frozen tandem-repair-v1 experiment without changing its
source, hypotheses, output handling, trial identities or analysis plan.
The successful 6506231 preflight and all 28 receipts from pilot 6506293 have
passed source, array, identity and distinct-GPU checks. An independent local
scalar Kalman calculation reproduces saved sample scores. Pilot runtime gives
a 697.2-second full estimate and a 1645.8-second estimate including the declared
50% margin plus ten minutes. The hard limit is tightened from the protocol's
three-hour ceiling to 45 minutes: eight nodes, 32 GPUs, at most six node-hours.
No hypothesis or detection threshold was selected using pilot outcomes.

Allocation information was refreshed using current project scheduler records.
The prior portal balance retains its date and estimated labels; renewed portal
authentication awaits the user. The resource decision uses full physical-node
accounting plus active remaining ceilings and the new six-node-hour ceiling,
against the last verified September opening balance. This is a conservative
planning estimate conditional on no unobserved allocation changes, not a live
spendable-credit claim. See allocation.json for the exact evidence.

Every full result must be hash-audited and its statistics independently checked.
The pilot overlaps the first 512 production identities in cells 0,15,16,31 of
every stage. Those records remain in accounting but are excluded from inference.
The eligibility count is 2,308,096 of 2,322,432 generated full records.
Scheduler completion alone is not an experimental conclusion.
