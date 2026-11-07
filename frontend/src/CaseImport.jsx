import React, { useState } from 'react';
import { ErrorNotice } from './Shared.jsx';
import { useMutation } from './useResource.js';

export default function CaseImport({ api, user, onBusy, onSaved, onCancel }) {
  const [csv, setCsv] = useState('');
  const [preview, setPreview] = useState(null);
  const [notice, setNotice] = useState('');
  const [fileError, setFileError] = useState('');
  const [fileVersion, setFileVersion] = useState(0);
  const mutation = useMutation(onBusy);
  async function chooseFile(event) {
    const file = event.target.files?.[0];
    setPreview(null); setCsv(''); setNotice(''); setFileError('');
    if (!file) return;
    if (file.size > 500000) { setFileError('Choose a CSV file smaller than 500 KB.'); return; }
    try { setCsv(await file.text()); } catch { setFileError('Could not read the file. Please choose it again.'); }
  }
  function check() {
    mutation.run(() => api('/cases/import/preview', { method: 'POST', body: { csv_text: csv } }), result => { setPreview(result); setNotice(''); });
  }
  function save() {
    mutation.run(() => api('/cases/import', { method: 'POST', body: { csv_text: csv } }), result => {
      setNotice(`Imported ${result.imported} cases; skipped ${result.skipped} invalid rows.`);
      setPreview(null); setCsv(''); setFileVersion(value => value + 1); onSaved();
    });
  }
  return <section className="panel" aria-labelledby="import-heading">
    <div className="section-title"><div><h2 id="import-heading">Import cases from CSV</h2><p>Cases will be assigned to {user.name} in {user.bureau}.</p></div></div>
    <p className="form-help">Use synthetic demo data only. Required headers: case_code, institution_name. Optional: aicte_id, raw_region, category, description, received_on, status, remarks, next_action, expected_disposal_on. Dates use YYYY-MM-DD. Maximum 200 rows.</p>
    <fieldset className="form-fields" disabled={mutation.busy}><legend className="sr-only">CSV import</legend>
      <label className="form-field"><span>CSV file</span><input key={fileVersion} type="file" accept=".csv,text/csv" onChange={chooseFile} /></label>
      {fileError ? <p className="error-notice" role="alert">{fileError}</p> : null}
      <div className="form-actions"><button className="button button-secondary" type="button" disabled={!csv} onClick={check}>Preview rows</button><button className="button button-secondary" type="button" onClick={onCancel}>Close</button></div>
      {preview ? <div><h3>Preview: {preview.valid_count} valid, {preview.invalid_count} invalid</h3><p className="form-help">Only valid rows will be imported. Missing or unknown institution IDs remain unresolved.</p>
        <div className="table-scroll" tabIndex="0" role="region" aria-label="CSV import preview"><table className="case-table"><thead><tr><th>Row</th><th>Case code</th><th>Institution</th><th>Validation</th></tr></thead><tbody>{preview.rows.map(row => <tr key={row.row}><td>{row.row}</td><td>{row.case_code || '—'}</td><td>{row.institution_name || '—'}</td><td>{[...row.errors, ...row.warnings].join('; ') || 'Ready'}</td></tr>)}</tbody></table></div>
        <div className="form-actions"><button className="button" type="button" disabled={!preview.valid_count} onClick={save}>Import {preview.valid_count} valid {preview.valid_count === 1 ? 'case' : 'cases'}</button></div></div> : null}
    </fieldset><ErrorNotice error={mutation.error} />{notice ? <p className="success-notice" role="status">{notice}</p> : null}
  </section>;
}
