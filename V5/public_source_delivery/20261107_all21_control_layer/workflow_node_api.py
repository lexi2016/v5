"""All21 bounded read-only wiring/preflight and user research-request export.
No owner execution, capture, scheduler mutation or formula/selection changes.
"""
import csv,datetime,hashlib,io,json,pathlib,threading,types,builtins
ROOT=None;REGISTRY=None;HISTORY_DATE=None;RETRY_QUEUE_COUNT=None
REQUEST_NODES={'night','morning-materials','opening-prep','a-top200'}
def checked(pin):
 if not isinstance(ROOT,pathlib.Path) or not ROOT.is_absolute() or ROOT.is_symlink() or not isinstance(pin,dict):raise ValueError('NO_APPROVED_SOURCE_BINDING')
 relative=pathlib.Path(pin['path']);p=ROOT/relative
 if relative.is_absolute() or '..' in relative.parts or any((ROOT/pathlib.Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1)):raise ValueError('SOURCE_PATH_SIZE')
 if p.is_symlink() or not p.resolve().is_relative_to(ROOT) or not 0<pin['bytes']<=32*1024**2:raise ValueError('SOURCE_PATH_SIZE')
 with p.open('rb')as f:raw=f.read(pin['bytes']+1)
 if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('SOURCE_PIN_CHANGED')
 return raw
