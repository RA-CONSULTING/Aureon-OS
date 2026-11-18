@echo off
REM Wait for the eval report, probing once every five minutes.
REM
REM The front end dropped and then timed out this address after an earlier loop
REM opened ~120 connections in three minutes, so spacing matters more than
REM latency here: one connect per five minutes will not re-trigger the block,
REM and the Slurm job runs to completion on the compute node either way.
setlocal
for /L %%i in (1,1,18) do (
    ssh -o BatchMode=yes -o ConnectTimeout=25 -o ConnectionAttempts=1 u6vs.aip2.isambard "bash /projects/u6vs/hnc-organism/training/scratch/eval_watch.sh"
    if not errorlevel 1 goto :done
    ping -n 301 127.0.0.1 >nul
)
echo gave up after 18 probes
exit /b 1

:done
echo report ready
exit /b 0
