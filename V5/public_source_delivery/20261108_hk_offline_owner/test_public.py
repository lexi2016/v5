import unittest
from unittest.mock import patch
import hk_close_owner_candidate as owner
class Tests(unittest.TestCase):
 def test_live_cas_hk16_block_before_read(self):
  with patch.object(owner,'verify_sources',side_effect=AssertionError('no source access')):
   for kw in ({},{'mode':'LIVE'},{'mode':'SYNTHETIC_ONLY','node':'CAS'},{'mode':'SYNTHETIC_ONLY','node':'HK16'}):
    r=owner.run_owner('20261109',**kw);self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['production_allowed'])
 def test_bad_date(self):
  with patch.object(owner,'verify_sources',side_effect=AssertionError('no source access')):
   for d in ('20261199','2026-11-09','bad'):
    with self.assertRaises(ValueError):owner.run_owner(d,mode='SYNTHETIC_ONLY')
 def test_missing_originals_fail(self):
  with self.assertRaises(FileNotFoundError):owner.run_owner('20261109',mode='SYNTHETIC_ONLY')
 def test_synthetic_provider_only(self):
  q=owner._SyntheticQuote('2026-11-09');status,frame=q.get_plate_stock('synthetic');rows=frame.to_dict('records')
  self.assertEqual(status,0);self.assertEqual(len(rows),600);self.assertTrue(all(r['stock_name']=='SYNTHETIC' for r in rows))
  s,f=q.get_market_snapshot(['HK.00001']);self.assertEqual(s,0);self.assertEqual(q.calls,1);self.assertEqual(f.to_dict('records')[0]['last_price'],10.001);q.close();self.assertTrue(q.closed)
if __name__=='__main__':unittest.main()
