import math
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.dummy import DummyClassifier
import joblib

from model_runtime import FEATURES, SCHEMA_VERSION, load_model, predict_rows


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.model = DummyClassifier(strategy='prior').fit(np.zeros((4, 15)), [0, 0, 1, 1])
        self.row = {'record_id': 'D1', **{key: 1.0 for key in FEATURES}}

    def test_predict_unlabelled_input_and_missing_value(self):
        row = {**self.row, FEATURES[0]: None}
        result = predict_rows(self.model, [row])
        self.assertEqual(result, [dict(record_id='D1', risk_probability=.5, predicted_at_risk=True)])

    def test_reject_invalid_data(self):
        incomplete = self.row.copy()
        del incomplete[FEATURES[0]]
        for rows in ([incomplete], [{**self.row, FEATURES[0]: math.inf}],
                     [{**self.row, FEATURES[0]: True}], [self.row, self.row], []):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                predict_rows(self.model, rows)

    def test_trusted_artifact_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'model.joblib'
            metadata = {'schema_version': SCHEMA_VERSION, 'features': FEATURES, 'source': 'test'}
            joblib.dump({'model': self.model, 'metadata': metadata}, path)
            model, loaded = load_model(path)
            self.assertEqual(loaded['source'], 'test')
            self.assertEqual(predict_rows(model, [self.row])[0]['record_id'], 'D1')
            metadata['features'] = FEATURES[::-1]
            joblib.dump({'model': self.model, 'metadata': metadata}, path)
            with self.assertRaisesRegex(ValueError, 'schema'):
                load_model(path)


if __name__ == '__main__':
    unittest.main()
