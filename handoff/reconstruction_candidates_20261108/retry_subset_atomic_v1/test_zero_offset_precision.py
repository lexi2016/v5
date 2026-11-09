"""Real-entry synthetic regression for the upstream fractional-offset guard."""
import copy
import dataclasses
import datetime as dt
import hashlib
import stat
import tempfile
import json
from pathlib import Path
import unittest

import test_entrypoint as entry_fixtures
from subset_plan import aware, canonical


class ZeroOffsetPrecisionTests(unittest.TestCase):
    @staticmethod
    def ledger_snapshot(root):
        result = {}
        for path in [root, *sorted(root.rglob('*'))]:
            info = path.lstat()
            if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                raise ValueError('UNEXPECTED_LEDGER_FILE_TYPE')
            result[str(path.relative_to(root))] = (
                info.st_dev, info.st_ino, info.st_mode, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest()
                if stat.S_ISREG(info.st_mode) else None)
        return result

    def check_unavailable(self, node, local_time, utc_time, separator):
        fixture = entry_fixtures.EntryTests(); fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.now = dt.datetime.fromisoformat('2026-11-09T' + local_time + '+08:00')
        original_path = Path(fixture.binding['original_binding']['contract_ref']['path'])
        original = json.loads(original_path.read_bytes())
        original['available_after'] = '2026-11-09T' + utc_time + '-00:00:00' + separator + '000001'
        new_original = fixture.put('original-contract.json', canonical(original))
        fixture.binding['original_binding']['contract_ref'] = new_original.as_dict()
        fixture.contract['binding'] = copy.deepcopy(fixture.binding)
        fixture.evidence['binding'] = copy.deepcopy(fixture.binding)
        new_contract = fixture.put('subset-contract.json', canonical(fixture.contract))
        fixture.approval['binding'] = copy.deepcopy(fixture.binding)
        fixture.approval['contract_ref'] = new_contract.as_dict()
        new_approval = fixture.put('approval.json', canonical(fixture.approval))
        new_review = fixture.put('review-1.json', canonical(fixture.evidence))
        fixture.registration = dataclasses.replace(
            fixture.registration, contract_ref=new_contract, approval_ref=new_approval,
            reconciliation_refs={'retry-1610': new_review, 'retry-1640': new_review})
        before = self.ledger_snapshot(fixture.root)
        with self.assertRaisesRegex(ValueError, '^UNSUPPORTED_ZERO_FRACTIONAL_OFFSET$'):
            entry_fixtures.entry._preflight(fixture.registration, node)
        self.assertEqual(self.ledger_snapshot(fixture.root), before)
        result = fixture.dispatch(node, execute=True)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['phase'], 'PREFLIGHT')
        self.assertEqual(result['reason'], 'ValueError:UNSUPPORTED_ZERO_FRACTIONAL_OFFSET')
        self.assertEqual(fixture.calls, [])
        self.assertEqual(fixture.events, [])
        self.assertEqual(self.ledger_snapshot(fixture.root), before)
        self.assertFalse(result['production_allowed'])

    def test_1610_actual_entry_refusal(self):
        for separator in ('.', ','):
            with self.subTest(separator=separator):
                self.check_unavailable('retry-1610', '16:10:00', '08:10:00', separator)

    def test_1640_actual_entry_refusal(self):
        for separator in ('.', ','):
            with self.subTest(separator=separator):
                self.check_unavailable('retry-1640', '16:40:00', '08:40:00', separator)

    def test_recursive_snapshot_detects_nested_same_size_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'day' / 'claim'
            nested.parent.mkdir()
            nested.write_bytes(b'old')
            before = self.ledger_snapshot(root)
            nested.write_bytes(b'new')
            after = self.ledger_snapshot(root)
            self.assertEqual(set(before), set(after))
            self.assertNotEqual(before['day/claim'][-1], after['day/claim'][-1])
            self.assertNotEqual(before, after)

    def test_published_precision_manifest_bytes(self):
        root = Path(__file__).parent
        manifest = json.loads((root / 'ZERO_OFFSET_MANIFEST.json').read_bytes())
        for item in manifest['files']:
            with self.subTest(path=item['path']):
                raw = (root / item['path']).read_bytes()
                self.assertEqual(len(raw), item['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])


if __name__ == '__main__':
    unittest.main()
