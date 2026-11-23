const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, 'D20_RESEARCH_PREVIEW.html'), 'utf8');
const wire = html.match(/<script id="board-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = new Map();
function get(id) {
  if (!elements.has(id)) elements.set(id, {value:'', textContent:'', rows:[],
    addEventListener(){}, replaceChildren(){this.rows=[]}, append(child){this.rows.push(child)}});
  return elements.get(id);
}
const document = {getElementById:get, createElement(){return {rows:[],append(c){this.rows.push(c)}}}};
get('board-data').textContent=wire;
get('date').value='20261120';
const ctx=vm.createContext({document});
vm.runInContext(script,ctx,{timeout:1000});
for (const [day, text, count] of [
  ['20261120',/^11月20日/,200], ['20261119',/^11月19日/,200], ['20261118',/未绑定/,0],
]){
  get('date').value=day;
  vm.runInContext('update()',ctx,{timeout:1000});
  assert.match(get('topSummary').textContent,text);
  assert.equal(get('top200Rows').rows.length,count);
}
console.log('DOM_DATE_SWITCH_20_19_18_PASS');
