"""Same frozen response M15 daily matches, bounded metadata and read-only HTTP."""
import base64
import copy
import json
import os
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import test_m18_v2_disk_pages as base
from v5_shadow import m18_offline_v2 as m
from v5_shadow import m18_v2_read_process as process
from v5_shadow.digests import canonical_bytes
from v5_shadow.m18_v2_publication_bridge import ROUTE

SECTION = 'us_mapping_research'
PROJECTION = 'us_mapping_matches'
FLAGS = dict(RESEARCH_ONLY=True, production_allowed=False, buy_gate_updated=False, orders_sent=False)
MISSING = object()


def fixture(matches, *, change_mapping=None, owner=MISSING):
    raw, _, _ = base.fixture()
    payload = json.loads(raw)['payload'];payload.pop('plan_product')
    payload['stocks'] = []
    payload['announcement_reviewed_analysis'] = dict(status='READY', products=[],
        research_references=[dict(stock_code='ANN')])
    historical = dict(hk_symbol='HK.09999', us_symbol='OLD', reason='HISTORICAL_NOT_DAILY')
    mapping = dict(schema_version='v4.manager_research.us_mapping_research.v1',
        target_trade_date='20261012', **FLAGS,
        daily_run=dict(schema_version='v4.manager_research.us_mapping_daily_run.v1',
            status='COMPLETED', target_trade_date='20261012', run_id='d'*32,
            artifact_sha256='a'*64, generated_at='2026-10-11T20:39:26Z',
            research_cutoff='2026-10-12T04:39:26.258807+08:00', us_session_date='20261009',
            source_status='READY', target_date_eligibility='CANNOT_CONFIRM', input_identity='c'*64,
            relation_artifact_sha256='b'*64, coverage_scope='PINNED_REVIEWED_SAMPLE',
            readback_required=True, gaps=['SYNTHETIC_UNVERIFIED'], source_gaps=[],
            coverage=dict(reviewed_us_symbol_count=4, matched_us_symbol_count=4,
                matched_hk_relation_count=len(matches), configured_us_universe_count=33,
                available_us_universe_count=None, full_market_coverage=False),
            source_identity=dict(private_path='/private/owner/source'), matches=matches, **FLAGS),
        reviewed_research=dict(target_trade_date='20260930', cards=[historical]),
        coverage_diagnostics=dict(schema_version='v5.us_mapping_scope.v1',status='PARTIAL',
            scope='PINNED_REVIEWED_RELATIONS_WITHIN_CONFIGURED_US_SAMPLE',
            reviewed_us_symbols=['AVGO','CIEN','COHR','LITE'], reviewed_us_symbol_count=4,
            reviewed_relation_artifact_sha256='b'*64, us_session_date='20261009',
            daily_run_id='d'*32, daily_artifact_sha256='a'*64,
            configured_sample_count=33,rising_individual_count=23,
            assessed_rising_symbol_count=4,unassessed_rising_symbol_count=19,
            full_market_coverage=False,formal_eligible=False,natural_verified=False,
            broader_relation_result=None,reason_codes=['BROADER_US_HK_RELATIONS_NOT_ASSESSED'],
            rows=[dict(source_row=historical)], registry_readback=dict(
                scope='ORIGINAL_REVIEWED_RETROSPECTIVE_RESEARCH_NOT_CURRENT_SELECTION',
                seed_target_date='20260930',formal_eligible=False,natural_verified=False,
                cards=[historical],non_matching_theme_cards=[historical],report={'private_path':'secret'})))
    if change_mapping:change_mapping(mapping)
    payload[SECTION] = mapping
    if owner is MISSING:
        owner = dict(other_owner={'body':'unrelated'},us_mapping_daily_plan_reference=dict(
            status='NOT_CONSUMED',target_trade_date='20261012',run_id='d'*32,artifact_sha256='a'*64,
            available_at='2026-10-11T20:39:26Z',plan_cutoff=None,reason='US_MARKET_SOURCE_FAILED',
            matches=matches,**FLAGS))
    if owner is not None:payload['owner_chain'] = owner
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


