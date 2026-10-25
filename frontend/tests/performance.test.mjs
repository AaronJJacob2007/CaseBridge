import test from 'node:test';
import assert from 'node:assert/strict';
import { performancePath, reportCell, columnLabel } from '../src/reportTools.js';
import { numericReportColumn, presentationCsv } from '../src/reportPresentation.js';

test('performance JSON and CSV requests preserve the selected calendar period', () => {
  const selected = { kind: 'quarterly', year: '2026', period: '3' };
  assert.equal(performancePath(selected), '/reports/performance?kind=quarterly&year=2026&period=3');
  assert.equal(performancePath(selected, true), '/reports/performance.csv?kind=quarterly&year=2026&period=3');
  for (const bad of [{ ...selected, period: 5 }, { ...selected, year: '' }, { ...selected, kind: 'weekly' }]) assert.throws(() => performancePath(bad));
});

test('performance tables show readable date boundaries and numeric zero counts', () => {
  assert.equal(reportCell('period_start', '2026-10-01'), '1 Oct 2026');
  assert.equal(reportCell('status_as_of', '2026-10-24'), '24 Oct 2026');
  for (const key of ['received', 'disposed', 'outstanding']) {
    assert.equal(numericReportColumn(key), true);
    assert.equal(reportCell(key, 0), '0');
  }
  assert.equal(columnLabel('receipts_through'), 'Receipts counted through');
});

test('performance browser CSV retains period boundaries and all zero counts', async () => {
  const source = 'period_start,period_end,receipts_through,status_as_of,bureau,received,disposed,outstanding\r\n2026-10-01,2026-12-31,2026-10-24,2026-10-24,All,0,0,0\r\n';
  const blob = await presentationCsv(new Blob([source], { type: 'text/csv' }));
  assert.equal(await blob.text(), source);
});
