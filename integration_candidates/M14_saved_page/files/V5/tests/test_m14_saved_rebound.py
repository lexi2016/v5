"""Synthetic persisted trios only; no owner calculation or real market data."""
import base64
import copy
import hashlib
import json
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from unittest.mock import patch
import test_rebound_owner as fixture
from v5_shadow import module_api, rebound_owner as owner
from v5_shadow.digests import canonical_bytes, sha256_json

ROUTE='/api/v5/source-bundle/rebound-saved'
GROUPS=('strict','near','pending','excluded','screen_unresolved')

class M14SavedTests(unittest.TestCase):
    def setUp(self):
        fixture.ReboundOwnerPersistenceTests.setUp(self)
        self.artifact['run_id']='4'*32
        legacy=self.artifact['legacy_diagnostic']['payload']
        for group in GROUPS:legacy[group]=[]
        legacy['cards']=[]
        legacy['pending']=[dict(code=f'HK.{i:05}',name='SYNTHETIC',classification='PENDING',
            target_monday=20261008,verified_session=20261007,prior60_session_count=57,
            previous5_session_count=3,history_unknown_reasons='PREVIOUS_5_SESSIONS_INCOMPLETE:3',
            source_refs=[dict(owner='SYNTHETIC',payload_path=str(self.output/'private'),
                              payload_sha256='a'*64)],private_root=str(self.output)) for i in range(70)]
        legacy['coverage']=dict(history_pending_count=70,strict_count=0,near_count=0)
        self.artifact['research_observation']=owner.research_projection(legacy,{})
        self.reference=owner._publish(self.output,self.artifact)
        self.api_root=self.root/'api';self.api_root.mkdir()
        (self.api_root/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
        self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='synthetic-m14',
            data_root=str(self.api_root),routes=[ROUTE],
            m14_rebound_binding=dict(private_root=str(self.output),reference=self.reference))

    def start(self):
        server=module_api.create_module_server(self.config)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return f'http://127.0.0.1:{server.server_port}'

    def get(self,url,query=None):
        try:r=urlopen(url+ROUTE+'?'+urlencode(query or {}),timeout=5)
        except HTTPError as error:r=error
        with r:return r.status,json.load(r)

    def snapshot(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()}

    def test_independent_saved_pages_pin_four_refs_and_keep_gaps_without_m18_identity(self):
        url=self.start();before=self.snapshot();cursor=None;seen=[]
        with patch.object(owner,'run_rebound_owner',side_effect=AssertionError('must never calculate')):
            for offset,size in ((0,32),(32,32),(64,6)):
                query=dict(group='pending',**self.reference)
                if cursor:query['cursor']=cursor
                status,page=self.get(url,query);self.assertEqual(status,200,page)
                self.assertEqual(page['reference'],self.reference)
                self.assertEqual((page['target_date'],page['signal_date']),('20261008','20261007'))
                self.assertEqual(page['rebound']['group_counts'],dict(strict=0,near=0,pending=70,excluded=0,screen_unresolved=0))
                self.assertEqual(page['rebound']['observation']['original_computation_status'],'READY_WITH_GAPS')
                self.assertEqual(page['rebound']['source']['status'],'CANNOT_CONFIRM')
                self.assertIsNone(page['rebound']['source']['eligible_screen'])
                self.assertEqual(page['offset'],offset);self.assertEqual(len(page['entries']),size)
                self.assertFalse(set(('generation_id','identity','profile_sha256'))&set(page))
                raw=json.dumps(page);self.assertNotIn(str(self.output),raw);self.assertNotIn('payload_path',raw)
                self.assertLessEqual(len(canonical_bytes(page)),256*1024)
                for entry in page['entries']:
                    original=self.artifact['research_observation']['pending'][entry['index']]
                    self.assertEqual(entry['sha256'],sha256_json(original))
                    self.assertEqual(entry['projection_sha256'],sha256_json(entry['value']))
                    self.assertEqual(entry['value']['previous5_session_count'],3)
                    seen.append(entry['index'])
                cursor=page['next_cursor']
            self.assertIsNone(cursor);self.assertEqual(seen,list(range(70)))
            for group in GROUPS:
                status,page=self.get(url,dict(group=group));self.assertEqual(status,200)
                self.assertEqual(page['group'],group)
        self.assertEqual(before,self.snapshot())
        self.assertEqual(owner.read_rebound_owner(self.output,self.reference),self.artifact)

    def test_unknown_queries_partial_refs_and_cross_group_cursor_reject(self):
        url=self.start();status,first=self.get(url,dict(group='pending'));self.assertEqual(status,200)
        for query in (dict(root=str(self.output)),dict(run_id=self.reference['run_id']),dict(group='cards'),
                      dict(group='strict',cursor=first['next_cursor']),dict(group='pending',cursor='bad'),
                      dict(group='pending',**dict(self.reference,artifact_sha256='0'*64)),dict(date='20261014')):
            with self.subTest(query=query):self.assertEqual(self.get(url,query)[0],409)
        forged=json.loads(base64.urlsafe_b64decode(first['next_cursor']));forged['receipt_sha256']='0'*64
        cursor=base64.urlsafe_b64encode(canonical_bytes(forged)).decode()
        self.assertEqual(self.get(url,dict(group='pending',cursor=cursor))[0],409)

    def test_every_get_rechecks_each_original_trio_sha(self):
        url=self.start();self.assertEqual(self.get(url)[0],200)
        for name in ('artifact','manifest','receipt'):
            path=self.output/'runs'/self.reference['run_id']/(name+'.json');raw=path.read_bytes()
            path.write_bytes(raw+b'\n')
            self.assertEqual(self.get(url)[0],409)
            path.write_bytes(raw);self.assertEqual(self.get(url)[0],200)

    def test_paths_and_symlinks_reject_without_exposing_private_root(self):
        config=copy.deepcopy(self.config);config['m14_rebound_binding']['private_root']=str(self.output)+'/../output'
        with self.assertRaises(ValueError):module_api.create_module_server(config)
        for target in (self.output,self.output/'runs',self.output/'runs'/self.reference['run_id'],
                       self.output/'runs'/self.reference['run_id']/'artifact.json'):
            with self.subTest(target=target):
                actual=target.with_name(target.name+'-real');target.rename(actual);target.symlink_to(actual,target_is_directory=actual.is_dir())
                try:
                    try:server=self.start()
                    except (ValueError,OSError):continue
                    status,page=self.get(server);self.assertEqual(status,409);self.assertNotIn(str(self.output),json.dumps(page))
                finally:target.unlink();actual.rename(target)

    def test_missing_binding_is_waiting_not_an_empty_success(self):
        del self.config['m14_rebound_binding'];url=self.start();status,page=self.get(url)
        self.assertEqual(status,200);self.assertEqual(page['status'],'WAITING');self.assertNotIn('entries',page)
        self.assertEqual(self.get(url,dict(root='/tmp'))[0],409)

    def test_old_reference_remains_readable_after_config_binds_another_run(self):
        old=copy.deepcopy(self.reference);old_artifact=copy.deepcopy(self.artifact)
        self.artifact['run_id']='5'*32;new=owner._publish(self.output,self.artifact)
        self.config['m14_rebound_binding']['reference']=new;url=self.start()
        self.assertEqual(self.get(url)[1]['reference'],new)
        self.assertEqual(self.get(url,old)[0],409)
        self.assertEqual(owner.read_rebound_owner(self.output,old),old_artifact)


