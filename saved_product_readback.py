"""Read an already saved installation product through integrated ledger/assembly.

No business owner execution or manager publication is represented by this probe.
"""
import sys,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'V5/src'))
from v5_shadow.run_ledger import read_run,claim_run
from v5_shadow.daily_manager_assembly import product_reference
original=R.parent/'v5-ledger-r3-local'
rows=[]
for name in ['integrity-job','safe-retry-drill']:
    identity=json.loads((original/(name+'-identity.json')).read_text())
    state=read_run(R/'evidence/saved-ledger',identity)
    claim=claim_run(R/'evidence/saved-ledger',identity)
    assert claim['status']=='REUSED_SUCCESS' and claim['state']==state
    ref=product_reference({'state':state})
    assert hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()==ref['sha256']
    rows.append({'job':name,'run_id':state['latest_success']['run_id'],'attempt_count':len(state['attempts']),'product_reference':ref,'sha_verified':True,'reuse':claim['status'],'scope':'ACTUAL_SAVED_INSTALLATION_PRODUCT_NOT_STRATEGY_RESULT'})
print(json.dumps({'rows':rows,'manager_plan_status':'BLOCKED_BUSINESS_OWNER_PRODUCTS_NOT_ADMITTED','natural_verified':False},indent=2))
