import http.server,json,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from service_watch import supervise

class Handler(http.server.BaseHTTPRequestHandler):
    checks=0
    healthy_checks=999
    failure_marker=None
    def do_GET(self):
        type(self).checks+=1
        failed=type(self).failure_marker is not None and type(self).failure_marker.exists()
        self.send_response(200 if self.path=='/health' and type(self).checks<=type(self).healthy_checks and not failed else 503)
        self.end_headers()
    def log_message(self,*args):pass

class WatchTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        Handler.checks=0;Handler.healthy_checks=999;Handler.failure_marker=None
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.temp.cleanup()
    def run_child(self,script):
        return supervise([sys.executable,'-c',script],self.root/'events.jsonl',
                         port=self.server.server_port,interval=.04,failures=2,timeout=.1,grace=1)
    def rows(self):return [json.loads(x) for x in (self.root/'events.jsonl').read_text().splitlines()]
    def test_success_is_not_rescored(self):
        self.assertEqual(self.run_child('import sys;sys.exit(0)'),0)
        self.assertEqual(self.rows()[-1]['event'],'client_exit')
    def test_failed_client_exit_is_preserved(self):
        self.assertEqual(self.run_child('import sys;sys.exit(2)'),2)
        self.assertEqual(self.rows()[-1]['returncode'],2)
    def test_service_failure_stops_new_work_and_retains_partial_journal(self):
        partial=self.root/'partial.jsonl'
        Handler.failure_marker=partial
        script='import time,pathlib,os;p=pathlib.Path('+repr(str(partial))+');f=p.open("w");f.write("durable\\n");f.flush();os.fsync(f.fileno());f.close();time.sleep(30)'
        started=time.monotonic();self.assertEqual(self.run_child(script),31)
        self.assertLess(time.monotonic()-started,5)
        self.assertEqual(partial.read_text(),'durable\n')
        self.assertIn('service_failure_stop',[x['event'] for x in self.rows()])
    def test_initial_failure_does_not_launch_client(self):
        Handler.healthy_checks=0;marker=self.root/'launched'
        self.assertEqual(self.run_child('import pathlib;pathlib.Path('+repr(str(marker))+').touch()'),31)
        self.assertFalse(marker.exists())
    def test_prior_receipt_cannot_be_overwritten(self):
        self.run_child('pass');original=(self.root/'events.jsonl').read_bytes()
        with self.assertRaises(FileExistsError):self.run_child('pass')
        self.assertEqual((self.root/'events.jsonl').read_bytes(),original)

if __name__=='__main__':unittest.main()
