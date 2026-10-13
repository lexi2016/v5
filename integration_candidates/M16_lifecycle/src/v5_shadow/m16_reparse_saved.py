"""Explicit offline PDF recovery. No provider construction, ensure, or transport.

Reads original input/product/material identities, previews by default, and uses
original admission + commit_result fencing only on explicit apply.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re
from uuid import uuid4

from .manager_loader import load_owner
from .m16_runtime import closure, PinnedObservationReader

ALLOWED_CODES = frozenset({'HK.02583', 'HK.01081', 'HK.00376'})


def _module(name):
    return importlib.import_module('m16_owner_manager_research.' + name)


def _financial_row(service, data, product, observation, row, result):
    date = data["target_trade_date"]
    built = service.ManagerResearchJobService._build_product(data,[observation],{row["code"]:result})['rows'][0]
    if not built['facts'] or len(built['facts']) != len(result['facts']):
        raise ValueError('M16_REPARSE_FACT_CONTRACT_INVALID')
    # Original recommendation builder, original generation time and PIT data.
    built['research_recommendation'] = service.build_research_recommendation(
        observation=observation,result={**result,'facts':built['facts']},target_trade_date=date,
        cutoff_at=data['cutoff_at'],generated_at=product['generated_at'],input_source_sha256=data.get('input_source_sha256'),
        stage_status=product.get('stage_status'),cannot_confirm=product.get('cannot_confirm',[]))
    replacement = deepcopy(row)
    for key in ('status','decision','direction','thesis_cn','facts','inferences_cn','counterevidence_cn',
                'confirmation_conditions','invalidation_conditions','research_next_action','source','source_url',
                'source_status','source_reason','source_failure_detail','research_recommendation'):
        replacement[key] = built[key]
    # Reuse the owner's pure financial projection on this row only.
    # Existing event evidence/ranks and every unselected row remain intact.
    replacement = service.ManagerResearchJobService._project_cached_financial_advice({'rows':[replacement]})['rows'][0]
    return replacement

def _financial_summary(service, updated, replacements):
    ready = sum(row.get('status') == 'READY' and bool(row.get('facts')) for row in updated['rows'])
    total = len(updated['rows'])
    updated['status'] = 'READY' if ready == total else 'PARTIAL_WITH_ROWS' if ready else 'CANNOT_CONFIRM'
    updated['coverage'] = dict(requested_rows=total,ready_rows=ready,cannot_confirm_rows=total-ready,coverage_ratio=round(ready/total,6))
    updated['recommendation_summary'] = service.recommendation_summary([row['research_recommendation'] for row in updated['rows'] if isinstance(row.get('research_recommendation'),dict)])
    updated['source_receipts'] = [({**receipt,**replacements[receipt['code']]['source'],'status':'READY','reason':'OFFICIAL_PDF_FACTS_EXTRACTED'} if receipt.get('code') in replacements else receipt) for receipt in updated.get('source_receipts',[])]
    if isinstance(updated.get('current_research'),dict):
        updated['current_research']['financial_research_status'] = updated['status']
    return updated


def reparse_saved(*, runtime_root: Path, input_path: Path, input_sha256: str,
                  target_trade_date: str, expected_product_sha256: str,
                  codes: list[str], apply: bool = False) -> dict:
    """Reparse only selected, already-matched PDFs; never repair issuer identity."""
    if not runtime_root.is_absolute() or not runtime_root.is_dir():
        raise ValueError('M16_EXISTING_RUNTIME_REQUIRED')
    if any(p.is_symlink() for p in (runtime_root, *runtime_root.parents)):
        raise ValueError('M16_RUNTIME_SYMLINK_REFUSED')
    for relative in ('jobs','products','receipts','materials','materials/index','materials/blobs'):
        member = runtime_root / relative
        if not member.is_dir() or member.is_symlink():
            raise ValueError('M16_INITIALIZED_RUNTIME_REQUIRED')
    if not codes or len(codes) != len(set(codes)) or not set(codes) <= ALLOWED_CODES:
        raise ValueError('M16_REPARSE_CODE_SCOPE')
    if not re.fullmatch('[0-9a-f]{64}', expected_product_sha256):
        raise ValueError('M16_PRODUCT_SHA_REQUIRED')
    components = load_owner(closure())['components']
    contracts, service, provider = (_module(n) for n in ('contracts','service','hkex_provider'))
    transport, materials, parser = (_module(n) for n in ('material_transport','materials','pdf_parser'))
    original = PinnedObservationReader(input_path, input_sha256).read(target_trade_date)
    data = contracts.normalise_observation_input(original)
    store = components.store_class(runtime_root)
    date, identity = data['target_trade_date'], data['input_identity']
    product = store.read_product(date, identity)
    digest = contracts.sha256_json
    if product is None or digest(product) != expected_product_sha256:
        raise ValueError('M16_PRODUCT_IDENTITY_OR_SHA_MISMATCH')
    for key in ('target_trade_date','input_identity','input_source_sha256','cutoff_at','stage_id','market','input_row_count'):
        if product.get(key) != data.get(key):
            raise ValueError('M16_PRODUCT_INPUT_BINDING_MISMATCH')
    if product.get('historical_system_available') is not False:
        raise ValueError('M16_HISTORICAL_BOUNDARY_REQUIRED')
    original_job_id = service.ManagerResearchJobService._job_id(data)
    committed = store._read_commit(date, identity)
    original_job = committed.get('jobs', {}).get(original_job_id) if committed else None
    original_receipt = committed.get('receipts', {}).get(original_job_id) if committed else None
    if (not original_job or not original_receipt or original_job.get('status') in {'QUEUED','RUNNING','CANCELLED'}
            or original_receipt.get('job_id') != original_job_id
            or original_receipt.get('input_identity') != identity or original_receipt.get('target_trade_date') != date):
        raise ValueError('M16_ORIGINAL_COMMITTED_JOB_REQUIRED')
    for key in ('target_trade_date','input_identity','input_source_sha256','cutoff_at','stage_id','market','input_row_count'):
        if original_job.get(key) != data.get(key):
            raise ValueError('M16_ORIGINAL_JOB_INPUT_BINDING_MISMATCH')
    observations = {row['code']: row for row in data['rows']}
    old_rows = {row['code']: row for row in product['rows']}
    if len(old_rows) != len(product['rows']) or set(old_rows) != set(observations):
        raise ValueError('M16_PRODUCT_ROW_BINDING_MISMATCH')
    material_store = components.material_store_class(runtime_root / 'materials')
    parsed_transport = transport.MaterialTransport(material_store, lambda *a, **k: (_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN')), namespace='hkex-official')
    replacements, evidence = {}, []
    # Validate all bytes and provenance before any parser/cache/job writes.
    prepared = []
    for code in codes:
        row = old_rows.get(code)
        result = original_job.get('results', {}).get(code)
        if not row or not isinstance(result, dict) or not isinstance(row.get('source'), dict):
            raise ValueError('M16_SAVED_SOURCE_REQUIRED')
        source = row['source']
        if source != result.get('source'):
            raise ValueError('M16_SOURCE_JOB_BINDING_MISMATCH')
        if (source.get('source_kind') != 'HKEX_OFFICIAL_ISSUER_ANNOUNCEMENT'
                or source.get('issuer_code') != code or not source.get('matching_basis')
                or not source.get('issuer_mapping_sha256') or not source.get('directory_sha256')
                or source.get('report_selection') != 'LATEST_EFFECTIVE_REPORT'
                or not provider._safe_official_url(str(source.get('url', '')))
                or not str(source.get('url', '')).lower().endswith('.pdf')):
            raise ValueError('M16_SAVED_SOURCE_PROVENANCE_INVALID')
        if datetime.fromisoformat(source['published_at']) > datetime.fromisoformat(data['cutoff_at']):
            raise ValueError('M16_SOURCE_AFTER_CUTOFF')
        key = 'hkex-official:' + source['url']
        entry = material_store.stat_source(key)
        if (not entry or entry.get('source_key') != key or entry.get('url') != source['url']
                or entry.get('retrieved_at') != source.get('retrieved_at')
                or not re.fullmatch('[0-9a-f]{64}', str(entry.get('sha256','')))):
            raise ValueError('M16_SAVED_MATERIAL_INDEX_MISMATCH')
        envelope = material_store._io.read_bytes(material_store._blob_relative(entry['sha256']))
        if sha256(envelope).hexdigest() != entry['sha256']:
            raise ValueError('M16_MATERIAL_ENVELOPE_HASH_MISMATCH')
        material = materials.Material(key, source['url'], entry['sha256'], entry['retrieved_at'], entry.get('content_type'), envelope, True)
        response = transport.response_from_material(material)
        if (not 200 <= response.status_code < 300
                or (response.final_url and not provider._safe_official_url(response.final_url))
                or sha256(response.body).hexdigest() != source.get('sha256')
                or len(response.body) != source.get('bytes') or not response.body.startswith(b'%PDF-')):
            raise ValueError('M16_SAVED_PDF_HASH_OR_PROVENANCE_MISMATCH')
        prepared.append((code, row, source, material, response.body))
    updated = deepcopy(product)
    for code, row, source, material, body in prepared:
        title = str(source.get('document_title',''))
        if apply:
            facts, pages = parsed_transport.parsed(material, parser_id='hkex-pdf-facts', parser_version=provider.PDF_FACTS_CACHE_VERSION,
                params={'title':title}, parse_fn=lambda raw, title=title: parser.extract_pdf_facts(raw,title=title))
        else:
            facts, pages = parser.extract_pdf_facts(body,title=title)
        if not facts:
            raise ValueError('M16_REPARSE_NO_STRUCTURED_FACTS')
        new_source = deepcopy(source)
        new_source.update(parse_status='STRUCTURED_FACTS',pdf_page_count=len(pages),text_locators=[f"PDF page {p['page']}" for p in pages][:12])
        result = dict(status='READY',reason='OFFICIAL_PDF_FACTS_EXTRACTED',issuer=row.get('issuer'),source=new_source,facts=facts)
        replacement = _financial_row(service, data, product, observations[code], row, result)
        replacements[code] = replacement
        evidence.append(dict(code=code,pdf_sha256=source['sha256'],material_sha256=material.sha256,
            old_fact_count=len(row.get('facts',[])),new_fact_count=len(facts),pdf_page_count=len(pages)))
    updated['rows'] = [replacements.get(row['code'],row) for row in updated['rows']]
    _financial_summary(service, updated, replacements)
    total = len(updated["rows"])
    report = dict(mode='OFFLINE_PDF_REPARSE',applied=False,input_identity=identity,target_trade_date=date,
        previous_product_sha256=expected_product_sha256,product_sha256=digest(updated),parser_cache_version=provider.PDF_FACTS_CACHE_VERSION,
        rows=evidence,network_calls=0)
    if not apply:
        return report
    job_id = f"mr-pdf-{date}-{identity[:16]}-v{provider.PDF_FACTS_CACHE_VERSION}-{expected_product_sha256[:12]}"
    now = service._now()
    def require_unchanged(latest):
        if digest(latest) != expected_product_sha256:
            raise ValueError('M16_PRODUCT_CHANGED_DURING_REPARSE')
        for other in store.list_jobs(date):
            if other.get('input_identity') == identity and other.get('job_id') != job_id and other.get('status') in {'QUEUED','RUNNING'}:
                raise ValueError('M16_OTHER_JOB_ACTIVE')
        return updated
    with store._transaction(date, identity):
        require_unchanged(store.read_product(date,identity))
        prior = store.read_job(job_id)
        job = dict(schema_version=service.JOB_SCHEMA_VERSION,kind='MANAGER_RESEARCH_JOB',mode='OFFLINE_PDF_REPARSE',
            job_id=job_id,generation=uuid4().hex,attempt=int(prior.get('attempt',0))+1 if prior else 1,
            target_trade_date=date,input_identity=identity,input_source_sha256=data.get('input_source_sha256'),
            stage_id=data['stage_id'],market=data['market'],cutoff_at=data['cutoff_at'],input_row_count=total,
            status='QUEUED',created_at=now,updated_at=now,can_retry=False,results={},**service.FOUR_FLAGS)
        store.admit_job(job)
    try:
        job.update(status='RUNNING',started_at=now); store.write_job(job)
        job.update(status=updated['status'],completed_at=service._now(),results={code:{'status':'READY','source':replacements[code]['source'],'facts':replacements[code]['facts']} for code in codes})
        receipt = dict(report, schema_version='v4.manager_research.receipt.v1',job_id=job_id,
            generated_at=now,status=job['status'],applied=True,previous_product=product,previous_job=original_job,
            previous_receipt=original_receipt,**service.FOUR_FLAGS)
        store.commit_result(job,updated,receipt,merge=require_unchanged)
    except Exception:
        job.update(status='FAILED',error='OFFLINE_PDF_REPARSE_COMMIT_FAILED',completed_at=service._now())
        try: store.write_job(job)
        except Exception: pass
        raise
    return {**report,'applied':True,'job_id':job_id,'generation':job['generation']}


def repair_missing_receipt_status(*, runtime_root: Path, input_path: Path, input_sha256: str,
        target_trade_date: str, expected_product_sha256: str, expected_commit_sha256: str,
        expected_commit_file_sha256: str, job_id: str, generation: str, apply: bool = False) -> dict:
    """Publish the same product with a new valid receipt; preserve the bad one.

    Only the known OFFLINE_PDF_REPARSE missing-status defect is accepted. This
    does not parse PDFs, reinterpret terminal states, or rewrite old receipts.
    """
    if (not runtime_root.is_absolute() or not runtime_root.is_dir()
            or any(p.is_symlink() for p in (runtime_root,*runtime_root.parents))
            or any(not (runtime_root/p).is_dir() or (runtime_root/p).is_symlink() for p in ('jobs','products','receipts'))):
        raise ValueError('M16_INITIALIZED_RUNTIME_REQUIRED')
    for value in (expected_product_sha256,expected_commit_sha256,expected_commit_file_sha256):
        if not re.fullmatch('[0-9a-f]{64}',value): raise ValueError('M16_RECEIPT_RECOVERY_PIN_REQUIRED')
    components=load_owner(closure())['components']; contracts=_module('contracts'); service=_module('service')
    data=contracts.normalise_observation_input(PinnedObservationReader(input_path,input_sha256).read(target_trade_date))
    date,identity=data['target_trade_date'],data['input_identity']; store=components.store_class(runtime_root)
    relative=f'.commits/{date}/{identity}.json'
    raw=store._io.read_bytes(relative,max_bytes=8*1024*1024)
    if sha256(raw).hexdigest()!=expected_commit_file_sha256: raise ValueError('M16_RECEIPT_RECOVERY_FILE_PIN')
    committed=store._read_commit(date,identity)
    if (not committed or committed['sha256']!=expected_commit_sha256 or json.loads(raw)!=committed):
        raise ValueError('M16_RECEIPT_RECOVERY_COMMIT_PIN')
    product=committed['product']; old_job=committed['jobs'].get(job_id); old_receipt=committed['receipts'].get(job_id)
    digest=contracts.sha256_json
    if digest(product)!=expected_product_sha256: raise ValueError('M16_RECEIPT_RECOVERY_PRODUCT_PIN')
    if (not isinstance(old_job,dict) or not isinstance(old_receipt,dict)
            or old_job.get('generation')!=generation or old_job.get('mode')!='OFFLINE_PDF_REPARSE'
            or old_job.get('schema_version')!='v4.manager_research.job.v1'
            or product.get('schema_version')!='v4.manager_research.product.v1'
            or product.get('kind')!='MANAGER_RESEARCH_PRODUCT'
            or any(key in old_receipt and old_receipt[key]!=old_job.get(key) for key in ('generation','attempt'))
            or old_job.get('status') not in {'READY','PARTIAL_WITH_ROWS','CANNOT_CONFIRM'}
            or product.get('status')!=old_job['status'] or 'status' in old_receipt
            or old_receipt.get('schema_version')!='v4.manager_research.receipt.v1'
            or old_receipt.get('mode')!='OFFLINE_PDF_REPARSE' or old_receipt.get('applied') is not True
            or old_receipt.get('parser_cache_version')!=3 or old_receipt.get('network_calls')!=0
            or old_receipt.get('product_sha256')!=expected_product_sha256
            or old_receipt.get('previous_product_sha256')!=digest(old_receipt.get('previous_product'))
            or not isinstance(old_receipt.get('previous_job'),dict)
            or not isinstance(old_receipt.get('previous_receipt'),dict)):
        raise ValueError('M16_RECEIPT_RECOVERY_NOT_KNOWN_MISSING_STATUS')
    for key in ('target_trade_date','input_identity','input_source_sha256','cutoff_at','stage_id','market','input_row_count'):
        if product.get(key)!=data.get(key) or old_job.get(key)!=data.get(key):
            raise ValueError('M16_RECEIPT_RECOVERY_INPUT_BINDING')
    if product.get('historical_system_available') is not False:
        raise ValueError('M16_HISTORICAL_BOUNDARY_REQUIRED')
    report=dict(mode='OFFLINE_RECEIPT_RECOVERY',applied=False,target_trade_date=date,input_identity=identity,
        product_sha256=expected_product_sha256,previous_commit_sha256=expected_commit_sha256,
        previous_commit_file_sha256=expected_commit_file_sha256,previous_job_id=job_id,
        previous_generation=generation,previous_receipt_sha256=digest(old_receipt),
        product_unchanged=True,network_calls=0,pdf_parse_calls=0)
    if not apply: return report
    recovery_id=f'mr-receipt-{date}-{identity[:16]}-{expected_commit_file_sha256[:12]}'
    archive=f'.receipt-recovery/{expected_commit_file_sha256}.json'
    def unchanged(latest):
        current=store._read_commit(date,identity)
        if (not current or current['sha256']!=expected_commit_sha256 or digest(latest)!=expected_product_sha256
                or sha256(store._io.read_bytes(relative,max_bytes=8*1024*1024)).hexdigest()!=expected_commit_file_sha256):
            raise ValueError('M16_RECEIPT_RECOVERY_COMMIT_CHANGED')
        if any(j.get('input_identity')==identity and j.get('job_id')!=recovery_id
               and j.get('status') in {'QUEUED','RUNNING'} for j in store.list_jobs(date)):
            raise ValueError('M16_OTHER_JOB_ACTIVE')
        return product
    now=service._now()
    with store._transaction(date,identity):
        unchanged(store.read_product(date,identity))
        try:
            if store._io.read_bytes(archive)!=raw: raise ValueError('M16_RECEIPT_RECOVERY_ARCHIVE_CONFLICT')
        except FileNotFoundError:
            store._io.write_bytes(archive,raw,require_absent=True)
        prior=store.read_job(recovery_id)
        job={key:deepcopy(old_job[key]) for key in ('schema_version','kind','target_trade_date','input_identity','input_source_sha256','stage_id','market','cutoff_at','input_row_count')}
        job.update(job_id=recovery_id,generation=uuid4().hex,attempt=int(prior.get('attempt',0))+1 if prior else 1,
            mode='OFFLINE_RECEIPT_RECOVERY',status='QUEUED',created_at=now,updated_at=now,can_retry=False,**service.FOUR_FLAGS)
        store.admit_job(job)
    try:
        job.update(status='RUNNING',started_at=now);store.write_job(job)
        job.update(status=product['status'],completed_at=service._now())
        receipt=dict(report,schema_version='v4.manager_research.receipt.v1',job_id=recovery_id,
            status=job['status'],generation=job['generation'],attempt=job['attempt'],applied=True,
            recovery_reason='MISSING_STATUS_IN_OFFLINE_PDF_REPARSE_RECEIPT',generated_at=now,
            previous_commit_archive=archive,**service.FOUR_FLAGS)
        store.commit_result(job,product,receipt,merge=unchanged)
    except Exception:
        job.update(status='FAILED',error='OFFLINE_RECEIPT_RECOVERY_COMMIT_FAILED',completed_at=service._now())
        try: store.write_job(job)
        except Exception: pass
        raise
    return {**report,'applied':True,'job_id':recovery_id,'generation':job['generation'],'attempt':job['attempt']}


def import_saved_provider_result(*, runtime_root: Path, input_path: Path, input_sha256: str,
        target_trade_date: str, expected_product_sha256: str, expected_commit_sha256: str,
        expected_commit_file_sha256: str, source_result_path: Path, source_result_sha256: str,
        apply: bool = False) -> dict:
    """Admit a pinned existing 02915 provider result, without collecting or parsing.

    Requires the exact original provider JSON file and matching existing v3 PDF
    cache. The prior commit is archived verbatim; all prior jobs remain intact.
    """
    code='HK.02915'
    if (not runtime_root.is_absolute() or not runtime_root.is_dir()
            or any(p.is_symlink() for p in (runtime_root,*runtime_root.parents))
            or any(not (runtime_root/p).is_dir() or (runtime_root/p).is_symlink()
                   for p in ('jobs','products','receipts','materials','materials/index','materials/blobs'))):
        raise ValueError('M16_INITIALIZED_RUNTIME_REQUIRED')
    for value in (expected_product_sha256,expected_commit_sha256,expected_commit_file_sha256,source_result_sha256):
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
            raise ValueError('M16_PROVIDER_IMPORT_PIN_REQUIRED')
    if any(p.is_symlink() for p in (source_result_path,*source_result_path.parents)):
        raise ValueError('M16_PROVIDER_RESULT_SYMLINK')
    raw_result=source_result_path.read_bytes()
    if len(raw_result)>8*1024*1024 or sha256(raw_result).hexdigest()!=source_result_sha256:
        raise ValueError('M16_PROVIDER_RESULT_FILE_PIN')
    result=json.loads(raw_result)
    components=load_owner(closure())['components']
    contracts,service,provider,transport,materials=(_module(n) for n in ('contracts','service','hkex_provider','material_transport','materials'))
    data=contracts.normalise_observation_input(PinnedObservationReader(input_path,input_sha256).read(target_trade_date))
    date,identity=data['target_trade_date'],data['input_identity'];digest=contracts.sha256_json
    store=components.store_class(runtime_root);relative=f'.commits/{date}/{identity}.json'
    raw_commit=store._io.read_bytes(relative,max_bytes=8*1024*1024)
    committed=store._read_commit(date,identity)
    if (sha256(raw_commit).hexdigest()!=expected_commit_file_sha256 or not committed
            or committed['sha256']!=expected_commit_sha256 or json.loads(raw_commit)!=committed):
        raise ValueError('M16_PROVIDER_IMPORT_COMMIT_PIN')
    product=committed['product']
    if digest(product)!=expected_product_sha256: raise ValueError('M16_PROVIDER_IMPORT_PRODUCT_PIN')
    for key in ('target_trade_date','input_identity','input_source_sha256','cutoff_at','stage_id','market','input_row_count'):
        if product.get(key)!=data.get(key): raise ValueError('M16_PROVIDER_IMPORT_INPUT_BINDING')
    if product.get('historical_system_available') is not False: raise ValueError('M16_HISTORICAL_BOUNDARY_REQUIRED')
    observations={r['code']:r for r in data['rows']};rows={r['code']:r for r in product['rows']}
    if len(rows)!=len(product['rows']) or set(rows)!=set(observations) or code not in rows:
        raise ValueError('M16_PROVIDER_IMPORT_ROW_BINDING')
    if rows[code].get('status')!='CANNOT_CONFIRM' or rows[code].get('facts'):
        raise ValueError('M16_PROVIDER_IMPORT_REQUIRES_UNRESOLVED_ROW')
    if (not isinstance(result,dict) or result.get('status')!='READY'
            or result.get('reason')!='OFFICIAL_PDF_FACTS_EXTRACTED' or not isinstance(result.get('facts'),list)
            or not result['facts'] or not isinstance(result.get('source'),dict)):
        raise ValueError('M16_PROVIDER_RESULT_CONTRACT')
    source=result['source']
    match=re.fullmatch(r'HKEX active stock list c=02670, i=(\d+); title directory stock code=02670; observed counter=02915',str(source.get('matching_basis','')))
    if (not match or source.get('provider_id')!=components.provider_class.provider_id
            or source.get('source_kind')!='HKEX_OFFICIAL_ISSUER_ANNOUNCEMENT'
            or source.get('issuer_code')!=code or source.get('observed_counter_code')!=code
            or source.get('issuer_document_code')!='HK.02670' or result.get('issuer')!=source.get('issuer')
            or source.get('report_selection')!='LATEST_EFFECTIVE_REPORT' or source.get('parse_status')!='STRUCTURED_FACTS'
            or not provider._safe_official_url(str(source.get('url',''))) or not str(source.get('url','')).endswith('.pdf')
            or source.get('issuer_mapping_url')!=provider.ACTIVE_STOCK_LIST_URL
            or not provider._safe_official_url(str(source.get('directory_url','')))
            or any(not re.fullmatch('[0-9a-f]{64}',str(source.get(k,''))) for k in ('sha256','directory_sha256','issuer_mapping_sha256'))):
        raise ValueError('M16_PROVIDER_SOURCE_PROVENANCE')
    expected=provider._resolve_document_issuer('02915',{'02670':dict(mapping_code='02670',stock_id=match[1],issuer=source['issuer'])},cutoff_at=data['cutoff_at'])
    if source.get('issuer_relationship')!=expected['counter_relationship']:
        raise ValueError('M16_PROVIDER_RELATIONSHIP_BINDING')
    times=[datetime.fromisoformat(source[k]) for k in ('published_at','retrieved_at','issuer_mapping_retrieved_at')]
    cutoff=datetime.fromisoformat(data['cutoff_at'])
    if any(t.tzinfo is None for t in times) or times[0]>cutoff or times[0]>times[1]:
        raise ValueError('M16_PROVIDER_SOURCE_TIME')
    material_store=components.material_store_class(runtime_root/'materials');key='hkex-official:'+source['url']
    entry=material_store.stat_source(key)
    if (not entry or entry.get('source_key')!=key or entry.get('url')!=source['url']
            or entry.get('retrieved_at')!=source['retrieved_at']):
        raise ValueError('M16_PROVIDER_MATERIAL_BINDING')
    envelope=material_store._io.read_bytes(material_store._blob_relative(entry['sha256']))
    if sha256(envelope).hexdigest()!=entry['sha256']: raise ValueError('M16_PROVIDER_ENVELOPE_HASH')
    material=materials.Material(key,source['url'],entry['sha256'],entry['retrieved_at'],entry.get('content_type'),envelope,True)
    response=transport.response_from_material(material)
    if (not 200<=response.status_code<300 or (response.final_url and not provider._safe_official_url(response.final_url))
            or sha256(response.body).hexdigest()!=source['sha256'] or len(response.body)!=source.get('bytes')
            or not response.body.startswith(b'%PDF-')):
        raise ValueError('M16_PROVIDER_PDF_BINDING')
    def missing_cache(_): raise ValueError('M16_PROVIDER_CURRENT_PARSE_CACHE_REQUIRED')
    facts,pages=material_store.parsed(material,parser_id='hkex-pdf-facts',parser_version=provider.PDF_FACTS_CACHE_VERSION,
        params={'title':str(source.get('document_title',''))},parse_fn=missing_cache)
    if (digest(facts)!=digest(result['facts']) or len(pages)!=source.get('pdf_page_count')
            or source.get('text_locators')!=[f"PDF page {p['page']}" for p in pages][:12]):
        raise ValueError('M16_PROVIDER_FACT_CACHE_BINDING')
    replacement=_financial_row(service,data,product,observations[code],rows[code],result)
    replacement['issuer']=result['issuer']
    updated=deepcopy(product);updated['rows']=[replacement if r['code']==code else r for r in updated['rows']]
    _financial_summary(service,updated,{code:replacement})
    updated['source_receipts']=[dict(code=code,status='READY',reason=result['reason'],**source) if r.get('code')==code else r for r in updated.get('source_receipts',[])]
    report=dict(mode='OFFLINE_SAVED_PROVIDER_IMPORT',applied=False,target_trade_date=date,input_identity=identity,
        previous_product_sha256=expected_product_sha256,product_sha256=digest(updated),
        previous_commit_sha256=expected_commit_sha256,previous_commit_file_sha256=expected_commit_file_sha256,
        source_result_sha256=source_result_sha256,code=code,new_fact_count=len(facts),pdf_sha256=source['sha256'],
        parser_cache_version=provider.PDF_FACTS_CACHE_VERSION,network_calls=0,pdf_parse_calls=0,
        directory_validation='PINNED_ORIGINAL_PROVIDER_RESULT_NOT_POST_REPLAY')
    if not apply:return report
    job_id=f'mr-import-{date}-{identity[:16]}-{source_result_sha256[:12]}'
    def unchanged(latest):
        current=store._read_commit(date,identity)
        if (not current or current['sha256']!=expected_commit_sha256 or digest(latest)!=expected_product_sha256
                or sha256(store._io.read_bytes(relative,max_bytes=8*1024*1024)).hexdigest()!=expected_commit_file_sha256):
            raise ValueError('M16_PROVIDER_IMPORT_COMMIT_CHANGED')
        if any(j.get('input_identity')==identity and j.get('job_id')!=job_id and j.get('status') in {'QUEUED','RUNNING'} for j in store.list_jobs(date)):
            raise ValueError('M16_OTHER_JOB_ACTIVE')
        return updated
    now=service._now();archive=f'.provider-import/{expected_commit_file_sha256}.json'
    with store._transaction(date,identity):
        unchanged(store.read_product(date,identity))
        try:
            if store._io.read_bytes(archive)!=raw_commit:raise ValueError('M16_PROVIDER_IMPORT_ARCHIVE_CONFLICT')
        except FileNotFoundError:store._io.write_bytes(archive,raw_commit,require_absent=True)
        result_archive=f'.provider-import/{source_result_sha256}.provider.json'
        try:
            if store._io.read_bytes(result_archive)!=raw_result:raise ValueError('M16_PROVIDER_RESULT_ARCHIVE_CONFLICT')
        except FileNotFoundError:store._io.write_bytes(result_archive,raw_result,require_absent=True)
        prior=store.read_job(job_id)
        job={k:data[k] for k in ('target_trade_date','input_identity','input_source_sha256','stage_id','market','cutoff_at','input_row_count')}
        job.update(schema_version=service.JOB_SCHEMA_VERSION,kind='MANAGER_RESEARCH_JOB',mode=report['mode'],
            job_id=job_id,generation=uuid4().hex,attempt=int(prior.get('attempt',0))+1 if prior else 1,
            status='QUEUED',created_at=now,updated_at=now,can_retry=False,results={},**service.FOUR_FLAGS)
        store.admit_job(job)
    try:
        job.update(status='RUNNING',started_at=now);store.write_job(job)
        job.update(status=updated['status'],completed_at=service._now(),results={code:deepcopy(result)})
        receipt=dict(report,schema_version='v4.manager_research.receipt.v1',job_id=job_id,status=job['status'],
            generation=job['generation'],attempt=job['attempt'],applied=True,generated_at=now,
            previous_commit_archive=archive,source_result_archive=result_archive,provider_result=deepcopy(result),**service.FOUR_FLAGS)
        store.commit_result(job,updated,receipt,merge=unchanged)
    except Exception:
        job.update(status='FAILED',error='OFFLINE_PROVIDER_IMPORT_COMMIT_FAILED',completed_at=service._now())
        try:store.write_job(job)
        except Exception:pass
        raise
    return {**report,'applied':True,'job_id':job_id,'generation':job['generation'],'attempt':job['attempt']}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--input-sha256',required=True);p.add_argument('--target-date',required=True)
    p.add_argument('--expected-product-sha256',required=True);p.add_argument('--code',action='append')
    p.add_argument('--source-result',type=Path);p.add_argument('--source-result-sha256')
    p.add_argument('--repair-receipt-job');p.add_argument('--repair-receipt-generation')
    p.add_argument('--expected-commit-sha256');p.add_argument('--expected-commit-file-sha256')
    p.add_argument('--apply',action='store_true',help='Explicitly admit and commit an offline recovery generation')
    args=p.parse_args(argv)
    if args.source_result_sha256 and not args.source_result:p.error("--source-result-sha256 requires --source-result")
    common=dict(runtime_root=args.runtime_root,input_path=args.input,input_sha256=args.input_sha256,
        target_trade_date=args.target_date,expected_product_sha256=args.expected_product_sha256,apply=args.apply)
    if args.source_result:
        if args.code or args.repair_receipt_job or args.repair_receipt_generation or not all((args.source_result_sha256,args.expected_commit_sha256,args.expected_commit_file_sha256)):
            p.error('provider import requires result SHA and both commit pins, without other recovery modes')
        result=import_saved_provider_result(**common,source_result_path=args.source_result,source_result_sha256=args.source_result_sha256,
            expected_commit_sha256=args.expected_commit_sha256,expected_commit_file_sha256=args.expected_commit_file_sha256)
    elif args.repair_receipt_job:
        if args.code or not all((args.repair_receipt_generation,args.expected_commit_sha256,args.expected_commit_file_sha256)):
            p.error('receipt recovery requires exact generation and both commit pins, without --code')
        result=repair_missing_receipt_status(**common,job_id=args.repair_receipt_job,generation=args.repair_receipt_generation,
            expected_commit_sha256=args.expected_commit_sha256,expected_commit_file_sha256=args.expected_commit_file_sha256)
    else:
        if not args.code or any((args.repair_receipt_generation,args.expected_commit_sha256,args.expected_commit_file_sha256)):
            p.error('PDF reparse requires --code; receipt pins require --repair-receipt-job')
        result=reparse_saved(**common,codes=args.code)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=='__main__': main()
