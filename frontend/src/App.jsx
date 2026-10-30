import React, { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { createApi, loadDemoUsers } from './api.js';
import { parseRoute } from './caseTools.js';
import { Feedback, ResourceFeedback } from './Shared.jsx';
import { useResource } from './useResource.js';

const ReportsPage = lazy(() => import('./ReportsPage.jsx'));
const OverlapPage = lazy(() => import('./OverlapPage.jsx'));
const OverviewPage = lazy(() => import('./OverviewPage.jsx'));
const CaseRegister = lazy(() => import('./CaseRegister.jsx'));
const CaseWorkspace = lazy(() => import('./CaseWorkspace.jsx'));
const InstitutionProfile = lazy(() => import('./InstitutionProfile.jsx'));

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
    const names = { reports: 'Reports', overlaps: 'Overlap and coordination', overview: 'Overview', register: 'Case register', case: 'Case workspace', institution: 'Institution profile' };
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
    reports: ['REPORTS', 'Reports and exports', 'Review the latest case figures or download a report for your bureau meeting.'],
    overlaps: ['COORDINATION', 'Related cases across bureaus', 'Compare the records, review their connection, and agree on the next action.'],
    overview: ['OVERVIEW', 'Case overview', 'Review your bureau’s work and see which cases need a follow-up.'],
    register: ['CASES', 'Case register', 'Find case records and register a complaint for your bureau.'],
    case: ['CASES', 'Case details', 'See who is handling the case, record an update, and review earlier actions.'],
    institution: ['INSTITUTIONS', 'Institution profile', 'View the cases and bureau activity recorded against this institution’s AICTE Permanent ID.'],
    notfound: ['CASEBRIDGE', 'Page not found', 'Choose Overview or Case register to continue.'],
  };
  const [, title, description] = headings[route.kind];
  const user = identity.data;
  const pageKey = selectedId + ':' + route.key;
  let content;
  if (catalog.status === 'error') content = <Feedback title="Could not load demo users" message={catalog.error} onRetry={() => setCatalogVersion((value) => value + 1)} />;
  else if (catalog.status === 'loading') content = <Feedback title="Loading demo users" message="Preparing your workspace…" loading />;
  else if (!catalog.users.length) content = <Feedback title="No demo users available" message="The workspace will be available when demo users have been added." onRetry={() => setCatalogVersion((value) => value + 1)} />;
  else if (identity.status !== 'ready') content = <ResourceFeedback resource={identity} title="demo workspace" />;
  else if (route.kind === 'reports') content = <ReportsPage key={pageKey} api={api} />;
  else if (route.kind === 'overlaps') content = <OverlapPage key={pageKey} api={api} user={user} users={catalog.users} pair={route.pair} navigate={navigate} onBusy={setWritePending} />;
  else if (route.kind === 'overview') content = <OverviewPage key={pageKey} api={api} />;
  else if (route.kind === 'register') content = <CaseRegister key={pageKey} api={api} user={user} users={catalog.users} navigate={navigate} onBusy={setWritePending} onCreated={created} />;
  else if (route.kind === 'case') content = <CaseWorkspace key={pageKey} api={api} user={user} users={catalog.users} id={route.id} navigate={navigate} onBusy={setWritePending} />;
  else if (route.kind === 'institution') content = <InstitutionProfile key={pageKey} api={api} id={route.id} navigate={navigate} />;
  else content = <Feedback title="Choose a workspace" message="This page address is not available." />;

  return <>
    <a className="skip-link" href="#main" onClick={(event) => { event.preventDefault(); document.getElementById('main')?.focus(); }}>Skip to workspace</a>
    <header className="app-header">
    <div className="institution-header"><div className="institution-heading"><span className="institution-emblem"><img src="/aicte-logo.png" alt="AICTE emblem" width="380" height="73" /></span><div><p className="institution-name">All India Council for Technical Education</p><p className="institution-purpose">Institution-related complaint coordination</p></div></div><span className="prototype-label">SIH 2026 prototype</span></div>
    <div className="header-inner">
      <a className="brand" href="#overview" onClick={(event) => { event.preventDefault(); navigate('#overview'); }} aria-label="CaseBridge overview">CaseBridge<span className="brand-description">Bureau workspace</span></a>
      <nav className="main-nav" aria-label="Main navigation">{[['#overview', 'Overview', route.kind === 'overview'], ['#cases', 'Case register', ['register', 'case', 'institution'].includes(route.kind)], ['#overlaps', 'Overlap & coordination', route.kind === 'overlaps'], ['#reports', 'Reports', route.kind === 'reports']].map(([href, label, active]) => <a key={href} href={href} className="nav-item" aria-current={active ? 'page' : undefined} aria-disabled={writePending || undefined} onClick={(event) => { event.preventDefault(); navigate(href); }}>{label}</a>)}</nav>
      <div className="demo-login"><label htmlFor="demo-user">View as · demo officer or supervisor</label><select id="demo-user" value={selectedId} disabled={writePending || catalog.status !== 'ready' || !catalog.users.length} onChange={(event) => setSelectedId(event.target.value)}>
        {!catalog.users.length ? <option value="">{catalog.status === 'loading' ? 'Loading users…' : 'No users available'}</option> : null}
        {catalog.users.map((row) => <option key={row.id} value={row.id}>{row.name}  /  {row.bureau}  /  {row.role}</option>)}
      </select></div>
    </div></header>
    <main id="main" className="main-shell" tabIndex="-1"><div className="page-heading"><div><h1>{title}</h1><p className="page-description">{description}</p></div></div>
      {writePending ? <p role="status" className="save-progress">Please wait while we finish this action before switching users.</p> : null}
      <Suspense fallback={<Feedback title="Loading workspace" message="Preparing this view…" loading />}>{content}</Suspense>
      <footer className="app-footer"><strong>CaseBridge</strong><span>Student-built SIH prototype · Synthetic records · Not an official AICTE service</span><a href="https://www.aicte.gov.in/" target="_blank" rel="noreferrer">AICTE website</a></footer>
    </main>
  </>;
}
