import React, { useState } from 'react';
import { buildCaseCreate, buildCaseQuery, EMPTY_FILTERS, STATUSES, statusLabel, formatDate } from './caseTools.js';
import { CasesTable, ErrorNotice, Field, ResourceFeedback } from './Shared.jsx';
import { useMutation, useResource } from './useResource.js';

function CaseEntry({ api, user, users, categories, regions, onBusy, onCreated, onCancel }) {
  const [form, setForm] = useState({ case_code: '', aicte_id: '', institution_name: '', raw_region: '',
    officer_id: String(user.id), category: '', description: '', received_on: '', status: 'pending',
    remarks: 'Case registered', next_action: '', expected_disposal_on: '' });
  const mutation = useMutation(onBusy);
  const change = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  const officers = users.filter((row) => row.role === 'officer' && row.bureau === user.bureau);
  function submit(event) {
    event.preventDefault();
    mutation.run(() => api('/cases', { method: 'POST', body: buildCaseCreate(form, user) }), onCreated);
  }
  return <section className="panel case-entry-panel" id="case-entry" aria-labelledby="entry-heading">
    <div className="section-title"><div><h2 id="entry-heading">Register a case</h2><p>New cases belong to your {user.bureau} bureau.</p></div></div>
    <p className="form-help">An exact registered AICTE ID resolves the institution. Missing or unknown IDs remain identity-unresolved for manual review.</p>
    <form onSubmit={submit}>
      <fieldset disabled={mutation.busy} className="form-fields"><legend className="sr-only">Case registration</legend>
        <div className="form-grid">
          <Field label="Case code *"><input name="case_code" value={form.case_code} onChange={change} required /></Field>
          <Field label="AICTE Permanent ID"><input name="aicte_id" value={form.aicte_id} onChange={change} autoCapitalize="off" spellCheck="false" /></Field>
          <Field label="Institution name *"><input name="institution_name" value={form.institution_name} onChange={change} required /></Field>
          <Field label="Reported region"><input name="raw_region" value={form.raw_region} onChange={change} list="entry-regions" /><datalist id="entry-regions">{regions.map((region) => <option key={region} value={region} />)}</datalist></Field>
          <Field label="Assigned officer"><select name="officer_id" value={form.officer_id} onChange={change} required>{officers.map((officer) => <option key={officer.id} value={officer.id}>{officer.name}</option>)}</select></Field>
          <Field label="Category"><input name="category" value={form.category} onChange={change} list="entry-categories" /><datalist id="entry-categories">{categories.map((category) => <option key={category} value={category} />)}</datalist></Field>
          <Field label="Received on (blank uses reference date)"><input type="date" name="received_on" value={form.received_on} onChange={change} /></Field>
          <Field label="Initial status"><select name="status" value={form.status} onChange={change}>{STATUSES.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select></Field>
          <Field label="Expected disposal"><input type="date" name="expected_disposal_on" value={form.expected_disposal_on} onChange={change} /></Field>
          <Field label="Description" wide><textarea name="description" value={form.description} onChange={change} rows="3" /></Field>
          <Field label="Registration remarks *" wide><textarea name="remarks" value={form.remarks} onChange={change} rows="2" required /></Field>
          <Field label="Next action" wide><input name="next_action" value={form.next_action} onChange={change} /></Field>
        </div>
        <div className="form-actions"><button type="submit" className="button">{mutation.busy ? 'Saving case…' : 'Save case'}</button><button type="button" className="button button-secondary" onClick={onCancel}>Cancel</button></div>
      </fieldset>
      <ErrorNotice error={mutation.error} />
    </form>
  </section>;
}

export default function CaseRegister({ api, user, users, navigate, onBusy, onCreated }) {
  const [draft, setDraft] = useState({ ...EMPTY_FILTERS });
  const [query, setQuery] = useState('');
  const [filterError, setFilterError] = useState(null);
  const [showEntry, setShowEntry] = useState(false);
  const allCases = useResource(api, '/cases');
  const deadlineFlags = useResource(api, '/alerts');
  const filtered = useResource(api, query ? '/cases?' + query : null);
  const results = query ? filtered : allCases;
  const catalog = allCases.data ?? [];
  const categories = [...new Set(catalog.map((row) => row.category).filter(Boolean))].sort();
  const regions = [...new Set(catalog.map((row) => row.region).filter(Boolean))].sort();
  const bureaus = [...new Set(users.map((row) => row.bureau))].sort();
  const change = (event) => setDraft((current) => ({ ...current, [event.target.name]: event.target.value }));
  function apply(event) {
    event.preventDefault();
    try { setQuery(buildCaseQuery(draft)); setFilterError(null); }
    catch (error) { setFilterError(error); }
  }
  function clear() { setDraft({ ...EMPTY_FILTERS }); setQuery(''); setFilterError(null); }
  return <div className="case-page">
    <div className="section-title"><p>Search across bureaus. Write access follows your demo role and bureau.</p>
      {user.role === 'officer' ? <button className="button" onClick={() => setShowEntry(true)} aria-expanded={showEntry} aria-controls="case-entry" disabled={showEntry}>New case</button> : <span className="role-badge">Read-only role</span>}
    </div>
    {showEntry ? <CaseEntry api={api} user={user} users={users} categories={categories} regions={regions} onBusy={onBusy} onCreated={onCreated} onCancel={() => setShowEntry(false)} /> : null}
    <section className="panel" aria-labelledby="filters-heading">
      <h2 id="filters-heading">Filter cases</h2>
      <form onSubmit={apply} className="filter-form"><div className="form-grid">
        <Field label="Institution name"><input name="institution_name" value={draft.institution_name} onChange={change} placeholder="e.g. Riverbend" /></Field>
        <Field label="AICTE Permanent ID"><input name="aicte_id" value={draft.aicte_id} onChange={change} autoCapitalize="off" spellCheck="false" /></Field>
        <Field label="Case code"><input name="case_code" value={draft.case_code} onChange={change} /></Field>
        <Field label="Bureau"><select name="bureau" value={draft.bureau} onChange={change}><option value="">All bureaus</option>{bureaus.map((bureau) => <option key={bureau} value={bureau}>{bureau}</option>)}</select></Field>
        <Field label="Region"><input name="region" list="filter-regions" value={draft.region} onChange={change} /><datalist id="filter-regions">{regions.map((region) => <option key={region} value={region} />)}</datalist></Field>
        <Field label="Category"><input name="category" list="filter-categories" value={draft.category} onChange={change} /><datalist id="filter-categories">{categories.map((category) => <option key={category} value={category} />)}</datalist></Field>
        <Field label="Status"><select name="status" value={draft.status} onChange={change}><option value="">All statuses</option>{STATUSES.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select></Field>
        <Field label="Received from"><input type="date" name="received_from" value={draft.received_from} onChange={change} max={draft.received_to || undefined} /></Field>
        <Field label="Received to"><input type="date" name="received_to" value={draft.received_to} onChange={change} min={draft.received_from || undefined} /></Field>
      </div><div className="form-actions"><button className="button" type="submit">Apply filters</button><button className="button button-secondary" type="button" onClick={clear}>Clear filters</button></div><ErrorNotice error={filterError} /></form>
    </section>
    <section className="panel register-results" aria-labelledby="results-heading"><div className="section-title"><div><h2 id="results-heading">Cases</h2><p role="status">{results.status === 'ready' ? results.data.length + ' cases shown' : 'Fetching cases…'}</p></div><button className="button button-secondary" onClick={results.refresh}>Refresh register</button></div>
      {deadlineFlags.status === 'ready' ? <p className="form-help">Deadline flags as of {formatDate(deadlineFlags.data.as_of)}.</p> : <ResourceFeedback resource={deadlineFlags} title="deadline flags" />}
      {results.status === 'ready' ? <CasesTable cases={results.data} navigate={navigate} overdueIds={deadlineFlags.data?.overdue.map(record => record.id) ?? []} /> : <ResourceFeedback resource={results} title="case register" />}
    </section>
  </div>;
}
