"""Synthetic one-stock observations and source event receipts, never live HK data."""
import dataclasses
import datetime as dt
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
import capture as m


class CloseEventTests(unittest.TestCase):
    def fixture(self, root, *, end='16:09:11', synthetic=True):
        stamp = '2026-11-06T' + end + '+08:00'
        scope = ['HK.00001']
        source = {'schema': 'HK_OBSERVATION_V1', 'node': 'hk-auction-final',
                  'day': '20261106', 'scope': scope, 'source_reference': 'SYNTHETIC_SOURCE',
                  'observed_at': stamp, 'available_at': stamp, 'actual_cas_end': stamp,
                  'rows': [{'symbol': scope[0], 'observation': 'SYNTHETIC ONLY'}],
                  'data_kind': 'SYNTHETIC_TEST' if synthetic else 'RECORDED_INPUT'}
        b = m.Binding('hk-auction-final', '20261106', tuple(scope), 'SYNTHETIC_SOURCE',
                      'a'*64, 'b'*64, m.sha(m.encode(scope)), 'c'*64, 'SYNTHETIC_ENV',
                      'SYNTHETIC_JOB', Path(root), lambda _: True, lambda: None,
                      nullcontext, lambda: m.encode(source),
                      lambda: dt.datetime.fromisoformat(stamp), synthetic)
        event = {'schema': 'HK_CAS_TERMINATION_EVENT_V1', 'event_id': 'synthetic-event-1',
                 'day': b.day, 'source_reference': b.source_reference,
                 'scope_sha256': b.scope_sha256, 'data_kind': source['data_kind'],
                 'continuous_close_at': '2026-11-06T16:00:00+08:00',
                 'actual_cas_end': stamp, 'available_at': stamp}
        return b, source, event

    def bound(self, b, event):
        fields = {f.name for f in dataclasses.fields(b)}
        self.assertIn('cas_event_ref', fields, 'Real event receipt has no binding')
        raw = m.encode(event)
        return dataclasses.replace(b, cas_event_ref={'path': 'cas.json', 'bytes': len(raw),
                                    'sha256': m.sha(raw)}, read_cas_event=lambda ref: raw)

    def test_non_synthetic_timestamp_alone_is_not_actual_event(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root, synthetic=False)
            with self.assertRaisesRegex(ValueError, 'ACTUAL_CAS_EVENT_BINDING_REQUIRED'):
                m.execute(b)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_verified_source_event_not_fixed_1610_end_and_reuse(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root, end='16:10:05')
            b = self.bound(b, event)
            result = m.execute(b)
            self.assertEqual(result['source']['actual_cas_end'], '2026-11-06T16:10:05+08:00')
            self.assertFalse(result['natural_verified'])
            self.assertTrue(m.execute(b)['reused'])

    def test_event_cannot_cross_source_scope_or_day(self):
        for field, value in [('source_reference', 'OTHER'), ('scope_sha256', 'd'*64),
                             ('day', '20261105'), ('actual_cas_end', '2026-11-06T16:09:00+08:00')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as root:
                b, source, event = self.fixture(root)
                event[field] = value
                with self.assertRaises(ValueError): m.execute(self.bound(b, event))

    def test_event_byte_change_blocks_cold_reuse(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root)
            b = self.bound(b, event)
            m.execute(b)
            b = dataclasses.replace(b, read_cas_event=lambda ref: b'{}')
            with self.assertRaisesRegex(ValueError, 'CAS_EVENT_PIN_CHANGED'): m.execute(b)

    def test_continuous_close_has_no_cas_terminal(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root, end='16:00:00')
            source.update(node='hk-continuous-close', actual_cas_end=None)
            b = dataclasses.replace(b, node='hk-continuous-close')
            self.assertEqual(m.execute(b)['status'], 'OBSERVATION_SAVED')
            source['actual_cas_end'] = source['observed_at']
            with self.assertRaises(ValueError): m.validate(b, source, b.clock())

    def test_later_event_proof_keeps_effective_final_availability(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root)
            event['available_at'] = '2026-11-06T16:09:15+08:00'
            b = dataclasses.replace(self.bound(b, event),
                clock=lambda: dt.datetime.fromisoformat('2026-11-06T16:10:00+08:00'))
            result = m.execute(b)
            self.assertEqual(result['source']['available_at'], '2026-11-06T16:09:11+08:00')
            self.assertEqual(result.get('effective_final_available_at'), '2026-11-06T16:09:15+08:00')
            self.assertEqual(result.get('cas_event_available_at'), '2026-11-06T16:09:15+08:00')
            self.assertTrue(m.execute(b)['reused'])
            saved = next(Path(root).glob('*.json'))
            import json
            doc = json.loads(saved.read_bytes())
            doc['effective_final_available_at'] = source['available_at']
            saved.write_bytes(m.encode(doc))
            with self.assertRaisesRegex(ValueError, 'SAVED_CAS_AVAILABILITY_CHANGED'):
                m.execute(b)

    def test_bad_event_pin_blocks_before_source_collection(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root)
            b = self.bound(b, event)
            pin = dict(b.cas_event_ref, sha256='0'*64)
            calls = []
            b = dataclasses.replace(b, cas_event_ref=pin,
                collect=lambda: (calls.append('collected'), m.encode(source))[1])
            with self.assertRaisesRegex(ValueError, 'CAS_EVENT_PIN_CHANGED'): m.execute(b)
            self.assertEqual(calls, [])

    def test_event_must_follow_the_bound_1600_continuous_close(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root, end='16:10:00')
            source['actual_cas_end'] = '2026-11-06T09:01:00+08:00'
            event.update(continuous_close_at='2026-11-06T09:00:00+08:00',
                         actual_cas_end=source['actual_cas_end'])
            with self.assertRaisesRegex(ValueError, 'CAS_CONTINUOUS_CLOSE_BINDING'):
                m.execute(self.bound(b, event))

    def test_explicit_owner_gate_denial_never_collects(self):
        with tempfile.TemporaryDirectory() as root:
            b, source, event = self.fixture(root)
            calls = []
            b = dataclasses.replace(self.bound(b, event), gate=lambda: False,
                collect=lambda: (calls.append('collected'), m.encode(source))[1])
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_RESOURCE_GATE_DENIED'):
                m.execute(b)
            self.assertEqual(calls, [])
            self.assertEqual(list(Path(root).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
