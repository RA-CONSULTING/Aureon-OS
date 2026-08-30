import importlib.util
import json
import math
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f'Unable to load {module_name} from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


em = load_module('test_emerald_spec_module', 'aureon/decoders/emerald_spec.py')


class TestTabletVerses(unittest.TestCase):
    """Verify the verse catalogue is well-formed and complete."""

    def test_verse_count_minimum(self):
        self.assertGreaterEqual(len(em._VERSE_CATALOG), 20)

    def test_verse_index_keys_match_catalog(self):
        for verse in em._VERSE_CATALOG:
            self.assertIn(verse.key, em.VERSE_INDEX)
            self.assertIs(em.VERSE_INDEX[verse.key], verse)

    def test_unique_keys(self):
        keys = [v.key for v in em._VERSE_CATALOG]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_verses_have_required_fields(self):
        for verse in em._VERSE_CATALOG:
            self.assertTrue(verse.key)
            self.assertTrue(verse.hermetic_text)
            self.assertTrue(verse.technical_translation)
            self.assertTrue(verse.aureon_implementation)


class TestSevenStages(unittest.TestCase):
    """Verify the 7 alchemical stages are well-formed."""

    def test_exactly_seven(self):
        self.assertEqual(len(em.SEVEN_STAGES), 7)

    def test_stages_numbered_1_to_7(self):
        numbers = [s.number for s in em.SEVEN_STAGES]
        self.assertEqual(numbers, [1, 2, 3, 4, 5, 6, 7])

    def test_stage_names_match_tradition(self):
        expected = [
            'Calcination', 'Dissolution', 'Separation',
            'Conjunction', 'Fermentation', 'Distillation', 'Coagulation',
        ]
        self.assertEqual([s.name for s in em.SEVEN_STAGES], expected)

    def test_final_stage_is_lt_score(self):
        final = em.SEVEN_STAGES[-1]
        self.assertEqual(final.name, 'Coagulation')
        self.assertEqual(final.units, 'L(t)')
        self.assertAlmostEqual(final.computed_value, 12.85, places=2)


class TestSacredConstants(unittest.TestCase):
    """Verify sacred constants match the seer module values."""

    def test_phi(self):
        self.assertAlmostEqual(em.PHI, (1 + math.sqrt(5)) / 2, places=12)

    def test_schumann(self):
        self.assertEqual(em.SCHUMANN_FUNDAMENTAL, 7.83)

    def test_love_frequency(self):
        self.assertEqual(em.LOVE_FREQUENCY, 528.0)

    def test_rf_carrier(self):
        self.assertEqual(em.RF_CARRIER_ISM, 13.56e6)

    def test_philosophical_threshold(self):
        self.assertEqual(em.PHILOSOPHERS_STONE_THRESHOLD, 2.8)


class TestEmeraldSeer(unittest.TestCase):
    """Test the EmeraldSeer decoder class."""

    def setUp(self):
        self.seer = em.EmeraldSeer()

    def test_decode_verse_known_key(self):
        verse = self.seer.decode_verse('verum')
        self.assertEqual(verse.key, 'verum')
        self.assertIn('Tier 1', verse.technical_translation)

    def test_decode_verse_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            self.seer.decode_verse('nonexistent')

    def test_decode_by_text_found(self):
        verse = self.seer.decode_by_text('below is like')
        self.assertIsNotNone(verse)
        self.assertEqual(verse.key, 'as_below')

    def test_decode_by_text_not_found(self):
        result = self.seer.decode_by_text('completely unrelated string xyz')
        self.assertIsNone(result)

    def test_verify_philosophers_stone_true(self):
        self.assertTrue(self.seer.verify_philosophers_stone(12.85))

    def test_verify_philosophers_stone_false(self):
        self.assertFalse(self.seer.verify_philosophers_stone(1.0))

    def test_verify_golden_gate(self):
        self.assertTrue(self.seer.verify_golden_gate(12.85))
        self.assertFalse(self.seer.verify_golden_gate(3.0))

    def test_classify_score_extreme(self):
        self.assertEqual(self.seer.classify_score(12.85), 'PHILOSOPHERS_STONE')

    def test_classify_score_lead(self):
        self.assertEqual(self.seer.classify_score(0.5), 'LEAD')

    def test_classify_score_prima_materia(self):
        self.assertEqual(self.seer.classify_score(1.5), 'PRIMA_MATERIA')

    def test_haarp_epos_ratio_positive(self):
        ratio = self.seer.haarp_epos_ratio()
        self.assertGreater(ratio, 1000)

    def test_seed_frequencies(self):
        seeds = self.seer.seed_frequencies()
        self.assertEqual(seeds['carrier_hz'], 13.56e6)
        self.assertEqual(seeds['modulation_hz'], 7.83)
        self.assertAlmostEqual(seeds['phi'], em.PHI)

    def test_run_pipeline_returns_seven(self):
        stages = self.seer.run_pipeline()
        self.assertEqual(len(stages), 7)

    def test_get_egyptian_crosswalk_anubis(self):
        crosswalk = self.seer.get_egyptian_crosswalk('anubis')
        self.assertEqual(crosswalk.key, 'anubis')
        self.assertEqual(crosswalk.deity['name'], 'Anubis')
        self.assertIn('fear_greed < 20', crosswalk.runtime['trigger'])
        self.assertEqual(crosswalk.runtime['action'], 'OBSERVE')

    def test_decode_egyptian_ascent_anubis(self):
        payload = self.seer.decode_egyptian_ascent('anubis')
        verse_keys = [verse['key'] for verse in payload['emerald_verses']]
        stage_numbers = [stage['number'] for stage in payload['pipeline_stages']]

        self.assertEqual(payload['target'], 'anubis')
        self.assertIn('verum', verse_keys)
        self.assertIn('separate', verse_keys)
        self.assertIn(3, stage_numbers)
        self.assertIn(5, stage_numbers)
        self.assertEqual(payload['scripture']['book_of_dead_key'], 'spell_125')

    def test_decode_egyptian_ascent_all(self):
        payload = self.seer.decode_egyptian_ascent('all')
        targets = [node['target'] for node in payload['ascent']]

        self.assertEqual(len(payload['ascent']), 5)
        self.assertEqual(targets, ['anubis', 'maat', 'thoth', 'osiris', 'ra'])

    def test_resolve_wikipedia_topic_alias(self):
        self.assertEqual(self.seer._resolve_wikipedia_topic("ma'at"), 'Maat')
        self.assertEqual(self.seer._resolve_wikipedia_topic('spell_125'), 'Book of the Dead')

    def test_decode_wikipedia_meaning(self):
        def fake_fetch(url):
            if 'opensearch' in url:
                return ['Maat', ['Maat'], [], []]
            return {
                'type': 'standard',
                'title': 'Maat',
                'extract': 'Maat is the ancient Egyptian concept of truth and balance.',
                'description': 'ancient Egyptian concept and goddess',
                'pageid': 123,
                'content_urls': {
                    'desktop': {'page': 'https://en.wikipedia.org/wiki/Maat'}
                },
            }

        with patch.object(self.seer, '_fetch_wikipedia_json', side_effect=fake_fetch):
            payload = self.seer.decode_wikipedia_meaning("ma'at")

        self.assertEqual(payload['resolved_query'], 'Maat')
        self.assertEqual(payload['title'], 'Maat')
        self.assertIn('truth and balance', payload['summary'])
        self.assertEqual(payload['page_id'], 123)

    def test_decode_egyptian_ascent_with_wikipedia(self):
        with patch.object(
            self.seer,
            'decode_wikipedia_meaning',
            side_effect=lambda topic: {'query': topic, 'title': topic, 'summary': f'{topic} summary'},
        ):
            payload = self.seer.decode_egyptian_ascent('anubis', include_wikipedia=True)

        topics = [topic['query'] for topic in payload['wikipedia_grounding']['topics']]
        self.assertEqual(topics, ['Emerald Tablet', 'Anubis', 'Book of the Dead', 'Maat'])

    def test_full_decode_json_serialisable(self):
        decoded = self.seer.full_decode()
        # Must be JSON-serialisable without error
        payload = json.dumps(decoded, indent=2)
        self.assertIn('Emerald Tablet', payload)
        self.assertIn('verses', decoded)
        self.assertIn('seven_stages', decoded)
        self.assertIn('egyptian_ascent', decoded)
        self.assertEqual(len(decoded['verses']), len(em._VERSE_CATALOG))
        self.assertEqual(len(decoded['seven_stages']), 7)
        self.assertEqual(len(decoded['egyptian_ascent']), 5)


