"""Test the original 21-node API with the narrow morning read-only overlay."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.request import urlopen
from urllib.error import HTTPError
from hashlib import sha256
import json,sys
HERE=Path(__file__).resolve().parent
R=HERE.parent
SRC=R/'workflow_api_smoke_20261120'
REL='workflow_runtime_20261119'
CONTRACT='node21_restore_20261118/overlay/local/public/research-system/timeline-data/contract.json'
PINS={
    f'{REL}/runtime.py':'98a649d519ffac83db1968d23d5b79b30d3bb3e54b72281f50ea954b6d80564d',
    f'{REL}/BINDINGS.json':'bafc50fa7d8444717585aaa9641f50fcc4d146adeb3c3c34be80abec8e32a434',
    f'{REL}/preview.py':'4afb2267e523b714b68fd0ea4e07a0def4dafc91c831360eddd048dddda38088',
    'full_board_nov18_v11/serve.py':'bdc5000055889db3a7a118c8c7a2ece5d51e01588063d8c212b8cd4d87beaba3',
    CONTRACT:'45661c39fc24b661c90cfa50894fa599896a91d0d6a91abe75d46cd096439cb5',
}
def require(condition,msg):
    if not condition: raise ValueError(msg)
def compose(raw):
    s=raw.decode()
    require(s.count('import argparse\n')==1 and s.count('        out.append(item)\n')==1,'ORIGINAL_RUNTIME_SHAPE')
    return s.replace('import argparse\n','import argparse\nfrom morning_projection import project as project_morning_check\n').replace('        out.append(item)\n','        project_morning_check(state, d, item)\n        out.append(item)\n').encode()

def run():
  with TemporaryDirectory(prefix='original_board_readback_') as tmp:
    root=Path(tmp)
    for rel,dig in PINS.items():
      raw=(SRC/rel).read_bytes()
      require(sha256(raw).hexdigest()==dig,'SOURCE_PIN:'+rel)
      p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
      p.write_bytes(compose(raw) if rel==f'{REL}/runtime.py' else raw)
    (root/REL/'morning_projection.py').write_bytes((HERE/'morning_projection.py').read_bytes())
    now='20261123'
    original=(R/'FIXED_SLOT_CHECK_20261123T001000Z_MORNING_DELIVERY.json').read_bytes()
    require(sha256(original).hexdigest()=='348e9e6de2156de53558c0f603efb9f6dd99baae84482a49d6fa64a1d7d32f19','CHECK_RECEIPT_PIN')
    live=json.loads(original)
    require(live['today_ready_card']=='NOT_FOUND_AT_CANONICAL_PATH' and live['actual_owner']=='UNKNOWN' and live['original_board_readback']=='CONNECTION_REFUSED_HTTP_8785','CHECK_EVIDENCE_CHANGED')
    ck={'schema':'BOARD_MORNING_CHECK_ONLY_V1','node_id':'morning-delivery','business_date':now,
        'observed_at':live['observed_check_utc'],'missing':['TODAY_READY_CARD','OWNER_REGISTRATION','BOARD_READBACK'],
        'business_started':False,'formal_delivery':False,'natural_verified':False}
    path=root/REL/'state'/now/'morning-delivery'/'check-only.json';path.parent.mkdir(parents=True);path.write_text(json.dumps(ck))
    sys.path.insert(0,str(root/REL))
    import preview
    with preview.make_server() as s:
      thread=Thread(target=s.serve_forever,daemon=True);thread.start()
      base=f'http://127.0.0.1:{s.server_port}/api/research/workflow-runtime?business_date='
      def read(q):
        with urlopen(base+q,timeout=3) as resp:return json.load(resp)
      try:
        same=read(now); old=read('20261120'); by={v['node_id']:v for v in same['nodes']}
        require(len(same['nodes'])==len(old['nodes'])==21 and same['natural_verified_count']==0,'CONTRACT')
        require(by['morning-delivery']['runtime_status']=='CHECK_BLOCKED_NOT_EXECUTED','NOT_PROJECTED')
        require(by['opening-prep']['runtime_status']=='UNKNOWN','FUTURE_CHECK')
        path.unlink()
        baseline=read(now)
        require([v for v in baseline['nodes'] if v['node_id']!='morning-delivery']==[v for v in same['nodes'] if v['node_id']!='morning-delivery'],'UNRELATED_NODES_CHANGED')
        require(next(x for x in old['nodes'] if x['node_id']=='morning-delivery')['runtime_status']=='UNKNOWN','DATE_LEAK')
        try:read(now+'&business_date=20261120')
        except HTTPError as e:require(e.code==422,'BAD_QUERY')
        else:raise ValueError('QUERY_ACCEPTED')
      finally:s.shutdown();thread.join(3)
    return {'exact_original_api':True,'checks_passed':6,'nodes':21,'natural_verified_count':0,'same_day_0810':by['morning-delivery']['runtime_status'],'0850':'UNKNOWN_NOT_YET_CHECKED','production':False,'new_owner':False,'unrelated_nodes_unchanged':True,'composed_runtime_sha256':sha256((root/REL/'runtime.py').read_bytes()).hexdigest()}
if __name__=='__main__':print(json.dumps(run(),indent=2,ensure_ascii=False))
