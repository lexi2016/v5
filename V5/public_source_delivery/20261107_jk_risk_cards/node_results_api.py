"""Read existing manual records only. No owner calls, uploads or scheduler actions."""
import hashlib,json,pathlib,threading,importlib.util,datetime
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RECORD_DATE=None;SOURCE_DATE=None;ISO_SOURCE_DATE=None;PRIVATE_BINDINGS=None
ANNOTATION_SYMBOL=None;ANNOTATION_DATES=();HK_FINAL_KEY=None;RISK_CARD_COUNT=None
def require_bindings(node):
 def text(value):return isinstance(value,str) and bool(value.strip())
 def date(value,fmt):
  if not text(value):return False
  try:return datetime.datetime.strptime(value,fmt).strftime(fmt)==value
  except ValueError:return False
 if not date(RECORD_DATE,'%Y%m%d') or not date(SOURCE_DATE,'%Y%m%d') or not date(ISO_SOURCE_DATE,'%Y-%m-%d') or ISO_SOURCE_DATE.replace('-','')!=SOURCE_DATE or not isinstance(PRIVATE_BINDINGS,dict):raise ValueError('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING')
 roles={'jk-verify':{'jk_result','jk_observations'},'a-top200':{'consolidated_review'},'hk-continuous-close':{'hk_observations'},'hk-auction-final':{'hk_observations'},'opening-prep':{'group_review','ranking_provenance_source'},'morning-materials':{'source_cards','announcement_event','announcement_code','risk_cards'}}
 pins=PRIVATE_BINDINGS.get(node)
 if not isinstance(pins,dict) or not roles.get(node,{'receipt'}).issubset(pins):raise ValueError('PUBLIC_EXPORT_INCOMPLETE_NODE_BINDING')
 if node in {'hk-continuous-close','hk-auction-final'} and not text(HK_FINAL_KEY):raise ValueError('PUBLIC_EXPORT_INCOMPLETE_HK_BINDING')
 if node=='morning-materials' and (not text(ANNOTATION_SYMBOL) or not isinstance(ANNOTATION_DATES,(tuple,list)) or not ANNOTATION_DATES or any(not date(d,'%Y-%m-%d') for d in ANNOTATION_DATES)):raise ValueError('PUBLIC_EXPORT_INCOMPLETE_ANNOTATION_BINDING')
 if node=='morning-materials' and (type(RISK_CARD_COUNT)is not int or RISK_CARD_COUNT<=0):raise ValueError('INCOMPLETE_RISK_COUNT_BINDING')
 for pin in pins.values():
  if not isinstance(pin,dict) or not text(pin.get('path')) or type(pin.get('bytes')) is not int or not 0<pin['bytes']<256*1024 or not isinstance(pin.get('sha256'),str) or len(pin['sha256'])!=64 or any(c not in '0123456789abcdef' for c in pin['sha256']):raise ValueError('PUBLIC_EXPORT_INCOMPLETE_PIN_BINDING')
