"""Explicit historical isolation harness; never grants production admission.
Run only with registered historical inputs and existing owner resource gates.
"""
import argparse,fcntl,hashlib,json,os,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent/'latest109_owner_v1'))
import isolated_owner as owner

def main():
 p=argparse.ArgumentParser();p.add_argument('--project',type=pathlib.Path,required=True);p.add_argument('--isolated',type=pathlib.Path,required=True);p.add_argument('--adapter-dir',type=pathlib.Path,required=True);p.add_argument('--input-wire',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--fault',choices=['none','second_object','receipt_before','receipt_after'],required=True);a=p.parse_args()
 original_load=owner.load;observations=[]
 def assert_lock(phase):
  fd=os.open(a.out.parent/'ISOLATED_OWNER.lock',os.O_RDWR|os.O_NOFOLLOW)
  try:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:observations.append(phase)
   else:raise AssertionError('OWNER_LOCK_NOT_HELD')
  finally:os.close(fd)
 def load(path,name,sha=None):
  module=original_load(path,name,sha)
  if name=='bridge':
   original_class=module.Bridge
   class InstrumentedBridge(original_class):
    def load_code(self):
     result=super().load_code();atomic=self.mods['atomic'];commit=atomic.atomic_commit;receipt=atomic.write_receipt
     def injected_commit(pending,final,*args,**kw):
      assert_lock('commit:'+pathlib.Path(final).name)
      if a.fault=='second_object' and pathlib.Path(final).name=='row_metadata.parquet':raise OSError('INJECT_SECOND_OBJECT')
      return commit(pending,final,*args,**kw)
     def injected_receipt(*args,**kw):
      assert_lock('receipt')
      if a.fault=='receipt_before':raise OSError('INJECT_RECEIPT_BEFORE')
      result=receipt(*args,**kw)
      if a.fault=='receipt_after':raise OSError('INJECT_RECEIPT_AFTER')
      return result
     atomic.atomic_commit=injected_commit;atomic.write_receipt=injected_receipt
     return result
   module.Bridge=InstrumentedBridge
  return module
 owner.load=load
 result=owner.run(a.project,a.isolated,a.adapter_dir,a.input_wire,a.out)
 expected='PASS_ISOLATED_NATIVE109_ORIGINAL_WRITER_COLD_READ' if a.fault=='none' else 'WRITER_OUTCOME_UNKNOWN_INSPECT_NO_RETRY'
 if result['status']!=expected:raise AssertionError('unexpected owner outcome:'+result['status'])
 if result.get('lock_held_during_terminal') is not True or result.get('isolated_lock_released') is not True:raise AssertionError('OWNER_LOCK_LIFECYCLE')
 if a.fault!='none' and (result['writer_reconciliation']['state']!='UNKNOWN_RECONCILE_NO_RETRY' or result['writer_reconciliation']['automatic_retry_allowed'] is not False):raise AssertionError('RECONCILIATION_STATE')
 if len(observations)<2:raise AssertionError('WRITER_NOT_REACHED')
 print(json.dumps({'harness_pass':True,'fault':a.fault,'lock_observations':observations,'production_allowed':False}))
if __name__=='__main__':main()
