"""M06 interpreter-only repair tests; temporary synthetic venv, no installs."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE/'src'),str(HERE/'tests')]
from v5_shadow import p0_hk_preselection as bridge
from fixtures.hk_preselection_verified_factory import create_verified_fixture


def digest(raw):return hashlib.sha256(raw).hexdigest()

class PythonLaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.venv=self.root/'synthetic-venv';(self.venv/'bin').mkdir(parents=True)
        self.real=Path(sys.executable).resolve();self.launch=self.venv/'bin/python'
        self.launch.symlink_to(self.real)
        self.cfg=self.venv/'pyvenv.cfg';self.cfg.write_text('home = '+str(self.real.parent)+'\ninclude-system-site-packages = false\n')
        packages=self.venv/('lib/python%d.%d/site-packages'%sys.version_info[:2]);packages.mkdir(parents=True)
        info=packages/'m06_launch_sentinel-0.0.dist-info';info.mkdir();(info/'METADATA').write_text('Name: m06-launch-sentinel\nVersion: 0.0\n')
        for name in ('input','assets','output'):(self.root/name).mkdir()
        (self.root/'output/.v5-shadow-root').write_bytes(b'v5.shadow-root.v1\n')
        self.registration=dict(enabled=True,python_executable=str(self.launch),python_sha256=digest(self.real.read_bytes()),
            timeout_seconds=120,store_root=str(self.root/'input'),asset_root=str(self.root/'assets'),private_root=str(self.root/'output'),
            python_venv=dict(root=str(self.venv),realpath=str(self.real),pyvenv_cfg_sha256=digest(self.cfg.read_bytes()),
                symlink_sha256=digest(os.readlink(self.launch).encode())))
    def test_pinned_venv_launch_is_accepted_and_retains_site_packages(self):
        try:bridge._config(self.registration)
        except ValueError as error:self.fail('Explicit pinned venv launch must be accepted: '+str(error))
        code="import sys,json,importlib.metadata as m; print(json.dumps(dict(prefix=sys.prefix,executable=sys.executable,sentinel=m.version('m06-launch-sentinel'))))"
        result=subprocess.run([self.registration['python_executable'],'-I','-B','-c',code],capture_output=True,text=True,check=True)
        observed=json.loads(result.stdout)
        self.assertEqual(observed['prefix'],str(self.venv));self.assertEqual(observed['executable'],str(self.launch));self.assertEqual(observed['sentinel'],'0.0')
    def test_unregistered_symlink_still_rejected(self):
        config=dict(self.registration);config.pop('python_venv')
        with self.assertRaisesRegex(ValueError,'SYMLINK_REJECTED'):bridge._config(config)
    def test_ordinary_real_executable_retains_legacy_registration(self):
        config=dict(self.registration,python_executable=str(self.real));config.pop('python_venv')
        self.assertEqual(bridge._config(config),config)
    def test_wrong_binary_realpath_cfg_or_link_pin_rejected(self):
        for key in ('realpath','pyvenv_cfg_sha256','symlink_sha256'):
            value=copy.deepcopy(self.registration);value['python_venv'][key]=str(self.root/'wrong') if key=='realpath' else '0'*64
            with self.subTest(key=key),self.assertRaises(ValueError):bridge._config(value)
        value=copy.deepcopy(self.registration);value['python_sha256']='0'*64
        with self.assertRaises(ValueError):bridge._config(value)
    def test_launch_outside_venv_bin_rejected_even_same_binary(self):
        outside=self.root/'python';outside.symlink_to(self.real)
        value=copy.deepcopy(self.registration);value['python_executable']=str(outside)
        with self.assertRaises(ValueError):bridge._config(value)
    def test_cfg_or_input_root_symlink_is_not_exempted(self):
        original=self.cfg.read_bytes();other=self.root/'other.cfg';other.write_bytes(original)
        self.cfg.rename(self.venv/'original.cfg');self.cfg.symlink_to(other)
        with self.assertRaises(ValueError):bridge._config(self.registration)
        self.cfg.unlink();(self.venv/'original.cfg').rename(self.cfg)
        alias=self.root/'input-alias';alias.symlink_to(self.root/'input',target_is_directory=True)
        value=copy.deepcopy(self.registration);value['store_root']=str(alias)
        with self.assertRaisesRegex(ValueError,'SYMLINK_REJECTED'):bridge._config(value)
    def test_launch_directory_symlink_is_not_exempted(self):
        bindir=self.venv/'bin';bindir.rename(self.venv/'real-bin');bindir.symlink_to(self.venv/'real-bin',target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'SYMLINK_REJECTED'):bridge._config(self.registration)
    def test_real_m06_inspection_preserves_pinned_venv(self):
        source=create_verified_fixture(self.root/'input')
        request=dict(signal_date='20261007',target_date='20261008',eligibility_source_date='20260930',
            admission_cutoff='2026-10-08T08:01:00+08:00',completion_cutoff='2026-10-08T09:20:00+08:00',
            files={},source_files=source['files'],execution_mode='RECORDED_INPUT_REPLAY',production_method='EXISTING_VERIFIED_POOL')
        try:result=bridge._process('inspect',request,self.registration)
        except ValueError as error:self.fail('Original M06 inspect must run inside pinned venv: '+str(error))
        self.assertEqual(result['python_launch']['prefix'],str(self.venv))
        self.assertEqual(result['python_launch']['executable'],str(self.launch))
        self.assertEqual(result['payload']['computation_identity']['target_date'],'20261008')
        self.assertEqual(list((self.root/'output').iterdir()),[self.root/'output/.v5-shadow-root'])
    def test_same_bytes_launch_replacement_changes_identity(self):
        self.assertTrue(hasattr(bridge,'_python_launch'),'explicit interpreter identity missing')
        before=bridge._python_launch(self.registration)
        replacement=self.venv/'bin/replacement';replacement.symlink_to(self.real);os.replace(replacement,self.launch)
        after=bridge._python_launch(self.registration)
        self.assertNotEqual(before,after)
        with self.assertRaisesRegex(ValueError,"M06_PYTHON_LAUNCH_CHANGED"):bridge._check_python(self.registration,before)
    def request(self):
        source=create_verified_fixture(self.root/'input')
        return dict(signal_date='20261007',target_date='20261008',eligibility_source_date='20260930',
            admission_cutoff='2026-10-08T08:01:00+08:00',completion_cutoff='2026-10-08T09:20:00+08:00',
            files={},source_files=source['files'],execution_mode='RECORDED_INPUT_REPLAY',production_method='EXISTING_VERIFIED_POOL')
    def test_original_owner_and_cold_reader_use_same_venv(self):
        request=self.request();snapshot=bridge._process('inspect',request,self.registration)['payload']
        produced=bridge._process('invoke',request,self.registration,snapshot)
        product=produced['payload']
        read=bridge._process('read',request,self.registration,snapshot,
            reference=product['committed_reference'],m06_ledger_run_id=product['m06_ledger_run_id'])
        self.assertEqual(read['payload'],{k:v for k,v in product.items() if k!='owner_reused'})
        self.assertNotEqual(read['pid'],produced['pid'])
        self.assertEqual(read['python_launch'],produced['python_launch'])
        self.assertEqual(product['row_count'],100);self.assertTrue(product['fixture_only'])
        self.assertFalse(product['producer_model_weights_reverified'])
    def test_launch_replaced_during_process_is_rejected(self):
        request=self.request();run=subprocess.run
        def replaced(*args,**kwargs):
            result=run(*args,**kwargs)
            replacement=self.venv/'bin/replacement';replacement.symlink_to(self.real);os.replace(replacement,self.launch)
            return result
        with patch.object(bridge.subprocess,'run',side_effect=replaced):
            with self.assertRaisesRegex(ValueError,'M06_PYTHON_LAUNCH_CHANGED'):bridge._process('inspect',request,self.registration)
    def test_child_wrong_venv_prefix_is_rejected(self):
        request=self.request();run=subprocess.run
        def wrong_prefix(*args,**kwargs):
            result=run(*args,**kwargs);value=json.loads(result.stdout)
            value['python_launch']['prefix']=value['python_launch']['base_prefix']
            return subprocess.CompletedProcess(result.args,result.returncode,json.dumps(value).encode(),result.stderr)
        with patch.object(bridge.subprocess,'run',side_effect=wrong_prefix):
            with self.assertRaisesRegex(ValueError,'M06_VENV_PROCESS_IDENTITY_MISMATCH'):bridge._process('inspect',request,self.registration)
    def test_non_executable_regular_file_rejected_without_chmod(self):
        target=self.root/'not-executable';target.write_bytes(self.real.read_bytes())
        config=dict(self.registration,python_executable=str(target));config.pop('python_venv')
        with self.assertRaisesRegex(ValueError,'M06_PYTHON_EXECUTABLE_REQUIRED'):bridge._config(config)

    def test_target_replacement_and_broken_loop_rejected(self):
        other=self.root/'same-bytes-python';other.write_bytes(self.real.read_bytes())
        self.launch.unlink();self.launch.symlink_to(other)
        with self.assertRaises(ValueError):bridge._config(self.registration)
        self.launch.unlink();self.launch.symlink_to('python')
        with self.assertRaises((ValueError,RuntimeError,OSError)):bridge._config(self.registration)

if __name__=='__main__':unittest.main(verbosity=2)
