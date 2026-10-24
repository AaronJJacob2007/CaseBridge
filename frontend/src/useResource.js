import { useEffect, useRef, useState } from 'react';

export function useResource(api, path) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({ status: 'loading', client: null, path: null, data: null, error: null });
  useEffect(() => {
    if (!api || !path) return;
    const controller = new AbortController();
    let active = true;
    setState({ status: 'loading', client: api, path, data: null, error: null });
    api(path, { signal: controller.signal }).then((data) => {
      if (active) setState({ status: 'ready', client: api, path, data, error: null });
    }).catch((error) => {
      if (active && error.name !== 'AbortError') setState({ status: 'error', client: api, path, data: null, error });
    });
    return () => { active = false; controller.abort(); };
  }, [api, path, revision]);
  const current = state.client === api && state.path === path ? state : { status: 'loading', data: null, error: null };
  return {
    ...current,
    refresh: () => setRevision((value) => value + 1),
    replace: (data) => setState({ status: 'ready', client: api, path, data, error: null }),
  };
}

export function useMutation(onBusy) {
  const mounted = useRef(false);
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  async function run(operation, onSuccess, onFailure) {
    if (locked.current) return;
    locked.current = true;
    setBusy(true); setError(null); onBusy(true);
    try {
      // Do not cancel/retry writes on unmount: the server may already commit them.
      const result = await operation();
      if (mounted.current) onSuccess(result);
    } catch (failure) {
      if (mounted.current) { setError(failure); onFailure?.(failure); }
    } finally {
      locked.current = false; onBusy(false);
      if (mounted.current) setBusy(false);
    }
  }
  return { run, busy, error };
}
