import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get('M14_ORIGINAL_RUNTIME','/workspace/shared/manager-daily-publication-20261013/V5'))
RUNTIME = Path(os.environ.get('M14_WINDOW_RUNTIME', str(ROOT/'candidate')))
RUNTIME_SRC = RUNTIME/'src' if (RUNTIME/'src').is_dir() else RUNTIME
sys.path.insert(0, str(BASE/'src'))
import v5_shadow
v5_shadow.__path__.insert(0, str(RUNTIME_SRC/'v5_shadow'))

def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def sha(x): return hashlib.sha256(x).hexdigest()

def fixture():
    signal='20261013'
    dates=sorted((datetime(2026,10,13)-timedelta(days=i)).strftime('%Y%m%d') for i in range(1,61))
    sessions=dict(prior60=dates, previous5=dates[-5:], calendar_sha256='b'*64)
    rows=[dict(datetime=datetime.strptime(d,'%Y%m%d').strftime('%Y-%m-%d 15:00'),open=8,high=10,low=7,close=8,trade=100,amount=700) for d in dates+[signal]]
    rows[-1]['trade']=150
    request=dict(category=4,market=71,code='00001',start=0,count=120)
    record=dict(code='HK.00001',status='RESPONSE_CAPTURED',error_code=None,
        source_sha256='fa7dcbce4ee026b0a02c47220820d0407af183553d3304afcc5db425dce33cbd',
        endpoint='119.97.142.130:7721',request=request,request_sha256=sha(canonical(request)),
        source_rows=rows,response_sha256=sha(canonical(rows)),returned_count=len(rows),
        request_started_at='2026-10-13T09:00:00+00:00',response_acquired_at='2026-10-13T09:00:01+00:00',request_finished_at='2026-10-13T09:00:02+00:00')
    return signal,sessions,record

def rehash(record):
    record['response_sha256']=sha(canonical(record['source_rows']))
    record['returned_count']=len(record['source_rows'])

