'use strict';const assert=require('assert/strict'),fs=require('fs'),os=require('os'),path=require('path'),vm=require('vm');const a=require('./adapter.cjs');const dir=fs.mkdtempSync(path.join(os.tmpdir(),'sina-bounds-'));let cases=0;
const reject=(f,re)=>{assert.throws(f,re);cases++;};
try{
 const f=path.join(dir,'raw');fs.writeFileSync(f,'abcd');assert.equal(a.readBoundedRegular(f,4).toString(),'abcd');cases++;
 reject(()=>a.readBoundedRegular(f,3),/FILE_SIZE/);fs.symlinkSync(f,path.join(dir,'link'));reject(()=>a.readBoundedRegular(path.join(dir,'link'),4),/FILE_TYPE/);reject(()=>a.readBoundedRegular(dir,4),/FILE_TYPE/);
 const orig=fs.readSync;let calls=0;fs.readSync=(...args)=>{calls++;return orig(...args)};reject(()=>a.readBoundedRegular(f,3),/FILE_SIZE/);assert.equal(calls,0);fs.readSync=orig;
 const savedRead=fs.readSync;let grown=false;fs.readSync=(...args)=>{if(!grown){grown=true;fs.appendFileSync(f,'efgh');}return savedRead(...args);};
 try{reject(()=>a.readBoundedRegular(f,4),/FILE_SIZE/);}finally{fs.readSync=savedRead;}
 const fifo=path.join(dir,'fifo');require('child_process').execFileSync('mkfifo',[fifo]);reject(()=>a.readBoundedRegular(fifo,4),/FILE_TYPE/);
 reject(()=>a.decode(Buffer.from('x'),'000001.SZ',Buffer.alloc(a.LIMITS.decoder+1)),/DECODER_PIN/);
 reject(()=>a.writeRowsExclusive(path.join(dir,'large'),['x'.repeat(a.LIMITS.output)]),/OUTPUT_SIZE/);assert.equal(fs.existsSync(path.join(dir,'large')),false);
 const row={date:'2000-01-01T00:00:00.000Z',open:1,high:2,low:0,close:1,volume:0};assert.deepStrictEqual(a.validateRows([row]),[row]);cases++;
 for(const change of [{volume:-1},{open:-1},{close:3},{amount:Infinity},{postVol:-1},{date:'2000-02-30T00:00:00.000Z'},{open:NaN}])reject(()=>a.validateRows([{...row,...change}]),/VALUE|FIELD|DATE|OHLC/);
 reject(()=>a.validateRows([row,row]),/DATE/);reject(()=>a.validateRows(Array(a.LIMITS.rows+1).fill(row)),/ROWS/);
 // Isolated VM mechanism test only, not a bypass of the public decoder pin.
 reject(()=>new vm.Script('while(true){}').runInContext(vm.createContext({}),{timeout:20}),/timed out/);
 console.log(JSON.stringify({status:'PASS',cases,scope:'bounded reads and data/VM mechanism, not market admission'}));
}finally{fs.rmSync(dir,{recursive:true});}
