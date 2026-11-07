import test from 'node:test';import assert from 'node:assert/strict';import {validateHistorical} from './intraday-history-view.mjs';
test('unbound validator and history cannot accept fabricated snapshot',()=>assert.throws(()=>validateHistorical({latest:{}},{symbols:[]}),/NO_APPROVED_PRIVATE_BINDING/));
