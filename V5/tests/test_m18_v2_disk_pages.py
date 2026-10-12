"""Real synthetic Bundle -> persisted layout -> publication -> HTTP regressions.

All writes are fixture setup. GET must only read already-built local artifacts.
No production input, owner execution, credentials, or external service is used.
"""
import base64
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from v5_shadow import m18_offline_v2 as m
from v5_shadow.digests import canonical_bytes
from v5_shadow.module_api import _config, create_module_server
from v5_shadow.m18_v2_publication_bridge import (
    ROUTE, descriptor_from_bundle, publish_m18_descriptor,
)


RUN = '46596b03c2ab4e29b1219fd2e5eb698f'


def fixture():
    payload = dict(target_trade_date='20261012', input_identity='b' * 64,
                   RESEARCH_ONLY=True, production_allowed=False,
                   buy_gate_updated=False, orders_sent=False,
                   gaps=['SYNTHETIC_UNAVAILABLE_INPUT'], unknown=None, empty=[],
                   materials=[{'body': 'SYNTHETIC_' * 27000}])
    saved = dict(run_id=RUN, target_trade_date=payload['target_trade_date'],
                 input_identity=payload['input_identity'], workspace=copy.deepcopy(payload))
    saved['sha256'] = m.sha(canonical_bytes(saved))
    saved_raw = canonical_bytes(saved)
    payload['plan_product'] = dict(consumed=True, run_id=RUN, sha256=saved['sha256'])
    raw = canonical_bytes(dict(payload=payload, readback=dict(
        run_id=RUN, plan_sha256=saved['sha256'], input_identity=payload['input_identity'])))
    identity = dict(run_id=RUN, target_date=payload['target_trade_date'],
                    plan_sha256=saved['sha256'], raw_sha256=m.sha(saved_raw),
                    response_sha256=m.sha(raw), input_identity=payload['input_identity'])
    bundle = m.build(raw, saved_raw, identity, expected_profile=m.PROFILE_SHA256)
    return raw, identity, bundle


class DiskPagesTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.raw, self.identity, self.bundle = fixture()
        self.bundle_root = self.root / 'bundle'
        self.bundle_root.mkdir()
        (self.bundle_root / 'objects').mkdir()
        (self.bundle_root / 'manifest.json').write_bytes(self.bundle.manifest)
        for key, value in self.bundle.objects.items():
            (self.bundle_root / 'objects' / key).write_bytes(value)
        self.publication = self.root / 'publication'
        self.publication.mkdir()
        (self.publication / '.v5-module-root').write_text('v5.module-root.v1:manager\n')
        self.config = dict(schema_version='v5.module_api.v1', module_id='manager',
            release_id='m18-v2-test', data_root=str(self.publication),
            routes=[ROUTE, ROUTE + '/pages'], m18_v2_binding=dict(
                manifest_sha256=m.sha(self.bundle.manifest), identity=self.identity,
                profile_sha256=m.PROFILE_SHA256, bundle_root=str(self.bundle_root)))
        self.reader = m.Reader(self.bundle, m.sha(self.bundle.manifest), self.identity,
                               expected_profile=m.PROFILE_SHA256)
        self.descriptor = descriptor_from_bundle(self.reader, self.identity,
                                                 json.loads(self.bundle.manifest))
        self.descriptor['generated_at'] = '2026-10-12T00:00:00+00:00'
        self.generation = publish_m18_descriptor(
            self.config, self.descriptor, expected_generation=None)['generation_sha256']

    def serve(self, config=None):
        server = create_module_server(config or self.config)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def stop():
            server.shutdown()
            server.server_close()
            thread.join(2)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)
        return 'http://127.0.0.1:' + str(server.server_address[1])

    def get(self, base, suffix=None, method='GET'):
        path = suffix if suffix is not None else ROUTE + '/pages?run_id=' + RUN + '&page=0'
        try:
            response = urlopen(Request(base + path, method=method), timeout=5)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw), dict(response.headers), len(raw)

    def snapshot(self):
        return {str(p.relative_to(self.root)): (m.sha(p.read_bytes()), p.stat().st_mtime_ns)
                for p in self.root.rglob('*') if p.is_file()}

    def test_persisted_pages_are_real_bounded_and_read_only(self):
        base = self.serve()
        before = self.snapshot()
        pieces = []
        with patch.object(m, 'build', side_effect=AssertionError('GET must not rebuild')), \
                patch('v5_shadow.module_artifacts.publish_generation',
                      side_effect=AssertionError('GET must not publish')), \
                patch('v5_shadow.m18_offline_v2_process.run',
                      side_effect=AssertionError('GET must not run offline writer')):
            self.assertEqual(self.get(base, '/__v5/module-health')[0], 200)
            status, descriptor, _, _ = self.get(base, ROUTE + '?run_id=' + RUN)
            self.assertEqual((status, descriptor), (200, self.descriptor))
            self.assertNotEqual(self.generation, descriptor['generation_id'])
            count = self.reader.overview()['content_chunks']
            self.assertGreater(count, 1)
            for page in range(count):
                status, body, headers, size = self.get(
                    base, ROUTE + '/pages?run_id=' + RUN + '&page=' + str(page))
                self.assertEqual(status, 200)
                self.assertLess(size, m.PROFILE['object_bytes'])
                self.assertEqual(body['identity'], self.identity)
                self.assertEqual(body['run_id'], RUN)
                self.assertEqual(body['page'], page)
                self.assertEqual(body['generation_id'], descriptor['generation_id'])
                self.assertEqual(body['profile_sha256'], m.PROFILE_SHA256)
                self.assertEqual(headers['X-V5-Workspace-Access'], 'READ_ONLY')
                self.assertEqual(headers['X-V5-Record-SHA256'], m.sha(canonical_bytes(body)))
                self.reader.verify_content(body['content'], expected_index=page)
                pieces.append(base64.b64decode(body['content']['data'], validate=True))
        self.assertEqual(b''.join(pieces), self.raw)
        self.assertIn(b'SYNTHETIC_UNAVAILABLE_INPUT', b''.join(pieces))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.get(base, method='POST')[0], 405)

    def test_binding_mismatches_fail_closed(self):
        for field in self.identity:
            config = copy.deepcopy(self.config)
            config['m18_v2_binding']['identity'][field] = '0' * len(self.identity[field])
            with self.subTest(field=field):
                if field == 'run_id':
                    with self.assertRaises(ValueError):
                        create_module_server(config)
                else:
                    self.assertEqual(self.get(self.serve(config))[0], 409)
        for field in ('manifest_sha256', 'profile_sha256'):
            config = copy.deepcopy(self.config)
            config['m18_v2_binding'][field] = '0' * 64
            with self.subTest(field=field):
                self.assertEqual(self.get(self.serve(config))[0], 409)

    def test_missing_or_invalid_binding_rejected_at_admission(self):
        for binding in (None, {}, {'bundle': {}}, 'invalid'):
            config = copy.deepcopy(self.config)
            if binding is None:
                config.pop('m18_v2_binding')
            else:
                config['m18_v2_binding'] = binding
            with self.subTest(binding=binding), self.assertRaises((ValueError, KeyError)):
                _config(config)

    def test_bad_page_and_unknown_run_never_return_empty_success(self):
        base = self.serve()
        for suffix in ('', '&page=-1', '&page=x', '&page=999', '&page=0&extra=1'):
            with self.subTest(query=suffix):
                self.assertEqual(self.get(base, ROUTE + '/pages?run_id=' + RUN + suffix)[0], 409)
        self.assertEqual(self.get(base, ROUTE + '/pages?run_id=' + '0'*32 + '&page=0')[0], 503)

    def test_missing_and_tampered_object_fail_closed(self):
        base = self.serve()
        key, raw = next(iter(self.bundle.objects.items()))
        path = self.bundle_root / 'objects' / key
        path.unlink()
        self.assertEqual(self.get(base)[0], 409)
        path.write_bytes(b'{}')
        self.assertEqual(self.get(base)[0], 409)
        path.write_bytes(raw)
        self.assertEqual(self.get(base)[0], 200)

    def test_invalid_object_name_type_and_size_fail_closed(self):
        base = self.serve()
        path = self.bundle_root / 'objects' / ('f' * 64)
        for kind in ('extra', 'oversize', 'fifo', 'symlink', 'directory', 'name'):
            with self.subTest(kind=kind):
                target = path if kind != 'name' else path.with_suffix('.json')
                if kind == 'extra' or kind == 'name':
                    target.write_bytes(b'{}')
                elif kind == 'oversize':
                    with target.open('wb') as stream:
                        stream.truncate(m.PROFILE['object_bytes'])
                elif kind == 'fifo':
                    os.mkfifo(target)
                elif kind == 'symlink':
                    target.symlink_to(self.bundle_root / 'manifest.json')
                else:
                    target.mkdir()
                try:
                    self.assertEqual(self.get(base)[0], 409)
                finally:
                    if kind == 'directory':
                        target.rmdir()
                    else:
                        target.unlink()

    def test_descriptor_generation_and_date_are_verified(self):
        for field, value in (('generation_id', 'f'*64), ('target_date', '20261011'),
                             ('pages_route', '/wrong'), ('status', 'NOT_READY')):
            descriptor = dict(self.descriptor, **{field: value})
            self.generation = publish_m18_descriptor(
                self.config, descriptor, expected_generation=self.generation)['generation_sha256']
            with self.subTest(field=field):
                self.assertEqual(self.get(self.serve())[0], 409)


if __name__ == '__main__':
    unittest.main()
