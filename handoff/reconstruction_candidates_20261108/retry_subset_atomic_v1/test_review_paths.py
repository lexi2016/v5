"""Independent regressions: directory and lock identity must not be reset."""
import copy,datetime as dt,hashlib,unittest
from coordinator import Coordinator
from subset_plan import canonical
from test_atomic import AtomicTests

class ReviewPaths(AtomicTests):
 def test_review_moved_day_does_not_reset(self):
  self.run_case()
  (self.root/('day-'+self.b['data_date'])).rename(self.root/'archived-day')
  with self.assertRaises((ValueError,OSError)):self.run_case()
  self.assertEqual(len(self.calls),1)
 def test_review_moved_lock_does_not_split(self):
  second=[]
  def fake(symbols):
   (self.root/'OWNER.lock').rename(self.root/'old-owner-lock')
   b=copy.deepcopy(self.b);b['data_date']='20261110';b['original_binding']['date']='20261110'
   e=copy.deepcopy(self.e);e['binding']=b;e['ended_at']='2026-11-10T15:40:00+08:00';raw=canonical(e)
   c=Coordinator(self.root)
   try:
    with self.assertRaises((ValueError,OSError)):
     c.execute(b,raw,hashlib.sha256(raw).hexdigest(),self.outputs,'retry-1610',dt.datetime.fromisoformat('2026-11-10T16:10:00+08:00'),lambda ss:(second.append(True) or {s:None for s in ss}))
   finally:c.close()
   return {s:None for s in symbols}
  try:self.run_case(fake)
  except (ValueError,OSError):pass # first owner should also notice replacement
  self.assertEqual(second,[])

if __name__=='__main__':unittest.main()
