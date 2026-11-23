"""Produce Friday research raw price/volume evidence from original pinned TDX daily releases."""
import hashlib, io, json, math, sys, types, zipfile
from pathlib import Path
out=Path(__file__).resolve().parent
source=out.parent/'d20_actual_candidate_restore_20261122'
def sha(b): return hashlib.sha256(b).hexdigest()
def pin(b, expected_size, expected_sha):
    if (len(b),sha(b))!=(expected_size,expected_sha):
        raise ValueError('PIN_MISMATCH')
    return b
loc_file=(source/'CALCULATION_KERNEL_RECOVERY_LOCATORS.json').read_bytes()
if sha(loc_file)!='75eb95e2244a894dad0ed2a86f0dc89e631b45fabe04558c950e0800912df74b':
    raise ValueError('LOCATOR_PIN')
loc=json.loads(loc_file)['locators']
m=(source/'D20_NATIVE_RESIDUAL_199_SOURCE_MAP_20261122.json').read_bytes()
if sha(m)!='6f3fc790eeb68f7f13a8847e2ee787ae6b56e0d9eb44fc366f267a9eac740b4f':
    raise ValueError('SCOPE_PIN')
spec=loc['numeric.g4_parser']['input_ref']
parser=types.ModuleType('pinned_tdx_g4')
p=source/'candidate_kernel_source'/spec['path']
exec(compile(pin(p.read_bytes(),spec['bytes'],spec['sha256']),str(p),'exec'),parser.__dict__)
def load(key, day):
    l=loc['numeric.'+key]['remote_index_members'][0]
    carrier=pin((source/'exact_sources'/(key+'.zip')).read_bytes(),l['archive_bytes'],l['archive_sha256'])
    with zipfile.ZipFile(io.BytesIO(carrier)) as z:
        if z.namelist().count(l['member'])!=1: raise ValueError('NONUNIQUE_MEMBER')
        payload=pin(z.read(l['member']),l['member_bytes'],l['member_sha256'])
    data,_=parser.parse_package(payload,day)
    return data,dict(data_date=day,sha256=sha(payload),bytes=len(payload),archive_sha256=sha(carrier))
prior, prior_info=load('g4_prior',20261119)
target, target_info=load('g4_target',20261120)
def bar(raw):
    if raw is None:
        return None
    parsed, ref, shares=raw
    cols={k:parsed[k] for k in ('open','high','low','close','amount')}
    if any(not math.isfinite(x) or x<=0 for x in cols.values()) or shares<=0:
        return None
    return dict(**cols,actual_shares=shares,reference_close=ref)
rows=[]
for row in json.loads(m)['rows']:
    code, market=row['symbol'].split('.')
    key={'SZ':0,'SH':1,'BJ':2}[market],code
    rows.append(dict(symbol=row['symbol'],native_route=row['route'],prior=bar(prior.get(key)),target=bar(target.get(key)),
                     full_history_native_recovered=False,formal=False))
doc=dict(schema='TDX_D20_199_OFFICIAL_DAILY_ONLY',state='READ_BACK_DAILY_NOT_FULL_HISTORY',
    scope_sha256=sha(m),scope=len(rows),d20_usable=sum(r['target'] is not None for r in rows),
    d19_and_d20_usable=sum(r['prior'] is not None and r['target'] is not None for r in rows),
    full_history_native_recovered=0,new_par_calculations=0,formal=False,sources=[prior_info,target_info],rows=rows)
with (out/'OFFICIAL_DAILY_199_RESEARCH_ONLY.json').open('x') as f:
    json.dump(doc,f,allow_nan=False,indent=2,ensure_ascii=False)
print(json.dumps({k:v for k,v in doc.items() if k!='rows'},ensure_ascii=False,indent=2))
