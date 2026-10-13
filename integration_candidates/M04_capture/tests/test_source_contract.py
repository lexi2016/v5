import importlib.util,json,subprocess,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
import test_capture as fixture

class SourceContractTests(unittest.TestCase):
 def setUp(self):
  self.case=fixture.CaptureTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
 def collect(self,payload):
  now=datetime.now(timezone.utc)
  def runner(*args,**kwargs):return subprocess.CompletedProcess(args[0],0,json.dumps(payload),'')
  return self.case.m._producer().collect_paginated_topics(cli=self.case.cli,groups=[('123','synthetic')],as_of=now,since=now-timedelta(days=4),process_runner=runner)
 def test_known_empty_envelopes_remain_empty(self):
  for key in ('topics','topics_brief'):
   with self.subTest(key=key):self.assertEqual(self.collect({key:[],'has_more':False})['topics'],[])
 def test_known_nonempty_envelopes_preserve_body(self):
  row={'topic_id':'12345678901234567','create_time':self.case.published,'content':self.case.body}
  for key in ('topics','topics_brief'):
   with self.subTest(key=key):self.assertEqual(self.collect({key:[row],'has_more':False})['topics'][0]['content'],self.case.body)
 def test_unknown_and_malformed_envelopes_fail_closed(self):
  for payload in ({},{'resp_data':{'topics':[]}},[],{'topics':None},{'topics':{}},{'topics_brief':False,'topics':[]},{'topics':[],'has_more':'false'}):
   with self.subTest(payload=payload):
    with self.assertRaisesRegex(RuntimeError,'ZSXQ_CLI_(ENVELOPE|ROWS|HAS_MORE)_INVALID'):self.collect(payload)
 def test_unknown_cli_cannot_commit_success_or_archive(self):
  c=self.case
  fixture.write_synthetic_cli(c.cli,'print(\'{"resp_data":{"topics":[]}}\')\n');c.config['cli']['sha256']=c.sha(c.cli)
  with self.assertRaisesRegex(RuntimeError,'ZSXQ_CLI_ENVELOPE_INVALID'):c.run_capture()
  self.assertFalse((c.runtime/'captures/case1/result.json').exists())
  self.assertEqual(list((c.runtime/'captures/case1/source').rglob('*status*.json')),[])
  with self.assertRaisesRegex(ValueError,'CAPTURE_INCOMPLETE'):c.m.resume(c.config,'case1')
 @unittest.skipUnless(importlib.util.find_spec('pyarrow'),'NOT_RUN: existing pyarrow required; never install from this test')
 def test_healthy_parquet_original_analyzer_owner_and_cold_reader(self):
  import pyarrow as pa
  import pyarrow.parquet as pq
  c=self.case
  # Fixed synthetic historical date deliberately differs from capture day.
  codes=[f'{i:06d}.SZ' for i in range(1,1002)]
  names=['合成科技']+[f'合成公司{i:04d}' for i in range(2,1002)]
  pq.write_table(pa.table({'trade_date':['20200102']*1001,'ts_code':codes,'name':names}),c.panel)
  c.config['selector_panel']['sha256']=c.sha(c.panel)
  result=c.run_capture();self.assertEqual(result['status'],'SUCCEEDED')
  summaries=list((c.runtime/'captures/case1/source').rglob('zsxq_summary.json'));self.assertEqual(len(summaries),1)
  summary=json.loads(summaries[0].read_bytes());health=summary['stock_lookup_health']
  self.assertTrue(health['ok'],health);self.assertEqual(health['master_count'],1001);self.assertEqual(health['selector_date'],'20200102')
  product=c.m.materials(result['archive_binding']);article=product['articles'][0]
  self.assertEqual(article['body_text'],c.body);self.assertEqual(article['published_at'],c.published)
  self.assertEqual(article['acquisition_status'],'RECORDED');self.assertTrue(article['retrieved_at']);self.assertTrue(article['available_at'])
  self.assertFalse(product['historical_pit_claimed'])
  p=subprocess.run([fixture.sys.executable,'-I','-B',str(fixture.ROOT/'launch.py'),'read'],input=json.dumps(result['archive_binding']).encode(),capture_output=True)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(json.loads(p.stdout)['articles'],product['articles'])
