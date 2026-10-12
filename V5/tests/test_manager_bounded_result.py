"""Synthetic only: exercise actual frozen owner and local process boundary."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from test_manager_archive_reader import ArchiveWiringTests
from v5_shadow.manager_plan import run_manager_plan


class LargeManagerResultTests(ArchiveWiringTests):
    # Inherit only fixture helpers, not the old suite's test methods.
    def test_large_result_and_independent_cold_read_keep_complete_payload(self):
        self.payload['articles'] = []
        for i in range(12):
            article = copy.deepcopy(self.original_article)
            article['article_id'] = hashlib.sha256(('article'+str(i)).encode()).hexdigest()
            article['dedupe_key'] = hashlib.sha256(('dedupe'+str(i)).encode()).hexdigest()
            article['source_title'] = 'SYNTHETIC_NOT_REAL_' * 42000
            self.payload['articles'].append(article)
        self.payload['article_count']=12
        self.receipt['article_count']=12
        from v5_shadow.digests import sha256_json
        self.receipt['payload_sha256']=sha256_json(self.payload)
        self.put(self.relative,self.payload)
        self.put('receipts/'+self.relative,self.receipt)
        self.put('manifest.json',{self.relative:sha256_json(self.payload)})
        self.request['action']='refresh'
        try:
            result=run_manager_plan(self.request)
        except ValueError as error:
            self.fail('Complete synthetic result must cross local boundary: '+str(error))
        print(json.dumps({'synthetic_large_result':result['local_result_transport']},sort_keys=True))
        encoded=json.dumps(result,ensure_ascii=False,separators=(',',':')).encode()
        self.assertGreater(len(encoded),16*1024*1024)
        self.assertTrue(result['payload']['materials'])
        self.assertTrue(any('ARCHIVE_ARTICLE_ACQUISITION_TIME_MISSING' in g for g in result['payload']['gaps']))
        request=self.root/'cold.json';request.write_text(json.dumps(dict(self.request,action='read')))
        destination=self.root/'cold-result.json'
        code="""import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from v5_shadow.manager_plan import run_manager_plan;p=run_manager_plan(json.loads(Path(sys.argv[2]).read_bytes()));Path(sys.argv[3]).write_text(json.dumps(p))"""
        cold=subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(__file__).resolve().parents[1]/'src'),str(request),str(destination)],capture_output=True,timeout=120)
        self.assertEqual(cold.returncode,0,cold.stderr.decode())
        read=json.loads(destination.read_bytes())
        self.assertEqual(read['payload'],result['payload'])
        self.assertEqual(read['readback']['run_id'],result['readback']['run_id'])
        self.assertEqual(read['readback']['plan_sha256'],result['readback']['plan_sha256'])
        self.assertIn('workspace_plan_attempt',read['payload'])
        self.assertIn('coverage_diagnostics',read['payload']['us_mapping_research'])
        self.assertEqual(result['local_result_transport']['response_sha256'],hashlib.sha256(json.dumps({k:v for k,v in result.items() if k!='local_result_transport'},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())

    def setUp(self):
        super().setUp()
        self.original_article=copy.deepcopy(self.payload['articles'][0])

# Avoid inadvertently rerunning inherited old tests in this class.
for _name in list(ArchiveWiringTests.__dict__):
    if _name.startswith('test_'):
        setattr(LargeManagerResultTests,_name,None)
