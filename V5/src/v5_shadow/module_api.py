"""One independent, read-only API process for one module's immutable responses."""
import argparse
from datetime import datetime
import base64
import fcntl
import time
import hashlib
import json
import os
import re
import socket
import stat
import sys
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from .composition import no_symlinks
from .contracts import exact_keys,aware,sha
from .digests import canonical_bytes,sha256_json,MAX_JSON_BYTES
from .api_gateway import (_parse_response, _precheck_json, _bounded_json,
                          _manager_response, MANAGER_WORKSPACE_PATH,
                          SOURCE_BUNDLE_READ_ONLY_COMPAT_ROUTES)
M18_ROUTE = "/api/v4/manager/m18/v2"
M17_ROUTE = "/api/v5/manager/close-recapture"
M07_ROUTE = "/api/v5/source-bundle/a-stage-saved"
M16_ROUTE = "/api/v5/source-bundle/manager-public-research"
M11_ROUTE = "/api/v5/source-bundle/intraday-research"
M12_ROUTE = "/api/v5/source-bundle/video-fupan"
M04_ROUTE = "/api/v5/source-bundle/research-intelligence"
M17_BINDING_ERROR_CODES = frozenset((
    'M17_READONLY_BINDING', 'M17_READONLY_CONFIG_LIMIT', 'M17_READONLY_LANE',
    'M17_READONLY_RUN_ID', 'M17_READONLY_ROOT_OVERLAP',
))
M17_PRODUCT_ERROR_CODES = frozenset((
    'M17_READONLY_PRODUCT_IDENTITY', 'M17_READONLY_FILES',
    'M17_READONLY_FILE_REFERENCE', 'M17_READONLY_FILES_CHANGED',
    'M17_READONLY_ORIGINAL_READER_REJECTED', 'M17_READONLY_EXTERNAL_POOL_CHANGED',
    'M17_READONLY_PRODUCT_CHANGED', 'M17_READONLY_RESPONSE_MISMATCH',
    'M17_READONLY_RESPONSE_INVALID', 'M17_READONLY_LEDGER_CHANGED',
))
M17_UNAVAILABLE_ERROR_CODES = frozenset((
    'M17_READONLY_SAVED_SUCCESS_REQUIRED', 'M17_READONLY_EXACT_REFERENCE_REQUIRED',
))
M17_READER_ERROR_CODES = frozenset((
    'M17_READONLY_READER_UNAVAILABLE', 'M17_READONLY_RESPONSE_LIMIT',
    'M17_READONLY_PACKET_LIMIT',
))


def response_key(module_id,path,query):
    return sha256_json(dict(module_id=module_id,path=path,query=query))


def _m18_page_query(query):
    if 'page' not in query:
        raise ValueError('M18_PAGE_REQUIRED')
    try:
        page = int(query['page'])
    except (TypeError, ValueError):
        raise ValueError('M18_PAGE_INVALID') from None
    if page < 0:
        raise ValueError('M18_PAGE_INVALID')
    return page


def _m18_identity_from_descriptor(payload):
    from .m18_offline_v2 import generation, profile_check, v1

    if not isinstance(payload, dict):
        raise ValueError('M18_DESCRIPTOR_NOT_READY')
    required = (
        'schema_version',
        'identity',
        'run_id',
        'target_date',
        'generation_id',
        'profile_sha256',
        'pages_route',
        'status',
        'generated_at',
    )
    if 'manifest_sha256' in payload:
        required += ('manifest_sha256',)
        sha(payload['manifest_sha256'])
    exact_keys(payload, required)
    if payload['schema_version'] != 'v5.m18.v2.descriptor.v1':
        raise ValueError('M18_DESCRIPTOR_NOT_READY')
    if payload['status'] != 'READY':
        raise ValueError('M18_DESCRIPTOR_NOT_READY')
    v1.identity_check(payload['identity'])
    profile_check(payload['profile_sha256'])
    aware(payload['generated_at'])
    if (payload['identity']['run_id'] != payload['run_id']
            or payload['identity']['target_date'] != payload['target_date']
            or generation(payload['identity']) != payload['generation_id']):
        raise ValueError('M18_IDENTITY_MISMATCH')
    if payload['pages_route'] != M18_ROUTE + '/pages':
        raise ValueError('M18_DESCRIPTOR_NOT_READY')
    return payload


def _m18_read_page_binding(config, root, query):
    """
    Read-only resolver for already published M18 descriptor.

    It intentionally does not publish, rebuild bundles, refresh manager state,
    or execute owners.
    """
    descriptor_query = {'run_id': query['run_id']}
    descriptor, _ = read_response(
        config,
        root,
        M18_ROUTE,
        descriptor_query,
    )
    if descriptor['status_code'] != 200:
        raise ValueError('M18_DESCRIPTOR_NOT_READY')
    return _m18_identity_from_descriptor(descriptor['payload'])


def _m18_binding_for_descriptor(config, descriptor):
    """Pin every read to this descriptor, never a changing current pointer."""
    if 'manifest_sha256' in descriptor:
        if config.get('m18_v2_daily_publication') is not True:
            raise ValueError('M18_DAILY_PUBLICATION_DISABLED')
        # All names come from validated digests, not request paths or roots.
        return dict(identity=descriptor['identity'],
                    manifest_sha256=descriptor['manifest_sha256'],
                    profile_sha256=descriptor['profile_sha256'],
                    bundle_root=str(Path(config['data_root']) / 'm18-v2-bundles' /
                                    descriptor['generation_id']))
    binding = config.get('m18_v2_binding')
    if not isinstance(binding, dict):
        raise ValueError('M18_READER_NOT_READY')
    exact_keys(binding, ('manifest_sha256', 'identity', 'profile_sha256', 'bundle_root'))
    if binding['identity'] != descriptor['identity']:
        raise ValueError('M18_IDENTITY_MISMATCH')
    if binding['profile_sha256'] != descriptor['profile_sha256']:
        raise ValueError('M18_PROFILE_MISMATCH')
    return binding


