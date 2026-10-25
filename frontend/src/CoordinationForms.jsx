import React, { useState } from 'react';
import { ErrorNotice, Field } from './Shared.jsx';
import { formatDate } from './caseTools.js';
import { useMutation } from './useResource.js';
import { buildCoordination, buildAcknowledgment, checkCoordination, submitCoordination, canCompleteRequest } from './coordinationTools.js';

function RequestStatus({ status }) {
  return <span className={'request-status request-status-' + status}>{status.replaceAll('_', ' ')}</span>;
}

export function RequestSummary({ request }) {
  return <dl className="request-summary">
    <div><dt>Action type</dt><dd>{request.action_type}</dd></div>
    <div><dt>Document category</dt><dd>{request.doc_category || 'Not recorded'}</dd></div>
    <div><dt>Period</dt><dd>{request.period || 'Not recorded'}</dd></div>
    <div><dt>Requested by / target bureau</dt><dd>{request.requester || 'Not recorded'}  /  {request.to_bureau}</dd></div>
    <div><dt>Assigned owner</dt><dd>{request.owner || 'Awaiting assignment'}</dd></div>
    <div><dt>Follow-up date</dt><dd>{formatDate(request.follow_up_on)}</dd></div>
    {request.proceed_reason ? <div className="field-wide"><dt>Reason for a separate request</dt><dd>{request.proceed_reason}</dd></div> : null}
  </dl>;
}

export function RequestForm({ api, link, target, onBusy, onSaved }) {
  const [form, setForm] = useState({ action_type: '', doc_category: '', period: '', to_bureau: target, follow_up_on: '', proceed_reason: '' });
  const [customAction, setCustomAction] = useState(false);
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
  return <section className="panel request-form-panel"><div className="section-title"><div><h2>Request coordination</h2><p>Each submission checks for a matching pending request before saving.</p></div><span className="review-state review-confirmed">Confirmed link</span></div>
    <form onSubmit={event => { event.preventDefault(); submit(); }}><fieldset className="request-fields" disabled={mutation.busy}><legend className="sr-only">Coordination request details</legend><div className="form-grid">
      <Field label="Action type *"><select required value={customAction ? '__custom__' : form.action_type} onChange={event => {
        const custom = event.target.value === '__custom__';
        setCustomAction(custom); field('action_type', custom ? '' : event.target.value);
      }}><option value="">Select action type</option><option value="Document request">Document request</option><option value="__custom__">Other action (specify)</option></select></Field>
      {customAction ? <Field label="Custom action type *"><input required value={form.action_type} onChange={event => field('action_type', event.target.value)} placeholder="e.g. Inspection request" /><small className="form-help">Use the same spelling and capitalization when checking an existing request.</small></Field> : null}
      <Field label="Document category"><input value={form.doc_category} onChange={event => field('doc_category', event.target.value)} placeholder="e.g. Fee records" /></Field>
      <Field label="Period"><input value={form.period} onChange={event => field('period', event.target.value)} placeholder="e.g. 2025-26" /></Field>
      <Field label="Target bureau"><select value={form.to_bureau} onChange={event => field('to_bureau', event.target.value)}><option value={target}>{target}</option></select></Field>
      <Field label="Initial follow-up (optional)"><input type="date" value={form.follow_up_on} onChange={event => field('follow_up_on', event.target.value)} /></Field>
    </div><p className="request-match-help">To check an existing request, use the same document category and period, including capitalization.</p><div className="form-actions request-actions"><button className="button button-secondary" type="button" onClick={checkOnly}>Check only</button><button className="button" type="submit">Check and save request</button></div>
    {warning ? <section className="coord-warning" role="alert" aria-labelledby="duplicate-warning-title"><div className="warning-heading"><div><h3 id="duplicate-warning-title">Matching pending request found</h3><p>Review the existing request before raising another for the same action, documents and period.</p></div></div>
      <div className="existing-request"><div className="section-title"><strong>Existing request #{warning.existing_request.id}</strong><RequestStatus status={warning.existing_request.status} /></div><RequestSummary request={warning.existing_request} /></div>
      <p className="warning-guidance">Choose Coordinate to use this request. A separate request requires a recorded reason.</p>
      <Field label="Reason for proceeding separately"><textarea rows="2" value={form.proceed_reason} onChange={event => setForm(old => ({ ...old, proceed_reason: event.target.value }))} placeholder="e.g. Different supporting documents are required" /></Field>
      <div className="form-actions"><button type="button" className="button" onClick={() => submit('coordinate')}>Coordinate</button><button type="button" className="button button-secondary" onClick={() => submit('proceed_separately')}>Proceed separately (reason required)</button></div>
    </section> : null}</fieldset></form>
    <ErrorNotice error={mutation.error} />{notice ? <p className="success-notice" role="status">{notice}</p> : null}
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
  const completable = canCompleteRequest(user, request);
  return <article className="request-item"><div className="section-title"><h3>Coordination request #{request.id}</h3><RequestStatus status={request.status} /></div><RequestSummary request={request} />
    {allowed && request.status === 'requested' && confirmed ? <form className="acknowledgment-form" onSubmit={event => {
      event.preventDefault(); mutation.run(() => api('/coordination/' + request.id + '/ack', { method: 'POST', body: buildAcknowledgment(owner, date) }), onSaved);
    }}><fieldset className="request-fields" disabled={mutation.busy}><legend>Acknowledge and assign responsibility</legend><div className="form-grid">
      <Field label="Acknowledgment owner *"><select required value={owner} onChange={event => setOwner(event.target.value)}>{eligible.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Field>
      <Field label="Follow-up date *"><input required type="date" value={date} onChange={event => setDate(event.target.value)} /></Field>
    </div><button className="button" type="submit">Acknowledge request</button></fieldset></form> : null}
    {completable ? <form className="completion-form" onSubmit={event => {
      event.preventDefault(); mutation.run(() => api('/coordination/' + request.id + '/complete', { method: 'POST', body: { remarks } }), onSaved);
    }}><fieldset className="request-fields" disabled={mutation.busy}><legend className="sr-only">Complete request</legend><Field label="Completion remarks"><input required value={remarks} onChange={event => setRemarks(event.target.value)} placeholder="e.g. Fee records received and shared" /></Field><button className="button button-secondary" type="submit">Mark completed</button></fieldset></form> : null}
    {allowed && pending && !completable ? <p className="read-only-notice">Acknowledge this request before marking it completed.</p> : null}
    {!allowed && pending ? <p className="read-only-notice">Only a target-bureau officer can acknowledge or complete this request.</p> : null}
    {!confirmed && pending ? <p className="identity-notice">{request.acknowledged_at ? 'Link is no longer confirmed. A target-bureau officer can still complete this previously acknowledged request.' : 'Link is no longer confirmed. Confirm the link again before acknowledging and completing this request.'}</p> : null}
    <ErrorNotice error={mutation.error} />
  </article>;
}
