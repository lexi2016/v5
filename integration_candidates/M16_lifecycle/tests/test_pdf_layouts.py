"""Original cached PDF text, with physical page and byte hashes; no fetching."""
import importlib
import json
from hashlib import sha256
from pathlib import Path
import unittest
from v5_shadow.manager_loader import load_owner
from v5_shadow.m16_runtime import closure

class PdfLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_owner(closure())
        cls.pdf = importlib.import_module('m16_owner_manager_research.pdf_parser')
        cls.rows = json.loads((Path(__file__).parent/'fixtures/real_pdf_fragments.json').read_text())

    def test_original_fragment_hashes(self):
        for row in self.rows:
            self.assertEqual(sha256(row['text'].encode()).hexdigest(), row['text_utf8_sha256'])

    def test_real_bilingual_rmb(self):
        row=self.rows[0]; facts=self.pdf._financial_facts(row['pdf_page'], row['text'])
        self.assertEqual(len(facts),2)
        self.assertEqual(facts[0]['fields']['values'],[{'column':'2026','raw':'333,284'},{'column':'2025','raw':'287,537'}])
        self.assertEqual(facts[0]['fields']['note_marker'],'4')
        self.assertIn('Revenue ϗɝ',facts[0]['source_excerpt'])
        self.assertEqual(facts[0]['locator'],'PDF page 33')

    def test_real_unit_rmb_half_year(self):
        row=self.rows[1]; facts=self.pdf._financial_facts(row['pdf_page'],row['text'])
        self.assertEqual(len(facts),2)
        self.assertEqual(facts[0]['fields']['currency'],'RMB')
        self.assertEqual(facts[0]['fields']['unit'],'yuan')
        self.assertIn('first half year of 2026',facts[0]['fields']['period_label'])
        self.assertEqual(facts[0]['fields']['values'][0]['raw'],'3,252,515,191.59')

    def test_real_missing_year_stays_unconfirmed(self):
        row=self.rows[2]
        self.assertEqual(self.pdf._financial_facts(row['pdf_page'],row['text']),[])

    def test_real_hkd_symbol_and_notes(self):
        row=self.rows[3]; facts=self.pdf._financial_facts(row['pdf_page'],row['text'])
        self.assertEqual(len(facts),2)
        self.assertEqual([f['fields']['note_marker'] for f in facts],['5','9'])
        self.assertEqual(facts[0]['fields']['currency'],'HKD')
        self.assertEqual(facts[0]['fields']['unit'],'thousands')
        self.assertIn('HK$’000',facts[0]['source_excerpt'])
        self.assertEqual(facts[1]['fields']['values'][0]['raw'],'(1,202,398)')

    def test_negative_contracts(self):
        header='For the six months ended 30 June 2026\n2026 2025\n(RMB in thousands)\n'
        for text in [header.replace('(RMB in thousands)\n','')+'Revenue 10 9',
                     '2026 2025\n(RMB in thousands)\nRevenue 10 9',
                     header+'Revenue 4 10 9', header+'Revenue 10',
                     header+'Revenue 利润 10 9',header+'Revenue Gross profit 10 9',
                     header+'Gross profit Loss 10 9',header+'Gross profit 亏损 10 9',
                     header+'Revenue 10 9 extra',header+'Revenue 10 9 8 7']:
            with self.subTest(text=text): self.assertEqual(self.pdf._financial_facts(1,text),[])

    def test_cache_version_changed(self):
        provider=importlib.import_module('m16_owner_manager_research.hkex_provider')
        self.assertGreater(provider.PDF_FACTS_CACHE_VERSION,1)

    def test_public_page_api_retains_audit(self):
        for row in (self.rows[0],self.rows[1],self.rows[3]):
            facts=self.pdf.extract_facts_from_pages([{'page':row['pdf_page'],'text':row['text']}],title='Interim results')
            facts=[f for f in facts if f.get('fact_kind')=='financial']
            self.assertEqual(len(facts),2)
            for fact in facts:
                self.assertEqual(fact['page'],row['pdf_page'])
                self.assertEqual(fact['fields']['columns'],['2026','2025'])

    def test_current_version_reparses_legacy_cache(self):
        import tempfile
        from types import SimpleNamespace
        materials=importlib.import_module('m16_owner_manager_research.materials')
        provider=importlib.import_module('m16_owner_manager_research.hkex_provider')
        row=self.rows[0]; body=row['text'].encode(); material=SimpleNamespace(body=body,sha256=sha256(body).hexdigest())
        with tempfile.TemporaryDirectory() as root:
            store=materials.MaterialStore(root)
            args=dict(parser_id='hkex-pdf-facts',params={'title':'Interim results'})
            self.assertEqual(store.parsed(material,parser_version=1,parse_fn=lambda _:[],**args),[])
            self.assertEqual(store.parsed(material,parser_version=2,parse_fn=lambda _:['SYNTHETIC_OLD_TRUNCATED_LABEL'],**args),['SYNTHETIC_OLD_TRUNCATED_LABEL'])
            calls=[]
            def parse(raw):
                calls.append(raw)
                return self.pdf._financial_facts(row['pdf_page'],raw.decode())
            new=store.parsed(material,parser_version=provider.PDF_FACTS_CACHE_VERSION,parse_fn=parse,**args)
            self.assertEqual(len(new),2); self.assertEqual(len(calls),1)
            self.assertEqual(store.parsed(material,parser_version=provider.PDF_FACTS_CACHE_VERSION,parse_fn=parse,**args),new)
            self.assertEqual(len(calls),1)
            self.assertEqual(store.parsed(material,parser_version=1,parse_fn=parse,**args),[])

    def test_same_period_header_needs_explicit_year(self):
        original=self.rows[2]['text']
        # Synthetic context variant, not claimed to occur on original page 5.
        explicit='For the six months ended 30 June 2026\n'+original
        facts=self.pdf._financial_facts(5,explicit)
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]['fields']['columns'][:2],['This Reporting Period','Same Period of Last Year'])
        self.assertEqual(facts[0]['fields']['values'][2]['raw'],'14.48%')
        self.assertEqual(self.pdf._financial_facts(5,original),[])

    def test_values_cannot_become_year_columns(self):
        text='For the six months ended 30 June 2026\n2026 2025\n(RMB in thousands)\nRevenue 2025 2026\nCost of sales 10 9'
        facts=self.pdf._financial_facts(1,text)
        self.assertEqual(len(facts),2)
        self.assertTrue(all(f['fields']['columns']==['2026','2025'] for f in facts))

    def test_currency_context_is_not_crossed(self):
        text='For the six months ended 30 June 2026\n2026 2025\nUnit: RMB\nRevenue (USD) 100 90'
        facts=self.pdf._financial_facts(1,text)
        self.assertEqual(len(facts),1)
        self.assertTrue(all(f['fields']['currency']=='USD' and f['fields']['unit']=='units' for f in facts))
        mixed='For the six months ended 30 June 2026\n2026 2025\nNote HK$’000 RMB’000\nRevenue 4 100 90'
        self.assertEqual(self.pdf._financial_facts(1,mixed),[])

    def test_ambiguous_or_unbound_note_is_rejected(self):
        header='For the six months ended 30 June 2026\n2026 2025\n'
        for line in ['Revenue 4 333,284','Revenue 4(a) 4 333,284 287,537']:
            self.assertEqual(self.pdf._financial_facts(1,header+'Notes RMB’000 RMB’000\n'+line),[])
        self.assertEqual(self.pdf._financial_facts(1,header+'RMB’000 RMB’000\nRevenue 4(a) 333,284 287,537'),[])
        facts=self.pdf._financial_facts(1,header+'Notes RMB’000 RMB’000\nRevenue 4(a) 333,284 287,537')
        self.assertEqual(facts[0]['fields']['note_marker'],'4(a)')

    def test_legacy_prose_columns_cannot_invent_year(self):
        for header in ['Reporting period / Corresponding period of previous year / Change (%)','The Reporting Period / Same Period of the Previous Year / YoY Change (%)']:
            self.assertEqual(self.pdf._financial_facts(1,header+'\nUnit: RMB\nRevenue 100 90 11.1%'),[])

    def test_previous_values_and_inline_units_do_not_leak(self):
        header='For the six months ended 30 June 2026\n2026 2025\n'
        facts=self.pdf._financial_facts(1,header+'Unit: RMB\nRevenue 2025 2026\nUnit: USD\nGross profit 20 19')
        self.assertEqual(len(facts),2)
        self.assertTrue(all(f['fields']['columns']==['2026','2025'] for f in facts))
        facts=self.pdf._financial_facts(1,header+'Unit: RMB\nRevenue (USD) 100 90\nCost of sales 80 70')
        self.assertEqual(len(facts),1)
        self.assertEqual(facts[0]['fields']['label'],'Revenue')
