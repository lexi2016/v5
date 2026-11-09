"""No local file or self-described approval may create a production freeze head."""
import unittest
from unittest.mock import patch, Mock

import registered as r
from test_freeze_lineage import fixture


class AuthorityBoundary(unittest.TestCase):
    def test_production_dispatch_refuses_before_reads_owner_claims_or_writes(self):
        guard = Mock(side_effect=AssertionError('owner must not be entered'))
        gate = Mock(side_effect=AssertionError('job must not start'))
        reg = {'node': 'freeze', 'run_id': 'SYNTHETIC_PROBE', 'environment_id': 'ISOLATED',
               'domain': 'production', 'owner_guard_factory': guard,
               'chain_authority': {'approved': True, 'head': None, 'file': 'not-authority.json'}}
        with patch.object(r, 'TRUSTED_RUNS', (reg,)), patch.object(r, 'module', side_effect=AssertionError('no IO')) as module:
            result = r.dispatch('freeze', 'SYNTHETIC_PROBE', 'ISOLATED', gate)
        self.assertEqual(result['status'], 'BLOCKED_FREEZE_AUTHORITY_NOT_BOUND')
        self.assertEqual(result['jobs_started'], 0)
        self.assertFalse(result['formal_freeze'])
        self.assertFalse(result['natural_verified'])
        module.assert_not_called()
        guard.assert_not_called()
        gate.assert_not_called()

    def test_direct_production_calculation_refuses_without_lineage(self):
        with patch.object(r, 'module', side_effect=AssertionError('no IO')):
            result = r.calculate({'node': 'freeze', 'domain': 'production'}, {}, {}, None)
        self.assertEqual(result['status'], 'BLOCKED_FREEZE_AUTHORITY_NOT_BOUND')
        self.assertNotIn('lineage', result)
        self.assertFalse(result['formal_freeze'])

    def test_pure_lineage_does_not_accept_production_or_implicit_domain(self):
        for domain in ('production', None):
            reg, policy, docs = fixture()
            if domain is None:
                reg.pop('domain', None)
            else:
                reg['domain'] = domain
            with self.assertRaisesRegex(ValueError, '^FREEZE_LINEAGE_SYNTHETIC_ONLY$'):
                r.build_freeze_lineage(reg, policy, docs)


if __name__ == '__main__':
    unittest.main()
