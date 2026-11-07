import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import hk_close_owner_candidate as owner

class OfflineOwner(unittest.TestCase):
    def test_default_live_and_cas_block_before_source(self):
        with patch.object(owner, 'verify_sources', side_effect=AssertionError('must not load')):
            for kwargs in ({}, {'mode':'LIVE'}, {'mode':'SYNTHETIC_ONLY','node':'CAS'}, {'mode':'SYNTHETIC_ONLY','node':'HK16'}):
                self.assertEqual(owner.run_owner('20261106', **kwargs)['status'], 'BLOCKED')
    def test_two_dates_original_store_rank_and_reuse(self):
        for day in ('20261106', '20261109'):
            r = owner.run_owner(day, mode='SYNTHETIC_ONLY')
            self.assertEqual(r['trade_date'], day)
            self.assertEqual(r['calls'], 3)
            self.assertEqual(r['second_publication'], 'IDEMPOTENT_REUSE')
            self.assertEqual(r['row_counts']['hkconnect_universe'], 600)
            self.assertEqual(r['top20_codes'][0], 'HK.00600')
            self.assertIsNone(r['models']['0.2_prob_active']['hit_count'])
            self.assertTrue(r['context_closed'])
            self.assertFalse(r['production_allowed'])
            self.assertEqual(r['actual_cas_terminal_event'], 'UNKNOWN')
    def test_changed_source_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / 'recovery'
            shutil.copytree(owner.RECOVERY, copy)
            changed = copy / 'original/domains/close_review.py'
            changed.write_bytes(changed.read_bytes() + b'\n# synthetic corruption test\n')
            with patch.object(owner, 'RECOVERY', copy), patch.dict(owner.sys.modules, {name:None for name in list(owner.sys.modules) if name.startswith(('contracts', 'infrastructure', 'domains'))}):
                with self.assertRaisesRegex(ValueError, 'INTEGRITY'):
                    owner.run_owner('20261106', mode='SYNTHETIC_ONLY')
    def test_foreign_loaded_module_rejected(self):
        import types
        fake = types.SimpleNamespace(__file__='/tmp/not_original.py')
        with patch.dict(owner.sys.modules, {'domains.close_review':fake}):
            with self.assertRaisesRegex(ValueError, 'ORIGIN_MISMATCH'):
                owner.run_owner('20261106', mode='SYNTHETIC_ONLY')
    def test_bad_date_rejected(self):
        for day in ('20261199','2026-11-06','2026116'):
            with self.assertRaises(ValueError): owner.run_owner(day, mode='SYNTHETIC_ONLY')
if __name__ == '__main__': unittest.main()
