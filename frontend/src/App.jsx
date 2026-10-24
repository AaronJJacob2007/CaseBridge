import React, { useEffect, useState } from 'react';
import { createApi, loadDemoUsers } from './api.js';
import { loadOverview } from './overview.js';
import Overview from './Overview.jsx';

function BridgeMark() {
  return <svg viewBox="0 0 32 32" aria-hidden="true" fill="none"><path d="M4 23V13m24 10V13M4 17h24M4 23c2-8 5-12 12-12s10 4 12 12M9 23v-6m7 6V11m7 12v-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>;
}

export function Feedback({ title, message, onRetry, loading = false }) {
  return <section className="feedback panel" aria-live="polite" role={loading ? 'status' : 'alert'}>
    <span className={loading ? 'feedback-dot loading' : 'feedback-dot'} aria-hidden="true" />
    <h2>{title}</h2>
    <p>{message}</p>
    {onRetry ? <button className="button" onClick={onRetry}>Try again</button> : null}
  </section>;
}

export default function App() {
  const [catalog, setCatalog] = useState({ status: 'loading', users: [], error: '' });
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [selectedId, setSelectedId] = useState('');
  const [reloadVersion, setReloadVersion] = useState(0);
  const [snapshot, setSnapshot] = useState({ status: 'loading', userId: '', view: null, error: '' });

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setCatalog({ status: 'loading', users: [], error: '' });
    async function discover() {
      try {
        const users = await loadDemoUsers({ signal: controller.signal });
        if (!active) return;
        setCatalog({ status: 'ready', users, error: '' });
        setSelectedId(users.length ? String(users[0].id) : '');
      } catch (error) {
        if (!active || error.name === 'AbortError') return;
        setCatalog({ status: 'error', users: [], error: error.message });
      }
    }
    discover();
    return () => { active = false; controller.abort(); };
  }, [catalogVersion]);

  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    let active = true;
    setSnapshot({ status: 'loading', userId: selectedId, view: null, error: '' });
    async function refresh() {
      try {
        const view = await loadOverview(createApi(selectedId), { signal: controller.signal });
        if (active) setSnapshot({ status: 'ready', userId: selectedId, view, error: '' });
      } catch (error) {
        if (!active || error.name === 'AbortError') return;
        setSnapshot({ status: 'error', userId: selectedId, view: null, error: error.message });
      }
    }
    refresh();
    return () => { active = false; controller.abort(); };
  }, [selectedId, reloadVersion]);

  // Never render the previous user's panel during a switch or a slow request.
  const current = snapshot.userId === selectedId ? snapshot : { status: 'loading' };
  const selectedUser = catalog.users.find((user) => String(user.id) === selectedId);
  const activeUser = current.view?.user ?? selectedUser;

  return <>
    <a className="skip-link" href="#main">Skip to overview</a>
    <header className="app-header">
      <div className="header-inner">
        <a className="brand" href="#main" aria-label="CaseBridge overview">
          <span className="brand-mark"><BridgeMark /></span>
          <span>CaseBridge<small>Institution case coordination</small></span>
        </a>
        <span className="nav-item" aria-current="page">Overview</span>
        <div className="demo-login">
          <label htmlFor="demo-user">Demo login</label>
          <select id="demo-user" value={selectedId} disabled={catalog.status !== 'ready' || !catalog.users.length}
            onChange={(event) => setSelectedId(event.target.value)}>
            {!catalog.users.length ? <option value="">{catalog.status === 'loading' ? 'Loading users…' : 'No users available'}</option> : null}
            {catalog.users.map((user) => <option key={user.id} value={user.id}>{user.name} · {user.bureau} · {user.role}</option>)}
          </select>
        </div>
      </div>
    </header>
    <main id="main" className="main-shell" tabIndex="-1">
      <div className="page-heading">
        <div><p className="eyebrow">CASEBRIDGE / OVERVIEW</p><h1>Case coordination overview</h1><p className="page-description">Track workload, spot overlaps, and keep follow-ups in view.</p></div>
        <span className="demo-pill"><span aria-hidden="true" />Synthetic demo data</span>
      </div>
      {catalog.status === 'error' ? <Feedback title="Could not load demo users" message={catalog.error} onRetry={() => setCatalogVersion((value) => value + 1)} />
        : catalog.status === 'loading' ? <Feedback title="Loading demo users" message="Preparing your workspace…" loading />
          : !catalog.users.length ? <Feedback title="No demo users available" message="The overview will be available when demo users have been added." onRetry={() => setCatalogVersion((value) => value + 1)} />
            : current.status === 'error' ? <Feedback title="Could not load the overview" message={current.error} onRetry={() => setReloadVersion((value) => value + 1)} />
              : current.status !== 'ready' ? <Feedback title="Loading your overview" message={activeUser ? 'Preparing the view for ' + activeUser.name + '…' : 'Fetching current case data…'} loading />
                : <Overview view={current.view} onRefresh={() => setReloadVersion((value) => value + 1)} />}
      <footer className="app-footer">CaseBridge <span aria-hidden="true">·</span> Synthetic demonstration records</footer>
    </main>
  </>;
}