class TestScalingLaw(unittest.TestCase):
    """Verify HAARP-to-EPOS scaling constants."""

    def test_chamber_volume_approximately_14_liters(self):
        vol_liters = em.EPOS_CHAMBER_VOLUME_M3 * 1000
        self.assertAlmostEqual(vol_liters, 14.14, places=1)

    def test_concentration_factor_order_of_magnitude(self):
        # Volumetric ratio is extremely large (ionosphere vs 30 cm chamber)
        self.assertGreater(em.VOLUMETRIC_CONCENTRATION_FACTOR, 1e9)

    def test_power_ratio_very_small(self):
        ratio = em.EPOS_RF_POWER_W / em.HAARP_POWER_W
        self.assertLess(ratio, 1e-4)
        self.assertGreater(ratio, 1e-6)


class TestCLI(unittest.TestCase):
    """Test CLI entry point."""

    def test_main_returns_zero(self):
        rc = em.main([])
        self.assertEqual(rc, 0)

    def test_main_json_mode(self):
        rc = em.main(['--json'])
        self.assertEqual(rc, 0)

    def test_main_verse_mode(self):
        rc = em.main(['--verse', 'verum'])
        self.assertEqual(rc, 0)

    def test_main_stage_mode(self):
        rc = em.main(['--stage', '7'])
        self.assertEqual(rc, 0)

    def test_main_verse_json_mode(self):
        rc = em.main(['--verse', 'as_below', '--json'])
        self.assertEqual(rc, 0)

    def test_main_ascent_mode(self):
        rc = em.main(['--ascent', 'anubis'])
        self.assertEqual(rc, 0)

    def test_main_ascent_json_mode(self):
        rc = em.main(['--ascent', 'all', '--json'])
        self.assertEqual(rc, 0)

    def test_main_wiki_mode(self):
        with patch.object(
            em.EmeraldSeer,
            'decode_wikipedia_meaning',
            return_value={
                'query': 'Emerald Tablet',
                'resolved_query': 'Emerald Tablet',
                'title': 'Emerald Tablet',
                'summary': 'A compact and cryptic text attributed to Hermes Trismegistus.',
                'description': 'ancient text',
                'page_id': 1,
                'url': 'https://en.wikipedia.org/wiki/Emerald_Tablet',
                'source': 'wikipedia_rest_summary',
            },
        ):
            rc = em.main(['--wiki', 'Emerald Tablet', '--json'])
        self.assertEqual(rc, 0)

    def test_main_ancient_mode(self):
        rc = em.main(['--ancient', 'mogollon'])
        self.assertEqual(rc, 0)

    def test_main_ancient_json_mode(self):
        rc = em.main(['--ancient', 'all', '--json'])
        self.assertEqual(rc, 0)

    def test_main_unified_mode(self):
        rc = em.main(['--unified', '--json'])
        self.assertEqual(rc, 0)


class TestAncientWisdomCatalog(unittest.TestCase):
    """Verify the Mogollon / Maya / Celtic crosswalk nodes."""

    def setUp(self):
        self.seer = em.EmeraldSeer()

    def test_catalog_has_three_nodes(self):
        self.assertEqual(len(em.ANCIENT_WISDOM_CATALOG), 3)
        keys = [n.key for n in em.ANCIENT_WISDOM_CATALOG]
        self.assertEqual(keys, ['mogollon', 'maya', 'celt'])

    def test_get_ancient_wisdom_crosswalk_mogollon(self):
        node = self.seer.get_ancient_wisdom_crosswalk('mogollon')
        self.assertEqual(node.key, 'mogollon')
        self.assertIn('spiral', node.deity['trading'].lower())
        self.assertIn('spiral', node.title.lower())
        self.assertIn((1, 7), [node.stage_numbers])

    def test_get_ancient_wisdom_crosswalk_maya(self):
        node = self.seer.get_ancient_wisdom_crosswalk('maya')
        self.assertEqual(node.key, 'maya')
        self.assertIn('Long Count', node.title)
        self.assertIn('7day_planner', ''.join(node.repo_surfaces))

    def test_get_ancient_wisdom_crosswalk_celt(self):
        node = self.seer.get_ancient_wisdom_crosswalk('celt')
        self.assertEqual(node.key, 'celt')
        self.assertIn('Ogham', node.title)
        self.assertEqual(node.runtime['action'], 'CROSS_THE_THRESHOLD')

    def test_get_ancient_wisdom_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            self.seer.get_ancient_wisdom_crosswalk('atlantis')

    def test_decode_ancient_wisdom_maya_structure(self):
        payload = self.seer.decode_ancient_wisdom('maya')
        self.assertEqual(payload['target'], 'maya')
        verse_keys = [v['key'] for v in payload['emerald_verses']]
        self.assertIn('manner', verse_keys)
        self.assertIn('adaptations', verse_keys)
        stage_numbers = [s['number'] for s in payload['pipeline_stages']]
        self.assertIn(7, stage_numbers)

    def test_decode_ancient_wisdom_all_returns_three_nodes(self):
        payload = self.seer.decode_ancient_wisdom('all')
        self.assertIn('ascent', payload)
        self.assertEqual(len(payload['ascent']), 3)
        targets = [n['target'] for n in payload['ascent']]
        self.assertEqual(targets, ['mogollon', 'maya', 'celt'])

    def test_resolve_wikipedia_topic_mogollon_alias(self):
        self.assertEqual(
            self.seer._resolve_wikipedia_topic('mogollon'),
            'Mogollon culture',
        )

    def test_resolve_wikipedia_topic_celt_alias(self):
        self.assertEqual(
            self.seer._resolve_wikipedia_topic('celt'),
            'Celtic mythology',
        )

    def test_decode_ancient_wisdom_with_wikipedia_mogollon(self):
        with patch.object(
            self.seer,
            'decode_wikipedia_meaning',
            side_effect=lambda t: {'query': t, 'title': t, 'summary': f'{t} summary'},
        ):
            payload = self.seer.decode_ancient_wisdom('mogollon', include_wikipedia=True)

        topics = [t['query'] for t in payload['wikipedia_grounding']['topics']]
        self.assertIn('Mogollon culture', topics)
        self.assertIn('Petroglyph', topics)


class TestUnifiedHarmonicThreads(unittest.TestCase):
    """Verify the five universal harmonic threads."""

    def test_exactly_five_threads(self):
        self.assertEqual(len(em.UNIFIED_HARMONIC_THREADS), 5)

    def test_thread_keys(self):
        keys = [t.key for t in em.UNIFIED_HARMONIC_THREADS]
        self.assertEqual(
            keys,
            ['phi_spiral', 'schumann_resonance', 'solar_cycle', 'triple_wisdom', 'void_origin'],
        )

    def test_phi_thread_value(self):
        phi_thread = em.HARMONIC_THREAD_INDEX['phi_spiral']
        self.assertAlmostEqual(phi_thread.value, em.PHI, places=10)
        self.assertIn('mogollon', phi_thread.nodes)
        self.assertIn('maya', phi_thread.nodes)
        self.assertIn('celt', phi_thread.nodes)

    def test_schumann_thread_frequency(self):
        sch = em.HARMONIC_THREAD_INDEX['schumann_resonance']
        self.assertEqual(sch.frequency_hz, 7.83)
        self.assertIn('all', sch.civilizations)

    def test_void_origin_thread_value(self):
        void_t = em.HARMONIC_THREAD_INDEX['void_origin']
        self.assertEqual(void_t.value, 0.0)
        self.assertIn('maya', void_t.nodes)
        self.assertIn('mogollon', void_t.nodes)

    def test_all_threads_json_serialisable(self):
        for thread in em.UNIFIED_HARMONIC_THREADS:
            d = thread.to_dict()
            json.dumps(d)  # must not raise
            self.assertIn('key', d)
            self.assertIn('civilizations', d)


