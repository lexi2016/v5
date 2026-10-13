"""Preparation is read-only; synthetic files never establish live acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_manager_plan as adapter_tests
from v5_shadow.manager_plan import run_manager_plan
from v5_shadow import manager_request_preparation as prep


class PreparationTests(adapter_tests.ManagerPlanAdapterTests):
    # Do not duplicate the inherited adapter regression cases.
    def test_missing_sources_keep_waiting_without_request_or_writes(self):
        before = self.files()
        value = prep.prepare(self.request)
        self.assertEqual(value['status'], 'WAITING_SOURCES')
        self.assertIsNone(value['manager_request'])
        self.assertIsNone(value['manager_template'])
        self.assertEqual(set(value['lanes']), {'announcement', 'rebound', 'us_mapping'})
        self.assertEqual(self.files(), before)
        self.assertFalse(value['natural_verified'])

    def test_original_not_run_daily_without_artifact_sha_waits(self):
        self.request['inputs']['manager']['files'] = {}
        original = run_manager_plan(self.request)['payload']
        daily = original['us_mapping_research']['daily_run']
        self.assertEqual(daily['status'], 'NOT_RUN')
        self.assertNotIn('artifact_sha256', daily)
        before = self.files()
        value = prep.prepare(self.request)
        self.assertEqual(value['status'], 'WAITING_SOURCES')
        self.assertIsNone(value['source_references']['us_mapping'])
        self.assertIsNone(value['manager_request'])
        self.assertIsNone(value['manager_template'])
        self.assertFalse(value['lanes']['us_mapping']['accepted'])
        self.assertEqual(value['lanes']['us_mapping']['daily_status'], 'NOT_RUN')
        self.assertEqual(self.files(), before)

    def test_partial_daily_identity_fields_fail_closed_without_crash(self):
        original = run_manager_plan(self.request)
        for key in ('target_trade_date', 'run_id', 'artifact_sha256', 'status', 'matches'):
            with self.subTest(missing=key):
                result = copy.deepcopy(original)
                result['payload']['us_mapping_research']['daily_run'].pop(key, None)
                with patch.object(prep, 'run_manager_plan', return_value=result):
                    value = prep.prepare(self.request)
                self.assertEqual(value['status'], 'WAITING_SOURCES')
                self.assertIsNone(value['source_references']['us_mapping'])
                self.assertIsNone(value['manager_template'])
                self.assertIsNone(value['manager_request'])

    def test_bad_sha_rejected_before_owner_read(self):
        key = next(iter(self.request['inputs']['manager']['files']))
        self.request['inputs']['manager']['files'][key] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'SHA'):
            prep.prepare(self.request)

    def test_template_uses_explicit_target_and_preserves_dates(self):
        spec = copy.deepcopy(self.request)
        for key in ('action', 'view', 'selection_date', 'announcement_date'):
            del spec[key]
        value = prep.template(spec)
        self.assertEqual(value['target_date'], '20261008')
        self.assertEqual(value['now'], self.request['now'])
        self.assertEqual(value['inputs'], self.request['inputs'])
        self.assertEqual(value['action'], 'read')

    def test_refresh_input_is_not_executed(self):
        self.request['action'] = 'refresh'
        before = self.files()
        prep.prepare(self.request)
        self.assertEqual(self.files(), before)

    def test_saved_manager_cold_binding_is_same_run(self):
        result = run_manager_plan(dict(self.request, action='refresh'))
        expected = {key: result['readback'][key] for key in ('run_id', 'plan_sha256')}
        before = self.files()
        value = prep.bind_saved(self.request, expected)
        self.assertEqual(value['saved_reference'], expected)
        self.assertEqual(value['status'], 'SAVED_READBACK_MATCHED')
        self.assertEqual(self.files(), before)
        self.assertFalse(value['three_lane_accepted'])
        with self.assertRaisesRegex(ValueError, 'SAME_RUN'):
            prep.bind_saved(self.request, dict(expected, run_id='f' * 32))

    def test_fresh_preparation_does_not_reuse_saved_plan_as_admission(self):
        run_manager_plan(dict(self.request, action='refresh'))
        before = self.files()
        value = prep.prepare(self.request)
        self.assertEqual(value['status'], 'WAITING_SOURCES')
        self.assertEqual(self.files(), before)

    def test_cli_is_read_only_and_waiting_has_nonzero_exit(self):
        path = self.root / 'spec.json'
        path.write_text(json.dumps(self.request))
        before = self.files()
        tool = Path(prep.__file__).resolve()
        result = subprocess.run([sys.executable, '-I', '-B', str(tool), '--request', str(path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'WAITING_SOURCES')
        self.assertEqual(self.files(), before)


# Reuse setup/helpers, not inherited tests (the original suite runs separately).
for name in list(vars(adapter_tests.ManagerPlanAdapterTests)):
    if name.startswith('test_') and name not in vars(PreparationTests):
        setattr(PreparationTests, name, None)


class AdmissionProjectionTests(unittest.TestCase):
    def payload(self):
        return dict(target_trade_date='20261014', plan_context=dict(plan_trade_date='20261014',
            market_session='20261013', research_cutoff='2026-10-14T08:45:00+08:00'),
            announcement_reviewed_analysis=dict(status='READY_EMPTY', products=[dict(
                status='CONSUMED', consumed=True, target_trade_date='20261014', product_sha256='a'*64)],
                consumed_product_sha256s=['a'*64], research_references=[], gaps=[]),
            market_screen=dict(status='READY', main_screen_ready=True, target_trade_date='20261014',
                verified_session='20261013', input_identity='b'*64, pending=[], strict=[], near=[], gaps=[]),
            us_mapping_research=dict(daily_run=dict(target_trade_date='20261014',run_id='c'*32,
                artifact_sha256='d'*64,status='VALID_EMPTY',matches=[])),
            owner_chain=dict(us_mapping_daily_plan_reference=dict(status='CONSUMED',target_trade_date='20261014',
                run_id='c'*32,artifact_sha256='d'*64)))

    def test_original_accepted_empty_is_not_missing(self):
        lanes=prep.lane_readiness(self.payload(), '20261014')
        self.assertTrue(all(row['accepted'] for row in lanes.values()))

    def test_pending_rebound_is_never_valid_empty(self):
        p=self.payload();p['market_screen'].update(status='READY_WITH_GAPS',pending=[{'code':'00001'}])
        self.assertFalse(prep.lane_readiness(p,'20261014')['rebound']['accepted'])

    def test_cross_date_and_mismatched_run_remain_waiting(self):
        for key in ('announcement','rebound','us_mapping'):
            p=self.payload()
            if key=='announcement':p['announcement_reviewed_analysis']['products'][0]['target_trade_date']='20261012'
            elif key=='rebound':p['market_screen']['target_trade_date']='20261012'
            else:p['owner_chain']['us_mapping_daily_plan_reference']['run_id']='e'*32
            self.assertFalse(prep.lane_readiness(p,'20261014')[key]['accepted'])

    def test_valid_empty_with_rows_is_not_accepted(self):
        p=self.payload();p['us_mapping_research']['daily_run']['matches']=[{'symbol':'X'}]
        self.assertFalse(prep.lane_readiness(p,'20261014')['us_mapping']['accepted'])

    def test_missing_fields_fail_closed(self):
        self.assertFalse(any(x['accepted'] for x in prep.lane_readiness({},'20261014').values()))
