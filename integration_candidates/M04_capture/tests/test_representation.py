import hashlib,json,sys,unittest
from urllib.parse import quote
from unittest.mock import patch
import test_capture as fixture
sys.path.insert(0,str(fixture.ROOT/'source/V5/src'))
from v5_shadow import archive_article_v2 as article

class RepresentationTests(unittest.TestCase):
 def test_original_decoder_only_decodes_its_known_tag_contract(self):
  name='合成科技';tag='<e type="hashtag" title="'+quote('#'+name+'#')+'" />'
  out=article.body_representation(tag+' 原样%23ABC%23',name)
  self.assertEqual(out['decoded_text'],'#合成科技# 原样%23ABC%23')
  self.assertEqual(out['raw_sha256'],hashlib.sha256((tag+' 原样%23ABC%23').encode()).hexdigest())
  self.assertEqual(out['issuer_encoded_tags'][0]['text'],tag)
  self.assertEqual(out['issuer_decoded_spans'][0]['text'],name)
 def test_missing_issuer_and_unrecognized_percent_text_rejected(self):
  for raw in ('无该公司正文',quote('合成科技')):
   with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,'ISSUER_BODY_BINDING'):article.body_representation(raw,'合成科技')
 def test_decoder_pin_drift_rejected(self):
  with patch.object(article,'ANALYZER_SHA256','0'*64):
   with self.assertRaisesRegex(ValueError,'DECODER_SOURCE_SHA'):article.body_representation('合成科技','合成科技')
 def test_encoded_issuer_and_composite_owner_summary_real_chain(self):
  c=fixture.CaptureTests();c.setUp();self.addCleanup(c.doCleanups)
  tag='<e type="hashtag" title="'+quote('#合成科技（000001）#')+'" />'
  # More than 240 characters; original collector appends the headline to its
  # truncated content_head. No punctuation after the company before truncation.
  body='独立  合成标题\n'+'普通文字'*42+'\n'+tag+'与 NASDAQ:AVGO 签署光模块供货协议 '+'尾部不是标题'*30
  response={'topics':[{'topic_id':'12345678901234567','create_time':c.published,'content':body}],'has_more':False}
  fixture.write_synthetic_cli(c.cli,'print('+repr(json.dumps(response,ensure_ascii=False))+')\n');c.config['cli']['sha256']=c.sha(c.cli)
  result=c.run_capture();self.assertEqual(result['status'],'SUCCEEDED')
  product=c.m.materials(result['archive_binding']);a=product['articles'][0]['source_article'];meta=a['acquisition_v2']
  self.assertEqual(a['body_text'],body);self.assertNotIn(a['stock_name'],body)
  self.assertIn(a['stock_name'],meta['body_representation']['decoded_text'])
  self.assertEqual(meta['evidence_semantics']['kind'],'ORIGINAL_BUILDER_SUMMARY')
  self.assertEqual(meta['evidence_semantics']['quote_status'],'NOT_A_SOURCE_QUOTE')
  self.assertNotIn(a['evidence_sentence'],meta['body_representation']['decoded_text'])
  self.assertEqual(meta['evidence_semantics']['summary_sha256'],hashlib.sha256(a['evidence_sentence'].encode()).hexdigest())
  self.assertIn('source_title_transform',meta);self.assertFalse(product['historical_pit_claimed'])
  import research_lane
  archive_root=fixture.Path(result['archive_binding']['root'])
  before={str(p):p.read_bytes() for p in archive_root.rglob('*') if p.is_file()}
  lane=research_lane.research_lane(result['archive_binding'],{'research_date':c.day})
  display=lane['archive_materials']['articles'][0]
  self.assertEqual(display['summary'],'原owner派生摘要（非原文引句）：'+a['evidence_sentence'])
  self.assertTrue(display['summary_display_only'])
  self.assertEqual({key:display[key] for key in a},a)
  self.assertEqual(display['body_text'],body)
  self.assertEqual(before,{str(p):p.read_bytes() for p in archive_root.rglob('*') if p.is_file()})
  # A hypothetical new issuer or fabricated summary still fails full owner replay.
  root=fixture.Path(result['archive_binding']['root']);payload=json.loads((root/product['articles'][0]['archive_file']).read_bytes());read=lambda name:(root/name).read_bytes()
  original=json.loads(read(payload['archive_input_v1']['path']));original['articles'][0]['evidence_sentence']='合成科技虚构合并结论'
  with self.assertRaises(ValueError):article.enrich(original,payload['acquisition_receipt'],payload['archive_input_v1'],read,payload['source_generated_at'],builder_source=payload['builder_source'],builder_receipt=payload['builder_receipt'])
  original=json.loads(read(payload['archive_input_v1']['path']));original['articles'][0]['source_title']='任意替换标题'
  with self.assertRaisesRegex(ValueError,'SUMMARY_BINDING_NOT_UNIQUE'):article.enrich(original,payload['acquisition_receipt'],payload['archive_input_v1'],read,payload['source_generated_at'],builder_source=payload['builder_source'],builder_receipt=payload['builder_receipt'])
