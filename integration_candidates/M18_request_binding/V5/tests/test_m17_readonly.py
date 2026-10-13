"""Synthetic fixtures; original reader/ledger code, no market acquisition.
Only this new suite is executed. The old suite is imported for its fixture builder.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'src'))
sys.path.insert(0, str(HERE / 'tests'))
from test_daily_close_recapture_owner import fixture
from v5_shadow import daily_close_recapture_owner as original
from v5_shadow.digests import canonical_bytes
from v5_shadow.run_ledger import identity_key


def files_snapshot(*roots):
    return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for root in roots for p in Path(root).rglob('*') if p.is_file()}


class M17ReadonlyTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m17_readonly'),
                             'M17_READONLY adapter is missing')
        from v5_shadow import m17_readonly
        self.api = m17_readonly
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        request, self.ledger = fixture(Path(self.tmp.name).resolve())
        self.request = request
        # Only fixture preparation calls the original synthetic owner. GET cannot.
        result = original.run_close_recapture_daily(request, str(self.ledger),
                    original.bind_close_recapture_owner(request['config']))
        self.assertEqual(result['status'], 'SUCCEEDED', result)
        self.state = result['state']
        self.run_id = self.state['latest_success']['run_id']
        self.source_date = request['source_trade_date']
        self.config = dict(schema_version='v5.m17.readonly-binding.v1',
            state_root=request['config']['state_root'], universe_root=request['config']['universe_root'],
            ledger_root=str(self.ledger), python_executable=sys.executable,
            identity=self.state['identity'], run_id=self.run_id,
            execution_label='MANUAL_RECOVERY', operation='EXISTING_VERIFIED_PRODUCT_REUSE')
        self.roots = [self.config[k] for k in ('state_root','universe_root','ledger_root')]

    def read(self, **kwargs):
        return self.api.read_m17(self.config,
            source_trade_date=kwargs.get('source_trade_date', self.source_date),
            run_id=kwargs.get('run_id', self.run_id))

    def rewrite_ledger(self):
        if self.state['latest_success'] is not None:
            self.state['attempts'][-1] = copy.deepcopy(self.state['latest_success'])
        path = self.ledger / self.state['identity']['lane'] / self.source_date
        (path / (identity_key(self.state['identity']) + '.json')).write_bytes(canonical_bytes(self.state))

    def test_get_returns_original_hundred_rows_with_fresh_reader_and_no_mutation(self):
        before = files_snapshot(*self.roots)
        with patch.object(original, 'claim_run', side_effect=AssertionError('claim forbidden')), \
             patch.object(original, 'finish_run', side_effect=AssertionError('finish forbidden')), \
             patch.object(original, 'run_close_recapture_owner', side_effect=AssertionError('owner forbidden')):
            value = self.read()
            again = self.read()
        self.assertEqual(files_snapshot(*self.roots), before)
        self.assertEqual(value['status'], 'READY')
        self.assertEqual(value['source_trade_date'], self.source_date)
        self.assertEqual(value['plan_trade_date'], '20260929')
        self.assertEqual(value['run_id'], self.run_id)
        self.assertEqual(value['identity'], self.state['identity'])
        self.assertNotEqual(value['reader_pid'], os.getpid())
        self.assertNotEqual(value['reader_pid'], again['reader_pid'])
        overlay = json.loads((Path(self.config['state_root']) /
            f'workbench_research/{self.source_date}/close_recapture.candidates.json').read_bytes())
        self.assertEqual(value['rows'], overlay['rows'])
        self.assertEqual(len(value['rows']), 100)
        self.assertEqual(value['candidate_count'], 100)
        self.assertEqual(value['files'], self.state['latest_success']['product_reference']['files'])
        self.assertEqual(value['captured_at'], self.state['latest_success']['product_reference']['captured_at'])
        self.assertEqual(value['pool'], self.state['latest_success']['product_reference']['pool'])
        self.assertEqual(value['execution_label'], 'MANUAL_RECOVERY')
        self.assertEqual(value['operation'], 'EXISTING_VERIFIED_PRODUCT_REUSE')
        for key in ('natural_verified','formal_eligibility_verified','production_allowed','buy_gate_updated','orders_sent'):
            self.assertIs(value[key], False)
        self.assertIs(value['RESEARCH_ONLY'], True)
        self.assertIs(value['received_not_historical_1530'], True)
        self.assertIn('PYTDX_TURNOVER_CURRENCY_UNIT_UNVERIFIED', value['cannot_confirm'])
        self.assertLessEqual(len(canonical_bytes(value)), self.api.MAX_RESPONSE_BYTES)
        self.assertNotIn(str(self.tmp.name), canonical_bytes(value).decode())
        self.assertFalse(any(k.startswith(('ops.', 'apps.api.')) for k in sys.modules))

    def test_wrong_run_source_or_identity_is_rejected_without_mutation(self):
        before = files_snapshot(*self.roots)
        for kwargs in ({'run_id':'f'*32}, {'source_trade_date':'20260929'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): self.read(**kwargs)
        for field in self.config['identity']:
            saved = self.config['identity'][field]
            self.config['identity'][field] = ('0'*64 if field.endswith('sha256') else
                '2026-09-29T00:00:09+08:00' if field == 'research_cutoff' else '20260929' if field == 'target_date' else 'rebound')
            with self.subTest(field=field), self.assertRaises(ValueError): self.read()
            self.config['identity'][field] = saved
        self.assertEqual(files_snapshot(*self.roots), before)

    def test_all_four_damaged_products_fail_closed(self):
        for item in self.state['latest_success']['product_reference']['files'].values():
            path = Path(self.config['state_root']) / item['artifact_ref']; raw = path.read_bytes()
            path.write_bytes(b'{}')
            before = files_snapshot(*self.roots)
            with self.subTest(ref=item['artifact_ref']), self.assertRaises(ValueError): self.read()
            self.assertEqual(files_snapshot(*self.roots), before)
            path.write_bytes(raw)

    def test_external_pool_drift_is_rejected(self):
        path = next(Path(self.config['universe_root']).rglob('artifact.csv'))
        path.write_bytes(b'changed pool')
        before = files_snapshot(*self.roots)
        with self.assertRaises(ValueError): self.read()
        self.assertEqual(files_snapshot(*self.roots), before)

    def test_ledger_file_hash_or_pool_substitution_is_rejected(self):
        ref = self.state['latest_success']['product_reference']
        for mutate in (lambda: ref['files']['receipt'].update(sha256='0'*64),
                       lambda: ref['pool'].update(run_id='different')):
            saved = copy.deepcopy(ref)
            mutate(); self.rewrite_ledger()
            with self.assertRaises(ValueError): self.read()
            ref.clear(); ref.update(saved)
        self.rewrite_ledger()

    def test_non_success_missing_readback_and_wrong_saved_run_rejected(self):
        for change in ({'status':'RUNNING'}, {'readback_verified':False}, {'run_id':'e'*32}):
            saved = copy.deepcopy(self.state['latest_success'])
            self.state['latest_success'].update(change); self.rewrite_ledger()
            with self.subTest(change=change), self.assertRaises(ValueError): self.read()
            self.state['latest_success'] = saved
        self.state['latest_success'] = None; self.rewrite_ledger()
        with self.assertRaises(ValueError): self.read()

    def test_missing_ledger_never_creates_attempts(self):
        folder = self.ledger / self.state['identity']['lane'] / self.source_date
        (folder / (identity_key(self.state['identity']) + '.json')).unlink()
        before = files_snapshot(*self.roots)
        with self.assertRaises(ValueError): self.read()
        self.assertEqual(files_snapshot(*self.roots), before)

    def test_root_overlap_or_wrong_marker_rejected(self):
        for key in ('ledger_root', 'universe_root'):
            saved = self.config[key]; self.config[key] = self.config['state_root']
            with self.subTest(key=key), self.assertRaises(ValueError): self.read()
            self.config[key] = saved
        (Path(self.config['state_root']) / '.v5-m17-close-root').write_text('not m17\n')
        with self.assertRaises(ValueError): self.read()

    def test_response_byte_limit_is_enforced(self):
        with patch.object(self.api, 'MAX_RESPONSE_BYTES', 200):
            with self.assertRaisesRegex(ValueError, 'LIMIT'): self.read()

    def test_private_paths_in_original_extra_fields_are_redacted(self):
        # Use a valid original product with an extra free-form field, then update
        # its source hashes consistently. Core reader still performs validation.
        root = Path(self.config['state_root']); ref = self.state['latest_success']['product_reference']
        paths = {k: root / v['artifact_ref'] for k,v in ref['files'].items()}
        overlay = json.loads(paths['candidate_overlay'].read_bytes())
        overlay['rows'][0]['debug_path'] = str(root / 'private.json')
        overlay['rows'][0]['debug_text'] = r'source=/Users/alice/private/receipt.json; error at C:\Users\alice\private.json; source:/Users/alice/private/a; path:C:\Users\alice\private.json; source:file:///Users/alice/private/a'
        paths['candidate_overlay'].write_bytes(canonical_bytes(overlay))
        digest = hashlib.sha256(paths['candidate_overlay'].read_bytes()).hexdigest()
        artifact = json.loads(paths['artifact'].read_bytes()); artifact['candidate_overlay']['sha256'] = digest
        paths['artifact'].write_bytes(canonical_bytes(artifact))
        receipt = json.loads(paths['receipt'].read_bytes())
        receipt.update(candidate_overlay_sha256=digest,artifact_sha256=hashlib.sha256(paths['artifact'].read_bytes()).hexdigest())
        paths['receipt'].write_bytes(canonical_bytes(receipt))
        for key,path in paths.items(): ref['files'][key]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.rewrite_ledger()
        value = self.read()
        self.assertEqual(value['rows'][0]['debug_path'], '<redacted>')
        self.assertNotIn(str(root), canonical_bytes(value).decode())
        self.assertNotIn('/Users/alice', value['rows'][0]['debug_text'])
        self.assertNotIn(r'C:\Users', value['rows'][0]['debug_text'])

    def test_fixed_get_query_contract_rejects_unbound_keys(self):
        query = dict(source_trade_date=self.source_date, run_id=self.run_id)
        value = self.api.get_response(self.config, query)
        self.assertEqual(value['run_id'], self.run_id)
        for invalid in ({}, dict(query, limit='1000'), dict(query, source_trade_date=['20260928'])):
            with self.subTest(query=invalid), self.assertRaises(ValueError):
                self.api.get_response(self.config, invalid)

    def test_fresh_original_reader_profile_has_no_owner_ledger_write_or_collection(self):
        code = r"""import json,sys
