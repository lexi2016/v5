/** Exact saved M12 evidence. GET only; never executes daily acquisition. */
export const M12_ROUTE='/api/v5/source-bundle/video-fupan';
type Fetcher=(url:string,init?:RequestInit)=>Promise<Response>;
type TextEvidence={text:string;sha256:string;truncated:boolean;total_characters:number};
export interface VideoResult {schema_version:string;module_id:string;status:'WAITING'|'SAVED_ASR_REVIEW_REQUIRED';reason_codes:string[];data_kind?:'SYNTHETIC'|'RECORDED_INPUT_REPLAY'|'OWNER_RESULT';reference?:{trade_date:string;run_id:string;manifest_sha256:string;owner_receipt_sha256:string};video?:Record<string,unknown>;transcript?:TextEvidence;segments?:TextEvidence;}
export interface VideoState {phase:'IDLE'|'LOADING'|'LOADED'|'WAITING'|'CANNOT_CONFIRM';result:VideoResult|null;error:string;}
function check(ok:unknown,reason:string):asserts ok{if(!ok)throw new Error('M12_'+reason);}
function object(v:unknown):v is Record<string,any>{return !!v&&typeof v==='object'&&!Array.isArray(v);}
export async function readSavedVideo(date='',fetcher:Fetcher=fetch,signal?:AbortSignal):Promise<VideoResult>{
 check(!date||/^\d{8}$/.test(date),'DATE');
 const response=await fetcher(M12_ROUTE+(date?'?trade_date='+date:''),{method:'GET',cache:'no-store',credentials:'omit',signal});check(response.ok,'HTTP_'+response.status);
 const max=4*1024*1024,header=response.headers.get('content-length');check(!header||(/^\d+$/.test(header)&&Number(header)<=max),'RESPONSE_LIMIT');
 check(response.body,'EMPTY_RESPONSE');const reader=response.body.getReader(),parts:Uint8Array[]=[];let size=0;
 try{while(true){const p=await reader.read();if(p.done)break;size+=p.value.length;if(size>max){await reader.cancel();throw new Error('M12_RESPONSE_LIMIT');}parts.push(p.value);}}finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const p of parts){bytes.set(p,offset);offset+=p.length;}
 const value:unknown=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 check(object(value)&&value.schema_version==='v5.m12_saved_video.v1'&&value.module_id==='M12_VIDEO_FUPAN','CONTRACT');
 check(value.research_only===true&&['natural_verified','review_completed','production_allowed','buy_gate_updated','orders_sent'].every(k=>value[k]===false),'RESEARCH_BOUNDARY');
 check(Array.isArray(value.reason_codes)&&value.reason_codes.length&&value.reason_codes.every((x:unknown)=>typeof x==='string'),'REASONS');
 if(value.status==='WAITING'){check(!value.transcript&&!value.segments,'WAITING_HAS_CONTENT');return value as unknown as VideoResult;}
 check(value.status==='SAVED_ASR_REVIEW_REQUIRED'&&['SYNTHETIC','RECORDED_INPUT_REPLAY','OWNER_RESULT'].includes(value.data_kind),'SAVED_STATE');
 const r=value.reference;check(object(r)&&/^\d{8}$/.test(r.trade_date)&&(!date||date===r.trade_date)&&/^[A-Za-z0-9][A-Za-z0-9_.-]{0,255}$/.test(r.run_id)&&/^[a-f0-9]{64}$/.test(r.manifest_sha256)&&/^[a-f0-9]{64}$/.test(r.owner_receipt_sha256),'REFERENCE');
 check(object(value.video)&&value.video.target_trade_date===r.trade_date&&value.video.asr_status==='ASR_REVIEW_REQUIRED','VIDEO');
 for(const key of ['transcript','segments']){const t=value[key];check(object(t)&&typeof t.text==='string'&&t.text.length<=256*1024&&/^[a-f0-9]{64}$/.test(t.sha256)&&typeof t.truncated==='boolean'&&Number.isInteger(t.total_characters)&&t.total_characters>=0,'TEXT');}
 return value as unknown as VideoResult;
}
export class SavedVideoSession{
 private revision=0;private closed=false;private controller:AbortController|null=null;
 private emit:(state:VideoState)=>void;private fetcher:Fetcher;
 constructor(emit:(state:VideoState)=>void,fetcher:Fetcher=fetch){this.emit=emit;this.fetcher=fetcher;}
 async load(date=''){
  if(this.closed)return;const revision=++this.revision;this.controller?.abort();this.controller=new AbortController();this.emit({phase:'LOADING',result:null,error:''});
  try{const result=await readSavedVideo(date,this.fetcher,this.controller.signal);if(!this.closed&&revision===this.revision)this.emit({phase:result.status==='WAITING'?'WAITING':'LOADED',result,error:''});}
  catch(e){if(!this.closed&&revision===this.revision)this.emit({phase:'CANNOT_CONFIRM',result:null,error:e instanceof Error?e.message:'M12_READ_FAILED'});}
 }
 close(){this.closed=true;this.revision++;this.controller?.abort();}
}
