/** Exact M08 observations only. Registry order is preserved; never choose latest. */
export const HK_STAGE_OBSERVED_ROUTE='/api/v5/source-bundle/hk-stage-observed';
export const HK_STAGES=['STAGE_0925','STAGE_0930_0935','STAGE_0935_0940','STAGE_0940_0945','STAGE_0945_1030','STAGE_1300_1315','STAGE_1445_1500','STAGE_1545_1555'] as const;
export const HK_STAGE_LABELS:Record<string,string>={STAGE_0925:'阶段 1 · 09:25 竞价／D1 参考',STAGE_0930_0935:'阶段 2 · 09:30–09:35',STAGE_0935_0940:'阶段 3 · 09:35–09:40',STAGE_0940_0945:'阶段 4 · 09:40–09:45',STAGE_0945_1030:'阶段 5 · 09:45–10:30',STAGE_1300_1315:'阶段 6 · 13:00–13:15',STAGE_1445_1500:'阶段 7 · 14:45–15:00',STAGE_1545_1555:'独立 Stage8 · 15:45–15:55'};
export type JsonObject=Record<string,unknown>;
export interface HkObservedReference extends JsonObject {schema_version:'v5.hk_stage_observed_reference.v1';target_date:string;stage_id:string;market:'HK_CONNECT';run_id:string;import_sha256:string;import_receipt_sha256:string;}
export interface HkObservedResult extends JsonObject {schema_version:'v5.hk_stage_observed_readonly.v1';status:string;reference:HkObservedReference;artifact:JsonObject&{rows:JsonObject[]};provenance:JsonObject;stage_group:string;m10_stage_member:boolean;}
export interface HkObservedCatalog extends JsonObject {schema_version:'v5.hk_stage_observed_catalog.v1';references:HkObservedReference[];}
export interface HkObservedMissing extends JsonObject {status:'NOT_CONFIGURED';reason_codes:string[];}
export interface HkObservedState {phase:'IDLE'|'LOADING'|'LOADED'|'NOT_CONFIGURED'|'CANNOT_CONFIRM';references:HkObservedReference[];selected:HkObservedReference|null;result:HkObservedResult|null;error:string;}
type Fetcher=(url:string,init?:RequestInit)=>Promise<Response>;
const MAX_BYTES=16*1024*1024,OWNER='0a9e49a088358954ce36093f6c068e694fde961f';
const FALSE_FLAGS=['production_allowed','buy_gate_updated','orders_sent','natural_verified','pit_verified','formal_admission','raw_input_verified','computation_replayed','market_data_authenticity_verified'];
const PROOF_FLAGS=FALSE_FLAGS.slice(3);
function check(ok:unknown,reason:string):asserts ok{if(!ok)throw new Error('M08_'+reason);}
function object(v:unknown):v is JsonObject{return !!v&&typeof v==='object'&&!Array.isArray(v);}
function digest(v:unknown){return typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);}
function strings(v:unknown):v is string[]{return Array.isArray(v)&&v.every(x=>typeof x==='string');}
function date(v:unknown){if(typeof v!=='string'||!/^\d{8}$/.test(v))return false;const s=`${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6)}`,d=new Date(s+'T00:00:00Z');return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===s;}
function reference(v:unknown):asserts v is HkObservedReference {
 check(object(v)&&Object.keys(v).length===7&&v.schema_version==='v5.hk_stage_observed_reference.v1'&&v.market==='HK_CONNECT'&&HK_STAGES.includes(v.stage_id as typeof HK_STAGES[number])&&date(v.target_date)&&digest(v.import_sha256)&&digest(v.import_receipt_sha256)&&typeof v.run_id==='string'&&/^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,254}[A-Za-z0-9])?$/.test(v.run_id),'REFERENCE');
}
function equalRef(a:HkObservedReference,b:HkObservedReference){return Object.keys(a).every(k=>a[k]===b[k])&&Object.keys(b).length===7;}
function classification(v:JsonObject){return v.data_kind==='OWNER_RESULT'&&v.evidence_mode==='HISTORICAL'&&v.qualification==='OBSERVED_ONLY';}
function validate(value:unknown,expected:HkObservedReference|null):HkObservedResult|HkObservedCatalog|HkObservedMissing {
 check(object(value)&&value.module_id==='M08_HK_STAGE_OBSERVED'&&value.research_only===true&&FALSE_FLAGS.every(k=>value[k]===false),'BOUNDARY');
 if(value.status==='NOT_CONFIGURED'){
  check(!expected&&strings(value.reason_codes)&&value.reason_codes.length===1&&value.reason_codes[0]==='M08_REFERENCES_NOT_CONFIGURED'&&!('artifact'in value)&&!('references'in value),'NOT_CONFIGURED');return value as unknown as HkObservedMissing;
 }
 check(value.owner_commit===OWNER&&classification(value),'CLASSIFICATION');
 if(!expected){
  check(value.schema_version==='v5.hk_stage_observed_catalog.v1'&&value.status==='CONFIGURED_REFERENCES'&&value.references_verified===false&&Array.isArray(value.references)&&value.references.length===10&&!('artifact'in value),'CATALOG');
  const refs=value.references;refs.forEach(reference);check(new Set(refs.map(r=>r.import_sha256)).size===10&&new Set(refs.map(r=>`${r.target_date}/${r.stage_id}/${r.run_id}`)).size===10&&new Set(refs.map(r=>r.stage_id)).size===8,'INVENTORY');return value as unknown as HkObservedCatalog;
 }
 reference(value.reference);check(equalRef(value.reference,expected),'REFERENCE_MISMATCH');const a=value.artifact,p=value.provenance;
 check(value.schema_version==='v5.hk_stage_observed_readonly.v1'&&value.read_status==='VERIFIED'&&object(a)&&object(p),'READ_CONTRACT');
 check(a.trade_date===expected.target_date&&a.stage_id===expected.stage_id&&a.run_id===expected.run_id&&a.market==='HK_CONNECT'&&a.selection_status===value.status&&['READY','READY_EMPTY','PARTIAL_WITH_ROWS','CANNOT_CONFIRM'].includes(String(value.status))&&['READY','READY_EMPTY','PARTIAL_WITH_ROWS','CANNOT_CONFIRM'].includes(String(a.source_status)),'ORIGINAL_IDENTITY');
 check(Array.isArray(a.rows)&&a.rows.length<=10&&a.rows.every(object)&&a.selected_rows===a.rows.length&&FALSE_FLAGS.slice(0,3).every(k=>a[k]===false),'ROWS_BOUNDARY');
 check(classification(p)&&PROOF_FLAGS.every(k=>p[k]===false)&&p.captured_at===null&&typeof p.imported_at==='string'&&Number.isFinite(Date.parse(p.imported_at)),'PROVENANCE');
 const original=p.original_reference;check(object(original)&&original.target_date===expected.target_date&&original.stage_id===expected.stage_id&&original.market===expected.market&&original.run_id===expected.run_id&&['artifact_sha256','manifest_sha256','receipt_sha256'].every(k=>digest(original[k]))&&digest(p.source_closure_sha256),'ORIGINAL_HASHES');
 check(value.stage_group===(expected.stage_id===HK_STAGES[7]?'HK_STAGE8_SEPARATE':'HK_SEVEN_STAGE')&&value.m10_stage_member===(expected.stage_id!==HK_STAGES[7]),'STAGE8_BOUNDARY');
 return value as unknown as HkObservedResult;
}
export async function readHkStageObserved(expected:HkObservedReference|null,fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<HkObservedResult|HkObservedCatalog|HkObservedMissing>{
 let url=HK_STAGE_OBSERVED_ROUTE;if(expected){reference(expected);url+='?'+new URLSearchParams({date:expected.target_date,stage:expected.stage_id,run_id:expected.run_id,import_sha256:expected.import_sha256});}
 const r=await fetcher(url,{method:'GET',cache:'no-store',credentials:'omit',signal});check(r.ok,'HTTP_'+r.status);const length=r.headers.get('content-length');check(!length||(/^\d+$/.test(length)&&Number(length)<=MAX_BYTES),'RESPONSE_LIMIT');check(r.body,'EMPTY_RESPONSE');const reader=r.body.getReader(),parts:Uint8Array[]=[];let size=0;
 try{while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;if(size>MAX_BYTES){await reader.cancel();throw new Error('M08_RESPONSE_LIMIT');}parts.push(item.value);}}finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}let value:unknown;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw new Error('M08_RESPONSE_JSON');}return validate(value,expected);
}
export class HkStageObservedSession {
 private revision=0;private controller:AbortController|null=null;private closed=false;private refs:HkObservedReference[]=[];
 private emit:(state:HkObservedState)=>void;private fetcher:Fetcher;
 constructor(emit:(state:HkObservedState)=>void,fetcher:Fetcher=fetch){this.emit=emit;this.fetcher=fetcher;}
 private begin(selected:HkObservedReference|null){const revision=++this.revision;this.controller?.abort();this.controller=new AbortController();this.emit({phase:'LOADING',references:this.refs,selected,result:null,error:''});return revision;}
 private fail(error:unknown,revision:number,selected:HkObservedReference|null){if(!this.closed&&revision===this.revision)this.emit({phase:'CANNOT_CONFIRM',references:this.refs,selected,result:null,error:error instanceof Error?error.message:'M08_READ_FAILED'});}
 async load(){
  if(this.closed)return;this.refs=[];const revision=this.begin(null);
  try{const value=await readHkStageObserved(null,this.fetcher,this.controller!.signal);if(this.closed||revision!==this.revision)return;
   if(value.status==='NOT_CONFIGURED'){this.emit({phase:'NOT_CONFIGURED',references:[],selected:null,result:null,error:(value as HkObservedMissing).reason_codes.join(' · ')});return;}
   this.refs=(value as HkObservedCatalog).references;await this.select(this.refs[0]);
  }catch(error){this.fail(error,revision,null);}
 }
 async select(ref:HkObservedReference){
  if(this.closed)return;const revision=this.begin(ref);
  try{check(this.refs.some(r=>equalRef(r,ref)),'UNKNOWN_REFERENCE');const value=await readHkStageObserved(ref,this.fetcher,this.controller!.signal);if(this.closed||revision!==this.revision)return;this.emit({phase:'LOADED',references:this.refs,selected:ref,result:value as HkObservedResult,error:''});}catch(error){this.fail(error,revision,ref);}
 }
 close(){this.closed=true;this.revision++;this.controller?.abort();this.refs=[];}
}
