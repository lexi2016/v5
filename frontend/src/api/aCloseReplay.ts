/** Exact configured historical M09 replay. No date/run selector or producer. */
export const A_CLOSE_REPLAY_ROUTE='/api/v5/source-bundle/a-close-replay';
const MAX_BYTES=16*1024*1024;
const FLAGS=['production_allowed','buy_gate_updated','orders_sent','natural_verified','formal_eligibility_verified','strict_1500_pit_verified','source_time_verified','membership_qualification_verified'];
const HASHES=['canonical_review_sha256','raw_review_sha256','source_sha256','record_sha256','generation_sha256'];
export const A_REPLAY_SECTIONS=[
 {key:'big_picture',label:'原模型市场总览'}, {key:'mainlines',label:'原模型行业主线'},
 {key:'core_stocks',label:'原核心股'}, {key:'observation_pool',label:'原观察池'},
 {key:'next_day_trigger_tree',label:'原次日情景'}, {key:'quality_gate',label:'原质量与证据门控'},
] as const;
export type JsonObject=Record<string,unknown>;
export type AReplayRows=typeof A_REPLAY_SECTIONS[number]['key'];
type Fetcher=(url:string,init?:RequestInit)=>Promise<Response>;
export interface AReplayReview extends JsonObject {
 trade_date:string;headline:string;market_regime:string;risk_tone:string;cannot_confirm:string[];
 big_picture:JsonObject[];mainlines:JsonObject[];core_stocks:JsonObject[];observation_pool:JsonObject[];
 next_day_trigger_tree:JsonObject[];quality_gate:JsonObject[];model_review:JsonObject;close_chain:JsonObject;
}
export interface AReplayPublication extends JsonObject {
 computed_at:string;historical_research:JsonObject;review_cannot_confirm:string[];record_cannot_confirm:string[];
 model_cannot_confirm:string[];close_chain_cannot_confirm:string[];
}
export interface ACloseReplayResult {
 schema_version:'v5.a_close_replay_readonly.v1';status:'PARTIAL';trade_date:string;run_id:string;generation:string;
 owner_commit:string;identity:JsonObject;review:AReplayReview;publication:AReplayPublication;
 data_kind:'RECORDED_INPUT_REPLAY';execution_kind:'HISTORICAL_REPLAY';scope:'OBSERVED_ROWS_ONLY';
}
export interface ACloseReplayNotConfigured {status:'NOT_CONFIGURED';module_id:'M09_A_CLOSE_REPLAY';reason_codes:string[];}
export interface ACloseReplayState {phase:'IDLE'|'LOADING'|'LOADED'|'NOT_CONFIGURED'|'CANNOT_CONFIRM';result:ACloseReplayResult|null;error:string;}
function check(ok:unknown,reason:string):asserts ok {if(!ok)throw new Error('M09_'+reason);}
function object(v:unknown):v is JsonObject{return !!v&&typeof v==='object'&&!Array.isArray(v);}
function digest(v:unknown):v is string{return typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);}
function strings(v:unknown):v is string[]{return Array.isArray(v)&&v.every(x=>typeof x==='string');}
function date(v:unknown):v is string {
 if(typeof v!=='string'||!/^\d{8}$/.test(v))return false;
 const iso=`${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6)}`;const d=new Date(iso+'T00:00:00Z');
 return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===iso;
}
function validate(value:unknown):ACloseReplayResult|ACloseReplayNotConfigured {
 check(object(value),'CONTRACT');check(FLAGS.every(k=>value[k]===false)&&value.research_only===true,'RESEARCH_BOUNDARY');
 check(value.module_id==='M09_A_CLOSE_REPLAY','MODULE_ID');
 if(value.status==='NOT_CONFIGURED'){
  check(strings(value.reason_codes)&&value.reason_codes.length===1&&value.reason_codes[0]==='M09_REFERENCE_NOT_CONFIGURED'
   &&!('review' in value)&&!('run_id' in value)&&!('publication' in value),'NOT_CONFIGURED_CONTRACT');
  return value as unknown as ACloseReplayNotConfigured;
 }
 check(value.schema_version==='v5.a_close_replay_readonly.v1'&&value.data_kind==='RECORDED_INPUT_REPLAY'
  &&value.execution_kind==='HISTORICAL_REPLAY'&&value.scope==='OBSERVED_ROWS_ONLY'&&value.status==='PARTIAL','HISTORICAL_CLASSIFICATION');
 check(typeof value.run_id==='string'&&/^m09-[0-9a-f]{32}-[0-9a-f]{12}$/.test(value.run_id)
  &&digest(value.generation)&&value.owner_commit==='084df7c61e57e7615633828a0d6a5d9078dc9b1c'&&date(value.trade_date),'REFERENCE_IDENTITY');
 const review=value.review,identity=value.identity,pub=value.publication;
 check(object(review)&&object(identity)&&object(pub),'REVIEW_STRUCTURE');
 check(review.trade_date===value.trade_date&&identity.trade_date===value.trade_date&&pub.trade_date===value.trade_date,'TRADE_DATE');
 check(HASHES.every(k=>digest(identity[k])&&pub[k]===identity[k])&&value.run_id===identity.model_run_id
  &&value.run_id===pub.model_run_id&&value.generation===identity.generation_sha256,'IDENTITY_LINKS');
 check(review.schema_version==='v3_5.a_share_review.v1'&&review.source_role==='V3_5_NATIVE_CLOSE_MODEL'
  &&review.source_sha256===identity.source_sha256&&['production_allowed','buy_gate_updated','orders_sent'].every(k=>review[k]===false),'REVIEW_BOUNDARY');
 check(pub.read_status==='VERIFIED'&&pub.schema_version==='v5.m09.read_evidence.v1'&&pub.business_status==='PARTIAL'
  &&pub.data_kind===value.data_kind&&pub.execution_kind===value.execution_kind&&pub.scope===value.scope
  &&pub.natural_verified===false&&pub.strict_1500_pit_verified===false&&pub.source_provenance_independently_verified===false
  &&pub.scenario_probabilities_status==='FROZEN_LEGACY_CONSTANTS_NOT_CALIBRATED','PUBLICATION_BOUNDARY');
 check(object(pub.safety)&&pub.safety.research_only===true
  &&['production_allowed','buy_gate_updated','orders_sent'].every(k=>(pub.safety as JsonObject)[k]===false),'PUBLICATION_SAFETY');
 check(typeof pub.computed_at==='string'&&Number.isFinite(Date.parse(pub.computed_at)),'COMPUTED_TIME');
 for(const key of ['review_cannot_confirm','record_cannot_confirm','model_cannot_confirm','close_chain_cannot_confirm','reason_codes'])check(strings(pub[key]),'GAP_ARRAYS');
 check(strings(review.cannot_confirm)&&['headline','market_regime','risk_tone','write_policy'].every(k=>typeof review[k]==='string'),'REVIEW_LABELS');
 for(const {key} of A_REPLAY_SECTIONS){
  const rows=review[key];check(Array.isArray(rows)&&rows.every(row=>object(row)&&row.trade_date===value.trade_date),'ROW_DATE');
 }
 const model=review.model_review,chain=review.close_chain,historical=pub.historical_research;
 check(object(model)&&model.run_id===value.run_id&&model.review_date===value.trade_date
  &&model.schema_version==='replay_model_v1'&&model.status==='INDEPENDENT_CLOSE_REVIEW_READY'
  &&model.model_promotion==='NO_MODEL_PROMOTED'&&model.semantic_model_call_count===0
  &&model.video_augmented_review_complete===false&&model.target_video_evidence_count===0,'MODEL_IDENTITY');
 check(object(chain)&&chain.trade_date===value.trade_date&&Array.isArray(chain.nodes)
  &&chain.nodes.every(n=>object(n)&&n.business_date===value.trade_date)
  &&['production_allowed','buy_gate_updated','orders_sent'].every(k=>chain[k]===false),'CHAIN_IDENTITY');
 check(object(historical)&&historical.schema_version==='v5.m09.historical_research.v1'
  &&['source_time_verified','source_available_by_requested_slot','membership_qualification_verified','strict_1500_pit_verified','natural_verified'].every(k=>historical[k]===false)
  &&historical.original_values_preserved===true,'HISTORICAL_NO_PROMOTION');
 check(Number.isInteger(historical.snapshot_row_count)&&(historical.snapshot_row_count as number)>0
  &&(historical.snapshot_row_count as number)<=20000&&object(historical.missing_text)
  &&['name','tdx_industry_code','tdx_industry_name'].every(k=>Number.isInteger((historical.missing_text as JsonObject)[k])&&((historical.missing_text as JsonObject)[k] as number)>=0)
  &&Number.isInteger(historical.nonfinite_unused_close_position)&&(historical.nonfinite_unused_close_position as number)>=0
  &&strings(historical.affected_metrics)&&object(historical.original_source)&&digest(historical.original_source.sha256),'HISTORICAL_GAPS');
 return value as unknown as ACloseReplayResult;
}
export async function readACloseReplay(fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<ACloseReplayResult|ACloseReplayNotConfigured>{
 const response=await fetcher(A_CLOSE_REPLAY_ROUTE,{method:'GET',cache:'no-store',credentials:'omit',signal});
 check(response.ok,'HTTP_'+response.status);const advertised=response.headers.get('content-length');
 check(!advertised||(/^\d+$/.test(advertised)&&Number(advertised)<=MAX_BYTES),'RESPONSE_LIMIT');
 check(response.body,'EMPTY_RESPONSE');const reader=response.body.getReader(),parts:Uint8Array[]=[];let size=0;
 try{while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;
  if(size>MAX_BYTES){await reader.cancel();throw new Error('M09_RESPONSE_LIMIT');}parts.push(item.value);}}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
 let value:unknown;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw new Error('M09_RESPONSE_JSON');}
 return validate(value);
}
export class ACloseReplaySession {
 private revision=0;private controller:AbortController|null=null;private closed=false;
 private emit:(state:ACloseReplayState)=>void;private fetcher:Fetcher;
 constructor(emit:(state:ACloseReplayState)=>void,fetcher:Fetcher=fetch){this.emit=emit;this.fetcher=fetcher;}
 async load(){
  if(this.closed)return;const revision=++this.revision;this.controller?.abort();this.controller=new AbortController();
  this.emit({phase:'LOADING',result:null,error:''});
  try{const result=await readACloseReplay(this.fetcher,this.controller.signal);
   if(this.closed||revision!==this.revision)return;
   if('reason_codes' in result)this.emit({phase:'NOT_CONFIGURED',result:null,error:result.reason_codes.join(' · ')});
   else this.emit({phase:'LOADED',result,error:''});
  }catch(error){if(!this.closed&&revision===this.revision)this.emit({phase:'CANNOT_CONFIRM',result:null,error:error instanceof Error?error.message:'M09_READ_FAILED'});}
 }
 close(){this.closed=true;this.revision++;this.controller?.abort();}
}
