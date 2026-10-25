// Read-only checks against the actual Vite proxy and PostgreSQL reports.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createApi, loadDemoUsers, ApiError } from '../src/api.js';
import { REPORTS, reportPath, reportFilename, reportCell } from '../src/reportTools.js';
import { parseRoute } from '../src/caseTools.js';
const baseUrl = 'http://127.0.0.1:5173';
async function context(name = 'Anita Rao') {
  const users = await loadDemoUsers({ baseUrl });
  const user = users.find(row => row.name === name);
  assert.ok(user);
  return createApi(user.id, { baseUrl });
}

// Parse CSV quoting, doubled quotes and embedded newlines for exact JSON comparison.
function csvRows(text) {
  const rows = []; let row = [], field = '', quoted = false;
  for (let index = 0; index < text.length; index++) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') { field += '"'; index++; }
      else quoted = !quoted;
    } else if (!quoted && char === ',') { row.push(field); field = ''; }
    else if (!quoted && (char === '\n' || char === '\r')) {
      if (char === '\r' && text[index + 1] === '\n') index++;
      row.push(field); rows.push(row); row = []; field = '';
    } else field += char;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  assert.equal(quoted, false, 'CSV must close every quoted field');
  return rows;
}
const counts = { 'institution-wise': 9, 'bureau-wise': 3, 'region-wise': 5, 'status-wise': 5, 'ageing-buckets': 5, 'disposal-rate': 4, 'overlapping-cases': 15 };
for (const report of REPORTS) {
  test(report.label + ' screen source and downloaded CSV contain the same real rows', async () => {
    const api = await context();
    const data = await api(reportPath(report.type));
    assert.equal(data.type, report.type);
    assert.equal(data.as_of, '2026-10-24');
    assert.equal(data.rows.length, counts[report.type]);
    const blob = await api(reportPath(report.type, true), { responseType: 'blob' });
    assert.match(blob.type, /^text\/csv/);
    const rows = csvRows(await blob.text());
    assert.deepEqual(rows[0], data.columns);
    assert.equal(rows.length - 1, data.rows.length);
    data.rows.forEach((row, rowIndex) => data.columns.forEach((column, columnIndex) => {
      const value = row[column], cell = rows[rowIndex + 1][columnIndex];
      if (typeof value === 'number') { assert.notEqual(cell, ''); assert.equal(Number(cell), value); }
      else assert.equal(cell, value === null || value === undefined ? '' : typeof value === 'boolean' ? (value ? 'True' : 'False') : String(value));
    }));
    const response = await fetch(baseUrl + '/api' + reportPath(report.type, true));
    assert.equal(response.headers.get('content-disposition'), 'attachment; filename="' + reportFilename(report.type) + '"');
  });
}

test('supervisor reads the same all-bureau report tables as an officer', async () => {
  const [officer, supervisor] = await Promise.all([context(), context('Dr. R. K. Sharma')]);
  for (const report of REPORTS) {
    const [a, b] = await Promise.all([officer(reportPath(report.type)), supervisor(reportPath(report.type))]);
    assert.deepEqual(a, b);
  }
});

test('CSV request errors retain real HTTP status and detail instead of downloading JSON', async () => {
  const api = await context();
  await assert.rejects(api('/reports/not-a-report.csv', { responseType: 'blob' }), error => error instanceof ApiError && error.status === 404 && error.message === 'Unknown report type');
});

test('abandoned CSV fetches preserve request cancellation', async () => {
  const api = await context();
  const controller = new AbortController(); controller.abort();
  await assert.rejects(api(reportPath('bureau-wise', true), { responseType: 'blob', signal: controller.signal }), { name: 'AbortError' });
});

test('report routes and cells preserve zero, unresolved identity and unbounded age', () => {
  assert.deepEqual(parseRoute('#reports'), { kind: 'reports', key: 'reports' });
  assert.equal(parseRoute('#reports/not-a-report').kind, 'notfound');
  assert.throws(() => reportPath('../cases'), /valid report/);
  assert.equal(reportCell('total', 0), '0');
  assert.equal(reportCell('identity_resolved', false), 'No');
  assert.equal(reportCell('max_days', null), 'No upper limit');
  assert.equal(reportCell('aicte_id', null), 'Not supplied');
  assert.equal(reportCell('disposal_rate_percent', 16.67), '16.67%');
});