class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert (RUNTIME_SRC/'v5_shadow/rebound_pytdx_window.py').exists(), 'new independent same-source adapter is missing'
        cls.m=importlib.import_module('v5_shadow.rebound_pytdx_window')
    def setUp(self):
        self.signal,self.sessions,self.record=fixture()
        self.kw=dict(members=['HK.00001','HK.00002'], signal_date=self.signal,sessions=self.sessions,
            research_cutoff='2026-10-13T10:00:00+00:00',now=datetime(2026,10,13,11,tzinfo=timezone.utc))
    def decode(self,records=None): return self.m.decode_window([self.record] if records is None else records,**self.kw)
    def test_original_decoder_is_used_and_sdk_trade_is_not_scaled(self):
        result=self.decode(); current=[r for r in result['rows'] if r['code_norm']=='HK.00001' and r['trade_date_compact']==self.signal][0]
        self.assertEqual(current['trade'],150.0); self.assertEqual(current['pre_close'],8.0)
        self.assertEqual(result['source_contract']['scale_applied'],1)
        self.assertIsNone(result['source_contract']['volume_unit'])
        self.assertEqual(len(result['rows']),62)
    def test_missing_member_has_null_signal_row_not_exclusion_or_zero(self):
        result=self.decode(); row=[r for r in result['rows'] if r['code_norm']=='HK.00002'][0]
        self.assertEqual(row['trade_date_compact'],self.signal)
        self.assertTrue(all(row[k] is None for k in ['open','high','low','close','trade','amount','pre_close']))
        self.assertIn('RECORD_MISSING',result['pending_reasons']['HK.00002'])
    def test_missing_history_never_filled_from_old_panel(self):
        self.record['source_rows'].pop(0); rehash(self.record)
        result=self.decode()
        current=[r for r in result['rows'] if r['code_norm']=='HK.00001' and r['trade_date_compact']==self.signal][0]
        self.assertIsNone(current['trade']); self.assertIsNone(current['close'])
        self.assertIn('PRIOR60_KEYS_MISSING',result['pending_reasons']['HK.00001'])
    def test_invalid_number_quarantines_member_with_null_target(self):
        self.record['source_rows'][0]['high']=-1; rehash(self.record)
        result=self.decode(); self.assertEqual(len([r for r in result['rows'] if r['code_norm']=='HK.00001']),1)
        self.assertIn('SOURCE_ROW_INVALID',result['pending_reasons']['HK.00001'])
    def test_duplicate_date_quarantines_member(self):
        self.record['source_rows'].append(copy.deepcopy(self.record['source_rows'][0])); rehash(self.record)
        self.assertIn('DUPLICATE_SOURCE_DATE',self.decode()['pending_reasons']['HK.00001'])
    def test_after_signal_rows_quarantine_even_if_not_selected(self):
        self.record['source_rows'][0]['datetime']='2026-10-14 15:00'; rehash(self.record)
        self.assertIn('SOURCE_ROW_INVALID',self.decode()['pending_reasons']['HK.00001'])
    def test_response_tamper_fails_closed(self):
        self.record['source_rows'][0]['trade']=777
        with self.assertRaisesRegex(ValueError,'RESPONSE_SHA'): self.decode()
    def test_request_interface_or_source_changes_fail_closed(self):
        for field,value in [('endpoint','other'),('source_sha256','a'*64)]:
            with self.subTest(field=field):
                r=copy.deepcopy(self.record);r[field]=value
                with self.assertRaisesRegex(ValueError,'SOURCE_IDENTITY'): self.decode([r])
        self.record['request']['market']=70; self.record['request_sha256']=sha(canonical(self.record['request']))
        with self.assertRaisesRegex(ValueError,'REQUEST'): self.decode()
    def test_cutoff_is_actual_capture_time_not_bar_date(self):
        self.kw['research_cutoff']='2026-10-13T09:00:01+00:00'
        with self.assertRaisesRegex(ValueError,'CUTOFF'): self.decode()
    def test_count_bound_and_unrequested_record_rejected(self):
        self.record['request']['count']=121;self.record['request_sha256']=sha(canonical(self.record['request']))
        with self.assertRaisesRegex(ValueError,'REQUEST_BOUND'): self.decode()
        _,_,r=fixture();r['code']='HK.00003';r['request']['code']='00003';r['request_sha256']=sha(canonical(r['request']))
        with self.assertRaisesRegex(ValueError,'UNREQUESTED'): self.decode([r])
    def test_failed_receipt_preserved_as_pending(self):
        self.record.update(status='QUERY_FAILED',error_code='HISTORY_CAPTURE_QUERY_FAILED',source_rows=None,response_sha256=None,returned_count=None,response_acquired_at=None)
        result=self.decode(); self.assertIn('QUERY_FAILED',result['pending_reasons']['HK.00001'])
    def test_duplicate_receipt_and_member_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_RECORD'): self.decode([self.record,self.record])
        self.kw['members']=['HK.00001','HK.00001']
        with self.assertRaisesRegex(ValueError,'MEMBERS'): self.decode()
    def test_shards_preserve_canonical_record_hash_and_missing_shard_fails(self):
        packed=self.m.pack_records([self.record],max_shard_bytes=1024*1024)
        self.assertEqual(len(packed),1)
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            root=Path(d); references=[]
            for i,blob in enumerate(packed):
                name=f'records-{i:03d}.json';(root/name).write_bytes(blob)
                references.append(dict(relative=name,sha256=sha(blob),bytes=len(blob)))
            self.assertEqual(self.m.read_records(root,references),[self.record])
            (root/references[0]['relative']).unlink()
            with self.assertRaises((ValueError,OSError)): self.m.read_records(root,references)
    def test_shard_tamper_and_bound_rejected(self):
        with self.assertRaisesRegex(ValueError,'SHARD'): self.m.pack_records([self.record],max_shard_bytes=10)
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            root=Path(d);(root/'records-000.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'SHA'): self.m.read_records(root,[dict(relative='records-000.json',sha256='a'*64,bytes=2)])

if __name__=='__main__': unittest.main()
