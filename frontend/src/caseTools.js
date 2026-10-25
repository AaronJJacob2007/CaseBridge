export const STATUSES = ['pending', 'under_process', 'escalated', 'transferred', 'disposed'];
export const FILTER_KEYS = ['institution_name', 'aicte_id', 'case_code', 'bureau', 'region', 'category', 'status', 'received_from', 'received_to'];
export const EMPTY_FILTERS = Object.fromEntries(FILTER_KEYS.map((key) => [key, '']));
export const statusLabel = (value) => ({ pending: 'Pending', under_process: 'Under process', escalated: 'Escalated', transferred: 'Transferred', disposed: 'Disposed' }[value] ?? value);
export const canWriteCase = (user, record) => user.role === 'officer' && user.bureau === record.bureau;
export const institutionLink = (record) => record.identity_resolved && record.institution_id ? '#institutions/' + record.institution_id : null;

export function parseRoute(hash) {
  const value = hash.replace(/^#\/?/, '');
  if (!value || value === 'main' || value === 'overview') return { kind: 'overview', key: 'overview' };
  if (value === 'overlaps') return { kind: 'overlaps', key: value };
  const pair = value.match(/^overlaps\/([1-9]\d*)\/([1-9]\d*)$/);
  if (pair && pair.slice(1).every(v => Number.isSafeInteger(Number(v))) && pair[1] !== pair[2]) return { kind: 'overlaps', key: value, pair: pair.slice(1).map(Number) };
  if (value === 'cases') return { kind: 'register', key: 'cases' };
  const match = value.match(/^(cases|institutions)\/([1-9]\d*)$/);
  if (match && Number.isSafeInteger(Number(match[2]))) {
    return { kind: match[1] === 'cases' ? 'case' : 'institution', id: Number(match[2]), key: value };
  }
  return { kind: 'notfound', key: value };
}

export function buildCaseQuery(filters) {
  if (filters.received_from && filters.received_to && filters.received_from > filters.received_to) {
    throw new Error('Received-from date cannot be after received-to date.');
  }
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    if (filters[key] !== '' && filters[key] !== undefined && filters[key] !== null) params.set(key, filters[key]);
  }
  return params.toString();
}

const optional = (value) => value?.trim() || null;
function positiveId(value) {
  const id = Number(value);
  if (!Number.isSafeInteger(id) || id <= 0) throw new Error('Select a valid officer.');
  return id;
}

export function buildCaseCreate(form, user) {
  if (user.role !== 'officer') throw new Error('Supervisors are read-only.');
  if (!form.case_code?.trim() || !form.institution_name?.trim() || !form.remarks?.trim()) {
    throw new Error('Case code, institution name and registration remarks are required.');
  }
  return {
    case_code: form.case_code.trim(), institution_name: form.institution_name.trim(),
    // Preserve exact AICTE ID input. Region never establishes institution identity.
    aicte_id: form.aicte_id || null, raw_region: optional(form.raw_region),
    bureau: user.bureau, officer_id: positiveId(form.officer_id || user.id),
    category: optional(form.category), description: optional(form.description),
    status: form.status || 'pending', remarks: form.remarks.trim(),
    next_action: optional(form.next_action), expected_disposal_on: form.expected_disposal_on || null,
    ...(form.received_on ? { received_on: form.received_on } : {}),
  };
}

export function buildCaseAction(form) {
  if (!form.remarks?.trim()) throw new Error('Remarks are required.');
  const doc = optional(form.doc_ref);
  if (doc && (/[\\/:]/.test(doc) || doc === '.' || doc === '..')) throw new Error('Document reference must be a file name only.');
  const body = {
    event_type: form.event_type || 'update', remarks: form.remarks.trim(), doc_ref: doc,
    next_action: optional(form.next_action), expected_disposal_on: form.expected_disposal_on || null,
  };
  if (body.event_type === 'transfer') {
    if (!form.to_bureau) throw new Error('Select a target bureau.');
    body.to_bureau = form.to_bureau;
    body.officer_id = positiveId(form.officer_id);
  } else if (body.event_type === 'update' && form.status) {
    body.status = form.status;
  }
  return body;
}

export function formatDate(value) {
  return value ? new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value + 'T00:00:00')) : 'Not recorded';
}
export function formatTimestamp(value) {
  return value ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'Not recorded';
}
