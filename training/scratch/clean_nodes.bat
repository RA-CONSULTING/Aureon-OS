@echo off
REM Clean staging writers on every login node the SSH name hands out.
REM One connection only reaches one node, so sample repeatedly.
setlocal
for /L %%i in (1,1,12) do (
    ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=2 u6vs.aip2.isambard "bash /projects/u6vs/hnc-organism/training/scratch/kill_strays.sh"
)
