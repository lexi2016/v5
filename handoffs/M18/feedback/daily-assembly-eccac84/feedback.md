# eccac84 daily assembly: isolated contract failure

New user-authorized feedback from the Mac isolated test. No product or original test was edited to repair this failure. This report does not decide whether backward compatibility or the new owner contract should change; the original Chat must resolve that contract.

## Fixed source identities

- Repository: private lexi2016/v5; branch: dev/m18-daily-assembly-20261012.
- Candidate commit: eccac84d0003a0dfd2e4bba3294dd4c74c942c91.
- Candidate file: V5/src/v5_shadow/daily_manager_assembly.py.
- Candidate: 10996 bytes; SHA256 5ee63f0bb94f2a85e2c8e8325a9ed8cf6460ff7f17a192c38edf8b2ad2dde251; Git blob 34d24f9fe7b4a6847a854f18b639930c443483d5.
- Local fixed dependency baseline: 6900d8982b2542e67a37fa4da5608bbbf94d5abf (the previously successful v2 baseline). Sparse candidate branch supplies only this product file; all dependencies and original tests come from the local baseline.
- Only the candidate product file differs in the isolated worktree; 794 baseline files stayed unchanged.

## Commands and actual execution

Commands below preserve the actual argv with the local absolute interpreter path replaced by a relative path. They were launched from the workspace root. No tests were rerun for this feedback upload.

```sh
../../2026-10-11/task/m13-isolated/venv/bin/python -I -B m18-daily-assembly-evidence/run_tests.py test_daily_manager_assembly
../../2026-10-11/task/m13-isolated/venv/bin/python -I -B m18-daily-assembly-evidence/run_tests.py test_daily_candidate_contracts
```

- Original suite: UTC 2026-10-12T01:10:55.740898+00:00 through 01:10:55.811005+00:00; exit 1; 8 methods = 7 PASS + 1 ERROR (0 assertion failures).
- Eight targeted contract classes: UTC 2026-10-12T01:11:16.375164+00:00 through 01:11:16.431871+00:00; exit 0; 8 methods = 8 PASS.
- Targeted coverage: fixed announcement binding retained; native_master/archives deep copy; rebound_owner research reference retained; four-argument signature; conflicting announcement binding rejected; wrong identity rejected; changed source bytes rejected/sealed cutoff stable; no qualification promotion.
- One prior accidental module-name collision ran nine unrelated baseline `test_contracts` methods; excluded from both acceptance groups. Correct targeted module was then run once.
- Fixture clock 2026-10-09 is synthetic test data, distinct from the actual execution timestamps above.
- Real producer runs: 0. Real manager runs: 0. Scheduler installations: 0. Existing preview updates: 0.

## Complete original test log and error stack (paths redacted)

```text
test_closed_execution_window_can_read_existing_ledger_without_claim (test_daily_manager_assembly.DailyManagerAssemblyTests.test_closed_execution_window_can_read_existing_ledger_without_claim) ... ok
test_missing_real_revision_inputs_do_not_invoke_model_or_owner (test_daily_manager_assembly.DailyManagerAssemblyTests.test_missing_real_revision_inputs_do_not_invoke_model_or_owner) ... ok
test_new_defaults_are_explicit_hk_slots_not_legacy_claim (test_daily_manager_assembly.DailyManagerAssemblyTests.test_new_defaults_are_explicit_hk_slots_not_legacy_claim) ... ok
test_rebound_reference_and_new_revision_binding_assembled (test_daily_manager_assembly.DailyManagerAssemblyTests.test_rebound_reference_and_new_revision_binding_assembled) ... ERROR
test_revision_capsule_is_exact_fixed_assembly (test_daily_manager_assembly.DailyManagerAssemblyTests.test_revision_capsule_is_exact_fixed_assembly) ... ok
test_sealed_real_cutoff_reused_not_new_plan_every_tick (test_daily_manager_assembly.DailyManagerAssemblyTests.test_sealed_real_cutoff_reused_not_new_plan_every_tick) ... ok
test_stale_template_us_and_observation_not_silently_reused (test_daily_manager_assembly.DailyManagerAssemblyTests.test_stale_template_us_and_observation_not_silently_reused) ... ok
test_us_exact_run_bytes_copied_and_changed_pointer_rejected (test_daily_manager_assembly.DailyManagerAssemblyTests.test_us_exact_run_bytes_copied_and_changed_pointer_rejected) ... ok

======================================================================
ERROR: test_rebound_reference_and_new_revision_binding_assembled (test_daily_manager_assembly.DailyManagerAssemblyTests.test_rebound_reference_and_new_revision_binding_assembled)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "V5/tests/test_daily_manager_assembly.py", line 46, in test_rebound_reference_and_new_revision_binding_assembled
    self.assertEqual(result['rebound_observation']['reference'],reference)
                     ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
KeyError: 'rebound_observation'

----------------------------------------------------------------------
Ran 8 tests in 0.024s

FAILED (errors=1)
```

