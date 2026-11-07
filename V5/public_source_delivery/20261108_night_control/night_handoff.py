"""Local user handoff only. No collector, research result, scheduler or delivery."""
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
        prompt=f'请为业务日 {date} 的北京时间 {period} 节点整理{focus}。所附200只名单来源日期 {source_date}，仅为研究范围，不代表当前选股、盘前可知名单、人工图审或交易资格。保留全部代码及完整分母，不重新选股或评分。逐股返回官方原件链接、标题、披露日、精确发布时间及时区、当时可得性、原文页码或段落、事实、推断、反证和缺件。夜间业务映射不能将题材关联当收入贡献，框架协议不能当已兑现订单；公告未匹配不代表无事项。未知填UNKNOWN，冲突分列。公告及外部研究由用户处理；本程序只生成名单和本prompt，不请求外站、不发送、不交易。'
        report={'schema':'NIGHT_MATERIAL_USER_HANDOFF_V1','node':node,'run_id':run_id,'environment_id':environment_id,'target_date':date,'list_date':source_date,'list_sha256':sha(raw),'code_sha256':sha(pathlib.Path(__file__).read_bytes()),'safeio_sha256':SAFE_SHA,'list_csv':out.getvalue(),'prompt':prompt,'count':200,'status':'BLOCKED_RESEARCH_HANDOFF_READY','source_admission':'UNKNOWN','pit_verified':False,'current_selection_verified':False,'business_accepted':False,'natural_verified':False,'source_calls':0,'delivery_status':'NOT_SENT','uploaded':False}
        report['identity']=s.sha(s.canonical(report))
        gate()
        if s.local_bytes(r['root'],r['list_path'])!=raw: raise ValueError('LIST_CHANGED_BEFORE_SAVE')
        saved=s.freeze(r['output'],report)
        return {'report':report,'save':saved}
