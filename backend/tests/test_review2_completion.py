"""Review issue 2: acknowledgment is a prerequisite for request completion."""
import pytest
from sqlalchemy import func, select

from backend.models import ActionLog, CoordinationRequest
from backend.tests.test_slice3 import check_body, identity, review


@pytest.fixture
def requested_item(api):
    status, link = review(api)
    assert status == 200
    status, result = api.request('POST', '/coordination', {
        **check_body(link['id']), 'to_bureau': 'PGRC',
    }, api.user('Rahul Mehta'))
    assert status == 201
    return result['request']


def acknowledge(api, item):
    status, result = api.request('POST', f"/coordination/{item['id']}/ack", {
        'owner_id': api.user('Anita Rao'), 'follow_up_on': '2026-10-30',
    }, api.user('Anita Rao'))
    assert status == 200 and result['acknowledged_at']
    return result


def test_unacknowledged_request_cannot_complete_or_remove_warning(api, requested_item):
    item = requested_item
    before = api.db.scalar(select(func.count()).select_from(ActionLog))
    status, error = api.request('POST', f"/coordination/{item['id']}/complete", {
        'remarks': 'Attempt before acknowledgment',
    }, api.user('Anita Rao'))
    assert status == 409
    assert error['detail'] == 'Acknowledge the request before marking it completed'
    api.db.expire_all()
    stored = api.db.get(CoordinationRequest, item['id'])
    assert stored.status == 'requested' and stored.acknowledged_at is None and stored.owner_id is None
    assert api.db.scalar(select(func.count()).select_from(ActionLog)) == before
    status, warning = api.request('POST', '/coordination/check', {
        **check_body(item['link_id']), 'to_bureau': 'RB',
    }, api.user('Anita Rao'))
    assert status == 200 and warning['warning'] is True
    assert warning['existing_request']['id'] == item['id']


@pytest.mark.parametrize('state', ['acknowledged', 'in_progress'])
def test_acknowledged_request_can_complete_once_without_changing_cases(api, requested_item, state):
    item = requested_item
    acknowledged = acknowledge(api, item)
    if state == 'in_progress':
        api.db.get(CoordinationRequest, item['id']).status = state
        api.db.commit()
    statuses = {code: api.request('GET', f"/cases/{identity(api, code)}")[1]['status']
                for code in ('PGRC-101', 'RB-201')}
    status, completed = api.request('POST', f"/coordination/{item['id']}/complete", {
        'remarks': 'Coordination concluded after acknowledgment',
    }, api.user('Anita Rao'))
    assert status == 200 and completed['status'] == 'completed'
    assert completed['acknowledged_at'] == acknowledged['acknowledged_at']
    assert completed['owner_id'] == acknowledged['owner_id']
    for code, original_status in statuses.items():
        _, detail = api.request('GET', f"/cases/{identity(api, code)}")
        assert detail['status'] == original_status
        completions = [entry for entry in detail['history']
                       if entry['event_type'] == 'update' and entry['remarks'] == f"Request {item['id']} completed: Coordination concluded after acknowledgment"]
        assert len(completions) == 1
    assert api.request('POST', f"/coordination/{item['id']}/complete", {}, api.user('Anita Rao'))[0] == 409
    assert api.request('POST', '/coordination/check', check_body(item['link_id']), api.user('Anita Rao'))[1]['warning'] is False


@pytest.mark.parametrize('state', ['acknowledged', 'in_progress'])
def test_status_without_actual_acknowledgment_cannot_bypass_completion_guard(api, requested_item, state):
    stored = api.db.get(CoordinationRequest, requested_item['id'])
    stored.status = state
    api.db.commit()
    status, error = api.request('POST', f"/coordination/{stored.id}/complete", {}, api.user('Anita Rao'))
    assert status == 409 and 'Acknowledge the request' in error['detail']
    api.db.expire_all()
    assert api.db.get(CoordinationRequest, stored.id).status == state


def test_rejecting_link_does_not_allow_unacknowledged_completion(api, requested_item):
    assert review(api, review_state='rejected', reason='Different incidents')[0] == 200
    status, error = api.request('POST', f"/coordination/{requested_item['id']}/complete", {}, api.user('Anita Rao'))
    assert status == 409 and 'Acknowledge the request' in error['detail']
    assert api.db.get(CoordinationRequest, requested_item['id']).status == 'requested'
