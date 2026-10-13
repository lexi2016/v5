"""Synthetic-only publication regression; no owner execution or source input."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from v5_shadow.digests import sha256_json
from v5_shadow.module_api import (M04_ROUTE, M07_ROUTE, M11_ROUTE, M12_ROUTE,
    M16_ROUTE, M17_ROUTE, _config, read_response, response_key)
from v5_shadow.module_artifacts import publish_generation
from v5_shadow.source_bundle import STATUS_ROUTE, publish_source_result, run_source_bundle
from v5_shadow.m11.owner_sources import BUILD_MANIFEST_SHA


class SourceBundlePublicationRouteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='p0-route-synthetic-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / '.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.routes = [STATUS_ROUTE, M04_ROUTE, M07_ROUTE, M11_ROUTE, M12_ROUTE,
            M16_ROUTE, M17_ROUTE, '/api/v5/source-bundle/hk-preselection',
            '/api/v5/source-bundle/hk-close-review', '/api/v5/source-bundle/a-close-replay',
            '/api/v5/source-bundle/hk-stage-observed',
            '/api/v5/source-bundle/rebound-saved', '/api/v5/research/lane',
            '/api/v5/research/wechat/materials', '/api/v5/source-bundle/us-mapping-saved']
        digest = sha256_json({'fixture': 'SYNTHETIC_ROUTE_METADATA_ONLY'})
        python = str(Path(sys.executable).resolve())
        # These existing validators check metadata only. No saved owner result
        # is claimed, read, generated, or published by these fixture bindings.
        self.config = dict(schema_version='v5.module_api.v1', module_id='source_bundle',
            release_id='synthetic-route-regression', data_root=str(self.root), routes=self.routes,
            m04_saved_research_binding=dict(archive_root=str(self.root/'m04'), python_executable=python),
            m07_a_stage_binding=dict(output_root=str(self.root/'m07'), python_executable=python,
                python_sha256=hashlib.sha256(Path(python).read_bytes()).hexdigest(), data_kind='SYNTHETIC',
                references=[dict(generation=digest, target_date='20261013', stage_id='STAGE_0925',
                    run_id='synthetic-route', artifact_sha256=digest, manifest_sha256=digest,
                    receipt_sha256=digest)]),
            m11_saved_research_binding=dict(archive_root=str(self.root/'m11'),
                identity=dict(target_date='2026-10-13', slot='15:00',
                    cutoff='2026-10-13T15:00:00+08:00', trigger='capture', run_id='synthetic-route',
                    input_sha=digest, config_sha=digest, code_sha=digest, source_sha=BUILD_MANIFEST_SHA),
                operation='capture', commit_sha256=digest, data_kind='SYNTHETIC', python_executable=python),
            m12_video_fupan_binding=dict(private_root=str(self.root/'m12'), trade_date='20261013',
                run_id='synthetic-route', manifest_sha256=digest, owner_receipt_sha256=digest,
                data_kind='SYNTHETIC', python_executable=python),
            m16_saved_public_research_binding=dict(private_root=str(self.root/'m16'),
                trade_date='20261013', input_identity=digest, job_id='synthetic-route',
                generation='synthetic-route', attempt=1, commit_sha256=digest,
                commit_file_sha256=digest, data_kind='SYNTHETIC', python_executable=python))
        self.result = run_source_bundle(dict(schema_version='v5.source_bundle.request.v1',
            data_kind='SYNTHETIC', jobs={}))

    def tree(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def seed_siblings(self):
        records = []
        for route in self.routes[1:]:
            payload = dict(fixture='SYNTHETIC_SAVED_RECORD_RETENTION_ONLY', route=route)
            records.append(dict(schema_version='v5.module_response.v1', module_id='source_bundle',
                release_id=self.config['release_id'], path=route, query={}, payload=payload,
                payload_sha256=sha256_json(payload), source_input_sha256=sha256_json(payload),
                data_kind='SYNTHETIC', generated_at='2026-10-13T00:00:00Z', status_code=200))
        publication = publish_generation(self.config, records, expected_generation=None)
        path = self.root/'generations'/(publication['generation_sha256']+'.json')
        return publication['generation_sha256'], json.loads(path.read_bytes())['records']

    def test_current_route_inventory_publishes_status_and_preserves_siblings_and_bindings(self):
        previous, siblings = self.seed_siblings()
        before = self.tree()
        config_before = copy.deepcopy(self.config)
        publication = publish_source_result(self.result, self.config, expected_generation=previous)
        self.assertEqual(publication['previous_generation'], previous)
        self.assertTrue(publication['changed'])
        self.assertEqual(self.config, config_before)
        current = json.loads((self.root/'active.json').read_bytes())['generation_sha256']
        self.assertEqual(current, publication['generation_sha256'])
        records = json.loads((self.root/'generations'/(current+'.json')).read_bytes())['records']
        key = response_key('source_bundle', STATUS_ROUTE, {})
        self.assertEqual(set(records), set(siblings)|{key})
        for sibling, digest in siblings.items():
            self.assertEqual(records[sibling], digest)
        for relative, raw in before.items():
            if relative != 'active.json':
                self.assertEqual((self.root/relative).read_bytes(), raw, relative)
        checked, fd = _config(self.config)
        try:
            record, _ = read_response(checked, fd, STATUS_ROUTE, {})
        finally:
            os.close(fd)
        self.assertEqual(record['payload'], self.result)
        self.assertTrue(all(row['status']=='BLOCKED_REQUEST_MISSING' for row in record['payload']['modules']))
        self.assertFalse(record['payload']['production_allowed'])

    def test_unknown_route_still_rejected_without_writes(self):
        previous, _ = self.seed_siblings()
        before = self.tree()
        config = copy.deepcopy(self.config)
        config['routes'].append('/api/v5/source-bundle/not-registered')
        with self.assertRaisesRegex(ValueError, '^SOURCE_MODULE_ID_REQUIRED$'):
            publish_source_result(self.result, config, expected_generation=previous)
        self.assertEqual(self.tree(), before)

    def test_stale_generation_still_rejected_without_writes(self):
        self.seed_siblings()
        before = self.tree()
        with self.assertRaisesRegex(ValueError, '^GENERATION_CONFLICT$'):
            publish_source_result(self.result, self.config, expected_generation=None)
        self.assertEqual(self.tree(), before)

    def test_status_route_and_source_module_identity_remain_required(self):
        previous, _ = self.seed_siblings()
        before = self.tree()
        missing_status = copy.deepcopy(self.config)
        missing_status['routes'].remove(STATUS_ROUTE)
        wrong_module = dict(self.config, module_id='manager')
        for config in (missing_status, wrong_module):
            with self.subTest(module=config['module_id'], routes=config['routes']):
                with self.assertRaisesRegex(ValueError, '^SOURCE_MODULE_ID_REQUIRED$'):
                    publish_source_result(self.result, config, expected_generation=previous)
                self.assertEqual(self.tree(), before)

    def test_invalid_existing_binding_still_rejected_without_writes(self):
        previous, _ = self.seed_siblings()
        before = self.tree()
        config = copy.deepcopy(self.config)
        config['m16_saved_public_research_binding']['attempt'] = 0
        with self.assertRaisesRegex(ValueError, '^M16_ATTEMPT$'):
            publish_source_result(self.result, config, expected_generation=previous)
        self.assertEqual(self.tree(), before)


if __name__ == '__main__':
    unittest.main()
