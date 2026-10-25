import React from 'react';
import { formatDate, formatTimestamp, institutionLink, statusLabel } from './caseTools.js';

export function Feedback({ title, message, onRetry, loading = false }) {
  return <section className="feedback panel" aria-live="polite" role={loading ? 'status' : 'alert'}>
    <span className={loading ? 'feedback-dot loading' : 'feedback-dot'} aria-hidden="true" />
    <h2>{title}</h2><p>{message}</p>
    {onRetry ? <button className="button" onClick={onRetry}>Try again</button> : null}
  </section>;
}
export function ResourceFeedback({ resource, title }) {
  return resource.status === 'error'
    ? <Feedback title={'Could not load ' + title} message={(resource.error.status ? resource.error.status + ': ' : '') + resource.error.message} onRetry={resource.refresh} />
    : <Feedback title={'Loading ' + title} message="Fetching current records…" loading />;
}
export function StatusBadge({ status }) { return <span className={'status-badge status-' + status}>{statusLabel(status)}</span>; }
export function ErrorNotice({ error }) { return error ? <p className="error-notice" role="alert">{error.status ? error.status + ': ' : ''}{error.message}</p> : null; }
export function Field({ label, children, wide = false }) { return <label className={'form-field' + (wide ? ' field-wide' : '')}><span>{label}</span>{children}</label>; }

export function CasesTable({ cases, navigate }) {
  if (!cases.length) return <p className="empty-state">No cases match these filters.</p>;
  return <div className="table-scroll" tabIndex="0" aria-label="Scrollable case register"><table className="case-table">
    <thead><tr><th scope="col">Case</th><th scope="col">Institution</th><th scope="col">Bureau</th><th scope="col">Category</th><th scope="col">Status</th><th scope="col">Officer</th><th scope="col">Received</th><th scope="col">Expected disposal</th></tr></thead>
    <tbody>{cases.map((record) => <tr key={record.id}>
      <th scope="row"><a href={'#cases/' + record.id} onClick={(event) => { event.preventDefault(); navigate('#cases/' + record.id); }}>{record.case_code}</a></th>
      <td>{institutionLink(record) ? <a href={institutionLink(record)} onClick={(event) => { event.preventDefault(); navigate(institutionLink(record)); }}>{record.institution_name}</a> : <>{record.institution_name}<small className="identity-warning">Identity unresolved</small></>}<small className="table-secondary">{record.aicte_id || record.raw_aicte_id || 'AICTE ID not supplied'}</small></td>
      <td>{record.bureau}</td><td>{record.category || 'Not recorded'}</td><td><StatusBadge status={record.status} /></td><td>{record.officer || 'Unassigned'}</td><td>{formatDate(record.received_on)}</td><td>{formatDate(record.expected_disposal_on)}</td>
    </tr>)}</tbody>
  </table></div>;
}

export function HistoryTimeline({ entries }) {
  if (!entries.length) return <p className="empty-state">No recorded actions.</p>;
  return <ol className="history-list">{entries.map((entry) => <li key={entry.id}>
    <div className="history-top"><strong>{entry.event_type.replaceAll('_', ' ')}</strong><time dateTime={entry.at}>{formatTimestamp(entry.at)}</time></div>
    <p>{entry.remarks || 'No remarks recorded'}</p>
    <small>{entry.actor || 'System / administrative import'}{entry.bureau ? ' · ' + entry.bureau : ''}</small>
    {entry.doc_ref ? <p className="document-reference">Document reference: {entry.doc_ref}</p> : null}
  </li>)}</ol>;
}
