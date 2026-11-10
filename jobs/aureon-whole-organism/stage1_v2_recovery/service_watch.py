"""Supervise a benchmark without modifying its requests, scoring or journals."""
from __future__ import annotations
import argparse, datetime, http.client, json, os, signal, subprocess, sys, time
from pathlib import Path

def healthy(port=8000, timeout=3):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=timeout)
    try:
        connection.request('GET','/health')
        response=connection.getresponse()
        return response.status==200
    except (OSError,http.client.HTTPException):
        return False
    finally:
        connection.close()

def supervise(command, receipt, *, port=8000, interval=5., failures=3, timeout=3., grace=15.):
    if not command or not 1<=port<=65535 or min(interval,timeout,grace)<=0 or failures<1:
        raise ValueError('Invalid supervision configuration')
    receipt=Path(receipt)
    # Every invocation has a new journal. Never erase an earlier service failure.
    stream=receipt.open('xb',buffering=0)
    def event(kind,**fields):
        row=dict(event=kind,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**fields)
        stream.write((json.dumps(row,sort_keys=True)+'\n').encode());os.fsync(stream.fileno())
    child=None
    def stop_child():
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=grace)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=grace)
    try:
        event('guard_start',command=command,port=port,interval_seconds=interval,failed_checks_limit=failures)
        if not healthy(port,timeout):
            event('service_unhealthy_before_launch');return 31
        flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
        child=subprocess.Popen(command,creationflags=flags)
        event('client_started',pid=child.pid)
        consecutive=0
        while True:
            status=child.poll()
            if status is not None:
                event('client_exit',returncode=status);return status
            ok=healthy(port,timeout)
            consecutive=0 if ok else consecutive+1
            event('health_check',healthy=ok,consecutive_failures=consecutive)
            if consecutive>=failures:
                event('service_failure_stop',client_pid=child.pid)
                stop_child()
                event('client_stopped',returncode=child.returncode,
                      journal_policy='Preserve every durable record; unresolved attempts require explicit reconciliation.')
                return 31
            time.sleep(interval)
    finally:
        stop_child();stream.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt',required=True)
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    return supervise(command,args.receipt)

if __name__=='__main__':raise SystemExit(main())
