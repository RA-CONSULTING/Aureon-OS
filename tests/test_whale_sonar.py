import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from mycelium_whale_sonar import WhaleSonar, ensure_sonar

from aureon_baton_link import link_system as _baton_link
from aureon_thought_bus import Thought, ThoughtBus

_baton_link(__name__)


class TestWhaleSonar(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tb = ThoughtBus(
            persist_path=str(Path(self._tmp.name) / "thoughts.jsonl")
        )
        self._sonars = []

    def tearDown(self):
        for sonar in self._sonars:
            sonar.stop()
        self._tmp.cleanup()

    def _sonar(self, **kwargs):
        sonar = WhaleSonar(thought_bus=self.tb, **kwargs)
        self._sonars.append(sonar)
        return sonar

    def test_basic_aggregation_and_thought_publish(self):
        tb = self.tb
        ws = self._sonar(sample_window=2.0, agg_interval=0.5)
        ws.start()

        # send a burst of messages from a simulated whale
        for _ in range(5):
            tb.publish(Thought(source='kraken_client', topic='system.health', payload={'message': 'ok', 'priority': 'high'}))
            time.sleep(0.1)

        # allow aggregator to run
        time.sleep(1.2)

        # check for whale.sonar.kraken_client thought
        thoughts = tb.recall(limit=200)
        sonar_thoughts = [t for t in thoughts if t['topic'].startswith('whale.sonar.kraken_client')]
        self.assertTrue(len(sonar_thoughts) >= 1)
        pack = sonar_thoughts[-1]['payload'].get('pack', {})
        self.assertIn('score', pack)
        self.assertGreaterEqual(pack['score'], 0.0)

    def test_enigma_decode_integration(self):
        tb = self.tb
        ws = self._sonar(sample_window=2.0, agg_interval=0.5)
        # inject a fake enigma integration with a decode method.
        # enigma_integration is a read-only lazy property now, so the injection
        # seam is the backing fields, not the property itself.
        mock_enigma = MagicMock()
        fake_decoded = MagicMock()
        fake_decoded.grade.name = 'MAGIC'
        fake_decoded.confidence = 0.77
        fake_decoded.message = 'decoded-intel'
        mock_enigma.enigma.decode.return_value = fake_decoded
        ws._enigma_integration = mock_enigma
        ws._enigma_checked = True

        ws.start()
        for _ in range(3):
            tb.publish(Thought(source='wave_scanner', topic='market.signal', payload={'message': 'spike'}))
            time.sleep(0.1)

        time.sleep(1.2)
        thoughts = tb.recall(limit=300)
        enigma_thoughts = [t for t in thoughts if t['topic'].startswith('enigma.whale.wave_scanner')]
        self.assertTrue(len(enigma_thoughts) >= 1)
        self.assertIn('grade', enigma_thoughts[-1]['payload'])

    def test_thought_bus_construction_is_side_effect_free(self):
        self.assertIsNone(getattr(self.tb, '_sonar', None))

    def test_queen_alert_on_loud_whale(self):
        tb = self.tb
        ws = self._sonar(sample_window=1.0, agg_interval=0.2)
        ws.start()
        # publish many messages quickly to make a loud whale
        for _ in range(20):
            tb.publish(Thought(source='kraken_client', topic='system.health', payload={'message': 'ok', 'priority': 'high'}))
        time.sleep(0.6)
        thoughts = tb.recall(limit=500)
        alerts = [t for t in thoughts if t['topic'] == 'queen.alert.whale' and t['payload'].get('whale') == 'kraken_client']
        self.assertTrue(len(alerts) >= 1)
    def test_explicit_lifecycle_wires_sonar(self):
        sonar = ensure_sonar(self.tb, sample_window=1.0, agg_interval=0.2)
        self._sonars.append(sonar)
        self.assertIs(self.tb._sonar, sonar)
        self.assertIs(sonar.thought_bus, self.tb)
        self.assertIs(ensure_sonar(self.tb), sonar)


if __name__ == '__main__':
    unittest.main()
