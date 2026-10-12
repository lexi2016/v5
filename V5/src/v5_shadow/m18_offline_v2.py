"""M18 v2 offline resource contract; stdlib JSON semantics, no owner execution.

Memory is a measured rejection gate, not hard isolation. Canonical sources are
parsed sequentially, never as two live JSON trees. v1 is deliberately unchanged.
"""
import base64
import hashlib
import json
import resource
import sys
import time
from types import MappingProxyType
from . import m18_offline_pages as v1

ContractError = v1.ContractError
Bundle = v1.Bundle
require = v1.require
sha = v1.sha
VERSION = 'v5.m18.offline.v2'
PROFILE = MappingProxyType(dict(
    id='m18.offline.budget.v2.1', object_bytes=16*1024*1024,
    generation_bytes=64*1024*1024, object_nodes=200000,
    response_nodes=1500000, saved_nodes=1500000, input_nodes=3000000,
    metadata_nodes=500000, logical_nodes=2000000, depth=64,
    entries=10000, records=10000, string_token_bytes=32*1024*1024,
    key_bytes=1024, scalar_bytes=128, chunk_bytes=256*1024,
    detail_items=32, index_items=512, rss_bytes=512*1024*1024,
    cpu_seconds=60, wall_seconds=90))
PROFILE_SHA256 = sha(v1.canonical(dict(PROFILE)))


def profile_check(pin):
    require(type(pin) is str and pin == PROFILE_SHA256, 'V2_PROFILE_PIN')


def enforce_usage(usage):
    for key, limit in [('peak_rss_bytes',PROFILE['rss_bytes']),
                       ('cpu_seconds',PROFILE['cpu_seconds']),
                       ('wall_seconds',PROFILE['wall_seconds'])]:
        value = usage.get(key)
        require(type(value) in (int,float) and 0 <= value <= limit,
                'V2_RESOURCE_' + key.upper())


class ResourceGuard:
    """Process high-water RSS and operation CPU/wall, checkpoint enforced."""
    def __init__(self):
        self.start = time.monotonic()
        self.cpu_start = time.process_time()
        self.scan_nodes = 0
        self.scan_bytes = 0
        self.stages = []
        self.checkpoint()

    def usage(self):
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Darwin exposes bytes; Linux exposes KiB. Reject unsupported hosts.
        require(sys.platform in ('darwin','linux'), 'V2_RESOURCE_PLATFORM')
        return dict(peak_rss_bytes=rss if sys.platform=='darwin' else rss*1024,
                    cpu_seconds=time.process_time()-self.cpu_start,
                    wall_seconds=time.monotonic()-self.start,
                    scan_nodes=self.scan_nodes, scan_bytes=self.scan_bytes)

    def checkpoint(self, stage=None):
        value = self.usage()
        enforce_usage(value)
        if stage is not None:
            self.stages.append(dict(stage=stage, **value))
        return value


class Ledger:
    """Cumulative generation budgets, separate from repeated execution work."""
    def __init__(self):
        self.counts = dict(input_nodes=0,metadata_nodes=0,logical_nodes=0,
                           stored_bytes=0,records=0)

    def charge(self, name, amount, limit, strict=False):
        require(type(amount) is int and amount >= 0, 'V2_COUNTER')
        total = self.counts[name]+amount
        require(total < limit if strict else total <= limit, 'V2_'+name.upper())
        self.counts[name] = total

    def input_nodes(self,n):self.charge('input_nodes',n,PROFILE['input_nodes'])
    def metadata_nodes(self,n):self.charge('metadata_nodes',n,PROFILE['metadata_nodes'])
    def logical_nodes(self,n):self.charge('logical_nodes',n,PROFILE['logical_nodes'])
    def stored_bytes(self,n):self.charge('stored_bytes',n,PROFILE['generation_bytes'],True)
    def records(self,n):self.charge('records',n,PROFILE['records'])


class _Scan(v1._Scan):
    """Reuse v1 grammar/span scanner, changing only explicit resource scopes."""
    def __init__(self, raw, scope, guard):
        require(scope in ('object','response','saved'), 'V2_SCOPE')
        cap = PROFILE['object_bytes'] if scope=='object' else PROFILE['generation_bytes']
        require(type(raw) is bytes and 0 < len(raw) < cap,
                'V2_OBJECT_BYTES' if scope=='object' else 'V2_SOURCE_BYTES')
        super().__init__(raw)
        self.scope = scope
        self.guard = guard
        self.limit = PROFILE[scope+'_nodes']

    def token(self):
        self.nodes += 1
        require(self.nodes <= self.limit, 'V2_'+self.scope.upper()+'_NODES')
        if self.nodes % 4096 == 0:self.guard.checkpoint()

    def string(self):
        left,right = super().string()
        require(right-left <= PROFILE['string_token_bytes'], 'V2_STRING_TOKEN')
        self.guard.checkpoint()
        return left,right


