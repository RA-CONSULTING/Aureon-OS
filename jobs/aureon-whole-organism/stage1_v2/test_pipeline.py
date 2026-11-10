"""Real pinned adapter against an inert local test endpoint, before model startup."""
import argparse,collections,json,sys,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
import run_benchmark as runner
from fixtures import case,canonical

class Pipeline(unittest.TestCase):
    def test_retry_invalid_checkpoint_and_resume(self):
        rows=[case('supported',0,i) for i in range(2)]
        lookup={canonical(r['input']):r for r in rows};calls=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(request);number=len(calls)
                if number==1:
                    self.send_response(503);self.end_headers();self.wfile.write(b'test transient error');return
                r=lookup[request['messages'][-1]['content']]
                text=canonical({'verdict':r['expected_verdict'],'action':r['expected_action'],
                    'cited_sources':r['required_sources'],'confidence':.9,'rationale':'Inert transport test.'})
                if number==2:text='invalid JSON retained as a model failure'
                body=canonical({'model':runner.MODEL,'choices':[{'finish_reason':'stop','message':{'content':text}}],
                                'usage':{'prompt_tokens':10,'completion_tokens':5}}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        previous=runner.URL;runner.URL=f'http://127.0.0.1:{server.server_port}/v1'
        try:
            with tempfile.TemporaryDirectory() as d:
                args=SimpleNamespace(output=d)
                summary=runner.run_block(args,'test',1,rows,{'full':'context','baseline':'base'},1,99)
                self.assertEqual(summary['completed_responses'],8)
                self.assertEqual(summary['schema_valid'],7)
                self.assertEqual(summary['transport_failures'],0)
                self.assertEqual(len(calls),9)
                summary=runner.run_block(args,'test',1,rows,{'full':'context','baseline':'base'},1,99)
                self.assertEqual(summary['new_responses'],0);self.assertEqual(len(calls),9)
                attempts=runner.read_jsonl(Path(d)/'test/attempts.jsonl')
                starts=[r for r in attempts if r['event']=='start']
                self.assertEqual(len(starts),9)
                for r in starts:self.assertEqual(r['request_sha256'],runner.digest(r['request_body_utf8']))
        finally:
            runner.URL=previous;server.shutdown();server.server_close();thread.join()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);args,rest=p.parse_known_args()
    sys.path.insert(0,args.repo)
    import os
    os.environ.update({'AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS':'1','AUREON_AUDIT_MODE':'1',
      'AUREON_LLM_ALLOW_HTTP_IN_AUDIT':'1','AUREON_LLM_PREFER_NATIVE':'0','AUREON_LLM_REQUEST_TIMEOUT_S':'5'})
    for key in ('AUREON_LLM_API_KEY','OPENAI_API_KEY','OLLAMA_API_KEY','AUREON_OLLAMA_API_KEY'):os.environ.pop(key,None)
    unittest.main(argv=[sys.argv[0]]+rest,verbosity=2)
