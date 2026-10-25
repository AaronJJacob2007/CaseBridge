import React, { useEffect, useRef, useState } from 'react';
import { visibleReportColumns, numericReportColumn, presentationCsv } from './reportPresentation.js';
import { REPORTS, PERFORMANCE_REPORT, performancePath, columnLabel, reportCell, reportFilename, reportPath } from './reportTools.js';
import { ErrorNotice, ResourceFeedback } from './Shared.jsx';
import { useResource } from './useResource.js';
import { formatDate } from './caseTools.js';

function ReportView({ api, report, selection }) {
  const path = csv => selection ? performancePath(selection, csv) : reportPath(report.type, csv);
  const resource = useResource(api, path(false));
  const [download, setDownload] = useState({ busy: false, error: null, saved: false });
  const lifecycle = useRef(null);
  useEffect(() => {
    const state = { active: true, controller: null, urls: new Map() };
    lifecycle.current = state;
    return () => {
      state.active = false;
      state.controller?.abort();
      for (const [url, timer] of state.urls) { clearTimeout(timer); URL.revokeObjectURL(url); }
      state.urls.clear();
    };
  }, []);
  async function downloadCsv() {
    const state = lifecycle.current;
    if (!state?.active || state.controller) return;
    state.controller = new AbortController();
    setDownload({ busy: true, error: null, saved: false });
    try {
      const source = await api(path(true), { responseType: 'blob', signal: state.controller.signal });
      const blob = await presentationCsv(source);
      if (!state.active) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = selection ? `casebridge-performance-${selection.kind}-${selection.year}-${selection.period}.csv` : reportFilename(report.type);
      document.body.append(anchor);
      try { anchor.click(); } finally {
        anchor.remove();
        const timer = setTimeout(() => { URL.revokeObjectURL(url); state.urls.delete(url); }, 1000);
        state.urls.set(url, timer);
      }
      setDownload({ busy: false, error: null, saved: true });
    } catch (error) {
      if (state.active && error.name !== 'AbortError') setDownload({ busy: false, error, saved: false });
    } finally { state.controller = null; }
  }
  if (resource.status !== 'ready') return <ResourceFeedback resource={resource} title={report.label + ' report'} />;
  const data = resource.data;
  const columns = visibleReportColumns(data.columns);
  return <section className="panel" aria-labelledby="report-title">
    <div className="section-title report-toolbar"><div><h2 id="report-title">{report.label}</h2><p>{report.description}</p><p className="form-help">As of {formatDate(data.as_of)}  /  {data.rows.length} rows  /  All bureaus</p></div>
      <div className="form-actions"><button className="button button-secondary" onClick={resource.refresh} disabled={download.busy}>Refresh report</button><button className="button" onClick={downloadCsv} disabled={download.busy}>{download.busy ? 'Preparing CSVÃ¢â‚¬Â¦' : 'Download CSV'}</button></div>
    </div>
    {data.counting_rules ? <div className="report-rules"><h3>Counting rules</h3><p>{data.counting_rules}</p>{data.partial_period ? <p>This period is in progress. Receipts stop at the reference date.</p> : null}</div> : null}
    <ErrorNotice error={download.error} />
    {download.saved ? <p className="success-notice" role="status">CSV download started. Check your browser downloads.</p> : null}
    {!data.rows.length ? <p className="empty-state" role="status">No records are available for this report. You can still download its column headers.</p> : <div className="table-scroll" tabIndex="0" role="region" aria-label={report.label + ' report table'}><table className="case-table report-table">
      <caption className="sr-only">{report.label}, as of {data.as_of}, all bureaus</caption>
      <thead><tr>{columns.map(column => <th key={column} scope="col" className={numericReportColumn(column) ? 'numeric' : undefined}>{columnLabel(column)}</th>)}</tr></thead>
      <tbody>{data.rows.map((row, index) => <tr key={index}>{columns.map((column, columnIndex) => {
        const Tag = columnIndex === 0 ? 'th' : 'td';
        const name = column === 'institution_name';
        const value = reportCell(column, row[column]);
        return <Tag key={column} scope={columnIndex === 0 ? 'row' : undefined} className={name ? 'report-institution' : numericReportColumn(column) ? 'numeric' : undefined} title={name ? value : undefined}>{name && row.identity_resolved && row.institution_id ? <a href={'#institutions/' + row.institution_id}>{value}</a> : value}</Tag>;
      })}</tr>)}</tbody>
    </table></div>}
  </section>;
}

function PerformanceSelection({ api, initial }) {
  const defaults = { kind: initial.kind, year: initial.year, period: initial.period };
  const [draft, setDraft] = useState(defaults);
  const [selection, setSelection] = useState(defaults);
  const [error, setError] = useState(null);
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  function apply(event) {
    event.preventDefault();
    try { performancePath(draft); setSelection({ ...draft }); setError(null); }
    catch (failure) { setError(failure); }
  }
  return <>
    <form className="panel" onSubmit={apply}>
      <div className="form-grid">
        <label className="form-field"><span>Period type</span><select value={draft.kind} onChange={event => setDraft({ ...draft, kind: event.target.value, period: 1 })}><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option></select></label>
        <label className="form-field"><span>Year</span><input type="number" min="1" max={Number(initial.as_of.slice(0, 4))} required value={draft.year} onChange={event => setDraft({ ...draft, year: event.target.value })} /></label>
        <label className="form-field"><span>{draft.kind === 'monthly' ? 'Month' : 'Quarter'}</span><select value={draft.period} onChange={event => setDraft({ ...draft, period: event.target.value })}>{(draft.kind === 'monthly' ? months : ['Q1: January - March', 'Q2: April - June', 'Q3: July - September', 'Q4: October - December']).map((label, index) => <option key={label} value={index + 1}>{label}</option>)}</select></label>
      </div>
      <ErrorNotice error={error} /><div className="form-actions"><button className="button" type="submit">Apply period</button></div>
    </form>
    <ReportView key={performancePath(selection)} api={api} report={PERFORMANCE_REPORT} selection={selection} />
  </>;
}
function PerformanceReport({ api }) {
  const resource = useResource(api, reportPath('performance'));
  return resource.status === 'ready' ? <PerformanceSelection api={api} initial={resource.data} /> : <ResourceFeedback resource={resource} title="Performance report" />;
}

export default function ReportsPage({ api }) {
  const [type, setType] = useState(REPORTS[0].type);
  const reports = [...REPORTS, PERFORMANCE_REPORT];
  const report = reports.find(item => item.type === type);
  return <div className="case-page">
    <section className="panel"><label className="form-field report-picker"><span>Report</span><select value={type} onChange={event => setType(event.target.value)}>{reports.map(item => <option key={item.type} value={item.type}>{item.label}</option>)}</select></label><p className="form-help">Reports show all bureaus for officers and supervisors. Refresh to include recent changes; CSV downloads use current saved data and omit internal record IDs.</p></section>
    {type === 'performance' ? <PerformanceReport api={api} /> : <ReportView key={type} api={api} report={report} />}
  </div>;
}
