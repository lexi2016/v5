import unittest,json,hashlib
from pathlib import Path
class Mapping(unittest.TestCase):
 def test_full_contract_and_pins(self):
  root=Path(__file__).parent;m=json.loads((root/'FULL_TIMELINE_MAP.json').read_text());self.assertEqual(len(m['nodes']),21);self.assertEqual(len({r['node'] for r in m['nodes']}),21);self.assertFalse(m['all_nodes_implemented']);self.assertFalse(m['natural_verified'])
  for row in m['nodes']:
   self.assertEqual(row['natural_acceptance'],'UNKNOWN')
   for ref in row['exported_candidate_sources']:
    self.assertEqual(hashlib.sha256((root/ref['path']).read_bytes()).hexdigest(),ref['sha256'])
   for ref in row['historical_github_sources']:
    self.assertTrue(ref['url'].startswith(('https://github.com/lexi2016/v5/blob/01d93717905813705732161d4d79062ae5af2d99/','https://github.com/lexi2016/perfect-chart-research-panel/blob/3c9a53b54d3a382efa416fe5eddb74c17db92d8c/')))
class RecurringMapping(unittest.TestCase):
 def test_both_recurring_obligations_explicit_not_implemented(self):
  root=Path(__file__).parent;m=json.loads((root/'FULL_TIMELINE_MAP.json').read_text());rows=m['cross_cutting_recurring_items']
  self.assertEqual({r['id'] for r in rows},{'intraday_10min','hourly_backup'})
  self.assertEqual(len(rows),2)
  for row in rows:
   self.assertEqual(row['implementation_in_this_export'],'NOT_IMPLEMENTED')
   self.assertEqual(row['current_execution'],'UNKNOWN')
   self.assertEqual(row['manual_business_test'],'NOT_RUN')
   self.assertEqual(row['natural_acceptance'],'UNKNOWN')
   self.assertEqual(row['scheduler_change'],'NONE')
if __name__=='__main__':unittest.main()
