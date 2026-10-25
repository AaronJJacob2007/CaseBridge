// Shared production payloads and check-before-save flow.
function id(value) {
  const result = Number(value);
  if (!Number.isSafeInteger(result) || result < 1) throw new Error('Choose a valid record.');
  return result;
}
const optional = value => value?.trim() || null;
export const canReview = (user, a, b) => user.role === 'officer' && [a.bureau, b.bureau].includes(user.bureau);
export const canCompleteRequest = (user, request) => user.role === 'officer'
  && user.bureau === request.to_bureau
  && ['acknowledged', 'in_progress'].includes(request.status)
  && Boolean(request.acknowledged_at);
export function buildLinkReview(a, b, state, reason = '') {
  if (id(a) === id(b)) throw new Error('Choose two different cases.');
  if (!['confirmed', 'rejected'].includes(state)) throw new Error('Choose Confirm or Reject.');
  if (state === 'rejected' && !reason.trim()) throw new Error('A rejection reason is required.');
  return { case_a: id(a), case_b: id(b), type: 'cross_bureau_overlap', review_state: state, reason: optional(reason) };
}
export function buildCoordination(linkId, form, decision) {
  if (!form.action_type?.trim()) throw new Error('Action type is required.');
  if (!form.to_bureau) throw new Error('Choose a target bureau.');
  const body = {
    link_id: id(linkId), action_type: form.action_type.trim(),
    doc_category: optional(form.doc_category), period: optional(form.period), to_bureau: form.to_bureau,
    follow_up_on: form.follow_up_on || null,
  };
  if (decision) {
    if (!['coordinate', 'proceed_separately'].includes(decision)) throw new Error('Invalid warning choice.');
    body.decision = decision;
    if (decision === 'proceed_separately') {
      if (!form.proceed_reason?.trim()) throw new Error('A reason is required to proceed separately.');
      body.proceed_reason = form.proceed_reason.trim();
    }
  }
  return body;
}
export function buildAcknowledgment(owner, date) {
  if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(date || '')) throw new Error('Choose a follow-up date.');
  return { owner_id: id(owner), follow_up_on: date };
}
export async function checkCoordination(api, body) {
  const { link_id, action_type, doc_category, period, to_bureau } = body;
  return api('/coordination/check', { method: 'POST', body: {
    link_id, action_type, doc_category, period,
    ...(to_bureau !== undefined ? { to_bureau } : {}),
  } });
}
export async function submitCoordination(api, body) {
  // Recheck immediately before every save, including either warning choice.
  const check = await checkCoordination(api, body);
  if (check.warning && !body.decision) return { outcome: 'warning', ...check };
  if (!check.warning && body.decision) throw new Error('The pending request changed. Check again before saving.');
  try {
    return await api('/coordination', { method: 'POST', body });
  } catch (error) {
    // A concurrent save may create a match after our check. Show that warning.
    if (error.status === 409 && error.data?.warning) return { outcome: 'warning', ...error.data };
    throw error;
  }
}