def _m18_disk_reader(binding, *, span_observer=None):
    """Load the immutable offline layout without invoking its writing worker."""
    from .m18_offline_v2 import Bundle, Reader, PROFILE, ResourceGuard

    guard = ResourceGuard()
    root = _open_directory(binding['bundle_root'])
    def read(directory, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        try:
            return _read_regular(fd, PROFILE['object_bytes'] - 1)
        finally:
            os.close(fd)
    try:
        manifest = read(root, 'manifest.json')
        if hashlib.sha256(manifest).hexdigest() != binding['manifest_sha256']:
            raise ValueError('M18_MANIFEST_HASH')
        objects_fd = os.open('objects', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                             dir_fd=root)
        try:
            objects = {}
            total = len(manifest)
            with os.scandir(objects_fd) as entries:
                for entry in entries:
                    if len(objects) + 2 > PROFILE['records']:
                        raise ValueError('M18_RECORDS')
                    if not re.fullmatch('[0-9a-f]{64}', entry.name):
                        raise ValueError('M18_OBJECT_NAME')
                    raw = read(objects_fd, entry.name)
                    total += len(raw)
                    if total >= PROFILE['generation_bytes']:
                        raise ValueError('M18_STORED_BYTES')
                    objects[entry.name] = raw
                    guard.checkpoint()
        finally:
            os.close(objects_fd)
    finally:
        os.close(root)
    return Reader(Bundle(manifest, objects), binding['manifest_sha256'],
                  binding['identity'], expected_profile=binding['profile_sha256'],
                  guard=guard, consume_content=True, span_observer=span_observer)


def _m18_page_response(config, root, query):
    exact_keys(query, ('run_id', 'page'))
    descriptor = _m18_read_page_binding(config, root, query)
    page = _m18_page_query(query)

    binding = _m18_binding_for_descriptor(config, descriptor)

    value = _m18_read_value(binding, 'content', {'page': page})

    return {
        'schema_version': 'v5.m18.v2.page_response.v1',
        'identity': descriptor['identity'],
        'run_id': descriptor['run_id'],
        'generation_id': descriptor['generation_id'],
        'profile_sha256': descriptor['profile_sha256'],
        'page': page,
        'content': value,
    }


# Per-view limits are narrower than existing global/offline budgets.
M18_VIEW_BYTES = 256 * 1024
M18_VIEW_ITEM_BYTES = 16 * 1024
M18_VIEW_VALUES_BYTES = 128 * 1024
M18_ANNOUNCEMENT_SECTION = 'announcement_reviewed_analysis'
M18_ANNOUNCEMENT_PROJECTION = 'announcement_references'
M18_REBOUND_SECTION = 'rebound_research_observation'
M18_REBOUND_PROJECTION = 'rebound_references'
M18_US_MAPPING_SECTION = 'us_mapping_research'
M18_US_MAPPING_PROJECTION = 'us_mapping_matches'
M18_US_MAPPING_SOURCE_FIELDS = (
    'schema_version', 'status', 'target_trade_date', 'gaps', 'RESEARCH_ONLY',
    'production_allowed', 'buy_gate_updated', 'orders_sent',
)
M18_US_MAPPING_DAILY_FIELDS = (
    'schema_version', 'status', 'target_trade_date', 'run_id', 'generated_at',
    'us_session_date', 'research_cutoff', 'coverage_scope', 'source_status',
    'input_identity', 'relation_artifact_sha256', 'target_date_eligibility',
    'producer_owner', 'readback_required', 'gaps', 'source_gaps', 'artifact_sha256',
    'RESEARCH_ONLY', 'production_allowed', 'buy_gate_updated', 'orders_sent',
)
M18_US_MAPPING_DAILY_COVERAGE_FIELDS = (
    'reviewed_us_symbol_count', 'matched_us_symbol_count', 'matched_hk_relation_count',
    'configured_us_universe_count', 'available_us_universe_count', 'full_market_coverage',
)
M18_US_MAPPING_COVERAGE_FIELDS = (
    'schema_version', 'status', 'scope', 'reviewed_us_symbols', 'reviewed_us_symbol_count',
    'reviewed_relation_artifact_sha256', 'us_session_date', 'daily_run_id',
    'daily_artifact_sha256', 'rising_individual_count', 'assessed_rising_symbol_count',
    'unassessed_rising_symbol_count', 'configured_sample_count', 'full_market_coverage',
    'broader_relation_result', 'reason_codes', 'formal_eligible', 'natural_verified',
)
M18_US_MAPPING_REGISTRY_FIELDS = ('scope', 'seed_target_date', 'formal_eligible', 'natural_verified')
M18_US_MAPPING_PLAN_FIELDS = (
    'status', 'target_trade_date', 'artifact_sha256', 'run_id', 'available_at',
    'plan_cutoff', 'reason', 'RESEARCH_ONLY', 'production_allowed', 'buy_gate_updated', 'orders_sent',
)
M18_REBOUND_GROUPS = ('strict', 'near', 'pending', 'excluded', 'screen_unresolved')
M18_REBOUND_SOURCE_FIELDS = (
    'status', 'eligible_screen', 'reason_codes', 'source_run_id', 'data_kind',
    'execution_kind', 'scope', 'research_only', 'production_allowed',
    'buy_gate_updated', 'orders_sent', 'natural_verified', 'formal_eligibility_verified',
)
M18_REBOUND_OBSERVATION_FIELDS = (
    'schema_version', 'rule_version', 'target_trade_date', 'observed_session', 'status',
    'original_computation_status', 'main_screen_ready', 'input_identity', 'decision_identity',
    'gaps', 'RESEARCH_ONLY', 'research_only', 'production_allowed', 'buy_gate_updated',
    'orders_sent', 'natural_verified', 'formal_eligibility_verified',
)
M18_REBOUND_BINDING_FIELDS = ('run_id', 'artifact_sha256', 'manifest_sha256', 'receipt_sha256')
M18_REBOUND_COVERAGE_FIELDS = (
    'input_candidate_count', 'history_complete_count', 'history_pending_count', 'strict_count',
    'near_candidate_count', 'near_count', 'selected_count', 'panel_row_count', 'panel_code_count',
    'excluded_count', 'screen_unresolved_count', 'row_accounted_count',
)
M18_REBOUND_DATE_FIELDS = (
    'data_session', 'reader_observed_at', 'manifest_available_at', 'manifest_prepared_at',
    'observation_status', 'provider_session_finality', 'master_captured_at',
    'read_started_at', 'read_completed_at',
)
M18_REBOUND_UNIT_FIELDS = (
    'status', 'scope', 'conversion_applied', 'legacy_declared_volume_unit', 'source_finality',
)
M18_ANNOUNCEMENT_PRODUCT_FIELDS = (
    'schema_version', 'target_trade_date', 'publication_date', 'status',
    'validation_status', 'consumed', 'product_sha256', 'source_manifest_sha256',
    'catalog_product_sha256', 'source_run_id', 'evidence_run_id',
    'handoff_manifest_sha256', 'agent_judgment_receipt_sha256',
    'owner_import_receipt_sha256', 'owner_handoff_binding_status',
    'decision_status', 'selection_status', 'stock_count', 'selected_stock_count',
    'conditional_watch_count', 'not_selected_stock_count', 'not_assessed_stock_count',
    'reviewed_at', 'owner_available_at', 'latest_source_or_review_at',
    'plan_cutoff', 'cutoff_status', 'failure_stage', 'gaps', 'RESEARCH_ONLY',
    'production_allowed', 'buy_gate_updated', 'orders_sent',
)


def _m18_read_value(binding, kind, query):
    from .m18_v2_read_process import run
    result = run(dict(binding=binding, kind=kind, query=query))
    if result['status'] != 'OK':
        if result.get('error') == 'MODULE_RESULT_NOT_AVAILABLE':
            raise FileNotFoundError('M18_READER_NOT_READY')
        raise ValueError('M18_READER_REJECTED')
    return result['payload']


def _m18_semantic_response(config, root, path, query):
    """Read one saved semantic page. Never reconstruct a full response for HTTP."""
    keys = ('run_id', 'generation_id')
    if path == M18_ROUTE + '/sections':
        keys += ('section',)
        if 'cursor' in query:
            keys += ('cursor',)
        if 'projection' in query:
            keys += ('projection',)
        if 'group' in query:
            keys += ('group',)
    exact_keys(query, keys)
    projection = query.get('projection')
    if projection == M18_ANNOUNCEMENT_PROJECTION:
        if query['section'] != M18_ANNOUNCEMENT_SECTION or 'group' in query:
            raise ValueError('M18_PROJECTION_INVALID')
    elif projection == M18_REBOUND_PROJECTION:
        if query['section'] != M18_REBOUND_SECTION or query.get('group') not in M18_REBOUND_GROUPS:
            raise ValueError('M18_PROJECTION_INVALID')
    elif projection == M18_US_MAPPING_PROJECTION:
        if query['section'] != M18_US_MAPPING_SECTION or 'group' in query:
            raise ValueError('M18_PROJECTION_INVALID')
    elif projection is not None or 'group' in query:
        raise ValueError('M18_PROJECTION_INVALID')
    descriptor = _m18_read_page_binding(config, root, query)
    if query['generation_id'] != descriptor['generation_id']:
        raise ValueError('M18_GENERATION_MISMATCH')
    binding = _m18_binding_for_descriptor(config, descriptor)
    kind = 'overview' if path == M18_ROUTE + '/overview' else 'section'
    if projection == M18_ANNOUNCEMENT_PROJECTION:kind = 'announcement'
    elif projection == M18_REBOUND_PROJECTION:kind = 'rebound'
    elif projection == M18_US_MAPPING_PROJECTION:kind = 'us_mapping'
    selection = {key: query[key] for key in ('section', 'cursor', 'projection', 'group') if key in query}
    return _m18_read_value(binding, kind, selection)


def _m18_announcement_cursor(binding, source_sha, offset):
    value = {key: binding[key] for key in (
        'manifest_sha256', 'generation_id', 'identity', 'profile_sha256')}
    value.update(section=M18_ANNOUNCEMENT_SECTION, projection=M18_ANNOUNCEMENT_PROJECTION,
                 source_section_sha256=source_sha, selection_sha256=sha256_json(None), offset=offset)
    return base64.urlsafe_b64encode(canonical_bytes(value)).decode('ascii')


def _m18_projection_source(reader, section):
    """Read and index one verified object under the existing object budget."""
    from . import m18_offline_v2 as m
    source_page = reader.detail(section)
    m.require(source_page['matched_total'] == 1 and len(source_page['entries']) == 1,
              'V2_ANNOUNCEMENT_SOURCE')
    source_entry = source_page['entries'][0]
    m.require(source_entry['kind'] == 'object'
              and 0 < source_entry['bytes'] < m.PROFILE['object_bytes'], 'V2_OBJECT_BYTES')
    parts = [];size = 0
    for part in reader.item_parts(section, 0):
        size += len(part)
        m.require(size < m.PROFILE['object_bytes'], 'V2_OBJECT_BYTES')
        parts.append(part)
    raw = b''.join(parts);del parts
    m.require(len(raw) == source_entry['bytes'] and m.sha(raw) == source_entry['sha256'],
              'V2_ANNOUNCEMENT_HASH')
    # Reuse the existing byte grammar and original object/node/depth budgets.
    # Treat this already-verified object as payload solely to index its fields;
    # offsets below are translated back into the original full saved response.
    scanner = m._Scan(raw, 'object', reader._guard)
    scanner.value(path=('payload',));scanner.space()
    m.require(scanner.position == len(raw), 'V2_ANNOUNCEMENT_SOURCE')
    reader._guard.scan_nodes += scanner.nodes;reader._guard.scan_bytes += len(raw)
    source = json.loads(raw)
    reader._guard.checkpoint('projection_source')
    return raw, source, scanner, source_entry


def _m18_announcement_value(reader, query):
    """Project exact saved reference spans; never infer stocks or rerun M13."""
    from . import m18_offline_v2 as m
    raw, source, scanner, source_entry = _m18_projection_source(reader, M18_ANNOUNCEMENT_SECTION)
    m.require(type(source) is dict and type(source.get('research_references')) is list
              and type(source.get('products')) is list
              and all(type(product) is dict for product in source['products']), 'V2_ANNOUNCEMENT_SOURCE')
    references = source['research_references']
    rows = scanner.sections['research_references']['entries']
    m.require(len(rows) == len(references), 'V2_ANNOUNCEMENT_SOURCE')
    binding = reader._binding();cursor = query.get('cursor');offset = 0
    if cursor is not None:
        try:
            encoded = base64.b64decode(cursor, altchars=b'-_', validate=True)
            declared, _ = m.v1.parse(encoded, object_limit=True)
            offset = declared['offset']
        except (ValueError, KeyError, TypeError):
            raise ValueError('M18_CURSOR_INVALID') from None
        m.require(m.v1.integer(offset, m.v1.PAGE_SIZE, len(rows)-1)
                  and offset % m.v1.PAGE_SIZE == 0, 'V2_ANNOUNCEMENT_CURSOR')
        m.require(cursor == _m18_announcement_cursor(binding, source_entry['sha256'], offset),
                  'V2_ANNOUNCEMENT_CURSOR')
    entries = [];loaded = 0;loaded_bytes = 0
    for row in rows[offset:offset+m.v1.PAGE_SIZE]:
        entry = dict(row, offset=source_entry['offset']+row['offset'])
        if entry['bytes'] > M18_VIEW_ITEM_BYTES:
            entry['reason'] = 'ITEM_BYTES_LIMIT'
        elif loaded_bytes + entry['bytes'] > M18_VIEW_VALUES_BYTES:
            entry['reason'] = 'PAGE_BYTES_LIMIT'
        else:
            entry.update(value=references[row['index']], value_state='LOADED')
            loaded += 1;loaded_bytes += entry['bytes']
        entries.append(entry)
    next_offset = offset + len(entries)
    metadata = dict(status=source.get('status'), plan_cutoff=source.get('plan_cutoff'),
        gaps=source.get('gaps'), source_section_sha256=source_entry['sha256'],
        reference_count=len(rows), products=[
            {key: product[key] for key in M18_ANNOUNCEMENT_PRODUCT_FIELDS if key in product}
            for product in source['products']])
    return dict(schema=m.VERSION+'.detail', **binding, section=M18_ANNOUNCEMENT_SECTION,
        projection=M18_ANNOUNCEMENT_PROJECTION, announcement=metadata,
        selection=None, cursor=cursor, offset=offset, matched_total=len(rows),
        loaded_count=loaded, not_loaded_count=len(rows)-loaded,
        remaining_entries=len(rows)-next_offset, entries=entries,
        next_cursor=(_m18_announcement_cursor(binding, source_entry['sha256'], next_offset)
                     if next_offset < len(rows) else None))


def _m18_rebound_cursor(binding, source_sha, group, offset):
    value = {key: binding[key] for key in (
        'manifest_sha256', 'generation_id', 'identity', 'profile_sha256')}
    value.update(section=M18_REBOUND_SECTION, projection=M18_REBOUND_PROJECTION,
        group=group, source_section_sha256=source_sha, selection_sha256=sha256_json(None), offset=offset)
    return base64.urlsafe_b64encode(canonical_bytes(value)).decode('ascii')


class _M18ReboundSpans:
    """Bounded private observation of the Reader's one existing complete scan."""
    def __init__(self, query):
        from . import m18_offline_v2 as m
        self.group=query['group'];self.offset=0
        if 'cursor' in query:
            value,_=m.v1.parse(base64.b64decode(query['cursor'],altchars=b'-_',validate=True),object_limit=True)
            self.offset=value['offset']
            m.require(m.v1.integer(self.offset,1,2**63-1),'V2_REBOUND_CURSOR')
        self.prefix=('payload',M18_REBOUND_SECTION)
        self.inner=self.prefix+('research_observation',)
        self.stop=self.offset+m.v1.PAGE_SIZE
        self.counts={group:0 for group in M18_REBOUND_GROUPS}
        self.rows=[];self.metadata={};self.kinds={}
        self.paths={};self.containers={self.prefix:None,self.prefix+('research_observation',):None}
        def fields(path, target, names):
            self.containers[path]=target
            for name in names:self.paths[path+(name,)]=target+(name,)
        fields(self.prefix,('source',),M18_REBOUND_SOURCE_FIELDS)
        fields(self.prefix+('binding_reference',),('source','binding_reference'),M18_REBOUND_BINDING_FIELDS)
        inner=self.prefix+('research_observation',)
        fields(inner,('observation',),M18_REBOUND_OBSERVATION_FIELDS)
        fields(inner+('coverage',),('observation','coverage'),M18_REBOUND_COVERAGE_FIELDS)
        native=inner+('native_evidence',)
        fields(native,('observation','native_evidence'),('volume_unit','price_currency','price_basis','gaps'))
        fields(native+('date_evidence',),('observation','native_evidence','date_evidence'),M18_REBOUND_DATE_FIELDS)
        fields(native+('unit_evidence',),('observation','native_evidence','unit_evidence'),M18_REBOUND_UNIT_FIELDS)

    def __call__(self, path, kind, start, end, raw):
        if len(path)<2 or path[0]!='payload' or path[1]!=M18_REBOUND_SECTION:return
        if path in self.containers:self.kinds[path]=kind
        inner=self.inner
        if len(path)==4 and path[:3]==inner and path[3] in self.counts:
            self.kinds[path]=kind
        if len(path)==5 and path[:3]==inner and path[3] in self.counts and type(path[4]) is int:
            self.counts[path[3]]=path[4]+1
            if path[3]==self.group and self.offset<=path[4]<self.stop:
                self.rows.append(dict(index=path[4],kind=kind,offset=start,bytes=end-start,
                    sha256=hashlib.sha256(memoryview(raw)[start:end]).hexdigest(),value_state='NOT_LOADED'))
        if path in self.paths:
            self.metadata[path]=dict(offset=start,bytes=end-start,
                sha256=hashlib.sha256(memoryview(raw)[start:end]).hexdigest())


def _m18_rebound_value(reader, query):
    """Parse only captured small values after complete Reader verification."""
    from . import m18_offline_v2 as m
    source_page=reader.detail(M18_REBOUND_SECTION)
    m.require(source_page['matched_total']==1 and len(source_page['entries'])==1,'V2_REBOUND_SOURCE')
    source_entry=source_page['entries'][0]
    m.require(source_entry['kind']=='object' and 0<source_entry['bytes']<m.PROFILE['object_bytes'],'V2_OBJECT_BYTES')
    capture=reader._span_observer
    m.require(isinstance(capture,_M18ReboundSpans) and capture.group==query['group'],'V2_REBOUND_CAPTURE')
    inner=capture.prefix+('research_observation',)
    m.require(all(capture.kinds.get(path)=='object' for path in (capture.prefix,inner))
              and all(kind=='object' for path,kind in capture.kinds.items() if path in capture.containers)
              and all(capture.kinds.get(inner+(group,))=='array' for group in M18_REBOUND_GROUPS)
              and sum(capture.counts.values())<=m.v1.MAX_ENTRIES,'V2_REBOUND_SOURCE')
    binding=reader._binding();cursor=query.get('cursor');offset=capture.offset;total=capture.counts[capture.group]
    if cursor is not None:
        m.require(offset<total and cursor==_m18_rebound_cursor(binding,source_entry['sha256'],capture.group,offset),
                  'V2_REBOUND_CURSOR')
    def small_value(span, limit):
        m.require(0<span['bytes']<=limit,'V2_OBJECT_BYTES')
        raw=reader._full[span['offset']:span['offset']+span['bytes']]
        m.require(len(raw)==span['bytes'] and m.sha(raw)==span['sha256'],'V2_REBOUND_HASH')
        return m.parse(raw,'object',reader._guard)[0]
    entries=[];loaded=0;loaded_bytes=0
    for row in capture.rows:
        entry=dict(row)
        if entry['bytes']>M18_VIEW_ITEM_BYTES:entry['reason']='ITEM_BYTES_LIMIT'
        # Defer this loadable row to the next page rather than skipping its value.
        elif loaded_bytes+entry['bytes']>M18_VIEW_VALUES_BYTES:break
        else:
            entry.update(value=small_value(entry,M18_VIEW_ITEM_BYTES),value_state='LOADED')
            loaded+=1;loaded_bytes+=entry['bytes']
        entries.append(entry)
    meta=dict(source={},observation={})
    for path,target in capture.containers.items():
        if path in capture.kinds and target:
            node=meta
            for key in target:node=node.setdefault(key,{})
    m.require(sum(span['bytes'] for span in capture.metadata.values())<=M18_VIEW_BYTES,'V2_REBOUND_METADATA_BYTES')
    for path,span in capture.metadata.items():
        target=capture.paths[path];node=meta
        for key in target[:-1]:node=node.setdefault(key,{})
        node[target[-1]]=small_value(span,M18_VIEW_BYTES)
    metadata=dict(source_section_sha256=source_entry['sha256'],group_counts=dict(capture.counts),**meta)
    next_offset=offset+len(entries)
    return dict(schema=m.VERSION+'.detail',**binding,section=M18_REBOUND_SECTION,
        projection=M18_REBOUND_PROJECTION,group=capture.group,rebound=metadata,
        selection=None,cursor=cursor,offset=offset,matched_total=total,
        loaded_count=loaded,not_loaded_count=total-loaded,remaining_entries=total-next_offset,entries=entries,
        next_cursor=(_m18_rebound_cursor(binding,source_entry['sha256'],capture.group,next_offset)
                     if next_offset<total else None))


def _m18_us_mapping_cursor(binding, source_sha, offset):
    value = {key: binding[key] for key in (
        'manifest_sha256', 'generation_id', 'identity', 'profile_sha256')}
    value.update(section=M18_US_MAPPING_SECTION, projection=M18_US_MAPPING_PROJECTION,
        source_section_sha256=source_sha, selection_sha256=sha256_json(None), offset=offset)
    return base64.urlsafe_b64encode(canonical_bytes(value)).decode('ascii')


def _m18_us_mapping_fields(value, fields):
    """Retain only named, small source fields, including explicit false/null."""
    from . import m18_offline_v2 as m
    if value is None:return None
    m.require(type(value) is dict, 'V2_US_MAPPING_METADATA')
    result = {key: value[key] for key in fields if key in value}
    m.require(all(len(canonical_bytes(item)) <= M18_VIEW_ITEM_BYTES for item in result.values()),
              'V2_US_MAPPING_METADATA_BYTES')
    return result


class _M18UsMappingPlanSpan:
    """Observe only one closed sibling path in the Reader's existing full scan."""
    def __init__(self):
        self.span = None

    def __call__(self, path, kind, start, end, raw):
        if path != ('payload', 'owner_chain', 'us_mapping_daily_plan_reference'):return
        self.span = dict(kind=kind, offset=start, bytes=end-start)
        if end-start <= M18_VIEW_ITEM_BYTES:
            self.span['sha256'] = hashlib.sha256(memoryview(raw)[start:end]).hexdigest()


def _m18_us_mapping_plan_reference(reader):
    """Read one closed sibling reference from this frozen response, never an owner."""
    from . import m18_offline_v2 as m
    missing = lambda reason: dict(value_state='NOT_LOADED', reason=reason)
    if 'owner_chain' not in reader.overview()['sections']:
        return missing('OWNER_CHAIN_MISSING')
    page = reader.detail('owner_chain')
    if page['matched_total'] != 1 or len(page['entries']) != 1 or page['entries'][0]['kind'] != 'object':
        return missing('REFERENCE_INVALID')
    source_entry = page['entries'][0]
    capture = reader._span_observer
    m.require(isinstance(capture, _M18UsMappingPlanSpan), 'V2_US_MAPPING_CAPTURE')
    span = capture.span
    if span is None:return missing('REFERENCE_MISSING')
    if span['kind'] != 'object':return missing('REFERENCE_INVALID')
    if span['bytes'] > M18_VIEW_ITEM_BYTES:return missing('REFERENCE_BYTES_LIMIT')
    m.require(source_entry['offset'] <= span['offset']
              and span['offset']+span['bytes'] <= source_entry['offset']+source_entry['bytes'],
              'V2_US_MAPPING_REFERENCE_SPAN')
    raw = reader._full[span['offset']:span['offset']+span['bytes']]
    m.require(len(raw) == span['bytes'] and m.sha(raw) == span['sha256'], 'V2_US_MAPPING_REFERENCE_HASH')
    reference, _ = m.parse(raw, 'object', reader._guard)
    # The span/hash describes the complete original reference, while value is
    # deliberately only its named metadata (not the duplicate matches array).
    return dict(value_state='LOADED', source_section_sha256=source_entry['sha256'],
        source_span=dict(offset=span['offset'],
                         bytes=span['bytes'], sha256=span['sha256']),
        value=_m18_us_mapping_fields(reference, M18_US_MAPPING_PLAN_FIELDS))


def _m18_us_mapping_value(reader, query):
    """Project only daily_run.matches from one verified, object-bounded source."""
    from . import m18_offline_v2 as m
    m.v1.exact(query, ('section', 'projection') + (('cursor',) if 'cursor' in query else ()),
               'V2_PAGE_QUERY')
    m.require(query['section'] == M18_US_MAPPING_SECTION
              and query['projection'] == M18_US_MAPPING_PROJECTION, 'V2_PAGE_PROJECTION')
    raw, source, scanner, source_entry = _m18_projection_source(reader, M18_US_MAPPING_SECTION)
    daily = source.get('daily_run')
    m.require(type(daily) is dict and type(daily.get('matches')) is list, 'V2_US_MAPPING_SOURCE')
    # Reuse the existing grammar on the exact nested object; no arbitrary JSON
    # path, Reader changes, full-response parsing or extra observer is exposed.
    daily_span = scanner.sections['daily_run']['entries'][0]
    nested = m._Scan(raw, 'object', reader._guard)
    nested.position = daily_span['offset'];nested.value(path=('payload',))
    m.require(nested.position == daily_span['offset']+daily_span['bytes'], 'V2_US_MAPPING_SOURCE')
    reader._guard.scan_nodes += nested.nodes;reader._guard.scan_bytes += daily_span['bytes']
    reader._guard.checkpoint('us_mapping_nested_source')
    rows = nested.sections['matches']['entries'];matches = daily['matches']
    m.require(len(rows) == len(matches), 'V2_US_MAPPING_SOURCE')
    binding = reader._binding();cursor = query.get('cursor');offset = 0
    if cursor is not None:
        try:
            declared, _ = m.v1.parse(base64.b64decode(cursor, altchars=b'-_', validate=True), object_limit=True)
            offset = declared['offset']
        except (ValueError, KeyError, TypeError):
            raise ValueError('M18_CURSOR_INVALID') from None
        m.require(m.v1.integer(offset, 1, len(rows)-1)
                  and cursor == _m18_us_mapping_cursor(binding, source_entry['sha256'], offset),
                  'V2_US_MAPPING_CURSOR')
    entries = [];loaded = 0;loaded_bytes = 0
    for row in rows[offset:offset+m.v1.PAGE_SIZE]:
        entry = dict(row, offset=source_entry['offset']+row['offset'])
        if entry['bytes'] > M18_VIEW_ITEM_BYTES:entry['reason'] = 'ITEM_BYTES_LIMIT'
        elif loaded_bytes+entry['bytes'] > M18_VIEW_VALUES_BYTES:break
        else:
            entry.update(value=matches[row['index']], value_state='LOADED')
            loaded += 1;loaded_bytes += entry['bytes']
        entries.append(entry)
    source_meta = _m18_us_mapping_fields(source, M18_US_MAPPING_SOURCE_FIELDS)
    daily_meta = _m18_us_mapping_fields(daily, M18_US_MAPPING_DAILY_FIELDS)
    if 'coverage' in daily:
        daily_meta['coverage'] = _m18_us_mapping_fields(daily['coverage'], M18_US_MAPPING_DAILY_COVERAGE_FIELDS)
    coverage = source.get('coverage_diagnostics', {})
    if type(coverage) is dict and 'registry_readback' in coverage:
        source_meta['registry_readback'] = _m18_us_mapping_fields(
            coverage['registry_readback'], M18_US_MAPPING_REGISTRY_FIELDS)
    metadata = dict(source_section_sha256=source_entry['sha256'], match_count=len(rows),
        source=source_meta, daily_run=daily_meta,
        coverage_diagnostics=_m18_us_mapping_fields(coverage, M18_US_MAPPING_COVERAGE_FIELDS),
        plan_reference=_m18_us_mapping_plan_reference(reader))
    m.require(len(canonical_bytes(metadata)) <= M18_VIEW_VALUES_BYTES, 'V2_US_MAPPING_METADATA_BYTES')
    next_offset = offset+len(entries)
    return dict(schema=m.VERSION+'.detail', **binding, section=M18_US_MAPPING_SECTION,
        projection=M18_US_MAPPING_PROJECTION, us_mapping=metadata,
        selection=None, cursor=cursor, offset=offset, matched_total=len(rows),
        loaded_count=loaded, not_loaded_count=len(rows)-loaded,
        remaining_entries=len(rows)-next_offset, entries=entries,
        next_cursor=(_m18_us_mapping_cursor(binding, source_entry['sha256'], next_offset)
                     if next_offset < len(rows) else None))


def _m18_semantic_value(reader, kind, query):
    """Bound one verified Reader value inside the short-lived read process."""
    if kind == 'announcement':
        value = _m18_announcement_value(reader, query)
    elif kind == 'rebound':
        value = _m18_rebound_value(reader, query)
    elif kind == 'us_mapping':
        value = _m18_us_mapping_value(reader, query)
    elif kind == 'overview':
        value = reader.overview()
    else:
        section = query['section']
        value = reader.detail(section, cursor=query.get('cursor'))
        loaded_bytes = 0
        loaded_count = 0
        for entry in value['entries']:
            if entry['bytes'] > M18_VIEW_ITEM_BYTES:
                entry['reason'] = 'ITEM_BYTES_LIMIT'
                continue
            if loaded_bytes + entry['bytes'] > M18_VIEW_VALUES_BYTES:
                entry['reason'] = 'PAGE_BYTES_LIMIT'
                continue
            pieces = []
            size = 0
            for piece in reader.item_parts(section, entry['index']):
                size += len(piece)
                if size > M18_VIEW_ITEM_BYTES:
                    raise ValueError('M18_VIEW_ITEM_SIZE')
                pieces.append(piece)
            raw = b''.join(pieces)
            if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
                raise ValueError('M18_VIEW_ITEM_HASH')
            entry['value'] = json.loads(raw)
            entry['value_state'] = 'LOADED'
            loaded_bytes += size
            loaded_count += 1
        value['loaded_count'] = loaded_count
        value['not_loaded_count'] = value['matched_total'] - loaded_count
    if len(canonical_bytes(value)) > M18_VIEW_BYTES:
        raise ValueError('M18_VIEW_RESPONSE_LIMIT')
    return value


def _open_directory(path):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts:raise ValueError('MODULE_ROOT_PATH')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for component in path.parts[1:]:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child
        return fd
    except Exception:
        os.close(fd);raise


def _read_regular(fd,limit):
    before=os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size>limit:raise ValueError('MODULE_RECORD_SIZE_OR_TYPE')
    chunks=[];size=0
    while block:=os.read(fd,min(65536,limit+1-size)):
        chunks.append(block);size+=len(block)
        if size>limit:raise ValueError('MODULE_RECORD_SIZE')
    after=os.fstat(fd)
    if tuple(getattr(before,k) for k in ('st_ino','st_dev','st_size','st_mtime_ns','st_ctime_ns'))!=tuple(getattr(after,k) for k in ('st_ino','st_dev','st_size','st_mtime_ns','st_ctime_ns')) or size!=before.st_size:raise ValueError('MODULE_RECORD_CHANGED')
    return b''.join(chunks)


def _config(value):
    keys = ('schema_version', 'module_id', 'release_id', 'data_root', 'routes')
    # Ordinary module APIs retain their original exact schema. Only an M18
    # pages route requires the extra immutable disk binding.
    if isinstance(value, dict) and 'm18_v2_daily_publication' in value:
        keys += ('m18_v2_daily_publication',)
    if isinstance(value, dict) and 'm18_v2_binding' in value:
        keys += ('m18_v2_binding',)
    if isinstance(value, dict) and 'm06_hk_preselection_binding' in value:
        keys += ('m06_hk_preselection_binding',)
    if isinstance(value, dict) and 'm08_hk_stage_observed_binding' in value:
        keys += ('m08_hk_stage_observed_binding',)
    if isinstance(value, dict) and 'm09_a_close_replay_binding' in value:
        keys += ('m09_a_close_replay_binding',)
    if isinstance(value, dict) and 'm10_hk_close_binding' in value:
        keys += ('m10_hk_close_binding',)
    if isinstance(value, dict) and 'm17_close_recapture_binding' in value:
        keys += ('m17_close_recapture_binding',)
    if isinstance(value, dict) and 'm04_saved_research_binding' in value:
        keys += ('m04_saved_research_binding',)
    if isinstance(value, dict) and 'm12_video_fupan_binding' in value:
        keys += ('m12_video_fupan_binding',)
    if isinstance(value, dict) and 'm07_a_stage_binding' in value:
        keys += ('m07_a_stage_binding',)
    if isinstance(value, dict) and 'm11_saved_research_binding' in value:
        keys += ('m11_saved_research_binding',)
    if isinstance(value, dict) and 'm16_saved_public_research_binding' in value:
        keys += ('m16_saved_public_research_binding',)
    if isinstance(value, dict) and 'm04_research_lane_binding' in value:
        keys += ('m04_research_lane_binding',)
    exact_keys(value, keys)
    if 'm04_research_lane_binding' in value:
        from .research_workbench_readonly import validate_binding
        validate_binding(value)
    if 'm18_v2_daily_publication' in value:
        if (type(value['m18_v2_daily_publication']) is not bool
                or value['module_id'] != 'manager' or M18_ROUTE not in value['routes']):
            raise ValueError('M18_DAILY_PUBLICATION_CONFIG')
    if 'm16_saved_public_research_binding' in value:
        from .m16_readonly import validate_binding
        validate_binding(value)
    if 'm07_a_stage_binding' in value:
        from .m07_readonly import validate_binding
        validate_binding(value)
    if 'm11_saved_research_binding' in value:
        from .m11_readonly import validate_binding
        validate_binding(value)
    if 'm12_video_fupan_binding' in value:
        from .m12_readonly import validate_binding
        validate_binding(value)
    if 'm04_saved_research_binding' in value:
        from .m04_readonly import validate_binding
        validate_binding(value)
    if 'm17_close_recapture_binding' in value:
        if value['module_id'] != 'source_bundle' or M17_ROUTE not in value['routes']:
            raise ValueError('M17_READONLY_HOST_BINDING')
        from .m17_readonly import validate_binding
        validate_binding(value['m17_close_recapture_binding'])
    if 'm08_hk_stage_observed_binding' in value:
        from .m08_readonly import validate_binding
        validate_binding(value)
    if 'm09_a_close_replay_binding' in value:
        from .m09_readonly import validate_binding
        validate_binding(value)
    if 'm10_hk_close_binding' in value:
        from .m10_readonly import validate_binding
        validate_binding(value)
    if 'm06_hk_preselection_binding' in value:
        from .m06_readonly import validate_binding
        validate_binding(value)
    if value['module_id'] == 'manager' and any(
        route in (M18_ROUTE + '/pages', M18_ROUTE + '/overview', M18_ROUTE + '/sections')
        for route in value['routes']
    ):
        binding = value['m18_v2_binding']

        exact_keys(
            binding,
            (
                'manifest_sha256',
                'identity',
                'profile_sha256',
                'bundle_root',
            ),
        )

        exact_keys(
            binding['identity'],
            (
                'run_id',
                'target_date',
                'plan_sha256',
                'raw_sha256',
                'response_sha256',
                'input_identity',
            ),
        )

        sha(binding['manifest_sha256'])
        sha(binding['profile_sha256'])

        if binding['identity']['run_id'] != \
                '46596b03c2ab4e29b1219fd2e5eb698f':
            raise ValueError('M18_BINDING_RUN_ID')
    if value['schema_version']!='v5.module_api.v1' or not isinstance(value['module_id'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}',value['module_id']):raise ValueError('MODULE_CONFIG_INVALID')
    if not isinstance(value['release_id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',value['release_id']):raise ValueError('MODULE_RELEASE_REQUIRED')
    if not isinstance(value['routes'],list) or len(value['routes'])>100 or any(not isinstance(v,str) for v in value['routes']) or len(set(value['routes']))!=len(value['routes']):raise ValueError('MODULE_ROUTES_INVALID')
    if any(not isinstance(p,str) or not re.fullmatch(r'/api/[A-Za-z0-9_/-]+',p) for p in value['routes']):raise ValueError('MODULE_ROUTES_INVALID')
    root_fd=_open_directory(value['data_root'])
    try:
        marker_fd=os.open('.v5-module-root',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=root_fd)
        try:marker=_read_regular(marker_fd,256)
        finally:os.close(marker_fd)
        if marker!=('v5.module-root.v1:'+value['module_id']+'\n').encode():raise ValueError('MODULE_ROOT_IDENTITY')
        canonical_bytes(value)
        return json.loads(canonical_bytes(value)),root_fd
    except Exception:
        os.close(root_fd);raise


def _read_at(root_fd,directory,name):
    parent=root_fd if directory is None else os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root_fd)
    try:fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    finally:
        if directory is not None:os.close(parent)
    try:return _read_regular(fd,MAX_JSON_BYTES)
    finally:os.close(fd)


def _generation_head(root_fd,config,*,publication_locked=False):
    try:data=_read_at(root_fd,None,'active.json')
    except FileNotFoundError:
        try:mode=_read_at(root_fd,None,'.v5-generation-mode')
        except FileNotFoundError:return None
        expected=canonical_bytes(dict(schema_version='v5.generation_mode.v1',module_id=config['module_id'],release_id=config['release_id']))
        if mode!=expected:raise ValueError('MODULE_GENERATION_MODE_IDENTITY')
        lock=None
        try:
            if not publication_locked:
                lock=os.open('.publication.lock',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=root_fd)
                if not stat.S_ISREG(os.fstat(lock).st_mode):raise ValueError('MODULE_PUBLICATION_LOCK')
                deadline=time.monotonic()+1
                while True:
                    try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        if time.monotonic()>=deadline:raise ValueError('MODULE_PUBLICATION_BUSY')
                        time.sleep(0.005)
            # Re-read while protected: the first publisher may have installed
            # the pointer after our initial ENOENT but before the mode read.
            data=_read_at(root_fd,None,'active.json')
        except FileNotFoundError as error:raise ValueError('MODULE_ACTIVE_MISSING') from error
        finally:
            if lock is not None:os.close(lock)
    value=_parse_response(data)
    exact_keys(value,('schema_version','module_id','release_id','generation_sha256'))
    if (value['schema_version']!='v5.module_active.v1' or value['module_id']!=config['module_id']
            or value['release_id']!=config['release_id']):raise ValueError('MODULE_ACTIVE_IDENTITY')
    return sha(value['generation_sha256'])


def _load_generation(root_fd,config,generation):
    sha(generation)
    try:data=_read_at(root_fd,'generations',generation+'.json')
    except FileNotFoundError as error:raise ValueError('MODULE_GENERATION_MISSING') from error
    if hashlib.sha256(data).hexdigest()!=generation:raise ValueError('MODULE_GENERATION_DIGEST')
    value=_parse_response(data)
    exact_keys(value,('schema_version','module_id','release_id','records'))
    if (value['schema_version']!='v5.module_generation.v1' or value['module_id']!=config['module_id']
            or value['release_id']!=config['release_id']):raise ValueError('MODULE_GENERATION_IDENTITY')
    refs=value['records']
    if not isinstance(refs,dict) or not 1<=len(refs)<=10000:raise ValueError('MODULE_GENERATION_RECORDS')
    for key,digest in refs.items():sha(key);sha(digest)
    return value


def _parse_record(data, config):
    # Budget comes from trusted module config, never payload-supplied metadata.
    # Record identity is checked again by _validate_record / _validate_ref.
    candidate = (config.get('module_id') == 'manager'
                 and MANAGER_WORKSPACE_PATH in config.get('routes', []))
    value = _parse_response(data, manager_workspace=candidate)
    if candidate and not (isinstance(value, dict)
            and value.get('module_id') == 'manager'
            and value.get('schema_version') == 'v5.module_response.v1'
            and value.get('data_kind') == 'OWNER_RESULT'
            and _manager_response('manager', value.get('path'), status=value.get('status_code'))):
        # Other records remain subject to the default, including manager errors.
        _precheck_json(data)
        _bounded_json(value)
    return value


def _read_object(root_fd,digest,config=None):
    sha(digest)
    try:data=_read_at(root_fd,'objects',digest+'.json')
    except FileNotFoundError as error:raise ValueError('MODULE_OBJECT_MISSING') from error
    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('MODULE_OBJECT_DIGEST')
    return (_parse_record(data,config) if config is not None else _parse_response(data)),data


def _read_record(root_fd,key,config):
    generation=_generation_head(root_fd,config)
    if generation is None:
        data=_read_at(root_fd,'responses',key+'.json')
        return _parse_record(data,config),hashlib.sha256(data).hexdigest()
    refs=_load_generation(root_fd,config,generation)['records']
    if key not in refs:raise FileNotFoundError('MODULE_RESULT_NOT_AVAILABLE')
    record,data=_read_object(root_fd,refs[key],config)
    return record,hashlib.sha256(data).hexdigest()


def _validate_record(config,record,path,query):
    exact_keys(record,('schema_version','module_id','release_id','path','query','payload','payload_sha256','source_input_sha256','data_kind','generated_at','status_code'))
    if (record['schema_version']!='v5.module_response.v1' or record['module_id']!=config['module_id']
        or record['release_id']!=config['release_id'] or record['path']!=path or record['query']!=query):raise ValueError('MODULE_RECORD_IDENTITY')
    if path not in config['routes'] and not (
            config['module_id']=='source_bundle' and path in SOURCE_BUNDLE_READ_ONLY_COMPAT_ROUTES
    ):raise ValueError('MODULE_ROUTE_NOT_CONFIGURED')
    if (not isinstance(query,dict) or len(query)>128 or any(not isinstance(k,str) or not isinstance(v,str) for k,v in query.items())):raise ValueError('MODULE_QUERY_INVALID')
    if record['data_kind'] not in ('SYNTHETIC','RECORDED_INPUT_REPLAY','OWNER_RESULT'):raise ValueError('MODULE_DATA_KIND')
    if type(record['status_code']) is not int or record['status_code'] not in (200,400,404,409,422,429,499,500,502,503,504):raise ValueError('MODULE_HTTP_STATUS')
    aware(record['generated_at']);sha(record['source_input_sha256']);sha(record['payload_sha256'])
    if not isinstance(record['payload'],dict) or sha256_json(record['payload'])!=record['payload_sha256']:raise ValueError('MODULE_PAYLOAD_DIGEST')
    return record


def _research_date_catalog(config,root_fd):
    """List only exact-date day products that already exist in the source-bundle store."""
    dates=set()
    generation=_generation_head(root_fd,config)
    if generation is not None:
        refs=_load_generation(root_fd,config,generation)['records']
        records=[_read_object(root_fd,digest,config)[0] for digest in refs.values()]
    else:
        try:
            directory=os.open('responses',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root_fd)
        except FileNotFoundError:
            directory=None
        records=[]
        if directory is not None:
            try:
                names=os.listdir(directory)
                if len(names)>10000:raise ValueError('RESEARCH_DATE_CATALOG_LIMIT')
                for name in names:
                    if not re.fullmatch(r'[0-9a-f]{64}\\.json',name):continue
                    raw=_read_at(root_fd,'responses',name)
                    records.append(_parse_record(raw,config))
            finally:os.close(directory)
    for record in records:
        if record.get('path')!='/api/v3/research/day' or record.get('status_code')!=200:
            continue
        query=record.get('query')
        if not isinstance(query,dict) or set(query)!={'archive_date'}:
            continue
        date=query.get('archive_date')
        if not isinstance(date,str) or not re.fullmatch(r'[0-9]{8}',date):
            continue
        try:
            if datetime.strptime(date,'%Y%m%d').strftime('%Y%m%d')!=date:continue
        except ValueError:
            continue
        _validate_record(config,record,'/api/v3/research/day',query)
        payload=record.get('payload')
        if not isinstance(payload,dict) or payload.get('schema_version')!='v3_5.research_day_product.v1':
            continue
        if payload.get('endpoint_mode')!='EXACT' or payload.get('archive_date')!=date or payload.get('requested_date')!=date:
            continue
        dates.add(date)
    ordered=sorted(dates,reverse=True)
    return dict(schema_version='v5.research_date_catalog.v1',
        status='READY_WITH_DECLARED_GAPS' if ordered else 'NOT_MATERIALIZED',
        default_date=ordered[0] if ordered else None,dates=ordered,
        stage_dates=[],future_target_dates=[],
        catalog_scope='PUBLISHED_EXACT_RESEARCH_DAY_PRODUCTS_ONLY',
        cannot_confirm=['V4_RUN_DATE_CATALOG_NOT_MIGRATED'],
        read_only=True,production_allowed=False,buy_gate_updated=False,orders_sent=False)


def read_response(config,root,path,query):
    if config['module_id'] == 'manager' and path == M18_ROUTE:
        if query == {} and config.get('m18_v2_daily_publication') is not True:
            binding = config.get('m18_v2_binding')
            if binding is None:
                raise FileNotFoundError('M18_READER_NOT_READY')
            return read_response(config, root, path, {'run_id': binding['identity']['run_id']})
        if query != {}:
            exact_keys(query, ('run_id',))
            if not isinstance(query['run_id'], str) or not re.fullmatch('[0-9a-f]{32}', query['run_id']):
                raise ValueError('M18_RUN_ID')
        record, digest = _read_record(root, response_key(config['module_id'], path, query), config)
        _validate_record(config, record, path, query)
        descriptor = _m18_identity_from_descriptor(record['payload'])
        if query and descriptor['run_id'] != query['run_id']:
            raise ValueError('M18_IDENTITY_MISMATCH')
        if 'manifest_sha256' in descriptor and config.get('m18_v2_daily_publication') is not True:
            raise ValueError('M18_DAILY_PUBLICATION_DISABLED')
        return record, digest
    if config['module_id']=='source_bundle' and path==M17_ROUTE:
        # This route can never fall back to a cached module-response record.
        # Every GET must cold-read the exact configured original ledger run.
        exact_keys(query, ('source_trade_date', 'run_id'))
        binding=config.get('m17_close_recapture_binding')
        if binding is None:raise FileNotFoundError('M17_REFERENCE_NOT_CONFIGURED')
        from .m17_readonly import get_response
        payload=get_response(binding,query)
        record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],
            release_id=config['release_id'],path=path,query=query,payload=payload,
            payload_sha256=sha256_json(payload),source_input_sha256=binding['identity']['input_sha256'],
            data_kind='OWNER_RESULT',generated_at=payload['available_at'],status_code=200)
        return _validate_record(config,record,path,query),sha256_json(record)
    if config['module_id']=='source_bundle' and path in (M07_ROUTE, M16_ROUTE, M11_ROUTE, M12_ROUTE, M04_ROUTE, '/api/v5/source-bundle/hk-preselection','/api/v5/source-bundle/hk-close-review', '/api/v5/source-bundle/a-close-replay', '/api/v5/source-bundle/hk-stage-observed'):
        if path==M07_ROUTE:
            from .m07_readonly import read_record,not_configured
        elif path==M16_ROUTE:
            from .m16_readonly import read_record,not_configured
        elif path==M11_ROUTE:
            from .m11_readonly import read_record,not_configured
        elif path==M12_ROUTE:
            from .m12_readonly import read_record,not_configured
        elif path==M04_ROUTE:
            from .m04_readonly import read_record,not_configured
        elif path=='/api/v5/source-bundle/hk-stage-observed':
            from .m08_readonly import read_record,not_configured
        elif path=='/api/v5/source-bundle/a-close-replay':
            from .m09_readonly import read_record,not_configured
        elif path=='/api/v5/source-bundle/hk-close-review':
            from .m10_readonly import read_record,not_configured
        else:
            from .m06_readonly import read_record,not_configured
        projected=read_record(config,query)
        if projected is not None:return projected
        payload=not_configured()
        record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],
            release_id=config['release_id'],path=path,query={},payload=payload,
            payload_sha256=sha256_json(payload),source_input_sha256=sha256_json(payload),
            data_kind='OWNER_RESULT',generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status_code=200)
        return _validate_record(config,record,path,query),sha256_json(record)
    record,digest=_read_record(root,response_key(config['module_id'],path,query),config)
    return _validate_record(config,record,path,query),digest


