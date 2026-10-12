"""FD snapshot contract tests, with no manager/announcement imports."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve(); (self.root/'a').write_bytes(b'original')
        self.binding={'root':str(self.root),'files':{'a':hashlib.sha256(b'original').hexdigest()}}

    def module(self):
        spec=importlib.util.find_spec('v5_shadow.m02_input_snapshot')
        self.assertIsNotNone(spec, 'standalone M02 snapshot is missing')
        return __import__('v5_shadow.m02_input_snapshot',fromlist=['snapshot'])

    def test_returns_original_bytes_without_manager_import(self):
        self.assertEqual(self.module().snapshot(self.binding),{'a':b'original'})

    def test_sha_path_and_symlink_boundaries(self):
        m=self.module()
        for path in ('/etc/passwd','../a','nested/../../a'):
            with self.subTest(path=path),self.assertRaises((ValueError,OSError)):
                m.snapshot(dict(self.binding,files={path:self.binding['files']['a']}))
        (self.root/'link').symlink_to(self.root/'a')
        with self.assertRaises((ValueError,OSError)):m.snapshot(dict(self.binding,files={'link':self.binding['files']['a']}))
        with self.assertRaisesRegex(ValueError,'SHA_OR_LIMIT'):m.snapshot(dict(self.binding,files={'a':'0'*64}))
        with self.assertRaises(ValueError):m.snapshot(dict(self.binding,root='relative'))

    def test_fifo_is_nonblocking_rejected(self):
        os.mkfifo(self.root/'fifo')
        with self.assertRaisesRegex(ValueError,'SIZE_OR_TYPE'):
            self.module().snapshot(dict(self.binding,files={'fifo':'0'*64}))

    def test_limits_preserve_exact_original_exception(self):
        m=self.module(); special='announcement_agent_runs/'+'a'*32+'/evidence/body_corpus.json'
        self.assertEqual(m.input_limit(special),32*1024*1024)
        for name in ('a',special.replace('a'*32,'A'*32),special+'/x'):
            self.assertEqual(m.input_limit(name),16*1024*1024)
        with (self.root/'a').open('wb') as stream:stream.truncate(16*1024*1024+1)
        with self.assertRaisesRegex(ValueError,'SIZE_OR_TYPE'):m.snapshot(self.binding)

    def test_change_during_read_rejected(self):
        m=self.module(); read=os.read
        def mutate(fd,n):
            raw=read(fd,n)
            if raw:(self.root/'a').write_bytes(b'changed!')
            return raw
        with patch('os.read',side_effect=mutate),self.assertRaisesRegex(ValueError,'RECORD_CHANGED'):
            m.snapshot(self.binding)

class FrozenAssetSnapshotTests(unittest.TestCase):
    def test_large_frozen_asset_uses_separate_streaming_snapshot_not_native_exception(self):
        from v5_shadow import hk_source_daily as daily
        self.assertTrue(hasattr(daily,'_asset_snapshot'),'separate bounded asset snapshot missing')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path=root/'models.joblib'
            with path.open('wb') as stream:stream.truncate(33062913)
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            binding={'root':str(root),'files':{'models.joblib':digest}}
            self.assertEqual(daily._asset_snapshot(binding)['models.joblib'],{'bytes':33062913,'sha256':digest})
            from v5_shadow.m02_input_snapshot import snapshot
            with self.assertRaisesRegex(ValueError,'SIZE_OR_TYPE'):snapshot(binding)
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'ASSET_SHA'):daily._asset_snapshot(binding)

class PanelDateTests(unittest.TestCase):
    def test_current_asset_can_bind_reference_identity_without_claiming_historical_pit(self):
        from v5_shadow import hk_source_daily as daily
        self.assertTrue(hasattr(daily,'_panel_date'),'panel reference-date contract missing')
        self.assertEqual(daily._panel_date({'panel_max_date':'20261012'},'20261009'),'20261012')
        with self.assertRaisesRegex(ValueError,'NOT_COVERED'):daily._panel_date({'panel_max_date':'20261008'},'20261009')
        with self.assertRaises(ValueError):daily._panel_date({'panel_max_date':'invalid'},'20261009')

class PanelProjectionTests(unittest.TestCase):
    def test_owner_result_must_match_fd_bound_manifest_paths_and_shas(self):
        from types import SimpleNamespace
        from v5_shadow import hk_source_daily as daily
        self.assertTrue(hasattr(daily,'_bound_projection'),'owner/snapshot result binding missing')
        root=Path('/synthetic/root')
        panel={'panel_relative':'p','panel_sha256':'a'*64};model={'bundle_relative':'m','bundle_sha256':'b'*64}
        binding={'root':str(root),'files':{'p':'a'*64,'m':'b'*64}}
        refs={'panel_latest.json':('p',panel),'model_latest.json':('m',model)}
        asset=SimpleNamespace(root=root,panel_path=root/'p',panel_manifest=panel,
            model_path=root/'m',model_manifest=model,name_dictionary_path=None)
        self.assertEqual(daily._bound_projection(asset,binding,refs)['panel_manifest'],panel)
        asset.panel_manifest=dict(panel,panel_sha256='c'*64)
        with self.assertRaisesRegex(ValueError,'PROJECTION'):daily._bound_projection(asset,binding,refs)
        asset.panel_manifest=panel;asset.panel_path=root/'other'
        with self.assertRaisesRegex(ValueError,'PROJECTION'):daily._bound_projection(asset,binding,refs)
        asset.panel_path=root/'p';binding['files']['p']='d'*64
        with self.assertRaisesRegex(ValueError,'DECLARED_SHA'):daily._bound_projection(asset,binding,refs)

    def test_bool_to_int_projection_substitution_is_not_json_identical(self):
        from types import SimpleNamespace
        from v5_shadow import hk_source_daily as daily
        root=Path('/synthetic/root')
        panel={'panel_relative':'p','panel_sha256':'a'*64,'research_only':True}
        model={'bundle_relative':'m','bundle_sha256':'b'*64}
        asset=SimpleNamespace(root=root,panel_path=root/'p',panel_manifest=dict(panel,research_only=1),
            model_path=root/'m',model_manifest=model,name_dictionary_path=None)
        refs={'panel_latest.json':('p',panel),'model_latest.json':('m',model)}
        with self.assertRaisesRegex(ValueError,'PROJECTION'):
            daily._bound_projection(asset,{'root':str(root),'files':{'p':'a'*64,'m':'b'*64}},refs)

class AssetBudgetTests(unittest.TestCase):
    def test_local_asset_budget_is_minimal_and_oversize_rejected(self):
        from v5_shadow import hk_source_daily as daily
        self.assertEqual((daily.ASSET_MAX_FILES,daily.ASSET_MAX_FILE_BYTES,daily.ASSET_MAX_TOTAL_BYTES),(9,64*1024**2,128*1024**2))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path=root/'too_large'
            with path.open('wb') as f:f.truncate(64*1024**2+1)
            with self.assertRaisesRegex(ValueError,'SIZE_OR_TYPE'):
                daily._asset_snapshot({'root':str(root),'files':{'too_large':'0'*64}})

    def test_asset_total_budget_and_fixed_file_count_fail_closed(self):
        from v5_shadow import hk_source_daily as daily
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();files={}
            raw=b'\0'*(64*1024**2);digest=hashlib.sha256(raw).hexdigest();del raw
            for name,size in (('a',64*1024**2),('b',64*1024**2),('c',1)):
                with (root/name).open('wb') as stream:stream.truncate(size)
                files[name]=digest if size>1 else hashlib.sha256(b'\0').hexdigest()
            with self.assertRaisesRegex(ValueError,'TOTAL_LIMIT'):daily._asset_snapshot({'root':str(root),'files':files})
            with self.assertRaisesRegex(ValueError,'ASSET_BINDING'):
                daily._asset_snapshot({'root':str(root),'files':{str(i):'0'*64 for i in range(10)}})

    def test_panel_metadata_stays_at_16_mib(self):
        from v5_shadow import hk_source_daily as daily
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path=root/'panel_latest.json'
            with path.open('wb') as stream:stream.truncate(16*1024**2+1)
            binding={'root':str(root),'files':{'panel_latest.json':hashlib.sha256(path.read_bytes()).hexdigest()}}
            daily._asset_snapshot(binding)
            with self.assertRaisesRegex(ValueError,'SIZE_OR_TYPE'):daily._panel_references(binding)
