"""Review issue 1: real cross-bureau request matching in rollback transactions."""
import pytest
from sqlalchemy import func, select

from backend.models import ActionLog, CoordinationRequest
from backend.tests.test_slice3 import check_body, review


@pytest.mark.parametrize('pending_status', ['requested', 'acknowledged', 'in_progress'])
def test_reverse_target_and_different_requester_still_warn(api, pending_status):
    status, link = review(api, actor='Rahul Mehta')
    assert status == 200 and link['review_state'] == 'confirmed'
    keys = check_body(link['id'])
    status, created = api.request('POST', '/coordination', {
        **keys, 'to_bureau': 'PGRC',
    }, api.user('Rahul Mehta'))
    assert status == 201 and created['outcome'] == 'created'
    original = created['request']
    assert original['requester'] == 'Rahul Mehta' and original['to_bureau'] == 'PGRC'

    if pending_status != 'requested':
        status, acknowledged = api.request('POST', f"/coordination/{original['id']}/ack", {
            'owner_id': api.user('Anita Rao'), 'follow_up_on': '2026-10-30',
        }, api.user('Anita Rao'))
        assert status == 200 and acknowledged['acknowledged_at']
        if pending_status == 'in_progress':
            # No progress endpoint exists; construct the allowed stored state.
            api.db.get(CoordinationRequest, original['id']).status = 'in_progress'
            api.db.commit()

    before_logs = api.db.scalar(select(func.count()).select_from(ActionLog))
    status, warning = api.request('POST', '/coordination/check', {
        **keys, 'to_bureau': 'RB',
    }, api.user('Anita Rao'))
    assert status == 200 and warning['warning'] is True
    existing = warning['existing_request']
    assert existing['id'] == original['id']
    assert existing['institution_id'] == original['institution_id']
    assert existing['link_id'] == link['id']
    assert existing['requested_by'] == api.user('Rahul Mehta')
    assert existing['requester'] == 'Rahul Mehta'
    assert existing['to_bureau'] == 'PGRC'  # Original target, not Anita's draft.
    assert existing['status'] == pending_status
    for key in ('action_type', 'doc_category', 'period'):
        assert existing[key] == keys[key]
    assert warning['choices'] == ['coordinate', 'proceed_separately']
    assert api.db.scalar(select(func.count()).select_from(CoordinationRequest)) == 1
    assert api.db.scalar(select(func.count()).select_from(ActionLog)) == before_logs

    # The save also rechecks: reversing requester/target cannot bypass warning.
    status, blocked = api.request('POST', '/coordination', {
        **keys, 'to_bureau': 'RB',
    }, api.user('Anita Rao'))
    assert status == 409 and blocked['warning'] is True
    assert blocked['existing_request']['id'] == original['id']
    assert api.db.scalar(select(func.count()).select_from(CoordinationRequest)) == 1
