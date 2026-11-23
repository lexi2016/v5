"""Run the original V5 board HTTP check with only pinned backup inputs."""
import argparse,hashlib,json,os,stat,subprocess,sys,tempfile,zipfile
from contextlib import ExitStack
from pathlib import Path,PurePosixPath
H=Path(__file__).resolve().parent
MANIFEST_SHA='8294faa8011c6d805fbaa30e7d941833859a0f85e280a9e847116f626378c98b'
ROLES=('workflow','service','contract','patch')
PATCH='morning_board_wiring_20261123'
def sha(x):return hashlib.sha256(x).hexdigest()
def need(x,e):
    if not x:raise ValueError(e)
def path(s):
    p=PurePosixPath(s)
    need(p.parts and str(p)==s and '..' not in p.parts and not p.is_absolute() and chr(92) not in s,'PATH')
    return p
def pinned(p,ref):
    with p.open('rb') as f:
        a=os.fstat(f.fileno())
        need(stat.S_ISREG(a.st_mode) and a.st_size==ref['bytes'],'FILE_SIZE_TYPE')
        raw=f.read(ref['bytes']+1)
        b=os.fstat(f.fileno())
    need((a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_size,b.st_mtime_ns,b.st_ctime_ns) and len(raw)==ref['bytes'] and sha(raw)==ref['sha256'],'FILE_SHA')
    return raw
def extract(z,ref):
    name=str(path(ref['member']))
    zs=[x for x in z.infolist() if x.filename==name]
    need(len(zs)==1,'MEMBER_COUNT')
    x=zs[0]
    need(not x.is_dir() and stat.S_IFMT(x.external_attr>>16) in (0,stat.S_IFREG) and x.file_size==ref['bytes'] and 0<x.file_size<=30000,'MEMBER_TYPE_SIZE')
    b=z.read(x)
    need(len(b)==x.file_size and sha(b)==ref['sha256'],'MEMBER_SHA')
    return b
def run(a):
    raw=(H/'RESTORE_MANIFEST.json').read_bytes();need(sha(raw)==MANIFEST_SHA,'MANIFEST_SHA')
    m=json.loads(raw);need(m['schema']=='MORNING_BOARD_COLD_RESTORE_V1' and set(m['roles'])==set(ROLES) and len(m['files'])==9,'MANIFEST_SCOPE')
    from io import BytesIO
    with tempfile.TemporaryDirectory(prefix='cold_morning_board_') as tmp,ExitStack() as stack:
        root=Path(tmp);need(not list(root.iterdir()),'EMPTY_ROOT')
        archives={k:stack.enter_context(zipfile.ZipFile(BytesIO(pinned(getattr(a,k),m['roles'][k])))) for k in ROLES}
        for f in m['files']:
            p=root/path(f['destination'])
            p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as out:out.write(extract(archives[f['role']],f))
        f=m['exact_checker_receipt']
        with (root/path(f['destination'])).open('xb') as out:out.write(pinned(H/f['destination'],f))
        cwd=root/PATCH
        env={'PATH':os.environ['PATH'],'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8'}
        units=subprocess.run([sys.executable,'-B','-m','unittest','-q'],cwd=cwd,env=env,check=True,capture_output=True,text=True,timeout=20)
        original=subprocess.run([sys.executable,'-B','verify_original_http.py'],cwd=cwd,env=env,check=True,capture_output=True,timeout=20)
        evidence=json.loads(original.stdout)
        need('Ran 6 tests' in units.stderr and evidence['checks_passed']==6 and evidence['nodes']==21 and evidence['natural_verified_count']==0,'CHECK_TOTALS')
        need(evidence==json.loads((cwd/'HTTP_SMOKE_RECEIPT.json').read_bytes()),'ORIGINAL_READBACK_NOT_IDENTICAL')
    return {'schema':'MORNING_BOARD_COLD_RESTORE_RESULT_V1','manifest_sha256':MANIFEST_SHA,'four_verified_zip_carriers':len(ROLES),'exact_original_inputs':6,'empty_stage_root':True,'unit_tests':6,'http':evidence,'same_as_original_smoke_receipt':True,'production':False,'actual_0810_run':False,'remote_reuploads':0}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ROLES:p.add_argument('--'+k,required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(run(a),ensure_ascii=False,indent=2))
