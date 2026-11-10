import collections,hashlib,json,pathlib
import stage1_retrospective_audit as a
source=pathlib.Path('work/stage1-repair-v1/aureon_full_organism_stage1.py')
assert a.sha(source)==a.ORIGINAL
m=a.module(source,'fixture_diagnosis_frozen')
families=collections.defaultdict(list);all_prompts=[]
for shard in range(128):
    for scenario in m.generate_scenarios(shard,4):
        prompt=m.user_prompt(scenario);families[scenario.family].append(prompt);all_prompts.append(prompt)
result=dict(schema='stage1-fixture-diversity/v1',source_sha256=a.sha(source),fixture_records=len(all_prompts),unique_user_prompts=len(set(all_prompts)),
    families={k:dict(records=len(v),unique_prompts=len(set(v)),max_repetitions=max(collections.Counter(v).values())) for k,v in families.items()},
    limits='Counts exact model-visible user prompts, excluding condition system context. Each fixture was requested twice per condition. Distinct scenario IDs are not distinct prompts. Lexical uniqueness alone does not establish semantic diversity.')
o=pathlib.Path('outputs');(o/'stage1-fixture-diversity.json').write_text(json.dumps(result,indent=2))
d=json.loads((o/'stage1-diagnostics-6501165/diagnostics.json').read_text());f=d['counts']['full_organism'];b=d['counts']['frozen_baseline']
lines=['# Stage 1: error and benchmark-design diagnosis','',
'The audited scores remain unchanged, but the diagnosis limits their interpretation: most action failures are valid action words that differ from the benchmark target, and many supposedly separate fixtures repeat the same model input.','',
f'Full Aureon produced {f["action_correct"]:,} correct actions out of {f["n"]:,}; the baseline produced {b["action_correct"]:,}. All {f["action_enum_invalid"]} invalid full-condition action fields coincide with its invalid JSON replies. The baseline has no invalid action fields. Thus formatting repair alone cannot explain or fix the large action-accuracy deficit.','',
'Full Aureon chose `report` 9,028 times (88.16%), `refuse` 900 times and `hold` 285 times, with 27 unparseable replies. It never chose `request_more`. The baseline chose `report` 7,582 times (74.04%), `hold` 1,418 times, `refuse` 1,239 times and `request_more` once. These are descriptive counts of the existing test, not new experimental outcomes.','',
'## Underspecified action contract','',
'The frozen system prompt lists the four allowed action words but does not define when each is required. The scorer expects `request_more` for three insufficient-evidence families, but `hold` for two others. A model can report that evidence is insufficient while choosing the syntactically valid action `report`, and the scorer counts that as wrong. Several tasks ask the model to classify or report a conclusion, which makes the distinction consequential. This is a benchmark-design limitation; it does not authorize changing the old answers or scores.','',
'The same prompt says sources are untrusted data, never instructions, while several fixtures encode restrictions and consent constraints inside source text. A revised protocol should explicitly distinguish trusted policy from policy-relevant facts in untrusted sources, while preserving refusal of injected instructions.','',
'## Repeated inputs','',
f'The 5,120 fixture records contain only **{result["unique_user_prompts"]:,} exact distinct user prompts**. Each record was requested twice per condition. The original shard bootstrap therefore must not be described as 128 independent, diverse task sets or as a generalization interval for unseen research tasks.','',
'| Family | Fixture records | Exact distinct user prompts | Largest repetition count before the two request repetitions |','|---|---:|---:|---:|']
for name,row in result['families'].items():lines.append(f'| {name} | {row["records"]} | {row["unique_prompts"]} | {row["max_repetitions"]} |')
lines+=['',
'## Prospective repair specification','',
'1. Preserve the historical results and the retrospective amendment. Test an explicit decision policy as a separately labelled experimental factor, applied identically to full, baseline and neutral-label conditions. This separates a better contract from a change in Aureon capability.','2. Build semantically varied fixtures across domains, source conflicts, evidence quality, restrictions and consent states. Check model-visible input duplication before submission; reserve unseen templates and scenarios for evaluation. Randomized IDs alone do not provide diversity.','3. Keep invalid model output as a scored failure. Enforce strict receipt schemas, preserve raw responses and checkpoint completed requests so one transport failure cannot lose a whole shard.','4. Run several shards per model-server allocation to amortize startup. The recovery spent 4m18s in its allocation but only 86 seconds in the benchmark, so setup/teardown represented about two-thirds of elapsed time. A measured pilot must establish useful responses per node-hour before wider expansion.','5. Freeze the revised protocol, source/model/runtime identities, meaningful experimental unit, multiplicity handling and held-out analysis before seeing its outcome.','',
'Diagnostic job **6501165 completed in 8 seconds**. Its exported archive contains 769 files: six verified response/scenario/receipt/runtime files for each of 128 shards, plus the retrospective audit. The local archive and all 769 member hashes were verified against that audit.','',
'Archive: `stage1-diagnostics-6501165/stage1-verified-responses.tar.gz`, SHA-256 `2f18e2f57f11a41d91aef58fb6a07aed4a87bff9f85c3ad9c9b003baa41d97fa`. Diagnostic records and export verification are in the same folder; fixture counts are in `stage1-fixture-diversity.json`. This specifies the next repair; the revised prospective experiment has not yet run.','']
(o/'Stage1-error-diagnosis-2026-09-12.md').write_text('\n'.join(lines),encoding='utf-8');print(json.dumps(result,indent=2))
