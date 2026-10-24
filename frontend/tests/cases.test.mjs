// Real proxy/API reads, plus production form builders with actual DB users.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createApi, loadDemoUsers, ApiError } from '../src/api.js';
import { buildCaseQuery, buildCaseCreate, buildCaseAction, canWriteCase, institutionLink, parseRoute } from '../src/caseTools.js';

const baseUrl = 'http://127.0.0.1:5173';
async function context(name = 'Anita Rao') {
  const users = await loadDemoUsers({ baseUrl });
  const user = users.find((row) => row.name === name);
  assert.ok(user);
  return { user, users, api: createApi(user.id, { baseUrl }) };
}

test('case-register query builder drives all eight real API filters', async () => {
  const { api } = await context();
  for (const [filters, expected] of [
    [{ institution_name: 'Riverbend' }, 7], [{ aicte_id: 'INST-0001' }, 5],
    [{ case_code: 'PGRC-109' }, 1], [{ bureau: 'PGRC' }, 17], [{ region: 'West' }, 12],
    [{ category: 'Fee collection' }, 4], [{ status: 'disposed' }, 5],
    [{ received_from: '2026-10-01', received_to: '2026-10-09' }, 3],
  ]) assert.equal((await api('/cases?' + buildCaseQuery(filters))).length, expected, JSON.stringify(filters));
});

test('combined filters use AND and clearing filters returns the full register', async () => {
  const { api } = await context();
  const rows = await api('/cases?' + buildCaseQuery({ institution_name: 'Riverbend', aicte_id: 'INST-0001', bureau: 'RB', status: 'pending' }));
  assert.deepEqual(rows.map((row) => row.case_code), ['RB-201']);
  assert.equal(buildCaseQuery({ institution_name: '', bureau: '' }), '');
  assert.equal((await api('/cases')).length, 30);
});

test('Central filter includes reported region without resolving PGRC-109', async () => {
  const { api } = await context();
  const rows = await api('/cases?' + buildCaseQuery({ region: 'Central' }));
  assert.equal(rows.length, 5);
  const unknown = rows.find((row) => row.case_code === 'PGRC-109');
  assert.equal(unknown.identity_resolved, false);
  assert.equal(unknown.institution_id, null);
  assert.equal(institutionLink(unknown), null);
});

test('workspace reload reads actual owner, next action and chronological history', async () => {
  const { api } = await context();
  const record = (await api('/cases?case_code=PGRC-101'))[0];
  const first = await api('/cases/' + record.id);
  const second = await api('/cases/' + record.id);
  assert.deepEqual(second, first);
  assert.equal(first.officer, 'Anita Rao');
  assert.ok('next_action' in first && first.history.length > 0);
  assert.deepEqual(first.history.map((row) => [row.at, row.id]), first.history.map((row) => [row.at, row.id]).toSorted((a, b) => a[0].localeCompare(b[0]) || a[1] - b[1]));
});

test('institution link opens the exact ID with all five case histories', async () => {
  const { api } = await context();
  const record = (await api('/cases?case_code=PGRC-101'))[0];
  assert.equal(institutionLink(record), '#institutions/' + record.institution_id);
  const profile = await api('/institutions/' + record.institution_id);
  assert.equal(profile.aicte_id, 'INST-0001');
  assert.equal(profile.address, '12 Lake Road, Pune');
  assert.deepEqual(profile.bureaus_involved, ['PGRC', 'RB']);
  assert.equal(profile.cases.length, 5);
  assert.ok(profile.cases.every((row) => row.history.length > 0));
});

test('visible write access follows actual role and bureau, not just ownership', async () => {
  const { api, users, user } = await context();
  const cases = await api('/cases');
  const pgrc = cases.find((row) => row.case_code === 'PGRC-101');
  const rb = cases.find((row) => row.case_code === 'RB-201');
  assert.equal(canWriteCase(user, pgrc), true);
  assert.equal(canWriteCase(user, rb), false);
  assert.equal(canWriteCase(users.find((row) => row.name === 'Vikram Singh'), pgrc), true);
  assert.equal(canWriteCase(users.find((row) => row.role === 'supervisor'), pgrc), false);
});

