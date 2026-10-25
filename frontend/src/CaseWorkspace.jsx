import React, { useState } from 'react';
import { buildCaseAction, canWriteCase, formatDate, institutionLink } from './caseTools.js';
import { ErrorNotice, Field, HistoryTimeline, ResourceFeedback, StatusBadge } from './Shared.jsx';
import { useMutation, useResource } from './useResource.js';

function ActionFields({ record, users, busy, submit }) {
  const [form, setForm] = useState({ event_type: 'update', remarks: '', doc_ref: '', status: '',
    next_action: record.next_action || '', expected_disposal_on: record.expected_disposal_on || '', to_bureau: '', officer_id: '' });
  const bureaus = [...new Set(users.map((row) => row.bureau))].filter((bureau) => bureau !== record.bureau).sort();
  const owners = users.filter((row) => row.role === 'officer' && row.bureau === form.to_bureau);
  function change(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value, ...(name === 'to_bureau' ? { officer_id: '' } : {}) }));
  }
  return <form onSubmit={(event) => { event.preventDefault(); submit(form); }}><fieldset className="form-fields" disabled={busy}><legend className="sr-only">New case action</legend><div className="form-grid">
    <Field label="Action type"><select name="event_type" value={form.event_type} onChange={change}><option value="update">Add note / update status</option><option value="escalate">Escalate</option><option value="transfer">Transfer</option></select></Field>
    {form.event_type === 'update' ? <Field label="Status"><select name="status" value={form.status} onChange={change}><option value="">Keep current status</option><option value="pending">Pending</option><option value="under_process">Under process</option><option value="disposed">Disposed</option></select></Field> : null}
    {form.event_type === 'transfer' ? <><Field label="Target bureau *"><select name="to_bureau" value={form.to_bureau} onChange={change} required><option value="">Select bureau</option>{bureaus.map((bureau) => <option key={bureau} value={bureau}>{bureau}</option>)}</select></Field><Field label="Target officer *"><select name="officer_id" value={form.officer_id} onChange={change} required disabled={!form.to_bureau}><option value="">Select officer</option>{owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.name}</option>)}</select></Field></> : null}
    <Field label="Remarks *" wide><textarea name="remarks" value={form.remarks} onChange={change} rows="3" required /></Field>
    <Field label="Document reference (file name only)"><input name="doc_ref" value={form.doc_ref} onChange={change} placeholder="reply.pdf" /><small className="form-help">Reference text only; no file is uploaded.</small></Field>
    <Field label="Next action"><input name="next_action" value={form.next_action} onChange={change} /></Field>
    <Field label="Expected disposal"><input type="date" name="expected_disposal_on" value={form.expected_disposal_on} onChange={change} /></Field>
  </div><div className="form-actions"><button className="button" type="submit">{busy ? 'Saving action…' : 'Save action'}</button></div></fieldset></form>;
}

export default function CaseWorkspace({ api, user, users, id, navigate, onBusy }) {
  const resource = useResource(api, '/cases/' + id);
  const mutation = useMutation(onBusy);
  const [notice, setNotice] = useState('');
  if (resource.status !== 'ready') return <ResourceFeedback resource={resource} title="case workspace" />;
  const record = resource.data;
  const writable = canWriteCase(user, record);
  function save(form) {
    setNotice('');
    mutation.run(() => api('/cases/' + id + '/actions', { method: 'POST', body: buildCaseAction(form) }), (updated) => {
      resource.replace(updated); setNotice('Action saved. The history below is updated.');
    }, (error) => { if (error.status === 403) resource.refresh(); });
  }
  return <div className="case-page">
    <div className="section-title"><div><h2>{record.case_code}</h2><p>{record.institution_name}</p></div><button className="button button-secondary" onClick={resource.refresh} disabled={mutation.busy}>Refresh case</button></div>
    {notice ? <p className="success-notice" role="status">{notice}</p> : null}<ErrorNotice error={mutation.error} />
    <section className="panel" aria-labelledby="case-details-heading"><div className="section-title"><h2 id="case-details-heading">Case details</h2><StatusBadge status={record.status} /></div>
      {!record.identity_resolved ? <p className="identity-notice">Identity unresolved. Reported details are retained; this case is not linked to a registered institution.</p> : null}
      <dl className="detail-grid">
        <div><dt>Institution</dt><dd>{institutionLink(record) ? <a href={institutionLink(record)} onClick={(event) => { event.preventDefault(); navigate(institutionLink(record)); }}>{record.institution_name}</a> : record.raw_institution_name}</dd></div>
        <div><dt>AICTE Permanent ID</dt><dd>{record.aicte_id || record.raw_aicte_id || 'Not supplied'}</dd></div>
        <div><dt>Bureau</dt><dd>{record.bureau}</dd></div><div><dt>Assigned officer</dt><dd>{record.officer || 'Unassigned'}</dd></div>
        <div><dt>Region</dt><dd>{record.region || 'Not recorded'}</dd></div><div><dt>Category</dt><dd>{record.category || 'Not recorded'}</dd></div>
        <div><dt>Received on</dt><dd>{formatDate(record.received_on)}</dd></div><div><dt>Expected disposal</dt><dd>{formatDate(record.expected_disposal_on)}</dd></div>
        <div className="detail-wide"><dt>Description</dt><dd>{record.description || 'Not recorded'}</dd></div>
        <div className="detail-wide"><dt>Last action</dt><dd>{record.last_action || 'Not recorded'}<small className="table-secondary">{formatDate(record.last_action_on)}</small></dd></div>
        <div className="detail-wide"><dt>Next action</dt><dd>{record.next_action || 'Not recorded'}</dd></div>
      </dl>
    </section>
    <section className="panel" aria-labelledby="action-heading"><h2 id="action-heading">Add an action</h2>
      {writable ? <ActionFields key={record.id + ':' + record.history.at(-1)?.id} record={record} users={users} busy={mutation.busy} submit={save} />
        : <p className="read-only-notice">{user.role === 'supervisor' ? 'Your supervisor role is read-only.' : 'This case belongs to ' + record.bureau + '. Only officers in that bureau can add actions.'} You can read the case and its history.</p>}
    </section>
    <section className="panel" aria-labelledby="history-heading"><div className="section-title"><div><h2 id="history-heading">Chronological history</h2><p>Oldest first. Every saved action and denied write is recorded.</p></div><span className="quiet-label">{record.history.length} entries</span></div><HistoryTimeline entries={record.history} /></section>
  </div>;
}
