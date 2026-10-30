import React, { useState } from 'react';
import { useResource, useMutation } from './useResource.js';
import { ErrorNotice, Field, HistoryTimeline, ResourceFeedback, StatusBadge } from './Shared.jsx';
import { canReview, buildLinkReview } from './coordinationTools.js';
import { formatDate } from './caseTools.js';
import { RequestForm, RequestItem } from './CoordinationForms.jsx';

function CompareChooser({ group, navigate }) {
  const [a, setA] = useState(String(group.cases[0]?.id || ''));
  const [b, setB] = useState('');
  const candidates = group.cases.filter(row => row.id !== Number(a) && row.bureau !== group.cases.find(item => item.id === Number(a))?.bureau);
  return <form className="compare-chooser" onSubmit={event => { event.preventDefault(); navigate('#overlaps/' + a + '/' + b); }}>
    <Field label="First case"><select value={a} onChange={event => { setA(event.target.value); setB(''); }}>{group.cases.map(row => <option key={row.id} value={row.id}>{row.case_code}  /  {row.bureau}</option>)}</select></Field>
    <Field label="Compare with"><select required value={b} onChange={event => setB(event.target.value)}><option value="">Choose another bureau's case</option>{candidates.map(row => <option key={row.id} value={row.id}>{row.case_code}  /  {row.bureau}</option>)}</select></Field>
    <button className="button" type="submit">Compare cases</button>
  </form>;
}

function OverlapGroup({ group, navigate }) {
  const bureaus = [...new Set(group.cases.map(record => record.bureau))];
  return <section className="panel overlap-group">
    <div className="section-title"><div><h2><a className="institution-title-link" href={'#institutions/' + group.institution_id} onClick={event => { event.preventDefault(); navigate('#institutions/' + group.institution_id); }}>{group.institution_name}</a></h2><p>{group.aicte_id} / {group.cases.length} open cases across {bureaus.length} bureaus</p></div><div className="bureau-tags">{bureaus.map(bureau => <span key={bureau} className={'bureau-tag bureau-' + bureau}>{bureau}</span>)}</div></div>
    <div className="table-scroll" role="region" tabIndex="0" aria-label={group.aicte_id + ' overlapping cases'}><table className="case-table overlap-table"><caption className="sr-only">Open cases at {group.institution_name}</caption><thead><tr><th scope="col">Case</th><th scope="col">Bureau</th><th scope="col">Status</th><th scope="col">Assigned officer</th></tr></thead><tbody>{group.cases.map(record => <tr key={record.id}><th scope="row"><a href={'#cases/' + record.id} onClick={event => { event.preventDefault(); navigate('#cases/' + record.id); }}>{record.case_code}</a></th><td><span className={'bureau-tag bureau-' + record.bureau}>{record.bureau}</span></td><td><StatusBadge status={record.status} /></td><td>{record.officer || 'Unassigned'}</td></tr>)}</tbody></table></div>
    <CompareChooser group={group} navigate={navigate} />
  </section>;
}

