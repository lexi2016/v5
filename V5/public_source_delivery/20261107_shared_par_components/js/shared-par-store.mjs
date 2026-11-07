import {loadScreen,validateScreen,countScreen,SCREEN_DATES} from './par-screen-data.mjs';
// One read-only logical store over existing admitted Par projections. No new DB,
// capture, formula execution, source admission or trade authority is introduced.
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
   const pending=Promise.resolve().then(()=>loader(input)).then(validateScreen).then(s=>{
    if(s.source_date!==input.sourceDate)throw Error('SHARED_PAR_DATE');
    return s;
   });inflight.set(key,pending);const clear=()=>{if(inflight.get(key)===pending)inflight.delete(key);};pending.then(clear,clear);
  }
  return inflight.get(key);
 }
 async function snapshot(input){const s=await read(input);return {source_date:s.source_date,observation_date:s.observation_date??null,selection_version:s.selection_version??'HISTORICAL',scope_count:s.scope_count,counts:countScreen(s),sources:s.sources,qualifications:s.qualifications};}
 return {read,snapshot};
}
