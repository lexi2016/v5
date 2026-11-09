"""Verify current development evidence, never runtime authorization."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parent
MANIFEST = 'ZERO_OFFSET_PRECISION_MANIFEST_V2.json'


def verify_manifest(root, manifest):
    if manifest['schema'] != 'RETRY_ENTRY_REGRESSION_EVIDENCE_V2':
        raise ValueError('MANIFEST_SCHEMA')
    for flag in ('production_dependency_pins_changed', 'authoritative_registration_created',
                 'production_allowed', 'business_accepted', 'natural_verified'):
        if manifest[flag] is not False:
            raise ValueError('NON_AUTHORITATIVE_FLAGS')
    for item in manifest['files'] + [manifest['historical_manifest']]:
        raw = (root / item['path']).read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('MANIFEST_FILE_MISMATCH:' + item['path'])
    total = 0
    for name, expected in manifest['tests']['methods_by_file'].items():
        tree = ast.parse((root / name).read_bytes())
        actual = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test_')
                     for cls in tree.body if isinstance(cls, ast.ClassDef) for n in cls.body)
        if actual != expected:
            raise ValueError('MANIFEST_METHOD_COUNT:' + name)
        total += actual
    if total != manifest['tests']['direct_methods_per_mode']:
        raise ValueError('MANIFEST_TOTAL_COUNT')
    return True


class ManifestVersionTests(unittest.TestCase):
    def test_current_v2_inventory_and_counts(self):
        self.assertTrue(verify_manifest(ROOT, json.loads((ROOT / MANIFEST).read_bytes())))

    def test_stale_test_hash_is_rejected(self):
        manifest = json.loads((ROOT / MANIFEST).read_bytes())
        original = json.loads((ROOT / 'ZERO_OFFSET_PRECISION_MANIFEST.json').read_bytes())
        changed = copy.deepcopy(manifest)
        item = next(x for x in changed['files'] if x['path'] == 'test_zero_offset_precision.py')
        item.update(original['files']['test_zero_offset_precision.py'])
        with self.assertRaisesRegex(ValueError, '^MANIFEST_FILE_MISMATCH:test_zero_offset_precision.py$'):
            verify_manifest(ROOT, changed)

    def test_stale_method_count_is_rejected(self):
        manifest = json.loads((ROOT / MANIFEST).read_bytes())
        manifest['tests']['methods_by_file']['test_zero_offset_precision.py'] = 1
        with self.assertRaisesRegex(ValueError, '^MANIFEST_METHOD_COUNT:test_zero_offset_precision.py$'):
            verify_manifest(ROOT, manifest)


if __name__ == '__main__':
    unittest.main()
