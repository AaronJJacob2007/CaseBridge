import React, { useEffect, useState } from 'react';
import { loadOverview } from './overview.js';
import Overview from './Overview.jsx';
import { Feedback } from './Shared.jsx';

export default function OverviewPage({ api }) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState({ status: 'loading', view: null, error: null });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ status: 'loading', view: null, error: null });
    loadOverview(api, { signal: controller.signal }).then((view) => {
      if (active) setState({ status: 'ready', view, error: null });
    }).catch((error) => {
      if (active && error.name !== 'AbortError') setState({ status: 'error', view: null, error });
    });
    return () => { active = false; controller.abort(); };
  }, [api, revision]);
  if (state.status === 'error') return <Feedback title="Could not load the overview" message={state.error.message} onRetry={() => setRevision((value) => value + 1)} />;
  if (state.status !== 'ready') return <Feedback title="Loading your overview" message="Fetching current case data…" loading />;
  return <Overview view={state.view} onRefresh={() => setRevision((value) => value + 1)} />;
}
