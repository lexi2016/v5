"""Official relationship facts; directory/PDF traffic below is synthetic/offline."""
from copy import deepcopy
from datetime import datetime
import importlib,json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs
from v5_shadow.manager_loader import load_owner
from v5_shadow.m16_runtime import closure
from support import observation,pdf_bytes

class TemporaryCounterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.components=load_owner(closure())['components']
        cls.hkex=importlib.import_module('m16_owner_manager_research.hkex_provider')
        cls.ports=importlib.import_module('m16_owner_manager_research.ports')
        cls.contracts=importlib.import_module('m16_owner_manager_research.contracts')
        cls.service=importlib.import_module('m16_owner_manager_research.service')

    def setUp(self):
        self.calls=[];self.mapping=[{'c':'02670','i':'123','n':'YUNJI'}];self.directory_code='02670'
        self.published='08/09/2026 08:30';self.row=observation()['rows'][0]
        self.row.update(code='HK.02915',name='YUNJI-OLD',source_last_bar_time='2026-10-12 09:40:00',last_price=21.5,volume=500,formal_eligible=False)
        for target in ('socket.create_connection','socket.socket.connect','urllib.request.urlopen','urllib.request.OpenerDirector.open'):
            guard=patch(target,side_effect=AssertionError('NO_REAL_NETWORK'));guard.start();self.addCleanup(guard.stop)
        self.provider=self.components.provider_class(transport=self.transport,eastmoney_transport=lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO_MIRROR')))

    def transport(self,url,**kwargs):
        self.calls.append((url,kwargs))
        if 'activestock' in url:body=json.dumps(self.mapping).encode()
        elif 'titlesearch' in url:
            body=f'<table><tr><td class="release-time">{self.published}</td><td class="stock-short-code">{self.directory_code}</td><td class="stock-short-name">YUNJI</td><td><div class="doc-link"><a href="https://www.hkexnews.hk/synthetic-yunji-test.pdf">Annual results</a></div></td></tr></table>'.encode()
        elif url.endswith('synthetic-yunji-test.pdf'):body=pdf_bytes()
        else:raise AssertionError('UNEXPECTED_URL')
        return self.ports.SourceResponse(url,200,body,{},'2026-10-13T10:00:00+08:00',url)

    def collect(self,date='20261012',row=None):
        return self.provider.collect(target_trade_date=date,cutoff_at=self.contracts.cutoff_at(date),observation=row or self.row)

    def test_official_evidence_record_and_no_security_alias(self):
        before=deepcopy(self.row);result=self.collect()
        self.assertEqual(result['status'],'READY');self.assertEqual(self.row,before)
        source=result['source'];self.assertEqual(source['issuer_code'],'HK.02915')
        self.assertEqual(source['observed_counter_code'],'HK.02915');self.assertEqual(source['issuer_document_code'],'HK.02670')
        relation=source['issuer_relationship']
        self.assertEqual(relation['counter_name_at_cutoff'],'YUNJI-OLD')
        self.assertEqual(relation['effective_from'],'2026-09-23T09:00:00+08:00')
        self.assertEqual(relation['scheduled_end_exclusive'],'2026-10-29T16:10:00+08:00')
        self.assertEqual(relation['scope'],'ISSUER_PUBLIC_DOCUMENT_LOOKUP_ONLY')
        self.assertEqual(len(relation['sources']),3)
        self.assertIn('2026090103473.pdf',relation['sources'][1]['url'])
        self.assertEqual(relation['sources'][1]['locator'],'PDF pages 1-2, Revised timetable (Hong Kong time)')
        post=next(kwargs for url,kwargs in self.calls if kwargs.get('method')=='POST')
        self.assertEqual(parse_qs(post['body'].decode())['stockId'],['123'])
        self.assertTrue(all('hkexnews.hk' in url for url,_ in self.calls))

    def test_before_open_and_at_or_after_scheduled_close_refused(self):
        mapping={'02670':{'mapping_code':'02670','stock_id':'123','issuer':'YUNJI'}}
        for cutoff in ('2026-09-23T08:59:59+08:00','2026-10-29T16:10:00+08:00','2026-10-30T09:40:00+08:00'):
            with self.subTest(cutoff=cutoff),self.assertRaisesRegex(self.hkex.ProviderError,'OUTSIDE_EVIDENCED_WINDOW'):
                self.hkex._resolve_document_issuer('02915',mapping,cutoff_at=cutoff)
        for date in ('20260922','20261030'):
            self.calls.clear();result=self.collect(date)
            self.assertEqual(result['status'],'CANNOT_CONFIRM')
            self.assertFalse(any('titlesearch' in url for url,_ in self.calls))

    def test_exact_open_and_parallel_phase(self):
        mapping={'02670':{'mapping_code':'02670','stock_id':'123','issuer':'YUNJI'}}
        first=self.hkex._resolve_document_issuer('02915',mapping,cutoff_at='2026-09-23T09:00:00+08:00')
        self.assertEqual(first['counter_relationship']['counter_name_at_cutoff'],'YUNJI')
        parallel=self.hkex._resolve_document_issuer('02915',mapping,cutoff_at='2026-10-08T09:00:00+08:00')
        self.assertEqual(parallel['counter_relationship']['counter_name_at_cutoff'],'YUNJI-OLD')
        self.assertEqual(mapping['02670'],{'mapping_code':'02670','stock_id':'123','issuer':'YUNJI'})

    def test_wrong_issuer_and_counter_conflict_refused(self):
        for mapping in ([{'c':'02670','i':'123','n':'UNRELATED ISSUER'}],
                        [{'c':'00928','i':'123','n':'YUNJI'}],
                        [{'c':'02670','i':'123','n':'YUNJI'},{'c':'02915','i':'999','n':'UNRELATED'}]):
            self.mapping=mapping;self.provider._active_stock_expires_at=0;self.calls.clear()
            result=self.collect();self.assertEqual(result['status'],'CANNOT_CONFIRM')
            self.assertFalse(any('titlesearch' in url for url,_ in self.calls))

    def test_other_codes_do_not_receive_relationship(self):
        result=self.hkex._resolve_document_issuer('00928',{},cutoff_at='2026-10-12T09:40:00+08:00')
        self.assertIsNone(result)
        mapping={'02670':{'mapping_code':'02670','stock_id':'123','issuer':'YUNJI'}}
        self.assertNotIn('counter_relationship',self.hkex._resolve_document_issuer('02670',mapping,cutoff_at='2026-10-12T09:40:00+08:00'))

    def test_wrong_directory_code_and_future_publication_refused(self):
        self.directory_code='00928'
        self.assertEqual(self.collect()['reason'],'NO_QUALIFYING_ANNOUNCEMENT')
        self.directory_code='02670';self.published='12/10/2026 09:41'
        self.assertEqual(self.collect()['reason'],'NO_QUALIFYING_ANNOUNCEMENT')
        self.assertFalse(any(url.endswith('.pdf') for url,_ in self.calls))

    def test_original_input_identity_prices_lot_and_pit_preserved(self):
        value=observation();value.update(target_trade_date='20261012',rows=[self.row])
        data=self.contracts.normalise_observation_input(value);before=deepcopy(data)
        result=self.collect();product=self.service.ManagerResearchJobService._build_product(data,data['rows'],{'HK.02915':result})
        self.assertEqual(data,before);self.assertEqual(product['input_identity'],before['input_identity'])
        self.assertEqual(product['cutoff_at'],before['cutoff_at']);self.assertEqual(product['rows'][0]['code'],'HK.02915')
        self.assertEqual(product['rows'][0]['observation']['last_price'],21.5)
        self.assertEqual(product['rows'][0]['observation']['volume'],500)
        self.assertFalse(product['rows'][0]['formal_eligible']);self.assertFalse(product['historical_system_available'])
        self.assertNotIn('HK.02670',{row['code'] for row in product['rows']})

    def test_record_matches_verified_official_revised_timetable(self):
        from pathlib import Path
        fixture=json.loads((Path(__file__).parent/'fixtures/yunji_counter_evidence.json').read_text())
        self.assertEqual(fixture['evidence_kind'],'MANUALLY_VERIFIED_PUBLIC_DOCUMENT_FACTS')
        self.assertIsNone(fixture['remote_document_bytes_sha256'])
        record=self.hkex._YUNJI_COUNTER_RELATION; timetable=fixture['sources'][1]
        self.assertEqual(record['effective_from'],timetable['revised_open'])
        self.assertNotEqual(record['effective_from'],timetable['original_open'])
        self.assertEqual(record['parallel_from'],timetable['revised_parallel_from'])
        self.assertEqual(record['scheduled_end_exclusive'],timetable['revised_scheduled_close'])
        self.assertEqual(record['issuer_document_code'],fixture['identity']['issuer_document_code'])
        self.assertEqual(record['observed_counter_code'],fixture['identity']['temporary_counter_code'])
        self.assertEqual([s['url'] for s in record['sources']],[s['url'] for s in fixture['sources']])
