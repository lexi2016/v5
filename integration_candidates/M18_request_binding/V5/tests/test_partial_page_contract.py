"""Synthetic-only tests of both pinned announcement consumers; no owner execution."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
import tempfile

CAPSULE = sys.argv.pop(1) if len(sys.argv) > 1 and sys.argv[1] in {
    'manager_plan_baseline', 'announcement_readback_baseline'} else 'manager_plan_baseline'
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE/'vendor'/CAPSULE))
from v4.manager_research import announcement_analysis as a
from v4.manager_research import workspace_announcements as w
from v4.manager_research.workspace_projection import digest, FLAGS

TARGET='20261012'; PUBLICATION='2026-10-09'; CODE='AN202610090000000001'
def sha(value):return hashlib.sha256(value.encode()).hexdigest()
def reseal(p):
    p['source_manifest_sha256']=digest(p['source_manifest'])
    p['sha256']=digest({k:v for k,v in p.items() if k!='sha256'})
    return p

def fixture(captured=1,total=8,success=False,explicit_zero=False):
    ref=dict(request=dict(url='https://np-anotice-stock.eastmoney.com/api/security/ann'),
             blob_sha256='a'*64,body_sha256='b'*64,retrieved_at='2026-10-11T01:00:00Z')
    issuer=dict(code='HK.00001',name='Synthetic',market_code='116',ann_type='H',source_stock_code='00001')
    listing=dict(art_code=CODE,title='Synthetic notice',notice_date=PUBLICATION+' 00:00:00',
                 page_index=1,item_index=1,raw_body_sha256='b'*64,source_ref=ref,source_issuer_codes=[issuer])
    catalog=dict(target_trade_date=TARGET,publication_date=PUBLICATION,source_scope='EASTMONEY_HK_DATE_CATALOG',
                 status='COMPLETE',connect_eligibility_status='NOT_ASSESSED',hkex_first_publication_verified=False,
                 run_id='1'*32,sha256='c'*64,manager_consumer_rows=[listing],captured_row_count=1,
                 captured_page_count=1,manager_consumer_row_count=1,manager_source_identity_count=1,manager_source_codes=['HK.00001'])
    read=dict(schema_version='v4.manager_research.eastmoney_hk_date_catalog_read.v1',target_trade_date=TARGET,
              publication_date=PUBLICATION,source_scope='EASTMONEY_HK_DATE_CATALOG',status='COMPLETE',readback_status='VERIFIED',catalog=catalog)
    pages=[]
    for index in range(1,captured+1):
        text='Synthetic page '+str(index);url=f'https://np-cnotice-stock.eastmoney.com/api/content/ann?art_code={CODE}&page_index={index}'
        pages.append(dict(page_index=index,page_total=total,source_ref=dict(request=dict(url=url),blob_sha256='d'*64,
                     body_sha256='e'*64,retrieved_at='2026-10-11T01:00:00Z'),raw_body_sha256='e'*64,
                     notice_date=PUBLICATION,text=text,text_sha256=sha(text)))
    text='\n\n'.join(p['text'] for p in pages) if success else None
    body=dict(art_code=CODE,title=listing['title'],body_status='COMPLETE_CONTENT_API_BODY' if success else 'BODY_CAPTURE_FAILED',
              content_page_count=total if captured else None,pages=pages,body_text=text,
              body_text_sha256=sha(text) if success else None,pdf_sha256=None,capture_receipt_sha256='f'*64)
    failure=dict(art_code=CODE,error_code='BODY_CAPTURE_FAILED:SYNTHETIC',receipt_sha256='f'*64)
    if captured or explicit_zero:failure.update(content_api_pages_captured=captured,content_api_page_total=total if captured else None)
    terminal=dict(schema_version='v4.manager_research.announcement_terminal_body_capture.v1',
                  status='PASS_COMPLETE_CONTENT_API_BODIES_ALL_ROWS' if success else 'PARTIAL_BODY_MATERIAL_CAPTURE_WITH_TERMINAL_GAPS',
                  article_count=1,input_identity_sha256='0'*64,failed_articles=[] if success else [failure],
                  body_status_counts={'COMPLETE_CONTENT_API_BODY':int(success),'BODY_CAPTURE_FAILED':int(not success)},
                  body_corpus_sha256='0'*64,body_corpus_manifest_sha256='0'*64,body_batch_receipt_sha256='0'*64,capture_receipt_sha256='0'*64)
    semantic=dict(schema='v4.announcement-semantic-catalog.v2',status='PASS_SYNTHETIC',target_research_date=TARGET,
                  target_notice_date=PUBLICATION,row_count=1,records=[dict(art_code=CODE,title=listing['title'],issuer_codes=[issuer])])
    corpus=dict(schema='v4.manager_research.eastmoney_hk_announcement_body_corpus.v3',target_notice_date=PUBLICATION,article_count=1,rows=[body])
    return semantic,corpus,read,terminal

def build(f):
    semantic,corpus,read,terminal=f
    descriptors=[dict(name=n,sha256=digest(v),canonical_sha256=digest(v),row_count=len(corpus["rows"])) for n,v in [('semantic_catalog',semantic),('body_corpus',corpus)]]
    return a.build_product(semantic,corpus,read,semantic_sha256=digest(semantic),body_sha256=digest(corpus),
                           verified_inputs=descriptors,target_trade_date=TARGET,publication_date=PUBLICATION,terminal_body_capture=terminal)
def validate(p,f):return a.validate_product(p,target_trade_date=TARGET,publication_date=PUBLICATION,catalog=f[2]['catalog'])
def terminal(f):return a._validated_terminal_body_capture(f[3],{CODE:f[1]['rows'][0]},{CODE})


def saved_fixture(root, captured=1, total=8, success=False, mutate=None):
    """Write only synthetic source/receipt bytes for the real evidence reader."""
    f=fixture(captured,total,success);b=f[1]['rows'][0];catalog=f[2]['catalog'];listing=catalog['manager_consumer_rows'][0]
    run='2'*32;evidence=root/run/'evidence';evidence.mkdir(parents=True)
    bodies=evidence/'body_batch'/'bodies';bodies.mkdir(parents=True)
    common=dict(art_code=CODE,target_trade_date=TARGET,publication_date=PUBLICATION,body_status=b['body_status'],
                listing_raw_body_sha256=listing['raw_body_sha256'],listing_source_ref=listing['source_ref'],
                source_issuer_codes=listing['source_issuer_codes'])
    original=dict(common,schema='v4.manager_research.source_bound_announcement_body.v1',
                  content_api_pages=copy.deepcopy(b['pages']),body_text=b['body_text'],body_text_sha256=b['body_text_sha256'],
                  pdf=None,semantic_status='NOT_REVIEWED',original_point_in_time_availability='CANNOT_CONFIRM',
                  first_hkex_publication_time='CANNOT_CONFIRM')
    receipt=dict(common,status=b['body_status'],error_code=None if success else 'BODY_CAPTURE_FAILED:SYNTHETIC',
                 content_api_pages_captured=captured,body_path=f'bodies/{CODE}.json')
    b.update(transport_body_status=b['body_status'],transport_semantic_status='NOT_REVIEWED',
             transport_pit_status='CANNOT_CONFIRM',transport_first_hkex_publication_time='CANNOT_CONFIRM')
    if mutate:mutate(receipt,b,original)
    def save(path,value):
        raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
        path.write_bytes(raw);return hashlib.sha256(raw).hexdigest()
    artifact_sha=save(bodies/(CODE+'.json'),original)
    receipt['body_file_sha256']=artifact_sha;b['capture_receipt_sha256']=artifact_sha
    material=dict(target_trade_date=TARGET,publication_date=PUBLICATION,catalog_run_id=catalog['run_id'],
                  catalog_sha256=catalog['sha256'],article_ids=[CODE],listing_body_sha256s=[listing['raw_body_sha256']])
    identity=sha(json.dumps(material,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
    common_meta=dict(target_trade_date=TARGET,publication_date=PUBLICATION,catalog_run_id=catalog['run_id'],
                     catalog_sha256=catalog['sha256'],input_identity_sha256=identity)
    counts={b['body_status']:1};status=f[3]['status']
    manifest=dict(common_meta,schema='v4.manager_research.source_bound_announcement_body_corpus.v1',
                  article_receipts=[receipt],body_status_counts=counts)
    manifest_sha=save(evidence/'body_corpus_manifest.json',manifest)
    f[1].update(input_identity_sha256=identity,source_manifest_sha256=manifest_sha,transport_complete_body_count=int(success))
    body_sha=save(evidence/'body_corpus.json',f[1]);catalog_sha=save(evidence/'catalog_read.json',f[2])
    batch=dict(common_meta,schema='v4.manager_research.announcement_body_batch_receipt.v1',status=status,
               article_rows=1,terminal_article_receipts=1,body_corpus='body_corpus.json',
               body_corpus_manifest='body_corpus_manifest.json',body_corpus_sha256=body_sha,
               body_corpus_manifest_sha256=manifest_sha,body_status_counts=counts)
    batch_sha=save(evidence/'body_batch_receipt.json',batch)
    capture=dict(schema_version='v4.manager_research.announcement_daily_capture.v1',status=status,
                 evidence_run_id=run,target_trade_date=TARGET,publication_date=PUBLICATION,catalog_run_id=catalog['run_id'],
                 catalog_product_sha256=catalog['sha256'],catalog_read_file_sha256=catalog_sha,
                 body_corpus_file_sha256=body_sha,body_corpus_manifest_file_sha256=manifest_sha,
                 body_batch_receipt_sha256=batch_sha,**FLAGS)
    save(evidence/'capture_receipt.json',capture)
    return evidence,f,run

class PartialPages(unittest.TestCase):
    def test_round_trip_zero_partial_and_all_pages_still_failed(self):
        for count,total,explicit in [(0,None,False),(0,None,True),(1,8,False),(3,3,False)]:
            with self.subTest(count=count,explicit=explicit):
                f=fixture(count,total,explicit_zero=explicit);before=copy.deepcopy(f);p=build(f)
                self.assertEqual(validate(p,f),p);self.assertEqual(f,before)
                row=p['records'][0];self.assertEqual(row['body_status'],'BODY_CAPTURE_FAILED')
                self.assertEqual(row['selection_status'],'NOT_ASSESSED');self.assertEqual(row['analysis_kind'],'TEXT_INSUFFICIENT_UNASSESSED')
                self.assertEqual(row['body_page_citations'],[]);self.assertIsNone(row['body_text_sha256'])
                self.assertEqual(p['source_manifest']['point_in_time_status'],'CANNOT_CONFIRM')
                for k,v in FLAGS.items():self.assertIs(p[k],v)
                self.assertEqual(row['body_capture_failure'].get('content_api_pages_captured'),count if count else None)

    def test_original_success_body_round_trip(self):
        f=fixture(2,2,success=True);p=build(f);self.assertEqual(validate(p,f),p)
        self.assertEqual(p['records'][0]['analysis_kind'],'COMPLETE_API_BODY')
        self.assertNotIn('body_capture_failure',p['records'][0])

    def test_terminal_counts_strict_types_and_unknown_keys(self):
        for field in ['content_api_pages_captured','content_api_page_total']:
            for value in [True,False,1.0,'1',-1,None]:
                with self.subTest(field=field,value=value):
                    f=fixture(1,1);f[3]['failed_articles'][0][field]=value
                    with self.assertRaises(ValueError):terminal(f)
        for field in ['content_api_pages_captured','content_api_page_total']:
            f=fixture();del f[3]['failed_articles'][0][field]
            with self.assertRaises(ValueError):terminal(f)
        f=fixture();f[3]['failed_articles'][0]['unexpected']=1
        with self.assertRaises(ValueError):terminal(f)

    def test_raw_count_and_page_numbers_reject_python_equal_nonintegers(self):
        for field in ['content_page_count','page_total','page_index']:
            for value in [True,1.0,'1',-1]:
                with self.subTest(field=field,value=value):
                    f=fixture(1,1);b=f[1]['rows'][0]
                    (b if field=='content_page_count' else b['pages'][0])[field]=value
                    with self.assertRaises(ValueError):build(f)

    def test_projected_summary_count_types_and_unknown_keys(self):
        f=fixture(1,1);b=f[1]['rows'][0];b['pages']=[];b['content_page_count']=None
        b['capture_page_summary']=dict(content_api_pages_captured=1,content_api_page_total=1)
        terminal(f)
        for field in ['content_api_pages_captured','content_api_page_total']:
            for value in [True,1.0,'1',-1]:
                with self.subTest(field=field,value=value):
                    g=copy.deepcopy(f);g[1]['rows'][0]['capture_page_summary'][field]=value
                    with self.assertRaises(ValueError):terminal(g)
        b['capture_page_summary']['unknown']=1
        with self.assertRaises(ValueError):terminal(f)

    def test_zero_requires_no_pages_no_total_no_summary(self):
        for mutate in [lambda b:b.update(content_page_count=0),lambda b:b.update(capture_page_summary={}),lambda b:b.update(pages=[{}])]:
            f=fixture(0,None);mutate(f[1]['rows'][0])
            with self.assertRaises(ValueError):terminal(f)
        f=fixture(0,None,explicit_zero=True);f[3]['failed_articles'][0]['content_api_page_total']=0
        with self.assertRaises(ValueError):terminal(f)

    def test_missing_order_total_receipt_source_and_hash_rejected(self):
        changes=[lambda b:b['pages'].pop(1),lambda b:b['pages'].reverse(),
                 lambda b:b['pages'][1].update(page_total=9),lambda b:b.update(capture_receipt_sha256='0'*64),
                 lambda b:b['pages'][0]['source_ref'].update(body_sha256='0'*64),
                 lambda b:b['pages'][0].update(text_sha256='0'*64),
                 lambda b:b['pages'][0].update(notice_date='2026-10-08')]
        for i,mutate in enumerate(changes):
            with self.subTest(change=i):
                f=fixture(3,8);mutate(f[1]['rows'][0])
                with self.assertRaises(ValueError):build(f)

    def test_resealed_product_projection_cannot_launder_types_or_promote_failure(self):
        f=fixture(1,1);p=build(f)
        changes=[lambda x:x['body_capture_failure'].update(content_api_pages_captured=True),
                 lambda x:x['body_capture_failure'].update(content_api_page_total=1.0),
                 lambda x:x['body_capture_failure'].update(extra=1),
                 lambda x:x.update(selection_status='SELECTED'),lambda x:x.update(body_status='COMPLETE_CONTENT_API_BODY'),
                 lambda x:x['body_capture_failure'].update(receipt_sha256='0'*64)]
        for i,mutate in enumerate(changes):
            with self.subTest(change=i):
                q=copy.deepcopy(p);mutate(q['records'][0]);reseal(q)
                with self.assertRaises(ValueError):validate(q,f)

    def test_owner_partial_receipt_and_original_pages_keep_strict_counts(self):
        for count,total in [(0,None),(1,8),(3,3)]:
            f=fixture(count,total);b=f[1]['rows'][0];original=dict(content_api_pages=copy.deepcopy(b['pages']))
            self.assertEqual(w._failed_capture_page_counts(dict(content_api_pages_captured=count),b,original,CODE,PUBLICATION),(count,total))
        for target in ['receipt','body','original_page','body_page']:
            for value in [True,1.0,'1',-1]:
                with self.subTest(target=target,value=value):
                    f=fixture(1,1);b=f[1]['rows'][0];o=dict(content_api_pages=copy.deepcopy(b['pages']));rec=dict(content_api_pages_captured=1)
                    if target=='receipt':rec['content_api_pages_captured']=value
                    elif target=='body':b['content_page_count']=value
                    elif target=='original_page':o['content_api_pages'][0]['page_total']=value
                    else:b['pages'][0]['page_total']=value
                    with self.assertRaises(ValueError):w._failed_capture_page_counts(rec,b,o,CODE,PUBLICATION)

    def test_product_hash_source_and_safety_still_enforced(self):
        f=fixture(0,None);p=build(f)
        for field,value in [('sha256','0'*64),('target_trade_date','20261013'),('production_allowed',True)]:
            q=copy.deepcopy(p);q[field]=value
            with self.assertRaises(ValueError):validate(q,f)


    def test_saved_evidence_reader_to_product_round_trip(self):
        for count,total,success in [(0,None,False),(1,8,False),(3,3,False),(2,2,True)]:
            with self.subTest(count=count,success=success),tempfile.TemporaryDirectory() as tmp:
                evidence,f,run=saved_fixture(Path(tmp),count,total,success)
                terminal_result=w.validate_terminal_body_capture(evidence,f[2],TARGET,PUBLICATION,expected_run_id=run)
                f=(*f[:3],terminal_result);p=build(f);self.assertEqual(validate(p,f),p)
                self.assertEqual(terminal_result['failed_articles']==[],success)
                if count and not success:
                    self.assertEqual(terminal_result['failed_articles'][0]['content_api_page_total'],total)

    def test_saved_receipt_types_and_original_pages_rejected(self):
        for success in [False,True]:
            for target in ['receipt','body_total','original_index','original_total','body_index']:
                for value in [True,1.0,'1',-1]:
                    with self.subTest(success=success,target=target,value=value),tempfile.TemporaryDirectory() as tmp:
                        def mutate(rec,b,o):
                            if target=='receipt':rec['content_api_pages_captured']=value
                            elif target=='body_total':b['content_page_count']=value
                            elif target=='original_index':o['content_api_pages'][0]['page_index']=value
                            elif target=='original_total':o['content_api_pages'][0]['page_total']=value
                            else:b['pages'][0]['page_index']=value
                        evidence,f,run=saved_fixture(Path(tmp),1,1,success,mutate)
                        with self.assertRaises(ValueError):w.validate_terminal_body_capture(evidence,f[2],TARGET,PUBLICATION,expected_run_id=run)

    def test_saved_artifact_tamper_and_safety_fail_closed(self):
        for name in ['catalog_read.json','body_corpus.json','body_corpus_manifest.json',
                     'body_batch_receipt.json',f'body_batch/bodies/{CODE}.json']:
            with self.subTest(file=name),tempfile.TemporaryDirectory() as tmp:
                evidence,f,run=saved_fixture(Path(tmp));path=evidence/name
                path.write_bytes(path.read_bytes()+b' ')
                with self.assertRaises(ValueError):w.validate_terminal_body_capture(evidence,f[2],TARGET,PUBLICATION,expected_run_id=run)
        for field,value in [('transport_pit_status','VERIFIED'),('transport_semantic_status','REVIEWED'),('body_text','upgrade')]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as tmp:
                evidence,f,run=saved_fixture(Path(tmp),mutate=lambda rec,b,o:b.update({field:value}))
                with self.assertRaises(ValueError):w.validate_terminal_body_capture(evidence,f[2],TARGET,PUBLICATION,expected_run_id=run)

    def test_three_failed_records_are_retained(self):
        f=fixture(1,8);semantic,corpus,read,term=f
        for i in [2,3]:
            code=CODE[:-1]+str(i)
            record=copy.deepcopy(semantic['records'][0]);record['art_code']=code;semantic['records'].append(record)
            listing=copy.deepcopy(read['catalog']['manager_consumer_rows'][0]);listing['art_code']=code;listing['item_index']=i
            read['catalog']['manager_consumer_rows'].append(listing)
            body=copy.deepcopy(corpus['rows'][0]);body['art_code']=code
            body['pages'][0]['source_ref']['request']['url']=body['pages'][0]['source_ref']['request']['url'].replace(CODE,code)
            corpus['rows'].append(body)
            failure=copy.deepcopy(term['failed_articles'][0]);failure['art_code']=code;term['failed_articles'].append(failure)
        semantic['row_count']=3;corpus['article_count']=3;term['article_count']=3;term['body_status_counts']['BODY_CAPTURE_FAILED']=3
        read['catalog'].update(captured_row_count=3,manager_consumer_row_count=3,manager_source_identity_count=3)
        p=build(f);self.assertEqual(validate(p,f),p);self.assertEqual(len(p['records']),3)
        self.assertTrue(all(row['body_status']=='BODY_CAPTURE_FAILED' and row['body_capture_failure']['content_api_pages_captured']==1 for row in p['records']))
        q=copy.deepcopy(p);q['records'].pop();reseal(q)
        with self.assertRaises(ValueError):validate(q,f)

if __name__=='__main__':unittest.main(verbosity=2)
