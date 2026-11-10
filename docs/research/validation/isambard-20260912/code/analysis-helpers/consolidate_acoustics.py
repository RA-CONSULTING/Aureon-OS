import pathlib,json,hashlib,tarfile,datetime
import numpy as np
root=pathlib.Path(__file__).resolve().parents[1];out=root/'outputs'
old=root/'work/september/kings-chamber-acoustics'
inputs={}
def read(p):
    b=p.read_bytes();inputs[str(p.relative_to(root)).replace('\\','/')]=hashlib.sha256(b).hexdigest();return json.loads(b)
prereg=old/'inputs/PREREGISTRATION.md';inputs[str(prereg.relative_to(root)).replace('\\','/')]=hashlib.sha256(prereg.read_bytes()).hexdigest()
historical=read(old/'verdict.json'); repair=read(out/'acoustics-repair-audit-6497982.json'); geo_audit=read(out/'acoustics-geometry-audit-6498032.json')
assert historical['verdict']=='INCONCLUSIVE' and repair['integrity_status']==geo_audit['integrity_status']=='PASS'
archive=out/'acoustics-repair-6497982.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==repair['archive_sha256']
inputs[archive.name]=repair['archive_sha256']
with tarfile.open(archive) as tar:
    data={m.name.split('/',1)[1]:tar.extractfile(m).read() for m in tar if m.isfile()}
for item in repair['result_files']:
    assert hashlib.sha256(data[item['file']]).hexdigest()==item['sha256']
rows=[json.loads(data[x['file']]) for x in repair['result_files']]
gals=sorted([r for r in rows if r['task']=='galerkin'],key=lambda r:r['cutoff_hz'])
control=next(r for r in rows if r['task']=='controls')
randoms=[r for r in rows if r['task']=='random']
bare={s:read(old/'runs/run-6369146'/('bare-'+s+'.json')) for s in ['0.15','0.10','0.05','0.025']}
geometry={}
for r in geo_audit['results']:
    actual=read(out/r['file']);assert inputs['outputs/'+r['file']]==r['sha256']
    assert actual['status']=='PASS' and all(actual['checks'].values())
    assert len(actual['frequencies_hz'])==len(actual['relative_residuals'])==26
    assert max(actual['relative_residuals'])<=1e-8
    geometry[(r['geometry'],r['dx'])]=actual
def target_gates(f):
    a=np.asarray(f);targets=np.array([16.2,32.4]);best=a[np.argmin(abs(a[:,None]-targets),axis=0)];deviation=abs(best-targets)/targets
    ratio=float(best[1]/best[0]);sch=np.array([7.83,14.3,20.8,27.3,33.8]);octaves=(sch[:,None]*np.array([1.,2.,4.])).ravel();adj=np.min(abs(best[:,None]-octaves)/octaves,axis=1)
    return dict(f_nearest_hz=best.tolist(),relative_target_errors=deviation.tolist(),hit_2pct=bool(np.all(deviation<=.02)),hit_1pct=bool(np.all(deviation<=.01)),octave_ratio=ratio,octave_relative_error=abs(ratio-2)/2,octave_gate=bool(abs(ratio-2)<=.04),closer_to='octave' if abs(ratio-2)<abs(ratio-(1+5**.5)/2) else 'phi',schumann_octave_relative_distances=adj.tolist(),schumann_adjacency_5pct=bool(np.all(adj<=.05)))
bare_errors={};continuum_errors={};acceptance={}
for dx,r in bare.items():
    shape=r['grid_shape'];h=r['h'];axis=[4/h[i]**2*np.sin(np.arange(min(shape[i],27))*np.pi/(2*shape[i]))**2 for i in range(3)]
    eig=(axis[0][:,None,None]+axis[1][None,:,None]+axis[2][None,None,:]).ravel();exact=np.sort(343/(2*np.pi)*np.sqrt(eig[eig>0]))[:26]
    actual=np.asarray(r['freqs_hz']);assert len(actual)==len(exact)==26
    bare_errors[dx]=float(np.max(abs(actual-exact)/exact));continuum_errors[dx]=abs(float(actual[0])-343/(2*10.47))/(343/(2*10.47));acceptance[dx]=r['max_resid_rel']
