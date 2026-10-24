import React from 'react';
import { CasesTable, HistoryTimeline, ResourceFeedback, StatusBadge } from './Shared.jsx';
import { useResource } from './useResource.js';

export default function InstitutionProfile({ api, id, navigate }) {
  const resource = useResource(api, '/institutions/' + id);
  if (resource.status !== 'ready') return <ResourceFeedback resource={resource} title="institution profile" />;
  const profile = resource.data;
  return <div className="case-page">
    <div className="section-title"><div><p className="eyebrow">INSTITUTION PROFILE</p><h2>{profile.name}</h2><p>{profile.aicte_id}</p></div><button className="button button-secondary" onClick={resource.refresh}>Refresh profile</button></div>
    <section className="panel" aria-label="Institution details"><dl className="detail-grid">
      <div><dt>AICTE Permanent ID</dt><dd>{profile.aicte_id}</dd></div><div><dt>Region</dt><dd>{profile.region || 'Not recorded'}</dd></div>
      <div className="detail-wide"><dt>Address</dt><dd>{profile.address || 'Not recorded'}</dd></div>
      <div><dt>Bureaus involved</dt><dd>{profile.bureaus_involved.length ? profile.bureaus_involved.join(', ') : 'None recorded'}</dd></div><div><dt>Cases</dt><dd>{profile.cases.length}</dd></div>
    </dl></section>
    <section className="panel"><div className="section-title"><div><h2>Institution case register</h2><p>Includes open and disposed cases at this exact AICTE ID.</p></div></div><CasesTable cases={profile.cases} navigate={navigate} /></section>
    <section className="panel" aria-labelledby="institution-history-heading"><div className="section-title"><div><h2 id="institution-history-heading">Case histories</h2><p>Expand a case to read its chronological audit history.</p></div></div>
      {profile.cases.map((record) => <details className="institution-history" key={record.id}><summary><strong>{record.case_code}</strong><span>{record.bureau}</span><StatusBadge status={record.status} /><span>{record.history.length} entries</span></summary><HistoryTimeline entries={record.history} /></details>)}
      {!profile.cases.length ? <p className="empty-state">No cases recorded for this institution.</p> : null}
    </section>
  </div>;
}
