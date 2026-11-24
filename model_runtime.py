"""Fit a separate prediction model and score records without outcome labels.

Model files use joblib, which can execute code during loading. Only load a
trusted, locally created artifact; never accept model paths from web requests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import joblib
import numpy as np

from train import FEATURES, load_data, make_model

ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = 1


def _matrix(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('records must be a nonempty list')
    values, ids = [], []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('each record must be an object')
        ident = row.get('record_id')
        if not isinstance(ident, str) or not ident.strip():
            raise ValueError('record_id must be a nonempty string')
        ids.append(ident)
        missing = [name for name in FEATURES if name not in row]
        if missing:
            raise ValueError('missing features: ' + ', '.join(missing))
        sample = []
        for name in FEATURES:
            value = row[name]
            if value is None or value == '':
                sample.append(float('nan'))
            else:
                if isinstance(value, bool):
                    raise ValueError(f'{name} must be numeric or null')
                try:
                    value = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f'{name} must be numeric or null') from exc
                if not np.isfinite(value):
                    raise ValueError(f'{name} must be finite or null')
                sample.append(value)
        if all(np.isnan(sample)):
            raise ValueError('all features missing for record ' + ident)
        values.append(sample)
    if len(set(ids)) != len(ids):
        raise ValueError('record_id must be unique within each request')
    return ids, np.asarray(values, dtype=float)


def predict_rows(model, rows):
    """Score records using a previously trained model; no ground truth required."""
    ids, matrix = _matrix(rows)
    classes = list(model.classes_)
    if 1 not in classes:
        raise ValueError('model has no positive class')
    probabilities = model.predict_proba(matrix)[:, classes.index(1)]
    if not np.isfinite(probabilities).all() or (probabilities < 0).any() or (probabilities > 1).any():
        raise ValueError('model returned invalid probabilities')
    return [dict(record_id=ident, risk_probability=float(p),
                 predicted_at_risk=bool(p >= 0.5)) for ident, p in zip(ids, probabilities)]


def load_model(path):
    """Load ONLY a trusted local joblib artifact (never a user-provided upload)."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('model artifact must be an existing non-symlink file')
    artifact = joblib.load(path)  # joblib executes code: trusted local files only.
    if not isinstance(artifact, dict) or not isinstance(artifact.get('metadata'), dict):
        raise ValueError('invalid model artifact')
    metadata = artifact['metadata']
    if metadata.get('schema_version') != SCHEMA_VERSION or metadata.get('features') != FEATURES:
        raise ValueError('model feature schema mismatch')
    model = artifact.get('model')
    if not callable(getattr(model, 'predict_proba', None)) or not hasattr(model, 'classes_'):
        raise ValueError('invalid fitted model')
    return model, metadata


def train_and_save(csv_path, output, source):
    """Refit on all labelled training rows. CV results remain separate."""
    csv_path, output = Path(csv_path), Path(output)
    if source not in ('demo', 'user'):
        raise ValueError('source must be demo or user')
    if source == 'demo' and csv_path.resolve() != (ROOT / 'data/demo.csv').resolve():
        raise ValueError('demo source is restricted to the generated demo.csv')
    _, x, y = load_data(csv_path)
    model = make_model()
    model.fit(x, y)
    metadata = dict(schema_version=SCHEMA_VERSION, features=list(FEATURES),
        source='synthetic demonstration' if source == 'demo' else 'user supplied training CSV',
        training_rows=len(y), training_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        label='remaining_days < 7', threshold=0.5,
        caveat='Local refit for prediction; not the original thesis model or proof of real-world performance.')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.model-', suffix='.tmp', dir=output.parent)
    os.close(fd)
    try:
        joblib.dump({'model': model, 'metadata': metadata}, name)
        os.replace(name, output)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    training = commands.add_parser('train', help='Fit a model from labelled local CSV')
    training.add_argument('--csv', type=Path, required=True)
    training.add_argument('--output', type=Path, default=ROOT/'artifacts/model.joblib')
    training.add_argument('--source', choices=['demo', 'user'], required=True)
    args = parser.parse_args()
    print(json.dumps(train_and_save(args.csv, args.output, args.source), indent=2))


if __name__ == '__main__':
    main()
