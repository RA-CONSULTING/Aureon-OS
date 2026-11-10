import copy
from portability_audit import compare
base={'seed':123,'decision':True,'phase_representatives':[{'surrogates':[{'selected_score':1.,'spectral_relative_error':1e-10,'ucr_localisation':True}]}]}
assert compare(base,base)['exact_decision_ledger_equivalence']
changed=copy.deepcopy(base);changed['phase_representatives'][0]['surrogates'][0]['selected_score']+=1e-12
assert compare(base,changed)['exact_decision_ledger_equivalence']
assert compare(base,changed)['diagnostic_value_equivalence']=='NOT_CLAIMED'
for key,value in [('seed',124),('decision',False)]:
 changed=copy.deepcopy(base);changed[key]=value
 assert not compare(base,changed)['exact_decision_ledger_equivalence']
changed=copy.deepcopy(base);changed['phase_representatives'][0]['surrogates'][0]['ucr_localisation']=False
assert not compare(base,changed)['exact_decision_ledger_equivalence']
changed=copy.deepcopy(base);changed['phase_representatives'][0]['surrogates'][0]['selected_score']=float('nan')
assert not compare(base,changed)['exact_decision_ledger_equivalence']
changed=copy.deepcopy(base);changed['phase_representatives'][0]['surrogates'].append({})
assert not compare(base,changed)['exact_decision_ledger_equivalence']
print('PASS: identity, decision mutation, seed mutation, missing/extra entries, nonfinite diagnostics, reported numerical differences')
