"""Synthetic v2 budget/identity regressions; no real input or services."""
import base64
import copy
import importlib.util
import json
import unittest
from test_m18_offline_pages import fixture,canon,digest
if importlib.util.find_spec('v5_shadow.m18_offline_v2'):
 from v5_shadow import m18_offline_v2 as m
else:m=None

class V2Tests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(m,'M18_V2_IMPLEMENTATION_MISSING')
  self.raw,self.saved,self.identity=fixture()
 def build(self,raw=None,saved=None,identity=None):
  return m.build(raw or self.raw,saved or self.saved,identity or self.identity,expected_profile=m.PROFILE_SHA256)
 def reader(self,bundle,identity=None):return m.Reader(bundle,digest(bundle.manifest),identity or self.identity,expected_profile=m.PROFILE_SHA256)
 def test_full_bytes_gaps_and_expected_requests(self):
  b=self.build();r=self.reader(b);self.assertEqual(r.full_response(),self.raw)
  cursor=None;offset=0
  while True:
   page=r.detail('gaps',cursor=cursor);r.verify_page(page,expected_section='gaps',expected_selection=None,expected_cursor=cursor,expected_offset=offset)
   offset+=len(page['entries']);cursor=page['next_cursor']
   if cursor is None:break
  self.assertEqual(offset,3250);self.assertEqual(r.overview()['sections']['gaps']['not_loaded_count'],3250)
  with self.assertRaises(m.ContractError):r.verify_page(r.detail('materials'),expected_section='gaps',expected_selection=None,expected_cursor=None,expected_offset=0)
 def test_profile_pin_required_and_no_self_increase(self):
  with self.assertRaises(TypeError):m.build(self.raw,self.saved,self.identity)
  with self.assertRaises(m.ContractError):m.build(self.raw,self.saved,self.identity,expected_profile='f'*64)
  b=self.build();v=json.loads(b.manifest);v['profile']['response_nodes']+=1;raw=canon(v)
  with self.assertRaises(m.ContractError):m.Reader(m.Bundle(raw,b.objects),digest(raw),self.identity,expected_profile=m.PROFILE_SHA256)
 def test_original_profile_cannot_mutate(self):
  with self.assertRaises(TypeError):m.PROFILE['response_nodes']=9000000
 def test_local_nodes_exact_and_over(self):
  for count,okay in [(199999,True),(200000,False)]:
   raw=b'['+b','.join([b'0']*count)+b']'
   with self.subTest(count=count):
    if okay:self.assertEqual(m.scan(raw,'object').nodes,200000)
    else:
     with self.assertRaisesRegex(m.ContractError,'OBJECT_NODES'):m.scan(raw,'object')
 def test_response_saved_node_exact_and_over(self):
  raw=b'['+b'0,'*1499998+b'0]'
  for scope in ['response','saved']:
   with self.subTest(scope=scope):
    self.assertEqual(m.scan(raw,scope).nodes,1500000)
    with self.assertRaises(m.ContractError):m.scan(raw[:-1]+b',0]',scope)
 def test_all_aggregate_node_boundaries(self):
  for method,limit in [('input_nodes',3000000),('metadata_nodes',500000),('logical_nodes',2000000)]:
   with self.subTest(method=method):
    ledger=m.Ledger();getattr(ledger,method)(limit);self.assertEqual(ledger.counts[method],limit)
    with self.assertRaises(m.ContractError):getattr(ledger,method)(1)
 def test_generation_bytes_and_record_boundaries(self):
  ledger=m.Ledger();ledger.stored_bytes(64*1024*1024-1)
  with self.assertRaises(m.ContractError):ledger.stored_bytes(1)
  ledger=m.Ledger();ledger.records(10000)
  with self.assertRaises(m.ContractError):ledger.records(1)
 def test_object_byte_boundary_before_parse(self):
  raw=b'"'+b'x'*(16*1024*1024-2)+b'"'
  with self.assertRaisesRegex(m.ContractError,'OBJECT_BYTES'):m.scan(raw,'object')
  self.assertEqual(m.scan(raw[:-2]+b'"','object').nodes,1)
 def test_single_string_32m_boundary_and_escape_bytes(self):
  size=32*1024*1024
  self.assertEqual(m.scan(b'"'+b'x'*(size-2)+b'"','response').nodes,1)
  for raw in [b'"'+b'x'*(size-1)+b'"',b'"'+b'\\u0000'*(size//6+1)+b'"']:
   with self.subTest(bytes=len(raw)),self.assertRaisesRegex(m.ContractError,'STRING_TOKEN'):m.scan(raw,'response')
 def test_depth_and_index_boundaries(self):
  m.scan(b'['*64+b'0'+b']'*64,'response')
  with self.assertRaisesRegex(m.ContractError,'DEPTH'):m.scan(b'['*65+b'0'+b']'*65,'response')
  for n in [10000,10001]:
   raw=b'{"payload":{"rows":['+b','.join([b'0']*n)+b']}}'
   with self.subTest(n=n):
    if n==10000:self.assertEqual(m.scan(raw,'response').entries,n)
    else:
     with self.assertRaisesRegex(m.ContractError,'ENTRY'):m.scan(raw,'response')
 def test_stdlib_semantics_canonical_escaping_and_duplicates(self):
  for value in [{'x':'汉😀\\\"\n'*4000},[1,1.2,None,False]]:
   with self.subTest(kind=type(value).__name__):self.assertEqual(m.parse(canon(value),'response')[0],value)
  for raw in [b'{"x":1,"x":2}',b'[NaN]',b'{"x":"\\ud800"}',b' [1]']:
   with self.subTest(raw=raw[:20]),self.assertRaises(m.ContractError):m.parse(raw,'response')
 def test_index_pages_and_tampered_page_rejected(self):
  b=self.build();v=json.loads(b.manifest);self.assertGreater(len(v['index_pages']),1)
  desc=v['index_pages'][0];objects=dict(b.objects);val=json.loads(objects[desc['object_sha256']]);val['entries'][0]['entry']['sha256']='0'*64
  changed=canon(val);objects[digest(changed)]=changed;del objects[desc['object_sha256']];desc['object_sha256']=digest(changed);raw=canon(v)
  with self.assertRaises(m.ContractError):self.reader(m.Bundle(raw,objects))
 def test_content_expected_index_and_cross_generation(self):
  raw,saved,identity=fixture(extra={'body':'x'*300000});b=self.build(raw,saved,identity);r=self.reader(b,identity)
  for i in range(r.overview()['content_chunks']):self.assertTrue(r.verify_content(r.content(i),expected_index=i))
  with self.assertRaises(m.ContractError):r.verify_content(r.content(1),expected_index=0)
  other=self.reader(self.build())
  with self.assertRaises(m.ContractError):other.verify_content(r.content(0),expected_index=0)
 def test_counts_cannot_be_self_declared(self):
  b=self.build();v=json.loads(b.manifest);v['response_nodes']=1;raw=canon(v)
  with self.assertRaises(m.ContractError):self.reader(m.Bundle(raw,b.objects))
 def test_resource_measurement_boundaries(self):
  for key,limit in [('peak_rss_bytes',512*1024*1024),('cpu_seconds',60),('wall_seconds',90)]:
   with self.subTest(metric=key):
    good=dict(peak_rss_bytes=1,cpu_seconds=0,wall_seconds=0);good[key]=limit;m.enforce_usage(good)
    good[key]=limit+1
    with self.assertRaises(m.ContractError):m.enforce_usage(good)
 def test_v1_manifest_rejected(self):
  from v5_shadow import m18_offline_pages as v1
  old=v1.build(self.raw,self.saved,self.identity)
  with self.assertRaises(m.ContractError):m.Reader(old,digest(old.manifest),self.identity,expected_profile=m.PROFILE_SHA256)