function CaseCard({ record, navigate }) {
  return <article className="panel comparison-card">
    <div className="section-title"><span className={'bureau-tag bureau-' + record.bureau}>{record.bureau} bureau</span><StatusBadge status={record.status} /></div>
    <h2><a href={'#cases/' + record.id} onClick={event => { event.preventDefault(); navigate('#cases/' + record.id); }}>{record.case_code}</a></h2><p className="comparison-officer">Assigned to {record.officer || 'Unassigned'}</p>
    <dl className="comparison-facts"><div><dt>Institution ID</dt><dd>{record.aicte_id || 'Unresolved'}</dd></div><div><dt>Category</dt><dd>{record.category || 'Not recorded'}</dd></div><div><dt>Received</dt><dd>{formatDate(record.received_on)}</dd></div><div><dt>Expected disposal</dt><dd>{formatDate(record.expected_disposal_on)}</dd></div></dl>
    <div className="comparison-description"><h3>Case description</h3><p>{record.description || 'Not recorded'}</p></div><div className="next-action"><span>Next action</span><p>{record.next_action || 'Not recorded'}</p></div>
    <details className="comparison-history"><summary>Chronological history <span>{record.history.length} entries</span></summary><HistoryTimeline entries={record.history} /></details>
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
  function refreshed() { setNotice('Saved. Reviews, requests and histories have been refreshed.'); first.refresh(); second.refresh(); }
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
    {notice ? <p className="success-notice" role="status">{notice}</p> : null}
    <section className="comparison-context" aria-label="Comparison context"><div><h2>{valid ? a.institution_name : 'Review the selected case identities'}</h2><p>{valid ? a.aicte_id + '  /  Exact registered ID match' : 'Both cases must be resolved at the same institution and belong to different bureaus.'}</p></div><span className={'review-state review-' + (link?.review_state || 'suggested')}>{link?.review_state === 'confirmed' ? 'Link confirmed' : link?.review_state === 'rejected' ? 'Link rejected' : 'Link not confirmed'}</span></section>
    <ol className="workflow-steps" aria-label="Coordination workflow">{['Compare cases', 'Review link', 'Coordinate request', 'Acknowledge'].map((step, index) => <li key={step}><span>{String(index + 1).padStart(2, '0')}</span>{step}</li>)}</ol>
    <div className="comparison-grid"><CaseCard record={a} navigate={navigate} /><CaseCard record={b} navigate={navigate} /></div>
    <fieldset className="coordination-controls" disabled={busy}><legend className="sr-only">Link review and coordination</legend>
      <section className="panel review-panel"><div className="section-title"><div><h2>Manual link review</h2></div><span className={'review-state review-' + (link?.review_state || 'suggested')}>{link?.review_state || 'Not reviewed'}</span></div>
        <p className="section-description">Do these cases concern related work? Review the details before confirming the link. Each case keeps its own status and history.</p>
        {link?.reason ? <p className="review-reason"><strong>Recorded reason:</strong> {link.reason}</p> : null}
        {!valid ? <p className="error-notice" role="alert">Select resolved cases from different bureaus at the same exact institution ID.</p> : null}
        {!allowed ? <p className="read-only-notice">{user.role === 'supervisor' ? 'Supervisor view is read-only.' : 'Only an officer in a selected case’s bureau can review or coordinate.'}</p> : <form onSubmit={event => { event.preventDefault(); submit('rejected'); }}><Field label="Review reason (required for rejection)"><textarea rows="2" value={reason} onChange={event => setReason(event.target.value)} placeholder="e.g. Complaints concern separate incidents" /></Field><div className="form-actions"><button className="button" type="button" onClick={() => submit('confirmed')}>Confirm link</button><button className="button button-danger-outline" type="submit">Reject link</button></div></form>}
        <p className="decision-footnote">Link review does not merge or close cases. The institution overlap alert remains independent.</p><ErrorNotice error={review.error} />
      </section>
      {allowed && link?.review_state === 'confirmed' ? <RequestForm api={api} link={link} target={target} onBusy={saving} onSaved={refreshed} /> : allowed ? <p className="coordination-locked">Confirm a link to make a coordination request.</p> : null}
      <section className="panel request-log"><div className="section-title"><div><h2>Recorded coordination requests</h2><p>Requests associated with either selected case</p></div><span className="scope-tag">{requests.length} recorded</span></div>
        {!requests.length ? <p className="compact-empty">No coordination requests have been recorded for these cases.</p> : requests.map(request => {
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
    <section className="overlap-banner"><div><h2>Potential Overlapping Cases - Coordination Required</h2><p>These institutions have open cases in more than one bureau. Matches use the exact AICTE Permanent ID; officers review whether the cases need coordination.</p></div><button className="button button-secondary" onClick={groups.refresh}>Refresh overlaps</button></section>
    {pair ? <><a className="text-link back-link" href="#overlaps" onClick={event => { event.preventDefault(); navigate('#overlaps'); }}>Back to  All overlapping institutions</a><Comparison key={pair.join(':')} api={api} user={user} users={users} pair={pair} navigate={navigate} onBusy={onBusy} /></> : groups.status !== 'ready' ? <ResourceFeedback resource={groups} title="overlaps" /> : !groups.data.length ? <section className="panel"><p className="compact-empty">No cross-bureau overlaps. Unresolved identities are excluded from matching.</p></section> : <>
      <div className="section-title overlap-list-heading"><div><h2>{groups.data.length} institutions with cross-bureau cases</h2><p>Choose one case from each bureau to compare their details.</p></div><span className="scope-tag">All bureaus</span></div>
      {groups.data.map(group => <OverlapGroup key={group.institution_id} group={group} navigate={navigate} />)}
    </>}
  </div>;
}
