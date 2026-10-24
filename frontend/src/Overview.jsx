import React from 'react';
import WorkloadChart from './WorkloadChart.jsx';

const METRICS = [
  ['total', 'Total cases', 'neutral'], ['pending', 'Pending', 'amber'],
  ['under_process', 'Under process', 'teal'], ['disposed', 'Disposed', 'neutral'],
  ['overdue', 'Overdue', 'red'], ['due_within_7_days', 'Due within 7 days', 'amber'],
  ['escalated', 'Escalated', 'red'], ['transferred', 'Transferred', 'neutral'],
];
const ALERTS = [
  ['overlap', 'Cross-bureau overlaps', 'Institutions needing coordination', 'amber'],
  ['overdue', 'Overdue cases', 'Past expected disposal date', 'red'],
  ['due_within_7_days', 'Due within 7 days', 'Due today through the next seven days', 'amber'],
  ['pending_too_long', 'Pending over 30 days', 'Awaiting progress for more than 30 days', 'amber'],
  ['escalated', 'Escalated cases', 'Flagged for senior review', 'red'],
  ['unacknowledged', 'Unacknowledged requests', 'Follow-up date has passed', 'neutral'],
];

function formatDate(iso) {
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(iso + 'T00:00:00'));
}

function RolePanel({ view }) {
  if (view.supervisor) {
    return <section className="role-panel supervisor-panel" aria-labelledby="role-heading">
      <div><p className="eyebrow">SUPERVISOR WORKSPACE</p><h2 id="role-heading">Cross-bureau supervision</h2><p>{view.user.name} <span aria-hidden="true">·</span> Monitor the full register across bureaus.</p><span className="role-badge">Read-only role</span></div>
      <dl className="role-statistics"><div><dt>Open cases</dt><dd>{view.summary.open}</dd></div><div><dt>Institutions</dt><dd>{view.resolvedInstitutions}</dd></div><div><dt>Bureaus</dt><dd>{view.summary.bureau_wise.length}</dd></div></dl>
    </section>;
  }
  return <section className="role-panel" aria-labelledby="role-heading">
    <div><p className="eyebrow">OFFICER WORKSPACE</p><h2 id="role-heading">Your bureau at a glance</h2><p>{view.user.name} <span aria-hidden="true">·</span> {view.user.bureau} bureau</p><span className="role-badge">Bureau officer</span></div>
    <dl className="role-statistics"><div><dt>Bureau cases</dt><dd>{view.bureau?.total ?? 0}</dd></div><div><dt>Bureau open</dt><dd>{view.bureau?.open ?? 0}</dd></div><div><dt>Assigned open</dt><dd>{view.assignedOpen}</dd></div></dl>
  </section>;
}

export default function Overview({ view, onRefresh }) {
  return <div className="overview-content">
    <div className="view-toolbar"><p><span className="status-dot" aria-hidden="true" />Reference date <strong>{formatDate(view.summary.as_of)}</strong></p><button className="button button-secondary" onClick={onRefresh}>Refresh overview</button></div>
    <RolePanel view={view} />
    <section aria-labelledby="register-heading">
      <div className="section-title"><div><h2 id="register-heading">The full case register</h2><p>All bureaus <span aria-hidden="true">·</span> Current status totals</p></div><span className="quiet-label">{view.summary.unresolved_cases} unresolved {view.summary.unresolved_cases === 1 ? 'identity' : 'identities'}</span></div>
      <dl className="metric-grid">{METRICS.map(([key, label, tone]) => <div className={'metric-card tone-' + tone} key={key}><dt>{label}</dt><dd>{view.summary[key]}</dd><span className="metric-line" aria-hidden="true" /></div>)}</dl>
    </section>
    <div className="overview-columns">
      <section className="panel workload-panel" aria-labelledby="workload-heading"><div className="section-title"><div><p className="eyebrow">CASE DISTRIBUTION</p><h2 id="workload-heading">Bureau workload</h2><p>All cases, including disposed records</p></div><span className="quiet-label">All bureaus</span></div><WorkloadChart data={view.summary.bureau_wise} /></section>
      <section className="panel alerts-panel" aria-labelledby="alerts-heading"><div className="section-title"><div><p className="eyebrow">ATTENTION & FOLLOW-UP</p><h2 id="alerts-heading">Alert flags</h2><p>{view.scopeLabel}</p></div><span className="flag-symbol" aria-hidden="true">!</span></div>
        <ul className="alert-list">{ALERTS.map(([key, label, description, tone]) => <li key={key}><span className={'alert-dot tone-' + tone} aria-hidden="true" /><div><strong>{label}</strong><small>{description}</small></div><span className={'alert-count tone-' + tone}>{view.alerts[key].length}<span className="sr-only"> {label}</span></span></li>)}</ul>
      </section>
    </div>
    {view.supervisor ? <section className="panel regions-panel" aria-labelledby="regions-heading"><div className="section-title"><div><h2 id="regions-heading">Regional coverage</h2><p>All cases by reported or registered region</p></div></div><dl className="region-grid">{view.summary.region_wise.map((row) => <div key={row.region}><dt>{row.region}</dt><dd>{row.total}</dd></div>)}</dl></section> : null}
  </div>;
}
