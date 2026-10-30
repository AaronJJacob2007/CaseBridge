import React from 'react';
import WorkloadChart from './WorkloadChart.jsx';
import { formatDate } from './caseTools.js';

const METRICS = [
  ['total', 'Total cases'], ['pending', 'Pending'], ['under_process', 'Under process'],
  ['disposed', 'Disposed'], ['overdue', 'Overdue'], ['due_within_7_days', 'Due within 7 days'],
  ['escalated', 'Escalated'], ['transferred', 'Transferred'],
];
const ALERTS = [
  ['overlap', 'Overlapping institutions'], ['overdue', 'Overdue cases'],
  ['due_within_7_days', 'Due within 7 days'], ['pending_too_long', 'Pending over 30 days'],
  ['escalated', 'Escalated cases'], ['unacknowledged', 'Past-due acknowledgments'],
];
function RolePanel({ view }) {
  return <section className="role-panel" aria-labelledby="role-heading">
    <div><h2 id="role-heading">{view.supervisor ? 'Cross-bureau supervision' : 'Your bureau'}</h2><p>{view.user.name} / {view.supervisor ? 'Read-only supervisor' : view.user.bureau + ' officer'}</p></div>
    <dl className="role-statistics">{view.supervisor ? <><div><dt>Open cases</dt><dd>{view.summary.open}</dd></div><div><dt>Institutions</dt><dd>{view.resolvedInstitutions}</dd></div><div><dt>Bureaus</dt><dd>{view.summary.bureau_wise.length}</dd></div></> : <><div><dt>Bureau cases</dt><dd>{view.bureau?.total ?? 0}</dd></div><div><dt>Bureau open</dt><dd>{view.bureau?.open ?? 0}</dd></div><div><dt>Assigned open</dt><dd>{view.assignedOpen}</dd></div></>}</dl>
  </section>;
}
function Priorities({ view }) {
  const cards = [
    ['overlap', 'Overlapping institutions', '#overlaps', 'Review overlapping institutions'],
    ['unacknowledged', 'Past-due acknowledgments', '#overlaps', 'Open coordination requests'],
    ['overdue', 'Overdue cases', '#cases', 'Open case register'],
  ];
  return <section aria-labelledby="priorities-heading"><div className="section-title"><div><h2 id="priorities-heading">Needs your attention</h2><p>{view.scopeLabel}. Open a group below to review the records.</p></div></div>
    <div className="priority-grid">{cards.map(([key, label, href, action]) => <a className="priority-card" key={key} href={href} aria-label={action + ': ' + view.alerts[key].length}><span className="summary-label">{label}</span><p className="summary-number">{view.alerts[key].length}</p></a>)}</div>
  </section>;
}
function AttentionList({ view }) {
  const overlaps = view.alerts.overlap.slice(0, 3);
  const overdue = view.alerts.overdue.slice().sort((a, b) => b.days_overdue - a.days_overdue || a.case_code.localeCompare(b.case_code)).slice(0, 3);
  return <div className="attention-columns">
    <section className="panel" aria-labelledby="coordination-list-heading"><div className="section-title"><div><h2 id="coordination-list-heading">Institutions to review</h2><p>{view.scopeLabel}. Showing {overlaps.length} of {view.alerts.overlap.length}.</p></div><a href="#overlaps">View all</a></div>
      {!overlaps.length ? <p className="compact-empty">No cross-bureau overlaps in this view.</p> : <ul className="work-list">{overlaps.map(group => <li key={group.institution_id}><div><a href={'#institutions/' + group.institution_id}>{group.institution_name}</a><span className="work-list-meta">{group.aicte_id} / {group.cases.length} open cases / {[...new Set(group.cases.map(row => row.bureau))].join(', ')}</span></div></li>)}</ul>}
    </section>
    <section className="panel" aria-labelledby="overdue-list-heading"><div className="section-title"><div><h2 id="overdue-list-heading">Overdue cases</h2><p>{view.scopeLabel}. Oldest deadlines first. Showing {overdue.length} of {view.alerts.overdue.length}.</p></div></div>
      {!overdue.length ? <p className="compact-empty">No overdue cases in this view.</p> : <ul className="work-list">{overdue.map(record => <li key={record.id}><div><a href={'#cases/' + record.id}>{record.case_code}</a><strong>{record.institution_name}</strong><span className="work-list-meta">Due {formatDate(record.expected_disposal_on)} / {record.officer || 'Unassigned'}</span></div><span className="days-overdue">{record.days_overdue} days overdue</span></li>)}</ul>}
    </section>
  </div>;
}
export default function Overview({ view, onRefresh }) {
  return <div className="overview-content">
    <div className="view-toolbar"><p>Demo reference date: <strong>{formatDate(view.summary.as_of)}</strong></p><button className="button button-secondary" onClick={onRefresh}>Refresh overview</button></div>
    <RolePanel view={view} /><Priorities view={view} /><AttentionList view={view} />
    <section aria-labelledby="register-heading"><div className="section-title"><div><h2 id="register-heading">All cases</h2><p>Current totals across all bureaus</p></div><span className="quiet-label">{view.summary.unresolved_cases} unresolved {view.summary.unresolved_cases === 1 ? 'identity' : 'identities'}</span></div><dl className="metric-grid">{METRICS.map(([key, label]) => <div className="metric-card" key={key}><dt>{label}</dt><dd>{view.summary[key]}</dd></div>)}</dl></section>
    <div className="overview-columns">
      <section className="panel" aria-labelledby="workload-heading"><div className="section-title"><h2 id="workload-heading">Bureau workload</h2><span className="quiet-label">All bureaus</span></div><WorkloadChart data={view.summary.bureau_wise} /></section>
      <section className="panel" aria-labelledby="alerts-heading"><div className="section-title"><div><h2 id="alerts-heading">Follow-up flags</h2><p>{view.scopeLabel}</p></div></div><ul className="alert-list">{ALERTS.map(([key, label]) => <li key={key}><span>{label}</span><span className="alert-count">{view.alerts[key].length}</span></li>)}</ul></section>
    </div>
    {view.supervisor ? <section className="panel" aria-labelledby="regions-heading"><div className="section-title"><div><h2 id="regions-heading">Regional coverage</h2><p>All cases by reported or registered region</p></div></div><dl className="region-grid">{view.summary.region_wise.map(row => <div key={row.region}><dt>{row.region}</dt><dd>{row.total}</dd></div>)}</dl></section> : null}
  </div>;
}
