"""Mac extraction snippets; preserve raw text and independently pin its bytes."""
from hashlib import sha256
import importlib,json
from pathlib import Path
import unittest
from v5_shadow.manager_loader import load_owner
from v5_shadow.m16_runtime import closure

class PdfSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_owner(closure());cls.pdf=importlib.import_module('m16_owner_manager_research.pdf_parser')
        cls.path=Path(__file__).parent/'fixtures/real_pdf_semantics.json'
        cls.rows=json.loads(cls.path.read_text())

    def test_original_snippet_file_hash(self):
        self.assertEqual(sha256(self.path.read_bytes()).hexdigest(),'ca84fb8902795bf2e6f15d351ac5c94e490c122f3cd43726ef164bfc4e3eeb96')

    def test_year_evidence_and_complete_comparison_header(self):
        facts=self.pdf._financial_facts(5,self.rows[0]['text'])
        self.assertEqual(len(facts),1);fact=facts[0]
        for field in ('period_label',): self.assertIn('2026 Interim Report',fact['fields'][field])
        self.assertIn('2026 Interim Report',fact['source_excerpt'])
        full='Increase/Decrease in This Reporting Period over the Same Period of Last Year'
        self.assertEqual(fact['fields']['columns'][2],full)
        self.assertIn(full,fact['source_excerpt'])
        self.assertEqual(fact['fields']['values'][2]['raw'],'14.48%')
        self.assertEqual(self.pdf._financial_facts(5,self.rows[0]['text'].replace('Dajin Heavy Industry Co., Ltd. 2026 Interim Report\n','')),[])

    def test_full_wrapped_metric_keeps_gain_loss_and_assets(self):
        lines=self.rows[1]['text'].splitlines()
        for index,expected,amount in [(5,'Net unrealised gain on financial asset and financial liabilities measured at fair value through profit or loss','189,943 939,951'),(11,'Net realised loss on fair value through other comprehensive income and amortised cost debt securities','(138,828) (13,880)')]:
            match,span=self.pdf._row_match(lines,index)
            self.assertIsNotNone(match)
            self.assertTrue(match.group('label').startswith(expected))
            self.assertEqual(match.group('values'),amount)
            self.assertEqual(span,6)
            self.assertEqual(' '.join(lines[index-span+1:index+1]),' '.join(lines[index-5:index+1]))

    def test_truncated_continuation_is_not_a_metric(self):
        lines=self.rows[1]['text'].splitlines()
        self.assertIsNone(self.pdf._row_match(lines[2:6],3)[0])
        self.assertIsNone(self.pdf._row_match(['General information',*lines[2:6]],4)[0])
        self.assertIsNone(self.pdf._row_match(lines[8:12],3)[0])
        # Synthetic separating row must prevent crossing to an older label.
        self.assertIsNone(self.pdf._row_match(['Net unrealised gain','Revenue 10 9',*lines[2:6]],5)[0])

    def test_wrapped_row_excerpt_keeps_the_full_raw_label(self):
        # Only the label fragment is original. This header is explicitly synthetic
        # because the Mac supplied no original page-94 header in this fixture.
        text='For the six months ended 30 June 2026\n2026 2025\nHK$’000 HK$’000\n'+self.rows[1]['text']
        facts=self.pdf._financial_facts(94,text)
        self.assertEqual(len(facts),2)
        raw=self.rows[1]['text'].splitlines()
        for fact,start in zip(facts,(0,6)):
            self.assertIn(' '.join(raw[start:start+6]),fact['source_excerpt'])
            self.assertTrue(fact['fields']['label'].startswith('Net '))
