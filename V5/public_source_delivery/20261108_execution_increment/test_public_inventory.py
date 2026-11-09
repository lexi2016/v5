"""Prevent source-release inventories from silently pinning obsolete bytes."""
import hashlib
import json
from pathlib import Path
import unittest


class PublicInventoryIdentity(unittest.TestCase):
    def test_current_allowlisted_files_and_provenance_match(self):
        base = Path(__file__).resolve().parent.parent
        for package in ('20261108_execution_increment', '20261108_m07_source_handoff',
                        '20261108_hk_a0915_selector'):
            root = base / package
            for name in ('MANIFEST.json', 'PROVENANCE.json'):
                inventory = json.loads((root / name).read_text())
                self.assertIs(inventory['production_admitted'], False)
                self.assertIs(inventory['natural_verified'], False)
                paths = [item['path'] for item in inventory['files']]
                self.assertEqual(len(paths), len(set(paths)))
                for item in inventory['files']:
                    with self.subTest(package=package, inventory=name, path=item['path']):
                        relative = Path(item['path'])
                        self.assertFalse(relative.is_absolute())
                        self.assertNotIn('..', relative.parts)
                        raw = (root / relative).read_bytes()
                        self.assertEqual(len(raw), item['bytes'])
                        self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])


if __name__ == '__main__':
    unittest.main()