def scan(raw, scope, guard=None):
    guard = guard or ResourceGuard()
    guard.checkpoint()
    scanner = _Scan(raw,scope,guard)
    scanner.run()
    guard.scan_nodes += scanner.nodes
    guard.scan_bytes += len(raw)
    guard.checkpoint()
    return scanner


def parse(raw, scope, guard=None, *, canonical_required=True):
    guard = guard or ResourceGuard()
    scanner = scan(raw,scope,guard)
    def invalid(_):raise ContractError('M18_V2_JSON_INVALID')
    try:value = json.loads(raw,parse_constant=invalid)
    except (ValueError,UnicodeError,RecursionError):raise ContractError('M18_V2_JSON_INVALID') from None
    guard.checkpoint('json_'+scope)
    if canonical_required:
        require(v1.streamed_sha(value)==sha(raw),'V2_NONCANONICAL')
    guard.checkpoint()
    return value,scanner


def encoded(value, guard):
    raw = v1.canonical(value)
    scanner = scan(raw,'object',guard)
    return raw,scanner.nodes


def generation(identity):
    return sha(v1.canonical(dict(schema=VERSION,identity=identity,profile_sha256=PROFILE_SHA256)))


def binding(identity, gen):
    return dict(identity=identity,generation_id=gen,profile_sha256=PROFILE_SHA256)


def charge_object(ledger, raw, nodes):
    ledger.records(1);ledger.stored_bytes(len(raw))
    ledger.metadata_nodes(nodes);ledger.logical_nodes(nodes)


def build(response_bytes, saved_plan_bytes, expected_identity, *, expected_profile, guard=None):
    profile_check(expected_profile);v1.identity_check(expected_identity)
    guard = guard or ResourceGuard();ledger=Ledger();identity=dict(expected_identity)
    for raw in (response_bytes,saved_plan_bytes):
        require(type(raw) is bytes and 0<len(raw)<PROFILE['generation_bytes'],'V2_SOURCE_BYTES')
    require(sha(response_bytes)==identity['response_sha256'] and sha(saved_plan_bytes)==identity['raw_sha256'],'V2_SOURCE_HASH')
    # Validate and release saved DOM before allocating the response DOM.
    saved,saved_scan=parse(saved_plan_bytes,'saved',guard,canonical_required=False)
    ledger.input_nodes(saved_scan.nodes);saved_nodes=saved_scan.nodes
    require(type(saved) is dict and saved.get('sha256')==identity['plan_sha256']
            and saved.get('run_id')==identity['run_id'] and saved.get('target_trade_date')==identity['target_date']
            and saved.get('input_identity')==identity['input_identity'],'V2_SAVED_IDENTITY')
    require(v1.streamed_sha({k:v for k,v in saved.items() if k!='sha256'})==identity['plan_sha256'],'V2_SAVED_SEMANTIC_HASH')
    del saved,saved_scan
    guard.checkpoint('saved_released')
    response,response_scan=parse(response_bytes,'response',guard)
    ledger.input_nodes(response_scan.nodes);ledger.logical_nodes(response_scan.nodes)
    v1.response_check(response,identity)
    sections=response_scan.sections;response_nodes=response_scan.nodes
    del response,response_scan
    guard.checkpoint('response_released')
    gen=generation(identity);objects={};chunks=[];index_pages=[]
    def put(value):
        raw,nodes=encoded(value,guard);charge_object(ledger,raw,nodes)
        key=sha(raw);require(key not in objects,'V2_DUPLICATE_OBJECT');objects[key]=raw
        return key
    for index,start in enumerate(range(0,len(response_bytes),PROFILE['chunk_bytes'])):
        block=response_bytes[start:start+PROFILE['chunk_bytes']]
        value=dict(schema=VERSION+'.content',**binding(identity,gen),index=index,offset=start,
                   bytes=len(block),sha256=sha(block),data=base64.b64encode(block).decode('ascii'))
        key=put(value)
        chunks.append(dict(object_sha256=key,index=index,offset=start,bytes=len(block),sha256=sha(block)))
    flat=[dict(section=section,entry=entry) for section,row in sorted(sections.items()) for entry in row['entries']]
    for index,start in enumerate(range(0,len(flat),PROFILE['index_items'])):
        entries=flat[start:start+PROFILE['index_items']]
        key=put(dict(schema=VERSION+'.index',**binding(identity,gen),index=index,offset=start,entries=entries))
        index_pages.append(dict(object_sha256=key,index=index,offset=start,count=len(entries)))
    manifest=dict(schema=VERSION+'.manifest',**binding(identity,gen),profile=dict(PROFILE),
                  response_bytes=len(response_bytes),response_nodes=response_nodes,saved_nodes=saved_nodes,
                  chunks=chunks,index_pages=index_pages,
                  sections={k:dict(kind=v['kind'],total=v['total']) for k,v in sections.items()})
    raw,nodes=encoded(manifest,guard);charge_object(ledger,raw,nodes)
    guard.checkpoint('build_complete')
    return Bundle(raw,objects)