class NodeResultsService:
 def __init__(self,gate):self.gate=gate;self.lock=threading.Lock()
 def get(self,node,record_date):
  require_bindings(node)
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
    records[role]=json.loads(raw) if role in {'receipt','summary','source_cards','announcement_event','group_review','ranking_provenance_source','hk_observations','consolidated_review','jk_result','jk_observations','risk_cards'} else raw.decode('utf-8')
   if node=='jk-verify':
    result=records['jk_result']
    if result.get('source_date')!=ISO_SOURCE_DATE or any(result.get(k) is not False for k in ['source_admission','natural_verified','business_accepted']):raise ValueError('JK_SCOPE')
    cross=[x for x in result['comparisons'] if x['field']=='post_session_reference']
    if len(cross)!=1 or cross[0]['value'] is not None or cross[0]['status']!='CROSS_SEMANTIC_DISCREPANCY_UNRESOLVED':raise ValueError('JK_CROSS_SEMANTIC_CHANGE')
    self.gate()
    return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'HISTORICAL_JK_REFERENCE_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
   if node=='a-top200':
    review=records['consolidated_review']
    if review.get('data_date')!=ISO_SOURCE_DATE or review.get('scope')!='POST_CLOSE_RETROSPECTIVE_ONLY_NOT_1500_CAPTURE' or review.get('natural_verified') is not False or review.get('business_accepted') is not False or len(review.get('rows',[]))!=200:raise ValueError('CONSOLIDATED_REVIEW_SCOPE')
    if any(x.get('historical_PIT') is not False or x.get('source_admission') is not False or x.get('buy_eligibility')!='NOT_EVALUATED' for x in review['rows']):raise ValueError('CONSOLIDATED_REVIEW_QUALIFICATION')
    self.gate()
    return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'POST_CLOSE_RETROSPECTIVE_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
   if node in {'hk-continuous-close','hk-auction-final'}:
    hk=records['hk_observations']
    if hk.get('data_date')!=ISO_SOURCE_DATE or hk.get('mode')!='MANUAL_HISTORICAL_LOOKUP_NOT_NATURAL_CAPTURE' or any(hk.get(k) is not False for k in ['source_admission','natural_verified','business_accepted','production_allowed']):raise ValueError('HK_HISTORICAL_SCOPE')
    if not isinstance(hk.get('official_schedule'),dict) or HK_FINAL_KEY not in hk['official_schedule']:raise ValueError('HK_FINAL_FIELD_MISSING')
    if hk['official_schedule'][HK_FINAL_KEY] is not None:raise ValueError('HK_FINAL_REQUIRES_NEW_REVIEW')
    self.gate()
    return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'HISTORICAL_MEDIA_REFERENCE_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
   if node=='opening-prep':
    review=records['group_review'];provenance=records.pop('ranking_provenance_source')['ranking_provenance']
    if review.get('source_date')!=SOURCE_DATE or review.get('top_rows')!=200 or review.get('buy_qualification') is not False or review.get('natural_verified') is not False or any(x.get('no_buy') is not True for x in review['rows']):raise ValueError('GROUP_REVIEW_SCOPE')
    if provenance.get('source')!='G4' or provenance.get('historical_PIT') is not False or provenance.get('source_admission') is not False:raise ValueError('RANKING_PROVENANCE')
    records['ranking_provenance']=provenance;self.gate()
    return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'HISTORICAL_REVIEW_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
   if node=='morning-materials':
    cards=records['source_cards']
    if cards.get('source_date')!=ISO_SOURCE_DATE or cards.get('mode')!='HISTORICAL_TEXT_ASSOCIATION_ONLY' or cards.get('natural_verified') is not False or cards.get('business_accepted') is not False:raise ValueError('CARDS_SCOPE_CHANGED')
    provenance=cards.get('ranking_provenance',{})
    if provenance.get('source')!='G4' or provenance.get('historical_PIT') is not False or provenance.get('source_admission') is not False:raise ValueError('PIT_PROVENANCE_MISSING_OR_CHANGED')
    code_path=ROOT/pins[node]['announcement_code']['path']
    spec=importlib.util.spec_from_file_location('announcement_name_annotation',code_path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    event=records['announcement_event']
    if event.get('symbol')!=ANNOTATION_SYMBOL or event.get('production_applied') is not False or event.get('risk_formula_changed') is not False:raise ValueError('ANNOUNCEMENT_SCOPE')
    records['announcement_annotations']={date+'|'+stage:module.annotate(event,event['symbol'],date,stage) for date in ANNOTATION_DATES for stage in ['PRE_OPEN','AFTER_OPEN','UNKNOWN']}
    records.pop('announcement_code')
    risk=records['risk_cards']
    if risk.get('source_date')!=ISO_SOURCE_DATE or risk.get('new_top200_verified_members')!=0 or len(risk.get('cards',[]))!=RISK_CARD_COUNT or any(c.get('publication_time')!='UNKNOWN' or c.get('top200_member') is not False or c.get('historical_PIT') is not False or c.get('source_admission') is not False or c.get('natural_verified') is not False for c in risk['cards']):raise ValueError('RISK_CARD_SCOPE')
    self.gate()
    return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'HISTORICAL_ASSOCIATION_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
   receipt=records['receipt']
   if receipt.get('natural_verified') is not False or receipt.get('exit_code')!=0:raise ValueError('RECEIPT_SCOPE_CHANGED')
   self.gate()
   return {'schema':'EXISTING_MANUAL_NODE_RESULT_V1','node_id':node,'record_date':record_date,'source_date':SOURCE_DATE,'trigger_type':'MANUAL_ONLY','natural_verified':False,'delivery_status':'NOT_SENT','business_acceptance':'NOT_GRANTED','records':records,'source_pins':pins[node]}
  finally:self.lock.release()