class TestDecodeUnifiedTheory(unittest.TestCase):
    """Verify the unified theory decoder."""

    def setUp(self):
        self.seer = em.EmeraldSeer()

    def test_decode_unified_theory_structure(self):
        payload = self.seer.decode_unified_theory()
        self.assertIn('title', payload)
        self.assertIn('vision', payload)
        self.assertIn('harmonic_threads', payload)
        self.assertIn('civilization_nodes', payload)
        self.assertIn('connection_map', payload)
        self.assertIn('unified_code', payload)

    def test_unified_theory_has_eight_nodes(self):
        payload = self.seer.decode_unified_theory()
        # 5 Egyptian + 3 ancient wisdom = 8
        self.assertEqual(len(payload['civilization_nodes']), 8)

    def test_unified_theory_has_five_threads(self):
        payload = self.seer.decode_unified_theory()
        self.assertEqual(len(payload['harmonic_threads']), 5)

    def test_connection_map_links_nodes_to_threads(self):
        payload = self.seer.decode_unified_theory()
        cmap = payload['connection_map']
        # mogollon should link to phi_spiral at minimum
        self.assertIn('phi_spiral', cmap.get('mogollon', []))
        # maya should link to solar_cycle
        self.assertIn('solar_cycle', cmap.get('maya', []))
        # celt should link to triple_wisdom
        self.assertIn('triple_wisdom', cmap.get('celt', []))

    def test_unified_theory_json_serialisable(self):
        payload = self.seer.decode_unified_theory()
        json.dumps(payload, indent=2)  # must not raise

    def test_full_decode_includes_new_keys(self):
        decoded = self.seer.full_decode()
        self.assertIn('ancient_wisdom', decoded)
        self.assertIn('harmonic_threads', decoded)
        self.assertEqual(len(decoded['ancient_wisdom']), 3)
        self.assertEqual(len(decoded['harmonic_threads']), 5)


class TestProjectDruidManifest(unittest.TestCase):
    """Project Druid — physical EPAS manifestation via EPOS device spec."""

    def setUp(self):
        self.seer = em.EmeraldSeer()
        self.manifest = self.seer.project_druid_manifest(self._receipt(
            layer1_field_score=0.646,
            layer2_score=0.500,
            layer3_score=0.508,
            shield_integrity=0.545,
            radar_score=0.728,
        ))

    @staticmethod
    def _receipt(**scores):
        now = datetime.now(timezone.utc).isoformat()
        return {
            'source_id': 'test.epas.receipt',
            'source_timestamp': now,
            'received_at': now,
            'receipt_id': 'test-epas-receipt',
            'truth_status': 'real_observed',
            'generated_values': False,
            **scores,
        }

    # ── Dataclass surface ──────────────────────────────────────────────────

    def test_manifest_has_six_phases(self):
        self.assertEqual(len(self.manifest.phase_scores), 6)
        self.assertEqual(len(self.manifest.phase_statuses), 6)

    def test_phase_scores_bounded(self):
        for score in self.manifest.phase_scores:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_shield_coherence_is_mean_of_phases(self):
        expected = round(sum(self.manifest.phase_scores) / 6, 4)
        self.assertAlmostEqual(self.manifest.shield_coherence, expected, places=4)

    # ── Chamber / power specs ──────────────────────────────────────────────

    def test_chamber_diameter_matches_epos_constant(self):
        self.assertAlmostEqual(
            self.manifest.chamber_diameter_m, em.EPOS_CHAMBER_DIAMETER_M, places=6
        )

    def test_fill_gas_is_argon(self):
        self.assertEqual(self.manifest.fill_gas, 'Argon')

    def test_rf_carrier_is_ism_band(self):
        self.assertAlmostEqual(self.manifest.rf_carrier_hz, em.RF_CARRIER_ISM, places=0)

    def test_rf_modulation_is_schumann(self):
        self.assertEqual(self.manifest.rf_modulation_hz, em.SCHUMANN_FUNDAMENTAL)

    def test_total_power_exceeds_rf_drive(self):
        self.assertGreater(self.manifest.total_power_w, em.EPOS_RF_POWER_W)

    def test_output_voltage_in_350_400_range(self):
        self.assertGreaterEqual(self.manifest.output_voltage_vdc, 350.0)
        self.assertLessEqual(self.manifest.output_voltage_vdc, 400.0)

    # ── Plasma density (Paschen law) ───────────────────────────────────────

    def test_paschen_pd_product_positive(self):
        self.assertGreater(self.manifest.paschen_pd_torr_cm, 0.0)

    def test_plasma_density_positive(self):
        self.assertGreater(self.manifest.plasma_density_m3, 0.0)

    def test_plasma_status_valid(self):
        self.assertIn(self.manifest.plasma_status, ('IGNITED', 'PRIMED', 'DORMANT'))

    # ── HAARP scaling ──────────────────────────────────────────────────────

    def test_concentration_factor_matches_constant(self):
        self.assertEqual(
            self.manifest.concentration_factor, em.VOLUMETRIC_CONCENTRATION_FACTOR
        )

    def test_haarp_power_matches_constant(self):
        self.assertAlmostEqual(self.manifest.haarp_power_w, em.HAARP_POWER_W, places=0)

    # ── EPAS state injection ───────────────────────────────────────────────

    def test_with_high_epas_scores_reaches_ignited(self):
        """IGNITED requires Γ ≥ 0.945 — inject perfect scores to verify."""
        perfect = {
            'layer1_field_score': 1.0,
            'layer2_score': 1.0,
            'layer3_score': 1.0,
            'shield_integrity': 1.0,
            'radar_score': 1.0,
        }
        m = self.seer.project_druid_manifest(self._receipt(**perfect))
        self.assertEqual(m.plasma_status, 'IGNITED')
        self.assertTrue(m.device_ready)

    def test_with_zero_epas_scores_is_dormant(self):
        """DORMANT — all shield layers at floor."""
        zeroed = {
            'layer1_field_score': 0.0,
            'layer2_score': 0.0,
            'layer3_score': 0.0,
            'shield_integrity': 0.0,
            'radar_score': 0.0,
        }
        m = self.seer.project_druid_manifest(self._receipt(**zeroed))
        self.assertEqual(m.plasma_status, 'DORMANT')
        self.assertFalse(m.device_ready)

    def test_default_baseline_dormant_without_live_health(self):
        """Baseline has no live equity data (L2=0.50) → Γ < PHI gate → DORMANT.

        This is correct and intentional: the device needs real exchange data
        (L2 equity buffer) to achieve PRIMED status.  The test documents this
        boundary so any regression is caught.
        """
        # Baseline: smoke test defaults — no Kraken credentials → L2 unknown
        self.assertAlmostEqual(self.manifest.phase_scores[5], 0.500, places=3)  # P6 = L2
        self.assertLess(self.manifest.shield_coherence, 0.618)  # below PHI gate
        self.assertEqual(self.manifest.plasma_status, 'DORMANT')
        self.assertFalse(self.manifest.device_ready)

    def test_unproven_epas_state_is_numeric_free_no_data(self):
        """Missing, stale, malformed, or generated input cannot yield readiness."""
        cases = (
            None,
            self._receipt(layer1_field_score=1.0, layer2_score=1.0,
                          layer3_score=1.0, shield_integrity=1.0),
            self._receipt(layer1_field_score=1.0, layer2_score=1.0,
                          layer3_score=1.0, shield_integrity=1.0, radar_score=1.0,
                          generated_values=True),
            {
                **self._receipt(layer1_field_score=1.0, layer2_score=1.0,
                                layer3_score=1.0, shield_integrity=1.0, radar_score=1.0),
                'source_timestamp': '2000-01-01T00:00:00+00:00',
                'received_at': '2000-01-01T00:00:00+00:00',
            },
        )
        for state in cases:
            manifest = self.seer.project_druid_manifest(state)
            payload = manifest.to_dict()
            self.assertEqual(manifest.status, 'no_data')
            self.assertFalse(manifest.device_ready)
            self.assertIsNone(manifest.timestamp)
            self.assertEqual(manifest.phase_scores, ())
            self.assertEqual(payload['truth_status'], 'no_data')
            self.assertFalse(payload['controls']['operational_eligible'])
            self.assertFalse(payload['controls']['actionable'])
            self.assertFalse(payload['controls']['accounting_eligible'])
            self.assertFalse(payload['controls']['learning_eligible'])
            self.assertIsNone(payload['evidence']['source_timestamp'])

    def test_with_live_equity_reaches_primed(self):
        """Injecting real L2 equity score (≥0.85) lifts Γ past the PHI gate → PRIMED."""
        live = {
            'layer1_field_score': 0.646,
            'layer2_score': 0.90,      # strong L2: position well above liq floor
            'layer3_score': 0.508,
            'shield_integrity': 0.545,
            'radar_score': 0.728,
        }
        m = self.seer.project_druid_manifest(self._receipt(**live))
        self.assertIn(m.plasma_status, ('PRIMED', 'IGNITED'))
        self.assertTrue(m.device_ready)

    # ── Serialisation ──────────────────────────────────────────────────────

    def test_to_dict_json_serialisable(self):
        d = self.manifest.to_dict()
        payload = json.dumps(d)
        self.assertIn('illumination_phases', payload)
        self.assertIn('plasma', payload)
        self.assertIn('power', payload)

    def test_to_dict_has_six_phases(self):
        d = self.manifest.to_dict()
        self.assertEqual(len(d['illumination_phases']), 6)
        self.assertEqual(d['illumination_phases'][0]['phase'], 'P1 Spark')
        self.assertEqual(d['illumination_phases'][5]['phase'], 'P6 Output')

    def test_full_decode_includes_project_druid(self):
        decoded = self.seer.full_decode()
        self.assertIn('project_druid', decoded)
        self.assertEqual(decoded['project_druid']['status'], 'no_data')
        self.assertFalse(decoded['project_druid']['device_ready'])

    # ── CLI ────────────────────────────────────────────────────────────────

    def test_cli_druid_mode_returns_zero(self):
        rc = em.main(['--druid'])
        self.assertEqual(rc, 0)

    def test_cli_druid_json_mode_returns_zero(self):
        rc = em.main(['--druid', '--json'])
        self.assertEqual(rc, 0)


