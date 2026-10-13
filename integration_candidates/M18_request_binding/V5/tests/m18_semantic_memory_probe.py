"""Large synthetic lifecycle probe, original hard budgets, separate API process."""
import gc, hashlib, json, os, resource, subprocess, sys, time, traceback
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
RUN='46596b03c2ab4e29b1219fd2e5eb698f'

def prepare(root):
    from test_m18_offline_pages import fixture
    from v5_shadow import m18_offline_v2 as m, m18_offline_v2_process as proc
    from v5_shadow.m18_v2_publication_bridge import ROUTE, descriptor_from_bundle, publish_m18_descriptor
    root.mkdir()
    (root/'SYNTHETIC_TEST_ONLY').write_text('v5.synthetic.memory-probe.v1\n')
    raw,saved,identity=fixture(run=RUN,extra={'summary':{'status':'PARTIAL'},'dense':{'rows':[{'a':i,'b':'S'*110} for i in range(220000)]}})
    (root/'response').write_bytes(raw);(root/'saved').write_bytes(saved)
    lengths={'response_bytes':len(raw),'saved_bytes':len(saved)};del raw,saved;gc.collect()
    result=proc.run(dict(action='build',response_path=str(root/'response'),saved_path=str(root/'saved'),output_root=str(root/'bundle'),identity=identity,profile_sha256=m.PROFILE_SHA256))
    if result['status']!='OK':raise RuntimeError(result)
    manifest=json.loads((root/'bundle/manifest.json').read_bytes())
    pr=root/'publication';pr.mkdir();(pr/'.v5-module-root').write_text('v5.module-root.v1:manager\n')
    config=dict(schema_version='v5.module_api.v1',module_id='manager',release_id='synthetic-dense',data_root=str(pr),routes=[ROUTE,ROUTE+'/pages',ROUTE+'/overview',ROUTE+'/sections'],m18_v2_binding=dict(manifest_sha256=result['manifest_sha256'],profile_sha256=m.PROFILE_SHA256,identity=identity,bundle_root=str(root/'bundle')))
    desc=descriptor_from_bundle(None,identity,manifest);publish_m18_descriptor(config,desc,expected_generation=None)
    (root/'config.json').write_text(json.dumps(config));(root/'descriptor.json').write_text(json.dumps(desc))
    print(json.dumps(dict(lengths,build=result,response_nodes=manifest['response_nodes'])),flush=True)

def serve(config):
    from v5_shadow import module_api as api
    from v5_shadow import m18_v2_read_process as read_process
    original_run=read_process.run
    def observed_run(request):
        result=original_run(request)
        print(json.dumps({key:result.get(key) for key in
              ('status','pid','usage','worker_exit','worker_reaped','supervisor_wall_seconds')}),
              file=sys.stderr,flush=True)
        return result
    read_process.run=observed_run
    original=api._m18_semantic_response
    def observed(*args):
        start=time.monotonic();code=None
        try:return original(*args)
        except Exception as error:code=str(error);raise
        finally:
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            print(json.dumps({'peak_rss_bytes':rss,'elapsed':time.monotonic()-start,'error':code}),file=sys.stderr,flush=True)
    api._m18_semantic_response=observed
    api.main(['--config',config,'--port','0'])

def sequence(root,source):
    from urllib.parse import urlencode
    assert (root/'SYNTHETIC_TEST_ONLY').read_text() == 'v5.synthetic.memory-probe.v1\n', 'Synthetic fixture root required'
    def snapshot():return {str(p.relative_to(root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for folder in ('bundle','publication') for p in (root/folder).rglob('*') if p.is_file()}
    before=snapshot();desc=json.loads((root/'descriptor.json').read_text());route='/api/v4/manager/m18/v2';env=dict(os.environ,PYTHONPATH=source)
    log=root/('requests-'+Path(source).parent.name+'.txt')
    with log.open('w') as errors:
        process=subprocess.Popen([sys.executable,__file__,'serve',str(root/'config.json')],env=env,stdout=subprocess.PIPE,stderr=errors,text=True)
        url=process.stdout.readline().strip();requests=[];cursor=None
        try:
            for section in ['overview','summary','gaps','gaps-next','materials','empty','summary','gaps','materials','overview']:
                query={'run_id':RUN,'generation_id':desc['generation_id']}
                if section!='overview':query['section']='gaps' if section=='gaps-next' else section
                if section=='gaps-next':query['cursor']=cursor
                suffix='/overview' if section=='overview' else '/sections'
                started=time.monotonic()
                try:response=urlopen(url+route+suffix+'?'+urlencode(query),timeout=100)
                except HTTPError as error:response=error
                with response:raw=response.read();value=json.loads(raw);requests.append({'section':section,'status':response.status,'bytes':len(raw),'elapsed':time.monotonic()-started})
                print(json.dumps(requests[-1]),flush=True)
                if response.status!=200:break
                if section=='gaps':cursor=value['next_cursor']
        finally:process.terminate();process.wait(10)
    print(json.dumps({'files_unchanged':snapshot()==before,'requests':requests}),flush=True)
    print(log.read_text(),flush=True)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='prepare':prepare(Path(sys.argv[2]).resolve())
    elif mode=='serve':serve(sys.argv[2])
    else:sequence(Path(sys.argv[2]).resolve(),sys.argv[3])
