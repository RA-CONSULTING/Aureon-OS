@echo off
REM Reconnect loop for the Isambard bulk transfers.
REM
REM This node resets long-lived SSH sessions every minute or two, so a single
REM held-open connection makes no progress. Each iteration opens a session,
REM lets the remote guard start whatever is not already running, and blocks
REM until that session dies. The remote guard refuses to start a second copy of
REM a job whose process survived the reset, which is what corrupted an archive
REM on 2026-10-26.
REM
REM Stop with: close the background task, or kill the ssh process.
setlocal

for /L %%i in (1,1,2000) do (
    echo ==== attempt %%i %DATE% %TIME% ====
    ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=4 u6vs.aip2.isambard "bash /projects/u6vs/hnc-organism/training/scratch/stage_both.sh"
    timeout /t 5 /nobreak >nul
)

echo reconnect loop finished
