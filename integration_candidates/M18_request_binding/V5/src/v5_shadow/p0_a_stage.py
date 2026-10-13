"""Actual explicit M07 replay entry. Not a scheduler and never called by GET."""
import json
import sys
from .contracts import exact_keys
from .m07_runtime import FLAGS,invoke,validate_paths
from .m07_readonly import waiting


def run_explicit(registration,request,*,allow_execution=False):
    if allow_execution is not True:return waiting('M07_EXPLICIT_EXECUTION_REQUIRED')
    if registration is None:return waiting('M07_EXECUTION_BINDING_NOT_CONFIGURED')
    exact_keys(registration,('enabled','output_root','python_executable','python_sha256'))
    if registration['enabled'] is not True:return waiting('M07_EXECUTION_DISABLED')
    validate_paths(registration)
    if not isinstance(request,dict):return waiting('M07_ORIGINAL_INPUT_REQUEST_REQUIRED')
    if request.get('data_kind')!='RECORDED_INPUT_REPLAY':return waiting('M07_REAL_RECORDED_INPUT_REQUIRED')
    if request.get('natural') is not False or request.get('trigger') not in ('RECORDED_INPUT_REPLAY','MANUAL_RECOVERY'):return waiting('M07_NATURAL_EXECUTION_NOT_BOUND')
    if set(request.get('inputs',{}))!={'pool','live','research','morning'} or not request.get('recording') or not request.get('pool_source_dates'):return waiting('M07_ORIGINAL_INPUT_REQUEST_REQUIRED')
    # The unchanged owner performs all original pool/raw/research admission,
    # checks source bytes and clocks, publishes, cold-reads and claims its ledger.
    result=invoke(registration,'run',dict(request=request,execution_authorized=True))
    if not isinstance(result,dict) or any(result.get(k) is not v for k,v in FLAGS.items()):raise ValueError('M07_OWNER_FLAGS')
    return result


def main():
    from .digests import MAX_JSON_BYTES,canonical_bytes
    raw=sys.stdin.buffer.read(MAX_JSON_BYTES+1)
    if len(raw)>MAX_JSON_BYTES:raise ValueError('M07_REQUEST_LIMIT')
    value=json.loads(raw);exact_keys(value,('registration','request','allow_execution'))
    print(canonical_bytes(run_explicit(value['registration'],value['request'],allow_execution=value['allow_execution'])).decode())


if __name__=='__main__':main()
