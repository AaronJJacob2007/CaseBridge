import React, { useState } from 'react';
import { ErrorNotice, Field } from './Shared.jsx';
import { formatDate } from './caseTools.js';
import { useMutation } from './useResource.js';
import { buildCoordination, buildAcknowledgment, checkCoordination, submitCoordination } from './coordinationTools.js';

export function RequestSummary({ request }) {
  return <dl className="record-grid">
    <div><dt>Request</dt><dd>#{request.id} · {request.status}</dd></div>
    <div><dt>Action / documents / period</dt><dd>{request.action_type} / {request.doc_category || 'Not recorded'} / {request.period || 'Not recorded'}</dd></div>
    <div><dt>Requester / target</dt><dd>{request.requester} / {request.to_bureau}</dd></div>
    <div><dt>Owner / follow-up</dt><dd>{request.owner || 'Unassigned'} / {formatDate(request.follow_up_on)}</dd></div>
    {request.proceed_reason ? <div><dt>Separate-request reason</dt><dd>{request.proceed_reason}</dd></div> : null}
  </dl>;
}
export function RequestForm({ api, link, target, onBusy, onSaved }) {
  const [form, setForm] = useState({ action_type: '', doc_category: '', period: '', to_bureau: target, follow_up_on: '', proceed_reason: '' });
  const [warning, setWarning] = useState(null);
  const [notice, setNotice] = useState('');
  const mutation = useMutation(onBusy);
  function field(key, value) { setForm(old => ({ ...old, [key]: value })); setWarning(null); setNotice(''); }
  function checkOnly() {
    mutation.run(() => checkCoordination(api, buildCoordination(link.id, form)), result => { setWarning(result.warning ? result : null); setNotice(result.warning ? '' : 'No matching pending request. Nothing saved.'); });
  }
  function submit(decision) {
    mutation.run(() => submitCoordination(api, buildCoordination(link.id, form, decision)), result => {
      if (result.outcome === 'warning') { setWarning(result); setNotice(''); }
      else {
        setWarning(null); setNotice(result.outcome === 'coordinated' ? 'Coordinating with existing request #' + result.request.id + '. No duplicate created.' : 'Request #' + result.request.id + ' saved.');
        onSaved();
      }
    });
  }
  return <section className="panel"><h2>Request coordination</h2>
    <p>Each submission checks for matching pending requests before saving.</p>
    <form onSubmit={e => { e.preventDefault(); submit(); }}><fieldset disabled={mutation.busy}><div className="form-grid">
      <Field label="Action type"><input required value={form.action_type} onChange={e => field('action_type', e.target.value)} placeholder="e.g. Document request" /></Field>
      <Field label="Document category"><input value={form.doc_category} onChange={e => field('doc_category', e.target.value)} placeholder="e.g. Fee records" /></Field>
      <Field label="Period"><input value={form.period} onChange={e => field('period', e.target.value)} placeholder="e.g. 2025-26" /></Field>
      <Field label="Target bureau"><select value={form.to_bureau} onChange={e => field('to_bureau', e.target.value)}><option value={target}>{target}</option></select></Field>
      <Field label="Initial follow-up (optional)"><input type="date" value={form.follow_up_on} onChange={e => field('follow_up_on', e.target.value)} /></Field>
    </div><div className="form-actions"><button className="button button-secondary" type="button" onClick={checkOnly}>Check only</button><button className="button" type="submit">Check and save request</button></div>
    {warning ? <section className="coord-warning" role="alert"><h3>Matching pending request found</h3>
      <RequestSummary request={warning.existing_request} /><p>Coordinate with this request, or explain why another is needed.</p>
      <Field label="Reason for proceeding separately"><textarea value={form.proceed_reason} onChange={e => setForm(old => ({ ...old, proceed_reason: e.target.value }))} /></Field>
      <div className="form-actions"><button type="button" className="button" onClick={() => submit('coordinate')}>Coordinate</button>
      <button type="button" className="button button-secondary" onClick={() => submit('proceed_separately')}>Proceed separately (reason required)</button></div>
    </section> : null}</fieldset></form>
    <ErrorNotice error={mutation.error} />{notice ? <p role="status">{notice}</p> : null}
  </section>;
}
export function RequestItem({ request, user, users, api, confirmed, onBusy, onSaved }) {
  const eligible = users.filter(row => row.role === 'officer' && row.bureau === request.to_bureau);
  const [owner, setOwner] = useState(String(request.owner_id || eligible.find(row => row.id === user.id)?.id || eligible[0]?.id || ''));
  const [date, setDate] = useState(request.follow_up_on || '');
  const [remarks, setRemarks] = useState('');
  const mutation = useMutation(onBusy);
  const allowed = user.role === 'officer' && user.bureau === request.to_bureau;
  const pending = ['requested', 'acknowledged', 'in_progress'].includes(request.status);
  return <article className="request-item"><h3>Coordination request #{request.id}</h3><RequestSummary request={request} />
    {allowed && request.status === 'requested' && confirmed ? <form onSubmit={e => {
      e.preventDefault(); mutation.run(() => api('/coordination/' + request.id + '/ack', { method: 'POST', body: buildAcknowledgment(owner, date) }), onSaved);
    }}><fieldset disabled={mutation.busy}><div className="form-grid">
      <Field label="Acknowledgment owner"><select required value={owner} onChange={e => setOwner(e.target.value)}>{eligible.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Field>
      <Field label="Follow-up date"><input required type="date" value={date} onChange={e => setDate(e.target.value)} /></Field>
    </div><button className="button">Acknowledge request</button></fieldset></form> : null}
    {allowed && pending ? <form onSubmit={e => {
      e.preventDefault(); mutation.run(() => api('/coordination/' + request.id + '/complete', { method: 'POST', body: { remarks } }), onSaved);
    }}><fieldset disabled={mutation.busy}><Field label="Completion remarks"><input required value={remarks} onChange={e => setRemarks(e.target.value)} /></Field><button className="button button-secondary">Mark completed</button></fieldset></form> : null}
    {!allowed && pending ? <p className="muted">Only a target-bureau officer can acknowledge or complete this request.</p> : null}
    {!confirmed && pending ? <p>Link is no longer confirmed. Acknowledgment is unavailable; the target bureau can still complete the existing request.</p> : null}
    <ErrorNotice error={mutation.error} />
  </article>;
}
