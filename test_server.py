import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from server import make_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.static = root / 'dist'
        self.static.mkdir()
        (self.static / 'index.html').write_text('<h1>dashboard</h1>')
        (root / 'private.txt').write_text('private')
        (self.static / 'escape').symlink_to(root / 'private.txt')
        self.result = root / 'results.json'
        self.result.write_text(json.dumps({'sample_count': 2}))
        self.server = make_server(0, self.static, self.result)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.tmp.cleanup()

    def test_serves_current_results_without_restart(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        with urlopen(self.base + '/api/results') as response:
            self.assertEqual(json.load(response)['sample_count'], 2)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.result.write_text('{"sample_count": 3}')
        with urlopen(self.base + '/api/results') as response:
            self.assertEqual(json.load(response)['sample_count'], 3)

    def test_static_file_and_denied_paths(self):
        with urlopen(self.base + '/') as response:
            self.assertIn(b'dashboard', response.read())
        for path in ['/escape', '/%2e%2e/private.txt']:
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                urlopen(self.base + path)
            self.assertEqual(error.exception.code, 404)

    def test_missing_or_invalid_results_returns_503(self):
        for contents in (None, 'not json'):
            if contents is None:
                self.result.unlink()
            else:
                self.result.write_text(contents)
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base + '/api/results')
            self.assertEqual(error.exception.code, 503)


if __name__ == '__main__':
    unittest.main()
