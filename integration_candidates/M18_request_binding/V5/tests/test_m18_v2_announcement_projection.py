"""Same-run announcement references projected from a real immutable Reader."""
import base64
import copy
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlencode
import test_m18_v2_disk_pages as base
from v5_shadow import m18_offline_v2 as m
from v5_shadow import m18_v2_read_process as process
from v5_shadow.digests import canonical_bytes
from v5_shadow.m18_v2_publication_bridge import ROUTE

SECTION = 'announcement_reviewed_analysis'
PROJECTION = 'announcement_references'


def fixture(references):
    raw, _, _ = base.fixture()
    payload = json.loads(raw)['payload']
    del payload['plan_product']
    payload['stocks'] = []
    product = dict(status='CONSUMED', validation_status='VERIFIED', consumed=True,
        selection_status='VERIFIED', product_sha256='c'*64, publication_date='2026-10-09',
        stock_count=280, selected_stock_count=103, conditional_watch_count=44,
        not_selected_stock_count=79, not_assessed_stock_count=54,
        cutoff_status='SATISFIED', orders_sent=False, reviewed_at=None,
        gaps=['SYNTHETIC_PRODUCT_GAP'], research_references=references,
        private_unneeded_field='MUST_NOT_BE_PROJECTED')
    payload[SECTION] = dict(status='READY', plan_cutoff='2026-10-11T23:42:13+00:00',
        gaps=['SYNTHETIC_PIT_UNCONFIRMED'], products=[product], research_references=references)
    saved = dict(run_id=base.RUN, target_trade_date=payload['target_trade_date'],
                 input_identity=payload['input_identity'], workspace=copy.deepcopy(payload))
    saved['sha256'] = m.sha(canonical_bytes(saved));saved_raw=canonical_bytes(saved)
    payload['plan_product'] = dict(consumed=True,run_id=base.RUN,sha256=saved['sha256'])
    raw = canonical_bytes(dict(payload=payload,readback=dict(run_id=base.RUN,
        plan_sha256=saved['sha256'],input_identity=payload['input_identity'])))
    identity = dict(run_id=base.RUN,target_date=payload['target_trade_date'],
        input_identity=payload['input_identity'],plan_sha256=saved['sha256'],
        raw_sha256=m.sha(saved_raw),response_sha256=m.sha(raw))
    return raw,identity,m.build(raw,saved_raw,identity,expected_profile=m.PROFILE_SHA256)


