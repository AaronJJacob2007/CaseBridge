"""Live acceptance must validate saved request alerts rather than require none."""
from copy import deepcopy

import pytest

from backend.tests.test_slice4 import make_request, read
from backend.verify_http_slice4 import check_unacknowledged


def test_live_alert_check_accepts_saved_overdue_request_and_detects_wrong_results(api):
    request = make_request(api, '2026-10-23')
    data = read(api, '/alerts')
    check_unacknowledged(data, api.db)
    assert [row['id'] for row in data['unacknowledged']] == [request['id']]

    missing = deepcopy(data)
    missing['unacknowledged'] = []
    with pytest.raises(AssertionError, match='IDs/order'):
        check_unacknowledged(missing, api.db)
    extra = deepcopy(data)
    extra['unacknowledged'].append(deepcopy(extra['unacknowledged'][0]))
    with pytest.raises(AssertionError, match='IDs/order'):
        check_unacknowledged(extra, api.db)
    incorrect_age = deepcopy(data)
    incorrect_age['unacknowledged'][0]['days_past_follow_up'] = 0
    with pytest.raises(AssertionError):
        check_unacknowledged(incorrect_age, api.db)

    status, _ = api.request('POST', f"/coordination/{request['id']}/ack", {
        'owner_id': api.user('Anita Rao'), 'follow_up_on': '2026-10-30',
    }, api.user('Anita Rao'))
    assert status == 200
    after = read(api, '/alerts')
    check_unacknowledged(after, api.db)
    assert after['unacknowledged'] == []
    with pytest.raises(AssertionError, match='IDs/order'):
        check_unacknowledged(data, api.db)
