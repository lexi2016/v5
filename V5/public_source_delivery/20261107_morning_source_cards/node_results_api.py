"""Read existing manual records only. No owner calls, uploads or scheduler actions."""
import hashlib,json,pathlib,threading
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RECORD_DATE=None;SOURCE_DATE=None;CARD_SOURCE_DATE=None;PRIVATE_BINDINGS=None
class NodeResultsService:
 def __init__(self,gate):self.gate=gate;self.lock=threading.Lock()
 def get(self,node,record_date):
  if RECORD_DATE is None or PRIVATE_BINDINGS is None:raise ValueError('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING')
  if record_date!=RECORD_DATE:raise ValueError('NO_RECORD_FOR_DATE')
  pins=PRIVATE_BINDINGS
  if node not in pins:raise ValueError('NO_NODE_RECORD')
  if not self.lock.acquire(timeout=95):raise ValueError('RESOURCE_BUSY')
  try:
   if hasattr(self.gate,'start'):self.gate.start()
   self.gate();records={}
   for role,pin in pins[node].items():
    path=ROOT/pin['path']
    if path.is_symlink() or not path.resolve().is_relative_to(ROOT) or not 0<pin['bytes']<256*1024:raise ValueError('SOURCE_PATH_OR_SIZE')
    with path.open('rb') as f:raw=f.read(pin['bytes']+1)
    if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('SOURCE_PIN_CHANGED')
    records[role]=json.loads(raw) if role in {'receipt','summary','source_cards'} else raw.decode('utf-8')
   if node=='morning-materials':
    cards=records['source_cards']
    if cards.get('source_date')!=CARD_SOURCE_DATE or cards.get('mode')!='HISTORICAL_TEXT_ASSOCIATION_ONLY' or cards.get('natural_verified') is not False or cards.get('business_accepted') is not False:raise ValueError('CARDS_SCOPE_CHANGED')
    self.gate()
    return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'HISTORICAL_ASSOCIATION_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
   receipt=records['receipt']
   if receipt.get('natural_verified') is not False or receipt.get('exit_code')!=0:raise ValueError('RECEIPT_SCOPE_CHANGED')
   self.gate()
   return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'MANUAL_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
  finally:self.lock.release()