## Original failing test source and fixture setup

Source copied verbatim from the fixed local baseline's `V5/tests/test_daily_manager_assembly.py`. The embedded whole source establishes fixture setup and the original expectation without relying on a remote file that is absent from the sparse branch.

```python
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import unittest
from daily_ledger_fixture import make_ledger_fixture
from v5_shadow.daily_manager_assembly import assemble_manager_request
from v5_shadow.daily_tick import default_slots
from v5_shadow.daily_announcement_revision import run_revision
from v5_shadow.announcement_offline_reader import sources,REVISION_APP,REVISION_PIN
from v5_shadow.run_ledger import claim_run,finish_run,read_run
from v5_shadow.digests import sha256_json,canonical_bytes


class DailyManagerAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=make_ledger_fixture(self.addCleanup)
        self.registration={k:self.fixture.identity[k] for k in ('code_sha256','config_sha256','dependency_sha256')}
        self.source=self.fixture.root/'source';self.source.mkdir()
        self.template=dict(target_date='20261009',now='2026-10-09T00:00:00Z',
            inputs={'manager':{'root':str(self.source),'files':{}}},rebound=None,
            manager_output_root=str(self.fixture.root/'separate-output'))
        self.clock=patch('v5_shadow.daily_manager_assembly.datetime');self.mock=self.clock.start();self.addCleanup(self.clock.stop)
        self.mock.now.return_value=datetime(2026,10,9,0,45,5,tzinfo=timezone.utc)

    def assemble(self,lanes):
        return assemble_manager_request(self.template,lanes,self.fixture.root,self.registration)

    def row(self,lane,ref):
        return dict(lane=lane,state={'attempts':[{'readback_verified':True,'product_reference':ref}]})

    def test_sealed_real_cutoff_reused_not_new_plan_every_tick(self):
        first=self.assemble([])
        self.mock.now.return_value=datetime(2026,10,9,0,50,tzinfo=timezone.utc)
        second=self.assemble([])
        self.assertEqual(first,second);self.assertEqual(first['now'],'2026-10-09T00:45:05+00:00')

    def test_rebound_reference_and_new_revision_binding_assembled(self):
        revision=dict(root='/revision',binding_sha256='a'*64,target_date='20261009',
            publication_date='2026-10-08',revision_manifest_sha256='b'*64)
        reference={'run_id':'a'*32,'artifact_sha256':'b'*64,'manifest_sha256':'c'*64,'receipt_sha256':'d'*64}
        result=self.assemble([self.row('announcement',{'binding':revision}),self.row('rebound',{'root':'/observation','reference':reference})])
        self.assertEqual(result['announcement_offline_owner'],revision)
        self.assertEqual(result['rebound_observation']['reference'],reference)

    def test_stale_template_us_and_observation_not_silently_reused(self):
        path='us_mapping_research/20261008/latest.json';p=self.source/path;p.parent.mkdir(parents=True);p.write_bytes(b'{}')
        self.template['inputs']['manager']['files'][path]=hashlib.sha256(b'{}').hexdigest()
        self.template['rebound_observation']={'root':'/old','reference':{}}
        result=self.assemble([])
        self.assertEqual(result['inputs']['manager']['files'],{});self.assertNotIn('rebound_observation',result)

    def test_us_exact_run_bytes_copied_and_changed_pointer_rejected(self):
        run='a'*32;day=self.source/'us_mapping_research/20261009';(day/'runs').mkdir(parents=True)
        daily=dict(run_id=run,target_trade_date='20261009',status='VALID_EMPTY')
        daily['artifact_sha256']=sha256_json(daily)
        raw=canonical_bytes(daily);(day/'runs'/f'{run}.json').write_bytes(raw)
        (day/'latest.json').write_bytes(canonical_bytes(dict(run_id=run,artifact_sha256=daily['artifact_sha256'])))
        row=self.row('us_mapping',dict(target_date='20261009',run_id=run,artifact_sha256=daily['artifact_sha256'],manager_output_root=str(self.source)))
        result=self.assemble([row]);relative=f'us_mapping_research/20261009/runs/{run}.json'
        self.assertEqual((Path(result['inputs']['manager']['root'])/relative).read_bytes(),raw)
        self.assertEqual(result['inputs']['manager']['files'][relative],hashlib.sha256(raw).hexdigest())
        (day/'latest.json').write_bytes(canonical_bytes(dict(run_id='b'*32,artifact_sha256=daily['artifact_sha256'])))
        with self.assertRaisesRegex(ValueError,'HEAD_CHANGED'):self.assemble([row])

    def test_closed_execution_window_can_read_existing_ledger_without_claim(self):
        claim=claim_run(self.fixture.root,self.fixture.identity)
        finish_run(self.fixture.root,claim,self.fixture.success)
        before=list(self.fixture.root.rglob('*'))
        state=read_run(self.fixture.root,self.fixture.identity)
        self.assertEqual(len(state['attempts']),1);self.assertEqual(state['latest_success']['product_reference'],self.fixture.success['product_reference'])
        self.assertEqual(before,list(self.fixture.root.rglob('*')))

    def test_new_defaults_are_explicit_hk_slots_not_legacy_claim(self):
        value=default_slots('20261009')
        self.assertTrue(value['scheduled_at'].endswith('08:00:00+08:00'))
        self.assertTrue(value['plan_at'].endswith('08:45:00+08:00'))
        self.assertEqual(value['schedule_basis'],'NEW_V5_DEFAULT_NOT_VERIFIED_V4_SCHEDULE')

    def test_missing_real_revision_inputs_do_not_invoke_model_or_owner(self):
        with patch('v5_shadow.daily_announcement_revision.subprocess.run') as owner:
            receipt=run_revision({'revision_create':{},'review_identities':None},'attempt')
        owner.assert_not_called();self.assertEqual(receipt['status'],'BLOCKED')

    def test_revision_capsule_is_exact_fixed_assembly(self):
        sources(REVISION_APP,REVISION_PIN)
        self.assertEqual(hashlib.sha256((REVISION_APP/'V5_OWNER_APP_MANIFEST.json').read_bytes()).hexdigest(),REVISION_PIN)
```

