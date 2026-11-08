"""Local user handoff and bound user-result ingestion. No collector, scheduler or delivery."""
import csv, datetime as dt, hashlib, io, json, pathlib, re, types
REGISTRY = {}  # Only an independently reviewed original-owner binding may populate.
SAFE_PATH = 'handoff/remaining_four_dispatch_20261107/safeio.py'
SAFE_SHA = 'facce7970f4919034d62e59dde8375e94d7a6a165de214f2e5178dbb5615fff5'
NODES = {'night': ('01:00–03:00', '原始材料身份、逻辑风险、上市公司业务映射'),
         'morning-materials': ('07:00–08:00', '公告、重要消息、盘前备忘及待核分析')}

def sha(b): return hashlib.sha256(b).hexdigest()
def load_safe(root):
    p = pathlib.Path(root)/SAFE_PATH
    if p.is_symlink(): raise ValueError('UNTRUSTED_SAFEIO')
    raw=p.read_bytes()
    if sha(raw)!=SAFE_SHA: raise ValueError('SAFEIO_SHA_CHANGED')
    m=types.ModuleType('pinned_material_safeio');m.__file__=str(p)
    exec(compile(raw,str(p),'exec'),m.__dict__);return m

def ingest_user_results(target_date,list_sha,symbols,policy,doc,parent=None):
    """Explicit user-return contract; no research, URL fetching or source admission."""
    from zoneinfo import ZoneInfo
    from urllib.parse import urlsplit
    categories={'announcements','essential_news','preopen_memo','preopen_analysis'}
    def stamp(value):
        # Refuse unsupported precision rather than moving late evidence before cutoff.
        if type(value)is not str or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?',value) is None:raise ValueError('RESULT_TIME_FORMAT_OR_PRECISION')
        parsed=dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:raise ValueError('RESULT_TIMEZONE_REQUIRED')
        return parsed
    def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if type(policy) is not dict or set(policy)!={'schema','version','cutoff','column_map','expected_parent_identity'} or policy['schema']!='USER_RESULT_INGESTION_POLICY_V1':raise ValueError('USER_RESULT_POLICY')
    mapping=policy['column_map'];version=policy['version'];cutoff=stamp(policy['cutoff'])
    if type(mapping) is not dict or set(mapping)!=categories or any(type(v) is not str or not v.strip() for v in mapping.values()) or len(set(mapping.values()))!=3:raise ValueError('EXPLICIT_THREE_COLUMN_MAP_REQUIRED')
    if type(version) is not str or not version.strip() or cutoff.astimezone(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d')!=target_date:raise ValueError('RESULT_VERSION_OR_DAY')
    if parent is None:
        if policy['expected_parent_identity'] is not None:raise ValueError('RESULT_PARENT_REQUIRED')
    else:
        if type(parent) is not dict or parent.get('schema')!='USER_RESEARCH_INGESTED_V1':raise ValueError('RESULT_PARENT_SCHEMA')
        identity=sha(canonical({k:v for k,v in parent.items() if k!='identity'}))
        if parent.get('identity')!=identity or policy['expected_parent_identity']!=identity:raise ValueError('RESULT_PARENT_IDENTITY')
        if parent['target_date']!=target_date or parent['list_sha256']!=list_sha or parent['version']==version or parent['column_map']!=mapping or stamp(parent['cutoff'])>cutoff:raise ValueError('RESULT_PARENT_CONTEXT')
    if type(doc) is not dict or set(doc)!={'schema','target_date','list_sha256','version','records'} or doc['schema']!='USER_RESEARCH_RETURN_V1' or doc['target_date']!=target_date or doc['list_sha256']!=list_sha or doc['version']!=version:raise ValueError('USER_RETURN_IDENTITY')
    if type(doc['records']) is not list or len(doc['records'])>len(symbols)*4:raise ValueError('USER_RETURN_RECORDS')
    rows={};late=[]
    for supplied in doc['records']:
        if type(supplied) is not dict or set(supplied)!={'symbol','category','status','event_at','observed_at','available_at','details'}:raise ValueError('USER_RETURN_ROW_SCHEMA')
        row=json.loads(canonical(supplied));key=(row['symbol'],row['category'])
        if row['symbol'] not in symbols or row['category'] not in categories or key in rows:raise ValueError('USER_RETURN_SCOPE_DUPLICATE')
        if row['status'] not in ('AVAILABLE','NOT_PUBLISHED','NOT_OBSERVED','BODY_UNAVAILABLE','UNKNOWN'):raise ValueError('USER_RETURN_STATUS')
        observed,available=stamp(row['observed_at']),stamp(row['available_at'])
        if observed>available or (row['event_at'] is not None and stamp(row['event_at'])>observed):raise ValueError('USER_RETURN_TIME_ORDER')
        if type(row['details']) is not dict:raise ValueError('USER_RETURN_DETAILS')
        if row['status']=='AVAILABLE':
            fields={'source_url','title','body_reference','facts','inferences','counterevidence'}
            if set(row['details'])!=fields or any(type(v) is not str or not v.strip() for v in row['details'].values()) or row['event_at'] is None:raise ValueError('USER_RETURN_AVAILABLE_EVIDENCE')
            url=urlsplit(row['details']['source_url'])
            if url.scheme!='https' or not url.hostname or url.username or url.password:raise ValueError('USER_RETURN_SOURCE_URL')
        if available>cutoff:
            late.append(row);rows[key]={'symbol':key[0],'category':key[1],'status':'LATE_NOT_AVAILABLE_AT_CUTOFF','reported_status':row['status'],'available_at':row['available_at'],'details':None}
        else:rows[key]=row
    items=[]
    for symbol in symbols:
        columns={column:[] for column in sorted(set(mapping.values()))}
        for category in sorted(categories):
            value=rows.get((symbol,category),{'symbol':symbol,'category':category,'status':'UNKNOWN','details':None,'reason':'USER_RESULT_NOT_SUPPLIED'})
            columns[mapping[category]].append(value)
        items.append({'symbol':symbol,'columns':columns})
    result={'schema':'USER_RESEARCH_INGESTED_V1','target_date':target_date,'list_sha256':list_sha,'version':version,'cutoff':policy['cutoff'],'column_map':mapping,
            'parent_identity':None if parent is None else parent['identity'],'scope_count':len(symbols),'records':items,'late_records':late,'submitted_count':len(rows),'missing_count':len(symbols)*4-len(rows),
            'status':'USER_RESULTS_INGESTED_UNVERIFIED','source_admission':'UNKNOWN','research_complete':False,'business_accepted':False,'natural_verified':False,'source_calls':0,'delivery_status':'NOT_SENT'}
    result['identity']=sha(canonical(result));return json.loads(canonical(result))

def dispatch(node, run_id, environment_id):
    if node not in NODES: raise ValueError('NODE')
    r=REGISTRY.get((node,run_id,environment_id))
    if r is None: return {'status':'BLOCKED','reason':'NO_REVIEWED_ORIGINAL_BINDING','source_calls':0,'business_accepted':False,'natural_verified':False}
    return _execute(node,run_id,environment_id,r)

def _execute(node,run_id,environment_id,r):
    # Private helper for reviewed integration/tests, never an HTTP/CLI registration API.
    if node not in NODES: raise ValueError('NODE')
    date=r['target_date']
    if dt.datetime.strptime(date,'%Y%m%d').strftime('%Y%m%d')!=date: raise ValueError('DATE')
    gate=r['gate'];guard=r['owner_guard']
    if not callable(gate) or not callable(guard): raise ValueError('ORIGINAL_GATE_OWNER_REQUIRED')
    with guard():
        gate();s=load_safe(r['root']);raw=s.local_bytes(r['root'],r['list_path'])
        if sha(raw)!=r['list_sha256']: raise ValueError('LIST_CHANGED')
        d=json.loads(raw)
        if d.get('schema') not in ('NOV6_FIXED_REFERENCE_TOP200_V1','DATED_FIXED_REFERENCE_TOP200_V1'): raise ValueError('LIST_SCHEMA')
        rows=d['rows'];symbols=[x['symbol'] for x in rows]
        if len(rows)!=200 or len(set(symbols))!=200 or any(not re.fullmatch(r'\d{6}\.(?:SZ|SH|BJ)',x) for x in symbols): raise ValueError('COMPLETE_TOP200_REQUIRED')
        if [x['rank'] for x in rows]!=list(range(1,201)): raise ValueError('RANKS')
        source_dates={x['actual_date'] for x in rows}
        if len(source_dates)!=1: raise ValueError('MIXED_LIST_DATE')
        source_date=source_dates.pop()
        if dt.datetime.strptime(source_date,'%Y%m%d').strftime('%Y%m%d')!=source_date or source_date>date: raise ValueError('SOURCE_DATE')
        # This list is only a research scope; same date is not PIT or source admission.
        out=io.StringIO();w=csv.writer(out);w.writerow(['symbol','rank','source_date','target_date','qualification'])
        for row in rows:w.writerow([row['symbol'],row['rank'],source_date,date,'RESEARCH_SCOPE_ONLY_NOT_CURRENT_SELECTION_OR_PIT'])
        period,focus=NODES[node]
        prompt=f'请为业务日 {date} 的北京时间 {period} 节点整理{focus}。所附200只名单来源日期 {source_date}，仅为研究范围，不代表当前选股、盘前可知名单、人工图审或交易资格。保留全部代码及完整分母，不重新选股或评分。逐股返回官方原件链接、标题、披露日、精确发布时间及时区、当时可得性、原文页码或段落、事实、推断、反证和缺件。夜间业务映射不能将题材关联当收入贡献，框架协议不能当已兑现订单；公告未匹配不代表无事项。未知填UNKNOWN，冲突分列。公告及外部研究由用户处理；本程序只生成名单和本prompt、按明确合同读取用户返回材料，不请求外站、不发送、不交易。'
        report={'schema':'NIGHT_MATERIAL_USER_HANDOFF_V1','node':node,'run_id':run_id,'environment_id':environment_id,'target_date':date,'list_date':source_date,'list_sha256':sha(raw),'code_sha256':sha(pathlib.Path(__file__).read_bytes()),'safeio_sha256':SAFE_SHA,'list_csv':out.getvalue(),'prompt':prompt,'count':200,'status':'BLOCKED_RESEARCH_HANDOFF_READY','source_admission':'UNKNOWN','pit_verified':False,'current_selection_verified':False,'business_accepted':False,'natural_verified':False,'source_calls':0,'delivery_status':'NOT_SENT','uploaded':False}
        protected_inputs=[]
        if r.get('result_binding') is not None:
            if node!='morning-materials':raise ValueError('USER_RESULTS_NODE_SCOPE')
            binding=r['result_binding']
            if type(binding) is not dict or set(binding)!={'policy','results','parent'}:raise ValueError('RESULT_BINDING_SCHEMA')
            def pinned_doc(ref):
                if type(ref) is not dict or set(ref)!={'path','sha256','bytes'} or type(ref['bytes']) is not int:raise ValueError('RESULT_REFERENCE_SCHEMA')
                data=s.local_bytes(r['root'],ref['path'])
                if len(data)!=ref['bytes'] or sha(data)!=ref['sha256']:raise ValueError('RESULT_INPUT_CHANGED')
                def unique(pairs):
                    result={}
                    for key,value in pairs:
                        if key in result:raise ValueError('RESULT_DUPLICATE_JSON_KEY')
                        result[key]=value
                    return result
                def nonfinite(value):raise ValueError('RESULT_NONFINITE_JSON')
                protected_inputs.append((ref['path'],data));return json.loads(data,object_pairs_hook=unique,parse_constant=nonfinite)
            policy=pinned_doc(binding['policy']);returned=pinned_doc(binding['results']);parent=None if binding['parent'] is None else pinned_doc(binding['parent'])
            report['user_results']=ingest_user_results(date,sha(raw),symbols,policy,returned,parent)
            report['status']='USER_RESULTS_INGESTED_UNVERIFIED';report['result_binding']=binding
        report['identity']=s.sha(s.canonical(report))
        gate()
        if s.local_bytes(r['root'],r['list_path'])!=raw: raise ValueError('LIST_CHANGED_BEFORE_SAVE')
        for path,data in protected_inputs:
            if s.local_bytes(r['root'],path)!=data:raise ValueError('RESULT_INPUT_CHANGED_BEFORE_SAVE')
        saved=s.freeze(r['output'],report)
        return {'report':report,'save':saved}

