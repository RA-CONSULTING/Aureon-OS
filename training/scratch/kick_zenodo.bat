@echo off
REM Kill the hung Zenodo pull child, whichever login node the balancer gives us.
REM
REM The child (pid 32824 on login41) has held .lock-zenodo since 11:59:30 while
REM writing nothing, and the guard only restarts a child whose pid has exited,
REM so a stalled-but-alive pull sits there forever. A signal cannot cross nodes,
REM so we sweep: pkill matches only '[f]etch_zenodo.py', which exists solely on
REM the owning node, and is a no-op everywhere else.
REM
REM Sleep with ping, never timeout /t: timeout exits at once when stdin is
REM redirected, which turns this into a connection burst.
setlocal
for /L %%i in (1,1,8) do (
    ssh -o BatchMode=yes -o ConnectTimeout=20 -o ConnectionAttempts=1 u6vs.aip2.isambard "hostname; pkill -9 -f '[f]etch_zenodo.py' && echo PK_YES || echo PK_NO"
    ping -n 6 127.0.0.1 >nul
)
echo sweep done
exit /b 0
