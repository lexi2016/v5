"""M18-owned offline pages. No owner execution, file I/O, HTTP or publication."""
import base64
from dataclasses import dataclass
import hashlib
import json
import re
from .manager_result_transport import _pieces

OBJECT_BYTES = 16 * 1024 * 1024
GENERATION_BYTES = 64 * 1024 * 1024
CHUNK_BYTES = 256 * 1024
PAGE_SIZE = 32
MAX_RECORDS = 10000
MAX_ENTRIES = 10000
MAX_NODES = 200000
MAX_DEPTH = 64
VERSION = 'v5.m18.offline.v1'
IDENTITY_KEYS = {'run_id', 'target_date', 'plan_sha256', 'raw_sha256', 'response_sha256', 'input_identity'}


class ContractError(ValueError):
    """Fixed codes only; never includes input content."""


def require(condition, code):
    if not condition:
        raise ContractError('M18_' + code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    result = bytearray()
    try:
        for piece in _pieces(value):
            require(len(result) + len(piece) < OBJECT_BYTES, 'OBJECT_LIMIT')
            result.extend(piece)
    except (TypeError, ValueError, UnicodeError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError('M18_JSON_INVALID') from None
    return bytes(result)


def streamed_sha(value):
    digest = hashlib.sha256()
    try:
        for piece in _pieces(value):
            digest.update(piece)
    except (TypeError, ValueError, UnicodeError):
        raise ContractError('M18_JSON_INVALID') from None
    return digest.hexdigest()


def identity_check(value):
    require(type(value) is dict and set(value) == IDENTITY_KEYS, 'IDENTITY_SCHEMA')
    for key, item in value.items():
        pattern = r'[0-9a-f]{32}' if key == 'run_id' else r'[0-9]{8}' if key == 'target_date' else r'[0-9a-f]{64}'
        require(type(item) is str and re.fullmatch(pattern, item) is not None, 'IDENTITY_VALUE')


def exact(value, keys, code='SCHEMA'):
    require(type(value) is dict and set(value) == set(keys), code)


def integer(value, low, high):
    return type(value) is int and low <= value <= high


class _Scan:
    """Bound JSON structure before json.loads; index exact canonical byte spans.

    Large strings are skipped with bounded searches, not regex backtracking or
    an encoded full-string copy. Duplicate keys are rejected at every depth.
    """
    whitespace = re.compile(rb'[ \t\r\n]*')
    scalar_end = re.compile(rb'[ \t\r\n,}\]]')

    def __init__(self, raw):
        require(type(raw) is bytes and 0 < len(raw) < GENERATION_BYTES, 'SOURCE_LIMIT')
        self.raw = raw
        self.position = 0
        self.nodes = 0
        self.entries = 0
        self.sections = {}

    def space(self):
        self.position = self.whitespace.match(self.raw, self.position).end()

    def token(self):
        self.nodes += 1
        require(self.nodes <= MAX_NODES, 'NODE_LIMIT')

    def string(self):
        start = self.position
        self.position += 1
        while True:
            end = self.raw.find(b'"', self.position)
            require(end >= 0, 'JSON_INVALID')
            back = end - 1
            while back >= start and self.raw[back] == 92:
                back -= 1
            self.position = end + 1
            if (end - 1 - back) % 2 == 0:
                return start, self.position

    def span(self, kind, start, end, index):
        self.entries += 1
        require(self.entries <= MAX_ENTRIES, 'ENTRY_LIMIT')
        return dict(index=index, kind=kind, offset=start, bytes=end-start,
                    sha256=sha(memoryview(self.raw)[start:end]), value_state='NOT_LOADED')

    def value(self, depth=0, path=()):
        require(depth <= MAX_DEPTH, 'DEPTH_LIMIT')
        self.space(); self.token()
        start = self.position
        require(start < len(self.raw), 'JSON_INVALID')
        first = self.raw[start]
        indexed = len(path) == 2 and path[0] == 'payload'
        entries = []
        if first == 34:
            kind = 'string'; self.string()
        elif first in (123, 91):
            mapping = first == 123
            kind = 'object' if mapping else 'array'
            close = 125 if mapping else 93
            self.position += 1; self.space()
            seen = set(); index = 0
            if self.position < len(self.raw) and self.raw[self.position] != close:
                while True:
                    if mapping:
                        require(self.position < len(self.raw) and self.raw[self.position] == 34, 'JSON_INVALID')
                        self.token(); left, right = self.string()
                        require(right-left <= 1024, 'KEY_LIMIT')
                        try:
                            key = json.loads(self.raw[left:right])
                        except (ValueError, UnicodeError):
                            raise ContractError('M18_JSON_INVALID') from None
                        require(key not in seen, 'DUPLICATE_KEY'); seen.add(key)
                        self.space(); require(self.position < len(self.raw) and self.raw[self.position] == 58, 'JSON_INVALID')
                        self.position += 1
                    else:
                        key = index
                    item_kind, left, right = self.value(depth+1, path+(key,))
                    if indexed and not mapping:
                        entries.append(self.span(item_kind, left, right, index))
                    index += 1
                    self.space(); require(self.position < len(self.raw), 'JSON_INVALID')
                    separator = self.raw[self.position]; self.position += 1
                    if separator == close:
                        break
                    require(separator == 44, 'JSON_INVALID'); self.space()
            else:
                require(self.position < len(self.raw), 'JSON_INVALID'); self.position += 1
        else:
            found = self.scalar_end.search(self.raw, start)
            self.position = found.start() if found else len(self.raw)
            require(0 < self.position-start <= 128, 'SCALAR_LIMIT')
            word = self.raw[start:self.position]
            kind = 'null' if word == b'null' else 'boolean' if word in (b'true', b'false') else 'number'
        end = self.position
        if indexed:
            if kind != 'array':
                entries = [self.span(kind, start, end, 0)]
            self.sections[path[1]] = dict(kind=kind, total=len(entries), entries=entries)
        return kind, start, end

    def run(self):
        self.value(); self.space()
        require(self.position == len(self.raw), 'JSON_INVALID')
        return self.sections


def parse(raw, *, object_limit=False, canonical_required=True):
    if object_limit:
        require(type(raw) is bytes and len(raw) < OBJECT_BYTES, 'OBJECT_LIMIT')
    scan = _Scan(raw); sections = scan.run()
    def invalid(_):
        raise ContractError('M18_JSON_INVALID')
    try:
        value = json.loads(raw, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError):
        raise ContractError('M18_JSON_INVALID') from None
    if canonical_required:
        require(streamed_sha(value) == sha(raw), 'NONCANONICAL')
    return value, sections


def response_check(response, identity):
    require(type(response) is dict and 'local_result_transport' not in response, 'RESPONSE_SCHEMA')
    payload = response.get('payload'); readback = response.get('readback')
    require(type(payload) is dict and type(readback) is dict, 'RESPONSE_SCHEMA')
    product = payload.get('plan_product')
    require(type(product) is dict and product.get('consumed') is True, 'NOT_CONSUMED')
    require(payload.get('target_trade_date') == identity['target_date']
            and payload.get('input_identity') == identity['input_identity']
            and readback.get('input_identity') == identity['input_identity']
            and product.get('run_id') == readback.get('run_id') == identity['run_id']
            and product.get('sha256') == readback.get('plan_sha256') == identity['plan_sha256'], 'SOURCE_IDENTITY')
    require(payload.get('RESEARCH_ONLY') is True and all(payload.get(k) is False for k in
            ('production_allowed', 'buy_gate_updated', 'orders_sent')), 'SAFETY_FLAGS')


def generation(identity):
    return sha(canonical(dict(schema=VERSION, identity=identity, chunk_bytes=CHUNK_BYTES, page_size=PAGE_SIZE)))


@dataclass(frozen=True)
class Bundle:
    manifest: bytes
    objects: dict


def build(response_bytes, saved_plan_bytes, expected_identity):
    identity_check(expected_identity)
    identity = dict(expected_identity)
    require(type(response_bytes) is bytes and type(saved_plan_bytes) is bytes, 'SOURCE_TYPE')
    require(0 < len(response_bytes) < GENERATION_BYTES and 0 < len(saved_plan_bytes) < GENERATION_BYTES, 'SOURCE_LIMIT')
    require(sha(response_bytes) == identity['response_sha256'] and sha(saved_plan_bytes) == identity['raw_sha256'], 'SOURCE_HASH')
    response, sections = parse(response_bytes)
    saved, _ = parse(saved_plan_bytes, canonical_required=False)
    require(type(saved) is dict and saved.get('sha256') == identity['plan_sha256']
            and saved.get('run_id') == identity['run_id'] and saved.get('target_trade_date') == identity['target_date']
            and saved.get('input_identity') == identity['input_identity'], 'SAVED_IDENTITY')
    require(streamed_sha({k:v for k,v in saved.items() if k != 'sha256'}) == identity['plan_sha256'], 'SAVED_SEMANTIC_HASH')
    response_check(response, identity)
    gen = generation(identity); objects = {}; chunks = []; total = 0
    for index, start in enumerate(range(0, len(response_bytes), CHUNK_BYTES)):
        require(index + 2 <= MAX_RECORDS, 'RECORD_LIMIT')
        block = response_bytes[start:start+CHUNK_BYTES]
        envelope = dict(schema=VERSION+'.content', generation_id=gen, identity=identity,
                        index=index, offset=start, bytes=len(block), sha256=sha(block),
                        data=base64.b64encode(block).decode('ascii'))
        raw = canonical(envelope); parse(raw, object_limit=True)
        total += len(raw); require(total < GENERATION_BYTES, 'GENERATION_LIMIT')
        key = sha(raw); objects[key] = raw
        chunks.append(dict(object_sha256=key, index=index, offset=start, bytes=len(block), sha256=sha(block)))
    manifest = canonical(dict(schema=VERSION+'.manifest', generation_id=gen, identity=identity,
                              response_bytes=len(response_bytes), chunks=chunks, sections=sections))
    require(total + len(manifest) < GENERATION_BYTES, 'GENERATION_LIMIT')
    parse(manifest, object_limit=True)
    return Bundle(manifest, objects)


class Reader:
    """An immutable local snapshot validated against caller-supplied pins."""
    def __init__(self, bundle, expected_manifest_sha256, expected_identity):
        identity_check(expected_identity)
        require(type(expected_manifest_sha256) is str and re.fullmatch('[0-9a-f]{64}', expected_manifest_sha256), 'MANIFEST_PIN')
        require(isinstance(bundle, Bundle) and type(bundle.manifest) is bytes and type(bundle.objects) is dict, 'BUNDLE_SCHEMA')
        require(0 < len(bundle.manifest) < OBJECT_BYTES, 'OBJECT_LIMIT')
        require(sha(bundle.manifest) == expected_manifest_sha256, 'MANIFEST_HASH')
        require(len(bundle.objects)+1 <= MAX_RECORDS, 'RECORD_LIMIT')
        require(all(type(k) is str and type(v) is bytes for k,v in bundle.objects.items()), 'OBJECT_SCHEMA')
        require(len(bundle.manifest)+sum(len(v) for v in bundle.objects.values()) < GENERATION_BYTES, 'GENERATION_LIMIT')
        manifest, _ = parse(bundle.manifest, object_limit=True)
        exact(manifest, ('schema','generation_id','identity','response_bytes','chunks','sections'))
        require(manifest['schema'] == VERSION+'.manifest' and manifest['identity'] == expected_identity
                and manifest['generation_id'] == generation(expected_identity), 'MANIFEST_IDENTITY')
        require(integer(manifest['response_bytes'], 1, GENERATION_BYTES-1)
                and type(manifest['chunks']) is list and type(manifest['sections']) is dict, 'MANIFEST_SCHEMA')
        require(len(manifest['chunks']) == (manifest['response_bytes']+CHUNK_BYTES-1)//CHUNK_BYTES, 'CHUNK_COUNT')
        require(all(type(d) is dict and type(d.get('object_sha256')) is str
                    and re.fullmatch('[0-9a-f]{64}', d['object_sha256'])
                    and type(d.get('sha256')) is str and re.fullmatch('[0-9a-f]{64}', d['sha256'])
                    for d in manifest['chunks']), 'CHUNK_SCHEMA')
        require(set(bundle.objects) == {d.get('object_sha256') for d in manifest['chunks']}, 'OBJECT_SET')
        data = bytearray()
        for index, descriptor in enumerate(manifest['chunks']):
            exact(descriptor, ('object_sha256','index','offset','bytes','sha256'))
            require(integer(descriptor['index'],index,index) and integer(descriptor['offset'],len(data),len(data)), 'CHUNK_ORDER')
            size = min(CHUNK_BYTES, manifest['response_bytes']-len(data))
            require(integer(descriptor['bytes'],size,size), 'CHUNK_SIZE')
            raw = bundle.objects[descriptor['object_sha256']]
            require(0 < len(raw) < OBJECT_BYTES, 'OBJECT_LIMIT')
            require(sha(raw) == descriptor['object_sha256'], 'OBJECT_HASH')
            value, _ = parse(raw, object_limit=True)
            exact(value, ('schema','generation_id','identity','index','offset','bytes','sha256','data'))
            require(value['schema'] == VERSION+'.content' and value['generation_id'] == manifest['generation_id']
                    and value['identity'] == expected_identity, 'CONTENT_IDENTITY')
            require(type(value['data']) is str and len(value['data']) == 4*((size+2)//3), 'CONTENT_SIZE')
            try:
                block = base64.b64decode(value['data'], validate=True)
            except (ValueError, TypeError):
                raise ContractError('M18_CONTENT_ENCODING') from None
            require(len(block) == size and sha(block) == descriptor['sha256'], 'CONTENT_HASH')
            require(canonical({k:value[k] for k in ('index','offset','bytes','sha256')}) == canonical({k:descriptor[k] for k in ('index','offset','bytes','sha256')}), 'CONTENT_DESCRIPTOR')
            data.extend(block)
        require(len(data) == manifest['response_bytes'] and sha(data) == expected_identity['response_sha256'], 'FULL_HASH')
        full = bytes(data); response, sections = parse(full)
        response_check(response, expected_identity)
        require(canonical(sections) == canonical(manifest['sections']), 'SECTION_INDEX')
        self._full = full; self._sections = sections
        self._identity = dict(expected_identity); self._generation = manifest['generation_id']; self._pin = expected_manifest_sha256

    def _binding(self):
        return dict(manifest_sha256=self._pin, generation_id=self._generation, identity=dict(self._identity))

    def overview(self):
        value = dict(schema=VERSION+'.overview', **self._binding(),
                     content_chunks=(len(self._full)+CHUNK_BYTES-1)//CHUNK_BYTES, sections={key:dict(
            kind=row['kind'], total=row['total'], loaded_count=0, not_loaded_count=row['total'],
            state='NOT_LOADED') for key,row in self._sections.items()})
        parse(canonical(value), object_limit=True)
        return value

    def _selected(self, section, selection):
        require(type(section) is str and section in self._sections, 'SECTION')
        total = self._sections[section]['total']
        if selection is None:
            return list(range(total))
        exact(selection, ('indices',), 'SELECTION_SCHEMA')
        values = selection['indices']
        require(type(values) is list and len(values) <= MAX_ENTRIES and all(integer(v,0,total-1) for v in values), 'SELECTION_INDEX')
        require(values == sorted(set(values)), 'SELECTION_ORDER')
        return values

    def _cursor(self, section, selection, offset):
        value = dict(**self._binding(), section=section, selection_sha256=sha(canonical(selection)), offset=offset)
        return base64.urlsafe_b64encode(canonical(value)).decode('ascii')

    def detail(self, section, *, selection=None, cursor=None):
        indices = self._selected(section, selection); offset = 0
        if cursor is not None:
            require(type(cursor) is str and 0 < len(cursor) <= 8192, 'CURSOR_LIMIT')
            try:
                encoded = base64.b64decode(cursor, altchars=b'-_', validate=True)
                value, _ = parse(encoded, object_limit=True)
            except (ValueError, TypeError, UnicodeError):
                raise ContractError('M18_CURSOR_INVALID') from None
            exact(value, ('manifest_sha256','generation_id','identity','section','selection_sha256','offset'), 'CURSOR_SCHEMA')
            offset = value['offset']
            require(integer(offset, PAGE_SIZE, len(indices)-1) and offset % PAGE_SIZE == 0, 'CURSOR_OFFSET')
            require(cursor == self._cursor(section, selection, offset), 'CURSOR_BINDING')
        chosen = indices[offset:offset+PAGE_SIZE]
        next_offset = offset+len(chosen)
        page = dict(schema=VERSION+'.detail', **self._binding(), section=section,
                    selection=selection, cursor=cursor, offset=offset, matched_total=len(indices),
                    not_loaded_count=len(indices), remaining_entries=len(indices)-next_offset,
                    entries=[dict(self._sections[section]['entries'][i]) for i in chosen],
                    next_cursor=self._cursor(section,selection,next_offset) if next_offset<len(indices) else None)
        parse(canonical(page), object_limit=True)
        return page

    def verify_page(self, page):
        require(type(page) is dict, 'PAGE_SCHEMA')
        parse(canonical(page), object_limit=True)
        expected = self.detail(page.get('section'), selection=page.get('selection'), cursor=page.get('cursor'))
        require(canonical(page) == canonical(expected), 'PAGE_MISMATCH')
        return True

    def content(self, index):
        """A bounded response carrying explicit root, identity and byte binding."""
        count = (len(self._full)+CHUNK_BYTES-1)//CHUNK_BYTES
        require(integer(index, 0, count-1), 'CONTENT_INDEX')
        offset = index*CHUNK_BYTES
        block = self._full[offset:offset+CHUNK_BYTES]
        value = dict(schema=VERSION+'.content', **self._binding(), index=index,
                     offset=offset, bytes=len(block), sha256=sha(block),
                     data=base64.b64encode(block).decode('ascii'))
        parse(canonical(value), object_limit=True)
        return value

    def verify_content(self, content):
        require(type(content) is dict, 'CONTENT_SCHEMA')
        parse(canonical(content), object_limit=True)
        expected = self.content(content.get('index'))
        require(canonical(content) == canonical(expected), 'CONTENT_MISMATCH')
        return True

    def item_parts(self, section, index):
        require(type(section) is str and section in self._sections, 'SECTION')
        require(integer(index,0,self._sections[section]['total']-1), 'ITEM_INDEX')
        entry = self._sections[section]['entries'][index]
        start = entry['offset']; end = start+entry['bytes']
        for offset in range(start, end, CHUNK_BYTES):
            yield self._full[offset:min(offset+CHUNK_BYTES,end)]

    def full_response(self):
        # Local reconstruction only. Never a permitted single HTTP response.
        return self._full
