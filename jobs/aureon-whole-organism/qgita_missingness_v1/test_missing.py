import hashlib,json,pathlib,sys,unittest
import numpy as np
import qgita_missing as candidate
import audit_qgita_ucr_robustness as legacy


class MissingChecks(unittest.TestCase):
    def setUp(self):
        self.x=np.random.default_rng(731).normal(size=1100);self.train=700
        self.scales=legacy.training_scales(self.x,self.train);self.clear=np.zeros(len(self.x),dtype=bool)

    def test_clean_bitwise_original(self):
        actual=candidate.score_bank(self.x,self.clear,self.train,self.scales)['scores']
        self.assertTrue(np.array_equal(actual,legacy.qgita_scores_with_scales(self.x,self.train,self.scales),equal_nan=True))

    def test_masked_values_cannot_change_output(self):
        mask=legacy.mcar_mask(len(self.x),self.train,.2,np.random.default_rng(71))
        a=self.x.copy();a[mask]=np.nan;b=self.x.copy();b[mask]=1e100
        left=candidate.score_bank(a,mask,self.train,self.scales)
        right=candidate.score_bank(b,mask,self.train,self.scales)
        for key in left:self.assertTrue(np.array_equal(left[key],right[key],equal_nan=True))

    def test_independent_scalar_oracle(self):
        mask=legacy.mcar_mask(len(self.x),self.train,.2,np.random.default_rng(11))
        bank=candidate.score_bank(self.x,mask,self.train,self.scales)
        for decision in range(self.train,len(self.x)):
            values=[]
            for offset,k in enumerate(range(1,len(legacy.LATTICE)-1)):
                p,c,s=map(int,legacy.LATTICE[k-1:k+2]);start=decision-s
                if start<0 or any(mask[i] for i in [start+p,start+c,decision]):continue
                hm=c-p;hp=s-c
                value=abs(2./(hm+hp)*((self.x[decision]-self.x[start+c])/hp-(self.x[start+c]-self.x[start+p])/hm))/self.scales[offset]
                values.append(value)
            i=decision-self.train
            self.assertEqual(bank['eligible_components'][i],len(values))
            if values:self.assertAlmostEqual(bank['scores'][i],max(values),places=12)
            else:self.assertTrue(np.isnan(bank['scores'][i]))

    def test_prefix_causality(self):
        mask=legacy.mcar_mask(len(self.x),self.train,.1,np.random.default_rng(12))
        full=candidate.score_bank(self.x,mask,self.train,self.scales)
        prefix=candidate.score_bank(self.x[:900],mask[:900],self.train,self.scales)
        for key in full:self.assertTrue(np.array_equal(full[key][:200],prefix[key],equal_nan=True))

    def test_no_evidence_abstains(self):
        mask=self.clear.copy();mask[self.train:]=True
        bank=candidate.score_bank(self.x,mask,self.train,self.scales)
        result=candidate.select(bank,self.train,800,850)
        self.assertTrue(result['abstained']);self.assertIsNone(result['selected_index_zero_based'])
        self.assertFalse(result['ucr_localisation']);self.assertEqual(result['scoreable_fraction'],0.)

    def test_tie_rule_earliest(self):
        bank=candidate.score_bank(np.ones(len(self.x)),self.clear,self.train,np.ones(len(legacy.LATTICE)-2))
        result=candidate.select(bank,self.train,800,850)
        self.assertEqual(result['selected_index_zero_based'],self.train)

    def test_control_and_imputed_attribution(self):
        mask=legacy.mcar_mask(len(self.x),self.train,.1,np.random.default_rng(31));filled=legacy.locf(self.x,mask)
        bank=candidate.score_bank(filled,mask,self.train,self.scales,require_observed=False)
        self.assertTrue(np.array_equal(bank['scores'],legacy.qgita_scores_with_scales(filled,self.train,self.scales),equal_nan=True))
        observed=candidate.score_bank(self.x,mask,self.train,self.scales)
        result=candidate.select(observed,self.train,800,850)
        self.assertFalse(candidate.selected_triplet(observed,result,mask,self.train)['contains_imputed_value'])

    def test_invalid_inputs_rejected(self):
        mask=self.clear.copy();mask[10]=True
        with self.assertRaises(ValueError):candidate.score_bank(self.x,mask,self.train,self.scales)
        with self.assertRaises(ValueError):candidate.score_bank(self.x,self.clear.astype(int),self.train,self.scales)
        with self.assertRaises(ValueError):candidate.score_bank(self.x,self.clear,self.train,np.zeros_like(self.scales))
        values=self.x.copy();values[750]=np.nan
        with self.assertRaises(ValueError):candidate.score_bank(values,self.clear,self.train,self.scales)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(MissingChecks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,numpy=np.__version__,
                source_sha256=hashlib.sha256(pathlib.Path(candidate.__file__).read_bytes()).hexdigest(),test_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
    if len(sys.argv)>1:pathlib.Path(sys.argv[1]).write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record));raise SystemExit(0 if result.wasSuccessful() else 1)
