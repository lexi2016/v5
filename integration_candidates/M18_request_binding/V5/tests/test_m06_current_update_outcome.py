"""Write-after-replace fault evidence with real fixed owner and both ledgers."""
from datetime import timedelta
import os
import unittest
from unittest.mock import patch

import test_m06_native_pool_owner as support
from v5_shadow import m06_readonly, module_api, p0_hk_preselection as m06, run_ledger


class M06CurrentUpdateOutcomeTests(unittest.TestCase):
    setUp = support.M06NativePoolOwnerTests.setUp
    write_delivery = support.M06NativePoolOwnerTests.write_delivery
    evening = support.M06NativePoolOwnerTests.evening
    prepare = support.M06NativePoolOwnerTests.prepare
    tick = support.M06NativePoolOwnerTests.tick
    _sync_inventory = support.M06NativePoolOwnerTests._sync_inventory

    def write_after_replace_fault(self, kind):
        binding = m06._current_binding(self.config)
        self.assertIsNone(m06_readonly.read_current_success(binding))
        real_replace, real_fsync, real_read = os.replace, os.fsync, module_api._read_at
        observed = dict(replaced=False, faulted=False)

        def replace(*args, **kwargs):
            value = real_replace(*args, **kwargs)
            if args[1] == '.m06-current-success.json':observed['replaced'] = True
            return value

        def fsync(fd):
            if kind == 'directory_fsync' and observed['replaced'] and not observed['faulted']:
                observed['faulted'] = True
                raise OSError('SYNTHETIC_DIRECTORY_FSYNC_AFTER_REPLACE')
            return real_fsync(fd)

        def read_at(*args, **kwargs):
            if (kind == 'readback' and observed['replaced'] and not observed['faulted']
                    and args[2] == '.m06-current-success.json'):
                observed['faulted'] = True
                raise OSError('SYNTHETIC_READBACK_AFTER_REPLACE')
            return real_read(*args, **kwargs)

        with patch.object(m06, 'run_owner', wraps=m06.run_owner) as owner:
            with patch.object(os, 'replace', side_effect=replace), patch.object(os, 'fsync', side_effect=fsync), \
                    patch.object(module_api, '_read_at', side_effect=read_at):
                first = self.tick()['lanes'][0]
            self.assertEqual(observed, dict(replaced=True, faulted=True))
            self.assertEqual(first['status'], 'SUCCEEDED', first)
            # Real replace has committed a new pointer; it must not be labelled unchanged.
            pointer = m06_readonly.read_current_success(binding)
            self.assertIsNotNone(pointer)
            m06_readonly.validate_current_success(binding, pointer)
            state = first['state']
            self.assertEqual(pointer['p0_run_id'], state['latest_success']['run_id'])
            self.assertEqual(run_ledger.read_run(self.config['ledger_root'], state['identity']), state)
            product = state['latest_success']['product_reference']
            original = run_ledger.read_run(str(self.root/'output/.m06-ledger'), product['m06_computation_identity'])
            self.assertEqual(original['latest_success']['status'], 'SUCCEEDED')
            self.assertEqual(len(original['attempts']), 1)
            self.assertEqual(first['current_success']['status'], 'CURRENT_SUCCESS_UPDATE_OUTCOME_UNKNOWN')
            self.assertEqual(first['current_success']['action_required'],
                             'READ_ONLY_VERIFY_CURRENT_AND_BOTH_LEDGERS_NO_OWNER_RETRY')
            self.assertEqual(first['current_success']['reason'], 'OSError')
            self.now += timedelta(minutes=5)
            second = self.tick()['lanes'][0]
            self.assertEqual(second['status'], 'REUSED_SUCCESS', second)
            self.assertEqual(second['current_success']['status'], 'REUSED_CURRENT_SUCCESS')
            self.assertEqual(m06_readonly.read_current_success(binding), pointer)
            self.assertEqual(owner.call_count, 1)
            self.assertEqual(len(second['state']['attempts']), 1)

    def test_directory_fsync_failure_after_replace_is_unknown_without_owner_retry(self):
        self.write_after_replace_fault('directory_fsync')

    def test_readback_failure_after_replace_is_unknown_without_owner_retry(self):
        self.write_after_replace_fault('readback')


if __name__ == '__main__':unittest.main()
