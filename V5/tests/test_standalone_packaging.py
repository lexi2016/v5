"""Standalone engineering checks. Fixtures are synthetic, never business proof."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
ENTRY = BASE / 'run_standalone.py'

class StandaloneTests(unittest.TestCase):
    def test_single_entry_help(self):
        result = subprocess.run([sys.executable, '-I', '-B', str(ENTRY), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('serve', result.stdout)

    def runtime(self):
        self.assertTrue((BASE/'src/v5_shadow/standalone.py').is_file(), 'standalone runtime missing')
        return importlib.import_module('v5_shadow.standalone')

    def test_init_requires_fresh_separate_root_and_does_not_invent_data(self):
        runtime = self.runtime()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'v5';runtime.initialize_root(root)
            self.assertEqual((root/runtime.MARKER).read_bytes(),runtime.MARKER_BYTES)
            self.assertFalse((root/'config/standalone.json').exists())
            self.assertFalse(list((root/'data').iterdir()))
            with self.assertRaises(ValueError):runtime.initialize_root(root)
            with self.assertRaises(ValueError):runtime.initialize_root(BASE/'new-runtime')

    def test_config_rejects_external_and_symlink_paths_before_start(self):
        runtime=self.runtime()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'v5';runtime.initialize_root(root)
            data=root/'data/module';data.mkdir();(data/'.v5-module-root').write_text('v5.module-root.v1:manager\n')
            module=dict(schema_version='v5.module_api.v1',module_id='manager',release_id='synthetic',data_root='data/module',routes=[])
            config=dict(schema_version='v5.standalone.v1',port=0,module_api=module)
            file=root/'config/standalone.json';file.write_text(json.dumps(config))
            checked=runtime.load_config(root,'config/standalone.json')
            self.assertEqual(checked['module_api']['data_root'],str(data))
            outside=Path(td)/'outside';outside.mkdir()
            for bad in (str(outside),'../outside','data/../../outside'):
                module['data_root']=bad;file.write_text(json.dumps(config))
                with self.assertRaises(ValueError):runtime.load_config(root,'config/standalone.json')
            (root/'data/link').symlink_to(outside,target_is_directory=True)
            module['data_root']='data/link';file.write_text(json.dumps(config))
            with self.assertRaises(ValueError):runtime.load_config(root,'config/standalone.json')
            self.assertEqual(list(outside.iterdir()),[])

    def test_packaged_owner_verifiers_do_not_require_external_checkout(self):
        self.runtime()
        from v5_shadow.daily_rebound_owner import verify_checkout
        from v5_shadow.cloud_us_collector import verify, BUNDLED_OWNER
        rebound=verify_checkout(None)
        self.assertTrue(rebound.is_relative_to(BASE/'vendor'))
        self.assertTrue(verify(BUNDLED_OWNER).is_relative_to(BASE/'vendor'))
        with self.assertRaises(ValueError):verify_checkout(Path('/unavailable/v4'))

    def test_manifest_rejects_damaged_resource_and_injected_module(self):
        runtime=self.runtime()
        with tempfile.TemporaryDirectory() as td:
            copied=Path(td)/'V5'
            shutil.copytree(BASE,copied)
            asset=next((copied/'frontend/dist/assets').glob('*.js'));original=asset.read_bytes()
            asset.write_bytes(original+b'/*changed*/')
            with self.assertRaisesRegex(ValueError,'STANDALONE_RESOURCE_SHA'):runtime.verify_package(copied)
            asset.write_bytes(original)
            (copied/'src/v5_shadow/injected.py').write_text('raise RuntimeError()')
            with self.assertRaisesRegex(ValueError,'STANDALONE_UNLISTED_RESOURCE'):runtime.verify_package(copied)

    def test_manifest_covers_resources_and_reproducible_archive(self):
        runtime=self.runtime();result=runtime.verify_package()
        self.assertGreater(result['files'],400)
        with tempfile.TemporaryDirectory() as td:
            outputs=[]
            for name in ('first.tar','second.tar'):
                out=Path(td)/name
                command=[sys.executable,'-I','-B',str(BASE/'tools/build_standalone.py'),'--output',str(out)]
                result=subprocess.run(command,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr);outputs.append(out.read_bytes())
            self.assertEqual(hashlib.sha256(outputs[0]).digest(),hashlib.sha256(outputs[1]).digest())

if __name__=='__main__':unittest.main()
