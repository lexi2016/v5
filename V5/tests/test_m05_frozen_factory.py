"""White-box instrumentation wraps real owner methods in a fresh process."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_m05_daily_boundary as fixture
from test_a_preselection import make_lane
from v5_shadow.a_preselection import BASE, run_a_preselection


class FrozenFactoryTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.M05DailyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def worker(self, body, request=None):
        f=self.fixture
        code='''import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v5_shadow.a_preselection_store_factory import build_strict_store,validate_strict_store
from v5_shadow.a_preselection_writer import _publish
runtime=build_strict_store(Path(sys.argv[2]),json.loads(sys.argv[3]))
'''+body
        args=[sys.executable,'-I','-B','-c',code,str(BASE/'src'),str(f.out),json.dumps(f.context)]
        if request is not None:
            args.extend([json.dumps(request),json.dumps(run_a_preselection(request))])
        proc=subprocess.run(args,capture_output=True,text=True,timeout=60)
        self.assertEqual(proc.returncode,0,proc.stderr+'\n'+proc.stdout)
        return proc.stdout

    def test_factory_checks_real_context_type_strictness_and_same_object(self):
        self.worker('''from dataclasses import replace
assert runtime.owner.StoreGateContext is runtime.gate.StoreGateContext
assert sys.modules[runtime.store.__class__.__module__].__loader__ is runtime.loader
assert runtime.store._write_gate_context is runtime.context
validate_strict_store(runtime)

def check(expected,changed):
    try:validate_strict_store(changed)
    except ValueError as error:assert str(error)==expected,(str(error),expected)
    else:raise AssertionError('invalid runtime accepted')
check('M05_WRITE_GATE_CONTEXT_TYPE_REQUIRED',replace(runtime,context=object()))
check('M05_STORE_TYPE_REQUIRED',replace(runtime,store=object()))
runtime.store._require_write_gate_context=False
check('M05_STORE_STRICT_GATE_REQUIRED',runtime)
runtime.store._require_write_gate_context=True
runtime.store._write_gate_context=replace(runtime.context)
check('M05_STORE_GATE_CONTEXT_MISMATCH',runtime)
''')
        self.assertEqual(set(self.fixture.tree(self.fixture.out)),{'.v5-shadow-root'})

    def test_all_final_readbacks_share_one_exact_live_lease_after_last_write(self):
        f=self.fixture
        request=f.request([make_lane(f.source/'fupan'),make_lane(f.source/'stage7','stage7')])
        self.worker('''request=json.loads(sys.argv[4]);assembly=json.loads(sys.argv[5])
events=[];leases=[]
original_write=runtime.owner.PreselectionPoolStore.materialize
original_read=runtime.owner.PreselectionPoolStore.read_pool_snapshot

def write(self,payload):
    result=original_write(self,payload)
    events.append(('write',payload['pool_id']))
    return result

def read(self,date,pool,*,lock_lease=None):
    assert lock_lease is not None
    runtime.locks.assert_owned_interprocess_lock(lock_lease,self.root/'.import.lock')
    leases.append(lock_lease);events.append(('read',pool))
    return original_read(self,date,pool,lock_lease=lock_lease)
runtime.owner.PreselectionPoolStore.materialize=write
runtime.owner.PreselectionPoolStore.read_pool_snapshot=read
result=_publish(runtime,request,assembly)
assert [x[0] for x in events]==['write','write','read','read'],events
assert len(leases)==2 and leases[0] is leases[1]
try:runtime.locks.assert_owned_interprocess_lock(leases[0],runtime.store.root/'.import.lock')
except ValueError as error:assert str(error)=='OWNER_LOCK_LEASE_NOT_ACTIVE'
else:raise AssertionError('expired lease accepted')
assert result['batch_identity']['snapshot_count']==2
''',request)

    def test_snapshot_identity_mismatch_is_not_a_publish_conflict(self):
        f=self.fixture
        request=f.request([make_lane(f.source/'fupan')])
        self.worker('''request=json.loads(sys.argv[4]);assembly=json.loads(sys.argv[5])
original=runtime.owner.PreselectionPoolStore.read_pool_snapshot

def damaged(self,*args,**kwargs):
    snapshot=original(self,*args,**kwargs)
    snapshot['artifact_raw_sha256']='0'*64
    return snapshot
runtime.owner.PreselectionPoolStore.read_pool_snapshot=damaged
try:_publish(runtime,request,assembly)
except ValueError as error:assert str(error)=='M05_SNAPSHOT_IDENTITY_MISMATCH'
else:raise AssertionError('snapshot mismatch accepted')
''',request)

    def test_narrow_conflict_classifier(self):
        self.worker('''from v5_shadow.a_preselection_writer import _classify_exception
assert _classify_exception(ValueError('conflicting preselection-pool materialization'))
for error in (RuntimeError('conflicting preselection-pool materialization'),
              ValueError('partial preselection-pool materialization'),
              ValueError('conflicting preselection-pool materialization extra'),OSError('disk')):
    assert not _classify_exception(error)
''')


if __name__=='__main__':unittest.main()
