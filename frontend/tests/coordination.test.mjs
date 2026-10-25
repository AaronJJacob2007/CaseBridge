// Actual proxy/PostgreSQL reads and denied writes. Successful writes roll back in pytest.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createApi, loadDemoUsers, ApiError } from '../src/api.js';
import { buildLinkReview, buildCoordination, buildAcknowledgment, canReview } from '../src/coordinationTools.js';
import { parseRoute } from '../src/caseTools.js';
const baseUrl = 'http://127.0.0.1:5173';
async function context(name = 'Rahul Mehta') {
  const users = await loadDemoUsers({ baseUrl });
  const user = users.find(row => row.name === name);
  assert.ok(user);
  return { users, user, api: createApi(user.id, { baseUrl }) };
}
test('overlap list contains exact IDs, statuses, officers and cross-bureau cases', async () => {
  const { api } = await context();
  const groups = await api('/overlaps');
  assert.deepEqual(groups.map(row => row.aicte_id), ['INST-0001', 'INST-0003', 'INST-0006', 'INST-0008']);
  for (const group of groups) {
    assert.equal(group.message, 'Potential Overlapping Cases - Coordination Required');
    assert.ok(new Set(group.cases.map(row => row.bureau)).size >= 2);
    for (const row of group.cases) {
      assert.equal(row.identity_resolved, true);
      assert.equal(row.aicte_id, group.aicte_id);
      assert.notEqual(row.status, 'disposed');
      assert.ok(row.officer && row.case_code);
    }
  }
});
test('side-by-side reload exposes persisted reviews, requests and histories', async () => {
  const { api } = await context();
  const all = await api('/cases');
  const records = await Promise.all(['PGRC-101', 'RB-201'].map(code => api('/cases/' + all.find(row => row.case_code === code).id)));
  assert.equal(records[0].institution_id, records[1].institution_id);
  assert.notEqual(records[0].bureau, records[1].bureau);
  for (const row of records) {
    assert.ok(Array.isArray(row.links) && Array.isArray(row.coordination_requests) && row.history.length > 0);
    for (const link of row.links) assert.ok([link.case_a, link.case_b].includes(row.id));
  }
});
test('review access follows actual bureau roles including supervisor and other bureau', async () => {
  const { users, api } = await context();
  const all = await api('/cases');
  const a = all.find(row => row.case_code === 'PGRC-101'), b = all.find(row => row.case_code === 'RB-201');
  for (const user of users) assert.equal(canReview(user, a, b), user.role === 'officer' && ['PGRC', 'RB'].includes(user.bureau));
});
test('link review requires distinct IDs and a nonblank rejection reason', () => {
  assert.throws(() => buildLinkReview(1, 1, 'confirmed'), /different/);
  assert.throws(() => buildLinkReview(1, 2, 'rejected', '  '), /reason/);
  assert.deepEqual(buildLinkReview(1, 2, 'rejected', ' Unrelated incidents '), {
    case_a: 1, case_b: 2, type: 'cross_bureau_overlap', review_state: 'rejected', reason: 'Unrelated incidents',
  });
});
test('request builder preserves matching keys and requires separate-request justification', () => {
  const form = { action_type: 'Document request', doc_category: 'Fee records', period: '2025-26', to_bureau: 'PGRC' };
  assert.deepEqual(buildCoordination(7, form), { link_id: 7, ...form, follow_up_on: null });
  assert.throws(() => buildCoordination(7, form, 'proceed_separately'), /reason/);
  assert.equal(buildCoordination(7, { ...form, proceed_reason: 'Another evidence set' }, 'proceed_separately').proceed_reason, 'Another evidence set');
  assert.equal(buildCoordination(7, { ...form, proceed_reason: 'hidden stale reason' }, 'coordinate').proceed_reason, undefined);
});
test('acknowledgment requires an owner and follow-up without using system today', () => {
  assert.throws(() => buildAcknowledgment('', '2026-10-30'), /valid/);
  assert.throws(() => buildAcknowledgment(1, ''), /follow-up/);
  assert.deepEqual(buildAcknowledgment('2', '2026-10-30'), { owner_id: 2, follow_up_on: '2026-10-30' });
});
test('comparison route survives reload and rejects malformed or identical pairs', () => {
  assert.deepEqual(parseRoute('#overlaps/1/2'), { kind: 'overlaps', key: 'overlaps/1/2', pair: [1, 2] });
  assert.equal(parseRoute('#overlaps').kind, 'overlaps');
  for (const hash of ['#overlaps/1/1', '#overlaps/0/2', '#overlaps/a/2', '#overlaps/1/2/3']) assert.equal(parseRoute(hash).kind, 'notfound');
});
test('blocked supervisor review surfaces real 403 detail and keeps overlap alerts', async () => {
  const { api } = await context('Dr. R. K. Sharma');
  const all = await api('/cases');
  const a = all.find(row => row.case_code === 'PGRC-101'), b = all.find(row => row.case_code === 'RB-201');
  await assert.rejects(api('/links', { method: 'POST', body: buildLinkReview(a.id, b.id, 'confirmed') }), error =>
    error instanceof ApiError && error.status === 403 && error.message === 'Supervisors are read-only' && error.data.detail === error.message);
  assert.equal((await api('/overlaps')).length, 4);
});

test('completion controls require target-bureau officer and an actual acknowledgment', async () => {
  const { canCompleteRequest } = await import('../src/coordinationTools.js');
  const target = { role: 'officer', bureau: 'PGRC' };
  const base = { to_bureau: 'PGRC', acknowledged_at: '2026-10-25T12:00:00Z' };
  for (const status of ['requested', 'completed', 'declined']) assert.equal(canCompleteRequest(target, { ...base, status }), false);
  for (const status of ['acknowledged', 'in_progress']) {
    assert.equal(canCompleteRequest(target, { ...base, status }), true);
    assert.equal(canCompleteRequest(target, { ...base, status, acknowledged_at: null }), false);
    assert.equal(canCompleteRequest({ role: 'supervisor', bureau: 'PGRC' }, { ...base, status }), false);
    assert.equal(canCompleteRequest({ role: 'officer', bureau: 'RB' }, { ...base, status }), false);
  }
});
