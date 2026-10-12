"""Real process resource faults. Only worker dispatch is injected; no fake clocks,
usage readings, page returns or budget changes. Opt-in ~90s parallel stress run.
"""
import concurrent.futures,json,os,time,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_m18_offline_pages import fixture
from v5_shadow import m18_offline_v2 as m
from v5_shadow import m18_offline_v2_process as proc

def resource_fault_worker(request,connection):
 guard=m.ResourceGuard();kind=Path(request['output_root']).name
 result=dict(pid=os.getpid(),status='REJECTED')
 try:
  if kind=='rss':
   block=bytearray(m.PROFILE['rss_bytes']);guard.checkpoint();assert block is not None
  elif kind=='cpu':
   while True:
    sum(i*i for i in range(50000));guard.checkpoint()
  elif kind=='wall':time.sleep(m.PROFILE['wall_seconds']+5)
 except m.ContractError as error:result['error']=str(error)
 result['usage']=guard.usage();connection.send(result);connection.close()

class ResourceStressTests(unittest.TestCase):
 def test_actual_rss_cpu_and_wall_gates(self):
  _,_,identity=fixture()
  with tempfile.TemporaryDirectory() as td,patch.object(proc,'_worker',resource_fault_worker):
   root=Path(td)
   def run(kind):return proc.run(dict(action='build',response_path=str(root/'unused-response'),saved_path=str(root/'unused-saved'),output_root=str(root/kind),identity=identity,profile_sha256=m.PROFILE_SHA256))
   with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results=dict(zip(['rss','cpu','wall'],pool.map(run,['rss','cpu','wall'])))
   for kind,result in results.items():
    with self.subTest(kind=kind):
     self.assertEqual(result['status'],'REJECTED',result)
     self.assertEqual(result['error'],{'rss':'M18_V2_RESOURCE_PEAK_RSS_BYTES','cpu':'M18_V2_RESOURCE_CPU_SECONDS','wall':'M18_V2_RESOURCE_WALL_SECONDS'}[kind],result)
     self.assertFalse((root/kind/'ACCEPTED.json').exists())
   if os.environ.get('M18_RESOURCE_STRESS_EVIDENCE'):Path(os.environ['M18_RESOURCE_STRESS_EVIDENCE']).write_text(json.dumps(results,indent=2)+'\n')
