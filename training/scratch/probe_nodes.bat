@echo off
REM Sample several SSH connections and report which login node answered and
REM whether a fetch is running there. The SSH name load-balances, so this is
REM the only way to see the whole cluster rather than one node.
setlocal
for /L %%i in (1,1,8) do (
    ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=2 u6vs.aip2.isambard "bash /projects/u6vs/hnc-organism/training/scratch/probe.sh"
)
