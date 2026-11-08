import copy
import types
import unittest
from unittest.mock import patch
import registered as module


class MorningGuardTests(unittest.TestCase):
    def setUp(self):
        self.reg = {'node':'jk-verify','source_date':'20261109','business_date':'20261109','cutoff':'2026-11-09T08:10:00+08:00'}
        self.policy = {'required_comparisons':[{'symbol':'X','field':'open','source_ids':['S1','S2']}], 'max_observation_age_seconds':600}
        self.doc = {'records':[{'symbol':'X','field':'open','source_id':s,'observed_at':'2026-11-09T08:05:00+08:00','available_at':'2026-11-09T08:06:00+08:00'} for s in ('S1','S2')]}

        self.policy['provider_catalog']={s:{'independence_group':s,'allowed_urls':['https://'+s.lower()+'.example.invalid/quote']} for s in ('S1','S2')}
        self.policy['required_comparisons'][0]['semantic_contract']={'unit':'index_points','basis':'unadjusted','currency':'JPY','raw_fields':{s:['open'] for s in ('S1','S2')}}
        for row in self.doc['records']:row.update(id='observation-'+row['source_id'],url=self.policy['provider_catalog'][row['source_id']]['allowed_urls'][0],unit='index_points',basis='unadjusted',currency='JPY',value='1')

    def validate(self):
        return module.validate_jk_observations(self.doc,self.policy,module.time(self.reg['cutoff']))

    def test_valid_policy_and_cutoff(self):
        self.assertTrue(self.validate()['per_record_cutoff_checked'])

    def test_empty_scope_rejected(self):
        self.policy['required_comparisons']=[];self.doc['records']=[]
        with self.assertRaises(ValueError):self.validate()

    def test_single_source_rejected(self):
        self.doc['records'].pop()
        with self.assertRaises(ValueError):self.validate()

    def test_unknown_or_duplicate_source_rejected(self):
        for source in ('S1','other'):
            with self.subTest(source=source):
                self.doc['records'][1]['source_id']=source
                with self.assertRaises(ValueError):self.validate()

    def test_future_and_naive_and_stale_rejected(self):
        for field,value in [('available_at','2026-11-09T08:11:00+08:00'),('available_at','2026-11-09T08:06:00'),('observed_at','2026-11-09T07:00:00+08:00')]:
            with self.subTest(value=value):
                prior=self.doc['records'][0][field];self.doc['records'][0][field]=value
                with self.assertRaises(ValueError):self.validate()
                self.doc['records'][0][field]=prior

    def test_missing_freshness_policy_rejected(self):
        del self.policy['max_observation_age_seconds']
        with self.assertRaises(ValueError):self.validate()

    def test_invalid_input_never_reaches_reconcile(self):
        self.doc['records']=[]
        with patch.object(module,'module') as loader:
            with self.assertRaises(ValueError):module.calculate(self.reg,self.policy,{'observations':self.doc},None)
            loader.assert_not_called()

    def test_valid_calculate_calls_reconcile_and_keeps_admission_false(self):
        reconcile=unittest.mock.Mock(return_value={'comparisons':[{'symbol':'X','field':'open','status':'OBSERVED_VALUES_AGREE'}]})
        with patch.object(module,'module',return_value=types.SimpleNamespace(reconcile=reconcile)):
            result=module.calculate(self.reg,self.policy,{'observations':self.doc},None)
        self.assertEqual(result['status'],'RECONCILED');self.assertFalse(result['source_admission']);reconcile.assert_called_once()

    def test_0810_cannot_fall_through_to_list_prompt(self):
        with patch.object(module,'module') as loader:
            result=module.calculate({'node':'morning-delivery'},{},{},None)
        self.assertEqual(result['status'],'BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND')
        self.assertEqual(result['delivery_status'],'NOT_SENT');self.assertFalse(result['business_accepted']);loader.assert_not_called()

    def test_registry_remains_empty(self):
        self.assertEqual(module.TRUSTED_RUNS,())


if __name__=='__main__':unittest.main()
