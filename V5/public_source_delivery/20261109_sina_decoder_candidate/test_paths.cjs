'use strict';const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert/strict');const a=require('./adapter.cjs');const dir=fs.mkdtempSync(path.join(os.tmpdir(),'sina-parent-'));let cases=0;
try{const real=path.join(dir,'real');fs.mkdirSync(real);const raw=path.join(real,'raw');fs.writeFileSync(raw,'abcd');const alias=path.join(dir,'alias');fs.symlinkSync(real,alias,'dir');
assert.throws(()=>a.readBoundedRegular(path.join(alias,'raw'),4),/PARENT_TYPE/);cases++;
assert.equal(a.readBoundedRegular(raw,4).toString(),'abcd');cases++;
assert.throws(()=>a.readBoundedRegular(path.join(alias,'x')+'/../raw',4),/FILE_PATH/);cases++;
const read=fs.readSync;let changed=false;fs.readSync=(...args)=>{if(!changed){changed=true;fs.writeFileSync(raw,'wxyz');}return read(...args);};try{assert.throws(()=>a.readBoundedRegular(raw,4),/FILE_CHANGED/);cases++;}finally{fs.readSync=read;}
for(const limit of [0,NaN,Infinity,-1,1.5]){assert.throws(()=>a.readBoundedRegular(raw,limit),/READ_LIMIT/);cases++;}
console.log(JSON.stringify({status:'PASS',cases,new_parent_symlink_rejected:true,same_size_mutation_rejected:true,atomic_snapshot_claim:false}));
}finally{fs.rmSync(dir,{recursive:true});}
