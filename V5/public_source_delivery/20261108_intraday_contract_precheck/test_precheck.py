import json, unittest
from precheck import precheck, sha

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.source = b'SYNTHETIC_NOT_REAL_SOURCE\n'
        self.c = dict(source_date='2030-01-04', observation_date='2030-01-07',
            purpose='CURRENT_NUMERIC_CANDIDATE_OBSERVATION_ONLY', source_path='SYNTHETIC.csv',
            source_sha256=sha(self.source), generation='0'*64, input_identity='1'*64,
            count=2, symbols=['000001.SZ','600000.SH'], keys=['sz000001','sh600000'],
            carry_forward=False, formula_or_chart_admission=False,
            no_HK_scope_assumed=True, missing_daily_selection='BLOCKED_SCOPE')
    def invoke(self, **kwargs):
        b=json.dumps(self.c).encode()
        args=dict(contract_bytes=b, expected_contract_sha256=sha(b), source_bytes=self.source,
                  expected_source_date='2030-01-04', expected_observation_date='2030-01-07')
        args.update(kwargs)
        return precheck(**args)
    def test_synthetic_only(self):
        r=self.invoke();self.assertFalse(r['approved_for_capture']);self.assertEqual(r['count'],2)
        self.assertIn('source_csv_schema_and_scope_equality',r['unverified'])
    def test_future_expected_date(self):
        with self.assertRaisesRegex(ValueError,'DATE_BINDING'): self.invoke(expected_observation_date='2030-01-08')
    def test_stale_source_date(self):
        self.c['source_date']='2030-01-03'
        with self.assertRaisesRegex(ValueError,'DATE_BINDING'):self.invoke()
    def test_changed_bytes(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_SHA_MISMATCH'):self.invoke(source_bytes=b'changed')
    def test_changed_contract(self):
        with self.assertRaisesRegex(ValueError,'CONTRACT_SHA_MISMATCH'):self.invoke(expected_contract_sha256='f'*64)
    def test_absent_bytes(self):
        with self.assertRaisesRegex(ValueError,'MISSING_BYTES'):self.invoke(source_bytes=None)
    def test_count_mismatch(self):
        self.c['count']=247
        with self.assertRaisesRegex(ValueError,'COUNT'):self.invoke()
    def test_duplicate(self):
        self.c['symbols']=['000001.SZ']*2
        with self.assertRaisesRegex(ValueError,'DUPLICATE_SCOPE'):self.invoke()
    def test_key_mismatch(self):
        self.c['keys'].reverse()
        with self.assertRaisesRegex(ValueError,'KEY_BINDING'):self.invoke()
    def test_no_admission(self):
        self.c['formula_or_chart_admission']=True
        with self.assertRaisesRegex(ValueError,'SCOPE_SAFETY_FLAGS'):self.invoke()
    def test_missing_binding(self):
        del self.c['generation']
        with self.assertRaisesRegex(ValueError,'MISSING_generation'):self.invoke()
    def test_unicode_identity_rejected(self):
        self.c['symbols'][0]='０００００１.SZ'
        self.c['keys'][0]='sz０００００１'
        with self.assertRaisesRegex(ValueError,'IDENTITY'):self.invoke()
    def test_no_hk_expansion(self):
        self.c['symbols'][0]='00700.HK'
        with self.assertRaisesRegex(ValueError,'IDENTITY'):self.invoke()
if __name__=='__main__':unittest.main()
