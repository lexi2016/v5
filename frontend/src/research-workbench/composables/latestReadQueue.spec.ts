import { afterEach, expect, it, vi } from 'vitest';
import { latestReadQueue } from './latestReadQueue';
afterEach(() => vi.useRealTimers());
const flush = async () => { await Promise.resolve(); await Promise.resolve(); };
it('retries 503 finitely then succeeds without overlapping reads', async () => {
 vi.useFakeTimers(); const success=vi.fn(),failure=vi.fn();
 const read=vi.fn().mockRejectedValueOnce({status:503}).mockRejectedValueOnce({status:503}).mockResolvedValue('final');
 const q=latestReadQueue({start:vi.fn(),success,failure}); q.submit('final',read);
 await vi.runAllTimersAsync(); expect(read).toHaveBeenCalledTimes(3);expect(success).toHaveBeenCalledWith('final');expect(failure).not.toHaveBeenCalled();
});
it('permanent 503 exits after three attempts and permits explicit retry', async () => {
 vi.useFakeTimers();const failure=vi.fn(),read=vi.fn().mockRejectedValue({status:503});
 const q=latestReadQueue({start:vi.fn(),success:vi.fn(),failure});q.submit('last',read);
 await vi.runAllTimersAsync();expect(read).toHaveBeenCalledTimes(3);expect(failure).toHaveBeenCalledTimes(1);expect(vi.getTimerCount()).toBe(0);
 q.submit('last',read);await vi.runAllTimersAsync();expect(read).toHaveBeenCalledTimes(6);
});
it('deduplicates selection and cancels superseded backoff and unmounted pending work', async () => {
 vi.useFakeTimers();const success=vi.fn(),read=vi.fn().mockRejectedValue({status:503});
 const q=latestReadQueue({start:vi.fn(),success,failure:vi.fn()});q.submit('old',read);q.submit('old',read);await flush();
 const final=vi.fn().mockResolvedValue('final');q.submit('final',final);await flush();await vi.runAllTimersAsync();
 expect(read).toHaveBeenCalledTimes(1);expect(final).toHaveBeenCalledTimes(1);expect(success).toHaveBeenCalledWith('final');
 q.submit('busy',read);await flush();q.dispose();await vi.runAllTimersAsync();expect(read).toHaveBeenCalledTimes(2);expect(vi.getTimerCount()).toBe(0);
});
it('unmount ignores active results and never starts the pending selection', async () => {
 let finish!:(v:string)=>void;const success=vi.fn(),next=vi.fn();
 const q=latestReadQueue<string>({start:vi.fn(),success,failure:vi.fn()});q.submit('first',()=>new Promise(resolve=>{finish=resolve}));q.submit('last',next);q.dispose();finish('stale');await flush();expect(next).not.toHaveBeenCalled();expect(success).not.toHaveBeenCalled();
});
