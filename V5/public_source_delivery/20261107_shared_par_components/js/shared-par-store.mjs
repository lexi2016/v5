import {loadScreen,validateScreen,countScreen,SCREEN_DATES} from './par-screen-data.mjs';
// One read-only logical store over existing admitted Par projections. No new DB,
// capture, formula execution, source admission or trade authority is introduced.
const LEGACY_SELECTIONS=Object.freeze({
 '20261105':Object.freeze({sha256:'d85a99a72d77412e3baeea6f27fa408495e791e2cbf12653a354ffac85f54d2d',bytes:15983668}),
 '20261106':Object.freeze({sha256:'77a9c0e5518376b42e51742e84f2969b91a6fc86c240d025406e7e228c7aeaf4',bytes:24011343})
});
function verifyIdentity(s,input){
 const merged=input.sourceDate==='20261106'&&input.selectionVersion==='merge407';
 const legacy=LEGACY_SELECTIONS[input.sourceDate];
 const valid=merged?s.selection_version==='MAIN_PLUS_SINA69_407'&&s.sources.selection.sha256==='2ddb37d1126eb2a68bd4179a65532b6f063212decb2dad2c4af3666bc4edb64f'&&s.sources.selection.bytes===24541169:
  !Object.hasOwn(s,'selection_version')&&legacy&&s.sources.selection.sha256===legacy.sha256&&s.sources.selection.bytes===legacy.bytes;
 if(!valid){const error=Error('SHARED_PAR_IDENTITY');error.status='UNKNOWN';throw error;}
 return s;
}
export function createSharedParStore({loader=loadScreen}={}){
 const inflight=new Map();
 function keyOf({sourceDate,selectionVersion='merge407'}){
  if(!SCREEN_DATES.includes(sourceDate)||!['merge407','main406'].includes(selectionVersion))throw Error('SHARED_PAR_VERSION');
  return `${sourceDate}:${selectionVersion}`;
 }
 async function read(input){
  input={...input,selectionVersion:input.selectionVersion??'merge407'};
  const key=keyOf(input);
  if(!inflight.has(key)){
   const pending=Promise.resolve().then(()=>loader({...input})).then(validateScreen).then(s=>{
    if(s.source_date!==input.sourceDate)throw Error('SHARED_PAR_DATE');
    return verifyIdentity(s,input);
   });inflight.set(key,pending);const clear=()=>{if(inflight.get(key)===pending)inflight.delete(key);};pending.then(clear,clear);
  }
  return inflight.get(key);
 }
 async function snapshot(input){const s=await read(input);return {source_date:s.source_date,observation_date:s.observation_date??null,selection_version:s.selection_version??'HISTORICAL',scope_count:s.scope_count,counts:countScreen(s),sources:s.sources,qualifications:s.qualifications};}
 return {read,snapshot};
}
