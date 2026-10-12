"""Read-only grouped M14 observation projection from real persisted M18 bundles."""
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

SECTION='rebound_research_observation'
PROJECTION='rebound_references'
GROUPS=('strict','near','pending','excluded','screen_unresolved')


def fixture(groups):
    raw,_,_=base.fixture();payload=json.loads(raw)['payload'];del payload['plan_product']
    payload['stocks']=[]
    payload['announcement_reviewed_analysis']=dict(status='READY',plan_cutoff=None,gaps=[],
        products=[],research_references=[dict(stock_code='ANN',research_status='SELECTED')])
    observation=dict(groups,status='CANNOT_CONFIRM',original_computation_status='READY_WITH_GAPS',
        observed_session='20261009',target_trade_date='20261012',main_screen_ready=False,
        input_identity='e'*64,decision_identity='f'*64,production_allowed=False,
        coverage=dict(strict_count=len(groups['strict']),near_count=len(groups['near']),
            pending_codes=['PRIVATE_DUPLICATE'],row_accounted_count=sum(map(len,groups.values()))),
        native_evidence=dict(volume_unit=None,price_currency=None,price_basis='RAW',gaps=['NOT_PROVEN'],
            date_evidence=dict(data_session='20261009',manifest_available_at=None,
                observation_status='NATIVE_SOURCE_READ_RECORDED'),
            unit_evidence=dict(status='NOT_PROVEN',conversion_applied=False),
            native_observation=dict(source_files=[dict(source_relative='/private/native')])),
        gaps=['SYNTHETIC_UNVERIFIED'],cards=groups['strict']+groups['near'])
    payload[SECTION]=dict(status='CANNOT_CONFIRM',eligible_screen=None,
        research_observation=observation,reason_codes=['SYNTHETIC_SOURCE_GAP'],
        scope='INDEPENDENT_READ_TIME_OBSERVATION_NOT_SAVED_PLAN_OR_FORMAL_SELECTION',
        source_run_id='d'*32,binding_reference=dict(run_id='d'*32,artifact_sha256='c'*64,
            manifest_sha256='a'*64,receipt_sha256='b'*64,
            payload_path='/private/owner/artifact.json'),production_allowed=False)
    saved=dict(run_id=base.RUN,target_trade_date=payload['target_trade_date'],
        input_identity=payload['input_identity'],workspace=copy.deepcopy(payload))
    saved['sha256']=m.sha(canonical_bytes(saved));saved_raw=canonical_bytes(saved)
    payload['plan_product']=dict(consumed=True,run_id=base.RUN,sha256=saved['sha256'])
    raw=canonical_bytes(dict(payload=payload,readback=dict(run_id=base.RUN,
        plan_sha256=saved['sha256'],input_identity=payload['input_identity'])))
    identity=dict(run_id=base.RUN,target_date=payload['target_trade_date'],
        input_identity=payload['input_identity'],plan_sha256=saved['sha256'],
        raw_sha256=m.sha(saved_raw),response_sha256=m.sha(raw))
    return raw,identity,m.build(raw,saved_raw,identity,expected_profile=m.PROFILE_SHA256)


