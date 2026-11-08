"""Reconcile observed facts only; no feed capture, admission, ranking or production writes."""
import argparse,hashlib,json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

def reconcile(doc,day):
 if doc['source_day']!=day: raise ValueError('SOURCE_DAY_MISMATCH')
 groups=defaultdict(list);ids=set()
 for r in doc['records']:
  if r['id'] in ids: raise ValueError('DUPLICATE_OBSERVATION')
  ids.add(r['id'])
  if r['source_date']!=day:raise ValueError('MIXED_SOURCE_DAY')
  n=Decimal(r['value'])
  if not n.is_finite() or n<=0:raise ValueError('INVALID_VALUE')
  if not r['url'].startswith('https://'):raise ValueError('SOURCE_URL_REQUIRED')
  groups[(r['symbol'],r.get('comparison_group',r['field']))].append(r)
 out=[]
 for (symbol,field),rows in sorted(groups.items()):
  values=sorted({Decimal(r['value']) for r in rows});source_fields=sorted({r['field'] for r in rows});same_semantics=len(source_fields)==1;agree=len(values)==1 and same_semantics
  out.append({'symbol':symbol,'field':field,'source_fields':source_fields,'status':('CROSS_SEMANTIC_DISCREPANCY_UNRESOLVED' if not same_semantics else ('OBSERVED_VALUES_AGREE' if agree else 'CONFLICT_UNRESOLVED')),'value':str(values[0]) if agree else None,'observed_values':[str(v) for v in values],'source_ids':[r['id'] for r in rows]})
 return {'source_date':day,'node':'jk-verify','comparisons':out,'source_admission':False,'natural_verified':False,'business_accepted':False,'gaps':['original node producer/binding not recovered here','no 08:00-08:10 capture or delivery receipt','exchange primary KOSPI not acquired','KOSPI latest/reference versus reported-close discrepancy unresolved','source timezone not fully confirmed','no live lookahead-safe intraday snapshot','no browser/dashboard integration']}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--sha256',required=True);a.add_argument('--day',required=True);a.add_argument('--output',type=Path,required=True);x=a.parse_args()
 raw=x.input.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=x.sha256:a.exit(2,'INPUT_HASH_MISMATCH\n')
 try:r=reconcile(json.loads(raw),x.day)
 except (ValueError,KeyError) as e:a.exit(2,str(e)+'\n')
 with x.output.open('x') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps(r))
