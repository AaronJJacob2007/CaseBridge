// Run with the real backend and Vite proxy running; no mocked API responses.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, stat } from 'node:fs/promises';
import { createApi, loadDemoUsers, ApiError } from '../src/api.js';
import { loadOverview } from '../src/overview.js';

const baseUrl = 'http://127.0.0.1:5173';
async function userByName(name) {
  const users = await loadDemoUsers({ baseUrl });
  const user = users.find((row) => row.name === name);
  assert.ok(user, 'Expected real seeded demo user: ' + name);
  return user;
}

// Every value below is an acceptance expectation for the supplied synthetic seed.
// The app itself contains no seed IDs, users or case-count fixtures.
test('demo catalog and identity are loaded through the real Vite proxy', async () => {
  const users = await loadDemoUsers({ baseUrl });
  assert.equal(users.length, 6);
  assert.equal(new Set(users.map((row) => row.id)).size, 6);
  assert.ok(users.every((row) => Number.isInteger(row.id) && row.id > 0 && row.name));
  const api = createApi(users[0].id, { baseUrl });
  const profile = await api('/demo/me');
  assert.deepEqual(profile, users[0]);
  assert.deepEqual(await api('/health'), { status: 'ok', database: 'ok' });
});

test('PGRC officer sees real global totals and scoped workload/flags', async () => {
  const actor = await userByName('Anita Rao');
  const view = await loadOverview(createApi(actor.id, { baseUrl }));
  assert.equal(view.supervisor, false);
  assert.equal(view.scopeLabel, 'PGRC bureau');
  assert.equal(view.bureau.total, 17);
  assert.equal(view.assignedOpen, 7);
  for (const [key, value] of Object.entries({ total: 30, pending: 10, under_process: 12, escalated: 2, transferred: 1, disposed: 5, overdue: 7, due_within_7_days: 7 })) {
    assert.equal(view.summary[key], value, key);
  }
  assert.equal(view.alerts.overdue.length, 5);
  assert.equal(view.alerts.due_within_7_days.length, 3);
  assert.equal(view.alerts.pending_too_long.length, 3);
});

test('RB user switch changes bureau workload, assignments and flags', async () => {
  const actor = await userByName('Rahul Mehta');
  const view = await loadOverview(createApi(actor.id, { baseUrl }));
  assert.equal(view.user.id, actor.id);
  assert.equal(view.scopeLabel, 'RB bureau');
  assert.equal(view.bureau.total, 11);
  assert.equal(view.assignedOpen, 5);
  assert.equal(view.alerts.overdue.length, 1);
  assert.equal(view.alerts.due_within_7_days.length, 3);
  assert.equal(view.alerts.pending_too_long.length, 2);
  assert.equal(view.summary.total, 30);
});

test('supervisor receives all-bureau context and unchanged chart source counts', async () => {
  const actor = await userByName('Dr. R. K. Sharma');
  const view = await loadOverview(createApi(actor.id, { baseUrl }));
  assert.equal(view.supervisor, true);
  assert.equal(view.scopeLabel, 'All bureaus');
  assert.equal(view.summary.open, 25);
  assert.equal(view.resolvedInstitutions, 8);
  assert.equal(view.alerts.overlap.length, 4);
  assert.equal(view.alerts.overdue.length, 7);
  assert.equal(view.alerts.pending_too_long.length, 6);
  assert.deepEqual(Object.fromEntries(view.summary.bureau_wise.map((row) => [row.bureau, row.total])), { OTHER: 2, PGRC: 17, RB: 11 });
  assert.deepEqual(Object.fromEntries(view.summary.region_wise.map((row) => [row.region, row.total])), { Central: 5, East: 6, North: 2, South: 5, West: 12 });
});

test('parallel user loads keep independent X-User-Id contexts', async () => {
  const [anita, rahul] = await Promise.all([userByName('Anita Rao'), userByName('Rahul Mehta')]);
  const [pgrc, rb] = await Promise.all([
    loadOverview(createApi(anita.id, { baseUrl })),
    loadOverview(createApi(rahul.id, { baseUrl })),
  ]);
  assert.equal(pgrc.user.id, anita.id);
  assert.equal(rb.user.id, rahul.id);
  assert.equal(pgrc.bureau.total, 17);
  assert.equal(rb.bureau.total, 11);
});

test('invalid selected identity surfaces the real 403 instead of fallback data', async () => {
  await assert.rejects(createApi(2147483647, { baseUrl })('/demo/me'), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 403);
    assert.equal(error.message, 'Select a valid demo user');
    return true;
  });
  assert.throws(() => createApi(0, { baseUrl }), ApiError);
});

test('request cancellation is preserved for abandoned user selections', async () => {
  const actor = await userByName('Anita Rao');
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(createApi(actor.id, { baseUrl })('/demo/me', { signal: controller.signal }), { name: 'AbortError' });
});

test('built frontend assets and the running overview document are available', async () => {
  const html = await readFile(new URL('../dist/index.html', import.meta.url), 'utf8');
  const asset = html.match(/src="(\/assets\/[^\"]+\.js)"/);
  assert.ok(asset, 'Expected a bundled JavaScript asset in the production index');
  assert.ok((await stat(new URL('../dist' + asset[1], import.meta.url))).size > 0);
  const response = await fetch(baseUrl + '/');
  assert.equal(response.status, 200);
  const page = await response.text();
  assert.ok(page.includes('CaseBridge | Overview'));
  assert.ok(page.includes('/src/main.jsx'));
});
