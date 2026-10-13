import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import test from 'node:test';

const apiUrl = new URL('../src/api/m16SavedResearch.ts', import.meta.url);
const flags = {read_only: true, can_execute: false, research_only: true, natural_verified: false, production_allowed: false, buy_gate_updated: false, orders_sent: false};
function fixture() {
  return {
    schema_version: 'v5.m16_saved_public_research.v1', module_id: 'M16_PUBLIC_RESEARCH',
    status: 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED', mode: 'READ_ONLY_SAVED_RESULT',
    data_kind: 'SYNTHETIC', evidence_status: 'VERIFIED_PERSISTENCE_ONLY', business_status: 'PARTIAL_WITH_ROWS',
    reference: {trade_date: '20261012', input_identity: '1'.repeat(64), job_id: 'synthetic-public-research', generation: 'generation-1', attempt: 1, commit_sha256: '2'.repeat(64), commit_file_sha256: '6'.repeat(64), product_sha256: '3'.repeat(64), job_sha256: '4'.repeat(64), receipt_sha256: '5'.repeat(64)},
    product: {kind: 'MANAGER_RESEARCH_PRODUCT', status: 'PARTIAL_WITH_ROWS', rows: [{code: '000001', name: '合成公司', status: 'CANNOT_CONFIRM', facts: [{statement_cn: 'SYNTHETIC <script>alert(1)</script>', source: 'saved-fixture'}], thesis_cn: '合成财务正文', counterevidence_cn: ['NO_NATURAL_VERIFICATION'], confirmation_conditions: ['合成确认条件']}]},
    job: {status: 'PARTIAL_WITH_ROWS', job_id: 'synthetic-public-research'},
    receipt: {status: 'PARTIAL_WITH_ROWS', reason_codes: ['PERSISTED_ONLY']},
    reason_codes: ['PUBLIC_RESEARCH_REVIEW_REQUIRED'], ...flags,
  };
}
function unavailable(status = 'WAITING') {
  return {schema_version: 'v5.m16_saved_public_research.v1', module_id: 'M16_PUBLIC_RESEARCH', status, mode: 'READ_ONLY_SAVED_RESULT', reason_codes: [status === 'WAITING' ? 'M16_SAVED_REFERENCE_NOT_CONFIGURED' : 'M16_SAVED_ARTIFACT_INVALID'], ...flags};
}
async function load() {
  assert.ok(existsSync(apiUrl), 'M16 saved-only client must exist');
  return import(apiUrl.href);
}
const reply = value => async () => new Response(JSON.stringify(value));

