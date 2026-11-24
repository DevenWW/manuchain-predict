"""Loopback-only CSV and Java event prediction service for local review."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import secrets
import csv
import io
import threading
import re
import time
from online_bridge import EventAssembler, FEATURES
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / 'frontend' / 'dist'
RESULTS = ROOT / 'artifacts' / 'results.json'
MODEL = ROOT / 'artifacts' / 'model.joblib'
MAX_BODY = 2 * 1024 * 1024


class Application:
    def __init__(self, model_path=MODEL, token=None, mapping=None, source='simulation'):
        self.model_path = Path(model_path)
        self.token = token or os.environ.get('MANUCHAIN_BRIDGE_TOKEN', '')
        self.mapping = mapping if mapping is not None else {f: f for f in FEATURES}
        self.source = source
        self.lock = threading.RLock()
        self.assembler = EventAssembler(self.mapping)
        self.mode = 'offline'
        self.online_enabled = False
        self.predictions = []
        self.message = 'Choose a mode. Online data requires all 15 mapped signals.'
        self._model = None
        self._metadata = None
        self._model_stamp = None

    def load(self):
        from model_runtime import load_model
        if not self.model_path.is_file():
            raise ValueError('No trained model. Train a local model first.')
        stat = self.model_path.stat()
        stamp = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
        if stamp != self._model_stamp:
            self._model, self._metadata = load_model(self.model_path)
            self._model_stamp = stamp
        return self._model, self._metadata

    def status(self):
        with self.lock:
            if self.mode == 'online':
                cutoff = time.time() - self.assembler.max_age
                self.predictions = [p for p in self.predictions if p.get('observed_at', 0) >= cutoff]
            return dict(mode=self.mode, online_enabled=self.online_enabled, predictions=list(self.predictions),
                        model_source=self.model_source(), message=self.message, online_source=self.source)

    def interface(self):
        with self.lock:
            return dict(mapping=dict(self.mapping), online_enabled=self.online_enabled,
                        online_source=self.source, message=self.message)

    def configure_mapping(self, mapping):
        if (not isinstance(mapping, dict) or len(mapping) != len(FEATURES)
                or any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name)
                       or not isinstance(feature, str) for name, feature in mapping.items())):
            raise ValueError('Mapping requires 15 valid signal names and feature names')
        assembler = EventAssembler(mapping)
        with self.lock:
            if self.online_enabled:
                raise ValueError('Stop online collection before changing the mapping')
            self.mapping = dict(mapping)
            self.assembler = assembler
            self.source = 'user-configured signals'
            if self.mode == 'online':
                self.predictions = []
            self.message = 'Mapping updated for this service session; verify its meaning before use.'
            return self.interface()

    def model_source(self):
        if not self.model_path.is_file():
            return 'No trained model'
        try:
            _, meta = self.load()
            return meta.get('source', 'unknown')
        except Exception:
            return 'Model unavailable'

    def predict(self, rows):
        from model_runtime import predict_rows
        model, _ = self.load()
        return predict_rows(model, rows)



class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=FRONTEND, results=RESULTS, app=None, **kwargs):
        self.app = app or Application()
        self.static_root = Path(directory).resolve()
        self.results_path = Path(results)
        super().__init__(*args, directory=str(self.static_root), **kwargs)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/interface':
            self.send_json(200, self.app.interface())
            return
        if path == '/api/status':
            self.send_json(200, self.app.status())
            return
        if path == '/api/results':
            try:
                data = self.results_path.read_bytes()
                json.loads(data)
            except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
                self.send_error(503, 'Experiment results unavailable')
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)
            return

        # Never expose files outside the build directory through encoded paths
        # or a symlink included in the built tree.
        parts = unquote(path).split('/')
        if any(part in ('.', '..') or '\\' in part for part in parts):
            self.send_error(404)
            return
        target = (self.static_root / unquote(path).lstrip('/')).resolve()
        if not target.is_relative_to(self.static_root):
            self.send_error(404)
            return
        super().do_GET()

    def send_json(self, status, body):
        data = json.dumps(body, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlsplit(self.path).path
        origin = self.headers.get('Origin')
        host = self.headers.get('Host', '')
        if not re.fullmatch(r'(127\.0\.0\.1|localhost):[0-9]{1,5}', host):
            self.send_json(403, {'error': 'Invalid host'})
            return
        if origin and origin not in ('http://' + host, 'https://' + host):
            self.send_json(403, {'error': 'Invalid origin'})
            return
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.send_json(403, {'error': 'Cross-site requests are not allowed'})
            return
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if length < 0 or length > MAX_BODY:
                raise ValueError('Request body is missing or too large')
            raw = self.rfile.read(length)
            if path == '/api/offline':
                if self.headers.get_content_type() != 'text/csv':
                    raise ValueError('Expected text/csv')
                reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
                if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise ValueError('Missing or duplicate CSV columns')
                rows = list(reader)
                if not rows or len(rows) > 10000:
                    raise ValueError('CSV must contain 1 to 10000 rows')
                with self.app.lock:
                    predictions = self.app.predict(rows)
                    self.app.mode = 'offline'
                    self.app.online_enabled = False
                    self.app.predictions = predictions
                    self.app.message = 'CSV predictions complete; input labels are not used.'
                    self.send_json(200, self.app.status())
                return
            if self.headers.get_content_type() != 'application/json':
                raise ValueError('Expected application/json')
            body = json.loads(raw.decode('utf-8'))
            if not isinstance(body, dict):
                raise ValueError('Expected a JSON object')
            if path == '/api/interface':
                if set(body) != {'mapping'}:
                    raise ValueError('Expected mapping')
                self.send_json(200, self.app.configure_mapping(body['mapping']))
                return
            if path == '/api/online/start':
                if not self.app.token or len(self.app.token) < 16:
                    raise ValueError('Set MANUCHAIN_BRIDGE_TOKEN to at least 16 characters and restart the server')
                if self.app.model_source() in ('No trained model', 'Model unavailable'):
                    raise ValueError('Train a trusted local model first')
                with self.app.lock:
                    self.app.mode = 'online'
                    self.app.online_enabled = True
                    self.app.assembler = EventAssembler(self.app.mapping)
                    self.app.predictions = []
                    self.app.message = 'Waiting for 15 mapped signals per device; source: ' + self.app.source
                    self.send_json(200, self.app.status())
                return
            if path == '/api/online/stop':
                with self.app.lock:
                    self.app.online_enabled = False
                    self.app.message = 'Online collection stopped.'
                    self.send_json(200, self.app.status())
                return
            if path == '/api/online/event':
                supplied = self.headers.get('X-Bridge-Token', '')
                if not self.app.token or not secrets.compare_digest(supplied.encode(), self.app.token.encode()):
                    self.send_json(403, {'error': 'Invalid bridge token'})
                    return
                with self.app.lock:
                    if not self.app.online_enabled:
                        raise ValueError('Online mode is stopped')
                    row, missing = self.app.assembler.add(body)
                    if row:
                        prediction = self.app.predict([row])[0]
                        prediction['observed_at'] = min(v[1] for v in self.app.assembler.devices[row['record_id']].values())
                        self.app.predictions = [p for p in self.app.predictions if p['record_id'] != row['record_id']]
                        self.app.predictions.append(prediction)
                        self.app.message = 'Complete device snapshot predicted; source: ' + self.app.source
                    else:
                        self.app.message = f'Waiting for {len(missing)} mapped signals for {body["device_id"]}'
                    self.send_json(200, dict(accepted=True, missing=missing, predicted=row is not None))
                return
            self.send_json(404, {'error': 'Unknown endpoint'})
        except (ValueError, KeyError, UnicodeError, json.JSONDecodeError) as error:
            self.send_json(400, {'error': str(error)})
        except Exception:
            self.send_json(500, {'error': 'Model or server error; check local logs'})

    def do_HEAD(self):
        # Keep API handling in one path and avoid filesystem path bypasses.
        self.send_error(405, 'HEAD not supported')


def make_server(port=8000, directory=FRONTEND, results=RESULTS, app=None):
    return ThreadingHTTPServer(('127.0.0.1', port),
                               partial(Handler, directory=directory, results=results, app=app or Application()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--mapping', type=Path, help='JSON map from real signal names to sensor_01...sensor_15')
    args = parser.parse_args()
    if not (FRONTEND / 'index.html').is_file():
        parser.error('frontend/dist/index.html is missing; build the frontend first')
    mapping = json.loads(args.mapping.read_text()) if args.mapping else None
    app = Application(mapping=mapping, source='configured signals' if mapping is not None else 'synthetic demonstration')
    with make_server(args.port, app=app) as server:
        print(f'Local dashboard: http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
