import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const panel = readFileSync(new URL('../src/components/HkPreselectionPool.vue', import.meta.url), 'utf8');

test('M06 source guard: reader false is explicitly scoped to this read, not the producer', () => {
 assert.match(panel, /reader model_weights_reverified=false/);
 assert.match(panel, /仅表示本次读取不重验模型权重/);
 assert.match(panel, /不否定生产者已完成的模型验证/);
 assert.match(panel, /formal_eligibility_verified=false/);
 assert.match(panel, /natural_verified=false/);
 assert.match(panel, /不代表正式准入、PIT 或自然运行验证/);
 assert.doesNotMatch(panel, /。未重新验证模型权重/);
});

test('M06 source guard: producer claims depend on the existing committed production method', () => {
 assert.match(panel, /state\.value\.result\?\.committed_reference\.producer_reference/);
 assert.match(panel, /v-if="productionMethod === 'FROZEN_MODEL_PRODUCER'"/);
 assert.match(panel, /v-else-if="productionMethod === 'EXISTING_VERIFIED_POOL'"/);
 assert.match(panel, /生产者已验证模型权重/);
 assert.match(panel, /生产者复用已验证预选池，未重新验证模型权重/);
 assert.match(panel, /无法确认生产者模型验证状态/);
 assert.doesNotMatch(panel, /\.sort\(|\.toSorted\(|method:\s*['"]POST|v-html/);
});
