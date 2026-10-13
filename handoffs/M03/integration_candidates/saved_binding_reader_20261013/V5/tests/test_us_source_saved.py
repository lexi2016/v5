"""Saved-only M03 adapter over original quote-only synthetic disk fixtures."""
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

from m03_fixture import SourceCase, BASE
from v5_shadow import us_source_daily as daily
from test_us_market_capture import offline_chain_runner


class SavedBindingTests(SourceCase):
    def setUp(self):
        super().setUp()
        self.req = self.request(market_snapshot_only=True, allow_network_capture=True,
            capture_root=self.root/'capture', cutoff='2026-10-09T20:20:00Z')
        self.binding = daily.run_us_source(self.req,
            runner=offline_chain_runner(self.root/'synthetic-provider-counts.jsonl'))
        self.assertEqual(self.binding['status'], 'VALIDATED_SOURCE_BINDING')
        self.request_file = self.root/'original-request.json'
        self.request_file.write_bytes(daily._json_bytes(daily._request_dict(self.req)))
        self.binding_file = self.req.binding_root/daily._binding_name(self.req)
        self.kw = dict(request_file=str(self.request_file),
            expected_request_sha256=daily._digest(daily._json_bytes(daily._request_dict(self.req))),
            expected_binding_sha256=hashlib.sha256(self.binding_file.read_bytes()).hexdigest(),
            expected_source_sha256=copy.deepcopy(self.binding['source_sha256']))

    def reader(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.us_source_saved'),
                             'M03_SAVED_READ_ADAPTER_MISSING')
        return importlib.import_module('v5_shadow.us_source_saved').read_saved_binding

    def tree(self):
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def invoke(self, **changes):
        return self.reader()(**dict(self.kw, **changes))

    def test_original_capture_true_request_is_read_unchanged_without_producer_or_writes(self):
        before=self.tree(); result=self.invoke()
        self.assertEqual(self.tree(),before)
        self.assertEqual(result['status'],'VALIDATED_SOURCE_BINDING')
        self.assertTrue(result['readback_verified'])
        self.assertEqual(result['source_status'],'READY_EMPTY')
        self.assertEqual(result['request_sha256'],self.kw['expected_request_sha256'])
        self.assertEqual(result['binding_sha256'],self.kw['expected_binding_sha256'])
        self.assertEqual(result['source_sha256'],self.binding['source_sha256'])
        self.assertEqual(result['market_snapshot']['status'],'READY')
        self.assertEqual(result['market_snapshot']['quote_count'],33)
        self.assertEqual(result['market_snapshot']['theme_count'],24)
        self.assertEqual(result['identity']['captured_at'],self.binding['identity']['captured_at'])
        self.assertTrue(json.loads(self.request_file.read_bytes())['allow_network_capture'])
        self.assertNotIn(str(self.root),json.dumps(result))
        self.assertNotIn(str(BASE),json.dumps(result))
        for key in ('production_allowed','orders_sent','buy_gate_updated','natural_verified'):
            self.assertIs(result[key],False)

    def test_request_mutation_or_wrong_digest_is_rejected_without_fallback(self):
        self.request_file.write_text(json.dumps(dict(daily._request_dict(self.req),allow_network_capture=False)))
        before=self.tree()
        with self.assertRaisesRegex(ValueError,'M03_SAVED_REQUEST_SHA_MISMATCH'):self.invoke()
        self.assertEqual(self.tree(),before)

    def test_binding_missing_and_binding_raw_tamper_do_not_create_or_repair(self):
        original=self.binding_file.read_bytes(); self.binding_file.unlink()
        before=self.tree()
        with self.assertRaisesRegex(ValueError,'M03_SAVED_BINDING_MISSING'):self.invoke()
        self.assertEqual(self.tree(),before)
        self.binding_file.write_bytes(original+b' '); before=self.tree()
        with self.assertRaisesRegex(ValueError,'M03_SAVED_BINDING_SHA_MISMATCH'):self.invoke()
        self.assertEqual(self.tree(),before)

    def test_each_snapshot_file_tamper_is_rejected_and_preserved(self):
        for name,path in daily.source_paths(self.req.snapshot_root,self.req.trade_date).items():
            with self.subTest(name=name):
                original=path.read_bytes(); path.write_bytes(original+b' '); before=self.tree()
                with self.assertRaisesRegex(ValueError,'M03_SNAPSHOT_SHA_MISMATCH'):self.invoke()
                self.assertEqual(self.tree(),before);path.write_bytes(original)

    def test_wrong_source_anchor_rejects_valid_binding(self):
        wrong=dict(self.kw['expected_source_sha256'],payload='0'*64); before=self.tree()
        with self.assertRaisesRegex(ValueError,'M03_SAVED_SOURCE_SHA_MISMATCH'):
            self.invoke(expected_source_sha256=wrong)
        self.assertEqual(self.tree(),before)

    def test_binding_resealed_with_wrong_time_or_status_is_not_accepted(self):
        original=self.binding_file.read_bytes()
        for change in ('captured_at','production_allowed','source_status'):
            with self.subTest(change=change):
                binding=copy.deepcopy(self.binding)
                if change=='captured_at':binding['identity']['captured_at']='2026-10-09T20:21:00Z'
                elif change=='production_allowed':binding[change]=True
                else:binding[change]='READY'
                raw=daily._json_bytes(binding);self.binding_file.write_bytes(raw);before=self.tree()
                with self.assertRaisesRegex(ValueError,'M03_BINDING_CONFLICT'):
                    self.invoke(expected_binding_sha256=hashlib.sha256(raw).hexdigest())
                self.assertEqual(self.tree(),before)
        self.binding_file.write_bytes(original)

    def test_bad_marker_symlink_and_unknown_request_field_are_rejected(self):
        marker=self.req.snapshot_root/'.v5-cloud-us-capture-root'; raw=marker.read_bytes()
        marker.write_bytes(b'bad');before=self.tree()
        with self.assertRaisesRegex(ValueError,'CLOUD_US_MARKED_PRIVATE_OUTPUT_REQUIRED'):self.invoke()
        self.assertEqual(self.tree(),before);marker.write_bytes(raw)
        linked=self.root/'request-link.json';linked.symlink_to(self.request_file)
        with self.assertRaises((ValueError,OSError)):self.invoke(request_file=str(linked))
        value=daily._request_dict(self.req);value['producer_override']='not allowed'
        self.request_file.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'M03_SAVED_REQUEST_FIELDS'):
            self.invoke(expected_request_sha256=hashlib.sha256(daily._json_bytes(value)).hexdigest())

    def test_missing_data_does_not_initialize_roots_even_if_request_permits_capture(self):
        shutil.rmtree(self.req.snapshot_root); before=self.tree()
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.tree(),before);self.assertFalse(self.req.snapshot_root.exists())

    def test_saved_only_cli_reads_same_original_request_from_other_cwd(self):
        self.reader()
        envelope=self.root/'read-envelope.json';envelope.write_text(json.dumps(self.kw))
        before=self.tree()
        proc=subprocess.run([sys.executable,'-I','-B',str(BASE/'src/v5_shadow/us_source_saved.py'),
                             '--request',str(envelope)],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(json.loads(proc.stdout),self.invoke())
        self.assertEqual(self.tree(),before)

    def test_formatted_original_file_keeps_raw_and_canonical_request_identities_distinct(self):
        raw=json.dumps(daily._request_dict(self.req),indent=2).encode()+b'\n'
        self.request_file.write_bytes(raw)
        result=self.invoke(expected_request_sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['request_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(result['request_identity_sha256'],daily._binding_name(self.req)[:-5])
        self.assertNotEqual(result['request_sha256'],result['request_identity_sha256'])

    def test_valid_poisoned_pyc_is_ignored_in_adapter_and_fresh_reader(self):
        import importlib._bootstrap_external as boot
        import importlib.util
        for module,cold_only in [('us_source_daily',False),('cloud_us_collector',True)]:
            source=BASE/'src/v5_shadow'/(module+'.py')
            cache=Path(importlib.util.cache_from_source(str(source)))
            existed=cache.exists();saved=cache.read_bytes() if existed else None
            cache.parent.mkdir(exist_ok=True)
            evil=("import sys\nif len(sys.argv)>5: raise RuntimeError('COLD_PYC_POISON')\n" if cold_only
                  else "raise RuntimeError('ADAPTER_PYC_POISON')\n")+source.read_text()
            code=compile(evil,str(source),'exec')
            cache.write_bytes(boot._code_to_timestamp_pyc(code,int(source.stat().st_mtime),source.stat().st_size))
            try:self.assertEqual(self.invoke()['status'],'VALIDATED_SOURCE_BINDING')
            finally:
                if existed:cache.write_bytes(saved)
                else:cache.unlink()

    def test_unlisted_top_level_dependency_cannot_shadow_stdlib(self):
        shadow=BASE/'src/dataclasses.py'
        self.assertFalse(shadow.exists())
        shadow.write_text("raise RuntimeError('UNLISTED_STDLIB_SHADOW')\n")
        try:self.assertEqual(self.invoke()['status'],'VALIDATED_SOURCE_BINDING')
        finally:shadow.unlink()
