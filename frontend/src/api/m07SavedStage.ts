/** M07 original saved A-stage selection only. This reader never starts selection. */
export const M07_SAVED_STAGE_ROUTE='/api/v5/source-bundle/a-stage-saved';
export const A_STAGES=['STAGE_0925','STAGE_0930_0935','STAGE_0935_0940','STAGE_0940_0945','STAGE_0945_1030','STAGE_1300_1315','STAGE_1445_1500'] as const;
export const A_STAGE_LABELS:Record<string,string>={STAGE_0925:'09:25 竞价',STAGE_0930_0935:'09:30–09:35',STAGE_0935_0940:'09:35–09:40',STAGE_0940_0945:'09:40–09:45',STAGE_0945_1030:'09:45–10:30',STAGE_1300_1315:'13:00–13:15',STAGE_1445_1500:'14:45–15:00'};
type JsonObject=Record<string,unknown>;
type Fetcher=(url:string,init?:RequestInit)=>Promise<Response>;
export interface SavedAStageQuery {date?:string;stage?:string;}
export interface SavedAStageReference {generation:string;target_date:string;stage_id:string;run_id:string;artifact_sha256:string;manifest_sha256:string;receipt_sha256:string;}
export interface SavedAStageSelection extends JsonObject {trade_date:string;stage_id:string;run_id:string;source_status:string;selection_status:string;rows:JsonObject[];cannot_confirm:string[];}
export interface SavedAStageResult {schema_version:'v5.m07_saved_stage.v1';module_id:'M07_A_STAGE';status:'WAITING'|'VERIFIED_SAVED';owner_commit:string;reason_codes:string[];missing_inputs:string[];data_kind:'RECORDED_INPUT_REPLAY'|null;reference:SavedAStageReference|null;selection:SavedAStageSelection|null;}
export interface SavedAStageState {phase:'IDLE'|'LOADING'|'WAITING'|'LOADED'|'CANNOT_CONFIRM';result:SavedAStageResult|null;error:string;}
const MAX_BYTES=4*1024*1024,OWNER='e99b5d0d8d0dfc7c2e76d68057c735b4e5dc7c31';
const FLAGS=['natural_verified','formal_eligibility_verified','production_allowed','buy_gate_updated','orders_sent'];
const TRADE_FLAGS=['production_allowed','buy_gate_updated','orders_sent'];
const STATUSES=['READY','READY_EMPTY','PARTIAL_WITH_ROWS','CANNOT_CONFIRM'];
function check(ok:unknown,reason:string):asserts ok{if(!ok)throw new Error('M07_'+reason);}
function object(value:unknown):value is JsonObject{return value!==null&&typeof value==='object'&&!Array.isArray(value);}
function strings(value:unknown):value is string[]{return Array.isArray(value)&&value.every(item=>typeof item==='string'&&item.trim().length>0);}
function token(value:unknown){return typeof value==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$/.test(value)&&!value.includes('..');}
function digest(value:unknown){return typeof value==='string'&&/^[0-9a-f]{64}$/.test(value);}
function validDate(value:unknown){if(typeof value!=='string'||!/^\d{8}$/.test(value))return false;const iso=`${value.slice(0,4)}-${value.slice(4,6)}-${value.slice(6)}`;const parsed=new Date(iso+'T00:00:00Z');return Number.isFinite(parsed.getTime())&&parsed.toISOString().slice(0,10)===iso;}
function validStage(value:unknown){return A_STAGES.includes(value as typeof A_STAGES[number]);}
function nestedBoundary(value:unknown,depth=0):void{
 check(depth<=64,'RESPONSE_DEPTH');
 if(Array.isArray(value)){value.forEach(item=>nestedBoundary(item,depth+1));return;}
 if(!object(value))return;
 for(const [key,item] of Object.entries(value)){
  if(FLAGS.includes(key))check(item===false,'NESTED_BOUNDARY');
  if(['data_kind','source_mode','evidence_mode','trigger'].includes(key))check(typeof item!=='string'||!/^SYNTHETIC(?:_|$)/i.test(item),'SYNTHETIC');
  nestedBoundary(item,depth+1);
 }
}
function validate(value:unknown,query:SavedAStageQuery):SavedAStageResult{
 check(object(value)&&FLAGS.every(key=>value[key]===false),'RESEARCH_BOUNDARY');
 check(value.schema_version==='v5.m07_saved_stage.v1'&&value.module_id==='M07_A_STAGE'&&value.owner_commit===OWNER,'CONTRACT');
 check(strings(value.reason_codes)&&strings(value.missing_inputs),'REASONS');
 nestedBoundary(value);
 if(value.status==='WAITING'){
  check(value.data_kind===null&&value.reference===null&&value.selection===null&&value.reason_codes.length>0&&value.missing_inputs.length>0,'WAITING_CONTRACT');
  return value as unknown as SavedAStageResult;
 }
 check(value.status==='VERIFIED_SAVED'&&value.data_kind==='RECORDED_INPUT_REPLAY','CLASSIFICATION');
 const r=value.reference,s=value.selection;
 check(object(r)&&digest(r.generation)&&validDate(r.target_date)&&validStage(r.stage_id)&&token(r.run_id)&&['artifact_sha256','manifest_sha256','receipt_sha256'].every(key=>digest(r[key])),'REFERENCE');
 check((!query.date||r.target_date===query.date)&&(!query.stage||r.stage_id===query.stage),'REFERENCE_MISMATCH');
 check(object(s)&&typeof s.schema_version==='string'&&['stage_center.selection.v1','stage_center.selection.v2'].includes(s.schema_version)&&s.market==='A_SHARE'&&s.trade_date===r.target_date&&s.stage_id===r.stage_id&&s.run_id===r.run_id,'SELECTION_IDENTITY');
 check(TRADE_FLAGS.every(key=>s[key]===false),'SELECTION_BOUNDARY');
 check(typeof s.source_status==='string'&&STATUSES.includes(s.source_status)&&typeof s.selection_status==='string'&&STATUSES.includes(s.selection_status)&&strings(s.cannot_confirm),'SELECTION_STATUS');
 check(Array.isArray(s.rows)&&s.rows.length<=10&&s.rows.every(object)&&s.selected_rows===s.rows.length,'SELECTION_ROWS');
 check(s.rows.every(row=>row.formal_eligible===false),'ROW_FORMAL_BOUNDARY');
 check(s.selection_status!=='READY_EMPTY'||s.rows.length===0,'SELECTION_STATUS');
 return value as unknown as SavedAStageResult;
}
export async function readSavedAStage(query:SavedAStageQuery={},fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<SavedAStageResult>{
 check(!query.date||validDate(query.date),'DATE');check(!query.stage||validStage(query.stage),'STAGE');
 const params=new URLSearchParams();if(query.date)params.set('date',query.date);if(query.stage)params.set('stage',query.stage);
 const response=await fetcher(M07_SAVED_STAGE_ROUTE+(params.size?'?'+params.toString():''),{method:'GET',cache:'no-store',credentials:'omit',signal});
 check(response.ok,'HTTP_'+response.status);const length=response.headers.get('content-length');
 check(!length||(/^\d+$/.test(length)&&Number(length)<=MAX_BYTES),'RESPONSE_LIMIT');check(response.body,'EMPTY_RESPONSE');
 const reader=response.body.getReader(),parts:Uint8Array[]=[];let size=0;
 try{while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;if(size>MAX_BYTES){await reader.cancel();throw new Error('M07_RESPONSE_LIMIT');}parts.push(item.value);}}finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
 let value:unknown;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw new Error('M07_RESPONSE_JSON');}
 return validate(value,query);
}
export class SavedAStageSession {
 private revision=0;private closed=false;private controller:AbortController|null=null;
 private emit:(state:SavedAStageState)=>void;private fetcher:Fetcher;
 constructor(emit:(state:SavedAStageState)=>void,fetcher:Fetcher=fetch){this.emit=emit;this.fetcher=fetcher;}
 async load(query:SavedAStageQuery={}){
  if(this.closed)return;const revision=++this.revision;this.controller?.abort();this.controller=new AbortController();
  this.emit({phase:'LOADING',result:null,error:''});
  try{const result=await readSavedAStage({...query},this.fetcher,this.controller.signal);if(!this.closed&&revision===this.revision)this.emit({phase:result.status==='WAITING'?'WAITING':'LOADED',result,error:''});}
  catch(error){if(!this.closed&&revision===this.revision)this.emit({phase:'CANNOT_CONFIRM',result:null,error:error instanceof Error?error.message:'M07_READ_FAILED'});}
 }
 close(){this.closed=true;this.revision++;this.controller?.abort();}
}
