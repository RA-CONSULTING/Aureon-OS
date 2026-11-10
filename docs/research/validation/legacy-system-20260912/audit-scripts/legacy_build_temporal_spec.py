from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'outputs'
audit = json.loads((OUT/'legacy-system-integrated-audit-20260912.json').read_text(encoding='utf-8'))
movements = [
    ('authority', 'Authority', 'I am the last qualified practitioner.'),
    ('temporal_depth', 'Temporal depth', 'This place is older than us.'),
    ('system', 'The system', 'Alphabet, cipher protocol and visual key read together.'),
    ('treasure', 'Treasure', 'The treasure is the system itself.'),
    ('warning', 'Warning', 'Do not enter alone.'),
    ('invitation', 'Invitation', 'The search is unfinished.'),
]
paragraphs = [dict(id=key, title=title, author_interpretation=meaning,
                   source='dormant_seed', section='2.3', order=i,
                   literal_translation_verified=False)
              for i, (key,title,meaning) in enumerate(movements,1)]
clocks = [
    dict(id='daily', fields=['utc','site_longitude','apparent_solar_time','light_source'],
         role='Physical illumination and observer visibility'),
    dict(id='annual', fields=['calendar','year','day_origin','day_index_convention','leap_rule','seasonal_event'],
         role='Annual recurrence, including dark and non-alignment periods'),
    dict(id='reading_frame', fields=['frame_id','rotation_deg','rotation_direction','north_reference'],
         role='Keep constructed Samhain/equinox projection separate from physical azimuth'),
    dict(id='calendar_month', fields=['calendar_source','month','intercalation_rule'],
         role='Keep Coligny, tree-calendar and alphabet wheels distinct'),
    dict(id='metonic', fields=['cycle_epoch','year_in_cycle','lunar_phase'],
         role='Nineteen-year comparison; cycle epoch has not been recovered'),
    dict(id='lunar_nodal', fields=['ascending_node','declination','ephemeris'],
         role='Separate approximately 18.6-year lunar geometry when lunar light is in scope'),
    dict(id='historical_epoch', fields=['epoch','sky_model','horizon_version','restoration_state','source_date'],
         role='Separate building, carving, preservation and reader contexts'),
]
nodes = [
    dict(id='practitioners', sources=['full_story','atlantic_substrate','people_of_threshold'],
         role='Proposed carriers of integrated observation, calendar, performance and memory'),
    dict(id='durable_archive', sources=['dormant_seed'], role='Chamber and marks proposed to preserve the account'),
    dict(id='time_light', sources=['pattern_recognition','people_of_threshold'], role='Recurring reference and proposed selection conditions'),
    dict(id='two_channels', sources=['dormant_seed'], role='Group and position; caller and response hypothesis'),
    dict(id='passages', sources=['dormant_seed'], role='Six-movement integrated interpretation'),
    dict(id='later_reader', sources=['dormant_seed','full_story'], role='Recovery by simultaneous cross-reference across time'),
    dict(id='hnc', sources=['hnc_grand_framework'], role='Corpus model of oscillation, observing integration and retained state'),
]
edges = [
    ('practitioners','durable_archive','Proposed preservation after disruption','dormant_seed','3, 5'),
    ('time_light','durable_archive','Solstice reference and constructed calendar addressing','pattern_recognition','3, 5'),
    ('durable_archive','two_channels','Marks carry proposed paired encoding','dormant_seed','1.2, 2.1'),
    ('two_channels','passages','Proposed cross-inscription reading','dormant_seed','2.3'),
    ('passages','later_reader','Invitation and across-time interpretation','dormant_seed','2.2, 2.3'),
    ('later_reader','practitioners','Proposed recovery of inherited practice','full_story','6'),
    ('hnc','later_reader','Interpretive temporal integration and memory','hnc_grand_framework','1.1; reference 23'),
]
spec = dict(
    schema='legacy-system-temporal-spec/v1', date='2026-09-12',
    state='SPECIFIED_WITH_UNRESOLVED_OBSERVATION_BINDINGS',
    purpose='Test whether time-dependent paired readings produce the proposed ordered account as an integrated whole.',
    historical_validation=False, executable_historical_run_ready=False,
    source_registry=audit['selected_sources'],
    narrative_arc=['origin','transmission','integration','fragmentation','dispersion','recovery'],
    narrative_arc_source=dict(id='full_story',section='Introduction and Parts 1-6',status='author synthesis'),
    paragraphs=paragraphs, clocks=clocks,
    graph=dict(nodes=nodes, edges=[dict(origin=a,target=b,relation=c,source=d,section=e,
                                      status='source-backed author proposition; not independently validated historical edge')
                                  for a,b,c,d,e in edges]),
    base_contact=dict(status='GEOMETRIC_REFERENT_UNRESOLVED', source='user clarified integrated legacy-system scope',
                      required_fields=['surface_id','contact_position_xyz','coordinate_frame','time','light_source',
                                       'visibility_rule','observer_position','uncertainty','source_receipt'],
                      selected_surface=None),
    historical_clock_epoch=None,
    physical_observations=[],
    time_to_mark_bindings=[],
    mark_to_passage_rules=[],
    explicit_paper_projections=[
        dict(source='pattern_recognition',section='5',day=322,year_days=365,angle_deg=317.5890410958904,
             sector='NW',passage='T-NW treasure pointer',type='constructed calendar projection',
             physical_illumination_verified=False,wall_assignment_reconciled=False),
        dict(source='pattern_recognition',section='5',day=144,year_days=365,angle_deg=142.02739726027397,
             sector='SE',passage='Nr.20 master-carver certification',type='constructed calendar projection',
             physical_illumination_verified=False,wall_assignment_reconciled=False)],
    blocking_evidence=[
        'Base-contact surface and observation-to-mark geometry',
        'Complete inscription population and reconciliation of competing wall assignments',
        'RTI/physical branch readings with uncertainty and explicit cipher conventions',
        'Fixed source-linked mark-to-passage rules and order at different times',
        'Calendar indexing, reading-frame transform and nineteen-year cycle epoch',
        'Chamber and horizon survey, ephemeris/version and historical restoration alternatives'],
    experiment_design=dict(
        stage='Development specification; not a claim of retrospective preregistration',
        primary_target='Full predicted ordered passage sequence and its change between held-out time windows',
        scoring_rule='Must be frozen after input recovery and before held-out observations are inspected; no numeric pass threshold is inferred from legacy gamma.',
        analysis_unit='Independent observed time window or separately acquired inscription reading; calendar bins and copied manuscripts are not independent witnesses.',
        coverage=['Daily visible and dark intervals','Complete annual cycle including both solstices and equinoxes',
                  'Nineteen complete solar years with retained lunar phase',
                  'Separate lunar nodal coordinate where used','Historical frame comparison at documented epochs'],
        controls=['Shifted times','Rotated reading frame','Swapped twig channels','Shuffled passage order',
                  'Alternative admissible wall inventories','Geometry/restoration sensitivity'],
        controls_policy='Same parameter/search freedom for target and controls; preserve dependence and correct for tried alternatives.',
        compute_gate='Recover source bindings and reproduce measured illumination in a pilot before larger scheduling.',
        invalid_input_behavior='Return TIMED_READING_UNRESOLVED with missing links; never fill unknown paragraphs from the desired story.'),
    parameter_roles=[
        dict(source='hnc_grand_framework',section='1.1',symbol='beta',value=0.25,role='echo gain',delay=10,delay_units='samples'),
        dict(source='author correction and prior HNC campaign',symbol='beta',value=1,role='separately tested recurrence instability parameter',
             rule='Do not conflate with the echo-gain role or convert samples to years without a declared model.')],
    audit_reference='legacy-system-integrated-audit-20260912.json')
ids = {s['id'] for s in spec['source_registry']}
assert len(ids) == 7 and len(paragraphs) == 6 and len(clocks) == 7
assert all(s in ids for node in nodes for s in node['sources'])
assert all(e['source'] in ids for e in spec['graph']['edges'])
assert not spec['executable_historical_run_ready'] and not spec['physical_observations']
assert spec['historical_clock_epoch'] is None
path = OUT/'legacy-system-temporal-spec-v1.json'
path.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(sources=len(ids),paragraphs=len(paragraphs),clock_dimensions=len(clocks),
                     graph_edges=len(edges),state=spec['state'])))
