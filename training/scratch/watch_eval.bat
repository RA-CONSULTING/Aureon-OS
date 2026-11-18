@echo off
REM Poll the eval job until its report file appears.
REM
REM Each iteration is a fresh short SSH probe: a long-held session on this
REM cluster is torn down within a minute or two, and the SSH name load-balances
REM across login nodes anyway.
REM
REM Sleep with ping, not `timeout /t`: under a redirected stdin `timeout` exits
REM immediately with "Input redirection is not supported", which turned this
REM loop into 120 back-to-back SSH connections in about three minutes and drew
REM connection resets from the far end.
setlocal
for /L %%i in (1,1,120) do (
    ssh -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=2 u6vs.aip2.isambard "bash /projects/u6vs/hnc-organism/training/scratch/eval_watch.sh"
    if not errorlevel 1 goto :done
    ping -n 61 127.0.0.1 >nul
)
echo watcher gave up after 120 polls
exit /b 1

:done
echo report ready
exit /b 0
