import hashlib,json,pathlib,sys,unittest
import numpy as np
import audit_qgita_missingness as audit
ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,sys.argv[2] if len(sys.argv)>2 else str(ROOT/'work/qgita-missingness-v1'))
import qgita_missing as candidate
import audit_qgita_ucr_robustness as legacy


class AuditChecks(unittest.TestCase):
    def test_independent_bank_and_endpoint(self):
        x=np.random.default_rng(801).normal(size=1100);train=700;scales=legacy.training_scales(x,train)
        for scenario in ['mcar_01','mcar_05','mcar_10','mcar_20','burst_05','burst_10']:
            rng=np.random.default_rng(int.from_bytes(hashlib.sha256(('audit-test|'+scenario).encode()).digest()[:8],'big'))
            if scenario.startswith('mcar_'):mask=legacy.mcar_mask(len(x),train,int(scenario.split('_')[1])/100,rng)
            elif scenario=='burst_05':mask=legacy.burst_mask(len(x),train,rng)
            else:
                mask=np.zeros(len(x),dtype=bool)
                for start in rng.integers(train,len(x),size=5):mask[int(start):min(len(x),int(start)+8)]=True
            filled=legacy.locf(x,mask)
            for observed,data in [(True,x),(False,filled)]:
                original=candidate.score_bank(data,mask,train,scales,require_observed=observed)
                reference=audit.independent_bank(data,mask,train,scales,legacy.LATTICE,observed)
                for left,right in zip([original['scores'],original['winner_component'],original['eligible_components']],reference):
                    self.assertTrue(np.array_equal(left,right,equal_nan=True))
                self.assertEqual(candidate.select(original,train,800,850),audit.endpoint(reference[0],train,800,850))

    def test_analytic_family_contrasts(self):
        names=['mcar_01','mcar_05','mcar_10','mcar_20','burst_05','burst_10']
        cfg=dict(bootstrap_seed_sequence=[20260912,41],bootstrap_draws=2000,historical_scenarios=['mcar_05','mcar_10','burst_05'],new_scenarios=names)
        rows=[]
        for i in range(46):
            counts=dict(n=32,observed=32,locf=0,coverage_sum=32.)
            rows.append(dict(family_key=str(i),clean=1,per_scenario={phase:{s:dict(counts) for s in names} for phase in ['historical','new_masks']}))
        result=audit.statistics(rows,cfg)
        for row in result['new_masks'].values():
            self.assertEqual(row['family_macro'],dict(clean=1.,locf=0.,observed=1.))
            self.assertEqual(row['contrasts']['observed_minus_locf']['percentile_95_interval'],[1.,1.])
            self.assertEqual(row['contrasts']['observed_minus_clean']['percentile_95_interval'],[0.,0.])
            self.assertTrue(row['noninferior_to_clean'])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AuditChecks))
    record=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,
                audit_source_sha256=hashlib.sha256(pathlib.Path(audit.__file__).read_bytes()).hexdigest(),numpy=np.__version__)
    if len(sys.argv)>1:pathlib.Path(sys.argv[1]).write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record));raise SystemExit(0 if result.wasSuccessful() else 1)
