import copy,hashlib,json,sys,unittest
from unittest.mock import patch
import test_capture as fixture
sys.path.insert(0,str(fixture.ROOT/'source/V5/src'))
from v5_shadow import archive_article_v2 as article

class EvidenceSpanTests(unittest.TestCase):
 def test_unicode_whitespace_exact_contiguous_raw_span(self):
  body='前言。✅投资亮点：\n▫️合成科技 000001\r\n\t兵器工业\u3000设备。尾段'
  evidence='✅投资亮点： ▫️合成科技 000001 兵器工业 设备。'
  span=article.evidence_raw_span(body,evidence)
  raw=body[span['char_start']:span['char_end']]
  self.assertEqual(raw,span['text']);self.assertEqual(body.encode()[span['utf8_start']:span['utf8_end']],raw.encode())
  self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(),span['sha256'])
  self.assertIn('\r\n\t',raw)
 def test_duplicate_normalized_span_rejected(self):
  with self.assertRaisesRegex(ValueError,'ARTICLE_V2_EVIDENCE_SPAN_NOT_UNIQUE'):
   article.evidence_raw_span('合成\n科技。合成\t科技。','合成 科技。')
 def test_nonwhitespace_difference_and_empty_rejected(self):
  for body,evidence in [('合成科技 增长。','合成科技 下跌。'),('','合成科技'),('合成科技',''),('合成\n科技','合成科技')]:
   with self.subTest(body=body,evidence=evidence),self.assertRaises(ValueError):article.evidence_raw_span(body,evidence)
 def test_saved_capture_recovery_body_span_and_cold_reader(self):
  c=fixture.CaptureTests();c.setUp();self.addCleanup(c.doCleanups)
  body='✅投资亮点：\n▫️合成科技（000001）\n与 NASDAQ:AVGO 签署光模块供货协议并交付光互连设备。'+'此处为独立测试合成正文，没有真实业务含义。'*20
  response={'topics':[{'topic_id':'12345678901234567','create_time':c.published,'content':body}],'has_more':False}
  fixture.write_synthetic_cli(c.cli,'print('+repr(json.dumps(response,ensure_ascii=False))+')\n');c.config['cli']['sha256']=c.sha(c.cli)
  with patch.object(c.m.ingest,'run_import',side_effect=ValueError('ARTICLE_V2_ISSUER_BODY_BINDING')):
   with self.assertRaisesRegex(ValueError,'ISSUER_BODY_BINDING'):c.run_capture()
  source=c.runtime/'captures/case1/source';before={str(p.relative_to(source)):c.sha(p) for p in source.rglob('*') if p.is_file()}
  c.cli.write_text('provider unavailable; recovery must not call it')
  result=c.m.resume(c.config,'case1');self.assertEqual(result['status'],'SUCCEEDED')
  self.assertEqual(before,{str(p.relative_to(source)):c.sha(p) for p in source.rglob('*') if p.is_file()})
  product=c.m.materials(result['archive_binding']);a=product['articles'][0]['source_article']
  self.assertEqual(a['body_text'],body);self.assertNotIn(a['evidence_sentence'],body)
  span=a['acquisition_v2']['evidence_raw_span'];self.assertIn('\n',span['text']);self.assertEqual(body[span['char_start']:span['char_end']],span['text'])
  self.assertEqual(a['acquisition_v2']['body_sha256'],hashlib.sha256(body.encode()).hexdigest())
  self.assertFalse(product['historical_pit_claimed'])
  # A stored span is evidence, not a bypass: even rehashed archive bytes cannot change it.
  binding=result['archive_binding'];name=product['articles'][0]['archive_file'];path=fixture.Path(binding['root'])/name
  old=path.read_bytes();payload=json.loads(old)
  archive_root=fixture.Path(binding['root']);read=lambda name:(archive_root/name).read_bytes()
  original=json.loads(read(payload['archive_input_v1']['path']))
  def enrich(value):
   return article.enrich(value,payload['acquisition_receipt'],payload['archive_input_v1'],read,payload['source_generated_at'],builder_source=payload['builder_source'],builder_receipt=payload['builder_receipt'])
  self.assertEqual(enrich(original),payload)
  for field,value in [('stock_name','不存在的发行人'),('evidence_sentence','合成科技虚构并购结论')]:
   changed=copy.deepcopy(original);changed['articles'][0][field]=value
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'ARTICLE_V2_ISSUER_BODY_BINDING'):enrich(changed)
  # Changing the expected raw page pin still fails before any span admission.
  bad_ref=copy.deepcopy(payload['acquisition_receipt']);bad_ref['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'ARTICLE_V2_FILE_SHA'):
   article.enrich(original,bad_ref,payload['archive_input_v1'],read,payload['source_generated_at'],builder_source=payload['builder_source'],builder_receipt=payload['builder_receipt'])
  payload['articles'][0]['acquisition_v2']['evidence_raw_span']['char_start']+=1
  path.write_text(json.dumps(payload));
  with self.assertRaises(ValueError):c.m.materials(binding)
