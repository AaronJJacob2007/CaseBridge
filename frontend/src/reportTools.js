export const REPORTS = [
  { type: 'institution-wise', label: 'Institution-wise', description: 'Status totals for each institution. Unresolved cases appear separately.' },
  { type: 'bureau-wise', label: 'Bureau-wise', description: 'Case status and open workload across all bureaus.' },
  { type: 'region-wise', label: 'Region-wise', description: 'Case totals by registered region, falling back to reported region.' },
  { type: 'status-wise', label: 'Status-wise', description: 'Counts for each case status.' },
  { type: 'ageing-buckets', label: 'Ageing buckets', description: 'Open cases grouped by days since receipt, using the displayed reference date.' },
  { type: 'disposal-rate', label: 'Disposal rate', description: 'Disposed cases as a percentage of all cases, overall and by bureau.' },
  { type: 'overlapping-cases', label: 'Overlapping cases', description: 'Open cases at institutions with cases in at least two bureaus.' },
];
export function reportPath(type, csv = false) {
  if (!REPORTS.some(report => report.type === type)) throw new Error('Choose a valid report.');
  return '/reports/' + type + (csv ? '.csv' : '');
}
export const reportFilename = type => 'casebridge-' + reportPath(type).slice('/reports/'.length) + '.csv';
const LABELS = { aicte_id: 'AICTE Permanent ID', institution_id: 'Institution record ID', identity_resolved: 'Identity resolved', disposal_rate_percent: 'Disposal rate (%)', min_days: 'Minimum days', max_days: 'Maximum days' };
export const columnLabel = key => LABELS[key] || key.replaceAll('_', ' ').replace(/^./, char => char.toUpperCase());
export function reportCell(key, value) {
  if (value === null || value === undefined) return key === 'max_days' ? 'No upper limit' : 'Not supplied';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (key === 'disposal_rate_percent') return Number(value).toFixed(2) + '%';
  return String(value);
}
