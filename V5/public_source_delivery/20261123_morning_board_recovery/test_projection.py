import hashlib,json,tempfile,unittest
from pathlib import Path
import morning_projection as m

DAY='20261123'
BASE={'node_id':'morning-delivery','binding_status':'REPAIR_REQUIRED','runtime_status':'UNKNOWN','detail':'original'}
class Check(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def receipt(self,**change):
        a=dict(schema='BOARD_MORNING_CHECK_ONLY_V1',node_id='morning-delivery',
            business_date=DAY,observed_at='2026-11-23T08:11:51+08:00',
            missing=['TODAY_READY_CARD','OWNER_REGISTRATION','BOARD_READBACK'],
            business_started=False,formal_delivery=False,natural_verified=False)
        a.update(change); p=self.root/DAY/BASE['node_id']/'check-only.json'
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(a))
        return p
    def test_dated_check(self):
        a=BASE.copy();p=self.receipt();m.project(self.root,DAY,a)
        self.assertEqual(a['runtime_status'],'CHECK_BLOCKED_NOT_EXECUTED')
        self.assertIn('当日就绪卡',a['detail'])
        self.assertEqual(a['check_only']['sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertEqual(a['binding_status'],'REPAIR_REQUIRED')
    def test_never_override_existing_business(self):
        a=dict(BASE,runtime_status='SCHEDULE_OK')
        self.receipt();m.project(self.root,DAY,a);self.assertEqual(a['detail'],'original')
    def test_false_dispatch_and_bad_date(self):
        for d in [dict(business_started=True),dict(formal_delivery=True),
                  dict(natural_verified=True),dict(business_date='20261120'),
                  dict(observed_at='2026-11-23T08:09:59+08:00'),dict(missing=['untrusted_text'])]:
            with self.subTest(d=d):
                a=BASE.copy();self.receipt(**d);m.project(self.root,DAY,a)
                self.assertEqual(a,BASE)
    def test_opening_missing_is_not_projected_before_window(self):
        a=dict(BASE,node_id='opening-prep');m.project(self.root,DAY,a)
        self.assertEqual(a['runtime_status'],'UNKNOWN')
    def test_symlink_receipt_not_read(self):
        p=self.receipt();b=self.root/'copy';p.rename(b);p.symlink_to(b)
        a=BASE.copy();m.project(self.root,DAY,a);self.assertEqual(a,BASE)
    def test_registered_owner_receipts_not_recast(self):
        a=dict(BASE,node_id='a-auction',runtime_status='UNKNOWN')
        self.receipt();m.project(self.root,DAY,a);self.assertEqual(a['runtime_status'],'UNKNOWN')
if __name__=='__main__':unittest.main()