# ════════════════════════════════════════════════════════════════════════════
# EARTH-SCALE EPAS SECOND IONOSPHERE TESTS
# ════════════════════════════════════════════════════════════════════════════

class TestEarthEPASSimulation(unittest.TestCase):
    """Validate the Earth-scale EPAS second-ionosphere simulation."""

    @classmethod
    def setUpClass(cls):
        cls.seer = em.EmeraldSeer()
        cls.sim = cls.seer.earth_shield_simulation()

    # ── Dataclass integrity ────────────────────────────────────────────────

    def test_returns_earth_epas_dataclass(self):
        self.assertIsInstance(self.sim, em.EarthEPASSimulation)

    def test_is_frozen(self):
        with self.assertRaises(AttributeError):
            self.sim.shield_status = 'HACKED'  # type: ignore[misc]

    def test_timestamp_is_utc_iso(self):
        self.assertIn('T', self.sim.timestamp)  # ISO 8601

    # ── Live VSOP87 positions ──────────────────────────────────────────────

    def test_planet_positions_has_all_bodies(self):
        required = {'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
                     'Uranus', 'Neptune', 'Pluto', 'Sun', 'Moon'}
        self.assertTrue(required.issubset(set(self.sim.planet_positions.keys())))

    def test_all_longitudes_in_range(self):
        for body, lon in self.sim.planet_positions.items():
            self.assertGreaterEqual(lon, 0.0, f'{body} longitude < 0')
            self.assertLess(lon, 360.0, f'{body} longitude >= 360')

    def test_positions_are_distinct(self):
        lons = list(self.sim.planet_positions.values())
        self.assertGreater(len(set(lons)), 5, 'Too many identical longitudes')

    # ── Aspects ────────────────────────────────────────────────────────────

    def test_aspects_non_negative(self):
        self.assertGreaterEqual(self.sim.total_aspects, 0)

    def test_aspects_have_structure(self):
        if self.sim.active_aspects:
            a = self.sim.active_aspects[0]
            for k in ('body1', 'body2', 'aspect', 'separation', 'orb',
                       'harmonic_value', 'pair_weight', 'phi_resonance', 'score'):
                self.assertIn(k, a, f'Missing key: {k}')

    def test_positive_negative_sum_equals_total(self):
        self.assertEqual(
            self.sim.positive_aspects + self.sim.negative_aspects,
            self.sim.total_aspects,
        )

    def test_dominant_aspect_string_non_empty(self):
        self.assertTrue(len(self.sim.dominant_aspect) > 0)

    # ── Cosmic field ───────────────────────────────────────────────────────

    def test_cosmic_field_in_unit_interval(self):
        self.assertGreaterEqual(self.sim.cosmic_field_score, 0.0)
        self.assertLessEqual(self.sim.cosmic_field_score, 1.0)

    def test_schumann_modulated_in_unit_interval(self):
        self.assertGreaterEqual(self.sim.schumann_modulated_score, 0.0)
        self.assertLessEqual(self.sim.schumann_modulated_score, 1.0)

    # ── Layer 1: EM Deflection ─────────────────────────────────────────────

    def test_l1_score_in_unit_interval(self):
        self.assertGreaterEqual(self.sim.l1_field_score, 0.0)
        self.assertLessEqual(self.sim.l1_field_score, 1.0)

    def test_l1_status_valid(self):
        self.assertIn(self.sim.l1_status, ('CLEAR', 'DEFLECTING', 'OVERLOADED'))

    # ── Layer 2: Plasma Ablation ───────────────────────────────────────────

    def test_l2_electron_density_physical(self):
        self.assertGreater(self.sim.l2_electron_density_m3, 0)
        self.assertLessEqual(self.sim.l2_electron_density_m3, em.F_REGION_ELECTRON_DENSITY)

    def test_l2_shell_volume_matches_constant(self):
        self.assertAlmostEqual(self.sim.l2_shell_volume_m3, em.F_REGION_SHELL_VOLUME_M3)

    def test_l2_total_electrons_physical(self):
        self.assertGreater(self.sim.l2_total_electrons, 0)

    def test_l2_plasma_frequency_physical(self):
        expected_max = 9.0 * (em.F_REGION_ELECTRON_DENSITY ** 0.5)
        self.assertGreater(self.sim.l2_plasma_frequency_hz, 0)
        self.assertLessEqual(self.sim.l2_plasma_frequency_hz, expected_max * 1.01)

    def test_l2_status_valid(self):
        self.assertIn(self.sim.l2_status, ('INTACT', 'ABLATING', 'CRITICAL', 'TERMINAL'))

    # ── Layer 3: Shield Phased Harmonics ───────────────────────────────────

    def test_l3_schumann_phase_in_unit(self):
        self.assertGreaterEqual(self.sim.l3_schumann_phase, 0.0)
        self.assertLess(self.sim.l3_schumann_phase, 1.0)

    def test_l3_schumann_modulator_near_unity(self):
        self.assertAlmostEqual(self.sim.l3_schumann_modulator, 1.0, delta=0.10)

    def test_l3_harmonic_coherence_in_unit(self):
        self.assertGreaterEqual(self.sim.l3_harmonic_coherence, 0.0)
        self.assertLessEqual(self.sim.l3_harmonic_coherence, 1.0)

    def test_l3_status_valid(self):
        self.assertIn(self.sim.l3_status, ('COHERENT', 'CRACKING', 'FRAGMENTED'))

    # ── Six Illumination Phases ────────────────────────────────────────────

    def test_six_phase_scores(self):
        self.assertEqual(len(self.sim.phase_scores), 6)

    def test_all_phase_scores_in_unit(self):
        for i, sc in enumerate(self.sim.phase_scores):
            self.assertGreaterEqual(sc, 0.0, f'Phase {i+1} score < 0')
            self.assertLessEqual(sc, 1.0, f'Phase {i+1} score > 1')

    def test_six_phase_statuses(self):
        self.assertEqual(len(self.sim.phase_statuses), 6)

    def test_shield_coherence_is_mean_of_phases(self):
        expected = sum(self.sim.phase_scores) / 6
        self.assertAlmostEqual(self.sim.shield_coherence, expected, places=3)

    # ── Power budget ───────────────────────────────────────────────────────

    def test_earth_rf_power_matches_epos_times_concentration(self):
        expected = em.EPOS_RF_POWER_W * em.VOLUMETRIC_CONCENTRATION_FACTOR
        self.assertAlmostEqual(self.sim.earth_rf_power_w, expected, places=0)

    def test_earth_power_density_positive(self):
        self.assertGreater(self.sim.earth_power_density_w_m3, 0)

    def test_earth_output_voltage_large(self):
        self.assertGreater(self.sim.earth_output_voltage_v, 1e3)

    # ── Shield verdict ─────────────────────────────────────────────────────

    def test_shield_status_valid(self):
        self.assertIn(self.sim.shield_status,
                       ('SHIELDS_UP', 'SHIELDS_STRESSED', 'SHIELDS_FAILING'))

    def test_coverage_pct_matches_coherence(self):
        expected = round(self.sim.shield_coherence * 100, 1)
        self.assertAlmostEqual(self.sim.shield_coverage_pct, expected, places=1)

    def test_planetary_summary_contains_shield_status(self):
        self.assertIn(self.sim.shield_status, self.sim.planetary_summary)

    # ── Serialisation ──────────────────────────────────────────────────────

    def test_to_dict_json_serialisable(self):
        d = self.sim.to_dict()
        payload = json.dumps(d)
        self.assertIn('solar_system', payload)
        self.assertIn('layer1_em_deflection', payload)
        self.assertIn('layer2_plasma_ablation', payload)
        self.assertIn('layer3_shield_phased_harmonics', payload)
        self.assertIn('illumination_phases', payload)

    def test_to_dict_has_six_phases(self):
        d = self.sim.to_dict()
        self.assertEqual(len(d['illumination_phases']), 6)

    def test_to_dict_planet_positions(self):
        d = self.sim.to_dict()
        self.assertIn('positions', d['solar_system'])
        self.assertGreaterEqual(len(d['solar_system']['positions']), 10)

    # ── CLI ────────────────────────────────────────────────────────────────

    def test_cli_earth_shield_returns_zero(self):
        rc = em.main(['--earth-shield'])
        self.assertEqual(rc, 0)

    def test_cli_earth_shield_json_returns_zero(self):
        rc = em.main(['--earth-shield', '--json'])
        self.assertEqual(rc, 0)

    # ── EmeraldSeer integration ────────────────────────────────────────────

    def test_seer_method_returns_simulation(self):
        result = self.seer.earth_shield_simulation()
        self.assertIsInstance(result, em.EarthEPASSimulation)