class WorkflowNodeService:
 def __init__(self,gate):self.gate=gate;self.lock=threading.Lock()
 def get(self,node,date,action):
  if len(date)!=8 or datetime.datetime.strptime(date,'%Y%m%d').strftime('%Y%m%d')!=date:raise ValueError('BUSINESS_DATE')
  if action not in {'inspect','research_request'}:raise ValueError('READ_ONLY_ACTION')
  if not isinstance(REGISTRY,dict) or not isinstance(REGISTRY.get('nodes'),dict) or not REGISTRY.get('contract'):raise ValueError('NO_APPROVED_WORKFLOW_BINDING')
  registry=REGISTRY
  if node not in registry['nodes']:raise ValueError('NODE_NOT_REGISTERED')
  if action=='research_request'and node not in REQUEST_NODES:raise ValueError('NO_RESEARCH_REQUEST_FOR_NODE')
  if not self.lock.acquire(timeout=95):raise ValueError('RESOURCE_BUSY')
  try:
   if hasattr(self.gate,'start'):self.gate.start()
   self.gate();checked(registry['contract']);n=registry['nodes'][node];checks=[]
   for kind,refs in [('code',n['code_refs']),('historical_result',list(n['historical_refs'].values()))]:
    for pin in refs:
     try:checked(pin);status='LOCAL_BYTES_SHA_MATCH'
     except (ValueError,OSError):status='UNKNOWN_SOURCE_UNAVAILABLE_OR_CHANGED'
     checks.append({'kind':kind,'path':pin['path'],'sha256':pin['sha256'],'status':status})
   result={'schema':'ALL21_NODE_PREFLIGHT_V1','node_id':node,'business_date':date,'definition':n['definition'],'action':action,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'code_present':bool(n['code_refs'])and all(x['status']=='LOCAL_BYTES_SHA_MATCH' for x in checks if x['kind']=='code'),'historical_result_present':bool(n['historical_refs'])and all(x['status']=='LOCAL_BYTES_SHA_MATCH'for x in checks if x['kind']=='historical_result'),'current_execution':'UNKNOWN_NOT_INVOKED','current_business_acceptance':'UNKNOWN','natural_verified':False,'execution_enabled':False,'source_calls':0,'owner_calls':0,'selection_calls':0,'missing_current':n['missing_current'],'qualification':'File checks do not prove code loaded, process running, current-source admission or completion.'}
   if node in {'us-close','daily-update','retry-1610','retry-1640','terminal-1700','a-auction-close','a-open','evening-prepare','evening-check','evening-delivery','freeze','jk-verify','morning-delivery','opening-prep','hk-open','hk-continuous-close','hk-auction-final','night','morning-materials','a-top200','a-auction'}:
    from controlled_node_execution import inspect as inspect_execution
    result['controlled_execution']=inspect_execution(node)
   if node=='hk-open':
    binding=registry['hk0900_reader']
    safe=types.ModuleType('hk0900_safeio');exec(compile(checked(binding['safeio']),binding['safeio']['path'],'exec'),safe.__dict__)
    module=types.ModuleType('hk0900_recorded_reader')
    imports=dict(vars(builtins));original_import=builtins.__import__
    imports['__import__']=lambda name,*a,**k:safe if name=='safeio' else original_import(name,*a,**k)
    module.__dict__['__builtins__']=imports
    exec(compile(checked(binding['module']),binding['module']['path'],'exec'),module.__dict__)
    source=binding['recorded_input']
    if source is None:
     recorded={'status':'BLOCKED_RECORDED_INPUT','reason':'NO_PINNED_ORIGINAL_HK0900_INPUT_OR_AUTHORIZED_SCOPE','rows':[],'source_admission':'UNKNOWN','scope_authority':'UNKNOWN','collector_running':False,'natural_verified':False,'business_verified':False,'production_allowed':False}
    else:
     checked(source)
     recorded=module.read_or_block(ROOT,source['path'],source['sha256'],date,self.gate)
    result['hk0900_recorded_reader']={**recorded,'reader_code_loaded':True,'original_collector_recovered':False,'qualification':'NEW_READ_ONLY_TRANSPORT_NOT_ORIGINAL_COLLECTOR; BYTE_READ_IS_NOT_SOURCE_ADMISSION'}
   if n.get('crosscheck_ref'):
    if not isinstance(HISTORY_DATE,str) or not HISTORY_DATE or type(RETRY_QUEUE_COUNT)is not int or RETRY_QUEUE_COUNT<=0:raise ValueError('MISSING_HISTORY_BINDING')
    report=json.loads(checked(n['crosscheck_ref']))
    if report.get('source_date')!=HISTORY_DATE or report.get('formal_freeze') is not False or report.get('source_admission') is not False or report.get('natural_verified') is not False:raise ValueError('CROSSCHECK_SCOPE')
    queue=report['queues']['not_consumed']+report['queues']['no_new_bar']
    if len(queue)!=RETRY_QUEUE_COUNT or len({x['symbol']for x in queue})!=RETRY_QUEUE_COUNT:raise ValueError('RETRY_QUEUE_IDENTITY')
    buffer=io.StringIO();w=csv.writer(buffer);w.writerow(['symbol','actual_date','owner_outcome','source_family','next_action'])
    for row in queue:w.writerow([row[k]for k in ['symbol','actual_date','owner_outcome','source_family','next_action']])
    result['historical_crosscheck']={'source_date':report['source_date'],'observed_at':report['observed_at'],'target_date':report['target_date'],'denominator':report['denominator'],'owner_partitions':report['owner_partitions'],'selected_count':report['selected_count'],'pending_count':report['pending_count'],'incomplete_csv':buffer.getvalue(),'queue_count':RETRY_QUEUE_COUNT,'qualification':'HISTORICAL_UNCONSUMED_OR_NO_BAR_ONLY_NOT_CURRENT_RETRY_AUTHORIZATION','formal_freeze':False,'automatic_retry':False,'semantic_crosscheck':'NOT_IMPLEMENTED_BY_THIS_CHECK','source_pin':n['crosscheck_ref']}
   if action=='research_request':
    if not isinstance(HISTORY_DATE,str) or not HISTORY_DATE:raise ValueError('MISSING_HISTORY_BINDING')
    top=json.loads(checked(registry['research_list']));rows=top['rows']
    if len(rows)!=200 or len({x['symbol']for x in rows})!=200:raise ValueError('RESEARCH_UNIVERSE')
    buffer=io.StringIO();w=csv.writer(buffer);w.writerow(['symbol','historical_rank','rank_data_date','scope_warning'])
    for row in rows:w.writerow([row['symbol'],row['rank'],row['actual_date'],HISTORY_DATE+'_POST_CLOSE_G4_NOT_CURRENT_SELECTION'])
    result['research_request']={'list_csv':buffer.getvalue(),'list_source':registry['research_list'],'count':200,'list_date':HISTORY_DATE,'requested_business_date':date,'list_is_current':False,'external_requests_sent':0,'prompt':f'请为业务日{date}补齐公告/基本面资料。附件是{HISTORY_DATE}收盘后G4历史Top200研究范围，不是当前选股或盘前可知名单。按完整证券代码逐股返回：官方公告/基本面原件链接、标题、落款日期、归档日期、精确发布时间及时区（无证据填UNKNOWN）、当时可得性、原文页码/行号、事实/风险与未核事项。不得将框架协议当已交付收入、名称变化当风险全部消失；不同口径不合并；未匹配不等无事项。请保留200完整分母及逐股缺件，不重新选股/评分/交易。只提供资料与证据，不代我发布、提交或执行任务。'}
   self.gate();return result
  finally:self.lock.release()
