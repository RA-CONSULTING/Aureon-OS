"""Supplemental decision/structure audit; never substitutes for frozen byte identity."""
import pathlib,json,math,argparse,hashlib,sys,re
import structural_audit as structural

def compare(reference,rerun):
 diagnostics=[];failures=[]
 allowed=re.compile(r'^/phase_representatives/\d+/surrogates/\d+/(selected_score|spectral_relative_error)$|^/phase_randomized_surrogate/maximum_spectral_relative_error$')
 def walk(a,b,path=''):
  if type(a)!=type(b):failures.append(path+':type');return
  if isinstance(a,dict):
   if a.keys()!=b.keys():failures.append(path+':keys');return
   for key in sorted(a):walk(a[key],b[key],path+'/'+key)
  elif isinstance(a,list):
   if len(a)!=len(b):failures.append(path+':length');return
   for i,(x,y) in enumerate(zip(a,b)):walk(x,y,path+'/'+str(i))
  elif isinstance(a,float) and (not math.isfinite(a) or not math.isfinite(b)):failures.append(path+':nonfinite')
  elif a!=b:
   if allowed.fullmatch(path) and isinstance(a,float):diagnostics.append({'path':path,'reference':a,'rerun':b,'absolute_difference':abs(a-b)})
   else:failures.append(path+':value')
 walk(reference,rerun)
 return {'exact_decision_ledger_equivalence':not failures,'failures':failures,'diagnostic_differences':diagnostics,
         'diagnostic_value_equivalence':'NOT_CLAIMED'}

def main():
 p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('--output',required=True);a=p.parse_args()
 root=pathlib.Path(a.package);ref=root/'QGITA_UCR_POSTCONFIRMATORY_ROBUSTNESS_RESULT_v2.json'
 rerun=root/'reproduced/robustness.json';stdout=root/'reproduced/robustness_stdout.json';canonical=root/'QGITA_UCR_CONFIRMATORY_RESULT_v1.json'
 report=compare(json.loads(ref.read_text()),json.loads(rerun.read_text()))
 report.update(schema='qgita-supplemental-portability-audit/v1',structural_audit=structural.audit(ref,rerun,stdout,canonical),
  frozen_byte_identity='PASS' if ref.read_bytes()==rerun.read_bytes() else 'FAIL',
  interpretation='Exact equality of decision ledgers plus recomputed structure/statistics; diagnostic score identity is not claimed. This does not amend the frozen byte-identity protocol or reverse missing-data performance results.')
 report['status']='SUPPLEMENTAL_AUDIT_PASS' if report['exact_decision_ledger_equivalence'] else 'FAIL'
 report['auditor_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
 pathlib.Path(a.output).write_text(json.dumps(report,indent=2))
 print(json.dumps({k:v for k,v in report.items() if k!='diagnostic_differences'},indent=2))
 if report['failures']:raise SystemExit(1)
if __name__=='__main__':main()
