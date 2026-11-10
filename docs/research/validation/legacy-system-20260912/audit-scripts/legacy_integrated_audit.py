"""Read-only corpus and calendar capability audit; never imports trading code."""
from pathlib import Path
import ast
import collections
import datetime as dt
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs'
INDEX = json.loads((OUT / 'git-research-source-index.json').read_text(encoding='utf-8'))
SELECTED = {
    'dormant_seed': '189bdc0dd4d8303a47cbbeaf473fa7161962197e',
    'full_story': '559088232b07d58eb805826512dea7ea1c00221f',
    'atlantic_substrate': '470fe715c9add37ef8d1f61a36fa4ad395b577a0',
    'from_a_to_b': '6a76d2415c2c3cf0081a136291db4fce4ada0cc7',
    'people_of_threshold': 'f85954729805568b84e2050d05b07d1d581fa2a3',
    'pattern_recognition': '76753aedea8fff1cf1a3b3756c2b0392c1e3735a',
    'hnc_grand_framework': 'ea4ae92ffd8e7f6d0fe548a0fa00d935ec28ffbe',
}
by_blob = {e['blob']: e for e in INDEX['entries']}
sources = []
for key, blob in SELECTED.items():
    e = by_blob[blob]
    matches = list((ROOT / 'work/research-history').glob(blob + '.*'))
    native = [p for p in matches if p.suffix.lower() in ('.docx', '.pdf')]
    assert len(native) == 1, (blob, native)
    data = native[0].read_bytes()
    assert hashlib.sha256(data).hexdigest() == e['sha256']
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob
    sources.append(dict(id=key, blob=blob, sha256=e['sha256'],
                        paths=e['all_paths'], first_commit=e.get('first_content_commit'),
                        local_native=str(native[0]), provenance_verified=True))

light_base_hits = []
reviewed = 0
for e in INDEX['entries']:
    p = ROOT / 'work/research-history' / (e['blob'] + '.extracted.json')
    if not p.exists():
        continue
    obj = json.loads(p.read_text(encoding='utf-8'))
    txt = obj.get('full_text', obj.get('text', ''))
    if not txt:
        pages = obj.get('pages', obj.get('parts', []))
        txt = '\n'.join(page.get('text', '') for page in pages)
    if not txt:
        continue
    reviewed += 1
    for line_number, line in enumerate(txt.splitlines(), 1):
        if (re.search(r'light|illumina|solstice|sunlight', line, re.I)
                and re.search(r'\bbase\b|paragraph|spoken|nineteen|19.year', line, re.I)):
            light_base_hits.append(dict(blob=e['blob'], paths=e['all_paths'],
                                       line=line_number, text=line))

assert reviewed == len(INDEX['entries']), ('Incomplete discovery scan', reviewed, len(INDEX['entries']))
code_path = ROOT / 'work/legacy-system-review/code/celtic_ogham.py'
tree = ast.parse(code_path.read_text(encoding='utf-8'))
calendar = []
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'TreeMonth':
        a = [ast.literal_eval(x) for x in node.args]
        kw = {x.arg: ast.literal_eval(x.value) for x in node.keywords}
        calendar.append(dict(month=a[0], name=a[1], start_day=a[3], hz=a[4],
                             decoded=a[5], line=node.lineno, **kw))
decoder = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'CelticOghamDecoder')
read = next(x for x in decoder.body if isinstance(x, ast.FunctionDef) and x.name == 'read')
start_refs = [x.lineno for x in ast.walk(read) if isinstance(x, ast.Attribute) and x.attr == 'start_day']
input_parameters = [x.arg for x in read.args.args if x.arg != 'self']
calls = [ast.unparse(x.func) for x in ast.walk(read) if isinstance(x, ast.Call)]
duplicates = {str(day): [m['month'] for m in calendar if m['start_day'] == day]
              for day, n in collections.Counter(m['start_day'] for m in calendar).items() if n > 1}

wall_centres = {'NE': 45., 'SE': 135., 'SW': 225., 'NW': 315.}
def projection(day, period):
    angle = day / period * 360. % 360.
    distance = lambda v: abs((angle - v + 180.) % 360. - 180.)
    return dict(day=day, year_days=period, angle_deg=angle,
                closest_walls=[k for k, v in wall_centres.items()
                               if abs(distance(v) - min(map(distance, wall_centres.values()))) < 1e-9])

endpoints = []
for year in (2025, 2026, 2027):
    start, end = dt.date(year, 11, 1), dt.date(year + 1, 11, 1)
    period = (end - start).days
    for name, date in [('last_light_paper_date', dt.date(year + 1, 3, 25)),
                       ('first_light_paper_date', dt.date(year + 1, 9, 18))]:
        day = (date - start).days
        endpoints.append(dict(event=name, date=date.isoformat(), origin=start.isoformat(),
                              zero_based_day=day, actual_calendar=projection(day, period),
                              one_based_comparison=projection(day + 1, period)))

result = dict(schema='legacy-integrated-audit/v1', source_count_scanned=reviewed,
              selected_sources=sources, light_base_time_passages=light_base_hits,
              existing_calendar=dict(file=str(code_path), sha256=hashlib.sha256(code_path.read_bytes()).hexdigest(),
                                     months=calendar, duplicate_starts=duplicates,
                                     starts_outside_documented_day_of_year=[m['month'] for m in calendar if m['start_day'] > 366],
                                     read_parameters=input_parameters, read_start_day_references=start_refs,
                                     read_calls=calls, timestamp_is_output_metadata=True,
                                     conclusion='Static aggregate; no supplied observation time, light geometry, or paragraph selection in read().'),
              wheel_checks=dict(classification='Constructed calendar projection, not a physical solar azimuth simulation.',
                                paper_days=[projection(322, 365), projection(144, 365)],
                                reported_angles=[317.6, 142.0], date_conventions=endpoints,
                                chronological_binding_to_maeshowe_passages='UNRESOLVED'),
              limitations=['No temporal decipherment is inferred from corpus co-occurrence.',
                           'Seven selected native sources were byte-verified; the 180-text scan is discovery coverage, not independent validation of all claims.',
                           'No named /home/claude/celtic wheel-generation scripts recovered in the completed path scan.',
                           'No independently observed light-to-mark-to-paragraph binding is supplied.'])
target = OUT / 'legacy-system-integrated-audit-20260912.json'
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps(dict(scanned=reviewed, selected_native_hashes_verified=len(sources),
                     light_base_time_passages=len(light_base_hits), duplicate_calendar_starts=duplicates,
                     calendar_read_time_parameters=input_parameters, start_day_references=start_refs,
                     reported_day_projections=result['wheel_checks']['paper_days']), indent=2))
print('LIGHT_BASE_CONTEXTS')
for hit in light_base_hits:
    if re.search(r'\bbase\b', hit['text'], re.I):
        print(json.dumps(dict(blob=hit['blob'], line=hit['line'], text=hit['text'][:500]), ensure_ascii=False))
