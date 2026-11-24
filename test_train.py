import csv
from pathlib import Path
import tempfile
import unittest
import numpy as np
from train import FEATURES, demo_data, label_days, load_data, make_model


class DataContractTests(unittest.TestCase):
    def test_seven_day_boundary(self):
        np.testing.assert_array_equal(label_days([0, 6.99, 7, 7.01]), [1, 1, 0, 0])

    def test_target_not_in_model_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'demo.csv'
            demo_data(path)
            rows, x, y = load_data(path)
            self.assertEqual(x.shape, (240, 15))
            self.assertNotIn('remaining_days', FEATURES)
            self.assertTrue(np.isnan(x).any())
            with path.open('a', newline='') as stream:
                csv.DictWriter(stream, fieldnames=list(rows[0])).writerow(rows[0])
            with self.assertRaisesRegex(ValueError, 'unique'):
                load_data(path)

    def test_imputation_inside_each_stacking_estimator(self):
        model = make_model()
        self.assertEqual(len(model.estimators), 3)
        for _, pipeline in model.estimators:
            self.assertEqual(pipeline.steps[0][0], 'iterativeimputer')
        self.assertEqual(model.final_estimator.__class__.__name__, 'LogisticRegression')


if __name__ == '__main__':
    unittest.main()
