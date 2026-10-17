import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import samsung_brightness as app


class ConfigTests(unittest.TestCase):
    def test_ip_survives_restart_without_pairing(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(app, 'DATA_DIR', Path(folder)):
            config = {}
            app.remember_monitor_ip(config, '192.168.1.100')
            self.assertEqual(app.load_config()['monitor_ip'], '192.168.1.100')
            self.assertNotIn('protected_token', config)

    def test_draft_address_keeps_existing_pairing_and_schedule(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(app, 'DATA_DIR', Path(folder)):
            config = {'ip': '192.168.1.100', 'protected_token': 'test-only', 'schedule_enabled': True}
            app.remember_monitor_ip(config, '192.168.1.101')
            saved = app.load_config()
            self.assertEqual(saved['monitor_ip'], '192.168.1.101')
            self.assertEqual(saved['ip'], '192.168.1.100')
            self.assertEqual(saved['protected_token'], 'test-only')
            self.assertTrue(saved['schedule_enabled'])

    def test_invalid_input_does_not_overwrite_saved_address(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(app, 'DATA_DIR', Path(folder)):
            config = {}
            app.remember_monitor_ip(config, '192.168.1.100')
            with self.assertRaises(ValueError):
                app.remember_monitor_ip(config, '192.168.')
            self.assertEqual(app.load_config()['monitor_ip'], '192.168.1.100')

    def test_failed_save_does_not_mutate_live_config(self):
        config = {'monitor_ip': '192.168.1.100'}
        with patch.object(app, 'save_config', side_effect=PermissionError()):
            with self.assertRaises(PermissionError):
                app.remember_monitor_ip(config, '192.168.1.101')
        self.assertEqual(config['monitor_ip'], '192.168.1.100')
