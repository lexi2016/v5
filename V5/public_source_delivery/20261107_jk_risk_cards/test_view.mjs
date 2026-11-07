import test from 'node:test';import assert from 'node:assert/strict';import {mountJKReference,mountRiskCards} from './jk-risk-view.mjs';
test('JK unbound refuses',()=>assert.throws(()=>mountJKReference({}),/NO_APPROVED_PRIVATE_BINDING/));
test('risk unbound refuses',()=>assert.throws(()=>mountRiskCards({}),/NO_APPROVED_PRIVATE_BINDING/));
