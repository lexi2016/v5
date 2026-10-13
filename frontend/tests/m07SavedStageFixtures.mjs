// Contract-only test doubles. These invented rows are not market evidence or preview data.
export const flags={natural_verified:false,formal_eligibility_verified:false,production_allowed:false,buy_gate_updated:false,orders_sent:false};
export const owner='e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31';
export function waiting(){return {schema_version:'v5.m07_saved_stage.v1',module_id:'M07_A_STAGE',owner_commit:owner,status:'WAITING',reason_codes:['M07_SAVED_REFERENCE_NOT_CONFIGURED'],missing_inputs:['M05 六个物理预选池','M01 原始 raw/manifest/receipt 与真实采集时钟','M04 hourly source witness 与原晨报三件套','M07 原始保存 reference'],data_kind:null,reference:null,selection:null,...flags};}
export function saved(status='PARTIAL_WITH_ROWS'){
 const reference={generation:'d'.repeat(64),target_date:'20261012',stage_id:'STAGE_0930_0935',run_id:'a-saved-contract-test',artifact_sha256:'a'.repeat(64),manifest_sha256:'b'.repeat(64),receipt_sha256:'c'.repeat(64)};
 const rows=['CANNOT_CONFIRM','READY_EMPTY'].includes(status)?[]:[{formal_eligible:false,rank:2,code:'000002',name:'Contract-only <script>alert(1)</script>',score:0,reason:'原缺口保留',reasons:['original reason'],cannot_confirm:['ORIGINAL_ROW_GAP']},{formal_eligible:false,rank:1,code:'000001',name:'Contract-only row',score:98.5,reason:'original reason two'}];
 return {...waiting(),status:'VERIFIED_SAVED',reason_codes:[],missing_inputs:[],data_kind:'RECORDED_INPUT_REPLAY',reference,selection:{schema_version:'stage_center.selection.v2',market:'A_SHARE',trade_date:reference.target_date,stage_id:reference.stage_id,run_id:reference.run_id,source_status:status,selection_status:status,selected_rows:rows.length,rows,cannot_confirm:status==='READY'?[]:['ORIGINAL_SOURCE_GAP'],production_allowed:false,buy_gate_updated:false,orders_sent:false}};
}
