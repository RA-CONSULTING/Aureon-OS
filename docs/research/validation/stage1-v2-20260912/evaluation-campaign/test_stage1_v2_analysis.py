import unittest
import numpy as np
from stage1_v2_evaluation_analysis import planned_statistics,holm

ARMS=['explicit_policy|full_organism','explicit_policy|frozen_baseline','explicit_policy|neutral_labels',
      'enum_only|full_organism','enum_only|frozen_baseline']
class AnalysisChecks(unittest.TestCase):
    def test_identical_conditions_have_zero_effect(self):
        r=planned_statistics(np.full((10,6,5),.4),ARMS,draws=1000)
        for c in r['primary_contrasts'].values():
            self.assertEqual(c['estimate'],0.);self.assertEqual(c['percentile_95_interval'],[0.,0.]);self.assertEqual(c['holm_adjusted_p'],1.)
    def test_known_paired_contrast_and_interaction(self):
        v=np.zeros((10,6,5));v[:,:,0]=1;v[:,:,2]=.5;v[:,:,3]=1
        r=planned_statistics(v,ARMS,draws=1000)['primary_contrasts']
        self.assertEqual(r['full_minus_baseline_explicit']['estimate'],1.)
        self.assertEqual(r['full_minus_neutral_explicit']['estimate'],.5)
        self.assertEqual(r['full_baseline_policy_interaction']['estimate'],0.)
    def test_holm_preserves_input_order(self):
        self.assertEqual(holm([.2,.01,.03]),[.2,.03,.06])
    def test_reject_wrong_independent_unit(self):
        with self.assertRaises(ValueError):planned_statistics(np.zeros((10,384,5)),ARMS,draws=1000)

if __name__=='__main__':unittest.main(verbosity=2)