sys.path.insert(0,sys.argv[1])
from v5_shadow.m17_readonly import _worker
packet=json.load(sys.stdin)
counts={'reader':0,'forbidden':0}
def profile(frame,event,arg):
    if event!='call': return
    name=frame.f_code.co_name
    if name=='read_close_recapture': counts['reader']+=1
    if name in {'claim_run','finish_run','recapture_close_minutes','collect_pytdx_exhq_minute','_collect_pytdx_exhq_batch','collect_payload','_connect_first_available',
                '_real_runtime_ready','_real_process_runner'}:
        counts['forbidden']+=1
        raise AssertionError('forbidden producer path')
sys.setprofile(profile)
value=_worker(packet)
sys.setprofile(None)
print(json.dumps({'counts':counts,'candidate_count':value['candidate_count']}))
"""
        before = files_snapshot(*self.roots)
        packet = dict(config=self.config, reference=self.state['latest_success']['product_reference'])
        done = subprocess.run([sys.executable,'-I','-B','-c',code,str(HERE/'src')],
            input=canonical_bytes(packet), capture_output=True)
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertEqual(json.loads(done.stdout),dict(counts=dict(reader=1,forbidden=0),candidate_count=100))
        self.assertEqual(files_snapshot(*self.roots),before)

    def test_cli_is_readonly_and_does_not_leak_private_config(self):
        path = Path(self.tmp.name) / 'binding.json'; path.write_bytes(canonical_bytes(self.config))
        before = files_snapshot(*self.roots)
        done = subprocess.run([sys.executable,'-I','-B',str(HERE/'src/v5_shadow/m17_readonly.py'),
            '--config',str(path),'--source-trade-date',self.source_date,'--run-id',self.run_id],capture_output=True)
        self.assertEqual(done.returncode,0,done.stderr)
        self.assertEqual(json.loads(done.stdout)['candidate_count'],100)
        self.assertNotIn(str(self.tmp.name).encode(),done.stdout+done.stderr)
        self.assertEqual(files_snapshot(*self.roots),before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
