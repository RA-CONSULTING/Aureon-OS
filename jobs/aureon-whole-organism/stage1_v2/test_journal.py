import hashlib,json,tempfile,unittest
from pathlib import Path
from fixtures import canonical,digest
from run_benchmark import Journal,read_jsonl,reconcile,plan

class JournalTests(unittest.TestCase):
    def test_durable_roundtrip_and_torn_tail_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal.jsonl';j=Journal(p);j.append({'v':'Rune þ'});j.close()
            self.assertEqual(read_jsonl(p),[{'v':'Rune þ'}])
            with p.open('ab') as f:f.write(b'{"unfinished":')
            original=p.read_bytes()
            with self.assertRaises(RuntimeError):Journal(p)
            self.assertEqual(p.read_bytes(),original)

    def test_resume_requires_matching_attempt(self):
        plans=[{'key':'k'}]
        start={'event':'start','key':'k','attempt':1}
        end={'event':'end','key':'k','attempt':1,'transport_ok':True}
        final={'key':'k','attempt':1,'attempt_result_sha256':digest(canonical(end))}
        rows,_=reconcile(plans,[start,end],[final]);self.assertEqual(len(rows),1)
        for attempts,finals in (([end],[final]),([start,end],[final,final]),([start,start,end],[final]),
                               ([start,end],[{**final,'attempt_result_sha256':'bad'}])):
            with self.assertRaises(RuntimeError):reconcile(plans,attempts,finals)

    def test_interrupted_final_index_retains_completed_http(self):
        start={'event':'start','key':'k','attempt':1}
        end={'event':'end','key':'k','attempt':1,'transport_ok':True}
        finals,attempts=reconcile([{'key':'k'}],[start,end],[])
        self.assertFalse(finals);self.assertTrue(attempts['k'][1]['transport_ok'])

    def test_balanced_condition_plan_is_deterministic(self):
        rows=[{'scenario_id':'a'},{'scenario_id':'b'}];contexts={'full':'x','baseline':'y'}
        a=plan(rows,contexts,2,7);b=plan(rows,contexts,2,7);c=plan(rows,contexts,2,8)
        self.assertEqual(a,b);self.assertNotEqual(a,c);self.assertEqual(len(a),16)
        self.assertEqual(len({r['key'] for r in a}),16)

if __name__=='__main__':unittest.main(verbosity=2)
