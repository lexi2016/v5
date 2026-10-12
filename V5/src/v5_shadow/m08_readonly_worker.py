"""Cold-read one exact M08 observation using its unmodified private owner tree."""
import json
from pathlib import Path
import sys

def main():
 root=Path(sys.argv[1]);sys.path.insert(0,str(root/'V5/src'))
 from v5_shadow.hk_stage_observed import read_hk_stage_observed,STAGES
 from v5_shadow.hk_stage_api import _public_value
 raw=sys.stdin.buffer.read(65537)
 if len(raw)>65536:raise ValueError('M08_READ_REQUEST_LIMIT')
 request=json.loads(raw);ref=request['reference']
 value=_public_value(read_hk_stage_observed(request['recorded_root'],ref))
 value.update(schema_version='v5.hk_stage_observed_readonly.v1',module_id='M08_HK_STAGE_OBSERVED',owner_commit='0a9e49a088358954ce36093f6c068e694fde961f',status=value['artifact']['selection_status'],stage_group='HK_STAGE8_SEPARATE' if ref['stage_id']==STAGES[-1] else 'HK_SEVEN_STAGE',m10_stage_member=ref['stage_id']!=STAGES[-1],research_only=True,data_kind='OWNER_RESULT',evidence_mode='HISTORICAL',qualification='OBSERVED_ONLY',pit_verified=False,formal_admission=False,raw_input_verified=False,computation_replayed=False,market_data_authenticity_verified=False)
 text=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
 if request['recorded_root'] in text:raise ValueError('M08_PRIVATE_PATH_IN_RESPONSE')
 sys.stdout.write(text)

if __name__=='__main__':
 try:main()
 except Exception:
  sys.stdout.write('{"status":"CANNOT_CONFIRM","reason":"M08_COMMITTED_REFERENCE_REJECTED"}')
  raise SystemExit(1)
