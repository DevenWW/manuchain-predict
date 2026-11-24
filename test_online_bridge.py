import time
import unittest
from online_bridge import EventAssembler, FEATURES


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = EventAssembler({f: f for f in FEATURES})
        self.now = time.time()

    def event(self, field, value=1, timestamp=None, device='device1'):
        return dict(device_id=device, signal=field, value=value,
                    timestamp=self.now if timestamp is None else timestamp)

    def test_no_prediction_until_complete_and_same_device(self):
        for f in FEATURES[:-1]:
            record, missing = self.bridge.add(self.event(f), self.now)
            self.assertIsNone(record)
        record, _ = self.bridge.add(self.event(FEATURES[-1], device='other'), self.now)
        self.assertIsNone(record)
        record, missing = self.bridge.add(self.event(FEATURES[-1]), self.now)
        self.assertEqual(len(missing), 0)
        self.assertEqual(record['record_id'], 'device1')
        self.assertEqual(record[FEATURES[-1]], 1)

    def test_reject_unknown_invalid_or_stale(self):
        for e in (self.event('unknown'), self.event(FEATURES[0], float('nan')),
                  self.event(FEATURES[0], timestamp=self.now - 61)):
            with self.assertRaises(ValueError):
                self.bridge.add(e, self.now)

    def test_out_of_order_and_expired_fields(self):
        self.bridge.add(self.event(FEATURES[0]), self.now)
        with self.assertRaises(ValueError):
            self.bridge.add(self.event(FEATURES[0], timestamp=self.now - 1), self.now)
        record, missing = self.bridge.add(self.event(FEATURES[1], timestamp=self.now + 61), self.now + 61)
        self.assertIsNone(record)
        self.assertIn(FEATURES[0], missing)

    def test_duplicate_mapping_rejected(self):
        with self.assertRaises(ValueError):
            EventAssembler({'one': FEATURES[0]})


if __name__ == '__main__':
    unittest.main()
