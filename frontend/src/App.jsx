import React, { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { createApi, loadDemoUsers } from './api.js';
import { parseRoute } from './caseTools.js';
import { Feedback, ResourceFeedback } from './Shared.jsx';
import { useResource } from './useResource.js';

const OverlapPage = lazy(() => import('./OverlapPage.jsx'));
const OverviewPage = lazy(() => import('./OverviewPage.jsx'));
const CaseRegister = lazy(() => import('./CaseRegister.jsx'));
const CaseWorkspace = lazy(() => import('./CaseWorkspace.jsx'));
const InstitutionProfile = lazy(() => import('./InstitutionProfile.jsx'));

function BridgeMark() {
  return <svg viewBox="0 0 32 32" aria-hidden="true" fill="none"><path d="M4 23V13m24 10V13M4 17h24M4 23c2-8 5-12 12-12s10 4 12 12M9 23v-6m7 6V11m7 12v-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>;
}

export default function App() {
  const [catalog, setCatalog] = useState({ status: 'loading', users: [], error: '' });
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [selectedId, setSelectedId] = useState('');
  const [writePending, setWritePending] = useState(false);
  const [hash, setHash] = useState(() => window.location.hash);
  const route = parseRoute(hash);
  const api = useMemo(() => selectedId ? createApi(selectedId) : null, [selectedId]);
  const identity = useResource(api, '/demo/me');

  useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  useEffect(() => {
    const names = { overlaps: 'Overlap and coordination', overview: 'Overview', register: 'Case register', case: 'Case workspace', institution: 'Institution profile' };
    document.title = 'CaseBridge | ' + (names[route.kind] || 'Page not found');
  }, [route.kind]);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setCatalog({ status: 'loading', users: [], error: '' });
    loadDemoUsers({ signal: controller.signal }).then((users) => {
      if (!active) return;
      setCatalog({ status: 'ready', users, error: '' });
      setSelectedId(users.length ? String(users[0].id) : '');
    }).catch((error) => {
      if (active && error.name !== 'AbortError') setCatalog({ status: 'error', users: [], error: error.message });
    });
    return () => { active = false; controller.abort(); };
  }, [catalogVersion]);

  function navigate(destination) { if (!writePending) window.location.hash = destination; }
  function created(record) { setWritePending(false); window.location.hash = '#cases/' + record.id; }
  const headings = {
    overlaps: ['COORDINATION', 'Overlap and coordination', 'Review cross-bureau cases and coordinate document requests.'],
    overview: ['OVERVIEW', 'Case coordination overview', 'Track workload, spot overlaps, and keep follow-ups in view.'],
    register: ['CASES', 'Case register', 'Find case records and register a complaint for your bureau.'],
    case: ['CASES', 'Case workspace', 'Review ownership, record progress, and follow the audit history.'],
    institution: ['INSTITUTIONS', 'Institution profile', 'Follow the full case history at one exact AICTE Permanent ID.'],
    notfound: ['CASEBRIDGE', 'Page not found', 'Choose Overview or Case register to continue.'],
  };
  const [eyebrow, title, description] = headings[route.kind];
  const user = identity.data;
  const pageKey = selectedId + ':' + route.key;
  let content;
  if (catalog.status === 'error') content = <Feedback title="Could not load demo users" message={catalog.error} onRetry={() => setCatalogVersion((value) => value + 1)} />;
  else if (catalog.status === 'loading') content = <Feedback title="Loading demo users" message="Preparing your workspace…" loading />;
  else if (!catalog.users.length) content = <Feedback title="No demo users available" message="The workspace will be available when demo users have been added." onRetry={() => setCatalogVersion((value) => value + 1)} />;
  else if (identity.status !== 'ready') content = <ResourceFeedback resource={identity} title="demo workspace" />;
  else if (route.kind === 'overlaps') content = <OverlapPage key={pageKey} api={api} user={user} users={catalog.users} pair={route.pair} navigate={navigate} onBusy={setWritePending} />;
  else if (route.kind === 'overview') content = <OverviewPage key={pageKey} api={api} />;
  else if (route.kind === 'register') content = <CaseRegister key={pageKey} api={api} user={user} users={catalog.users} navigate={navigate} onBusy={setWritePending} onCreated={created} />;
  else if (route.kind === 'case') content = <CaseWorkspace key={pageKey} api={api} user={user} users={catalog.users} id={route.id} navigate={navigate} onBusy={setWritePending} />;
  else if (route.kind === 'institution') content = <InstitutionProfile key={pageKey} api={api} id={route.id} navigate={navigate} />;
  else content = <Feedback title="Page not found" message="This page address is not available." />;

  return <>
    <a className="skip-link" href="#main" onClick={(event) => { event.preventDefault(); document.getElementById('main')?.focus(); }}>Skip to workspace</a>
    <header className="app-header"><div className="header-inner">
      <a className="brand" href="#overview" onClick={(event) => { event.preventDefault(); navigate('#overview'); }} aria-label="CaseBridge overview"><span className="brand-mark"><BridgeMark /></span><span>CaseBridge<small>Institution case coordination</small></span></a>
      <nav className="main-nav" aria-label="Main navigation">{[['#overview', 'Overview', route.kind === 'overview'], ['#cases', 'Case register', ['register', 'case', 'institution'].includes(route.kind)], ['#overlaps', 'Overlap & coordination', route.kind === 'overlaps']].map(([href, label, active]) => <a key={href} href={href} className="nav-item" aria-current={active ? 'page' : undefined} aria-disabled={writePending || undefined} onClick={(event) => { event.preventDefault(); navigate(href); }}>{label}</a>)}</nav>
      <div className="demo-login"><label htmlFor="demo-user">Demo login</label><select id="demo-user" value={selectedId} disabled={writePending || catalog.status !== 'ready' || !catalog.users.length} onChange={(event) => setSelectedId(event.target.value)}>
        {!catalog.users.length ? <option value="">{catalog.status === 'loading' ? 'Loading users…' : 'No users available'}</option> : null}
        {catalog.users.map((row) => <option key={row.id} value={row.id}>{row.name} · {row.bureau} · {row.role}</option>)}
      </select></div>
    </div></header>
    <main id="main" className="main-shell" tabIndex="-1"><div className="page-heading"><div><p className="eyebrow">CASEBRIDGE / {eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div><span className="demo-pill"><span aria-hidden="true" />Synthetic demo data</span></div>
      {writePending ? <p role="status" className="save-progress">Saving changes… Please wait before switching users.</p> : null}
      <Suspense fallback={<Feedback title="Loading workspace" message="Preparing this view…" loading />}>{content}</Suspense>
      <footer className="app-footer">CaseBridge <span aria-hidden="true">·</span> Synthetic demonstration records</footer>
    </main>
  </>;
}
