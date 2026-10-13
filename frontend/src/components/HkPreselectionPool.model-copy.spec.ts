import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/vue';
import type { HkPreselectionResult, HkPreselectionState } from '../api/hkPreselectionPool';
import HkPreselectionPool from './HkPreselectionPool.vue';

// View-only synthetic state. This suite does not claim a real model run or
// replace the existing client/owner/reader contract tests.
const harness = vi.hoisted(() => ({ next: null as HkPreselectionState | null }));
vi.mock('../api/hkPreselectionPool', () => ({
 HkPreselectionSession: class {
  constructor(private emit: (state: HkPreselectionState) => void) {}
  load() { this.emit(harness.next!); }
  close() {}
 },
}));

function loaded(method?: string): HkPreselectionState {
 const result: HkPreselectionResult = {
  model_weights_reverified: false, fixture_only: true,
  artifact: { rows: [], source_run_id: 'SYNTHETIC_COPY_ONLY', source_sha256: '', source_manifest_sha256: '', source_receipt_sha256: '', status: 'STRICT_0_2_READY' },
  committed_reference: { target_date: '20261013', signal_date: '20261012', eligibility_source_date: '20261012', research_cutoff: '2026-10-13T02:17:48Z', execution_mode: 'MANUAL_RECOVERY', computation_sha256: '', artifact_sha256: '', artifact_relative: '', producer_reference: { production_method: method } },
 };
 return { phase: 'LOADED', result, error: '' };
}
afterEach(() => { cleanup(); harness.next = null; });

describe('M06 producer versus reader model-verification copy', () => {
 it('shows a frozen producer verification separately from reader no-reverification', async () => {
  harness.next = loaded('FROZEN_MODEL_PRODUCER');
  const view = render(HkPreselectionPool);
  await waitFor(() => expect(view.container.textContent).toContain('生产者已验证模型权重'));
  expect(view.container.textContent).toContain('reader model_weights_reverified=false');
  expect(view.container.textContent).toContain('仅表示本次读取不重验模型权重');
  expect(view.container.textContent).toContain('不代表正式准入、PIT 或自然运行验证');
  expect(view.container.textContent).toContain('合成测试数据，非实际源结果');
  expect(view.container.textContent).not.toContain('生产者复用已验证预选池');
 });
 it('does not promote an existing-pool producer to model-verified', async () => {
  harness.next = loaded('EXISTING_VERIFIED_POOL');
  const view = render(HkPreselectionPool);
  await waitFor(() => expect(view.container.textContent).toContain('生产者复用已验证预选池，未重新验证模型权重'));
  expect(view.container.textContent).not.toContain('生产者已验证模型权重');
 });
 it.each([undefined, 'UNKNOWN_METHOD'])('does not infer producer verification from method %s', async method => {
  harness.next = loaded(method);
  const view = render(HkPreselectionPool);
  await waitFor(() => expect(view.container.textContent).toContain('无法确认生产者模型验证状态'));
  expect(view.container.textContent).not.toContain('生产者已验证模型权重');
 });
 it('clears the previous producer claim while refreshing and when unconfigured', async () => {
  harness.next = loaded('FROZEN_MODEL_PRODUCER');
  const view = render(HkPreselectionPool);
  await waitFor(() => expect(view.container.textContent).toContain('生产者已验证模型权重'));
  harness.next = { phase: 'LOADING', result: null, error: '' };
  await fireEvent.click(view.getByRole('button', { name: '读取 M06 已提交结果' }));
  expect(view.container.textContent).not.toContain('生产者已验证模型权重');
  harness.next = { phase: 'NOT_CONFIGURED', result: null, error: 'M06_REFERENCE_NOT_CONFIGURED' };
  await fireEvent.click(view.getByRole('button', { name: '读取 M06 已提交结果' }));
  expect(view.container.textContent).toContain('NOT_CONFIGURED');
  expect(view.container.textContent).not.toContain('生产者已验证模型权重');
 });
});
