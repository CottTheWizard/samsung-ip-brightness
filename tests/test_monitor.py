import json
import unittest
from unittest.mock import patch, MagicMock

from samsung_brightness import Monitor, clamp, validate_ip, protect
import sys


class MonitorTests(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(clamp(-4), 0)
        self.assertEqual(clamp(99), 50)
        self.assertEqual(clamp(15), 15)

    def test_ip_validation(self):
        self.assertEqual(validate_ip(' 192.168.1.100 '), '192.168.1.100')
        for bad in ('example.com', '', '127.0.0.1', '0.0.0.0', '224.0.0.1', '::1'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_ip(bad)

    @patch('samsung_brightness.http.client.HTTPSConnection')
    def test_pairing_omits_token_and_extra_headers(self, connection):
        response = connection.return_value.getresponse.return_value
        response.status = 200
        response.read.return_value = b'{"result":{"AccessToken":"test-only"}}'
        self.assertEqual(Monitor('192.168.1.100').call('createAccessToken')['AccessToken'], 'test-only')
        conn = connection.return_value
        body = json.loads(conn.send.call_args.args[0])
        self.assertNotIn('params', body)
        conn.putrequest.assert_called_once_with('POST', '/', skip_accept_encoding=True)
        conn.close.assert_called_once()

    @patch('samsung_brightness.http.client.HTTPSConnection')
    def test_panel_command_and_readback(self, connection):
        response = connection.return_value.getresponse.return_value
        response.status = 200
        response.read.return_value = b'{"result":{"backlight":50}}'
        monitor = Monitor('192.168.1.100', 'test-only')
        self.assertEqual(monitor.set(90), 50)
        bodies = [json.loads(call.args[0]) for call in connection.return_value.send.call_args_list]
        self.assertEqual(bodies[0]['method'], 'backlightControl')
        self.assertEqual(bodies[0]['params'], {'AccessToken': 'test-only', 'backlight': 50})
        self.assertEqual(bodies[1]['params'], {'AccessToken': 'test-only'})

    @patch('samsung_brightness.http.client.HTTPSConnection')
    def test_errors_do_not_leak_response_payload(self, connection):
        response = connection.return_value.getresponse.return_value
        response.status = 200
        for code in (-32010, -32700, -32601, -32001, -32002, -32003, -999):
            response.read.return_value = json.dumps({'error': {'code': code, 'message': 'secret-canary'}}).encode()
            with self.subTest(code=code), self.assertRaises(RuntimeError) as error:
                Monitor('192.168.1.100', 'test-only').read()
            self.assertNotIn('secret-canary', str(error.exception))

    @patch('samsung_brightness.http.client.HTTPSConnection')
    def test_timeout_closes_connection(self, connection):
        connection.return_value.getresponse.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            Monitor('192.168.1.100', 'test-only').read()
        connection.return_value.close.assert_called_once()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows DPAPI only')
    def test_dpapi_roundtrip(self):
        data = b'test-token-not-a-real-credential'
        encrypted = protect(data)
        self.assertNotIn(data, encrypted)
        self.assertEqual(protect(encrypted, decrypt=True), data)


if __name__ == '__main__':
    unittest.main()
