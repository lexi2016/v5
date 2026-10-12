"""M18 owned pure offline contract tests. Every input is synthetic."""
import base64
import copy
import hashlib
import importlib.util
import json
import unittest
from unittest.mock import patch

SPEC=importlib.util.find_spec('v5_shadow.m18_offline_pages')
if SPEC:
 from v5_shadow import m18_offline_pages as m
else:m=None

def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(x):return hashlib.sha256(x).hexdigest()
def fixture(run='a'*32, extra=None):
 p=dict(target_trade_date='20261012',input_identity='b'*64,RESEARCH_ONLY=True,production_allowed=False,buy_gate_updated=False,orders_sent=False,
        materials=[{'i':i,'body':'SYNTHETIC','available_at':None} for i in range(70)],
        gaps=['ARCHIVE_ARTICLE_ACQUISITION_TIME_MISSING:'+str(i) for i in range(3075)]+['ARCHIVE_ARTICLE_STRUCTURED_THEME_MISSING:'+str(i) for i in range(175)],
        empty=[],unknown=None,formal_eligibility=False)
 if extra:p.update(extra)
 saved=dict(run_id=run,target_trade_date=p['target_trade_date'],input_identity=p['input_identity'],workspace=copy.deepcopy(p))
 saved['sha256']=digest(canon(saved));saved_raw=json.dumps(saved,ensure_ascii=False,indent=2).encode()
 p['plan_product']=dict(consumed=True,run_id=run,sha256=saved['sha256'])
 response=dict(payload=p,readback=dict(run_id=run,plan_sha256=saved['sha256'],input_identity=p['input_identity']),unknown_outer={'kept':True})
 raw=canon(response);identity=dict(run_id=run,target_date=p['target_trade_date'],plan_sha256=saved['sha256'],raw_sha256=digest(saved_raw),response_sha256=digest(raw),input_identity=p['input_identity'])
 return raw,saved_raw,identity

class OfflinePagesTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(m,'M18_OFFLINE_PAGES_IMPLEMENTATION_MISSING')
  self.raw,self.saved,self.identity=fixture();self.bundle=m.build(self.raw,self.saved,self.identity)
  self.reader=m.Reader(self.bundle,digest(self.bundle.manifest),self.identity)
 def test_full_response_all_fields_and_gaps_exact(self):
  self.assertEqual(self.reader.full_response(),self.raw)
  value=json.loads(self.reader.full_response());self.assertEqual(len(value['payload']['gaps']),3250)
  self.assertEqual(value['unknown_outer'],{'kept':True});self.assertFalse(value['payload']['formal_eligibility'])
 def test_overview_has_explicit_not_loaded_and_empty_vs_unknown(self):
  view=self.reader.overview();sections=view['sections']
  self.assertEqual(sections['gaps']['not_loaded_count'],3250);self.assertEqual(sections['gaps']['loaded_count'],0)
  self.assertEqual(sections['empty']['total'],0);self.assertEqual(sections['unknown']['total'],1)
  self.assertEqual(sections['materials']['state'],'NOT_LOADED');self.assertNotIn('absent',sections)
 def test_detail_pages_cover_all_items_in_original_order(self):
  cursor=None;items=[]
  while True:
   page=self.reader.detail('materials',cursor=cursor);self.reader.verify_page(page)
   items.extend(page['entries']);cursor=page['next_cursor']
   if cursor is None:break
  self.assertEqual([e['index'] for e in items],list(range(70)))
  entry=items[4];parts=list(self.reader.item_parts('materials',entry['index']))
  self.assertEqual(json.loads(b''.join(parts)),json.loads(self.raw)['payload']['materials'][4])
  self.assertEqual(digest(b''.join(parts)),entry['sha256'])
 def test_selection_and_cursor_binding(self):
  selection={'indices':list(range(40))};first=self.reader.detail('materials',selection=selection)
  second=self.reader.detail('materials',selection=selection,cursor=first['next_cursor']);self.assertEqual(second['entries'][0]['index'],32)
  for section,sel in [('gaps',selection),('materials',None),('materials',{'indices':[0,1]})]:
   with self.subTest(section=section,selection=sel),self.assertRaises(m.ContractError):self.reader.detail(section,selection=sel,cursor=first['next_cursor'])
 def test_wrong_page_fields_or_entry_are_rejected(self):
  page=self.reader.detail('materials')
  for key,val in [('offset',32),('matched_total',0),('not_loaded_count',0),('generation_id','f'*64),('unknown',True),('identity',dict(self.identity,run_id='f'*32))]:
   bad=copy.deepcopy(page);bad[key]=val
   with self.subTest(field=key),self.assertRaises(m.ContractError):self.reader.verify_page(bad)
  bad=copy.deepcopy(page);bad['entries'][0]['sha256']='f'*64
  with self.assertRaises(m.ContractError):self.reader.verify_page(bad)
 def test_cross_run_and_generation_page_cursor_rejected(self):
  raw,saved,identity=fixture(run='c'*32);other=m.build(raw,saved,identity);reader=m.Reader(other,digest(other.manifest),identity)
  for foreign in [reader.detail('materials')]:
   with self.assertRaises(m.ContractError):self.reader.verify_page(foreign)
   with self.assertRaises(m.ContractError):self.reader.detail('materials',cursor=foreign['next_cursor'])
 def test_wrong_identity_and_manifest_pin_rejected(self):
  for key in self.identity:
   bad=dict(self.identity);bad[key]='0'*len(bad[key])
   with self.subTest(key=key),self.assertRaises(m.ContractError):m.Reader(self.bundle,digest(self.bundle.manifest),bad)
  with self.assertRaises(m.ContractError):m.Reader(self.bundle,'0'*64,self.identity)
 def test_corrupt_missing_extra_chunk_rejected(self):
  for mode in ['corrupt','missing','extra']:
   objects=dict(self.bundle.objects);key=next(iter(objects))
   if mode=='corrupt':objects[key]=b'{}'
   elif mode=='missing':del objects[key]
   else:objects['f'*64]=b'{}'
   with self.subTest(mode=mode),self.assertRaises(m.ContractError):m.Reader(m.Bundle(self.bundle.manifest,objects),digest(self.bundle.manifest),self.identity)
 def test_reordered_manifest_chunks_rejected_even_resealed(self):
  source,saved,identity=fixture(extra={'body':'x'*m.CHUNK_BYTES})
  bundle=m.build(source,saved,identity);value=json.loads(bundle.manifest)
  self.assertGreater(len(value['chunks']),1)
  value['chunks']=list(reversed(value['chunks']));raw=canon(value)
  with self.assertRaises(m.ContractError):m.Reader(m.Bundle(raw,bundle.objects),digest(raw),identity)
 def test_huge_single_body_uses_bounded_parts(self):
  raw,saved,identity=fixture(extra={'giant_body':'SYNTHETIC_'*(1800000)})
  bundle=m.build(raw,saved,identity);reader=m.Reader(bundle,digest(bundle.manifest),identity)
  self.assertGreater(len(raw),16*1024*1024);self.assertTrue(all(len(v)<16*1024*1024 for v in bundle.objects.values()))
  page=reader.detail('giant_body');self.assertLess(len(canon(page)),4096);self.assertEqual(page['entries'][0]['value_state'],'NOT_LOADED')
  parts=list(reader.item_parts('giant_body',0));self.assertGreater(len(parts),1);self.assertTrue(all(len(p)<=m.CHUNK_BYTES for p in parts))
  self.assertEqual(reader.full_response(),raw)
 def test_saved_raw_semantic_and_response_hashes_not_interchangeable(self):
  for key in ['plan_sha256','raw_sha256','response_sha256']:
   bad=dict(self.identity);bad[key]='f'*64
   with self.subTest(key=key),self.assertRaises(m.ContractError):m.build(self.raw,self.saved,bad)
 def test_source_identity_mismatch_even_with_new_response_digest(self):
  for path in ['run','input','product','target']:
   value=json.loads(self.raw)
   if path=='run':value['readback']['run_id']='c'*32
   if path=='input':value['payload']['input_identity']='c'*64
   if path=='product':value['payload']['plan_product']['consumed']=False
   if path=='target':value['payload']['target_trade_date']='20261013'
   raw=canon(value);identity=dict(self.identity,response_sha256=digest(raw))
   with self.subTest(path=path),self.assertRaises(m.ContractError):m.build(raw,self.saved,identity)
 def test_unsafe_flags_rejected(self):
  value=json.loads(self.raw);value['payload']['orders_sent']=True;raw=canon(value)
  with self.assertRaises(m.ContractError):m.build(raw,self.saved,dict(self.identity,response_sha256=digest(raw)))
 def test_noncanonical_duplicate_key_and_depth_rejected(self):
  for raw in [b'{"payload":{},"payload":{}}',b' '+self.raw,b'['*65+b'0'+b']'*65]:
   with self.subTest(kind=raw[:12]),self.assertRaises(m.ContractError):m.build(raw,self.saved,dict(self.identity,response_sha256=digest(raw)))
 def test_malformed_selection_and_cursor_rejected(self):
  for selection in [{'unknown':1},{'indices':[True]},{'indices':[-1]},{'indices':[2,1]},{'indices':[1,1]},{'indices':[9999]}]:
   with self.subTest(selection=selection),self.assertRaises(m.ContractError):self.reader.detail('materials',selection=selection)
  for cursor in ['', '%%%','x'*20000]:
   with self.subTest(cursor=cursor[:8]),self.assertRaises(m.ContractError):self.reader.detail('materials',cursor=cursor)
 def test_budgets_reject_without_relaxation(self):
  for name,limit in [('OBJECT_BYTES',100),('GENERATION_BYTES',1000),('MAX_RECORDS',1),('MAX_ENTRIES',3),('MAX_NODES',50)]:
   with self.subTest(budget=name),patch.object(m,name,limit),self.assertRaises(m.ContractError):m.build(self.raw,self.saved,self.identity)
 def test_manifest_schema_and_range_rejected(self):
  for mode in ['unknown','range','count']:
   value=json.loads(self.bundle.manifest)
   if mode=='unknown':value['extra']=1
   elif mode=='range':value['sections']['materials']['entries'][0]['offset']+=1
   else:value['sections']['materials']['total']+=1
   raw=canon(value)
   with self.subTest(mode=mode),self.assertRaises(m.ContractError):m.Reader(m.Bundle(raw,self.bundle.objects),digest(raw),self.identity)
 def test_readers_do_not_mutate_input(self):
  before=(self.bundle.manifest,dict(self.bundle.objects),dict(self.identity));self.reader.overview();self.reader.detail('gaps');self.reader.full_response()
  self.assertEqual(before,(self.bundle.manifest,self.bundle.objects,self.identity))

 def test_content_reads_bound_and_verified(self):
  chunks=[]
  for index in range(self.reader.overview()['content_chunks']):
   part=self.reader.content(index);self.assertTrue(self.reader.verify_content(part))
   self.assertLess(len(canon(part)),16*1024*1024)
   chunks.append(base64.b64decode(part['data']))
  self.assertEqual(b''.join(chunks),self.raw)
  for field in ['generation_id','manifest_sha256','data','sha256','index']:
   bad=copy.deepcopy(part);bad[field]=0 if field=='index' else 'bad'
   if field=='index':bad[field]=True
   with self.subTest(field=field),self.assertRaises(m.ContractError):self.reader.verify_content(bad)
 def test_same_run_other_generation_rejected(self):
  raw,saved,identity=fixture(extra={'changed':True});bundle=m.build(raw,saved,identity);other=m.Reader(bundle,digest(bundle.manifest),identity)
  self.assertEqual(identity['run_id'],self.identity['run_id'])
  with self.assertRaises(m.ContractError):self.reader.verify_page(other.detail('materials'))
  with self.assertRaises(m.ContractError):self.reader.verify_content(other.content(0))
  with self.assertRaises(m.ContractError):self.reader.detail('materials',cursor=other.detail('materials')['next_cursor'])
 def test_malformed_descriptor_types_rejected(self):
  for key,val in [('object_sha256',[]),('object_sha256',None),('index',True),('bytes',False),('sha256',{})]:
   value=json.loads(self.bundle.manifest);value['chunks'][0][key]=val;raw=canon(value)
   with self.subTest(key=key,value=val),self.assertRaises(m.ContractError):m.Reader(m.Bundle(raw,self.bundle.objects),digest(raw),self.identity)
 def test_generation_aggregate_strict_boundary(self):
  aggregate=len(self.bundle.manifest)+sum(map(len,self.bundle.objects.values()))
  self.assertLess(max(len(self.raw),len(self.saved),len(self.bundle.manifest),*map(len,self.bundle.objects.values())),aggregate)
  with patch.object(m,'GENERATION_BYTES',aggregate):
   with self.assertRaisesRegex(m.ContractError,'M18_GENERATION_LIMIT'):m.build(self.raw,self.saved,self.identity)
   with self.assertRaisesRegex(m.ContractError,'M18_GENERATION_LIMIT'):m.Reader(self.bundle,digest(self.bundle.manifest),self.identity)
  with patch.object(m,'GENERATION_BYTES',aggregate+1):
   self.assertEqual(m.build(self.raw,self.saved,self.identity),self.bundle)
 def test_object_strict_boundary(self):
  raw=canon({'synthetic':'x'*100})
  with patch.object(m,'OBJECT_BYTES',len(raw)):
   with self.assertRaisesRegex(m.ContractError,'M18_OBJECT_LIMIT'):m.parse(raw,object_limit=True)
   with self.assertRaisesRegex(m.ContractError,'M18_OBJECT_LIMIT'):m.canonical(json.loads(raw))
  with patch.object(m,'OBJECT_BYTES',len(raw)+1):self.assertEqual(m.canonical(json.loads(raw)),raw)
 def test_saved_semantic_tampering_even_with_matching_raw_hash(self):
  saved=json.loads(self.saved);saved['workspace']['gaps']=[];raw=canon(saved)
  with self.assertRaisesRegex(m.ContractError,'M18_SAVED_SEMANTIC_HASH'):m.build(self.raw,raw,dict(self.identity,raw_sha256=digest(raw)))
 def test_empty_selection_and_forged_cursor_offsets(self):
  page=self.reader.detail('materials',selection={'indices':[]})
  self.assertEqual(page['entries'],[]);self.assertIsNone(page['next_cursor']);self.assertEqual(page['matched_total'],0)
  cursor=self.reader.detail('materials')['next_cursor'];value=json.loads(base64.urlsafe_b64decode(cursor))
  for offset in [True,-1,0,1,31,70,96]:
   value['offset']=offset;bad=base64.urlsafe_b64encode(canon(value)).decode()
   with self.subTest(offset=offset),self.assertRaises(m.ContractError):self.reader.detail('materials',cursor=bad)
