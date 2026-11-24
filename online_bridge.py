"""Validated, per-device assembly of explicitly mapped Java signal events."""
import math
import re
import time
from collections import OrderedDict

FEATURES = tuple(f'sensor_{i:02}' for i in range(1, 16))


class EventAssembler:
    def __init__(self, mapping, max_age=60, max_devices=100):
        if set(mapping.values()) != set(FEATURES) or len(mapping) != len(FEATURES):
            raise ValueError('Mapping must map exactly 15 distinct signals to sensor_01 through sensor_15')
        self.mapping = dict(mapping)
        self.max_age = max_age
        self.max_devices = max_devices
        self.devices = OrderedDict()

    def add(self, event, now=None):
        now = time.time() if now is None else now
        if set(event) != {'device_id', 'signal', 'value', 'timestamp'}:
            raise ValueError('Event requires device_id, signal, value and timestamp')
        device, signal, value, timestamp = (event[k] for k in ('device_id', 'signal', 'value', 'timestamp'))
        if not isinstance(device, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', device):
            raise ValueError('Invalid device_id')
        if not isinstance(signal, str) or signal not in self.mapping:
            raise ValueError('Signal not in configured mapping')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Signal value must be a finite number')
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            raise ValueError('timestamp must be Unix seconds')
        if timestamp > now + 5 or timestamp < now - self.max_age:
            raise ValueError('Event timestamp outside the permitted freshness window')
        if device not in self.devices and len(self.devices) >= self.max_devices:
            raise ValueError('Maximum number of devices reached')
        row = self.devices.setdefault(device, {})
        field = self.mapping[signal]
        if field in row and timestamp < row[field][1]:
            raise ValueError('Out-of-order event')
        row[field] = (float(value), float(timestamp))
        missing = [f for f in FEATURES if f not in row or now - row[f][1] > self.max_age]
        if missing:
            return None, missing
        return {'record_id': device, **{f: row[f][0] for f in FEATURES}}, []