class Reader(v1.Reader):
    """Reuses v1 expected-request verification; each response pins v2 profile."""
    def __init__(self,bundle,expected_manifest_sha256,expected_identity,*,expected_profile,guard=None):
        profile_check(expected_profile);v1.identity_check(expected_identity)
        self._guard=guard or ResourceGuard();ledger=Ledger()
        require(isinstance(bundle,Bundle) and type(bundle.objects) is dict,'V2_BUNDLE')
        require(type(bundle.manifest) is bytes and 0<len(bundle.manifest)<PROFILE['object_bytes'],'V2_OBJECT_BYTES')
        require(sha(bundle.manifest)==expected_manifest_sha256,'V2_MANIFEST_HASH')
        manifest,sc=parse(bundle.manifest,'object',self._guard)
        v1.exact(manifest,('schema','identity','generation_id','profile_sha256','profile','response_bytes','response_nodes','saved_nodes','chunks','index_pages','sections'))
        require(manifest['schema']==VERSION+'.manifest' and v1.canonical(manifest['profile'])==v1.canonical(dict(PROFILE))
                and manifest['profile_sha256']==expected_profile,'V2_PROFILE')
        require(manifest['identity']==expected_identity and manifest['generation_id']==generation(expected_identity),'V2_IDENTITY')
        require(v1.integer(manifest['response_bytes'],1,PROFILE['generation_bytes']-1),'V2_RESPONSE_BYTES')
        require(v1.integer(manifest['response_nodes'],1,PROFILE['response_nodes'])
                and v1.integer(manifest['saved_nodes'],1,PROFILE['saved_nodes']),'V2_DECLARED_NODES')
        ledger.input_nodes(manifest['response_nodes']);ledger.input_nodes(manifest['saved_nodes'])
        ledger.logical_nodes(manifest['response_nodes']);charge_object(ledger,bundle.manifest,sc.nodes)
        chunks=manifest['chunks'];pages=manifest['index_pages']
        require(type(chunks) is list and type(pages) is list and type(manifest['sections']) is dict,'V2_MANIFEST_SCHEMA')
        require(len(bundle.objects)+1<=PROFILE['records'],'V2_RECORDS')
        require(len(chunks)==(manifest['response_bytes']+PROFILE['chunk_bytes']-1)//PROFILE['chunk_bytes'],'V2_CHUNK_COUNT')
        keys=[]
        for descriptor in chunks+pages:
            require(type(descriptor) is dict and type(descriptor.get('object_sha256')) is str,'V2_DESCRIPTOR')
            keys.append(descriptor['object_sha256'])
        require(len(keys)==len(set(keys)) and set(keys)==set(bundle.objects),'V2_OBJECT_SET')
        require(all(type(raw) is bytes and 0<len(raw)<PROFILE['object_bytes'] for raw in bundle.objects.values()),'V2_OBJECT_BYTES')
        require(len(bundle.manifest)+sum(map(len,bundle.objects.values()))<PROFILE['generation_bytes'],'V2_STORED_BYTES')
        def get(descriptor,kind):
            raw=bundle.objects[descriptor['object_sha256']]
            require(sha(raw)==descriptor['object_sha256'],'V2_OBJECT_HASH')
            value,scanner=parse(raw,'object',self._guard);charge_object(ledger,raw,scanner.nodes)
            require(type(value) is dict and value.get('schema')==VERSION+'.'+kind
                    and value.get('identity')==expected_identity and value.get('generation_id')==manifest['generation_id']
                    and value.get('profile_sha256')==expected_profile,'V2_OBJECT_IDENTITY')
            return value
        # One exact-size assembly buffer. Release it before parsing the bytes copy.
        data=bytearray(manifest['response_bytes']);offset=0
        for index,desc in enumerate(chunks):
            v1.exact(desc,('object_sha256','index','offset','bytes','sha256'))
            size=min(PROFILE['chunk_bytes'],len(data)-offset)
            require(v1.integer(desc['index'],index,index) and v1.integer(desc['offset'],offset,offset)
                    and v1.integer(desc['bytes'],size,size),'V2_CHUNK_ORDER')
            value=get(desc,'content');v1.exact(value,('schema','identity','generation_id','profile_sha256','index','offset','bytes','sha256','data'))
            require(type(value['data']) is str and len(value['data'])==4*((size+2)//3),'V2_CONTENT_SIZE')
            try:block=base64.b64decode(value['data'],validate=True)
            except (ValueError,TypeError):raise ContractError('M18_V2_CONTENT_ENCODING') from None
            require(len(block)==size and sha(block)==desc['sha256'],'V2_CONTENT_HASH')
            require(v1.canonical({k:value[k] for k in ('index','offset','bytes','sha256')})==v1.canonical({k:desc[k] for k in ('index','offset','bytes','sha256')}),'V2_CONTENT_DESCRIPTOR')
            data[offset:offset+size]=block;offset+=size
        full=bytes(data);del data
        require(sha(full)==expected_identity['response_sha256'],'V2_FULL_HASH')
        response,scanner=parse(full,'response',self._guard);v1.response_check(response,expected_identity)
        require(scanner.nodes==manifest['response_nodes'],'V2_RESPONSE_NODES')
        sections=scanner.sections;del response,scanner
        expected_sections={k:dict(kind=v['kind'],total=v['total']) for k,v in sections.items()}
        require(v1.canonical(expected_sections)==v1.canonical(manifest['sections']),'V2_SECTIONS')
        flat=[dict(section=k,entry=e) for k,v in sorted(sections.items()) for e in v['entries']]
        require(len(pages)==(len(flat)+PROFILE['index_items']-1)//PROFILE['index_items'],'V2_INDEX_COUNT')
        for index,desc in enumerate(pages):
            v1.exact(desc,('object_sha256','index','offset','count'))
            start=index*PROFILE['index_items'];entries=flat[start:start+PROFILE['index_items']]
            require(v1.integer(desc['index'],index,index) and v1.integer(desc['offset'],start,start)
                    and v1.integer(desc['count'],len(entries),len(entries)),'V2_INDEX_ORDER')
            value=get(desc,'index')
            expected=dict(schema=VERSION+'.index',**binding(expected_identity,manifest['generation_id']),index=index,offset=start,entries=entries)
            require(v1.canonical(value)==v1.canonical(expected),'V2_INDEX_CONTENT')
        self._full=full;self._sections=sections;self._identity=dict(expected_identity)
        self._generation=manifest['generation_id'];self._pin=expected_manifest_sha256
        self.counts=dict(ledger.counts,response_nodes=manifest['response_nodes'],saved_nodes=manifest['saved_nodes'])
        self._guard.checkpoint('reader_complete')

    def _binding(self):
        return dict(super()._binding(),profile_sha256=PROFILE_SHA256)

    def overview(self):
        value=super().overview();value['schema']=VERSION+'.overview';self._guard.checkpoint();return value

    def detail(self,section,*,selection=None,cursor=None):
        value=super().detail(section,selection=selection,cursor=cursor)
        value['schema']=VERSION+'.detail';self._guard.checkpoint();return value

    def _cursor(self,section,selection,offset):
        # v1 detail validates an exact cursor schema. The profile is committed by
        # manifest+generation; keep its established cursor shape/verification.
        value=dict(manifest_sha256=self._pin,generation_id=self._generation,identity=dict(self._identity),
                   section=section,selection_sha256=sha(v1.canonical(selection)),offset=offset)
        return base64.urlsafe_b64encode(v1.canonical(value)).decode('ascii')

    def content(self,index):
        value=super().content(index);value['schema']=VERSION+'.content';self._guard.checkpoint();return value
