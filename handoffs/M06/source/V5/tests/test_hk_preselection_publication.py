"""Real cold-reader publication tests; fixtures never claim producer/model execution."""
import concurrent.futures
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from v5_shadow.digests import canonical_bytes


class HKPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.output = self.base / 'output'
        self.output.mkdir()
        (self.output / '.v5-shadow-root').write_text('v5.shadow-root.v1\n')

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.hk_preselection_publication'),
                             'the M06 no-clobber publication module must exist')
        from v5_shadow import hk_preselection_publication
        return hk_preselection_publication

    def request(self, **changes):
        from fixtures.hk_preselection_verified_factory import create_verified_fixture
        return create_verified_fixture(self.base / 'source', **changes)

    def producer(self, request):
        return dict(schema_version='v5.hk_preselection_producer_receipt.v1', status='READY',
                    verified_source_reference=copy.deepcopy(request['expected_source']),
                    production_method='EXISTING_VERIFIED_POOL',
                    original_result=dict(request['expected_source'], status='READY'),
                    model_weights_reverified=False, fixture_only=True)

    def publish(self, request=None, **kwargs):
        request = request or self.request()
        return self.module().publish_verified_hk_preselection(
            request, bound_root=self.output,
            producer_receipt=kwargs.pop('producer_receipt', self.producer(request)), **kwargs)

    def test_publication_api_exists(self):
        self.assertTrue(callable(self.module().publish_verified_hk_preselection))
        self.assertTrue(callable(self.module().read_verified_hk_preselection_reference))

    def test_actual_eight_file_snapshot_and_full100_cold_readback(self):
        request = self.request()
        reference = self.publish(request)
        result = self.module().read_verified_hk_preselection_reference(self.output, reference)
        self.assertEqual(result['status'], 'ASSEMBLED')
        self.assertEqual(result['data_kind'], 'VERIFIED_SOURCE_SNAPSHOT')
        self.assertEqual(len(result['artifact']['rows']), 100)
        self.assertEqual(result['verified_source_reference'], reference['verified_source_reference'])
        self.assertFalse(result['model_weights_reverified'])
        self.assertFalse(result['natural_verified'])
        self.assertFalse(result['production_allowed'])
        self.assertEqual(reference['business_status'], 'STRICT_0_2_READY')
        self.assertEqual(set(reference['computation_identity']), {
            'lane', 'target_date', 'input_sha256', 'research_cutoff', 'code_sha256',
            'config_sha256', 'dependency_sha256'})
        obj = (self.output / reference['artifact_relative']).parent
        for relative, digest in request['files'].items():
            self.assertEqual(hashlib.sha256((obj / 'source' / relative).read_bytes()).hexdigest(), digest)
        for name in ('input_manifest.json', 'code_manifest.json', 'dependency_manifest.json',
                     'producer_receipt.json', 'strict_reader_receipt.json'):
            self.assertTrue((obj / name).is_file(), name)
        self.assertEqual(result['artifact']['rows'][0]['score_prob_active'], '0.999')
        self.assertEqual([r['pool_rank'] for r in result['artifact']['rows']], list(range(1, 101)))
        self.assertEqual([r['pool_score'] for r in result['artifact']['rows']], [1-i/1000 for i in range(1, 101)])

    def test_producer_ledger_identity_and_fixture_disclosure_remain_separate(self):
        request = self.request()
        producer = self.producer(request)
        ledger_identity = dict(lane='hk_preselection', target_date=request['target_date'],
                               input_sha256='a'*64, research_cutoff=request['research_cutoff'],
                               code_sha256='b'*64, config_sha256='c'*64, dependency_sha256='d'*64)
        producer['computation_identity'] = ledger_identity
        reference = self.publish(request, producer_receipt=producer)
        self.assertEqual(reference.get('producer_computation_identity'), ledger_identity)
        self.assertNotEqual(reference['computation_identity'], ledger_identity)
        self.assertTrue(reference['fixture_only'])
        obj = (self.output / reference['artifact_relative']).parent
        code = json.loads((obj / 'code_manifest.json').read_bytes())
        self.assertIn('contracts/hk_preselection_production_sources.json', code['files'])
        self.assertIn('src/v5_shadow/provider_evidence.py', code['files'])

    def test_route_record_uses_exact_committed_reference_without_writes(self):
        module = self.module()
        self.assertTrue(callable(getattr(module, 'project_hk_preselection_record', None)))
        reference = self.publish()
        config = dict(module_id='hk_preselection', release_id='fixture-release', routes=['/api/fixture-hk-pool'])
        query = {'target_date': reference['target_date']}
        before = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        record = module.project_hk_preselection_record(self.output, reference, config=config,
                                                       path='/api/fixture-hk-pool', query=query)
        from v5_shadow.module_api import _validate_record
        self.assertEqual(_validate_record(config, record, '/api/fixture-hk-pool', query), record)
        self.assertEqual(record['data_kind'], 'SYNTHETIC')
        self.assertEqual(record['payload']['committed_reference'], reference)
        self.assertEqual(len(record['payload']['artifact']['rows']), 100)
        self.assertFalse(record['payload']['natural_verified'])
        self.assertFalse(record['payload']['model_weights_reverified'])
        self.assertEqual(before, {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob('*') if p.is_file()})
        with self.assertRaisesRegex(ValueError, 'MODULE_ROUTE_NOT_CONFIGURED'):
            module.project_hk_preselection_record(self.output, reference, config=config,
                                                  path='/api/not-configured', query=query)
        bad = copy.deepcopy(reference); bad['artifact_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            module.project_hk_preselection_record(self.output, bad, config=config,
                                                  path='/api/fixture-hk-pool', query=query)

    def test_same_input_reuses_exact_reference_and_checks_current_bytes(self):
        request = self.request()
        first = self.publish(request)
        before = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(self.publish(request), first)
        after = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        self.assertEqual(after, before)
        (Path(request['input_root']) / request['expected_source']['artifact_relative']).write_bytes(b'bad')
        with self.assertRaises(ValueError): self.publish(request)
        self.assertEqual(self.module().read_verified_hk_preselection_reference(self.output, first)['status'], 'ASSEMBLED')

    def test_tampered_committed_source_and_artifact_rejected(self):
        request = self.request()
        reference = self.publish(request)
        obj = (self.output / reference['artifact_relative']).parent
        path = obj / 'source' / request['expected_source']['artifact_relative']
        path.chmod(0o600)
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            self.module().read_verified_hk_preselection_reference(self.output, reference)
        with self.assertRaises(ValueError): self.publish(request)

    def test_receipt_raw_bytes_cannot_change_even_when_json_is_equal(self):
        reference = self.publish()
        receipt = self.output / reference['receipt_relative']
        value = json.loads(receipt.read_bytes())
        receipt.chmod(0o600)
        receipt.write_text(json.dumps(value, indent=2))
        with self.assertRaises(ValueError):
            self.module().read_verified_hk_preselection_reference(self.output, reference)

    def test_metadata_mutation_during_cold_read_is_detected(self):
        reference = self.publish()
        module = self.module()
        path = (self.output / reference['artifact_relative']).parent / 'input_manifest.json'
        original_reader = module.verified.run_verified_hk_preselection
        def real_reader_then_change(request):
            result = original_reader(request)
            path.chmod(0o600)
            path.write_bytes(path.read_bytes() + b' ')
            return result
        with patch.object(module.verified, 'run_verified_hk_preselection', side_effect=real_reader_then_change):
            with self.assertRaisesRegex(ValueError, 'M06_INPUT_CHANGED'):
                module.read_verified_hk_preselection_reference(self.output, reference)

    def test_wrong_reference_does_not_fall_back_to_latest(self):
        reference = self.publish()
        bad = copy.deepcopy(reference)
        bad['artifact_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.module().read_verified_hk_preselection_reference(self.output, bad)
        bad = copy.deepcopy(reference)
        bad['target_date'] = '20261009'
        with self.assertRaises(ValueError):
            self.module().read_verified_hk_preselection_reference(self.output, bad)

    def test_different_same_slot_input_cannot_replace_prior_success(self):
        request = self.request()
        first = self.publish(request)
        changed = copy.deepcopy(request)
        changed['research_cutoff'] = '2026-10-08T09:21:00+08:00'
        with self.assertRaisesRegex(ValueError, 'M06_COMMIT_CONFLICT'):
            self.publish(changed)
        self.assertEqual(self.module().read_verified_hk_preselection_reference(self.output, first)['status'], 'ASSEMBLED')

    def test_marker_missing_or_invalid_never_auto_binds(self):
        request = self.request()
        marker = self.output / '.v5-shadow-root'
        marker.unlink()
        with self.assertRaisesRegex(ValueError, 'SHADOW_ROOT_NOT_INITIALIZED'):
            self.publish(request)
        self.assertFalse(marker.exists())
        marker.write_text('some-other-owner\n')
        with self.assertRaisesRegex(ValueError, 'SHADOW_ROOT_NOT_INITIALIZED'):
            self.publish(request)

    def test_output_inside_input_and_input_inside_output_rejected(self):
        request = self.request()
        for root in (Path(request['input_root']), Path(request['input_root']) / 'child'):
            root.mkdir(exist_ok=True)
            (root / '.v5-shadow-root').write_text('v5.shadow-root.v1\n')
            with self.assertRaisesRegex(ValueError, 'SOURCE_OUTPUT_OVERLAP'):
                self.module().publish_verified_hk_preselection(request, bound_root=root, producer_receipt=self.producer(request))
        (self.base / '.v5-shadow-root').write_text('v5.shadow-root.v1\n')
        with self.assertRaisesRegex(ValueError, 'SOURCE_OUTPUT_OVERLAP'):
            self.module().publish_verified_hk_preselection(request, bound_root=self.base, producer_receipt=self.producer(request))

    def test_root_ancestor_leaf_and_input_symlinks_rejected(self):
        request = self.request()
        alias = self.base / 'alias'
        alias.symlink_to(self.output, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'SYMLINK'):
            self.module().publish_verified_hk_preselection(request, bound_root=alias, producer_receipt=self.producer(request))
        source = Path(request['input_root']) / 'latest.json'
        saved = source.read_bytes(); source.unlink()
        elsewhere = self.base / 'latest-copy.json'; elsewhere.write_bytes(saved)
        source.symlink_to(elsewhere)
        with self.assertRaises(ValueError): self.publish(request)

    def test_producer_identity_or_original_result_mismatch_rejected(self):
        request = self.request()
        for where in ('verified_source_reference', 'original_result'):
            receipt = self.producer(request)
            receipt[where]['run_id'] = 'FAKE'
            with self.assertRaisesRegex(ValueError, 'M06_IDENTITY_CHAIN_MISMATCH'):
                self.publish(request, producer_receipt=receipt)
        receipt = self.producer(request); receipt['model_weights_reverified'] = True
        with self.assertRaises(ValueError): self.publish(request, producer_receipt=receipt)
        self.assertFalse(list(self.output.rglob('committed.json')))

    def test_arbitrary_model_proof_cannot_claim_weights_verified(self):
        request = self.request()
        receipt = self.producer(request)
        receipt.update(production_method='FROZEN_MODEL_PRODUCER', model_weights_reverified=True,
                       input_manifest={'claimed': True}, code_manifest={'claimed': True},
                       dependency_manifest={'claimed': True})
        with self.assertRaisesRegex(ValueError, 'M06_PRODUCER'):
            self.publish(request, producer_receipt=receipt)
        self.assertFalse(list(self.output.rglob('committed.json')))

    def test_frozen_receipt_requires_complete_runtime_inventory(self):
        from v5_shadow import hk_preselection_daily as daily
        from v5_shadow import hk_preselection_verified as verified
        from v5_shadow.digests import sha256_json
        request = self.request(); receipt = self.producer(request)
        code = daily._code_manifest(); descriptor = verified._production_sources()
        receipt.update(production_method='FROZEN_MODEL_PRODUCER', model_weights_reverified=True,
                       worker_request={}, request_sha256=sha256_json({}), implementation_identity=code,
                       code_manifest=code, dependency_manifest=daily._dependency_manifest(), runtime=descriptor['producer_runtime'],
                       input_manifest={}, asset_evidence={}, asset_snapshot={})
        with self.assertRaisesRegex(ValueError, 'M06_PRODUCER_PROOF_INVALID:runtime-inventory'):
            self.module()._producer(receipt, request['expected_source'])

    def test_exact_declared_runtime_and_code_do_not_replace_actual_asset_bytes(self):
        from v5_shadow import hk_preselection_daily as daily
        from v5_shadow import hk_preselection_verified as verified
        from v5_shadow.digests import sha256_json
        request = self.request()
        assets = self.base / 'fake-model-assets'; assets.mkdir()
        fake = assets / 'models.joblib'; fake.write_bytes(b'not-a-model')
        files = {'models.joblib': hashlib.sha256(fake.read_bytes()).hexdigest()}
        dates = {key: request[key] for key in ('target_date', 'signal_date', 'eligibility_source_date', 'research_cutoff')}
        source_files = {key: value for key, value in request['files'].items() if key.startswith('assets/hk_security_master/')}
        worker = dict(store_root=request['input_root'], asset_root=str(assets), asset_files=files,
                      source_files=source_files, **dates)
        inputs = dict(dates=dates, execution_mode='MANUAL_RECOVERY', data_kind='SOURCE_SNAPSHOT',
                      source_files=source_files, asset_files=files)
        code = daily._code_manifest(); descriptor = verified._production_sources()
        producer = self.producer(request)
        producer.update(production_method='FROZEN_MODEL_PRODUCER', model_weights_reverified=True,
                        worker_request=worker, request_sha256=sha256_json(worker), implementation_identity=code,
                        code_manifest=code, dependency_manifest=daily._dependency_manifest(), runtime=descriptor['producer_runtime'],
                        runtime_dependencies={'python': descriptor['producer_runtime']['python'], 'executable_sha256': '1'*64,
                            'packages': {'numpy': '2.4.0', 'pandas': '3.0.0', 'scikit-learn': '1.9.0',
                                         'joblib': '1.5.3', 'pyarrow': '23.0.0', 'fastparquet': 'MISSING'}},
                        input_manifest=inputs, asset_snapshot={'input_root': str(assets), 'files': files},
                        asset_evidence={}, asset_binding_status='FROZEN_ASSET_BYTES_CHECKED',
                        panel_sha256='f'*64, model_bundle_sha256='3b0d5d5239342439cabf25b30012365a64d78839bc3cd4d90bad7be6ff4aaa07')
        producer['original_result']['ok'] = True
        producer['computation_identity'] = dict(lane='hk_preselection', target_date=request['target_date'],
                input_sha256=sha256_json(inputs), research_cutoff=request['research_cutoff'], code_sha256=sha256_json(code),
                config_sha256=sha256_json(dict(execution_mode='MANUAL_RECOVERY', reader=verified.SCHEMA)),
                dependency_sha256=sha256_json(producer['dependency_manifest']))
        with self.assertRaises(ValueError): self.publish(request, producer_receipt=producer)
        self.assertFalse(list(self.output.rglob('committed.json')))

    def test_recorded_asset_bytes_persist_without_claiming_model_proof(self):
        request = self.request()
        assets = self.base / 'assets'; assets.mkdir()
        support = assets / 'recorded-context.json'; support.write_bytes(b'{"fixture_only":true}')
        files = {support.name: hashlib.sha256(support.read_bytes()).hexdigest()}
        producer = self.producer(request)
        producer.update(asset_snapshot={'input_root': str(assets), 'files': files},
                        asset_binding_status='NOT_REVERIFIED_RECORDED_INPUT_ONLY',
                        input_manifest={'asset_files': files})
        reference = self.publish(request, producer_receipt=producer, execution_mode='RECORDED_INPUT_REPLAY')
        saved = (self.output / reference['artifact_relative']).parent / 'producer_assets' / support.name
        self.assertTrue(saved.is_file())
        self.assertEqual(saved.read_bytes(), support.read_bytes())
        support.unlink(); assets.rmdir()
        result = self.module().read_verified_hk_preselection_reference(self.output, reference)
        self.assertFalse(result['model_weights_reverified'])
        self.assertEqual(result['status'], 'ASSEMBLED')
        saved.chmod(0o600); saved.write_bytes(b'bad')
        with self.assertRaises(ValueError):
            self.module().read_verified_hk_preselection_reference(self.output, reference)

    def test_recorded_replay_allows_explicit_absent_asset_snapshot(self):
        request = self.request()
        producer = self.producer(request)
        producer['asset_snapshot'] = None
        producer['asset_binding_status'] = 'NOT_REVERIFIED_RECORDED_INPUT_ONLY'
        reference = self.publish(request, producer_receipt=producer, execution_mode='RECORDED_INPUT_REPLAY')
        self.assertEqual(self.module().read_verified_hk_preselection_reference(self.output, reference)['status'], 'ASSEMBLED')

    def test_bad_source_never_commits(self):
        for changes in ({'count':99}, {'status':'CANNOT_CONFIRM'}, {'model_sha':'a'*64}, {'score_override':'nan'}):
            request = self.request(**changes)
            with self.assertRaises(ValueError): self.publish(request)
            self.assertFalse(list(self.output.rglob('committed.json')))

    def test_execution_mode_cannot_set_natural_verified(self):
        request = self.request()
        reference = self.publish(request, execution_mode='NATURAL')
        self.assertFalse(self.module().read_verified_hk_preselection_reference(self.output, reference)['natural_verified'])
        with self.assertRaises(ValueError): self.publish(request, execution_mode='MADE_UP')

    def test_concurrent_publish_has_one_immutable_success(self):
        request = self.request()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            references = list(pool.map(lambda _: self.publish(request), range(3)))
        self.assertEqual(references[0], references[1])
        self.assertEqual(references[1], references[2])
        self.assertEqual(len(list(self.output.rglob('committed.json'))), 1)
        self.assertEqual(len(list(self.output.rglob('strict_reader_receipt.json'))), 1)

    def test_nonregular_metadata_is_rejected_without_waiting_for_fifo_writer(self):
        module = self.module()
        fifo = self.base / 'bad-receipt.json'; os.mkfifo(fifo)
        done = threading.Event(); errors = []
        def read_fifo():
            try: module._read(fifo)
            except ValueError as error: errors.append(error)
            finally: done.set()
        thread = threading.Thread(target=read_fifo, daemon=True); thread.start()
        finished_without_writer = done.wait(0.3)
        if not finished_without_writer:
            with fifo.open('wb'): pass
        thread.join(2)
        self.assertTrue(finished_without_writer, 'a FIFO must fail closed without blocking')
        self.assertEqual(len(errors), 1)

    def test_existing_empty_final_is_conflict_not_replaceable(self):
        request = self.request()
        final = self.output / 'hk_preselection' / request['target_date'] / 'committed.json'
        final.parent.mkdir(parents=True)
        final.mkdir()
        with self.assertRaisesRegex(ValueError, 'M06_COMMIT_CONFLICT'):
            self.publish(request)
        self.assertTrue(final.is_dir())
        self.assertEqual(list(final.iterdir()), [])

    def test_crash_before_commit_leaves_unknown_not_auto_republished(self):
        request = self.request()
        module = self.module()
        # Failure injection is only in tests; production exposes no callback or failpoint.
        with patch.object(module.os, 'link', side_effect=OSError('simulated precommit crash')):
            with self.assertRaises(OSError): self.publish(request)
        self.assertFalse(list(self.output.rglob('committed.json')))
        with self.assertRaisesRegex(ValueError, 'M06_COMMIT_CONFLICT'):
            self.publish(request)
        self.assertFalse(list(self.output.rglob('committed.json')))


if __name__ == '__main__':
    unittest.main()
