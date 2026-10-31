export function buildOverview(user, summary, alerts, cases) {
  const supervisor = user.role === 'supervisor';
  const forBureau = (rows) => supervisor ? rows : rows.filter((row) => row.bureau === user.bureau);
  const visibleAlerts = {
    overlap: supervisor ? alerts.overlap : alerts.overlap.filter((group) => group.cases.some((row) => row.bureau === user.bureau)),
    pending_too_long: forBureau(alerts.pending_too_long),
    due_within_7_days: forBureau(alerts.due_within_7_days),
    overdue: forBureau(alerts.overdue),
    escalated: forBureau(alerts.escalated),
    unacknowledged: supervisor ? alerts.unacknowledged : alerts.unacknowledged.filter((row) => row.to_bureau === user.bureau),
  };
  return {
    user, summary, supervisor, alerts: visibleAlerts,
    scopeLabel: supervisor ? 'All bureaus' : user.bureau + ' bureau',
    bureau: summary.bureau_wise.find((row) => row.bureau === user.bureau) ?? null,
    assignedOpen: cases.filter((row) => row.officer_id === user.id && row.status !== 'disposed').length,
    resolvedInstitutions: summary.institution_wise.filter((row) => row.identity_resolved).length,
  };
}

export async function loadOverview(api, { signal, user: currentUser } = {}) {
  const [user, overview] = await Promise.all([
    currentUser ? Promise.resolve(currentUser) : api('/demo/me', { signal }),
    api('/dashboard/overview', { signal }),
  ]);
  return buildOverview(user, overview.summary, overview.alerts, overview.cases);
}
