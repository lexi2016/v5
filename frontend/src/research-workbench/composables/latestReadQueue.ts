/** One in-flight read. Superseded selections are discarded, never aborted into
 * another worker; only the newest pending selection runs after settlement.
 * HTTP 503 gets at most two delayed retries. Disposal cancels pending work and
 * timers, and ignores the active read without pretending the server stopped. */
export function latestReadQueue<T>(events: {
  start: () => void; success: (value: T) => void; failure: (error: unknown) => void;
}) {
  type Request = { key: string; read: () => Promise<T>; generation: number };
  let pending: Request | undefined;
  let running = false;
  let disposed = false;
  let generation = 0;
  let currentKey: string | undefined;
  let wake: (() => void) | undefined;
  const delays = [250, 750];
  async function pump() {
    if (running || disposed) return;
    running = true;
    try {
      while (pending && !disposed) {
        const request = pending;
        pending = undefined;
        for (let attempt = 0; ; attempt++) {
          try {
            const value = await request.read();
            if (!disposed && request.generation === generation) {
              currentKey = undefined;
              events.success(value);
            }
            break;
          } catch (error) {
            if (disposed || request.generation !== generation) break;
            if ((error as { status?: number } | null)?.status !== 503 || attempt >= delays.length) {
              currentKey = undefined;
              events.failure(error);
              break;
            }
            await new Promise<void>((resolve) => {
              const timer = setTimeout(done, delays[attempt]);
              function done() { clearTimeout(timer); wake = undefined; resolve(); }
              wake = done;
            });
            if (disposed || request.generation !== generation) break;
          }
        }
      }
    } finally { running = false; }
  }
  return {
    submit(key: string, read: () => Promise<T>) {
      if (disposed || currentKey === key) return;
      currentKey = key;
      pending = { key, read, generation: ++generation };
      events.start();
      wake?.();
      void pump();
    },
    dispose() { disposed = true; generation++; pending = undefined; wake?.(); },
  };
}