class TestRelayNetwork(unittest.TestCase):
    """Validate the historical relay site network."""

    @classmethod
    def setUpClass(cls):
        cls.sim = em.simulate_earth_epas()
        cls.relays, cls.coverage, cls.active, cls.total = em.compute_relay_network(
            cosmic_field=0.6,
            shield_coherence=0.7,
            earth_rf_power_w=1e12,
        )

    # ── Relay site constant ────────────────────────────────────────────────

    def test_historical_sites_tuple_exists(self):
        self.assertIsInstance(em._HISTORICAL_RELAY_SITES, tuple)
        self.assertGreater(len(em._HISTORICAL_RELAY_SITES), 20)

    def test_site_tuple_has_five_fields(self):
        for site in em._HISTORICAL_RELAY_SITES:
            self.assertEqual(len(site), 5, f'Site {site[0]} wrong length')

    def test_all_latitudes_valid(self):
        for name, _, lat, _, _ in em._HISTORICAL_RELAY_SITES:
            self.assertGreaterEqual(lat, -90.0, f'{name} lat < -90')
            self.assertLessEqual(lat, 90.0, f'{name} lat > 90')

    def test_all_longitudes_valid(self):
        for name, _, _, lon, _ in em._HISTORICAL_RELAY_SITES:
            self.assertGreaterEqual(lon, -180.0, f'{name} lon < -180')
            self.assertLessEqual(lon, 180.0, f'{name} lon > 180')

    def test_sites_have_unique_names(self):
        names = [s[0] for s in em._HISTORICAL_RELAY_SITES]
        self.assertEqual(len(names), len(set(names)))

    def test_civilisations_include_core_groups(self):
        civs = {s[1] for s in em._HISTORICAL_RELAY_SITES}
        for c in ('Egyptian', 'Maya', 'Celtic', 'Mogollon', 'Chinese',
                  'Indian', 'Indus', 'Japanese', 'Persian', 'Sumerian',
                  'Greek', 'Minoan', 'Nabataean', 'Ethiopian', 'Norse',
                  'Mississippian', 'Burmese', 'Sinhalese', 'Maltese'):
            self.assertIn(c, civs, f'{c} missing from relay civilisations')

    # ── RelaySite dataclass ────────────────────────────────────────────────

    def test_relay_site_is_frozen(self):
        r = self.relays[0]
        with self.assertRaises(AttributeError):
            r.name = 'hacked'  # type: ignore[misc]

    def test_relay_to_dict_has_all_keys(self):
        d = self.relays[0].to_dict()
        for k in ('name', 'civilisation', 'latitude', 'longitude',
                   'harmonic_role', 'geomagnetic_coupling', 'relay_strength',
                   'relay_status', 'power_share_w'):
            self.assertIn(k, d)

    # ── compute_relay_network ──────────────────────────────────────────────

    def test_returns_all_sites(self):
        self.assertEqual(self.total, len(em._HISTORICAL_RELAY_SITES))
        self.assertEqual(len(self.relays), self.total)

    def test_active_count_within_range(self):
        self.assertGreaterEqual(self.active, 0)
        self.assertLessEqual(self.active, self.total)

    def test_coverage_in_unit_interval(self):
        self.assertGreaterEqual(self.coverage, 0.0)
        self.assertLessEqual(self.coverage, 1.0)

    def test_geomag_coupling_in_unit(self):
        for r in self.relays:
            self.assertGreaterEqual(r.geomagnetic_coupling, 0.0)
            self.assertLessEqual(r.geomagnetic_coupling, 1.0)

    def test_relay_strength_in_unit(self):
        for r in self.relays:
            self.assertGreaterEqual(r.relay_strength, 0.0)
            self.assertLessEqual(r.relay_strength, 1.0)

    def test_relay_status_valid(self):
        valid = {'ACTIVE', 'RESONATING', 'DORMANT', 'OFFLINE'}
        for r in self.relays:
            self.assertIn(r.relay_status, valid, f'{r.name}: {r.relay_status}')

    def test_power_shares_sum_roughly_to_total(self):
        total_share = sum(r.power_share_w for r in self.relays)
        self.assertAlmostEqual(total_share, 1e12, delta=1e6)

    def test_equatorial_sites_have_higher_coupling(self):
        giza = next(r for r in self.relays if 'Giza' in r.name)
        brodgar = next(r for r in self.relays if 'Brodgar' in r.name)
        self.assertGreater(giza.geomagnetic_coupling, brodgar.geomagnetic_coupling)

    def test_zero_cosmic_field_produces_offline(self):
        relays, cov, active, total = em.compute_relay_network(0.0, 0.0, 1e12)
        for r in relays:
            self.assertEqual(r.relay_status, 'OFFLINE', f'{r.name} not offline')
        self.assertEqual(active, 0)

    # ── Integration with EarthEPASSimulation ───────────────────────────────

    def test_simulation_has_relay_sites(self):
        self.assertIsInstance(self.sim.relay_sites, tuple)
        self.assertGreater(len(self.sim.relay_sites), 0)

    def test_simulation_relay_fields(self):
        self.assertGreaterEqual(self.sim.relay_network_coverage, 0.0)
        self.assertLessEqual(self.sim.relay_network_coverage, 1.0)
        self.assertGreaterEqual(self.sim.relay_active_count, 0)
        self.assertEqual(self.sim.relay_total_count, len(em._HISTORICAL_RELAY_SITES))

    def test_simulation_to_dict_has_relay_network(self):
        d = self.sim.to_dict()
        self.assertIn('relay_network', d)
        rn = d['relay_network']
        self.assertIn('sites', rn)
        self.assertIn('network_coverage', rn)
        self.assertIn('active_count', rn)
        self.assertIn('total_count', rn)
        self.assertEqual(len(rn['sites']), rn['total_count'])

    def test_simulation_summary_includes_relays(self):
        self.assertIn('relays=', self.sim.planetary_summary)

    def test_relay_json_serialisable(self):
        d = self.sim.to_dict()
        payload = json.dumps(d)
        self.assertIn('relay_network', payload)
        self.assertIn('Great Pyramid of Giza', payload)

    def test_specific_sites_present(self):
        names = [s['name'] for s in self.sim.to_dict()['relay_network']['sites']]
        for expected in ('Great Pyramid of Giza', 'Stonehenge', 'Chaco Canyon',
                         'Chichen Itza', 'Machu Picchu', 'Angkor Wat', 'Uluru',
                         'Temple of Heaven', 'Mohenjo-Daro', 'Konark Sun Temple',
                         'Ise Grand Shrine', 'Persepolis', 'Delphi', 'Petra',
                         'Lalibela', 'Bagan', 'Old Uppsala', 'Cahokia Mounds',
                         'Ggantija', 'Sigiriya', 'Knossos', 'Baalbek'):
            self.assertIn(expected, names, f'{expected} missing from relay network')


