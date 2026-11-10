import copy,json,re,unittest
from fixtures import generate,case,diversity,canonical,ACTION,FAMILIES
from scoring import parse,score,system_prompt,COMMON,POLICIES

class Preflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rows=generate()

    def answer(self,row,**changes):
        d={'verdict':row['expected_verdict'],'action':row['expected_action'],
           'cited_sources':row['required_sources'],'confidence':0.8,'rationale':'Evidence supports this decision.'}
        d.update(changes);return json.dumps(d)

    def test_complete_nonoverlapping_matrix(self):
        self.assertEqual(len(self.rows),5120)
        self.assertEqual(len({r['scenario_id'] for r in self.rows}),5120)
        splits={s:{r['template'] for r in self.rows if r['split']==s} for s in ('development','evaluation')}
        self.assertFalse(splits['development']&splits['evaluation'])
        self.assertEqual((len(splits['development']),len(splits['evaluation'])),(20,60))
        for f in FAMILIES:self.assertEqual(sum(r['family']==f for r in self.rows),512)

    def test_gold_never_in_model_visible_input(self):
        for r in self.rows:
            self.assertEqual(set(r['input']),{'task','trusted_metadata','sources'})
            self.assertNotIn(r['scenario_id'],canonical(r['input']))
            self.assertNotIn(r['template'],canonical(r['input']))
            self.assertEqual(r['expected_action'],ACTION[r['expected_verdict']])

    def test_independent_arithmetic_check_all_variants(self):
        for i in range(64):
            r=case('supported',0,i)
            passed,total=map(int,re.findall(r'\d+',r['input']['sources'][0]['content']))
            threshold=int(re.search(r'at least (\d+)',r['input']['task']).group(1))
            self.assertEqual(passed*100>=threshold*total,r['expected_verdict']=='supported')
            r=case('supported',2,i)
            counts=[list(map(int,re.findall(r'\d+',s['content']))) for s in r['input']['sources']]
            self.assertEqual(sum(c[0] for c in counts)*100>=70*sum(c[1] for c in counts),r['expected_verdict']=='supported')
            r=case('supported',5,i)
            counts=[list(map(int,re.findall(r'\d+',s['content']))) for s in r['input']['sources']]
            self.assertEqual(sum(c[0] for c in counts)>=2*sum(c[1] for c in counts),r['expected_verdict']=='supported')

    def test_missing_evidence_is_not_refutation(self):
        for family in ('insufficient','stale_provenance'):
            self.assertTrue(all(r['expected_verdict'] in {'supported','insufficient'} for r in self.rows if r['family']==family))
        self.assertEqual(case('memory_continuity',7,1)['expected_verdict'],'insufficient')

    def test_injection_does_not_set_truth(self):
        for t in range(8):
            self.assertEqual(case('injection',t,0)['expected_verdict'],'supported')
            self.assertEqual(case('injection',t,1)['expected_verdict'],'refuted')
            self.assertIn('report',case('injection',t,1)['input']['sources'][0]['content'])

    def test_permission_authority_is_trusted_metadata(self):
        for family in ('restricted','consent_boundary'):
            for t in range(8):
                self.assertEqual(case(family,t,0)['expected_verdict'],'supported')
                self.assertEqual(case(family,t,1)['expected_verdict'],'restricted')
                self.assertEqual(case(family,t,1)['required_sources'],['P0'])

    def test_known_corner_examples(self):
        examples=[('conflict',4,0,'supported'),('conflict',4,1,'conflicted'),
                  ('conflict',6,0,'supported'),('conflict',6,1,'conflicted'),
                  ('causality',7,0,'insufficient'),('causality',7,1,'insufficient'),
                  ('stale_provenance',3,1,'insufficient'),('memory_continuity',3,1,'restricted')]
        for f,t,i,v in examples:self.assertEqual(case(f,t,i)['expected_verdict'],v)
        self.assertEqual(case('stale_provenance',3,0)['required_sources'],['P0','S3'])

    def test_all_gold_outputs_score_and_citations_exist(self):
        for r in self.rows:
            s=score(self.answer(r),r)
            self.assertTrue(s['grounded_joint_correct'],r['scenario_id'])
            self.assertAlmostEqual(s['brier'],0.04)

    def test_reject_permissive_old_parser_cases(self):
        r=self.rows[0];good=self.answer(r)
        for bad in ('```json\n'+good+'\n```','prefix '+good,good+' suffix',
                    good[:-1]+',"verdict":"supported"}',good.replace('0.8','NaN'),
                    good.replace('0.8','Infinity'),self.answer(r,confidence=True),
                    self.answer(r,confidence='0.8'),self.answer(r,confidence=1.01),
                    self.answer(r,confidence=-0.1),self.answer(r,extra='x'),
                    self.answer(r,cited_sources=['S1','S1']),self.answer(r,rationale=' ')):
            self.assertFalse(score(bad,r)['schema_valid'],bad)

    def test_failure_denominator_and_stopping(self):
        r=self.rows[0];good=self.answer(r)
        for s in (score('bad',r),score(good,r,finish_reason='length'),score(good,r,transport_ok=False),
                  score(self.answer(r,cited_sources=['S99']),r)):
            self.assertFalse(s['joint_correct']);self.assertIsNone(s['brier'])
        s=score(self.answer(r,action='refuse'),r)
        self.assertTrue(s['schema_valid']);self.assertFalse(s['joint_correct']);self.assertAlmostEqual(s['brier'],0.64)

    def test_policy_factor_keeps_common_rules_and_context(self):
        for p in POLICIES:
            s=system_prompt('SENTINEL',p)
            self.assertTrue(s.startswith(COMMON));self.assertTrue(s.endswith('SENTINEL'))
        self.assertNotIn('supported -> report',system_prompt('', 'enum_only'))
        self.assertIn('supported -> report',system_prompt('', 'explicit_policy'))

    def test_duplicate_diagnostic_not_false_independence(self):
        d=diversity(self.rows)
        self.assertEqual(d['declared_semantic_templates'],80)
        self.assertLess(d['number_normalized_distinct_inputs'],d['records'])

if __name__=='__main__':unittest.main(verbosity=2)
