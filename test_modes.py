import csv
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from online_bridge import FEATURES
from server import Application, make_server


class FakeApplication(Application):
    def model_source(self): return 'test model'
    def predict(self, rows):
        return [dict(record_id=row['record_id'], risk_probability=0.25, predicted_at_risk=False) for row in rows]


class ModeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = FakeApplication(token='test-token-long-enough')
        self.server = make_server(0, Path(self.tmp.name), app=self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%s' % self.server.server_port

    def tearDown(self):
        self.server.shutdown(); self.thread.join(); self.server.server_close(); self.tmp.cleanup()

    def post(self, path, data, content_type='application/json', token=None, origin=None):
        headers = {'Content-Type': content_type}
        if token: headers['X-Bridge-Token'] = token
        if origin: headers['Origin'] = origin
        payload = data.encode() if isinstance(data, str) else json.dumps(data).encode()
        with urlopen(Request(self.url + path, data=payload, headers=headers)) as response:
            return json.load(response)

    def test_offline_and_online_complete_flow(self):
        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=['record_id', *FEATURES])
        writer.writeheader(); writer.writerow({'record_id': 'csv1', **{f: 1 for f in FEATURES}})
        result = self.post('/api/offline', output.getvalue(), 'text/csv')
        self.assertEqual(result['predictions'][0]['record_id'], 'csv1')
        self.assertTrue(self.post('/api/online/start', {})['online_enabled'])
        now = time.time()
        for i, field in enumerate(FEATURES):
            response = self.post('/api/online/event', dict(device_id='java1', signal=field, value=i, timestamp=now), token=self.app.token)
            self.assertEqual(response['predicted'], i == 14)
        with urlopen(self.url + '/api/status') as response:
            status = json.load(response)
        self.assertEqual(status['predictions'][0]['record_id'], 'java1')
        self.app.predictions[0]['observed_at'] = now - 61
        with urlopen(self.url + '/api/status') as response:
            self.assertEqual(json.load(response)['predictions'], [])
        self.assertFalse(self.post('/api/online/stop', {})['online_enabled'])
        with self.assertRaises(HTTPError):
            self.post('/api/online/event', dict(device_id='java1', signal=FEATURES[0], value=1, timestamp=now), token=self.app.token)

    def test_reject_cross_origin_and_bad_token(self):
        with self.assertRaises(HTTPError) as error:
            self.post('/api/online/start', {}, origin='https://example.com')
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            self.post('/api/online/event', {}, token='wrong')
        self.assertEqual(error.exception.code, 403)

    def test_mapping_settings_are_applied_and_cannot_change_while_running(self):
        mapping = {f'plc_{i:02}': field for i, field in enumerate(FEATURES, 1)}
        with urlopen(self.url + '/api/interface') as response:
            self.assertEqual(json.load(response)['mapping'], {field: field for field in FEATURES})
        self.assertEqual(self.post('/api/interface', {'mapping': mapping})['mapping'], mapping)
        for bad in ({'bad': FEATURES[0]}, {**mapping, 'plc_01': 'sensor_02'}):
            with self.assertRaises(HTTPError) as error:
                self.post('/api/interface', {'mapping': bad})
            self.assertEqual(error.exception.code, 400)
        self.assertTrue(self.post('/api/online/start', {})['online_enabled'])
        with self.assertRaises(HTTPError):
            self.post('/api/interface', {'mapping': mapping})
        now = time.time()
        for i, signal in enumerate(mapping):
            result = self.post('/api/online/event', dict(device_id='plc1', signal=signal, value=i, timestamp=now), token=self.app.token)
        self.assertTrue(result['predicted'])


if __name__ == '__main__':
    unittest.main()
