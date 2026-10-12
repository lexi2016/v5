"""Historical fixture inputs; real frozen producer/store/cold reader, no network."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v5_shadow import a_close_daily as daily
from v5_shadow import a_close_daily_sources as sources
historical = __import__('v5_shadow.a_close_historical',fromlist=['*']) if importlib.util.find_spec('v5_shadow.a_close_historical') else None
from v5_shadow.a_close_daily_api import read_a_close_preview
from v5_shadow.digests import canonical_bytes,sha256_json
from test_a_close_daily import make_input,file_sha,tree_bytes


class HistoricalResearchTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(historical,'Explicit historical research entry is missing')
        self.tmp=tempfile.TemporaryDirectory(prefix='m09-historical-');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve();self.source=self.base/'snapshot';self.root=self.base/'research'
        temp=self.base/'fixture';make_input(temp)
        self.rows=json.loads((temp/'panel.json').read_bytes())
        self.rows[0]['name']='';self.rows[1]['tdx_industry_name']='';self.rows[1]['tdx_industry_code']=''
        self.rows[2]['bar_close_pos']=float('nan')
        origin={'sha256':file_sha(temp/'panel.json'),'bytes':(temp/'panel.json').stat().st_size,
                'format':'SYNTHETIC_FIXTURE_ONLY','hash_verified':True}
        historical._write_snapshot(self.source,'20261009',self.rows,origin,None)
        historical.initialize_a_close_historical_root(self.root)

    def run_history(self,attempt='first',**kw):
        return historical.run_a_close_historical(self.root,self.source,'20261009',attempt_id=attempt,**kw)

    def test_unmodified_gaps_run_original_owner_and_cold_read(self):
        before=tree_bytes(self.source);result=self.run_history();self.assertEqual(result['status'],'SUCCEEDED',result)
        out=daily.read_a_close_daily(self.root,'20261009');r=out['record']
        self.assertEqual(r['data_kind'],'RECORDED_INPUT_REPLAY');self.assertEqual(r['execution_kind'],'HISTORICAL_REPLAY')
        self.assertEqual(r['scope'],'OBSERVED_ROWS_ONLY');self.assertFalse(r['strict_1500_pit_verified'])
        self.assertFalse(r['natural_verified']);self.assertFalse(r['historical_research']['source_time_verified'])
        self.assertFalse(r['historical_research']['membership_qualification_verified'])
        self.assertEqual(r['historical_research']['missing_text']['name'],1)
        self.assertEqual(r['historical_research']['nonfinite_unused_close_position'],1)
        self.assertEqual(sum(out['review']['model_review']['market_summary'][k] for k in ('up_count','down_count','flat_count')),6)
        preview=read_a_close_preview(self.root,'20261009')
        self.assertEqual(preview['m09_publication']['read_status'],'VERIFIED')
        self.assertEqual(preview['m09_publication']['historical_research'],r['historical_research'])
        self.assertEqual(tree_bytes(self.source),before)
        code="import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from v5_shadow.a_close_daily import read_a_close_daily;assert read_a_close_daily(Path(sys.argv[2]),'20261009')['record']['execution_kind']=='HISTORICAL_REPLAY'"
        p=subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(daily.__file__).resolve().parents[1]),str(self.root)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)

    def test_nan_null_infinity_and_string_have_distinct_frame_identity(self):
        import pandas as pd
        hashes=[]
        for v in (None,float('nan'),float('inf'),float('-inf'),'nan',0.0,-0.0):
            frame=pd.DataFrame({'x':pd.Series([v],dtype=object)})
            hashes.append(sources._frame_digest(frame))
        self.assertEqual(len(set(hashes)),len(hashes))
        encoded=sources.encode_rows([{'value':float('nan'),'string':'NaN','none':None}])
        raw=canonical_bytes(encoded);decoded=sources.decode_rows(json.loads(raw))
        self.assertTrue(math.isnan(decoded[0]['value']));self.assertEqual(decoded[0]['string'],'NaN');self.assertIsNone(decoded[0]['none'])

    def test_strict_frame_validation_and_pit_are_unchanged(self):
        import pandas as pd
        with self.assertRaisesRegex(ValueError,'FRAME_TEXT'):sources._validate_frame(pd.DataFrame(self.rows,columns=list(sources.COLUMNS)),'20261009')
        issues=[];daily._time_pair({'captured_at':None,'available_at':None},'20261009',daily._date_slot('20261009','16:05'),'SOURCE',issues)
        self.assertTrue(issues)

    def test_replay_cannot_run_as_real_manual_or_natural(self):
        for kind in ('ENGINEERING','MANUAL_RECOVERY','NATURAL'):
            req=historical._request_for(self.source,'20261009',kind,'16:05','replay-test')
            req['execution_kind']=kind
            with self.assertRaises(ValueError):daily.run_a_close_daily(self.root,req)
        self.assertEqual(list(self.root.glob('runs/*')),[])

    def test_replay_cannot_publish_in_existing_strict_root(self):
        strict=self.base/'strict';daily.initialize_a_close_root(strict);before=tree_bytes(strict)
        with self.assertRaises(ValueError):historical.initialize_a_close_historical_root(strict)
        req=historical._request_for(self.source,'20261009','wrong-root','16:05','replay-test')
        result=daily.run_a_close_daily(strict,req)
        self.assertEqual(result['status'],'FAILED',result);self.assertIsNone(daily.read_a_close_daily(strict,'20261009'))
        self.assertEqual(list(strict.glob('runs/*')),[])

    def test_invalid_core_numeric_duplicate_and_date_are_hard_rejected(self):
        cases=[lambda r:r[0].update(pct_chg=float('nan')),lambda r:r[0].update(amount=-1),
               lambda r:r[0].update(amount=True),lambda r:r[0].update(bar_close_pos=1.1),lambda r:r[0].update(trade_date='20261008'),
               lambda r:r[1].update(ts_code=r[0]['ts_code'])]
        for i,change in enumerate(cases):
            with self.subTest(i=i):
                rows=copy.deepcopy(self.rows);change(rows)
                with self.assertRaises(ValueError):historical._write_snapshot(self.base/('bad'+str(i)),'20261009',rows,{'sha256':'1'*64,'bytes':1,'format':'SYNTHETIC_FIXTURE_ONLY','hash_verified':True},None)

    def test_failed_later_attempt_and_tampering_preserve_old_success(self):
        first=self.run_history();self.assertEqual(first['status'],'SUCCEEDED',first)
        p=self.source/'panel.json';raw=p.read_bytes();p.write_bytes(raw+b' ')
        failed=self.run_history('changed');self.assertEqual(failed['status'],'FAILED',failed)
        out=daily.read_a_close_daily(self.root,'20261009');self.assertEqual(out['identity']['generation_sha256'],first['generation_sha256'])
        self.assertEqual(out['latest_attempt']['status'],'FAILED')

    def test_two_slots_are_historical_receipts_not_cutoff_proof(self):
        first=self.run_history(slot='16:05');second=self.run_history('second',slot='17:10')
        self.assertEqual(first['status'],'SUCCEEDED',first);self.assertEqual(second['status'],'SUCCEEDED',second)
        self.assertEqual(first['run_id'],second['run_id']);self.assertTrue(second['reused'])
        out=daily.read_a_close_daily(self.root,'20261009')
        self.assertFalse(out['record']['historical_research']['source_available_by_requested_slot'])
        self.assertGreater(daily.aware(first['started_at']),daily.aware(first['cutoff']))

    def test_original_model_parity_preserves_native_missing_values(self):
        import pandas as pd
        result=self.run_history();self.assertEqual(result['status'],'SUCCEEDED',result)
        out=daily.read_a_close_daily(self.root,'20261009')
        original=sources.load_frozen_module('domains.a_share_close_model')
        expected=original.build_close_model(pd.DataFrame(self.rows,columns=list(sources.COLUMNS)),'20261009',result['run_id'])
        self.assertEqual(out['review']['model_review'],expected)

    def test_large_opaque_receipt_is_hash_reference_never_ready_summary(self):
        from unittest.mock import patch
        import os
        receipt=self.base/'large-receipt.json'
        with receipt.open('wb') as handle:
            for _ in range(17):handle.write(b'x'*(1024*1024))
        expected=hashlib.sha256(b'x'*(17*1024*1024)).hexdigest()
        reads=[];original=os.read
        def bounded(fd,count):reads.append(count);return original(fd,count)
        with patch.object(os,'read',side_effect=bounded):meta=historical._hash_source(receipt,expected)
        self.assertTrue(reads);self.assertLessEqual(max(reads),1024*1024)
        reference=dict(sha256=meta['sha256'],bytes=meta['bytes'],hash_verified=True,
                       metadata_status='OPAQUE_ORIGINAL_RECEIPT_HASH_ONLY_NO_READY_CLAIM')
        prepared=self.base/'large-ref-input'
        historical._write_snapshot(prepared,'20261009',self.rows,{'sha256':'1'*64,'bytes':1,'format':'SYNTHETIC_FIXTURE_ONLY','hash_verified':True},reference)
        manifest=json.loads((prepared/'input.json').read_bytes())
        self.assertEqual(manifest['provenance']['status'],'UNKNOWN')
        self.assertIsNone(manifest['provenance']['available_at'])
        self.assertLess((prepared/'source_reference.json').stat().st_size,1024)
        result=historical.run_a_close_historical(self.root,prepared,'20261009',attempt_id='opaque')
        self.assertEqual(result['status'],'SUCCEEDED',result)
        out=daily.read_a_close_daily(self.root,'20261009')
        self.assertEqual(out['record']['historical_research']['original_receipt'],reference)
        self.assertEqual(daily.MAX_JSON_BYTES,16*1024*1024);self.assertEqual(daily.MAX_PANEL_BYTES,128*1024*1024)

    def test_resealed_ready_claim_is_rejected_without_publication(self):
        manifest=json.loads((self.source/'input.json').read_bytes())
        manifest['provenance']['status']='READY'
        (self.source/'input.json').write_bytes(canonical_bytes(manifest))
        result=self.run_history();self.assertEqual(result['status'],'FAILED',result)
        self.assertIn('PROVENANCE_PROMOTION',result['reason'])
        self.assertIsNone(daily.read_a_close_daily(self.root,'20261009'))

    def test_stream_hash_is_bounded_and_preserves_file(self):
        p=self.base/'opaque';p.write_bytes(b'x'*(2*1024*1024+3));before=p.read_bytes()
        meta=historical._hash_source(p,hashlib.sha256(before).hexdigest())
        self.assertEqual(meta['bytes'],len(before));self.assertEqual(p.read_bytes(),before)
        with self.assertRaises(ValueError):historical._hash_source(p,'0'*64)


@unittest.skipUnless(importlib.util.find_spec('pyarrow') is not None,'NOT_RUN: existing pyarrow absent; no installation')
class HistoricalParquetTests(unittest.TestCase):
    def test_multiday_parquet_stream_filter_keeps_exact_date_and_source_sha(self):
        import pyarrow as pa,pyarrow.parquet as pq
        with tempfile.TemporaryDirectory(prefix='m09-stream-') as t:
            base=Path(t).resolve();source=base/'source';make_input(source)
            rows=json.loads((source/'panel.json').read_bytes());rows[0]['bar_close_pos']=float('nan')
            previous=copy.deepcopy(rows)
            for row in previous:row['trade_date']='20261008'
            p=source/'panel.parquet';pq.write_table(pa.Table.from_pylist(previous+rows),p,row_group_size=3)
            pointer=source/'pointer.txt';pointer.write_text('panel.parquet\n')
            snapshot=base/'snapshot'
            manifest=historical.prepare_a_close_historical_snapshot(source,'pointer.txt',file_sha(pointer),file_sha(p),'20261009',snapshot)
            self.assertEqual(manifest['panel']['row_count'],6)
            bind=json.loads((snapshot/'source_binding.json').read_bytes())
            self.assertEqual(bind['source']['sha256'],file_sha(p));self.assertEqual(bind['source']['bytes'],p.stat().st_size)
            decoded=historical._read_snapshot_rows((snapshot/'panel.json').read_bytes(),'20261009')
            self.assertTrue(all(r['trade_date']=='20261009' for r in decoded));self.assertTrue(math.isnan(decoded[0]['bar_close_pos']))
            root=base/'run';historical.initialize_a_close_historical_root(root)
            result=historical.run_a_close_historical(root,snapshot,'20261009',attempt_id='stream-real')
            self.assertEqual(result['status'],'SUCCEEDED',result)


if __name__=='__main__':unittest.main()
