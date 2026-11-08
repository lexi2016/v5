"""Synthetic registration fixtures; no real owner, market input or production send."""
import contextlib
import copy
import dataclasses
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import coordinator
import entrypoint as entry
from subset_plan import canonical, digest
import test_subset as fixtures


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.root = coordinator.initialize(self.home / 'fixed-owner')
        f = fixtures.Tests(); f.setUp()
        self.binding, self.evidence = f.b, f.e
        self.now = f.now
        self.calls, self.events = [], []
        self.guard_active = False
        self.fail_gate = False
        self.fail_executor = False
        self.partial_effect = False
        self.source = self.put('input.json', b'{"fixture":"synthetic-input"}')
        self.owner_source = self.put('owner_fixture.py', b'# synthetic owner dependency\n')
        self.success = self.put('success.bin', f.raw)
        self.outputs = {f.sha: self.success}
        original = {
            'date': self.binding['data_date'], 'node': 'owner',
            'input_refs': [self.source.as_dict()], 'code_refs': [self.owner_source.as_dict()],
            'argv': ['UNCHANGED_SYNTHETIC_OWNER'],
            'resources': {'fixture': 'original gate retained, no real resource approval'},
            'locks': ['UNCHANGED_SYNTHETIC_ORIGINAL_LOCK'],
            'source_date': self.binding['data_date'],
            'available_after': '2026-11-09T15:40:00+08:00',
        }
        original_pin = self.put('original-contract.json', canonical(original))
        self.binding['original_binding'] = {
            'contract_ref': original_pin.as_dict(),
            'identity': digest({'date': original['date'], 'node': 'owner',
                                'inputs': original['input_refs']}),
            **{k: original[k] for k in ('date', 'node', 'input_refs', 'code_refs',
                                       'argv', 'resources', 'locks')},
        }
        self.evidence['binding'] = copy.deepcopy(self.binding)
        self.contract = {
            'schema': 'REVIEWED_RETRY_SUBSET_ENTRY_V1',
            'owner_api': 'RETRY_SUBSET_OWNER_API_V1',
            'owner_identity': 'SYNTHETIC_OWNER',
            'environment_id': 'SYNTHETIC_ENV',
            'original_root': str(self.home),
            'binding': copy.deepcopy(self.binding),
            'ledger_root': str(self.root),
            'ledger_inode': list(self.inode(self.root)),
            'lock_inode': list(self.inode(self.root / 'OWNER.lock')),
            'dependencies': [self.pin(Path(entry.__file__)).as_dict(),
                             self.pin(Path(coordinator.__file__)).as_dict(),
                             self.pin(Path(coordinator.__file__).with_name('subset_plan.py')).as_dict(),
                             self.owner_source.as_dict()],
        }
        self.contract_pin = self.put('subset-contract.json', canonical(self.contract))
        self.approval = {'schema': 'RETRY_SUBSET_ENTRY_APPROVAL_V1',
                         'status': 'PASS_RETRY_SUBSET_ENTRY',
                         'reviewer_role': 'independent_reviewer',
                         'contract_ref': self.contract_pin.as_dict(),
                         'environment_id': 'SYNTHETIC_ENV',
                         'binding': copy.deepcopy(self.binding),
                         'test_fixture': True}
        self.approval_pin = self.put('approval.json', canonical(self.approval))
        self.review_pin = self.put('review-1.json', canonical(self.evidence))

        @contextlib.contextmanager
        def guard(binding):
            self.assertEqual(binding, self.binding['original_binding'])
            self.events.append('original_guard_enter')
            if self.fail_gate:
                raise RuntimeError('SYNTHETIC_ORIGINAL_RESOURCE_GATE')
            self.guard_active = True
            try:
                yield self.pulse
            finally:
                self.guard_active = False
                self.events.append('original_guard_exit')

        def execute_subset(symbols, context, pulse):
            self.assertTrue(self.guard_active)
            self.assertEqual(context['binding'], self.binding)
            self.assertEqual(context['owner_identity'], 'SYNTHETIC_OWNER')
            self.calls.append((symbols, copy.deepcopy(context)))
            pulse()
            if self.fail_executor:
                raise RuntimeError('SYNTHETIC_PARTIAL_EXECUTION')
            if self.partial_effect:
                (self.home / 'partial-effect.bin').write_bytes(b'not-a-terminal')
                raise RuntimeError('SYNTHETIC_PARTIAL_EXECUTION')
            return {symbol: None for symbol in symbols}

        self.hooks = entry.OwnerHooks('SYNTHETIC_OWNER', guard, execute_subset)
        self.registration = entry.ReviewedRun(
            run_id=self.binding['run_id'], environment_id='SYNTHETIC_ENV',
            contract_ref=self.contract_pin, approval_ref=self.approval_pin,
            reconciliation_refs={'retry-1610': self.review_pin, 'retry-1640': self.review_pin},
            success_output_refs=self.outputs, owner=self.hooks, clock=lambda: self.now,
        )

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def inode(path):
        s = path.stat(follow_symlinks=False)
        return s.st_dev, s.st_ino

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return entry.FilePin(str(path), len(raw), hashlib.sha256(raw).hexdigest())

    def put(self, name, raw):
        path = self.home / name
        path.write_bytes(raw)
        return self.pin(path)

    def pulse(self):
        self.assertTrue(self.guard_active)
        self.events.append('original_monitor_check')

    def dispatch(self, node='retry-1610', execute=True):
        with mock.patch.object(entry, 'TRUSTED_RUNS', (self.registration,)):
            return entry.dispatch(node, self.binding['run_id'], 'SYNTHETIC_ENV', execute=execute)

    def next_review(self, terminal, *, success=False, filename='review-2.json'):
        self.evidence['attempt_ids'].append(terminal['attempt_id'])
        self.evidence['last_attempt_id'] = terminal['attempt_id']
        self.evidence['stocks'][1]['attempt_id'] = terminal['attempt_id']
        self.evidence['ended_at'] = self.now.isoformat()
        if success:
            new = self.put('new-output.bin', b'new-verified-output')
            self.outputs[new.sha256] = new
            self.evidence['stocks'][1] = {'symbol': '600027.SH', 'status': 'SUCCESS',
                                         'attempt_id': terminal['attempt_id'],
                                         'output_sha256': new.sha256}
        pin = self.put(filename, canonical(self.evidence))
        self.registration = dataclasses.replace(self.registration,
            reconciliation_refs={'retry-1610': pin, 'retry-1640': pin})

    def test_no_registered_owner_blocks_without_any_read_or_write(self):
        with mock.patch.object(entry, 'TRUSTED_RUNS', ()), mock.patch.object(entry, '_read_pin', side_effect=AssertionError('must not read')):
            result = entry.dispatch('retry-1610', 'unknown', 'unknown', execute=True)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(result['reason'], 'NO_REVIEWED_SUBSET_BINDING')

    def test_read_only_default_does_not_claim_or_call_owner(self):
        result = self.dispatch(execute=False)
        self.assertEqual(result['status'], 'PLAN_ONLY_NOT_EXECUTED')
        self.assertEqual(result['plan']['retry_symbols'], ['600027.SH'])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.events, [])
        self.assertEqual(list(self.root.glob('day-*')), [])

    def test_failed_subset_uses_original_guard_and_attempt_identity(self):
        result = self.dispatch()
        self.assertEqual(result['status'], 'RETURNED_AWAIT_INDEPENDENT_RECONCILIATION')
        self.assertEqual([c[0] for c in self.calls], [('600027.SH',)])
        self.assertEqual(self.calls[0][1]['attempt_id'], result['attempt_id'])
        self.assertEqual(self.calls[0][1]['attempt_ordinal'], 2)
        self.assertEqual(self.events[0], 'original_guard_enter')
        self.assertEqual(self.events[-1], 'original_guard_exit')
        self.assertFalse(result['business_accepted'])
        self.assertFalse(result['natural_verified'])

    def test_same_evidence_never_reexecutes_unknown_claim(self):
        self.dispatch()
        result = self.dispatch()
        self.assertEqual(result['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(len(self.calls), 1)

    def test_two_slots_share_attempt_budget_and_final_success_reuses(self):
        first = self.dispatch()
        self.next_review(first)
        self.now += dt.timedelta(minutes=30)
        second = self.dispatch('retry-1640')
        self.assertEqual(self.calls[-1][1]['attempt_ordinal'], 3)
        self.next_review(second, success=True, filename='review-3.json')
        self.now += dt.timedelta(seconds=1)
        last = self.dispatch('retry-1640')
        self.assertEqual(last['status'], 'NO_RETRY_NEEDED')
        self.assertEqual(len(self.calls), 2)

    def test_input_change_blocks_before_original_guard(self):
        Path(self.source.path).write_bytes(b'changed-input')
        result = self.dispatch()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(self.events, [])

    def test_dependency_change_blocks_before_original_guard(self):
        Path(self.owner_source.path).write_bytes(b'changed-code')
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        self.assertEqual(self.events, [])

    def test_unknown_partial_review_never_invokes_owner(self):
        self.evidence['stocks'][1]['effects'] = 'PARTIAL'
        pin = self.put('partial-review.json', canonical(self.evidence))
        self.registration = dataclasses.replace(self.registration,
            reconciliation_refs={'retry-1610': pin, 'retry-1640': pin})
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        self.assertEqual(self.calls, [])

    def test_success_output_change_blocks(self):
        Path(self.success.path).write_bytes(b'changed-success')
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        self.assertEqual(self.calls, [])

    def test_missing_owner_hook_blocks(self):
        self.registration = dataclasses.replace(self.registration, owner=None)
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        self.assertEqual(list(self.root.glob('day-*')), [])

    def test_resource_rejection_is_preclaim_and_keeps_gate(self):
        self.fail_gate = True
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        self.assertEqual(list(self.root.glob('day-*')), [])
        self.assertEqual(self.calls, [])

    def test_owner_failure_preserves_unknown_and_partial_effect(self):
        self.partial_effect = True
        self.assertEqual(self.dispatch()['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertTrue((self.home / 'partial-effect.bin').exists())
        self.assertEqual(len(list(self.root.glob('day-*/CLAIM-2.json'))), 1)
        self.assertEqual(self.dispatch()['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(len(self.calls), 1)

    def test_registered_clock_is_used_no_request_clock_override(self):
        self.now = self.now.replace(tzinfo=None)
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        with self.assertRaises(TypeError):
            entry.dispatch('retry-1610', 'r', 'e', now=dt.datetime.now())

    def test_request_cannot_switch_state_directory(self):
        with self.assertRaises(TypeError):
            entry.dispatch('retry-1610', 'r', 'e', state_root=str(self.home / 'new'))

    def test_replaced_registered_root_cannot_reset_budget(self):
        self.dispatch()
        self.root.rename(self.home / 'archived-root')
        coordinator.initialize(self.root)
        result = self.dispatch()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('LEDGER_ROOT_IDENTITY', result['reason'])
        self.assertEqual(len(self.calls), 1)

    def test_foreign_environment_is_not_registered(self):
        with mock.patch.object(entry, 'TRUSTED_RUNS', (self.registration,)):
            result = entry.dispatch('retry-1610', self.binding['run_id'], 'other-env', execute=True)
        self.assertEqual(result['reason'], 'NO_REVIEWED_SUBSET_BINDING')

    def test_old_full_argv_review_cannot_authorize_subset(self):
        bad = self.put('old-dispatch-review.json', canonical({
            'status': 'PASS_DATED_DISPATCH', 'reviewer_role': 'independent_reviewer',
            'binding': self.binding['original_binding']}))
        self.registration = dataclasses.replace(self.registration, approval_ref=bad)
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        self.assertEqual(self.events, [])

    def test_symlink_evidence_is_refused(self):
        old = Path(self.review_pin.path)
        old.rename(self.home / 'real-review.json')
        old.symlink_to(self.home / 'real-review.json')
        self.assertEqual(self.dispatch()['status'], 'BLOCKED')
        self.assertEqual(self.calls, [])

    def test_sys_modules_cannot_substitute_subset_dependency(self):
        bogus = types.ModuleType('subset_plan')
        bogus.plan = lambda *a, **k: (_ for _ in ()).throw(AssertionError('foreign module'))
        with mock.patch.dict('sys.modules', {'subset_plan': bogus}):
            self.assertEqual(self.dispatch()['status'], 'RETURNED_AWAIT_INDEPENDENT_RECONCILIATION')

    def test_input_change_during_owner_stays_unknown(self):
        old = self.hooks.execute_subset
        def changed(symbols, context, pulse):
            value = old(symbols, context, pulse)
            Path(self.source.path).write_bytes(b'changed-during-work')
            return value
        self.registration = dataclasses.replace(self.registration,
            owner=dataclasses.replace(self.hooks, execute_subset=changed))
        result = self.dispatch()
        self.assertEqual(result['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(len(list(self.root.glob('day-*/CLAIM-2.json'))), 1)
        self.assertEqual(list(self.root.glob('day-*/RETURNED-*')), [])

    def test_dependency_loader_executes_the_verified_snapshot(self):
        folder = self.home / 'checked-code'
        folder.mkdir()
        names = ('entrypoint.py', 'subset_plan.py', 'coordinator.py')
        for name in names:
            (folder / name).write_bytes(Path(entry.__file__).with_name(name).read_bytes())
        target = folder / 'subset_plan.py'
        target.write_bytes(target.read_bytes() + b'\nSNAPSHOT_MARKER = "verified"\n')
        refs = [self.pin(folder / name).as_dict() for name in names]
        old = entry._read_pin
        def swap(value, original_root=None):
            raw = old(value, original_root)
            if entry._pin(value).path == str(folder / 'coordinator.py'):
                target.write_bytes(b'SNAPSHOT_MARKER = "reopened-unverified"\n')
            return raw
        with mock.patch.object(entry, 'HERE', folder), mock.patch.object(entry, '_read_pin', swap):
            plan_module, _ = entry._load_components(refs, self.home)
        self.assertEqual(plan_module.SNAPSHOT_MARKER, 'verified')

    def test_original_relative_pins_are_not_rewritten_to_new_identity(self):
        original = self.binding['original_binding']
        body = json.loads(Path(original['contract_ref']['path']).read_bytes())
        for key in ('input_refs', 'code_refs'):
            for ref in body[key]:
                ref['path'] = str(Path(ref['path']).relative_to(self.home))
            original[key] = copy.deepcopy(body[key])
        original['identity'] = digest({'date': body['date'], 'node': 'owner', 'inputs': body['input_refs']})
        ref = self.put('relative-original-contract.json', canonical(body)).as_dict()
        ref['path'] = 'relative-original-contract.json'
        original['contract_ref'] = ref
        self.evidence['binding'] = copy.deepcopy(self.binding)
        review = self.put('relative-review.json', canonical(self.evidence))
        self.contract['binding'] = copy.deepcopy(self.binding)
        contract = self.put('relative-subset-contract.json', canonical(self.contract))
        self.approval.update(contract_ref=contract.as_dict(), binding=copy.deepcopy(self.binding))
        approval = self.put('relative-approval.json', canonical(self.approval))
        self.registration = dataclasses.replace(self.registration, contract_ref=contract,
            approval_ref=approval, reconciliation_refs={'retry-1610': review, 'retry-1640': review})
        result = self.dispatch()
        self.assertEqual(result['status'], 'RETURNED_AWAIT_INDEPENDENT_RECONCILIATION')
        self.assertEqual(self.calls[0][1]['binding']['original_binding']['contract_ref']['path'],
                         'relative-original-contract.json')

    def test_version_change_cannot_obtain_new_same_day_budget(self):
        self.dispatch()
        self.binding['input_version'] = 'synthetic-new-version'
        self.evidence['binding'] = copy.deepcopy(self.binding)
        review = self.put('changed-version-review.json', canonical(self.evidence))
        self.contract['binding'] = copy.deepcopy(self.binding)
        contract = self.put('changed-version-contract.json', canonical(self.contract))
        self.approval.update(contract_ref=contract.as_dict(), binding=copy.deepcopy(self.binding))
        approval = self.put('changed-version-approval.json', canonical(self.approval))
        self.registration = dataclasses.replace(self.registration, contract_ref=contract,
            approval_ref=approval, reconciliation_refs={'retry-1610': review, 'retry-1640': review})
        result = self.dispatch()
        self.assertEqual(result['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertIn('SAME_DATE_IDENTITY_CONFLICT', result['reason'])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(list(self.root.glob('day-*/CLAIM-*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