test('entry form preserves exact ID and leaves blank received date to the backend', async () => {
  const { user } = await context();
  const body = buildCaseCreate({ case_code: 'FORM-CHECK', institution_name: 'Synthetic', aicte_id: ' INST-0001 ', raw_region: 'Central', received_on: '', remarks: 'Form input' }, user);
  assert.equal(body.aicte_id, ' INST-0001 ');
  assert.equal(body.bureau, user.bureau);
  assert.equal(body.officer_id, user.id);
  assert.equal(body.raw_region, 'Central');
  assert.equal('received_on' in body, false);
});

test('note form omits hidden ownership/status fields and explicitly clears optional fields', () => {
  const body = buildCaseAction({ event_type: 'update', remarks: 'A note', doc_ref: 'reply.pdf', status: '', next_action: '', expected_disposal_on: '', to_bureau: 'RB', officer_id: '999' });
  assert.equal(body.doc_ref, 'reply.pdf');
  assert.equal(body.next_action, null);
  assert.equal(body.expected_disposal_on, null);
  assert.equal('officer_id' in body || 'to_bureau' in body || 'status' in body, false);
  assert.throws(() => buildCaseAction({ remarks: 'Note', doc_ref: 'C:\\reply.pdf' }), /file name/);
});

test('transfer and escalation payloads cannot inherit a hidden disposal status', async () => {
  const { users } = await context();
  const owner = users.find((row) => row.name === 'Rahul Mehta');
  const transfer = buildCaseAction({ event_type: 'transfer', remarks: 'Transfer', to_bureau: 'RB', officer_id: String(owner.id), status: 'disposed' });
  assert.equal(transfer.officer_id, owner.id);
  assert.equal(transfer.to_bureau, 'RB');
  assert.equal('status' in transfer, false);
  const escalation = buildCaseAction({ event_type: 'escalate', remarks: 'Review', status: 'disposed', officer_id: String(owner.id) });
  assert.equal(escalation.event_type, 'escalate');
  assert.equal('status' in escalation || 'officer_id' in escalation, false);
});

test('invalid date range is rejected locally and by the real service', async () => {
  assert.throws(() => buildCaseQuery({ received_from: '2026-10-09', received_to: '2026-10-01' }), /after/);
  const { api } = await context();
  await assert.rejects(api('/cases?received_from=2026-10-09&received_to=2026-10-01'), (error) => error instanceof ApiError && error.status === 422);
});

test('empty searches and unknown case/profile addresses stay empty or 404', async () => {
  const { api } = await context();
  assert.deepEqual(await api('/cases?' + buildCaseQuery({ case_code: 'NO-SUCH-CASE' })), []);
  for (const path of ['/cases/2147483647', '/institutions/2147483647']) {
    await assert.rejects(api(path), (error) => error instanceof ApiError && error.status === 404);
  }
});

test('case/profile hash routes survive reload and reject malformed identifiers', async () => {
  const { api } = await context();
  const record = (await api('/cases?case_code=PGRC-101'))[0];
  assert.deepEqual(parseRoute('#cases/' + record.id), { kind: 'case', id: record.id, key: 'cases/' + record.id });
  assert.equal(parseRoute(institutionLink(record)).kind, 'institution');
  assert.equal(parseRoute('#cases').kind, 'register');
  assert.equal(parseRoute('#cases/-1').kind, 'notfound');
  assert.equal(parseRoute('#cases/1/extra').kind, 'notfound');
});


test('real client case POST surfaces duplicate conflict without creating a case', async () => {
  const { user, api } = await context();
  const body = buildCaseCreate({ case_code: 'PGRC-101', institution_name: 'Synthetic duplicate attempt',
    aicte_id: 'INST-0001', remarks: 'Duplicate validation check' }, user);
  await assert.rejects(api('/cases', { method: 'POST', body }), (error) => error instanceof ApiError && error.status === 409);
  assert.equal((await api('/cases')).length, 30);
});