test('reads the declared date using a credential-free GET and preserves original product/job/receipt', async () => {
  const m = await load(); let request;
  const signal = new AbortController().signal;
  const result = await m.readSavedPublicResearch('20261012', async (url, init) => {request = {url, init}; return new Response(JSON.stringify(fixture()));}, signal);
  assert.equal(request.url, '/api/v5/source-bundle/manager-public-research?trade_date=20261012');
  assert.equal(request.init.method, 'GET'); assert.equal(request.init.credentials, 'omit');
  assert.equal(request.init.cache, 'no-store'); assert.equal(request.init.signal, signal);
  assert.deepEqual(result, fixture());
});
test('missing bindings and rejected saved artifacts preserve WAITING/CANNOT_CONFIRM with reasons', async () => {
  const m = await load();
  for (const status of ['WAITING', 'CANNOT_CONFIRM']) {
    const value = unavailable(status);
    assert.deepEqual(await m.readSavedPublicResearch('', reply(value)), value);
  }
});
test('rejects malformed and impossible dates before a request', async () => {
  const m = await load(); let requests = 0;
  for (const date of ['2026-10-12', '2026101', '202610120', '20261012&job_id=other', '20260230', '20261301']) {
    await assert.rejects(m.readSavedPublicResearch(date, async () => {requests++; return new Response('{}');}), /M16_DATE/);
  }
  assert.equal(requests, 0);
});
test('requires the direct M16 payload and refuses a backend storage wrapper', async () => {
  const m = await load();
  await assert.rejects(m.readSavedPublicResearch('', reply({schema_version: 'v5.module_response.v1', payload: fixture()})), /M16_CONTRACT/);
});
test('requires every read-only flag without deriving business success from persistence', async () => {
  const m = await load();
  for (const key of Object.keys(flags)) {
    const v = fixture(); v[key] = !flags[key];
    await assert.rejects(m.readSavedPublicResearch('', reply(v)), /M16_RESEARCH_BOUNDARY/);
    delete v[key]; await assert.rejects(m.readSavedPublicResearch('', reply(v)), /M16_RESEARCH_BOUNDARY/);
  }
  const v = fixture(); v.mode = 'EXECUTE';
  await assert.rejects(m.readSavedPublicResearch('', reply(v)), /M16_RESEARCH_BOUNDARY/);
});
test('rejects malformed research identity, evidence, business status and records', async () => {
  const m = await load();
  for (const mutate of [v => v.schema_version = 'wrong', v => v.module_id = 'M11_INTRADAY_RESEARCH', v => v.status = 'READY', v => v.data_kind = 'REAL', v => v.evidence_status = 'DECLARED_ONLY', v => v.business_status = '', v => v.business_status = 'READY', v => v.product = [], v => delete v.product.status, v => v.product.rows = {}, v => v.product.rows = [null], v => v.job = null, v => v.receipt = [], v => v.reason_codes = [], v => v.reason_codes = ['  '], v => v.reason_codes = [42]]) {
    const v = fixture(); mutate(v); await assert.rejects(m.readSavedPublicResearch('', reply(v)));
  }
});
test('all persisted identity fields are required and requests cannot display a different date', async () => {
  const m = await load();
  for (const key of ['input_identity', 'commit_sha256', 'commit_file_sha256', 'product_sha256', 'job_sha256', 'receipt_sha256']) {
    const v = fixture(); v.reference[key] = 'bad'; await assert.rejects(m.readSavedPublicResearch('', reply(v)), /M16_REFERENCE/);
  }
  for (const mutate of [v => v.reference.trade_date = '20261011', v => v.reference.trade_date = '20260230', v => v.reference.job_id = '', v => v.reference.generation = ' ', v => v.reference.attempt = 0, v => v.reference.attempt = 1.5, v => v.reference.attempt = '1', v => v.requested_trade_date = '20261011']) {
    const v = fixture(); mutate(v); await assert.rejects(m.readSavedPublicResearch('20261012', reply(v)), /M16_(REFERENCE|DATE)/);
  }
});
test('unavailable states cannot carry stale business content or saved identities', async () => {
  const m = await load();
  for (const status of ['WAITING', 'CANNOT_CONFIRM']) for (const key of ['reference', 'product', 'job', 'receipt', 'display_data', 'data_kind', 'business_status', 'evidence_status']) {
    const v = unavailable(status); v[key] = fixture()[key] ?? {};
    await assert.rejects(m.readSavedPublicResearch('', reply(v)), /M16_UNAVAILABLE_HAS_CONTENT/);
  }
});
test('preserves all three data kinds and never upgrades business CANNOT_CONFIRM to success', async () => {
  const m = await load();
  for (const data_kind of ['SYNTHETIC', 'RECORDED_INPUT_REPLAY', 'OWNER_RESULT']) {
    const v = fixture(); v.data_kind = data_kind; v.business_status = v.product.status = 'CANNOT_CONFIRM';
    assert.deepEqual(await m.readSavedPublicResearch('', reply(v)), v);
  }
});
test('rejects oversized advertised responses before reading the body', async () => {
  const m = await load(); let read = false;
  await assert.rejects(m.readSavedPublicResearch('', async () => ({ok: true, status: 200, headers: new Headers({'content-length': String(4 * 1024 * 1024 + 1)}), get body() {read = true; throw new Error('must not read');}})), /M16_RESPONSE_LIMIT/);
  assert.equal(read, false);
});
test('stream limit also applies without content-length and cancels overflow', async () => {
  const m = await load(); let cancelled = false;
  const stream = new ReadableStream({pull(controller) {controller.enqueue(new Uint8Array(1024 * 1024));}, cancel() {cancelled = true;}});
  await assert.rejects(m.readSavedPublicResearch('', async () => new Response(stream)), /M16_RESPONSE_LIMIT/);
  assert.equal(cancelled, true);
});
test('HTTP errors, empty responses, invalid UTF-8 and invalid JSON never become saved content', async () => {
  const m = await load();
  for (const response of [new Response('{}', {status: 503}), new Response(null), new Response(new Uint8Array([0xff])), new Response('{bad')]) await assert.rejects(m.readSavedPublicResearch('', async () => response));
});
test('a new read clears old results immediately, aborts its request and exposes a failed read', async () => {
  const m = await load(); const calls = [], states = [];
  const session = new m.SavedPublicResearchSession(s => states.push(s), (url, init) => new Promise(resolve => calls.push({resolve, init})));
  const first = session.load('20261012'); calls[0].resolve(new Response(JSON.stringify(fixture()))); await first;
  assert.equal(states.at(-1).phase, 'LOADED');
  const second = session.load('20261013'); assert.deepEqual(states.at(-1), {phase: 'LOADING', result: null, error: ''});
  assert.equal(calls[0].init.signal.aborted, true); calls[1].resolve(new Response('{}', {status: 503})); await second;
  assert.equal(states.at(-1).phase, 'CANNOT_CONFIRM'); assert.equal(states.at(-1).result, null); assert.match(states.at(-1).error, /M16_HTTP_503/);
  session.close();
});
test('an older success cannot replace the latest date, and an older error cannot erase it', async () => {
  const m = await load(); const calls = [], states = [];
  const session = new m.SavedPublicResearchSession(s => states.push(s), (url, init) => new Promise((resolve, reject) => calls.push({resolve, reject, init})));
  const old = session.load('20261012'), middle = session.load('20261012'), current = session.load('20261013');
  calls[2].resolve(new Response(JSON.stringify({...unavailable(), requested_trade_date: '20261013'}))); await current;
  const count = states.length;
  calls[0].resolve(new Response(JSON.stringify(fixture()))); calls[1].reject(new Error('stale failure')); await Promise.all([old, middle]);
  assert.equal(states.length, count); assert.equal(states.at(-1).phase, 'WAITING'); assert.equal(states.at(-1).result.requested_trade_date, '20261013'); session.close();
});
test('close aborts the request and no late result or subsequent load can publish', async () => {
  const m = await load(); const calls = [], states = [];
  const session = new m.SavedPublicResearchSession(s => states.push(s), (url, init) => new Promise(resolve => calls.push({resolve, init})));
  const pending = session.load(); session.close(); assert.equal(calls[0].init.signal.aborted, true); const count = states.length;
  calls[0].resolve(new Response(JSON.stringify(fixture()))); await pending; await session.load();
  assert.equal(states.length, count); assert.equal(calls.length, 1);
});
test('explicit backend CANNOT_CONFIRM never appears LOADED and a retry may read saved content', async () => {
  const m = await load(); const states = [], replies = [unavailable('CANNOT_CONFIRM'), fixture()];
  const session = new m.SavedPublicResearchSession(s => states.push(s), async () => new Response(JSON.stringify(replies.shift())));
  await session.load(); assert.equal(states.at(-1).phase, 'CANNOT_CONFIRM'); assert.equal(states.at(-1).result.status, 'CANNOT_CONFIRM');
  await session.load(); assert.equal(states.at(-1).phase, 'LOADED'); session.close();
});
test('component stays lazy and read-only, escapes text and includes review and synthetic disclosure', () => {
  const path = new URL('../src/components/M16SavedResearch.vue', import.meta.url);
  assert.ok(existsSync(path), 'M16 component must exist');
  const component = readFileSync(path, 'utf8');
  assert.match(component, /id="m16-saved-research"/); assert.match(component, /@toggle="onToggle"/);
  assert.doesNotMatch(component, /v-html|onMounted|window\.open/);
  assert.match(component, /VERIFIED_PERSISTENCE_ONLY/); assert.match(component, /SYNTHETIC/);
  assert.match(component, /product\.rows/); assert.match(component, /row\.facts/);
  assert.match(component, /session\.close\(\)/);
});
test('M16 has its own loopback proxy and front-panel entry while M11/M12 stay mounted', async () => {
  const vite = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8');
  const view = readFileSync(new URL('../src/views/SavedManagerResultView.vue', import.meta.url), 'utf8');
  assert.match(vite, /proxy\['\/api\/v5\/source-bundle\/manager-public-research'\] = readonlyProxy\(sourceTarget\)/);
  assert.match(view, /aria-controls="m16-saved-research"/);
  assert.match(view, /<M16SavedResearch\s*\/>/);
  assert.match(view, /<M11SavedResearch\s*\/>/);
  assert.match(view, /<M12SavedVideo\s*\/>/);
});
