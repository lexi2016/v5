"""Extracted bundle and clean-root HTTP smoke; SYNTHETIC engineering evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tarfile
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from v5_shadow import m18_offline_v2 as m
from v5_shadow.digests import canonical_bytes
from v5_shadow.m18_v2_publication_bridge import descriptor_from_bundle, publish_m18_descriptor, ROUTE
from test_m18_v2_disk_pages import RUN
import test_m18_v2_announcement_projection as announcement
import test_m18_v2_rebound_projection as rebound
import test_m18_v2_us_mapping_projection as us

BASE=Path(__file__).resolve().parents[1]


def install_synthetic(root):
    references=[dict(stock_code='SYNTHETIC_ANN',research_status='CONDITIONAL_WATCH',orders_sent=False,article_refs=[])]
    groups={key:[] for key in rebound.GROUPS};groups['near']=[dict(code='SYNTHETIC_REBOUND',production_allowed=False)]
    matches=[dict(us_symbol='SYNTHETIC_US',hk_symbol='SYNTHETIC_HK',reason='fixture only',official_sources=[])]
    raw,_,_=announcement.fixture(references);payload=json.loads(raw)['payload'];payload.pop('plan_product')
    payload[rebound.SECTION]=json.loads(rebound.fixture(groups)[0])['payload'][rebound.SECTION]
    us_payload=json.loads(us.fixture(matches)[0])['payload']
    payload[us.SECTION]=us_payload[us.SECTION];payload['owner_chain']=us_payload['owner_chain']
    saved=dict(run_id=RUN,target_trade_date=payload['target_trade_date'],input_identity=payload['input_identity'],workspace=copy.deepcopy(payload))
    saved['sha256']=m.sha(canonical_bytes(saved));saved_raw=canonical_bytes(saved)
    payload['plan_product']=dict(consumed=True,run_id=RUN,sha256=saved['sha256'])
    raw=canonical_bytes(dict(payload=payload,readback=dict(run_id=RUN,plan_sha256=saved['sha256'],input_identity=payload['input_identity'])))
    identity=dict(run_id=RUN,target_date=payload['target_trade_date'],input_identity=payload['input_identity'],plan_sha256=saved['sha256'],raw_sha256=m.sha(saved_raw),response_sha256=m.sha(raw))
    bundle=m.build(raw,saved_raw,identity,expected_profile=m.PROFILE_SHA256)
    bundle_root=root/'data/bundle';(bundle_root/'objects').mkdir(parents=True)
    (bundle_root/'manifest.json').write_bytes(bundle.manifest)
    for name,value in bundle.objects.items():(bundle_root/'objects'/name).write_bytes(value)
    publication=root/'data/publication';publication.mkdir();(publication/'.v5-module-root').write_text('v5.module-root.v1:manager\n')
    config=dict(schema_version='v5.module_api.v1',module_id='manager',release_id='standalone-synthetic',data_root=str(publication),
        routes=[ROUTE,ROUTE+'/pages',ROUTE+'/overview',ROUTE+'/sections'],m18_v2_binding=dict(manifest_sha256=m.sha(bundle.manifest),identity=identity,profile_sha256=m.PROFILE_SHA256,bundle_root=str(bundle_root)))
    reader=m.Reader(bundle,m.sha(bundle.manifest),identity,expected_profile=m.PROFILE_SHA256)
    descriptor=descriptor_from_bundle(reader,identity,json.loads(bundle.manifest));descriptor['generated_at']='2026-10-12T00:00:00+00:00'
    publish_m18_descriptor(config,descriptor,expected_generation=None)
    config['data_root']='data/publication';config['m18_v2_binding']['bundle_root']='data/bundle'
    (root/'config/standalone.json').write_text(json.dumps(dict(schema_version='v5.standalone.v1',port=0,module_api=config)))
    return descriptor, references, groups, matches


def snapshot(root):
    return {str(p.relative_to(root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


class ExtractedPreviewTests(unittest.TestCase):
    def test_archive_serves_three_saved_views_without_external_source_or_writes(self):
        with tempfile.TemporaryDirectory() as td:
            clean=Path(td).resolve();archive=clean/'bundle.tar'
            build=subprocess.run([sys.executable,'-I','-B',str(BASE/'tools/build_standalone.py'),'--output',str(archive)],capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            with tarfile.open(archive) as source:source.extractall(clean/'install',filter='data')
            entry=clean/'install/V5/run_standalone.py';root=clean/'runtime-root'
            env=dict(os.environ,PYTHONPATH=str(clean/'NO_V4_OR_EXTERNAL_SOURCE'),PYTHONDONTWRITEBYTECODE='1')
            init=subprocess.run([sys.executable,'-I','-B',str(entry),'init','--root',str(root)],cwd=clean,env=env,capture_output=True,text=True)
            self.assertEqual(init.returncode,0,init.stderr)
            descriptor,refs,groups,matches=install_synthetic(root)
            outside=clean/'outside-sentinel';outside.write_text('untouched')
            before_code=snapshot(clean/'install');before_out=outside.read_bytes()
            proc=subprocess.Popen([sys.executable,'-I','-B',str(entry),'serve','--root',str(root)],cwd=clean,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                selector=selectors.DefaultSelector();selector.register(proc.stdout,selectors.EVENT_READ)
                self.assertTrue(selector.select(15),'launcher readiness timeout')
                line=proc.stdout.readline();selector.close()
                if not line:
                    proc.wait(timeout=5);self.fail(proc.stderr.read())
                ready=json.loads(line);self.assertEqual(ready['status'],'READY_READ_ONLY')
                self.assertFalse(ready['daily_enabled']);url='http://127.0.0.1:'+str(ready['port'])
                def get(path,method='GET',headers=None):
                    try:response=urlopen(Request(url+path,method=method,headers=headers or {}),timeout=15)
                    except HTTPError as error:response=error
                    with response:return response.status,response.read()
                before=snapshot(root)
                status,html=get('/manager-selection/');self.assertEqual(status,200);self.assertIn(b'<html',html)
                for module,extra,expected in [(announcement,{},refs),(rebound,{'group':'near'},groups['near']),(us,{},matches)]:
                    query=dict(run_id=RUN,generation_id=descriptor['generation_id'],section=module.SECTION,projection=module.PROJECTION,**extra)
                    status,raw=get(ROUTE+'/sections?'+urlencode(query));self.assertEqual(status,200,raw)
                    data=json.loads(raw);self.assertEqual([row['value'] for row in data['entries']],expected)
                    self.assertLess(len(raw),256*1024)
                status,_=get(ROUTE+'/sections?run_id=wrong');self.assertEqual(status,409)
                status,_=get(ROUTE,method='POST');self.assertEqual(status,405)
                status,_=get('/manager-selection/',headers={'Origin':'https://example.com'});self.assertEqual(status,403)
                self.assertEqual(snapshot(root),before)
                self.assertEqual(snapshot(clean/'install'),before_code)
                self.assertEqual(outside.read_bytes(),before_out)
            finally:
                proc.send_signal(signal.SIGHUP);proc.wait(timeout=10)
                proc.stdout.close();proc.stderr.close()
            self.assertFalse((root/'runtime/runtime.json').exists())

if __name__=='__main__':unittest.main()