class M14SavedBoundaryTests(unittest.TestCase):
    setUp = M14SavedTests.setUp
    start = M14SavedTests.start
    get = M14SavedTests.get
    snapshot = M14SavedTests.snapshot
    # Reuse synthetic persisted setup, not the original owner calculation.
    def republish(self, rows):
        self.artifact['run_id']='6'*32
        legacy=self.artifact['legacy_diagnostic']['payload'];legacy['pending']=rows
        self.artifact['research_observation']=owner.research_projection(legacy,{})
        self.reference=owner._publish(self.output,self.artifact)
        self.config['m14_rebound_binding']['reference']=self.reference

    def test_public_projection_excludes_all_private_paths_and_unknown_nested_fields(self):
        self.republish([dict(code='SYNTHETIC',name='synthetic',history_unknown_reasons='GAP:/private/hidden/file',
            payload_path='/private/hidden',manifest_path='/private/hidden',artifact_path='/private/hidden',
            arbitrary={'secret':'not-public'},source_refs=[dict(owner='SYNTHETIC',payload_path='/private/hidden',
            manifest_path='/private/hidden',artifact_path='/private/hidden',payload_sha256='b'*64)])])
        status,page=self.get(self.start(),dict(group='pending'));self.assertEqual(status,200,page)
        text=json.dumps(page);self.assertNotIn('/private/hidden',text);self.assertNotIn('not-public',text)
        self.assertEqual(page['entries'][0]['value']['source_refs'],[dict(owner='SYNTHETIC',payload_sha256='b'*64)])

    def test_complete_sha_and_bounded_rows_progress_without_dropping_deferred_rows(self):
        rows=[dict(code='BIG',name='x'*17000)]+[dict(code=str(i),name='x'*10000) for i in range(32)]
        self.republish(rows);url=self.start();cursor=None;seen=[]
        while True:
            query=dict(group='pending')
            if cursor:query['cursor']=cursor
            status,page=self.get(url,query);self.assertEqual(status,200,page)
            self.assertLessEqual(len(canonical_bytes(page)),256*1024)
            self.assertLessEqual(sum(e['bytes'] for e in page['entries'] if e['value_state']=='LOADED'),128*1024)
            self.assertGreater(len(page['entries']),0);seen.extend(page['entries']);cursor=page['next_cursor']
            if cursor is None:break
        self.assertEqual([e['index'] for e in seen],list(range(len(rows))))
        self.assertEqual(seen[0]['value_state'],'NOT_LOADED');self.assertNotIn('value',seen[0])
        self.assertEqual(seen[0]['sha256'],sha256_json(self.artifact['research_observation']['pending'][0]))

    def test_690_pending_rows_and_history_gaps_remain_visible_across_all_pages(self):
        self.artifact['legacy_diagnostic']['payload']['gaps'] = [f'SYNTHETIC_HISTORY_MISSING:{i}' for i in range(690)]
        self.artifact['legacy_diagnostic']['payload']['coverage'] = dict(history_pending_count=690,strict_count=0,near_count=0)
        self.republish([dict(code=f'SYNTHETIC_{i}',previous5_session_count=3 if i<688 else 2,
                            prior60_session_count=57,history_unknown_reasons='SYNTHETIC_INCOMPLETE_HISTORY') for i in range(690)])
        url=self.start();seen=[];cursor=None
        while True:
            query=dict(group='pending')
            if cursor:query['cursor']=cursor
            status,page=self.get(url,query);self.assertEqual(status,200,page)
            self.assertEqual(page['rebound']['group_counts'],dict(strict=0,near=0,pending=690,excluded=0,screen_unresolved=0))
            self.assertGreaterEqual(len(page['rebound']['observation']['gaps']),690)
            self.assertEqual(page['rebound']['observation']['original_computation_status'],'READY_WITH_GAPS')
            self.assertFalse(page['formal_eligibility_verified']);self.assertFalse(page['natural_verified'])
            seen.extend(e['value']['code'] for e in page['entries']);cursor=page['next_cursor']
            if cursor is None:break
        self.assertEqual(seen,[f'SYNTHETIC_{i}' for i in range(690)])
        status,empty=self.get(url,dict(group='strict'));self.assertEqual(status,200)
        self.assertEqual(empty['matched_total'],0);self.assertEqual(empty['rebound']['group_counts']['pending'],690)

    def test_cursor_duplicate_keys_noninteger_out_of_range_and_extra_keys_reject(self):
        url=self.start();status,page=self.get(url,dict(group='pending'));self.assertEqual(status,200)
        value=json.loads(base64.urlsafe_b64decode(page['next_cursor']))
        for key,bad in [('offset',True),('offset',32.5),('offset',70),('offset',-1),('other',1)]:
            forged=dict(value,**{key:bad});cursor=base64.urlsafe_b64encode(canonical_bytes(forged)).decode()
            with self.subTest(key=key,bad=bad):self.assertEqual(self.get(url,dict(group='pending',cursor=cursor))[0],409)
        raw=canonical_bytes(value).decode();cursor=base64.urlsafe_b64encode((raw[:-1]+',"offset":32}').encode()).decode()
        self.assertEqual(self.get(url,dict(group='pending',cursor=cursor))[0],409)

    def test_rehashed_cross_file_identity_tampering_is_rejected(self):
        path=self.output/'runs'/self.reference['run_id']/'receipt.json';receipt=json.loads(path.read_bytes());receipt['run_id']='7'*32
        path.write_bytes(canonical_bytes(receipt));self.reference['receipt_sha256']=sha256_json(receipt)
        self.assertEqual(self.get(self.start())[0],409)

    def test_missing_observation_does_not_masquerade_as_five_empty_groups(self):
        self.artifact.update(run_id='8'*32,research_observation=None,legacy_diagnostic=None,computation_status='CANNOT_CONFIRM')
        self.reference=owner._publish(self.output,self.artifact);self.config['m14_rebound_binding']['reference']=self.reference
        status,page=self.get(self.start());self.assertEqual(status,409);self.assertNotIn('entries',page)

if __name__=='__main__':unittest.main()