class ReboundProjectionTests(unittest.TestCase):
    serve=base.DiskPagesTests.serve
    get=base.DiskPagesTests.get
    snapshot=base.DiskPagesTests.snapshot

    def setUp(self):
        self.groups={group:[dict(code=f'{group}{i}',observed_session='20261009',
            target_monday='20261012',qualification_status='UNVERIFIED_RESEARCH_OBSERVATION',
            connect_eligibility='UNVERIFIED',volume_unit='NOT_PROVEN',
            production_allowed=False,unknown=None) for i in range(count)]
            for group,count in zip(GROUPS,(70,35,2,3,0))}
        self.install(self.groups)

    def install(self,groups):
        with patch.object(base,'fixture',return_value=fixture(groups)):
            base.DiskPagesTests.setUp(self)

    def start(self):
        self.config['routes'] += [ROUTE+'/overview',ROUTE+'/sections']
        return self.serve()

    def path(self,**changes):
        query=dict(run_id=base.RUN,generation_id=self.descriptor['generation_id'],
            section=SECTION,projection=PROJECTION,group='strict')
        query.update(changes)
        return ROUTE+'/sections?'+urlencode({k:v for k,v in query.items() if v is not None})

    def test_three_pages_exact_offsets_hashes_and_group_counts_without_cards(self):
        url=self.start();before=self.snapshot();cursor=None;seen=[]
        for offset,count in ((0,32),(32,32),(64,6)):
            status,page,_,size=self.get(url,self.path(cursor=cursor))
            self.assertEqual(status,200);self.assertLessEqual(size,256*1024)
            self.assertEqual(page['projection'],PROJECTION);self.assertEqual(page['group'],'strict')
            self.assertEqual(page['offset'],offset);self.assertEqual(page['matched_total'],70)
            self.assertEqual(page['loaded_count'],count);self.assertIsNone(page['selection'])
            self.assertEqual(page['identity'],self.identity)
            metadata=page['rebound']
            self.assertEqual(metadata['group_counts'],{k:len(v) for k,v in self.groups.items()})
            self.assertEqual(metadata['source']['status'],'CANNOT_CONFIRM')
            self.assertIsNone(metadata['source']['eligible_screen'])
            self.assertFalse(metadata['source']['production_allowed'])
            self.assertEqual(metadata['observation']['original_computation_status'],'READY_WITH_GAPS')
            self.assertFalse(metadata['observation']['main_screen_ready'])
            self.assertNotIn('cards',metadata['observation'])
            self.assertFalse(set(GROUPS)&set(metadata['observation']))
            self.assertNotIn('payload_path',metadata['source']['binding_reference'])
            self.assertEqual(metadata['source']['binding_reference']['artifact_sha256'],'c'*64)
            self.assertEqual(metadata['source']['binding_reference']['receipt_sha256'],'b'*64)
            inner=metadata['observation']
            self.assertEqual(inner['input_identity'],'e'*64)
            self.assertEqual(inner['decision_identity'],'f'*64)
            self.assertEqual(inner['coverage']['strict_count'],70)
            self.assertNotIn('pending_codes',inner['coverage'])
            self.assertIsNone(inner['native_evidence']['volume_unit'])
            self.assertFalse(inner['native_evidence']['unit_evidence']['conversion_applied'])
            self.assertNotIn('native_observation',inner['native_evidence'])
            self.assertEqual(metadata['source_section_sha256'],m.sha(b''.join(self.reader.item_parts(SECTION,0))))
            for entry in page['entries']:
                original=self.groups['strict'][entry['index']];encoded=canonical_bytes(original)
                self.assertEqual(entry['value'],original);self.assertEqual(entry['sha256'],m.sha(encoded))
                self.assertEqual(self.raw[entry['offset']:entry['offset']+entry['bytes']],encoded)
                seen.append(entry['value'])
            cursor=page['next_cursor']
        self.assertIsNone(cursor);self.assertEqual(seen,self.groups['strict'])
        for group in GROUPS[1:]:
            status,page,_,_=self.get(url,self.path(group=group))
            self.assertEqual(status,200);self.assertEqual(page['matched_total'],len(self.groups[group]))
            self.assertEqual([e['value'] for e in page['entries']],self.groups[group][:32])
        self.assertEqual(json.loads(self.raw)['payload']['stocks'],[])
        self.assertEqual(before,self.snapshot())

    def test_projection_and_cross_group_source_cursors_are_closed(self):
        url=self.start();status,first,_,_=self.get(url,self.path());self.assertEqual(status,200)
        cursor=first['next_cursor'];forged=json.loads(base64.urlsafe_b64decode(cursor))
        forged['source_section_sha256']='f'*64
        wrong_source=base64.urlsafe_b64encode(canonical_bytes(forged)).decode()
        for query in (dict(group='cards'),dict(group=None),dict(projection='other'),
            dict(section='stocks'),dict(group='near',cursor=cursor),dict(cursor=wrong_source),
            dict(cursor=self.reader._cursor('gaps',None,32)),dict(projection=None,group=None,cursor=cursor)):
            with self.subTest(query=query):self.assertEqual(self.get(url,self.path(**query))[0],409)

    def test_false_null_and_caps_preserve_complete_row_hash(self):
        groups=copy.deepcopy(self.groups);groups['strict']=[False,None,dict(body='x'*17000)]+[dict(body='x'*10000) for _ in range(29)]
        self.install(groups);url=self.start();status,page,_,size=self.get(url,self.path())
        self.assertEqual(status,200);self.assertLessEqual(size,256*1024)
        self.assertEqual([e['value'] for e in page['entries'][:2]],[False,None])
        big=page['entries'][2];self.assertEqual(big['reason'],'ITEM_BYTES_LIMIT')
        self.assertNotIn('value',big);self.assertEqual(big['sha256'],m.sha(canonical_bytes(groups['strict'][2])))
        loaded=[e for e in page['entries'] if e['value_state']=='LOADED']
        self.assertLessEqual(sum(e['bytes'] for e in loaded),128*1024)
        self.assertTrue(any(e.get('reason')=='PAGE_BYTES_LIMIT' for e in page['entries']))

    def test_supervisor_projection_group_and_receipt_are_closed(self):
        from v5_shadow.module_api import _m18_semantic_value
        query=dict(section=SECTION,projection=PROJECTION,group='strict')
        request=dict(binding=self.config['m18_v2_binding'],kind='rebound',query=query)
        process._validate(request);page=_m18_semantic_value(self.reader,'rebound',query)
        process._check_payload(page,request)
        for changes in (dict(group='cards'),dict(projection='announcement_references'),dict(section='stocks')):
            with self.subTest(changes=changes),self.assertRaises(m.ContractError):
                process._validate(dict(request,query=dict(query,**changes)))
        for changes in (dict(group='near'),dict(projection='announcement_references'),dict(offset=32)):
            with self.subTest(changes=changes),self.assertRaises(m.ContractError):
                process._check_payload(dict(page,**changes),request)

    def test_source_limit_precedes_read_and_full_response_is_never_called(self):
        from v5_shadow.module_api import _m18_semantic_value
        query=dict(section=SECTION,projection=PROJECTION,group='strict')
        with patch.object(self.reader,'full_response',side_effect=AssertionError('no full response')):
            self.assertEqual(_m18_semantic_value(self.reader,'rebound',query)['matched_total'],70)
        oversized=copy.deepcopy(self.reader.detail(SECTION))
        oversized['entries'][0]['bytes']=m.PROFILE['object_bytes']
        with patch.object(self.reader,'detail',return_value=oversized), \
                patch.object(self.reader,'item_parts',side_effect=AssertionError('must reject before read')), \
                self.assertRaisesRegex(m.ContractError,'V2_OBJECT_BYTES'):
            _m18_semantic_value(self.reader,'rebound',query)

    def test_real_http_frontend_preserves_announcement_default_and_group_history(self):
        import shutil
        import subprocess
        from pathlib import Path
        node=shutil.which('node')
        if not node:self.skipTest('Node unavailable; frontend acceptance not run')
        url=self.start();before=self.snapshot()
        client=Path(__file__).resolve().parents[2]/'frontend/src/api/m18SavedResult.ts'
        script='''
import assert from 'node:assert/strict';
import { M18SavedClient, SavedRunSession } from CLIENT;
const session=new SavedRunSession(new M18SavedClient((url,options)=>fetch(BASE+url,options)));
await session.load(RUN);
assert.equal(session.state.phase,'LOADED');
assert.equal(session.state.page.projection,'announcement_references');
await session.select('rebound_research_observation','strict');
assert.equal(session.state.phase,'LOADED');
assert.equal(session.state.page.projection,'rebound_references');
assert.equal(session.state.page.group,'strict');
assert.equal(session.state.page.entries.length,32);
assert.equal(session.state.page.rebound.source.eligible_screen,null);
assert.equal(session.state.page.rebound.observation.status,'CANNOT_CONFIRM');
assert.equal(session.state.page.entries[0].value.production_allowed,false);
await session.next();
assert.equal(session.state.page.offset,32);
assert.equal(session.state.page.group,'strict');
await session.next();
assert.equal(session.state.page.offset,64);
assert.equal(session.state.page.entries.length,6);
await session.previous();
assert.equal(session.state.page.offset,32);
await session.select('rebound_research_observation','near');
assert.equal(session.state.page.group,'near');
assert.equal(session.state.page.offset,0);
assert.equal(session.state.canPrevious,false);
await session.next();
assert.equal(session.state.page.entries.length,3);
for(const [group,count] of [['pending',2],['excluded',3],['screen_unresolved',0]]) {
 await session.select('rebound_research_observation',group);
 assert.equal(session.state.phase,'LOADED');
 assert.equal(session.state.page.group,group);
 assert.equal(session.state.page.matched_total,count);
}
await session.select('stocks');
assert.equal(session.state.page.matched_total,0);
await session.select('announcement_reviewed_analysis');
assert.equal(session.state.page.projection,'announcement_references');
assert.equal(session.state.page.entries[0].value.stock_code,'ANN');
session.close();
'''.replace('CLIENT',json.dumps(client.as_uri())).replace('BASE',json.dumps(url)).replace('RUN',json.dumps(base.RUN))
        result=subprocess.run([node,'--input-type=module','-e',script],capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(before,self.snapshot())


if __name__=='__main__':unittest.main()