def create_module_server(value,host='127.0.0.1',port=0):
    if host!='127.0.0.1':raise ValueError('LOOPBACK_ONLY')
    config,root=_config(value)
    if any(route in config['routes'] for route in
           (M18_ROUTE + '/pages', M18_ROUTE + '/overview', M18_ROUTE + '/sections', M17_ROUTE, M07_ROUTE, M11_ROUTE, M12_ROUTE, M04_ROUTE, '/api/v5/source-bundle/hk-preselection', '/api/v5/source-bundle/hk-close-review', '/api/v5/source-bundle/a-close-replay', '/api/v5/source-bundle/hk-stage-observed')):
        # Set at service startup, before any GET can spawn/import a reader.
        # Also covers library callers that did not start their interpreter -B.
        sys.dont_write_bytecode=True
        os.environ['PYTHONDONTWRITEBYTECODE']='1'
    # One heavy read at a time; do not queue stale browser requests or allow
    # multiple full Reader allocations. Ordinary module routes stay independent.
    m18_read_slot=threading.BoundedSemaphore(1)
    # Independent M10 reader: simultaneous source-page mounts cannot starve M06.
    m10_read_slot=threading.BoundedSemaphore(1)
    m09_read_slot=threading.BoundedSemaphore(1)
    m08_read_slot=threading.BoundedSemaphore(1)
    m17_read_slot=threading.BoundedSemaphore(1)
    m07_read_slot=threading.BoundedSemaphore(1)
    m16_read_slot=threading.BoundedSemaphore(1)
    m11_read_slot=threading.BoundedSemaphore(1)
    m12_read_slot=threading.BoundedSemaphore(1)
    m04_read_slot=threading.BoundedSemaphore(1)
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup();self.connection.settimeout(5)
            def expire():
                try:self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            self.timer=threading.Timer(5,expire);self.timer.daemon=True;self.timer.start()
        def finish(self):
            self.timer.cancel();super().finish()
        def log_message(self,*args):pass
        def reply(self,status,payload,digest=None):
            data=canonical_bytes(payload);self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-V5-Module',config['module_id']);self.send_header('X-V5-Release',config['release_id'])
            if config['module_id']=='manager':self.send_header('X-V5-Workspace-Access','READ_ONLY')
            if digest:self.send_header('X-V5-Record-SHA256',digest)
            self.end_headers()
            try:
                if getattr(self,'command',None)!='HEAD':self.wfile.write(data)
            except OSError:pass
        def error(self,status,reason):self.reply(status,dict(status='CANNOT_CONFIRM',reason_codes=[reason],module_id=config['module_id']))
        def do_POST(self):self.error(405,'MODULE_READ_ONLY')
        do_PUT=do_POST
        do_DELETE=do_POST
        do_OPTIONS=do_POST
        do_PATCH=do_POST
        do_TRACE=do_POST
        do_HEAD=do_POST
        def send_error(self,code,message=None,explain=None):
            self.error(405 if code==501 else code,'MODULE_READ_ONLY' if code==501 else 'MODULE_REQUEST_INVALID')
        def do_GET(self):
            hosts=('127.0.0.1:'+str(self.server.server_address[1]),'localhost:'+str(self.server.server_address[1]))
            if len(self.headers.get_all('Host',[]))!=1 or len(self.headers.get_all('Origin',[]))>1:return self.error(400,'MODULE_HEADERS_INVALID')
            if self.headers.get('Host') not in hosts:return self.error(403,'HOST_REJECTED')
            if self.headers.get('Origin') and self.headers['Origin'] not in ['http://'+h for h in hosts]:return self.error(403,'ORIGIN_REJECTED')
            if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Length','0')!='0' or len(self.path)>8192:return self.error(400,'MODULE_REQUEST_INVALID')
            try:
                parsed=urlsplit(self.path)
                if parsed.scheme or parsed.netloc:raise ValueError('MODULE_REQUEST_INVALID')
                multi=parse_qs(parsed.query,keep_blank_values=True,max_num_fields=128)
                if any(len(v)!=1 for v in multi.values()):raise ValueError('MODULE_QUERY_INVALID')
                query={k:v[0] for k,v in multi.items()};self.timer.cancel()
            except ValueError:return self.error(400,'MODULE_QUERY_INVALID')
            if parsed.path=='/__v5/module-health':
                return self.reply(200,dict(status='READ_ONLY_RESPONSE_SERVICE',module_id=config['module_id'],release_id=config['release_id'],pid=os.getpid(),
                    implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),config_sha256=sha256_json(config),source_provenance_verified=False))
            if parsed.path not in config['routes'] and not (
                    config['module_id']=='source_bundle' and parsed.path in SOURCE_BUNDLE_READ_ONLY_COMPAT_ROUTES
            ):return self.error(404,'MODULE_ROUTE_NOT_CONFIGURED')
            heavy = parsed.path in (M18_ROUTE + '/pages', M18_ROUTE + '/overview', M18_ROUTE + '/sections') or (config['module_id']=='source_bundle' and parsed.path in (M07_ROUTE, M16_ROUTE, M11_ROUTE, M12_ROUTE, M04_ROUTE, '/api/v5/source-bundle/hk-preselection','/api/v5/source-bundle/hk-close-review', '/api/v5/source-bundle/a-close-replay', '/api/v5/source-bundle/hk-stage-observed', '/api/v3/research/day', '/api/v1/runs/date-list'))
            heavy = heavy or (config['module_id']=='source_bundle' and parsed.path==M17_ROUTE)
            research_path = config['module_id']=='source_bundle' and parsed.path in ('/api/v5/research/lane','/api/v5/research/wechat/materials')
            heavy = heavy or research_path
            reader_slot = m10_read_slot if config['module_id']=='source_bundle' and parsed.path=='/api/v5/source-bundle/hk-close-review' else m18_read_slot
            if config['module_id']=='source_bundle' and parsed.path=='/api/v5/source-bundle/a-close-replay':
                reader_slot=m09_read_slot
            if config['module_id']=='source_bundle' and parsed.path=='/api/v5/source-bundle/hk-stage-observed':
                reader_slot=m08_read_slot
            if config['module_id']=='source_bundle' and parsed.path==M17_ROUTE:
                reader_slot=m17_read_slot
            if config['module_id']=='source_bundle' and parsed.path==M04_ROUTE:
                reader_slot=m04_read_slot
            if config['module_id']=='source_bundle' and parsed.path==M07_ROUTE:
                reader_slot=m07_read_slot
            if config['module_id']=='source_bundle' and parsed.path==M16_ROUTE:
                reader_slot=m16_read_slot
            if config['module_id']=='source_bundle' and parsed.path==M11_ROUTE:
                reader_slot=m11_read_slot
            if config['module_id']=='source_bundle' and parsed.path==M12_ROUTE:
                reader_slot=m12_read_slot
            if research_path or (config['module_id']=='source_bundle' and parsed.path in ('/api/v3/research/day','/api/v1/runs/date-list')):
                reader_slot=m04_read_slot
            if heavy and not reader_slot.acquire(blocking=False):
                return self.error(503, 'MODULE_BUSY')
            try:
                if research_path:
                    from .research_workbench_readonly import response
                    status,payload=response(config,parsed.path,query)
                    self.reply(status,payload,sha256_json(payload))
                elif config['module_id']=='source_bundle' and parsed.path=='/api/v1/runs/date-list':
                    if query:raise ValueError('RESEARCH_DATE_CATALOG_QUERY')
                    payload=_research_date_catalog(config,root)
                    self.reply(200,payload,sha256_json(payload))
                elif config['module_id']=='source_bundle' and parsed.path==M17_ROUTE:
                    required={'source_trade_date','run_id'}
                    source_date=query.get('source_trade_date')
                    run_id=query.get('run_id')
                    valid_date=False
                    if isinstance(source_date,str) and re.fullmatch(r'[0-9]{8}',source_date):
                        try: valid_date=datetime.strptime(source_date,'%Y%m%d').strftime('%Y%m%d')==source_date
                        except ValueError: valid_date=False
                    if set(query)!=required or not valid_date or not isinstance(run_id,str) or not re.fullmatch(r'[0-9a-f]{32}',run_id):
                        self.error(400,'M17_QUERY_INVALID')
                    elif config.get('m17_close_recapture_binding') is None:
                        self.error(503,'M17_BINDING_NOT_CONFIGURED')
                    else:
                        try:
                            record,digest=read_response(config,root,parsed.path,query)
                            self.reply(record['status_code'],record['payload'],digest)
                        except TimeoutError:
                            self.error(503,'M17_READER_TIMEOUT')
                        except FileNotFoundError:
                            self.error(503,'M17_SAVED_PRODUCT_NOT_AVAILABLE')
                        except ValueError as error:
                            code=str(error)
                            if code in M17_BINDING_ERROR_CODES:self.error(409,'M17_BINDING_INVALID')
                            elif code in M17_UNAVAILABLE_ERROR_CODES:self.error(503,'M17_SAVED_PRODUCT_NOT_AVAILABLE')
                            elif code in M17_READER_ERROR_CODES:self.error(503,'M17_READER_UNAVAILABLE')
                            elif code in M17_PRODUCT_ERROR_CODES:self.error(409,'M17_PRODUCT_INVALID')
                            else:self.error(500,'M17_INTERNAL_ERROR')
                        except (TypeError,KeyError,OSError,RecursionError):
                            self.error(500,'M17_INTERNAL_ERROR')
                elif parsed.path == M18_ROUTE + '/pages':
                    payload = _m18_page_response(config,root,query)
                    self.reply(200,payload,sha256_json(payload))
                elif parsed.path in (M18_ROUTE + '/overview', M18_ROUTE + '/sections'):
                    payload = _m18_semantic_response(config,root,parsed.path,query)
                    self.reply(200,payload,sha256_json(payload))
                else:
                    record,digest=read_response(config,root,parsed.path,query)
                    self.reply(record['status_code'],record['payload'],digest)
            except TimeoutError:self.error(503,'RESEARCH_READER_TIMEOUT')
            except FileNotFoundError:self.error(503,'MODULE_RESULT_NOT_AVAILABLE')
            except ValueError as error:
                self.error(503,'MODULE_BUSY') if str(error)=='MODULE_PUBLICATION_BUSY' else self.error(409,'MODULE_RESULT_INVALID')
            except (TypeError,KeyError,OSError,RecursionError):self.error(409,'MODULE_RESULT_INVALID')
            finally:
                if heavy:reader_slot.release()
    class Server(ThreadingHTTPServer):
        daemon_threads=False
        block_on_close=True
        slots=threading.BoundedSemaphore(8)
        def process_request(self,request,address):
            if not self.slots.acquire(blocking=False):
                try:
                    body=b'{"status":"CANNOT_CONFIRM","reason_codes":["MODULE_BUSY"]}'
                    request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body)).encode()+b'\r\nConnection: close\r\n\r\n'+body)
                except OSError:pass
                self.shutdown_request(request);return
            try:super().process_request(request,address)
            except Exception:
                self.slots.release();raise
        def process_request_thread(self,request,address):
            try:super().process_request_thread(request,address)
            finally:self.slots.release()
        def server_close(self):
            try:super().server_close()
            finally:
                if getattr(self,'root_fd',None) is not None:
                    os.close(self.root_fd);self.root_fd=None
    try:server=Server((host,port),Handler)
    except Exception:
        os.close(root);raise
    server.root_fd=root
    return server


def main(argv=None):
    parser=argparse.ArgumentParser(description='One V5 module, one read-only API process')
    parser.add_argument('--config',required=True);parser.add_argument('--port',type=int,required=True)
    args=parser.parse_args(argv)
    with open(args.config,encoding='utf-8') as stream:config=json.load(stream)
    server=create_module_server(config,port=args.port)
    print('http://127.0.0.1:'+str(server.server_address[1]),flush=True)
    try:server.serve_forever()
    finally:server.server_close()

if __name__=='__main__':main()

