"""Bounded semantic read-only pages, never a full payload or invented success."""
import hashlib
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
import test_m18_v2_disk_pages as base
from v5_shadow import m18_offline_v2 as m
from v5_shadow.digests import canonical_bytes
RUN = base.RUN
from v5_shadow.m18_v2_publication_bridge import ROUTE


class SemanticPagesTests(unittest.TestCase):
    serve = base.DiskPagesTests.serve
    get = base.DiskPagesTests.get
    snapshot = base.DiskPagesTests.snapshot

    def setUp(self):
        raw, _, _ = base.fixture()
        payload = json.loads(raw)['payload']
        del payload['plan_product']
        payload['gaps'] += ['SYNTHETIC_GAP_' + str(i) for i in range(69)]
        payload['medium'] = [{'text': 'synthetic ' * 1000} for _ in range(32)]
        saved = dict(run_id=RUN, target_trade_date=payload['target_trade_date'],
                     input_identity=payload['input_identity'], workspace=payload.copy())
        saved['sha256'] = m.sha(canonical_bytes(saved))
        saved_raw = canonical_bytes(saved)
        payload['plan_product'] = dict(consumed=True, run_id=RUN, sha256=saved['sha256'])
        raw = canonical_bytes(dict(payload=payload, readback=dict(
            run_id=RUN, plan_sha256=saved['sha256'], input_identity=payload['input_identity'])))
        identity = dict(run_id=RUN,target_date=payload['target_trade_date'],
            plan_sha256=saved['sha256'],raw_sha256=m.sha(saved_raw),
            response_sha256=m.sha(raw),input_identity=payload['input_identity'])
        bundle = m.build(raw,saved_raw,identity,expected_profile=m.PROFILE_SHA256)
        with patch.object(base, 'fixture', return_value=(raw,identity,bundle)):
            base.DiskPagesTests.setUp(self)

    def start(self):
        self.config['routes'] += [ROUTE + '/overview', ROUTE + '/sections']
        return self.serve()

    def path(self, suffix, **query):
        return ROUTE + suffix + '?' + urlencode(dict(
            run_id=RUN, generation_id=self.descriptor['generation_id'], **query))

    def test_overview_and_small_saved_values_match_pinned_reader(self):
        base = self.start()
        before = self.snapshot()
        with patch('v5_shadow.m18_offline_v2.Reader.full_response', side_effect=AssertionError('no full response')):
            status, body, _, size = self.get(base, self.path('/overview'))
            self.assertEqual(status, 200)
            self.assertEqual(body, self.reader.overview())
            self.assertLess(size, 256 * 1024)
            for section, expected in [('gaps', 'SYNTHETIC_UNAVAILABLE_INPUT'), ('unknown', None), ('orders_sent', False)]:
                status, body, _, size = self.get(base, self.path('/sections', section=section))
                self.assertEqual(status, 200)
                self.assertEqual(body['identity'], self.identity)
                self.assertEqual(body['generation_id'], self.descriptor['generation_id'])
                self.assertEqual(body['profile_sha256'], self.descriptor['profile_sha256'])
                self.assertEqual(body['entries'][0]['value'], expected)
                self.assertEqual(body['entries'][0]['value_state'], 'LOADED')
                raw = b''.join(self.reader.item_parts(section, 0))
                self.assertEqual(body['entries'][0]['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertLess(size, 256 * 1024)
        self.assertEqual(before, self.snapshot())

    def test_oversized_item_is_not_loaded_and_empty_array_stays_empty(self):
        base = self.start()
        status, body, _, _ = self.get(base, self.path('/sections', section='materials'))
        self.assertEqual(status, 200)
        self.assertEqual(body['entries'][0]['value_state'], 'NOT_LOADED')
        self.assertEqual(body['entries'][0]['reason'], 'ITEM_BYTES_LIMIT')
        self.assertNotIn('value', body['entries'][0])
        self.assertEqual(body['not_loaded_count'], 1)
        status, body, _, _ = self.get(base, self.path('/sections', section='empty'))
        self.assertEqual(status, 200)
        self.assertEqual(body['entries'], [])
        self.assertEqual(body['matched_total'], 0)
        self.assertIsNone(body['next_cursor'])

    def test_query_binding_and_unknown_sections_fail_closed(self):
        base = self.start()
        for path in [ROUTE+'/overview?run_id='+RUN,
                     ROUTE+'/overview?'+urlencode(dict(run_id=RUN,generation_id='0'*64)),
                     self.path('/overview', extra='1'),
                     self.path('/sections',section='does_not_exist'),
                     self.path('/sections',section='gaps',cursor='invalid')]:
            with self.subTest(path=path):
                self.assertEqual(self.get(base,path)[0],409)
        self.assertEqual(self.get(base,self.path('/overview'),method='POST')[0],405)

    def test_opaque_cursor_paginates_exact_saved_entries_and_rejects_cross_section(self):
        base_url = self.start()
        status, first, _, _ = self.get(base_url, self.path('/sections', section='gaps'))
        self.assertEqual(status, 200)
        self.assertEqual(len(first['entries']), 32)
        self.assertEqual(first['remaining_entries'], 38)
        status, second, _, _ = self.get(base_url, self.path('/sections', section='gaps', cursor=first['next_cursor']))
        self.assertEqual(status, 200)
        self.assertEqual(second['offset'], 32)
        self.assertEqual(second['entries'][0]['index'], 32)
        self.assertEqual(second['entries'][0]['value'], 'SYNTHETIC_GAP_31')
        self.assertEqual(self.get(base_url, self.path('/sections',section='medium',cursor=first['next_cursor']))[0],409)

    def test_page_byte_budget_preserves_metadata_for_unloaded_values(self):
        base_url = self.start()
        status, page, _, size = self.get(base_url,self.path('/sections',section='medium'))
        self.assertEqual(status,200)
        self.assertLess(size,256*1024)
        loaded = [entry for entry in page['entries'] if entry['value_state']=='LOADED']
        missing = [entry for entry in page['entries'] if entry['value_state']=='NOT_LOADED']
        self.assertGreater(len(loaded),0)
        self.assertGreater(len(missing),0)
        self.assertLessEqual(sum(entry['bytes'] for entry in loaded),128*1024)
        self.assertEqual(page['not_loaded_count'],len(missing))
        self.assertTrue(all(entry['reason']=='PAGE_BYTES_LIMIT' and 'value' not in entry for entry in missing))

    def test_real_http_response_is_consumed_by_frontend_client_and_cursor_session(self):
        import shutil
        import subprocess
        from pathlib import Path
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is not installed; frontend transport acceptance not run')
        base_url = self.start()
        before = self.snapshot()
        client = Path(__file__).resolve().parents[2] / 'frontend/src/api/m18SavedResult.ts'
        script = '''
import assert from 'node:assert/strict';
import { M18SavedClient, SavedRunSession } from CLIENT;
const api=new M18SavedClient((url,options)=>fetch(BASE+url,options));
const session=new SavedRunSession(api);
await session.load(RUN);
assert.equal(session.state.phase,'LOADED');
assert.equal(session.state.page.section,'gaps');
assert.equal(session.state.page.entries[0].value,'SYNTHETIC_UNAVAILABLE_INPUT');
await session.next();
assert.equal(session.state.page.offset,32);
assert.equal(session.state.page.entries[0].value,'SYNTHETIC_GAP_31');
await session.select('materials');
assert.equal(session.state.page.entries[0].value_state,'NOT_LOADED');
await session.select('empty');
assert.equal(session.state.page.entries.length,0);
session.close();
'''.replace('CLIENT',json.dumps(client.as_uri())).replace('BASE',json.dumps(base_url)).replace('RUN',json.dumps(RUN))
        result = subprocess.run([node,'--input-type=module','-e',script],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(before,self.snapshot())