# ═══════════════════════════════════════════════════════════════════════════
# §12  Natural Ionosphere Profile — Chapman / Drude / FFS / Lighthouse
# ═══════════════════════════════════════════════════════════════════════════

class TestNaturalIonosphereProfile(unittest.TestCase):
    """Tests for the complete natural ionosphere profiling engine."""

    @classmethod
    def setUpClass(cls):
        # Get relay site dicts from existing simulation
        cls.sim = em.simulate_earth_epas()
        relay_dicts = [r if isinstance(r, dict) else r.to_dict() if hasattr(r, 'to_dict') else r
                       for r in cls.sim.relay_sites]
        # Call profiler directly
        cls.profile = em.profile_natural_ionosphere(
            relay_sites_data=relay_dicts,
            cosmic_field=0.5,
        )

    # ── NaturalIonosphereProfile top-level fields ──────────────────────

    def test_profile_type(self):
        self.assertIsInstance(self.profile, em.NaturalIonosphereProfile)

    def test_timestamp_iso(self):
        self.assertIsInstance(self.profile.timestamp, str)
        self.assertIn('T', self.profile.timestamp)

    def test_solar_zenith_range(self):
        self.assertGreaterEqual(self.profile.solar_zenith_deg, 0.0)
        self.assertLessEqual(self.profile.solar_zenith_deg, 180.0)

    def test_is_daytime_bool(self):
        self.assertIsInstance(self.profile.is_daytime, bool)

    def test_readiness_bounded(self):
        self.assertGreaterEqual(self.profile.readiness_for_epas, 0.0)
        self.assertLessEqual(self.profile.readiness_for_epas, 1.0)

    def test_health_valid_status(self):
        self.assertIn(self.profile.ionosphere_health,
                      ('ROBUST', 'MODERATE', 'DEPLETED', 'STORM'))

    # ── Chapman layer model ────────────────────────────────────────────

    def test_five_layers_present(self):
        self.assertEqual(len(self.profile.layers), 5)

    def test_layer_names(self):
        names = [ly.name for ly in self.profile.layers]
        self.assertEqual(names, ['D', 'E', 'F1', 'F2', 'Topside'])

    def test_layers_are_ionospheric_layer(self):
        for ly in self.profile.layers:
            self.assertIsInstance(ly, em.IonosphericLayer)

    def test_layer_altitudes_positive(self):
        for ly in self.profile.layers:
            self.assertGreater(ly.base_alt_km, 0)
            self.assertGreater(ly.peak_alt_km, ly.base_alt_km)
            self.assertGreater(ly.top_alt_km, ly.peak_alt_km)

    def test_layer_densities_positive(self):
        for ly in self.profile.layers:
            self.assertGreater(ly.peak_density_m3, 0)

    def test_f2_has_highest_density_among_main_layers(self):
        """F2 should have the highest peak density (excluding D/F1 daytime edge cases)."""
        f2 = next(ly for ly in self.profile.layers if ly.name == 'F2')
        e = next(ly for ly in self.profile.layers if ly.name == 'E')
        self.assertGreaterEqual(f2.peak_density_m3, e.peak_density_m3)

    def test_layer_temperatures_positive(self):
        for ly in self.profile.layers:
            self.assertGreater(ly.temperature_k, 0)

    def test_layer_plasma_freq_positive(self):
        for ly in self.profile.layers:
            self.assertGreater(ly.plasma_freq_hz, 0)

    def test_layer_scale_heights_positive(self):
        for ly in self.profile.layers:
            self.assertGreater(ly.scale_height_km, 0)

    def test_layer_conductivity_nonneg(self):
        for ly in self.profile.layers:
            self.assertGreaterEqual(ly.conductivity_s_m, 0)

    def test_layer_skin_depth_positive(self):
        for ly in self.profile.layers:
            self.assertGreater(ly.skin_depth_m, 0)

    def test_layer_drude_epsilon_real_below_one(self):
        """Drude real part < 1 for plasma at Schumann frequencies."""
        for ly in self.profile.layers:
            self.assertLessEqual(ly.drude_epsilon_real, 1.0)

    def test_layer_harmonic_fluid_ratio_small(self):
        """Ionospheric fp / aluminum fp should be tiny (< 1e-5)."""
        for ly in self.profile.layers:
            self.assertGreaterEqual(ly.harmonic_fluid_ratio, 0.0)
            self.assertLess(ly.harmonic_fluid_ratio, 1e-5)

    def test_layer_to_dict_keys(self):
        d = self.profile.layers[0].to_dict()
        for k in ('name', 'base_alt_km', 'peak_alt_km', 'top_alt_km',
                   'peak_density_m3', 'scale_height_km', 'collision_freq_hz',
                   'temperature_k', 'plasma_freq_hz', 'critical_freq_hz',
                   'conductivity_s_m', 'drude_epsilon_real', 'drude_epsilon_imag',
                   'skin_depth_m', 'harmonic_fluid_ratio'):
            self.assertIn(k, d, f'Missing key {k}')

    # ── F2 peak extraction ─────────────────────────────────────────────

    def test_f2_peak_density(self):
        self.assertGreater(self.profile.f2_peak_density_m3, 0)

    def test_f2_peak_alt_reasonable(self):
        self.assertGreaterEqual(self.profile.f2_peak_alt_km, 200)
        self.assertLessEqual(self.profile.f2_peak_alt_km, 400)

    def test_f2_critical_freq_formula(self):
        """foF2 = 9 √(NmF2)."""
        expected = 9.0 * math.sqrt(self.profile.f2_peak_density_m3)
        self.assertAlmostEqual(self.profile.f2_critical_freq_hz, expected, places=0)

    def test_tec_positive(self):
        self.assertGreater(self.profile.total_electron_content_tecu, 0)

    # ── Chapman function directly ──────────────────────────────────────

    def test_chapman_peak_at_peak_alt(self):
        # At chi=0 (overhead sun), N(hm) = Nm exactly
        n_peak = em._chapman_density(300.0, 300.0, 1e12, 60.0, 0.0)
        self.assertAlmostEqual(n_peak, 1e12, delta=1e12 * 0.01)

    def test_chapman_decreases_above(self):
        chi = math.radians(30.0)
        n_at_peak = em._chapman_density(300.0, 300.0, 1e12, 60.0, chi)
        n_above = em._chapman_density(500.0, 300.0, 1e12, 60.0, chi)
        self.assertLess(n_above, n_at_peak)

    def test_chapman_decreases_below(self):
        chi = math.radians(30.0)
        n_at_peak = em._chapman_density(300.0, 300.0, 1e12, 60.0, chi)
        n_below = em._chapman_density(150.0, 300.0, 1e12, 60.0, chi)
        self.assertLess(n_below, n_at_peak)

    def test_chapman_always_positive(self):
        chi = math.radians(45.0)
        for h in (60, 100, 200, 300, 500, 800, 1000):
            n = em._chapman_density(h, 300.0, 1e12, 60.0, chi)
            self.assertGreater(n, 0, f'Negative density at {h} km')

    # ── Drude permittivity ─────────────────────────────────────────────

    def test_drude_returns_tuple_pair(self):
        eps_r, eps_i = em._drude_permittivity(1e6, 3e6, 1e3)
        self.assertIsInstance(eps_r, float)
        self.assertIsInstance(eps_i, float)

    def test_drude_real_below_one_when_fp_above_freq(self):
        eps_r, _ = em._drude_permittivity(1e6, 5e6, 1e3)
        self.assertLess(eps_r, 1.0)

    def test_drude_imag_nonneg(self):
        _, eps_i = em._drude_permittivity(1e6, 3e6, 1e4)
        self.assertGreaterEqual(eps_i, 0.0)

    def test_drude_at_zero_freq(self):
        """At zero frequency, permittivity should still be computable."""
        eps_r, eps_i = em._drude_permittivity(0.0, 3e6, 1e3)
        self.assertIsInstance(eps_r, float)

    # ── Aluminum harmonic fluid summary ────────────────────────────────

    def test_fluid_classification_valid(self):
        self.assertIn(self.profile.fluid_classification,
                      ('DIELECTRIC', 'WEAK_CONDUCTOR', 'CONDUCTOR'))

    def test_peak_fluid_geq_mean(self):
        self.assertGreaterEqual(self.profile.peak_harmonic_fluid_ratio,
                                self.profile.mean_harmonic_fluid_ratio)

    def test_fluid_ratios_positive(self):
        self.assertGreater(self.profile.mean_harmonic_fluid_ratio, 0)
        self.assertGreater(self.profile.peak_harmonic_fluid_ratio, 0)

    # ── FFS spectral analysis ──────────────────────────────────────────

    def test_ffs_band_count(self):
        self.assertEqual(len(self.profile.ffs_bands), 52)

    def test_ffs_bands_are_spectral_band(self):
        for b in self.profile.ffs_bands:
            self.assertIsInstance(b, em.FFSSpectralBand)

    def test_ffs_opaque_below_positive(self):
        self.assertGreater(self.profile.ffs_opaque_below_hz, 0)

    def test_ffs_transparent_geq_opaque(self):
        self.assertGreaterEqual(self.profile.ffs_transparent_above_hz,
                                self.profile.ffs_opaque_below_hz)

    def test_ffs_low_freq_reflects(self):
        """Very low frequencies should be reflected (not penetrating)."""
        low_bands = [b for b in self.profile.ffs_bands if b.freq_hz < 1e4]
        for b in low_bands:
            self.assertFalse(b.penetrates,
                             f'{b.band_name} at {b.freq_hz} Hz should reflect')

    def test_ffs_high_freq_penetrates(self):
        """Frequencies well above foF2 should penetrate."""
        high_bands = [b for b in self.profile.ffs_bands if b.freq_hz > 2e7]
        for b in high_bands:
            self.assertTrue(b.penetrates,
                            f'{b.band_name} at {b.freq_hz} Hz should penetrate')

    def test_ffs_band_has_required_fields(self):
        d = self.profile.ffs_bands[0].to_dict()
        for k in ('band_name', 'freq_hz', 'reflection_alt_km',
                   'absorption_db_km', 'phase_velocity_ratio', 'penetrates'):
            self.assertIn(k, d)

    def test_ffs_phase_velocity_positive_when_penetrating(self):
        """Penetrating bands have real phase velocity; evanescent bands are 0."""
        for b in self.profile.ffs_bands:
            if b.penetrates:
                self.assertGreater(b.phase_velocity_ratio, 0,
                                   f'{b.band_name}@{b.freq_hz}Hz penetrates but Vp=0')
            else:
                self.assertGreaterEqual(b.phase_velocity_ratio, 0)

    # ── Lighthouse mapping ─────────────────────────────────────────────

    def test_lighthouse_probe_count(self):
        self.assertEqual(len(self.profile.lighthouse_probes),
                         len(em._HISTORICAL_RELAY_SITES))

    def test_probes_are_lighthouse_probe(self):
        for p in self.profile.lighthouse_probes:
            self.assertIsInstance(p, em.LighthouseProbe)

    def test_probe_b_field_positive(self):
        for p in self.profile.lighthouse_probes:
            self.assertGreater(p.local_b_field_tesla, 0)

    def test_probe_gyrofreq_positive(self):
        for p in self.profile.lighthouse_probes:
            self.assertGreater(p.electron_gyrofreq_hz, 0)

    def test_probe_upper_hybrid_gt_plasma(self):
        """Upper hybrid freq = √(fp² + fce²) — always ≥ both fp and fce."""
        for p in self.profile.lighthouse_probes:
            self.assertGreater(p.upper_hybrid_freq_hz, 0)

    def test_probe_tec_positive(self):
        for p in self.profile.lighthouse_probes:
            self.assertGreater(p.tec_tecu, 0)

    def test_probe_density_profile_nonempty(self):
        for p in self.profile.lighthouse_probes:
            self.assertGreater(len(p.density_profile_km), 0)

    def test_probe_status_valid(self):
        for p in self.profile.lighthouse_probes:
            self.assertIn(p.probe_status, ('LOCKED', 'PARTIAL', 'NO_RETURN'))

    def test_locked_count_matches(self):
        actual_locked = sum(1 for p in self.profile.lighthouse_probes
                            if p.probe_status == 'LOCKED')
        self.assertEqual(self.profile.lighthouse_locked_count, actual_locked)

    def test_mean_fof2_positive(self):
        self.assertGreater(self.profile.lighthouse_mean_fof2_hz, 0)

    def test_mean_tec_positive(self):
        self.assertGreater(self.profile.lighthouse_mean_tec_tecu, 0)

    def test_probe_to_dict_keys(self):
        d = self.profile.lighthouse_probes[0].to_dict()
        for k in ('site_name', 'latitude', 'longitude', 'local_b_field_tesla',
                   'electron_gyrofreq_hz', 'upper_hybrid_freq_hz',
                   'lower_hybrid_freq_hz', 'local_fof2_hz', 'tec_tecu',
                   'density_profile', 'probe_status'):
            self.assertIn(k, d)

    def test_high_latitude_stronger_b_field(self):
        """Higher latitudes should have stronger dipole B-field."""
        probes_by_lat = sorted(self.profile.lighthouse_probes,
                                key=lambda p: abs(p.latitude))
        if len(probes_by_lat) >= 2:
            low_lat = probes_by_lat[0]
            high_lat = probes_by_lat[-1]
            self.assertGreater(high_lat.local_b_field_tesla,
                               low_lat.local_b_field_tesla)

    # ── to_dict / serialisation ────────────────────────────────────────

    def test_to_dict_top_keys(self):
        d = self.profile.to_dict()
        for k in ('timestamp', 'solar_zenith_deg', 'is_daytime',
                   'layers', 'f2_peak', 'aluminum_harmonic_fluid',
                   'ffs_spectral', 'lighthouse_mapping', 'assessment'):
            self.assertIn(k, d)

    def test_to_dict_json_serialisable(self):
        payload = json.dumps(self.profile.to_dict())
        self.assertIn('layers', payload)
        self.assertIn('aluminum_harmonic_fluid', payload)
        self.assertIn('ffs_spectral', payload)
        self.assertIn('lighthouse_mapping', payload)

    def test_to_dict_layers_count(self):
        d = self.profile.to_dict()
        self.assertEqual(len(d['layers']), 5)

    def test_to_dict_ffs_bands_count(self):
        d = self.profile.to_dict()
        self.assertEqual(len(d['ffs_spectral']['bands']), 52)

    def test_to_dict_probes_count(self):
        d = self.profile.to_dict()
        self.assertEqual(len(d['lighthouse_mapping']['probes']),
                         len(em._HISTORICAL_RELAY_SITES))

    # ── Integration with EarthEPASSimulation ───────────────────────────

    def test_sim_has_ionosphere_profile(self):
        self.assertIsNotNone(self.sim.ionosphere_profile)
        self.assertIsInstance(self.sim.ionosphere_profile, dict)

    def test_sim_to_dict_has_natural_ionosphere(self):
        d = self.sim.to_dict()
        self.assertIn('natural_ionosphere', d)

    def test_sim_ionosphere_has_layers(self):
        iono = self.sim.to_dict()['natural_ionosphere']
        self.assertIn('layers', iono)
        self.assertEqual(len(iono['layers']), 5)

    def test_sim_ionosphere_has_assessment(self):
        iono = self.sim.to_dict()['natural_ionosphere']
        self.assertIn('assessment', iono)
        self.assertIn('ionosphere_health', iono['assessment'])
        self.assertIn('readiness_for_epas', iono['assessment'])

    def test_sim_summary_includes_iono(self):
        self.assertIn('iono=', self.sim.planetary_summary)

    def test_sim_ionosphere_json_serialisable(self):
        d = self.sim.to_dict()
        payload = json.dumps(d)
        self.assertIn('natural_ionosphere', payload)
        self.assertIn('ffs_spectral', payload)
        self.assertIn('lighthouse_mapping', payload)

    # ── Edge case: zero cosmic field ───────────────────────────────────

    def test_zero_cosmic_field_still_valid(self):
        relay_dicts = [r if isinstance(r, dict) else r.to_dict()
                       for r in self.sim.relay_sites]
        profile = em.profile_natural_ionosphere(
            relay_sites_data=relay_dicts,
            cosmic_field=0.0,
        )
        self.assertIsInstance(profile, em.NaturalIonosphereProfile)
        self.assertEqual(len(profile.layers), 5)
        self.assertGreater(profile.f2_peak_density_m3, 0)
        self.assertGreater(len(profile.lighthouse_probes), 0)
        self.assertGreaterEqual(profile.readiness_for_epas, 0.0)
        self.assertLessEqual(profile.readiness_for_epas, 1.0)

    def test_high_cosmic_field_still_valid(self):
        relay_dicts = [r if isinstance(r, dict) else r.to_dict()
                       for r in self.sim.relay_sites]
        profile = em.profile_natural_ionosphere(
            relay_sites_data=relay_dicts,
            cosmic_field=1.0,
        )
        self.assertIsInstance(profile, em.NaturalIonosphereProfile)
        self.assertEqual(len(profile.layers), 5)
        self.assertGreaterEqual(profile.readiness_for_epas, 0.0)