## Minimal synthetic reproduction and conflicting keys

Use the original fixture setup above and run only `DailyManagerAssemblyTests.test_rebound_reference_and_new_revision_binding_assembled` against the pinned candidate. It uses empty manager source files, the synthetic announcement binding `/revision`, and synthetic rebound lane reference rooted at `/observation` with repeated a/b/c/d hex identities. The four-argument call is:

```python
result = assemble_manager_request(template, [
    {"lane": "announcement", "state": {"attempts": [{
        "readback_verified": True, "product_reference": {"binding": revision}}]}},
    {"lane": "rebound", "state": {"attempts": [{
        "readback_verified": True, "product_reference": {
            "root": "/observation", "reference": reference}}]}}
], ledger_root, registration)
assert result["announcement_offline_owner"] == revision
# Original expectation; this is the recorded KeyError:
assert result["rebound_observation"]["reference"] == reference
```

The failing case's template contains `rebound=None`, not a rebound_observation object; its rebound reference enters through the verified lane. The original test expects the output key `rebound_observation`. The candidate's independently passing targeted test observes the same reference under `rebound_owner`, and absence of `rebound_observation`.

Separately, the unchanged original stale-input test explicitly supplies `template["rebound_observation"] = {"root": "/old", "reference": {}}` with no rebound lane and expects that stale observation to be removed; that original test passed. Thus this report does not conflate a stale input's intentional removal with the failing verified lane's output-key expectation.

No real market data, archive bodies, credentials, prior rejected feedback, or local usernames/absolute machine paths are included. No acceptance claim is made for all lanes, a natural day, production eligibility, or browser interaction.
