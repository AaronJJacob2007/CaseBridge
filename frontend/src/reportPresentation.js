// Report presentation only. API payloads and server CSVs remain unchanged.
export function visibleReportColumns(columns) {
  const visible = columns.filter(column => column !== 'institution_id');
  const identity = ['aicte_id', 'institution_name'].filter(column => visible.includes(column));
  return [...identity, ...visible.filter(column => !identity.includes(column))];
}
export const numericReportColumn = column => ['total', 'pending', 'under_process', 'escalated', 'transferred', 'disposed', 'open', 'min_days', 'max_days', 'disposal_rate_percent'].includes(column);

// Retain each raw CSV cell so server quoting and spreadsheet-formula escaping
// survive column removal. Handle quoted commas, doubled quotes and newlines.
function rawCsvRows(text) {
  const rows = []; let row = [], cell = '', quoted = false;
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (char === '"') {
      cell += char;
      if (quoted && text[index + 1] === '"') { cell += '"'; index++; }
      else quoted = !quoted;
    } else if (!quoted && char === ',') { row.push(cell); cell = ''; }
    else if (!quoted && (char === '\r' || char === '\n')) {
      if (char === '\r' && text[index + 1] === '\n') index++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += char;
  }
  if (quoted) throw new Error('The CSV contains an unfinished quoted field. Please retry.');
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}
export async function presentationCsv(blob) {
  const rows = rawCsvRows((await blob.text()).replace(/^\uFEFF/, ''));
  if (!rows.length) throw new Error('The report CSV has no column headers.');
  const headers = rows[0].map(cell => cell.startsWith('"') && cell.endsWith('"') ? cell.slice(1, -1).replaceAll('""', '"') : cell);
  const indices = visibleReportColumns(headers).map(column => headers.indexOf(column));
  if (rows.some(row => row.length !== headers.length)) throw new Error('The report CSV columns are inconsistent. Please retry.');
  return new Blob([rows.map(row => indices.map(index => row[index]).join(',')).join('\r\n') + '\r\n'], { type: blob.type || 'text/csv;charset=utf-8' });
}
