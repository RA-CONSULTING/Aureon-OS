"""Separately labelled whole-shard operational replication sensitivity."""
from __future__ import annotations
import argparse, collections, csv, datetime, json, subprocess, sys
from pathlib import Path
import numpy as np
from stage1_v2_audit import audit_block, records, save, sha
from stage1_v2_evaluation_analysis import planned_statistics


def analyse(pack, run, oldroot, oldanalysis, recoverypack):
    for directory, manifest in [(pack, 'inputs.sha256'), (recoverypack, 'recovery.sha256')]:
        for line in (directory / manifest).read_text().splitlines():
            digest, name = line.split('  ', 1); assert sha(directory / name) == digest
    assert sha(pack / 'inputs.sha256') == 'cafd48d0c4abeedfc2c832c5aefa56c4aaba45a6252f47dad3b5c3dec0885504'
    assert sha(recoverypack / 'recovery.sha256') == 'd4213bd2a9df14a75196344a4e584a29d17332a8fcc16b867a9cff93bdb9ac4b'
    for line in (oldanalysis.parent / 'results.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1); assert sha(oldanalysis.parent / name) == digest
    original = json.loads(oldanalysis.read_text()); assert original['evidence_integrity'] == 'PASS'
    assert original['transport_failures'] == 39484 and original['final_request_records'] == 184320
    original_hash = sha(oldanalysis)
    before = {str(p.relative_to(run)).replace('\\', '/'): sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
    for line in (run / 'results.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1); assert sha(run / name) == digest
    assert json.loads((run / 'exit.json').read_text())['batch_exit_code'] == 0
    assert (run / 'completed_utc.txt').exists()
    assert (run / 'inputs.sha256').read_bytes() == (pack / 'inputs.sha256').read_bytes()
    assert (run / 'recovery.sha256').read_bytes() == (recoverypack / 'recovery.sha256').read_bytes()
    cache = json.loads((run / 'cache-ready.json').read_text())
    assert cache['filesystem'] == 'tmpfs' and cache['runtime_rank_paths_checked']
    assert sorted(Path(p).name for p in cache['rank_cache_paths']) == ['rank_'+str(i)+'_0' for i in range(4)]
    assert all(str(p).startswith(cache['cache_base'] + '/') for p in cache['rank_cache_paths'])
    guards = {}
    for name in ['pilot', 'evaluation']:
        events = list(records(run / (name + '-service-watch.jsonl')))
        assert events[0]['event'] == 'guard_start' and events[-1]['event'] == 'client_exit' and events[-1]['returncode'] == 0
        assert not any(e['event'].startswith('service_') for e in events)
        checks = [e for e in events if e['event'] == 'health_check']
        guards[name] = dict(health_checks=len(checks), failed_checks=sum(not e['healthy'] for e in checks), final_returncode=0)
    assert (run / 'vllm-version.txt').read_text().strip().splitlines()[-1] == '0.15.1'
    assert 'b5c939de8f754692c1647ca79fbf85e8c1e70f8a' in json.loads((run / 'model-files.json').read_text())['snapshot']
    pilots = [audit_block(run / 'preflight' / ('pilot-'+str(i)+'-c'+str(c)), pack) for i, c in enumerate([32,128,128,32])]
    assert sum(x['responses'] for x in pilots) == 7680 and all(x['summary']['transport_failures'] == 0 and x['unresolved_attempts'] == 0 for x in pilots)
    sys.path.insert(0, str(pack)); from fixtures import FAMILIES; from run_benchmark import plan
    contexts = json.loads((pack / 'contexts.json').read_text())['contexts']
    evaluation = list(records(pack / 'evaluation.jsonl'))
    rows = [r for r in evaluation if (r['instance'] // 2) % 4 == 0]
    newblock = run / 'evaluation-000'
    assert json.loads((newblock / 'plan.json').read_text()) == plan(rows, contexts, 2, 91300)
    newaudit = audit_block(newblock, pack)
    assert newaudit['responses'] == 46080 and newaudit['unresolved_attempts'] == 0
    newresults = {r['key']: r for r in records(newblock / 'results.jsonl')}
    counts = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    arms = collections.defaultdict(collections.Counter); keys = set(); audits = [newaudit]
    original_success = {}; original_sources = {}
    for i in range(4):
        name = 'evaluation-6502171_' + str(i); oldrun = oldroot / name
        hashes = original['source_file_hashes'][name]
        assert {str(p.relative_to(oldrun)).replace('\\', '/') for p in oldrun.rglob('*') if p.is_file()} == set(hashes)
        for relative, digest in hashes.items(): assert sha(oldrun / relative) == digest, (name, relative)
        original_sources[name] = hashes
        oldblock = oldrun / ('evaluation-' + str(i).zfill(3))
        if i == 0:
            original_success = {r['key']: r for r in records(oldblock / 'results.jsonl') if r['transport_ok']}
            block = newblock; audited = newaudit
        else:
            block = oldblock; audited = original['per_shard_audits'][i]; audits.append(audited)
        for r in records(block / 'results.jsonl'):
            assert r['key'] not in keys; keys.add(r['key'])
        for template, aa in audited['template_joint_counts'].items():
            for arm, count in aa.items(): counts[template][arm].update(count)
        for arm, count in audited['arms'].items(): arms[arm].update(count)
    assert keys == {r['key'] for r in plan(evaluation, contexts, 2, 0)} and len(keys) == 184320
    armnames = sorted(arms); values = np.zeros((10,6,24)); assert len(armnames) == 24
    for fi, family in enumerate(FAMILIES):
        templates = sorted(t for t in counts if t.startswith(family + '/')); assert len(templates) == 6
        for ti, template in enumerate(templates):
            for ai, arm in enumerate(armnames):
                count = counts[template][arm]; assert count['n'] == 128
                values[fi,ti,ai] = count['sum'] / count['n']
    comparison = collections.Counter()
    assert len(original_success) == 6596
    for key, old in original_success.items():
        new = newresults[key]; comparison['matched_original_successful_requests'] += 1
        comparison['same_score_record'] += old['score'] == new['score']
        comparison['old_joint_correct'] += old['score']['joint_correct']
        comparison['new_joint_correct'] += new['score']['joint_correct']
        comparison['joint_gain'] += not old['score']['joint_correct'] and new['score']['joint_correct']
        comparison['joint_loss'] += old['score']['joint_correct'] and not new['score']['joint_correct']
        comparison['new_transport_failures'] += not new['transport_ok']
    after = {str(p.relative_to(run)).replace('\\', '/'): sha(p) for p in sorted(run.rglob('*')) if p.is_file()}
    assert before == after and sha(oldanalysis) == original_hash
    return dict(schema='stage1-v2-operational-replication-sensitivity/v1', evidence_integrity='PASS',
                analysis_label='New whole-shard 0 plus original healthy shards 1-3; operational replication sensitivity',
                original_first_run_preserved=True, original_first_run_analysis_sha256=original_hash,
                first_run_transport_failures_unchanged=39484, input_manifest_sha256=sha(pack / 'inputs.sha256'),
                recovery_manifest_sha256=sha(recoverypack / 'recovery.sha256'),
                recovery_final_requests=46080, recovery_transport_failures=newaudit['summary']['transport_failures'],
                recovery_invalid_model_outputs=46080-newaudit['summary']['transport_failures']-newaudit['summary']['schema_valid'],
                combined_final_requests=184320, combined_transport_failures=sum(x['summary']['transport_failures'] for x in audits),
                combined_invalid_model_outputs=sum(x['responses']-x['summary']['transport_failures']-x['summary']['schema_valid'] for x in audits),
                family_order=list(FAMILIES), analysis=planned_statistics(values, armnames),
                arm_counts={k:dict(v) for k,v in arms.items()}, per_shard_audits=audits, pilot_audits=pilots,
                service_guards=guards, cache_proof=cache, repeated_original_successful_requests=dict(comparison),
                recovery_source_hashes=before, original_source_hashes_reverified=original_sources,
                interpretation='Conditional synthetic authored-template evidence. This replication does not replace the degraded primary first run, prove full live-OS performance, or validate the physical/historical theory.')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--pack', required=True); p.add_argument('--run', required=True)
    p.add_argument('--oldroot', required=True); p.add_argument('--oldanalysis', required=True)
    p.add_argument('--recoverypack', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); out = Path(a.output); out.mkdir(parents=True, exist_ok=False)
    accounting = subprocess.check_output(['sacct','-j','6503592','--format=JobID,State,ExitCode,ElapsedRaw,AllocNodes,AllocTRES','-P'], text=True)
    jobs = {r['JobID']:r for r in csv.DictReader(accounting.splitlines(), delimiter='|')}
    assert jobs['6503592']['State'] == 'COMPLETED' and jobs['6503592']['ExitCode'] == '0:0'
    (out / 'accounting.psv').write_text(accounting)
    result = analyse(Path(a.pack), Path(a.run), Path(a.oldroot), Path(a.oldanalysis), Path(a.recoverypack))
    result.update(audit_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), analysis_source_sha256=sha(__file__),
                  recovery_accounting=jobs, recovery_allocated_node_hours=int(jobs['6503592']['ElapsedRaw']) / 3600)
    save(out / 'analysis.json', result)
    (out / 'results.sha256').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps({k:result[k] for k in ['evidence_integrity','recovery_final_requests','recovery_transport_failures','recovery_invalid_model_outputs','combined_final_requests','combined_transport_failures','combined_invalid_model_outputs','repeated_original_successful_requests']}, indent=2))

if __name__ == '__main__': main()
