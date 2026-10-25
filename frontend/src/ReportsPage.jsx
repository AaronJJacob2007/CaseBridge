import React, { useEffect, useRef, useState } from 'react';
import { visibleReportColumns, numericReportColumn, presentationCsv } from './reportPresentation.js';
import { REPORTS, columnLabel, reportCell, reportFilename, reportPath } from './reportTools.js';
import { ErrorNotice, ResourceFeedback } from './Shared.jsx';
import { useResource } from './useResource.js';
import { formatDate } from './caseTools.js';

function ReportView({ api, report }) {
  const resource = useResource(api, reportPath(report.type));
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
      const source = await api(reportPath(report.type, true), { responseType: 'blob', signal: state.controller.signal });
      const blob = await presentationCsv(source);
      if (!state.active) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = reportFilename(report.type);
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
      <div className="form-actions"><button className="button button-secondary" onClick={resource.refresh} disabled={download.busy}>Refresh report</button><button className="button" onClick={downloadCsv} disabled={download.busy}>{download.busy ? 'Preparing CSV…' : 'Download CSV'}</button></div>
    </div>
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

export default function ReportsPage({ api }) {
  const [type, setType] = useState(REPORTS[0].type);
  const report = REPORTS.find(item => item.type === type);
  return <div className="case-page">
    <section className="panel"><label className="form-field report-picker"><span>Report</span><select value={type} onChange={event => setType(event.target.value)}>{REPORTS.map(item => <option key={item.type} value={item.type}>{item.label}</option>)}</select></label><p className="form-help">Reports show all bureaus for officers and supervisors. Refresh to include recent changes; CSV downloads use current saved data and omit internal record IDs.</p></section>
    <ReportView key={type} api={api} report={report} />
  </div>;
}
