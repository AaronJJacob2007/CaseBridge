from datetime import date

from backend.models import CoordinationRequest
from backend.tests.test_review2_completion import acknowledge, requested_item  # noqa: F401


def test_followups_cover_due_acknowledged_and_exclude_completed(api, requested_item):
    acknowledge(api, requested_item)
    request = api.db.get(CoordinationRequest, requested_item['id'])
    request.follow_up_on = date(2026, 10, 23)
    api.db.commit()
    status, data = api.request('GET', '/dashboard/overview')
    assert status == 200
    item = next(row for row in data['alerts']['coordination_follow_ups'] if row['id'] == request.id)
    assert item['status'] == 'acknowledged' and item['days_until_follow_up'] == -1
    assert item['owner'] == 'Anita Rao' and item['case_a'] != item['case_b']
    assert not data['alerts']['unacknowledged']
    request.follow_up_on = date(2026, 10, 31)
    api.db.commit()
    assert any(row['id'] == request.id and row['days_until_follow_up'] == 7 for row in api.request('GET', '/alerts')[1]['coordination_follow_ups'])
    request.follow_up_on = date(2026, 11, 1)
    api.db.commit()
    assert not api.request('GET', '/alerts')[1]['coordination_follow_ups']
    request.status = 'completed'
    request.follow_up_on = date(2026, 10, 23)
    api.db.commit()
    assert not api.request('GET', '/alerts')[1]['coordination_follow_ups']