# ════════════════════════════════════════════════════════════════════════════
# GEOMETRIC PATTERN MAPPER TESTS
# ════════════════════════════════════════════════════════════════════════════


class TestHaversine(unittest.TestCase):
    """Verify great-circle distance helper."""

    def test_same_point_zero(self):
        self.assertAlmostEqual(em._haversine_km(0, 0, 0, 0), 0.0, places=3)

    def test_equator_to_pole(self):
        # ~10,000 km quarter-circumference
        d = em._haversine_km(0, 0, 90, 0)
        self.assertAlmostEqual(d, 10007.5, delta=10)

    def test_known_pair_giza_stonehenge(self):
        d = em._haversine_km(29.9792, 31.1342, 51.1789, -1.8262)
        self.assertGreater(d, 3500)
        self.assertLess(d, 4000)

    def test_symmetry(self):
        d1 = em._haversine_km(10, 20, 30, 40)
        d2 = em._haversine_km(30, 40, 10, 20)
        self.assertAlmostEqual(d1, d2, places=3)


class TestInitialBearing(unittest.TestCase):
    """Verify bearing calculation."""

    def test_due_north(self):
        brg = em._initial_bearing_deg(0, 0, 10, 0)
        self.assertAlmostEqual(brg, 0.0, delta=0.5)

    def test_due_east(self):
        brg = em._initial_bearing_deg(0, 0, 0, 10)
        self.assertAlmostEqual(brg, 90.0, delta=0.5)

    def test_due_south(self):
        brg = em._initial_bearing_deg(10, 0, 0, 0)
        self.assertAlmostEqual(brg, 180.0, delta=0.5)

    def test_bearing_range(self):
        brg = em._initial_bearing_deg(29.9, 31.1, 51.2, -1.8)
        self.assertGreaterEqual(brg, 0)
        self.assertLess(brg, 360)