class AnnouncementProjectionTests(unittest.TestCase):
    serve = base.DiskPagesTests.serve
    get = base.DiskPagesTests.get
    snapshot = base.DiskPagesTests.snapshot

    def setUp(self):
        self.references = [dict(stock_code=str(i),research_status='SELECTED' if i%2 else 'CONDITIONAL_WATCH',
            point_in_time_status='CANNOT_CONFIRM',connect_eligibility_status='NOT_ASSESSED',
            orders_sent=False,unknown=None,selection_reasons=['SYNTHETIC'],risk_notes=[],
            article_refs=[]) for i in range(70)]
        self.install(self.references)

    def install(self, references):
        with patch.object(base,'fixture',return_value=fixture(references)):
            base.DiskPagesTests.setUp(self)

    def start(self):
        self.config['routes'] += [ROUTE+'/overview',ROUTE+'/sections']
        return self.serve()

    def path(self, **changes):
        query=dict(run_id=base.RUN,generation_id=self.descriptor['generation_id'],
                   section=SECTION,projection=PROJECTION)
        query.update(changes)
        return ROUTE+'/sections?'+urlencode({k:v for k,v in query.items() if v is not None})

    def test_three_pages_preserve_exact_references_metadata_and_files(self):
        url=self.start();before=self.snapshot();cursor=None;seen=[]
        for offset,count in [(0,32),(32,32),(64,6)]:
            status,page,_,size=self.get(url,self.path(cursor=cursor))
            self.assertEqual(status,200)
            self.assertLessEqual(size,256*1024)
            self.assertEqual(page['projection'],PROJECTION)
            self.assertEqual(page['section'],SECTION)
            self.assertIsNone(page['selection'])
            self.assertEqual(page['offset'],offset)
            self.assertEqual(page['matched_total'],70)
            self.assertEqual(page['loaded_count'],count)
            self.assertEqual(page['not_loaded_count'],70-count)
            self.assertEqual(page['identity'],self.identity)
            self.assertEqual(page['announcement']['reference_count'],70)
            self.assertEqual(page['announcement']['status'],'READY')
            self.assertEqual(page['announcement']['gaps'],['SYNTHETIC_PIT_UNCONFIRMED'])
            product=page['announcement']['products'][0]
            self.assertEqual(product['stock_count'],280)
            self.assertFalse(product['orders_sent']);self.assertIsNone(product['reviewed_at'])
            self.assertNotIn('research_references',product)
            self.assertNotIn('private_unneeded_field',product)
            source=b''.join(self.reader.item_parts(SECTION,0))
            self.assertEqual(page['announcement']['source_section_sha256'],m.sha(source))
            for entry in page['entries']:
                original=self.references[entry['index']]
                encoded=canonical_bytes(original)
                self.assertEqual(entry['value'],original)
                self.assertEqual(entry['sha256'],m.sha(encoded))
                self.assertEqual(self.raw[entry['offset']:entry['offset']+entry['bytes']],encoded)
                self.assertFalse(entry['value']['orders_sent'])
                self.assertIsNone(entry['value']['unknown'])
                seen.append(entry['value'])
            cursor=page['next_cursor']
        self.assertIsNone(cursor);self.assertEqual(seen,self.references)
        self.assertEqual(json.loads(self.raw)['payload']['stocks'],[])
        self.assertEqual(before,self.snapshot())

    def test_large_row_and_page_budget_remain_not_loaded(self):
        refs=[dict(body='x'*(16*1024))]+[dict(body='x'*10000) for _ in range(31)]
        self.install(refs);url=self.start();status,page,_,size=self.get(url,self.path())
        self.assertEqual(status,200);self.assertLessEqual(size,256*1024)
        self.assertEqual(page['entries'][0]['reason'],'ITEM_BYTES_LIMIT')
        self.assertNotIn('value',page['entries'][0])
        self.assertEqual(page['entries'][0]['sha256'],m.sha(canonical_bytes(refs[0])))
        loaded=[e for e in page['entries'] if e['value_state']=='LOADED']
        self.assertLessEqual(sum(e['bytes'] for e in loaded),128*1024)
        self.assertTrue(any(e.get('reason')=='PAGE_BYTES_LIMIT' for e in page['entries']))

    def test_false_null_and_empty_are_not_coerced(self):
        self.install([False,None]);url=self.start()
        status,page,_,_=self.get(url,self.path())
        self.assertEqual(status,200)
        self.assertEqual([e['value'] for e in page['entries']],[False,None])
        self.install([]);url=self.start();status,page,_,_=self.get(url,self.path())
        self.assertEqual(status,200);self.assertEqual(page['matched_total'],0)
        self.assertEqual(page['entries'],[]);self.assertIsNone(page['next_cursor'])

    def test_projection_and_cross_cursor_replays_are_rejected(self):
        url=self.start();status,first,_,_=self.get(url,self.path())
        self.assertEqual(status,200);cursor=first['next_cursor']
        forged=json.loads(base64.urlsafe_b64decode(cursor))
        forged['source_section_sha256']='f'*64
        wrong_source=base64.urlsafe_b64encode(canonical_bytes(forged)).decode()
        normal_cursor=self.reader._cursor('gaps',None,32)
        for query in [dict(projection='other'),dict(section='gaps'),
                      dict(cursor=normal_cursor),dict(cursor=wrong_source),
                      dict(projection=None,cursor=cursor),dict(generation_id='f'*64)]:
            with self.subTest(query=query):
                self.assertEqual(self.get(url,self.path(**query))[0],409)

    def test_supervisor_kind_and_projection_contracts_are_closed(self):
        from v5_shadow.module_api import _m18_semantic_value
        query=dict(section=SECTION,projection=PROJECTION)
        page=_m18_semantic_value(self.reader,'announcement',query)
        request=dict(binding=self.config['m18_v2_binding'],kind='announcement',query=query)
        process._validate(request);process._check_payload(page,request)
        for changes in [dict(projection='other'),dict(section='gaps')]:
            with self.subTest(changes=changes),self.assertRaises(m.ContractError):
                process._validate(dict(request,query=dict(query,**changes)))
        for changes in [dict(projection='other'),dict(section='gaps'),dict(offset=32)]:
            with self.subTest(changes=changes),self.assertRaises(m.ContractError):
                process._check_payload(dict(page,**changes),request)

    def test_source_object_limit_precedes_materialization_and_no_full_response(self):
        from v5_shadow.module_api import _m18_semantic_value
        query=dict(section=SECTION,projection=PROJECTION)
        with patch.object(self.reader,'full_response',side_effect=AssertionError('no full response')):
            page=_m18_semantic_value(self.reader,'announcement',query)
            self.assertEqual(page['matched_total'],70)
        oversized=copy.deepcopy(self.reader.detail(SECTION))
        oversized['entries'][0]['bytes']=m.PROFILE['object_bytes']
        with patch.object(self.reader,'detail',return_value=oversized), \
                patch.object(self.reader,'item_parts',side_effect=AssertionError('must reject before read')), \
                self.assertRaisesRegex(m.ContractError,'V2_OBJECT_BYTES'):
            _m18_semantic_value(self.reader,'announcement',query)

    def test_real_http_frontend_session_pages_and_returns_to_projection(self):
        import shutil
        import subprocess
        from pathlib import Path
        node=shutil.which('node')
        if not node:
            self.skipTest('Node is not installed; frontend transport acceptance not run')
        url=self.start();before=self.snapshot()
        client=Path(__file__).resolve().parents[2]/'frontend/src/api/m18SavedResult.ts'
        script='''
import assert from 'node:assert/strict';
import { M18SavedClient, SavedRunSession } from CLIENT;
const api=new M18SavedClient((url,options)=>fetch(BASE+url,options));
const session=new SavedRunSession(api);
await session.load(RUN);
assert.equal(session.state.phase,'LOADED');
assert.equal(session.state.page.section,'announcement_reviewed_analysis');
assert.equal(session.state.page.projection,'announcement_references');
assert.equal(session.state.page.announcement.reference_count,70);
assert.equal(session.state.page.announcement.products[0].stock_count,280);
assert.equal(session.state.page.offset,0);
assert.equal(session.state.page.entries.length,32);
assert.equal(session.state.page.entries[0].value.orders_sent,false);
assert.equal(session.state.page.entries[0].value.unknown,null);
await session.next();
assert.equal(session.state.page.offset,32);
assert.equal(session.state.page.entries.length,32);
await session.next();
assert.equal(session.state.page.offset,64);
assert.equal(session.state.page.entries.length,6);
assert.equal(session.state.page.next_cursor,null);
await session.previous();
assert.equal(session.state.page.offset,32);
await session.previous();
assert.equal(session.state.page.offset,0);
await session.select('stocks');
assert.equal(session.state.phase,'LOADED');
assert.equal(session.state.page.section,'stocks');
assert.equal(session.state.page.matched_total,0);
assert.deepEqual(session.state.page.entries,[]);
assert.equal(session.state.page.projection,undefined);
await session.select('announcement_reviewed_analysis');
assert.equal(session.state.phase,'LOADED');
assert.equal(session.state.page.projection,'announcement_references');
assert.equal(session.state.page.offset,0);
assert.equal(session.state.page.announcement.reference_count,70);
assert.equal(session.state.page.entries.length,32);
session.close();
'''.replace('CLIENT',json.dumps(client.as_uri())).replace('BASE',json.dumps(url)).replace('RUN',json.dumps(base.RUN))
        result=subprocess.run([node,'--input-type=module','-e',script],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(before,self.snapshot())


if __name__=='__main__':unittest.main()
