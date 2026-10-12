/** Exact configured M10 cold review; no producer and no latest/run selector. */
export const HK_CLOSE_REVIEW_ROUTE='/api/v5/source-bundle/hk-close-review';
export const HK_REVIEW_STAGES=['STAGE_0925','STAGE_0930_0935','STAGE_0935_0940','STAGE_0940_0945','STAGE_0945_1030','STAGE_1300_1315','STAGE_1445_1500'] as const;
const MAX_BYTES=16*1024*1024;
const FLAGS=['production_allowed','buy_gate_updated','orders_sent','natural_verified','formal_eligibility_verified'];
const METRICS=['hit_count','coverage','precision','coverage_pct','precision_pct'];
type JsonObject=Record<string,unknown>;
type Fetcher=(url:string,init?:RequestInit)=>Promise<Response>;
export type ReviewRows='close_top20'|'model_rows'|'stage_rows'|'top20_attribution';
export interface HkReview extends JsonObject {
 trade_date:string;status:string;source_status:string;cannot_confirm:string[];
 close_top20:JsonObject[];model_rows:JsonObject[];stage_rows:JsonObject[];top20_attribution:JsonObject[];
 stages:Record<string,JsonObject>;models:Record<string,JsonObject>;stage_union:JsonObject;kpi:JsonObject;
}
export interface HkCloseReviewResult {
 schema_version:'v5.hk_close_readonly.v1';status:string;review:HkReview;
 run_id:string;generation:string;native_review_sha256:string;identity:JsonObject;
 data_kind:'RECORDED_INPUT_REPLAY';natural_admission:'UNVERIFIED';cannot_confirm:string[];
}
export interface HkCloseNotConfigured {status:'NOT_CONFIGURED';module_id:'M10_HK_CLOSE_REVIEW';reason_codes:string[];}
export interface HkCloseReviewState {phase:'IDLE'|'LOADING'|'LOADED'|'NOT_CONFIGURED'|'CANNOT_CONFIRM';result:HkCloseReviewResult|null;error:string;}
function check(ok:unknown,reason:string):asserts ok {if(!ok)throw new Error('M10_'+reason);}
function object(v:unknown):v is JsonObject{return !!v&&typeof v==='object'&&!Array.isArray(v);}
function digest(v:unknown):v is string{return typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);}
function strings(v:unknown):v is string[]{return Array.isArray(v)&&v.every(x=>typeof x==='string');}
function date(v:unknown):v is string {
 if(typeof v!=='string'||!/^\d{8}$/.test(v))return false;
 const iso=`${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6)}`;const parsed=new Date(iso+'T00:00:00Z');
 return Number.isFinite(parsed.getTime())&&parsed.toISOString().slice(0,10)===iso;
}
function validate(value:unknown):HkCloseReviewResult|HkCloseNotConfigured {
 check(object(value),'CONTRACT');check(FLAGS.every(k=>value[k]===false)&&value.research_only===true,'RESEARCH_BOUNDARY');
 check(value.module_id==='M10_HK_CLOSE_REVIEW','MODULE_ID');
 if(value.status==='NOT_CONFIGURED'){
  check(strings(value.reason_codes)&&value.reason_codes.length===1&&value.reason_codes[0]==='M10_REFERENCE_NOT_CONFIGURED'
   &&!('review' in value)&&!('run_id' in value),'NOT_CONFIGURED_CONTRACT');
  return value as unknown as HkCloseNotConfigured;
 }
 check(value.schema_version==='v5.hk_close_readonly.v1'&&value.data_kind==='RECORDED_INPUT_REPLAY'
  &&value.natural_admission==='UNVERIFIED','EVIDENCE_MODE');
 check(typeof value.run_id==='string'&&/^\d{8}-[0-9a-f]{24}$/.test(value.run_id)
  &&digest(value.generation)&&digest(value.native_review_sha256),'REFERENCE_IDENTITY');
 const review=value.review,identity=value.identity;
 check(object(review)&&object(identity)&&date(review.trade_date)&&review.trade_date===identity.trade_date
  &&value.run_id.startsWith(review.trade_date+'-'),'TRADE_DATE');
 check(['input_sha256','calendar_sha256','code_sha256','config_sha256','owner_capsule_sha256'].every(k=>digest(identity[k])),'INPUT_IDENTITY');
 check(review.schema_version==='v3_5.close_review.v1'&&review.evidence_mode===value.data_kind
  &&['production_allowed','buy_gate_updated','orders_sent'].every(k=>review[k]===false),'REVIEW_BOUNDARY');
 check(strings(value.cannot_confirm)&&strings(review.cannot_confirm)&&typeof review.source_status==='string'
  &&typeof review.status==='string'&&review.status===value.status,'REVIEW_STATUS');
 check(!(value.cannot_confirm.length||review.cannot_confirm.length)||value.status==='PARTIAL','PARTIAL_REQUIRED');
 const counts=review.row_counts;check(object(counts),'ROW_COUNTS');
 for(const [key,count,maximum] of [['close_top20','close_top20',20],['model_rows','model_0_2',100],['stage_rows','stage_rows',10000]] as const){
  const rows=review[key];check(Array.isArray(rows)&&rows.length<=maximum&&counts[count]===rows.length,'ROW_COUNT');
  check(rows.every(row=>object(row)&&row.trade_date===review.trade_date&&typeof row.code==='string'&&/^HK\.\d{5}$/.test(row.code)),'ROW_IDENTITY');
 }
 check(Array.isArray(review.top20_attribution)&&Array.isArray(review.close_top20)
  &&review.top20_attribution.length===review.close_top20.length,'ATTRIBUTION_COUNT');
 check(object(review.models)&&object(review.models['0.2_prob_active'])&&object(review.stages)
  &&object(review.stage_union)&&object(review.kpi),'METRICS_CONTRACT');
 const stages=review.stages;
 check(Object.keys(stages).length===7&&HK_REVIEW_STAGES.every(id=>object(stages[id])),'STAGES');
 let stageKnown=true;
 for(const id of HK_REVIEW_STAGES){
  const metric=stages[id] as JsonObject;
  check(typeof metric.source_status==='string'&&strings(metric.cannot_confirm),'STAGE_SOURCE');
  if(!['READY','READY_EMPTY'].includes(metric.source_status)){
   stageKnown=false;check(METRICS.every(k=>metric[k]===null),'PARTIAL_METRIC');
  }
 }
 if(!stageKnown){
  const union=review.stage_union;check(METRICS.every(k=>union[k]===null)&&review.kpi.stage_union_close_top20_hits===null,'PARTIAL_UNION');
 }
 const modelKnown=review.models['0.2_prob_active'].evidence_status==='READY';
 const top=review.close_top20 as JsonObject[];
 check(review.top20_attribution.every((row:unknown,index:number)=>object(row)&&row.code===top[index]?.code&&row.trade_date===review.trade_date
  &&(stageKnown||row.stage_union_hit===null)&&(modelKnown||row.model_0_2_hit===null)
  &&((stageKnown&&modelKnown)||row.classification==='CANNOT_CONFIRM')),'ATTRIBUTION_EVIDENCE');
 // Preserve the original projected rows and scalars. Validation never normalizes them.
 return value as unknown as HkCloseReviewResult;
}
export async function readHkCloseReview(fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<HkCloseReviewResult|HkCloseNotConfigured>{
 const response=await fetcher(HK_CLOSE_REVIEW_ROUTE,{method:'GET',cache:'no-store',credentials:'omit',signal});
 check(response.ok,'HTTP_'+response.status);
 const advertised=response.headers.get('content-length');
 check(!advertised||(/^\d+$/.test(advertised)&&Number(advertised)<=MAX_BYTES),'RESPONSE_LIMIT');
 check(response.body,'EMPTY_RESPONSE');const reader=response.body.getReader(),parts:Uint8Array[]=[];let size=0;
 try{while(true){const item=await reader.read();if(item.done)break;size+=item.value.length;
  if(size>MAX_BYTES){await reader.cancel();throw new Error('M10_RESPONSE_LIMIT');}parts.push(item.value);}}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
 let value:unknown;try{value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{throw new Error('M10_RESPONSE_JSON');}
 return validate(value);
}
export class HkCloseReviewSession {
 private revision=0;private controller:AbortController|null=null;private closed=false;
 private emit:(state:HkCloseReviewState)=>void;private fetcher:Fetcher;
 constructor(emit:(state:HkCloseReviewState)=>void,fetcher:Fetcher=fetch){this.emit=emit;this.fetcher=fetcher;}
 async load(){
  if(this.closed)return;const revision=++this.revision;this.controller?.abort();this.controller=new AbortController();
  this.emit({phase:'LOADING',result:null,error:''});
  try{const result=await readHkCloseReview(this.fetcher,this.controller.signal);
   if(this.closed||revision!==this.revision)return;
   if('reason_codes' in result)this.emit({phase:'NOT_CONFIGURED',result:null,error:result.reason_codes.join(' · ')});
   else this.emit({phase:'LOADED',result,error:''});
  }catch(error){if(!this.closed&&revision===this.revision)this.emit({phase:'CANNOT_CONFIRM',result:null,error:error instanceof Error?error.message:'M10_READ_FAILED'});}
 }
 close(){this.closed=true;this.revision++;this.controller?.abort();}
}