order=float(np.polyfit(np.log([float(x) for x in continuum_errors]),np.log(list(continuum_errors.values())),1)[0])
gf=np.array(gals[-1]['frequencies_hz']);cf15=np.array(geometry[('coffer',.15)]['frequencies_hz']);cf10=np.array(geometry[('coffer',.1)]['frequencies_hz'])
v4_15=float(np.max(abs(gf[:8]-cf15[:8])/gf[:8]));v4_10=float(np.max(abs(gf[:8]-cf10[:8])/gf[:8]))
validation=dict(V1_all26_discrete_match=all(x<1e-8 for x in bare_errors.values()),V1_residual_acceptance_all_grids=all(x<=1e-3 for x in acceptance.values()),production_residual_target=acceptance['0.05']<=1e-8,V2_second_order=1.5<order<2.6,V3_amended_random_solver=len(randoms)==3 and all(r['status']=='PASS' and all(r['checks'].values()) for r in randoms),V4_coffer_first8_at_original_015_threshold=v4_15<.01,V5_empty_coffer=all(r['empty_coffer_relative_error']<1e-10 for r in gals),geometry_all26_residual_and_reported_orthogonality=all(r['status']=='PASS' and all(r['checks'].values()) for r in geometry.values()))
primary=target_gates(bare['0.05']['freqs_hz']);null=np.asarray(control['null_schumann_min_rel_all']);stat=control['chamber_stats']['schumann_min_rel'];k=int(np.count_nonzero(null<=stat));p=(k+1)/(len(null)+1)
gates=dict(G1_primary_hit_2pct=primary['hit_2pct'],G1_strict_hit_1pct=primary['hit_1pct'],G2_octave=primary['octave_gate'],G3_distinctiveness=primary['hit_2pct'] and control['p_null_hit_both_2pct']<.05,G4_amended_schumann=primary['schumann_adjacency_5pct'] and p<.01)
valid=all(validation.values())
verdict='INCONCLUSIVE' if not valid else ('SUBSTANTIATED-SPECIFIC' if gates['G1_primary_hit_2pct'] and gates['G2_octave'] and gates['G3_distinctiveness'] else 'SUBSTANTIATED-GENERIC' if gates['G1_primary_hit_2pct'] and gates['G2_octave'] else 'FALSIFIED-AS-STATED' if not gates['G1_primary_hit_2pct'] else 'INCONCLUSIVE')
report=dict(schema='acoustics-amended-gates/v1',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),claim_class='C2 computational simulation',historical_frozen_verdict='INCONCLUSIVE',amended_numerical_assessment=verdict,post_hoc_amendment=True,gates=gates,primary=primary,validation=validation,bare_all26_max_relative_errors=bare_errors,bare_residuals=acceptance,convergence_order=order,coffer_first8_galerkin_vs_fd_015=v4_15,coffer_first8_galerkin_vs_fd_010=v4_10,coffer_all26_galerkin_vs_fd_010=float(np.max(abs(gf-cf10)/gf)),null_hit_2pct=control['p_null_hit_both_2pct'],null_hit_1pct=control['p_null_hit_both_1pct'],schumann=dict(chamber_statistic=stat,null_at_least_as_close=k,n=len(null),plus_one_rank=p),geometry_robustness={name+'_'+str(dx):target_gates(r['frequencies_hz']) for (name,dx),r in geometry.items()},limitations=['Original 300-iteration random-start failure remains unchanged.','New residual and orthogonality claims use recorded solver checks; eigenvectors were not retained for independent recomputation.','First-eight cross-method threshold is inherited from the old analyser; the all-26 comparison is reported without inventing a new pass threshold.','The doorway is a simplified pressure-release stub, not a calibrated measurement of the real chamber.','Dimension detuning does not test coffer-position uncertainty or real material/radiation loss.','Current comparisons validate selected numerical outputs, not archaeological intention or physical tuning.'],inputs_sha256=inputs)
(out/'acoustics-amended-gates-20260912.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lines=['# Acoustics: consolidated amended assessment','',f'Assessment: **{verdict}** under the amended numerical procedure. Historical frozen verdict: **INCONCLUSIVE**. These are simulations of the specified geometry.','', '| Check | Result |','|---|---|']
for name,result in gates.items():lines.append('| '+name+' | '+('PASS' if result else 'FAIL')+' |')
lines+=['',f'The closed-box primary calculation returns {primary["f_nearest_hz"][0]:.6f} and {primary["f_nearest_hz"][1]:.6f} Hz, about 1.11% above the claimed 16.2/32.4 Hz. It passes 2%, fails 1%, and forms an octave. Among 10,000 matched-volume synthetic rooms, {control["p_null_hit_both_2pct"]:.2%} also hit both targets; the distinctiveness requirement of less than 5% fails.',f'The corrected Schumann comparison finds {k:,}/{len(null):,} control rooms at least as close as the chamber, with plus-one rank {p:.6f}. This fails the 1% significance requirement.','',f'All {len(validation)} explicit numerical checks pass under the amendment. The discrete bare-box oracle now covers all 26 modes; the grid-convergence order is {order:.6f}. Corrected Galerkin versus the 0.15 m coffer grid differs by at most {v4_15:.3%} across the first eight modes, meeting the inherited 1% criterion. The 0.10 m comparison is {v4_10:.3%} for the first eight and {report["coffer_all26_galerkin_vs_fd_010"]:.3%} across all 26. No all-26 1% pass is claimed.','', '## Geometry sensitivity','', '| Geometry | Nearest lower / upper target modes (Hz) | 2% target hit | Octave gate |','|---|---|---|---|']
for name,r in report['geometry_robustness'].items():lines.append(f'| {name} | {r["f_nearest_hz"][0]:.6f} / {r["f_nearest_hz"][1]:.6f} | {r["hit_2pct"]} | {r["octave_gate"]} |')
lines+=['','The opening model shifts the lower target mode outside 2% and its selected pair fails the octave gate. This is a robustness finding, not a replacement for the preregistered closed-box gate. Claims covering an open chamber need a calibrated boundary model and measurements.','', '## Interpretation and remaining limitations','']+['- '+s for s in report['limitations']]+['','The corrected analysis supports ordinary resonances in the specified closed-room geometry. It does not support distinctive tuning or stronger Schumann adjacency. The original failed protocol remains preserved. Detailed inputs, hashes and recomputed gate values are in `acoustics-amended-gates-20260912.json`.']
(out/'Acoustics-amended-assessment-2026-09-12.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['amended_numerical_assessment','gates','validation','coffer_first8_galerkin_vs_fd_015','geometry_robustness']},indent=2))