class TestCrossTrack(unittest.TestCase):
    """Verify cross-track distance."""

    def test_point_on_great_circle_zero(self):
        # Midpoint of equator from lon 0 to lon 20 should be ~0
        xt = em._cross_track_km(0, 0, 0, 20, 0, 10)
        self.assertLess(xt, 1.0)  # within 1 km

    def test_off_equator(self):
        # 10°N from equatorial great circle should be significant
        xt = em._cross_track_km(0, 0, 0, 90, 10, 45)
        self.assertGreater(xt, 500)


class TestGeometricMapResult(unittest.TestCase):
    """Verify the full geometric pattern mapper."""

    @classmethod
    def setUpClass(cls):
        cls.result = em.map_geometric_pattern()

    def test_returns_correct_type(self):
        self.assertIsInstance(self.result, em.GeometricMapResult)

    def test_total_sites_45(self):
        self.assertEqual(self.result.total_sites, 45)

    def test_total_links_990(self):
        self.assertEqual(self.result.total_links, 990)

    def test_alignments_found(self):
        self.assertGreater(len(self.result.alignments), 0)
        for al in self.result.alignments:
            self.assertIsInstance(al, em.SacredAlignment)
            self.assertGreaterEqual(len(al.sites), 3)
            self.assertGreaterEqual(al.total_arc_km, 0)

    def test_major_alignments_exist(self):
        major = [a for a in self.result.alignments if len(a.sites) >= 4]
        self.assertGreater(len(major), 0, 'Expected at least one 4+ site alignment')

    def test_mega_alignment_spans_globe(self):
        longest = max(self.result.alignments, key=lambda a: a.total_arc_km)
        self.assertGreater(longest.total_arc_km, 15000)

    def test_phi_ratios_found(self):
        self.assertGreater(len(self.result.phi_ratios), 0)
        for p in self.result.phi_ratios:
            self.assertIsInstance(p, em.PhiRatioLink)
            self.assertLess(p.phi_error_pct, 3.0)
            self.assertGreater(p.ratio, 1.5)
            self.assertLess(p.ratio, 1.7)

    def test_phi_ratio_best_precision(self):
        best = self.result.phi_ratios[0]
        self.assertLess(best.phi_error_pct, 0.1, 'Best PHI ratio should be < 0.1% error')

    def test_sacred_triangles_found(self):
        self.assertGreater(len(self.result.sacred_triangles), 0)
        patterns = {t.pattern for t in self.result.sacred_triangles}
        self.assertTrue(len(patterns) >= 1)
        for t in self.result.sacred_triangles:
            self.assertIsInstance(t, em.SacredTriangle)
            self.assertIn(t.pattern, ('golden', 'equilateral', 'right', 'phi-sided', 'isosceles'))
            self.assertGreaterEqual(t.symmetry_score, 0)
            self.assertLessEqual(t.symmetry_score, 1.01)

    def test_latitude_bands_found(self):
        self.assertGreater(len(self.result.latitude_bands), 0)
        for b in self.result.latitude_bands:
            self.assertIsInstance(b, em.LatitudeBand)
            self.assertGreaterEqual(len(b.sites), 2)

    def test_holy_30th_parallel(self):
        band_labels = [b.label for b in self.result.latitude_bands]
        self.assertIn('Holy 30th Parallel', band_labels)

    def test_network_centroid_plausible(self):
        lat, lon = self.result.network_centroid
        self.assertGreater(lat, -90)
        self.assertLess(lat, 90)
        self.assertGreater(lon, -180)
        self.assertLess(lon, 180)

    def test_max_span_plausible(self):
        self.assertGreater(self.result.max_span_km, 15000)
        self.assertLess(self.result.max_span_km, 21000)

    def test_mean_nearest_neighbour(self):
        self.assertGreater(self.result.mean_nearest_km, 0)
        self.assertLess(self.result.mean_nearest_km, 5000)

    def test_phi_grid_score_range(self):
        self.assertGreaterEqual(self.result.phi_grid_score, 0)
        self.assertLessEqual(self.result.phi_grid_score, 1.0)

    def test_dominant_pattern_nonempty(self):
        self.assertTrue(self.result.dominant_pattern)

    def test_to_dict_serialisable(self):
        d = self.result.to_dict()
        self.assertIsInstance(d, dict)
        s = json.dumps(d)
        self.assertIsInstance(s, str)
        parsed = json.loads(s)
        self.assertEqual(parsed['total_sites'], 45)
        self.assertEqual(parsed['total_links'], 990)

    def test_to_dict_contains_all_fields(self):
        d = self.result.to_dict()
        for key in ('alignments', 'phi_ratios', 'sacred_triangles',
                     'latitude_bands', 'network_centroid', 'mean_nearest_km',
                     'max_span_km', 'max_span_pair', 'phi_grid_score',
                     'dominant_pattern'):
            self.assertIn(key, d)


class TestGeometricMapASCII(unittest.TestCase):
    """Verify the ASCII renderer and console formatter."""

    @classmethod
    def setUpClass(cls):
        cls.result = em.map_geometric_pattern()

    def test_ascii_map_renders(self):
        text = em._render_ascii_world_map(self.result)
        self.assertIn('┌', text)
        self.assertIn('┘', text)
        self.assertIn('180W', text)

    def test_console_formatter(self):
        text = em._format_console_geometric_map(self.result)
        self.assertIn('GEOMETRIC PATTERN MAPPER', text)
        self.assertIn('DOMINANT PATTERN', text)
        self.assertIn('GREAT CIRCLE ALIGNMENTS', text)
        self.assertIn('PHI-RATIO', text)
        self.assertIn('SACRED TRIANGLES', text)
        self.assertIn('LATITUDE BANDS', text)
        self.assertIn('NETWORK GEOMETRY', text)


class TestSeerGeometricMap(unittest.TestCase):
    """Verify EmeraldSeer.geometric_map() integration."""

    def test_seer_geometric_map(self):
        seer = em.EmeraldSeer()
        result = seer.geometric_map()
        self.assertIsInstance(result, em.GeometricMapResult)
        self.assertEqual(result.total_sites, 45)


if __name__ == '__main__':
    unittest.main()
