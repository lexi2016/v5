"""P0 saved M07 A-stage view. Every GET is a cold exact original-reader call."""
import time
from .contracts import exact_keys,trade_date
from .digests import sha256_json
from .m07_runtime import OWNER_COMMIT,FLAGS,STAGES,validate_paths,validate_reference,read_reference
ROUTE='/api/v5/source-bundle/a-stage-saved'
BINDING='m07_a_stage_binding'
MISSING=('M05_SIX_PHYSICAL_POOLS','M01_RAW_TRIO_AND_RECORDING_CLOCKS','M04_HOURLY_SOURCE_WITNESS_AND_MORNING','M07_VERIFIED_SAVED_REFERENCE')


def waiting(reason='M07_SAVED_REFERENCE_NOT_CONFIGURED'):
    return dict(schema_version='v5.m07_saved_stage.v1',module_id='M07_A_STAGE',status='WAITING',reason_codes=[reason],missing_inputs=list(MISSING),owner_commit=OWNER_COMMIT,data_kind=None,reference=None,selection=None,**FLAGS)


def validate_binding(config):
    binding=config.get(BINDING)
    if binding is None:return
    if config.get('module_id')!='source_bundle' or ROUTE not in config.get('routes',[]):raise ValueError('M07_ROUTE_CONFIG')
    exact_keys(binding,('output_root','python_executable','python_sha256','data_kind','references'))
    validate_paths(binding)
    if binding['data_kind'] not in ('SYNTHETIC','RECORDED_INPUT_REPLAY'):raise ValueError('M07_DATA_KIND')
    refs=binding['references']
    if not isinstance(refs,list) or not 1<=len(refs)<=1000:raise ValueError('M07_REFERENCE_INVENTORY')
    for reference in refs:validate_reference(reference)
    if len({(r['target_date'],r['stage_id']) for r in refs})!=len(refs):raise ValueError('M07_REFERENCE_SLOT_DUPLICATE')


def not_configured():return waiting()


def read_record(config,query):
    if query:
        if set(query)-{'date','stage'}:raise ValueError('M07_QUERY_KEYS')
        if 'date' in query:trade_date(query['date'])
        if 'stage' in query and query['stage'] not in STAGES:raise ValueError('M07_QUERY_STAGE')
    validate_binding(config);binding=config.get(BINDING)
    if binding is None:value=waiting()
    else:
        refs=binding['references']
        reference=next((r for r in refs if (('date' not in query or r['target_date']==query['date']) and ('stage' not in query or r['stage_id']==query['stage']))),None)
        if reference is None:value=waiting('M07_NO_SAVED_RESULT_FOR_SLOT')
        elif binding['data_kind']=='SYNTHETIC':value=waiting('M07_SYNTHETIC_NOT_DISPLAYABLE')
        else:
            result=read_reference(binding,reference);selection=result['selection']
            # Explicit synthetic evidence cannot be relabelled by transport config.
            if 'SYNTHETIC' in str(selection.get('source_evidence',[])).upper():value=waiting('M07_SYNTHETIC_NOT_DISPLAYABLE')
            else:value=dict(schema_version='v5.m07_saved_stage.v1',module_id='M07_A_STAGE',status='VERIFIED_SAVED',reason_codes=list(selection.get('cannot_confirm',[])),missing_inputs=[],owner_commit=OWNER_COMMIT,data_kind='RECORDED_INPUT_REPLAY',reference=reference,selection=selection,**FLAGS)
    record=dict(schema_version='v5.module_response.v1',module_id=config['module_id'],release_id=config['release_id'],path=ROUTE,query=query,payload=value,payload_sha256=sha256_json(value),source_input_sha256=sha256_json(binding) if binding else sha256_json(value),data_kind='RECORDED_INPUT_REPLAY' if value['status']=='VERIFIED_SAVED' else 'OWNER_RESULT',generated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status_code=200)
    from .module_api import _validate_record
    return _validate_record(config,record,ROUTE,query),sha256_json(record)
