import React, { useState } from 'react';
import { useResource, useMutation } from './useResource.js';
import { CasesTable, ErrorNotice, Field, HistoryTimeline, ResourceFeedback, StatusBadge } from './Shared.jsx';
import { canReview, buildLinkReview } from './coordinationTools.js';
import { RequestForm, RequestItem } from './CoordinationForms.jsx';

function CompareChooser({ group, navigate }) {
  const [a, setA] = useState(String(group.cases[0]?.id || ''));
  const [b, setB] = useState('');
  const candidates = group.cases.filter(row => row.id !== Number(a) && row.bureau !== group.cases.find(item => item.id === Number(a))?.bureau);
  return <form className="compare-chooser" onSubmit={event => { event.preventDefault(); navigate('#overlaps/' + a + '/' + b); }}>
    <Field label="First case"><select value={a} onChange={event => { setA(event.target.value); setB(''); }}>{group.cases.map(row => <option key={row.id} value={row.id}>{row.case_code} · {row.bureau}</option>)}</select></Field>
    <Field label="Second case"><select required value={b} onChange={event => setB(event.target.value)}><option value="">Choose another bureau's case</option>{candidates.map(row => <option key={row.id} value={row.id}>{row.case_code} · {row.bureau}</option>)}</select></Field>
    <button className="button">Compare cases</button>
  </form>;
}
function CaseCard({ record, navigate }) {
  return <article className="panel"><h2><a href={'#cases/' + record.id} onClick={e => { e.preventDefault(); navigate('#cases/' + record.id); }}>{record.case_code}</a></h2>
    <dl className="record-grid"><div><dt>Institution / AICTE Permanent ID</dt><dd>{record.institution_name} / {record.aicte_id || 'Unresolved'}</dd></div>
      <div><dt>Bureau / officer</dt><dd>{record.bureau} / {record.officer || 'Unassigned'}</dd></div>
      <div><dt>Status</dt><dd><StatusBadge status={record.status} /></dd></div>
      <div><dt>Category</dt><dd>{record.category || 'Not recorded'}</dd></div>
      <div><dt>Description</dt><dd>{record.description || 'Not recorded'}</dd></div>
      <div><dt>Next action</dt><dd>{record.next_action || 'Not recorded'}</dd></div></dl>
    <details><summary>Chronological history ({record.history.length})</summary><HistoryTimeline entries={record.history} /></details>
  </article>;
}
function Comparison({ api, user, users, pair, navigate, onBusy }) {
  const first = useResource(api, '/cases/' + pair[0]);
  const second = useResource(api, '/cases/' + pair[1]);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  function saving(value) { setBusy(value); onBusy(value); }
  const review = useMutation(saving);
  function refreshed() { setNotice('Saved. Links, requests and histories reloaded from the database.'); first.refresh(); second.refresh(); }
  if (first.status !== 'ready') return <ResourceFeedback resource={first} title="first case" />;
  if (second.status !== 'ready') return <ResourceFeedback resource={second} title="second case" />;
  const a = first.data, b = second.data;
  const valid = a.identity_resolved && b.identity_resolved && a.institution_id === b.institution_id && a.bureau !== b.bureau;
  const link = a.links.find(row => [row.case_a, row.case_b].includes(a.id) && [row.case_a, row.case_b].includes(b.id));
  const allowed = valid && canReview(user, a, b);
  const requests = [...new Map([...a.coordination_requests, ...b.coordination_requests].map(row => [row.id, row])).values()];
  function submit(state) { review.run(() => api('/links', { method: 'POST', body: buildLinkReview(a.id, b.id, state, reason) }), refreshed); }
  const target = a.bureau === user.bureau ? b.bureau : a.bureau;
  return <>
    {notice ? <p role="status">{notice}</p> : null}
    <div className="comparison-grid"><CaseCard record={a} navigate={navigate} /><CaseCard record={b} navigate={navigate} /></div>
    <fieldset className="coordination-controls" disabled={busy}>
      <section className="panel"><h2>Manual link review</h2><p>Review state: <strong>{link?.review_state || 'Not reviewed'}</strong>{link?.reason ? ' · Reason: ' + link.reason : ''}</p>
        <p>Reviewing a link does not merge, close or change either case. Institution overlap alerts remain independent.</p>
        {!valid ? <p role="alert">Select resolved cases from different bureaus at the same exact institution ID.</p> : null}
        {!allowed ? <p className="readonly-note">{user.role === 'supervisor' ? 'Supervisor view is read-only.' : 'Only an officer in a selected case’s bureau can review or coordinate.'}</p> : <form onSubmit={e => { e.preventDefault(); submit('rejected'); }}>
          <Field label="Review reason (required for rejection)"><textarea value={reason} onChange={e => setReason(e.target.value)} /></Field>
          <div className="form-actions"><button className="button" type="button" onClick={() => submit('confirmed')}>Confirm link</button><button className="button button-secondary" type="submit">Reject link</button></div>
        </form>}<ErrorNotice error={review.error} />
      </section>
      {allowed && link?.review_state === 'confirmed' ? <RequestForm api={api} link={link} target={target} onBusy={saving} onSaved={refreshed} /> : null}
      <section className="panel"><h2>Recorded coordination requests</h2>
        {!requests.length ? <p className="empty-state">No recorded requests for either selected case.</p> : requests.map(request => {
          const sourceLink = [...a.links, ...b.links].find(row => row.id === request.link_id);
          return <RequestItem key={request.id + ':' + request.status} request={request} user={user} users={users} api={api} confirmed={sourceLink?.review_state === 'confirmed'} onBusy={saving} onSaved={refreshed} />;
        })}
      </section>
    </fieldset>
  </>;
}
export default function OverlapPage({ api, user, users, pair, navigate, onBusy }) {
  const groups = useResource(api, '/overlaps');
  return <div className="workspace-stack">
    <div className="section-toolbar"><h2>Potential Overlapping Cases - Coordination Required</h2><button className="button button-secondary" onClick={groups.refresh}>Refresh overlaps</button></div>
    <p>Open cases in two or more bureaus, grouped by exact AICTE Permanent ID. Confirming or rejecting a link does not remove this alert.</p>
    {pair ? <><p><a href="#overlaps" onClick={e => { e.preventDefault(); navigate('#overlaps'); }}>Back to overlap list</a></p>
      <Comparison key={pair.join(':')} api={api} user={user} users={users} pair={pair} navigate={navigate} onBusy={onBusy} /></> : groups.status !== 'ready' ? <ResourceFeedback resource={groups} title="overlaps" /> : !groups.data.length ? <p className="empty-state">No cross-bureau overlaps.</p> : groups.data.map(group =>
      <section className="panel" key={group.institution_id}><h2>{group.aicte_id} · {group.institution_name}</h2><CasesTable cases={group.cases} navigate={navigate} /><CompareChooser group={group} navigate={navigate} /></section>
    )}
  </div>;
}
