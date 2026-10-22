"""Check the cloud hold against restored active approvals and replayed signals."""
import importlib, json, os, pathlib, sys, tempfile, unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE))
TEMP = tempfile.TemporaryDirectory()
os.environ['SERO_WORKSPACE'] = TEMP.name
os.environ['AUREON_DEPLOYMENT_HOLD'] = '1'
os.environ['AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS'] = '1'
os.environ['AUREON_AUDIT_MODE'] = '1'
from aureon_fusion import capability_gate as gate, organ_registry as registry
from aureon_radar import aureon_bridge as bridge

class CloudHoldTests(unittest.TestCase):
    def setUp(self):
        gate.FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
        gate.FLAG_FILE.write_text(gate.RELEASE_LINE)
        gate.MATRIX_FILE.parent.mkdir(parents=True, exist_ok=True)
        gate.MATRIX_FILE.write_text(json.dumps({'gates': {
            gate.PINNED_GATE: {'status':'active'},
            'network_access:fetch_public_data': {'status':'active'},
        }}))

    def test_restored_live_approval_does_not_release_cloud(self):
        self.assertFalse(gate.release_authorized())
        self.assertFalse(registry._release_granted())
        self.assertFalse(gate._check_verdict(gate.PINNED_GATE)['allowed'])
        with patch.object(registry, '_iter_matching_pids', return_value=[]), patch.object(registry.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            self.assertEqual(registry.start('aureon_radar_suite')['state'], 'held')

    def test_cloud_hold_blocks_consequential_domains(self):
        for key in ('external_communication:send_message','process_control:execute',
                    'code_generation:execute_code','network_access:scan_network'):
            with self.subTest(key=key):
                self.assertTrue(gate._check_verdict(key)['deployment_hold'])

    def test_public_fetch_still_requires_existing_matrix_approval(self):
        self.assertTrue(gate._check_verdict('network_access:fetch_public_data')['allowed'])
        gate.MATRIX_FILE.write_text('{}')
        self.assertFalse(gate._check_verdict('network_access:fetch_public_data')['allowed'])

    def test_bridge_never_starts_exchange_script_or_replays_import(self):
        bridge.TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
        bridge.TRACE_FILE.write_text('{}')
        bridge.PROMOTION_LOG.write_text('{"historical":true}\n')
        with patch.object(bridge.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            instance=bridge.AureonRadarBridge()
            self.assertIsNone(instance.start_aureon_dry_run())
        self.assertEqual(instance.last_trace_mtime, bridge.TRACE_FILE.stat().st_mtime)
        self.assertEqual(instance._promotion_offset, bridge.PROMOTION_LOG.stat().st_size)
        self.assertEqual(bridge.AUREON_DIR, pathlib.Path(TEMP.name)/'aureon-os-upstream')

    def test_imported_door_approval_does_not_respawn_process(self):
        from aureon_fusion import heartbeat_daemon
        with patch.object(heartbeat_daemon, '_door_held_open', return_value=True), patch.object(heartbeat_daemon.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            heartbeat_daemon._watch_entry({'name':'planetary_switchboard'})

if __name__ == '__main__':
    unittest.main()
