"""Synthetic original-owner trios only; no Mac data or market/PIT attestation."""
import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from v5_shadow.digests import canonical_bytes, sha256_json
from v5_shadow.module_api import _config, create_module_server, read_response

STAGES = ('STAGE_0925', 'STAGE_0930_0935', 'STAGE_0935_0940', 'STAGE_0940_0945',
          'STAGE_0945_1030', 'STAGE_1300_1315', 'STAGE_1445_1500', 'STAGE_1545_1555')
ROUTE = '/api/v5/hk-stage-observed'
FIXTURE_SCRIPT = r'''
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from v5_shadow.hk_stage_sources import load_owners
from v5_shadow.digests import sha256_json
selection, contracts, calendar = load_owners()
root=Path(sys.argv[2]);store=selection.SelectionStore(root)
stages=json.loads(sys.argv[3]);result=[]
cases=[('20261008', stage, 10, 'PARTIAL_WITH_ROWS' if stage in stages[1:7] else 'READY',
        ['SYNTHETIC_SOURCE_GAP'] if stage in stages[1:7] else []) for stage in stages]
cases += [('20261009', stages[0], 0, 'READY_EMPTY', []),
          ('20261009', stages[1], 0, 'CANNOT_CONFIRM', ['SYNTHETIC_SOURCE_MISSING'])]
for date, stage, count, status, cannot in cases:
    rows=[dict(code=f'HK.{i:05}',rank=i,auction_score=100-i,
          reference_price_hkd=11,strict_failure_price_hkd=10.5,ask_price=11.1,bid_price=10.9,
          second_filter_status='WATCH_ONLY',preselect_lane='D1_MODEL_TOP100',
          candidate_lanes=['D1_MODEL_TOP100'],open_price=10,last_price=11,high_price=11,low_price=10,
          pct_chg=10,volume_ratio=2,turnover_hkd=100000000,circular_market_cap_hkd_yi=20)
          for i in range(1,count+1)]
    kwargs=dict(source_status=status,requested_rows=count,missing_symbols=[],cannot_confirm=cannot,
                source_evidence=['fixture_only=SYNTHETIC',
                                 'active_snapshot_path=/Users/Private Person/source snapshot.json'])
    raw_hash=sha256_json(dict(date=date,stage=stage,rows=rows,status=status))
    if stage=='STAGE_0925':
        artifact=selection.select_hk_0925_second_filter(rows,date,raw_hash,**kwargs)
    else:
        artifact=selection.select_hk_four_lane(rows,date,stage,raw_hash,**kwargs)
    artifact=store.publish(artifact,market='HK_CONNECT')
    verified=store._verify_run(date,stage,'HK_CONNECT',artifact['run_id'])
    prefix=f"selection_runs/{date}/HK_CONNECT_SELECTION_{stage}/{artifact['run_id']}"
    trio={}
    for name in ('artifact.csv','manifest.json','receipt.json'):
        path=root/prefix/name;raw=path.read_bytes()
        trio[name]=dict(relative_path=f'{prefix}/{name}',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    result.append(dict(date=date,stage=stage,run_id=artifact['run_id'],source_status=artifact['source_status'],
                       rows=len(artifact['rows']),reader='ORIGINAL_SelectionStore._verify_run_PASS',trio=trio,
                       canonical={k:verified[k] for k in ('artifact_sha256','manifest_sha256','receipt_sha256')},
                       artifact=artifact))
print(json.dumps(result))
'''


class HKObservedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_temp=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixture_temp.cleanup)
        cls.fixture_root=Path(cls.fixture_temp.name)/'original'
        cls.fixture_root.mkdir()
        source=Path(__file__).resolve().parents[1]/'src'
        proc=subprocess.run([sys.executable,'-I','-B','-c',FIXTURE_SCRIPT,str(source),
                             str(cls.fixture_root),json.dumps(STAGES)],capture_output=True,text=True,timeout=30)
        if proc.returncode:
            raise AssertionError(proc.stderr)
        cls.fixtures=json.loads(proc.stdout)

    def setUp(self):
        self.api=importlib.import_module('v5_shadow.hk_stage_observed')
        self.publisher=importlib.import_module('v5_shadow.hk_stage_observed_api')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        self.source=self.base/'original';shutil.copytree(self.fixture_root,self.source)
        self.recorded=self.base/'recorded';self.api.init_hk_observed_root(self.recorded)

    def inventory(self,index=0):
        return {k:copy.deepcopy(v) for k,v in self.fixtures[index].items() if k not in ('canonical','artifact','date')}

    def expected(self,index=0):
        return self.api.prepare_hk_stage_observed_reference(self.source,self.inventory(index),
                                                           target_date=self.fixtures[index]['date'])

    def imported(self,index=0):
        return self.api.import_hk_stage_observed(self.source,self.recorded,self.expected(index))

    def files(self,root):
        return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def committed_dirs(self):
        imports=self.recorded/'imports'
        return [p for p in imports.glob('*') if len(p.name)==64 and all(c in '0123456789abcdef' for c in p.name)]

    def config(self):
        responses=self.base/'responses';responses.mkdir()
        (responses/'.v5-module-root').write_text('v5.module-root.v1:hk_stage\n')
        return dict(schema_version='v5.module_api.v1',module_id='hk_stage',release_id='observed-test',
                    data_root=str(responses),routes=[ROUTE])

    def test_prepare_augments_inventory_with_original_canonical_hashes(self):
        expected=self.expected()
        self.assertEqual(expected['trio'],self.inventory()['trio'])
        self.assertEqual(expected['market'],'HK_CONNECT')
        for key,value in self.fixtures[0]['canonical'].items():
            self.assertEqual(expected[key],value)
        self.assertNotEqual(expected['manifest_sha256'],expected['trio']['manifest.json']['sha256'])
        self.assertNotIn(str(self.source),json.dumps(expected))

    def test_all_eight_stages_copy_exact_bytes_and_survive_source_removal(self):
        before=self.files(self.source);results=[]
        for index in range(8):
            result=self.imported(index);results.append(result)
            owner=self.recorded/'imports'/result['reference']['import_sha256']/'owner'
            for info in self.inventory(index)['trio'].values():
                self.assertEqual((owner/info['relative_path']).read_bytes(),(self.source/info['relative_path']).read_bytes())
            self.assertFalse((owner/'selection_latest.json').exists())
        self.assertEqual(self.files(self.source),before)
        self.source.rename(self.base/'offline-original')
        for index,result in enumerate(results):
            read=self.api.read_hk_stage_observed(self.recorded,result['reference'])
            self.assertEqual(read['artifact'],self.fixtures[index]['artifact'])
            self.assertEqual(read['reference'],result['reference'])
            self.assertEqual(read['read_status'],'VERIFIED')
            self.assertEqual(read['provenance']['data_kind'],'OWNER_RESULT')
            self.assertEqual(read['provenance']['evidence_mode'],'HISTORICAL')
            self.assertEqual(read['provenance']['qualification'],'OBSERVED_ONLY')
            self.assertIsNone(read['provenance']['captured_at'])
            for flag in ('natural_verified','pit_verified','formal_admission','raw_input_verified','computation_replayed'):
                self.assertIs(read['provenance'][flag],False)
            for flag in ('production_allowed','buy_gate_updated','orders_sent'):
                self.assertIs(read[flag],False)

    def test_missing_canonical_fields_cannot_be_imported(self):
        expected=self.expected();expected.pop('receipt_sha256')
        with self.assertRaises(ValueError):
            self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        self.assertEqual(self.committed_dirs(),[])

    def test_wrong_identity_digest_size_and_layout_are_rejected(self):
        expected=self.expected()
        mutations=[lambda r:r.update(market='A_SHARE'),lambda r:r.update(target_date='20261009'),
                   lambda r:r.update(stage_id=STAGES[1]),lambda r:r.update(run_id='run-wrong'),
                   lambda r:r.update(manifest_sha256='f'*64),
                   lambda r:r['trio']['artifact.csv'].update(sha256='f'*64),
                   lambda r:r['trio']['artifact.csv'].update(bytes=1),
                   lambda r:r['trio']['artifact.csv'].update(relative_path='../artifact.csv')]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                bad=copy.deepcopy(expected);mutation(bad)
                with self.assertRaises((ValueError,OSError)):
                    self.api.import_hk_stage_observed(self.source,self.recorded,bad)
                self.assertEqual(self.committed_dirs(),[])

    def test_source_missing_symlink_and_whitespace_tamper_are_rejected(self):
        expected=self.expected();path=self.source/expected['trio']['manifest.json']['relative_path']
        raw=path.read_bytes();path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'BYTES'):
            self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        path.write_bytes(raw);other=self.base/'saved-manifest.json';path.rename(other);path.symlink_to(other)
        with self.assertRaises((ValueError,OSError)):
            self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        path.unlink()
        with self.assertRaises((ValueError,OSError)):
            self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        self.assertEqual(self.committed_dirs(),[])

    def test_pinned_raw_bytes_do_not_replace_original_reader_verification(self):
        entry=self.inventory();path=self.source/entry['trio']['receipt.json']['relative_path']
        value=json.loads(path.read_bytes());value['row_count']=999
        raw=canonical_bytes(value);path.write_bytes(raw)
        import hashlib
        entry['trio']['receipt.json'].update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        with self.assertRaisesRegex(ValueError,'row_count'):
            self.api.prepare_hk_stage_observed_reference(self.source,entry,target_date='20261008')

    def test_marked_empty_distinct_destination_required(self):
        dirty=self.base/'dirty';dirty.mkdir();(dirty/'keep').write_text('existing')
        with self.assertRaises(ValueError):self.api.init_hk_observed_root(dirty)
        alias=self.base/'alias';alias.symlink_to(self.recorded,target_is_directory=True)
        with self.assertRaises((ValueError,OSError)):self.api.read_hk_stage_observed(alias,{})
        with self.assertRaises(ValueError):
            self.api.import_hk_stage_observed(self.source,self.source,self.expected())
        unmarked=self.base/'unmarked';unmarked.mkdir()
        with self.assertRaises((ValueError,OSError)):
            self.api.import_hk_stage_observed(self.source,unmarked,self.expected())
        self.assertEqual((dirty/'keep').read_text(),'existing')

    def test_latest_pointers_are_never_consulted(self):
        expected=self.expected(1)
        (self.source/'selection_latest.json').write_text('not json')
        result=self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        owner=self.recorded/'imports'/result['reference']['import_sha256']/'owner'
        (owner/'selection_latest.json').write_text('also not json')
        read=self.api.read_hk_stage_observed(self.recorded,result['reference'])
        self.assertEqual(read['artifact'],self.fixtures[1]['artifact'])
        self.assertEqual(read['artifact']['selection_status'],'PARTIAL_WITH_ROWS')
        self.assertIn('SYNTHETIC_SOURCE_GAP',read['artifact']['cannot_confirm'])

    def test_rehashed_envelope_metadata_and_numeric_false_are_rejected(self):
        import hashlib
        entry=self.inventory()
        manifest_path=self.source/entry['trio']['manifest.json']['relative_path']
        receipt_path=self.source/entry['trio']['receipt.json']['relative_path']
        saved_manifest=manifest_path.read_bytes();saved_receipt=receipt_path.read_bytes()
        mutations=[lambda a:a.update(market='A_SHARE'),lambda a:a.update(trade_date='20261009'),
                   lambda a:a.update(stage_id=STAGES[1]),lambda a:a.update(production_allowed=0),
                   lambda a:a.update(selection_status='CANNOT_CONFIRM'),lambda a:a.update(source_status='LIVE')]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                manifest=json.loads(saved_manifest);receipt=json.loads(saved_receipt)
                mutate(manifest['selection_envelope']);receipt['manifest_sha256']=sha256_json(manifest)
                changed=copy.deepcopy(entry)
                for name,value in (('manifest.json',manifest),('receipt.json',receipt)):
                    raw=canonical_bytes(value)+b'\n';(self.source/entry['trio'][name]['relative_path']).write_bytes(raw)
                    changed['trio'][name].update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
                with self.assertRaises(ValueError):
                    self.api.prepare_hk_stage_observed_reference(self.source,changed,target_date='20261008')
                manifest_path.write_bytes(saved_manifest);receipt_path.write_bytes(saved_receipt)

    def test_exact_retry_is_immutable_and_reuses_import_time(self):
        first=self.imported();before=self.files(self.recorded)
        mtimes={str(p):p.stat().st_mtime_ns for p in self.recorded.rglob('*') if p.is_file()}
        second=self.imported()
        self.assertTrue(second['reused']);self.assertFalse(first['reused'])
        self.assertEqual(first['reference'],second['reference'])
        self.assertEqual(first['provenance']['imported_at'],second['provenance']['imported_at'])
        self.assertEqual(self.files(self.recorded),before)
        self.assertEqual(mtimes,{str(p):p.stat().st_mtime_ns for p in self.recorded.rglob('*') if p.is_file()})

    def test_same_run_different_metadata_never_overwrites_previous_import(self):
        first=self.imported();before=self.files(self.recorded)
        entry=self.inventory();manifest_path=self.source/entry['trio']['manifest.json']['relative_path']
        receipt_path=self.source/entry['trio']['receipt.json']['relative_path']
        manifest=json.loads(manifest_path.read_bytes());receipt=json.loads(receipt_path.read_bytes())
        manifest['selection_envelope']['source_evidence'].append('new_observation=separate')
        receipt['manifest_sha256']=sha256_json(manifest)
        import hashlib
        for name,value in (('manifest.json',manifest),('receipt.json',receipt)):
            raw=canonical_bytes(value)+b'\n';(self.source/entry['trio'][name]['relative_path']).write_bytes(raw)
            entry['trio'][name].update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        expected=self.api.prepare_hk_stage_observed_reference(self.source,entry,target_date='20261008')
        second=self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        self.assertNotEqual(first['reference']['import_sha256'],second['reference']['import_sha256'])
        self.assertEqual(first['reference']['run_id'],second['reference']['run_id'])
        for name,raw in before.items():self.assertEqual((self.recorded/name).read_bytes(),raw)
        self.assertEqual(self.api.read_hk_stage_observed(self.recorded,first['reference'])['artifact'],self.fixtures[0]['artifact'])

    def test_failed_copy_never_commits_or_corrupts_previous_import(self):
        first=self.imported();before=self.files(self.recorded);expected=self.expected(1)
        original=self.api._write_bytes
        def fail_manifest(path,raw):
            if Path(path).name=='manifest.json':raise OSError('INJECTED_COPY_FAILURE')
            return original(path,raw)
        with patch.object(self.api,'_write_bytes',side_effect=fail_manifest):
            with self.assertRaisesRegex(OSError,'INJECTED_COPY_FAILURE'):
                self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        self.assertEqual(len(self.committed_dirs()),1)
        for name,raw in before.items():self.assertEqual((self.recorded/name).read_bytes(),raw)
        self.assertEqual(self.api.read_hk_stage_observed(self.recorded,first['reference'])['read_status'],'VERIFIED')

    def test_copied_owner_must_verify_before_commit(self):
        expected=self.expected();original=self.api._verify_owner;calls=[]
        def fail_copy(root,ref):
            calls.append(str(root))
            if Path(root)!=self.source:raise ValueError('INJECTED_COPIED_OWNER_FAILURE')
            return original(root,ref)
        with patch.object(self.api,'_verify_owner',side_effect=fail_copy):
            with self.assertRaisesRegex(ValueError,'INJECTED_COPIED_OWNER_FAILURE'):
                self.api.import_hk_stage_observed(self.source,self.recorded,expected)
        self.assertEqual(len(calls),2);self.assertEqual(self.committed_dirs(),[])

    def test_cold_reader_rejects_each_changed_original_file(self):
        result=self.imported();ref=result['reference'];owner=self.recorded/'imports'/ref['import_sha256']/'owner'
        for info in self.inventory()['trio'].values():
            path=owner/info['relative_path'];raw=path.read_bytes();path.write_bytes(raw+b' ')
            with self.assertRaisesRegex(ValueError,'BYTES'):
                self.api.read_hk_stage_observed(self.recorded,ref)
            path.write_bytes(raw)

    def test_exact_reference_and_import_receipt_tampering_fail(self):
        result=self.imported();ref=result['reference']
        for key in ('import_sha256','import_receipt_sha256','run_id','target_date'):
            bad=copy.deepcopy(ref);bad[key]='f'*64 if key.endswith('sha256') else ('run-wrong' if key=='run_id' else '20261009')
            with self.assertRaises((ValueError,OSError)):self.api.read_hk_stage_observed(self.recorded,bad)
        receipt=self.recorded/'imports'/ref['import_sha256']/'receipt.json';receipt.write_bytes(receipt.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.api.read_hk_stage_observed(self.recorded,ref)

    def test_original_empty_and_cannot_confirm_remain_distinct(self):
        for index in (8,9):
            result=self.imported(index)
            self.assertEqual(result['artifact']['selection_status'],self.fixtures[index]['artifact']['selection_status'])
            self.assertEqual(result['artifact']['cannot_confirm'],self.fixtures[index]['artifact']['cannot_confirm'])

    def test_http_cold_reads_observations_without_any_source_or_producer(self):
        config=self.config();published=[];generation=None
        for index in (0,1,7):
            result=self.imported(index);ref=result['reference']
            generation=self.publisher.publish_hk_stage_observed_response(config,self.recorded,ref,expected_generation=generation)['generation_sha256']
            query=dict(date=ref['target_date'],stage=ref['stage_id'],run_id=ref['run_id'],import_sha256=ref['import_sha256'])
            checked,fd=_config(config)
            try:record,_=read_response(checked,fd,ROUTE,query)
            finally:os.close(fd)
            self.assertEqual(record['data_kind'],'OWNER_RESULT')
            self.assertEqual(record['generated_at'],result['provenance']['imported_at'])
            payload=record['payload'];self.assertNotIn('/Users/',json.dumps(payload))
            self.assertEqual(payload['artifact']['rows'],result['artifact']['rows'])
            self.assertEqual(payload['reference'],ref)
            self.assertEqual(payload['m10_stage_member'],index!=7)
            self.assertEqual(payload['provenance']['qualification'],'OBSERVED_ONLY')
            published.append((query,payload))
        self.source.rename(self.base/'source-offline');self.recorded.rename(self.base/'recorded-offline')
        before=self.files(Path(config['data_root']))
        server=create_module_server(config);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base='http://127.0.0.1:'+str(server.server_address[1])
            for query,payload in published+list(reversed(published)):
                with urlopen(base+ROUTE+'?'+urlencode(query),timeout=3) as response:
                    self.assertEqual(json.load(response),payload)
            with self.assertRaises(HTTPError) as missing:
                urlopen(base+ROUTE+'?date=20261008',timeout=3)
            missing.exception.close();self.assertEqual(missing.exception.code,503)
        finally:server.shutdown();server.server_close();thread.join(timeout=5)
        self.assertEqual(self.files(Path(config['data_root'])),before)
        script="""
import json,os,sys
from v5_shadow.module_api import _config,read_response
v=json.loads(sys.stdin.read());c,fd=_config(v['config'])
try: r,_=read_response(c,fd,v['route'],v['query'])
finally:os.close(fd)
assert 'v5_shadow.hk_stage_daily' not in sys.modules
assert 'v5_shadow.hk_stage_observed' not in sys.modules
print(r['data_kind'])
"""
        proc=subprocess.run([sys.executable,'-B','-c',script],input=json.dumps(dict(config=config,route=ROUTE,query=published[0][0])),text=True,capture_output=True,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr);self.assertEqual(proc.stdout.strip(),'OWNER_RESULT')

    def test_cli_reference_and_config_reject_symlinks_and_nonregular_files(self):
        result=self.imported();reference_file=self.base/'reference.json'
        reference_file.write_bytes(canonical_bytes(result['reference']))
        config=self.config();config_file=self.base/'config.json';config_file.write_bytes(canonical_bytes(config))
        reference_link=self.base/'reference-link.json';reference_link.symlink_to(reference_file)
        config_link=self.base/'config-link.json';config_link.symlink_to(config_file)
        inventory_file=self.base/'inventory.json';inventory_file.write_bytes(canonical_bytes(dict(date='20261008',stage_runs=[self.inventory()])))
        inventory_link=self.base/'inventory-link.json';inventory_link.symlink_to(inventory_file)
        commands=[['v5_shadow.hk_stage_observed','prepare','--source-root',str(self.source),'--inventory',str(inventory_link),'--run-id',self.inventory()['run_id']],
                  ['v5_shadow.hk_stage_observed','read','--root',str(self.recorded),'--reference',str(reference_link)],
                  ['v5_shadow.hk_stage_observed_api','--config',str(config_link),'--root',str(self.recorded),
                   '--reference',str(reference_file),'--expected-generation','NONE']]
        fifo=self.base/'reference-fifo';os.mkfifo(fifo)
        commands.append(['v5_shadow.hk_stage_observed','read','--root',str(self.recorded),'--reference',str(fifo)])
        for command in commands:
            with self.subTest(command=command):
                proc=subprocess.run([sys.executable,'-B','-m',*command],capture_output=True,text=True,timeout=5)
                self.assertNotEqual(proc.returncode,0,proc.stdout)

    def test_observation_metadata_requires_literal_false(self):
        result=self.imported();ref=result['reference']
        path=self.recorded/'imports'/ref['import_sha256']/'receipt.json'
        receipt=json.loads(path.read_bytes());receipt['natural_verified']=0
        raw=canonical_bytes(receipt);path.write_bytes(raw)
        import hashlib
        changed=dict(ref,import_receipt_sha256=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):self.api.read_hk_stage_observed(self.recorded,changed)

    def test_cli_prepare_import_read_and_publish_without_payload_stdout(self):
        root=self.base/'cli-recorded'
        def command(module,*arguments):
            proc=subprocess.run([sys.executable,'-B','-m',module,*map(str,arguments)],
                                text=True,capture_output=True,timeout=15)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            return json.loads(proc.stdout)
        module='v5_shadow.hk_stage_observed'
        command(module,'init','--root',root)
        inventory=self.base/'inventory.json'
        inventory.write_bytes(canonical_bytes(dict(date='20261008',stage_runs=[self.inventory(1)])))
        expected=command(module,'prepare','--source-root',self.source,'--inventory',inventory,
                         '--run-id',self.inventory(1)['run_id'])
        expected_file=self.base/'expected.json';expected_file.write_bytes(canonical_bytes(expected))
        reference=command(module,'import','--source-root',self.source,'--root',root,'--reference',expected_file)
        reference_file=self.base/'cli-reference.json';reference_file.write_bytes(canonical_bytes(reference))
        self.source.rename(self.base/'original-offline')
        summary=command(module,'read','--root',root,'--reference',reference_file)
        self.assertNotIn('artifact',summary);self.assertNotIn('/Users/',json.dumps(summary))
        self.assertEqual(summary['reference'],reference);self.assertEqual(summary['rows'],10)
        self.assertEqual(summary['selection_status'],'PARTIAL_WITH_ROWS')
        self.assertEqual(summary['qualification'],'OBSERVED_ONLY')
        config=self.config();config_file=self.base/'api.json';config_file.write_bytes(canonical_bytes(config))
        published=command('v5_shadow.hk_stage_observed_api','--config',config_file,'--root',root,
                          '--reference',reference_file,'--expected-generation','NONE')
        self.assertRegex(published['generation_sha256'],r'^[0-9a-f]{64}$')

    def test_failed_publication_keeps_existing_generation(self):
        config=self.config();first=self.imported();ref=first['reference']
        result=self.publisher.publish_hk_stage_observed_response(config,self.recorded,ref,expected_generation=None)
        active=Path(config['data_root'])/'active.json';before=active.read_bytes()
        with self.assertRaisesRegex(ValueError,'GENERATION_CONFLICT'):
            self.publisher.publish_hk_stage_observed_response(config,self.recorded,ref,expected_generation=None)
        self.assertEqual(active.read_bytes(),before)
        receipt=self.recorded/'imports'/ref['import_sha256']/'receipt.json';receipt.write_text('{}')
        with self.assertRaises(ValueError):
            self.publisher.publish_hk_stage_observed_response(config,self.recorded,ref,expected_generation=result['generation_sha256'])
        self.assertEqual(active.read_bytes(),before)


if __name__=='__main__':unittest.main()