class UsMappingProjectionTests(unittest.TestCase):
    serve=base.DiskPagesTests.serve
    get=base.DiskPagesTests.get
    snapshot=base.DiskPagesTests.snapshot

    def setUp(self):
        self.matches=[dict(us_symbol=us,hk_symbol=hk,hk_name='示例',change_pct=1.25,
            session_date='20261009',relationship_type='PRODUCT_PEER',reason='原研究理由',
            maturity='原产品阶段',limitations=['目标日资格未确认'],research_priority=None,
            official_sources=[dict(published_at='2026-09-30',title='官方材料',url='https://example.com/report')],
            source_row=dict(symbol=us,change_pct=1.25),reviewed_relation_artifact_sha256='b'*64,
            target_date_eligibility='CANNOT_CONFIRM',production_allowed=False)
            for us,hk in zip(('AVGO','CIEN','COHR','LITE'),('HK.00001','HK.00002','HK.00003','HK.00003'))]
        self.install(self.matches)

    def install(self,matches,**options):
        with patch.object(base,'fixture',return_value=fixture(matches,**options)):
            base.DiskPagesTests.setUp(self)
        from v5_shadow.module_api import _M18UsMappingPlanSpan
        self.reader=m.Reader(self.bundle,m.sha(self.bundle.manifest),self.identity,
            expected_profile=m.PROFILE_SHA256,span_observer=_M18UsMappingPlanSpan())

    def start(self):
        self.config['routes'] += [ROUTE+'/overview',ROUTE+'/sections']
        return self.serve()

    def path(self,**changes):
        query=dict(run_id=base.RUN,generation_id=self.descriptor['generation_id'],
            section=SECTION,projection=PROJECTION)
        query.update(changes)
        return ROUTE+'/sections?'+urlencode({k:v for k,v in query.items() if v is not None})

    def query(self,**changes):
        return dict(section=SECTION,projection=PROJECTION,**changes)

    def test_four_same_run_relationships_three_hk_exact_spans_and_read_only_http(self):
        url=self.start();before=self.snapshot()
        status,page,headers,size=self.get(url,self.path())
        self.assertEqual(status,200);self.assertLessEqual(size,256*1024)
        self.assertEqual(headers['X-V5-Workspace-Access'],'READ_ONLY')
        self.assertEqual(page['identity'],self.identity);self.assertEqual(page['projection'],PROJECTION)
        self.assertEqual(page['matched_total'],4);self.assertEqual(page['loaded_count'],4)
        self.assertEqual(len({e['value']['hk_symbol'] for e in page['entries']}),3)
        self.assertEqual([e['value'] for e in page['entries']],self.matches)
        for entry in page['entries']:
            raw=self.raw[entry['offset']:entry['offset']+entry['bytes']]
            self.assertEqual(raw,canonical_bytes(self.matches[entry['index']]))
            self.assertEqual(m.sha(raw),entry['sha256'])
        meta=page['us_mapping']
        self.assertEqual(meta['source_section_sha256'],m.sha(b''.join(self.reader.item_parts(SECTION,0))))
        self.assertEqual(meta['match_count'],4)
        self.assertEqual(meta['daily_run']['status'],'COMPLETED')
        self.assertEqual(meta['daily_run']['source_status'],'READY')
        self.assertEqual(meta['daily_run']['research_cutoff'],'2026-10-12T04:39:26.258807+08:00')
        self.assertEqual(meta['daily_run']['generated_at'],'2026-10-11T20:39:26Z')
        self.assertEqual(meta['daily_run']['us_session_date'],'20261009')
        self.assertEqual(meta['daily_run']['target_date_eligibility'],'CANNOT_CONFIRM')
        self.assertIsNone(meta['daily_run']['coverage']['available_us_universe_count'])
        self.assertFalse(meta['source']['production_allowed'])
        coverage=meta['coverage_diagnostics']
        self.assertEqual([coverage[k] for k in ('configured_sample_count','rising_individual_count',
            'assessed_rising_symbol_count','unassessed_rising_symbol_count')],[33,23,4,19])
        self.assertFalse(coverage['natural_verified']);self.assertFalse(coverage['formal_eligible'])
        self.assertIsNone(coverage['broader_relation_result'])
        self.assertNotIn('rows',coverage);self.assertNotIn('registry_readback',coverage)
        self.assertEqual(meta['source']['registry_readback'],dict(
            scope='ORIGINAL_REVIEWED_RETROSPECTIVE_RESEARCH_NOT_CURRENT_SELECTION',
            seed_target_date='20260930',formal_eligible=False,natural_verified=False))
        self.assertNotIn('HISTORICAL_NOT_DAILY',json.dumps(page))
        self.assertNotIn('source_identity',meta['daily_run']);self.assertNotIn('matches',meta['daily_run'])
        reference=meta['plan_reference'];self.assertEqual(reference['value_state'],'LOADED')
        self.assertEqual(reference['value']['status'],'NOT_CONSUMED')
        self.assertEqual(reference['value']['reason'],'US_MARKET_SOURCE_FAILED')
        self.assertIsNone(reference['value']['plan_cutoff'])
        self.assertNotIn('matches',reference['value']);self.assertNotIn('consumed',reference['value'])
        span=reference['source_span'];original=self.raw[span['offset']:span['offset']+span['bytes']]
        self.assertEqual(m.sha(original),span['sha256'])
        self.assertEqual(json.loads(original)['matches'],self.matches)
        self.assertEqual(reference['source_section_sha256'],m.sha(b''.join(self.reader.item_parts('owner_chain',0))))
        self.assertEqual(before,self.snapshot());self.assertIsNone(page['next_cursor'])
        self.assertEqual(self.get(url,self.path(),method='POST')[0],405)

    def test_bounded_thirty_two_rows_and_variable_page_deferral(self):
        matches=[dict(body='x'*(size-11)) for size in [4500]*29+[4367]*41]
        self.install(matches);url=self.start();seen=[];cursor=None;offsets=[];before=self.snapshot()
        while True:
            status,page,_,size=self.get(url,self.path(cursor=cursor));self.assertEqual(status,200)
            self.assertEqual(page['offset'],len(seen));offsets.append(page['offset'])
            self.assertLessEqual(size,256*1024);self.assertLessEqual(len(page['entries']),32)
            self.assertLessEqual(sum(e['bytes'] for e in page['entries']),128*1024)
            self.assertTrue(all(e['value_state']=='LOADED' for e in page['entries']))
            self.assertEqual(page['us_mapping']['plan_reference']['reason'],'REFERENCE_BYTES_LIMIT')
            seen.extend(e['value'] for e in page['entries']);cursor=page['next_cursor']
            if cursor is None:break
            self.assertGreater(len(page['entries']),0);self.assertLess(len(seen),len(matches))
        self.assertEqual(offsets,[0,29,59]);self.assertEqual(seen,matches);self.assertEqual(before,self.snapshot())

    def test_oversize_false_null_values_and_exact_page_boundary(self):
        for extra,expected in ((0,32),(1,31)):
            rows=[dict(body='x'*(4096-11)) for _ in range(33)];rows[31]['body']+='x'*extra
            self.install(rows,owner=None);url=self.start();status,page,_,_=self.get(url,self.path())
            self.assertEqual(status,200);self.assertEqual(len(page['entries']),expected)
            self.assertEqual(self.get(url,self.path(cursor=page['next_cursor']))[1]['offset'],expected)
        rows=[False,None,dict(body='x'*17000)]+[dict(body='x'*10000) for _ in range(29)]
        self.install(rows,owner=None);url=self.start();seen=[];cursor=None
        while True:
            status,page,_,_=self.get(url,self.path(cursor=cursor));self.assertEqual(status,200)
            seen.extend(page['entries']);cursor=page['next_cursor']
            if cursor is None:break
        self.assertEqual([e['index'] for e in seen],list(range(32)))
        self.assertEqual([e['value'] for e in seen[:2]],[False,None])
        self.assertEqual(seen[2]['reason'],'ITEM_BYTES_LIMIT');self.assertNotIn('value',seen[2])
        self.assertEqual(seen[2]['sha256'],m.sha(canonical_bytes(rows[2])))
        self.assertEqual([e['index'] for e in seen if e['value_state']=='NOT_LOADED'],[2])
        self.install([dict(body='x'*17000)],owner=None);url=self.start()
        status,page,_,_=self.get(url,self.path());self.assertEqual(status,200)
        self.assertEqual(len(page['entries']),1);self.assertIsNone(page['next_cursor'])

    def test_selector_and_source_identity_cursors_fail_closed(self):
        self.install([dict(index=i) for i in range(70)],owner=None);url=self.start()
        status,page,_,_=self.get(url,self.path());self.assertEqual(status,200)
        cursor=page['next_cursor'];decoded=json.loads(base64.urlsafe_b64decode(cursor))
        invalid=[dict(group='strict'),dict(section='stocks'),dict(projection='daily_run.matches'),
            dict(projection='rebound_references'),dict(cursor=self.reader._cursor('gaps',None,32)),
            dict(projection=None,cursor=cursor),dict(cursor='bad')]
        for key,value in (('source_section_sha256','f'*64),('projection','announcement_references'),
            ('section','stocks'),('group','strict'),('offset',0),('offset',True),
            ('identity',dict(self.identity,input_identity='f'*64)),('manifest_sha256','e'*64),
            ('generation_id','e'*64),('profile_sha256','e'*64)):
            forged=dict(decoded,**{key:value})
            invalid.append(dict(cursor=base64.urlsafe_b64encode(canonical_bytes(forged)).decode()))
        for query in invalid:
            with self.subTest(query=query):self.assertEqual(self.get(url,self.path(**query))[0],409)

    def test_original_consumption_state_missing_and_bounded_reference(self):
        from v5_shadow.module_api import _m18_semantic_value
        cases=[(None,'OWNER_CHAIN_MISSING'),({},'REFERENCE_MISSING'),
            (dict(us_mapping_daily_plan_reference=None),'REFERENCE_INVALID'),
            (dict(us_mapping_daily_plan_reference=dict(body='x'*17000)),'REFERENCE_BYTES_LIMIT')]
        for owner,reason in cases:
            self.install(self.matches,owner=owner)
            page=_m18_semantic_value(self.reader,'us_mapping',self.query())
            self.assertEqual(page['us_mapping']['plan_reference']['value_state'],'NOT_LOADED')
            self.assertEqual(page['us_mapping']['plan_reference']['reason'],reason)
            self.assertNotIn('value',page['us_mapping']['plan_reference'])
        reference=dict(status='CONSUMED',reason=None,**FLAGS)
        self.install(self.matches,owner=dict(us_mapping_daily_plan_reference=reference))
        page=_m18_semantic_value(self.reader,'us_mapping',self.query())
        self.assertEqual(page['us_mapping']['plan_reference']['value'],reference)

    def test_large_owner_chain_keeps_small_original_consumption_reference_readable(self):
        reference=dict(status='CONSUMED',reason=None,run_id='d'*32,matches=self.matches,**FLAGS)
        self.install(self.matches,owner=dict(unrelated='x'*1_331_642,
            us_mapping_daily_plan_reference=reference))
        url=self.start();before=self.snapshot();status,page,_,_=self.get(url,self.path())
        self.assertEqual(status,200)
        projected=page['us_mapping']['plan_reference']
        self.assertEqual(projected['value_state'],'LOADED')
        self.assertEqual(projected['value']['status'],'CONSUMED')
        self.assertIsNone(projected['value']['reason'])
        span=projected['source_span'];original=self.raw[span['offset']:span['offset']+span['bytes']]
        self.assertEqual(json.loads(original),reference);self.assertEqual(m.sha(original),span['sha256'])
        self.assertEqual(self.snapshot(),before)
        plain=m.Reader(self.bundle,m.sha(self.bundle.manifest),self.identity,expected_profile=m.PROFILE_SHA256)
        self.assertEqual(self.reader.counts,plain.counts);self.assertEqual(self.reader._sections,plain._sections)
        capture=self.reader._span_observer
        self.assertEqual(set(vars(capture)),{'span'})
        self.assertEqual(set(capture.span),{'kind','offset','bytes','sha256'})
        from v5_shadow.module_api import _m18_semantic_value
        original_parts=self.reader.item_parts
        def only_mapping(section,index):
            self.assertEqual(section,SECTION)
            return original_parts(section,index)
        with patch.object(self.reader,'item_parts',side_effect=only_mapping),\
                patch.object(self.reader,'full_response',side_effect=AssertionError('no full response')):
            self.assertEqual(_m18_semantic_value(self.reader,'us_mapping',self.query())['us_mapping']['plan_reference'],projected)

    def run_node(self,url,script):
        import shutil
        import subprocess
        from pathlib import Path
        node=shutil.which('node')
        if not node:self.skipTest('Node unavailable; HTTP frontend acceptance not run')
        client=Path(__file__).resolve().parents[2]/'frontend/src/api/m18SavedResult.ts'
        script='''
import assert from 'node:assert/strict';
import { M18SavedClient, SavedRunSession } from CLIENT;
const session=new SavedRunSession(new M18SavedClient((url,options)=>fetch(BASE+url,options)));
await session.load(RUN);
assert.equal(session.state.phase,'LOADED');
assert.equal(session.state.page.projection,'announcement_references');
'''+script+'''\nsession.close();'''
        script=script.replace('CLIENT',json.dumps(client.as_uri())).replace('BASE',json.dumps(url)).replace('RUN',json.dumps(base.RUN))
        result=subprocess.run([node,'--input-type=module','-e',script],capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_real_http_typescript_client_preserves_same_run_matches_and_plan_reference(self):
        url=self.start();before=self.snapshot()
        self.run_node(url,'''
await session.select('us_mapping_research');
assert.equal(session.state.phase,'LOADED',session.state.error);
const page=session.state.page;
assert.equal(page.projection,'us_mapping_matches');
assert.equal(page.matched_total,4);assert.equal(page.entries.length,4);
assert.equal(new Set(page.entries.map(e=>e.value.hk_symbol)).size,3);
assert.equal(page.entries[3].value.us_symbol,'LITE');
assert.equal(page.entries[0].value.target_date_eligibility,'CANNOT_CONFIRM');
assert.equal(page.entries[0].value.production_allowed,false);
assert.equal(page.us_mapping.daily_run.status,'COMPLETED');
assert.equal(page.us_mapping.daily_run.source_status,'READY');
assert.equal(page.us_mapping.daily_run.coverage.available_us_universe_count,null);
assert.equal(page.us_mapping.coverage_diagnostics.configured_sample_count,33);
assert.equal(page.us_mapping.coverage_diagnostics.natural_verified,false);
assert.equal(page.us_mapping.plan_reference.value.status,'NOT_CONSUMED');
assert.equal(page.us_mapping.plan_reference.value.plan_cutoff,null);
assert.equal(page.us_mapping.source.registry_readback.seed_target_date,'20260930');
assert.equal(JSON.stringify(page).includes('HISTORICAL_NOT_DAILY'),false);
assert.equal(page.next_cursor,null);assert.equal(session.state.canPrevious,false);
await session.select('stocks');assert.equal(session.state.page.matched_total,0);
await session.select('announcement_reviewed_analysis');
assert.equal(session.state.page.projection,'announcement_references');
assert.equal(session.state.page.entries[0].value.stock_code,'ANN');
''')
        self.assertEqual(before,self.snapshot())

    def test_real_http_typescript_variable_history_and_null_diagnostics(self):
        self.install([dict(body='x'*(size-11)) for size in [4500]*29+[4367]*41])
        url=self.start();before=self.snapshot()
        self.run_node(url,'''
await session.select('us_mapping_research');
const seen=[];
for(const [offset,count] of [[0,29],[29,30],[59,11]]) {
 assert.equal(session.state.phase,'LOADED',session.state.error);
 assert.equal(session.state.page.offset,offset);assert.equal(session.state.page.entries.length,count);
 assert.ok(session.state.page.entries.every(e=>e.value_state==='LOADED'));
 assert.equal(session.state.page.us_mapping.plan_reference.value_state,'NOT_LOADED');
 seen.push(...session.state.page.entries.map(e=>e.index));
 if(offset!==59)await session.next();
}
assert.deepEqual(seen,Array.from({length:70},(_,i)=>i));
assert.equal(session.state.page.next_cursor,null);
await session.previous();assert.equal(session.state.page.offset,29);
await session.previous();assert.equal(session.state.page.offset,0);
await session.next();assert.equal(session.state.page.offset,29);
await session.select('stocks');assert.equal(session.state.page.matched_total,0);
await session.select('us_mapping_research');assert.equal(session.state.page.offset,0);
assert.equal(session.state.canPrevious,false);
''')
        self.assertEqual(before,self.snapshot())
        self.install([],owner=None,change_mapping=lambda value:value.update(coverage_diagnostics=None))
        url=self.start();before=self.snapshot()
        self.run_node(url,'''
await session.select('us_mapping_research');assert.equal(session.state.phase,'LOADED',session.state.error);
assert.equal(session.state.page.us_mapping.coverage_diagnostics,null);
assert.equal(session.state.page.us_mapping.plan_reference.reason,'OWNER_CHAIN_MISSING');
assert.deepEqual(session.state.page.entries,[]);assert.equal(session.state.page.next_cursor,null);
''')
        self.assertEqual(before,self.snapshot())

    def test_empty_missing_and_null_metadata_are_not_promoted(self):
        from v5_shadow.module_api import _m18_semantic_value
        def valid_empty(value):
            value['daily_run']['status']='VALID_EMPTY';value['coverage_diagnostics']['configured_sample_count']=0
        self.install([],change_mapping=valid_empty,owner=None)
        page=_m18_semantic_value(self.reader,'us_mapping',self.query())
        self.assertEqual(page['matched_total'],0);self.assertEqual(page['loaded_count'],0)
        self.assertIsNone(page['next_cursor']);self.assertEqual(page['us_mapping']['daily_run']['status'],'VALID_EMPTY')
        self.assertEqual(page['us_mapping']['coverage_diagnostics']['configured_sample_count'],0)
        def unavailable(value):
            value['daily_run']['status']='CANNOT_CONFIRM';value['daily_run']['coverage']=None
            value['coverage_diagnostics']=None
        self.install([],change_mapping=unavailable,owner=None)
        page=_m18_semantic_value(self.reader,'us_mapping',self.query())
        self.assertEqual(page['us_mapping']['daily_run']['status'],'CANNOT_CONFIRM')
        self.assertIsNone(page['us_mapping']['coverage_diagnostics'])
        self.assertIsNone(page['us_mapping']['daily_run']['coverage'])
        self.install([],change_mapping=lambda value:value['daily_run'].pop('matches'),owner=None)
        with self.assertRaises(m.ContractError):_m18_semantic_value(self.reader,'us_mapping',self.query())

    def test_supervisor_selector_receipt_and_fresh_process_are_closed(self):
        from v5_shadow.module_api import _m18_semantic_value
        query=self.query();request=dict(binding=self.config['m18_v2_binding'],kind='us_mapping',query=query)
        process._validate(request);page=_m18_semantic_value(self.reader,'us_mapping',query)
        process._check_payload(page,request)
        for change in (dict(section='stocks'),dict(projection='announcement_references'),dict(group='strict'),dict(path='daily_run.matches')):
            with self.subTest(change=change),self.assertRaises(m.ContractError):process._validate(dict(request,query=dict(query,**change)))
        for change in (dict(projection='announcement_references'),dict(offset=1),dict(group='strict'),
            dict(us_mapping=dict(page['us_mapping'],match_count=5))):
            with self.subTest(change=change),self.assertRaises(m.ContractError):process._check_payload(dict(page,**change),request)
        before=self.snapshot();first=process.run(request);second=process.run(request)
        self.assertEqual(first['status'],'OK');self.assertEqual(second['status'],'OK')
        self.assertNotEqual(first['pid'],second['pid']);self.assertNotEqual(first['pid'],os.getpid())
        self.assertTrue(first['worker_reaped']);self.assertTrue(second['worker_reaped'])
        self.assertEqual(first['payload'],page);self.assertEqual(before,self.snapshot())

    def test_unchanged_source_and_http_budgets_fail_before_unsafe_load(self):
        from v5_shadow.module_api import _m18_semantic_value
        original=dict(m.PROFILE)
        with patch.object(self.reader,'full_response',side_effect=AssertionError('no full response')):
            self.assertEqual(_m18_semantic_value(self.reader,'us_mapping',self.query())['matched_total'],4)
        large=copy.deepcopy(self.reader.detail(SECTION));large['entries'][0]['bytes']=m.PROFILE['object_bytes']
        with patch.object(self.reader,'detail',return_value=large),\
                patch.object(self.reader,'item_parts',side_effect=AssertionError('must reject before read')),\
                self.assertRaisesRegex(m.ContractError,'V2_OBJECT_BYTES'):
            _m18_semantic_value(self.reader,'us_mapping',self.query())
        def metadata_overflow(value):value['daily_run']['gaps']=['x'*17000]
        self.install(self.matches,change_mapping=metadata_overflow,owner=None)
        with self.assertRaisesRegex(m.ContractError,'V2_US_MAPPING_METADATA_BYTES'):
            _m18_semantic_value(self.reader,'us_mapping',self.query())
        self.assertEqual(dict(m.PROFILE),original)


if __name__=='__main__':unittest.main()
